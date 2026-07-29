const CACHE_NAME = 'pimascor-shell-v4'
const SCOPE_PATH = new URL(self.registration.scope).pathname
const scoped = (path) => `${SCOPE_PATH}${path}`
const SAFE_SHELL = [
  scoped(''),
  scoped('index.html'),
  scoped('manifest.webmanifest'),
  scoped('pimascor-logo.jpg'),
  scoped('pimascor-icon-192.png'),
  scoped('pimascor-icon-512.png'),
  scoped('pimascor-icon-maskable-192.png'),
  scoped('pimascor-icon-maskable-512.png'),
  scoped('apple-touch-icon.png'),
]

self.addEventListener('install', (event) => {
  event.waitUntil(caches.open(CACHE_NAME).then((cache) => cache.addAll(SAFE_SHELL)))
  self.skipWaiting()
})

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) => Promise.all(keys.filter((key) => key !== CACHE_NAME).map((key) => caches.delete(key)))),
  )
  self.clients.claim()
})

self.addEventListener('fetch', (event) => {
  const request = event.request
  const url = new URL(request.url)

  if (request.method !== 'GET' || url.origin !== self.location.origin || url.pathname.startsWith(scoped('api/'))) return

  if (request.mode === 'navigate') {
    event.respondWith(fetch(request).catch(() => caches.match(scoped('index.html'))))
    return
  }

  if (!['style', 'script', 'image', 'font'].includes(request.destination)) return

  event.respondWith(
    caches.match(request).then((cached) => cached || fetch(request).then((response) => {
      if (response.ok) {
        const copy = response.clone()
        caches.open(CACHE_NAME).then((cache) => cache.put(request, copy))
      }
      return response
    })),
  )
})
