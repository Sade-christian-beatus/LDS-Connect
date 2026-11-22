import { Suspense } from "react";
import { OrderView } from "./order-view";

export default function OrderPage({ params }: PageProps<"/billets/[reference]">) {
  return (
    <Suspense fallback={<p className="text-subtle">Chargement de vos billets…</p>}>
      <Resolve params={params} />
    </Suspense>
  );
}

async function Resolve({ params }: { params: PageProps<"/billets/[reference]">["params"] }) {
  const { reference } = await params;
  return <OrderView reference={reference} />;
}
