// Comptes : création d'un délégué, attribution d'un match, première connexion et
// changement de mot de passe par l'intéressé.
import { expect, type Page, test } from "@playwright/test";

test.use({ viewport: { width: 1280, height: 900 }, isMobile: false, hasTouch: false });

async function login(page: Page, email: string, password: string) {
  await page.goto("/connexion");
  await page.getByLabel("Adresse e-mail").fill(email);
  await page.getByLabel("Mot de passe").fill(password);
  await page.getByRole("button", { name: "Se connecter" }).click();
}

test("création d'un délégué, attribution d'un match et changement de mot de passe", async ({ page }) => {
  const stamp = Date.now().toString().slice(-6);
  const email = `delegue.${stamp}@exemple.bf`;
  const name = `Délégué E2E ${stamp}`;

  // 1. Le super administrateur crée le compte
  await login(page, "superadmin@lds.local", "Lds2027-demo");
  await page.getByRole("navigation", { name: "Espace officiels" }).getByRole("link", { name: "Comptes" }).click();
  await page.getByRole("button", { name: "+ Nouveau compte" }).click();
  const form = page.getByRole("dialog", { name: "Nouveau compte" });
  await form.getByLabel("Adresse e-mail *").fill(email);
  await form.getByLabel("Nom complet *").fill(name);
  await form.getByLabel("Rôle *").selectOption("delegue_match");
  await form.getByRole("button", { name: "Créer le compte" }).click();
  const creds = page.getByRole("dialog", { name: "Mot de passe provisoire" });
  const temporary = (await creds.getByLabel("Mot de passe provisoire").textContent())!.trim();
  expect(temporary).toMatch(/^[\w]{4}(-[\w]{4}){3}$/);
  await creds.getByRole("button", { name: "J'ai transmis le mot de passe" }).click();
  await expect(page.getByRole("row").filter({ hasText: email })).toBeVisible();

  // 2. Attribution d'un match encore à jouer
  await page.getByRole("navigation", { name: "Espace officiels" }).getByRole("link", { name: "Calendrier" }).click();
  const select = page.locator(`select[aria-label^="Délégué"]:enabled`).first();
  const fixture = (await select.getAttribute("aria-label"))!.replace("Délégué ", "");
  await select.selectOption({ label: name });
  await expect(page.getByText(`${fixture} : délégué ${name}`)).toBeVisible();

  // 3. Première connexion du délégué, changement de mot de passe
  await page.getByRole("button", { name: "Déconnexion" }).click();
  // Mot de passe provisoire : arrivée directe sur « Mon compte », le reste est bloqué
  await login(page, email, temporary);
  await expect(page.getByRole("heading", { name: "Mon compte" })).toBeVisible();
  await expect(page.getByText(/Votre mot de passe est provisoire/)).toBeVisible();
  await page.goto("/delegue");
  await expect(page.getByRole("link", { name: "Choisissez votre mot de passe" })).toBeVisible();
  await page.getByRole("link", { name: "Choisissez votre mot de passe" }).click();
  const newPassword = `Une-phrase-solide-${stamp}`;
  await page.getByLabel("Mot de passe provisoire reçu").fill(temporary);
  await page.getByLabel("Nouveau mot de passe", { exact: true }).fill(newPassword);
  await page.getByLabel("Confirmer le nouveau mot de passe").fill(newPassword);
  await page.getByRole("button", { name: "Changer le mot de passe" }).click();
  await expect(page.getByText("Mot de passe modifié")).toBeVisible();
  await page.getByRole("button", { name: "Se reconnecter" }).click();

  // L'ancien mot de passe ne fonctionne plus, le nouveau oui ; le match attribué est listé
  await login(page, email, temporary);
  await expect(page.getByText("Adresse e-mail ou mot de passe incorrect")).toBeVisible();
  await login(page, email, newPassword);
  await page.getByLabel("Toute la saison").check();
  const [home, away] = fixture.split(" – ");
  await expect(page.getByRole("link").filter({ hasText: home }).filter({ hasText: away })).toBeVisible();
});
