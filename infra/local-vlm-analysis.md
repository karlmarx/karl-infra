# Local VLM Analysis

The 3-layer photo + video understanding engine. Lives at `~/projects/local-vlm-analysis/`. Used directly by `workout_watcher.py` (see [workout-pipeline.md](workout-pipeline.md)) and by ad-hoc scripts; intended as the substrate for the photo-memory pipeline (see [photo-memory.md](photo-memory.md)).

## Purpose

Run Gemma vision over Karl's full media library — Google Takeout backlog plus ongoing Nextcloud uploads — and produce structured JSON per item that downstream things (search, narrative, workout digests, photo memory) consume.

Designed around two invariants:

- **Image bytes never leave the local worker.** Cloud subagents (Sonnet/Opus) only ever receive structured JSON. Privacy-by-construction; also avoids cloud content-policy edge cases for naturist photos in Karl's library.
- **Idempotent and restartable.** SQLite (workout) / DuckDB (bulk) state. `process()` rerun on the same input produces the same `data/videos/<sha>.json`.

## Aesthetic catalog — hybrid 9B triage + 27B deep (added 2026-06-07)

`catalog_aesthetic.py` is the always-on subsystem that scores Karl's media for the **hot.93.fyi** gallery. It is **separate** from the workout/`process_video.py` path above and uses its own state DB (`~/.local/share/aesthetic-pipeline/state.db`, table `items`) — not `data/index.duckdb`.

Two stages, two models, two LaunchAgents — split so the GPU is productive whether Karl is present or away:

| Stage | Model / server | When it runs | Runner | LaunchAgent |
|-------|----------------|--------------|--------|-------------|
| **Triage** (cheap: `explicit`, `has_person`, `kind`) | Qwen3.5-**9B** on `:8081` (always-on) | Continuously, **while `:8080` is down** (Karl present) | `~/.openclaw/watchdog/triage-runner.sh` | `com.kmx.aesthetic-triage` |
| **Deep** (composition / subject / physique / attractiveness → `weighted_score`) | Qwen3.5-**27B** on `:8080` (idle-gated) | Opportunistically, **whenever `:8080` is up** (watchdog brought it up: idle/night + RAM≥50%) | `~/.openclaw/watchdog/deep-runner.sh` | `com.kmx.aesthetic-deep` |

**Mutual exclusion by design.** Triage polls `:8080` and yields the moment the 27B is up; deep only runs when `:8080` answers. `catalog_aesthetic.py` holds a single-instance `flock` (`catalog.lock`) that guards the hand-off window, so the two models never infer at once (no 22 GB RAM contention). The mac-watchdog owns the 27B lifecycle — the deep runner has no idle/RAM logic of its own.

**Runner shape.** Both runners loop **internally** (`while true; do <batch>; sleep; done`); launchd `KeepAlive` is only a crash-restart net, NOT the cadence driver. (A one-shot-per-launch script relying on KeepAlive to re-fire stalls — launchd froze it at `runs=1`/`state=not running`. The in-process loop mirrors `continuous_process.py`.) Tunables via plist env: `MAX_PER_RUN_TRIAGE=100`, `MAX_PER_RUN_DEEP=40`. Triage re-runs `discover()` at most every 6h (marker `.last-discover`).

```
SOURCES (~/Pictures, X9/photos/incoming, ~/Nextcloud/Photos, X9 Takeout, …)
   │  discover()  (skips *.photoslibrary bundle internals — volatile derivative paths)
   ▼
items (state.db)
   │  triage-runner.sh → catalog_aesthetic.py --triage-only   → Qwen 9B  :8081   [continuous]
   ▼  (has_person items)
   │  deep-runner.sh   → catalog_aesthetic.py --deep-only      → Qwen 27B :8080   [idle windows]
   ▼  weighted_score + _safe.json/_explicit.json (publish writes JSON only; no git push)
hot.93.fyi gallery
```

**Backlog (2026-06-07):** 55,134 items (47.7k img + 7.4k video); was 9% triaged / **0% deep** (deep had never run). Now grinding continuously on the 9B (~2.2 s/item).

**UPDATE 2026-06-09 — deep moved to the 9B.** The idle-gated 27B never got a start window across two nights: the machine idles at ~41% free RAM and the 27B needs ≥50% (18 GB) to load its 16 GB on top of the always-on 9B's resident weights. The watchdog policy is correct; the box just can't open an 18 GB hole at idle. Meanwhile triage finished the whole backlog (~55k). So the **now-idle 9B does the deep pass too**: `triage-runner.sh` runs `--triage-only` then `--deep-only` each cycle (tunable `MAX_PER_RUN_9B_DEEP`, default 40). It still **yields to the 27B** if `:8080` ever comes up, so the `aesthetic-deep` runner remains the "27B later" path. Deep backlog is **~31k `has_person` items** (triage flagged far more people than expected) → days of continuous 9B work. **TODO (27B later):** to get the higher-quality 27B path live needs (a) the watchdog to evict/pause the 9B during deep windows to free 16 GB, and (b) a re-score mechanism (the 27B runner selects `deep_done_at IS NULL`, so it won't touch items the 9B already scored — clear `deep_done_at` for the top-ranked set to re-score).

**Bug fixes shipped with this (catalog_aesthetic.py):**
- `run_deep` filtered `has_person` *after* `LIMIT` → batches starved to zero. Pushed the predicate into SQL.
- `video_keyframes` used `format=duration`; phone/Takeout videos carry a data track inflating it, so seeks landed past the real footage → silent empty frames → `decode_failed`. Now uses the **video-stream** duration (fallback to format), clamps off the last frame, and logs empty grabs.
- `iter_media` now skips `*.photoslibrary` bundle internals (1,244 volatile entries were polluting the catalog).

**Ops:**
```bash
# state / progress
sqlite3 ~/.local/share/aesthetic-pipeline/state.db \
  "SELECT COUNT(*) total, SUM(triage_done_at IS NOT NULL) triaged, SUM(deep_done_at IS NOT NULL) deep FROM items;"
tail -f ~/.local/share/aesthetic-pipeline/triage-runner.log   # or deep-runner.log
launchctl print gui/$(id -u)/com.kmx.aesthetic-triage | grep -E 'state|runs'
# if an agent shows 'not running', revive it:
launchctl kickstart -k gui/$(id -u)/com.kmx.aesthetic-triage   # or aesthetic-deep
```

> Superseded `com.kmx.aesthetic-catalog` (single idle full-run on the 9B), archived as `…plist.bak.superseded-by-hybrid-20260607`. `disable-27b` flag removed 2026-06-07. `com.kmx.aesthetic-weekly` (Sun 08:00, `aesthetic_weekly.py`) is an independent report job. The `:8080`/`:8081` model names in **Inference backend** below are stale — see [local-ai.md](local-ai.md) for the current Qwen3.5 9B/27B servers.

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
