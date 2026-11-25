/// <reference no-default-lib="true" />
/// <reference lib="esnext" />
/// <reference lib="webworker" />
// Service worker (Serwist), construit après `next build` par scripts/build-sw.mjs.
// - Ressources statiques et écrans officiels précachés : utilisables sans réseau.
// - Les données ne passent jamais par ce cache : l'API est toujours en réseau seul,
//   la feuille de match et les clés de licences sont stockées dans IndexedDB.
// - Seule exception : les logos publics (/api/v1/media/…), fichiers versionnés et immuables,
//   gardés en cache pour s'afficher aussi hors connexion (billets, cartes, feuille de match).
//   Les photos de licence (privées, sous /admin/ ou /licences/) restent en réseau seul.
import type { PrecacheEntry, SerwistGlobalConfig } from "serwist";
import { CacheFirst, ExpirationPlugin, NetworkFirst, NetworkOnly, Serwist } from "serwist";

declare global {
  interface WorkerGlobalScope extends SerwistGlobalConfig {
    __SW_MANIFEST: (PrecacheEntry | string)[] | undefined;
  }
}
declare const self: ServiceWorkerGlobalScope;

// Toutes les feuilles de match partagent la même page (rendue côté client d'après l'URL) :
// une seule copie en cache sert pour n'importe quel match, même jamais ouvert sur l'appareil.
const SHEET_SHELL = "/delegue/match/_";

const serwist = new Serwist({
  precacheEntries: self.__SW_MANIFEST,
  skipWaiting: true,
  clientsClaim: true,
  navigationPreload: true,
  runtimeCaching: [
    {
      matcher: ({ url, request }) => request.method === "GET" && url.pathname.startsWith("/api/v1/media/"),
      handler: new CacheFirst({
        cacheName: "logos",
        plugins: [new ExpirationPlugin({ maxEntries: 80, maxAgeSeconds: 365 * 24 * 3600 })],
      }),
    },
    { matcher: ({ url }) => url.pathname.startsWith("/api/"), handler: new NetworkOnly() },
    {
      matcher: ({ request, url }) =>
        request.mode === "navigate" && url.pathname.startsWith("/delegue/match/"),
      handler: new NetworkFirst({
        cacheName: "feuille-de-match",
        networkTimeoutSeconds: 4,
        plugins: [{ cacheKeyWillBeUsed: async () => new URL(SHEET_SHELL, self.location.origin).href }],
      }),
    },
    {
      matcher: ({ request }) => request.mode === "navigate",
      handler: new NetworkFirst({
        cacheName: "pages",
        networkTimeoutSeconds: 4,
        plugins: [new ExpirationPlugin({ maxEntries: 50, maxAgeSeconds: 7 * 24 * 3600 })],
      }),
    },
    {
      matcher: ({ url }) => url.pathname.startsWith("/_next/static/"),
      handler: new CacheFirst({
        cacheName: "statique",
        plugins: [new ExpirationPlugin({ maxEntries: 300, maxAgeSeconds: 30 * 24 * 3600 })],
      }),
    },
  ],
});

serwist.addEventListeners();
