// Billetterie : catégorie créée par l'administration, achat sans compte payé dans le
// simulateur mobile money, billets QR, contrôle des entrées (double entrée, hors ligne).
import { expect, test } from "@playwright/test";

test.use({ viewport: { width: 1280, height: 900 }, isMobile: false, hasTouch: false });

test("achat de billets, paiement mobile money et contrôle à l'entrée", async ({ browser, page }) => {
  const stamp = Date.now().toString().slice(-6);
  const category = `Tribune E2E ${stamp}`;

  // 1. L'administration met des billets en vente pour le premier match à venir
  await page.goto("/connexion");
  await page.getByLabel("Adresse e-mail").fill("admin@lds.local");
  await page.getByLabel("Mot de passe").fill("Lds2027-demo");
  await page.getByRole("button", { name: "Se connecter" }).click();
  await page.getByRole("navigation", { name: "Espace officiels" }).getByRole("link", { name: "Billetterie" }).click();
  const matchSelect = page.getByLabel("Match", { exact: true });
  await expect(matchSelect.locator("option").nth(1)).toBeAttached();
  const matchId = await matchSelect.locator("option").nth(1).getAttribute("value");
  await matchSelect.selectOption(matchId!);
  await page.getByRole("button", { name: "+ Nouvelle catégorie" }).click();
  await page.getByLabel("Nom *").fill(category);
  await page.getByLabel("Prix (FCFA) *").fill("1500");
  await page.getByLabel("Nombre de places").fill("100");
  await page.getByRole("button", { name: "Enregistrer" }).click();
  await expect(page.getByRole("row", { name: new RegExp(category) })).toContainText("En vente");

  // 2. Un supporter achète 2 billets, sans compte, sur son téléphone
  const phoneCtx = await browser.newContext({ viewport: { width: 400, height: 860 } });
  const fan = await phoneCtx.newPage();
  await fan.goto(`/billetterie/${matchId}`);
  await fan.getByText(category).click();
  await fan.getByRole("button", { name: "Un billet de plus" }).click();
  await expect(fan.getByText("3 000 FCFA")).toBeVisible();
  await fan.getByLabel("Nom et prénom").fill("Awa Ouédraogo");
  await fan.getByLabel("Numéro mobile money").fill(`76 ${stamp.slice(0, 2)} ${stamp.slice(2, 4)} ${stamp.slice(4)}`);
  await fan.getByRole("button", { name: "Payer par mobile money" }).click();

  // Page de l'opérateur (simulateur) puis retour automatique vers les billets
  await expect(fan.getByText("SIMULATEUR — aucun argent réel")).toBeVisible();
  await fan.getByRole("button", { name: "Confirmer le paiement" }).click();
  await expect(fan.getByText(/C'est payé ! Voici vos 2 billet/)).toBeVisible({ timeout: 20_000 });
  await expect(fan.getByRole("img", { name: /QR code du billet B-/ })).toHaveCount(2);

  // Les billets restent sur l'appareil (Mes billets) même hors connexion
  const url = new URL(fan.url());
  const reference = url.pathname.split("/").pop()!;
  await phoneCtx.setOffline(true);
  await fan.goto("/billets").catch(() => {});
  await phoneCtx.setOffline(false);

  const order = await (await fan.request.get(`/api/v1/tickets/orders/${reference}?k=${url.searchParams.get("k")}`)).json();
  const [t1, t2] = order.tickets.map((t: { token: string }) => t.token);

  // 3. Contrôle à l'entrée par un contrôleur d'accès
  const gateCtx = await browser.newContext({ viewport: { width: 420, height: 900 } });
  const gate = await gateCtx.newPage();
  await gate.goto("/connexion");
  await gate.getByLabel("Adresse e-mail").fill("controle@lds.local");
  await gate.getByLabel("Mot de passe").fill("Lds2027-demo");
  await gate.getByRole("button", { name: "Se connecter" }).click();
  await expect(gate.getByRole("heading", { name: "Contrôle des entrées" })).toBeVisible();
  await gate.getByLabel("Match").selectOption(matchId!);
  await gate.getByLabel("Porte / appareil").fill("Porte A");
  await gate.getByRole("button", { name: "Préparer l'appareil" }).click();
  await expect(gate.getByText(/Prêt hors ligne : \d+ billet\(s\) connus/)).toBeVisible();

  const qr = gate.getByLabel("Contenu du QR code");
  await qr.fill(t1);
  await gate.getByRole("button", { name: "Vérifier" }).click();
  await expect(gate.getByRole("alert", { name: "Résultat du contrôle" })).toContainText("ENTRÉE AUTORISÉE");
  await qr.fill(t1);
  await gate.getByRole("button", { name: "Vérifier" }).click();
  await expect(gate.getByRole("alert", { name: "Résultat du contrôle" })).toContainText("DÉJÀ ENTRÉ");

  // Coupure réseau : l'appareil continue, puis synchronise au retour du réseau
  await gateCtx.setOffline(true);
  await qr.fill(t2);
  await gate.getByRole("button", { name: "Vérifier" }).click();
  await expect(gate.getByRole("alert", { name: "Résultat du contrôle" })).toContainText("ENTRÉE AUTORISÉE");
  await expect(gate.getByText("1 passage(s) à synchroniser", { exact: false })).toBeVisible();
  await gateCtx.setOffline(false);
  await expect(gate.getByText("à synchroniser", { exact: false })).toHaveCount(0, { timeout: 20_000 });

  // 4. Le back-office voit les ventes et les entrées
  await page.reload();
  await page.getByLabel("Match", { exact: true }).selectOption(matchId!);
  await expect(page.getByRole("row", { name: new RegExp(category) })).toContainText("3 000 FCFA");
  await expect(page.getByText(reference)).toBeVisible();

  await phoneCtx.close();
  await gateCtx.close();
});
