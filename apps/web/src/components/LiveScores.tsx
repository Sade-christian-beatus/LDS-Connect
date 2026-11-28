"use client";
// Scores en direct : flux SSE de l'API (/api/v1/live), reconnexion automatique du navigateur.
import { useEffect, useRef, useState } from "react";
import { goalSpeech } from "@/lib/a11y";
import type { Match } from "@/lib/types";
import { MatchCard } from "./MatchCard";

export function LiveScores({ initial }: { initial: Match[] }) {
  const [matches, setMatches] = useState<Record<string, Match>>(() =>
    Object.fromEntries(initial.map((m) => [m.id, m])),
  );

  // Annonce des buts au lecteur d'écran : seulement quand un score change, pas à chaque
  // minute de jeu (une zone « live » sur toute la liste serait relue en boucle)
  const [announce, setAnnounce] = useState("");
  const scores = useRef<Record<string, string>>(Object.fromEntries(initial.map((m) => [m.id, `${m.home_score}-${m.away_score}`])));

  useEffect(() => {
    const source = new EventSource("/api/v1/live");
    source.addEventListener("match", (ev) => {
      try {
        const m: Match = JSON.parse((ev as MessageEvent).data);
        const key = `${m.home_score}-${m.away_score}`;
        const before = scores.current[m.id];
        scores.current[m.id] = key;
        if (m.status === "live" && before !== undefined && before !== key) setAnnounce(goalSpeech(m));
        setMatches((prev) => ({ ...prev, [m.id]: m }));
      } catch {
        /* message ignoré */
      }
    });
    return () => source.close();
  }, []);

  const live = Object.values(matches).filter((m) => m.status === "live");
  return (
    <>
      <p role="status" className="sr-only">
        {announce}
      </p>
      {live.length > 0 && <LiveList live={live} />}
    </>
  );
}

function LiveList({ live }: { live: Match[] }) {
  return (
    <section aria-labelledby="en-direct" className="space-y-3">
      <h2 id="en-direct" className="flex items-center gap-2 text-xl font-black tracking-tight text-lds-red">
        <span aria-hidden className="relative flex h-3 w-3">
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
