import type { Env } from "./env";
import { TriageStateDO } from "./state";
import { activityStream, getActivity, getBudget, logActivity } from "./guardrails";
import { pollAndTriage } from "./poll";
import { handleMcp } from "./mcp";
import { runChat } from "./chat";

export { TriageStateDO };

const CORS = {
  "access-control-allow-origin": "*",
  "access-control-allow-headers": "authorization,content-type",
  "access-control-allow-methods": "GET,POST,OPTIONS",
};

export default {
  async fetch(req: Request, env: Env, ctx: ExecutionContext): Promise<Response> {
    if (req.method === "OPTIONS") return new Response(null, { headers: CORS });

    const url = new URL(req.url);
    const r = (res: Response) => addCors(res);

    try {
      switch (url.pathname) {
        case "/":
          return r(Response.json({ ok: true, name: "triage-worker", version: "0.1.0" }));
        case "/budget":
          return r(Response.json(await getBudget(env)));
        case "/activity":
          return r(
            Response.json(
              await getActivity(
                env,
                parseInt(url.searchParams.get("limit") ?? "100", 10),
              ),
            ),
          );
        case "/activity/stream":
          return addCors(await activityStream(env));
        case "/trigger": {
          if (!isAuthed(req, env)) return r(new Response("unauthorized", { status: 401 }));
          ctx.waitUntil(pollAndTriage(env));
          return r(Response.json({ triggered: true }));
        }
        case "/mcp":
          return r(await handleMcp(req, env));
        case "/chat": {
          if (!isAuthed(req, env)) return r(new Response("unauthorized", { status: 401 }));
          if (req.method !== "POST")
            return r(new Response("method not allowed", { status: 405 }));
          const body = (await req.json()) as { messages: unknown };
          if (!Array.isArray(body.messages))
            return r(new Response("messages required", { status: 400 }));
          const out = await runChat(env, { messages: body.messages as never });
          return r(Response.json(out));
        }
      }
    } catch (e) {
      await logActivity(env, {
        kind: "triage.error",
        message: `fetch handler: ${e instanceof Error ? e.message : String(e)}`,
      }).catch(() => {});
      return r(
        new Response(`error: ${e instanceof Error ? e.message : String(e)}`, {
          status: 500,
        }),
      );
    }
    return r(new Response("not found", { status: 404 }));
  },

  async scheduled(_event: ScheduledEvent, env: Env, ctx: ExecutionContext): Promise<void> {
    ctx.waitUntil(
      pollAndTriage(env).catch(async (e) => {
        await logActivity(env, {
          kind: "triage.error",
          message: `scheduled: ${e instanceof Error ? e.message : String(e)}`,
        });
      }),
    );
  },
};

function isAuthed(req: Request, env: Env): boolean {
  const auth = req.headers.get("authorization") ?? "";
  return auth.replace(/^Bearer\s+/i, "") === env.MCP_SHARED_SECRET;
}

function addCors(res: Response): Response {
  const h = new Headers(res.headers);
  for (const [k, v] of Object.entries(CORS)) h.set(k, v);
  return new Response(res.body, { status: res.status, headers: h });
}
