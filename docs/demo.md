# Boss Demo Plan — Email Triage Agent

**Goal:** show that an MCP-based agent can do real work on real data, end-to-end,
with hard guardrails — and that the pattern transfers directly to the work POC.

**Runtime:** 15-18 min. Live demo, no slides except the architecture sketch.

**Companion runbook:** `services/email-triage/README.md` (system internals).

---

## Pre-flight checklist (do these BEFORE walking in)

- [ ] Mac runner is running on launchd. Confirm: `launchctl list | grep triage`
      shows a non-zero status code.
- [ ] `tail -f ~/Library/Logs/triage.log` open in a Terminal pane (visible to
      you, not the projector).
- [ ] `/triage` dashboard open in browser, full-screen on the projector.
- [ ] Gmail open in another tab so you can flip to Drafts + Labels.
- [ ] Phone vibration tested on silent. The SMS is the showstopper; if you don't
      notice it, the moment falls flat.
- [ ] 5 demo emails staged in Gmail compose, addressed to yourself, ready to
      send one click at a time. See "Email scripts" below.
- [ ] Daily budget reset for visual impact:
      ```sql
      update triage_budget
         set spent_usd = 0, triage_count = 0
       where date = current_date;
      ```
- [ ] Vercel env vars set on karl-command-center production (`SUPABASE_URL`,
      `SUPABASE_SERVICE_ROLE_KEY`) — otherwise `/triage` will throw.
- [ ] Boss's calendar confirmed for 20 min, not 15.

---

## Act 1 — The Why (2 min, no live demo yet)

Open your actual Gmail inbox on the projector.

> "I get ~50 emails a day. Maybe 5 actually need me. The rest are receipts,
> marketing, and stuff I should reply to in two sentences but don't for three
> days. I built a triage agent that runs locally, watches my inbox, and does
> the obvious work — and importantly, it uses the same MCP pattern we're
> discussing for the work POC."

Frame the **pattern**, not just the product:

- Agent runs somewhere (Mac in my case, a Worker for work).
- Talks to external services through MCP servers (Gmail MCP here;
  Jira / Confluence / SVN at work).
- Has hard budget + scope guardrails (or it eats your money).
- Activity streams to a dashboard so you can audit what it did.

---

## Act 2 — Architecture in 90 seconds

Pull up `services/email-triage/README.md` — the ASCII diagram is the only
visual you need.

Three boxes:

1. **Mac (launchd, every 60s)** — Python runner. Spawns the local Gmail MCP
   server over stdio. Runs a Claude Opus 4.7 agent loop with 8 tools.
2. **Tool layer** — 6 action tools (label, draft, Todoist task, GH issue,
   SMS, finish) + 2 diagnostic tools (recent merges, user activity). All
   parameterized + gated.
3. **Supabase** — every event, every cost, every dedup-id. Powers the
   dashboard. Nothing the agent does is invisible.

Key callouts:

- **Drafts only.** No `gmail_send` tool exists in the codebase. Architectural,
  not a config flag.
- **Sender allowlist** is a hard filter *before* the agent sees the email.
  Two addresses. Anything else: $0, skipped, logged.
- **$1/day cap** via an atomic Postgres RPC. If a runaway loop hits the cap,
  the runner becomes read-only until UTC midnight.

---

## Act 3 — Live demo, escalating complexity (10 min)

### Demo 1 — Routine receipt → label only (~$0.005)

**Send:** Subject `Receipt: Spotify Premium $11.99`, body is a fake receipt.

Watch `/triage`:
- `triage.start` → `triage.tool: gmail_apply_label(triaged/low)` → `triage.done`

In Gmail, show the `triaged/low` label on the email.

> "Cheapest path. No follow-up needed. Half a cent."

### Demo 2 — Personal note → draft created (~$0.01)

**Send:** Subject `lunch next week?`, friendly 1-paragraph body.

Dashboard sequence:
- Label → `gmail_draft_reply` → finish.

Open Gmail → Drafts. The draft is there. Read it aloud.

> "Agent decided this needed a personal reply, drafted one, and stopped. I'll
> review before hitting send. It *can't* send — that tool doesn't exist."

### Demo 3 — Bug report → GitHub issue auto-filed (~$0.02)

**Send:** Subject `foodr bug — meal log won't save on Safari`, body has
reproduction steps.

Dashboard:
- Label → `github_create_issue` (target: `karlmarx/foodr`) → finish.

Click the issue URL in the dashboard. Issue body has the repro steps from
the email, formatted.

> "Zero clicks from me. Lives in the right repo. Karl-the-developer can pick
> it up tomorrow without ever opening Karl-the-emailer's inbox."

### Demo 4 — THE SHOWSTOPPER (~$0.05)

**Send:** Subject `URGENT: prod nfit.93.fyi returning 500s`, body says
something broke after the latest deploy.

Talk over the dashboard while it runs:

1. **`github_recent_merges({repo: "karlmarx/nwb-plan", hours: 24})`** ← *pause*
   > "Watch this. It hasn't filed anything yet. It's asking GitHub what shipped
   > recently."
