// Chapitres des tutoriels : un parcours réel par public, sous-titres courts à l'écran et
// texte complet de la voix off. Les données sont celles de la démonstration (fictives).
import fs from "node:fs";
import { apiToken, API, BASE, login, SMS } from "./lib.mjs";

const SHARED = "/tmp/lds-tutoriels-partage.json";
const share = (o) => fs.writeFileSync(SHARED, JSON.stringify({ ...read(), ...o }));
const read = () => (fs.existsSync(SHARED) ? JSON.parse(fs.readFileSync(SHARED, "utf8")) : {});

export const CHAPITRES = [
  {
    id: "01-site-public",
    titre: "Suivre la compétition",
    public: "Supporters · sur téléphone",
    mobile: true,
    async run(t) {
      const p = t.page;
      await p.goto(BASE);
      await t.say("Le site public, sur téléphone", "Bienvenue sur LDS Connect, la plateforme de la Ligue de la Souveraineté. Sur le téléphone d'un supporter, l'accueil présente le prochain match, avec le compte à rebours jusqu'au coup d'envoi.");
      await t.scroll(560);
      await t.say("Les scores en direct", "Les matchs en cours s'affichent en direct : le score et la minute se mettent à jour sans recharger la page.");
      await t.scroll(700);
      await t.say("Résultats et classements", "Plus bas, les derniers résultats et le classement des deux poules, calculés automatiquement dès qu'une feuille de match est validée.");
      await t.scroll(1300, 1200);
      const race = p.getByRole("region", { name: "La course aux trophées" });
      await race.evaluate((el) => el.scrollIntoView({ block: "start", behavior: "smooth" }));
      await t.pause(900);
      await t.say("La course aux cinq trophées", "La course aux cinq trophées de la Ligue se suit en direct : vainqueur, meilleur buteur, meilleur gardien, homme du match et meilleur joueur, à partir des feuilles de match validées et des votes du public.");
      await t.scroll(700, 1200);
      await t.scroll(800, 1200);
      await t.say("Les 20 équipes", "Le mur des blasons réunit les vingt équipes. Un appui ouvre la page du club.");
      const wall = p.getByRole("region", { name: "Les équipes" });
      await wall.scrollIntoViewIfNeeded();
      await t.pause(600);
      await t.tap(wall.getByRole("link").nth(18));
      await p.waitForLoadState("networkidle");
      await t.say("La page d'un club", "La page d'un club donne son effectif, ses matchs et ses résultats. Pour les joueurs, seuls le nom d'usage, le poste et l'âge sont publics : la compétition compte des mineurs.");
      await t.scroll(650);
      await t.pause(800);
      await t.tap(p.getByRole("navigation").getByRole("link", { name: "Classement" }).last());
      await p.waitForLoadState("networkidle");
      await t.say("Le classement détaillé", "L'onglet Classement donne le tableau complet : matchs joués, victoires, nuls, défaites, différence de buts et points. Les quatre premiers de chaque poule se qualifient.");
      await t.scroll(500);
      await t.tap(p.getByRole("navigation").getByRole("link", { name: "Matchs" }).last());
      await p.waitForLoadState("networkidle");
      await t.say("Le calendrier", "Le calendrier liste toutes les journées, avec le stade et l'heure de chaque rencontre.");
      await t.scroll(500);
    },
  },
  {
    id: "02-billet",
    titre: "Acheter un billet",
    public: "Supporters · sur téléphone",
    mobile: true,
    async run(t) {
      const p = t.page;
      await p.goto(`${BASE}/billetterie`);
      await t.say("La billetterie", "Pour acheter un billet, pas besoin de créer de compte. La billetterie liste les matchs en vente.");
      const link = p.locator('a[href^="/billetterie/"]').first();
      const matchId = (await link.getAttribute("href")).split("/").pop();
      await t.tap(link);
      await p.waitForLoadState("networkidle");
      await t.say("Choisir ses places", "On choisit la catégorie de places et le nombre de billets. Le total s'affiche aussitôt.");
      await t.tap(p.getByRole("button", { name: "Un billet de plus" }));
      await t.pause(500);
      await t.say("Nom et numéro mobile money", "On indique son nom et son numéro mobile money. Les places sont réservées quinze minutes, le temps de payer.");
      await t.type(p.getByLabel("Nom et prénom"), "Awa Ouédraogo");
      const n = String(Date.now()).slice(-6);
      await t.type(p.getByLabel("Numéro mobile money"), `76 ${n.slice(0, 2)} ${n.slice(2, 4)} ${n.slice(4)}`);
      await t.tap(p.getByRole("checkbox", { name: /conditions générales de vente/ }));
      await t.say("Paiement mobile money", "Après avoir accepté les conditions de vente, on paie par mobile money, sur la page de l'opérateur. Ici, un simulateur : aucun argent réel.");
      await t.tap(p.getByRole("button", { name: "Payer par mobile money" }));
      await p.getByText("SIMULATEUR").waitFor();
      await t.pause(900);
      await t.tap(p.getByRole("button", { name: "Confirmer le paiement" }));
      await p.getByText(/C'est payé/).waitFor({ timeout: 30_000 });
      await t.say("Les billets, avec leur QR code", "Le paiement confirmé, les billets s'affichent avec leur QR code. Le lien est aussi envoyé par SMS, et les billets restent sur le téléphone, même sans réseau.");
      await t.scroll(500, 1200);
      await t.scroll(500, 1200);
      const u = new URL(p.url());
      share({ matchId, order: u.pathname.split("/").pop(), key: u.searchParams.get("k") });
      await t.tap(p.getByRole("link", { name: /Mes billets/ }).first());
      await p.waitForLoadState("networkidle");
      await t.say("Mes billets", "La rubrique Mes billets retrouve toutes les commandes faites sur cet appareil. À l'entrée du stade, il suffit de présenter le QR code.");
    },
  },
  {
    id: "03-vote",
    titre: "Voter pour son joueur",
    public: "Supporters · sur téléphone",
    mobile: true,
    async run(t) {
      const p = t.page;
      await p.goto(`${BASE}/votes`);
      await t.say("Les votes du public", "Les supporters élisent l'homme du match, le but du mois ou le joueur de la saison. Les scrutins ouverts sont listés ici.");
      await t.tap(p.locator('a[href^="/votes/"]').first());
      await p.waitForLoadState("networkidle");
      await t.say("Choisir", "On choisit son candidat.");
      await t.tap(p.getByRole("region", { name: "Voter" }).getByRole("radio").first());
      const phone = `+22670${String(Date.now()).slice(-6)}`;
      await t.say("Un vote par numéro, confirmé par SMS", "Pour garantir un vote par personne, on saisit son numéro de téléphone et on reçoit un code par SMS. Le numéro est chiffré et ne sert qu'à ce contrôle.");
      await t.type(p.getByLabel("2. Votre numéro de téléphone"), phone);
      await t.tap(p.getByRole("button", { name: "Recevoir mon code" }));
      await p.getByText(/Code reçu par SMS au/).waitFor();
      const inbox = await (await fetch(`${SMS}/sms/messages?to=${encodeURIComponent(phone)}`)).json();
      const code = /(\d{6})/.exec(inbox[0].message)[1];
      await t.say("Saisir le code reçu", "On saisit le code reçu, puis on valide.");
      await t.type(p.getByLabel(/3\. Code reçu par SMS/), code);
      await t.tap(p.getByRole("button", { name: "Valider mon vote" }));
      await p.getByText("Merci, votre vote est enregistré !").waitFor();
      await t.say("Vote enregistré", "Le vote est enregistré. Selon le scrutin, les résultats s'affichent en direct ou à la date annoncée par la Ligue. Les votes en masse sont détectés et mis de côté pour examen.");
      await t.scroll(400);
    },
  },
  {
    id: "04-club",
    titre: "Gérer son effectif",
    public: "Clubs · sur ordinateur",
    mobile: false,
    async run(t) {
      const p = t.page;
      await p.goto(`${BASE}/connexion`);
      await t.say("L'espace des clubs", "Chaque club dispose d'un accès à l'espace officiels. Le gestionnaire se connecte avec le compte créé par la Ligue.");
      await login(t, "club.vinnim@lds.local");
      await p.waitForLoadState("networkidle");
      await t.say("Son équipe, et seulement elle", "Il arrive directement sur son équipe : le gestionnaire ne voit et ne modifie que son propre effectif.");
      await t.say("La conformité en un coup d'œil", "Le tableau contrôle en continu les règles de la saison : nombre de joueurs et d'encadreurs, âge minimum, quota de moins de dix-neuf ans et joueurs locaux.");
      await t.scroll(450, 1200);
      const row = p.getByRole("row").filter({ has: p.getByRole("button", { name: "Licence" }) }).filter({ hasText: /LDS27-/ }).first();
      await row.scrollIntoViewIfNeeded();
      await t.say("La licence numérique", "Chaque joueur a sa licence numérique, avec un QR code signé que l'on peut vérifier au stade, même sans réseau.");
      await t.tap(row.getByRole("button", { name: "Licence" }));
      const dialog = p.getByRole("dialog", { name: "Licence" });
      await dialog.getByAltText(/QR code de la licence/).waitFor();
      await t.pause(900);
      await t.say("Ajouter la photo d'identité", "Le club ajoute la photo d'identité du joueur, recadrée automatiquement. Elle figure sur la carte imprimée et sur l'écran du contrôleur, jamais sur le site public. Pour un mineur, l'autorisation parentale est exigée.");
      const photo = await silhouette(t);
      await dialog.getByLabel("Photo d'identité").setInputFiles(photo);
      await dialog.getByText("Photo enregistrée").waitFor();
      await t.pause(1200);
      await t.tap(dialog.getByRole("button", { name: "Fermer" }));
      await t.say("Inscrire un nouveau joueur", "Pour inscrire un joueur, on remplit sa fiche. La pièce d'identité et le téléphone sont chiffrés, et chaque consultation est enregistrée.");
      await t.scroll(-2000, 800);
      await t.tap(p.getByRole("button", { name: "+ Joueur" }));
      const form = p.getByRole("dialog", { name: "Nouveau joueur" });
      await t.type(form.getByLabel("Prénom(s) *"), "Issa");
      await t.type(form.getByLabel("Nom *", { exact: true }), "Démonstration");
      await form.getByLabel("Date de naissance *").fill("2005-06-12");
      await t.pause(600);
      await form.getByLabel("Poste *").selectOption("MF");
      await t.pause(1500);
      await t.tap(form.getByRole("button", { name: "Annuler" }));
    },
  },
  {
    id: "05-delegue",
    titre: "La feuille de match",
    public: "Délégués · sur téléphone",
    mobile: true,
    async run(t) {
      const p = t.page;
      await p.goto(`${BASE}/connexion`);
      await t.say("Le délégué du match", "Le délégué tient la feuille de match sur son téléphone, au bord du terrain.");
      await login(t, "delegue@lds.local");
      await p.getByRole("heading", { name: "Mes matchs" }).waitFor();
      await t.tap(p.getByLabel("Toute la saison"));
      await t.say("Ses matchs attribués", "Il retrouve les matchs que la Ligue lui a attribués.");
      const match = p.getByRole("link").filter({ hasText: "Feuille non ouverte" }).first();
      await t.tap(match);
      await p.getByLabel("Score").waitFor();
      const tabs = p.getByRole("navigation", { name: "Sections de la feuille" }).getByRole("button");
      await t.say("Les compositions, contrôlées", "Les compositions des deux équipes sont saisies et contrôlées automatiquement : joueurs licenciés et non suspendus, nombre de titulaires, et au moins la moitié de joueurs locaux.");
      for (const i of [0, 1]) {
        await t.tap(tabs.nth(i));
        await t.tap(p.getByRole("button", { name: "Proposer une composition conforme" }));
        await t.pause(900);
        await t.tap(p.getByRole("button", { name: "Enregistrer la composition" }));
        await p.getByText("✓ Composition conforme").waitFor();
        await t.pause(700);
      }
      await t.say("Coup d'envoi", "Au coup d'envoi, le délégué soumet la feuille : les compositions sont verrouillées.");
      await t.tap(p.getByRole("button", { name: /Soumettre la feuille/ }));
      await p.getByText("Soumise — match en cours").first().waitFor();
      await t.tap(tabs.filter({ hasText: "Match" }));
      const form = p.getByRole("form", { name: "Nouvel événement" });
      const event = async (type, minute) => {
        await form.getByLabel("Type").selectOption({ label: type });
        await t.type(form.getByLabel("Minute"), minute);
        await form.getByLabel("Joueur", { exact: true }).selectOption({ index: 1 });
        await t.tap(form.getByRole("button", { name: "Ajouter l'événement" }));
      };
      await t.say("Buts et cartons, minute par minute", "Pendant le match, il saisit les buts, les cartons et les remplacements. Le score est diffusé en direct sur le site public.");
      await event("But", "23");
      await t.pause(900);
      await t.say("Même sans réseau", "Sans réseau, rien n'est perdu : les saisies restent sur le téléphone et partent dès que la connexion revient.");
      await t.ctx.setOffline(true);
      await p.getByText("Hors connexion").first().waitFor();
      await event("Carton jaune", "41");
      await p.getByText(/action\(s\) en attente/).waitFor();
      await t.pause(1500);
      await t.ctx.setOffline(false);
      await p.getByText(/action\(s\) en attente/).waitFor({ state: "hidden", timeout: 30_000 });
      await t.say("Validation : le résultat devient officiel", "À la fin du match, le délégué valide la feuille. Le résultat devient officiel : classements, suspensions et statistiques des joueurs sont mis à jour automatiquement.");
      await t.tap(p.getByRole("button", { name: /valider la feuille/ }));
      await p.getByText(/Feuille validée/).waitFor();
      await t.pause(1200);
    },
  },
  {
    id: "06-controle",
    titre: "Le contrôle au stade",
    public: "Contrôleurs · sur téléphone",
    mobile: true,
    async run(t) {
      const p = t.page;
      const s = read();
      const order = await (await fetch(`${API}/api/v1/tickets/orders/${s.order}?k=${s.key}`)).json();
      const ticket = order.tickets[0].token;
      const licence = await licenceAvecPhoto();
      await p.goto(`${BASE}/connexion`);
      await t.say("Le contrôle des entrées", "Le contrôleur d'accès utilise son téléphone pour vérifier billets, accréditations et licences.");
      await login(t, "controle@lds.local");
      await p.getByRole("heading", { name: "Contrôle des entrées" }).waitFor();
      await t.say("Préparer l'appareil avant le match", "Avant l'ouverture des portes, il choisit le match, le nom de sa porte et la zone qu'il garde, puis prépare l'appareil : la vérification fonctionnera ensuite sans réseau.");
      await p.getByLabel("Match").selectOption(s.matchId);
      await t.pause(600);
      await t.type(p.getByLabel("Porte / appareil"), "Porte Nord");
      await t.tap(p.getByRole("button", { name: "Préparer l'appareil" }));
      await p.getByText(/Prêt hors ligne/).waitFor();
      await t.say("Scanner le QR code", "Il scanne le QR code du billet avec la caméra. Pour la démonstration, le contenu du code est collé directement.");
      const qr = p.getByLabel("Contenu du QR code");
      await qr.fill(ticket);
      await t.tap(p.getByRole("button", { name: "Vérifier" }));
      await p.getByRole("alert", { name: "Résultat du contrôle" }).waitFor();
      await t.say("Entrée autorisée", "Le billet est authentique : entrée autorisée.");
      await t.pause(600);
      await qr.fill(ticket);
      await t.tap(p.getByRole("button", { name: "Vérifier" }));
      await t.say("Un billet ne sert qu'une fois", "Présenté une seconde fois, le même billet est refusé : la double entrée est détectée, y compris entre deux portes après synchronisation.");
      await t.tap(p.getByRole("navigation", { name: "Espace officiels" }).getByRole("link", { name: "Licences" }));
      await p.getByRole("heading", { name: "Contrôle des licences" }).waitFor();
      await t.say("Vérifier la licence d'un joueur", "Pour les joueurs, le contrôleur vérifie la licence : la signature numérique est contrôlée sur l'appareil, et la photo s'affiche pour comparer avec la personne présente.");
      await p.getByLabel(/coller le contenu du QR code/).fill(licence);
      await t.tap(p.getByRole("button", { name: "Vérifier" }));
      await p.getByRole("alert").filter({ hasText: /Licence|valide/ }).first().waitFor();
      await t.say("Nom, équipe, validité", "Le contrôleur voit le nom, l'équipe, le numéro et la période de validité. Ici, la saison n'a pas encore commencé : l'écran signale que la licence ne sera valable qu'à partir du premier janvier.");
      await t.pause(1200);
    },
  },
  {
    id: "07-administration",
    titre: "Piloter la compétition",
    public: "Administration de la Ligue · sur ordinateur",
    mobile: false,
    async run(t) {
      const p = t.page;
      const nav = () => p.getByRole("navigation", { name: "Espace officiels" });
      await p.goto(`${BASE}/connexion`);
      await t.say("L'administration de la Ligue", "L'administration de la Ligue pilote toute la compétition depuis l'espace officiels.");
      await login(t, "admin@lds.local");
      await p.getByRole("heading", { name: "Tableau de bord" }).waitFor();
      await t.say("Le tableau de bord", "Le tableau de bord rassemble l'essentiel : avancement de la saison, points à traiter, licences, billets vendus, votes, et les prochains matchs.");
      await t.scroll(500, 1500);
      await t.tap(nav().getByRole("link", { name: "Registre" }));
      await p.getByRole("heading", { name: "Registre des équipes" }).waitFor();
      await t.say("Le registre des vingt équipes", "Le registre montre la conformité des vingt équipes : effectifs, jeunes, locaux et licences.");
      await t.scroll(400, 1200);
      await t.tap(nav().getByRole("link", { name: "Calendrier" }));
      await p.getByRole("heading", { name: "Calendrier" }).waitFor();
      await t.say("Le calendrier", "Le calendrier est généré automatiquement. Stades, horaires et délégués s'attribuent match par match.");
      await t.scroll(400, 1200);
      await t.tap(nav().getByRole("link", { name: "Saison et règles" }));
      await p.getByRole("heading", { name: "Saison et règles" }).waitFor();
      await t.say("Les règles de la saison", "Toutes les règles sportives se règlent ici : barème, effectifs, discipline, dotations. Chaque modification est motivée et journalisée, et les règles qui changent le classement sont figées dès le premier match.");
      await t.scroll(600, 1500);
      await t.tap(nav().getByRole("link", { name: "Billetterie" }));
      await p.waitForLoadState("networkidle");
      const select = p.getByLabel("Match", { exact: true });
      const first = await select.locator("option").nth(1).getAttribute("value");
      await select.selectOption(first);
      await p.waitForLoadState("networkidle");
      await t.say("Billetterie et remboursements", "La billetterie se configure par match : catégories, prix, nombre de places. Les ventes se suivent en temps réel, et les remboursements sont consignés.");
      await t.scroll(500, 1200);
      await t.tap(nav().getByRole("link", { name: "Votes" }));
      await p.waitForLoadState("networkidle");
      await t.say("Les scrutins du public", "Les scrutins se créent en quelques clics, avec résultats en direct ou à date fixée, et un procès-verbal imprimable.");
      await t.tap(nav().getByRole("link", { name: "Journal" }));
      await p.waitForLoadState("networkidle");
      await t.say("Tout est tracé", "Enfin, le journal d'audit trace chaque action sensible : licences, feuilles de match, résultats, votes et accès aux données personnelles. Il ne peut pas être modifié.");
      await t.scroll(400, 1500);
    },
  },
];

/** Image de démonstration pour la photo de licence : silhouette dessinée, aucune vraie personne. */
async function silhouette(t) {
  const data = await t.page.evaluate(() => {
    const c = document.createElement("canvas");
    c.width = 600;
    c.height = 800;
    const g = c.getContext("2d");
    const grd = g.createLinearGradient(0, 0, 0, 800);
    grd.addColorStop(0, "#e2e8ef");
    grd.addColorStop(1, "#b9c7d6");
    g.fillStyle = grd;
    g.fillRect(0, 0, 600, 800);
    g.fillStyle = "#4b5563";
    g.beginPath();
    g.arc(300, 300, 130, 0, Math.PI * 2);
    g.fill();
    g.beginPath();
    g.ellipse(300, 760, 250, 260, 0, Math.PI, 0);
    g.fill();
    return c.toDataURL("image/png").split(",")[1];
  });
  return { name: "photo.png", mimeType: "image/png", buffer: Buffer.from(data, "base64") };
}

/** Jeton d'une licence dont le titulaire a une photo (préparé au chapitre du club). */
async function licenceAvecPhoto() {
  const token = await apiToken("admin@lds.local");
  const h = { Authorization: `Bearer ${token}` };
  const teams = await (await fetch(`${API}/api/v1/admin/teams/overview`, { headers: h })).json();
  const vinnim = teams.find((x) => x.team.short_name === "Vinnim") ?? teams[0];
  const squad = await (await fetch(`${API}/api/v1/admin/teams/${vinnim.team.id}/squad`, { headers: h })).json();
  const withPhoto = squad.members.find((m) => m.has_photo && m.licence?.status === "active") ?? squad.members.find((m) => m.licence);
  const lics = await (await fetch(`${API}/api/v1/admin/teams/${vinnim.team.id}/licences`, { headers: h })).json();
  return lics.find((l) => l.number === withPhoto.licence.number).token;
}
