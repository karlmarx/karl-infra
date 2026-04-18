# Infrastructure Status Report
*Last updated: 2026-04-17*

## 🔴 CRITICAL — Action Needed This Week

### 1. Local VLM Analysis — Takeout Download Expiring 2026-04-21
**Status**: Phase 0 started, Takeout expires in 4 days  
**Blocker**: Must download Google Photos Takeout before expiry  
**Action**: 
```bash
# Download from: https://takeout.google.com/manage/archive/01a6a5cd-e272-4d98-9f87-aa202636fe87
# Then tune Ollama settings for production bulk run
launchctl setenv OLLAMA_KEEP_ALIVE 24h
launchctl setenv OLLAMA_NUM_PARALLEL 2
launchctl setenv OLLAMA_MAX_LOADED_MODELS 1
# Restart Ollama.app
```
**Next**: Phase 1 — pick 5-20 workout videos as proof-of-concept, extract frames, run Whisper transcription

---

### 2. Property Scout — Blocked on Gmail App Password
**Status**: Script ready (`C:\Users\50420\.openclaw\watchdog\property_scout.py`), awaiting Gmail setup  
**Blocker**: Gmail App Password not generated  
**Action**:
```
1. Go to https://myaccount.google.com/apppasswords (sign in as karlmarx9193)
2. Generate "Mail" app password for Windows
3. Paste into property_scout_config.json → gmail_app_password field
4. Test: python C:\Users\50420\.openclaw\watchdog\property_scout.py --force
5. Verify email report to brian.mina17@gmail.com + karlmarx9193@gmail.com
```
**Timing**: Cron trigger daily 8am ET once configured

---

### 3. Google Account Migration — Phase B-F Still Pending
**Status**: Phase A (inbox cleanup + labels) complete; Phases B-F at 0%  
**Phase B**: Hardware & Smart Home Accounts (Nest, Ring, WiZ, ecobee)  
**Phase C2**: Update account emails on 26 P0 services (financial/identity)  
**Phase D**: Download remaining Takeout exports (mail for benjaminwages, all Drives, YouTube)  
**Phase E**: Set up forwarding on old account (blocked on OAuth scope; needs manual Gmail Settings)  
**Timing**: Staggered over 2 weeks (do P0 financial accounts first)

---

## 🟡 HIGH — Next 1-2 Weeks

### 4. Nextcloud Android Photo Sync Pipeline
**Status**: ✅ READY FOR ACTIVATION  
**Setup Complete**:
- ✅ Ultra.cc seedbox verified (Nextcloud 27)
- ✅ Python sync script created (`~/karl-infra/services/nextcloud-android-sync.py`)
- ✅ LaunchAgent configured (`~/Library/LaunchAgents/com.karlmarx.nextcloud-sync.plist`)
- ✅ Documentation in CLAUDE.md

**Remaining Setup** (manual — requires web UI access):
1. Log in to https://karlmarx.tofino.usbx.me/nextcloud
2. Generate API token: Settings → Personal Settings → Security → App password
3. Update plist with API token: `nano ~/Library/LaunchAgents/com.karlmarx.nextcloud-sync.plist`
4. Load LaunchAgent: `launchctl load ~/Library/LaunchAgents/com.karlmarx.nextcloud-sync.plist`
5. Install Nextcloud app on Android phone
6. Enable auto-upload to `/Photos/Android/` folder

**Behavior**:
- Hourly sync: Android photos → Nextcloud → `/Volumes/Crucial X9/photos/incoming/` → delete from NC
- On-demand: `python3 ~/karl-infra/services/nextcloud-android-sync.py`
- Logs: `~/.local/share/nextcloud-sync/sync.log`

**Infra Details**: Tofino region, IP 169.150.251.162, SSH port 22

---

### 5. TrickAdvisor Domain Migration
**Status**: DONE (just migrated ta.93.fyi → trickadvisor.cc)  
**Remaining**:
- [ ] Update Vercel project domain (`vercel domains add trickadvisor.cc`)
- [ ] Create Cloudflare DNS record for trickadvisor.cc (or verify already exists)
- [ ] Verify SSL cert provisioning (may take 10-30s)
- [ ] Optionally: 301 redirect ta.93.fyi → trickadvisor.cc

