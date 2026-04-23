# Mom's Reassurance Hub (mom.93.fyi)

> A personal collection of gentle answers to the everyday things Mom worries about

## Overview

| Field | Value |
|-------|-------|
| **URL** | [mom.93.fyi](https://mom.93.fyi) |
| **Tech** | Next.js 16 + React 19 + TypeScript, Tailwind v4, framer-motion |
| **Hosting** | Vercel (free tier, auto-deploy from main) |
| **Design** | "Letter from your son" aesthetic — Caveat/Lora/Newsreader fonts |
| **Audience** | Mom, an elderly worrier |

## Current Worry Topics

1. Phone hacking vs. ads/notifications
2. VW ID4 AC running when car is off
3. Flight connection anxiety (links to layover.93.fyi)
4. Scam texts/emails recognition
5. Did I leave the stove on?
6. Did I lock the front door?
7. Why is my computer slow?
8. Is this phone call from my bank real?
9. Did I take my medication today?
10. General reassurance ("but what if...?")

## Adding New Worries

Edit `lib/worries.ts` — add a new `Worry` object to the array with:
- `id` (unique slug)
- `category` (from fixed list)
- `question` (what she asks)
- `shortAnswer` (reassuring TL;DR)
- `fullAnswer` (longer explanation, son's voice)
- `stillWorried?` (optional deeper layer)
- `actionLink?` (optional CTA)
- `phoneCall?` (optional tel: link)

Rebuild and push. Auto-deploys.

## Related

- [layover.93.fyi](https://layover.93.fyi) — flight connection tool (linked from Worry #3)
