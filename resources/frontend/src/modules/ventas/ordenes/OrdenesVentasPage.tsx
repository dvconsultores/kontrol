/** Órdenes de venta — crédito, reserva y transiciones (FR-005-011/012, WF-04). */
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { createColumnHelper } from "@tanstack/react-table";

import { apiFetch } from "@/api/client";
import type { PagedResult, SalesOrderSummary } from "@/api/types";
import { useNotifications } from "@/app/contexts/NotificationContext";
import { AsyncButton } from "@/components/AsyncButton";
import { DataTable } from "@/components/DataTable";
import { PageContent } from "@/layout/PageContent";
import { PageHeader } from "@/components/PageHeader";

const columnHelper = createColumnHelper<SalesOrderSummary>();

export function OrdenesVentasPage(): React.JSX.Element {
  const queryClient = useQueryClient();
  const { notify } = useNotifications();

  const query = useQuery({
    queryKey: ["ventas", "ordenes"],
    queryFn: () => apiFetch<PagedResult<SalesOrderSummary>>("/sales/orders"),
    retry: false,
  });

  const runTransition = async (id: string, target: string): Promise<void> => {
    await apiFetch(`/sales/orders/${id}/transition`, { method: "POST", body: { target } });
    await queryClient.invalidateQueries({ queryKey: ["ventas", "ordenes"] });
    notify({ type: "success", title: "Orden actualizada", description: `Estado → ${target}` });
  };

  const columns = [
    columnHelper.accessor("code", { header: "Código" }),
    columnHelper.accessor("customer_id", { header: "Cliente" }),
    columnHelper.accessor("margin", { header: "Margen" }),
    columnHelper.accessor("status", { header: "Estado" }),
    columnHelper.display({
      id: "actions",
      header: "Acciones",
      cell: ({ row }) => {
        const a = row.original.allowed_actions;
        const transitions: Array<[string, string]> = [
          ["submit", "SUBMITTED"],
          ["credit", "CREDIT_PENDING"],
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
        title="Órdenes de venta"
        description="Crédito, margen y reserva separados. Al aprobar se reserva inventario."
        crumbs={[{ label: "Ventas" }, { label: "Órdenes" }]}
      />
      <DataTable
        columns={columns}
        data={query.data?.items ?? []}
        loading={query.isLoading}
        error={query.isError ? "No fue posible cargar las órdenes." : null}
        getRowId={(row) => row.id}
        emptyTitle="Sin órdenes"
        emptyDescription="Aún no hay órdenes de venta registradas."
      />
    </PageContent>
  );
}
