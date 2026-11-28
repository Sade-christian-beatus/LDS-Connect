// Accessibilité du site public : contrôle automatique axe-core (règles WCAG 2.1 A et AA) sur
// les pages principales, sur téléphone et sur ordinateur. Un contrôle automatique ne remplace
// pas un essai avec un lecteur d'écran, mais il empêche de réintroduire les erreurs connues.
import { expect, test, type Page } from "@playwright/test";

const AXE = require.resolve("axe-core/axe.min.js");

type Violation = { id: string; impact: string; help: string; nodes: { target: string[] }[] };

async function audit(page: Page, path: string) {
  await page.goto(path, { waitUntil: "networkidle" });
  await page.addScriptTag({ path: AXE });
  const violations: Violation[] = await page.evaluate(async () => {
    const axe = (window as unknown as { axe: { run: (ctx: Document, o: object) => Promise<{ violations: Violation[] }> } }).axe;
    const r = await axe.run(document, { runOnly: ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"] });
    return r.violations.map((v) => ({ id: v.id, impact: v.impact, help: v.help, nodes: v.nodes.map((n) => ({ target: n.target })) }));
  });
  return violations.map((v) => `${path} — ${v.impact} ${v.id} : ${v.help} (${v.nodes.map((n) => n.target.join(" ")).join(" | ")})`);
}

async function pages(page: Page) {
  const paths = ["/", "/calendrier", "/resultats", "/classements", "/statistiques", "/equipes", "/billetterie", "/votes", "/billets", "/accessibilite"];
  // Une fiche d'équipe et une page d'achat, prises dans les liens du site
  await page.goto("/equipes");
  const team = await page.locator('main a[href^="/equipes/"]').first().getAttribute("href");
  if (team) paths.push(team);
  await page.goto("/billetterie");
  const buy = await page.locator('main a[href^="/billetterie/"]').first().getAttribute("href");
  if (buy) paths.push(buy);
  return paths;
}

for (const [name, use] of [
  ["téléphone", {}],
  ["ordinateur", { viewport: { width: 1366, height: 900 }, isMobile: false, hasTouch: false }],
] as const) {
  test.describe(name, () => {
    test.use(use);
    test(`pages publiques sans erreur d'accessibilité (${name})`, async ({ page }) => {
      const problems: string[] = [];
      for (const path of await pages(page)) problems.push(...(await audit(page, path)));
      expect(problems, problems.join("\n")).toEqual([]);
    });
  });
}

test("lien d'évitement : premier élément atteint au clavier, il mène au contenu", async ({ page }) => {
  await page.goto("/classements");
  await page.keyboard.press("Tab");
  const skip = page.getByRole("link", { name: "Aller au contenu" });
  await expect(skip).toBeFocused();
  await expect(skip).toBeVisible();
  await page.keyboard.press("Enter");
  await expect(page.locator("main#contenu")).toBeFocused();
});

test("classement : colonnes nommées en entier pour le lecteur d'écran", async ({ page }) => {
  await page.goto("/classements");
  const table = page.getByRole("table").first();
  for (const name of ["Rang", "Matchs joués", "Différence de buts", "Points"]) {
    await expect(table.getByRole("columnheader", { name })).toBeAttached();
  }
});
