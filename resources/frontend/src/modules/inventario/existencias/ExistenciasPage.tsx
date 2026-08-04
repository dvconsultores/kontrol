/** Existencias — saldos con filtros (FR-003-010/012, WF-01). */
import { useQuery } from "@tanstack/react-query";
import { createColumnHelper } from "@tanstack/react-table";
import { useState } from "react";

import { apiFetch } from "@/api/client";
import type { InventoryBalance, PagedResult } from "@/api/types";
import { DataTable } from "@/components/DataTable";
import { PageContent } from "@/layout/PageContent";
import { PageHeader } from "@/components/PageHeader";
import { SearchInput } from "@/components/SearchInput";

const columnHelper = createColumnHelper<InventoryBalance>();

export function ExistenciasPage(): React.JSX.Element {
  const [search, setSearch] = useState("");

  const query = useQuery({
    queryKey: ["inventario", "existencias", search],
    queryFn: () => apiFetch<PagedResult<InventoryBalance>>(`/inventory/balances?q=${encodeURIComponent(search)}`),
    retry: false,
  });

  const columns = [
    columnHelper.accessor("product_id", { header: "Producto" }),
    columnHelper.accessor("warehouse_id", { header: "Almacén" }),
    columnHelper.accessor("lot_id", { header: "Lote" }),
    columnHelper.accessor("state", { header: "Estado" }),
    columnHelper.accessor("qty_on_hand", { header: "Físico" }),
    columnHelper.accessor("qty_reserved", { header: "Reservado" }),
    columnHelper.accessor("qty_available", { header: "Disponible" }),
  ];

  return (
    <PageContent maxWidth="full">
      <PageHeader
        title="Existencias"
        description="Saldos por producto, almacén, lote y estado (disponible = físico − reservas)."
        crumbs={[{ label: "Inventario" }, { label: "Existencias" }]}
      />
      <div className="mb-4">
        <SearchInput value={search} onChange={setSearch} placeholder="Buscar por producto…" />
      </div>
      <DataTable
        columns={columns}
        data={query.data?.items ?? []}
        loading={query.isLoading}
        error={query.isError ? "No fue posible cargar las existencias." : null}
        getRowId={(row) => row.id}
        emptyTitle="Sin existencias"
        emptyDescription="No hay saldos registrados para los filtros actuales."
      />
    </PageContent>
  );
}
