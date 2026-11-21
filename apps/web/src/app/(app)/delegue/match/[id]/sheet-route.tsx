"use client";
import { useParams } from "next/navigation";
import { RequireAuth } from "@/components/RequireAuth";
import { SheetScreen } from "@/components/delegate/SheetScreen";

export function SheetRoute() {
  const { id } = useParams<{ id: string }>();
  return (
    <RequireAuth permission="sheet:edit">
      <SheetScreen matchId={id} />
    </RequireAuth>
  );
}
