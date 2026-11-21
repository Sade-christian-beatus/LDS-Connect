// Back-office : registre (ajout d'un joueur, licence, suspension), calendrier, journal,
// et périmètre limité du gestionnaire de club.
import { expect, type Page, test } from "@playwright/test";

const PASSWORD = "Lds2027-demo";

async function login(page: Page, email: string) {
  await page.goto("/connexion");
  await page.getByLabel("Adresse e-mail").fill(email);
  await page.getByLabel("Mot de passe").fill(PASSWORD);
  await page.getByRole("button", { name: "Se connecter" }).click();
}

test.use({ viewport: { width: 1280, height: 900 }, isMobile: false, hasTouch: false });

test("l'administration gère un effectif, une licence et le calendrier", async ({ page }) => {
  await login(page, "admin@lds.local");
  await expect(page.getByRole("heading", { name: "Registre des équipes" })).toBeVisible();
  await page.getByRole("link", { name: "Nanga du Kadiogo" }).click();
  await expect(page.getByRole("heading", { name: "Nanga du Kadiogo" })).toBeVisible();

  // Libérer une place (effectif complet) puis inscrire un joueur
  const unique = `E2e${Date.now().toString().slice(-6)}`;
  const row = page.getByRole("row").filter({ hasText: "Défenseur" }).last();
  await row.getByRole("button", { name: "Retirer" }).click();
  await page.getByRole("dialog", { name: "Retirer de l'effectif" }).getByRole("button", { name: "Retirer de l'effectif" }).click();
  await expect(page.getByText(/retiré\(e\) de l'effectif/)).toBeVisible();

  await page.getByRole("button", { name: "+ Joueur" }).click();
  const form = page.getByRole("dialog", { name: "Nouveau joueur" });
  await form.getByLabel("Prénom(s) *").fill("Test");
  await form.getByLabel("Nom *", { exact: true }).fill(unique);
  await form.getByLabel("Date de naissance *").fill("2009-03-15");
  await form.getByLabel("Poste *").selectOption("FW");
  await form.getByRole("button", { name: "Ajouter à l'effectif" }).click();
  await expect(page.getByText(`Test ${unique} ajouté(e) à l'effectif`)).toBeVisible();

  // Mineur, résidence non vérifiée, licence à délivrer
  const newRow = page.getByRole("row").filter({ hasText: unique });
  await expect(newRow.getByText("Mineur")).toBeVisible();
  await expect(newRow.getByText("À délivrer")).toBeVisible();

  // Délivrance puis suspension de la licence
  await newRow.getByRole("button", { name: "Licence" }).click();
  const dialog = page.getByRole("dialog", { name: "Licence" });
  await dialog.getByRole("button", { name: "Délivrer la licence" }).click();
  await expect(page.getByText("Licence délivrée")).toBeVisible();
  await expect(newRow.getByText(/LDS27-\d{5}/)).toBeVisible();

  await newRow.getByRole("button", { name: "Licence" }).click();
  await expect(dialog.getByAltText(/QR code de la licence/)).toBeVisible();
  await dialog.getByLabel("Nouveau statut").selectOption("suspended");
  await dialog.getByLabel("Motif (journalisé)").fill("Pièce d'identité à présenter");
  await dialog.getByRole("button", { name: "Appliquer" }).click();
  await expect(newRow.getByText("Suspendue")).toBeVisible();

  // Calendrier : déplacer un match
  await page.getByRole("navigation", { name: "Espace officiels" }).getByRole("link", { name: "Calendrier" }).click();
  await expect(page.getByRole("heading", { name: "Calendrier" })).toBeVisible();
  // Le match est suivi par son nom : la liste est triée par coup d'envoi et il change de place
  const firstKickoff = page.getByLabel(/Coup d'envoi/).first();
  const label = (await firstKickoff.getAttribute("aria-label"))!;
  const fixture = label.replace("Coup d'envoi ", "");
  await firstKickoff.fill("2027-01-10T16:30");
  await page.getByRole("row").filter({ has: page.getByLabel(label, { exact: true }) }).getByRole("button", { name: "Enregistrer" }).click();
  await expect(page.getByText(`${fixture} : modifications enregistrées`)).toBeVisible();
  await expect(page.getByLabel(label, { exact: true })).toHaveValue("2027-01-10T16:30");

  // Journal : la suspension est tracée
  await page.getByRole("navigation", { name: "Espace officiels" }).getByRole("link", { name: "Journal" }).click();
  await page.getByLabel("Action").selectOption("status_change");
  await expect(page.getByRole("cell", { name: "Changement de statut" }).first()).toBeVisible();
});

test("un gestionnaire de club ne voit que son équipe", async ({ page }) => {
  await login(page, "club.vinnim@lds.local");
  await expect(page.getByRole("heading", { name: "Vinnim du Kadiogo" })).toBeVisible();
  const menu = page.getByRole("navigation", { name: "Espace officiels" });
  await expect(menu.getByRole("link", { name: "Calendrier" })).toHaveCount(0);
  await expect(menu.getByRole("link", { name: "Journal" })).toHaveCount(0);
  await expect(page.getByRole("button", { name: /Délivrer/ })).toHaveCount(0);
  await expect(page.getByRole("link", { name: "← Toutes les équipes" })).toHaveCount(0);
});
