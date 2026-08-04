/** Facturas del proveedor — duplicidad y estados (FR-004-040/041/042, WF-04). */
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { createColumnHelper } from "@tanstack/react-table";

import { apiFetch } from "@/api/client";
import type { PagedResult, SupplierInvoiceSummary } from "@/api/types";
import { useNotifications } from "@/app/contexts/NotificationContext";
import { AsyncButton } from "@/components/AsyncButton";
import { DataTable } from "@/components/DataTable";
import { PageContent } from "@/layout/PageContent";
import { PageHeader } from "@/components/PageHeader";

const columnHelper = createColumnHelper<SupplierInvoiceSummary>();

export function FacturasProveedorPage(): React.JSX.Element {
  const queryClient = useQueryClient();
  const { notify } = useNotifications();

  const query = useQuery({
    queryKey: ["compras", "facturas"],
    queryFn: () => apiFetch<PagedResult<SupplierInvoiceSummary>>("/purchasing/supplier-invoices"),
    retry: false,
  });

  const runTransition = async (id: string, target: string): Promise<void> => {
    await apiFetch(`/purchasing/supplier-invoices/${id}/transition`, { method: "POST", body: { target } });
    await queryClient.invalidateQueries({ queryKey: ["compras", "facturas"] });
    notify({ type: "success", title: "Factura actualizada", description: `Estado → ${target}` });
  };

  const columns = [
    columnHelper.accessor("invoice_number", { header: "Factura" }),
    columnHelper.accessor("control_number", { header: "Control" }),
    columnHelper.accessor("supplier_id", { header: "Proveedor" }),
    columnHelper.accessor("total", { header: "Total" }),
    columnHelper.accessor("status", { header: "Estado" }),
    columnHelper.display({
      id: "actions",
      header: "Acciones",
      cell: ({ row }) => {
        const a = row.original.allowed_actions;
        const transitions: Array<[string, string]> = [
          ["validate", "VALIDATED"],
          ["match", "MATCHED"],
          ["approve", "APPROVED"],
          ["post", "POSTED"],
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
        title="Facturas del proveedor"
        description="Registro con validación de duplicidad y conciliación previa a postear."
        crumbs={[{ label: "Compras" }, { label: "Facturas" }]}
      />
      <DataTable
        columns={columns}
        data={query.data?.items ?? []}
        loading={query.isLoading}
        error={query.isError ? "No fue posible cargar las facturas." : null}
        getRowId={(row) => row.id}
        emptyTitle="Sin facturas"
        emptyDescription="Aún no hay facturas de proveedor registradas."
      />
    </PageContent>
  );
}
