"use client";
// Logo de la Ligue côté navigateur (espace officiels, pages clientes) : demandé une fois,
// gardé dans le navigateur pour s'afficher aussi hors connexion.
import { useEffect, useState } from "react";

const KEY = "lds-brand-logo";

export function useBrandLogo(): string | null {
  const [url, setUrl] = useState<string | null>(null);
  useEffect(() => {
    let active = true;
    Promise.resolve().then(() => active && setUrl(localStorage.getItem(KEY)));
    fetch("/api/v1/brand")
      .then((r) => (r.ok ? r.json() : null))
      .then((b: { logo_url: string | null } | null) => {
        if (!active || !b) return;
        if (b.logo_url) localStorage.setItem(KEY, b.logo_url);
        else localStorage.removeItem(KEY);
        setUrl(b.logo_url);
      })
      .catch(() => {});
    return () => {
      active = false;
    };
  }, []);
  return url;
}
