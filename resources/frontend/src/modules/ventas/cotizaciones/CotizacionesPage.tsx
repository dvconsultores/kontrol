/** Cotizaciones — sin reserva de inventario (FR-005-001, WF-02). */
import { useQuery } from "@tanstack/react-query";
import { createColumnHelper } from "@tanstack/react-table";

import { apiFetch } from "@/api/client";
import type { SalesQuoteSummary } from "@/api/types";
import { DataTable } from "@/components/DataTable";
import { PageContent } from "@/layout/PageContent";
import { PageHeader } from "@/components/PageHeader";

const columnHelper = createColumnHelper<SalesQuoteSummary>();

export function CotizacionesPage(): React.JSX.Element {
  const query = useQuery({
    queryKey: ["ventas", "cotizaciones"],
    queryFn: () => apiFetch<{ items: SalesQuoteSummary[] }>("/sales/quotes"),
    retry: false,
  });

  const columns = [
    columnHelper.accessor("code", { header: "Código" }),
    columnHelper.accessor("customer_id", { header: "Cliente" }),
    columnHelper.accessor("currency", { header: "Moneda" }),
    columnHelper.accessor("status", { header: "Estado" }),
  ];

  return (
    <PageContent maxWidth="full">
      <PageHeader
        title="Cotizaciones"
        description="Cotizaciones de venta sin reservar inventario."
        crumbs={[{ label: "Ventas" }, { label: "Cotizaciones" }]}
      />
      <DataTable
        columns={columns}
        data={query.data?.items ?? []}
        loading={query.isLoading}
        error={query.isError ? "No fue posible cargar las cotizaciones." : null}
        getRowId={(row) => row.id}
        emptyTitle="Sin cotizaciones"
        emptyDescription="Aún no hay cotizaciones registradas."
      />
    </PageContent>
  );
}
