export interface Env {
  // Bindings
  STATE: DurableObjectNamespace;

  // Secrets
  ANTHROPIC_API_KEY: string;
  GOOGLE_CLIENT_ID: string;
  GOOGLE_CLIENT_SECRET: string;
  GOOGLE_REFRESH_TOKEN: string;
  TODOIST_TOKEN: string;
  GITHUB_TOKEN: string;
  MCP_SHARED_SECRET: string;

  // Vars
  SENDER_ALLOWLIST: string;
  DAILY_BUDGET_USD: string;
  MAX_TRIAGES_PER_DAY: string;
  MAX_TOKENS_PER_TRIAGE: string;
  DEFAULT_GH_REPO: string;
  TRIAGE_MODEL: string;
}
