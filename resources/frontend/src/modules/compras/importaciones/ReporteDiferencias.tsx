import { useQuery } from "@tanstack/react-query";
import { useEffect, useRef } from "react";
import { Link } from "react-router";

import {
  ApiError,
  apiFetch,
  type ArchivoDescargado,
} from "@/api/client";
import { descargarArchivo, mensajeDeDescarga } from "@/api/descargas";
import { useNotifications } from "@/app/contexts/NotificationContext";
import { Autorizado } from "@/components/Autorizado";
import { AsyncButton } from "@/components/AsyncButton";
import { formatearInstante } from "@/lib/fecha-de-negocio";
import type {
  EstadoReporteDiferencias,
  ReportesDeRecepcionRespuesta,
  ResumenReporteDiferencias,
} from "./tipos";

const ETIQUETAS_ESTADO: Record<string, string> = {
  NO_DIFFERENCES: "Sin diferencias",
  DIFFERENCES_WITHOUT_REPORT: "Diferencias detectadas sin reporte",
  REPORT_ISSUED: "Reporte emitido",
  NEW_REVISION_AVAILABLE: "Nueva revisión disponible",
};

interface PropsRecepcion {
  importacionId: string;
  recepcionId: string;
  recepcionCodigo: string;
}

export function ReporteDiferenciasRecepcion({
  importacionId,
  recepcionId,
  recepcionCodigo,
}: PropsRecepcion): React.JSX.Element {
  const { notify } = useNotifications();
  const urlsImpresion = useRef<string[]>([]);

  useEffect(() => {
    const urls = urlsImpresion.current;
    return () => {
      for (const url of urls) {
        URL.revokeObjectURL(url);
      }
    };
  }, []);

  const query = useQuery({
    queryKey: ["importaciones", importacionId, "reporte-diferencias", recepcionId],
    queryFn: () =>
      apiFetch<EstadoReporteDiferencias>(
        `/importaciones/${importacionId}/receipts/${recepcionId}/difference-report`,
      ),
    refetchOnMount: "always",
  });

  if (query.isLoading) {
    return (
      <section className="rounded-lg border border-border-default bg-surface-0 p-6">
        <p className="text-sm text-text-600">Cargando reporte de diferencias…</p>
      </section>
    );
  }

  if (query.isError || !query.data) {
    return (
      <section className="rounded-lg border border-border-default bg-surface-0 p-6">
        <p className="text-sm text-text-600">
          No fue posible cargar el reporte de diferencias.
        </p>
      </section>
    );
  }

  const data = query.data;
  const ultimoReporte: ResumenReporteDiferencias | undefined = data.reports[0];

  async function emitirReporte(): Promise<void> {
    try {
      const detalle = await apiFetch<ResumenReporteDiferencias>(
        `/importaciones/${importacionId}/receipts/${recepcionId}/difference-report`,
        {
          method: "POST",
          body: { expected_snapshot_hash: data.current_snapshot_hash },
        },
      );
      notify({
        type: "success",
        title: `Reporte ${detalle.reference} emitido`,
      });
      await query.refetch();
    } catch (error) {
      if (error instanceof ApiError) {
        if (error.code === "DIFFERENCE_REPORT_STALE") {
          notify({
            type: "warning",
            title: "La recepción cambió. Revise el estado actualizado antes de emitir.",
          });
          await query.refetch();
          return;
        }
        if (error.code === "DIFFERENCE_REPORT_UNCHANGED") {
          notify({
            type: "info",
            title: "Ya existe un reporte para este estado.",
          });
          await query.refetch();
          return;
        }
        notify({ type: "error", title: error.message });
        return;
      }
      notify({
        type: "error",
        title: "No fue posible emitir el reporte.",
      });
    }
  }

  async function descargarReporte(report: ResumenReporteDiferencias): Promise<void> {
    try {
      const nombre = await descargarArchivo(
        `/importaciones/${importacionId}/difference-reports/${report.id}/pdf`,
        report.file_name,
      );
      notify({ type: "success", title: `Descargado ${nombre}` });
    } catch (error) {
      notify({ type: "error", title: mensajeDeDescarga(error) });
    }
  }

  async function imprimirReporte(report: ResumenReporteDiferencias): Promise<void> {
    try {
      const archivo = await apiFetch<ArchivoDescargado>(
        `/importaciones/${importacionId}/difference-reports/${report.id}/pdf?inline=true`,
        { responseType: "archivo" },
      );
      const url = URL.createObjectURL(archivo.blob);
      urlsImpresion.current.push(url);
      window.open(url, "_blank");
    } catch (error) {
      notify({ type: "error", title: mensajeDeDescarga(error) });
    }
  }

  const numLineasConDiferencia = data.lines.length;
  const numIncidencias = data.incidents.length;

  return (
    <section
      aria-labelledby={`reporte-diferencias-${recepcionId}`}
      className="rounded-lg border border-border-default bg-surface-0 p-6"
    >
      <h3
        id={`reporte-diferencias-${recepcionId}`}
        className="mb-3 text-md font-medium text-text-800"
      >
        Reporte formal de diferencias · {recepcionCodigo}
      </h3>

      <p className="mb-3 text-sm text-text-700">
        {ETIQUETAS_ESTADO[data.state] ?? data.state}
      </p>

      {data.has_differences ? (
        <p className="mb-3 text-sm text-text-600">
          {numLineasConDiferencia} líneas con diferencia · {numIncidencias}{" "}
          incidencias
        </p>
      ) : null}

      {(data.state === "DIFFERENCES_WITHOUT_REPORT" ||
        data.state === "NEW_REVISION_AVAILABLE") && (
        <Autorizado
          operacion={[
            "POST",
            `/importaciones/${importacionId}/receipts/${recepcionId}/difference-report`,
          ]}
        >
          <AsyncButton
            size="sm"
            onClick={emitirReporte}
            disabled={!data.current_snapshot_hash}
          >
            {data.state === "DIFFERENCES_WITHOUT_REPORT"
              ? "Emitir reporte formal"
              : "Emitir nueva revisión"}
          </AsyncButton>
        </Autorizado>
      )}

      {ultimoReporte ? (
        <div className="mt-4 flex flex-wrap items-center gap-3">
          <div className="text-sm text-text-800">
            <span className="font-medium">{ultimoReporte.reference}</span> ·{" "}
            <span>Revisión {ultimoReporte.revision}</span> ·{" "}
            <span>{formatearInstante(ultimoReporte.issued_at)}</span> ·{" "}
            <span>Emitido por {ultimoReporte.issued_by_name}</span>
          </div>
          <div className="flex flex-wrap gap-2">
            <AsyncButton
              size="sm"
              variant="secondary"
              onClick={() => descargarReporte(ultimoReporte)}
            >
              Descargar PDF
            </AsyncButton>
            <AsyncButton
              size="sm"
              variant="secondary"
              onClick={() => imprimirReporte(ultimoReporte)}
            >
              Imprimir
            </AsyncButton>
          </div>
        </div>
      ) : null}

      {data.reports.length > 1 ? (
        <div className="mt-4">
          <h4 className="mb-2 text-sm font-medium text-text-700">
            Historial de revisiones
          </h4>
          <ul aria-label="Historial de revisiones" className="space-y-2">
            {data.reports.map((reporte) => (
              <li
                key={reporte.id}
                className="flex flex-wrap items-center gap-3 text-sm"
              >
                <span className="text-text-800">
                  <span className="font-medium">{reporte.reference}</span> ·{" "}
                  <span>Revisión {reporte.revision}</span> ·{" "}
                  <span>{formatearInstante(reporte.issued_at)}</span> ·{" "}
                  <span>{reporte.issued_by_name}</span>
                </span>
                <AsyncButton
                  size="sm"
                  variant="secondary"
                  aria-label={`Descargar ${reporte.reference}`}
                  onClick={() => descargarReporte(reporte)}
                >
                  Descargar
                </AsyncButton>
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </section>
  );
}

export function ReportesDeRecepcion({
  recepcionId,
}: {
  recepcionId: string;
}): React.JSX.Element | null {
  const { notify } = useNotifications();

  const query = useQuery({
    queryKey: ["recepciones", recepcionId, "reportes-diferencias"],
    queryFn: () =>
      apiFetch<ReportesDeRecepcionRespuesta>(
        `/importaciones/receipt-difference-reports/${recepcionId}`,
      ),
    refetchOnMount: "always",
  });

  if (query.isLoading || query.isError || !query.data) {
    return null;
  }

  const data = query.data;

  if (!data.import_file_id) {
    return null;
  }

  async function descargarReporte(report: ResumenReporteDiferencias): Promise<void> {
    if (!data.import_file_id) {
      return;
    }
    try {
      const nombre = await descargarArchivo(
        `/importaciones/${data.import_file_id}/difference-reports/${report.id}/pdf`,
        report.file_name,
      );
      notify({ type: "success", title: `Descargado ${nombre}` });
    } catch (error) {
      notify({ type: "error", title: mensajeDeDescarga(error) });
    }
  }

  return (
    <section
      aria-labelledby={`reportes-diferencias-recepcion-${recepcionId}`}
      className="rounded-lg border border-border-default bg-surface-0 p-6"
    >
      <h2
        id={`reportes-diferencias-recepcion-${recepcionId}`}
        className="mb-3 text-lg font-semibold text-text-900"
      >
        Reporte formal de diferencias
      </h2>
      {data.import_file_code ? (
        <Link
          to={`/compras/importaciones/${data.import_file_id}#diferencias`}
          className="mb-3 inline-block text-sm font-medium text-brand-600 hover:text-brand-700"
        >
          Abrir expediente {data.import_file_code}
        </Link>
      ) : null}
      {data.reports.length === 0 ? (
        <p className="text-sm text-text-600">
          Esta recepción aún no tiene reporte formal de diferencias.
        </p>
      ) : (
        <ul aria-label="Reportes de diferencias" className="space-y-3">
          {data.reports.map((reporte) => (
            <li
              key={reporte.id}
              className="flex flex-wrap items-center gap-3 text-sm"
            >
              <span className="text-text-800">
                <span className="font-medium">{reporte.reference}</span> ·{" "}
                <span>Revisión {reporte.revision}</span> ·{" "}
                <span>{formatearInstante(reporte.issued_at)}</span> ·{" "}
                <span>{reporte.issued_by_name}</span>
              </span>
              <AsyncButton
                size="sm"
                variant="secondary"
                aria-label={`Descargar ${reporte.reference}`}
                onClick={() => descargarReporte(reporte)}
              >
                Descargar
              </AsyncButton>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
