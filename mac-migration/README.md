# Mac → Work Mac · Config Migration Review

Interactive triage of Karl's home-Mac configuration for setting up a **new, strictly work/dev Mac**.

## How this was generated

This was produced by Claude Code running **in a remote Linux cloud container** (Claude Code on
the web) that only had the `karl-infra` repo cloned into it — **not** the physical Mac. It therefore
**cannot read live machine state** (`~/Library/Preferences/com.googlecode.iterm2.plist`,
`defaults read`, shell dotfiles). Verified: `uname` → Linux; `sw_vers`/`defaults` don't exist;
`~/Library` doesn't exist.

Consequences:
- **Documented config** (the OpenClaw/MLX stack, LaunchAgents, dev tooling, paths, secrets posture)
  was mined from this repo and categorized in `report.html`.
- **Live look-and-feel settings** (iTerm2, macOS `defaults`, shell, Homebrew, VS Code) can't be read
  from here — `report.html` **Section A** gives the exact commands to dump them **on the old Mac**.

## Usage

1. Open `report.html` in a browser.
2. **Section A:** run the export commands on the *old* Mac (or hand them to local Mac Claude).
3. **Section B:** toggle which documented items to carry over. Defaults pre-select only the portable
   `Include`/`Adapt` dev-environment items; personal automation and secrets are left off.
4. Add per-item notes + overall feedback.
5. **Build handoff manifest** → copy/download the Markdown. Hand it to Mac Claude on the new machine,
   alongside the Windows/WSL notes from the work-machine Claude.

## Verdicts

| Verdict | Meaning |
|---|---|
| **Live-export** | Only on the physical Mac — dump via Section A. |
| **Include** | Portable dev-environment value; carry over. |
| **Adapt** | Useful but needs rework / re-keying / a work-policy check. |
| **Exclude** | Personal / home-specific / cloud-hosted — leave behind. |
| **Sensitive** | Involves secrets — never copy verbatim; rotate + use Keychain. |

## ⚠️ Security note surfaced during analysis

`~/.openclaw/openclaw.json` stores secrets in **plaintext**, including `KEEPASS_MASTER_PASSWORD`,
and a GitLab PAT was committed in `tui-dashboard/IDEAS.md`. **Rotate these regardless of migration**,
and never bring them onto a work machine.
