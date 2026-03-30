# NWB Yoga

> Non-weight-bearing yoga practice PWA for femoral neck stress fracture protocol

## Overview

| Field | Value |
|-------|-------|
| **Repo** | [karlmarx/nwb-yoga](https://github.com/karlmarx/nwb-yoga) |
| **URL** | [nyoga.93.fyi](https://nyoga.93.fyi) |
| **Stack** | Single-file HTML PWA |
| **Hosting** | Vercel (free tier) |
| **Database** | None (fully client-side) |

## Architecture

- **Single HTML file** — yoga poses with descriptions and animations
- **Service Worker** for offline PWA support
- **No backend** — all content embedded
- Self-contained pose descriptions
- Companion app to nwb-plan (NWB Fitness)
- Shared lotus flower SVG icon with nwb-plan

## Relationship to nwb-plan

Both apps serve the same recovery use case (femoral neck stress fracture, non-weight-bearing phase):
- **nwb-plan**: strength/fitness exercises
- **nwb-yoga**: yoga/flexibility poses

They share the lotus flower SVG icon and similar design language.
