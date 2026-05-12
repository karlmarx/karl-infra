import Anthropic from "@anthropic-ai/sdk";
import type { Env } from "./env";
import type { TokenUsage } from "./types";
import { TOOLS, runTool } from "./tools";
import { chargeBudget, estimateCostUsd, preflight } from "./guardrails";

const SYSTEM = `You are Karl's command-center assistant. You have tools that touch his Gmail, Todoist, and GitHub.

Be precise. Only call a tool when the user has clearly asked for the action.
Never send anything externally without explicit confirmation in the conversation.
gmail_draft_reply creates DRAFTS — that is safe.
For destructive or sending actions, ask first.`;

const MAX_ITERATIONS = 8;

export interface ChatRequest {
  messages: Anthropic.MessageParam[];
}

export interface ChatResponse {
  reply: string;
  toolTrace: Array<{
    name: string;
    input: unknown;
    result: unknown;
    ok: boolean;
  }>;
  usage: TokenUsage;
  costUsd: number;
  stopped?: string;
}

export async function runChat(env: Env, req: ChatRequest): Promise<ChatResponse> {
  const pre = await preflight(env);
  if (!pre.ok) {
    return {
      reply: `(blocked) ${pre.reason}. Daily spend $${pre.budget.spentUsd.toFixed(4)}.`,
      toolTrace: [],
      usage: { input_tokens: 0, output_tokens: 0 },
      costUsd: 0,
      stopped: pre.reason,
    };
  }

  const anthropic = new Anthropic({ apiKey: env.ANTHROPIC_API_KEY });
  const messages = [...req.messages];
  const trace: ChatResponse["toolTrace"] = [];
  const usage: TokenUsage = { input_tokens: 0, output_tokens: 0 };
  let reply = "";

  for (let i = 0; i < MAX_ITERATIONS; i++) {
    const resp = await anthropic.messages.create({
      model: env.TRIAGE_MODEL,
      max_tokens: 1024,
      system: [{ type: "text", text: SYSTEM, cache_control: { type: "ephemeral" } }],
      tools: TOOLS.map((t, idx) =>
        idx === TOOLS.length - 1 ? { ...t, cache_control: { type: "ephemeral" } } : t,
      ) as Anthropic.Tool[],
      messages,
    });

    usage.input_tokens += resp.usage.input_tokens ?? 0;
    usage.output_tokens += resp.usage.output_tokens ?? 0;
    usage.cache_creation_input_tokens =
      (usage.cache_creation_input_tokens ?? 0) +
      (resp.usage.cache_creation_input_tokens ?? 0);
    usage.cache_read_input_tokens =
      (usage.cache_read_input_tokens ?? 0) + (resp.usage.cache_read_input_tokens ?? 0);

    const text = resp.content
      .filter((b): b is Anthropic.TextBlock => b.type === "text")
      .map((b) => b.text)
      .join("\n");
    if (text) reply = text;

    messages.push({ role: "assistant", content: resp.content });

    const toolUses = resp.content.filter(
      (b): b is Anthropic.ToolUseBlock => b.type === "tool_use",
    );
    if (toolUses.length === 0 || resp.stop_reason === "end_turn") break;

    const results: Anthropic.ToolResultBlockParam[] = [];
    for (const tu of toolUses) {
      const out = await runTool(env, tu.name, tu.input as Record<string, unknown>);
      trace.push({ name: tu.name, input: tu.input, result: out.result ?? out.error, ok: out.ok });
      results.push({
        type: "tool_result",
        tool_use_id: tu.id,
        content: JSON.stringify(out),
        is_error: !out.ok,
      });
    }
    messages.push({ role: "user", content: results });
  }

  const costUsd = estimateCostUsd(usage);
  await chargeBudget(env, costUsd);

  return { reply, toolTrace: trace, usage, costUsd };
}
