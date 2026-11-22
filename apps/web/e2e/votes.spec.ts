// Votes du public : création et ouverture d'un scrutin par l'administration, vote d'un
// visiteur avec code SMS (lu dans le simulateur), résultats et procès-verbal.
import { expect, test } from "@playwright/test";

test.use({ viewport: { width: 1280, height: 900 }, isMobile: false, hasTouch: false });

const SMS_SIMULATOR = process.env.SMS_SIMULATOR_URL ?? "http://localhost:8090";
const local = (d: Date) => d.toISOString().slice(0, 16); // Ouagadougou = UTC

test("scrutin créé par l'administration, vote par SMS, résultats et procès-verbal", async ({ page, request }) => {
  const stamp = Date.now().toString().slice(-6);
  const title = `Joueur du mois E2E ${stamp}`;

  // 1. Création du scrutin
  await page.goto("/connexion");
  await page.getByLabel("Adresse e-mail").fill("admin@lds.local");
  await page.getByLabel("Mot de passe").fill("Lds2027-demo");
  await page.getByRole("button", { name: "Se connecter" }).click();
  await page.getByRole("navigation", { name: "Espace officiels" }).getByRole("link", { name: "Votes" }).click();
  await page.getByRole("link", { name: "+ Nouveau scrutin" }).click();
  await page.getByLabel("Type de scrutin *").selectOption("player_of_the_season");
  await page.getByLabel("Titre *").fill(title);
  await page.getByLabel("Ouverture du vote *").fill(local(new Date(Date.now() - 3600_000)));
  await page.getByLabel("Clôture du vote *").fill(local(new Date(Date.now() + 2 * 86400_000)));
  await page.getByLabel("Équipe").selectOption({ label: "GulmuSport" });
  await page.getByRole("button", { name: /Suggérer/ }).click();
  const suggestions = page.getByRole("list", { name: "Propositions suggérées" }).getByRole("checkbox");
  for (const i of [0, 1, 2]) await suggestions.nth(i).check();
  await page.getByRole("button", { name: "Enregistrer le brouillon" }).click();
  await expect(page.getByRole("heading", { name: title })).toBeVisible();

  page.on("dialog", (d) => d.accept());
  await page.getByRole("button", { name: "Ouvrir le scrutin" }).click();
  await expect(page.getByText("Scrutin ouvert au public")).toBeVisible();
  const ballotUrl = page.url().replace("/admin/votes/", "/votes/");

  // 2. Vote d'un visiteur (sans compte)
  const visitor = await page.context().browser()!.newPage();
  await visitor.goto(ballotUrl);
  await expect(visitor.getByRole("heading", { name: title })).toBeVisible();
  const firstOption = visitor.getByRole("region", { name: "Voter" }).getByRole("radio").first();
  await firstOption.check();
  const phone = `+22671${stamp}`;
  await visitor.getByLabel("2. Votre numéro de téléphone").fill(phone);
  await visitor.getByRole("button", { name: "Recevoir mon code" }).click();
  await expect(visitor.getByText(/Code reçu par SMS au/)).toBeVisible();

  const inbox = await (await request.get(`${SMS_SIMULATOR}/sms/messages?to=${encodeURIComponent(phone)}`)).json();
  const code = /(\d{6})/.exec(inbox[0].message)![1];
  await visitor.getByLabel(/3\. Code reçu par SMS/).fill(code);
  await visitor.getByRole("button", { name: "Valider mon vote" }).click();
  await expect(visitor.getByText("Merci, votre vote est enregistré !")).toBeVisible();
  await expect(visitor.getByText("1 votant(s).")).toBeVisible();

  // Le même numéro ne peut pas revoter
  await visitor.reload();
  await visitor.getByRole("region", { name: "Voter" }).getByRole("radio").nth(1).check();
  await visitor.getByLabel("2. Votre numéro de téléphone").fill(phone);
  await visitor.getByRole("button", { name: "Recevoir mon code" }).click();
  await expect(visitor.getByText("Ce numéro a déjà voté pour ce scrutin")).toBeVisible();

  // 3. Résultats et procès-verbal côté administration
  await page.reload();
  await expect(page.getByText("(1 votant(s) comptés)")).toBeVisible();
  await page.getByRole("link", { name: "Procès-verbal" }).click();
  await expect(page.getByRole("heading", { name: "Procès-verbal du vote du public" })).toBeVisible();
  await expect(page.getByText(/^[0-9a-f]{64}$/)).toBeVisible();
});
