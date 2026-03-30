# Claude Pipeline

> File-based prompt pipeline: Claude.ai -> Nextcloud -> OpenClaw sub-agent

## Overview

| Field | Value |
|-------|-------|
| **Repo** | [karlmarx/claude-pipeline](https://github.com/karlmarx/claude-pipeline) (private) |
| **Status** | Scaffolded, testing |
| **Runs On** | Windows 11 workstation |
| **Stack** | Python (watchdog) |

## Purpose

Bridges Claude.ai (browser) with the local OpenClaw gateway. When a user saves a `.md` file from Claude.ai to a Nextcloud-synced inbox folder, this pipeline:

1. Detects the new file via filesystem watcher (watchdog)
2. Parses frontmatter/metadata from the `.md` file
3. Routes the prompt to the appropriate OpenClaw sub-agent
4. Writes the response back to Nextcloud for sync

## Data Flow

```
Claude.ai (browser) -> save .md file
  -> ~/Nextcloud/Documents/inbox/ (synced via Nextcloud)
    -> claude-pipeline (watchdog listener)
      -> parse .md frontmatter
      -> route to OpenClaw sub-agent
        -> execute prompt
        -> write response to Nextcloud
```

## Dependencies

- Nextcloud desktop client (filesystem sync)
- OpenClaw gateway (must be running)
- openclaw-watchdog (keeps OpenClaw alive)
