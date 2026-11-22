import type { Metadata } from "next";
import Link from "next/link";
import { Suspense } from "react";
import { BALLOT_KIND_LABEL, formatDateTime } from "@/lib/format";
import { apiGet } from "@/lib/server-api";
import type { BallotOut } from "@/lib/types";

export const metadata: Metadata = { title: "Votes du public" };

export default function VotesPage() {
  return (
    <>
      <h1 className="text-2xl font-bold text-green-900">Votes du public</h1>
      <p className="text-stone-600">
        Élisez l&apos;homme du match, le but du mois, le joueur de la saison… Un vote par numéro de téléphone, confirmé par
        un code reçu par SMS. Vote gratuit.
      </p>
      <Suspense fallback={<p className="text-stone-500">Chargement des votes…</p>}>
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
  if (ballots.length === 0) return <p className="text-stone-600">Aucun vote en cours pour le moment.</p>;
  return (
    <>
      {groups
        .filter(([, list]) => list.length)
        .map(([title, list]) => (
          <section key={title} className="space-y-2">
            <h2 className="text-lg font-bold text-green-900">{title}</h2>
            <ul className="grid gap-3 md:grid-cols-2">
              {list.map((b) => (
                <li key={b.id}>
                  <Link href={`/votes/${b.id}`} className="block rounded-lg border border-stone-200 bg-white p-4 hover:border-lds-green">
                    <span className="text-xs font-semibold uppercase tracking-wide text-lds-red">{BALLOT_KIND_LABEL[b.kind]}</span>
                    <span className="mt-1 block text-lg font-bold leading-tight">{b.title}</span>
                    <span className="mt-1 block text-sm text-stone-600">
                      {b.state === "open" && `Vote ouvert jusqu'au ${formatDateTime(b.closes_at)}`}
                      {b.state === "upcoming" && `Ouverture le ${formatDateTime(b.opens_at)}`}
                      {b.state === "closed" &&
                        (b.results_visible ? "Résultats disponibles" : `Résultats le ${formatDateTime(b.results_publish_at)}`)}
                    </span>
                    {b.state === "open" && (
                      <span className="mt-3 inline-block rounded bg-lds-green px-3 py-1 text-sm font-semibold text-white">Voter</span>
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
