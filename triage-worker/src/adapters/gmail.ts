import type { Env } from "../env";
import type { GmailMessage } from "../types";

const GMAIL_BASE = "https://gmail.googleapis.com/gmail/v1/users/me";

async function getAccessToken(env: Env): Promise<string> {
  const doStub = env.STATE.get(env.STATE.idFromName("singleton"));
  const cached = await (
    await doStub.fetch("https://do/gmail-token")
  ).json<{ accessToken: string | null }>();
  if (cached.accessToken) return cached.accessToken;

  const res = await fetch("https://oauth2.googleapis.com/token", {
    method: "POST",
    headers: { "content-type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams({
      client_id: env.GOOGLE_CLIENT_ID,
      client_secret: env.GOOGLE_CLIENT_SECRET,
      refresh_token: env.GOOGLE_REFRESH_TOKEN,
      grant_type: "refresh_token",
    }),
  });
  if (!res.ok) {
    throw new Error(`gmail token refresh failed: ${res.status} ${await res.text()}`);
  }
  const data = (await res.json()) as { access_token: string; expires_in: number };
  await doStub.fetch("https://do/gmail-token/set", {
    method: "POST",
    body: JSON.stringify({
      accessToken: data.access_token,
      expiresAt: Date.now() + data.expires_in * 1000,
    }),
  });
  return data.access_token;
}

async function gfetch(env: Env, path: string, init?: RequestInit): Promise<Response> {
  const token = await getAccessToken(env);
  return fetch(`${GMAIL_BASE}${path}`, {
    ...init,
    headers: {
      ...(init?.headers ?? {}),
      authorization: `Bearer ${token}`,
    },
  });
}

export async function listRecentInbox(
  env: Env,
  senderAllowlist: string[],
  maxResults = 10,
): Promise<{ id: string; threadId: string }[]> {
  const fromQuery = senderAllowlist.map((s) => `from:${s}`).join(" OR ");
  const q = `(${fromQuery}) -label:triaged newer_than:1d`;
  const url = `/messages?maxResults=${maxResults}&q=${encodeURIComponent(q)}`;
  const res = await gfetch(env, url);
  if (!res.ok) throw new Error(`gmail list failed: ${res.status} ${await res.text()}`);
  const data = (await res.json()) as { messages?: { id: string; threadId: string }[] };
  return data.messages ?? [];
}

export async function getMessage(env: Env, id: string): Promise<GmailMessage> {
  const res = await gfetch(env, `/messages/${id}?format=full`);
  if (!res.ok) throw new Error(`gmail get failed: ${res.status} ${await res.text()}`);
  const m = (await res.json()) as {
    id: string;
    threadId: string;
    snippet: string;
    internalDate: string;
    payload: GmailPayload;
  };
  const headers = headerMap(m.payload.headers ?? []);
  return {
    id: m.id,
    threadId: m.threadId,
    from: headers["from"] ?? "",
    to: headers["to"] ?? "",
    subject: headers["subject"] ?? "(no subject)",
    snippet: m.snippet ?? "",
    body: extractBody(m.payload),
    date: parseInt(m.internalDate, 10),
  };
}

interface GmailPayload {
  mimeType?: string;
  headers?: { name: string; value: string }[];
  body?: { data?: string; size?: number };
  parts?: GmailPayload[];
}

function headerMap(hs: { name: string; value: string }[]): Record<string, string> {
  const o: Record<string, string> = {};
  for (const h of hs) o[h.name.toLowerCase()] = h.value;
  return o;
}

function decodeBase64Url(s: string): string {
  const b64 = s.replace(/-/g, "+").replace(/_/g, "/");
  return atob(b64);
}

function extractBody(payload: GmailPayload): string {
  if (payload.mimeType === "text/plain" && payload.body?.data) {
    return decodeBase64Url(payload.body.data);
  }
  if (payload.parts) {
    for (const p of payload.parts) {
      if (p.mimeType === "text/plain" && p.body?.data) {
        return decodeBase64Url(p.body.data);
      }
    }
    for (const p of payload.parts) {
      const nested = extractBody(p);
      if (nested) return nested;
    }
  }
  return "";
}

export async function ensureLabel(env: Env, name: string): Promise<string> {
  const res = await gfetch(env, "/labels");
  if (!res.ok) throw new Error(`labels list failed: ${res.status}`);
  const data = (await res.json()) as { labels?: { id: string; name: string }[] };
  const found = data.labels?.find((l) => l.name === name);
  if (found) return found.id;
  const create = await gfetch(env, "/labels", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({
      name,
      labelListVisibility: "labelShow",
      messageListVisibility: "show",
    }),
  });
  if (!create.ok) throw new Error(`label create failed: ${create.status}`);
  return ((await create.json()) as { id: string }).id;
}

export async function applyLabel(env: Env, messageId: string, name: string): Promise<void> {
  const labelId = await ensureLabel(env, name);
  const res = await gfetch(env, `/messages/${messageId}/modify`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ addLabelIds: [labelId] }),
  });
  if (!res.ok) throw new Error(`label apply failed: ${res.status} ${await res.text()}`);
}

export async function createDraftReply(
  env: Env,
  msg: GmailMessage,
  bodyText: string,
): Promise<string> {
  const mime = [
    `To: ${msg.from}`,
    `Subject: Re: ${msg.subject}`,
    `In-Reply-To: ${msg.id}`,
    `References: ${msg.id}`,
    `Content-Type: text/plain; charset=utf-8`,
    ``,
    bodyText,
  ].join("\r\n");
  const raw = btoa(unescape(encodeURIComponent(mime)))
    .replace(/\+/g, "-")
    .replace(/\//g, "_")
    .replace(/=+$/, "");
  const res = await gfetch(env, "/drafts", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ message: { raw, threadId: msg.threadId } }),
  });
  if (!res.ok) throw new Error(`draft create failed: ${res.status} ${await res.text()}`);
  return ((await res.json()) as { id: string }).id;
}
