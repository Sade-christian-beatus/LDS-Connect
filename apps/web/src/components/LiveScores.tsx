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
    <section aria-live="polite" className="space-y-3">
      <h2 className="flex items-center gap-2 text-xl font-black tracking-tight text-lds-red">
        <span className="relative flex h-3 w-3">
          <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-lds-red opacity-60" />
          <span className="relative inline-flex h-3 w-3 rounded-full bg-lds-red" />
        </span>
        En direct
      </h2>
      <div className="grid gap-3 md:grid-cols-2">
        {live.map((m) => (
          <MatchCard key={m.id} match={m} />
        ))}
      </div>
    </section>
  );
}
