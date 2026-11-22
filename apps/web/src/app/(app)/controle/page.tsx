"use client";
// Contrôle des licences au stade : fonctionne hors connexion une fois l'appareil synchronisé.
import { useLiveQuery } from "dexie-react-hooks";
import { useCallback, useEffect, useRef, useState } from "react";
import { RequireAuth } from "@/components/RequireAuth";
import { useAuth } from "@/lib/auth";
import { type KeySet, type OfflineResult, type StatusEntry, verifyOffline } from "@/lib/licence-verify";
import { db } from "@/lib/offline/db";

export default function ControlePage() {
  return (
    <RequireAuth permission="licence:verify">
      <Controle />
    </RequireAuth>
  );
}

type BarcodeDetectorLike = { detect: (src: CanvasImageSource) => Promise<{ rawValue: string }[]> };

function Controle() {
  const { api } = useAuth();
  const keys = useLiveQuery(() => db.kv.get("licence-keys"));
  const statuses = useLiveQuery(() => db.kv.get("licence-status"));
  const [token, setToken] = useState("");
  const [result, setResult] = useState<OfflineResult | null>(null);
  const [syncError, setSyncError] = useState<string | null>(null);
  const [scanning, setScanning] = useState(false);
  const video = useRef<HTMLVideoElement>(null);

  const sync = useCallback(async () => {
    try {
      const k = await api<KeySet>("/licences/public-keys");
      const st = await api<{ entries: StatusEntry[] }>("/licences/status-list");
      await db.kv.bulkPut([
        { key: "licence-keys", value: k, savedAt: Date.now() },
        { key: "licence-status", value: st.entries, savedAt: Date.now() },
      ]);
      setSyncError(null);
    } catch (e) {
      setSyncError(e instanceof Error ? e.message : "Synchronisation impossible");
    }
  }, [api]);

  useEffect(() => {
    let active = true;
    Promise.resolve().then(() => {
      if (active && navigator.onLine) sync();
    });
    return () => {
      active = false;
    };
  }, [sync]);

  const check = useCallback(
    async (value: string) => {
      if (!keys) {
        setResult({ valid: false, reason: "Appareil non synchronisé : connectez-vous une première fois au réseau" });
        return;
      }
      setResult(await verifyOffline(value, keys.value as KeySet, (statuses?.value as StatusEntry[]) ?? []));
    },
    [keys, statuses],
  );

  async function startScan() {
    const Detector = (window as unknown as { BarcodeDetector?: new (o: object) => BarcodeDetectorLike }).BarcodeDetector;
    if (!Detector) {
      setResult({ valid: false, reason: "Lecture caméra non prise en charge : saisir ou coller le code" });
      return;
    }
    const stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: "environment" } });
    setScanning(true);
    const detector = new Detector({ formats: ["qr_code"] });
    const el = video.current!;
    el.srcObject = stream;
    await el.play();
    const stop = () => {
      stream.getTracks().forEach((t) => t.stop());
      setScanning(false);
    };
    const loop = async () => {
      if (!el.srcObject) return;
      const codes = await detector.detect(el).catch(() => []);
      if (codes[0]) {
        stop();
        setToken(codes[0].rawValue);
        await check(codes[0].rawValue);
      } else requestAnimationFrame(loop);
    };
    loop();
  }

  return (
    <div className="mx-auto max-w-3xl space-y-4">
      <h1 className="text-xl font-black tracking-tight text-pitch">Contrôle des licences</h1>
      <p className="text-xs text-stone-500">
        {keys
          ? `Appareil synchronisé le ${new Date(keys.savedAt).toLocaleString("fr-FR")} — vérification possible hors connexion.`
          : "Appareil non synchronisé."}{" "}
        <button type="button" className="underline" onClick={sync}>
          Synchroniser
        </button>
      </p>
      {syncError && <p className="text-sm text-lds-red">{syncError}</p>}

      <video ref={video} className={scanning ? "w-full rounded" : "hidden"} muted playsInline />
      <button type="button" onClick={startScan} className="w-full rounded-lg bg-lds-green py-3 font-bold text-white">
        Scanner un QR code
      </button>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          check(token);
        }}
        className="space-y-2"
      >
        <label className="block text-sm">
          …ou coller le contenu du QR code
          <textarea value={token} onChange={(e) => setToken(e.target.value)} rows={3} className="mt-1 w-full rounded border p-2 font-mono text-xs" />
        </label>
        <button type="submit" className="rounded bg-stone-800 px-4 py-2 text-sm font-semibold text-white">
          Vérifier
        </button>
      </form>

      {result && (
        <div role="alert" className={`rounded-xl p-4 text-white ${result.valid ? "bg-green-700" : "bg-lds-red"}`}>
          <p className="text-2xl font-bold">{result.valid ? "✓ " : "✗ "}{result.reason}</p>
          {result.payload && (
            <dl className="mt-2 grid grid-cols-[auto_1fr] gap-x-3 text-sm">
              <dt>Nom</dt>
              <dd className="font-semibold">{result.payload.nm}</dd>
              <dt>Équipe</dt>
              <dd>{result.payload.tm}</dd>
              <dt>Qualité</dt>
              <dd>
                {result.payload.r === "J" ? "Joueur" : "Encadreur"}
                {result.payload.no ? ` · n° ${result.payload.no}` : ""}
              </dd>
              <dt>Licence</dt>
              <dd>
                {result.payload.n} (jusqu&apos;au {result.payload.vu})
              </dd>
            </dl>
          )}
          <p className="mt-2 text-xs opacity-90">Comparer le nom avec la pièce d&apos;identité présentée.</p>
        </div>
      )}
    </div>
  );
}
