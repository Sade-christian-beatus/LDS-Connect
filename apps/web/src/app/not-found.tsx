import Link from "next/link";
import { Ball, PitchLines } from "@/components/Illustrations";

export default function NotFound() {
  return (
    <main className="relative flex min-h-screen flex-col items-center justify-center overflow-hidden bg-pitch px-6 text-center text-white">
      <PitchLines className="text-white/[0.07]" />
      <div className="relative space-y-4">
        <Ball className="mx-auto h-20 w-20 animate-bounce" />
        <p className="text-sm font-bold uppercase tracking-[0.3em] text-lds-gold">Hors-jeu</p>
        <h1 className="text-4xl font-black">Page introuvable</h1>
        <p className="mx-auto max-w-md text-green-100">
          Cette page n&apos;existe pas ou plus : le match a peut-être été déplacé, ou le lien est incomplet.
        </p>
        <div className="flex flex-wrap justify-center gap-2 pt-2">
          <Link href="/" className="rounded-full bg-lds-gold px-5 py-2.5 font-bold text-pitch">
            Retour à l&apos;accueil
          </Link>
          <Link href="/calendrier" className="rounded-full border border-white/30 px-5 py-2.5 font-semibold hover:bg-white/10">
            Calendrier
          </Link>
        </div>
      </div>
    </main>
  );
}
