# Property Scout

> South Florida real estate alert system

## Overview

| Field | Value |
|-------|-------|
| **Location** | `C:\Users\50420\.openclaw\watchdog\property_scout.py` (Windows) |
| **Status** | Running (daily 8:00 AM ET via OpenClaw watchdog) |
| **Stack** | Python (31KB script) |
| **Trigger** | OpenClaw watchdog scheduled task |

## Purpose

Automated daily property search for South Florida house hunting. Checks for new MLS listings matching custom scoring criteria and emails formatted HTML reports.

## How It Works

1. Checks daily for new property listing emails from real estate agent
2. Fetches Matrix MLS portal data for new listings
3. Scores properties on weighted criteria:
   - Privacy / nudity-friendly backyard
   - Water access (< 500 ft)
   - Pool presence
   - Rental separation potential (ADU / guest house)
4. Generates HTML email report with scored rankings
5. Sends to configured recipients (personal + agent)

## Configuration

- `property_scout_config.json` — Gmail app password, recipient list, scoring weights
- Can run in test mode (`--force`) or live (triggered by watchdog)
- Logs to `property_scout.log`

## Dependencies

- Gmail IMAP for listing email detection
- Matrix/OneHome MLS portal for property data
- Gmail SMTP for report delivery
