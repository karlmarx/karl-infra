// Karl's infrastructure automation graph — source of truth for the dashboard.
// Edit this file to add / remove / tweak nodes and edges. The App layer renders
// whatever is declared here.

export type Category =
  | 'vercel'
  | 'local'
  | 'seedbox'
  | 'gha'
  | 'infra'
  | 'windows'
  | 'self';

export type Group =
  | 'mac-studio'
  | 'vercel'
  | 'seedbox'
  | 'windows'
  | 'gha'
  | 'infra';

export interface AutomationNode {
  id: string;
  label: string;
  sublabel?: string;
  category: Category;
  group: Group;
  description: string;
  schedule?: string;
  script?: string;
  url?: string;
  repo?: string;
  stack?: string;
  notes?: string[];
  /** Position on the canvas — laid out by hand for readability. */
  position: { x: number; y: number };
}

export interface AutomationEdge {
  id: string;
  source: string;
  target: string;
  label?: string;
  animated?: boolean;
}

export interface GroupBox {
  id: Group;
  label: string;
  sublabel?: string;
  /** Bounding box in canvas coordinates; nodes inside should have positions
   * that render inside this box for visual grouping. */
  x: number;
  y: number;
  width: number;
  height: number;
  category: Category;
}

// ---------------------------------------------------------------------------
// Group containers (rendered as background rectangles behind the graph)
// ---------------------------------------------------------------------------

export const groups: GroupBox[] = [
  {
    id: 'mac-studio',
    label: 'Mac Studio M4 Max',
    sublabel: 'launchd agents · 36 GB · local AI',
    x: 40,
    y: 40,
    width: 560,
    height: 960,
    category: 'local',
  },
  {
    id: 'seedbox',
    label: 'Ultra.cc Seedbox',
    sublabel: 'karlmarx.tofino.usbx.me',
    x: 660,
    y: 40,
    width: 380,
    height: 360,
    category: 'seedbox',
  },
  {
    id: 'windows',
    label: 'Windows 11 Workstation',
    sublabel: 'secondary · AI gateway',
    x: 660,
    y: 440,
    width: 380,
    height: 380,
    category: 'windows',
  },
  {
    id: 'gha',
    label: 'GitHub Actions',
    sublabel: 'karlmarx org · cron workflows',
    x: 1100,
    y: 40,
    width: 360,
    height: 260,
    category: 'gha',
  },
  {
    id: 'vercel',
    label: 'Vercel + CF Workers',
    sublabel: 'free tier · public deploys',
    x: 1100,
    y: 340,
    width: 360,
    height: 850,
    category: 'vercel',
  },
  {
    id: 'infra',
    label: 'Infrastructure Layer',
    sublabel: 'DNS · auth · storage · registrars',
    x: 40,
    y: 700,
    width: 1000,
    height: 220,
    category: 'infra',
  },
];

// ---------------------------------------------------------------------------
// Nodes
// ---------------------------------------------------------------------------

