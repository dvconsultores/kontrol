/** Auditoría — timeline de eventos con filtros y paginación (FR-001-070). */
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

import { listAuditEvents } from "@/api/audit";
import type { AuditEvent } from "@/api/types";
import { useAutoridad } from "@/app/autoridad/AutoridadContext";
import { DataTable } from "@/components/DataTable";
import { PageContent } from "@/layout/PageContent";
import { PageHeader } from "@/components/PageHeader";
import { Pagination } from "@/components/Pagination";
import { SearchInput } from "@/components/SearchInput";
import { formatearFecha } from "@/i18n";
import { createColumnHelper } from "@tanstack/react-table";

const columnHelper = createColumnHelper<AuditEvent>();

const columns = [
  columnHelper.accessor("event_time", {
    header: "Fecha",
    cell: (info) => formatearFecha(info.getValue()),
  }),
  columnHelper.accessor("action", { header: "Acción" }),
  columnHelper.accessor("entity_type", { header: "Entidad" }),
  columnHelper.accessor("user_id", { header: "Usuario" }),
  columnHelper.accessor("request_id", { header: "Request ID" }),
];

export function AuditoriaPage(): React.JSX.Element {
  const { tiene } = useAutoridad();
  const [search, setSearch] = useState("");
  // Paginación de servidor (contrato de listados), como en Empresas: la
  // página es cero-based en la interfaz y uno-based en la petición, y
  // cambiar el tamaño vuelve a la primera. La caja de búsqueda no reinicia
  // la página: el servidor ignora `q` (`UI-BUSQUEDA-MUERTA`, decisión
  // pendiente).
  const [pagina, setPagina] = useState(0);
  const [tamano, setTamano] = useState(10);
  const query = useQuery({
    queryKey: ["audit", "events", search, pagina, tamano],
    queryFn: () => listAuditEvents({ q: search, page: pagina + 1, page_size: tamano }),
    retry: false,
  });

  return (
    <PageContent maxWidth="full">
      <PageHeader
        title="Auditoría"
        description={tiene("audit:view", "tenant") ? "Eventos de acceso y operaciones de todas las empresas del tenant, incluidos los que no pertenecen a ninguna empresa (como los inicios de sesión)." : "Eventos de las empresas en las que usted tiene autoridad de auditoría. Los eventos sin empresa (como los inicios de sesión) solo los ve quien audita todas las empresas del tenant."}
        crumbs={[{ label: "Auditoría" }]}
      />
      <div className="mb-4">
        <SearchInput value={search} onChange={setSearch} />
      </div>
      <DataTable
        columns={columns}
        // El servidor ya entrega una página: las filas son `items` y la tabla no vuelve a paginar.
        data={query.data?.items ?? []}
        loading={query.isLoading}
        error={query.isError ? "No fue posible cargar la auditoría." : null}
        getRowId={(row) => row.id}
        emptyTitle="Sin eventos"
        emptyDescription="No hay eventos de auditoría registrados con los filtros actuales."
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
