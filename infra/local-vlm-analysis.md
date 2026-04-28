# Local VLM Analysis

The 3-layer photo + video understanding engine. Lives at `~/projects/local-vlm-analysis/`. Used directly by `workout_watcher.py` (see [workout-pipeline.md](workout-pipeline.md)) and by ad-hoc scripts; intended as the substrate for the photo-memory pipeline (see [photo-memory.md](photo-memory.md)).

## Purpose

Run Gemma vision over Karl's full media library — Google Takeout backlog plus ongoing Nextcloud uploads — and produce structured JSON per item that downstream things (search, narrative, workout digests, photo memory) consume.

Designed around two invariants:

- **Image bytes never leave the local worker.** Cloud subagents (Sonnet/Opus) only ever receive structured JSON. Privacy-by-construction; also avoids cloud content-policy edge cases for naturist photos in Karl's library.
- **Idempotent and restartable.** SQLite (workout) / DuckDB (bulk) state. `process()` rerun on the same input produces the same `data/videos/<sha>.json`.

## Location

| Piece | Path |
|-------|------|
| Project root | `~/projects/local-vlm-analysis/` |
| Per-video JSON | `~/projects/local-vlm-analysis/data/videos/<sha>.json` |
| Frame derivatives | `~/projects/local-vlm-analysis/data/derivatives/<sha>/frame_*.jpg` |
| Bulk photo index | `~/projects/local-vlm-analysis/data/index.duckdb` |
| Strategy doc | `~/projects/local-vlm-analysis/STRATEGY.md` |
| Schemas | `~/projects/local-vlm-analysis/schemas.py` |

Bulk media lives on `/Volumes/Crucial X9` — the project dir holds derivatives + index, not raw bytes.

## Inference backend

- **Primary**: MLX-VLM HTTP server on `http://localhost:8080/v1/chat/completions` (OpenAI-compatible).
- **Default model**: `mlx-community/gemma-4-26b-a4b-it-8bit` (~26 GB unified memory, 8K ctx, vision-capable).
- **Fallback / dev**: Ollama (`gemma4:26b`, `gemma4:latest`), but Ollama's `gemma4` pull is text-only — switched away on 2026-04-15.

The MLX server is **not** managed by this project — it's a precondition. Same `:8080` instance is shared with openclaw and the workout pipeline. RAM rules in [local-ai.md](local-ai.md) apply.

```bash
mlx_vlm.server --model mlx-community/gemma-4-26b-a4b-it-8bit --host 127.0.0.1 --port 8080
```

## Three-layer schema

Lower layers are cheap and apply to everything; higher layers run only on candidates the previous layer flagged. Schemas in `schemas.py`.

| Layer | When | Output (abridged) |
|-------|------|---------------------|
| **Triage** | Every image | `quality` (excellent → blurry/screenshot/dup), `kind` (photo/screenshot/meme/document/art). If quality < ok or kind ≠ photo, skip Layer 2. |
| **Universal** | Photos that pass triage | `caption`, `tags[]` (≤8), `scene`, `setting`, `people_count`, `people_visible_attributes[]` (incl. `nude` — meaningful tag, not a flag), `primary_subject`, `time_of_day_guess`, `weather_guess`, `color_palette[]`, `is_workout_related`. |
| **Workout** | When Universal sets `is_workout_related: true` | `exercise_type`, `exercises_visible[]`, `equipment_visible[]`, `body_focus[]`, `form_notes`, `is_progress_photo`, `intensity_guess`, `environment`. |

Output is forced to JSON via OpenAI `response_format: json_object` and validated for required keys in Python (one retry on missing fields). Temperature 0.2 for classification stability.

## Entry points

