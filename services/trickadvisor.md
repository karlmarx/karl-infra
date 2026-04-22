# Social Identity Verification (SIV)

> A privacy-focused app for rating and verifying social encounters

## Overview

| Field | Value |
|-------|-------|
| **Repos** | [karlmarx/identity-verification](https://github.com/karlmarx/identity-verification) (frontend), [karlmarx/id-api](https://github.com/karlmarx/id-api) (backend) |
| **URL** | [id.93.fyi](https://id.93.fyi) |
| **Stack** | React 19 (Vite) + Node/Express + Supabase |
| **Hosting** | Vercel (free tier) |
| **Database** | Supabase (Postgres + Auth + Storage) |
| **Domain** | id.93.fyi (WIP — public domain TBD) |

## Architecture

### Frontend
- React 19 SPA built with Vite + TypeScript
- Deployed to Vercel with auto-deploy from `main`
- Custom domain: id.93.fyi (Cloudflare DNS → Vercel CNAME)

### Backend
- Express.js API deployed as Vercel Serverless Functions (separate repo: `karlmarx/id-api`)
- CRUD for encounters, ratings, user profiles, and photos
- Supabase integration: Auth, Postgres, and Storage APIs

### Data & Auth
- **Supabase Auth**: Email/password registration, session management
- **Supabase Postgres**: users, profiles, encounters (rating logs), ratings (with photo/timestamp)
- **Supabase Storage**: User-uploaded photos (JPG/PNG) with private ACL; admin review pipeline
- **Email**: Fire-and-forget notifications on photo approval/rejection (avoids function timeout; uses Supabase SMTP or SendGrid)

### Deployment
- Frontend: `vercel --prod` (auto-triggered on `main` push to karlmarx/identity-verification)
- Backend: Vercel Functions (auto-triggered on `main` push to karlmarx/id-api)
- Preview deploys enabled on PRs for both repos

## Key Features

- User registration and profiles
- Encounter logging with ratings
- Photo upload with admin moderation pipeline
- Rating subcategories with custom icons (splat/loads scale)

## Open Issues

| # | Title | Priority |
|---|-------|----------|
| [#7](https://github.com/karlmarx/identity-verification/issues/7) | Profile editing: bio, display name, preferences | High |
| [#5](https://github.com/karlmarx/identity-verification/issues/5) | Add mock/seed test data | High |
| [#6](https://github.com/karlmarx/identity-verification/issues/6) | Alternative rating icon: loads scale | Medium |
| [#9](https://github.com/karlmarx/identity-verification/issues/9) | Empty states and loading skeletons | Medium |
| [#10](https://github.com/karlmarx/identity-verification/issues/10) | Post-registration onboarding | Medium |
| [#8](https://github.com/karlmarx/identity-verification/issues/8) | Improve search | Medium |
| [#11](https://github.com/karlmarx/identity-verification/issues/11) | Notifications | Low |
| [#12](https://github.com/karlmarx/identity-verification/issues/12) | Mobile UX improvements | Low |
| [#13](https://github.com/karlmarx/identity-verification/issues/13) | Shareable rating card image | Low |
| [#14](https://github.com/karlmarx/identity-verification/issues/14) | Accessibility audit | Low |
