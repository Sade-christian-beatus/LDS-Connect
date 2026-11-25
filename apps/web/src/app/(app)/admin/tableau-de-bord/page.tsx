"use client";
// Tableau de bord de l'administration : matchs du jour et à venir, points à traiter (feuilles
// à valider, remboursements, votes mis de côté), chiffres clés de la saison.
import Link from "next/link";
import { MatchCard } from "@/components/MatchCard";
import { RequireAuth } from "@/components/RequireAuth";
import { formatFcfa } from "@/lib/format";
import type { Dashboard } from "@/lib/types";
import { useApi } from "@/lib/use-api";

export default function TableauDeBordPage() {
  return (
    <RequireAuth permission="audit:read">
      <Board />
    </RequireAuth>
  );
}

function Tile({ label, value, hint, href, tone = "plain" }: { label: string; value: string | number; hint?: string; href?: string; tone?: "plain" | "alert" | "good" }) {
  const tones = {
    plain: "border-stone-200 bg-white",
    alert: "border-amber-300 bg-amber-50",
    good: "border-green-200 bg-green-50",
  };
  const body = (
    <>
      <p className="text-xs font-semibold uppercase tracking-wide text-stone-500">{label}</p>
      <p className="mt-1 text-3xl font-black tabular-nums text-pitch">{value}</p>
      {hint && <p className="mt-0.5 text-xs text-stone-600">{hint}</p>}
    </>
  );
  const cls = `block rounded-xl border p-4 shadow-sm ${tones[tone]}`;
  return href ? (
    <Link href={href} className={`${cls} transition hover:-translate-y-0.5 hover:shadow-md`}>
      {body}
    </Link>
  ) : (
    <div className={cls}>{body}</div>
  );
}

function Board() {
  const { data, error } = useApi<Dashboard>("/admin/dashboard");
  if (error) return <p className="text-lds-red">{error}</p>;
  if (!data) return <p className="text-stone-500">Chargement du tableau de bord…</p>;
  const c = data.counts;
  const progress = c.matches_total ? Math.round((c.matches_played / c.matches_total) * 100) : 0;
  const todo = [
    c.sheets_to_validate > 0 && { text: `${c.sheets_to_validate} feuille(s) de match soumise(s) à valider`, href: "/admin/calendrier" },
    c.refunds_due > 0 && { text: `${c.refunds_due} commande(s) à rembourser`, href: "/admin/billetterie" },
    c.votes_flagged > 0 && { text: `${c.votes_flagged} vote(s) mis de côté à examiner`, href: "/admin/votes" },
    c.licences_blocked > 0 && { text: `${c.licences_blocked} licence(s) suspendue(s) ou révoquée(s)`, href: "/admin/equipes" },
  ].filter(Boolean) as { text: string; href: string }[];

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-2">
        <div>
          <p className="text-xs font-bold uppercase tracking-[0.2em] text-lds-red">{data.season}</p>
          <h1 className="text-2xl font-black tracking-tight text-pitch">Tableau de bord</h1>
        </div>
        <div className="min-w-56 flex-1 sm:max-w-xs">
          <p className="flex justify-between text-xs text-stone-600">
            <span>Avancement de la saison</span>
            <span className="font-semibold">
              {c.matches_played}/{c.matches_total} matchs
            </span>
          </p>
          <div className="mt-1 h-2 overflow-hidden rounded-full bg-stone-200" role="progressbar" aria-valuenow={progress} aria-valuemin={0} aria-valuemax={100} aria-label="Avancement de la saison">
            <div className="h-full rounded-full bg-gradient-to-r from-lds-green to-lds-gold" style={{ width: `${progress}%` }} />
          </div>
        </div>
      </div>

      <section aria-label="À traiter" className="rounded-xl border border-stone-200 bg-white p-4">
        <h2 className="font-bold text-pitch">À traiter</h2>
        {todo.length === 0 ? (
          <p className="mt-1 text-sm text-green-800">✓ Rien en attente.</p>
        ) : (
          <ul className="mt-2 space-y-1.5">
            {todo.map((t) => (
              <li key={t.text}>
                <Link href={t.href} className="flex items-center justify-between gap-2 rounded-lg bg-amber-50 px-3 py-2 text-sm text-amber-950 hover:bg-amber-100">
                  {t.text}
                  <span aria-hidden>→</span>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </section>

      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <Tile label="Licences actives" value={c.licences_active} href="/admin/equipes" />
        <Tile label="Billets vendus" value={c.tickets_sold} hint={formatFcfa(c.revenue_fcfa)} href="/admin/billetterie" />
        <Tile label="Scrutins ouverts" value={c.ballots_open} hint={`${c.votes_valid} vote(s) valide(s)`} href="/admin/votes" />
        <Tile
          label="Feuilles à valider"
          value={c.sheets_to_validate}
          tone={c.sheets_to_validate ? "alert" : "good"}
          href="/admin/calendrier"
        />
      </div>

      {data.live.length > 0 && (
        <section className="space-y-2">
          <h2 className="text-lg font-bold text-lds-red">● En direct</h2>
          <div className="grid gap-3 md:grid-cols-2">
            {data.live.map((m) => (
              <MatchCard key={m.id} match={m} />
            ))}
          </div>
        </section>
      )}

      <section className="space-y-2">
        <h2 className="text-lg font-bold text-pitch">Prochains matchs</h2>
        {data.upcoming.length === 0 ? (
          <p className="text-sm text-stone-600">Aucun match programmé.</p>
        ) : (
          <div className="grid gap-3 md:grid-cols-2">
            {data.upcoming.map((m) => (
              <MatchCard key={m.id} match={m} />
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
