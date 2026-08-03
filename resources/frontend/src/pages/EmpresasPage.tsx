/** Empresas — listado con DataTable (WF-01, FR-016/017/018/019). */
import { useQuery } from "@tanstack/react-query";
import { createColumnHelper } from "@tanstack/react-table";
import { useState } from "react";

import { apiFetch } from "@/api/client";
import type { CompanySummary } from "@/api/types";
import { useCompany } from "@/app/contexts/CompanyContext";
import { Button } from "@/components/Button";
import { DataTable } from "@/components/DataTable";
import { PageContent } from "@/layout/PageContent";
import { PageHeader } from "@/components/PageHeader";
import { SearchInput } from "@/components/SearchInput";

const columnHelper = createColumnHelper<CompanySummary>();

export function EmpresasPage(): React.JSX.Element {
  const { setActiveCompany } = useCompany();
  const [search, setSearch] = useState("");

  const query = useQuery({
    queryKey: ["organization", "companies", search],
    queryFn: () => apiFetch<CompanySummary[]>(`/organization/companies?q=${encodeURIComponent(search)}`),
    retry: false,
  });

  const columns = [
    columnHelper.accessor("code", { header: "Código" }),
    columnHelper.accessor("legal_name", { header: "Razón social" }),
    columnHelper.accessor("rif", { header: "RIF" }),
    columnHelper.accessor("status", { header: "Estado" }),
    columnHelper.display({
      id: "actions",
      header: "Acciones",
      cell: ({ row }) => (
        <div className="flex justify-end gap-1">
          <Button variant="secondary" size="sm" onClick={() => setActiveCompany(row.original)}>
            Activar
          </Button>
        </div>
      ),
    }),
  ];

  return (
    <PageContent maxWidth="full">
      <PageHeader
        title="Empresas"
        description="Entidades legales de esta instalación."
        crumbs={[{ label: "Organización" }, { label: "Empresas" }]}
      />
      <div className="mb-4">
        <SearchInput value={search} onChange={setSearch} />
      </div>
      <DataTable
        columns={columns}
        data={query.data ?? []}
        loading={query.isLoading}
        error={query.isError ? "No fue posible cargar las empresas." : null}
        getRowId={(row) => row.id}
        emptyTitle="Sin empresas"
        emptyDescription="Aún no hay empresas registradas."
      />
    </PageContent>
  );
}
