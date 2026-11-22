"use client";
// Vote en trois étapes : choix → numéro de téléphone → code reçu par SMS.
import { useRouter } from "next/navigation";
import { useState } from "react";
import { TeamBadge } from "@/components/TeamBadge";
import type { BallotOut, CodeSent } from "@/lib/types";

async function post<T>(path: string, body: unknown): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`/api/v1${path}`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
  } catch {
    throw new Error("Pas de connexion : vérifiez votre réseau et réessayez.");
  }
  if (res.status === 429) throw new Error("Trop de demandes : patientez quelques minutes avant de réessayer.");
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(typeof data.detail === "string" ? data.detail : "Une erreur est survenue, réessayez.");
  }
  return res.status === 204 ? (undefined as T) : ((await res.json()) as T);
}

export function VoteWidget({ ballot }: { ballot: BallotOut }) {
  const router = useRouter();
  const [choices, setChoices] = useState<string[]>([]);
  const [phone, setPhone] = useState("");
  const [sent, setSent] = useState<CodeSent | null>(null);
  const [code, setCode] = useState("");
  const [done, setDone] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const multi = ballot.max_choices > 1;

  const toggle = (id: string) =>
    setChoices((prev) =>
      prev.includes(id) ? prev.filter((c) => c !== id) : multi ? (prev.length < ballot.max_choices ? [...prev, id] : prev) : [id],
    );

  async function run(fn: () => Promise<void>) {
    setBusy(true);
    setError(null);
    try {
      await fn();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  if (done) {
    return (
      <div role="status" className="rounded-xl bg-green-50 p-5 text-green-900">
        <p className="text-lg font-bold">Merci, votre vote est enregistré !</p>
        <p className="text-sm">Un seul vote est possible par numéro pour ce scrutin.</p>
      </div>
    );
  }

  return (
    <section className="space-y-4 rounded-xl border border-stone-200 bg-white p-4" aria-label="Voter">
      <fieldset disabled={!!sent} className="space-y-2">
        <legend className="font-semibold">
          1. {multi ? `Choisissez jusqu'à ${ballot.max_choices} propositions` : "Choisissez votre favori"}
          {multi && <span className="ml-2 text-sm font-normal text-stone-500">({choices.length}/{ballot.max_choices})</span>}
        </legend>
        <ul className="grid gap-2 sm:grid-cols-2">
          {ballot.options.map((o) => {
            const on = choices.includes(o.id);
            return (
              <li key={o.id}>
                <label
                  className={`flex cursor-pointer items-center gap-3 rounded-lg border p-3 ${on ? "border-lds-green bg-green-50" : "border-stone-200"}`}
                >
                  <input type={multi ? "checkbox" : "radio"} name="choice" checked={on} onChange={() => toggle(o.id)} className="h-4 w-4" />
                  {o.team && <TeamBadge team={o.team} size="sm" />}
                  <span className="flex-1">
                    <span className="block font-medium">{o.label}</span>
                    {o.team && <span className="text-xs text-stone-500">{o.team.name}</span>}
                  </span>
                </label>
              </li>
            );
          })}
        </ul>
      </fieldset>

      {!sent ? (
        <form
          className="space-y-2"
          onSubmit={(e) => {
            e.preventDefault();
            if (!choices.length) return setError("Choisissez d'abord une proposition.");
            run(async () => setSent(await post<CodeSent>(`/ballots/${ballot.id}/code`, { phone, choices })));
          }}
        >
          <label className="block font-semibold" htmlFor="phone">
            2. Votre numéro de téléphone
          </label>
          <div className="flex gap-2">
            <input
              id="phone"
              type="tel"
              inputMode="tel"
              autoComplete="tel"
              placeholder="70 12 34 56"
              required
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              className="w-full rounded border border-stone-300 px-3 py-2"
            />
            <button type="submit" disabled={busy} className="whitespace-nowrap rounded bg-lds-green px-4 py-2 font-semibold text-white disabled:opacity-60">
              Recevoir mon code
            </button>
          </div>
          <p className="text-xs text-stone-500">
            Numéros du Burkina Faso. Votre numéro sert uniquement à garantir un vote par personne : il n&apos;est ni publié,
            ni utilisé à d&apos;autres fins.
          </p>
        </form>
      ) : (
        <form
          className="space-y-2"
          onSubmit={(e) => {
            e.preventDefault();
            run(async () => {
              await post(`/ballots/${ballot.id}/vote`, { challenge_id: sent.challenge_id, code });
              setDone(true);
              router.refresh(); // résultats en continu
            });
          }}
        >
          <label className="block font-semibold" htmlFor="code">
            3. Code reçu par SMS au {sent.phone_hint}
          </label>
          <div className="flex gap-2">
            <input
              id="code"
              inputMode="numeric"
              autoComplete="one-time-code"
              pattern="[0-9]{6}"
              maxLength={6}
              required
              value={code}
              onChange={(e) => setCode(e.target.value.replace(/\D/g, ""))}
              className="w-40 rounded border border-stone-300 px-3 py-2 text-center font-mono text-lg tracking-widest"
            />
            <button type="submit" disabled={busy} className="rounded bg-lds-green px-4 py-2 font-semibold text-white disabled:opacity-60">
              Valider mon vote
            </button>
          </div>
          <button type="button" className="text-xs underline" onClick={() => { setSent(null); setCode(""); }}>
            Modifier mon choix ou mon numéro
          </button>
        </form>
      )}

      {error && (
        <p role="alert" className="rounded bg-red-50 p-2 text-sm text-lds-red">
          {error}
        </p>
      )}
    </section>
  );
}
