const SHELL_CACHE = "jans-matchday-shell-v4";
const DATA_CACHE = "jans-matchday-data-v3";
const APP_SHELL = [
  "./",
  "./index.html",
  "./styles.css",
  "./app.js",
  "./sw.js",
  "./manifest.webmanifest",
  "./assets/football-on-pitch.jpg",
  "./assets/hongkou-stadium.jpg",
  "./assets/apple-touch-icon.png",
  "./assets/jans-matchday-192.png",
  "./assets/jans-matchday-512.png",
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(SHELL_CACHE)
      .then((cache) => cache.addAll(APP_SHELL))
      .then(() => self.skipWaiting()),
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys()
      .then((cacheNames) => Promise.all(
        cacheNames
          .filter((cacheName) => (
            cacheName.startsWith("jans-matchday-")
            && ![SHELL_CACHE, DATA_CACHE].includes(cacheName)
          ))
          .map((cacheName) => caches.delete(cacheName)),
      ))
      .then(() => self.clients.claim()),
  );
});

self.addEventListener("fetch", (event) => {
  const { request } = event;
  if (request.method !== "GET") return;

  const url = new URL(request.url);
  if (url.origin === self.location.origin && request.mode === "navigate") {
    event.respondWith(
      fetch(request)
        .then(async (response) => {
          if (response.ok) {
            try {
              const cache = await caches.open(SHELL_CACHE);
              await cache.put(request, response.clone());
            } catch (error) {
              console.error("Unable to cache the app page.", error);
            }
          }
          return response;
        })
        .catch(async () => (
          await caches.match(request)
          ?? await caches.match(new URL("./index.html", self.registration.scope).href)
        )),
    );
    return;
  }

  if (url.origin === "https://api.openligadb.de") {
    event.respondWith(
      fetch(request)
        .then(async (response) => {
          if (response.ok) {
            try {
              const cache = await caches.open(DATA_CACHE);
              await cache.put(request, response.clone());
            } catch (error) {
              console.error("Unable to cache OpenLigaDB response.", error);
            }
          }
          return response;
        })
        .catch(async () => (await caches.match(request)) ?? Response.error()),
    );
    return;
  }

  if (url.origin === self.location.origin) {
    event.respondWith(
      caches.match(request)
        .then((cached) => cached ?? fetch(request)),
    );
  }
});