export const nodes: AutomationNode[] = [
  // ---------- Mac Studio ----------
  {
    id: 'phone',
    label: 'Android Phone',
    sublabel: 'Nextcloud mobile app',
    category: 'local',
    group: 'mac-studio',
    description:
      'Auto-uploads photos + screenshots to the Nextcloud server on the seedbox. Also the entry point for return-label screenshots.',
    notes: [
      'Instant-upload folder syncs on mobile data + Wi-Fi',
      'Screenshots land in InstantUpload/Screenshots',
    ],
    position: { x: 80, y: 100 },
  },
  {
    id: 'nextcloud-local',
    label: 'Nextcloud (Mac)',
    sublabel: '~/Library/CloudStorage/Nextcloud-…/',
    category: 'local',
    group: 'mac-studio',
    description:
      'Desktop Nextcloud client mirrors the seedbox Nextcloud to the Mac. Upstream for every local ingest script.',
    notes: ['Desktop app keeps a live two-way sync', 'Actual path is under ~/Library/CloudStorage'],
    position: { x: 320, y: 100 },
  },
  {
    id: 'ingest',
    label: 'Nextcloud Photo Ingest',
    sublabel: 'launchd · every 30 min',
    category: 'local',
    group: 'mac-studio',
    description:
      'rclone move from Nextcloud into the bulk photo archive on the X9 SSD. Deduplicates against a 196K-file index built from Google Takeout so nothing gets double-ingested.',
    schedule: 'every 30 min',
    script: '~/bin/nextcloud-ingest.sh',
    notes: [
      'rclone move, not copy — cleans up the phone side after ingest',
      'Dedup uses SHA index from Google Takeout (196K files)',
      'Destination: /Volumes/Crucial X9/photos/incoming/',
    ],
    position: { x: 80, y: 240 },
  },
  {
    id: 'return-scan',
    label: 'Return Label Scanner',
    sublabel: 'launchd · every 60 min',
    category: 'local',
    group: 'mac-studio',
    description:
      'Watches three Nextcloud folders for return-label filenames, copies matches into a single "Pending Returns" folder so Karl never loses a label.',
    schedule: 'every 60 min',
    script: '~/bin/return-label-scanner.sh',
    notes: [
      'Sources: InstantUpload/Screenshots, Documents/Returnsfromphone, claude-pipeline/inbox',
      'Copies (not moves) to Documents/Pending Returns/',
    ],
    position: { x: 320, y: 240 },
  },
  {
    id: 'return-receipt-scan',
    label: 'Return Receipt Tracker',
    sublabel: 'launchd · every 6 hours',
    category: 'local',
    group: 'mac-studio',
    description:
      'Scans Nextcloud for return receipts (PDFs) and tracks return deadlines by store. Maintains JSON catalog with deadline warnings (7-day look-ahead).',
    schedule: 'every 6 hours',
    script: '~/bin/return-receipt-scanner.sh',
    notes: [
      'Scans: Documents/Pending Returns/, Gmail (via rclone sync to local)',
      'Output: ~/Nextcloud/Documents/returns-tracking.json',
      'Patterns: return, rma, refund, shipping.?label, *.pdf',
      '7-day deadline alerts logged to stdout',
    ],
    position: { x: 200, y: 360 },
  },
  {
    id: 'x9',
    label: 'X9 SSD Archive',
    sublabel: '/Volumes/Crucial X9 · 1.1 TB · 196K files',
    category: 'local',
    group: 'mac-studio',
    description:
      'External SSD holding the Google Photos Takeout archive plus all new ingested photos. All VLM inference reads from here.',
    notes: ['Google Photos archive: 1.1 TB, 196K files', 'Takeout expires 2026-04-21'],
    position: { x: 80, y: 380 },
  },
  {
    id: 'ollama',
    label: 'Ollama VLM Inference',
    sublabel: 'gemma4:26b · gemma4:latest · llama3.2:1b',
    category: 'local',
    group: 'mac-studio',
    description:
      'Local vision-language inference over the photo archive. MLX-VLM is preferred for production runs; Ollama is the quick-test / fallback path.',
    notes: [
      'gemma4:26b (17 GB) — solo model, best quality',
      'gemma4:latest (9.6 GB, 12B A2B) — bulk workloads',
      'llama3.2:1b — tiny, fast smoke tests',
      'RAM-aware: 4 GB safety margin, pauses under memory pressure',
    ],
    position: { x: 320, y: 380 },
  },
  {
    id: 'catalog',
    label: 'SQLite Catalog',
    sublabel: 'SSD-local · Nextcloud snapshots',
    category: 'local',
    group: 'mac-studio',
    description:
      'VLM output catalog: one row per media file with tags, captions, embeddings. Lives on SSD; periodic snapshots published to Nextcloud for cross-device query.',
    notes: ['Queryable indices snapshot to Nextcloud', 'Raw output files stay on SSD'],
    position: { x: 200, y: 520 },
  },
  {
    id: 'command-agent',
    label: 'command-agent',
    sublabel: 'FastAPI · always-on · JSON for command.93.fyi',
    category: 'local',
    group: 'mac-studio',
    description:
      'FastAPI service exposing local Mac Studio data (process status, RAM, log tails, voice corpus state, openclaw runs, .remember/ memory) as JSON over a Cloudflare tunnel. Consumed by command.93.fyi.',
    script: '~/karl-infra/services/command-agent/ (planned)',
    notes: [
      'Endpoints: /stats, /pipelines, /voices, /memory, /openclaw, /repos, /timeline',
      'launchd-managed, restarts on boot',
      'RAM-aware: refuses to start heavy actions when free RAM <1GB',
    ],
    position: { x: 440, y: 520 },
  },
  {
    id: 'nextcloud-android-sync',
    label: 'nextcloud-android-sync',
    sublabel: 'hourly · DEAD (EX_CONFIG)',
    category: 'local',
    group: 'mac-studio',
    description:
      'Hourly WebDAV poll of Nextcloud /InstantUpload/Camera/ → /Volumes/Crucial X9/photos/incoming/. Deletes source after download. Currently dead since 2026-04-22 — bad uv path + placeholder password in plist.',
    schedule: 'hourly (3600s)',
    script: '~/karl-infra/services/nextcloud-android-sync.py',
    notes: [
      'Bug: plist uses /opt/homebrew/bin/uv — actual is /Users/kmx/.local/bin/uv',
      'Bug: NEXTCLOUD_PASSWORD env var is placeholder 12345678aA',
      'EX_CONFIG triggers sticky backoff; needs unload+load, not kickstart',
      'See infra/nextcloud-android-sync.md',
    ],
    position: { x: 440, y: 240 },
  },
  {
    id: 'screenshot-parser',
    label: 'screenshot-parser',
    sublabel: 'hourly · MLX-VLM classify · DEAD',
    category: 'local',
    group: 'mac-studio',
    description:
      'Hourly poll of Nextcloud /InstantUpload/Screenshots/. MLX-VLM classifies into return_label / receipt / warranty / ticket / deadline / other, files by category on X9, appends Todoist tasks via karl-todo mirror. Same plist bugs as nextcloud-android-sync.',
    schedule: 'hourly (3600s)',
    script: '~/karl-infra/services/nextcloud-screenshot-parser.py',
    notes: [
      'Spawns mlx_vlm.generate cold per screenshot — should migrate to shared :8080',
      'See infra/nextcloud-screenshot-parser.md',
    ],
    position: { x: 440, y: 360 },
  },
  {
    id: 'mlx-vlm-8080',
    label: 'MLX-VLM :8080',
    sublabel: 'Qwen3.5-27B-4bit · watched',
    category: 'local',
    group: 'mac-studio',
    description:
      'Heavy analysis MLX-VLM server. Watchdog config = gemma-4-26b-4bit; live process as of 2026-04-26 = Qwen3.5-27B-4bit. Restarted by mac-watchdog.sh on death (RAM-gated).',
    notes: [
      'Watchdog hardcodes MLX_VLM_MODEL — must match openclaw.json primary',
      'Used by openclaw, workout_watcher, photo-memory, local-vlm-analysis',
    ],
    position: { x: 80, y: 640 },
  },
  {
    id: 'mlx-vlm-8081',
    label: 'MLX-VLM :8081',
    sublabel: 'Qwen3.5-9B-4bit · NOT watched',
    category: 'local',
    group: 'mac-studio',
    description:
      'Fast chat MLX-VLM server. 32k ctx. Currently the openclaw default chat model. Silent failure if it dies — not in watchdog scope.',
    notes: ['Restart manually: nohup mlx_vlm.server --model <id> --port 8081 &'],
    position: { x: 260, y: 640 },
  },
  {
    id: 'mlx-vlm-8082',
    label: 'MLX-VLM :8082',
    sublabel: 'Qwen3.5-9B 262k · DOWN',
    category: 'local',
    group: 'mac-studio',
    description:
      'Long-context reasoning server. 262k ctx. Currently NOT running (audit 2026-04-26). Silent failure mode — not in watchdog scope.',
    notes: ['Was up briefly today; restart manually if needed'],
    position: { x: 440, y: 640 },
  },
  {
    id: 'local-vlm-analysis',
    label: 'local-vlm-analysis',
    sublabel: 'library · 3-layer Gemma pipeline',
    category: 'local',
    group: 'mac-studio',
    description:
      '3-layer Gemma pipeline (triage → universal → workout) shared by workout_watcher and photo-memory. DuckDB index. Routes to MLX-VLM :8080.',
    repo: '~/projects/local-vlm-analysis/',
    notes: [
      'Schemas in schemas.py',
      'Image bytes never leave local worker',
      'See infra/local-vlm-analysis.md',
    ],
    position: { x: 80, y: 760 },
  },
  {
    id: 'photo-memory',
    label: 'Photo Memory',
    sublabel: 'phase 1: SHA256 dedupe',
    category: 'local',
    group: 'mac-studio',
    description:
      'Local VLM pipeline over Google Takeout (1.1 TB, ~125K unique items). Phase 1 (dedupe) written; phases 2-4 (VLM analysis, curation, photos.93.fyi worker) designed only.',
    schedule: 'manual (planned: launchd + .pause touch-file)',
    script: '~/photo-memory/indexer/phase1_dedupe.py',
    repo: 'karlmarx/photo-memory',
    notes: [
      'Source: /Volumes/Crucial X9/google-takeout-2026-04-16/ (expires 2026-04-21!)',
      'Catalog target: /Volumes/Crucial X9/photo-memory/catalog.db',
      'Future: photos.93.fyi (D1 + R2, GitHub OAuth, Tailscale byte server)',
    ],
    position: { x: 260, y: 760 },
  },
  {
    id: 'gemini-cli',
    label: 'Gemini CLI',
    sublabel: 'OAuth · 5 MCP extensions',
    category: 'local',
    group: 'mac-studio',
    description:
      'Google\'s interactive Gemini CLI. Secondary AI assistant alongside Claude Code, scoped per project via ~/.gemini/projects.json.',
    notes: [
      'Active account: karlmarx9193@gmail.com (OAuth, no API key)',
      'Extensions: chrome-devtools-mcp, github, google-workspace, uv-mcp, youtube-to-docs',
      'Distinct from gemini-auto (UI automation) and openclaw "google" provider (API key)',
    ],
    position: { x: 440, y: 760 },
  },

  // ---------- Seedbox ----------
  {
    id: 'nextcloud-server',
    label: 'Nextcloud Server',
    sublabel: 'karlmarx.tofino.usbx.me/nextcloud',
    category: 'seedbox',
    group: 'seedbox',
    description:
      'Ultra.cc-managed Nextcloud 27 subpath install. The authoritative sync point for phone uploads and todo.md mirroring.',
    url: 'https://karlmarx.tofino.usbx.me/nextcloud/',
    notes: ['Receives phone uploads', 'Receives todo.md from karl-todo CI'],
    position: { x: 700, y: 120 },
  },
  {
    id: 'find-hub',
    label: 'find-hub-tracker',
    sublabel: 'planned · Google Find Hub → Discord',
    category: 'seedbox',
    group: 'seedbox',
    description:
      'Planned always-on poller for Google Find Hub API. Watches device location / battery and fires Discord alerts on anomalies.',
    notes: ['Not yet deployed', 'Will run on seedbox for always-on availability'],
    position: { x: 700, y: 260 },
  },

  // ---------- Windows ----------
  {
    id: 'openclaw',
    label: 'OpenClaw',
    sublabel: 'Claude Code gateway · Node.js',
    category: 'windows',
    group: 'windows',
    description:
      'AI assistant gateway running on the Windows workstation. Receives tasks from the claude-pipeline watcher and from direct remote triggers.',
    notes: [
      'Workspace: ~/.openclaw/workspace/',
      'Plaintext creds in ~/.openclaw/openclaw.json — pending migration',
    ],
    position: { x: 700, y: 500 },
  },
  {
    id: 'openclaw-watchdog',
    label: 'openclaw-watchdog',
    sublabel: 'Python · Rich + Playwright',
    category: 'windows',
    group: 'windows',
    description:
      'Keeps OpenClaw alive and the Windows screen awake. Monitors for crashes and restarts OpenClaw if it dies.',
    position: { x: 700, y: 620 },
  },
  {
    id: 'claude-pipeline',
    label: 'claude-pipeline',
    sublabel: 'Python · inbox watcher',
    category: 'windows',
    group: 'windows',
    description:
      'Watches Nextcloud/inbox/*.md on the Windows side; when a markdown file lands, routes it into OpenClaw as a task.',
    notes: ['Inbox: ~/Nextcloud/claude-pipeline/inbox/'],
    position: { x: 880, y: 500 },
  },
  {
    id: 'gemini-auto',
    label: 'gemini-auto',
    sublabel: 'Playwright/CDP · 3-account rotation',
    category: 'local',
    group: 'mac-studio',
    description:
      'On-demand Python script that drives Gemini\'s image-gen UI over Chrome DevTools Protocol, rotating across 3 Google accounts at 40 images/day each. Originally a Windows tool; ported to Mac (hardcoded C:\\Users\\50420\\... constants still in source).',
    script: '~/gemini-auto/gemini_auto.py',
    notes: [
      'Chrome :9222 primary, Edge :9224/:9225 fallback',
      'Queues to queued_prompts.txt when all accounts hit daily cap',
    ],
    position: { x: 80, y: 880 },
  },

  // ---------- GitHub Actions ----------
  {
    id: 'karl-todo',
    label: 'karl-todo sync',
    sublabel: 'cron · every 15 min',
    category: 'gha',
    group: 'gha',
    description:
      'Todoist is the source of truth. Every 15 min, CI pulls the karl-todo project → regenerates todo.md → commits with [skip ci] → mirrors to Nextcloud. Push to main additionally runs a forward sync (md → Todoist) as an escape hatch for bulk edits.',
    schedule: '*/15 * * * *',
    repo: 'karlmarx/karl-todo',
    notes: [
      'Forward sync is additive-only — removing a line does NOT delete',
      'Secrets: TODOIST_API_TOKEN, NEXTCLOUD_URL, NEXTCLOUD_USER, NEXTCLOUD_APP_PASSWORD',
    ],
    position: { x: 1140, y: 110 },
  },
  {
    id: 'karl-infra-update',
    label: 'karl-infra daily',
    sublabel: 'cron · docs refresh',
    category: 'gha',
    group: 'gha',
    description:
      'Refreshes infrastructure docs from upstream sources (Vercel project list, package versions, etc.) so the infra repo stays in sync with reality.',
    repo: 'karlmarx/karl-infra',
    position: { x: 1140, y: 230 },
  },

  // ---------- Vercel apps ----------
  {
    id: 'v-nfit',
    label: 'nfit.93.fyi',
    sublabel: 'nwb-plan · Next.js 16 + Claude API',
    category: 'vercel',
    group: 'vercel',
    description:
      'Workout planner, client-side state. Uses the Claude API for plan generation.',
    url: 'https://nfit.93.fyi',
    stack: 'Next.js 16, React 19, TypeScript, Claude API',
    notes: ['Also serves root 93.fyi'],
    position: { x: 1140, y: 400 },
  },
  {
    id: 'v-nyoga',
    label: 'nyoga.93.fyi',
    sublabel: 'nwb-yoga · React 18 + Vite',
    category: 'vercel',
    group: 'vercel',
    description: 'Yoga flow visualizer. Canvas animations, no backend.',
    url: 'https://nyoga.93.fyi',
    stack: 'React 18, Vite, Canvas',
    position: { x: 1140, y: 490 },
  },
  {
    id: 'v-wip-siv',
    label: 'WIP Social ID Verification',
    sublabel: 'Private project · in development',
    category: 'vercel',
    group: 'vercel',
    description:
      'Private project in active development. Supabase-backed (Postgres + Auth + Storage). For info: contact via the contact form.',
    stack: 'React 19 + Vite + TypeScript, Supabase',
    notes: ['Project is under NDA', 'Contact via /contact for inquiries'],
    position: { x: 1140, y: 580 },
  },
  {
    id: 'v-foodr',
    label: 'foodr-app.vercel.app',
    sublabel: 'foodr · Next.js 16',
    category: 'vercel',
    group: 'vercel',
    description: 'Recipe / meal tracker, localStorage-backed.',
    url: 'https://foodr-app.vercel.app',
    stack: 'Next.js 16, React 19, TypeScript',
    position: { x: 1140, y: 670 },
  },
  {
    id: 'v-paddles',
    label: 'blazingpaddles.org',
    sublabel: 'blazing-paddles-react',
    category: 'vercel',
    group: 'vercel',
    description:
      'Pickleball site. Feature tracker lives in GitHub Issues on karlmarx/blazing-paddles-react.',
    url: 'https://blazingpaddles.org',
    stack: 'React (Vite)',
    position: { x: 1140, y: 760 },
  },
  {
    id: 'v-auto',
    label: 'auto.93.fyi',
    sublabel: 'THIS DASHBOARD · React + Vite',
    category: 'self',
    group: 'vercel',
    description:
      'The page you are currently looking at. Self-referential node. Built with React 19, Vite, @xyflow/react, Tailwind. Deploys as a static SPA.',
    url: 'https://auto.93.fyi',
    repo: 'karlmarx/karl-infra (auto-dashboard/)',
    stack: 'React 19, Vite, TypeScript, @xyflow/react, Tailwind 4',
    notes: ['You are here'],
    position: { x: 1140, y: 850 },
  },
  {
    id: 'v-command',
    label: 'command.93.fyi',
    sublabel: 'Command Center · Next.js 16 + Tailwind 4',
    category: 'vercel',
    group: 'vercel',
    description:
      'Karl\'s daily-driver dashboard. Three routes: / (Today + Status, read-only), /control (buttons + toggles, typed-confirm modal), /explore (photos, voices, memory, activity timeline). Gated by Cloudflare Access. Pulls local data from the Mac Studio FastAPI command-agent via Cloudflare tunnel.',
    url: 'https://command.93.fyi',
    repo: 'karl-command-center (local)',
    stack: 'Next.js 16, React 19, Tailwind 4, framer-motion, lucide-react, better-sqlite3',
    notes: [
      'Gated by Cloudflare Access (9193 tenant)',
      'Design doc: ~/karl-infra/infra/command-center.md',
    ],
    position: { x: 1140, y: 940 },
  },
  {
    id: 'v-house',
    label: 'house-tracker',
    sublabel: 'S. FL property comparison · *.vercel.app',
    category: 'vercel',
    group: 'vercel',
    description:
      'Side-by-side property comparison dashboard for South Florida home shopping. Static React 19 SPA with Gemini-generated concept renders for kitchens and pools.',
    url: '(no custom domain — *.vercel.app)',
    repo: 'karlmarx/house-tracker',
    stack: 'React 19, Vite 8, react-router 7, Tailwind 4',
    notes: [
      'Two properties tracked at present',
      'Photos + Gemini renders committed to git under public/photos/',
    ],
    position: { x: 1140, y: 1030 },
  },
  {
    id: 'v-photos',
    label: 'photos.93.fyi',
    sublabel: 'Cloudflare Worker · PLANNED',
    category: 'vercel',
    group: 'vercel',
    description:
      'Planned Cloudflare Worker exposing Karl\'s local photo catalog (built by photo-memory) as a searchable web UI. Phase 0 — design only, not built. D1 for metadata, R2 for thumbnails, full-res served via Tailscale byte-server. See infra/photos-93fyi.md.',
    notes: [
      'Phase 4 of photo-memory feeds this',
      'Cloudflare (not Vercel) — D1 + R2 + Workers AI fit shape better',
      'GitHub OAuth or Cloudflare Access for auth (TBD)',
    ],
    position: { x: 1140, y: 1110 },
  },

  // ---------- Infrastructure layer ----------
  {
    id: 'github',
    label: 'GitHub (karlmarx)',
    sublabel: 'source of truth for all code',
    category: 'infra',
    group: 'infra',
    description:
      'All source code lives under the karlmarx GitHub org. Vercel auto-deploys from main on every repo.',
    url: 'https://github.com/karlmarx',
    position: { x: 90, y: 760 },
  },
  {
    id: 'cloudflare',
    label: 'Cloudflare',
    sublabel: 'DNS · email routing',
    category: 'infra',
    group: 'infra',
    description:
      'DNS for 93.fyi, plus email routing: k@93.fyi → karlmarx9193@gmail.com.',
    position: { x: 290, y: 760 },
  },
  {
    id: 'dynadot',
    label: 'Dynadot',
    sublabel: '.fyi registrar',
    category: 'infra',
    group: 'infra',
    description: 'Registrar for 93.fyi. Nameservers delegated to Cloudflare.',
    position: { x: 490, y: 760 },
  },
  {
    id: 'supabase',
    label: 'Supabase',
    sublabel: 'Postgres + Auth + Storage',
    category: 'infra',
    group: 'infra',
    description: 'Backend for WIP Social ID Verification — Postgres DB, Auth, and Storage.',
    position: { x: 690, y: 760 },
  },
  {
    id: 'vercel-platform',
    label: 'Vercel Platform',
    sublabel: 'free tier · CI + CDN',
    category: 'infra',
    group: 'infra',
    description:
      'Build + CDN for every web app. Auto-deploys from main branch, preview deploys on PRs.',
    position: { x: 870, y: 760 },
  },
  {
    id: 'todoist',
    label: 'Todoist',
    sublabel: 'karl-todo project · source of truth',
    category: 'infra',
    group: 'infra',
    description:
      'Daily actionable TODO list. Sync API integration feeds the karl-todo GHA which round-trips to todo.md and Nextcloud every 15 min.',
    position: { x: 90, y: 860 },
  },
  {
    id: 'discord',
    label: 'Discord',
    sublabel: 'alerts channel',
    category: 'infra',
    group: 'infra',
    description: 'Alert sink for future find-hub-tracker and other notifiers.',
    position: { x: 290, y: 860 },
  },
  {
    id: 'cloudflare-access',
    label: 'Cloudflare Access',
    sublabel: 'zero-trust · 9193 tenant',
    category: 'infra',
    group: 'infra',
    description:
      'Zero-trust auth gate sitting in front of private Vercel apps. Currently gates command.93.fyi.',
    position: { x: 490, y: 860 },
  },
];

