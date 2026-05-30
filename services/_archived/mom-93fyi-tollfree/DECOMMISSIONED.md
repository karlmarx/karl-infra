# mom-93fyi-tollfree — decommissioned 2026-05-30

## Why
Twilio toll-free verification stuck in TWILIO_REJECTED after 2 auto-resubmits.
Rejection reasons: "Website Must Be Established and Active" (30489) +
"Opt-In Example Must Be Complete, Branded, and Legible" (30510).
Karl decided to stop trying and not spend more cycles on TFN verification.

## What was killed
- 2 LaunchAgents (renamed to .plist.disabled in ~/Library/LaunchAgents/)
- 5 service files (moved here)
- State dir at ~/.local/state/mom-93fyi-tollfree (removed)

## What was NOT touched
- The toll-free phone number itself (still rented from Twilio at ~$2/mo)
- ~/mom-93fyi/.env.production.local (Twilio creds preserved)
- The mom-93fyi website (mom.93.fyi) — fully alive
- The pending verification SID HH26844a254ed93af0c8732fc48591a535
  on Twilio (terminal-rejected, no action needed)

## How to revive
1. Move 5 files back to ~/karl-infra/services/
2. Move autofixer plist back to ~/karl-infra/services/launchd/
3. Rename both ~/Library/LaunchAgents/*.disabled → *.plist
4. launchctl load both plists
