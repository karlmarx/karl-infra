import type { Env } from "./env";
import { listRecentInbox, getMessage } from "./adapters/gmail";
import {
  isProcessed,
  logActivity,
  markProcessed,
  preflight,
  senderAllowed,
} from "./guardrails";
import { triageEmail } from "./triage";

export async function pollAndTriage(env: Env): Promise<{
  scanned: number;
  triaged: number;
  skipped: number;
}> {
  const allowlist = env.SENDER_ALLOWLIST.split(",").map((s) => s.trim());
  const stats = { scanned: 0, triaged: 0, skipped: 0 };

  const pre = await preflight(env);
  if (!pre.ok) {
    await logActivity(env, {
      kind: "budget.exceeded",
      message: `poll skipped: ${pre.reason}`,
    });
    return stats;
  }

  await logActivity(env, { kind: "poll.start" });

  const refs = await listRecentInbox(env, allowlist, 10);
  stats.scanned = refs.length;

  for (const ref of refs) {
    if (await isProcessed(env, ref.id)) {
      stats.skipped += 1;
      continue;
    }
    const msg = await getMessage(env, ref.id);
    if (!senderAllowed(env, msg.from)) {
      await logActivity(env, {
        kind: "poll.skip",
        emailId: msg.id,
        from: msg.from,
        subject: msg.subject,
        message: "sender not in allowlist",
      });
      await markProcessed(env, ref.id);
      stats.skipped += 1;
      continue;
    }
    await logActivity(env, {
      kind: "poll.match",
      emailId: msg.id,
      from: msg.from,
      subject: msg.subject,
    });
    try {
      await triageEmail(env, msg);
      stats.triaged += 1;
    } catch (e) {
      await logActivity(env, {
        kind: "triage.error",
        emailId: msg.id,
        message: e instanceof Error ? e.message : String(e),
      });
    }
    await markProcessed(env, ref.id);

    const after = await preflight(env);
    if (!after.ok) {
      await logActivity(env, {
        kind: "budget.exceeded",
        message: `stopping batch: ${after.reason}`,
      });
      break;
    }
  }

  return stats;
}
