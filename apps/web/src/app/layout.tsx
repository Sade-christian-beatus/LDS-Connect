import type { Metadata, Viewport } from "next";
import { ServiceWorker } from "@/components/ServiceWorker";
import "./globals.css";

export const metadata: Metadata = {
  title: { default: "LDS Connect", template: "%s · LDS Connect" },
  description:
    "Calendrier, résultats et classements de la Ligue de la Souveraineté (Burkina Faso).",
  applicationName: "LDS Connect",
};

export const viewport: Viewport = {
  themeColor: "#0a3a1e",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="fr" suppressHydrationWarning>
      <body className="min-h-screen bg-stone-50 text-stone-900 antialiased">
        {children}
        <ServiceWorker />
      </body>
    </html>
  );
}
