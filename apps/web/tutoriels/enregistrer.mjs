// Enregistre les chapitres des tutoriels (pile locale lancée et données de démonstration).
// Usage : node tutoriels/enregistrer.mjs <dossier_de_sortie> [id du chapitre…]
import path from "node:path";
import { CHAPITRES } from "./chapitres.mjs";
import { launch, Take } from "./lib.mjs";

const out = process.argv[2] ?? "./tutoriels-sortie";
const only = process.argv.slice(3);
const browser = await launch();
try {
  for (const ch of CHAPITRES.filter((c) => !only.length || only.includes(c.id))) {
    const take = new Take(browser, { mobile: ch.mobile, out: path.join(out, ch.id) });
    await take.start();
    const started = Date.now();
    try {
      await ch.run(take);
    } catch (e) {
      console.error(`Chapitre ${ch.id} interrompu :`, e.message);
      await take.page.screenshot({ path: path.join(out, `${ch.id}-erreur.png`) }).catch(() => {});
      await take.stop();
      process.exitCode = 1;
      continue;
    }
    await take.stop();
    console.log(`${ch.id} : ${((Date.now() - started) / 1000).toFixed(0)} s, ${take.frames.length} images, ${take.captions.length} sous-titres`);
  }
} finally {
  await browser.close();
}
