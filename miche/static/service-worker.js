/**
 * Miche Service Worker — PWA offline + push notifications.
 *
 * Cache strategy:
 * - App shell (HTML, CSS, JS): cache-first with network update
 * - API proxy calls: network-first with cache fallback
 * - Static assets: cache-first
 */

const CACHE_NAME = "miche-v1";
const SHELL_CACHE = "miche-shell-v1";

// App shell — the files needed for the UI to load offline
const SHELL_URLS = [
  "/orchestrate",
  "/static/miche.css",
  "/static/orchestrate.css",
  "/static/orchestrate.js",
  "/static/utils.js",
  "/static/island.css",
  "/static/island.js",
  "/static/miche-mascot.svg",
  "/static/manifest.json",
];

// Install: pre-cache the app shell
self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(SHELL_CACHE).then((cache) => {
      return cache.addAll(SHELL_URLS).catch((err) => {
        console.warn("[sw] shell pre-cache partial failure:", err);
      });
    })
  );
  self.skipWaiting();
});

// Activate: clean old caches
self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) => {
      return Promise.all(
        keys
          .filter((k) => k !== CACHE_NAME && k !== SHELL_CACHE)
          .map((k) => caches.delete(k))
      );
    })
  );
  self.clients.claim();
});

// Fetch: app shell = cache-first, API = network-first
self.addEventListener("fetch", (event) => {
  const url = new URL(event.request.url);

  // Skip non-GET
  if (event.request.method !== "GET") return;

  // API calls: network-first with cache fallback
  if (url.pathname.startsWith("/api/caffenagent/") || url.pathname.startsWith("/api/platform/")) {
    event.respondWith(
      fetch(event.request)
        .then((response) => {
          // Cache successful API responses
          if (response.ok) {
            const clone = response.clone();
            caches.open(CACHE_NAME).then((cache) => cache.put(event.request, clone));
          }
          return response;
        })
        .catch(() => caches.match(event.request))
    );
    return;
  }

  // App shell + static: cache-first with network update
  event.respondWith(
    caches.match(event.request).then((cached) => {
      const fetchPromise = fetch(event.request)
        .then((response) => {
          if (response.ok) {
            const clone = response.clone();
            caches.open(CACHE_NAME).then((cache) => cache.put(event.request, clone));
          }
          return response;
        })
        .catch(() => cached);

      return cached || fetchPromise;
    })
  );
});

// Push notifications — agent status updates
self.addEventListener("push", (event) => {
  let data = { title: "Miche", body: "Agent update" };
  try {
    data = event.data.json();
  } catch {
    data.body = event.data?.text() || "Agent update";
  }

  event.waitUntil(
    self.registration.showNotification(data.title, {
      body: data.body,
      icon: "/static/icons/icon-192.png",
      badge: "/static/icons/icon-192.png",
      tag: data.tag || "miche-notification",
      data: data.url || "/orchestrate",
      actions: [
        { action: "open", title: "Open" },
        { action: "dismiss", title: "Dismiss" },
      ],
    })
  );
});

// Notification click — open the relevant page
self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  if (event.action === "dismiss") return;

  const url = event.notification.data || "/orchestrate";
  event.waitUntil(
    clients.matchAll({ type: "window" }).then((windowClients) => {
      // Focus existing window if open
      for (const client of windowClients) {
        if (client.url.includes(url) && "focus" in client) {
          return client.focus();
        }
      }
      // Open new window
      return clients.openWindow(url);
    })
  );
});
