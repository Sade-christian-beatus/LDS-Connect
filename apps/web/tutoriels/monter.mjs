// Montage des tutoriels (v2) : chaque image est composée dans tutoriels/studio.html — fond animé
// aux couleurs nationales, appareil, zoom automatique sur l'action (calculé à partir des clics et
// saisies enregistrés), sous-titres et narration qui s'affiche au rythme de la voix, barre de
// diffusion en pied de page — puis capturée et encodée par ffmpeg.
// Usage : node tutoriels/monter.mjs <dossier_des_prises> <dossier_de_sortie> [id du chapitre…]
import { spawn } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { chromium } from "@playwright/test";
import { CHAPITRES } from "./chapitres.mjs";
import { API } from "./lib.mjs";

const here = path.dirname(fileURLToPath(import.meta.url));
const takes = path.resolve(process.argv[2] ?? "./tutoriels-sortie");
const out = path.resolve(process.argv[3] ?? "./tutoriels-videos");
const only = process.argv.slice(4);
fs.mkdirSync(out, { recursive: true });

const FPS = 30;
const TITLE = 3.4; // carton d'ouverture (s)
const TAIL = 1.0; // dernière image tenue (s)
const LAYOUT = {
  mobile: { x: 330, y: 58, w: 405, h: 900, panel: { x: 900, w: 920 } },
  desktop: { x: 56, y: 96, w: 1280, h: 800, panel: { x: 1376, w: 488 } },
};
const URLS = {
  "01-site-public": "lds-connect.bf",
  "02-billet": "lds-connect.bf/billetterie",
  "03-vote": "lds-connect.bf/votes",
  "04-club": "lds-connect.bf/admin/equipes",
  "05-delegue": "lds-connect.bf/delegue",
  "06-controle": "lds-connect.bf/acces",
  "07-administration": "lds-connect.bf/admin",
};

let logo = "";
try {
  const b = await (await fetch(`${API}/api/v1/brand`)).json();
  if (b.logo_url) logo = `${API}${b.logo_url}`;
} catch {
  /* sans logo */
}

/** Caméra image par image : zoom sur la zone de l'action en cours, retour au plan large aux
 * changements de page ; mouvement amorti (ressort) pour rester doux à l'œil. */
function cameraPath(take, frames) {
  const vw = take.viewport.width;
  const vh = take.viewport.height;
  const zoomIn = take.mobile ? 1.22 : 1.6;
  const events = (take.events ?? []).slice().sort((a, b) => a.t - b.t);
  // Zoom sur le clic (2,4 s, pour laisser voir son résultat en plan large) ou sur la saisie
  // en cours, jusqu'à l'action suivante ; un changement de page ou un
  // défilement ramène au plan large.
  const focus = (t) => {
    let best = null;
    for (const [i, e] of events.entries()) {
      if ((e.kind === "nav" || e.kind === "scroll") && t >= e.t && t < e.t + 0.9) return null;
      if (e.kind !== "tap" && e.kind !== "type") continue;
      const next = events.slice(i + 1).find((x) => x.t > (e.end ?? e.t));
      const hold = e.kind === "type" ? (e.end ?? e.t) + 1.5 : e.t + 2.4;
      const to = Math.min(hold, next ? next.t - 0.2 : Infinity);
      if (t >= e.t - 0.45 && t <= to) best = e;
    }
    return best;
  };
  const cam = [];
  let z = 1;
  let cx = 0.5;
  let cy = 0.5;
  const k = 1 - Math.exp(-4.2 / FPS);
  for (let i = 0; i < frames; i++) {
    const t = i / FPS;
    const e = focus(t);
    const zt = e ? zoomIn : 1;
    const xt = e ? e.x / vw : 0.5;
    const yt = e ? e.y / vh : 0.5;
    z += (zt - z) * k;
    cx += (xt - cx) * k;
    cy += (yt - cy) * k;
    const h = 0.5 / z;
    cam.push([+z.toFixed(4), +Math.min(1 - h, Math.max(h, cx)).toFixed(4), +Math.min(1 - h, Math.max(h, cy)).toFixed(4)]);
  }
  return cam;
}

