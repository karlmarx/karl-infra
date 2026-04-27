// orthoappt service worker — App Shell + offline fallback.
// Strategy:
//   /_next/static/*   → cache-first (immutable hashed assets)
//   navigations + same-origin GET → stale-while-revalidate
// On install we precache the 3 HTML routes and manifest so the app boots offline.

const CACHE = "orthoappt-v1";
const APP_SHELL = ["/", "/doctor", "/export", "/manifest.json"];

self.addEventListener("install", (e) => {
  e.waitUntil(
    caches
      .open(CACHE)
      .then((c) =>
        Promise.all(
          APP_SHELL.map((url) =>
            c.add(new Request(url, { cache: "reload" })).catch(() => {})
          )
        )
      )
  );
  self.skipWaiting();
});

self.addEventListener("activate", (e) => {
  e.waitUntil(
    caches
      .keys()
      .then((keys) =>
        Promise.all(
          keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))
        )
      )
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (event) => {
  const req = event.request;
  if (req.method !== "GET") return;

  let url;
  try {
    url = new URL(req.url);
  } catch {
    return;
  }
  if (url.origin !== self.location.origin) return;

  if (url.pathname.startsWith("/_next/static/")) {
    event.respondWith(cacheFirst(req));
    return;
  }

  if (req.mode === "navigate" || req.headers.get("accept")?.includes("text/html")) {
    event.respondWith(networkFallingBackToCache(req));
    return;
  }

  event.respondWith(staleWhileRevalidate(req));
});

async function cacheFirst(req) {
  const c = await caches.open(CACHE);
  const cached = await c.match(req);
  if (cached) return cached;
  try {
    const res = await fetch(req);
    if (res.ok) c.put(req, res.clone()).catch(() => {});
    return res;
  } catch (err) {
    return new Response("offline", { status: 504, statusText: "Offline" });
  }
}

async function staleWhileRevalidate(req) {
  const c = await caches.open(CACHE);
  const cached = await c.match(req);
  const fetched = fetch(req)
    .then((res) => {
      if (res.ok) c.put(req, res.clone()).catch(() => {});
      return res;
    })
    .catch(() => null);
  return cached || (await fetched) || new Response("offline", { status: 504 });
}

async function networkFallingBackToCache(req) {
  const c = await caches.open(CACHE);
  try {
    const res = await fetch(req);
    if (res.ok) c.put(req, res.clone()).catch(() => {});
    return res;
  } catch {
    const cached = await c.match(req);
    if (cached) return cached;
    const root = await c.match("/");
    return (
      root ||
      new Response("offline", {
        status: 503,
        headers: { "content-type": "text/plain" },
      })
    );
  }
}