2. `gmail_apply_label("triaged/urgent")`
3. **`github_create_issue`** — open it. Show the body:
   > "Recent merges that may be related: PR #X (title), merged Yh ago."
4. **`twilio_send_urgent_sms`** — your phone buzzes. Show the SMS on the
   projector (AirPlay) or hold it up:
   > "URGENT: nfit 500s. PR #X merged Yh ago is suspect. <url>"
5. `finish_triage` — tier `urgent`, cost ~$0.05.

> "The agent connected the deploy to the breakage on its own. Not because I
> told it which PR — because the prompt says 'when something breaks, check
> what shipped first' and the recent-merges tool exists. That's MCP working."

### Demo 5 — Guardrail check ($0.00)

**Send:** From a non-allowlisted account (work account, old Gmail, anything),
to your monitored address. Subject doesn't matter.

Dashboard:
- `poll.skip` event, kind `allowlist`. Zero cost added.

> "Sender allowlist is a hard filter. Costs me nothing. Spam farms can't
> bankrupt me."

---

## Act 4 — Tie to the work POC (2 min)

Refresh `/triage`. Point at the budget bar (~$0.09 of $1.00 used after 4
triages).

> "Same shape as the work POC, just different MCPs wired in."

| Personal POC | Work POC |
|---|---|
| Gmail MCP | Outlook / Confluence / Jira MCPs |
| GitHub create_issue | SVN / git create_changeset |
| Todoist | Internal ticket system |
| Twilio SMS | PagerDuty |
| Supabase audit log | Internal observability |
| $1/day cap | Whatever spending limit makes sense |

The Opus 4.7 agent loop + tool dispatcher + guardrails transfer directly.
The lift to wire up the work MCPs is the work of days, not weeks.

---

## Anticipated questions

| Question | One-line answer |
|---|---|
| What if it hallucinates and files a bad issue? | Drafts only for emails. Issues are recoverable (close + delete). Allowlist + budget limit blast radius. |
| Why MCP specifically, not plain function calling? | Same servers work in Claude Desktop, this agent, and any future client. Avoids re-implementing Gmail / Jira / etc. per agent. |
| What stops it from sending an email? | The `gmail_send` tool isn't registered. Architectural, not config. Adding it would require a code change + PR review. |
| Prompt injection in email bodies? | Real risk. Mitigations: tool calls return structured data the agent must reason over, not free-form HTML rendering. Sender allowlist means injection only works from one of two accounts. For the work version we'd add a content scanner before the agent ever sees a message. |
| Cost at scale? | $0.04 per triage on Opus 4.7. At 50 triages/day = $2/day. Sonnet 4.6 is ~5x cheaper at near-identical quality on bounded tasks like this. |
| Can I see the code? | `github.com/karlmarx/karl-infra/tree/main/services/email-triage` — happy to walk through any file. |

---

## Email scripts (paste these into Gmail compose)

All From: your allowlisted Gmail unless noted. All To: yourself.

### Email 1 — Spotify receipt
```
Subject: Receipt: Spotify Premium $11.99

Thank you for your payment.

Plan: Spotify Premium
Amount: $11.99 USD
Date: <today>
Card ending in: ••••4242

Your next payment will be on <today + 30d>.
```

### Email 2 — Lunch ask
```
Subject: lunch next week?

Hey — back in town next Thursday/Friday. Free for lunch either day?
Was thinking Tacombi or that new ramen place on 4th. Let me know.
```

### Email 3 — Bug report
```
Subject: foodr bug — meal log won't save on Safari

Found a bug in foodr. When I tap "Save" on a new meal entry in Safari
(iOS 17), nothing happens. Works fine in Chrome. Console shows "Cannot
read properties of undefined (reading 'id')" coming from MealForm.tsx
line ~120. Not urgent but would be good to fix before the next demo.
```

### Email 4 — Urgent prod
```
Subject: URGENT: prod nfit.93.fyi returning 500s

Hey - I just tried to open the workout planner and the page is returning
a 500 on every route. Looks like something broke after the latest deploy.
Can you take a look? Lots of users hitting it right now.
```

### Email 5 — Non-allowlisted (send from another account)
```
Subject: Hi from outside the allowlist

You don't know me. This email tests that triage skips anything not from
Karl's allowlist.
```

---

## What NOT to do

- Don't show Python code on the projector. Boss doesn't want to read code;
  the dashboard tells the story better.
- Don't promise the work version is "the same thing." It's the same *shape*.
  The different MCPs are the actual work.
- Don't demo on caffeine. The Opus loop takes ~5s per turn. Slow down. Use
  the pauses to narrate what the agent is "thinking."
- Don't open Demo 4 cold — always do Demos 1-3 first so the boss sees the
  baseline before the showstopper.

---

## Post-demo retrospective (fill in after)

- [ ] Boss reaction:
- [ ] Questions you couldn't answer:
- [ ] Work POC next steps agreed:
- [ ] Total demo cost (from `/triage` budget bar):
