"use client";
// Billets achetés sur cet appareil (sans compte).
import Link from "next/link";
import { useEffect, useState } from "react";
import { formatDate, formatTime } from "@/lib/format";
import { cachedOrder, forgetOrder, type SavedOrder, savedOrders } from "@/lib/my-tickets";

export default function MesBilletsPage() {
  const [list, setList] = useState<SavedOrder[] | null>(null);
  useEffect(() => {
    Promise.resolve().then(() => setList(savedOrders()));
  }, []);

  return (
    <>
      <title>Mes billets · LDS Connect</title>
      <h1 className="text-3xl font-black text-green-900">Mes billets</h1>
      <p className="text-stone-600">
        Les billets achetés depuis ce téléphone s&apos;affichent ici, même sans connexion. Achat fait sur un autre appareil ? Ouvrez le
        lien reçu par SMS.
      </p>
      {list && list.length === 0 && (
        <div className="rounded-xl border border-dashed border-stone-300 bg-white p-8 text-center">
          <p className="text-stone-600">Aucun billet sur cet appareil.</p>
          <Link href="/billetterie" className="mt-3 inline-block rounded-lg bg-lds-green px-4 py-2 font-semibold text-white">
            Acheter des billets
          </Link>
        </div>
      )}
      <ul className="space-y-3">
        {list?.map((o) => {
          const c = cachedOrder(o.reference);
          const m = c?.order.match;
          return (
            <li key={o.reference} className="flex items-center gap-3 rounded-xl bg-white p-4 shadow-sm ring-1 ring-stone-200">
              <Link href={`/billets/${o.reference}?k=${o.key}`} className="flex-1">
                <span className="block text-lg font-bold">
                  {m ? `${m.home?.short_name ?? "?"} – ${m.away?.short_name ?? "?"}` : (o.label ?? "Commande en cours")}
                </span>
                <span className="text-sm text-stone-600">
                  {m && `${formatDate(m.kickoff_at)} · ${formatTime(m.kickoff_at)} · `}
                  {c ? `${c.order.tickets.length} billet(s) · ${c.order.type_name}` : "Paiement non confirmé"}
                </span>
              </Link>
              <button
                type="button"
                className="text-xs text-stone-500 underline"
                onClick={() => {
                  if (confirm("Retirer cette commande de cet appareil ? Le lien reçu par SMS reste valable.")) {
                    forgetOrder(o.reference);
                    setList(savedOrders());
                  }
                }}
              >
                Retirer
              </button>
            </li>
          );
        })}
      </ul>
    </>
  );
}
