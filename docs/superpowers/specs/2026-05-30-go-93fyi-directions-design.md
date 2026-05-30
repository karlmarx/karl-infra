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

3. **Media pipeline** — each step uses either a **short clip** (the relevant
   ~3–6s, trimmed from a longer source — e.g. the 51s walk is split per step) or
   a **still photo** where one frame suffices. Clips are
   **`<video autoplay loop muted playsinline>` H.264 720p** (~0.4–1.5 MB each) +
   poster JPGs — the "GIF look" (silent, looping, inline) **without GIF's** size
   or blockiness. **No animated GIFs.** HEVC drive clip → H.264 for universal
   playback. Script: `scripts/transcode.sh` (ffmpeg), source-of-truth list in
   repo. Mobile-first: one-handed vertical scroll, large tap targets, phone-width
   column centered on desktop.

4. **Door-pass backend (in the Worker)** — *email format reverse-engineered from
   a real pass on 2026-05-30 (see "ButterflyMX email format" below).*
   - **KV** — `current` (the pass): `{ qrImageUrl, walletPassUrl?, code?,
     startsAt, endsAt, receivedAt }`; `access-log` — append one entry per
     request (`req:<ts>:<rand>` → `{ ip, country, ua, ts }`).
   - **`GET /api/pass/status`** → `{ active, endsAt }` only (no code/QR). Lets
     the page decide whether to show the **Request entry pass** button.
   - **`POST /api/request-pass`** → logs requester IP (`CF-Connecting-IP` +
     `request.cf.country`, UA, ts) to `access-log`, then returns the **code, QR,
     Wallet, entry steps** for the active pass. This is the only endpoint that
     exposes the credential, and only after the visitor accepts terms.
   - **`email()` handler** → on mail to `go@93.fyi`:
     1. Verify `from` is `access@butterflymx.com` (else ignore).
     2. Parse the MIME (`postal-mime`); extract:
        - QR image: `https://s3…/qr_keys/qr_code_images/…\.png`
        - Wallet pass: `https://s3…/wallet_pass/…pass\.pkpass…`
        - Numeric **code** *if the email includes one* (some passes do, some
          don't — page falls back to QR/directory when absent).
        - Validity: text `Starts: <date>` / `Ends: <date>`
          (e.g. `May 30, 2026 6:24pm`) → parse to timestamps.
     3. `KV.put('current', …)`; optionally `message.forward(Gmail)` for a copy.
   - **Validity:** Karl keeps a ~1-year pass; page shows it until `endsAt`. The
     directory-call path is the fallback when the pass is flaky or revoked.

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

## The two ButterflyMX boxes

There are **two** ButterflyMX intercom boxes; the two routes use different ones:

- **🚗 Driving box** — at the vehicle entrance/gate, reached by car. Used in the
  driving route to open the gate.
- **🚶 Clubhouse box** — the pedestrian intercom at the clubhouse entrance. Used
  on foot.

The page makes crystal-clear **which box you're at** before giving entry steps,
because the steps differ. How to physically reach each box is shown per route.

> **Confirmed (2026-05-30):** the **clubhouse *is* the 3000 building lobby** (the
> one with the big communal table that leads to the elevator). The entrance
> everyone wrongly uses is the **separate door behind Sprouts**. The two boxes
> are physically separate hardware (vehicle gate vs. clubhouse walk-up).

## Entry method design

At whichever box, three tiers in order:

1. **Enter the pass code — exact steps.** If the guest's Visitor Pass includes a
   numeric **code**, the page shows it and **exactly how to key it in on that
   box** (captured from a clip/photo), in the visitor's language.
2. **Scan / show the QR** + **Add to Apple Wallet**.
3. **Find Karl in the directory (never fails).** If no code was provided, or the
   code doesn't work: on the box, open the directory, search **501 / Marx**,
   press call → Karl gets a video call and opens it. This is the universal
   no-fail path and is emphasized as such.

Plus the sticky **Call/Text Karl** bar for anything else.

### The shared pass + the Request gate

Karl keeps **one long-lived (≈1-year) Visitor Pass** emailed to `go@93.fyi`. The
page does **not** display the code/QR openly. Instead:

- A **"Request entry pass"** button. Tapping it shows **terms** (you're an invited
  guest; access is logged; don't share) that the visitor must accept.
- On accept, the SPA calls `POST /api/request-pass`, which **logs the visitor's
  IP** (+ timestamp, country, user-agent) to a KV access log, then returns the
  pass. Only then are the **code + QR + Wallet + exact entry steps** revealed.
- This gives Karl an accountability trail and a deterrent/friction layer while
  keeping the pass self-serve. It's a deterrent, **not** a hard lock — see
  Privacy. The directory-call path always works if the pass is revoked or flaky.

## Route content (draft — fill exact clips during build)

**🚗 Driving**
1. Turn in from **NE 6th Ave** (landmark TBD from clip).
2. At the **vehicle gate**, use the **🚗 driving box** — key in the pass code, or
   find **501 / Marx** in the directory and call → gate opens.
3. **THIS building** — East Park Square, the one at **3000** — *not* the
   identical neighbors. *(needs "right building" clip)*
4. **Park anywhere.**
5. ⚠️ Go to the **clubhouse / 3000 entrance** — **NOT the door behind Sprouts.**

**🚶 On foot (from your car to the door)**
1. To the **clubhouse entrance** *(connector clip TBD)*.
2. At the **🚶 clubhouse box**: key in the pass code, or find **501 / Marx** in
   the directory and call → Karl buzzes you in.
3. Inside: **walk forward past the big communal table, then take a right** to a
   **door with a (green) push-to-exit button** — press it.
   *(clip: Karl shooting 2026-05-31)*
4. Through that door → the **elevator** → **floor 5** → **Apt 501**.
   *(elevator→501 clip TBD)*

## Assets

| Source | Role | Action |
|---|---|---|
| `~/Documents/PXL_20260522_110601456.mp4` | Driving in (8s, HEVC) | → H.264 720p loop |
| `~/Documents/PXL_20240909_115102034.mp4` | Entrance→lobby→elevator (51s, 200MB) | trim + → H.264 720p, likely split per step |
| `~/Documents/Screenshot_20241004-183427.png` | Annotated map reference | crop/clean, used as map overlay or reference |
| Garage walk | not found (no GPS on interior clips) | slot reserved; Karl supplies later |
| **Clubhouse interior** (in → past big table → right → push-to-exit door → elevator) | **Karl shooting 2026-05-31** | high-value foot-route clip |
| Both intercom **boxes** (driving gate box; clubhouse box) + code-entry keypad | needed for exact entry steps | clip/photo each |
| Wishlist clips | turn-in, right-building, wrong-entrance, elevator→501 | optional, slot into existing structure |

## Privacy / security

- **Long-lived pass on a public page** is Karl's explicit choice. Mitigations:
  the credential is **never shown openly** — it's behind a **Request entry pass**
  button that displays **terms** and **logs the requester's IP** (+ country, UA,
  timestamp) before revealing the code/QR. This is a deterrent + accountability
  trail, **not** a hard lock: anyone who accepts terms can get the pass. Karl
  accepts this; the pass is revocable in ButterflyMX and entries are
  photo-logged, and the directory-call path stands behind it.
- **Email handler** verifies the sender is `access@butterflymx.com` before
  storing — so a spoofed email can't plant a bogus pass (note: sender spoofing is
  still possible without DMARC checks; Worker should also honor SPF/DMARC pass
  flags from the inbound message if available).
- Showing **Apt 501** publicly is intentional (it's the whole point).
- Access-log retention: keep it small (recent requests only); it's for Karl's
  visibility, not long-term storage.

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
