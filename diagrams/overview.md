# System Overview

```
+-------------------------------------------------------------------+
|                      Karl's Infrastructure                        |
+-------------------------------------------------------------------+
|                                                                   |
|  APPS (Vercel)              AUTOMATION (Local / ultra.cc)         |
|  ---------------            ----------------------------          |
|  nfit.93.fyi                Windows 11 Workstation                |
|  +- nwb-plan ----------+   +- OpenClaw (AI assistant)            |
|  |                      |   +- claude-pipeline (watcher)          |
|  nyoga.93.fyi           |   |  +- watches Nextcloud/inbox/       |
|  +- nwb-yoga ------+   |   |                                     |
|  |                  |   |   ultra.cc seedbox (planned)            |
|  id.93.fyi          |   |   +- find-hub-tracker                  |
|  +- Social ID       |   |      +- polls Google Find Hub          |
|     + SIV-API       |   |         +- Discord alerts              |
|                     |   |                                         |
|  contact.93.fyi ----+   |   INFRA                                |
|  +- Contact Form        |   ------                                |
|     + Turnstile CAPTCHA |   Dynadot (.fyi registrar)              |
|     + Resend email      |   Cloudflare (DNS + email routing)      |
|                         |   GitHub (all repos + Actions)          |
|  Supabase (DB) -----+   |   Vercel (all deployments)            |
|                         |                                         |
|  progress.93.fyi -------+   Nextcloud (Takeout, TODO, logs)       |
|  +- Progress Dashboard  |                                         |
|     (status monitor)    |                                         |
|     + local system polling                                       |
|     + email notifications
|                            | Nextcloud (Takeout, TODO, logs)     |
|  93.fyi ----------------+  |                                     |
|  (Cloudflare DNS)           |                                     |
|  k@93.fyi -> Gmail          |                                     |
+-------------------------------------------------------------------+
```

## Deployment Topology

```
                    GitHub (karlmarx)
                         |
              +----------+-----------+
              |                      |
         Push to main          GitHub Actions
              |                      |
              v                      v
           Vercel              daily-update.yml
        (auto-deploy)          (karl-infra refresh)
              |
    +---------+---------+---------+
    |         |         |         |
 nwb-plan  nwb-yoga   SIV     SIV-API
    |         |         |         |
    v         v         v         v
nfit.93.fyi nyoga.    id.93   Serverless
            93.fyi    .fyi    Functions
```

## Local Services

```
  Mac Studio M4 Max (36 GB unified memory)
  +--------------------------------------------------------+
  |                                                        |
  |  OpenClaw (Claude Code gateway)                        |
  |    ^                                                   |
  |    | monitors                                          |
  |  openclaw-watchdog (Python/Rich)                       |
  |    +- keeps gateway alive                              |
  |    +- screen awake                                     |
  |    +- Discord notifications                            |
  |                                                        |
  |  claude-pipeline (Python)                              |
  |    +- watches ~/Nextcloud/Documents/inbox/             |
  |    +- routes .md files to OpenClaw sub-agent           |
  |                                                        |
  |  gemini-auto (Playwright)                              |
  |    +- CDP connection to Chrome:9222                    |
  |    +- Gemini UI automation for image gen               |
  |                                                        |
  |  process-monitor-dashboard (Python 3)                  |
  |    +- real-time terminal UI (3 columns)                |
  |    +- monitors background processes                    |
  |    +- tracks Ollama models & VRAM usage                |
  |    +- displays recent Claude sessions                  |
  |    +- refreshes every 5 seconds                        |
  |                                                        |
  |  Ollama (local LLM inference)                          |
  |    +- gemma4:26b (17 GB)                               |
  |    +- gemma4:latest (9.6 GB)                           |
  |    +- llama3.2:1b (1.3 GB)                             |
  |                                                        |
  +--------------------------------------------------------+
```
