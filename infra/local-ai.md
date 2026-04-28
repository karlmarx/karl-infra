# Local AI (Mac Studio M4 Max)

Three always-on `mlx_vlm.server` processes serve as Karl's primary local inference plane. Ollama is kept around as a fallback for quick text tests but is **disabled in openclaw**. Heavy compute lives here; orchestration may still call hosted APIs.

## Why MLX-VLM (not Ollama) is primary

MLX-VLM runs natively on Apple Silicon's unified memory — no CPU↔GPU copy, no Metal Performance Shaders trampoline. On 36 GB of unified RAM, that's the difference between "loads in 6s" and "OOMs trying to mirror the model."

Per `~/.claude/CLAUDE.md`: **prefer MLX-VLM over Ollama** for vision/VLM tasks. Use the OpenAI-compatible `mlx_vlm.server` endpoints (loopback only — `127.0.0.1`, never `0.0.0.0`).

Ollama remains installed but `plugins.ollama.enabled = false` in `~/.openclaw/openclaw.json` — it's reachable manually for one-shot text tests, not part of the live routing chain. See [openclaw.md](openclaw.md#model-providers) for routing details.

## MLX-VLM Servers

Three independent `mlx_vlm.server` processes, each pinned to one model on a different port. All bind loopback. All speak OpenAI completions.

| Port | Provider name (in openclaw) | Loaded model | Context | Role |
|------|------------------------------|--------------|---------|------|
| 8080 | `mlx-vlm` | `mlx-community/Qwen3.5-27B-4bit` | 128k | Heavy analysis (vision + text). Fallback target for `mlx-vlm-fast`. **Watched.** |
| 8081 | `mlx-vlm-fast` | `mlx-community/Qwen3.5-9B-MLX-4bit` | 32k | Default chat / fast text. Currently the **primary** model in openclaw. **Not watched.** |
| 8082 | `mlx-vlm-qwen` | `mlx-community/Qwen3.5-9B-MLX-4bit` | 262k | Long-context reasoning (vision + text). **Not watched.** |

Provider strings in openclaw are `<provider>/<model.id>` with the full `mlx-community/...` HF prefix in the model ID — bare names will not resolve.

