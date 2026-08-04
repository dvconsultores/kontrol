/** Ajustes — motivo/evidencia/aprobación (FR-003-072/073, WF-02). */
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { createColumnHelper } from "@tanstack/react-table";

import { apiFetch } from "@/api/client";
import type { InventoryAdjustment, PagedResult } from "@/api/types";
import { useNotifications } from "@/app/contexts/NotificationContext";
import { AsyncButton } from "@/components/AsyncButton";
import { DataTable } from "@/components/DataTable";
import { PageContent } from "@/layout/PageContent";
import { PageHeader } from "@/components/PageHeader";

const columnHelper = createColumnHelper<InventoryAdjustment>();

export function AjustesPage(): React.JSX.Element {
  const queryClient = useQueryClient();
  const { notify } = useNotifications();

  const query = useQuery({
    queryKey: ["inventario", "ajustes"],
    queryFn: () => apiFetch<PagedResult<InventoryAdjustment>>("/inventory/adjustments"),
    retry: false,
  });

  const runTransition = async (id: string, target: string): Promise<void> => {
    await apiFetch(`/inventory/adjustments/${id}/transition`, { method: "POST", body: { target } });
    await queryClient.invalidateQueries({ queryKey: ["inventario", "ajustes"] });
    notify({ type: "success", title: "Ajuste actualizado", description: `Estado → ${target}` });
  };

  const columns = [
    columnHelper.accessor("product_id", { header: "Producto" }),
    columnHelper.accessor("quantity", { header: "Cantidad" }),
    columnHelper.accessor("reason", { header: "Motivo" }),
    columnHelper.accessor("unit_cost", { header: "Costo unit." }),
    columnHelper.accessor("status", { header: "Estado" }),
    columnHelper.display({
      id: "actions",
      header: "Acciones",
      cell: ({ row }) => {
        const a = row.original.allowed_actions;
        const transitions: Array<[string, string]> = [
          ["submit", "SUBMITTED"],
          ["approve", "APPROVED"],
          ["reject", "REJECTED"],
          ["apply", "APPLIED"],
        ];
        return (
          <div className="flex justify-end gap-1">
            {transitions
              .filter(([key]) => a[key])
              .map(([key, target]) => (
                <AsyncButton key={key} size="sm" variant="secondary" onClick={() => runTransition(row.original.id, target)}>
                  {key}
                </AsyncButton>
              ))}
          </div>
        );
      },
    }),
  ];

  return (
    <PageContent maxWidth="full">
      <PageHeader
        title="Ajustes de inventario"
        description="Ajustes con motivo, evidencia y aprobación. Nunca editan el saldo: generan movimientos."
        crumbs={[{ label: "Inventario" }, { label: "Ajustes" }]}
      />
      <DataTable
        columns={columns}
        data={query.data?.items ?? []}
        loading={query.isLoading}
        error={query.isError ? "No fue posible cargar los ajustes." : null}
        getRowId={(row) => row.id}
        emptyTitle="Sin ajustes"
        emptyDescription="Aún no hay ajustes registrados."
      />
    </PageContent>
  );
}
