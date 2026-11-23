import Link from "next/link";
import { Suspense } from "react";
import { Countdown } from "@/components/Countdown";
import { LiveScores } from "@/components/LiveScores";
import { MatchCard } from "@/components/MatchCard";
import { MatchHero } from "@/components/MatchHero";
import { ScorersTable } from "@/components/ScorersTable";
import { StandingsTable } from "@/components/StandingsTable";
import { TeamBadge } from "@/components/TeamBadge";
import { BALLOT_KIND_LABEL, formatDate, formatFcfa, formatTime } from "@/lib/format";
import { apiGet } from "@/lib/server-api";
import type { BallotOut, Match, MatchTickets, PoolStandings, Season, SeasonStats, Venue } from "@/lib/types";

export default function Accueil() {
  return (
    <Suspense fallback={<HomeSkeleton />}>
      <HomeContent />
    </Suspense>
  );
}

function HomeSkeleton() {
  return <div className="h-80 animate-pulse rounded-2xl bg-pitch/80" aria-label="Chargement…" />;
}

function SectionTitle({ children, href, more }: { children: React.ReactNode; href?: string; more?: string }) {
  return (
    <div className="mb-3 flex items-end justify-between gap-3">
      <h2 className="flex items-center gap-2 text-xl font-black tracking-tight text-heading">
        <span aria-hidden className="h-5 w-1.5 rounded-full bg-lds-red" />
        {children}
      </h2>
      {href && (
        <Link href={href} className="text-sm font-semibold text-lds-green hover:underline dark:text-green-300">
          {more ?? "Tout voir"} →
        </Link>
      )}
    </div>
  );
}

const optional = <T,>(p: Promise<T>, fallback: T) => p.catch(() => fallback);

