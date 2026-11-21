import { Suspense } from "react";
import { TeamAdmin } from "./team-admin";

export default function FicheEquipePage() {
  return (
    <Suspense fallback={<p className="text-stone-500">Chargement…</p>}>
      <TeamAdmin />
    </Suspense>
  );
}
