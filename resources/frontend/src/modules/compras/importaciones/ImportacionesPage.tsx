import { useMemo, useState } from "react";
import { Link } from "react-router";
import { createColumnHelper } from "@tanstack/react-table";
import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/api/client";
import type { PagedResult } from "@/api/types";
import { PageHeader } from "@/components/PageHeader";
import { PageContent } from "@/layout/PageContent";
import { SearchInput } from "@/components/SearchInput";
import { DataTable } from "@/components/DataTable";
import { Button } from "@/components/Button";
import { Pagination } from "@/components/Pagination";
import { Autorizado } from "@/components/Autorizado";
import { useCompany } from "@/app/contexts/CompanyContext";
import { ESTADOS, importacionKey, type EstadoImportacion } from "./tipos";

type ImportacionItem = {
  id: string;
  code: string;
  status: EstadoImportacion;
  currency: string;
  supplier_id: string;
  supplier_name: string;
  order_id: string | null;
  order_code: string | null;
  incoterm: string | null;
  expected_arrival_date: string | null;
  created_at: string;
  version: number;
};

const columnHelper = createColumnHelper<ImportacionItem>();

export function ImportacionesPage() {
  const { activeCompany } = useCompany();
  const [q, setQ] = useState("");
  const [status, setStatus] = useState("");
  const [page, setPage] = useState(0);
  const [pageSize, setPageSize] = useState(10);

  const companyId = activeCompany?.id ?? "";

  const params = new URLSearchParams();
  if (q) params.set("q", q);
  if (status) params.set("status", status);
  params.set("page", String(page + 1));
  params.set("page_size", String(pageSize));

  const query = useQuery({
    queryKey: ["importaciones", companyId, { q, status, page, pageSize }],
    queryFn: () => apiFetch<PagedResult<ImportacionItem>>(`/importaciones?${params}`),
  });

  const columns = useMemo(
    () => [
      columnHelper.accessor("code", {
        header: "Código",
        cell: (info) => info.getValue(),
      }),
      columnHelper.accessor("supplier_name", {
        header: "Proveedor",
        cell: (info) => info.getValue(),
      }),
      columnHelper.accessor("order_code", {
        header: "Orden",
        cell: (info) => info.getValue() ?? "Sin orden",
      }),
      columnHelper.accessor("incoterm", {
        header: "INCOTERM",
        cell: (info) => info.getValue() ?? "—",
      }),
      columnHelper.accessor("expected_arrival_date", {
        header: "Llegada prevista",
        cell: (info) => info.getValue() ?? "—",
      }),
      columnHelper.accessor("status", {
        header: "Estado",
        cell: (info) => ESTADOS[info.getValue()],
      }),
      columnHelper.display({
        id: "ver",
        header: "Ver",
        cell: (info) => (
          <Link to={`/compras/importaciones/${info.row.original.id}`}>
            <Button variant="secondary" size="sm">
              Ver
            </Button>
          </Link>
        ),
      }),
    ],
    [],
  );

  const errorMessage =
    query.error instanceof Error ? query.error.message : query.isError ? "Error al cargar importaciones." : null;

  return (
    <PageContent maxWidth="full">
      <PageHeader
        title="Importaciones"
        description="Expedientes de importación desde la negociación hasta la recepción."
        crumbs={[
          { label: "Compras", to: "/compras" },
          { label: "Importaciones" },
        ]}
        actions={
          <Autorizado operacion={["POST", "/importaciones"]}>
            <Link to="/compras/importaciones/nueva">
              <Button>Nueva importación</Button>
            </Link>
          </Autorizado>
        }
      />
      <div className="mb-4 flex flex-wrap items-center gap-3">
        <SearchInput value={q} onChange={setQ} placeholder="Buscar por código…" />
        <select
          aria-label="Estado"
          className="h-10 w-full rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900"
          value={status}
          onChange={(e) => {
            setStatus(e.target.value);
            setPage(0);
          }}
        >
          <option value="">Todos</option>
          <option value="NEGOTIATING">En negociación</option>
          <option value="ORDERED">Orden vinculada</option>
          <option value="DOCUMENTS_COMPLETE">Documentación completa</option>
          <option value="CANCELLED">Cancelada</option>
        </select>
      </div>
      <DataTable
        columns={columns}
        data={query.data?.items ?? []}
        loading={query.isLoading}
        error={errorMessage}
        getRowId={(row) => importacionKey(companyId, row.id)}
        emptyTitle="Sin importaciones"
        emptyDescription="Crea la primera con Nueva importación."
      />
      {query.data && query.data.total > 0 && (
        <Pagination
          pageIndex={page}
          pageSize={pageSize}
          total={query.data.total}
          onPageChange={setPage}
          onPageSizeChange={setPageSize}
        />
      )}
    </PageContent>
  );
}
