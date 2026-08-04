/** Kardex — historial de movimientos (FR-003-090, WF-03 solo consulta). */
import { useQuery } from "@tanstack/react-query";
import { createColumnHelper } from "@tanstack/react-table";
import { useState } from "react";

import { apiFetch } from "@/api/client";
import type { InventoryMovement, PagedResult } from "@/api/types";
import { DataTable } from "@/components/DataTable";
import { PageContent } from "@/layout/PageContent";
import { PageHeader } from "@/components/PageHeader";
import { SearchInput } from "@/components/SearchInput";

const columnHelper = createColumnHelper<InventoryMovement>();

export function KardexPage(): React.JSX.Element {
  const [search, setSearch] = useState("");

  const query = useQuery({
    queryKey: ["inventario", "kardex", search],
    queryFn: () => apiFetch<PagedResult<InventoryMovement>>(`/inventory/movements?q=${encodeURIComponent(search)}`),
    retry: false,
  });

  const columns = [
    columnHelper.accessor("occurred_at", {
      header: "Fecha",
      cell: (info) => new Date(info.getValue()).toLocaleString("es-VE"),
    }),
    columnHelper.accessor("product_id", { header: "Producto" }),
    columnHelper.accessor("movement_type_id", { header: "Tipo" }),
    columnHelper.accessor("quantity", {
      header: "Cantidad",
      cell: (info) => (info.getValue() > 0 ? `+${info.getValue()}` : `${info.getValue()}`),
    }),
    columnHelper.accessor("unit_cost", { header: "Costo unit." }),
    columnHelper.accessor("document_ref", { header: "Documento" }),
    columnHelper.accessor("status", { header: "Estado" }),
  ];

  return (
    <PageContent maxWidth="full">
      <PageHeader
        title="Kardex"
        description="Historial de movimientos de inventario (inmutable; reversos vinculados)."
        crumbs={[{ label: "Inventario" }, { label: "Kardex" }]}
      />
      <div className="mb-4">
        <SearchInput value={search} onChange={setSearch} placeholder="Buscar por documento…" />
      </div>
      <DataTable
        columns={columns}
        data={query.data?.items ?? []}
        loading={query.isLoading}
        error={query.isError ? "No fue posible cargar el kardex." : null}
        getRowId={(row) => row.id}
        emptyTitle="Sin movimientos"
        emptyDescription="No hay movimientos registrados para los filtros actuales."
      />
    </PageContent>
  );
}
