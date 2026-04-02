# foodr

> Fast food chain-relative rating app

## Overview

| Field | Value |
|-------|-------|
| **Repo** | [karlmarx/foodr](https://github.com/karlmarx/foodr) |
| **URL** | [foodr-app.vercel.app](https://foodr-app.vercel.app) |
| **Stack** | Next.js 16 + React 19 + TypeScript 6 + Tailwind CSS v4 |
| **Hosting** | Vercel (free tier) |
| **Database** | None (localStorage only) |

## Architecture

- **Next.js 16 App Router** — same stack as nwb-plan
- **No backend** — all state lives in React / localStorage
- **12 supported chains**: McDonald's, Wendy's, Burger King, Taco Bell, Chick-fil-A, Popeyes, Five Guys, In-N-Out, Chipotle, Subway, KFC, Sonic
- Each chain has its own emoji used as the rating icon (chain-relative 1-5 scale)
- A "5/5 at McDonald's" means something different from "5/5 at Five Guys"

## Status

Complete MVP. Built entirely with Claude Code.
