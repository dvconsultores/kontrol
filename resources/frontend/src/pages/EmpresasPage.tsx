/** Empresas — listado con DataTable (WF-01, FR-016/017/018/019). */
import { useQuery } from "@tanstack/react-query";
import { createColumnHelper } from "@tanstack/react-table";
import { useState } from "react";

import { listCompanies } from "@/api/organization";
import type { CompanySummary } from "@/api/types";
import { useCompany } from "@/app/contexts/CompanyContext";
import { useNotifications } from "@/app/contexts/NotificationContext";
import { Button } from "@/components/Button";
import { DataTable } from "@/components/DataTable";
import { PageContent } from "@/layout/PageContent";
import { PageHeader } from "@/components/PageHeader";
import { Pagination } from "@/components/Pagination";
import { SearchInput } from "@/components/SearchInput";

const columnHelper = createColumnHelper<CompanySummary>();

export function EmpresasPage(): React.JSX.Element {
  const { activeCompany, selectCompany, clearCompany } = useCompany();
  const { notify } = useNotifications();
  const [search, setSearch] = useState("");
  // Paginación de servidor (contrato de listados): la página es estado de la
  // pantalla, cero-based en la interfaz y uno-based en la petición, como en
  // Alertas. Cambiar la búsqueda o el tamaño vuelve a la primera página.
  const [pagina, setPagina] = useState(0);
  const [tamano, setTamano] = useState(10);

  const query = useQuery({
    queryKey: ["organization", "companies", search, pagina, tamano],
    queryFn: () => listCompanies({ q: search, page: pagina + 1, page_size: tamano }),
    retry: false,
  });

  const buscar = (valor: string): void => {
    setSearch(valor);
    setPagina(0);
  };

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
        <SearchInput value={search} onChange={buscar} />
      </div>
      <DataTable
        columns={columns}
        data={query.data?.items ?? []}
        loading={query.isLoading}
        error={query.isError ? "No fue posible cargar las empresas." : null}
        getRowId={(row) => row.id}
        emptyTitle="Sin empresas"
        emptyDescription="Aún no hay empresas registradas."
        manualPagination
      />
      {query.data && query.data.total > 10 ? (
        <Pagination
          pageIndex={pagina}
          pageSize={tamano}
          total={query.data.total}
          onPageChange={setPagina}
          onPageSizeChange={(valor) => {
            setTamano(valor);
            setPagina(0);
          }}
        />
      ) : null}
    </PageContent>
  );
}
