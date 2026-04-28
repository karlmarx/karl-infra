# gemini-auto (Mac Studio)

Headless Playwright automation that drives Google Gemini's *web UI* over Chrome DevTools Protocol to generate images, rotating across multiple Google accounts to dodge per-account daily caps. Bypasses pyautogui's focus issues by speaking directly to the browser DOM.

This is a **content-generation tool**, not a chat client. For the interactive `gemini` CLI (Karl's secondary AI assistant) see [gemini-cli.md](gemini-cli.md).

## What it does

1. Picks the next account that hasn't hit its 40-image/day cap.
2. Ensures Chrome (or Edge) is running with `--remote-debugging-port=<N>` for that account's profile, launching it if needed.
3. Connects via Playwright `chromium.connect_over_cdp(...)`, finds or opens a `gemini.google.com/app` tab.
4. Dismisses CDK overlays, types the prompt with human-like delays / occasional fake typos, submits.
5. Waits for image generation, grabs the result via `download` event → button click → `~/Downloads` scan → `<canvas>` `toDataURL` (four cascading fallbacks).
6. Saves images, updates per-account state.

## Location & layout

| Path | Purpose |
|------|---------|
| `~/gemini-auto/gemini_auto.py` | Single-file script (~790 lines). |
| `~/gemini-auto/README.md` | Brief usage notes. |
| `~/gemini-auto/gemini_auto_results.md` | Run notes / results log. |

No package, no venv hint in-repo — it expects `playwright` available in whatever Python it's invoked with.

## Account rotation

Three accounts hardcoded in the `ACCOUNTS` list. Chrome on `:9222` is primary (assumed already running, e.g. via Claude Desktop); Edge on `:9224` and `:9225` are fallbacks.

| # | Email | Browser | Profile | Debug port |
|---|-------|---------|---------|------------|
| 1 | `5042021062karlmarx@gmail.com` | Chrome | `Default` | 9222 |
| 2 | `karlmarx9193@gmail.com` | Edge | `Profile 1` | 9224 |
| 3 | `benjaminwages@gmail.com` | Edge | `Profile 2` | 9225 |

`DAILY_LIMIT_PER_ACCOUNT = 40`. Per-account history is kept in `account_state.json` next to the output dir; entries older than 24h are pruned each call. When all three accounts are at the cap, the prompt is appended to `queued_prompts.txt` and the run exits with `error: all_accounts_exhausted`.

## Rate limits (per-process)

In addition to the per-account daily cap, the script enforces:

- Hard 30-second floor between consecutive generations within the same run.
- 5-minute back-off (+ 30–120s jitter) if 10+ generations have happened in the last 30 minutes.
- Random 2–5s "warm-up" delay before the first action.
- Human-like typing: variable per-char delays, ~3% chance of typing a wrong char then backspacing, longer pauses on punctuation, occasional thinking pauses.

The point isn't politeness — it's making the traffic look enough like a human that Gemini doesn't trip its abuse heuristics on the account.

## Windows-isms still in the code (flag)

This started life on Windows and several hardcoded paths weren't ported when it moved to the Mac. The script as-shipped will fail on macOS until these are fixed:

| Line | Constant | Current value | Mac equivalent |
|------|----------|---------------|----------------|
| 46 | `OUTPUT_DIR` | `r"C:\Users\50420\.openclaw\workspace\gemini_output"` | `os.path.expanduser("~/.openclaw/workspace/gemini_output")` |
| 50 | `EDGE_PATH` | `r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"` | `/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge` |
| 51 | `CHROME_PATH` | `r"C:\Program Files\Google\Chrome\Application\chrome.exe"` | `/Applications/Google Chrome.app/Contents/MacOS/Google Chrome` |
| 52 | `CHROME_USER_DATA` | `r"C:\Users\50420\AppData\Local\Google\Chrome\User Data"` | `~/Library/Application Support/Google/Chrome` |
| 135-136 | Edge fallback path / user data | `r"C:\Program Files\..."` / `r"C:\Users\50420\AppData\Local\Microsoft\Edge\User Data"` | `~/Library/Application Support/Microsoft Edge` |
| 685 | `~/Downloads` scan | (already portable — uses `os.path.expanduser`) | OK |
| 9 (docstring) | example output path | `C:\\path\\to\\save` | cosmetic |

The `--user-data-dir=<X>` flag also implies Mac equivalents — see Chrome / Edge docs for `--profile-directory`.

If `:9222` is already open (Karl's normal Chrome session with the Default profile), the script is happy to attach to it without touching any of those constants — that's the only path that currently works on Mac without code edits.

## Output

Per-run side-effects under `OUTPUT_DIR`:

- `gemini_image_<timestamp>.png` / `gemini_canvas_<timestamp>.png` / `gemini_download_<timestamp>.png` — the actual images, named by which fallback won.
- `step1_loaded.png` and other progressive screenshots — useful for debugging selector failures at 2am.
- `last_result.json` — `{prompt, timestamp, account, logged_in, saved_images, image_count}`.
- `gemini_auto.log` — per-run log (cleared at start of each run, so previous run's log is gone unless captured).
- `session_state.json` — process-wide rate-limit state.
- `account_state.json` — per-account daily counters.
- `queued_prompts.txt` — append-only overflow when all accounts are exhausted.

## Operational Quick-Reference

| Task | Command |
|------|---------|
| Run a one-shot | `python ~/gemini-auto/gemini_auto.py "a watercolor of Tofino at golden hour"` |
| Check today's per-account usage | `cat <OUTPUT_DIR>/account_state.json \| jq` |
| See the latest run result | `cat <OUTPUT_DIR>/last_result.json` |
| Drain the queue (manual loop) | `while read -r p; do python ~/gemini-auto/gemini_auto.py "$p" && sleep 60; done < <OUTPUT_DIR>/queued_prompts.txt` |
| Debug failure at the selector | Look at `step1_loaded.png` and the in-run screenshots Gemini's UI changes often. |

## Cross-References

- [gemini-cli.md](gemini-cli.md) — interactive Gemini CLI (different tool, different code path).
- [openclaw.md](openclaw.md) — `google` provider for Gemini via API, also different code path.
- [../ARCHITECTURE.md](../ARCHITECTURE.md)
