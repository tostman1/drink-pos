const CACHE_NAME = 'drink-pos-shell-v82';
const SHELL_URLS = ['/', '/liste/', '/admin', '/kassa', '/kassa/', '/manifest.webmanifest', '/kassa.webmanifest', '/icon.png', '/icon.svg', '/icon-192.png', '/icon-512.png', '/kassa-icon.png', '/kassa-icon.svg', '/kassa-icon-192.png', '/kassa-icon-512.png'];

self.addEventListener('install', event => {
  event.waitUntil(caches.open(CACHE_NAME).then(cache => cache.addAll(SHELL_URLS)).then(() => self.skipWaiting()));
});

self.addEventListener('activate', event => {
  event.waitUntil(caches.keys().then(keys => Promise.all(keys.filter(key => key !== CACHE_NAME).map(key => caches.delete(key)))).then(() => self.clients.claim()));
});

self.addEventListener('fetch', event => {
  const url = new URL(event.request.url);
  if (url.pathname.startsWith('/api/')) return;
  if (event.request.mode === 'navigate') {
    event.respondWith(fetch(event.request).then(response => {
      const copy = response.clone();
      caches.open(CACHE_NAME).then(cache => cache.put(event.request, copy));
      return response;
    }).catch(() => caches.match(event.request).then(cached => {
      if (cached) return cached;
      if (url.pathname.startsWith('/kassa')) return caches.match('/kassa/');
      if (url.pathname.startsWith('/liste')) return caches.match('/liste/');
      return caches.match('/');
    })));
    return;
  }
  event.respondWith(caches.match(event.request).then(cached => cached || fetch(event.request)));
});
