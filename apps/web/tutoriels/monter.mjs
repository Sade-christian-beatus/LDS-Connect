// Montage des tutoriels : habillage 1920×1080 aux couleurs de la Ligue, téléphone ou navigateur,
// sous-titres en fondu, carton de titre par chapitre, version complète et script de voix off.
// Usage : node tutoriels/monter.mjs <dossier_des_prises> <dossier_de_sortie>
import { execFileSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { CHAPITRES } from "./chapitres.mjs";
import { API, launch } from "./lib.mjs";

const takes = path.resolve(process.argv[2] ?? "./tutoriels-sortie");
const out = path.resolve(process.argv[3] ?? "./tutoriels-videos");
const work = path.join(out, "_travail");
fs.mkdirSync(work, { recursive: true });
const W = 1920;
const H = 1080;
const TITLE = 3.2; // durée du carton de titre (s)
const FPS = 30;

const LAYOUT = {
  mobile: { x: 330, y: 60, w: 432, h: 960, panel: { x: 880, w: 940 } },
  desktop: { x: 60, y: 176, w: 1280, h: 800, panel: { x: 1390, w: 470 } },
};

let logo = "";
try {
  const b = await (await fetch(`${API}/api/v1/brand`)).json();
  if (b.logo_url) logo = `${API}${b.logo_url}`;
} catch {
  /* sans logo : marque textuelle */
}

const CSS = `
* { margin:0; box-sizing:border-box; }
body { width:${W}px; height:${H}px; font-family: Inter, system-ui, sans-serif; color:#fff; overflow:hidden; }
.bg { position:absolute; inset:0; background: radial-gradient(120% 90% at 85% 10%, #1f7a3a 0%, #0d4a24 40%, #062b15 100%); }
.lines { position:absolute; inset:0; opacity:.07; }
.stripe { position:absolute; left:0; right:0; bottom:0; height:10px; display:flex; }
.stripe span { flex:1 } .r{background:#c8102e} .g{background:#f5c518} .v{background:#1f7a3a}
.brand { position:absolute; left:60px; top:44px; display:flex; align-items:center; gap:16px; }
.brand img { height:64px; border-radius:14px; background:#fff; padding:4px; }
.brand b { display:block; font-size:15px; letter-spacing:.28em; color:#f5c518; font-weight:700; }
.brand i { display:block; font-style:normal; font-size:26px; font-weight:900; }
.gold { color:#f5c518 }
`;
const PITCH = `<svg class="lines" viewBox="0 0 1920 1080" preserveAspectRatio="none"><g fill="none" stroke="#fff" stroke-width="4">
<rect x="80" y="60" width="1760" height="960"/><line x1="960" y1="60" x2="960" y2="1020"/><circle cx="960" cy="540" r="150"/>
<rect x="80" y="300" width="260" height="480"/><rect x="1580" y="300" width="260" height="480"/></g></svg>`;
const STRIPE = `<div class="stripe"><span class="r"></span><span class="g"></span><span class="v"></span></div>`;
const BRAND = `<div class="brand">${logo ? `<img src="${logo}">` : ""}<div><b>LDS CONNECT</b><i>Tutoriel</i></div></div>`;

async function render(page, html, file, transparent = false) {
  await page.setContent(`<!doctype html><html><head><meta charset="utf-8"><style>${CSS}</style></head><body${transparent ? ' style="background:transparent"' : ""}>${html}</body></html>`);
  await page.waitForLoadState("networkidle").catch(() => {});
  await page.screenshot({ path: file, omitBackground: transparent });
}

function background(ch, n, total) {
  const L = ch.mobile ? LAYOUT.mobile : LAYOUT.desktop;
  const device = ch.mobile
    ? `<div style="position:absolute;left:${L.x - 18}px;top:${L.y - 18}px;width:${L.w + 36}px;height:${L.h + 36}px;border-radius:56px;background:#0b0f0d;box-shadow:0 30px 80px rgba(0,0,0,.55), inset 0 0 0 2px #2b332f"></div>`
    : `<div style="position:absolute;left:${L.x}px;top:${L.y - 40}px;width:${L.w}px;height:${L.h + 40}px;border-radius:14px;background:#f1f1ef;box-shadow:0 30px 80px rgba(0,0,0,.55);overflow:hidden">
         <div style="height:40px;display:flex;align-items:center;gap:8px;padding:0 16px;background:#e4e4e0">
           <span style="width:12px;height:12px;border-radius:50%;background:#ec6a5e"></span><span style="width:12px;height:12px;border-radius:50%;background:#f4bf4f"></span><span style="width:12px;height:12px;border-radius:50%;background:#61c554"></span>
           <span style="margin-left:18px;flex:0 0 520px;height:24px;border-radius:12px;background:#fff;color:#555;font-size:14px;line-height:24px;padding-left:14px">lds-connect · espace officiels</span>
         </div></div>`;
  return `<div class="bg"></div>${PITCH}${BRAND}
  <div style="position:absolute;left:${L.panel.x}px;top:${ch.mobile ? 150 : 176}px;width:${L.panel.w}px">
    <p style="font-size:18px;letter-spacing:.24em;font-weight:700" class="gold">CHAPITRE ${n} / ${total}</p>
    <p style="margin-top:10px;font-size:${ch.mobile ? 60 : 44}px;font-weight:900;line-height:1.05">${ch.titre}</p>
    <p style="margin-top:14px;font-size:22px;color:#cfe8d6">${ch.public}</p>
  </div>${device}${STRIPE}`;
}

function caption(ch, text, i, count) {
  const L = ch.mobile ? LAYOUT.mobile : LAYOUT.desktop;
  const top = ch.mobile ? 470 : 470;
  const size = ch.mobile ? 54 : 38;
  return `<div style="position:absolute;left:${L.panel.x}px;top:${top}px;width:${L.panel.w}px">
    <div style="display:flex;gap:10px;margin-bottom:22px">${Array.from({ length: count }, (_, k) => `<span style="height:6px;flex:1;border-radius:3px;background:${k <= i ? "#f5c518" : "rgba(255,255,255,.22)"}"></span>`).join("")}</div>
    <p style="font-size:${size}px;font-weight:800;line-height:1.15;text-shadow:0 2px 12px rgba(0,0,0,.35)">${text}</p>
  </div>`;
}

function titleCard(ch, n, total) {
  return `<div class="bg"></div>${PITCH}${BRAND}
  <div style="position:absolute;left:160px;top:330px;right:160px">
    <p style="font-size:26px;letter-spacing:.3em;font-weight:700" class="gold">CHAPITRE ${n} / ${total}</p>
    <p style="margin-top:18px;font-size:120px;font-weight:900;line-height:1">${ch.titre}</p>
    <p style="margin-top:28px;font-size:34px;color:#cfe8d6">${ch.public}</p>
  </div>${STRIPE}`;
}

function bookend(kind) {
  const intro = kind === "intro";
  return `<div class="bg"></div>${PITCH}${STRIPE}
  <div style="position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center">
    ${logo ? `<img src="${logo}" style="height:190px;border-radius:32px;background:#fff;padding:10px;box-shadow:0 20px 60px rgba(0,0,0,.4)">` : ""}
    <p style="margin-top:40px;font-size:24px;letter-spacing:.32em;font-weight:700" class="gold">LDS CONNECT</p>
    <p style="margin-top:12px;font-size:84px;font-weight:900">${intro ? "Guide de la plateforme" : "Merci"}</p>
    <p style="margin-top:18px;font-size:30px;color:#cfe8d6">${intro ? "Supporters · clubs · délégués · contrôleurs · administration — sur téléphone et ordinateur" : "Ligue de la Souveraineté · plateforme numérique LDS Connect"}</p>
  </div>`;
}

const ff = (args) => execFileSync("ffmpeg", ["-y", "-v", "error", ...args], { stdio: "inherit" });

function screenVideo(take, ch, file) {
  const L = ch.mobile ? LAYOUT.mobile : LAYOUT.desktop;
  const frames = take.frames;
  const list = frames
    .map((f, i) => {
      const next = i + 1 < frames.length ? frames[i + 1].t : take.end;
      return `file '${f.file}'\nduration ${Math.max(0.001, next - f.t).toFixed(3)}`;
    })
    .join("\n");
  const listFile = file.replace(/\.mp4$/, ".txt");
  fs.writeFileSync(listFile, `${list}\nfile '${frames.at(-1).file}'\n`);
  const lead = frames[0].t; // les premières images arrivent après le début de la prise
  ff([
    "-f", "concat", "-safe", "0", "-i", listFile,
    "-vf", `tpad=start_duration=${lead.toFixed(3)}:start_mode=clone,fps=${FPS},scale=${L.w}:${L.h}:flags=lanczos,format=yuv420p`,
    "-c:v", "libx264", "-preset", "medium", "-crf", "18", file,
  ]);
}

function compose(ch, take, dir) {
  const L = ch.mobile ? LAYOUT.mobile : LAYOUT.desktop;
  const dur = take.end;
  const caps = take.captions;
  const inputs = ["-loop", "1", "-t", dur.toFixed(2), "-i", path.join(dir, "fond.png"), "-i", path.join(dir, "ecran.mp4")];
  let filter = `[0:v][1:v]overlay=${L.x}:${L.y}:shortest=0[b0]`;
  caps.forEach((c, i) => {
    const start = Math.max(0, c.t);
    const end = i + 1 < caps.length ? caps[i + 1].t : dur;
    inputs.push("-loop", "1", "-t", dur.toFixed(2), "-i", path.join(dir, `st-${i}.png`));
    filter += `;[${i + 2}:v]format=rgba,fade=t=in:st=${start.toFixed(2)}:d=0.35:alpha=1,fade=t=out:st=${Math.max(start, end - 0.3).toFixed(2)}:d=0.3:alpha=1[c${i}]`;
    filter += `;[b${i}][c${i}]overlay=0:0[b${i + 1}]`;
  });
  // Carton de titre en ouverture, fondu enchaîné vers l'écran
  inputs.push("-loop", "1", "-t", (TITLE + 0.6).toFixed(2), "-i", path.join(dir, "titre.png"));
  const t = caps.length + 2;
  filter += `;[b${caps.length}]format=yuv420p,setpts=PTS-STARTPTS[main];[${t}:v]format=yuv420p,fade=t=in:st=0:d=0.5,setpts=PTS-STARTPTS[tc]`;
  filter += `;[tc][main]xfade=transition=fade:duration=0.6:offset=${TITLE.toFixed(2)},format=yuv420p[v]`;
  const file = path.join(out, `${ch.id}-${slug(ch.titre)}.mp4`);
  ff([...inputs, "-filter_complex", filter, "-map", "[v]", "-r", String(FPS), "-c:v", "libx264", "-preset", "medium", "-crf", "19", "-pix_fmt", "yuv420p", "-movflags", "+faststart", file]);
  return { file, duration: TITLE + dur };
}

const slug = (s) => s.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/(^-|-$)/g, "");
const tc = (s) => `${String(Math.floor(s / 60)).padStart(2, "0")}:${String(Math.floor(s % 60)).padStart(2, "0")}`;

const browser = await launch();
const page = await (await browser.newContext({ viewport: { width: W, height: H }, deviceScaleFactor: 1 })).newPage();
const chapters = CHAPITRES.filter((c) => fs.existsSync(path.join(takes, c.id, "take.json")));
const made = [];
const script = ["# Tutoriels LDS Connect — script de la voix off", "", "Texte à enregistrer par une voix réelle, minuté sur chaque vidéo (le minutage inclut le carton de titre de 3 s). Les sous-titres à l'écran sont la version courte.", ""];
for (const [k, ch] of chapters.entries()) {
  const take = JSON.parse(fs.readFileSync(path.join(takes, ch.id, "take.json"), "utf8"));
  const dir = path.join(work, ch.id);
  fs.mkdirSync(dir, { recursive: true });
  await page.setViewportSize({ width: W, height: H });
  await render(page, background(ch, k + 1, chapters.length), path.join(dir, "fond.png"));
  await render(page, titleCard(ch, k + 1, chapters.length), path.join(dir, "titre.png"));
  for (const [i, c] of take.captions.entries()) await render(page, caption(ch, c.caption, i, take.captions.length), path.join(dir, `st-${i}.png`), true);
  screenVideo(take, ch, path.join(dir, "ecran.mp4"));
  const r = compose(ch, take, dir);
  made.push(r);
  console.log(`${path.basename(r.file)} : ${r.duration.toFixed(0)} s`);
  script.push(`## ${k + 1}. ${ch.titre} — ${ch.public}`, "", `Fichier : \`${path.basename(r.file)}\` (${tc(r.duration)})`, "", "| Début | À l'écran | Voix off |", "|---|---|---|");
  for (const c of take.captions) script.push(`| ${tc(TITLE + c.t)} | ${c.caption} | ${c.voice} |`);
  script.push("");
}
fs.writeFileSync(path.join(out, "SCRIPT_VOIX_OFF.md"), script.join("\n"));

// Version complète : ouverture, chapitres enchaînés, fermeture
for (const kind of ["intro", "outro"]) await render(page, bookend(kind), path.join(work, `${kind}.png`));
await browser.close();
const parts = [];
for (const kind of ["intro", "outro"]) {
  const f = path.join(work, `${kind}.mp4`);
  ff(["-loop", "1", "-t", "4", "-i", path.join(work, `${kind}.png`), "-vf", `fade=t=in:st=0:d=0.6,fade=t=out:st=3.4:d=0.6,fps=${FPS},format=yuv420p`, "-c:v", "libx264", "-crf", "19", f]);
  parts.push(f);
}
const list = [parts[0], ...made.map((m) => m.file), parts[1]].map((f) => `file '${f}'`).join("\n");
fs.writeFileSync(path.join(work, "complet.txt"), list);
ff(["-f", "concat", "-safe", "0", "-i", path.join(work, "complet.txt"), "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p", "-movflags", "+faststart", path.join(out, "00-tutoriel-complet.mp4")]);
console.log("00-tutoriel-complet.mp4 : prêt");
