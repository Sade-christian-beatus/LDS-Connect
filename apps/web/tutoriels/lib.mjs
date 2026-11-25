// Outils d'enregistrement des tutoriels : capture des images de l'écran (protocole Chrome),
// curseur ou doigt visible, sous-titres horodatés et rythme réglé sur la voix off.
import fs from "node:fs";
import path from "node:path";
import { chromium } from "@playwright/test";

export const BASE = process.env.TUTO_BASE_URL ?? "http://127.0.0.1:3000";
export const API = process.env.TUTO_API_URL ?? "http://127.0.0.1:8000";
export const SMS = process.env.SMS_SIMULATOR_URL ?? "http://127.0.0.1:8090";
export const PASSWORD = "Lds2027-demo";
const CHROMIUM = process.env.PW_CHROMIUM_PATH ?? "/opt/pw-browsers/chromium";

// Curseur (ordinateur) ou doigt (téléphone) dessiné dans la page : il apparaît dans la vidéo.
const POINTER_SCRIPT = (touch) => `
(() => {
  const TOUCH = ${touch};
  const install = () => {
    if (document.getElementById("tuto-pointer")) return;
    const p = document.createElement("div");
    p.id = "tuto-pointer";
    p.style.cssText = "position:fixed;left:0;top:0;z-index:2147483647;pointer-events:none;transition:opacity .2s;";
    p.innerHTML = TOUCH
      ? '<div style="width:38px;height:38px;margin:-19px 0 0 -19px;border-radius:50%;background:rgba(255,255,255,.55);border:3px solid rgba(20,83,45,.85);box-shadow:0 2px 10px rgba(0,0,0,.35)"></div>'
      : '<svg width="28" height="34" viewBox="0 0 28 34" style="filter:drop-shadow(0 2px 3px rgba(0,0,0,.45))"><path d="M2 2 L2 28 L9 21 L14 32 L19 30 L14 19 L24 19 Z" fill="#fff" stroke="#111" stroke-width="2" stroke-linejoin="round"/></svg>';
    document.documentElement.appendChild(p);
    const saved = JSON.parse(sessionStorage.getItem("tuto-pointer") || "null");
    if (saved) p.style.transform = "translate(" + saved.x + "px," + saved.y + "px)";
    else p.style.opacity = "0";
    addEventListener("mousemove", (e) => {
      p.style.opacity = "1";
      p.style.transform = "translate(" + e.clientX + "px," + e.clientY + "px)";
      sessionStorage.setItem("tuto-pointer", JSON.stringify({ x: e.clientX, y: e.clientY }));
    }, true);
    addEventListener("mousedown", (e) => {
      const r = document.createElement("div");
      r.style.cssText = "position:fixed;z-index:2147483646;pointer-events:none;border-radius:50%;border:3px solid #f5c518;width:16px;height:16px;left:" + (e.clientX - 8) + "px;top:" + (e.clientY - 8) + "px;transition:all .45s ease-out;opacity:1";
      document.documentElement.appendChild(r);
      requestAnimationFrame(() => { r.style.transform = "scale(4)"; r.style.opacity = "0"; });
      setTimeout(() => r.remove(), 600);
    }, true);
  };
  if (document.documentElement) install(); else addEventListener("DOMContentLoaded", install);
  addEventListener("DOMContentLoaded", install);
})();`;

export async function launch() {
  // Facteur d'échelle réel du navigateur : les images capturées sont en pleine définition
  return chromium.launch({ executablePath: CHROMIUM, args: ["--force-device-scale-factor=2"] });
}

/** Une séquence enregistrée : contexte de navigation, capture d'écran continue, sous-titres. */
export class Take {
  constructor(browser, { mobile, out }) {
    this.browser = browser;
    this.mobile = mobile;
    this.out = out;
    this.frames = [];
    this.captions = [];
    // Actions (clics, saisies, défilements, changements de page) : le montage zoome dessus
    this.events = [];
    this.voiceUntil = 0;
  }

