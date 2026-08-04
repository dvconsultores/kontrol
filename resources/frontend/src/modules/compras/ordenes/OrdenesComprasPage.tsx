/** Órdenes de compra — listado y transiciones (FR-004-020/021, WF-04). */
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { createColumnHelper } from "@tanstack/react-table";

import { apiFetch } from "@/api/client";
import type { PagedResult, PurchaseOrderSummary } from "@/api/types";
import { useNotifications } from "@/app/contexts/NotificationContext";
import { AsyncButton } from "@/components/AsyncButton";
import { DataTable } from "@/components/DataTable";
import { PageContent } from "@/layout/PageContent";
import { PageHeader } from "@/components/PageHeader";

const columnHelper = createColumnHelper<PurchaseOrderSummary>();

export function OrdenesComprasPage(): React.JSX.Element {
  const queryClient = useQueryClient();
  const { notify } = useNotifications();

  const query = useQuery({
    queryKey: ["compras", "ordenes"],
    queryFn: () => apiFetch<PagedResult<PurchaseOrderSummary>>("/purchasing/orders"),
    retry: false,
  });

  const runTransition = async (id: string, target: string): Promise<void> => {
    await apiFetch(`/purchasing/orders/${id}/transition`, { method: "POST", body: { target } });
    await queryClient.invalidateQueries({ queryKey: ["compras", "ordenes"] });
    notify({ type: "success", title: "Orden actualizada", description: `Estado → ${target}` });
  };

  const columns = [
    columnHelper.accessor("code", { header: "Código" }),
    columnHelper.accessor("supplier_id", { header: "Proveedor" }),
    columnHelper.accessor("currency", { header: "Moneda" }),
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
          ["cancel", "CANCELLED"],
          ["close", "CLOSED"],
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
        title="Órdenes de compra"
        description="Órdenes con aprobación y totales por moneda (no sustituyen recepción ni factura)."
        crumbs={[{ label: "Compras" }, { label: "Órdenes" }]}
      />
      <DataTable
        columns={columns}
        data={query.data?.items ?? []}
        loading={query.isLoading}
        error={query.isError ? "No fue posible cargar las órdenes." : null}
        getRowId={(row) => row.id}
        emptyTitle="Sin órdenes"
        emptyDescription="Aún no hay órdenes de compra registradas."
      />
    </PageContent>
  );
}
