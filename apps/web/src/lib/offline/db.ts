// Base locale IndexedDB (Dexie) : feuilles de match en cache et file d'actions hors ligne.
import Dexie, { type EntityTable } from "dexie";
import type { DelegateMatch, Sheet } from "../types";

export type QueuedOp =
  | { kind: "lineup"; teamId: string; body: { entries: unknown[] } }
  | { kind: "header"; body: Record<string, unknown> }
  | { kind: "submit" }
  | { kind: "reopen" }
  | { kind: "event"; body: Record<string, unknown> & { client_uuid: string } }
  | { kind: "delete_event"; eventId: string }
  | { kind: "validate" };

export type QueueItem = {
  id?: number;
  matchId: string;
  op: QueuedOp;
  createdAt: number;
  state: "pending" | "failed";
  error?: string;
};

export type CachedSheet = { matchId: string; sheet: Sheet; savedAt: number };
export type CachedList = { key: string; matches: DelegateMatch[]; savedAt: number };
export type CachedKeys = { key: string; value: unknown; savedAt: number };

class LdsDb extends Dexie {
  sheets!: EntityTable<CachedSheet, "matchId">;
  queue!: EntityTable<QueueItem, "id">;
  lists!: EntityTable<CachedList, "key">;
  kv!: EntityTable<CachedKeys, "key">;

  constructor() {
    super("lds-connect");
    this.version(1).stores({
      sheets: "matchId",
      queue: "++id, matchId, state",
      lists: "key",
      kv: "key",
    });
  }
}

export const db = new LdsDb();
