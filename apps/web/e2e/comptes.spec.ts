// Comptes : création d'un délégué, attribution d'un match, première connexion et
// changement de mot de passe par l'intéressé.
import { createHmac } from "node:crypto";
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

// Code TOTP (RFC 6238) calculé comme le ferait l'application d'authentification du téléphone
function totp(secret: string, offset = 0): string {
  const alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567";
  let bits = "";
  for (const c of secret.replace(/\s/g, "").toUpperCase()) bits += alphabet.indexOf(c).toString(2).padStart(5, "0");
  const key = Buffer.from(bits.match(/.{8}/g)!.map((b) => parseInt(b, 2)));
  const counter = Buffer.alloc(8);
  counter.writeBigUInt64BE(BigInt(Math.floor(Date.now() / 30000) + offset));
  const digest = createHmac("sha1", key).update(counter).digest();
  const o = digest[digest.length - 1] & 0x0f;
  return String((digest.readUInt32BE(o) & 0x7fffffff) % 1_000_000).padStart(6, "0");
}

test("double authentification : activation depuis « Mon compte » puis connexion avec code", async ({ page }) => {
  // Compte neuf (créé par le super administrateur) pour rester rejouable
  const stamp = Date.now().toString().slice(-6);
  const email = `mfa.${stamp}@exemple.bf`;
  await login(page, "superadmin@lds.local", "Lds2027-demo");
  await page.getByRole("navigation", { name: "Espace officiels" }).getByRole("link", { name: "Comptes" }).click();
  await page.getByRole("button", { name: "+ Nouveau compte" }).click();
  const form = page.getByRole("dialog", { name: "Nouveau compte" });
  await form.getByLabel("Adresse e-mail *").fill(email);
  await form.getByLabel("Nom complet *").fill(`Contrôleur MFA ${stamp}`);
  await form.getByLabel("Rôle *").selectOption("controleur_acces");
  await form.getByRole("button", { name: "Créer le compte" }).click();
  const creds = page.getByRole("dialog", { name: "Mot de passe provisoire" });
  const temporary = (await creds.getByLabel("Mot de passe provisoire").textContent())!.trim();
  await creds.getByRole("button", { name: "J'ai transmis le mot de passe" }).click();
  await page.getByRole("button", { name: "Déconnexion" }).click();

  await login(page, email, temporary);
  const password = `Phrase-de-passe-${stamp}`;
  await page.getByLabel("Mot de passe provisoire reçu").fill(temporary);
  await page.getByLabel("Nouveau mot de passe", { exact: true }).fill(password);
  await page.getByLabel("Confirmer le nouveau mot de passe").fill(password);
  await page.getByRole("button", { name: "Changer le mot de passe" }).click();
  await page.getByRole("button", { name: "Se reconnecter" }).click();
  await login(page, email, password);
  await expect(page.getByRole("heading", { name: "Contrôle des entrées" })).toBeVisible();

  await page.goto("/compte");
  const section = page.getByRole("region", { name: "Double authentification" });
  await section.getByRole("button", { name: "Activer la double authentification" }).click();
  await expect(section.getByAltText("QR code d'activation")).toBeVisible();
  const secret = (await section.getByLabel("Clé de configuration").textContent())!;
  await section.getByLabel("Code à 6 chiffres").fill(totp(secret));
  await section.getByRole("button", { name: "Confirmer l'activation" }).click();
  await expect(section.getByText("Double authentification activée")).toBeVisible();
  await page.getByRole("button", { name: "Déconnexion" }).click();

  // Connexion en deux étapes ; le code de l'activation ne peut pas resservir
  await login(page, email, password);
  await expect(page.getByText("Mot de passe vérifié")).toBeVisible();
  await page.getByLabel("Code de vérification").fill(totp(secret, 1));
  await page.getByRole("button", { name: "Valider le code" }).click();
  await expect(page.getByRole("heading", { name: "Contrôle des entrées" })).toBeVisible();
});
