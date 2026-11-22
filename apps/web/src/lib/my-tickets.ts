// « Mes billets » sans compte : les commandes passées sur cet appareil sont gardées dans le
// navigateur (référence + clé d'accès), avec une copie des billets et de leurs QR codes pour
// pouvoir les présenter au stade sans connexion.
import type { TicketOrder } from "./types";

const INDEX = "lds-billets";
const cacheKey = (ref: string) => `lds-billet:${ref}`;

export type SavedOrder = { reference: string; key: string; savedAt: number; label?: string };
export type CachedOrder = { order: TicketOrder; qr: Record<string, string>; savedAt: number };

function read<T>(key: string, fallback: T): T {
  try {
    const raw = localStorage.getItem(key);
    return raw ? (JSON.parse(raw) as T) : fallback;
  } catch {
    return fallback;
  }
}

export function savedOrders(): SavedOrder[] {
  return read<SavedOrder[]>(INDEX, []).sort((a, b) => b.savedAt - a.savedAt);
}

export function rememberOrder(o: SavedOrder) {
  const list = savedOrders().filter((x) => x.reference !== o.reference);
  localStorage.setItem(INDEX, JSON.stringify([{ ...savedOrders().find((x) => x.reference === o.reference), ...o }, ...list]));
}

export function cachedOrder(reference: string): CachedOrder | null {
  return read<CachedOrder | null>(cacheKey(reference), null);
}

export function cacheOrder(reference: string, data: CachedOrder) {
  try {
    localStorage.setItem(cacheKey(reference), JSON.stringify(data));
  } catch {
    /* stockage plein : l'affichage en ligne reste possible */
  }
}

export function forgetOrder(reference: string) {
  localStorage.setItem(INDEX, JSON.stringify(savedOrders().filter((x) => x.reference !== reference)));
  localStorage.removeItem(cacheKey(reference));
}

export function svgDataUrl(svg: string) {
  return `data:image/svg+xml;charset=utf-8,${encodeURIComponent(svg)}`;
}
