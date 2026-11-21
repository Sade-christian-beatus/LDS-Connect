// Accès à l'API depuis les composants serveur (rendu à la requête, jamais au build).
import "server-only";
import { connection } from "next/server";

const API = process.env.API_INTERNAL_URL ?? "http://127.0.0.1:8000";

export class ApiUnavailable extends Error {}

export async function apiGet<T>(path: string): Promise<T> {
  // Les données changent en cours de match : rendu à chaque requête.
  await connection();
  let res: Response;
  try {
    res = await fetch(`${API}/api/v1${path}`, { cache: "no-store" });
  } catch {
    throw new ApiUnavailable("API injoignable");
  }
  if (res.status === 404) {
    const { notFound } = await import("next/navigation");
    notFound();
  }
  if (!res.ok) throw new ApiUnavailable(`API : erreur ${res.status}`);
  return (await res.json()) as T;
}
