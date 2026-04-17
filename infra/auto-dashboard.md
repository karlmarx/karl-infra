# Auto Dashboard (auto.93.fyi)

## Purpose

Interactive infrastructure map of Karl's personal automations. Single source of truth for what's running where, what talks to what, and on what schedule. Lives alongside the other diagram docs but renders as an explorable graph rather than static markdown.

## Components

- **`auto-dashboard/`** — Vite + React 19 + TypeScript SPA, uses `@xyflow/react` for the node/edge canvas and Tailwind 4 for styling.
- **`auto-dashboard/src/data/automations.ts`** — Declarative graph: 6 deployment-group boxes, 28 automation nodes, 27 edges. Edit this file to add or remove systems.
- **`auto-dashboard/vercel.json`** — Vite framework preset + SPA rewrite so deep links resolve to `index.html`.

## Deploy Path

```
~/karl-infra/auto-dashboard (repo subdirectory)
  |
  |  git push origin main
  v
GitHub (karlmarx/karl-infra)
  |
  |  Vercel auto-deploy (main branch, subdirectory root)
  v
Vercel Project: auto-dashboard
  |
  |  Custom domain
  v
auto.93.fyi (CNAME -> cname.vercel-dns.com, Cloudflare-managed)
```

## Editing the Graph

The entire map is data-driven. To add a new automation:

1. Append a new entry to the `nodes` array in `src/data/automations.ts` with a unique id, category, group, label, position, and optional details.
2. Add any edges in the `edges` array referencing the new node id.
3. Dev loop: `npm run dev` and check the canvas.
4. Commit + push; Vercel auto-deploys.

## Categories

- `vercel` (blue) — apps on Vercel
- `local` (green) — Mac Studio launchd agents / scripts
- `seedbox` (orange) — Ultra.cc hosted services
- `gha` (purple) — GitHub Actions workflows
- `infra` (gray) — registrar, DNS, git host, managed services
- `windows` (cyan) — Windows workstation services (legacy / secondary)
- `self` (pink) — the dashboard itself (self-referential node)

## Cross-refs

- Renders the same systems documented in `~/karl-infra/services/` and diagrammed ASCII-style in `~/karl-infra/diagrams/`.
- The DNS assignment joins the list in `diagrams/domains.md` under 93.fyi subdomains.
