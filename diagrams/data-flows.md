# Data Flow Diagrams

## TrickAdvisor

```
User (browser)
  |
  |  HTTPS (ta.93.fyi)
  v
TrickAdvisor (React SPA on Vercel)
  |
  +-- Supabase Auth (login/register)
  |     +-- email/password
  |     +-- session tokens
  |
  +-- TrickAdvisor-API (Vercel Functions)
  |     |
  |     +-- GET /encounters -> list encounters
  |     +-- POST /encounters -> create encounter
  |     +-- POST /ratings -> submit rating
  |     +-- POST /photos -> upload (-> Supabase Storage)
  |     +-- Admin: approve/reject photos -> email notification
  |     |
  |     v
  |   Supabase Postgres
  |     +-- users, profiles
  |     +-- encounters, ratings
  |     +-- photos (metadata)
  |
  +-- Supabase Storage (photos bucket)
```

## NWB Fitness / NWB Yoga

```
User (browser or installed PWA)
  |
  |  HTTPS (nfit.93.fyi / nyoga.93.fyi)
  v
Vercel CDN (static HTML)
  |
  v
Single-file PWA (no backend)
  +-- Service Worker (offline caching)
  +-- localStorage (user preferences)
  +-- All exercise data embedded in HTML
```

## Find Hub Tracker (Planned)

```
Google Find Hub API
  |
  |  Poll every N minutes
  v
find-hub-tracker (Python on ultra.cc)
  |
  +-- Parse device location + battery
  |
  +-- Geofence check
  |     +-- If outside boundary -> alert
  |     +-- If battery low -> alert
  |
  +-- Discord Webhook
  |     +-- Location update message
  |     +-- Alert embeds with map link
  |
  +-- Healthchecks.io ping (dead man's switch)
```

## Claude Pipeline

```
Claude.ai (browser)
  |
  |  User saves .md file
  v
~/Nextcloud/Documents/inbox/
  |
  |  Nextcloud sync
  v
Windows workstation filesystem
  |
  |  File watcher (watchdog)
  v
claude-pipeline (Python)
  |
  +-- Parse .md frontmatter
  +-- Route to OpenClaw sub-agent
  |
  v
OpenClaw gateway
  +-- Execute prompt
  +-- Write response back to Nextcloud
```

## OpenClaw Watchdog

```
openclaw-watchdog (Python/Rich)
  |
  +-- Monitor OpenClaw gateway process
  |     +-- Check if alive every 30s
  |     +-- Restart if crashed
  |
  +-- Screen management
  |     +-- Prevent sleep/lock
  |
  +-- Health notifications
        +-- Discord webhook on crash/restart
        +-- AI scoring (Gemini -> DeepSeek fallback)
```
