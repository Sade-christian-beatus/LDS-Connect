"use client";
// Image réservée aux comptes habilités (photo de licence) : demandée avec le jeton de session,
// affichée depuis la mémoire du navigateur, jamais mise en cache sur l'appareil.
import { useEffect, useState } from "react";
import { NetworkError, useAuth } from "@/lib/auth";

export type PrivateImage = { url: string | null; state: "loading" | "ready" | "none" | "offline" };

export function usePrivateImage(path: string | null, version = 0): PrivateImage {
  const { raw } = useAuth();
  const [image, setImage] = useState<PrivateImage>({ url: null, state: path ? "loading" : "none" });

  useEffect(() => {
    if (!path) return;
    let url: string | null = null;
    let active = true;
    Promise.resolve().then(() => active && setImage({ url: null, state: "loading" }));
    raw(path)
      .then((r) => r.blob())
      .then((b) => {
        if (!active) return;
        url = URL.createObjectURL(b);
        setImage({ url, state: "ready" });
      })
      .catch((e: Error) => {
        if (active) setImage({ url: null, state: e instanceof NetworkError ? "offline" : "none" });
      });
    return () => {
      active = false;
      if (url) URL.revokeObjectURL(url);
    };
  }, [path, version, raw]);

  return path ? image : { url: null, state: "none" };
}
