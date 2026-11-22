// Vérification d'une licence SANS réseau : signature Ed25519 avec les clés publiques mises
// en cache, puis liste d'état (licences suspendues/révoquées) synchronisée auparavant.
// Même format que l'API (apps/api/src/lds_api/domain/signed_token.py).
import { type KeySet, verifyToken } from "./signed-token";

export type { KeySet };

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

export type StatusEntry = { n: string; status: string };

export async function verifyOffline(
  token: string,
  keySet: KeySet,
  statusList: StatusEntry[],
  today: string = new Date().toISOString().slice(0, 10),
): Promise<OfflineResult> {
  const decoded = await verifyToken<LicencePayload>(token, [keySet.prefix], keySet.keys);
  if (!decoded.ok) {
    const reason = decoded.reason.startsWith("Signature")
      ? "FAUSSE LICENCE : signature invalide"
      : decoded.reason === "QR code non reconnu"
        ? "QR code non reconnu (ce n'est pas une licence LDS)"
        : decoded.reason;
    return { valid: false, reason, payload: decoded.payload };
  }
  const payload = decoded.payload;

  const status = statusList.find((e) => e.n === payload.n);
  if (status) {
    const label = status.status === "suspended" ? "suspendue" : status.status === "revoked" ? "révoquée" : status.status;
    return { valid: false, reason: `Licence ${label}`, payload };
  }
  if (today < payload.vf) return { valid: false, reason: `Licence valide à partir du ${payload.vf}`, payload };
  if (today > payload.vu) return { valid: false, reason: "Licence expirée", payload };
  return { valid: true, reason: "Licence valide", payload };
}
