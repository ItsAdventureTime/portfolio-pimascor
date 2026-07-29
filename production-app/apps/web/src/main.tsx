import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import App from './App'
import { ApplicationErrorBoundary } from './IncidentCenter'
import './styles.css'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <ApplicationErrorBoundary>
      <App />
    </ApplicationErrorBoundary>
  </StrictMode>,
)

if ('serviceWorker' in navigator) {
  if (import.meta.env.PROD) {
    window.addEventListener('load', () => {
      navigator.serviceWorker.register(`${import.meta.env.BASE_URL}sw.js`).catch(() => {
        // PWA installation is optional. The online application remains available.
      })
    })
  } else {
    // A locally tested production build can otherwise keep controlling the Vite
    // development origin and make current source changes appear to be missing.
    void navigator.serviceWorker.getRegistrations()
      .then((registrations) => Promise.all(
        registrations
          .filter((registration) => new URL(registration.scope).origin === window.location.origin)
          .map((registration) => registration.unregister()),
      ))
    if ('caches' in window) {
      void caches.keys()
        .then((keys) => Promise.all(keys.filter((key) => key.startsWith('pimascor-shell-')).map((key) => caches.delete(key))))
    }
  }
}
