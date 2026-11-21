"use client";
// Chargement de données authentifiées (écrans d'administration, en ligne uniquement).
import { useCallback, useEffect, useState } from "react";
import { useAuth } from "./auth";

export function useApi<T>(path: string | null) {
  const { api } = useAuth();
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [version, setVersion] = useState(0);

  useEffect(() => {
    if (!path) return;
    let active = true;
    api<T>(path)
      .then((d) => {
        if (!active) return;
        setData(d);
        setError(null);
      })
      .catch((e: Error) => active && setError(e.message));
    return () => {
      active = false;
    };
  }, [api, path, version]);

  const reload = useCallback(() => setVersion((v) => v + 1), []);
  return { data, error, reload, loading: data === null && error === null };
}
