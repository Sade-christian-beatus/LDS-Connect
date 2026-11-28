"use client";
// « Écouter la page » : lit le contenu de la page à voix haute avec la voix de l'appareil
// (synthèse vocale du navigateur, sans service extérieur). Pour les personnes malvoyantes et
// pour celles qui lisent difficilement le français ; les personnes aveugles gardent leur
// lecteur d'écran, plus complet.
import { usePathname } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";
import { frenchVoice, type Passage, passages } from "@/lib/read-aloud";

const RATE_KEY = "lds-ecoute-vitesse";
const RATES = [
  { value: 1, label: "Vitesse normale" },
  { value: 0.8, label: "Lecture lente" },
  { value: 1.25, label: "Lecture rapide" },
];

type State = "idle" | "playing" | "paused";

function mark(el: HTMLElement | null) {
  document.querySelectorAll("[data-reading]").forEach((e) => e.removeAttribute("data-reading"));
  if (!el) return;
  el.setAttribute("data-reading", "");
  const reduce = matchMedia("(prefers-reduced-motion: reduce)").matches;
  el.scrollIntoView({ block: "center", behavior: reduce ? "auto" : "smooth" });
}

export function ListenButton() {
  const [supported, setSupported] = useState(false);
  const [state, setState] = useState<State>("idle");
  const [index, setIndex] = useState(0);
  const [total, setTotal] = useState(0);
  const [rate, setRate] = useState(1);
  const list = useRef<Passage[]>([]);
  const pos = useRef(0);
  const run = useRef(0); // chaque lecture porte un numéro : une phrase annulée ne relance rien
  const pathname = usePathname();

  useEffect(() => {
    Promise.resolve().then(() => {
      setSupported(typeof window !== "undefined" && "speechSynthesis" in window && "SpeechSynthesisUtterance" in window);
      const saved = Number(localStorage.getItem(RATE_KEY));
      if (RATES.some((r) => r.value === saved)) setRate(saved);
    });
  }, []);

  const speakFrom = useCallback(
    (i: number, speed: number) => {
      const synth = window.speechSynthesis;
      const id = ++run.current;
      synth.cancel();
      const step = (n: number) => {
        if (id !== run.current) return;
        if (n >= list.current.length) {
          mark(null);
          setState("idle");
          return;
        }
        pos.current = n;
        setIndex(n);
        const p = list.current[n];
        mark(p.el);
        const u = new SpeechSynthesisUtterance(p.text);
        u.lang = "fr-FR";
        const voice = frenchVoice();
        if (voice) u.voice = voice;
        u.rate = speed;
        u.onend = () => step(n + 1);
        u.onerror = (e) => {
          // « interrupted » / « canceled » : arrêt demandé, rien à faire
          if (e.error !== "interrupted" && e.error !== "canceled") step(n + 1);
        };
        synth.speak(u);
      };
      setState("playing");
      step(i);
    },
    [],
  );

  const stop = useCallback(() => {
    run.current++;
    window.speechSynthesis?.cancel();
    mark(null);
    setState("idle");
  }, []);

  // Changement de page : la lecture s'arrête
  useEffect(() => {
    if (supported) Promise.resolve().then(stop);
  }, [pathname, supported, stop]);
  useEffect(() => () => window.speechSynthesis?.cancel(), []);

  const start = () => {
    const main = document.getElementById("contenu");
    if (!main) return;
    list.current = passages(main);
    setTotal(list.current.length);
    if (list.current.length) speakFrom(0, rate);
  };
  // Pause : la phrase en cours est arrêtée, puis reprise du début (plus fiable que pause()
  // sur les téléphones Android)
  const pause = () => {
    run.current++;
    window.speechSynthesis.cancel();
    setState("paused");
  };
  const move = (delta: number) => speakFrom(Math.min(Math.max(0, pos.current + delta), list.current.length - 1), rate);
  const changeRate = () => {
    const next = RATES[(RATES.findIndex((r) => r.value === rate) + 1) % RATES.length].value;
    setRate(next);
    localStorage.setItem(RATE_KEY, String(next));
    if (state === "playing") speakFrom(pos.current, next);
  };

  if (!supported) return null;
  const rateLabel = RATES.find((r) => r.value === rate)?.label ?? "Vitesse normale";
  const btn = "flex h-10 min-w-10 items-center justify-center gap-1.5 rounded-full px-3 text-sm font-semibold hover:bg-white/10";

  return (
    <>
      <button
        type="button"
        onClick={state === "idle" ? start : stop}
        aria-pressed={state !== "idle"}
        title={state === "idle" ? "Écouter la page" : "Arrêter la lecture"}
        className="flex h-9 items-center gap-1.5 rounded-full px-2.5 text-sm font-semibold text-white/90 hover:bg-white/10"
      >
        <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden>
          <path d="M4 9v6h4l5 4V5L8 9Z" fill="currentColor" />
          <path d="M16.5 8.5a5 5 0 0 1 0 7M19 6a8.5 8.5 0 0 1 0 12" strokeLinecap="round" />
        </svg>
        <span className="hidden lg:inline">{state === "idle" ? "Écouter la page" : "Arrêter"}</span>
        <span className="sr-only lg:hidden">{state === "idle" ? "Écouter la page" : "Arrêter la lecture"}</span>
      </button>

      {state !== "idle" && (
        <div
          role="toolbar"
          aria-label="Lecture à voix haute"
          data-read-aloud-skip
          className="fixed inset-x-3 bottom-20 z-40 mx-auto flex max-w-xl flex-wrap items-center justify-between gap-1 rounded-2xl bg-pitch px-3 py-2 text-white shadow-2xl ring-1 ring-white/15 md:bottom-5 print:hidden"
        >
          <p className="px-1 text-xs text-green-100" aria-live="off">
            {state === "paused" ? "En pause" : "Lecture"} · {Math.min(index + 1, total)}/{total}
          </p>
          <div className="flex items-center gap-0.5">
            <button type="button" className={btn} onClick={() => move(-1)} aria-label="Passage précédent">
              <svg viewBox="0 0 24 24" className="h-5 w-5" fill="currentColor" aria-hidden>
                <path d="M6 5h2v14H6zM20 5v14L9 12Z" />
              </svg>
            </button>
            {state === "playing" ? (
              <button type="button" className={btn} onClick={pause} aria-label="Pause">
                <svg viewBox="0 0 24 24" className="h-5 w-5" fill="currentColor" aria-hidden>
                  <path d="M6 5h4v14H6zM14 5h4v14h-4z" />
                </svg>
              </button>
            ) : (
              <button type="button" className={btn} onClick={() => speakFrom(pos.current, rate)} aria-label="Reprendre">
                <svg viewBox="0 0 24 24" className="h-5 w-5" fill="currentColor" aria-hidden>
                  <path d="M7 4v16l13-8Z" />
                </svg>
              </button>
            )}
            <button type="button" className={btn} onClick={() => move(1)} aria-label="Passage suivant">
              <svg viewBox="0 0 24 24" className="h-5 w-5" fill="currentColor" aria-hidden>
                <path d="M16 5h2v14h-2zM4 5v14l11-7Z" />
              </svg>
            </button>
            <button type="button" className={btn} onClick={changeRate} aria-label={`${rateLabel} (changer)`}>
              <span aria-hidden className="text-xs">
                {rate === 1 ? "×1" : rate < 1 ? "×0,8" : "×1,25"}
              </span>
            </button>
            <button type="button" className={btn} onClick={stop} aria-label="Arrêter la lecture">
              <svg viewBox="0 0 24 24" className="h-5 w-5" fill="currentColor" aria-hidden>
                <path d="M6 6h12v12H6z" />
              </svg>
            </button>
          </div>
        </div>
      )}
    </>
  );
}
