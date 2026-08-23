const CACHE_NAME = 'drink-pos-shell-v99';
const NAVIGATION_TIMEOUT_MS = 1800;
const SHELL_URLS = ['/', '/liste', '/liste/', '/admin', '/kassa', '/kassa/', '/self-pay', '/self-pay/', '/bezahlen', '/bezahlen/', '/manifest.webmanifest', '/kassa.webmanifest', '/self-pay.webmanifest', '/service-worker.js', '/icon.png', '/icon.svg', '/icon-192.png', '/icon-512.png', '/kassa-icon.png', '/kassa-icon.svg', '/kassa-icon-192.png', '/kassa-icon-512.png'];
const NAVIGATION_FALLBACKS = [
  { prefix: '/kassa', url: '/kassa/' },
  { prefix: '/self-pay', url: '/self-pay/' },
  { prefix: '/bezahlen', url: '/self-pay/' },
  { prefix: '/liste', url: '/liste/' },
];

function timeoutAfter(ms) {
  return new Promise((_, reject) => {
    setTimeout(() => reject(new Error('network timeout')), ms);
  });
}

function canCache(response) {
  return response && response.ok && ['basic', 'default'].includes(response.type);
}

async function cacheShell() {
  const cache = await caches.open(CACHE_NAME);
  await Promise.all(SHELL_URLS.map(url => cache.add(url).catch(() => null)));
}

async function putInCache(request, response) {
  if (!canCache(response)) return;
  const cache = await caches.open(CACHE_NAME);
  await cache.put(request, response.clone());
}

async function navigationFallback(request, url) {
  const cached = await caches.match(request);
  if (cached) return cached;
  const fallback = NAVIGATION_FALLBACKS.find(item => url.pathname.startsWith(item.prefix));
  if (fallback) {
    const fallbackResponse = await caches.match(fallback.url);
    if (fallbackResponse) return fallbackResponse;
  }
  const home = await caches.match('/') || await caches.match('/liste/');
  if (home) return home;
  return new Response('Drink POS ist offline und die App-Shell ist auf diesem Geraet nicht im Cache.', {
    status: 503,
    headers: { 'Content-Type': 'text/plain; charset=utf-8' },
  });
}

async function networkFirstNavigation(event, url) {
  try {
    const response = await Promise.race([fetch(event.request), timeoutAfter(NAVIGATION_TIMEOUT_MS)]);
    event.waitUntil(putInCache(event.request, response.clone()).catch(() => {}));
    return response;
  } catch {
    return navigationFallback(event.request, url);
  }
}

self.addEventListener('install', event => {
  event.waitUntil(cacheShell().then(() => self.skipWaiting()));
});

self.addEventListener('activate', event => {
  event.waitUntil(caches.keys().then(keys => Promise.all(keys.filter(key => key !== CACHE_NAME).map(key => caches.delete(key)))).then(() => self.clients.claim()));
});

self.addEventListener('fetch', event => {
  const url = new URL(event.request.url);
  if (url.pathname.startsWith('/api/')) return;
  if (event.request.mode === 'navigate') {
    event.respondWith(networkFirstNavigation(event, url));
    return;
  }
  if (event.request.method !== 'GET') return;
  event.respondWith(caches.match(event.request).then(cached => cached || fetch(event.request).then(response => {
    event.waitUntil(putInCache(event.request, response.clone()).catch(() => {}));
    return response;
  })));
});
