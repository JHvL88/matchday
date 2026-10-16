const SHELL_CACHE = "jans-matchday-shell-v8";
const DATA_CACHE = "jans-matchday-data-v3";
const APP_SHELL = [
  "./",
  "./index.html",
  "./styles.css",
  "./app.js",
  "./i18n.js",
  "./sw.js",
  "./manifest.webmanifest",
  "./assets/football-on-pitch.jpg",
  "./assets/apple-touch-icon.png",
  "./assets/jans-matchday-192.png",
  "./assets/jans-matchday-512.png",
  "./analysis/2026-27-md5-augsburg-bayern/figs/fig1_forecast.svg",
  "./analysis/2026-27-md5-augsburg-bayern/figs/de/fig1_forecast.svg",
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(SHELL_CACHE)
      .then((cache) => cache.addAll(APP_SHELL.map((url) => new Request(url, { cache: "reload" }))))
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

// Network first, so the page, its script and its styles always come from the same release;
// the cache is only the offline fallback. Version query strings (styles.css?v=8) are ignored
// when falling back, so the precached copies still match.
async function networkFirst(event, cacheName, fallbackUrl) {
  const { request } = event;
  try {
    const response = await fetch(request);
    if (response.ok) {
      const copy = response.clone();
      event.waitUntil(
        caches.open(cacheName)
          .then((cache) => cache.put(request, copy))
          .catch((error) => console.error("Unable to cache a response.", error)),
      );
    }
    return response;
  } catch (error) {
    const options = { ignoreSearch: cacheName === SHELL_CACHE };
    return await caches.match(request, options)
      ?? (fallbackUrl ? await caches.match(fallbackUrl) : undefined)
      ?? Response.error();
  }
}

self.addEventListener("fetch", (event) => {
  const { request } = event;
  if (request.method !== "GET") return;

  const url = new URL(request.url);
  if (url.origin === self.location.origin) {
    const fallback = request.mode === "navigate"
      ? new URL("./index.html", self.registration.scope).href
      : undefined;
    event.respondWith(networkFirst(event, SHELL_CACHE, fallback));
    return;
  }

  if (url.origin === "https://api.openligadb.de") {
    event.respondWith(networkFirst(event, DATA_CACHE));
  }
});
