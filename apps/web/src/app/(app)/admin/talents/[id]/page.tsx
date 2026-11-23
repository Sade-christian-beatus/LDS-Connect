"use client";
// Fiche interne d'un joueur : chiffres, match par match, suivi et notes d'observation.
import Link from "next/link";
import { useParams } from "next/navigation";
import { Suspense, useState } from "react";
import { Badge, Button, Dialog, Field, inputClass, Notice } from "@/components/admin/ui";
import { MatchLogList, StatTiles } from "@/components/PlayerStats";
import { RequireAuth } from "@/components/RequireAuth";
import { TeamBadge } from "@/components/TeamBadge";
import { useAuth } from "@/lib/auth";
import { formatDateTime, POSITION_LABEL } from "@/lib/format";
import type { TalentProfile } from "@/lib/types";
import { useApi } from "@/lib/use-api";

export default function TalentProfilePage() {
  return (
    <RequireAuth permission="talent:notes">
      <Suspense>
        <Profile />
      </Suspense>
    </RequireAuth>
  );
}

const FOOT: Record<string, string> = { left: "gauche", right: "droit", both: "des deux pieds" };
const TAGS = ["Potentiel sélection", "À revoir en match", "Leader", "Vitesse", "Technique", "Jeu de tête"];

function Stars({ value, onChange }: { value: number | null; onChange?: (v: number | null) => void }) {
  return (
    <span className="inline-flex" role={onChange ? "radiogroup" : undefined} aria-label={onChange ? "Appréciation" : `${value ?? 0} sur 5`}>
      {[1, 2, 3, 4, 5].map((n) =>
        onChange ? (
          <button
            key={n}
            type="button"
            role="radio"
            aria-checked={value === n}
            aria-label={`${n} sur 5`}
            onClick={() => onChange(value === n ? null : n)}
            className={`text-2xl leading-none ${value && n <= value ? "text-lds-gold" : "text-stone-300"}`}
          >
            ★
          </button>
        ) : (
          <span key={n} aria-hidden className={value && n <= value ? "text-lds-gold" : "text-stone-300"}>
            ★
          </span>
        ),
      )}
    </span>
  );
}

