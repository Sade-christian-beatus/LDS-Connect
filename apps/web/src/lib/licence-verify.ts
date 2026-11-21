// Vérification d'une licence SANS réseau : signature Ed25519 avec les clés publiques mises
// en cache, puis liste d'état (licences suspendues/révoquées) synchronisée auparavant.
// Même format que l'API (apps/api/src/lds_api/domain/signed_token.py).
import { verifyAsync } from "@noble/ed25519";

export type LicencePayload = {
  kid: string;
  n: string; // numéro
  s: number; // saison
  nm: string; // nom complet
  tm: string; // équipe
  r: "J" | "E"; // joueur / encadreur
  vf: string; // valide du
  vu: string; // valide jusqu'au
  no?: number; // numéro de maillot
};

export type OfflineResult = {
  valid: boolean;
  reason: string;
  payload?: LicencePayload;
};

export type KeySet = { prefix: string; keys: { kid: string; x: string }[] };
export type StatusEntry = { n: string; status: string };

function b64urlDecode(s: string): Uint8Array {
  const b64 = s.replace(/-/g, "+").replace(/_/g, "/") + "=".repeat((4 - (s.length % 4)) % 4);
  const bin = atob(b64);
  return Uint8Array.from(bin, (c) => c.charCodeAt(0));
}

export async function verifyOffline(
  token: string,
  keySet: KeySet,
  statusList: StatusEntry[],
  today: string = new Date().toISOString().slice(0, 10),
): Promise<OfflineResult> {
  const parts = token.trim().split(".");
  if (parts.length !== 3 || parts[0] !== keySet.prefix) {
    return { valid: false, reason: "QR code non reconnu (ce n'est pas une licence LDS)" };
  }
  let payload: LicencePayload;
  let signature: Uint8Array;
  try {
    payload = JSON.parse(new TextDecoder().decode(b64urlDecode(parts[1])));
    signature = b64urlDecode(parts[2]);
  } catch {
    return { valid: false, reason: "QR code illisible" };
  }
  const key = keySet.keys.find((k) => k.kid === payload.kid);
  if (!key) return { valid: false, reason: "Clé de signature inconnue : synchroniser l'appareil", payload };
  const message = new TextEncoder().encode(`${parts[0]}.${parts[1]}`);
  let ok = false;
  try {
    ok = await verifyAsync(signature, message, b64urlDecode(key.x));
  } catch {
    ok = false;
  }
  if (!ok) return { valid: false, reason: "FAUSSE LICENCE : signature invalide", payload };

  const status = statusList.find((e) => e.n === payload.n);
  if (status) {
    const label = status.status === "suspended" ? "suspendue" : status.status === "revoked" ? "révoquée" : status.status;
    return { valid: false, reason: `Licence ${label}`, payload };
  }
  if (today < payload.vf) return { valid: false, reason: `Licence valide à partir du ${payload.vf}`, payload };
  if (today > payload.vu) return { valid: false, reason: "Licence expirée", payload };
  return { valid: true, reason: "Licence valide", payload };
}
