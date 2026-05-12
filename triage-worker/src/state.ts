import type { ActivityEvent, BudgetState } from "./types";

const MAX_ACTIVITY = 500;
const PROCESSED_TTL_MS = 7 * 24 * 60 * 60 * 1000;

interface ProcessedRecord {
  ts: number;
}

interface OAuthCache {
  accessToken: string;
  expiresAt: number;
}

export class TriageStateDO {
  private state: DurableObjectState;
  private sseClients = new Set<WritableStreamDefaultWriter<Uint8Array>>();

  constructor(state: DurableObjectState) {
    this.state = state;
  }

  async fetch(req: Request): Promise<Response> {
    const url = new URL(req.url);
    switch (url.pathname) {
      case "/budget":
        return this.handleBudget(req);
      case "/budget/charge":
        return this.handleCharge(req);
      case "/activity":
        return this.handleActivity(req);
      case "/activity/stream":
        return this.handleActivityStream();
      case "/append":
        return this.handleAppend(req);
      case "/processed/check":
        return this.handleProcessedCheck(req);
      case "/processed/mark":
        return this.handleProcessedMark(req);
      case "/gmail-token":
        return this.handleGmailToken(req);
      case "/gmail-token/set":
        return this.handleGmailTokenSet(req);
    }
    return new Response("not found", { status: 404 });
  }

  // --- Budget ---

  private todayKey(): string {
    return new Date().toISOString().slice(0, 10);
  }

  private async getBudget(): Promise<BudgetState> {
    const today = this.todayKey();
    const cur = (await this.state.storage.get<BudgetState>("budget")) ?? {
      date: today,
      spentUsd: 0,
      triageCount: 0,
    };
    if (cur.date !== today) {
      const fresh: BudgetState = { date: today, spentUsd: 0, triageCount: 0 };
      await this.state.storage.put("budget", fresh);
      return fresh;
    }
    return cur;
  }

  private async handleBudget(_req: Request): Promise<Response> {
    return Response.json(await this.getBudget());
  }

  private async handleCharge(req: Request): Promise<Response> {
    const { costUsd } = (await req.json()) as { costUsd: number };
    const cur = await this.getBudget();
    cur.spentUsd += costUsd;
    cur.triageCount += 1;
    await this.state.storage.put("budget", cur);
    return Response.json(cur);
  }

  // --- Activity log ---

  private async handleAppend(req: Request): Promise<Response> {
    const ev = (await req.json()) as ActivityEvent;
    const list =
      (await this.state.storage.get<ActivityEvent[]>("activity")) ?? [];
    list.push(ev);
    if (list.length > MAX_ACTIVITY) list.splice(0, list.length - MAX_ACTIVITY);
    await this.state.storage.put("activity", list);
    this.broadcast(ev);
    return new Response("ok");
  }

  private async handleActivity(req: Request): Promise<Response> {
    const url = new URL(req.url);
    const limit = Math.min(
      parseInt(url.searchParams.get("limit") ?? "100", 10),
      MAX_ACTIVITY,
    );
    const list =
      (await this.state.storage.get<ActivityEvent[]>("activity")) ?? [];
    return Response.json(list.slice(-limit).reverse());
  }

  private async handleActivityStream(): Promise<Response> {
    const { readable, writable } = new TransformStream<Uint8Array, Uint8Array>();
    const writer = writable.getWriter();
    this.sseClients.add(writer);

    const encoder = new TextEncoder();
    writer.write(encoder.encode(": connected\n\n")).catch(() => {});

    const cleanup = () => {
      this.sseClients.delete(writer);
      writer.close().catch(() => {});
    };
    this.state.waitUntil?.(
      new Promise<void>((resolve) => {
        // Best-effort: connection cleanup happens on next write failure.
        setTimeout(resolve, 0);
      }),
    );

    return new Response(readable, {
      headers: {
        "content-type": "text/event-stream",
        "cache-control": "no-cache, no-transform",
        "x-accel-buffering": "no",
      },
    });
  }

  private broadcast(ev: ActivityEvent) {
    const encoder = new TextEncoder();
    const payload = encoder.encode(`data: ${JSON.stringify(ev)}\n\n`);
    for (const w of this.sseClients) {
      w.write(payload).catch(() => this.sseClients.delete(w));
    }
  }

  // --- Processed dedupe ---

  private async handleProcessedCheck(req: Request): Promise<Response> {
    const { id } = (await req.json()) as { id: string };
    const rec = await this.state.storage.get<ProcessedRecord>(`p:${id}`);
    return Response.json({ processed: !!rec });
  }

  private async handleProcessedMark(req: Request): Promise<Response> {
    const { id } = (await req.json()) as { id: string };
    await this.state.storage.put<ProcessedRecord>(`p:${id}`, { ts: Date.now() });
    await this.state.storage.setAlarm(Date.now() + 60 * 60 * 1000);
    return new Response("ok");
  }

  async alarm() {
    const cutoff = Date.now() - PROCESSED_TTL_MS;
    const all = await this.state.storage.list<ProcessedRecord>({ prefix: "p:" });
    const toDelete: string[] = [];
    for (const [k, v] of all) if (v.ts < cutoff) toDelete.push(k);
    if (toDelete.length) await this.state.storage.delete(toDelete);
  }

  // --- Gmail OAuth token cache ---

  private async handleGmailToken(_req: Request): Promise<Response> {
    const cached = await this.state.storage.get<OAuthCache>("gmail-oauth");
    if (cached && cached.expiresAt > Date.now() + 30_000) {
      return Response.json({ accessToken: cached.accessToken });
    }
    return Response.json({ accessToken: null });
  }

  private async handleGmailTokenSet(req: Request): Promise<Response> {
    const cache = (await req.json()) as OAuthCache;
    await this.state.storage.put("gmail-oauth", cache);
    return new Response("ok");
  }
}
