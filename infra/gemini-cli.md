# Gemini CLI (Mac Studio)

Google's official `gemini` CLI, configured for Karl's primary Google account. Used as a *secondary* AI assistant alongside Claude Code — different model family (Gemini 3.x), different rate-limit pool, different MCP extension set.

This is the **interactive `gemini` binary** under `~/.gemini/`. It is not the same thing as:

- `gemini-auto` — the Playwright UI automation that drives Gemini's image-gen page (see [gemini-auto.md](gemini-auto.md)).
- The `google` provider inside openclaw — that calls the Gemini API directly with `GEMINI_API_KEY` (see [openclaw.md](openclaw.md#model-providers)).

## Auth

OAuth personal account (no API key for the CLI itself).

| File | Purpose |
|------|---------|
| `~/.gemini/google_accounts.json` | Active account: `karlmarx9193@gmail.com` (no rotated/old accounts). |
| `~/.gemini/oauth_creds.json` | OAuth refresh token (mode `0600`). Rewritten on token refresh; mtime tracks last refresh. |
| `~/.gemini/settings.json` | `security.auth.selectedType = "oauth-personal"`. |

If `oauth_creds.json` goes stale or is deleted, run `gemini auth login` to re-pair the active account.

## Project Registry

`~/.gemini/projects.json` maps filesystem paths to project names. The CLI scopes history, MCP overrides, and trust state per project.

| Path | Project name |
|------|--------------|
| `/` | `project` |
| `/Users/kmx` | `kmx` |
| `/Users/kmx/mac-setup` | `mac-setup` |
| `/Users/kmx/.openclaw/workspace` | `workspace` |

`/Users/kmx/.openclaw/workspace` is the same workspace openclaw treats as its agent root — running `gemini` there gives it visibility into per-project `AGENTS.md`, `SOUL.md`, `IDENTITY.md`, `USER.md`. Other Karl projects (e.g. `~/karl-infra`, `~/projects/local-vlm-analysis`) inherit the parent `kmx` project rather than getting their own slot.

`~/.gemini/trustedFolders.json` marks `/Users/kmx` as `TRUST_PARENT`, so anything under `~` skips the trust prompt.

Per-project state and history:

- `~/.gemini/history/<project>/` — chat history per project slot.
- `~/.gemini/tmp/<project>/` — scratch files; also `tmp/background-processes/` and `tmp/bin/`.

## Extensions (MCP)

Five extensions installed under `~/.gemini/extensions/`. All are scoped via `extension-enablement.json` overrides to `/Users/kmx/*` (everything under `~`).

| Extension | Source | Purpose |
|-----------|--------|---------|
| `chrome-devtools-mcp` | Google official | Drive Chrome DevTools from a model — DOM, network, console, performance traces. |
| `github` | GitHub official (Go binary) | Issues, PRs, repos, releases against `karlmarx` org. |
| `google-workspace` | — | Gmail / Drive / Calendar over the active OAuth account. |
| `uv-mcp` | — | `uv` package manager wrapper for Python projects. |
| `youtube-to-docs` | — | YouTube transcript / video → doc pipeline. |

`extension_integrity.json` (mode `0600`) holds checksums; if an extension's files change without an explicit reinstall, the CLI refuses to load it.

## State

`~/.gemini/state.json`:

- `tipsShown` — counter for the rotating startup tips.
- `startupWarningCounts.home-directory` — `1`. Karl has run gemini directly from `~` once; the CLI warns about that because tools can wander the entire home tree.
- `defaultBannerShownCount` — keyed by SHA256 of the banner content; once it hits a threshold the banner stops appearing.

`installation_id` (a UUID) identifies this install for telemetry / extension trust.

## When to use Gemini CLI vs. Claude Code

This is the assistant Karl reaches for when:

- The work is **read-heavy across Google accounts** (Gmail search, Drive content extraction) — `google-workspace` MCP is first-class here, vs. Claude Code which goes through individual Gmail/Drive plugin connectors.
- He wants a **second opinion** on a design or a code review without burning Claude Code's context budget for the day.
- He's hitting Anthropic rate limits and needs to keep moving.
- The task is **YouTube transcript → doc** — `youtube-to-docs` lives here.

Claude Code (`claude`) remains the default for general coding, multi-file edits, and anything orchestrated through openclaw. Its config lives at `~/.claude/settings.json` + `~/.claude/CLAUDE.md`; coordination across simultaneous sessions is documented at `~/.claude/coordination.md`.

The two CLIs do **not** share history or context. They share the host's RAM budget, so the same multi-session coordination rule applies — see [local-ai.md](local-ai.md#multi-session-ram-coordination) before starting heavy gemini extension work alongside Claude Code sessions.

## Operational Quick-Reference

| Task | Command |
|------|---------|
| Re-auth active account | `gemini auth login` |
| List projects | `cat ~/.gemini/projects.json` |
| Reset banner / tips | `rm ~/.gemini/state.json` (regenerated on next launch) |
| List enabled extensions | `cat ~/.gemini/extensions/extension-enablement.json` |
| Trust a new folder | Run `gemini` in it, accept the trust prompt (writes `trustedFolders.json`) |

## Cross-References

- [gemini-auto.md](gemini-auto.md) — separate Playwright tool that automates Gemini's image-gen UI.
- [openclaw.md](openclaw.md) — `google` provider uses `GEMINI_API_KEY`, separate from the CLI's OAuth.
- [local-ai.md](local-ai.md) — RAM coordination between Gemini CLI, Claude Code, and MLX servers.
- [../ARCHITECTURE.md](../ARCHITECTURE.md)