`mlx_vlm.server` exposes its loaded model at `GET /v1/models`. The `id` returned must match what openclaw asks for, or the gateway surfaces an HTTP 401 to the caller (see [openclaw.md](openclaw.md#critical-gotcha--primary-model-is-hardcoded-twice)).

### Models pulled but not currently served

These are present in `~/.cache/huggingface/hub/` and show up in `/v1/models` listings on whichever server has scanned them, but no port is dedicated to them today:

- `mlx-community/gemma-4-26b-a4b-it-4bit` (15 GB) — best balance of speed + quality on 36 GB.
- `mlx-community/gemma-4-26b-a4b-it-8bit` (26 GB) — higher quality, tight on RAM.
- `mlx-community/gemma-3-4b-it-4bit` — small/fast Gemma 3.
- `mlx-community/paligemma2-10b-mix-448-4bit` — lightweight vision model.
- `mlx-community/gemma-2-27b-it-4bit`, `gemma-2-9b-it-4bit` — older gen, kept for compat.

To switch one of the three live servers to a different model, see [Manual restart](#manual-restart) below.

## Routing

openclaw is the only thing that should be calling these servers. It picks via `agents.defaults.model` (primary + fallback chain) in `~/.openclaw/openclaw.json`. Don't duplicate that config here — see [openclaw.md#default-model--fallback-chain](openclaw.md#default-model--fallback-chain).

The short version: a request that hits openclaw at `127.0.0.1:18789` gets routed to one of the three MLX ports based on the requested provider. If the server on that port is down or running the wrong model, openclaw returns 401/502 to the caller — it does not transparently fail over to a different MLX port.

## Startup & Recovery

### Watched: `:8080` only

The `mac-watchdog.sh` LaunchAgent (loops every 60s) explicitly watches **only** the `:8080` server. If it dies, the watchdog restarts it with:

```bash
nohup mlx_vlm.server --model "$ANALYSIS_MODEL" --host 127.0.0.1 --port 8080 \
  >> ~/.openclaw/logs/mlx-vlm-server-27b.log 2>&1 &
```

`ANALYSIS_MODEL` is hardcoded in the watchdog at line 8 — currently `mlx-community/Qwen3.5-27B-4bit`. **Must match** the model openclaw expects on `:8080`, or restart-after-crash will silently bring up the wrong model and inference will look broken. See [openclaw.md](openclaw.md#critical-gotcha--primary-model-is-hardcoded-twice) for the full failure mode.

The watchdog also defines `CHAT_MODEL = "mlx-community/Qwen3.5-9B-MLX-4bit"` and a `CHAT_LOG` path at line 12 — but these constants are **not** used by the active `check_and_restart` calls. `:8081` and `:8082` are not watched.

### Not watched: `:8081`, `:8082` (silent failure mode)

If either dies, openclaw routes to it transparently 502, and nothing brings it back. You will only notice when:

- A pipeline that uses long-context Qwen on `:8082` starts erroring.
- The default chat path (currently routed to `:8081` via `mlx-vlm-fast`) goes dead.

The [process-monitor-dashboard](process-monitor-dashboard.md) does not yet probe these ports specifically — it shows Ollama state, not MLX state. If you want a heads-up, `lsof -i :8081 -i :8082` in a `watch` is the cheapest tell.

### Manual restart

```bash
# :8080 (heavy analysis, watched)
nohup mlx_vlm.server --model mlx-community/Qwen3.5-27B-4bit \
  --host 127.0.0.1 --port 8080 \
  >> ~/.openclaw/logs/mlx-vlm-server-27b.log 2>&1 &

# :8081 (fast chat, NOT watched)
nohup mlx_vlm.server --model mlx-community/Qwen3.5-9B-MLX-4bit \
  --host 127.0.0.1 --port 8081 \
  >> ~/.openclaw/logs/mlx-vlm-server-fast.log 2>&1 &

# :8082 (long-context reasoning, NOT watched)
nohup mlx_vlm.server --model mlx-community/Qwen3.5-9B-MLX-4bit \
  --host 127.0.0.1 --port 8082 \
  >> ~/.openclaw/logs/mlx-vlm-qwen.log 2>&1 &
```

To swap the model on a port: kill the existing process (`pkill -f "port 8080"` is precise enough since each runs on a unique port), edit the relevant config (watchdog if `:8080`, or just the manual command), and restart.

To verify a server has the model openclaw expects:

```bash
curl -s http://127.0.0.1:8080/v1/models | jq '.data[].id'
```

The first ID returned is the active model; subsequent IDs are HF cache scans, not loaded weights.

## Ollama (fallback / quick test)

Installed at the standard location, manageable via the `Ollama` macOS app or the `ollama` CLI. Listens on `http://127.0.0.1:11434`. The watchdog will restart the Ollama process if `pgrep -f "ollama serve"` and `pgrep -x Ollama` both come up empty (`open -a Ollama`).

Models available locally:

| Model | Size | Notes |
|-------|------|-------|
| `gemma4:26b` | 17 GB | Largest local; only run solo. |
| `gemma4` / `gemma4:latest` | ~9.6 GB | Mid VLM (~12B), default for ad-hoc. |
| `llama3.2:1b` | 1.3 GB | Sanity tests, prompt validation. |

In openclaw, `plugins.entries.ollama.enabled = false`. The provider config is still present under `models.providers.ollama` so it can be flipped back on without re-auth — but until it's flipped, openclaw will not route here and the `mlx-vlm` chain owns all traffic. Flip it back if MLX is down across the board and you need *something* serving locally.

Direct call without going through openclaw:

```bash
ollama run gemma4:latest "summarize this changelog"
ollama ps   # see what's loaded
```

## RAM Awareness (the always rule)

**Every long-running local-AI workload must be RAM-aware.** This applies to *every* background pipeline — not just AI jobs. The 36 GB unified budget is easily exhausted by simultaneous Claude Code sessions, Chrome, MLX servers, and an active Ollama load.

### Safety margin

- Default reserve: **4 GB** for OS / interactive apps.
- Compute headroom: `available_memory − 4 GB`. If a model doesn't fit, downshift or wait — never start.
- During a run, pause workers when `psutil.virtual_memory().available` drops below the safety margin. Resume when it recovers. **Pause, don't die.**

The watchdog uses a stricter rule for `:8080` restart specifically:

- Restart of `:8080` is **deferred** when available RAM < 10% of total OR `kern.memorystatus_vm_pressure_level ≥ 4` (critical).
- Probe still runs, so logs reflect actual state during deferral.
- Critical-RAM transitions emit a Telegram + Discord alert (see [openclaw.md](openclaw.md#known-alert-routing-bugs-open) — these are currently misrouted to `--target default` and silently fail).

### Patterns

- Long pipelines run detached (`nohup`), not in the foreground of an interactive session.
- Worker-pool sizes are **computed at runtime** from RAM readings, never hard-coded.
- State files (e.g. `pipeline.state`) are append-only and atomic so a killed job resumes cleanly.
- Output catalogs (SQLite + flat files) live on `/Volumes/Crucial X9` alongside the source data; queryable indices snapshot periodically to Nextcloud.
- Inference stays local; orchestration may call Anthropic / Google APIs for planning beyond a single session.

## Multi-Session RAM Coordination

When 2+ Claude Code sessions are running in parallel (Karl regularly runs up to 9), they share the same 36 GB pool with the MLX servers. Coordinate through `~/.claude/coordination.md` — read it before starting any heavy compute.

Decision rules:

| Free RAM | Action |
|----------|--------|
| < 200 MB | Stop. Report "Memory critical. Pausing work." Wait for user signal. |
| 200 MB – 500 MB | Light tasks only (text, research, small edits). No inference. |
| 500 MB – 1 GB | Non-memory-intensive work OK. Ask user before heavy tasks. |
| > 1 GB | OK to proceed with light/medium tasks. |

Cheap probe: `top -l1 | grep PhysMem`.

Before starting heavy inference or large data processing, **tell the user first** — don't assume other Claude instances are idle. The `mlx_vlm.server` process holding `Qwen3.5-27B-4bit` alone reserves ~17 GB of resident memory; a sibling Claude session that triggers a Gemma load can flip the system into pressure level 4 instantly.

## Storage

| Path | Purpose |
|------|---------|
| `~/.cache/huggingface/hub/` | MLX-VLM model weights (download cache). |
| `~/.openclaw/logs/mlx-vlm-server-27b.log` | `:8080` (analysis) stdout/stderr. |
| `~/.openclaw/logs/mlx-vlm-server-fast.log` | `:8081` (fast chat) — convention; verify on restart. |
| `~/.openclaw/logs/mlx-vlm-qwen.log` | `:8082` (long-ctx reasoning). |
| `/Volumes/Crucial X9/` | Bulk source data (photos, videos) for pipelines. |
| `~/.local/share/<pipeline>/state.db` | Per-pipeline SQLite state (e.g. `workout-pipeline/state.db`). |

## Operational Quick-Reference

| Task | Command |
|------|---------|
| What's listening on MLX ports | `lsof -i :8080 -i :8081 -i :8082` |
| Active model on a port | `curl -s http://127.0.0.1:<port>/v1/models \| jq '.data[0].id'` |
| Tail `:8080` log | `tail -f ~/.openclaw/logs/mlx-vlm-server-27b.log` |
| Free RAM right now | `top -l1 \| grep PhysMem` |
| Pressure level | `sysctl -n kern.memorystatus_vm_pressure_level` (`1` normal, `2` warning, `3` urgent, `4` critical) |
| Kill a wedged MLX server on a port | `lsof -ti :<port> \| xargs kill` |
| End-to-end test through openclaw | `openclaw model run "say yes" --provider mlx-vlm-fast --model mlx-community/Qwen3.5-9B-MLX-4bit` |

## Cross-References

- [openclaw.md](openclaw.md) — gateway, routing, watchdog details, alert routing bugs.
- [process-monitor-dashboard.md](process-monitor-dashboard.md) — terminal UI; currently shows Ollama + Claude sessions, not MLX state.
- [workout-pipeline.md](workout-pipeline.md) — heaviest consumer of `:8080`; documents the OpenAI-compatible call shape.
- [gemini-cli.md](gemini-cli.md), [gemini-auto.md](gemini-auto.md) — non-MLX inference paths that share the RAM budget.
- [../ARCHITECTURE.md](../ARCHITECTURE.md)
