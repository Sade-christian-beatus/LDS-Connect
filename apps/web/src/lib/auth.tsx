"use client";
// Authentification côté navigateur : jeton d'accès en mémoire, jeton de rafraîchissement
// dans un cookie httpOnly (inaccessible au JavaScript). Voir docs/ARCHITECTURE.md.
import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from "react";
import { db } from "./offline/db";
import type { TokenOut, User } from "./types";

const ME_KEY = "me";
const rememberUser = (u: User) => db.kv.put({ key: ME_KEY, value: u, savedAt: Date.now() });
const forgetUser = () => db.kv.delete(ME_KEY);

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
    public code?: string,
    public details?: unknown,
  ) {
    super(message);
  }
}

/** Erreur réseau (hors connexion) : l'action peut être rejouée plus tard. */
export class NetworkError extends Error {}

type AuthState = {
  user: User | null;
  ready: boolean;
  login: (email: string, password: string) => Promise<User>;
  logout: () => Promise<void>;
  api: <T>(path: string, init?: RequestInit) => Promise<T>;
};

const AuthContext = createContext<AuthState | null>(null);

async function parseError(res: Response): Promise<ApiError> {
  let body: { detail?: unknown; code?: string; details?: unknown } = {};
  try {
    body = await res.json();
  } catch {
    /* corps vide */
  }
  const detail =
    typeof body.detail === "string"
      ? body.detail
      : Array.isArray(body.detail)
        ? "Données invalides"
        : `Erreur ${res.status}`;
  return new ApiError(res.status, detail, body.code, body.details);
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [ready, setReady] = useState(false);
  const token = useRef<string | null>(null);
  const refreshing = useRef<Promise<boolean> | null>(null);

  const refresh = useCallback(async (): Promise<boolean> => {
    if (!refreshing.current) {
      refreshing.current = (async () => {
        try {
          const res = await fetch("/api/v1/auth/refresh", { method: "POST", credentials: "include" });
          if (!res.ok) {
            token.current = null;
            setUser(null);
            await forgetUser();
            return false;
          }
          const data: TokenOut = await res.json();
          token.current = data.access_token;
          setUser(data.user);
          await rememberUser(data.user);
          return true;
        } catch {
          // Hors connexion : on reprend le dernier profil connu sur cet appareil (lecture
          // des données en cache) ; les actions attendront le retour du réseau.
          const cached = await db.kv.get(ME_KEY);
          if (cached) setUser((prev) => prev ?? (cached.value as User));
          return false;
        } finally {
          refreshing.current = null;
        }
      })();
    }
    return refreshing.current;
  }, []);

  useEffect(() => {
    refresh().finally(() => setReady(true));
  }, [refresh]);

  const api = useCallback(
    async <T,>(path: string, init: RequestInit = {}): Promise<T> => {
      const doFetch = () =>
        fetch(`/api/v1${path}`, {
          ...init,
          credentials: "include",
          headers: {
            "Content-Type": "application/json",
            ...(token.current ? { Authorization: `Bearer ${token.current}` } : {}),
            ...init.headers,
          },
        });
      let res: Response;
      try {
        res = await doFetch();
        if (res.status === 401 && (await refresh())) res = await doFetch();
      } catch {
        throw new NetworkError("Hors connexion");
      }
      if (!res.ok) throw await parseError(res);
      if (res.status === 204) return undefined as T;
      return (await res.json()) as T;
    },
    [refresh],
  );

  const login = useCallback(async (email: string, password: string) => {
    let res: Response;
    try {
      res = await fetch("/api/v1/auth/login", {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });
    } catch {
      throw new NetworkError("Connexion impossible : vérifiez le réseau");
    }
    if (!res.ok) throw await parseError(res);
    const data: TokenOut = await res.json();
    token.current = data.access_token;
    setUser(data.user);
    await rememberUser(data.user);
    return data.user;
  }, []);

  const logout = useCallback(async () => {
    try {
      await fetch("/api/v1/auth/logout", { method: "POST", credentials: "include" });
    } finally {
      token.current = null;
      setUser(null);
      await forgetUser();
    }
  }, []);

  const value = useMemo(() => ({ user, ready, login, logout, api }), [user, ready, login, logout, api]);
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth doit être utilisé dans <AuthProvider>");
  return ctx;
}
