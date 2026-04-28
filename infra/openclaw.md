# OpenClaw (Mac Studio)

Local model gateway/router that routes inference between MLX-VLM, Ollama, and Google Gemini. Loopback-only, token-auth, four LaunchAgents.

## Mode

- `gateway.mode = local` (no Tailscale, no remote node sharing)
- Listens on `127.0.0.1:18789` (`gateway.bind = loopback`)
- Token auth: `feda81ca…` in `~/.openclaw/openclaw.json` (`gateway.auth.token`)
- ControlUi origins limited to `http://127.0.0.1:18789` and `http://localhost:18789`

## LaunchAgents

| Label | Plist | Role |
|-------|-------|------|
| `ai.openclaw.gateway` | `~/Library/LaunchAgents/ai.openclaw.gateway.plist` | Node.js gateway (`openclaw gateway --port 18789`). KeepAlive. Logs `gateway.log` / `gateway.err.log`. |
| `ai.openclaw.node` | `~/Library/LaunchAgents/ai.openclaw.node.plist` | Worker node (`openclaw node run --host 127.0.0.1 --port 18789`). KeepAlive. Logs `node.log` / `node-error.log`. |
| `ai.openclaw.watchdog` | `~/Library/LaunchAgents/ai.openclaw.watchdog.plist` | Runs `~/.openclaw/watchdog/mac-watchdog.sh` in a 60s loop. KeepAlive. |
| `com.karlmarx.openclaw-health-check` | `~/Library/LaunchAgents/com.karlmarx.openclaw-health-check.plist` | Weekly Sunday 10:00 — runs `~/.openclaw/scripts/health-check.sh`, emits to `health-check.log`. |

All paths logged under `~/.openclaw/logs/`.

## Model Providers

Defined in `~/.openclaw/openclaw.json` under `models.providers`. Five providers, all `apiKey` env-var-resolved:

| Provider | Endpoint | API | Models |
|----------|----------|-----|--------|
| `mlx-vlm` | `http://127.0.0.1:8080/v1` | `openai-completions` | `gemma-4-26b-a4b-it-4bit` (128k ctx), `gemma-4-26b-a4b-it-8bit` (128k), `gemma-3-4b-it-4bit` (32k) |
| `mlx-vlm-fast` | `http://127.0.0.1:8081/v1` | `openai-completions` | `gemma-3-4b-it-4bit` (8k) |
| `mlx-vlm-qwen` | `http://127.0.0.1:8082/v1` | `openai-completions` | `Qwen3.5-9B-MLX-4bit` (262k, reasoning) |
| `ollama` | `http://127.0.0.1:11434` | `ollama` | `gemma4`, `gemma4:latest`, `gemma4:26b`, `llama3.2:1b` (currently `plugins.ollama.enabled = false`) |
| `google` | `https://generativelanguage.googleapis.com` | `google-generative-ai` | `gemini-3.1-pro-preview`, `gemini-3.1-flash-preview` |

All MLX providers send the literal token `MLX_VLM_API_KEY` (env-var name; not actually validated by the local server). Google uses `GEMINI_API_KEY`.

### Default model + fallback chain

`agents.defaults.model`:

```
primary:    mlx-vlm/mlx-community/gemma-4-26b-a4b-it-4bit
fallbacks:  google/gemini-3.1-pro-preview
```

Provider strings are `<provider>/<model.id>` with the full `mlx-community/...` HF prefix in the model ID — bare names will not resolve.

## Watchdog

Script: `~/.openclaw/watchdog/mac-watchdog.sh` (loops every 60s).

Watches and restarts:

| Process | Detect | Restart |
|---------|--------|---------|
| `openclaw-gateway` | `pgrep -f` | `openclaw gateway restart` |
| `openclaw-node` | `pgrep -f` | `openclaw node restart` |
| Ollama | `pgrep -f "ollama serve"` or `pgrep -x Ollama` | `open -a Ollama` |
| MLX-VLM `:8080` | `lsof -i :8080` | `nohup mlx_vlm.server --model "$MLX_VLM_MODEL" --host 127.0.0.1 --port 8080` |

**NOT watched (silent failure mode):**

- `:8081` — `mlx-vlm-fast` (`gemma-3-4b-it-4bit`). If it dies, openclaw routes to it transparently 502.
- `:8082` — `mlx-vlm-qwen` (`Qwen3.5-9B-MLX-4bit`). Same.

If you need either of these, restart manually (see `local-ai.md`).

### RAM-gated restart

The watchdog computes available memory the macOS-correct way (16K page size on Apple Silicon, includes free + speculative + inactive pages) and reads kernel pressure (`kern.memorystatus_vm_pressure_level`). Restart of `:8080` is **deferred** when:

- available < 10% of total, **or**
- pressure ≥ 4 (critical)

Probe of `:8080` always runs, so logs reflect actual state even during deferral. Critical-RAM transitions emit a Telegram + Discord alert (see "Channel alerts" below).

