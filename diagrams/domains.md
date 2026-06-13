# DNS & Domain Map

## 93.fyi

**Registrar:** Dynadot
**DNS Provider:** Cloudflare (free tier)

```
93.fyi (Cloudflare nameservers)
|
+-- A/CNAME Records
|   |
|   +-- 93.fyi          CNAME -> cname.vercel-dns.com  (nwb-plan, temporary)
|   +-- nfit.93.fyi     CNAME -> cname.vercel-dns.com  (nwb-plan)
|   +-- nyoga.93.fyi    CNAME -> cname.vercel-dns.com  (nwb-yoga)
|   +-- id.93.fyi       CNAME -> cname.vercel-dns.com  (Social Identity Verification)
|   +-- auto.93.fyi     CNAME -> cname.vercel-dns.com  (auto-dashboard)
|   +-- ortho.93.fyi    CNAME -> cname.vercel-dns.com  (orthoappt)
|   +-- pwbpb.93.fyi    CNAME -> cname.vercel-dns.com  (pickleball-drills)
|   +-- contact.93.fyi  CNAME -> cname.vercel-dns.com  (Contact Form)
|   +-- layover.93.fyi  CNAME -> cname.vercel-dns.com  (Flight Connection Confidence)
|   +-- mom.93.fyi      CNAME -> cname.vercel-dns.com  (Mom's Reassurance Hub)
|   +-- suspect.93.fyi  CNAME -> cname.vercel-dns.com  (suspect-game)
|   +-- progress.93.fyi CNAME -> (resolves via wildcard A `*.93.fyi`) (progress-dashboard)
|   +-- command.93.fyi  A     -> 76.76.21.21 (proxied)  (karl-command-center, CF Access gated)
|   +-- workoutgifs.93.fyi CNAME -> cname.vercel-dns.com  (93-fyi, public/DNS-only)
|   +-- go.93.fyi         CNAME -> cname.vercel-dns.com  (go-93fyi, public/DNS-only)
|   +-- scout.93.fyi      CNAME -> cname.vercel-dns.com  (relayhub-scout, demo/preview)
|
| (Many more records exist in the live Cloudflare zone — bedbug, dev.*, fake,
|  ha, house, login, me, now, seed, status, thumbfit/yoga, todo, www, plus
|  wildcards. This file documents only the curated/load-bearing subdomains.
|  Source of truth: Cloudflare zone 8881c2fb46004f18cbf6faf47e562731.)
|
+-- Email Routing (Cloudflare)
    |
    +-- k@93.fyi -> karlmarx9193@gmail.com
```

## Domain Assignments

| Domain | Vercel Project | Repo | Notes |
|--------|---------------|------|-------|
| `93.fyi` (apex) | nwb-plan | karlmarx/nwb-plan | Temporary — may change |
| `nfit.93.fyi` | nwb-plan | karlmarx/nwb-plan | Primary domain for NWB Fitness |
| `nyoga.93.fyi` | nwb-yoga | karlmarx/nwb-yoga | NWB Yoga companion |
| `id.93.fyi` | Social ID Verification | karlmarx/identity-verification | Frontend for Social Identity Verification |
| (public domain) | Social ID Verification | karlmarx/identity-verification | Primary domain (WIP) |
| `auto.93.fyi` | auto-dashboard | karlmarx/karl-infra (subdir: `auto-dashboard/`) | Interactive automation map |
| `ortho.93.fyi` | orthoappt | karlmarx/karl-infra (subdir: `orthoappt/`) | Appointment companion (Dr. Almodovar follow-up, NWB protocol) |
| `pwbpb.93.fyi` | pickleball-drills | karlmarx/pickleball-drills | Stationary pickleball drills for the partial-weight-bearing phase |
| `contact.93.fyi` | (Contact Form) | (private repo) | Public contact form, Turnstile + Resend, rate-limited |
| `layover.93.fyi` | (Flight Connection Confidence) | (private repo) | Connection success calculator for elderly travelers |
| `mom.93.fyi` | (Mom's Reassurance Hub) | (private repo) | Letter-style answers to Mom's worries |
| `suspect.93.fyi` | suspect-game | karlmarx/suspect-game | Multiplayer word bluffing game for happy hours. Realtime via PartyKit (`suspect-game.karlmarx.partykit.dev`). |
| `progress.93.fyi` | progress-dashboard | karlmarx/progress-dashboard | Milestone tracker, NextAuth + CF Access |
| `command.93.fyi` | karl-command-center | karlmarx/karl-command-center | Daily-driver hub, **Cloudflare Access gated**. Hosts `/status` PWA route (installable on mobile) |
| `workoutgifs.93.fyi` | 93-fyi | karlmarx/93-fyi | Workout GIFs gallery. **Public (DNS-only)** as of 2026-05-24 — was unrouted (fell through to parking wildcard); CF Access app for it is now inert. |
| `go.93.fyi` | go-93fyi | karlmarx/go-93fyi | Foolproof step-by-step directions to home (3000 NE 6th Ave Apt 501). **Public (DNS-only)**, shipped 2026-05-30 (v0: direction A annotated stills). See `infra/go-93fyi.md`. |

## Email

| Address | Destination | Provider |
|---------|-------------|----------|
| `k@93.fyi` | `karlmarx9193@gmail.com` | Cloudflare Email Routing |

## SSL/TLS

All domains use Cloudflare's Universal SSL (free) with Full (Strict) mode pointing to Vercel's automatic SSL certificates.

## Other Domains

| Domain | Registrar | Use |
|--------|-----------|-----|
| `blazingpaddles.org` | (TBD) | Blazing Paddles pickleball club website |
