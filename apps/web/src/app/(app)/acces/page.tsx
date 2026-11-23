"use client";
// Contrôle des entrées au stade (billets et accréditations). Fonctionne hors connexion une
// fois l'appareil préparé pour le match ; les passages sont synchronisés dès que possible.
import { useLiveQuery } from "dexie-react-hooks";
import { useCallback, useEffect, useRef, useState } from "react";
import { RequireAuth } from "@/components/RequireAuth";
import { type Decision, decide, KEYS_KEY, manifestKey, recordScan, syncScans } from "@/lib/access";
import { useAuth } from "@/lib/auth";
import { formatDate, formatTime } from "@/lib/format";
import { db, type LocalScan } from "@/lib/offline/db";
import { useOnline } from "@/lib/offline/use-sheet";
import type { KeySet } from "@/lib/signed-token";
import type { AccessManifest, AccessStats, Match } from "@/lib/types";

export default function AccesPage() {
  return (
    <RequireAuth permission="access:scan">
      <Acces />
    </RequireAuth>
  );
}

type BarcodeDetectorLike = { detect: (src: CanvasImageSource) => Promise<{ rawValue: string }[]> };

const TONE: Record<LocalScan["result"], { bg: string; icon: string; title: string }> = {
  admitted: { bg: "bg-green-700", icon: "✓", title: "ENTRÉE AUTORISÉE" },
  duplicate: { bg: "bg-amber-600", icon: "⚠", title: "DÉJÀ ENTRÉ" },
  invalid: { bg: "bg-lds-red", icon: "✗", title: "REFUSÉ" },
  wrong_match: { bg: "bg-lds-red", icon: "✗", title: "MAUVAIS MATCH" },
};

function matchLabel(m: Match) {
  return `${m.home?.short_name ?? "?"} – ${m.away?.short_name ?? "?"}`;
}

