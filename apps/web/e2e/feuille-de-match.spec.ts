// Parcours délégué : composition conforme (règle des locaux) → soumission → événements
// (dont un saisi hors connexion puis synchronisé) → validation → classement public.
import { expect, test } from "@playwright/test";

const DELEGATE = { email: "delegue@lds.local", password: "Lds2027-demo" };

test("le délégué saisit et valide une feuille de match, y compris hors connexion", async ({ page, context }) => {
  page.on("dialog", (d) => d.accept());

  // Connexion
  await page.goto("/connexion");
  await page.getByLabel("Adresse e-mail").fill(DELEGATE.email);
  await page.getByLabel("Mot de passe").fill(DELEGATE.password);
  await page.getByRole("button", { name: "Se connecter" }).click();
  await expect(page.getByRole("heading", { name: "Mes matchs" })).toBeVisible();

  // Premier match dont la feuille n'a pas encore été ouverte
  await page.getByLabel("Toute la saison").check();
  const match = page.getByRole("link").filter({ hasText: "Feuille non ouverte" }).first();
  await expect(match).toBeVisible();
  await match.click();
  await expect(page.getByText("Brouillon")).toBeVisible();

  // Compositions des deux équipes (proposition automatique conforme)
  const tabs = page.getByRole("navigation", { name: "Sections de la feuille" }).getByRole("button");
  for (const index of [0, 1]) {
    await tabs.nth(index).click();
    await page.getByRole("button", { name: "Proposer une composition conforme" }).click();
    await expect(page.getByText(/Titulaires : 11\/11/)).toBeVisible();
    await expect(page.getByText(/Locaux titulaires : \d+ \(min\. 6\)/)).toBeVisible();
    await page.getByRole("button", { name: "Enregistrer la composition" }).click();
    await expect(page.getByText("✓ Composition conforme")).toBeVisible();
  }

  // Soumission : compositions verrouillées, saisie des événements ouverte
  await page.getByRole("button", { name: /Soumettre la feuille/ }).click();
  await expect(page.getByText("Soumise — match en cours").first()).toBeVisible();
  await expect(page.getByText(/action\(s\) en attente/)).toBeHidden();
  await tabs.filter({ hasText: "Match" }).click();

  const form = page.getByRole("form", { name: "Nouvel événement" });
  const addEvent = async (type: string, minute: string) => {
    await form.getByLabel("Type").selectOption({ label: type });
    await form.getByLabel("Minute").fill(minute);
    await form.getByLabel("Joueur", { exact: true }).selectOption({ index: 1 });
    await form.getByRole("button", { name: "Ajouter l'événement" }).click();
  };

  await addEvent("But", "12");
  await expect(page.getByLabel("Score")).toHaveText("1 – 0");

  // Hors connexion : l'action est mise en file d'attente puis synchronisée
  await context.setOffline(true);
  await expect(page.getByText("Hors connexion")).toBeVisible();
  await addEvent("Carton jaune", "40");
  await expect(page.getByText(/action\(s\) en attente de synchronisation/)).toBeVisible();
  await expect(page.getByRole("list", { name: "Événements du match" }).getByText("Carton jaune")).toBeVisible();
  await context.setOffline(false);
  await expect(page.getByText(/action\(s\) en attente/)).toBeHidden({ timeout: 30_000 });

  // Validation : résultat officiel
  await page.getByRole("button", { name: /valider la feuille/ }).click();
  await expect(page.getByText(/Feuille validée/)).toBeVisible();

  // Le classement public reflète la victoire
  await page.goto("/classements");
  await expect(page.locator("tbody tr").filter({ hasText: /^\s*1/ }).first()).toBeVisible();
  const points = await page.locator("tbody tr td:nth-last-child(2)").allTextContents();
  expect(points.map(Number)).toContain(3);
});
