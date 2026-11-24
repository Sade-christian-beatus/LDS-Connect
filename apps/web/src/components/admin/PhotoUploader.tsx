"use client";
// Photo d'identité de la licence : recadrée au format portrait (3:4) et compressée en JPEG dans
// le navigateur avant l'envoi. Privée : jamais affichée sur le site public.
import { useRef, useState } from "react";
import { Button } from "./ui";

const W = 450;
const H = 600;

async function toPortraitJpeg(file: File): Promise<Blob> {
  const url = URL.createObjectURL(file);
  try {
    const img = await new Promise<HTMLImageElement>((resolve, reject) => {
      const i = new Image();
      i.onload = () => resolve(i);
      i.onerror = () => reject(new Error("Image illisible : choisissez une photo JPEG, PNG ou WebP"));
      i.src = url;
    });
    // Recadrage centré au format 3:4 (photo d'identité)
    const ratio = W / H;
    let sw = img.naturalWidth;
    let sh = img.naturalHeight;
    if (sw / sh > ratio) sw = sh * ratio;
    else sh = sw / ratio;
    const sx = (img.naturalWidth - sw) / 2;
    const sy = (img.naturalHeight - sh) / 2;
    const canvas = document.createElement("canvas");
    canvas.width = W;
    canvas.height = H;
    const ctx = canvas.getContext("2d")!;
    ctx.fillStyle = "#fff";
    ctx.fillRect(0, 0, W, H);
    ctx.drawImage(img, sx, sy, sw, sh, 0, 0, W, H);
    return await new Promise<Blob>((resolve, reject) =>
      canvas.toBlob((b) => (b ? resolve(b) : reject(new Error("Conversion impossible"))), "image/jpeg", 0.85),
    );
  } finally {
    URL.revokeObjectURL(url);
  }
}

export function PhotoUploader({
  hasPhoto,
  needsConsent,
  upload,
  remove,
  onDone,
  onError,
}: {
  hasPhoto: boolean;
  needsConsent: boolean;
  upload: (body: FormData) => Promise<unknown>;
  remove: () => Promise<unknown>;
  onDone: (text: string) => void;
  onError: (text: string) => void;
}) {
  const input = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState(false);

  async function run(fn: () => Promise<unknown>, ok: string) {
    setBusy(true);
    try {
      await fn();
      onDone(ok);
    } catch (e) {
      onError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
      if (input.current) input.current.value = "";
    }
  }

  if (needsConsent) {
    return (
      <p className="rounded bg-amber-50 p-2 text-xs text-amber-900">
        Joueur mineur : enregistrez la date de l&apos;autorisation parentale (bouton « Modifier ») avant d&apos;ajouter une
        photo.
      </p>
    );
  }
  return (
    <div className="flex flex-wrap items-center gap-2">
      <input
        ref={input}
        type="file"
        accept="image/jpeg,image/png,image/webp"
        capture="user"
        aria-label="Photo d'identité"
        className="hidden"
        onChange={(e) => {
          const file = e.target.files?.[0];
          if (!file) return;
          run(async () => {
            const body = new FormData();
            body.append("file", await toPortraitJpeg(file), "photo.jpg");
            await upload(body);
          }, "Photo enregistrée");
        }}
      />
      <Button variant="secondary" disabled={busy} onClick={() => input.current?.click()}>
        {busy ? "Envoi…" : hasPhoto ? "Changer la photo" : "Ajouter une photo"}
      </Button>
      {hasPhoto && (
        <Button variant="secondary" disabled={busy} onClick={() => run(remove, "Photo retirée")}>
          Retirer la photo
        </Button>
      )}
      <p className="w-full text-xs text-stone-500">Photo d&apos;identité récente, visage dégagé. Visible seulement par le club, la Ligue et les contrôleurs.</p>
    </div>
  );
}
