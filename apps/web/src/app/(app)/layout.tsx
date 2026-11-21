import type { Metadata } from "next";
import { AuthProvider } from "@/lib/auth";
import { AppHeader } from "./app-header";

export const metadata: Metadata = { title: "Espace officiels", robots: { index: false } };

export default function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <AuthProvider>
      <AppHeader />
      <main className="mx-auto max-w-6xl px-3 py-4">{children}</main>
    </AuthProvider>
  );
}
