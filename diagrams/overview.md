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
|  progress.93.fyi -------+   Dynadot (.fyi registrar)              |
|  +- Progress Dashboard     Cloudflare (DNS + email routing)      |
|     (status monitor)       GitHub (all repos + Actions)          |
|     + local system polling | Vercel (all deployments)            |
|     + email notifications  |                                     |
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
