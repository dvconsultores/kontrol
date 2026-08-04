/** Servicios — listado (FR-002-022, WF-01). Los servicios no usan inventario. */
import { useQuery } from "@tanstack/react-query";
import { createColumnHelper } from "@tanstack/react-table";
import { useState } from "react";

import { apiFetch } from "@/api/client";
import type { CatalogItemSummary, PagedResult } from "@/api/types";
import { DataTable } from "@/components/DataTable";
import { PageContent } from "@/layout/PageContent";
import { PageHeader } from "@/components/PageHeader";
import { SearchInput } from "@/components/SearchInput";

const columnHelper = createColumnHelper<CatalogItemSummary>();

export function ServiciosPage(): React.JSX.Element {
  const [search, setSearch] = useState("");

  const query = useQuery({
    queryKey: ["maestros", "servicios", search],
    queryFn: () =>
      apiFetch<PagedResult<CatalogItemSummary>>(
        `/maestros/catalogos/items?q=${encodeURIComponent(search)}&status=ACTIVE`,
      ).then((data) => ({ ...data, items: data.items.filter((i) => i.item_type === "SERVICE") })),
    retry: false,
  });

  const columns = [
    columnHelper.accessor("code", { header: "Código" }),
    columnHelper.accessor("name", { header: "Servicio" }),
    columnHelper.accessor("status", { header: "Estado" }),
  ];

  return (
    <PageContent maxWidth="full">
      <PageHeader
        title="Servicios"
        description="Catálogo de servicios (unidad de facturación, sin inventario)."
        crumbs={[{ label: "Maestros" }, { label: "Servicios" }]}
      />
      <div className="mb-4">
        <SearchInput value={search} onChange={setSearch} placeholder="Buscar servicio…" />
      </div>
      <DataTable
        columns={columns}
        data={query.data?.items ?? []}
        loading={query.isLoading}
        error={query.isError ? "No fue posible cargar los servicios." : null}
        getRowId={(row) => row.id}
        emptyTitle="Sin servicios"
        emptyDescription="Aún no hay servicios registrados."
      />
    </PageContent>
  );
}
