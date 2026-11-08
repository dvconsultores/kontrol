/** Terceros — listado con búsqueda, filtros y DataTable (FR-002-042, WF-01). */
import { useQuery } from "@tanstack/react-query";
import { createColumnHelper } from "@tanstack/react-table";
import { useState } from "react";
import { Link } from "react-router";

import { apiFetch } from "@/api/client";
import type { PagedResult, Party } from "@/api/types";
import { Autorizado } from "@/components/Autorizado";
import { Button } from "@/components/Button";
import { DataTable } from "@/components/DataTable";
import { Pagination } from "@/components/Pagination";
import { PageContent } from "@/layout/PageContent";
import { PageHeader } from "@/components/PageHeader";
import { SearchInput } from "@/components/SearchInput";
import { StatusFilter, type StatusFilterValue } from "@/components/StatusFilter";

const columnHelper = createColumnHelper<Party>();

type TercerosQueryParams = {
  search: string;
  status: StatusFilterValue;
  pageIndex: number;
  pageSize: number;
};

function tercerosParams({ search, status, pageIndex, pageSize }: TercerosQueryParams): string {
  const params = new URLSearchParams();
  if (search.trim()) {
    params.set("q", search.trim());
  }
  if (status !== "ALL") {
    params.set("status", status);
  }
  params.set("page", String(pageIndex + 1));
  params.set("page_size", String(pageSize));

  return params.toString();
}

export function TercerosPage(): React.JSX.Element {
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState<StatusFilterValue>("ALL");
  const [pageIndex, setPageIndex] = useState(0);
  const [pageSize, setPageSize] = useState(25);

  const query = useQuery({
    queryKey: ["maestros", "terceros", search, status, pageIndex, pageSize],
    queryFn: () =>
      apiFetch<PagedResult<Party>>(
        `/maestros/terceros?${tercerosParams({ search, status, pageIndex, pageSize })}`,
      ),
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
    columnHelper.accessor("status", {
      header: "Estado",
      cell: (info) => (info.getValue() === "ACTIVE" ? "Activo" : "Inactivo"),
    }),
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
        actions={
          <Autorizado operacion={["POST", "/maestros/terceros"]}>
            <Link to="/maestros/terceros/nuevo">
              <Button>Nuevo tercero</Button>
            </Link>
          </Autorizado>
        }
      />
      <div className="mb-4 flex flex-wrap items-end gap-2">
        <SearchInput
          value={search}
          onChange={(value) => {
            setSearch(value);
            setPageIndex(0);
          }}
          placeholder="Buscar por nombre, RIF o código…"
        />
        <StatusFilter
          value={status}
          onChange={(value) => {
            setStatus(value);
            setPageIndex(0);
          }}
        />
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
      <Pagination
        pageIndex={pageIndex}
        pageSize={pageSize}
        total={query.data?.total ?? 0}
        onPageChange={setPageIndex}
        onPageSizeChange={(size) => {
          setPageSize(size);
          setPageIndex(0);
        }}
      />
    </PageContent>
  );
}
