# go.93.fyi — Foolproof, Multilingual "How to Get to My Apartment"

**Date:** 2026-05-30
**Status:** Design — awaiting Karl's review
**Owner:** Karl

## Goal

A **foolproof**, step-by-step guide anyone can use to get to Karl's apartment —
**3000 NE 6th Ave, Apt 501, Oakland Park, FL 33334** (5th floor) — covering
both the **drive in** and the **walk to the door**. People reliably get
confused today (wrong building, wrong entrance), so the bar is *idiot-proof*,
not just pretty. Fully public, shareable by link, and **multilingual** so an
international guest sees their own language automatically.

## Constraints & decisions (locked with Karl)

| Decision | Value |
|---|---|
| Subdomain | **go.93.fyi** |
| Visibility | **Fully public** (Cloudflare Access bypass, like `where.93.fyi`) |
| Format | **Guided step-by-step** (scrollytelling), mobile-first |
| Languages | EN base + **es, pt, fr, de, he, ko, zh-Hant, ht** (9 total) |
| Hero entry method | **ButterflyMX intercom call to unit 501** (never expires) |
| Live door pass | Optional, set by emailing a ButterflyMX Visitor Pass to `go@93.fyi` |
| Parking | "Park anywhere" (no guest-parking restriction) |
| Hosting | **Single Cloudflare Worker** (serves SPA + `/api/pass` + email ingest + KV) |

### Known pain points (these drive the design)
1. **Wrong entrance** — people use the door **behind Sprouts** instead of the
   **3000 front entrance**. This warning is front-and-center, every language.
2. **Wrong building** — "East Park Square" is several near-identical pastel
   mid-rises. A "THIS building, not those" step disambiguates.
3. General confusion → big visuals, minimal words, numbered steps, and a
   persistent **Call/Text Karl** fallback.

## Architecture

One Cloudflare Worker project (mirrors the proven `where.93.fyi` shape):

```
                    ┌─────────────────────── Cloudflare Worker: go-93fyi ──────────────────────┐
 visitor ──GET / ──▶│ static assets: multilingual step-by-step SPA (Vite build)               │
 visitor ──GET ─────▶│ /api/pass         → read current door pass from KV (public)             │
                     │ email() handler   → ingest ButterflyMX pass sent to go@93.fyi           │
 ButterflyMX ──mail─▶│   (Cloudflare Email Routing → this Worker)                              │
                     │   parse link+validity → KV put → optional forward copy to Gmail         │
                     └──────────────────────── KV: go-93fyi-pass (key: current) ───────────────┘
```

- **No Vercel.** The write-from-email requirement makes the all-Cloudflare
  pattern the right fit; everything lives in one repo / one deploy / KV is free.
- **Repo:** new private GitHub repo `karlmarx/go-93fyi` (sibling of
  `where-93fyi`). Durable artifact is the pushed repo (lesson from where.93.fyi).

### Components

1. **Frontend SPA** — Vite + React + TypeScript, built to static assets served
   by the Worker.
   - `App` → language bootstrap (auto-detect + switcher) → `<Guide>`.
   - **Mode toggle:** 🚗 Driving / 🚶 On foot. Each renders an ordered list of
     `<StepCard>`s.
   - **`<StepCard>`:** number + short instruction + media (looping muted clip or
     photo) + optional ⚠️ inline warning.
   - **`<DestinationCard>`** (top): address, "📍 Open in Maps" deep link
     (`https://maps.google.com/?q=3000+NE+6th+Ave+Apt+501+Oakland+Park+FL+33334`;
     Apple Maps variant for iOS UA).
   - **`<EntrySection>`:** intercom-call instructions (hero) + live door-pass
     (when set) + Call/Text fallback.
   - **`<HelpBar>`:** sticky bottom "Still lost? 📞 Call / 💬 Text Karl".

2. **Content model** — one typed `routes.ts` (step order, which media, which i18n
   keys) + per-locale JSON catalogs (`locales/en.json` … `ht.json`). Adding a
   step once creates a slot in all 9 languages. Proper nouns ("3000", "Apt 501",
   "NE 6th Ave", "Sprouts", "ButterflyMX") are **not** translated.

3. **Media pipeline** — transcode source clips to web-optimized **muted,
   autoplay, loop, playsinline H.264 720p** (~2–6 MB) + poster JPGs, committed in
   repo. HEVC drive clip → H.264 for universal playback. Script:
   `scripts/transcode.sh` (ffmpeg), source-of-truth list in repo.

4. **Door-pass backend (in the Worker)** — *email format reverse-engineered from
   a real pass on 2026-05-30 (see "ButterflyMX email format" below).*
   - **KV schema** `current`:
     `{ qrImageUrl, walletPassUrl?, startsAt, endsAt, receivedAt }`.
   - **`GET /api/pass`** → returns current pass if present and now is within
     `startsAt`…`endsAt`; else `{ active:false }`. SPA loads it on mount.
   - **`email()` handler** → on mail to `go@93.fyi`:
     1. Verify `from` is `access@butterflymx.com` (else ignore).
     2. Parse the MIME (`postal-mime`); extract:
        - QR image: `https://s3…/qr_keys/qr_code_images/…\.png`
        - Wallet pass: `https://s3…/wallet_pass/…pass\.pkpass…`
        - Validity: text `Starts: <date>` / `Ends: <date>`
          (e.g. `May 30, 2026 6:24pm`) → parse to timestamps.
     3. `KV.put('current', …)`; optionally `message.forward(Gmail)` for a copy.
   - **Expiry:** page hides the pass once `endsAt` passes. No standing pass is
     left up indefinitely (Karl sends short passes per guest).

