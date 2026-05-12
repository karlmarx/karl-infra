import type Anthropic from "@anthropic-ai/sdk";
import type { Env } from "./env";
import * as gmail from "./adapters/gmail";
import * as todoist from "./adapters/todoist";
import * as github from "./adapters/github";

export const TOOLS: Anthropic.Tool[] = [
  {
    name: "gmail_apply_label",
    description:
      "Add a Gmail label to a specific message. Use 'triaged' plus a tier like 'triaged/urgent', 'triaged/normal', 'triaged/low', 'triaged/bug', 'triaged/spam'.",
    input_schema: {
      type: "object",
      properties: {
        message_id: { type: "string", description: "Gmail message id." },
        label: { type: "string", description: "Label name to apply." },
      },
      required: ["message_id", "label"],
    },
  },
  {
    name: "gmail_draft_reply",
    description:
      "Create a DRAFT reply to a message. Does not send. Use when the email warrants a personal response.",
    input_schema: {
      type: "object",
      properties: {
        message_id: { type: "string" },
        body: { type: "string", description: "Plain-text reply body." },
      },
      required: ["message_id", "body"],
    },
  },
  {
    name: "todoist_create_task",
    description:
      "Create a Todoist task. Use for emails that require follow-up action by Karl.",
    input_schema: {
      type: "object",
      properties: {
        content: { type: "string", description: "Short task title." },
        description: {
          type: "string",
          description: "Optional longer body (include email snippet + link).",
        },
        priority: {
          type: "integer",
          enum: [1, 2, 3, 4],
          description: "1=lowest, 4=highest urgency.",
        },
        due_string: {
          type: "string",
          description: "Natural language due (e.g. 'tomorrow 9am'). Optional.",
        },
      },
      required: ["content"],
    },
  },
  {
    name: "github_create_issue",
    description:
      "Create a GitHub issue. Use only for emails that are clearly bug reports or code-related requests.",
    input_schema: {
      type: "object",
      properties: {
        repo: {
          type: "string",
          description: "owner/repo. Defaults to env DEFAULT_GH_REPO if omitted.",
        },
        title: { type: "string" },
        body: { type: "string" },
        labels: { type: "array", items: { type: "string" } },
      },
      required: ["title", "body"],
    },
  },
  {
    name: "finish_triage",
    description:
      "Call this exactly once when you are done. Provide a short human summary of the triage decision.",
    input_schema: {
      type: "object",
      properties: {
        summary: { type: "string" },
        tier: {
          type: "string",
          enum: ["urgent", "normal", "low", "bug", "spam"],
        },
      },
      required: ["summary", "tier"],
    },
  },
];

export interface ToolResult {
  ok: boolean;
  result?: unknown;
  error?: string;
}

export async function runTool(
  env: Env,
  name: string,
  input: Record<string, unknown>,
): Promise<ToolResult> {
  try {
    switch (name) {
      case "gmail_apply_label": {
        await gmail.applyLabel(env, input.message_id as string, input.label as string);
        return { ok: true, result: { labeled: true } };
      }
      case "gmail_draft_reply": {
        const msg = await gmail.getMessage(env, input.message_id as string);
        const id = await gmail.createDraftReply(env, msg, input.body as string);
        return { ok: true, result: { draft_id: id } };
      }
      case "todoist_create_task": {
        const t = await todoist.createTask(env, {
          content: input.content as string,
          description: input.description as string | undefined,
          priority: input.priority as 1 | 2 | 3 | 4 | undefined,
          dueString: input.due_string as string | undefined,
        });
        return { ok: true, result: t };
      }
      case "github_create_issue": {
        const i = await github.createIssue(env, {
          repo: input.repo as string | undefined,
          title: input.title as string,
          body: input.body as string,
          labels: input.labels as string[] | undefined,
        });
        return { ok: true, result: i };
      }
      case "finish_triage": {
        return { ok: true, result: { summary: input.summary, tier: input.tier } };
      }
    }
    return { ok: false, error: `unknown tool: ${name}` };
  } catch (e) {
    return { ok: false, error: e instanceof Error ? e.message : String(e) };
  }
}
