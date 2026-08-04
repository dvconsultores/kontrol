/** Productos — listado con DataTable (FR-002-042, WF-01). */
import { useQuery } from "@tanstack/react-query";
import { createColumnHelper } from "@tanstack/react-table";
import { useState } from "react";
import { Link } from "react-router";

import { apiFetch } from "@/api/client";
import type { CatalogItemSummary, PagedResult } from "@/api/types";
import { Button } from "@/components/Button";
import { DataTable } from "@/components/DataTable";
import { PageContent } from "@/layout/PageContent";
import { PageHeader } from "@/components/PageHeader";
import { SearchInput } from "@/components/SearchInput";

const columnHelper = createColumnHelper<CatalogItemSummary>();

export function ProductosPage(): React.JSX.Element {
  const [search, setSearch] = useState("");

  const query = useQuery({
    queryKey: ["maestros", "productos", search],
    queryFn: () =>
      apiFetch<PagedResult<CatalogItemSummary>>(
        `/maestros/catalogos/items?q=${encodeURIComponent(search)}&status=ACTIVE`,
      ),
    retry: false,
  });

  const columns = [
    columnHelper.accessor("code", { header: "Código" }),
    columnHelper.accessor("name", { header: "Producto" }),
    columnHelper.accessor("status", { header: "Estado" }),
    columnHelper.display({
      id: "actions",
      header: "Acciones",
      cell: ({ row }) => (
        <div className="flex justify-end gap-1">
          <Link to={`/maestros/productos/${row.original.id}`} className="text-sm text-brand-700 hover:underline">
            Ver
          </Link>
        </div>
      ),
    }),
  ];

  return (
    <PageContent maxWidth="full">
      <PageHeader
        title="Productos"
        description="Catálogo de productos (inventario, fiscal y regulatorio)."
        crumbs={[{ label: "Maestros" }, { label: "Productos" }]}
        actions={
          <Link to="/maestros/productos/nuevo">
            <Button>Nuevo producto</Button>
          </Link>
        }
      />
      <div className="mb-4">
        <SearchInput value={search} onChange={setSearch} placeholder="Buscar producto…" />
      </div>
      <DataTable
        columns={columns}
        data={query.data?.items ?? []}
        loading={query.isLoading}
        error={query.isError ? "No fue posible cargar los productos." : null}
        getRowId={(row) => row.id}
        emptyTitle="Sin productos"
        emptyDescription="Aún no hay productos registrados."
      />
    </PageContent>
  );
}
