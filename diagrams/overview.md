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
|  ta.93.fyi          |   |   +- find-hub-tracker                  |
|  +- TrickAdvisor    |   |      +- polls Google Find Hub          |
|     + TA-API        |   |         +- Discord alerts              |
|                     |   |                                         |
|  Supabase (DB) -----+   |   INFRA                                |
|                         |   ------                                |
|  93.fyi ----------------+   Dynadot (.fyi registrar)              |
|  (Cloudflare DNS)           Cloudflare (DNS + email routing)      |
|  k@93.fyi -> Gmail          GitHub (all repos + Actions)          |
|                             Vercel (all deployments)              |
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
 nwb-plan  nwb-yoga   TA      TA-API
    |         |         |         |
    v         v         v         v
nfit.93.fyi nyoga.    ta.93   Serverless
            93.fyi    .fyi    Functions
```

## Local Services

```
  Windows 11 Workstation
  +----------------------------------------------------+
  |                                                    |
  |  OpenClaw (Claude Code gateway)                    |
  |    ^                                               |
  |    | monitors                                      |
  |  openclaw-watchdog (Python/Rich)                   |
  |    +- keeps gateway alive                          |
  |    +- screen awake                                 |
  |    +- Discord notifications                        |
  |                                                    |
  |  claude-pipeline (Python)                          |
  |    +- watches ~/Nextcloud/Documents/inbox/         |
  |    +- routes .md files to OpenClaw sub-agent       |
  |                                                    |
  |  gemini-auto (Playwright)                          |
  |    +- CDP connection to Chrome:9222                |
  |    +- Gemini UI automation for image gen           |
  |                                                    |
  +----------------------------------------------------+
```
