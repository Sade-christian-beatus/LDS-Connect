// Contrôle des entrées au stade (billets LDT1, accréditations LDA1), hors ligne d'abord :
// l'appareil décide seul avec le manifeste du match et les clés publiques, garde chaque
// passage dans IndexedDB, puis les envoie au serveur dès que le réseau revient. Le serveur
// tranche en dernier (double entrée vue par une autre porte, billet annulé entre-temps).
import type { AccessManifest, ScanOut } from "./types";
import { db, type LocalScan } from "./offline/db";
import { type KeySet, verifyToken } from "./signed-token";

export const TICKET_PREFIX = "LDT1";
export const ACCREDITATION_PREFIX = "LDA1";

type TicketPayload = { kid: string; c: string; m: string; t: string; s: number; mt?: string; d?: string };
type AccreditationPayload = {
  kid: string;
  c: string;
  nm: string;
  cat: string;
  z: string[];
  vf: string;
  vu: string;
  org?: string;
};

// Zones réservées du stade. Une porte sans zone est une entrée du public (tribunes).
export const ZONES = ["Pelouse", "Vestiaires", "Tribune de presse", "Zone mixte", "Tribune d'honneur"];
export const ALL_ZONES = "Toutes zones";

/** Même règle que le serveur (domain/ticketing.py, zone_refusal). */
export function zoneRefusal(kind: "ticket" | "accreditation", gateZone: string | undefined, zones: string[] = []): string | null {
  if (!gateZone) return null;
  if (kind === "ticket") return `Billet du public : pas d'accès à la zone « ${gateZone} »`;
  if (zones.includes(ALL_ZONES) || zones.includes(gateZone)) return null;
  return `Zone « ${gateZone} » non autorisée pour cette accréditation`;
}

export const ACCREDITATION_LABEL: Record<string, string> = {
  press: "Presse",
  official: "Officiel",
  team: "Équipe",
  security: "Sécurité",
  volunteer: "Bénévole",
  partner: "Partenaire",
};

export type Decision = Pick<LocalScan, "result" | "detail" | "kind" | "code" | "label"> & { zones?: string[] };

export const manifestKey = (matchId: string) => `access-manifest:${matchId}`;
export const KEYS_KEY = "access-keys";

function hhmm(iso: string) {
  return new Date(iso).toLocaleTimeString("fr-FR", { hour: "2-digit", minute: "2-digit" });
}

/** Décision locale, sans réseau. */
export async function decide(
  token: string,
  ctx: { matchId: string; keys: KeySet["keys"]; manifest: AccessManifest | null; now?: Date; zone?: string },
): Promise<Decision> {
  const now = ctx.now ?? new Date();
  const decoded = await verifyToken<TicketPayload | AccreditationPayload>(
    token,
    [TICKET_PREFIX, ACCREDITATION_PREFIX],
    ctx.keys,
  );
  if (!decoded.ok) return { result: "invalid", detail: decoded.reason, kind: "unknown", code: null, label: null };

  if (decoded.prefix === ACCREDITATION_PREFIX) {
    const a = decoded.payload as AccreditationPayload;
    const base = { kind: "accreditation" as const, code: a.c, label: a.nm, zones: a.z };
    if (ctx.manifest?.revoked_accreditations.includes(a.c)) return { ...base, result: "invalid", detail: "Accréditation révoquée" };
    const today = now.toISOString().slice(0, 10);
    if (today < a.vf || today > a.vu) return { ...base, result: "invalid", detail: "Accréditation hors de sa période de validité" };
    const zoneIssue = zoneRefusal("accreditation", ctx.zone, a.z);
    if (zoneIssue) return { ...base, result: "invalid", detail: zoneIssue };
    const org = a.org ? ` · ${a.org}` : "";
    return { ...base, result: "admitted", detail: `${ACCREDITATION_LABEL[a.cat] ?? a.cat}${org}` };
  }

  const t = decoded.payload as TicketPayload;
  const base = { kind: "ticket" as const, code: t.c, label: t.t };
  if (t.m !== ctx.matchId) {
    return { ...base, result: "wrong_match", detail: `Billet valable pour un autre match${t.mt ? ` (${t.mt})` : ""}` };
  }
  const ticketZone = zoneRefusal("ticket", ctx.zone);
  if (ticketZone) return { ...base, result: "invalid", detail: ticketZone };
  const entry = ctx.manifest?.tickets.find((x) => x.c === t.c);
  if (entry?.s === "cancelled") return { ...base, result: "invalid", detail: "Billet annulé" };
  const local = await db.scans
    .where("code")
    .equals(t.c)
    .filter((s) => s.matchId === ctx.matchId && (s.serverResult ?? s.result) === "admitted")
    .first();
  if (local) return { ...base, result: "duplicate", detail: `Déjà entré à ${hhmm(local.scannedAt)} (${local.device})` };
  if (entry?.e) return { ...base, result: "duplicate", detail: `Déjà entré à ${hhmm(entry.e)}` };
  if (!entry) {
    // Authentique et pour ce match, mais acheté après la préparation de l'appareil
    return { ...base, result: "admitted", detail: "Billet authentique (acheté après la dernière synchronisation)" };
  }
  return { ...base, result: "admitted", detail: "Entrée autorisée" };
}

export async function recordScan(token: string, d: Decision, ctx: { matchId: string; device: string; offline: boolean; zone?: string }) {
  const scan: LocalScan = {
    clientId: crypto.randomUUID(),
    matchId: ctx.matchId,
    token,
    code: d.code,
    kind: d.kind,
    label: d.label,
    result: d.result,
    detail: d.detail,
    scannedAt: new Date().toISOString(),
    device: ctx.device,
    zone: ctx.zone || undefined,
    offline: ctx.offline,
    synced: 0,
  };
  await db.scans.add(scan);
  return scan;
}

type Api = <T>(path: string, init?: RequestInit) => Promise<T>;

/** Envoie les passages en attente (par lots) ; renvoie le nombre synchronisé. */
export async function syncScans(api: Api): Promise<number> {
  const pending = await db.scans.where("synced").equals(0).limit(200).toArray();
  if (!pending.length) return 0;
  const results = await api<ScanOut[]>("/access/scans", {
    method: "POST",
    body: JSON.stringify({
      scans: pending.map((s) => ({
        client_id: s.clientId,
        token: s.token,
        match_id: s.matchId,
        scanned_at: s.scannedAt,
        offline: s.offline,
        device: s.device,
        zone: s.zone ?? null,
      })),
    }),
  });
  const byId = new Map(results.map((r) => [r.client_id, r]));
  await db.transaction("rw", db.scans, async () => {
    for (const s of pending) {
      const r = byId.get(s.clientId);
      if (!r) continue;
      const differs = r.result !== s.result;
      await db.scans.update(s.clientId, {
        synced: 1,
        ...(differs ? { serverResult: r.result, serverDetail: r.detail } : {}),
      });
    }
  });
  return pending.length;
}
