import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Image autonome pour Docker (aucune dépendance à un hébergeur particulier)
  output: "standalone",
  cacheComponents: true,
  partialPrefetching: true,
  poweredByHeader: false,
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
