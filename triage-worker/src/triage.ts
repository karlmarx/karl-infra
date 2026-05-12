import Anthropic from "@anthropic-ai/sdk";
import type { Env } from "./env";
import type { GmailMessage, TokenUsage } from "./types";
import { TOOLS, runTool } from "./tools";
import {
  chargeBudget,
  estimateCostUsd,
  logActivity,
  preflight,
} from "./guardrails";

const SYSTEM_PROMPT = `You are an email triage agent for Karl.

You are triaging ONE email at a time. Your job:
1. Decide a tier: urgent | normal | low | bug | spam.
2. Apply a Gmail label "triaged/<tier>" using gmail_apply_label.
3. If the email requires Karl's action, create a Todoist task. Include a one-line summary and link back to the email thread in the description.
4. If the email is a bug report or code-related, create a GitHub issue in addition to (or instead of) Todoist.
5. If a personal reply is warranted, create a draft reply (do NOT send it).
6. Call finish_triage exactly once at the end with a 1-sentence summary and the tier.

Be decisive. Use a maximum of 4 tool calls before finish_triage. Do not call gmail_apply_label more than once.
If the email is clearly spam or a notification with no action needed, just label and finish — no task, no draft.`;

const MAX_ITERATIONS = 6;

export async function triageEmail(env: Env, msg: GmailMessage): Promise<void> {
  const pre = await preflight(env);
  if (!pre.ok) {
    await logActivity(env, {
      kind: "budget.exceeded",
      emailId: msg.id,
      from: msg.from,
      subject: msg.subject,
      message: pre.reason,
    });
    return;
  }

  await logActivity(env, {
    kind: "triage.start",
    emailId: msg.id,
    from: msg.from,
    subject: msg.subject,
  });

  const anthropic = new Anthropic({ apiKey: env.ANTHROPIC_API_KEY });
  const maxTokens = parseInt(env.MAX_TOKENS_PER_TRIAGE, 10);

  const emailBlock = formatEmail(msg);
  const messages: Anthropic.MessageParam[] = [
    {
      role: "user",
      content: [
        {
          type: "text",
          text: emailBlock,
        },
      ],
    },
  ];

  let totalUsage: TokenUsage = { input_tokens: 0, output_tokens: 0 };
  let finished = false;

  for (let iter = 0; iter < MAX_ITERATIONS; iter++) {
    const resp = await anthropic.messages.create({
      model: env.TRIAGE_MODEL,
      max_tokens: 1024,
      system: [
        {
          type: "text",
          text: SYSTEM_PROMPT,
          cache_control: { type: "ephemeral" },
        },
      ],
      tools: TOOLS.map((t, i) =>
        i === TOOLS.length - 1
          ? { ...t, cache_control: { type: "ephemeral" } }
          : t,
      ) as Anthropic.Tool[],
      messages,
    });

    accumulateUsage(totalUsage, resp.usage);

    if (totalUsage.input_tokens + totalUsage.output_tokens > maxTokens) {
      await logActivity(env, {
        kind: "limit.exceeded",
        emailId: msg.id,
        message: `per-triage token limit hit (${maxTokens})`,
        usage: totalUsage,
      });
      break;
    }

    messages.push({ role: "assistant", content: resp.content });

    const toolUses = resp.content.filter(
      (b): b is Anthropic.ToolUseBlock => b.type === "tool_use",
    );

    if (toolUses.length === 0 || resp.stop_reason === "end_turn") {
      finished = true;
      break;
    }

    const toolResults: Anthropic.ToolResultBlockParam[] = [];
    for (const tu of toolUses) {
      const out = await runTool(
        env,
        tu.name,
        tu.input as Record<string, unknown>,
      );
      await logActivity(env, {
        kind: "triage.tool",
        emailId: msg.id,
        toolName: tu.name,
        toolInput: tu.input,
        toolResult: out,
      });
      toolResults.push({
        type: "tool_result",
        tool_use_id: tu.id,
        content: JSON.stringify(out),
        is_error: !out.ok,
      });
      if (tu.name === "finish_triage") {
        finished = true;
      }
    }
    messages.push({ role: "user", content: toolResults });
    if (finished) break;
  }

  const costUsd = estimateCostUsd(totalUsage);
  const after = await chargeBudget(env, costUsd);

  await logActivity(env, {
    kind: "triage.done",
    emailId: msg.id,
    from: msg.from,
    subject: msg.subject,
    usage: totalUsage,
    costUsd,
    message: finished
      ? `done; daily spend now $${after.spentUsd.toFixed(4)} (${after.triageCount}/${env.MAX_TRIAGES_PER_DAY})`
      : `stopped without finish_triage`,
  });
}

function formatEmail(m: GmailMessage): string {
  const body = m.body.length > 4000 ? m.body.slice(0, 4000) + "\n…[truncated]" : m.body;
  return [
    `Email to triage:`,
    `From: ${m.from}`,
    `To: ${m.to}`,
    `Subject: ${m.subject}`,
    `Date: ${new Date(m.date).toISOString()}`,
    `Message-Id: ${m.id}`,
    `Thread-Id: ${m.threadId}`,
    ``,
    `--- BODY ---`,
    body || m.snippet,
    `--- END BODY ---`,
  ].join("\n");
}

function accumulateUsage(acc: TokenUsage, u: Anthropic.Usage) {
  acc.input_tokens += u.input_tokens ?? 0;
  acc.output_tokens += u.output_tokens ?? 0;
  acc.cache_creation_input_tokens =
    (acc.cache_creation_input_tokens ?? 0) + (u.cache_creation_input_tokens ?? 0);
  acc.cache_read_input_tokens =
    (acc.cache_read_input_tokens ?? 0) + (u.cache_read_input_tokens ?? 0);
}
