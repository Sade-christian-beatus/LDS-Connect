"use client";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useState } from "react";
import { Badge, Button, Notice } from "@/components/admin/ui";
import { RequireAuth } from "@/components/RequireAuth";
import { ResultsBars } from "@/components/ResultsBars";
import { useAuth } from "@/lib/auth";
import { BALLOT_KIND_LABEL, ballotBadge, formatDateTime } from "@/lib/format";
import type { BallotAdmin, Voter } from "@/lib/types";
import { useApi } from "@/lib/use-api";

export function BallotAdminView() {
  const { id } = useParams<{ id: string }>();
  return (
    <RequireAuth permission="vote:manage">
      <BallotScreen id={id} />
    </RequireAuth>
  );
}

function BallotScreen({ id }: { id: string }) {
  const { api, raw } = useAuth();
  const { data: b, reload } = useApi<BallotAdmin>(`/admin/ballots/${id}`);
  const { data: flagged, reload: reloadFlagged } = useApi<Voter[]>(`/admin/ballots/${id}/voters?status=flagged`);
  const [notice, setNotice] = useState<{ tone: "ok" | "error"; text: string } | null>(null);

  const act = useCallback(
    async (action: string, ok: string, confirm?: string) => {
      if (confirm && !window.confirm(confirm)) return;
      try {
        await api(`/admin/ballots/${id}/${action}`, { method: "POST" });
        setNotice({ tone: "ok", text: ok });
        reload();
      } catch (e) {
        setNotice({ tone: "error", text: e instanceof Error ? e.message : String(e) });
      }
    },
    [api, id, reload],
  );

  async function review(voter: string, decision: "valid" | "rejected") {
    try {
      await api(`/admin/ballots/${id}/voters/${voter}/review`, { method: "POST", body: JSON.stringify({ decision }) });
      setNotice({ tone: "ok", text: decision === "valid" ? "Vote validé : il est compté" : "Vote rejeté" });
      reload();
      reloadFlagged();
    } catch (e) {
      setNotice({ tone: "error", text: e instanceof Error ? e.message : String(e) });
    }
  }

  async function download(path: string, filename: string) {
    try {
      const blob = await (await raw(path)).blob();
      const a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      a.download = filename;
      a.click();
      URL.revokeObjectURL(a.href);
    } catch (e) {
      setNotice({ tone: "error", text: e instanceof Error ? e.message : String(e) });
    }
  }

  if (!b) return <p className="text-stone-500">Chargement du scrutin…</p>;
  const st = ballotBadge(b);
  // Définitifs une fois le vote clos et tous les votes suspects examinés.
  const final = b.state === "closed" && b.flagged_voters === 0;

  return (
    <div className="space-y-4">
      <Link href="/admin/votes" className="text-sm text-lds-green underline">
        ← Tous les scrutins
      </Link>
      <header className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-green-900">{b.title}</h1>
          <p className="text-sm text-stone-600">
            {BALLOT_KIND_LABEL[b.kind]} · {b.max_choices} choix · du {formatDateTime(b.opens_at)} au {formatDateTime(b.closes_at)}
          </p>
          <p className="text-xs text-stone-500">
            Résultats :{" "}
            {b.results_visibility === "immediate" ? "publiés en continu" : `publiés le ${formatDateTime(b.results_publish_at)}`}
            {b.status === "published" && " (publication confirmée)"}
          </p>
        </div>
        <Badge tone={st.tone}>{st.label}</Badge>
      </header>
      <Notice notice={notice} onClose={() => setNotice(null)} />

      <div className="flex flex-wrap gap-2">
        {b.status === "draft" && (
          <Button onClick={() => act("open", "Scrutin ouvert au public", "Ouvrir le scrutin ? Les propositions seront figées.")}>
            Ouvrir le scrutin
          </Button>
        )}
        {b.status === "open" && (
          <Button variant="secondary" onClick={() => act("close", "Scrutin clos", "Clore le vote maintenant, avant la date prévue ?")}>
            Clore maintenant
          </Button>
        )}
        {b.state === "closed" && b.status !== "published" && (
          <Button onClick={() => act("publish", "Résultats publiés")}>Publier les résultats</Button>
        )}
        <Button variant="secondary" onClick={() => download(`/admin/ballots/${id}/results.csv`, `resultats-${id}.csv`)}>
          Résultats (CSV)
        </Button>
        <Button variant="secondary" onClick={() => download(`/admin/ballots/${id}/journal.csv`, `journal-votes-${id}.csv`)}>
          Journal des votes (CSV)
        </Button>
        <Link href={`/admin/votes/${id}/pv`} className="rounded border border-stone-300 bg-white px-3 py-1.5 text-sm">
          Procès-verbal
        </Link>
      </div>

      <section className="space-y-2 rounded-lg border border-stone-200 bg-white p-4">
        <h2 className="font-semibold">
          Résultats {final ? "définitifs" : "provisoires"} <span className="text-sm font-normal text-stone-500">({b.results?.participants ?? 0} votant(s) comptés)</span>
        </h2>
        {b.results && <ResultsBars results={b.results} />}
      </section>

      <section className="space-y-2 rounded-lg border border-stone-200 bg-white p-4">
        <h2 className="font-semibold">
          Votes à examiner <span className="text-sm font-normal text-stone-500">({flagged?.length ?? 0})</span>
        </h2>
        <p className="text-xs text-stone-500">
          Mis de côté automatiquement (votes en masse depuis une même connexion, numéros qui se suivent). Ils ne comptent
          qu&apos;une fois validés. Le numéro n&apos;est jamais affiché : seule son empreinte l&apos;est.
        </p>
        {flagged?.length === 0 && <p className="text-sm text-stone-600">Aucun vote suspect.</p>}
        <ul className="divide-y divide-stone-100">
          {flagged?.map((v) => (
            <li key={v.voter} className="flex flex-wrap items-center gap-3 py-2 text-sm">
              <span className="font-mono text-xs">{v.voter}</span>
              <span className="text-xs text-stone-500">{formatDateTime(v.cast_at)}</span>
              <span className="flex-1">{v.choices.join(", ")}</span>
              <span className="text-xs text-lds-red">{v.flag_reason}</span>
              <Button variant="link" onClick={() => review(v.voter, "valid")}>
                Valider
              </Button>
              <Button variant="link" className="!text-lds-red" onClick={() => review(v.voter, "rejected")}>
                Rejeter
              </Button>
            </li>
          ))}
        </ul>
        {b.rejected_voters > 0 && <p className="text-xs text-stone-500">{b.rejected_voters} votant(s) rejeté(s) après examen.</p>}
      </section>
    </div>
  );
}
