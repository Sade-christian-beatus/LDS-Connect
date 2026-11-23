"use client";
// Envoi d'un logo : l'image est redimensionnée dans le navigateur (512 px au plus, PNG) avant
// l'envoi, pour rester légère sur les réseaux mobiles.
import { useRef, useState } from "react";
import { Button } from "./ui";

const MAX = 512;

async function toPng(file: File): Promise<Blob> {
  const url = URL.createObjectURL(file);
  try {
    const img = await new Promise<HTMLImageElement>((resolve, reject) => {
      const i = new Image();
      i.onload = () => resolve(i);
      i.onerror = () => reject(new Error("Image illisible : choisissez un fichier PNG, JPEG ou WebP"));
      i.src = url;
    });
    const scale = Math.min(1, MAX / Math.max(img.naturalWidth, img.naturalHeight));
    const canvas = document.createElement("canvas");
    canvas.width = Math.round(img.naturalWidth * scale);
    canvas.height = Math.round(img.naturalHeight * scale);
    canvas.getContext("2d")!.drawImage(img, 0, 0, canvas.width, canvas.height);
    return await new Promise<Blob>((resolve, reject) =>
      canvas.toBlob((b) => (b ? resolve(b) : reject(new Error("Conversion impossible"))), "image/png"),
    );
  } finally {
    URL.revokeObjectURL(url);
  }
}

export function LogoUploader({
  label,
  currentUrl,
  upload,
  remove,
  onDone,
  onError,
  preview,
}: {
  label: string;
  currentUrl: string | null | undefined;
  upload: (body: FormData) => Promise<unknown>;
  remove: () => Promise<unknown>;
  onDone: (text: string) => void;
  onError: (text: string) => void;
  preview?: React.ReactNode;
}) {
  const input = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState(false);

  async function send(file: File) {
    setBusy(true);
    try {
      const png = await toPng(file);
      const body = new FormData();
      body.append("file", png, "logo.png");
      await upload(body);
      onDone("Logo enregistré");
    } catch (e) {
      onError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
      if (input.current) input.current.value = "";
    }
  }

  return (
    <div className="flex flex-wrap items-center gap-4">
      <div className="flex h-24 w-24 items-center justify-center rounded-xl border border-dashed border-stone-300 bg-white p-2">
        {preview ??
          (currentUrl ? (
            // eslint-disable-next-line @next/next/no-img-element -- aperçu du logo servi par l'API
            <img src={currentUrl} alt="Logo actuel" className="max-h-full max-w-full object-contain" />
          ) : (
            <span className="text-center text-xs text-stone-400">Aucun logo</span>
          ))}
      </div>
      <div className="space-y-2">
        <input
          ref={input}
          type="file"
          accept="image/png,image/jpeg,image/webp"
          aria-label={label}
          className="hidden"
          onChange={(e) => e.target.files?.[0] && send(e.target.files[0])}
        />
        <div className="flex flex-wrap gap-2">
          <Button disabled={busy} onClick={() => input.current?.click()}>
            {busy ? "Envoi…" : currentUrl ? "Remplacer le logo" : "Envoyer un logo"}
          </Button>
          {currentUrl && (
            <Button
              variant="secondary"
              disabled={busy}
              onClick={async () => {
                setBusy(true);
                try {
                  await remove();
                  onDone("Logo retiré");
                } catch (e) {
                  onError(e instanceof Error ? e.message : String(e));
                } finally {
                  setBusy(false);
                }
              }}
            >
              Retirer
            </Button>
          )}
        </div>
        <p className="text-xs text-stone-500">PNG, JPEG ou WebP ; fond transparent ou blanc de préférence. Redimensionné à 512 px.</p>
      </div>
    </div>
  );
}
