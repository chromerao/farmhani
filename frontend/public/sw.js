/* Farm하니 서비스워커 — 앱 셸 캐시 + 네트워크 우선.
   API 응답은 캐시하지 않고, 정적 자원만 오프라인 폴백으로 보관한다. */
const CACHE_NAME = "farmhani-shell-v1";
const SHELL_ASSETS = ["/", "/manifest.webmanifest", "/icons/icon-192.png", "/icons/icon-512.png"];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(SHELL_ASSETS)).then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) => Promise.all(keys.filter((key) => key !== CACHE_NAME).map((key) => caches.delete(key))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (event) => {
  const request = event.request;
  if (request.method !== "GET") return;

  const url = new URL(request.url);
  // 백엔드 API·Supabase 요청은 서비스워커가 관여하지 않는다
  if (url.origin !== self.location.origin || url.pathname.startsWith("/api/")) return;

  event.respondWith(
    fetch(request)
      .then((response) => {
        // 정상 응답이면 정적 자원을 캐시에 갱신 보관
        if (response.ok && (request.destination !== "" || url.pathname === "/")) {
          const copy = response.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(request, copy));
        }
        return response;
      })
      .catch(() =>
        caches.match(request).then((cached) => {
          if (cached) return cached;
          // 오프라인 내비게이션은 앱 셸로 폴백
          if (request.mode === "navigate") return caches.match("/");
          return Response.error();
        })
      )
  );
});
