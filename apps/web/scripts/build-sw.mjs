// Construit public/sw.js après `next build` : bundle esbuild de src/sw/sw.ts puis injection
// du manifeste de précache (Serwist). Exécuté par `pnpm build`.
import { readFileSync } from "node:fs";
import { injectManifest } from "@serwist/build";
import { build } from "esbuild";

const tmp = ".next/sw.bundle.js";
await build({
  entryPoints: ["src/sw/sw.ts"],
  bundle: true,
  format: "iife",
  minify: true,
  target: "es2020",
  outfile: tmp,
  define: { "process.env.NODE_ENV": '"production"' },
  logLevel: "warning",
});

const revision = readFileSync(".next/BUILD_ID", "utf8").trim();
const { count, size, warnings } = await injectManifest({
  swSrc: tmp,
  swDest: "public/sw.js",
  globDirectory: ".next",
  globPatterns: ["static/**/*.{js,css,woff2}"],
  modifyURLPrefix: { "static/": "/_next/static/" },
  maximumFileSizeToCacheInBytes: 5 * 1024 * 1024,
  // Écrans officiels disponibles hors connexion dès la première visite
  additionalPrecacheEntries: ["/connexion", "/delegue", "/controle", "/manifest.webmanifest"].map(
    (url) => ({ url, revision }),
  ),
});
for (const w of warnings) console.warn(w);
console.log(`Service worker : ${count} fichiers précachés (${(size / 1024).toFixed(0)} Kio).`);