function Acces() {
  const { api } = useAuth();
  const online = useOnline();
  const [matchId, setMatchId] = useState<string>("");
  const [device, setDevice] = useState<string>("");
  const [current, setCurrent] = useState<(Decision & { at: string }) | null>(null);
  const [token, setToken] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [scanning, setScanning] = useState(false);
  const [stats, setStats] = useState<AccessStats | null>(null);
  const video = useRef<HTMLVideoElement>(null);
  const stopRef = useRef<() => void>(() => {});

  const matches = useLiveQuery(() => db.kv.get("access-matches"));
  const keys = useLiveQuery(() => db.kv.get(KEYS_KEY));
  const manifest = useLiveQuery(() => (matchId ? db.kv.get(manifestKey(matchId)) : undefined), [matchId]);
  const history = useLiveQuery(
    () => (matchId ? db.scans.where("matchId").equals(matchId).reverse().sortBy("scannedAt") : []),
    [matchId],
  );
  const pending = history?.filter((s) => !s.synced).length ?? 0;
  const admittedHere = history?.filter((s) => (s.serverResult ?? s.result) === "admitted").length ?? 0;

  // Préférences de l'appareil (match et nom de la porte) conservées localement
  useEffect(() => {
    Promise.resolve().then(() => {
      setMatchId(localStorage.getItem("lds-access-match") ?? "");
      setDevice(localStorage.getItem("lds-access-device") ?? "");
    });
  }, []);

  const refreshMatches = useCallback(async () => {
    try {
      const list = await api<Match[]>("/access/matches");
      await db.kv.put({ key: "access-matches", value: list, savedAt: Date.now() });
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  }, [api]);

  const prepare = useCallback(async () => {
    if (!matchId) return;
    setError(null);
    try {
      const [k, m] = await Promise.all([
        api<KeySet>("/licences/public-keys"),
        api<AccessManifest>(`/access/matches/${matchId}/manifest`),
      ]);
      await db.kv.bulkPut([
        { key: KEYS_KEY, value: k, savedAt: Date.now() },
        { key: manifestKey(matchId), value: m, savedAt: Date.now() },
      ]);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Préparation impossible : réseau indisponible");
    }
  }, [api, matchId]);

  const sync = useCallback(async () => {
    try {
      await syncScans(api);
      if (matchId) setStats(await api<AccessStats>(`/access/matches/${matchId}/stats`));
    } catch {
      /* hors ligne : nouvel essai plus tard */
    }
  }, [api, matchId]);

  useEffect(() => {
    if (!online) return;
    Promise.resolve().then(() => {
      refreshMatches();
      sync();
    });
    const t = setInterval(sync, 10_000);
    return () => clearInterval(t);
  }, [online, refreshMatches, sync]);

  const check = useCallback(
    async (value: string) => {
      if (!value.trim()) return;
      const k = keys?.value as KeySet | undefined;
      if (!k || !matchId) {
        setError("Préparez d'abord l'appareil pour un match (réseau nécessaire une fois).");
        return;
      }
      const d = await decide(value, { matchId, keys: k.keys, manifest: (manifest?.value as AccessManifest) ?? null });
      const scan = await recordScan(value, d, { matchId, device: device || "Appareil", offline: !navigator.onLine });
      setCurrent({ ...d, at: scan.scannedAt });
      if (navigator.onLine) sync();
    },
    [keys, manifest, matchId, device, sync],
  );

  async function startScan() {
    const Detector = (window as unknown as { BarcodeDetector?: new (o: object) => BarcodeDetectorLike }).BarcodeDetector;
    if (!Detector) {
      setError("Lecture caméra non prise en charge sur ce navigateur : coller le contenu du QR code.");
      return;
    }
    const stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: "environment" } });
    const detector = new Detector({ formats: ["qr_code"] });
    const el = video.current!;
    el.srcObject = stream;
    await el.play();
    setScanning(true);
    let last = "";
    let lastAt = 0;
    let running = true;
    stopRef.current = () => {
      running = false;
      stream.getTracks().forEach((t) => t.stop());
      el.srcObject = null;
      setScanning(false);
    };
    // Lecture en continu : un même QR n'est pas relu pendant 3 secondes
    const loop = async () => {
      if (!running) return;
      const codes = await detector.detect(el).catch(() => []);
      const value = codes[0]?.rawValue;
      if (value && (value !== last || Date.now() - lastAt > 3000)) {
        last = value;
        lastAt = Date.now();
        await check(value);
      }
      setTimeout(loop, 250);
    };
    loop();
  }

  useEffect(() => () => stopRef.current(), []);

  const matchList = (matches?.value as Match[] | undefined) ?? [];
  const m = manifest?.value as AccessManifest | undefined;
  const tone = current ? TONE[current.result] : null;

  return (
    <div className="mx-auto max-w-3xl space-y-4">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h1 className="text-xl font-bold text-green-900">Contrôle des entrées</h1>
        <span className={`rounded-full px-2 py-0.5 text-xs font-semibold ${online ? "bg-green-100 text-green-800" : "bg-amber-100 text-amber-900"}`}>
          {online ? "En ligne" : "Hors ligne — les passages sont gardés sur l'appareil"}
        </span>
      </div>

      <section className="grid gap-3 rounded-lg border border-stone-200 bg-white p-3 sm:grid-cols-[1fr_12rem_auto] sm:items-end">
        <label className="text-sm">
          Match
          <select
            className="mt-1 w-full rounded border border-stone-300 px-2 py-2"
            value={matchId}
            onChange={(e) => {
              setMatchId(e.target.value);
              localStorage.setItem("lds-access-match", e.target.value);
              setCurrent(null);
              setStats(null);
            }}
          >
            <option value="">— choisir le match —</option>
            {matchList.map((x) => (
              <option key={x.id} value={x.id}>
                {matchLabel(x)} · {formatDate(x.kickoff_at)} {formatTime(x.kickoff_at)}
              </option>
            ))}
          </select>
        </label>
        <label className="text-sm">
          Porte / appareil
          <input
            className="mt-1 w-full rounded border border-stone-300 px-2 py-2"
            placeholder="Porte A"
            value={device}
            onChange={(e) => {
              setDevice(e.target.value);
              localStorage.setItem("lds-access-device", e.target.value);
            }}
          />
        </label>
        <button
          type="button"
          onClick={prepare}
          disabled={!matchId || !online}
          className="rounded bg-stone-800 px-3 py-2 text-sm font-semibold text-white disabled:opacity-50"
        >
          Préparer l&apos;appareil
        </button>
        <p className="text-xs text-stone-600 sm:col-span-3">
          {m
            ? `Prêt hors ligne : ${m.tickets.length} billet(s) connus, préparé le ${new Date(manifest!.savedAt).toLocaleString("fr-FR")}.`
            : matchId
              ? "Appareil pas encore préparé pour ce match : appuyez sur « Préparer l'appareil » avant l'ouverture des portes."
              : "Choisissez le match contrôlé."}
          {pending > 0 && ` · ${pending} passage(s) à synchroniser.`}
        </p>
      </section>

      {error && (
        <p role="alert" className="rounded bg-red-50 p-2 text-sm text-lds-red">
          {error}
        </p>
      )}

      <video ref={video} className={scanning ? "w-full rounded-lg bg-black" : "hidden"} muted playsInline />
      <div className="flex gap-2">
        {!scanning ? (
          <button type="button" onClick={startScan} disabled={!matchId} className="flex-1 rounded-lg bg-lds-green py-4 text-lg font-bold text-white disabled:opacity-50">
            Scanner les billets
          </button>
        ) : (
          <button type="button" onClick={() => stopRef.current()} className="flex-1 rounded-lg bg-stone-800 py-4 text-lg font-bold text-white">
            Arrêter la caméra
          </button>
        )}
      </div>
      <form
        className="flex gap-2"
        onSubmit={(e) => {
          e.preventDefault();
          check(token);
          setToken("");
        }}
      >
        <input
          aria-label="Contenu du QR code"
          placeholder="…ou coller le contenu du QR code"
          value={token}
          onChange={(e) => setToken(e.target.value)}
          className="flex-1 rounded border border-stone-300 px-2 py-2 font-mono text-xs"
        />
        <button type="submit" className="rounded bg-stone-800 px-4 text-sm font-semibold text-white">
          Vérifier
        </button>
      </form>

      {current && tone && (
        <div role="alert" aria-live="assertive" aria-label="Résultat du contrôle" className={`rounded-xl p-5 text-white shadow ${tone.bg}`}>
          <p className="text-3xl font-black tracking-tight">
            {tone.icon} {tone.title}
          </p>
          <p className="mt-1 text-lg">{current.detail}</p>
          {current.label && (
            <p className="mt-2 text-sm opacity-90">
              {current.kind === "accreditation" ? "Accrédité : " : "Catégorie : "}
              <strong>{current.label}</strong>
              {current.code && <span className="ml-2 font-mono">{current.code}</span>}
            </p>
          )}
          {current.zones && current.zones.length > 0 && <p className="text-sm">Zones : {current.zones.join(", ")}</p>}
          {current.kind === "accreditation" && current.result === "admitted" && (
            <p className="mt-1 text-xs opacity-90">Vérifier la pièce d&apos;identité.</p>
          )}
        </div>
      )}

      <section className="grid grid-cols-3 gap-2 text-center">
        <Stat label="Entrées (cet appareil)" value={admittedHere} />
        <Stat label="Entrées (toutes portes)" value={stats ? stats.admitted + stats.accreditations_admitted : "—"} />
        <Stat label="Billets vendus" value={stats?.tickets_sold ?? m?.tickets.length ?? "—"} />
      </section>

      {history && history.length > 0 && (
        <section>
          <h2 className="mb-1 text-sm font-semibold text-stone-700">Derniers passages</h2>
          <ul className="divide-y divide-stone-100 rounded-lg border border-stone-200 bg-white text-sm">
            {history.slice(0, 15).map((s) => {
              const r = s.serverResult ?? s.result;
              return (
                <li key={s.clientId} className="flex items-center gap-2 px-3 py-2">
                  <span className={`h-2.5 w-2.5 shrink-0 rounded-full ${r === "admitted" ? "bg-green-600" : r === "duplicate" ? "bg-amber-500" : "bg-lds-red"}`} />
                  <span className="w-12 text-stone-500">{formatTime(s.scannedAt)}</span>
                  <span className="flex-1 truncate">
                    {s.label ?? "QR inconnu"} {s.code && <span className="font-mono text-xs text-stone-500">{s.code}</span>}
                    {s.serverResult && <span className="block text-xs text-amber-800">Corrigé par le serveur : {s.serverDetail}</span>}
                  </span>
                  <span className="text-xs text-stone-500">{s.synced ? "synchronisé" : "en attente"}</span>
                </li>
              );
            })}
          </ul>
        </section>
      )}
    </div>
  );
}

function Stat({ label, value }: { label: string; value: number | string }) {
  return (
    <div className="rounded-lg border border-stone-200 bg-white p-2">
      <p className="text-2xl font-bold text-green-900">{value}</p>
      <p className="text-xs text-stone-600">{label}</p>
    </div>
  );
}
