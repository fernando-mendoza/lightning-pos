import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)

if ("serviceWorker" in navigator) {
  // Si ya habia un SW controlando esta pagina y entra uno nuevo (skipWaiting +
  // clients.claim), recargamos UNA vez para tomar el shell nuevo. Sin esto, el
  // SW viejo sigue sirviendo su index.html cacheado y el usuario tarda varias
  // cargas en ver una version nueva de la app.
  const hadController = !!navigator.serviceWorker.controller;
  let refreshing = false;
  navigator.serviceWorker.addEventListener("controllerchange", () => {
    if (!hadController || refreshing) return; // primera instalacion: no recargar
    refreshing = true;
    window.location.reload();
  });

  window.addEventListener("load", () => {
    navigator.serviceWorker.register("/sw.js").catch(() => {});
  });
}
