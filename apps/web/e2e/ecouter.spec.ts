// « Écouter la page » : la lecture à voix haute suit le contenu de la page, avec les textes
// prévus pour les lecteurs d'écran. La voix de l'appareil est remplacée par un enregistreur
// (le navigateur de test n'a pas de voix).
import { expect, test, type Page } from "@playwright/test";

test.use({ viewport: { width: 1366, height: 900 }, isMobile: false, hasTouch: false });

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => {
    const w = window as unknown as { __spoken: string[]; __hold: boolean };
    w.__spoken = [];
    w.__hold = false;
    let pending: { onend?: () => void } | null = null;
    const synth = {
      getVoices: () => [{ lang: "fr-FR", name: "Voix de test", localService: true }],
      cancel: () => (pending = null),
      speak(u: { text: string; onend?: () => void }) {
        w.__spoken.push(u.text);
        pending = u;
        // Phrase « terminée » aussitôt, sauf si le test veut garder la lecture en cours
        setTimeout(() => !w.__hold && pending === u && u.onend?.(), 0);
      },
      addEventListener() {},
    };
    Object.defineProperty(window, "speechSynthesis", { value: synth });
    (window as unknown as { SpeechSynthesisUtterance: unknown }).SpeechSynthesisUtterance = function (this: { text: string }, t: string) {
      this.text = t;
    };
  });
});

const spoken = (page: Page) => page.evaluate(() => (window as unknown as { __spoken: string[] }).__spoken);

test("le classement est lu ligne par ligne, avec le nom des colonnes", async ({ page }) => {
  await page.goto("/classements");
  await page.getByRole("button", { name: "Écouter la page" }).click();
  await expect.poll(async () => (await spoken(page)).length).toBeGreaterThan(10);
  const text = (await spoken(page)).join("\n");
  expect(text).toContain("Classements");
  expect(text).toMatch(/Rang 1, place qualificative, Équipe .+, Matchs joués \d+, .*Points \d+/);
  expect(text).not.toContain("→");
  // Ni l'en-tête ni le menu ne sont lus
  expect(text).not.toContain("Navigation principale");
});

test("commandes de lecture : pause, reprise, arrêt", async ({ page }) => {
  await page.goto("/");
  await page.evaluate(() => ((window as unknown as { __hold: boolean }).__hold = true));
  await page.getByRole("button", { name: "Écouter la page" }).click();
  const bar = page.getByRole("toolbar", { name: "Lecture à voix haute" });
  await expect(bar).toBeVisible();
  await expect(page.locator("[data-reading]")).toHaveCount(1);
  await bar.getByRole("button", { name: "Pause" }).click();
  await expect(bar).toContainText("En pause");
  await bar.getByRole("button", { name: "Reprendre" }).click();
  await bar.getByRole("button", { name: "Passage suivant" }).click();
  await expect(bar).toContainText("2/");
  await bar.getByRole("button", { name: "Arrêter la lecture" }).click();
  await expect(bar).toBeHidden();
  await expect(page.locator("[data-reading]")).toHaveCount(0);
});
