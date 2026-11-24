import type { Metadata } from "next";
import Link from "next/link";
import { LegalPage } from "@/components/LegalPage";

export const metadata: Metadata = { title: "Mentions légales" };

export default function MentionsLegalesPage() {
  return (
    <LegalPage title="Mentions légales" updated="[date de publication]">
      <section>
        <h2>1. Éditeur du site</h2>
        <p>
          Le site LDS Connect est édité par la <strong>Ligue de la Souveraineté</strong> ([forme juridique, numéro de
          récépissé ou d&apos;enregistrement]), dont le siège est situé [adresse], Ouagadougou, Burkina Faso.
        </p>
        <ul>
          <li>Directeur ou directrice de la publication : [nom et fonction]</li>
          <li>Contact : [adresse électronique] · [téléphone]</li>
        </ul>
      </section>
      <section>
        <h2>2. Conception et hébergement</h2>
        <p>Conception et développement : LUPORA Group, Ouagadougou, Burkina Faso, pour le compte de la Ligue.</p>
        <p>Hébergement : [nom de l&apos;hébergeur, adresse, pays d&apos;hébergement des données].</p>
      </section>
      <section>
        <h2>3. Propriété intellectuelle</h2>
        <p>
          Le nom, le logo et les éléments graphiques de la Ligue de la Souveraineté, ainsi que les logos des équipes,
          appartiennent à leurs titulaires respectifs. Toute reproduction sans autorisation écrite est interdite. Les
          résultats, calendriers et classements peuvent être cités en mentionnant la source « Ligue de la
          Souveraineté ».
        </p>
      </section>
      <section>
        <h2>4. Données personnelles</h2>
        <p>
          Le traitement des données (joueurs, encadreurs, votants, acheteurs de billets) est décrit dans la{" "}
          <Link href="/confidentialite" className="font-semibold text-lds-green underline">
            politique de confidentialité
          </Link>
          . Les ventes de billets sont régies par les{" "}
          <Link href="/conditions-de-vente" className="font-semibold text-lds-green underline">
            conditions générales de vente
          </Link>
          .
        </p>
      </section>
      <section>
        <h2>5. Responsabilité</h2>
        <p>
          Les informations sportives (horaires, lieux, résultats) sont publiées par la Ligue et peuvent évoluer. En cas
          de différence, les décisions officielles de la Ligue font foi. Les résultats sont publiés après validation de
          la feuille de match.
        </p>
      </section>
    </LegalPage>
  );
}
