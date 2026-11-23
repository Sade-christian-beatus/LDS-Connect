"use client";
// Accréditations : presse, officiels, équipes, sécurité, bénévoles, partenaires.
import { useBrandLogo } from "@/lib/brand";
import { BrandLogo } from "@/components/BrandLogo";
import { useCallback, useEffect, useState } from "react";
import { Badge, Button, Dialog, Field, inputClass, Notice } from "@/components/admin/ui";
import { RequireAuth } from "@/components/RequireAuth";
import { ACCREDITATION_LABEL } from "@/lib/access";
import { useAuth } from "@/lib/auth";
import { formatDate } from "@/lib/format";
import type { Accreditation, AccreditationCategory } from "@/lib/types";
import { useApi } from "@/lib/use-api";

export default function AccreditationsPage() {
  return (
    <RequireAuth permission="accreditation:manage">
      <Accreditations />
    </RequireAuth>
  );
}

const ZONES = ["Pelouse", "Vestiaires", "Tribune de presse", "Zone mixte", "Tribune d'honneur", "Toutes zones"];
const today = () => new Date().toISOString().slice(0, 10);

function Accreditations() {
  const { api } = useAuth();
  const { data, reload } = useApi<Accreditation[]>("/admin/accreditations");
  const [form, setForm] = useState<{
    full_name: string;
    organisation: string;
    category: AccreditationCategory;
    zones: string[];
    valid_from: string;
    valid_until: string;
  } | null>(null);
  const [card, setCard] = useState<Accreditation | null>(null);
  const [revoke, setRevoke] = useState<{ acc: Accreditation; reason: string } | null>(null);
  const [filter, setFilter] = useState("");
  const [notice, setNotice] = useState<{ tone: "ok" | "error"; text: string } | null>(null);
  const fail = useCallback((e: unknown) => setNotice({ tone: "error", text: e instanceof Error ? e.message : String(e) }), []);

  async function create(e: React.FormEvent) {
    e.preventDefault();
    if (!form) return;
    try {
      const a = await api<Accreditation>("/admin/accreditations", {
        method: "POST",
        body: JSON.stringify({ ...form, organisation: form.organisation || null }),
      });
      setForm(null);
      reload();
      setCard(a);
    } catch (err) {
      fail(err);
    }
  }

  async function doRevoke(e: React.FormEvent) {
    e.preventDefault();
    if (!revoke) return;
    try {
      await api(`/admin/accreditations/${revoke.acc.id}/revoke`, { method: "POST", body: JSON.stringify({ reason: revoke.reason }) });
      setNotice({ tone: "ok", text: `Accréditation de ${revoke.acc.full_name} révoquée : elle sera refusée aux entrées` });
      setRevoke(null);
      reload();
    } catch (err) {
      fail(err);
    }
  }

  const list = (data ?? []).filter((a) => !filter || a.category === filter);

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-black tracking-tight text-pitch">Accréditations</h1>
          <p className="text-sm text-stone-600">Cartes à QR signé, contrôlées aux entrées comme les billets (y compris hors connexion).</p>
        </div>
        <Button
          onClick={() =>
            setForm({ full_name: "", organisation: "", category: "press", zones: [], valid_from: today(), valid_until: today() })
          }
        >
          + Nouvelle accréditation
        </Button>
      </div>
      <Notice notice={notice} onClose={() => setNotice(null)} />

      <div className="flex flex-wrap gap-1 text-sm" role="group" aria-label="Filtrer par catégorie">
        {[["", "Toutes"], ...Object.entries(ACCREDITATION_LABEL)].map(([k, v]) => (
          <button
            key={k}
            type="button"
            aria-pressed={filter === k}
            onClick={() => setFilter(k)}
            className={`rounded-full border px-3 py-1 ${filter === k ? "border-lds-green bg-lds-green text-white" : "border-stone-300 bg-white"}`}
          >
            {v}
          </button>
        ))}
      </div>

      {data && list.length === 0 && <p className="text-stone-600">Aucune accréditation.</p>}
      <ul className="grid gap-2 md:grid-cols-2">
        {list.map((a) => (
          <li key={a.id} className={`flex items-center gap-3 rounded-lg border bg-white p-3 ${a.revoked_at ? "border-stone-200 opacity-60" : "border-stone-200"}`}>
            <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-green-100 text-xs font-bold text-green-900">
              {ACCREDITATION_LABEL[a.category].slice(0, 3).toUpperCase()}
            </span>
            <span className="min-w-0 flex-1">
              <span className="block truncate font-semibold">{a.full_name}</span>
              <span className="block truncate text-xs text-stone-600">
                {ACCREDITATION_LABEL[a.category]}
                {a.organisation ? ` · ${a.organisation}` : ""} · du {formatDate(a.valid_from)} au {formatDate(a.valid_until)}
              </span>
            </span>
            {a.revoked_at ? (
              <Badge tone="red">Révoquée</Badge>
            ) : (
              <span className="flex gap-2 text-xs">
                <button type="button" className="underline" onClick={() => setCard(a)}>
                  Carte
                </button>
                <button type="button" className="text-lds-red underline" onClick={() => setRevoke({ acc: a, reason: "" })}>
                  Révoquer
                </button>
              </span>
            )}
          </li>
        ))}
      </ul>

      <Dialog open={!!form} title="Nouvelle accréditation" onClose={() => setForm(null)}>
        {form && (
          <form onSubmit={create} className="grid gap-3 sm:grid-cols-2">
            <Field label="Nom complet *">
              <input required minLength={3} className={inputClass} value={form.full_name} onChange={(e) => setForm({ ...form, full_name: e.target.value })} />
            </Field>
            <Field label="Organisation">
              <input className={inputClass} placeholder="Média, institution…" value={form.organisation} onChange={(e) => setForm({ ...form, organisation: e.target.value })} />
            </Field>
            <Field label="Catégorie *">
              <select className={inputClass} value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value as AccreditationCategory })}>
                {Object.entries(ACCREDITATION_LABEL).map(([k, v]) => (
                  <option key={k} value={k}>
                    {v}
                  </option>
                ))}
              </select>
            </Field>
            <div />
            <Field label="Valable du *">
              <input required type="date" className={inputClass} value={form.valid_from} onChange={(e) => setForm({ ...form, valid_from: e.target.value })} />
            </Field>
            <Field label="au *">
              <input required type="date" className={inputClass} value={form.valid_until} onChange={(e) => setForm({ ...form, valid_until: e.target.value })} />
            </Field>
            <fieldset className="sm:col-span-2">
              <legend className="text-sm text-stone-700">Zones autorisées</legend>
              <div className="mt-1 flex flex-wrap gap-2">
                {ZONES.map((z) => (
                  <label key={z} className="flex items-center gap-1 rounded border border-stone-200 px-2 py-1 text-sm">
                    <input
                      type="checkbox"
                      checked={form.zones.includes(z)}
                      onChange={() => setForm({ ...form, zones: form.zones.includes(z) ? form.zones.filter((x) => x !== z) : [...form.zones, z] })}
                    />
                    {z}
                  </label>
                ))}
              </div>
            </fieldset>
            <div className="flex justify-end gap-2 sm:col-span-2">
              <Button variant="secondary" onClick={() => setForm(null)}>
                Annuler
              </Button>
              <Button type="submit">Créer et afficher la carte</Button>
            </div>
          </form>
        )}
      </Dialog>

      <Dialog open={!!card} title="Carte d'accréditation" onClose={() => setCard(null)}>
        {card && <Card acc={card} onError={fail} />}
      </Dialog>

      <Dialog open={!!revoke} title={`Révoquer l'accréditation de ${revoke?.acc.full_name ?? ""}`} onClose={() => setRevoke(null)}>
        {revoke && (
          <form onSubmit={doRevoke} className="space-y-3">
            <p className="text-sm text-stone-600">Définitif. Les appareils de contrôle la refuseront dès leur prochaine préparation.</p>
            <Field label="Motif *">
              <input required minLength={3} className={inputClass} value={revoke.reason} onChange={(e) => setRevoke({ ...revoke, reason: e.target.value })} />
            </Field>
            <div className="flex justify-end gap-2">
              <Button variant="secondary" onClick={() => setRevoke(null)}>
                Retour
              </Button>
              <Button type="submit" variant="danger">
                Révoquer
              </Button>
            </div>
          </form>
        )}
      </Dialog>
    </div>
  );
}

