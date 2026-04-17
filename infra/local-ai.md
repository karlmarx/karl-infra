# Local AI Infrastructure (Mac Studio)

## Overview

Mac Studio M4 Max (36 GB unified memory, commissioned 2026-04-13) is the primary local inference host for vision-language and audio models. Claude Code orchestrates; Ollama serves the models. Bulk data lives on a Crucial X9 2 TB external SSD.

## Hardware

| Component | Spec |
|-----------|------|
| Machine | Mac Studio M4 Max |
| Unified memory | 36 GB |
| Bulk storage | Crucial X9 2 TB (USB 3.2, mounted at `/Volumes/Crucial X9`) |

## Models (via Ollama)

| Model | Size | Role |
|-------|------|------|
| `gemma4:26b` | 17 GB | Large VLM — best quality, run solo (no concurrent heavy models) |
| `gemma4:latest` | 9.6 GB | Mid VLM (~12B) — default for bulk work; allows limited parallelism |
| `llama3.2:1b` | 1.3 GB | Quick sanity tests, prompt validation |

Whisper (for audio/speech pipelines) runs separately — see speech-pipeline docs when created.

## Operational Rule: Back-off Under Load

**Every long-running local-AI workload must be RAM-aware and yield to other processes.** This rule applies to *every* background job Claude orchestrates on this machine — not just one-off pipelines.

Before starting (and periodically during) a heavy inference run:

1. Read current free RAM and RSS of other processes (`vm_stat`, `ps`, or `psutil`).
2. Compute headroom: `available_memory - safety_margin` (default margin: 4 GB for OS/apps).
3. Decide:
   - If the chosen model fits within headroom, proceed at the concurrency allowed by headroom.
   - If not, either (a) wait and re-poll, (b) downshift to a smaller model (`gemma4:26b` → `gemma4:latest` → skip), or (c) reduce concurrency.
4. During the run, pause workers when `psutil.virtual_memory().available` drops below the safety margin. Resume when it recovers. **Pause, don't die** — state files must be durable so the job can be killed and restarted with no data loss.

**Why:** a crashed system from OOM loses in-flight pipeline state, corrupts files mid-write, and costs hours of recovery. The 36 GB budget is easily exhausted by concurrent Ollama instances, browser tabs, other automation, and IDE memory. One misbehaving parallel job can take the whole machine down.

## Patterns

- Long pipelines run detached (background / nohup), not in the foreground of an interactive session.
- Worker-pool sizes are **computed at runtime** from RAM readings, never hard-coded.
- State files (e.g., `pipeline.state`) are append-only and atomic so a killed job resumes cleanly.
- Output catalogs (SQLite + flat files) live on the Crucial X9 alongside the source data; queryable indices get periodically snapshotted to Nextcloud.
- Inference stays local; orchestration may call the Claude API for planning/summarization beyond a single session.

## Cross-References

- [ARCHITECTURE.md](../ARCHITECTURE.md) — full infra map
- [local-windows.md](local-windows.md) — Windows 11 workstation services (separate tier)
