import Link from "next/link";
import { Suspense } from "react";
import { ResultsBars } from "@/components/ResultsBars";
import { BALLOT_KIND_LABEL, formatDateTime } from "@/lib/format";
import { apiGet } from "@/lib/server-api";
import type { BallotOut } from "@/lib/types";
import { VoteWidget } from "./vote-widget";

export default function VotePage({ params }: PageProps<"/votes/[id]">) {
  return (
    <Suspense fallback={<p className="text-stone-500">Chargement du vote…</p>}>
      <Ballot params={params} />
    </Suspense>
  );
}

async function Ballot({ params }: { params: PageProps<"/votes/[id]">["params"] }) {
  const { id } = await params;
  const b = await apiGet<BallotOut>(`/ballots/${encodeURIComponent(id)}`);
  return (
    <>
      <title>{`${b.title} · LDS Connect`}</title>
      <Link href="/votes" className="text-sm text-lds-green underline">
        ← Tous les votes
      </Link>
      <header>
        <p className="text-xs font-semibold uppercase tracking-wide text-lds-red">{BALLOT_KIND_LABEL[b.kind]}</p>
        <h1 className="text-2xl font-bold text-green-900">{b.title}</h1>
        {b.description && <p className="mt-1 text-stone-700">{b.description}</p>}
        <p className="mt-1 text-sm text-stone-600">
          Vote du {formatDateTime(b.opens_at)} au {formatDateTime(b.closes_at)}
        </p>
      </header>

      {b.state === "open" && <VoteWidget ballot={b} />}
      {b.state === "upcoming" && <p className="rounded bg-blue-50 p-3 text-blue-900">Le vote ouvrira le {formatDateTime(b.opens_at)}.</p>}
      {b.state === "closed" && <p className="rounded bg-stone-100 p-3">Le vote est terminé.</p>}

      <section className="space-y-2">
        <h2 className="text-lg font-bold text-green-900">Résultats{b.state === "open" ? " provisoires" : ""}</h2>
        {b.results_visible && b.results ? (
          <>
            <ResultsBars results={b.results} />
            <p className="text-xs text-stone-500">{b.results.participants} votant(s).</p>
          </>
        ) : (
          <p className="text-sm text-stone-600">Les résultats seront publiés le {formatDateTime(b.results_publish_at)}.</p>
        )}
      </section>
    </>
  );
}
