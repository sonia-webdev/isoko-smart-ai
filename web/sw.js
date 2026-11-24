/* Isoko Smart AI service worker: the page opens even with a weak or no connection, using the last prices it saw. */
const VERSION = "isoko-v1";
const SHELL = ["./", "index.html", "manifest.webmanifest", "icons/icon-192.png", "icons/icon-512.png"];
const CDN = ["cdnjs.cloudflare.com", "cdn.tailwindcss.com", "fonts.googleapis.com", "fonts.gstatic.com"];

self.addEventListener("install", (e) => { e.waitUntil(caches.open(VERSION).then((c) => c.addAll(SHELL)).then(() => self.skipWaiting())); });
self.addEventListener("activate", (e) => {
  e.waitUntil(caches.keys().then((ks) => Promise.all(ks.filter((k) => k !== VERSION).map((k) => caches.delete(k)))).then(() => self.clients.claim()));
});

self.addEventListener("fetch", (e) => {
  const req = e.request, url = new URL(req.url);
  if (req.method !== "GET") return;                                         // SMS and feedback always go to the server
  if (url.origin === location.origin && (url.pathname.includes("/api/") || url.pathname.endsWith("/health"))) return;   // never cache answers
  const fresh = url.origin === location.origin && (url.pathname.endsWith("data.json") || url.pathname.endsWith("index.html") || url.pathname.endsWith("/"));
  if (fresh) {                                                              // prices: the network first, the saved copy if offline
    e.respondWith(fetch(req).then((r) => { const copy = r.clone(); caches.open(VERSION).then((c) => c.put(req, copy)); return r; })
      .catch(() => caches.match(req).then((m) => m || caches.match("index.html"))));
    return;
  }
  if (url.origin === location.origin || CDN.includes(url.hostname)) {       // everything else: saved copy at once, refreshed in the background
    e.respondWith(caches.match(req).then((m) => {
      const net = fetch(req).then((r) => { if (r && (r.ok || r.type === "opaque")) { const copy = r.clone(); caches.open(VERSION).then((c) => c.put(req, copy)); } return r; }).catch(() => m);
      return m || net;
    }));
  }
});
