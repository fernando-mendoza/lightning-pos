// Estrategia de cache:
//   - /assets/*  -> cache-first. Vite les pone hash de contenido en el nombre,
//                   asi que una URL dada es inmutable: nunca sirve algo viejo.
//   - resto (app shell, "/" e "/index.html") -> NETWORK-FIRST con fallback a
//                   cache para offline.
//
// El shell NO puede ser cache-first: index.html referencia el bundle hasheado,
// asi que un index cacheado deja al usuario clavado en una version vieja de la
// app hasta que borre el cache del navegador a mano (bug real: el fix del boton
// "Salir" del modo demo no llegaba a los usuarios que ya habian abierto el PoS).
//
// Al cambiar CACHE_NAME, el handler de `activate` borra las caches anteriores.
const CACHE_NAME = "lpos-v12";
const SHELL_URLS = ["/", "/index.html"];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(SHELL_URLS))
  );
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(
        keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k))
      )
    )
  );
  self.clients.claim();
});

function cachePut(request, response) {
  if (!response.ok) return;
  const clone = response.clone();
  caches.open(CACHE_NAME).then((cache) => cache.put(request, clone));
}

self.addEventListener("fetch", (event) => {
  const { request } = event;

  // Ignore non-http(s) requests (chrome-extension://, about:, etc.)
  if (!request.url.startsWith("http")) return;
  if (request.method !== "GET") return;

  const url = new URL(request.url);

  // Network-first for API calls (el SW no participa)
  if (url.pathname.startsWith("/api/") || url.pathname.startsWith("/ws/")) {
    return;
  }

  // Cache-first solo para assets con hash de contenido
  if (url.pathname.startsWith("/assets/")) {
    event.respondWith(
      caches.match(request).then(
        (cached) =>
          cached ||
          fetch(request).then((response) => {
            cachePut(request, response);
            return response;
          })
      )
    );
    return;
  }

  // App shell y demas: network-first; el cache es solo el respaldo offline.
  event.respondWith(
    fetch(request)
      .then((response) => {
        cachePut(request, response);
        return response;
      })
      .catch(() =>
        caches
          .match(request)
          .then((cached) => cached || caches.match("/index.html"))
      )
  );
});