5. **`go@93.fyi` email routing** — Cloudflare Email Routing rule binds the
   address to this Worker's email handler. Karl saves `go@93.fyi` as a contact
   ("GO / door site") for one-tap recipient entry in ButterflyMX.

## Internationalization

- **Auto-detect** from `navigator.language`; **manual switcher** (globe + flags)
  always visible; choice persisted in `localStorage`.
- **Hebrew** renders `dir="rtl"`; layout uses CSS **logical properties** so one
  attribute flips the page. (Haitian Creole, Korean, Traditional Chinese, etc.
  remain LTR.)
- Karl vets **Spanish** (neutral/formal *usted*, masculine where gendered).
  Languages neither Karl nor the author can fully vet (ko, he, ht, zh-Hant) are
  kept to **short, concrete sentences** (street names + numbers + arrows) to
  minimize mistranslation risk.

## Entry method design (defeats the "expired code" problem)

1. **Hero — call the unit on the ButterflyMX intercom.** At the **3000** door,
   on the screen tap the directory, search **501 / Marx**, press call → Karl gets
   a video call and opens the door. Zero maintenance, never expires. Show a
   photo/clip of the intercom + exact taps.
2. **Live door pass (optional).** When Karl emails a Visitor Pass to `go@93.fyi`,
   the page renders the **real intercom QR image directly** ("Show this at the
   3000 intercom") + an **Add to Apple Wallet** button + a "valid through ___"
   note. Auto-hides when none set or `endsAt` has passed. Karl is encouraged to
   send **short** passes (hours, not a year) since the QR is the live credential
   on a public page.
3. **Fallback — Call/Text Karl** (sticky). For codes: *"Codes rotate — if the one
   you were given doesn't work, use the intercom to call 501 or text Karl."*

## Route content (draft — fill exact clips during build)

**🚗 Driving**
1. Turn in from **NE 6th Ave** (landmark TBD from clip).
2. **THIS building** — East Park Square, the one at **3000** — *not* the
   identical neighbors. *(needs "right building" clip)*
3. **Park anywhere.**
4. Walk to the **3000 front entrance** — ⚠️ **NOT the door behind Sprouts.**

**🚶 On foot (from your car)**
1. To the **3000** front doors *(connector clip TBD)*.
2. ButterflyMX intercom → call **501 / Marx** (or open your door pass).
3. Through the lobby → **elevators**.
4. Elevator to **floor 5** → **Apt 501**. *(elevator→door clip TBD)*

## Assets

| Source | Role | Action |
|---|---|---|
| `~/Documents/PXL_20260522_110601456.mp4` | Driving in (8s, HEVC) | → H.264 720p loop |
| `~/Documents/PXL_20240909_115102034.mp4` | Entrance→lobby→elevator (51s, 200MB) | trim + → H.264 720p, likely split per step |
| `~/Documents/Screenshot_20241004-183427.png` | Annotated map reference | crop/clean, used as map overlay or reference |
| Garage walk | not found (no GPS on interior clips) | slot reserved; Karl supplies later |
| Wishlist clips | turn-in, right-building, wrong-entrance, buzzer, elevator→501, guest parking | optional, slot into existing structure |

## Privacy / security

- **Public page + live pass:** anyone loading the page *while a pass is live*
  could open it. Mitigation: send the pass at arrival time, short validity,
  auto-clear; passes are revocable + photo-logged by ButterflyMX. Accepted.
- **No standing gate code** is ever published.
- **Email handler** verifies the sender is a ButterflyMX domain before storing.
- Showing **Apt 501** publicly is intentional (it's the whole point).

## Deployment

- Cloudflare Worker `go-93fyi` + KV `go-93fyi-pass`; `go.93.fyi` custom domain
  (auto-provisioned by `wrangler deploy`).
- Access bypass app for `go.93.fyi` (exact-host beats the `*.93.fyi` wildcard),
  same as `where.93.fyi`.
- Email Routing rule: `go@93.fyi` → Worker email handler.
- `setup.sh` one-shot (KV + secret + email route + deploy);
  `.github/workflows/deploy-worker.yml` for CI.

## Infra docs to update (standing rule)

- New `infra/go-93fyi.md`; update `ARCHITECTURE.md`, `diagrams/overview.md`,
  `infra/domain-93fyi.md` (DNS + `go@93.fyi` email route).

## Out of scope / future

- **Auto-minting** ButterflyMX passes via their API — requires becoming an
  approved partner (demo video, branding, review); not worth it. Documented as
  someday-maybe only.
- Twilio "text Karl the gate code" automation (phase 2).
- Garage-route steps (pending clip).

## ButterflyMX email format (reverse-engineered 2026-05-30)

From a real Visitor Pass Karl sent to `karlmarx9193@gmail.com`:

- **From:** `access@butterflymx.com`
- **Subject:** `New Visitor Pass from Karl Marx`
- **Body contains** (direct S3 URLs, *not* behind the tracking redirect):
  - QR PNG: `https://s3.dualstack.us-east-1.amazonaws.com/bmx-rails-production/system/qr_keys/qr_code_images/041/670/820/medium/qr_code_20260530-1-g2tkwl.png`
  - Wallet: `https://s3…/bmx-rails-production/uploads/wallet_pass/41670820/…/pass.pkpass…`
  - Validity text: `Starts: May 30, 2026 6:24pm` / `Ends: May 30, 2027 7:21pm`
  - (Plus `tracking.butterflymx.com/ls/click?…` wrapped CTA links — ignored.)
- The QR PNG is the credential the intercom scans → render it directly.

## Open items for Karl

1. ✅ **Email parser** — format known (above).
2. **Extra clips** from the wishlist — whenever easy (esp. right-building +
   wrong-entrance).
3. **Spanish** review once drafted.
