/** Auditoría consolidada — timeline de eventos (FR-009-022). */
import { useQuery } from "@tanstack/react-query";
import { createColumnHelper } from "@tanstack/react-table";

import { apiFetch } from "@/api/client";
import type { AuditTimelineItem } from "@/api/types";
import { DataTable } from "@/components/DataTable";
import { PageContent } from "@/layout/PageContent";
import { PageHeader } from "@/components/PageHeader";

const columnHelper = createColumnHelper<AuditTimelineItem>();

export function ReportesAuditoriaPage(): React.JSX.Element {
  const timeline = useQuery({
    queryKey: ["reporting", "audit", "timeline"],
    queryFn: () => apiFetch<{ items: AuditTimelineItem[] }>("/reporting/audit/timeline"),
    retry: false,
  });

  const columns = [
    columnHelper.accessor("event_time", { header: "Fecha" }),
    columnHelper.accessor("action", { header: "Acción" }),
    columnHelper.accessor("entity_type", { header: "Entidad" }),
    columnHelper.accessor("entity_id", { header: "ID" }),
    columnHelper.accessor("user_id", { header: "Usuario" }),
    columnHelper.accessor("source", { header: "Origen" }),
    columnHelper.accessor("reason", { header: "Motivo" }),
  ];

  return (
    <PageContent maxWidth="full">
      <PageHeader
        title="Auditoría"
        description="Timeline de cambios, impresiones, exportaciones, accesos e incidentes (reutiliza AuditEvent de 001)."
        crumbs={[{ label: "Reportes" }, { label: "Auditoría" }]}
      />

      <DataTable
        columns={columns}
        data={timeline.data?.items ?? []}
        loading={timeline.isLoading}
        error={timeline.isError ? "No fue posible cargar la auditoría." : null}
        getRowId={(row) => row.id}
        emptyTitle="Sin eventos de auditoría"
        emptyDescription="Los cambios, impresiones y exportaciones quedarán registrados aquí."
      />
    </PageContent>
  );
}
