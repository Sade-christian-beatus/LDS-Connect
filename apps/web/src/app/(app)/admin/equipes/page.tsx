"use client";
import Link from "next/link";
import { Badge } from "@/components/admin/ui";
import { RequireAuth } from "@/components/RequireAuth";
import { TeamBadge } from "@/components/TeamBadge";
import type { Rules, TeamOverview } from "@/lib/types";
import { useApi } from "@/lib/use-api";

export default function RegistrePage() {
  return (
    <RequireAuth permission="squad:read">
      <Overview />
    </RequireAuth>
  );
}

function Overview() {
  const { data, error } = useApi<TeamOverview[]>("/admin/teams/overview");
  const { data: rules } = useApi<Rules>("/rules");
  if (error) return <p className="text-lds-red">{error}</p>;
  if (!data) return <p className="text-stone-500">Chargement du registre…</p>;

  const ok = data.filter((t) => t.compliant).length;
  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h1 className="text-2xl font-black tracking-tight text-pitch">Registre des équipes</h1>
        <p className="text-sm text-stone-600">
          {ok}/{data.length} équipe(s) conforme(s)
        </p>
      </div>
      <div className="overflow-x-auto rounded-lg border border-stone-200 bg-white">
        <table className="w-full text-sm">
          <thead className="bg-stone-100 text-left text-xs uppercase text-stone-600">
            <tr>
              <th className="px-3 py-2">Équipe</th>
              <th className="px-2 py-2">Poule</th>
              <th className="px-2 py-2 text-center">Joueurs</th>
              <th className="px-2 py-2 text-center">Encadreurs</th>
              <th className="px-2 py-2 text-center" title={`Joueurs de moins de ${rules?.youth_age_limit ?? "?"} ans`}>
                −{rules?.youth_age_limit ?? "?"} ans
              </th>
              <th className="px-2 py-2 text-center">Locaux</th>
              <th className="px-2 py-2 text-center">Licences</th>
              <th className="px-3 py-2">État</th>
            </tr>
          </thead>
          <tbody>
            {data.map((t) => (
              <tr key={t.team.id} className="border-t border-stone-100 align-top">
                <td className="px-3 py-2">
                  <Link href={`/admin/equipes/${t.team.id}`} className="flex items-center gap-2 font-medium hover:underline">
                    <TeamBadge team={t.team} size="sm" />
                    {t.team.name}
                  </Link>
                </td>
                <td className="px-2 py-2">{t.team.pool_code}</td>
                <td className="px-2 py-2 text-center tabular-nums">{t.players}/{rules?.max_squad_players ?? "?"}</td>
                <td className="px-2 py-2 text-center tabular-nums">{t.staff}/{rules?.max_staff ?? "?"}</td>
                <td className="px-2 py-2 text-center tabular-nums">{t.youth_players}</td>
                <td className="px-2 py-2 text-center tabular-nums">{t.local_players}</td>
                <td className="px-2 py-2 text-center tabular-nums">
                  {t.licences_active}
                  {t.licences_missing > 0 && <Badge tone="amber">+{t.licences_missing} à délivrer</Badge>}
                  {t.licences_blocked > 0 && <Badge tone="red">{t.licences_blocked} bloquée(s)</Badge>}
                </td>
                <td className="px-3 py-2">
                  {t.compliant ? (
                    <Badge tone="green">Conforme</Badge>
                  ) : (
                    <ul className="space-y-0.5 text-xs text-lds-red">
                      {t.issues.map((i) => (
                        <li key={i}>• {i}</li>
                      ))}
                    </ul>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="text-xs text-stone-500">
        Effectifs maximum, quota de moins de 19 ans et âge minimum selon les règles de la saison.
      </p>
    </div>
  );
}
