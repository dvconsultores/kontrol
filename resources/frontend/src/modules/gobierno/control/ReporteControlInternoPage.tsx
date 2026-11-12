import { useEffect, useState } from "react";
import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { Link } from "react-router";
import { apiFetch, ApiError } from "@/api/client";
import { useCompany } from "@/app/contexts/CompanyContext";
import { useNotifications } from "@/app/contexts/NotificationContext";
import { Button } from "@/components/Button";
import { DateInput } from "@/components/DateInput";
import { EmptyState } from "@/components/EmptyState";
import { FormField } from "@/components/FormField";
import { LoadingState } from "@/components/LoadingState";
import { PageHeader } from "@/components/PageHeader";
import { PageContent } from "@/layout/PageContent";
import { ErrorDeCarga } from "@/modules/gobierno/ocupacion/ErrorDeCarga";
import { descargarArchivo } from "@/api/descargas";
import { formatearFechaDeNegocio, formatearInstante } from "@/lib/fecha-de-negocio";

type EventoSod = {
  evento_id: string;
  fecha: string;
  usuario: string | null;
  regla_codigo: string;
  regla_nombre: string;
  proceso: string;
  proceso_etiqueta: string;
  accion_etiqueta: string;
  accion_previa_etiqueta: string;
};

type BloqueoIdentidadEvento = {
  evento_id: string;
  fecha: string;
  usuario: string | null;
  etiqueta: string;
};

type BloqueoCierreEvento = {
  evento_id: string;
  fecha: string;
  usuario: string | null;
  politica_codigo: string;
  accion_etiqueta: string;
  objeto_codigo: string;
  controles: { etiqueta: string; pendientes: number }[];
};

type AccionVencida = {
  hallazgo_id: string;
  hallazgo_codigo: string;
  hallazgo_titulo: string;
  accion_orden: number;
  descripcion: string;
  cargo: string;
  unidad: string;
  fecha_objetivo: string;
  porcentaje: number;
  dias_atraso: number;
};

type Reporte = {
  periodo: { desde: string; hasta: string };
  generado_en: string;
  conflictos_sod: {
    total: number;
    por_regla: {
      regla_codigo: string;
      regla_nombre: string;
      proceso: string;
      proceso_etiqueta: string;
      total: number;
    }[];
    eventos: EventoSod[];
  };
  bloqueos_identidad: {
    total: number;
    por_motivo: { codigo: string; etiqueta: string; total: number }[];
    eventos: BloqueoIdentidadEvento[];
  };
  bloqueos_cierre: {
    total: number;
    por_politica: {
      politica_codigo: string;
      accion_etiqueta: string;
      total: number;
    }[];
    eventos: BloqueoCierreEvento[];
  };
  hallazgos: {
    disponible: boolean;
    motivo: string | null;
    por_estado: Record<string, number>;
    por_riesgo: Record<string, number>;
    acciones_por_estado: Record<string, number>;
    acciones_vencidas: AccionVencida[];
  };
  overrides: { disponible: boolean; motivo: string | null };
  operaciones_duplicadas: { disponible: boolean; motivo: string | null };
};

const ETIQUETAS_ESTADO: Record<string, string> = {
  ABIERTO: "Abierto",
  PLAN_DE_ACCION: "Plan de acción",
  EN_REMEDIACION: "En remediación",
  EVIDENCIA_PRESENTADA: "Evidencia presentada",
  CERRADO: "Cerrado",
};

const ETIQUETAS_RIESGO: Record<string, string> = {
  ALTO: "Alto",
  MEDIO: "Medio",
  BAJO: "Bajo",
};

const ETIQUETAS_ACCION_ESTADO: Record<string, string> = {
  PENDIENTE: "Pendiente",
  EN_CURSO: "En curso",
  COMPLETADA: "Completada",
};

function renderConteos(
  conteos: Record<string, number> | undefined,
  etiquetas: Record<string, string>,
): string[] {
  if (!conteos) return [];
  return Object.entries(etiquetas)
    .filter(([codigo]) => conteos[codigo] !== undefined)
    .map(([codigo, etiqueta]) => `${etiqueta}: ${conteos[codigo]}`);
}