async function renderVideo(page, cfg, frames, file) {
  await page.evaluate((c) => window.setup(c), cfg);
  const ff = spawn("ffmpeg", ["-y", "-v", "error", "-f", "image2pipe", "-framerate", String(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", "-r", String(FPS), "-movflags", "+faststart", file], { stdio: ["pipe", "inherit", "inherit"] });
  const done = new Promise((resolve, reject) => ff.on("close", (code) => (code === 0 ? resolve() : reject(new Error(`ffmpeg ${code}`)))));
  const cdp = await page.context().newCDPSession(page);
  for (let i = 0; i < frames; i++) {
    await page.evaluate((n) => window.render(n), i);
    const shot = await cdp.send("Page.captureScreenshot", { format: "jpeg", quality: 92 });
    if (!ff.stdin.write(Buffer.from(shot.data, "base64"))) await new Promise((r) => ff.stdin.once("drain", r));
  }
  ff.stdin.end();
  await done;
}

const slug = (s) => s.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/(^-|-$)/g, "");
const tc = (s) => `${String(Math.floor(s / 60)).padStart(2, "0")}:${String(Math.floor(s % 60)).padStart(2, "0")}`;

// Rendu sans facteur d'échelle forcé : 1920 × 1080 exactement
const browser = await chromium.launch({ executablePath: process.env.PW_CHROMIUM_PATH ?? "/opt/pw-browsers/chromium" });
const page = await (await browser.newContext({ viewport: { width: 1920, height: 1080 }, deviceScaleFactor: 1 })).newPage();
await page.goto(pathToFileURL(path.join(here, "studio.html")).href);
await page.waitForLoadState("networkidle").catch(() => {});

const chapters = CHAPITRES.filter((c) => fs.existsSync(path.join(takes, c.id, "take.json")));
const made = [];
const script = ["# Tutoriels LDS Connect — script de la voix off", "", "Texte à enregistrer par une voix réelle, minuté sur chaque vidéo (le minutage inclut le carton d'ouverture). Les sous-titres à l'écran sont la version courte ; la narration s'affiche aussi à l'écran, mot à mot.", ""];
for (const [n, ch] of chapters.entries()) {
  const take = JSON.parse(fs.readFileSync(path.join(takes, ch.id, "take.json"), "utf8"));
  const file = path.join(out, `${ch.id}-${slug(ch.titre)}.mp4`);
  const duration = TITLE - 0.6 + take.end + TAIL;
  const frames = Math.round(duration * FPS);
  if (!only.length || only.includes(ch.id)) {
    const started = Date.now();
    const cfg = {
      mode: "chapter",
      n: n + 1,
      total: chapters.length,
      titre: ch.titre,
      public: ch.public,
      mobile: ch.mobile,
      url: URLS[ch.id] ?? "lds-connect.bf",
      logo,
      fps: FPS,
      titleDur: TITLE,
      end: take.end,
      layout: ch.mobile ? LAYOUT.mobile : LAYOUT.desktop,
      frames: take.frames.map((f) => ({ t: f.t, file: pathToFileURL(f.file).href })),
      captions: take.captions,
      cam: cameraPath(take, Math.round((take.end + TAIL) * FPS) + 1),
    };
    await renderVideo(page, cfg, frames, file);
    console.log(`${path.basename(file)} : ${duration.toFixed(0)} s, rendu en ${((Date.now() - started) / 1000).toFixed(0)} s`);
  }
  made.push(file);
  script.push(`## ${n + 1}. ${ch.titre} — ${ch.public}`, "", `Fichier : \`${path.basename(file)}\` (${tc(duration)})`, "", "| Début | À l'écran | Voix off |", "|---|---|---|");
  for (const c of take.captions) script.push(`| ${tc(TITLE - 0.6 + c.t)} | ${c.caption} | ${c.voice} |`);
  script.push("");
}
fs.writeFileSync(path.join(out, "SCRIPT_VOIX_OFF.md"), script.join("\n"));

if (!only.length) {
  // Ouverture et fermeture de la version complète, puis assemblage sans réencodage
  const parts = [];
  for (const [mode, seconds] of [["intro", 5], ["outro", 4]]) {
    const f = path.join(out, `_${mode}.mp4`);
    await renderVideo(page, { mode, fps: FPS, duration: seconds, logo, chapters: chapters.map((c) => c.titre) }, seconds * FPS, f);
    parts.push(f);
  }
  const list = path.join(out, "_complet.txt");
  fs.writeFileSync(list, [parts[0], ...made, parts[1]].map((f) => `file '${f}'`).join("\n"));
  await new Promise((resolve, reject) => {
    const ff = spawn("ffmpeg", ["-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", list, "-c", "copy", "-movflags", "+faststart", path.join(out, "00-tutoriel-complet.mp4")], { stdio: "inherit" });
    ff.on("close", (code) => (code === 0 ? resolve() : reject(new Error(`ffmpeg ${code}`))));
  });
  for (const f of [...parts, list]) fs.rmSync(f);
  console.log("00-tutoriel-complet.mp4 : prêt");
}
await browser.close();
