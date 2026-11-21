"use client";
// Scores en direct : flux SSE de l'API (/api/v1/live), reconnexion automatique du navigateur.
import { useEffect, useState } from "react";
import type { Match } from "@/lib/types";
import { MatchCard } from "./MatchCard";

export function LiveScores({ initial }: { initial: Match[] }) {
  const [matches, setMatches] = useState<Record<string, Match>>(() =>
    Object.fromEntries(initial.map((m) => [m.id, m])),
  );

  useEffect(() => {
    const source = new EventSource("/api/v1/live");
    source.addEventListener("match", (ev) => {
      try {
        const m: Match = JSON.parse((ev as MessageEvent).data);
        setMatches((prev) => ({ ...prev, [m.id]: m }));
      } catch {
        /* message ignoré */
      }
    });
    return () => source.close();
  }, []);

  const live = Object.values(matches).filter((m) => m.status === "live");
  if (live.length === 0) return null;
  return (
    <section aria-live="polite" className="space-y-2">
      <h2 className="flex items-center gap-2 text-lg font-bold text-lds-red">
        <span className="h-2 w-2 animate-pulse rounded-full bg-lds-red" /> En direct
      </h2>
      {live.map((m) => (
        <MatchCard key={m.id} match={m} />
      ))}
    </section>
  );
}
