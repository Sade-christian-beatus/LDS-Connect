import type { Metadata } from "next";
import Link from "next/link";
import { LegalPage } from "@/components/LegalPage";

export const metadata: Metadata = { title: "Conditions générales de vente" };

export default function ConditionsDeVentePage() {
  return (
    <LegalPage title="Conditions générales de vente des billets" updated="[date de publication]">
      <section>
        <h2>1. Objet</h2>
        <p>
          Ces conditions régissent la vente en ligne des billets pour les matchs de la Ligue de la Souveraineté sur LDS
          Connect. Toute commande suppose leur acceptation.
        </p>
      </section>
      <section>
        <h2>2. Commande et paiement</h2>
        <ul>
          <li>L&apos;achat se fait sans compte : nom, numéro de téléphone du Burkina Faso, catégorie et nombre de places.</li>
          <li>Le nombre de billets par commande est limité (indiqué pour chaque catégorie).</li>
          <li>
            Les places sont réservées 15 minutes pendant le paiement par mobile money. Passé ce délai sans paiement, elles
            sont remises en vente.
          </li>
          <li>Les prix sont indiqués en francs CFA (FCFA), [toutes taxes comprises / frais de service éventuels].</li>
          <li>La vente est définitive dès la confirmation du paiement par l&apos;opérateur.</li>
        </ul>
      </section>
      <section>
        <h2>3. Billets électroniques</h2>
        <ul>
          <li>
            Après le paiement, vos billets s&apos;affichent à l&apos;écran et le lien vous est envoyé par SMS. Ils restent
            consultables hors connexion sur l&apos;appareil utilisé pour l&apos;achat (page{" "}
            <Link href="/billets" className="font-semibold text-lds-green underline">
              Mes billets
            </Link>
            ).
          </li>
          <li>Chaque billet porte un QR code unique, valable pour une seule entrée : le premier passage au contrôle fait foi.</li>
          <li>Ne partagez pas le lien ni les QR codes : une copie utilisée avant vous ne pourra pas être remplacée.</li>
          <li>Les billets sont nominatifs à titre indicatif ; [la Ligue peut demander une pièce d&apos;identité à l&apos;entrée].</li>
        </ul>
      </section>
      <section>
        <h2>4. Report ou annulation d&apos;un match</h2>
        <ul>
          <li>Match reporté : les billets restent valables pour la nouvelle date, [sauf demande de remboursement dans un délai de … jours].</li>
          <li>Match annulé ou joué à huis clos : [modalités et délai de remboursement à fixer par la Ligue].</li>
          <li>
            Si un paiement est confirmé après la fin de la réservation alors qu&apos;il ne reste plus de place, la commande
            est annulée et intégralement remboursée [délai et moyen de remboursement].
          </li>
          <li>Hors ces cas, les billets ne sont ni repris ni échangés.</li>
        </ul>
      </section>
      <section>
        <h2>5. Billet perdu et réclamations</h2>
        <p>
          Conservez la référence de commande (CMD-…). En cas de perte du lien ou de réclamation, contactez [adresse
          électronique ou numéro du service billetterie] en indiquant cette référence et le numéro utilisé pour
          l&apos;achat.
        </p>
      </section>
      <section>
        <h2>6. Accès au stade</h2>
        <p>
          L&apos;accès est soumis au règlement intérieur du stade et aux consignes de sécurité. [Objets interdits, âge
          minimum ou accompagnement des mineurs, conditions d&apos;exclusion.]
        </p>
      </section>
      <section>
        <h2>7. Données personnelles et droit applicable</h2>
        <p>
          Les données de commande sont traitées selon la{" "}
          <Link href="/confidentialite" className="font-semibold text-lds-green underline">
            politique de confidentialité
          </Link>
          . Ces conditions sont soumises au droit burkinabè ; [juridiction compétente en cas de litige].
        </p>
      </section>
    </LegalPage>
  );
}
