// Application locale (optimiste) des actions en attente sur la dernière feuille reçue du serveur.
// Fonction pure : le serveur reste la référence, ceci ne sert qu'à l'affichage hors connexion.
import type { Sheet, SheetEvent } from "../types";
import type { QueueItem } from "./db";

const GOALS = new Set(["goal", "penalty_goal"]);

export function liveScore(sheet: Sheet): [number, number] {
  const home = sheet.home.team.id;
  let h = 0;
  let a = 0;
  for (const e of sheet.events) {
    const forHome = GOALS.has(e.type) ? e.team_id === home : e.type === "own_goal" ? e.team_id !== home : null;
    if (forHome === true) h++;
    else if (forHome === false) a++;
  }
  return [h, a];
}

function nameOf(sheet: Sheet, personId: string | null | undefined): string | null {
  if (!personId) return null;
  for (const side of [sheet.home, sheet.away]) {
    const c = side.candidates.find((x) => x.person_id === personId);
    if (c) return c.display_name;
  }
  return "?";
}

export function applyPending(server: Sheet, items: QueueItem[]): Sheet {
  let s: Sheet = structuredClone(server);
  for (const item of items) {
    const op = item.op;
    switch (op.kind) {
      case "lineup": {
        const side = s.home.team.id === op.teamId ? "home" : "away";
        const cands = s[side].candidates;
        s[side].lineup = (op.body.entries as Sheet["home"]["lineup"]).map((e) => {
          const c = cands.find((x) => x.person_id === e.person_id);
          return { ...e, display_name: c?.display_name ?? "?", is_local: c?.is_local ?? false };
        });
        break;
      }
      case "header":
        s = { ...s, ...(op.body as Partial<Sheet>) };
        break;
      case "submit":
        s.status = "submitted";
        s.match.status = "live";
        break;
      case "reopen":
        s.status = "draft";
        s.match.status = "scheduled";
        break;
      case "validate":
        s.status = "validated";
        s.match.status = "finished";
        break;
      case "event": {
        const b = op.body as Record<string, string | number | null>;
        if (s.events.some((e) => e.client_uuid === b.client_uuid)) break;
        const ev: SheetEvent = {
          id: String(b.client_uuid),
          client_uuid: String(b.client_uuid),
          team_id: String(b.team_id),
          type: b.type as SheetEvent["type"],
          minute: Number(b.minute),
          added_time: (b.added_time as number | null) ?? null,
          person_id: String(b.person_id),
          person_name: nameOf(s, b.person_id as string) ?? "?",
          related_person_id: (b.related_person_id as string | null) ?? null,
          related_person_name: nameOf(s, b.related_person_id as string | null),
        };
        s.events = [...s.events, ev].sort(
          (x, y) => x.minute - y.minute || (x.added_time ?? 0) - (y.added_time ?? 0),
        );
        break;
      }
      case "delete_event":
        s.events = s.events.filter((e) => e.id !== op.eventId);
        break;
    }
  }
  const [h, a] = liveScore(s);
  if (s.status !== "draft") {
    s.match.home_score = h;
    s.match.away_score = a;
  }
  return s;
}
