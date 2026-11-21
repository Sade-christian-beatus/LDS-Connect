"use client";
// Feuille de match utilisable hors connexion : cache local + file d'actions synchronisée.
import { useLiveQuery } from "dexie-react-hooks";
import { useCallback, useEffect, useRef, useState } from "react";
import { ApiError, NetworkError, useAuth } from "../auth";
import type { Sheet } from "../types";
import { applyPending } from "./apply";
import { type QueuedOp, db } from "./db";

function endpoint(matchId: string, op: QueuedOp): { path: string; method: string; body?: unknown } {
  const base = `/matches/${matchId}/sheet`;
  switch (op.kind) {
    case "lineup":
      return { path: `${base}/lineup/${op.teamId}`, method: "PUT", body: op.body };
    case "header":
      return { path: base, method: "PATCH", body: op.body };
    case "submit":
      return { path: `${base}/submit`, method: "POST" };
    case "reopen":
      return { path: `${base}/reopen`, method: "POST" };
    case "event":
      return { path: `${base}/events`, method: "POST", body: op.body };
    case "delete_event":
      return { path: `${base}/events/${op.eventId}`, method: "DELETE" };
    case "validate":
      return { path: `${base}/validate`, method: "POST" };
  }
}

export function useOnline(): boolean {
  const [online, setOnline] = useState(true);
  useEffect(() => {
    const update = () => setOnline(navigator.onLine);
    update();
    window.addEventListener("online", update);
    window.addEventListener("offline", update);
    return () => {
      window.removeEventListener("online", update);
      window.removeEventListener("offline", update);
    };
  }, []);
  return online;
}

export function useSheet(matchId: string) {
  const { api } = useAuth();
  const online = useOnline();
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const syncing = useRef(false);

  const cached = useLiveQuery(() => db.sheets.get(matchId), [matchId]);
  const queue = useLiveQuery(
    () => db.queue.where("matchId").equals(matchId).sortBy("id"),
    [matchId],
    [],
  );

  const save = useCallback(
    (sheet: Sheet) => db.sheets.put({ matchId, sheet, savedAt: Date.now() }),
    [matchId],
  );

  const rerun = useRef(false);

  /** Rejoue la file dans l'ordre ; s'arrête à la première erreur. Une action ajoutée pendant
   *  une synchronisation en cours est traitée dans la foulée (pas d'attente du cycle suivant). */
  const sync = useCallback(async () => {
    if (syncing.current) {
      rerun.current = true;
      return;
    }
    syncing.current = true;
    try {
      let blocked = false;
      do {
        rerun.current = false;
        const items = await db.queue.where("matchId").equals(matchId).sortBy("id");
        for (const item of items) {
          if (item.state === "failed") {
            blocked = true;
            break;
          }
          const { path, method, body } = endpoint(matchId, item.op);
          try {
            const sheet = await api<Sheet>(path, {
              method,
              body: body === undefined ? undefined : JSON.stringify(body),
            });
            await db.transaction("rw", db.queue, db.sheets, async () => {
              await db.queue.delete(item.id!);
              await save(sheet);
            });
          } catch (e) {
            blocked = true;
            if (e instanceof NetworkError) break; // on réessaiera au retour du réseau
            const msg = e instanceof ApiError ? e.message : "Erreur inattendue";
            await db.queue.update(item.id!, { state: "failed", error: msg });
            break;
          }
        }
      } while (rerun.current && !blocked);
    } finally {
      syncing.current = false;
    }
  }, [api, matchId, save]);

  const reload = useCallback(async () => {
    try {
      await sync();
      const pending = await db.queue.where("matchId").equals(matchId).count();
      if (pending === 0) await save(await api<Sheet>(`/matches/${matchId}/sheet`));
      setError(null);
    } catch (e) {
      if (!(e instanceof NetworkError)) setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }, [api, matchId, save, sync]);

  useEffect(() => {
    // Chargement asynchrone (cache local puis serveur), annulé si l'écran est quitté
    let active = true;
    Promise.resolve().then(() => {
      if (active) reload();
    });
    return () => {
      active = false;
    };
  }, [reload]);

  useEffect(() => {
    if (online) sync();
    const t = setInterval(() => navigator.onLine && sync(), 15_000);
    return () => clearInterval(t);
  }, [online, sync]);

  const enqueue = useCallback(
    async (op: QueuedOp) => {
      // Enregistrement local immédiat ; l'envoi au serveur part en arrière-plan, pour que
      // l'écran reste disponible (saisie de l'action suivante) même sur un réseau lent.
      await db.queue.add({ matchId, op, createdAt: Date.now(), state: "pending" });
      if (navigator.onLine) void sync();
    },
    [matchId, sync],
  );

  const discardFailed = useCallback(async () => {
    const failed = await db.queue
      .where("matchId")
      .equals(matchId)
      .filter((i) => i.state === "failed")
      .toArray();
    // L'action refusée et toutes les suivantes (elles pouvaient en dépendre) sont retirées
    if (failed.length) {
      const firstId = Math.min(...failed.map((f) => f.id!));
      await db.queue.where("matchId").equals(matchId).and((i) => i.id! >= firstId).delete();
    }
    await reload();
  }, [matchId, reload]);

  const sheet = cached ? applyPending(cached.sheet, queue ?? []) : null;
  const failed = (queue ?? []).find((q) => q.state === "failed") ?? null;
  const pendingCount = (queue ?? []).length;

  return { sheet, loading, error, online, pendingCount, failed, enqueue, reload, discardFailed };
}
