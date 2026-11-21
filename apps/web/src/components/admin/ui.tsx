"use client";
// Petits composants d'interface du back-office (sans bibliothèque externe).
import { useEffect, useRef } from "react";

export function Dialog({
  open,
  title,
  onClose,
  children,
  wide = false,
}: {
  open: boolean;
  title: string;
  onClose: () => void;
  children: React.ReactNode;
  wide?: boolean;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    const d = ref.current;
    if (!d) return;
    if (open && !d.open) d.showModal();
    if (!open && d.open) d.close();
  }, [open]);
  return (
    <dialog
      ref={ref}
      onClose={onClose}
      aria-label={title}
      className={`m-auto w-[95vw] rounded-xl p-0 shadow-xl backdrop:bg-black/40 ${wide ? "max-w-3xl" : "max-w-lg"}`}
    >
      {open && (
        <div className="p-4">
          <div className="mb-3 flex items-start justify-between gap-4">
            <h2 className="text-lg font-bold text-green-900">{title}</h2>
            <button type="button" onClick={onClose} className="text-2xl leading-none text-stone-500" aria-label="Fermer">
              ×
            </button>
          </div>
          {children}
        </div>
      )}
    </dialog>
  );
}

export function Field({
  label,
  hint,
  children,
}: {
  label: string;
  hint?: string;
  children: React.ReactNode;
}) {
  return (
    <label className="block text-sm">
      <span className="font-medium text-stone-700">{label}</span>
      {children}
      {hint && <span className="mt-0.5 block text-xs text-stone-500">{hint}</span>}
    </label>
  );
}

export const inputClass = "mt-1 w-full rounded border border-stone-300 px-2 py-1.5 text-sm disabled:bg-stone-100";

export function Badge({ tone, children }: { tone: "green" | "red" | "amber" | "stone" | "blue"; children: React.ReactNode }) {
  const tones = {
    green: "bg-green-100 text-green-800",
    red: "bg-red-100 text-lds-red",
    amber: "bg-amber-100 text-amber-900",
    stone: "bg-stone-100 text-stone-700",
    blue: "bg-blue-100 text-blue-800",
  };
  return <span className={`inline-block rounded px-1.5 py-0.5 text-[11px] font-semibold ${tones[tone]}`}>{children}</span>;
}

export function Notice({ notice, onClose }: { notice: { tone: "ok" | "error"; text: string } | null; onClose: () => void }) {
  if (!notice) return null;
  return (
    <div
      role={notice.tone === "error" ? "alert" : "status"}
      className={`flex items-start justify-between gap-3 rounded p-3 text-sm ${notice.tone === "error" ? "bg-red-50 text-lds-red" : "bg-green-50 text-green-800"}`}
    >
      <span>{notice.text}</span>
      <button type="button" onClick={onClose} aria-label="Masquer le message">
        ×
      </button>
    </div>
  );
}

export function Button({
  variant = "primary",
  ...props
}: React.ButtonHTMLAttributes<HTMLButtonElement> & { variant?: "primary" | "secondary" | "danger" | "link" }) {
  const styles = {
    primary: "rounded bg-lds-green px-3 py-1.5 font-semibold text-white",
    secondary: "rounded border border-stone-300 bg-white px-3 py-1.5",
    danger: "rounded bg-lds-red px-3 py-1.5 font-semibold text-white",
    link: "text-lds-green underline",
  };
  return <button type="button" {...props} className={`text-sm disabled:opacity-50 ${styles[variant]} ${props.className ?? ""}`} />;
}
