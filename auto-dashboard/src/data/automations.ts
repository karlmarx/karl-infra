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
    height: 620,
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
    label: 'Vercel',
    sublabel: 'free tier · auto-deploy from main',
    x: 1100,
    y: 340,
    width: 360,
    height: 580,
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
    sublabel: 'Playwright · CDP automation',
    category: 'windows',
    group: 'windows',
    description:
      'Automates the Gemini web UI for image generation via Chrome DevTools Protocol.',
    position: { x: 880, y: 620 },
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
  { id: 'e17', source: 'vercel-platform', target: 'v-ta' },
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
