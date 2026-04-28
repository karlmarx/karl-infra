# photos.93.fyi (planned)

Future Cloudflare Worker that exposes Karl's local photo catalog (built by `photo-memory`) as a searchable, browsable web UI. Not yet built.

This stub exists so `photo-memory` Phase 4 has a concrete target to point at, and so the auto.93.fyi map has a placeholder node for the eventual deploy.

## Status

**Phase 0 — design only.** No code, no DNS record, no Worker. Reachable via `git log photo-memory` Phase 4 plans only.

## Planned architecture

```
photo-memory (Mac Studio)
  ├── Phase 1: SHA256 dedupe of /Volumes/Crucial X9/google-takeout-2026-04-16/
  ├── Phase 2: MLX-VLM analysis → captions, tags, embeddings
  ├── Phase 3: curation → SQLite catalog + sqlite-vec embeddings
  └── Phase 4: nightly sync to Cloudflare D1
                                |
                                v
                       Cloudflare Worker
                       photos.93.fyi
                       ├── D1: catalog metadata, captions, tag joins
                       ├── R2: thumbnails (full-res stays on X9)
                       ├── GitHub OAuth: gate to karlmarx only
                       └── Tailscale byte-server (planned): proxy to X9 SSD for full-res reads
```

## Why Cloudflare (not Vercel)

- Workers + D1 + R2 are designed for this shape: search-heavy, image-heavy, low-traffic-personal.
- R2 has no egress fees — full-res-thumb requests don't blow up the budget.
- Workers AI could later run captioning/embeddings cheaper than re-running locally.
- DNS is already on Cloudflare, so attaching the Worker is a one-config step.

## Open questions

- **Tailscale byte server** — full-res photos stay on `/Volumes/Crucial X9/`. The Worker needs a way to serve them on demand without copying everything to R2. Tailscale tailnet exposes the Mac Studio over WireGuard; Worker fetches via `tailscale.93.fyi/<sha>` (or similar). Architecture depends on the Mac being online — acceptable, this is a personal tool.
- **Auth shape** — GitHub OAuth with a strict allowlist (`karlmarx9193@gmail.com` only) vs. Cloudflare Access (consistent with `command.93.fyi`). Cloudflare Access is the simpler answer; deferred.
- **Embeddings strategy** — generate locally (MLX-VLM), upload to D1 with sqlite-vec extension; or generate via Workers AI on demand. Local-first matches the rest of Karl's stack.

## Cross-references

- [photo-memory.md](photo-memory.md) — the upstream pipeline that builds the catalog
- [local-vlm-analysis.md](local-vlm-analysis.md) — the VLM library photo-memory calls
- [domain-93fyi.md](domain-93fyi.md) — DNS for the `*.93.fyi` zone
- [command-center.md](command-center.md) — when shipped, command.93.fyi `/explore` Photos tab will probably embed this
