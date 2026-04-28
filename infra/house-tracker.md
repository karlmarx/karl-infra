# house-tracker

South Florida real-estate property comparison dashboard — side-by-side analysis of candidate properties (price history, reno cost, comps, flood zone, walk/bike/transit) with Gemini-generated concept renders for kitchens and pools.

## Purpose

Karl is shopping for a home in greater Fort Lauderdale. This is the working file for shortlisted properties: structured data per house (price, sqft, taxes, flood risk, comps, reno line items, after-reno value), photo galleries, AI-generated "what could this look like?" renders for big renovations, and a side-by-side compare view. Source-of-truth for offers, negotiation notes, and verdicts (`strong-buy` / `consider` / `pass`).

## Stack

| Layer | Tech |
|-------|------|
| Build | Vite 8 |
| UI | React 19 + react-router-dom 7 |
| Styling | Tailwind 4 (`@tailwindcss/vite`) |
| Icons | lucide-react |
| Routing | client-side (BrowserRouter) — `vercel.json` rewrites all paths to `index.html` |
| Hosting | Vercel (no custom domain wired yet) |
| Renders | Gemini-generated images, committed under `public/photos/<id>/{kitchen,pool}-concepts/` |

No backend. All property data is a static JS export.

## How it runs

```bash
cd ~/house-tracker
npm install
npm run dev      # vite dev server
npm run build    # production build → dist/
npm run preview  # serve build locally
npm run lint     # eslint
```

Vercel auto-deploys from `main` (typical `karlmarx/*` SPA wiring). No custom domain assigned at the time of writing — accessed at the project's `*.vercel.app` URL.

## Data flow

```
src/data/properties.js  ──── (static JS export, hand-curated per property)
  │  { id, address, askingPrice, priceHistory[], beds, sqft, taxes,
  │    floodZone, renoItems[], afterRenoValue, comps, ... }
  ▼
src/pages/Dashboard.jsx        → list of <PropertyCard>
src/pages/PropertyDetail.jsx   → /property/:id — full record + <PhotoGallery> + <SitePlan{id}>
src/pages/Compare.jsx          → /compare — side-by-side
  │
  ▼
public/photos/<property-id>/
  ├── 01..NN-*.jpg               (listing photos, downloaded)
  ├── kitchen-concepts/          (Gemini renders, committed)
  └── pool-concepts/             (Gemini renders, committed)
```

Routing (`src/main.jsx`):

| Path | Page |
|------|------|
| `/` | Dashboard (grid of properties) |
| `/property/:id` | PropertyDetail |
| `/compare` | Compare |

`AppContext` holds dark mode state. Per-property site plans (`SitePlan3497`, `SitePlan1741`) are bespoke React components keyed by id in a `sitePlanComponents` map — adding a new property with a custom site plan means adding a new component and registering it.

## Current properties

Two tracked at the time of writing:

| ID | Address | Status | Verdict |
|----|---------|--------|---------|
| `3497-ne-20th-ave` | 3497 NE 20th Avenue, Oakland Park | active | strong-buy (offer $500–525K) |
| `1741-ne-40th-st` | 1741 NE 40th St, Fort Lauderdale | (see data file) | (see data file) |

Both have full photo galleries and Gemini-generated kitchen + pool concept renders.

## Status

**Active personal use.** Last meaningful change: `2026-04-06` (`359141e feat: add kitchen renovation concept renders for 3497 NE 20th Ave`). Five commits, clean trajectory: scaffold → site plans → Gemini pool renders → mobile fixes → kitchen renders. README is still the default Vite scaffold; the real "what is this" lives in `src/data/properties.js` and the page components.

## Open questions / known issues

- README is the unmodified Vite template. The repo's actual purpose is undocumented in-tree.
- `App.jsx` is a one-liner stub (`export default function App() { return null; }`); the real root render lives in `src/main.jsx`. Not a bug, just unusual — a future refactor would move the routes into `App.jsx`.
- No subdomain. If it gets one, follow the `shipping-93fyi-app` skill (Cloudflare CNAME + Vercel project linking) and add it to `auto-dashboard`.
- Photos and Gemini renders are committed to git, which inflates repo size. Acceptable for now; revisit if it crosses ~500 MB.
- Adding a third property requires (a) a new entry in `properties.js`, (b) photo dir under `public/photos/`, (c) a bespoke `SitePlan{id}.jsx` if the property warrants one, (d) registration in `PropertyDetail.jsx`'s `sitePlanComponents` map.

## Cross-references

- [vercel.md](vercel.md) — deployment target
- [auto-dashboard.md](auto-dashboard.md) — should get a `house-tracker` Vercel node once it has a public domain
- [../ARCHITECTURE.md](../ARCHITECTURE.md)
