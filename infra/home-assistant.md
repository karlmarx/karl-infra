# Home Assistant (ha.93.fyi)

Unified smart-home control plane. **Status: stalled migration — nothing is actually running.** This doc records what exists today (verified 2026-07-03) and the plan to get a real instance live at `ha.93.fyi`.

## Where the migration actually is

| Artifact | State |
|----------|-------|
| `ha` DNS record in Cloudflare zone `8881c2fb…` | **Exists**, proxied (resolves to CF edge IPs `104.21.45.71` / `172.67.211.16`). One of the undocumented extras noted in [diagrams/domains.md](../diagrams/domains.md). No documented origin — almost certainly falls through to the parking wildcard, same failure mode `workoutgifs.93.fyi` had before 2026-05-24. |
| Cloudflare Access | `https://ha.93.fyi` 302s to `9193.cloudflareaccess.com` login. This is the account-wide wildcard app **`93.fyi Subdomains`** (`*.93.fyi`, see [where-93fyi.md](where-93fyi.md)) doing its job — not an HA-specific app. |
| HA instance / config / container | **Does not exist.** No trace in this repo, no launchd service, no tunnel route. |
| Backlog entries | [STATUS.md](../STATUS.md) item 6: "Evaluate Home Assistant (Pi 4/5 or HA Green $99)" — unchecked. [FUTURE.md](../FUTURE.md): "Home Assistant integration for device tracking." |

So "the migration" = a subdomain was reserved and the idea was written down. Everything else is still to do.

## What it would control (current smart-home inventory)

- **7 WiZ bulbs** on the Deco subnet `192.168.68.x` (`.100`, `.102`–`.106`, `.123`), controlled today by raw UDP (`wiz_lights.py` in the openclaw workspace, port 38899). Works only when the caller is on the home LAN — the documented limitation in [tui-dashboard.md](tui-dashboard.md).
- **WiZ account** still on the old email (STATUS item 6: move to `karlmarx9193@gmail.com`).
- Future per FUTURE.md: device/presence tracking via the HA companion app.

## Plan

### Phase 0 — Cloudflare recon (15 min, no purchases)
- In the CF dashboard, confirm what the `ha` record actually points at and note it here.
- Decide it stays reserved for HA (it should — nothing else claims it).

### Phase 1 — Network prep (the unfinished STATUS #6 tasks)
- [ ] Move the 7 WiZ bulbs onto the target Wi-Fi subnet (STATUS says "Deco → asdfjkl6"; tui-dashboard.md says the bulbs already live on "`asdfjkl` (Deco subnet 192.168.68.x)" — **resolve this naming contradiction first**; the only hard requirement is that the HA host and the bulbs share one L2 network so UDP discovery works).
- [ ] DHCP reservations for all 7 bulbs in the Deco app (WiZ integration is happier with stable IPs).
- [ ] Name the bulbs sensibly in the WiZ app.
- [ ] Migrate WiZ account to `karlmarx9193@gmail.com`.

### Phase 2 — Pick the host and install ($0 constraint — no new hardware)

