/** Terceros — listado con búsqueda y DataTable (FR-002-042, WF-01). */
import { useQuery } from "@tanstack/react-query";
import { createColumnHelper } from "@tanstack/react-table";
import { useState } from "react";
import { Link } from "react-router";

import { apiFetch } from "@/api/client";
import type { PagedResult, Party } from "@/api/types";
import { DataTable } from "@/components/DataTable";
import { PageContent } from "@/layout/PageContent";
import { PageHeader } from "@/components/PageHeader";
import { SearchInput } from "@/components/SearchInput";

const columnHelper = createColumnHelper<Party>();

export function TercerosPage(): React.JSX.Element {
  const [search, setSearch] = useState("");

  const query = useQuery({
    queryKey: ["maestros", "terceros", search],
    queryFn: () => apiFetch<PagedResult<Party>>(`/maestros/terceros?q=${encodeURIComponent(search)}`),
    retry: false,
  });

  const columns = [
    columnHelper.accessor("code", { header: "Código" }),
    columnHelper.accessor("name", { header: "Nombre" }),
    columnHelper.accessor("tax_id", { header: "RIF" }),
    columnHelper.accessor("roles", {
      header: "Roles",
      cell: (info) => (info.getValue() ?? []).join(", "),
    }),
    columnHelper.accessor("status", { header: "Estado" }),
    columnHelper.display({
      id: "actions",
      header: "Acciones",
      cell: ({ row }) => (
        <div className="flex justify-end gap-1">
          <Link to={`/maestros/terceros/${row.original.id}`} className="text-sm text-brand-700 hover:underline">
            Ver
          </Link>
        </div>
      ),
    }),
  ];

  return (
    <PageContent maxWidth="full">
      <PageHeader
        title="Terceros"
        description="Clientes, proveedores, transportistas y conductores."
        crumbs={[{ label: "Maestros" }, { label: "Terceros" }]}
      />
      <div className="mb-4">
        <SearchInput value={search} onChange={setSearch} placeholder="Buscar por nombre, RIF o código…" />
      </div>
      <DataTable
        columns={columns}
        data={query.data?.items ?? []}
        loading={query.isLoading}
        error={query.isError ? "No fue posible cargar los terceros." : null}
        getRowId={(row) => row.id}
        emptyTitle="Sin terceros"
        emptyDescription="Aún no hay terceros registrados."
      />
    </PageContent>
  );
}
