export interface ActivityEvent {
  id: string;
  ts: number;
  kind:
    | "poll.start"
    | "poll.skip"
    | "poll.match"
    | "triage.start"
    | "triage.tool"
    | "triage.done"
    | "triage.error"
    | "budget.exceeded"
    | "limit.exceeded";
  emailId?: string;
  from?: string;
  subject?: string;
  toolName?: string;
  toolInput?: unknown;
  toolResult?: unknown;
  message?: string;
  usage?: TokenUsage;
  costUsd?: number;
}

export interface TokenUsage {
  input_tokens: number;
  output_tokens: number;
  cache_creation_input_tokens?: number;
  cache_read_input_tokens?: number;
}

export interface BudgetState {
  date: string; // YYYY-MM-DD UTC
  spentUsd: number;
  triageCount: number;
}

export interface GmailMessage {
  id: string;
  threadId: string;
  from: string;
  to: string;
  subject: string;
  snippet: string;
  body: string;
  date: number; // ms epoch
}
