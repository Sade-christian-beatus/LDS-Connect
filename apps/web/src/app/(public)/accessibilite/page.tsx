import type { Metadata } from "next";
import Link from "next/link";
import { LegalPage } from "@/components/LegalPage";

export const metadata: Metadata = { title: "Accessibilité" };

const link = "font-semibold text-lds-green underline dark:text-green-300";

export default function AccessibilitePage() {
  return (
    <LegalPage title="Accessibilité" updated="[date de publication]">
      <section>
        <h2>1. Notre engagement</h2>
        <p>
          LDS Connect doit pouvoir être utilisé par tout le monde, y compris par les personnes aveugles ou malvoyantes. Le
          site public vise le niveau AA des règles internationales d&apos;accessibilité du web (WCAG 2.1).
        </p>
        <p>
          <strong>État actuel : partiellement conforme.</strong> Toutes les pages publiques passent sans erreur un contrôle
          automatique, sur ordinateur comme sur téléphone. Des essais avec des personnes aveugles restent à mener : vos
          retours nous aideront à aller plus loin.
        </p>
      </section>

      <section>
        <h2>2. Utiliser le site avec un lecteur d&apos;écran</h2>
        <p>Le site fonctionne avec les lecteurs d&apos;écran gratuits déjà présents sur la plupart des appareils :</p>
        <ul>
          <li>
            <strong>Téléphone Android :</strong> TalkBack (Paramètres, Accessibilité, TalkBack).
          </li>
          <li>
            <strong>iPhone :</strong> VoiceOver (Réglages, Accessibilité, VoiceOver).
          </li>
          <li>
            <strong>Ordinateur Windows :</strong> NVDA, gratuit, ou Narrateur, intégré à Windows.
          </li>
        </ul>
        <p>Pour aller vite :</p>
        <ul>
          <li>le premier lien de chaque page, « Aller au contenu », passe directement l&apos;en-tête et le menu ;</li>
          <li>chaque page a un titre principal, et chaque partie son propre titre : naviguez de titre en titre ;</li>
          <li>le menu principal est annoncé « Navigation principale ».</li>
        </ul>
      </section>

      <section>
        <h2>3. Écouter la page</h2>
        <p>
          Le bouton <strong>« Écouter la page »</strong>, en haut de chaque page (icône de haut-parleur sur téléphone), lit
          le contenu à voix haute avec la voix de votre appareil. Il est utile si vous voyez mal ou si vous lisez
          difficilement le français. Le passage lu est surligné, et une barre permet de mettre en pause, de passer au
          passage suivant ou précédent, et de lire plus lentement ou plus vite.
        </p>
        <p>
          La voix est celle de votre téléphone ou de votre ordinateur : aucun son n&apos;est envoyé par Internet. Si la
          lecture est en anglais, installez une voix française dans les réglages de synthèse vocale de l&apos;appareil. Les
          langues nationales (mooré, dioula, fulfuldé) ne sont pas encore proposées par ces voix.
        </p>
      </section>

      <section>
        <h2>4. Ce qui est adapté</h2>
        <ul>
          <li>
            <strong>Scores :</strong> lus en toutes lettres, par exemple « 2 à 1, en direct, 66e minute ». Pendant un match,
            chaque but est annoncé automatiquement.
          </li>
          <li>
            <strong>Classements :</strong> de vrais tableaux, avec des colonnes nommées en entier (matchs joués, victoires,
            points…). La forme récente est dite en mots (« victoire, nul, défaite »), et les places qualificatives sont
            signalées.
          </li>
          <li>
            <strong>Phases finales :</strong> les matchs sont lus dans l&apos;ordre de la compétition, des quarts à la finale.
          </li>
          <li>
            <strong>Billetterie :</strong> formulaire entièrement étiqueté. Le lien de vos billets vous est envoyé par SMS ;
            chaque billet porte son numéro écrit en clair sous le QR code.
          </li>
          <li>
            <strong>Votes :</strong> choix, numéro de téléphone et code de confirmation sont étiquetés et annoncés.
          </li>
          <li>
            <strong>Lecture :</strong> contrastes renforcés, zoom du navigateur possible, mode sombre, et animations réduites
            si votre appareil le demande.
          </li>
        </ul>
      </section>

      <section>
        <h2>5. Au stade</h2>
        <p>
          À l&apos;entrée, présentez votre billet sur votre téléphone, ou imprimé : le contrôleur le scanne pour vous.
          [Le personnel d&apos;accueil peut vous accompagner jusqu&apos;à votre place : signalez-vous au contrôle.]
        </p>
      </section>

      <section>
        <h2>6. Limites connues</h2>
        <ul>
          <li>
            L&apos;espace des officiels (feuilles de match, contrôle des entrées) s&apos;utilise au clavier, mais n&apos;a pas
            encore été testé avec un lecteur d&apos;écran.
          </li>
          <li>
            Les blasons des équipes sont décoratifs : le nom de l&apos;équipe est toujours écrit à côté.
          </li>
          <li>
            Sur téléphone, certaines colonnes du classement (buts pour, buts contre, forme) ne s&apos;affichent qu&apos;en
            tournant l&apos;écran ou sur ordinateur.
          </li>
        </ul>
      </section>

      <section>
        <h2>7. Signaler une difficulté</h2>
        <p>
          Une page vous pose problème ? Dites-le nous : [adresse électronique] · [téléphone ou WhatsApp]. Précisez la page,
          votre appareil et votre lecteur d&apos;écran si possible. Nous répondons sous [7 jours] et vous donnons
          l&apos;information demandée par un autre moyen en attendant la correction.
        </p>
        <p>
          Voir aussi les{" "}
          <Link href="/mentions-legales" className={link}>
            mentions légales
          </Link>
          .
        </p>
      </section>
    </LegalPage>
  );
}
