import type { NextConfig } from "next";

// En-têtes de sécurité (production) : pas d'affichage dans le cadre d'un autre site
// (détournement de clic), scripts et ressources de la même origine seulement, caméra réservée
// au site (lecture des QR au stade). « unsafe-inline » reste nécessaire pour les scripts
// d'amorçage de Next et le script du thème ; aucune ressource externe n'est chargée.
const CONTENT_SECURITY_POLICY = [
  "default-src 'self'",
  "script-src 'self' 'unsafe-inline'",
  "style-src 'self' 'unsafe-inline'",
  "img-src 'self' data: blob:",
  "font-src 'self' data:",
  "connect-src 'self'",
  "media-src 'self' blob:",
  "worker-src 'self'",
  "manifest-src 'self'",
  "frame-ancestors 'none'",
  "base-uri 'self'",
  "form-action 'self'",
  "object-src 'none'",
].join("; ");

const SECURITY_HEADERS = [
  { key: "Content-Security-Policy", value: CONTENT_SECURITY_POLICY },
  { key: "X-Frame-Options", value: "DENY" },
  { key: "X-Content-Type-Options", value: "nosniff" },
  { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
  { key: "Permissions-Policy", value: "camera=(self), microphone=(), geolocation=(), payment=()" },
];

const nextConfig: NextConfig = {
  // Image autonome pour Docker (aucune dépendance à un hébergeur particulier)
  output: "standalone",
  cacheComponents: true,
  partialPrefetching: true,
  poweredByHeader: false,
  async headers() {
    // En développement, le rechargement à chaud a besoin d'eval : en-têtes en production seulement
    if (process.env.NODE_ENV !== "production") return [];
    return [{ source: "/:path*", headers: SECURITY_HEADERS }];
  },
  // En local, /api/* est relayé vers l'API (même origine, donc cookies simples).
  // En production, le reverse proxy (Caddy, Nginx…) fait ce routage directement.
  async rewrites() {
    const api = process.env.API_INTERNAL_URL ?? "http://127.0.0.1:8000";
    return [{ source: "/api/:path*", destination: `${api}/api/:path*` }];
  },
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
};

export default nextConfig;