export function ReporteControlInternoPage() {
  const { activeCompanyId } = useCompany();
  const { notify } = useNotifications();

  const [filtroDesde, setFiltroDesde] = useState("");
  const [filtroHasta, setFiltroHasta] = useState("");
  const [periodoConsultado, setPeriodoConsultado] = useState<{
    desde: string;
    hasta: string;
  }>({ desde: "", hasta: "" });

  const reporteQuery = useQuery({
    queryKey: [
      "gobierno-control-interno",
      activeCompanyId,
      periodoConsultado.desde,
      periodoConsultado.hasta,
    ],
    placeholderData: keepPreviousData,
    queryFn: () => {
      const params = new URLSearchParams();
      if (periodoConsultado.desde) params.set("desde", periodoConsultado.desde);
      if (periodoConsultado.hasta) params.set("hasta", periodoConsultado.hasta);
      const qs = params.toString();
      return apiFetch<Reporte>(
        `/gobierno/control-interno/reporte${qs ? `?${qs}` : ""}`,
      );
    },
    enabled: Boolean(activeCompanyId),
    retry: false,
  });

  const [ultimo, setUltimo] = useState<Reporte | null>(null);
  useEffect(() => {
    if (reporteQuery.data) setUltimo(reporteQuery.data);
  }, [reporteQuery.data]);

  if (!activeCompanyId) {
    return (
      <PageContent>
        <EmptyState
          title="Sin empresa"
          description="Selecciona una empresa para continuar."
        />
      </PageContent>
    );
  }

  const aplicarFiltros = () => {
    setPeriodoConsultado({ desde: filtroDesde, hasta: filtroHasta });
  };

  const exportarCsv = async () => {
    try {
      const datos = reporteQuery.data ?? ultimo;
      if (!datos) return;
      const params = new URLSearchParams();
      if (datos.periodo.desde) params.set("desde", datos.periodo.desde);
      if (datos.periodo.hasta) params.set("hasta", datos.periodo.hasta);
      const qs = params.toString();
      await descargarArchivo(
        `/gobierno/control-interno/reporte.csv${qs ? `?${qs}` : ""}`,
        "control-interno",
      );
    } catch {
      notify({ type: "error", title: "No se pudo exportar el reporte" });
    }
  };

  const errorDesde =
    reporteQuery.isError && reporteQuery.error instanceof ApiError
      ? reporteQuery.error.fieldErrors.desde?.[0] ?? reporteQuery.error.message
      : undefined;

  if (reporteQuery.isLoading) {
    return (
      <PageContent>
        <PageHeader
          crumbs={[{ label: "Gobierno" }, { label: "Reporte de control interno" }]}
          title="Reporte de control interno"
          description="Conflictos de segregación de funciones, bloqueos de control y hallazgos con sus acciones correctivas (IR §12)."
        />
        <LoadingState />
      </PageContent>
    );
  }

  if (
    reporteQuery.isError &&
    (!(reporteQuery.error instanceof ApiError) || reporteQuery.error.status !== 422)
  ) {
    const error = reporteQuery.error as {
      status?: number;
      code?: string;
      message?: string;
      field_errors?: { desde?: string[] };
    };
    const mensaje =
      error?.status === 403
        ? "No tiene permiso para ver esta información"
        : "No se pudo cargar el reporte de control interno.";
    return (
      <PageContent>
        <PageHeader
          crumbs={[{ label: "Gobierno" }, { label: "Reporte de control interno" }]}
          title="Reporte de control interno"
          description="Conflictos de segregación de funciones, bloqueos de control y hallazgos con sus acciones correctivas (IR §12)."
        />
        <ErrorDeCarga
          message={mensaje}
          onRetry={() => reporteQuery.refetch()}
        />
      </PageContent>
    );
  }

  const datos = reporteQuery.data ?? ultimo;

  if (!datos) {
    return (
      <PageContent>
        <PageHeader
          crumbs={[{ label: "Gobierno" }, { label: "Reporte de control interno" }]}
          title="Reporte de control interno"
          description="Conflictos de segregación de funciones, bloqueos de control y hallazgos con sus acciones correctivas (IR §12)."
        />
        <EmptyState
          title="Sin datos"
          description="No hay información disponible."
        />
      </PageContent>
    );
  }

  return (
    <PageContent>
      <PageHeader
        crumbs={[{ label: "Gobierno" }, { label: "Reporte de control interno" }]}
        title="Reporte de control interno"
        description="Conflictos de segregación de funciones, bloqueos de control y hallazgos con sus acciones correctivas (IR §12)."
      />

      <section aria-label="Filtros del reporte" className="mb-8">
        <div className="flex flex-col gap-4 md:flex-row md:items-end">
          <FormField label="Desde" htmlFor="rc-desde" error={errorDesde}>
            <DateInput
              id="rc-desde"
              value={filtroDesde}
              onChange={(e) => setFiltroDesde(e.target.value)}
            />
          </FormField>
          <FormField label="Hasta" htmlFor="rc-hasta">
            <DateInput
              id="rc-hasta"
              value={filtroHasta}
              onChange={(e) => setFiltroHasta(e.target.value)}
            />
          </FormField>
          <Button onClick={aplicarFiltros}>Aplicar</Button>
          <Button variant="secondary" onClick={exportarCsv}>
            Exportar CSV
          </Button>
        </div>
        <p className="mt-4 text-sm text-text-800">
          Período: {formatearFechaDeNegocio(datos.periodo.desde)} a{" "}
          {formatearFechaDeNegocio(datos.periodo.hasta)}
        </p>
      </section>

      <section aria-label="Resumen" className="mb-8">
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <div className="rounded-lg border border-border-subtle p-4">
            <p className="text-2xl font-semibold text-text-900">
              {datos.conflictos_sod.total}
            </p>
            <p className="text-sm text-text-600">Conflictos de segregación</p>
          </div>
          <div className="rounded-lg border border-border-subtle p-4">
            <p className="text-2xl font-semibold text-text-900">
              {datos.bloqueos_identidad.total}
            </p>
            <p className="text-sm text-text-600">Bloqueos de identidad</p>
          </div>
          <div className="rounded-lg border border-border-subtle p-4">
            <p className="text-2xl font-semibold text-text-900">
              {datos.bloqueos_cierre.total}
            </p>
            <p className="text-sm text-text-600">Bloqueos de cierre</p>
          </div>
          <div className="rounded-lg border border-border-subtle p-4">
            <p className="text-2xl font-semibold text-text-900">
              {datos.hallazgos.disponible
                ? datos.hallazgos.acciones_vencidas.length
                : "—"}
            </p>
            <p className="text-sm text-text-600">Acciones vencidas</p>
          </div>
        </div>
      </section>

      <section aria-labelledby="sec-sod" className="mb-8">
        <h2 id="sec-sod" className="mb-4 text-lg font-semibold text-text-900">
          Conflictos de segregación de funciones
        </h2>
        <div className="mb-6 overflow-x-auto" tabIndex={0} role="region" aria-label="Conflictos por regla">
          <table className="w-full border-collapse text-sm">
            <caption className="sr-only">Conflictos por regla</caption>
            <thead>
              <tr className="border-b border-border-subtle text-left">
                <th scope="col" className="px-3 py-2 font-medium text-text-700">Regla</th>
                <th scope="col" className="px-3 py-2 font-medium text-text-700">Proceso</th>
                <th scope="col" className="px-3 py-2 font-medium text-text-700">Total</th>
              </tr>
            </thead>
            <tbody>
              {datos.conflictos_sod.por_regla.map((regla, idx) => (
                <tr key={`${regla.regla_codigo}-${regla.proceso}-${idx}`} className="border-b border-border-subtle">
                  <td className="px-3 py-2 break-words">
                    {regla.regla_codigo} · {regla.regla_nombre}
                  </td>
                  <td className="px-3 py-2 break-words">{regla.proceso_etiqueta}</td>
                  <td className="px-3 py-2">{regla.total}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {datos.conflictos_sod.eventos.length === 0 ? (
          <EmptyState
            title="Sin conflictos"
            description="No hay conflictos bloqueados en el período."
          />
        ) : (
          <div className="overflow-x-auto" tabIndex={0} role="region" aria-label="Conflictos recientes">
            <table className="w-full border-collapse text-sm">
              <caption className="sr-only">Conflictos recientes</caption>
              <thead>
                <tr className="border-b border-border-subtle text-left">
                  <th scope="col" className="px-3 py-2 font-medium text-text-700">Fecha</th>
                  <th scope="col" className="px-3 py-2 font-medium text-text-700">Usuario</th>
                  <th scope="col" className="px-3 py-2 font-medium text-text-700">Regla</th>
                  <th scope="col" className="px-3 py-2 font-medium text-text-700">Acción intentada</th>
                  <th scope="col" className="px-3 py-2 font-medium text-text-700">Acción previa</th>
                  <th scope="col" className="px-3 py-2 font-medium text-text-700">Detalle</th>
                </tr>
              </thead>
              <tbody>
                {datos.conflictos_sod.eventos.map((evento) => (
                  <tr key={evento.evento_id} className="border-b border-border-subtle">
                    <td className="px-3 py-2">{formatearInstante(evento.fecha)}</td>
                    <td className="px-3 py-2 break-words">{evento.usuario ?? "—"}</td>
                    <td className="px-3 py-2 break-words">
                      {evento.regla_codigo} · {evento.regla_nombre}
                    </td>
                    <td className="px-3 py-2 break-words">{evento.accion_etiqueta}</td>
                    <td className="px-3 py-2 break-words">{evento.accion_previa_etiqueta}</td>
                    <td className="px-3 py-2">
                      <Link
                        to={`/gobierno/bitacora/${evento.evento_id}`}
                        className="font-medium text-brand-700 underline"
                      >
                        Ver en la bitácora
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <section aria-labelledby="sec-identidad" className="mb-8">
        <h2 id="sec-identidad" className="mb-4 text-lg font-semibold text-text-900">
          Bloqueos de identidad institucional
        </h2>
        {datos.bloqueos_identidad.eventos.length === 0 ? (
          <EmptyState
            title="Sin bloqueos"
            description="No hay bloqueos de identidad en el período."
          />
        ) : (
          <div className="overflow-x-auto" tabIndex={0} role="region" aria-label="Bloqueos de identidad recientes">
            <table className="w-full border-collapse text-sm">
              <caption className="sr-only">Bloqueos de identidad recientes</caption>
              <thead>
                <tr className="border-b border-border-subtle text-left">
                  <th scope="col" className="px-3 py-2 font-medium text-text-700">Fecha</th>
                  <th scope="col" className="px-3 py-2 font-medium text-text-700">Usuario</th>
                  <th scope="col" className="px-3 py-2 font-medium text-text-700">Motivo</th>
                  <th scope="col" className="px-3 py-2 font-medium text-text-700">Detalle</th>
                </tr>
              </thead>
              <tbody>
                {datos.bloqueos_identidad.eventos.map((evento) => (
                  <tr key={evento.evento_id} className="border-b border-border-subtle">
                    <td className="px-3 py-2">{formatearInstante(evento.fecha)}</td>
                    <td className="px-3 py-2 break-words">{evento.usuario ?? "—"}</td>
                    <td className="px-3 py-2 break-words">{evento.etiqueta}</td>
                    <td className="px-3 py-2">
                      <Link
                        to={`/gobierno/bitacora/${evento.evento_id}`}
                        className="font-medium text-brand-700 underline"
                      >
                        Ver en la bitácora
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <section aria-labelledby="sec-cierre" className="mb-8">
        <h2 id="sec-cierre" className="mb-4 text-lg font-semibold text-text-900">
          Bloqueos de cierre
        </h2>
        {datos.bloqueos_cierre.eventos.length === 0 ? (
          <EmptyState
            title="Sin bloqueos"
            description="No hay cierres bloqueados en el período."
          />
        ) : (
          <div className="overflow-x-auto" tabIndex={0} role="region" aria-label="Bloqueos de cierre recientes">
            <table className="w-full border-collapse text-sm">
              <caption className="sr-only">Bloqueos de cierre recientes</caption>
              <thead>
                <tr className="border-b border-border-subtle text-left">
                  <th scope="col" className="px-3 py-2 font-medium text-text-700">Fecha</th>
                  <th scope="col" className="px-3 py-2 font-medium text-text-700">Usuario</th>
                  <th scope="col" className="px-3 py-2 font-medium text-text-700">Política</th>
                  <th scope="col" className="px-3 py-2 font-medium text-text-700">Acción</th>
                  <th scope="col" className="px-3 py-2 font-medium text-text-700">Objeto</th>
                  <th scope="col" className="px-3 py-2 font-medium text-text-700">Controles pendientes</th>
                  <th scope="col" className="px-3 py-2 font-medium text-text-700">Detalle</th>
                </tr>
              </thead>
              <tbody>
                {datos.bloqueos_cierre.eventos.map((evento) => (
                  <tr key={evento.evento_id} className="border-b border-border-subtle">
                    <td className="px-3 py-2">{formatearInstante(evento.fecha)}</td>
                    <td className="px-3 py-2 break-words">{evento.usuario ?? "—"}</td>
                    <td className="px-3 py-2 break-words">{evento.politica_codigo}</td>
                    <td className="px-3 py-2 break-words">{evento.accion_etiqueta}</td>
                    <td className="px-3 py-2 break-words">{evento.objeto_codigo}</td>
                    <td className="px-3 py-2 break-words">
                      {evento.controles
                        .map((c) => `${c.etiqueta}: ${c.pendientes}`)
                        .join("; ")}
                    </td>
                    <td className="px-3 py-2">
                      <Link
                        to={`/gobierno/bitacora/${evento.evento_id}`}
                        className="font-medium text-brand-700 underline"
                      >
                        Ver en la bitácora
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <section aria-labelledby="sec-hallazgos" className="mb-8">
        <h2 id="sec-hallazgos" className="mb-4 text-lg font-semibold text-text-900">
          Hallazgos y acciones correctivas
        </h2>
        {datos.hallazgos.disponible ? (
          <>
            <dl className="mb-6 grid grid-cols-1 gap-4 sm:grid-cols-3">
              <div>
                <dt className="text-sm font-medium text-text-900">Por estado</dt>
                <dd className="mt-1 space-y-1 text-sm text-text-800">
                  {renderConteos(datos.hallazgos.por_estado, ETIQUETAS_ESTADO).map(
                    (linea) => (
                      <p key={linea}>{linea}</p>
                    ),
                  )}
                </dd>
              </div>
              <div>
                <dt className="text-sm font-medium text-text-900">Por riesgo</dt>
                <dd className="mt-1 space-y-1 text-sm text-text-800">
                  {renderConteos(datos.hallazgos.por_riesgo, ETIQUETAS_RIESGO).map(
                    (linea) => (
                      <p key={linea}>{linea}</p>
                    ),
                  )}
                </dd>
              </div>
              <div>
                <dt className="text-sm font-medium text-text-900">Acciones por estado</dt>
                <dd className="mt-1 space-y-1 text-sm text-text-800">
                  {renderConteos(
                    datos.hallazgos.acciones_por_estado,
                    ETIQUETAS_ACCION_ESTADO,
                  ).map((linea) => (
                    <p key={linea}>{linea}</p>
                  ))}
                </dd>
              </div>
            </dl>
            {datos.hallazgos.acciones_vencidas.length === 0 ? (
              <EmptyState
                title="Sin acciones vencidas"
                description="No hay acciones vencidas."
              />
            ) : (
              <div className="overflow-x-auto" tabIndex={0} role="region" aria-label="Acciones vencidas">
                <table className="w-full border-collapse text-sm">
                  <caption className="sr-only">Acciones vencidas</caption>
                  <thead>
                    <tr className="border-b border-border-subtle text-left">
                      <th scope="col" className="px-3 py-2 font-medium text-text-700">Hallazgo</th>
                      <th scope="col" className="px-3 py-2 font-medium text-text-700">Acción</th>
                      <th scope="col" className="px-3 py-2 font-medium text-text-700">Responsable</th>
                      <th scope="col" className="px-3 py-2 font-medium text-text-700">Fecha objetivo</th>
                      <th scope="col" className="px-3 py-2 font-medium text-text-700">Avance</th>
                      <th scope="col" className="px-3 py-2 font-medium text-text-700">Días de atraso</th>
                    </tr>
                  </thead>
                  <tbody>
                    {datos.hallazgos.acciones_vencidas.map((accion) => (
                      <tr key={accion.hallazgo_id} className="border-b border-border-subtle">
                        <td className="px-3 py-2 break-words">
                          <Link
                            to={`/gobierno/hallazgos/${accion.hallazgo_id}`}
                            className="font-medium text-brand-700 underline"
                          >
                            {accion.hallazgo_codigo}
                          </Link>{" "}
                          {accion.hallazgo_titulo}
                        </td>
                        <td className="px-3 py-2 break-words">
                          {accion.accion_orden}. {accion.descripcion}
                        </td>
                        <td className="px-3 py-2 break-words">
                          {accion.cargo} · {accion.unidad}
                        </td>
                        <td className="px-3 py-2">
                          {formatearFechaDeNegocio(accion.fecha_objetivo)}
                        </td>
                        <td className="px-3 py-2">{accion.porcentaje} %</td>
                        <td className="px-3 py-2">{accion.dias_atraso}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </>
        ) : (
          <p className="text-sm text-text-800">{datos.hallazgos.motivo}</p>
        )}
      </section>

      <section aria-labelledby="sec-overrides" className="mb-8">
        <h2 id="sec-overrides" className="mb-4 text-lg font-semibold text-text-900">
          Excepciones a los controles (overrides)
        </h2>
        <p className="text-sm text-text-800">{datos.overrides.motivo}</p>
      </section>

      <section aria-labelledby="sec-duplicadas">
        <h2 id="sec-duplicadas" className="mb-4 text-lg font-semibold text-text-900">
          Operaciones duplicadas
        </h2>
        <p className="text-sm text-text-800">{datos.operaciones_duplicadas.motivo}</p>
      </section>

      <p className="mt-8 text-sm text-text-600">
        Generado el {formatearInstante(datos.generado_en)}
      </p>
    </PageContent>
  );
}
