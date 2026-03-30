# TrickAdvisor

> A privacy-focused app for rating and reviewing hookup experiences

## Overview

| Field | Value |
|-------|-------|
| **Repos** | [karlmarx/TrickAdvisor](https://github.com/karlmarx/TrickAdvisor) (frontend), [karlmarx/TrickAdvisor-API](https://github.com/karlmarx/TrickAdvisor-API) (backend) |
| **URL** | [ta.93.fyi](https://ta.93.fyi) |
| **Stack** | React (Vite) + Node/Express + Supabase |
| **Hosting** | Vercel (free tier) |
| **Database** | Supabase (Postgres + Auth + Storage) |

## Architecture

- **Frontend**: React SPA built with Vite, deployed to Vercel
- **Backend**: Express API deployed as Vercel Serverless Functions (separate repo)
- **Auth**: Supabase Auth (email/password)
- **Storage**: Supabase Storage for user photos with admin moderation
- **Email**: Notifications on photo approval/rejection (fire-and-forget to avoid function timeout)

## Key Features

- User registration and profiles
- Encounter logging with ratings
- Photo upload with admin moderation pipeline
- Rating subcategories with custom icons (splat/loads scale)

## Open Issues

| # | Title | Priority |
|---|-------|----------|
| [#7](https://github.com/karlmarx/TrickAdvisor/issues/7) | Profile editing: bio, display name, preferences | High |
| [#5](https://github.com/karlmarx/TrickAdvisor/issues/5) | Add mock/seed test data | High |
| [#6](https://github.com/karlmarx/TrickAdvisor/issues/6) | Alternative rating icon: loads scale | Medium |
| [#9](https://github.com/karlmarx/TrickAdvisor/issues/9) | Empty states and loading skeletons | Medium |
| [#10](https://github.com/karlmarx/TrickAdvisor/issues/10) | Post-registration onboarding | Medium |
| [#8](https://github.com/karlmarx/TrickAdvisor/issues/8) | Improve search | Medium |
| [#11](https://github.com/karlmarx/TrickAdvisor/issues/11) | Notifications | Low |
| [#12](https://github.com/karlmarx/TrickAdvisor/issues/12) | Mobile UX improvements | Low |
| [#13](https://github.com/karlmarx/TrickAdvisor/issues/13) | Shareable rating card image | Low |
| [#14](https://github.com/karlmarx/TrickAdvisor/issues/14) | Accessibility audit | Low |
