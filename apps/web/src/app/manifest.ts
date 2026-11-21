import type { MetadataRoute } from "next";

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "LDS Connect — Ligue de la Souveraineté",
    short_name: "LDS Connect",
    description: "Calendrier, scores en direct et classements de la Ligue de la Souveraineté",
    start_url: "/",
    display: "standalone",
    lang: "fr",
    background_color: "#fafaf9",
    theme_color: "#1f7a3a",
    icons: [{ src: "/icon.svg", sizes: "any", type: "image/svg+xml" }],
  };
}