function Card({ acc, onError }: { acc: Accreditation; onError: (e: unknown) => void }) {
  const { raw } = useAuth();
  const logo = useBrandLogo();
  const [qr, setQr] = useState<string | null>(null);
  useEffect(() => {
    let url: string | null = null;
    let active = true;
    raw(`/admin/accreditations/${acc.id}/qr.svg`)
      .then((r) => r.blob())
      .then((b) => {
        if (!active) return;
        url = URL.createObjectURL(b);
        setQr(url);
      })
      .catch(onError);
    return () => {
      active = false;
      if (url) URL.revokeObjectURL(url);
    };
  }, [acc.id, raw, onError]);

  return (
    <div className="space-y-3">
      <div className="print-area mx-auto w-72 overflow-hidden rounded-xl border-2 border-lds-green text-center">
        <div className="flex items-center gap-2 bg-lds-green px-3 py-2 text-left text-white">
          <BrandLogo logoUrl={logo} size="md" className="shadow-none" />
          <div>
          <p className="text-[10px] font-bold uppercase tracking-widest">Ligue de la Souveraineté</p>
          <p className="text-xl font-black uppercase">{ACCREDITATION_LABEL[acc.category]}</p>
          </div>
        </div>
        <div className="space-y-1 p-3">
          <p className="text-lg font-bold leading-tight">{acc.full_name}</p>
          {acc.organisation && <p className="text-sm text-stone-700">{acc.organisation}</p>}
          {/* eslint-disable-next-line @next/next/no-img-element -- QR SVG authentifié (blob local) */}
          {qr ? <img src={qr} alt={`QR code de l'accréditation ${acc.code}`} className="mx-auto h-44 w-44" /> : <div className="mx-auto h-44 w-44 animate-pulse bg-stone-100" />}
          <p className="font-mono text-sm">{acc.code}</p>
          {acc.zones.length > 0 && <p className="text-xs">Zones : {acc.zones.join(" · ")}</p>}
          <p className="text-xs text-stone-600">
            Valable du {formatDate(acc.valid_from)} au {formatDate(acc.valid_until)}
          </p>
        </div>
        <div className="h-1.5 bg-gradient-to-r from-lds-red via-yellow-400 to-lds-green" />
      </div>
      <div className="flex justify-center">
        <Button variant="secondary" onClick={() => window.print()}>
          Imprimer la carte
        </Button>
      </div>
    </div>
  );
}
