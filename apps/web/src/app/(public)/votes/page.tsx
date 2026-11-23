import type { Metadata } from "next";
import Link from "next/link";
import { Suspense } from "react";
import { PageHeader } from "@/components/PageHeader";
import { BALLOT_KIND_LABEL, formatDateTime } from "@/lib/format";
import { apiGet } from "@/lib/server-api";
import type { BallotOut } from "@/lib/types";

export const metadata: Metadata = { title: "Votes du public" };

export default function VotesPage() {
  return (
    <>
      <PageHeader kicker="À vous de jouer" title="Votes du public">
        Élisez l&apos;homme du match, le but du mois, le joueur de la saison… Un vote par numéro de téléphone, confirmé par un code
        reçu par SMS. Vote gratuit.
      </PageHeader>
      <Suspense fallback={<p className="text-subtle">Chargement des votes…</p>}>
        <Ballots />
      </Suspense>
    </>
  );
}

async function Ballots() {
  const ballots = await apiGet<BallotOut[]>("/ballots");
  const groups: [string, BallotOut[]][] = [
    ["Votes ouverts", ballots.filter((b) => b.state === "open")],
    ["Bientôt", ballots.filter((b) => b.state === "upcoming")],
    ["Votes terminés", ballots.filter((b) => b.state === "closed")],
  ];
  if (ballots.length === 0) return <p className="text-muted">Aucun vote en cours pour le moment.</p>;
  return (
    <>
      {groups
        .filter(([, list]) => list.length)
        .map(([title, list]) => (
          <section key={title} className="space-y-2">
            <h2 className="text-xl font-black tracking-tight text-heading">{title}</h2>
            <ul className="grid gap-3 md:grid-cols-2">
              {list.map((b) => (
                <li key={b.id}>
                  <Link href={`/votes/${b.id}`} className="group relative block overflow-hidden rounded-2xl border border-line bg-surface p-5 shadow-sm transition hover:-translate-y-0.5 hover:shadow-md">
                    <span className="text-xs font-semibold uppercase tracking-wide text-lds-red">{BALLOT_KIND_LABEL[b.kind]}</span>
                    {b.state === "open" && <span aria-hidden className="absolute inset-y-0 left-0 w-1.5 bg-lds-red" />}
                    <span className="mt-1 block text-xl font-black leading-tight">{b.title}</span>
                    <span className="mt-1 block text-sm text-muted">
                      {b.state === "open" && `Vote ouvert jusqu'au ${formatDateTime(b.closes_at)}`}
                      {b.state === "upcoming" && `Ouverture le ${formatDateTime(b.opens_at)}`}
                      {b.state === "closed" &&
                        (b.results_visible ? "Résultats disponibles" : `Résultats le ${formatDateTime(b.results_publish_at)}`)}
                    </span>
                    {b.state === "open" && (
                      <span className="mt-3 inline-block rounded-full bg-lds-red px-4 py-1.5 text-sm font-bold text-white group-hover:bg-red-700">Voter</span>
                    )}
                  </Link>
                </li>
              ))}
            </ul>
          </section>
        ))}
    </>
  );
}
