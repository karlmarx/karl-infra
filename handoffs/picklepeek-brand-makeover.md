# Handoff: PicklePeek brand makeover + About / How to use / Contact

Paste everything below the line into a fresh Claude Code session that has
`karlmarx/where-93fyi` and `karlmarx/karl-infra` attached.

---

You're giving the pickleball court-traffic site a brand makeover. Its new name and
domain are **PicklePeek** at **https://picklepeek.com**. The old address,
https://p.93.fyi, stays live. Karl owns it. He has ADHD: keep replies short, with a
clear summary and an explicit "your next steps" list.

## Where things are
- Repo `karlmarx/where-93fyi`, folder `courts/`. Read `courts/README.md` first.
  It's a Cloudflare Worker `p-93fyi` with one SQLite Durable Object (`CourtsStore`).
  Server-rendered HTML lives in `src/page.js` (board, terms, admin) and
  `src/pages-web.js` (report `/r/<park>`, printable signs `/sign/<park>`, `/try`, `/tops`).
  Routes are in `src/app.js`. Browser code and the one theme are in
  `public/app/` (`style.css`, `common.js`, `board.js`, `report.js`).
  The PWA manifest is `MANIFEST` in `src/app.js`. Translations (en, es, pt) live in
  `src/i18n.js` and the `L` tables inside each `public/app/*.js`.
- Deploys run from `.github/workflows/deploy-courts.yml` on push to `main`
  (it runs `npm test` first). Work on your designated branch and open a draft PR.
  Never push to `main`.
- Docs are in `karlmarx/karl-infra`: `infra/p-93fyi.md` and the README Live Services table.
  Read its CLAUDE.md.

## What it is (use this for the About copy)
PicklePeek shows how busy the public pickleball courts at **Hagen Park** and
**Wimberly Fields** are right now, so people can decide whether to go. Players
report what they see. Nobody has to install anything. You can report by:
- texting or calling **(888) 601-6132**
- emailing **p@93.fyi**
- tapping the QR code on the court sign (`/r/<park>`)
- the web page

Every number is self-reported and shows how old it is. Verified and trusted reports
beat anonymous ones. Nobody's phone number or email is ever stored or shown:
reporter ids are one-way hashes. It also shows weather and wet courts, the
4-on-4-off and challenge lines at Hagen, and wait estimates. Karl runs it as a
free community project.

## The job
1. **Brand.** Name **PicklePeek**, with a short tagline along the lines of "See how busy
   the courts are before you go". Create a simple logo or wordmark (inline SVG),
   a favicon, an `icon.svg` and PWA icons, plus an OG/social share image and meta tags
   (title, description, `og:*`, `twitter:card`). Refresh the palette and type.
   **Keep** what makes it work outdoors and for older eyes: light, high-contrast,
   WCAG AA, rem-based type, 48px+ tap targets, reduced-motion support. Replace
   "p.93.fyi" in user-facing copy (page titles, header, footer, sign pages, email
   sign-in text in `src/web.js`) with PicklePeek / picklepeek.com.
   **Don't** change the SMS reply strings in `src/i18n.js` or the voice prompts
   without asking Karl: SMS length and toll-free verification depend on them.
2. **New pages**, each linked from a footer on every page and from the header menu.
   Each needs en/es/pt, and must be added to the tests and `robots.txt` where relevant:
   - `/about`: the purpose, who it's for, the parks, how the counts work (self-reported,
     age, trust tiers, holds), privacy in plain words, and that it's free and
     community-run.
   - `/how`: how to use it. Checking the board; reporting by text with examples
     (`hagen 8`, `wimberly 6 waiting 2`, `UNDO`, `wet`); by phone; by email; by QR;
     what the court icons mean; tips such as "count the paddles".
   - `/contact`: email p@93.fyi, the phone number, the feedback form (reuse `/try`'s
     feedback API, `/api/feedback`), and a "report a problem with the site" link.
   - Possibly a short FAQ, for example "Is this official? No, it's run by players."
3. **Polish** the home page header and the first-visit welcome card to match the new
   brand. Keep the board's plain-answer layout, which came out of a six-way UX review.
4. Run `npm test` in `courts/` and keep it green. Take Playwright screenshots at phone
   width (375px) of the home page, report, about, how and contact pages, then send them
   to Karl. If a larger visual change is worth comparing, offer two or three directions
   as `/try` versions before committing to one.

## Don'ts
- Don't touch `/twilio/*`, `/api/report`, the email handler, or the Durable Object schema.
- Don't remove `p.93.fyi` from `wrangler.toml` routes.
- Use no paid services. Keep it free tier.
- Never put a secret in code.

## Finish with
Push, open a draft PR, update `infra/p-93fyi.md`, and give Karl a short summary
with his next steps.
