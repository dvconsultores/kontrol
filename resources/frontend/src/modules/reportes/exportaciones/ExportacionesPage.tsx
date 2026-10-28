/** Exportaciones auditadas y trabajos asíncronos (FR-009-020/023). */
import { useCallback, useMemo, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { createColumnHelper } from "@tanstack/react-table";

import { apiFetch } from "@/api/client";
import { descargarArchivo, mensajeDeDescarga } from "@/api/descargas";
import type { ReportExportSummary, ReportJobSummary } from "@/api/types";
import { useNotifications } from "@/app/contexts/NotificationContext";
import { useAutoridad } from "@/app/autoridad/AutoridadContext";
import { AsyncButton } from "@/components/AsyncButton";
import { Autorizado } from "@/components/Autorizado";
import { DataTable } from "@/components/DataTable";
import { IconButton } from "@/components/IconButton";
import { Download } from "lucide-react";
import { formatearInstante } from "@/lib/fecha-de-negocio";
import { PageContent } from "@/layout/PageContent";
import { PageHeader } from "@/components/PageHeader";

const exportHelper = createColumnHelper<ReportExportSummary>();
const jobHelper = createColumnHelper<ReportJobSummary>();

function BotonDescarga({ etiqueta, alDescargar }: { etiqueta: string; alDescargar: () => Promise<void> }): React.JSX.Element {
  const [ocupado, setOcupado] = useState(false);

  const pulsar = async (): Promise<void> => {
    if (ocupado) return;
    setOcupado(true);
    try {
      await alDescargar();
    } finally {
      setOcupado(false);
    }
  };

  return (
    <IconButton
      label={etiqueta}
      title="Descargar archivo"
      icon={Download}
      onClick={() => void pulsar()}
      disabled={ocupado}
      aria-busy={ocupado}
    />
  );
}

export function ExportacionesPage(): React.JSX.Element {
  const queryClient = useQueryClient();
  const { notify } = useNotifications();

  const exportsData = useQuery({
    queryKey: ["reporting", "exports"],
    queryFn: () => apiFetch<{ items: ReportExportSummary[] }>("/reporting/exports"),
    retry: false,
  });
  const jobs = useQuery({
    queryKey: ["reporting", "jobs"],
    queryFn: () => apiFetch<{ items: ReportJobSummary[] }>("/reporting/jobs"),
    retry: false,
  });

  const { puede } = useAutoridad();

  const runJob = async (): Promise<void> => {
    const created = await apiFetch<{ id: string }>("/reporting/jobs", {
      method: "POST",
      body: { report_key: "executive_ventas" },
    });
    const done = await apiFetch<{ id: string; status: string }>(`/reporting/jobs/${created.id}/run`, { method: "POST" });
    notify({ type: "success", title: "Trabajo completado", description: `Job ${done.id.slice(0, 8)} · ${done.status}` });
    void queryClient.invalidateQueries({ queryKey: ["reporting", "jobs"] });
  };

  const descargar = useCallback(async (id: string): Promise<void> => {
    try {
      const nombre = await descargarArchivo(`/reporting/exports/${id}/download`, `exportacion-${id}`);
      notify({ type: "success", title: "Archivo descargado", description: nombre });
    } catch (error) {
      notify({ type: "error", title: "No fue posible descargar", description: mensajeDeDescarga(error) });
    }
  }, [notify]);

  const exportColumns = useMemo(() => [
    exportHelper.accessor("report_key", { header: "Reporte" }),
    exportHelper.accessor("format", { header: "Formato" }),
    exportHelper.accessor("file_ref", { header: "Archivo" }),
    exportHelper.accessor("exported_by", { header: "Exportado por" }),
    exportHelper.accessor("exported_at", { header: "Fecha", cell: (info) => formatearInstante(info.getValue()) }),
    exportHelper.accessor("status", { header: "Estado" }),
    exportHelper.display({
      id: "download",
      header: "Acción",
      cell: ({ row }) =>
        puede("GET", "/reporting/exports/_/download") ? (
          <BotonDescarga
            etiqueta={`Descargar ${row.original.file_ref ?? "exportación"}`}
            alDescargar={() => descargar(row.original.id)}
          />
        ) : null,
    }),
  ], [puede, descargar]);

  const jobColumns = [
    jobHelper.accessor("report_key", { header: "Reporte" }),
    jobHelper.accessor("status", { header: "Estado" }),
    jobHelper.accessor("error", { header: "Error" }),
    jobHelper.accessor("result_ref", { header: "Resultado" }),
  ];

  return (
    <PageContent maxWidth="full">
      <PageHeader
        title="Exportaciones y trabajos"
        description="Histórico de exportaciones auditadas (quién/cuándo/qué) y jobs asíncronos (FR-009-020/023)."
        crumbs={[{ label: "Reportes" }, { label: "Exportaciones" }]}
      />

      <Autorizado operacion={["POST", "/reporting/jobs"]}>
        <div className="mb-4 flex items-end justify-between rounded-lg border border-border-default bg-surface-0 p-4">
          <div>
            <p className="text-sm font-semibold text-text-700">Trabajo asíncrono de prueba</p>
            <p className="text-sm text-text-500">Ejecuta el reporte ejecutivo de ventas como job.</p>
          </div>
          {puede("POST", "/reporting/jobs/_/run") ? <AsyncButton variant="secondary" onClick={runJob}>Ejecutar job</AsyncButton> : null}
        </div>
      </Autorizado>

      <h2 className="mb-2 text-base font-semibold text-text-900">Jobs</h2>
      <div className="mb-6">
        <DataTable
          columns={jobColumns}
          data={jobs.data?.items ?? []}
          loading={jobs.isLoading}
          error={jobs.isError ? "No fue posible cargar los trabajos." : null}
          getRowId={(row) => row.id}
          emptyTitle="Sin trabajos"
          emptyDescription="Ejecute un job para ver su estado."
        />
      </div>

      <h2 className="mb-2 text-base font-semibold text-text-900">Exportaciones auditadas</h2>
      <DataTable
        columns={exportColumns}
        data={exportsData.data?.items ?? []}
        loading={exportsData.isLoading}
        error={exportsData.isError ? "No fue posible cargar las exportaciones." : null}
        getRowId={(row) => row.id}
        emptyTitle="Sin exportaciones"
        emptyDescription="Exporte un reporte desde el centro de reportes y descárguelo aquí."
      />
    </PageContent>
  );
}
