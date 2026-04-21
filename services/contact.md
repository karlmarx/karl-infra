# Contact Form (contact.93.fyi)

> Bot-resistant contact form with CAPTCHA protection and rate limiting

## Overview

| Field | Value |
|-------|-------|
| **URL** | [contact.93.fyi](https://contact.93.fyi) |
| **Repo** | [karlmarx/contact-93fyi](https://github.com/karlmarx/contact-93fyi) (git worktree) |
| **Tech Stack** | Next.js 16 (React 19) + Vite + TypeScript, Vercel Functions |
| **Hosting** | Vercel (free tier, auto-deploy from main) |
| **Database** | Supabase (Postgres) |
| **CAPTCHA** | Cloudflare Turnstile (free tier) |
| **Email** | Resend (transactional) |

## Architecture

### Frontend
- Next.js 16 SPA built with Vite + TypeScript
- Dark gradient UI (slate-900 to slate-800)
- ContactForm component with Turnstile CAPTCHA embedded
- Client-side form validation (name, email, subject, message required)
- States: idle, loading, success, error

### Backend
- Express-like Next.js Route Handler at `/app/api/submit.ts`
- Validates form input on server side
- Extracts client IP (x-forwarded-for with fallback)
- Checks rate limit (5 submissions/hour per IP)
- Verifies Turnstile token via Cloudflare API
- Stores submission in Supabase `contact_submissions` table
- Increments rate limit counter in `rate_limit_log` table
- Sends emails asynchronously (non-blocking fire-and-forget pattern)

### Data & Auth
- **Supabase Auth**: Service role key for server-side ops (no user auth required)
- **Supabase Postgres**:
  - `contact_submissions` (id, name, email, subject, message, ip_address, turnstile_token, user_agent, timestamps)
  - `rate_limit_log` (id, ip_address, submission_count, window_start/end, timestamps)
  - Indexes on email, created_at, ip_address, window_start
- **Cloudflare Turnstile**: CAPTCHA verification endpoint `/siteverify`
- **Resend Email**: Fire-and-forget confirmation (submitter) + notification (admin)

### Deployment
- Frontend: Vercel (auto-deploy on main push)
- Backend: Vercel Serverless Functions (auto-triggered on main push)
- DNS: Cloudflare CNAME (contact.93.fyi → cname.vercel-dns.com)

## Key Features

- Bot-resistant contact form (Turnstile CAPTCHA)
- Rate limiting: 5 submissions per IP per hour
- Confirmation email to submitter (via Resend)
- Notification email to admin (karlmarx9193@gmail.com)
- Form data stored in Supabase with metadata (IP, user agent, CAPTCHA token)
- Client IP extraction (handles Vercel x-forwarded-for headers)
- Graceful error handling (frontend + backend validation)

## Environment Variables

```
NEXT_PUBLIC_SUPABASE_URL=<supabase-project-url>
NEXT_PUBLIC_SUPABASE_ANON_KEY=<anon-key>
SUPABASE_SERVICE_ROLE_KEY=<service-role-key>
NEXT_PUBLIC_TURNSTILE_SITEKEY=<turnstile-site-key>
TURNSTILE_SECRET_KEY=<turnstile-secret-key>
RESEND_API_KEY=<resend-api-key>
ADMIN_EMAIL=karlmarx9193@gmail.com
SUBMITTER_EMAIL_SENDER=noreply@contact.93.fyi
```

## Database Schema

```sql
CREATE TABLE contact_submissions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL,
  email TEXT NOT NULL,
  subject TEXT NOT NULL,
  message TEXT NOT NULL,
  ip_address INET NOT NULL,
  turnstile_token TEXT NOT NULL,
  user_agent TEXT,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE rate_limit_log (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  ip_address INET NOT NULL,
  submission_count INT NOT NULL DEFAULT 1,
  window_start TIMESTAMP WITH TIME ZONE NOT NULL,
  window_end TIMESTAMP WITH TIME ZONE NOT NULL,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  UNIQUE(ip_address, window_start)
);

CREATE INDEX idx_contact_submissions_email ON contact_submissions(email);
CREATE INDEX idx_contact_submissions_created_at ON contact_submissions(created_at);
CREATE INDEX idx_rate_limit_log_ip ON rate_limit_log(ip_address);
CREATE INDEX idx_rate_limit_log_window ON rate_limit_log(window_start);
```

## Monitoring & Logs

- **Form submissions**: Query Supabase `contact_submissions` table
- **Rate limit status**: Check `rate_limit_log` table (rolling 1-hour windows)
- **Email delivery**: Check Resend dashboard for sent/bounced/failed emails
- **Vercel logs**: Function logs at https://vercel.com/dashboard → project → Logs
- **Turnstile**: Monitor CAPTCHA metrics at https://dash.cloudflare.com/ → Turnstile

## Related Services

- **93.fyi**: Root domain (Cloudflare DNS apex)
- **Supabase**: Shared Postgres database for all 93.fyi apps
- **Vercel**: Deployment platform for all 93.fyi frontends
