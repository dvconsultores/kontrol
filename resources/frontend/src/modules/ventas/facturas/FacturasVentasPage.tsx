/** Facturas de venta — base VES, tasa snapshot y estados (FR-005-030/031, WF-04). */
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { createColumnHelper } from "@tanstack/react-table";

import { apiFetch } from "@/api/client";
import type { PagedResult, SalesInvoiceSummary } from "@/api/types";
import { useNotifications } from "@/app/contexts/NotificationContext";
import { AsyncButton } from "@/components/AsyncButton";
import { DataTable } from "@/components/DataTable";
import { PageContent } from "@/layout/PageContent";
import { PageHeader } from "@/components/PageHeader";

const columnHelper = createColumnHelper<SalesInvoiceSummary>();

export function FacturasVentasPage(): React.JSX.Element {
  const queryClient = useQueryClient();
  const { notify } = useNotifications();

  const query = useQuery({
    queryKey: ["ventas", "facturas"],
    queryFn: () => apiFetch<PagedResult<SalesInvoiceSummary>>("/sales/invoices"),
    retry: false,
  });

  const runTransition = async (id: string, target: string): Promise<void> => {
    await apiFetch(`/sales/invoices/${id}/transition`, { method: "POST", body: { target } });
    await queryClient.invalidateQueries({ queryKey: ["ventas", "facturas"] });
    notify({ type: "success", title: "Factura actualizada", description: `Estado → ${target}` });
  };

  const columns = [
    columnHelper.accessor("invoice_number", { header: "Factura" }),
    columnHelper.accessor("customer_id", { header: "Cliente" }),
    columnHelper.accessor("base_fiscal", { header: "Base VES" }),
    columnHelper.accessor("tax_total", { header: "IVA" }),
    columnHelper.accessor("total", { header: "Total" }),
    columnHelper.accessor("status", { header: "Estado" }),
    columnHelper.display({
      id: "actions",
      header: "Acciones",
      cell: ({ row }) => {
        const a = row.original.allowed_actions;
        const transitions: Array<[string, string]> = [
          ["validate", "VALIDATED"],
          ["approve", "APPROVED"],
          ["emit", "EMITTED"],
          ["deliver", "DELIVERED"],
          ["void", "VOIDED"],
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
        title="Facturas de venta"
        description="Documento comercial con base fiscal en VES y tasa snapshot (emisión fiscal en Spec 007)."
        crumbs={[{ label: "Ventas" }, { label: "Facturas" }]}
      />
      <DataTable
        columns={columns}
        data={query.data?.items ?? []}
        loading={query.isLoading}
        error={query.isError ? "No fue posible cargar las facturas." : null}
        getRowId={(row) => row.id}
        emptyTitle="Sin facturas"
        emptyDescription="Aún no hay facturas de venta registradas."
      />
    </PageContent>
  );
}
