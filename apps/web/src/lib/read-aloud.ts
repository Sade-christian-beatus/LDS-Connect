// Lecture à voix haute du contenu d'une page (« Écouter la page ») : découpe le contenu
// principal en passages, dans l'ordre de lecture, avec les textes prévus pour les lecteurs
// d'écran (« 1 à 0, en direct ») et sans ce qui leur est masqué (affichage compact, décor).

export type Passage = { el: HTMLElement; text: string };

const BLOCKS = new Set(["H1", "H2", "H3", "H4", "H5", "H6", "P", "LI", "DT", "DD", "BLOCKQUOTE", "FIGCAPTION", "LEGEND", "LABEL", "A"]);
const SKIP = new Set(["SCRIPT", "STYLE", "NOSCRIPT", "TEMPLATE", "BUTTON", "INPUT", "SELECT", "TEXTAREA", "NAV", "IFRAME", "VIDEO", "AUDIO", "CANVAS"]);
const INLINE = new Set(["inline", "inline-block", "inline-flex", "contents"]);
const MAX = 220; // au-delà, certaines voix s'arrêtent en cours de phrase : passage découpé

function hidden(el: Element): boolean {
  if (SKIP.has(el.tagName)) return true;
  if (el.getAttribute("aria-hidden") === "true" || (el as HTMLElement).hidden) return true;
  if (el.closest("[data-read-aloud-skip]")) return true;
  const s = getComputedStyle(el);
  return s.display === "none" || s.visibility === "hidden";
}

/** Texte d'un élément tel qu'il doit être entendu. */
function textOf(node: Node): string {
  if (node.nodeType === Node.TEXT_NODE) return node.textContent ?? "";
  if (node.nodeType !== Node.ELEMENT_NODE) return "";
  const el = node as Element;
  if (hidden(el)) return "";
  if (el.tagName === "IMG") return (el as HTMLImageElement).alt ? ` ${(el as HTMLImageElement).alt} ` : "";
  if (el.getAttribute("role") === "img") return el.getAttribute("aria-label") ? ` ${el.getAttribute("aria-label")} ` : "";
  if (el.tagName === "svg" || el.tagName === "SVG") return "";
  let out = "";
  for (const child of Array.from(el.childNodes)) {
    const t = textOf(child);
    // Deux éléments mis en page côte à côte se lisent avec une courte pause
    const block = child.nodeType === Node.ELEMENT_NODE && !INLINE.has(getComputedStyle(child as Element).display);
    out += block && t.trim() ? ` ${t.trim()}, ` : t;
  }
  return out;
}

const clean = (t: string) =>
  t
    .replace(/[←→↑↓↗★●]/g, " ") // signes décoratifs, lus « flèche droite » par certaines voix
    .replace(/\s+·\s+/g, ", ")
    .replace(/\s+/g, " ")
    .replace(/\s+([,.;:!?])/g, "$1")
    .replace(/([,;])(\s*[,;])+/g, "$1")
    .replace(/^[\s,;]+|[\s,;]+$/g, "")
    .trim();

function hasBlockChild(el: Element): boolean {
  for (const child of Array.from(el.children)) {
    if (hidden(child)) continue;
    if (BLOCKS.has(child.tagName) || child.tagName === "TABLE") return true;
    if (!INLINE.has(getComputedStyle(child).display)) return true;
  }
  return false;
}

/** Une ligne de tableau se lit avec le nom de chaque colonne : « Rang 1, Équipe Vinnim, Points 6 ». */
function tableRows(table: HTMLTableElement, push: (el: HTMLElement, t: string) => void) {
  const caption = table.caption ? clean(textOf(table.caption)) : "";
  if (caption) push(table, caption);
  const heads = Array.from(table.tHead?.rows[0]?.cells ?? []).map((c) => (hidden(c) ? null : clean(textOf(c))));
  for (const body of Array.from(table.tBodies)) {
    for (const row of Array.from(body.rows)) {
      const parts = Array.from(row.cells).map((cell, i) => {
        if (hidden(cell)) return "";
        const value = clean(textOf(cell));
        const head = heads[i];
        return value && head && head !== value ? `${head} ${value}` : value;
      });
      push(row, parts.filter(Boolean).join(", "));
    }
  }
}

/** Découpe un passage trop long aux fins de phrase, puis aux virgules. */
function split(text: string): string[] {
  if (text.length <= MAX) return [text];
  const out: string[] = [];
  let cur = "";
  for (const piece of text.split(/(?<=[.!?;:])\s+|(?<=,)\s+/)) {
    if (cur && (cur + " " + piece).length > MAX) {
      out.push(cur);
      cur = piece;
    } else cur = cur ? `${cur} ${piece}` : piece;
  }
  if (cur) out.push(cur);
  // Pas de fin de passage réduite à un mot : rattachée au passage précédent
  if (out.length > 1 && out[out.length - 1].length < 60) {
    const tail = out.pop()!;
    out[out.length - 1] += ` ${tail}`;
  }
  return out;
}

export function passages(root: HTMLElement): Passage[] {
  const out: Passage[] = [];
  const push = (el: HTMLElement, raw: string) => {
    const text = clean(raw);
    if (text) for (const part of split(text)) out.push({ el, text: part });
  };
  const walk = (el: HTMLElement) => {
    if (hidden(el)) return;
    if (el.tagName === "TABLE") return tableRows(el as HTMLTableElement, push);
    if (BLOCKS.has(el.tagName) || !hasBlockChild(el)) return push(el, textOf(el));
    for (const child of Array.from(el.childNodes)) {
      if (child.nodeType === Node.ELEMENT_NODE) walk(child as HTMLElement);
      else if (child.nodeType === Node.TEXT_NODE && child.textContent?.trim()) push(el, child.textContent);
    }
  };
  walk(root);
  return out;
}

/** Voix française de l'appareil, si elle existe (sinon la voix par défaut, réglée en français). */
export function frenchVoice(): SpeechSynthesisVoice | null {
  const voices = window.speechSynthesis.getVoices();
  return (
    voices.find((v) => v.lang === "fr-FR" && v.localService) ??
    voices.find((v) => v.lang === "fr-FR") ??
    voices.find((v) => v.lang.toLowerCase().startsWith("fr")) ??
    null
  );
}
