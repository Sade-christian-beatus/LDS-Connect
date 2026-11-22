import { Suspense } from "react";
import { BallotAdminView } from "./ballot-admin";

export default function ScrutinPage() {
  return (
    <Suspense fallback={<p className="text-stone-500">Chargement…</p>}>
      <BallotAdminView />
    </Suspense>
  );
}
