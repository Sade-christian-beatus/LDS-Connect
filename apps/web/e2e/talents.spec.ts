// Talents : la cellule technique filtre les joueurs, suit un joueur et note une observation ;
// le public consulte la fiche d'un joueur (données autorisées seulement).
import { expect, test } from "@playwright/test";

test.use({ viewport: { width: 1280, height: 900 }, isMobile: false, hasTouch: false });

test("tableau de bord, suivi et observation d'un joueur ; fiche publique", async ({ page, browser }) => {
  const stamp = Date.now().toString().slice(-6);

  await page.goto("/connexion");
  await page.getByLabel("Adresse e-mail").fill("technique@lds.local");
  await page.getByLabel("Mot de passe").fill("Lds2027-demo");
  await page.getByRole("button", { name: "Se connecter" }).click();
  await expect(page.getByRole("heading", { name: "Talents" })).toBeVisible();

  // Recherche prête : gardiens, triés par clean sheets
  await page.getByRole("button", { name: "Gardiens" }).click();
  await expect(page.getByLabel("Trier par")).toHaveValue("clean_sheets");
  const rows = page.getByRole("row");
  await expect(rows.nth(1)).toContainText("Gardien");

  // Filtre d'âge
  await page.getByRole("button", { name: "Réinitialiser" }).click();
  await page.getByLabel("Âge max.").fill("18");
  await expect(page.getByText(/joueur\(s\) · classés par/)).toBeVisible();
  await expect(rows.nth(1).getByText("jeune")).toBeVisible();

  // Fiche du premier joueur : suivi, étiquette, observation notée
  const first = rows.nth(1).getByRole("link");
  const name = (await first.locator("span.font-semibold").innerText()).replace("★", "").trim();
  await first.click();
  await expect(page.getByRole("heading", { name })).toBeVisible();
  if (await page.getByRole("button", { name: "★ Suivi" }).isVisible()) {
    await page.getByRole("button", { name: "★ Suivi" }).click();
    await expect(page.getByRole("button", { name: "☆ Suivre ce joueur" })).toBeVisible();
  }
  await page.getByRole("button", { name: "☆ Suivre ce joueur" }).click();
  await expect(page.getByRole("button", { name: "★ Suivi" })).toBeVisible();
  await page.getByRole("group", { name: "Étiquettes de suivi" }).getByRole("button", { name: "Potentiel sélection" }).click();
  await expect(page.getByRole("button", { name: "Potentiel sélection", pressed: true })).toBeVisible();

  const text = `Bon placement, à revoir en match (${stamp}).`;
  await page.getByLabel("Nouvelle observation").fill(text);
  await page.getByRole("radio", { name: "4 sur 5" }).click();
  await page.getByRole("button", { name: "Enregistrer" }).click();
  await expect(page.getByText(text)).toBeVisible();

  // Le joueur apparaît dans « Joueurs suivis »
  await page.getByRole("link", { name: "← Tous les talents" }).click();
  await page.getByRole("button", { name: "Joueurs suivis" }).click();
  await expect(page.getByRole("link", { name: new RegExp(name) })).toBeVisible();

  // Fiche publique : depuis la page d'une équipe, sans nom complet
  const visitor = await (await browser.newContext()).newPage();
  await visitor.goto("/equipes/gulmusport");
  const player = visitor.getByRole("link", { name: /\. / }).first();
  const display = await player.innerText();
  await player.click();
  await expect(visitor.getByRole("heading", { name: display })).toBeVisible();
  await expect(visitor.getByRole("heading", { name: "Match par match" })).toBeVisible();
  await expect(visitor.getByText("Minutes", { exact: true })).toBeVisible();
});