function Profile() {
  const { id } = useParams<{ id: string }>();
  const { api } = useAuth();
  const { data: p, reload, error } = useApi<TalentProfile>(`/admin/talents/${id}`);
  const [note, setNote] = useState<{ body: string; rating: number | null; match_id: string }>({ body: "", rating: null, match_id: "" });
  const [del, setDel] = useState<{ id: string; reason: string } | null>(null);
  const [notice, setNotice] = useState<{ tone: "ok" | "error"; text: string } | null>(null);
  const [busy, setBusy] = useState(false);

  async function run(fn: () => Promise<unknown>, ok: string) {
    setBusy(true);
    try {
      await fn();
      setNotice({ tone: "ok", text: ok });
      reload();
    } catch (e) {
      setNotice({ tone: "error", text: e instanceof Error ? e.message : String(e) });
    } finally {
      setBusy(false);
    }
  }

  if (error) return <p className="text-lds-red">{error}</p>;
  if (!p) return <p className="text-stone-500">Chargement de la fiche…</p>;

  const watch = (watched: boolean, tags: string[]) =>
    run(
      () => api(`/admin/talents/${id}/watch`, { method: "PUT", body: JSON.stringify({ watched, tags }) }),
      watched ? "Liste de suivi mise à jour" : "Joueur retiré de la liste de suivi",
    );

  return (
    <div className="space-y-5">
      <Link href="/admin/talents" className="text-sm text-lds-green underline">
        ← Tous les talents
      </Link>
      <Notice notice={notice} onClose={() => setNotice(null)} />

      <header
        className="flex flex-wrap items-center gap-4 rounded-2xl p-5 text-white shadow"
        style={{ background: `linear-gradient(120deg, ${p.team.primary_color} 0%, #0a3a1e 85%)` }}
      >
        <span
          className="flex h-16 w-16 items-center justify-center rounded-2xl text-3xl font-black tabular-nums ring-4 ring-white/20"
          style={{ backgroundColor: p.team.primary_color, color: p.team.secondary_color }}
        >
          {p.shirt_number ?? "–"}
        </span>
        <div className="min-w-0 flex-1">
          <p className="text-xs font-bold uppercase tracking-[0.2em] text-lds-gold">
            {POSITION_LABEL[p.position]} · {p.age} ans{p.preferred_foot ? ` · pied ${FOOT[p.preferred_foot] ?? p.preferred_foot}` : ""}
          </p>
          <h1 className="text-2xl font-black leading-tight sm:text-3xl">{p.full_name}</h1>
          <p className="flex items-center gap-2 text-sm text-white/90">
            <TeamBadge team={p.team} size="sm" /> {p.team.name}
            {p.region ? ` · région ${p.region}` : ""} · nom d&apos;usage « {p.display_name} »
          </p>
        </div>
        <div className="flex flex-col items-end gap-2">
          {p.is_youth && <Badge tone="blue">Catégorie jeunes</Badge>}
          <button
            type="button"
            disabled={busy}
            onClick={() => watch(!p.watched, p.tags)}
            className={`rounded-full px-4 py-1.5 text-sm font-bold ${p.watched ? "bg-lds-gold text-pitch" : "border border-white/40 hover:bg-white/10"}`}
          >
            {p.watched ? "★ Suivi" : "☆ Suivre ce joueur"}
          </button>
        </div>
      </header>

      {p.watched && (
        <div className="flex flex-wrap items-center gap-2 text-sm" role="group" aria-label="Étiquettes de suivi">
          <span className="text-stone-600">Étiquettes :</span>
          {TAGS.map((t) => {
            const on = p.tags.includes(t);
            return (
              <button
                key={t}
                type="button"
                aria-pressed={on}
                disabled={busy}
                onClick={() => watch(true, on ? p.tags.filter((x) => x !== t) : [...p.tags, t])}
                className={`rounded-full border px-3 py-0.5 ${on ? "border-lds-green bg-lds-green text-white" : "border-stone-300 bg-white"}`}
              >
                {t}
              </button>
            );
          })}
        </div>
      )}

      <StatTiles stats={p.stats} goalkeeper={p.position === "GK"} />

      <div className="grid gap-5 lg:grid-cols-[1.2fr_1fr]">
        <section className="space-y-2">
          <h2 className="text-lg font-black tracking-tight text-pitch">Match par match</h2>
          <MatchLogList matches={p.matches} teamId={p.team.id} />
        </section>

        <section className="space-y-3">
          <h2 className="text-lg font-black tracking-tight text-pitch">Observations ({p.notes.length})</h2>
          <form
            className="space-y-2 rounded-xl border border-stone-200 bg-white p-4"
            onSubmit={(e) => {
              e.preventDefault();
              run(
                () =>
                  api(`/admin/talents/${id}/notes`, {
                    method: "POST",
                    body: JSON.stringify({ body: note.body, rating: note.rating, match_id: note.match_id || null }),
                  }),
                "Observation enregistrée",
              ).then(() => setNote({ body: "", rating: null, match_id: "" }));
            }}
          >
            <Field label="Nouvelle observation">
              <textarea
                required
                minLength={3}
                rows={3}
                className={inputClass}
                placeholder="Points forts, axes de progression, contexte du match…"
                value={note.body}
                onChange={(e) => setNote({ ...note, body: e.target.value })}
              />
            </Field>
            <div className="flex flex-wrap items-end justify-between gap-3">
              <div className="text-sm">
                <span className="block text-stone-700">Appréciation</span>
                <Stars value={note.rating} onChange={(rating) => setNote({ ...note, rating })} />
              </div>
              <label className="text-sm">
                Match observé
                <select className={inputClass} value={note.match_id} onChange={(e) => setNote({ ...note, match_id: e.target.value })}>
                  <option value="">—</option>
                  {p.matches.map((l) => (
                    <option key={l.match.id} value={l.match.id}>
                      {l.match.home?.short_name} – {l.match.away?.short_name}
                    </option>
                  ))}
                </select>
              </label>
              <Button type="submit" disabled={busy}>
                Enregistrer
              </Button>
            </div>
            <p className="text-xs text-stone-500">
              Note interne et chiffrée, visible seulement de la cellule technique et de l&apos;administration. Le joueur peut être
              mineur : s&apos;en tenir à des appréciations sportives.
            </p>
          </form>

          {p.notes.length === 0 && <p className="text-sm text-stone-500">Aucune observation pour le moment.</p>}
          <ul className="space-y-2">
            {p.notes.map((n) => (
              <li key={n.id} className="rounded-xl border border-stone-200 bg-white p-3 text-sm">
                <div className="flex flex-wrap items-center justify-between gap-2 text-xs text-stone-500">
                  <span>
                    <strong className="text-stone-700">{n.author}</strong> · {formatDateTime(n.created_at)}
                  </span>
                  {n.rating && <Stars value={n.rating} />}
                </div>
                <p className="mt-1 whitespace-pre-line">{n.body}</p>
                <button type="button" className="mt-1 text-xs text-lds-red underline" onClick={() => setDel({ id: n.id, reason: "" })}>
                  Retirer
                </button>
              </li>
            ))}
          </ul>
        </section>
      </div>

      <Dialog open={!!del} title="Retirer l'observation" onClose={() => setDel(null)}>
        {del && (
          <form
            className="space-y-3"
            onSubmit={(e) => {
              e.preventDefault();
              run(
                () => api(`/admin/talent-notes/${del.id}/delete`, { method: "POST", body: JSON.stringify({ reason: del.reason }) }),
                "Observation retirée",
              ).then(() => setDel(null));
            }}
          >
            <p className="text-sm text-stone-600">L&apos;observation n&apos;apparaîtra plus ; le retrait est inscrit au journal.</p>
            <Field label="Motif *">
              <input required minLength={3} className={inputClass} value={del.reason} onChange={(e) => setDel({ ...del, reason: e.target.value })} />
            </Field>
            <div className="flex justify-end gap-2">
              <Button variant="secondary" onClick={() => setDel(null)}>
                Annuler
              </Button>
              <Button type="submit" variant="danger">
                Retirer
              </Button>
            </div>
          </form>
        )}
      </Dialog>
    </div>
  );
}