### Critical gotcha — primary model is hardcoded twice

The watchdog hardcodes `MLX_VLM_MODEL` at line 14 of `mac-watchdog.sh`:

```bash
MLX_VLM_MODEL="mlx-community/gemma-4-26b-a4b-it-4bit"
```

This **must** match `agents.defaults.model.primary` in `~/.openclaw/openclaw.json`. If you change the primary in `openclaw.json` and forget the watchdog:

1. The next time `:8080` dies, the watchdog brings up the *old* model.
2. Openclaw asks the gateway for the *new* model.
3. The gateway gets a "model not loaded" error from `mlx_vlm.server` and surfaces it as **HTTP 401** to the caller.
4. Inference appears broken with no obvious cause — the MLX server is up, just running the wrong model.

**Always edit both files together.** Sanity check with the weekly health check: it logs `watchdog script configured for <name>` and `:8080 healthy with <name> model`.

## Channel Integrations

Configured in `channels.*` in `~/.openclaw/openclaw.json`:

- **Telegram** — `enabled: true`, bot token in config, `dmPolicy: pairing`, `groupPolicy: open`, partial streaming.
- **Discord** — `enabled: true`, token in config, `groupPolicy: open`, no streaming, guild `1486327292438253602` allows user `643945264868098049` without mention.

### Known alert routing bugs (open)

Watchdog/health-check use `--target default`, which neither channel resolves:

```
Error: Telegram recipient @default could not be resolved to a numeric chat ID
       (Call to 'getChat' failed! (400: Bad Request: chat not found))
Error: Unknown target "default" for Discord.
       Hint: <channelId|user:ID|channel:ID>
Error: Cannot send messages to this user
```

Result: critical-RAM alerts and weekly health failures **silently fail to reach Karl**. Fix is to either (a) configure a paired Telegram peer + Discord channel ID and replace `default`, or (b) teach `send_alert()` in `mac-watchdog.sh` to read from a `~/.openclaw/alert-targets.json`. Tracked but not yet done.

## Storage

| Path | Purpose |
|------|---------|
| `~/.openclaw/openclaw.json` | Main config (env, gateway, channels, model providers). |
| `~/.openclaw/openclaw.json.bak*` | Rolling backups across config edits. |
| `~/.openclaw/tasks/runs.sqlite` (+ `-wal`, `-shm`) | Run history. |
| `~/.openclaw/memory/main.sqlite` | Persistent agent memory. |
| `~/.openclaw/flows/registry.sqlite` | Flow registry. |
| `~/.openclaw/workspace/` | Per-project agent workspaces (AGENTS.md, SOUL.md, IDENTITY.md, USER.md, etc.). Gemini CLI also has this registered as a project. |
| `~/.openclaw/logs/*.log` | gateway, node, watchdog, mlx-vlm-server, mlx-vlm-qwen, health-check, config-audit, commands. |

## Security — plaintext credentials (deferred migration)

`~/.openclaw/openclaw.json` stores secrets in plaintext under `env`:

- `GITHUB_TOKEN`
- `GEMINI_API_KEY`
- `GOOGLE_API_KEY`
- **`KEEPASS_MASTER_PASSWORD`** ← KeePass master password lives here in cleartext

Discord and Telegram bot tokens are also plaintext under `channels.*`. The same secrets are duplicated into `EnvironmentVariables` in `ai.openclaw.gateway.plist`.

This is a known issue tracked in MEMORY as `project_openclaw_secrets_migration` — pending migration to Keychain or a `.env` file with `0600` perms read at gateway startup. **Until that lands, treat this file as the most sensitive plaintext on the machine** — back it up to nothing that isn't already at rest encrypted.

## Operational Quick-Reference

| Task | Command |
|------|---------|
| Tail watchdog | `tail -f ~/.openclaw/logs/watchdog.log` |
| Tail gateway | `tail -f ~/.openclaw/logs/gateway.log` |
| End-to-end test | `openclaw model run "say yes" --provider mlx-vlm --model mlx-community/gemma-4-26b-a4b-it-4bit` |
| Restart watchdog | `launchctl kickstart -k gui/$UID/ai.openclaw.watchdog` |
| Restart gateway | `launchctl kickstart -k gui/$UID/ai.openclaw.gateway` |
| Force health check now | `bash ~/.openclaw/scripts/health-check.sh` |
| Inspect runs DB | `sqlite3 ~/.openclaw/tasks/runs.sqlite '.tables'` |

## Cross-References

- [local-ai.md](local-ai.md) — MLX-VLM servers, Ollama, RAM rules
- [process-monitor-dashboard.md](process-monitor-dashboard.md) — terminal UI that reads MLX/Ollama state
- [command-center.md](command-center.md) — dashboard at command.93.fyi consumes `/openclaw` from the FastAPI agent
- [../ARCHITECTURE.md](../ARCHITECTURE.md)
