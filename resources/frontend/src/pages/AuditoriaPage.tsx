/** Auditoría — timeline de eventos con filtros y paginación (FR-001-070). */
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

import { listAuditEvents } from "@/api/audit";
import type { AuditEvent } from "@/api/types";
import { DataTable } from "@/components/DataTable";
import { PageContent } from "@/layout/PageContent";
import { PageHeader } from "@/components/PageHeader";
import { SearchInput } from "@/components/SearchInput";
import { createColumnHelper } from "@tanstack/react-table";

const columnHelper = createColumnHelper<AuditEvent>();

const columns = [
  columnHelper.accessor("created_at", {
    header: "Fecha",
    cell: (info) => new Date(info.getValue()).toLocaleString("es-VE"),
  }),
  columnHelper.accessor("action", { header: "Acción" }),
  columnHelper.accessor("entity_type", { header: "Entidad" }),
  columnHelper.accessor("user_id", { header: "Usuario" }),
  columnHelper.accessor("request_id", { header: "Request ID" }),
];

export function AuditoriaPage(): React.JSX.Element {
  const [search, setSearch] = useState("");
  const query = useQuery({
    queryKey: ["audit", "events", search],
    queryFn: () => listAuditEvents(search),
    retry: false,
  });

  return (
    <PageContent maxWidth="full">
      <PageHeader
        title="Auditoría"
        description="Eventos de acceso y operaciones relevantes de la instalación."
        crumbs={[{ label: "Auditoría" }]}
      />
      <div className="mb-4">
        <SearchInput value={search} onChange={setSearch} />
      </div>
      <DataTable
        columns={columns}
        // El servidor responde un sobre paginado: las filas son `items`.
        data={query.data?.items ?? []}
        loading={query.isLoading}
        error={query.isError ? "No fue posible cargar la auditoría." : null}
        getRowId={(row) => row.id}
        emptyTitle="Sin eventos"
        emptyDescription="No hay eventos de auditoría registrados con los filtros actuales."
      />
    </PageContent>
  );
}
