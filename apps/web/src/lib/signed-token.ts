// Jetons signés LDS (licences LDS1, billets LDT1, accréditations LDA1) : vérification de la
// signature Ed25519 sans réseau, avec les clés publiques mises en cache.
// Même format que l'API (apps/api/src/lds_api/domain/signed_token.py).
import { verifyAsync } from "@noble/ed25519";

export type KeySet = { prefix: string; keys: { kid: string; x: string }[] };

export type Decoded<P> =
  | { ok: true; prefix: string; payload: P }
  | { ok: false; reason: string; prefix?: string; payload?: P };

export function b64urlDecode(s: string): Uint8Array {
  const b64 = s.replace(/-/g, "+").replace(/_/g, "/") + "=".repeat((4 - (s.length % 4)) % 4);
  const bin = atob(b64);
  return Uint8Array.from(bin, (c) => c.charCodeAt(0));
}

export async function verifyToken<P extends { kid: string }>(
  token: string,
  prefixes: string[],
  keys: KeySet["keys"],
): Promise<Decoded<P>> {
  const parts = token.trim().split(".");
  if (parts.length !== 3 || !prefixes.includes(parts[0])) {
    return { ok: false, reason: "QR code non reconnu" };
  }
  let payload: P;
  let signature: Uint8Array;
  try {
    payload = JSON.parse(new TextDecoder().decode(b64urlDecode(parts[1])));
    signature = b64urlDecode(parts[2]);
  } catch {
    return { ok: false, reason: "QR code illisible" };
  }
  const key = keys.find((k) => k.kid === payload.kid);
  if (!key) return { ok: false, reason: "Clé de signature inconnue : synchroniser l'appareil", prefix: parts[0], payload };
  let valid = false;
  try {
    valid = await verifyAsync(signature, new TextEncoder().encode(`${parts[0]}.${parts[1]}`), b64urlDecode(key.x));
  } catch {
    valid = false;
  }
  if (!valid) return { ok: false, reason: "Signature invalide : QR falsifié", prefix: parts[0], payload };
  return { ok: true, prefix: parts[0], payload };
}
