# karl-infra: agent instructions

## Adding a new site on a 93.fyi subdomain

**Default to Vercel.** Use Cloudflare Workers only if the user explicitly asks for it.
Vercel is already linked to GitHub, so a merge to the production branch deploys by
itself. No repo secrets and no GitHub Actions workflow are needed.

1. **Repo:** one repo per site under `karlmarx/`. Commit the static output or
   framework source as usual.
2. **Vercel project:** import the repo into the `karlmarxs-projects` team (Vercel
   dashboard → Add New → Project, or the Vercel MCP tools). Check which branch is
   the production branch, which is usually the repo's default branch. Some repos use
   `master`, not `main`.
3. **Domain:** add `<name>.93.fyi` to the Vercel project.
4. **DNS (Cloudflare zone 93.fyi):** add `CNAME <name> → cname.vercel-dns.com` with
   **proxied OFF (DNS only)**. This matches every other Vercel subdomain.
   - An unproxied record is **public**. The `*.93.fyi` Cloudflare Access login wall
     only applies to proxied hostnames.
   - For a private site, ask the user first. Either proxy the record so the
     wildcard Access app covers it, or use Vercel Deployment Protection.
5. **Verify:** `curl -sS -o /dev/null -w "%{http_code}" https://<name>.93.fyi/`
   returns 200 and not a 302 to `cloudflareaccess.com`.
6. **Bookkeeping (same session):**
   - Add a row to the Live Services table in `README.md`.
   - Add the DNS record to `infra/domain-93fyi.md`.
   - If public, add it to `PUBLIC_LINKS` in `karlmarx/93-fyi`
     `src/app/page.tsx`. That repo's production branch is **`master`**.

## Existing Cloudflare Workers (exceptions, don't copy for new sites)

- `balls-93fyi` (karlmarx/lt-pickleball): deploys with the GitHub Action
  `.github/workflows/deploy.yml`, repo secret `CLOUDFLARE_API_TOKEN`, and
  `wranglerVersion: "4"`. It's public through its own Access bypass app.
- `where-93fyi`: see `infra/where-93fyi.md`.
- The Cloudflare GitHub app ("Workers Builds") can't be installed on this account
  (GitHub 404), so Cloudflare sites can't auto-deploy the way Vercel does.
