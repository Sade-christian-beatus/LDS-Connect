import { Suspense } from "react";
import { SheetRoute } from "./sheet-route";

// Coquille statique (mise en cache par le service worker pour tous les matchs) ;
// l'identifiant du match est lu dans l'URL côté navigateur.
export default function FeuilleDeMatchPage() {
  return (
    <Suspense fallback={<p className="text-stone-500">Chargement…</p>}>
      <SheetRoute />
    </Suspense>
  );
}
