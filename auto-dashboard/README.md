# auto-dashboard

Interactive map of Karl's personal infrastructure automations. Renders a
node/edge graph of every cron job, launchd agent, GitHub Action, Vercel app,
and supporting service across the Mac Studio, the Ultra.cc seedbox, the
Windows 11 workstation, and the shared infra layer.

Deployed at **https://auto.93.fyi**.

## Stack

- Vite + React 19 + TypeScript
- `@xyflow/react` for the interactive graph
- Tailwind CSS 4 (`@tailwindcss/vite` plugin)
- Static SPA — no backend

## Local dev

```sh
npm install
npm run dev      # http://localhost:5173
npm run build    # → dist/
```

## Editing the graph

All nodes, edges, groups, and category colors live in
[`src/data/automations.ts`](src/data/automations.ts). Edit that file to add,
remove, or rewire anything on the diagram — the rest of the app is purely
presentational and will rerender automatically.

Node positions are hand-laid rather than auto-layout so the grouping stays
readable. When adding a new node, pick a position that sits inside the
intended group's bounding box (group boxes are declared at the top of
`automations.ts`).

## Deploy

`vercel.json` pins the build to Vite with SPA rewrites. Vercel auto-deploys
from `main` once the domain is wired.