| Script | Purpose |
|--------|---------|
| `process_video.py` | End-to-end one video → frames + transcript + per-frame VLM + aggregate `workout_summary`. Called as a library by `workout_watcher.py`. Output: `data/videos/<sha>.json`. |
| `extract_frames.py` | ffmpeg keyframes (scene-change `gt(scene,0.3)`) + uniform fallback every 5 s, dedup gap 1.5 s, downscale to 1024 px. Also exports `sha256_head()` (first 1 MiB hash, used as the canonical video ID). |
| `worker.py` | Bulk photo worker: pulls pending rows from `data/index.duckdb`, runs triage + universal + workout, writes back. `--batch N`, idempotent (skips `status='done'`). |
| `vlm.py` | Shared HTTP shim — `triage()`, `universal()`, `workout()`. All paths through `:8080`. |
| `transcribe.py` | Whisper for video audio (used by `process_video.py`). |
| `inventory.py` | Walk Takeout + osxphotos export, populate `media` table with sha256 dedup. |

## Data flow (workout case)

```
[/Volumes/Crucial X9/photos/incoming/Camera/VID_*.mp4]
    ↓ workout_watcher.py (every 15 min, com.kmx.workout-ingest)
[process_video.process()]
    ├─ extract_frames.py → data/derivatives/<sha>/frame_*.jpg
    ├─ vlm.triage() per frame                 →
    ├─ vlm.universal() if not skipped         → → MLX-VLM :8080 (Gemma 4 26B 8-bit)
    ├─ vlm.workout() if is_workout_related    →
    └─ aggregate_workout() → workout_summary
[~/projects/local-vlm-analysis/data/videos/<sha>.json]
    ↓ workout_digest.py (daily 07:00, com.kmx.workout-digest)
[Email digest]
```

## Data flow (bulk photo case — Phase 2 of STRATEGY.md)

```
[X9 Takeout + osxphotos export]
    ↓ inventory.py
[data/index.duckdb: media table, status='pending']
    ↓ worker.py --batch N
[triage_json, universal_json, workout_json columns populated]
    ↓ (Phase 3)
[Search + narrative layer — not yet built]
```

## RAM and concurrency

- The 8-bit Gemma model occupies ~26 GB. On a 36 GB Mac Studio, that leaves ~10 GB for OS + browser + everything else.
- No batch parallelism — unified memory is already shared with the GPU.
- Per [local-ai.md](local-ai.md): every long-running consumer here must check `psutil.virtual_memory().available` before each work unit and pause/exit when below the safety margin (currently 200 MB hard floor, 500 MB tight, 1 GB caution).
- `workout_watcher.py` is the canonical example of the right RAM-guard pattern — copy that shape for any new consumer.

## Throughput targets

| Workload | Wall time |
|----------|-----------|
| 10k photos (Layer 1+2 mixed) | ~3–4 hours |
| 100k photos | ~28–36 hours (one long weekend) |
| 1-min video at 1 frame / 2 s | ~30 s inference |
| 10-min video at same rate | ~5 min inference |

## Known limitations

- **No video file cleanup.** `process_video.py` writes JSON but never touches the source `.mp4`. Retention policy is manual.
- **No durable retry queue.** Transient MLX-VLM or filesystem failures get logged and skipped; the next watcher cycle picks them up via SHA-based dedup.
- **No audio + video joint reasoning.** Whisper transcript and per-frame VLM outputs sit side-by-side in the JSON; downstream code (workout digest, future photo-memory) does the joining.
- **Schema drift requires reprocessing.** `reprocess_vlm.py` exists for this — re-runs vlm calls on existing derivative frames without re-extracting.

## Cross-references

- [workout-pipeline.md](workout-pipeline.md) — the most active consumer; uses `process_video.process()` + state DB for video deduplication.
- [photo-memory.md](photo-memory.md) — bulk-photo consumer of the same engine (separate doc).
- [local-ai.md](local-ai.md) — MLX-VLM server lifecycle, RAM rules, model inventory.
- [openclaw.md](openclaw.md) — routes inference through the same `:8080` MLX-VLM provider; this project + openclaw share the model.
- `~/projects/local-vlm-analysis/STRATEGY.md` — the long-form design doc; this infra doc is the operational summary.
- [../ARCHITECTURE.md](../ARCHITECTURE.md)
