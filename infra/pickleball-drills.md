# pickleball-drills (pwbpb.93.fyi)

Stationary pickleball drills for the partial-weight-bearing phase of Karl's NWB protocol. Six kitchen-line drills designed around the same movement constraints as `orthoappt`: left foot back, right foot forward, weight shifts only onto the right, hip flexion under 90°, no lateral coverage, no chasing.

## Status

**Live.** Single-file static HTML, animated SVG court diagrams, no build step, no dependencies, no JS framework.

## Layout

```
pickleball-drills/
└── index.html          # six drill cards + safety rules + animated SVGs
```

That's the whole site.

## Deploy path

```
karlmarx/pickleball-drills (GitHub, private)
        |
        v  (Vercel auto-deploy on push to main)
Vercel project: pickleball-drills (team karlmarxs-projects)
        |
        v  (CNAME pwbpb -> cname.vercel-dns.com, proxied:false)
Cloudflare DNS (zone 93.fyi)
        |
        v
https://pwbpb.93.fyi
```

## Why standalone repo (not a karl-infra subdir)

Unlike `auto-dashboard` and `orthoappt` (which live inside karl-infra and share its Vercel surface), `pickleball-drills` has zero overlap with the rest of the infra map: no shared components, no shared data, no build pipeline. Standalone repo keeps the deploy fast (~7s, no monorepo to traverse) and makes the karl-infra docs commit cleanly separable from the app code.

## Cross-refs

- `infra/orthoappt.md` — same protocol context (Dr. Almodovar follow-up, NWB phase)
- `diagrams/domains.md` — pwbpb CNAME entry
