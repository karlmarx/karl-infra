import type { Env } from "./env";
import { TOOLS, runTool } from "./tools";

interface JsonRpcReq {
  jsonrpc: "2.0";
  id?: string | number | null;
  method: string;
  params?: Record<string, unknown>;
}

function rpcResult(id: JsonRpcReq["id"], result: unknown) {
  return { jsonrpc: "2.0" as const, id: id ?? null, result };
}

function rpcError(id: JsonRpcReq["id"], code: number, message: string) {
  return { jsonrpc: "2.0" as const, id: id ?? null, error: { code, message } };
}

export async function handleMcp(req: Request, env: Env): Promise<Response> {
  const auth = req.headers.get("authorization") ?? "";
  const token = auth.replace(/^Bearer\s+/i, "");
  if (!token || token !== env.MCP_SHARED_SECRET) {
    return new Response("unauthorized", { status: 401 });
  }
  if (req.method !== "POST") {
    return new Response("method not allowed", { status: 405 });
  }
  let body: JsonRpcReq;
  try {
    body = (await req.json()) as JsonRpcReq;
  } catch {
    return Response.json(rpcError(null, -32700, "parse error"), { status: 400 });
  }

  switch (body.method) {
    case "initialize":
      return Response.json(
        rpcResult(body.id, {
          protocolVersion: "2024-11-05",
          capabilities: { tools: {} },
          serverInfo: { name: "karl-triage-gateway", version: "0.1.0" },
        }),
      );
    case "tools/list":
      return Response.json(
        rpcResult(body.id, {
          tools: TOOLS.map((t) => ({
            name: t.name,
            description: t.description,
            inputSchema: t.input_schema,
          })),
        }),
      );
    case "tools/call": {
      const { name, arguments: args } =
        (body.params as { name: string; arguments: Record<string, unknown> }) ?? {};
      const out = await runTool(env, name, args ?? {});
      return Response.json(
        rpcResult(body.id, {
          content: [{ type: "text", text: JSON.stringify(out) }],
          isError: !out.ok,
        }),
      );
    }
    case "ping":
      return Response.json(rpcResult(body.id, {}));
  }
  return Response.json(rpcError(body.id, -32601, `method not found: ${body.method}`));
}
