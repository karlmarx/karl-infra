# Vercel Infrastructure

## Account

- **Plan**: Free (Hobby)
- **All projects**: auto-deploy from `main` branch on GitHub

## Projects

| Vercel Project | Repo | Framework | Domain(s) |
|---------------|------|-----------|-----------|
| nwb-plan | karlmarx/nwb-plan | Other (static HTML) | nfit.93.fyi, 93.fyi |
| nwb-yoga | karlmarx/nwb-yoga | Other (static HTML) | nyoga.93.fyi |
| Identity Verification | karlmarx/identity-verification | React 19 + Vite | id.93.fyi |
| ID API | karlmarx/id-api | Other (Express) | (auto-assigned .vercel.app) |
| blazing-paddles-react | karlmarx/blazing-paddles-react | Vite | blazingpaddles.org |
| auto-dashboard | karlmarx/karl-infra (subdir) | React 19 + Vite | auto.93.fyi |

## Domain Configuration

All custom domains use Cloudflare DNS pointing to Vercel via CNAME records to `cname.vercel-dns.com`. Vercel handles SSL automatically.

## Serverless Functions

- **ID API**: Express app running as Vercel Serverless Functions
  - Email notifications (fire-and-forget pattern to avoid timeout)
  - Photo moderation endpoints
  - All CRUD operations for encounters/ratings

## Build Configuration

| Project | Build Command | Output |
|---------|--------------|--------|
| nwb-plan | (none — static) | `./` |
| nwb-yoga | (none — static) | `./` |
| Identity Verification | `npm run build` | `dist/` |
| ID API | (auto-detected) | `api/` |
| blazing-paddles-react | `npm run build` | `dist/` |

## Notes

- Free tier limits: 100 GB bandwidth/month, 100 hours serverless execution
- Preview deployments enabled on all projects (auto-deploy on PR)
- No environment variables needed for static sites (nwb-plan, nwb-yoga)
- TrickAdvisor/API use Supabase env vars (SUPABASE_URL, SUPABASE_ANON_KEY, etc.)