// ---------------------------------------------------------------------------
// Edges (data flow)
// ---------------------------------------------------------------------------

export const edges: AutomationEdge[] = [
  // Phone uploads
  { id: 'e1', source: 'phone', target: 'nextcloud-server', label: 'upload photos' },
  { id: 'e2', source: 'nextcloud-server', target: 'nextcloud-local', label: 'desktop sync' },

  // Photo ingest
  { id: 'e3', source: 'nextcloud-local', target: 'ingest', label: 'source', animated: true },
  { id: 'e4', source: 'ingest', target: 'x9', label: 'rclone move (dedup)', animated: true },

  // Return label
  { id: 'e5', source: 'nextcloud-local', target: 'return-scan', label: 'scan' },
  { id: 'e6', source: 'return-scan', target: 'nextcloud-local', label: 'Pending Returns/' },

  // VLM
  { id: 'e7', source: 'x9', target: 'ollama', label: 'read photos', animated: true },
  { id: 'e8', source: 'ollama', target: 'catalog', label: 'write rows', animated: true },
  { id: 'e9', source: 'catalog', target: 'nextcloud-local', label: 'snapshot' },

  // karl-todo cycle
  { id: 'e10', source: 'todoist', target: 'karl-todo', label: 'pull tasks', animated: true },
  { id: 'e11', source: 'karl-todo', target: 'nextcloud-server', label: 'mirror todo.md' },
  { id: 'e12', source: 'karl-todo', target: 'github', label: 'commit [skip ci]' },

  // karl-infra docs
  { id: 'e13', source: 'karl-infra-update', target: 'github', label: 'commit docs' },

  // GitHub → Vercel deploys
  { id: 'e14', source: 'github', target: 'vercel-platform', label: 'auto-deploy' },
  { id: 'e15', source: 'vercel-platform', target: 'v-nfit' },
  { id: 'e16', source: 'vercel-platform', target: 'v-nyoga' },
  { id: 'e18', source: 'vercel-platform', target: 'v-foodr' },
  { id: 'e19', source: 'vercel-platform', target: 'v-paddles' },
  { id: 'e20', source: 'vercel-platform', target: 'v-auto' },

  // DNS / registrar
  { id: 'e21', source: 'dynadot', target: 'cloudflare', label: 'delegate NS' },
  { id: 'e22', source: 'cloudflare', target: 'vercel-platform', label: 'CNAMEs' },

  // WIP Social ID Verification → Supabase
  { id: 'e23', source: 'v-wip-siv', target: 'supabase', label: 'DB + Auth' },

  // Seedbox → find-hub → Discord
  { id: 'e24', source: 'find-hub', target: 'discord', label: 'alerts' },

  // Windows pipeline
  { id: 'e25', source: 'nextcloud-server', target: 'claude-pipeline', label: 'inbox/*.md' },
  { id: 'e26', source: 'claude-pipeline', target: 'openclaw', label: 'route task' },
  { id: 'e27', source: 'openclaw-watchdog', target: 'openclaw', label: 'keep alive' },

  // Command Center
  { id: 'e28', source: 'vercel-platform', target: 'v-command', label: 'deploy' },
  { id: 'e29', source: 'cloudflare-access', target: 'v-command', label: 'gates auth' },
  { id: 'e30', source: 'command-agent', target: 'v-command', label: 'JSON via CF tunnel', animated: true },

  // Nextcloud pipelines (separate from rclone video ingest)
  { id: 'e31', source: 'nextcloud-server', target: 'nextcloud-android-sync', label: 'WebDAV poll Camera/' },
  { id: 'e32', source: 'nextcloud-android-sync', target: 'x9', label: 'download photos' },
  { id: 'e33', source: 'nextcloud-server', target: 'screenshot-parser', label: 'WebDAV poll Screenshots/' },
  { id: 'e34', source: 'screenshot-parser', target: 'x9', label: 'categorized → docs/' },
  { id: 'e35', source: 'screenshot-parser', target: 'karl-todo', label: 'append todo.md' },

  // MLX-VLM ports + openclaw routing
  { id: 'e36', source: 'openclaw', target: 'mlx-vlm-8080', label: 'analysis / vision' },
  { id: 'e37', source: 'openclaw', target: 'mlx-vlm-8081', label: 'primary chat', animated: true },
  { id: 'e38', source: 'openclaw', target: 'mlx-vlm-8082', label: 'long-ctx reasoning' },

  // local-vlm-analysis library
  { id: 'e39', source: 'local-vlm-analysis', target: 'mlx-vlm-8080', label: 'library calls', animated: true },

  // photo-memory
  { id: 'e40', source: 'x9', target: 'photo-memory', label: 'reads Takeout' },
  { id: 'e41', source: 'photo-memory', target: 'mlx-vlm-8080', label: 'VLM analysis' },

  // house-tracker deploy
  { id: 'e42', source: 'vercel-platform', target: 'v-house', label: 'deploy' },

  // photos.93.fyi (planned)
  { id: 'e43', source: 'photo-memory', target: 'v-photos', label: 'phase 4 nightly sync (planned)' },
];

