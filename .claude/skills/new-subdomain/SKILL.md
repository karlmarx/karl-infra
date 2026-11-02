---
name: new-subdomain
description: Put a static site live on a new *.93.fyi subdomain (e.g. balls.93.fyi) using Cloudflare Workers static assets. Use whenever Karl asks to deploy, publish, or "spin up" a site on a 93.fyi subdomain.
---

# New 93.fyi subdomain (static site)

Default target: **Cloudflare Worker with static assets**. Do not use Vercel for new
static sites: the Vercel connector cannot create projects (403).

## Gotchas (learned the hard way)

- `93.fyi` DNS is on Cloudflare (`sima`/`uriah.ns.cloudflare.com`).
- A **proxied `*.93.fyi` wildcard sits behind Cloudflare Access** (team `9193.cloudflareaccess.com`).
  Any subdomain without its own record shows a login page. A public site needs its own
  custom domain AND an Access bypass (or an Access app for that host with a Bypass/Everyone policy).
- The Cloudflare MCP connector has no DNS, Pages or Worker-deploy tools. Use `wrangler`
  / the REST API with the env vars below.
- New sessions do not remember old ones. Everything must live in the repo + this skill.

## Prerequisites (environment variables)

- `CLOUDFLARE_API_TOKEN`: Workers Scripts Edit (account), Workers Routes Edit + DNS Edit (zone 93.fyi),
  Access: Apps and Policies Edit.
- `CLOUDFLARE_ACCOUNT_ID`

If either is missing, stop and tell Karl to add it in the cloud environment settings
(environment name in the session title bar, then Edit). Never ask for the token in chat.

## Steps

1. **Site repo**: built files in one folder (usually `public/`). Add `wrangler.jsonc` at repo root:
   ```jsonc
   {
     "name": "<sub>-93fyi",
     "compatibility_date": "<today>",
     "assets": { "directory": "./public", "not_found_handling": "404-page" },
     "routes": [{ "pattern": "<sub>.93.fyi", "custom_domain": true }]
   }
   ```
   Security/cache headers go in `public/_headers`, e.g.
   ```
   /*
     X-Content-Type-Options: nosniff
     Referrer-Policy: strict-origin-when-cross-origin
   ```
2. **Deploy**: `npx wrangler@latest deploy` from the repo root. `custom_domain: true` creates
   the DNS record for `<sub>.93.fyi`, which overrides the wildcard.
3. **Access bypass**: check whether the Access app covers `*.93.fyi`:
   `GET /accounts/$CLOUDFLARE_ACCOUNT_ID/access/apps`. If it does, create an Access app for
   `<sub>.93.fyi` with a single policy `decision: "bypass"`, `include: [{"everyone": {}}]`.
4. **Verify**: `curl -sI https://<sub>.93.fyi/` returns `200` (not `302` to cloudflareaccess.com),
   and the page's canonical/og URLs use the new domain.
5. **Record it**: add a row to the "Live Services" table and the "Domain: 93.fyi" table in
   `karl-infra/README.md`, then commit + PR in both repos.

## Report back to Karl

Short summary: live URL, what was created (Worker name, DNS record, Access app), and any
step he must do himself.
