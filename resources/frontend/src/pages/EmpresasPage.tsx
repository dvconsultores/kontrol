/** Empresas — listado con DataTable (WF-01, FR-016/017/018/019). */
import { useQuery } from "@tanstack/react-query";
import { createColumnHelper } from "@tanstack/react-table";
import { useState } from "react";

import { apiFetch } from "@/api/client";
import type { CompanySummary } from "@/api/types";
import { useCompany } from "@/app/contexts/CompanyContext";
import { useNotifications } from "@/app/contexts/NotificationContext";
import { Button } from "@/components/Button";
import { DataTable } from "@/components/DataTable";
import { PageContent } from "@/layout/PageContent";
import { PageHeader } from "@/components/PageHeader";
import { SearchInput } from "@/components/SearchInput";

const columnHelper = createColumnHelper<CompanySummary>();

export function EmpresasPage(): React.JSX.Element {
  const { activeCompany, selectCompany, clearCompany } = useCompany();
  const { notify } = useNotifications();
  const [search, setSearch] = useState("");

  const query = useQuery({
    queryKey: ["organization", "companies", search],
    queryFn: () => apiFetch<CompanySummary[]>(`/organization/companies?q=${encodeURIComponent(search)}`),
    retry: false,
  });

  const activate = (company: CompanySummary): void => {
    selectCompany(company.id);
    notify({
      type: "success",
      title: "Empresa activada",
      description: `A partir de ahora opera sobre ${company.legal_name}.`,
    });
  };

  const deactivate = (): void => {
    clearCompany();
    notify({
      type: "info",
      title: "Empresa desactivada",
      description: "Ninguna empresa está activa; seleccione una para operar.",
    });
  };

  const columns = [
    columnHelper.accessor("code", { header: "Código" }),
    columnHelper.accessor("legal_name", { header: "Razón social" }),
    columnHelper.accessor("rif", { header: "RIF" }),
    columnHelper.accessor("status", { header: "Estado" }),
    columnHelper.display({
      id: "actions",
      header: "Acciones",
      cell: ({ row }) => {
        const isActive = activeCompany?.id === row.original.id;
        return (
          <div className="flex justify-end gap-1">
            {isActive ? (
              <>
                <Button variant="secondary" size="sm" disabled title="Empresa activa">
                  Activa
                </Button>
                <Button variant="ghost" size="sm" onClick={deactivate}>
                  Desactivar
                </Button>
              </>
            ) : (
              <Button variant="primary" size="sm" onClick={() => activate(row.original)}>
                Activar
              </Button>
            )}
          </div>
        );
      },
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
