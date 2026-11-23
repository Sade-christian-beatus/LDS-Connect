"use client";
// Thème du site public : automatique (réglage du téléphone), clair ou sombre.
import { useEffect, useState } from "react";
import { THEME_KEY as KEY } from "@/lib/theme";

type Theme = "auto" | "light" | "dark";
const NEXT: Record<Theme, Theme> = { auto: "light", light: "dark", dark: "auto" };
const LABEL: Record<Theme, string> = { auto: "Thème automatique", light: "Thème clair", dark: "Thème sombre" };

function apply(theme: Theme) {
  const dark = theme === "dark" || (theme === "auto" && matchMedia("(prefers-color-scheme: dark)").matches);
  document.documentElement.classList.toggle("public-dark", dark);
}

export function ThemeToggle() {
  const [theme, setTheme] = useState<Theme>("auto");

  useEffect(() => {
    Promise.resolve().then(() => setTheme((localStorage.getItem(KEY) as Theme) ?? "auto"));
    const mq = matchMedia("(prefers-color-scheme: dark)");
    const onChange = () => apply((localStorage.getItem(KEY) as Theme) ?? "auto");
    mq.addEventListener("change", onChange);
    return () => mq.removeEventListener("change", onChange);
  }, []);

  return (
    <button
      type="button"
      aria-label={`${LABEL[theme]} (changer)`}
      title={LABEL[theme]}
      onClick={() => {
        const next = NEXT[theme];
        localStorage.setItem(KEY, next);
        setTheme(next);
        apply(next);
      }}
      className="flex h-9 w-9 items-center justify-center rounded-full text-white/90 hover:bg-white/10"
    >
      {theme === "dark" ? (
        <svg viewBox="0 0 24 24" className="h-5 w-5" fill="currentColor" aria-hidden>
          <path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8Z" />
        </svg>
      ) : theme === "light" ? (
        <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden>
          <circle cx="12" cy="12" r="4" />
          <path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" />
        </svg>
      ) : (
        <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden>
          <circle cx="12" cy="12" r="9" />
          <path d="M12 3a9 9 0 0 1 0 18Z" fill="currentColor" />
        </svg>
      )}
    </button>
  );
}