Karl wants this free, so the host is repurposed from machines already running. The trick in every case is the same: HA needs to sit on the home LAN with a **bridged** (not NAT'd) network interface so WiZ UDP discovery works, and running **HAOS in a VM** (a supported install type) keeps the add-on store — which Phase 4's cloudflared add-on depends on.

(No Mac Studio is available for this — per Karl 2026-07-03. The always-on-Mac references elsewhere in this repo can't host it.)

**Recommendation: Raspberry Pi 4 or 5 (4 GB+), HAOS flashed directly.**
- The Pi is HAOS's first-class, most-supported target: flash the HAOS preset from Raspberry Pi Imager onto an SD card (or better, a USB SSD — SD cards wear out under HA's database writes), Ethernet into the Deco, boot, done. ~30 minutes, ~3 W of power.
- A Pi 3 technically works but is sluggish; 4 GB+ RAM is the comfortable floor.

**Fallback: the old 2018 MacBook — keep macOS, run HAOS in a free UTM VM.**
- Do **not** wipe a 2018 MacBook to bare-metal Linux: T2-chip Macs make Linux installs (SSD/keyboard drivers, Secure Boot) genuinely painful. A UTM VM on macOS sidesteps all of it.
- UTM (free) runs the official HAOS x86-64 image virtualized; use "Bridged (Advanced)" networking so the VM sits directly on the Deco subnet (UTM's vmnet bridging generally works over Wi-Fi; Ethernet dongle if it doesn't). 2 GB RAM / 32 GB disk.
- Housekeeping: lid-closed operation on AC power, disable sleep (`caffeinate` LaunchAgent or Amphetamine), auto-start the VM on login. Battery doubles as a free UPS.
- HA backups restore across hosts in minutes, so starting on the MacBook and hopping to a Pi later (or vice versa) is cheap.

Third choice only if neither is on hand: **Windows 11 workstation**, HAOS x86 VM in Hyper-V (external/bridged switch) or VirtualBox — works, but that box's role is being wound down (WSL-migration backlog), so don't build on it.

Not viable, for the record: Docker on macOS (bridge/NAT — and even its newer host-networking mode is TCP-only — breaks WiZ UDP discovery) and HA Core in a venv (least-supported install, no add-on store, another pet process).

Install → onboard at `http://homeassistant.local:8123` → create the owner account → set up the built-in backup schedule immediately (nightly, keep 7) so the instance can hop hosts later.

### Phase 3 — Integrations
1. **WiZ** — auto-discovered once host and bulbs share a subnet; adopt all 7, name to match Phase 1.
2. **Mobile companion app** on Karl's phone → gives the FUTURE.md "device tracking" (presence, battery, location) for free.
3. Optional later: TP-Link Deco integration (router-based presence), HomeKit bridge.

### Phase 4 — Expose as ha.93.fyi
1. Install the **Cloudflared add-on** in HAOS; create a named tunnel and route `ha.93.fyi` → `http://localhost:8123`. This replaces/repoints the stale `ha` DNS record (the add-on provisions the CNAME).
2. Set `http.use_x_forwarded_for` + `trusted_proxies` for Cloudflare ranges in `configuration.yaml` (HA rejects proxied logins otherwise).
3. Keep the wildcard `93.fyi Subdomains` Access app gating it — web access then has zero-trust login in front of HA's own auth. Do **not** create a Bypass app like where.93.fyi; this is an admin surface.
4. **Companion-app caveat**: the mobile app can't drive the CF Access browser login on every reconnect. Options, in order of preference: (a) internal URL = `http://homeassistant.local:8123` on home Wi-Fi + Tailscale for remote (already in the stack — dev-setup uses it), (b) a CF Access **service token** policy on an exact-hostname `ha.93.fyi` app with the token headers configured in the app. Decide when Phase 4 lands.

### Phase 5 — Migrate existing consumers off raw UDP
- Point `wiz_lights.py` callers (openclaw workspace, both Windows and Mac copies) at the HA REST API (`POST /api/services/light/turn_on`, long-lived access token) instead of UDP broadcast — this makes light control work from anywhere, not just the home LAN.
- tui-dashboard 💡 Lights panel: wire to HA's API instead of `192.168.68.255:38899` (fixes its documented remote-access limitation).
- Later: a lights card on command.93.fyi `/control`.

### Phase 6 — Documentation close-out (when live)
- [ ] Row for `ha.93.fyi` in [domain-93fyi.md](domain-93fyi.md) + [diagrams/domains.md](../diagrams/domains.md)
- [ ] Mac-Studio-adjacent entry in [ARCHITECTURE.md](../ARCHITECTURE.md) hardware section
- [ ] Check off STATUS.md item 6; move FUTURE.md line to done
- [ ] Node + edges in `auto-dashboard/src/data/automations.ts`

## Open questions

- **Subnet naming**: is "asdfjkl6" a distinct SSID from the Deco's "asdfjkl", or the same network? Phase 1 blocks on this.
- **Hardware on hand**: which Pi is it (3 vs 4/5, RAM size)? Pi 4/5 with 4 GB+ → flash HAOS directly. Only a Pi 3 or no Pi → MacBook UTM path.
- What does the `ha` record currently point at (Phase 0)?

## Cross-references

- [domain-93fyi.md](domain-93fyi.md), [diagrams/domains.md](../diagrams/domains.md) — zone state
- [where-93fyi.md](where-93fyi.md) — how the wildcard Access app + exact-hostname exceptions work
- [tui-dashboard.md](tui-dashboard.md) — current WiZ UDP control + its limitations
- [../STATUS.md](../STATUS.md) item 6, [../FUTURE.md](../FUTURE.md) — original backlog entries
