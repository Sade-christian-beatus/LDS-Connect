"use client";
// Compte à rebours jusqu'au coup d'envoi.
import { useEffect, useState } from "react";

function parts(ms: number) {
  const s = Math.max(0, Math.floor(ms / 1000));
  return { d: Math.floor(s / 86400), h: Math.floor((s % 86400) / 3600), m: Math.floor((s % 3600) / 60), s: s % 60 };
}

export function Countdown({ to }: { to: string }) {
  const [now, setNow] = useState<number | null>(null);
  useEffect(() => {
    Promise.resolve().then(() => setNow(Date.now()));
    const t = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(t);
  }, []);
  if (now === null) return <div className="h-14" aria-hidden />;
  const left = new Date(to).getTime() - now;
  if (left <= 0) return <p className="text-center font-semibold text-yellow-300">Coup d&apos;envoi imminent</p>;
  const p = parts(left);
  const cells: [number, string][] = [
    [p.d, "jours"],
    [p.h, "heures"],
    [p.m, "min"],
    [p.s, "s"],
  ];
  return (
    <div className="flex justify-center gap-2" role="timer" aria-label="Temps avant le coup d'envoi">
      {cells.map(([v, l]) => (
        <div key={l} className="w-16 rounded-xl bg-white/10 py-1.5 text-center backdrop-blur">
          <div className="text-2xl font-black tabular-nums">{String(v).padStart(2, "0")}</div>
          <div className="text-[10px] uppercase tracking-wider text-green-100">{l}</div>
        </div>
      ))}
    </div>
  );
}
