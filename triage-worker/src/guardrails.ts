import type { Env } from "./env";
import type { ActivityEvent, BudgetState, TokenUsage } from "./types";

// Prices in USD per 1M tokens (Claude Haiku 4.5).
const HAIKU_PRICES = {
  input: 1.0,
  output: 5.0,
  cache_write: 1.25,
  cache_read: 0.1,
};

export function estimateCostUsd(usage: TokenUsage): number {
  const p = HAIKU_PRICES;
  const inputBase = usage.input_tokens / 1_000_000;
  const output = usage.output_tokens / 1_000_000;
  const cacheWrite = (usage.cache_creation_input_tokens ?? 0) / 1_000_000;
  const cacheRead = (usage.cache_read_input_tokens ?? 0) / 1_000_000;
  return (
    inputBase * p.input +
    output * p.output +
    cacheWrite * p.cache_write +
    cacheRead * p.cache_read
  );
}

function stub(env: Env): DurableObjectStub {
  return env.STATE.get(env.STATE.idFromName("singleton"));
}

export async function getBudget(env: Env): Promise<BudgetState> {
  const res = await stub(env).fetch("https://do/budget");
  return res.json();
}

export async function chargeBudget(
  env: Env,
  costUsd: number,
): Promise<BudgetState> {
  const res = await stub(env).fetch("https://do/budget/charge", {
    method: "POST",
    body: JSON.stringify({ costUsd }),
  });
  return res.json();
}

export async function logActivity(
  env: Env,
  ev: Omit<ActivityEvent, "id" | "ts"> & Partial<Pick<ActivityEvent, "ts">>,
): Promise<void> {
  const full: ActivityEvent = {
    id: crypto.randomUUID(),
    ts: ev.ts ?? Date.now(),
    ...ev,
  } as ActivityEvent;
  await stub(env).fetch("https://do/append", {
    method: "POST",
    body: JSON.stringify(full),
  });
}

export async function getActivity(
  env: Env,
  limit = 100,
): Promise<ActivityEvent[]> {
  const res = await stub(env).fetch(`https://do/activity?limit=${limit}`);
  return res.json();
}

export function activityStream(env: Env): Promise<Response> {
  return stub(env).fetch("https://do/activity/stream");
}

export async function isProcessed(env: Env, id: string): Promise<boolean> {
  const res = await stub(env).fetch("https://do/processed/check", {
    method: "POST",
    body: JSON.stringify({ id }),
  });
  return (await res.json<{ processed: boolean }>()).processed;
}

export async function markProcessed(env: Env, id: string): Promise<void> {
  await stub(env).fetch("https://do/processed/mark", {
    method: "POST",
    body: JSON.stringify({ id }),
  });
}

export interface PreflightResult {
  ok: boolean;
  reason?: string;
  budget: BudgetState;
}

export async function preflight(env: Env): Promise<PreflightResult> {
  const budget = await getBudget(env);
  const cap = parseFloat(env.DAILY_BUDGET_USD);
  const maxCount = parseInt(env.MAX_TRIAGES_PER_DAY, 10);
  if (budget.spentUsd >= cap) {
    return { ok: false, reason: `daily $${cap} cap hit`, budget };
  }
  if (budget.triageCount >= maxCount) {
    return { ok: false, reason: `daily ${maxCount} triage count hit`, budget };
  }
  return { ok: true, budget };
}

export function senderAllowed(env: Env, fromHeader: string): boolean {
  const allow = env.SENDER_ALLOWLIST.split(",").map((s) =>
    s.trim().toLowerCase(),
  );
  const addr = extractAddress(fromHeader).toLowerCase();
  return allow.includes(addr);
}

export function extractAddress(fromHeader: string): string {
  const m = fromHeader.match(/<([^>]+)>/);
  return (m ? m[1] : fromHeader).trim();
}
