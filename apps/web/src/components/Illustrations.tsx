// Illustrations originales (SVG, sans image externe ni droit à céder) : lignes de terrain,
// stade, trophée, ballon, état vide.

/** Tracé d'un terrain vu de dessus, en filigrane sur les bandeaux. */
export function PitchLines({ className = "" }: { className?: string }) {
  return (
    <svg aria-hidden viewBox="0 0 400 240" preserveAspectRatio="xMidYMid slice" className={`pointer-events-none absolute inset-0 h-full w-full ${className}`}>
      <g fill="none" stroke="currentColor" strokeWidth="1.5">
        <rect x="10" y="10" width="380" height="220" rx="2" />
        <line x1="200" y1="10" x2="200" y2="230" />
        <circle cx="200" cy="120" r="34" />
        <circle cx="200" cy="120" r="2" fill="currentColor" />
        <rect x="10" y="62" width="56" height="116" />
        <rect x="10" y="92" width="20" height="56" />
        <rect x="334" y="62" width="56" height="116" />
        <rect x="370" y="92" width="20" height="56" />
        <path d="M66 100a24 24 0 0 1 0 40M334 100a24 24 0 0 0 0 40" />
      </g>
      <g fill="currentColor" opacity="0.5">
        {Array.from({ length: 10 }, (_, i) => (
          <rect key={i} x={10 + i * 38} y="10" width="19" height="220" opacity="0.12" />
        ))}
      </g>
    </svg>
  );
}

/** Stade la nuit : tribunes, projecteurs, pelouse. */
export function Stadium({ className = "" }: { className?: string }) {
  return (
    <svg aria-hidden viewBox="0 0 480 220" className={className}>
      <defs>
        <radialGradient id="lds-light" cx="0.5" cy="0" r="0.8">
          <stop offset="0" stopColor="#fff7d6" stopOpacity="0.9" />
          <stop offset="1" stopColor="#fff7d6" stopOpacity="0" />
        </radialGradient>
        <linearGradient id="lds-grass" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#2f9e4f" />
          <stop offset="1" stopColor="#14652f" />
        </linearGradient>
      </defs>
      {[60, 420].map((x) => (
        <g key={x}>
          <path d={`M${x - 70} 150 L${x} 26 L${x + 70} 150Z`} fill="url(#lds-light)" opacity="0.55" />
          <rect x={x - 2} y="26" width="4" height="120" fill="#0a3a1e" />
          <rect x={x - 14} y="16" width="28" height="12" rx="2" fill="#f2c230" />
          {[0, 1, 2].map((i) => (
            <circle key={i} cx={x - 8 + i * 8} cy="22" r="2.5" fill="#fffbe8" />
          ))}
        </g>
      ))}
      <path d="M0 120 Q240 70 480 120 V160 H0Z" fill="#0f2c1b" />
      <path d="M0 132 Q240 88 480 132 V160 H0Z" fill="#c1272d" opacity="0.85" />
      <path d="M0 142 Q240 102 480 142 V160 H0Z" fill="#f2c230" opacity="0.9" />
      {Array.from({ length: 46 }, (_, i) => (
        <circle key={i} cx={8 + i * 10.3} cy={128 - Math.sin((i / 45) * Math.PI) * 30} r="2.6" fill="#ffffff" opacity={0.25 + ((i * 37) % 10) / 20} />
      ))}
      <path d="M0 156 Q240 118 480 156 V220 H0Z" fill="url(#lds-grass)" />
      <g stroke="#ffffff" strokeOpacity="0.7" strokeWidth="1.5" fill="none">
        <path d="M30 210 Q240 160 450 210" />
        <ellipse cx="240" cy="190" rx="44" ry="10" />
        <line x1="240" y1="172" x2="240" y2="214" />
      </g>
      <circle cx="262" cy="196" r="5" fill="#ffffff" />
    </svg>
  );
}

export function Trophy({ className = "" }: { className?: string }) {
  return (
    <svg aria-hidden viewBox="0 0 64 64" className={className}>
      <path d="M20 8h24v14a12 12 0 0 1-24 0Z" fill="#f2c230" />
      <path d="M20 12h-8a8 8 0 0 0 8 12M44 12h8a8 8 0 0 1-8 12" fill="none" stroke="#f2c230" strokeWidth="3.5" />
      <rect x="29" y="33" width="6" height="11" fill="#d9a514" />
      <path d="M22 44h20l3 8H19Z" fill="#0a3a1e" />
      <rect x="17" y="52" width="30" height="5" rx="1" fill="#0a3a1e" />
      <path d="m32 13 1.6 3.3 3.6.5-2.6 2.5.6 3.6-3.2-1.7-3.2 1.7.6-3.6-2.6-2.5 3.6-.5Z" fill="#fff8dc" />
    </svg>
  );
}

/** Ballon (pentagones) pour les états vides et décorations. */
export function Ball({ className = "" }: { className?: string }) {
  return (
    <svg aria-hidden viewBox="0 0 64 64" className={className}>
      <circle cx="32" cy="32" r="29" fill="#ffffff" stroke="#1c1917" strokeWidth="2.5" />
      <path d="M32 21 42.5 28.6 38.5 41h-13L21.5 28.6Z" fill="#1c1917" />
      <path d="M32 21V8M42.5 28.6 54 24M38.5 41l7 10.5M25.5 41l-7 10.5M21.5 28.6 10 24" stroke="#1c1917" strokeWidth="2.5" />
      <path d="M26 5l6 3 6-3M56 20l-2 4 3 6M50 52l-4.5-.5-3 5M14 52l4.5-.5 3 5M8 20l2 4-3 6" fill="none" stroke="#1c1917" strokeWidth="2.5" strokeLinejoin="round" />
    </svg>
  );
}

/** Ballon au fond des filets : messages « rien pour le moment ». */
export function EmptyState({ title, children }: { title: string; children?: React.ReactNode }) {
  return (
    <div className="flex flex-col items-center gap-3 rounded-2xl border border-dashed border-line bg-surface px-6 py-10 text-center">
      <div className="relative h-20 w-36 text-subtle">
        <svg aria-hidden viewBox="0 0 120 70" className="h-full w-full">
          <g fill="none" stroke="currentColor" strokeWidth="1.2" opacity="0.6">
            {Array.from({ length: 11 }, (_, i) => (
              <line key={`v${i}`} x1={10 + i * 10} y1="8" x2={14 + i * 9.2} y2="62" />
            ))}
            {Array.from({ length: 6 }, (_, i) => (
              <line key={`h${i}`} x1="10" y1={8 + i * 10.8} x2="110" y2={8 + i * 10.8} />
            ))}
          </g>
          <path d="M6 66V6h108v60" fill="none" stroke="currentColor" strokeWidth="4" strokeLinejoin="round" />
        </svg>
        <Ball className="absolute bottom-1 right-8 h-7 w-7 -rotate-12" />
      </div>
      <p className="font-bold text-heading">{title}</p>
      {children && <div className="max-w-md text-sm text-muted">{children}</div>}
    </div>
  );
}
