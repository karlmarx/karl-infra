# go.93.fyi — Foolproof Apartment Directions

A **fully public**, mobile-first, step-by-step guide for guests getting to Karl's
home — **3000 NE 6th Ave, Apt 501, Oakland Park, FL 33334** (5th floor). Built to
defeat the recurring confusions (wrong building, wrong entrance, the gate).

| Field | Value |
|-------|-------|
| **Public URL** | https://go.93.fyi |
| **Repo** | [karlmarx/go-93fyi](https://github.com/karlmarx/go-93fyi) (private) |
| **Hosting** | Vercel project `go-93fyi` (static; GitHub auto-deploy on push to `main`) |
| **DNS** | `go.93.fyi` CNAME → `cname.vercel-dns.com`, **proxied:false (DNS-only)** |
| **Public?** | Yes — DNS-only bypasses the `*.93.fyi` Cloudflare Access wildcard |
| **Shipped** | 2026-05-30 (v0) |
| **Design spec** | `docs/superpowers/specs/2026-05-30-go-93fyi-directions-design.md` |

## Status — v0 (shipped 2026-05-30)

Live now: **direction "A" (annotated stills + animated SVG arrows/callouts)** as a
single self-contained `index.html` + `assets/`, with a swipeable **carousel**
(Next/Back + swipe + arrow keys) and a 🚗 Driving / 🚶 On-foot mode toggle.

Placeholder frames are pulled from existing (soft, motion-blurred) video. **Karl is
shooting proper photos/videos 2026-05-31** — reminded via Todoist `karl-todo`
(due 6am) **and** a durable launchd nag `com.kmx.go-photos-reminder`
(`bin/go-photos-reminder.py`, Gmail SMTP like `_emaillib`): pinned to May 31,
hourly 6:07am–8:07pm, fires even with Claude closed, **auto-stops** when ≥2 media
files land in `~/Documents`. Plist (holds the Gmail app password) lives in
`~/Library/LaunchAgents/`, not the repo.

> **UI note (2026-05-30 v0.2):** the first build looked rough; rebuilt as a
> light "transit wayfinding" system — clean editorial hero, single Start→Next
> flow, graceful "preview photo" handling on the soft frames, fixed step
> counter, entry copy anchored to unit **501** (intercom name TBC: Marx vs
> Marx-Levi). Direction confirmed by Karl.

## Roadmap (next passes)

1. **Real photos** + re-placed overlays (replaces the soft v0 frames).
2. **"Am I at the right entrance?" confirmation** — the #1 confusion. Entrances
   differ by mode: **car** = the entrance **inside the gate**; **walking** = the
   **high-numbers** entrance **outside the gate** (NOT the one behind Sprouts).
   Each mode's entrance step shows a reference photo + a "does this match? ✅/❌"
   check.
3. **Multilingual** — EN + es, pt, fr, de, he (RTL), ko, zh-Hant, ht; browser
   auto-detect + switcher.
4. **Live ButterflyMX door pass** — Karl emails a Visitor Pass to **`go@93.fyi`**;
   a Cloudflare Email Worker parses it (QR PNG + Wallet + Starts/Ends from
   `access@butterflymx.com`) into KV; the page surfaces it behind a **"Request
   entry pass"** button that shows terms and **logs the requester's IP** before
   revealing the QR/code. Intercom-call to **501 / Marx** is the no-fail fallback.
   *(This is why the long-term home may migrate from Vercel-static to a Cloudflare
   Worker, à la `where.93.fyi`.)*

## Indoor foot route (as known)

Clubhouse = the **3000 building lobby** (big communal table → elevator). Path:
enter → past the big table → **right** → through the **green push-to-exit door** →
**past the mailboxes → right → left** → elevator → **floor 5 → Apt 501**.

## Two ButterflyMX boxes

Physically separate hardware: a **driving/gate box** (vehicles) and a **clubhouse
walk-up box** (pedestrians). Passes/codes work at the box; the directory call to
**501 / Marx** always works.

## Cross-refs

- Design spec: `docs/superpowers/specs/2026-05-30-go-93fyi-directions-design.md`
- Domain map: `diagrams/domains.md` · Architecture: `ARCHITECTURE.md` (Vercel table)
- Pattern sibling: `infra/where-93fyi.md` (Worker + KV write-from-trigger model)
