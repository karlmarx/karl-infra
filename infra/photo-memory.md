# Photo Memory

Local VLM analysis pipeline over a Google Photos Takeout archive (1.1 TB, ~125K unique items after dedupe), with an auth-gated search/MCP layer planned at `photos.93.fyi`.

## Purpose

Turn Karl's personal photo/video archive into a searchable, curated, AI-analyzable library entirely on the Mac Studio. Specifically:

1. Dedupe the Takeout dump (~36% redundancy from album-folder replication) without losing album-membership metadata.
2. Run every unique item through MLX-VLM (Gemma 4 primary, Qwen 2.5-VL for explicit content, PaliGemma 2 for OCR) plus MLX-Whisper for video transcripts. Captions, tags, faces, aesthetic scores, NSFW classification.
3. Curate best-of outputs across multiple modes (general, year-in-review, print, dating-profile shortlists).
4. Serve a single-user GitHub-OAuth-gated search + MCP endpoint at `photos.93.fyi` (Cloudflare Worker, D1 catalog, Mac proxies bytes over Tailscale).
5. Extract speech samples from video audio for future voice-AI work.

Naturist / intimate content is treated as normal personal content; the permissive Qwen VLM is the fallback when Gemma refuses.

## Stack

- **Python 3.14** managed by `uv`; phase scripts run via `uv run` PEP 723 inline metadata.
- **Storage:** SQLite catalog on `/Volumes/Crucial X9` (planned), `sqlite-vec` for image/text embeddings.
- **Inference:** MLX-VLM (`http://127.0.0.1:8080/v1`) — Gemma 4 26B-A4B 4-bit primary, Qwen 2.5-VL 7B 4-bit for explicit, PaliGemma 2 10B for OCR, MLX-Whisper for audio. NudeNet/InsightFace ONNX classifiers.
- **Source data:** `/Volumes/Crucial X9/google-takeout-2026-04-16/Takeout/` (1.1 TB, 115 albums, photo+video+JSON sidecars). Takeout link expires **2026-04-21**.
- **Future deploy:** Cloudflare Worker (D1 + R2 thumbs), GitHub OAuth (allowlist `karlmarx`), Tailscale-only Mac byte server.

## How it runs

| Phase | Script | State | Schedule |
|-------|--------|-------|----------|
| 1 — exact dedupe | `indexer/phase1_dedupe.py` | written, not yet run on full archive | manual `uv run`, resumable via `.pause` touch-file |
| 1 — perceptual dedupe | `indexer/dedupe_perceptual.py` | designed only | — |
| 2 — classify / VLM | `indexer/phase2_classify.py` | sketch (incomplete VLM payload, missing PIL dep) | — |
| 3 — curation | `indexer/curate.py` | designed only | — |
| 4 — Cloudflare worker + Mac byte server | `mcp/`, `mac-server/` | designed only | launchd (planned) |

Phase 1 entry point:

```bash
uv run python ~/photo-memory/indexer/phase1_dedupe.py \
  --root "/Volumes/Crucial X9/google-takeout-2026-04-16/Takeout" \
  --db   "/Volumes/Crucial X9/photo-memory/catalog.db" \
  --log  "/Volumes/Crucial X9/photo-memory/logs/phase1.log"
```

Pause / resume by touching `/Volumes/Crucial X9/photo-memory/.pause`. Pre-flight refuses to start if available RAM < 6 GB or CPU load > 8.

## Data flow

```
Takeout (1.1 TB, X9 SSD)
  │
  ├─ phase1_dedupe.py      → SHA256, pick canonical, symlink dupes → media + dedupe_alts
  ├─ dedupe_perceptual.py  → pHash/dHash clusters → keep best, symlink rest
  ├─ walk.py + pipeline.py → NSFW classify → route to VLM (Gemma/Qwen/PaliGemma)
  │                           → CLIP embeddings → faces → aesthetic → video keyframes + Whisper
  ├─ curate.py             → multi-mode scoring (general/year/print/dating)
  └─ sync.py (nightly)     → quantized export → Cloudflare D1 + R2

Cloudflare Worker (photos.93.fyi)
  └─ MCP tools + web UI, GitHub OAuth (karlmarx only)
       └─ proxies image bytes from Mac via Tailscale (X-Secret header)
```

Catalog tables (planned): `media`, `dedupe_alts`, `captions`, `transcripts`, `tags`, `faces`, `face_clusters`, `people_sidecar`, `curation_scores`, `embeddings`, `work_queue`, `runs`. Faces and raw blobs >1 MB never leave the Mac.

## Status

**Design phase + phase 1 in progress.** Last meaningful change: `2026-04-17` — added `phase1_dedupe.py`. The committed `database.sqlite` at the repo root is a 0-byte placeholder; the live catalog will live on the X9 SSD, not in the repo.

| Component | State |
|-----------|-------|
| Design spec (`docs/superpowers/specs/2026-04-17-photo-memory-design.md`) | Complete, 315 lines, awaiting first full-archive run |
| `phase1_dedupe.py` | Written, RAM-aware, resumable, **not yet run on full archive** |
| `phase2_classify.py` | Sketch only — calls Gemma at `:8080` but `classify_media()` returns hardcoded "Categorized"; PIL not in deps |
| Phases 3–4 | Not started |
| `photos.93.fyi` DNS / Worker | Not provisioned |

## Open questions / known issues

- **Takeout archive expires 2026-04-21** — already past as of writing; verify the source dir at `/Volumes/Crucial X9/google-takeout-2026-04-16/` is still intact before any new download is requested.
- `phase2_classify.py` imports `PIL` but it's not declared in any pyproject — script will fail on first run until rewritten or a proper `pyproject.toml` is added (the repo has none yet).
- The "196K+ files" headline is the spec target, not realized state. Phase 1 has not been run end-to-end.
- Watchdog on `:8080` (in `openclaw`) hardcodes the primary model — see `openclaw.md` for the gotcha if you change it for this pipeline.
- No `pyproject.toml` at the repo root yet; both indexer scripts use PEP 723 inline metadata (`# /// script`).

## Cross-references

- [local-ai.md](local-ai.md) — MLX-VLM server, RAM rules, model roster
- [openclaw.md](openclaw.md) — gateway in front of MLX-VLM `:8080` (and the model-mismatch trap)
- [workout-pipeline.md](workout-pipeline.md) — also reads from `/Volumes/Crucial X9/photos/incoming/`; both pipelines compete for the same MLX-VLM server
- [domain-93fyi.md](domain-93fyi.md) — `photos.93.fyi` will join the same Cloudflare zone
- [../ARCHITECTURE.md](../ARCHITECTURE.md)
