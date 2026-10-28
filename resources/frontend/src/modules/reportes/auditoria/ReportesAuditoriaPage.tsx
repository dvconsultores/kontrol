/** Auditoría consolidada — timeline de eventos (FR-009-022, T-205). */
import { useQuery } from "@tanstack/react-query";
import { createColumnHelper } from "@tanstack/react-table";
import { useState } from "react";

import { apiFetch } from "@/api/client";
import type { AuditTimelineItem } from "@/api/types";
import { DataTable } from "@/components/DataTable";
import { formatearFecha } from "@/i18n";
import { PageContent } from "@/layout/PageContent";
import { PageHeader } from "@/components/PageHeader";
import { TextInput } from "@/components/TextInput";

const columnHelper = createColumnHelper<AuditTimelineItem>();

export function ReportesAuditoriaPage(): React.JSX.Element {
  const [entityType, setEntityType] = useState("");
  const [action, setAction] = useState("");

  const params = new URLSearchParams();
  if (entityType) params.set("entity_type", entityType);
  if (action) params.set("action", action);
  const qs = params.toString();

  const timeline = useQuery({
    queryKey: ["reporting", "audit", "timeline", entityType, action],
    queryFn: () => apiFetch<{ items: AuditTimelineItem[] }>(`/reporting/audit/timeline${qs ? `?${qs}` : ""}`),
    retry: false,
  });

  const columns = [
    columnHelper.accessor("event_time", {
      header: "Fecha",
      cell: (info) => formatearFecha(info.getValue()),
    }),
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

      <div className="mb-4 flex flex-wrap items-end gap-3 rounded-lg border border-border-default bg-surface-0 p-4">
        <label className="flex flex-col gap-1 text-sm text-text-500">
          Entidad
          <TextInput value={entityType} onChange={(e) => setEntityType(e.target.value)} placeholder="SalesInvoice, Payment…" />
        </label>
        <label className="flex flex-col gap-1 text-sm text-text-500">
          Acción
          <TextInput value={action} onChange={(e) => setAction(e.target.value)} placeholder="EMITTED, PAYMENT_TRANSITIONED…" />
        </label>
      </div>

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