  async start() {
    fs.rmSync(this.out, { recursive: true, force: true });
    fs.mkdirSync(path.join(this.out, "frames"), { recursive: true });
    this.ctx = await this.browser.newContext(
      this.mobile
        ? { viewport: { width: 412, height: 915 }, deviceScaleFactor: 2, isMobile: true, hasTouch: true, locale: "fr-FR" }
        : { viewport: { width: 1440, height: 900 }, deviceScaleFactor: 2, locale: "fr-FR" },
    );
    await this.ctx.addInitScript(POINTER_SCRIPT(this.mobile));
    this.page = await this.ctx.newPage();
    this.page.setDefaultTimeout(20_000);
    this.page.on("dialog", (d) => d.accept());
    this.page.on("framenavigated", (f) => {
      if (f === this.page.mainFrame() && this.t0) this.events.push({ t: this.now(), kind: "nav" });
    });
    this.cdp = await this.ctx.newCDPSession(this.page);
    this.cdp.on("Page.screencastFrame", async (f) => {
      const file = path.join(this.out, "frames", `${String(this.frames.length).padStart(5, "0")}.jpg`);
      fs.writeFileSync(file, Buffer.from(f.data, "base64"));
      this.frames.push({ file, t: Date.now() / 1000 });
      await this.cdp.send("Page.screencastFrameAck", { sessionId: f.sessionId }).catch(() => {});
    });
    await this.cdp.send("Page.startScreencast", { format: "jpeg", quality: 90, maxWidth: 3000, maxHeight: 3000 });
    this.t0 = Date.now() / 1000;
    return this.page;
  }

  now() {
    return Date.now() / 1000 - this.t0;
  }

  /** Sous-titre à l'écran et texte de la voix off ; le pas suivant attend la fin de la phrase. */
  async say(caption, voice = caption) {
    await this.waitVoice();
    const t = Date.now() / 1000 - this.t0;
    this.captions.push({ t, caption, voice });
    const words = voice.split(/\s+/).length;
    this.voiceUntil = Date.now() + Math.max(2200, (words / 2.6) * 1000);
  }

  async waitVoice() {
    const left = this.voiceUntil - Date.now();
    if (left > 0) await this.page.waitForTimeout(left);
  }

  async pause(ms = 800) {
    await this.page.waitForTimeout(ms);
  }

  /** Déplacement visible du curseur jusqu'à l'élément, puis clic. */
  async tap(locator, { hold = 350 } = {}) {
    // Élément centré à l'écran : jamais caché sous la barre d'onglets du téléphone
    const visible = await locator.evaluate((el) => {
      const r = el.getBoundingClientRect();
      return r.top > 90 && r.bottom < innerHeight - 110;
    });
    if (!visible) {
      await locator.evaluate((el) => el.scrollIntoView({ block: "center", behavior: "smooth" }));
      await this.page.waitForTimeout(650);
    }
    const box = await locator.boundingBox();
    if (box) this.events.push({ t: this.now(), kind: "tap", x: box.x + box.width / 2, y: box.y + box.height / 2, w: box.width, h: box.height });
    if (box) {
      await this.page.mouse.move(box.x + box.width / 2, box.y + box.height / 2, { steps: 14 });
      await this.page.waitForTimeout(hold);
    }
    await locator.click();
  }

  async type(locator, text) {
    await this.tap(locator, { hold: 200 });
    await locator.fill("");
    const start = this.now();
    await locator.pressSequentially(text, { delay: 55 });
    const box = await locator.boundingBox().catch(() => null);
    if (box) this.events.push({ t: start, end: this.now(), kind: "type", x: box.x + box.width / 2, y: box.y + box.height / 2, w: box.width, h: box.height });
  }

  async scroll(dy, ms = 900) {
    this.events.push({ t: this.now(), kind: "scroll", dy });
    await this.page.evaluate((y) => window.scrollBy({ top: y, behavior: "smooth" }), dy);
    await this.page.waitForTimeout(ms);
  }

  async stop() {
    await this.waitVoice();
    await this.page.waitForTimeout(1200);
    await this.cdp.send("Page.stopScreencast").catch(() => {});
    await this.ctx.close();
    const end = Date.now() / 1000 - this.t0;
    fs.writeFileSync(
      path.join(this.out, "take.json"),
      JSON.stringify(
        {
          mobile: this.mobile,
          viewport: this.mobile ? { width: 412, height: 915 } : { width: 1440, height: 900 },
          end,
          frames: this.frames.map((f) => ({ file: f.file, t: f.t - this.t0 })),
          captions: this.captions,
          events: this.events,
        },
        null,
        1,
      ),
    );
  }
}

export async function login(take, email) {
  const p = take.page;
  await p.goto(`${BASE}/connexion`);
  await take.type(p.getByLabel("Adresse e-mail"), email);
  await take.type(p.getByLabel("Mot de passe"), PASSWORD);
  await take.tap(p.getByRole("button", { name: "Se connecter" }));
  await p.waitForURL((u) => !u.pathname.startsWith("/connexion"));
}

/** Jeton d'accès de l'API (préparation des données du tournage, sans passer par l'écran). */
export async function apiToken(email) {
  const r = await fetch(`${API}/api/v1/auth/login`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ email, password: PASSWORD }),
  });
  return (await r.json()).access_token;
}
