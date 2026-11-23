"use client";
// Procès-verbal d'un scrutin : page imprimable (enregistrement en PDF depuis le navigateur).
import { useBrandLogo } from "@/lib/brand";
import { BrandLogo } from "@/components/BrandLogo";
import Link from "next/link";
import { useParams } from "next/navigation";
import { Suspense } from "react";
import { Button } from "@/components/admin/ui";
import { RequireAuth } from "@/components/RequireAuth";
import { BALLOT_KIND_LABEL, formatDateTime } from "@/lib/format";
import type { VoteReport } from "@/lib/types";
import { useApi } from "@/lib/use-api";

export default function ProcesVerbalPage() {
  return (
    <Suspense fallback={<p>Chargement…</p>}>
      <RequireAuth permission="vote:manage">
        <Report />
      </RequireAuth>
    </Suspense>
  );
}

function Report() {
  const { id } = useParams<{ id: string }>();
  const logo = useBrandLogo();
  const { data: r, error } = useApi<VoteReport>(`/admin/ballots/${id}/report`);
  if (error) return <p className="text-lds-red">{error}</p>;
  if (!r) return <p className="text-stone-500">Préparation du procès-verbal…</p>;
  const b = r.ballot;
  const results = b.results;

  return (
    <div className="mx-auto max-w-3xl space-y-4">
      <div className="flex justify-between print:hidden">
        <Link href={`/admin/votes/${id}`} className="text-sm text-lds-green underline">
          ← Retour au scrutin
        </Link>
        <Button onClick={() => window.print()}>Imprimer / enregistrer en PDF</Button>
      </div>

      <article className="space-y-5 bg-white p-8 text-sm leading-relaxed text-stone-900 shadow print:p-0 print:shadow-none">
        <header className="border-b-2 border-lds-green pb-3 text-center">
          <div className="mb-2 flex justify-center">
            <BrandLogo logoUrl={logo} size="lg" className="shadow-none" />
          </div>
          <p className="text-xs font-bold uppercase tracking-widest text-lds-green">Ligue de la Souveraineté</p>
          <h1 className="mt-1 text-xl font-bold">Procès-verbal du vote du public</h1>
          <p className="font-semibold">{b.title}</p>
          <p className="text-xs text-stone-600">{BALLOT_KIND_LABEL[b.kind]}</p>
        </header>

        <section>
          <h2 className="font-bold">1. Organisation du scrutin</h2>
          <ul className="mt-1 list-disc pl-5">
            <li>
              Période de vote : du {formatDateTime(b.opens_at)} au {formatDateTime(b.closes_at)} (heure de Ouagadougou).
            </li>
            <li>
              {b.max_choices} choix par votant parmi {b.options.length} propositions.
            </li>
            <li>
              Un seul vote par numéro de téléphone, confirmé par un code à usage unique envoyé par SMS ; numéros du Burkina
              Faso. Vote gratuit.
            </li>
            <li>
              Votes en masse (même connexion, numéros qui se suivent) mis de côté automatiquement, puis examinés un par un par
              l&apos;administration de la Ligue.
            </li>
          </ul>
        </section>

        <section>
          <h2 className="font-bold">2. Participation</h2>
          <table className="mt-1 w-full border-collapse">
            <tbody>
              {[
                ["Votants comptés", r.valid_voters],
                ["Votes encore en examen", r.flagged_voters],
                ["Votes rejetés après examen", r.rejected_voters],
              ].map(([label, n]) => (
                <tr key={label as string} className="border-b border-stone-200">
                  <td className="py-1">{label}</td>
                  <td className="py-1 text-right font-semibold tabular-nums">{n}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {r.flagged_voters > 0 && (
            <p className="mt-1 text-xs font-semibold text-lds-red">
              Attention : des votes restent à examiner ; les résultats ci-dessous sont provisoires.
            </p>
          )}
        </section>

        <section>
          <h2 className="font-bold">3. Résultats</h2>
          <table className="mt-1 w-full border-collapse text-left">
            <thead>
              <tr className="border-b-2 border-stone-300 text-xs uppercase">
                <th className="py-1">Rang</th>
                <th className="py-1">Proposition</th>
                <th className="py-1">Équipe</th>
                <th className="py-1 text-right">Voix</th>
                <th className="py-1 text-right">Part des votants</th>
              </tr>
            </thead>
            <tbody>
              {results?.options.map((o) => (
                <tr key={o.option_id} className="border-b border-stone-200">
                  <td className="py-1 tabular-nums">{o.rank}</td>
                  <td className="py-1 font-medium">{o.label}</td>
                  <td className="py-1">{o.team?.name ?? ""}</td>
                  <td className="py-1 text-right tabular-nums">{o.votes}</td>
                  <td className="py-1 text-right tabular-nums">{(o.share * 100).toFixed(1).replace(".", ",")} %</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>

        <section>
          <h2 className="font-bold">4. Intégrité</h2>
          <p>
            Le journal détaillé des votes (export CSV, sans aucun numéro en clair) a pour empreinte SHA-256 :
          </p>
          <p className="break-all rounded bg-stone-100 p-2 font-mono text-xs">{r.journal_sha256}</p>
          <p className="text-xs text-stone-600">
            Toute modification du journal changerait cette empreinte. Les actions d&apos;administration (ouverture, clôture,
            examen des votes, publication) sont inscrites au journal d&apos;audit de la plateforme.
          </p>
        </section>

        <footer className="space-y-6 border-t border-stone-300 pt-3">
          <p className="text-xs text-stone-600">
            Procès-verbal établi le {formatDateTime(r.generated_at)} par {r.generated_by}, à partir des données de LDS
            Connect.
          </p>
          <div className="grid grid-cols-2 gap-8 pt-6 text-xs">
            <div className="border-t border-stone-400 pt-1">Pour le Secrétariat exécutif (nom, signature)</div>
            <div className="border-t border-stone-400 pt-1">Témoin (nom, signature)</div>
          </div>
        </footer>
      </article>
    </div>
  );
}
