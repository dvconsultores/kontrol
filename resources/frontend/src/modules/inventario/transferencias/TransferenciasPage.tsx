/** Transferencias — listado y transiciones de estado (FR-003-060/061, WF-04). */
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { createColumnHelper } from "@tanstack/react-table";

import { apiFetch } from "@/api/client";
import type { PagedResult, TransferSummary } from "@/api/types";
import { useNotifications } from "@/app/contexts/NotificationContext";
import { AsyncButton } from "@/components/AsyncButton";
import { DataTable } from "@/components/DataTable";
import { PageContent } from "@/layout/PageContent";
import { PageHeader } from "@/components/PageHeader";

const columnHelper = createColumnHelper<TransferSummary>();

export function TransferenciasPage(): React.JSX.Element {
  const queryClient = useQueryClient();
  const { notify } = useNotifications();

  const query = useQuery({
    queryKey: ["inventario", "transferencias"],
    queryFn: () => apiFetch<PagedResult<TransferSummary>>("/inventory/transfers"),
    retry: false,
  });

  const runTransition = async (id: string, target: string): Promise<void> => {
    await apiFetch(`/inventory/transfers/${id}/transition`, { method: "POST", body: { target } });
    await queryClient.invalidateQueries({ queryKey: ["inventario", "transferencias"] });
    notify({ type: "success", title: "Transferencia actualizada", description: `Estado → ${target}` });
  };

  const columns = [
    columnHelper.accessor("code", { header: "Código" }),
    columnHelper.accessor("origin_warehouse_id", { header: "Origen" }),
    columnHelper.accessor("destination_warehouse_id", { header: "Destino" }),
    columnHelper.accessor("status", { header: "Estado" }),
    columnHelper.display({
      id: "actions",
      header: "Acciones",
      cell: ({ row }) => {
        const a = row.original.allowed_actions;
        const transitions: Array<[string, string]> = [
          ["submit", "SUBMITTED"],
          ["approve", "APPROVED"],
          ["confirm_ship", "IN_TRANSIT"],
          ["confirm_receipt", "RECEIVED"],
          ["close", "CLOSED"],
        ];
        return (
          <div className="flex justify-end gap-1">
            {transitions
              .filter(([key]) => a[key])
              .map(([key, target]) => (
                <AsyncButton key={key} size="sm" variant="secondary" onClick={() => runTransition(row.original.id, target)}>
                  {key.replace("_", " ")}
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
        title="Transferencias"
        description="Movimiento de mercancía entre almacenes con máquina de estados."
        crumbs={[{ label: "Inventario" }, { label: "Transferencias" }]}
      />
      <DataTable
        columns={columns}
        data={query.data?.items ?? []}
        loading={query.isLoading}
        error={query.isError ? "No fue posible cargar las transferencias." : null}
        getRowId={(row) => row.id}
        emptyTitle="Sin transferencias"
        emptyDescription="Aún no hay transferencias registradas."
      />
    </PageContent>
  );
}
