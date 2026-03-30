# Domain: 93.fyi

## Registration

| Field | Value |
|-------|-------|
| **Domain** | 93.fyi |
| **Registrar** | Dynadot |
| **DNS Provider** | Cloudflare (free tier) |
| **Nameservers** | Cloudflare-assigned |

## DNS Records

| Name | Type | Value | Proxied | Notes |
|------|------|-------|---------|-------|
| `93.fyi` | CNAME | `cname.vercel-dns.com` | Yes | Points to nwb-plan (temporary) |
| `nfit.93.fyi` | CNAME | `cname.vercel-dns.com` | Yes | NWB Fitness PWA |
| `nyoga.93.fyi` | CNAME | `cname.vercel-dns.com` | Yes | NWB Yoga PWA |
| `ta.93.fyi` | CNAME | `cname.vercel-dns.com` | Yes | TrickAdvisor |

## Email Routing

| From | To | Provider |
|------|----|----------|
| `k@93.fyi` | `karlmarx9193@gmail.com` | Cloudflare Email Routing |

Cloudflare Email Routing is free and requires MX + TXT records:
- MX records pointing to Cloudflare's email routing servers
- TXT record for SPF validation

## SSL/TLS

- **Mode**: Full (Strict) on Cloudflare
- Cloudflare provides edge SSL (Universal SSL, free)
- Vercel provides origin SSL (automatic)
- End-to-end encryption: Browser -> Cloudflare (edge SSL) -> Vercel (origin SSL)

## Future Considerations

- Apex domain (`93.fyi`) is temporarily pointing to nwb-plan — may be reassigned
- Could add more subdomains as new services launch
- Consider adding a landing page at `93.fyi` listing all services
