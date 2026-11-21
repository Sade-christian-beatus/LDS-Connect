import { defineConfig, devices } from "@playwright/test";

// Tests de bout en bout : la pile doit tourner (make dev) et être seedée (make seed).
// E2E_BASE_URL : adresse du site (défaut http://localhost:3000).
// PW_CHROMIUM_PATH : navigateur Chromium déjà installé (sinon : npx playwright install chromium).
export default defineConfig({
  testDir: "./e2e",
  timeout: 90_000,
  expect: { timeout: 15_000 },
  fullyParallel: false,
  workers: 1,
  reporter: [["list"]],
  use: {
    baseURL: process.env.E2E_BASE_URL ?? "http://localhost:3000",
    locale: "fr-FR",
    timezoneId: "Africa/Ouagadougou",
    trace: "off",
    launchOptions: process.env.PW_CHROMIUM_PATH ? { executablePath: process.env.PW_CHROMIUM_PATH } : {},
  },
  projects: [{ name: "mobile", use: { ...devices["Pixel 7"] } }],
});