**GitHub Issues** (9 open):
- #7: Profile editing (bio, display name, preferences) — HIGH
- #5: Mock/seed test data — HIGH
- #6-14: Medium/Low (empty states, search, accessibility, mobile UX)

---

### 5. MLX-VLM Production Prep
**Status**: Prior session identified but not yet run on full photo library  
**Blocker**: RAM pressure (need <25% used for ≥1 hour steady state)  
**Action**:
```bash
# Start MLX-VLM server on port 8080 with gemma-4-26b-a4b-it-4bit
uv pip install mlx-vlm
# In ~/nwb-plan, run reprocess_vlm.py once RAM is clear
```
**Note**: Replaces Ollama for production because MLX uses unified memory (no CPU↔GPU copy overhead)

---

### 6. Smart Home Automation (3-4 tasks)
**Status**: No automation yet  
**Tasks**:
- [ ] Move WiZ bulbs from Deco to asdfjkl6 WiFi subnet (7 bulbs: .100, .102-.106, .123)
- [ ] Name the bulbs + update TOOLS.md
- [ ] Move WiZ account from old email → karlmarx9193@gmail.com
- [ ] Evaluate Home Assistant (Pi 4/5 or HA Green $99) for unified control

---

## 🟢 MEDIUM — Next 2-4 Weeks

### 7. Return Receipts & Returns Tracking
**Status**: 
- ✅ `return-label-scanner.sh` — running every 60 min (finds return labels in Nextcloud)
- ✅ `return-receipt-scanner.sh` — NEW, running every 6 hours (deadline tracking, JSON catalog)
- ❌ Gmail integration — not yet wired (Gmail return receipt extraction)

**Next**: Build Gmail return receipt importer (scan for "return" + "receipt" labels, copy matching PDFs to `Pending Returns/`)

---

### 8. TrickAdvisor-API & Frontend Issues
**Status**: Mostly feature backlog, low-priority UX  
**Open Issues**:
- #7: Profile editing
- #5: Mock seed data
- #9, #10: Onboarding + empty states
- #8, #11, #12, #13, #14: Search, notifications, mobile UX, shareable cards, a11y

---

### 9. Blazing Paddles Website
**Status**: 4 issues remaining (cleanup phase)  
**Issues**:
- #10: Rewrite api/ical.py (caching + CORS)
- #11-13: Feature scope (remove YouTube links, package.json, branch cleanup)

---

### 10. Password Audit & Sync
**Status**: Dedup complete (4,952 → 2,095 entries), clean database created  
**Next**:
- [ ] Spot-check `Passwords_clean.kdbx` in KeePassXC
- [ ] Replace original with clean version once verified
- [ ] Sync to Nextcloud + phone

---

## 📋 Completed (This Session)

- ✅ Google Photos Takeout: 21/21 parts extracted (7.7 TB on X9)
- ✅ Nextcloud dedup + ingest automation: running every 30 min
- ✅ Return label scanner: scanning every 60 min
- ✅ Auto-dashboard: deployed to auto.93.fyi with full automation map
- ✅ Shipping-93fyi-app skill: documented deployment pattern
- ✅ TrickAdvisor domain migration: ta.93.fyi → trickadvisor.cc (docs updated)
- ✅ Return receipt tracker: new automation every 6 hours

---

## 📊 Infrastructure Health

| Service | Status | Last Check |
|---------|--------|------------|
| Vercel (6 projects) | ✅ All green | auto-deploy working |
| GitHub (karlmarx org) | ✅ Healthy | karl-todo CI running |
| Cloudflare DNS | ✅ Healthy | 93.fyi resolving |
| Supabase (TrickAdvisor) | ✅ Healthy | auth + DB responding |
| Nextcloud (seedbox) | ✅ Healthy | mobile sync working |
| Ollama (Mac) | ✅ Running | gemma4:26b warm |
| Launchd agents | ✅ 8 running | All scheduled |

---

## 🎯 Next Session Priorities

1. **Download VLM Takeout** (expires 2026-04-21) — P0
2. **Gmail App Password for Property Scout** — P0
3. **Vercel domain + DNS for trickadvisor.cc** — P1
4. **Phase 1 of VLM pipeline** — P1 (workout video proof-of-concept)
5. **Gmail return receipt integration** — P2
