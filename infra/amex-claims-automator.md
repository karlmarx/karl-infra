# Amex Claims Automator

Playwright-driven Chromium bot that files Amex Return Protection and Loss Protection claims from a JSON batch. Headed mode, human-in-the-loop for login + MFA, automation takes over for the repetitive form filling.

## Purpose

Filing one Amex benefit claim is annoying. Filing a backlog of them is several hours of identical multi-step forms with document uploads. This tool keeps the human in the loop only for what genuinely needs a human (login, MFA, final review of confirmations) and automates the rest.

## Stack

| Layer | Tech |
|-------|------|
| Runtime | Python 3.14 via `uv` |
| Browser | Playwright (Chromium, headed, async) |
| Models | Pydantic v2 (`ClaimsBatch` → `ReturnProtectionClaim` ⨁ `LossProtectionClaim`) |
| CLI / output | Rich (terminal formatting, error logs) |
| Lint | ruff (`py314`, line 100) |

## How it runs

Manual, on-demand. No schedule, no daemon — you run it when you have claims to file.

### Reconnaissance (Phase 1, current)

```bash
cd ~/amex-claims-automator
uv sync
uv run playwright install chromium
uv run python scripts/capture_form.py
```

Opens Chromium → log in manually → capture form HTML at each step into `docs/FORM_STRUCTURE.md`. The selectors that the filler will use don't exist yet — they have to be reverse-engineered from these captures.

### Filing (Phase 2+, not yet implemented)

```bash
cp claims.example.json claims.json
# fill in real claim data + document paths
uv run python src/main.py --claims claims.json [--dry-run] [--verbose]
```

Flow:

1. `main.py` validates `claims.json` against `ClaimsBatch` (Pydantic).
2. `AmexSession` (browser.py) launches Chromium headed, navigates to the login URL with `DestPage=` set to claims center.
3. Terminal prompts: "LOG IN AND COMPLETE MFA … press ENTER". Script blocks on `input()`.
4. Once you press Enter, it confirms it's on the claims center and hands the page to `ClaimFiller`.
5. Per claim: navigate the form, fill fields, upload docs via `page.set_input_files()`, capture confirmation number on success.
6. On error: `capture_error_snapshot()` writes a screenshot + HTML dump under `screenshots/`, then continues with the next claim.

Browser launches with `slow_mo=200` ms by default to stay under any rate-limit / bot-detection thresholds.

## Data flow

```
claims.json (your batch)
  │
  ▼
ClaimsBatch (Pydantic validation — fail fast on bad dates, missing files, etc.)
  │
  ▼
AmexSession ──── opens ─────▶ Chromium (you log in + MFA)
  │                                      │
  │ (you press Enter)                    │
  ▼                                      ▼
ClaimFiller.file_claim()  ─── drives ──▶ claims-center.americanexpress.com
  │
  ├─ on success → confirmation # → terminal log
  └─ on error   → screenshots/{claim_n}_*.png + .html → continue
```

Document uploads come from local paths declared in each claim entry (see `claims.example.json`):

```json
{
  "claim_type": "return_protection",
  "card_last_four": "1234",
  "documents": [{ "path": "docs/receipts/headphones_receipt.pdf", "description": "..." }]
}
```

`DocumentUpload` validates that the file exists before the browser opens.

## Status

**Phase 1 — Reconnaissance.** Scaffolded `2026-04-26`. Single commit: `c9be689 feat: scaffold amex claims automator project`.

| Component | State |
|-----------|-------|
| Project scaffold (`pyproject.toml`, `src/`, `docs/PLAN.md`, `claims.example.json`) | ✅ |
| `AmexSession` (browser launch + login wait) | ✅ Implemented |
| Pydantic models (`ReturnProtectionClaim`, `LossProtectionClaim`) | ✅ Placeholder fields, will need updating after Phase 1 captures |
| `scripts/capture_form.py` | Stub (Phase 1 task 1.1) |
| `ClaimFiller.file_claim()` | Not implemented — raises `NotImplementedError` until selectors are captured |
| Resume / dedupe by confirmation # | Phase 4, not started |
| Dry-run mode | Phase 4, plumbed in CLI but not in filler |

See [`docs/PLAN.md`](https://github.com/karlmarx/amex-claims-automator/blob/main/docs/PLAN.md) for the full 5-phase roadmap.

## Open questions / known issues

- **No selectors yet.** Phase 1 is a literal "go look at the form" exercise. The Pydantic model fields are guesses and will likely change.
- **Rate-limit / fraud-detection risk.** Submitting many claims in a row from the same session may trip Amex's anti-fraud heuristics. Phase 4 plans configurable inter-claim delays; until then, batch sizes should stay small.
- **Login is fully manual every run.** No persisted session cookies (would risk MFA bypass anyway). Plan: live with it.
- **No KeePass auto-fill.** Considered for Phase 5 but the MFA still needs hands so the value is low.
- **Disclaimer:** legitimate cardholder benefits only. Karl is responsible for claim accuracy.

## Cross-references

- Closest cousin: `~/karl-infra/services/return_receipt_scanner.py` (parses return-receipt screenshots into the return tracker — different problem, same general "Karl's purchases" data domain)
- [process-monitor-dashboard.md](process-monitor-dashboard.md) — already monitors a "Return Receipt Scanner" job; this tool is its outbound counterpart, not a scheduled job to add
- [../ARCHITECTURE.md](../ARCHITECTURE.md)