// ---------------------------------------------------------------------------
// Category metadata (legend + colors)
// ---------------------------------------------------------------------------

export interface CategoryMeta {
  id: Category;
  label: string;
  colorVar: string;
  hex: string;
}

export const categoryMeta: Record<Category, CategoryMeta> = {
  local: {
    id: 'local',
    label: 'Local automation (Mac Studio)',
    colorVar: '--color-cat-local',
    hex: '#22c55e',
  },
  seedbox: {
    id: 'seedbox',
    label: 'Seedbox (Ultra.cc)',
    colorVar: '--color-cat-seedbox',
    hex: '#f97316',
  },
  gha: {
    id: 'gha',
    label: 'GitHub Actions',
    colorVar: '--color-cat-gha',
    hex: '#a855f7',
  },
  vercel: {
    id: 'vercel',
    label: 'Vercel app',
    colorVar: '--color-cat-vercel',
    hex: '#3b82f6',
  },
  windows: {
    id: 'windows',
    label: 'Windows 11 workstation',
    colorVar: '--color-cat-windows',
    hex: '#06b6d4',
  },
  infra: {
    id: 'infra',
    label: 'Infrastructure layer',
    colorVar: '--color-cat-infra',
    hex: '#6b7280',
  },
  self: {
    id: 'self',
    label: 'You are here',
    colorVar: '--color-cat-self',
    hex: '#ec4899',
  },
};