async function HomeContent() {
  const [season, matches, standings, stats, venues, onSale, ballots] = await Promise.all([
    apiGet<Season>("/seasons/current"),
    apiGet<Match[]>("/matches"),
    apiGet<PoolStandings[]>("/standings"),
    apiGet<SeasonStats>("/stats?limit=5"),
    apiGet<Venue[]>("/venues"),
    optional(apiGet<MatchTickets[]>("/tickets/matches"), []),
    optional(apiGet<BallotOut[]>("/ballots"), []),
  ]);
  const upcoming = matches.filter((m) => m.status === "scheduled" && m.home && m.kickoff_at);
  const next = upcoming[0];
  const results = matches.filter((m) => m.status === "finished").slice(-6).reverse();
  const nextTickets = next && onSale.find((x) => x.match.id === next.id);
  const minPrice = nextTickets?.types.filter((t) => t.state === "on_sale").map((t) => t.price_fcfa);
  const openBallots = ballots.filter((b) => b.state === "open");

  return (
    <>
      {next ? (
        <section aria-label="Prochain match">
          <MatchHero match={next}>
            <div className="space-y-4">
              <Countdown to={next.kickoff_at!} />
              <div className="flex flex-wrap justify-center gap-2">
                {minPrice && minPrice.length > 0 && (
                  <Link href={`/billetterie/${next.id}`} className="rounded-full bg-lds-gold px-5 py-2.5 font-bold text-pitch shadow hover:brightness-105">
                    Acheter mes billets · dès {formatFcfa(Math.min(...minPrice))}
                  </Link>
                )}
                <Link href="/calendrier" className="rounded-full border border-white/30 px-5 py-2.5 font-semibold text-white hover:bg-white/10">
                  Calendrier complet
                </Link>
              </div>
            </div>
          </MatchHero>
        </section>
      ) : (
        <section className="relative overflow-hidden rounded-2xl bg-gradient-to-br from-pitch to-lds-green p-6 text-white sm:p-8">
          <p className="text-sm font-semibold uppercase tracking-widest text-lds-gold">{season.name}</p>
          <h1 className="mt-1 text-3xl font-black sm:text-4xl">Ligue de la Souveraineté</h1>
          <p className="mt-2 max-w-2xl text-green-50">
            20 équipes issues des 17 régions, deux poules : poule A à Ouagadougou, poule B à Bobo-Dioulasso.
          </p>
        </section>
      )}

      <LiveScores initial={matches.filter((m) => m.status === "live")} />

      {upcoming.length > 1 && (
        <section>
          <SectionTitle href="/calendrier" more="Calendrier">
            À venir
          </SectionTitle>
          <ul className="no-scrollbar -mx-4 flex snap-x gap-3 overflow-x-auto px-4 pb-2">
            {upcoming.slice(1, 9).map((m) => (
              <li key={m.id} className="w-64 shrink-0 snap-start">
                <div className="h-full overflow-hidden rounded-2xl border border-line bg-surface shadow-sm">
                  <div className="flex h-1.5">
                    <span className="flex-1" style={{ backgroundColor: m.home?.primary_color }} />
                    <span className="flex-1" style={{ backgroundColor: m.away?.primary_color }} />
                  </div>
                  <div className="p-4">
                    <p className="text-xs font-semibold uppercase tracking-wide text-subtle">
                      {formatDate(m.kickoff_at)} · {formatTime(m.kickoff_at)}
                    </p>
                    <div className="mt-3 space-y-2">
                      {[m.home, m.away].map((t, i) =>
                        t ? (
                          <Link key={i} href={`/equipes/${t.slug}`} className="flex items-center gap-2 font-semibold hover:underline">
                            <TeamBadge team={t} size="sm" />
                            <span className="truncate">{t.name}</span>
                          </Link>
                        ) : null,
                      )}
                    </div>
                    <p className="mt-3 truncate text-xs text-subtle">{m.venue ? `${m.venue.name}` : `Poule ${m.pool_code}`}</p>
                  </div>
                </div>
              </li>
            ))}
          </ul>
        </section>
      )}

      <section>
        <SectionTitle href="/resultats" more="Tous les résultats">
          Derniers résultats
        </SectionTitle>
        {results.length === 0 ? (
          <p className="rounded-xl border border-dashed border-line p-4 text-sm text-muted">
            Coup d&apos;envoi de la {season.name.toLowerCase()} le {new Date(season.starts_on).toLocaleDateString("fr-FR")}.
          </p>
        ) : (
          <div className="grid gap-3 md:grid-cols-2">
            {results.map((m) => (
              <MatchCard key={m.id} match={m} />
            ))}
          </div>
        )}
      </section>

      <section>
        <SectionTitle href="/classements" more="Classements complets">
          Classements
        </SectionTitle>
        <div className="grid gap-4 md:grid-cols-2">
          {standings.map((p) => (
            <StandingsTable key={p.pool_code} pool={p} compact />
          ))}
        </div>
      </section>

      <div className="grid gap-6 lg:grid-cols-[1.3fr_1fr]">
        <section>
          <SectionTitle href="/statistiques" more="Statistiques">
            Meilleurs buteurs
          </SectionTitle>
          <ScorersTable rows={stats.scorers} unit="buts" empty="Aucun but marqué pour le moment." />
        </section>
        <div className="space-y-4">
          <Link
            href={openBallots[0] ? `/votes/${openBallots[0].id}` : "/votes"}
            className="group block overflow-hidden rounded-2xl bg-gradient-to-br from-lds-red to-red-800 p-5 text-white shadow"
          >
            <p className="text-xs font-semibold uppercase tracking-widest text-red-100">Votes du public</p>
            <p className="mt-1 text-2xl font-black leading-tight">
              {openBallots[0] ? openBallots[0].title : "Élisez vos joueurs préférés"}
            </p>
            <p className="mt-1 text-sm text-red-100">
              {openBallots[0]
                ? `${BALLOT_KIND_LABEL[openBallots[0].kind]} · vote ouvert, gratuit, par SMS`
                : "Homme du match, but du mois, onze idéal…"}
            </p>
            <span className="mt-3 inline-block rounded-full bg-white px-4 py-1.5 text-sm font-bold text-lds-red group-hover:bg-red-50">
              {openBallots.length ? `Voter (${openBallots.length} ouvert${openBallots.length > 1 ? "s" : ""})` : "Voir les votes"}
            </span>
          </Link>
          <Link href="/billetterie" className="group block rounded-2xl bg-lds-gold p-5 text-pitch shadow">
            <p className="text-xs font-semibold uppercase tracking-widest">Billetterie</p>
            <p className="mt-1 text-2xl font-black leading-tight">Votre place au stade, sur votre téléphone</p>
            <p className="mt-1 text-sm">Paiement mobile money · billet à QR code, valable même sans réseau.</p>
            <span className="mt-3 inline-block rounded-full bg-pitch px-4 py-1.5 text-sm font-bold text-white">
              {onSale.length ? `${onSale.length} match${onSale.length > 1 ? "s" : ""} en vente` : "Voir la billetterie"}
            </span>
          </Link>
        </div>
      </div>

      <section>
        <SectionTitle>Lieux de la compétition</SectionTitle>
        <ul className="grid gap-3 sm:grid-cols-2">
          {season.pools.map((p) => (
            <li key={p.code} className="flex items-center gap-4 rounded-2xl border border-line bg-surface p-4 shadow-sm">
              <span className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-pitch text-lg font-black text-lds-gold">
                {p.code}
              </span>
              <span>
                <span className="block text-xs font-semibold uppercase tracking-wide text-lds-red">
                  {p.name} · {p.host_city}
                </span>
                {venues
                  .filter((v) => v.city === p.host_city)
                  .map((v) => (
                    <span key={v.id} className="block text-sm font-medium">
                      {v.name}
                    </span>
                  ))}
              </span>
            </li>
          ))}
        </ul>
      </section>
    </>
  );
}
