/** Recepciones — confirmación, calidad y aceptación (FR-004-030/032, WF-04). */
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { createColumnHelper } from "@tanstack/react-table";

import { apiFetch } from "@/api/client";
import type { GoodsReceiptSummary } from "@/api/types";
import { useNotifications } from "@/app/contexts/NotificationContext";
import { AsyncButton } from "@/components/AsyncButton";
import { DataTable } from "@/components/DataTable";
import { PageContent } from "@/layout/PageContent";
import { PageHeader } from "@/components/PageHeader";

const columnHelper = createColumnHelper<GoodsReceiptSummary>();

export function RecepcionesPage(): React.JSX.Element {
  const queryClient = useQueryClient();
  const { notify } = useNotifications();

  const query = useQuery({
    queryKey: ["compras", "recepciones"],
    queryFn: () => apiFetch<{ items: GoodsReceiptSummary[] }>("/purchasing/receipts"),
    retry: false,
  });

  const runAction = async (id: string, action: string, body?: unknown): Promise<void> => {
    await apiFetch(`/purchasing/receipts/${id}/${action}`, { method: "POST", body });
    await queryClient.invalidateQueries({ queryKey: ["compras", "recepciones"] });
    notify({ type: "success", title: "Recepción actualizada", description: `Acción: ${action}` });
  };

  const columns = [
    columnHelper.accessor("code", { header: "Código" }),
    columnHelper.accessor("order_id", { header: "Orden" }),
    columnHelper.accessor("warehouse_id", { header: "Almacén" }),
    columnHelper.accessor("status", { header: "Estado" }),
    columnHelper.accessor("quality_status", { header: "Calidad" }),
    columnHelper.display({
      id: "actions",
      header: "Acciones",
      cell: ({ row }) => {
        const r = row.original;
        return (
          <div className="flex justify-end gap-1">
            {r.status === "DRAFT" ? (
              <AsyncButton size="sm" variant="secondary" onClick={() => runAction(r.id, "confirm")}>
                confirmar
              </AsyncButton>
            ) : null}
            {r.status === "CONFIRMED" && r.quality_status !== "APPROVED" ? (
              <AsyncButton size="sm" variant="secondary" onClick={() => runAction(r.id, "quality", { quality_status: "APPROVED" })}>
                aprobar calidad
              </AsyncButton>
            ) : null}
            {r.status === "CONFIRMED" && r.quality_status === "APPROVED" ? (
              <AsyncButton size="sm" variant="secondary" onClick={() => runAction(r.id, "accept")}>
                aceptar
              </AsyncButton>
            ) : null}
          </div>
        );
      },
    }),
  ];

  return (
    <PageContent maxWidth="full">
      <PageHeader
        title="Recepciones"
        description="Recibir contra orden: lotes, seriales, vencimientos y calidad (integra inventario)."
        crumbs={[{ label: "Compras" }, { label: "Recepciones" }]}
      />
      <DataTable
        columns={columns}
        data={query.data?.items ?? []}
        loading={query.isLoading}
        error={query.isError ? "No fue posible cargar las recepciones." : null}
        getRowId={(row) => row.id}
        emptyTitle="Sin recepciones"
        emptyDescription="Aún no hay recepciones registradas."
      />
    </PageContent>
  );
}
