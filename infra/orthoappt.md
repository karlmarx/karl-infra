# orthoappt — Appointment companion

**Domain:** [ortho.93.fyi](https://ortho.93.fyi)
**Repo:** `karlmarx/karl-infra` (subdir: `orthoappt/`)
**Vercel project:** `orthoappt`
**Status:** Live (deployed for the Dr. Almodovar follow-up on Tuesday April 28, 2026)

## Purpose

Phone-first companion for the orthopedic follow-up appointment for Karl's left
femoral neck stress fracture and left hip labral tear (with right-side FAI).
The site renders the prepared question list as an interactive checklist Karl
can use *during the appointment*: track which questions have been asked,
capture the doctor's answers, flag follow-ups, and export the result as a
PDF afterwards.

The single source of truth is `content/appointment-questions.md`, which is
parsed at build time into structured sections + questions + checklist items.
The runtime UI is purely a renderer over that structured data plus
localStorage state.

## Components

| Piece | Path | Notes |
|-------|------|-------|
| Source content | `content/appointment-questions.md` | Owned by Karl. Edit here, push, redeploy. |
| Build-time parser | `lib/parseMarkdown.ts` | `unified` + `remark-parse`. Detects 3 question patterns + checklist sections. Server-only (uses `node:fs`). |
| Type contract | `lib/types.ts` | Shared between server parser and client UI. Keeps client bundle from pulling parser code. |
| Storage shell | `lib/storage.tsx` | React context over localStorage. Two keys: `orthoappt:questions:v1`, `orthoappt:checklist:v1`. Debounced writes (150ms). |
| Main view | `app/page.tsx` + `components/HomeView.tsx` | RSC parses MD, hands structured doc to client `<HomeView>`. Sticky header w/ progress + search + ★-only filter. |
| Doctor handoff | `app/doctor/page.tsx` | Pure server-rendered, no JS, ★ items pulled to top, print-friendly. |
| Post-appt export | `app/export/page.tsx` + `components/ExportView.tsx` | Reads localStorage, renders for print/PDF. |
| Service worker | `public/sw.js` | App-shell + offline. Cache-first for `/_next/static/*`, network-first for HTML. Pre-caches `/`, `/doctor`, `/export`, `/manifest.json`. |
| PWA manifest | `public/manifest.json` | Standalone display, sky-600 theme. |

## Data flow

```
content/appointment-questions.md
    │
    ▼  (build-time, server only)
lib/parseMarkdown.ts → ParsedDoc
    │
    ▼  (passed as RSC props)
app/page.tsx ──▶ <HomeView>  (client)
                    │
                    ├─▶ <SectionNav>      (TOC; bottom-sheet on mobile)
                    ├─▶ <ProgressBar>     (subscribes to localStorage)
                    ├─▶ <SearchBar>       (substring filter)
                    ├─▶ <PriorityToggle>  (★-only)
                    ├─▶ <QuestionCard> × N
                    │       └─▶ checkbox / textarea / follow-up flag
                    │             └─▶ localStorage (debounced)
                    ├─▶ <ChecklistItemCard> × M
                    └─▶ <SettingsDrawer>  (reset all)

                                 ▲
                                 │  on mount, hydrates from localStorage
                                 │
                          [ orthoappt:questions:v1 ]
                          [ orthoappt:checklist:v1 ]
```

`/doctor` and `/export` use the same `ParsedDoc` but render different shells:

```
app/doctor/page.tsx → static HTML, ★ pulled to top, no controls (handoff print)
app/export/page.tsx → reads localStorage, formats with answers (post-appt PDF)
```

## Build / deploy

Standard Next.js on Vercel. Auto-deploys from `main` whenever
`karl-infra/orthoappt/**` changes (Vercel rebuilds the project from
`rootDirectory: "orthoappt"`). Service worker is a static asset and ships
unchanged.

```
local:    cd ~/karl-infra/orthoappt && npm run build
prod:     git push origin main   →   Vercel rebuild   →   ortho.93.fyi
```

## Cross-references

- DNS record + domain assignment: `~/karl-infra/diagrams/domains.md`
- Vercel project row: `~/karl-infra/ARCHITECTURE.md` (Deployment Targets)
- Sibling 93.fyi apps in this repo: `auto-dashboard/` (auto.93.fyi)
- Independent 93.fyi apps in their own repos: `nwb-plan` (nfit.93.fyi),
  `nwb-yoga` (nyoga.93.fyi), `identity-verification` (id.93.fyi),
  `command-center` (command.93.fyi)

## Notes for future-me

- The parser handles three bold-question patterns. If new patterns appear in
  the source MD, add a case in `extractQuestion()` in `lib/parseMarkdown.ts`
  and re-run `npx tsx tools/inspect.ts` to verify.
- localStorage keys are versioned (`:v1`). Bump if the schema changes —
  losing user state is preferable to a partial corrupted read.
- Bundle size: First Load JS is ~190 KB gzipped due to Next.js 16 + React 19
  framework cost. The static HTML is fully readable without JS (~23 KB gz),
  so the read-only experience is fast even on bad cell signal.
- Appointment date is hard-coded in `lib/format.ts` as `APPOINTMENT_DATE`.
  Future appointments: update the constant or generalize via
  frontmatter in the source MD.
