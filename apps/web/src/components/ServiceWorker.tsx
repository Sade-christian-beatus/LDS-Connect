"use client";
import { useEffect } from "react";

/** Enregistre le service worker (en production uniquement : public/sw.js est généré au build). */
export function ServiceWorker() {
  useEffect(() => {
    if (process.env.NODE_ENV !== "production" || !("serviceWorker" in navigator)) return;
    navigator.serviceWorker.register("/sw.js", { scope: "/" }).catch(() => {
      /* navigateur sans prise en charge : le site reste utilisable en ligne */
    });
  }, []);
  return null;
}
