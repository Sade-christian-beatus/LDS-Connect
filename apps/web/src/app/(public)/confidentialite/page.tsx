import type { Metadata } from "next";
import { LegalPage } from "@/components/LegalPage";

export const metadata: Metadata = { title: "Politique de confidentialité" };

export default function ConfidentialitePage() {
  return (
    <LegalPage title="Politique de confidentialité" updated="[date de publication]">
      <section>
        <h2>1. Qui traite vos données ?</h2>
        <p>
          Le responsable de traitement est la Ligue de la Souveraineté, [représentée par son Secrétariat exécutif],
          [adresse]. LUPORA Group intervient comme prestataire technique et [l&apos;hébergeur] comme hébergeur. Les
          traitements sont conduits conformément à la loi n° 001-2021/AN du 30 mars 2021 portant protection des
          personnes à l&apos;égard du traitement des données à caractère personnel et déclarés auprès de la Commission de
          l&apos;informatique et des libertés (CIL) [référence de la déclaration].
        </p>
      </section>
      <section>
        <h2>2. Joueurs et encadreurs</h2>
        <ul>
          <li>
            <strong>Données</strong> : identité, date et lieu de naissance, nationalité, poste, numéro de maillot,
            région de résidence, numéro de CNIB, téléphone, photo d&apos;identité de licence, statistiques sportives.
          </li>
          <li>
            <strong>Pourquoi</strong> : délivrer les licences, contrôler l&apos;identité au stade, organiser les matchs,
            appliquer le règlement (discipline, classements) et informer le public.
          </li>
          <li>
            <strong>Ce qui est public</strong> : uniquement le nom d&apos;usage (par exemple « A. Ouédraogo »), le poste,
            l&apos;équipe, le numéro, l&apos;âge en années et les statistiques sportives. Jamais la date de naissance, le
            prénom complet, la CNIB, le téléphone ni la photo.
          </li>
          <li>
            <strong>Protection</strong> : CNIB et téléphones chiffrés ; leur consultation est enregistrée au nom de la
            personne qui les consulte ; la photo n&apos;est visible que par le club, la Ligue et les contrôleurs.
          </li>
          <li>
            <strong>Mineurs</strong> : la compétition accueille des joueurs dès 16 ans. L&apos;autorisation d&apos;un parent
            ou tuteur est enregistrée avant l&apos;ajout d&apos;une photo.
          </li>
        </ul>
      </section>
      <section>
        <h2>3. Votes du public</h2>
        <p>
          Votre numéro de téléphone sert uniquement à vous envoyer un code de vote par SMS et à garantir un vote par
          personne. Il est chiffré, n&apos;est jamais publié, ni réutilisé, ni transmis ; les résultats et procès-verbaux
          n&apos;en contiennent qu&apos;une empreinte. Votre adresse IP n&apos;est conservée que sous forme d&apos;empreinte, pour
          détecter les votes en masse.
        </p>
      </section>
      <section>
        <h2>4. Billetterie</h2>
        <p>
          Votre nom et votre numéro servent à la commande, au paiement mobile money et à l&apos;envoi du lien de vos billets.
          Le nom figure sur vos billets ; le numéro est chiffré. Le QR code d&apos;un billet ne contient ni votre nom ni votre
          numéro. Le paiement est traité par [l&apos;opérateur ou l&apos;agrégateur de paiement] : la Ligue ne reçoit jamais
          votre code secret mobile money.
        </p>
      </section>
      <section>
        <h2>5. Durées de conservation</h2>
        <ul>
          <li>Licences et feuilles de match : [durée à fixer par la Ligue] (historique sportif de la compétition).</li>
          <li>Codes de vote : [30 jours après la clôture du scrutin] ; empreintes : [durée].</li>
          <li>Commandes de billets : [durée imposée par les obligations comptables].</li>
          <li>Journal des actions des officiels : [durée].</li>
        </ul>
      </section>
      <section>
        <h2>6. Vos droits</h2>
        <p>
          Vous pouvez demander l&apos;accès à vos données, leur rectification ou leur effacement, et vous opposer à un
          traitement, en écrivant à [adresse électronique du référent données personnelles] avec la mention « Données
          personnelles ». Un joueur peut aussi s&apos;adresser à son club. Les résultats sportifs validés sont conservés pour
          l&apos;intégrité de la compétition. En cas de désaccord, vous pouvez saisir la CIL du Burkina Faso.
        </p>
      </section>
      <section>
        <h2>7. Cookies et stockage sur l&apos;appareil</h2>
        <p>
          Le site n&apos;utilise ni publicité ni outil de mesure d&apos;audience tiers. Il conserve seulement sur votre appareil
          : le choix du thème clair ou sombre, les références de vos commandes de billets (pour les retrouver hors
          connexion) et, pour les officiels, un cookie de session sécurisé.
        </p>
      </section>
    </LegalPage>
  );
}
