# DNS & Domain Map

## 93.fyi

**Registrar:** Dynadot
**DNS Provider:** Cloudflare (free tier)

```
93.fyi (Cloudflare nameservers)
|
+-- A/CNAME Records
|   |
|   +-- 93.fyi          CNAME -> cname.vercel-dns.com  (nwb-plan, temporary)
|   +-- nfit.93.fyi     CNAME -> cname.vercel-dns.com  (nwb-plan)
|   +-- nyoga.93.fyi    CNAME -> cname.vercel-dns.com  (nwb-yoga)
|   +-- id.93.fyi       CNAME -> cname.vercel-dns.com  (Social Identity Verification)
|   +-- auto.93.fyi     CNAME -> cname.vercel-dns.com  (auto-dashboard)
|   +-- ortho.93.fyi    CNAME -> cname.vercel-dns.com  (orthoappt)
|
+-- Email Routing (Cloudflare)
    |
    +-- k@93.fyi -> karlmarx9193@gmail.com
```

## Domain Assignments

| Domain | Vercel Project | Repo | Notes |
|--------|---------------|------|-------|
| `93.fyi` (apex) | nwb-plan | karlmarx/nwb-plan | Temporary — may change |
| `nfit.93.fyi` | nwb-plan | karlmarx/nwb-plan | Primary domain for NWB Fitness |
| `nyoga.93.fyi` | nwb-yoga | karlmarx/nwb-yoga | NWB Yoga companion |
| `id.93.fyi` | Social ID Verification | karlmarx/identity-verification | Frontend for Social Identity Verification |
| (public domain) | Social ID Verification | karlmarx/identity-verification | Primary domain (WIP) |
| `auto.93.fyi` | auto-dashboard | karlmarx/karl-infra (subdir: `auto-dashboard/`) | Interactive automation map |
| `ortho.93.fyi` | orthoappt | karlmarx/karl-infra (subdir: `orthoappt/`) | Appointment companion (Dr. Almodovar follow-up, NWB protocol) |

## Email

| Address | Destination | Provider |
|---------|-------------|----------|
| `k@93.fyi` | `karlmarx9193@gmail.com` | Cloudflare Email Routing |

## SSL/TLS

All domains use Cloudflare's Universal SSL (free) with Full (Strict) mode pointing to Vercel's automatic SSL certificates.

## Other Domains

| Domain | Registrar | Use |
|--------|-----------|-----|
| `blazingpaddles.org` | (TBD) | Blazing Paddles pickleball club website |
