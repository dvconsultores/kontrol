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

type DistribucionItem = {
  codigo: string | null;
  etiqueta: string;
  total: number;
};

type UnidadItem = {
  unidad_id: string;
  unidad_nombre: string;
  total: number;
};

type ProveedorItem = {
  documento: string;
  nombre: string;
  ofertas: number;
  adjudicaciones: number;
};

type TiemposItem = {
  codigo: string | null;
  etiqueta: string;
  expedientes: number;
  inicio_recepcion: number | null;
  recepcion_evaluacion: number | null;
  evaluacion_decision: number | null;
  inicio_cierre: number | null;
};

type HitoDesviacion = {
  expediente_id: string;
  expediente_numero: string;
  hito: string;
  fecha_prevista: string;
  fecha_real: string | null;
  estado: "CON_ATRASO" | "VENCIDO";
  dias: number;
};

type Reporte = {
  periodo: { desde: string; hasta: string };
  generado_en: string;
  totales: {
    expedientes: number;
    abiertos: number;
    cerrados: number;
    descartados: number;
  };
  por_modalidad: DistribucionItem[];
  por_estado: DistribucionItem[];
  por_tipo: DistribucionItem[];
  por_unidad: UnidadItem[];
  resultados: DistribucionItem[];
  proveedores: ProveedorItem[];
  tiempos: {
    por_modalidad: TiemposItem[];
    global: {
      inicio_recepcion: number | null;
      recepcion_evaluacion: number | null;
      evaluacion_decision: number | null;
      inicio_cierre: number | null;
    };
  };
  desviaciones: {
    a_tiempo: number;
    con_atraso: number;
    vencidos: number;
    hitos: HitoDesviacion[];
  };
  monto: {
    disponible: boolean;
    motivo: string | null;
    nota: string;
    por_moneda: {
      moneda: string;
      total_con_tributos: string;
      monto_sin_iva: string;
      adjudicaciones: number;
    }[];
    adjudicaciones_con_monto: number;
    adjudicaciones_sin_monto: number;
  };
};

function formatearDias(valor: number | null): string {
  if (valor === null) return "—";
  return valor.toLocaleString("es-VE", {
    minimumFractionDigits: 1,
    maximumFractionDigits: 1,
  });
}

export function ReporteContratacionesPage() {
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
      "gobierno-reporte-contrataciones",
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
        `/gobierno/contrataciones/reporte${qs ? `?${qs}` : ""}`,
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
        `/gobierno/contrataciones/reporte.csv${qs ? `?${qs}` : ""}`,
        "contrataciones",
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
          crumbs={[{ label: "Gobierno" }, { label: "Reporte de contrataciones" }]}
          title="Reporte de contrataciones"
          description="Expedientes por modalidad, estado, tipo y unidad, proveedores, tiempos y desviaciones de hitos (IR §12)."
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
        : "No se pudo cargar el reporte de contrataciones.";
    return (
      <PageContent>
        <PageHeader
          crumbs={[{ label: "Gobierno" }, { label: "Reporte de contrataciones" }]}
          title="Reporte de contrataciones"
          description="Expedientes por modalidad, estado, tipo y unidad, proveedores, tiempos y desviaciones de hitos (IR §12)."
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
          crumbs={[{ label: "Gobierno" }, { label: "Reporte de contrataciones" }]}
          title="Reporte de contrataciones"
          description="Expedientes por modalidad, estado, tipo y unidad, proveedores, tiempos y desviaciones de hitos (IR §12)."
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
        crumbs={[{ label: "Gobierno" }, { label: "Reporte de contrataciones" }]}
        title="Reporte de contrataciones"
        description="Expedientes por modalidad, estado, tipo y unidad, proveedores, tiempos y desviaciones de hitos (IR §12)."
      />

      <section aria-label="Filtros del reporte" className="mb-8">
        <div className="flex flex-col gap-4 md:flex-row md:items-end">
          <FormField label="Desde" htmlFor="rp-desde" error={errorDesde}>
            <DateInput
              id="rp-desde"
              value={filtroDesde}
              onChange={(e) => setFiltroDesde(e.target.value)}
            />
          </FormField>
          <FormField label="Hasta" htmlFor="rp-hasta">
            <DateInput
              id="rp-hasta"
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
              {datos.totales.expedientes}
            </p>
            <p className="text-sm text-text-600">Expedientes</p>
          </div>
          <div className="rounded-lg border border-border-subtle p-4">
            <p className="text-2xl font-semibold text-text-900">
              {datos.totales.abiertos}
            </p>
            <p className="text-sm text-text-600">Abiertos</p>
          </div>
          <div className="rounded-lg border border-border-subtle p-4">
            <p className="text-2xl font-semibold text-text-900">
              {datos.totales.cerrados}
            </p>
            <p className="text-sm text-text-600">Cerrados</p>
          </div>
          <div className="rounded-lg border border-border-subtle p-4">
            <p className="text-2xl font-semibold text-text-900">
              {datos.totales.descartados}
            </p>
            <p className="text-sm text-text-600">Descartados</p>
          </div>
        </div>
      </section>

      <section aria-labelledby="sec-distribucion" className="mb-8">
        <h2 id="sec-distribucion" className="mb-4 text-lg font-semibold text-text-900">
          Distribución
        </h2>
        <div className="mb-6 overflow-x-auto" tabIndex={0} role="region" aria-label="Por modalidad">
          <table className="w-full border-collapse text-sm">
            <caption className="sr-only">Por modalidad</caption>
            <thead>
              <tr className="border-b border-border-subtle text-left">
                <th scope="col" className="px-3 py-2 font-medium text-text-700">Modalidad</th>
                <th scope="col" className="px-3 py-2 font-medium text-text-700">Expedientes</th>
              </tr>
            </thead>
            <tbody>
              {datos.por_modalidad.map((item, idx) => (
                <tr key={`modalidad-${item.codigo ?? "nula"}-${idx}`} className="border-b border-border-subtle">
                  <td className="px-3 py-2 break-words">{item.etiqueta}</td>
                  <td className="px-3 py-2">{item.total}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="mb-6 overflow-x-auto" tabIndex={0} role="region" aria-label="Por estado">
          <table className="w-full border-collapse text-sm">
            <caption className="sr-only">Por estado</caption>
            <thead>
              <tr className="border-b border-border-subtle text-left">
                <th scope="col" className="px-3 py-2 font-medium text-text-700">Estado</th>
                <th scope="col" className="px-3 py-2 font-medium text-text-700">Expedientes</th>
              </tr>
            </thead>
            <tbody>
              {datos.por_estado.map((item, idx) => (
                <tr key={`estado-${item.codigo}-${idx}`} className="border-b border-border-subtle">
                  <td className="px-3 py-2 break-words">{item.etiqueta}</td>
                  <td className="px-3 py-2">{item.total}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="mb-6 overflow-x-auto" tabIndex={0} role="region" aria-label="Por tipo de contratación">
          <table className="w-full border-collapse text-sm">
            <caption className="sr-only">Por tipo de contratación</caption>
            <thead>
              <tr className="border-b border-border-subtle text-left">
                <th scope="col" className="px-3 py-2 font-medium text-text-700">Tipo</th>
                <th scope="col" className="px-3 py-2 font-medium text-text-700">Expedientes</th>
              </tr>
            </thead>
            <tbody>
              {datos.por_tipo.map((item, idx) => (
                <tr key={`tipo-${item.codigo}-${idx}`} className="border-b border-border-subtle">
                  <td className="px-3 py-2 break-words">{item.etiqueta}</td>
                  <td className="px-3 py-2">{item.total}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="mb-6 overflow-x-auto" tabIndex={0} role="region" aria-label="Por unidad">
          <table className="w-full border-collapse text-sm">
            <caption className="sr-only">Por unidad</caption>
            <thead>
              <tr className="border-b border-border-subtle text-left">
                <th scope="col" className="px-3 py-2 font-medium text-text-700">Unidad</th>
                <th scope="col" className="px-3 py-2 font-medium text-text-700">Expedientes</th>
              </tr>
            </thead>
            <tbody>
              {datos.por_unidad.map((item) => (
                <tr key={item.unidad_id} className="border-b border-border-subtle">
                  <td className="px-3 py-2 break-words">{item.unidad_nombre}</td>
                  <td className="px-3 py-2">{item.total}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="overflow-x-auto" tabIndex={0} role="region" aria-label="Resultado de la decisión">
          <table className="w-full border-collapse text-sm">
            <caption className="sr-only">Resultado de la decisión</caption>
            <thead>
              <tr className="border-b border-border-subtle text-left">
                <th scope="col" className="px-3 py-2 font-medium text-text-700">Resultado</th>
                <th scope="col" className="px-3 py-2 font-medium text-text-700">Expedientes</th>
              </tr>
            </thead>
            <tbody>
              {datos.resultados.map((item, idx) => (
                <tr key={`resultado-${item.codigo}-${idx}`} className="border-b border-border-subtle">
                  <td className="px-3 py-2 break-words">{item.etiqueta}</td>
                  <td className="px-3 py-2">{item.total}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section aria-labelledby="sec-proveedores" className="mb-8">
        <h2 id="sec-proveedores" className="mb-4 text-lg font-semibold text-text-900">
          Proveedores
        </h2>
        {datos.proveedores.length === 0 ? (
          <EmptyState
            title="Sin ofertas"
            description="No hay ofertas en el período."
          />
        ) : (
          <div className="overflow-x-auto" tabIndex={0} role="region" aria-label="Ofertas y adjudicaciones por proveedor">
            <table className="w-full border-collapse text-sm">
              <caption className="sr-only">Ofertas y adjudicaciones por proveedor</caption>
              <thead>
                <tr className="border-b border-border-subtle text-left">
                  <th scope="col" className="px-3 py-2 font-medium text-text-700">Documento</th>
                  <th scope="col" className="px-3 py-2 font-medium text-text-700">Proveedor</th>
                  <th scope="col" className="px-3 py-2 font-medium text-text-700">Ofertas</th>
                  <th scope="col" className="px-3 py-2 font-medium text-text-700">Adjudicaciones</th>
                </tr>
              </thead>
              <tbody>
                {datos.proveedores.map((proveedor) => (
                  <tr key={proveedor.documento} className="border-b border-border-subtle">
                    <td className="px-3 py-2 break-words">{proveedor.documento}</td>
                    <td className="px-3 py-2 break-words">{proveedor.nombre}</td>
                    <td className="px-3 py-2">{proveedor.ofertas}</td>
                    <td className="px-3 py-2">{proveedor.adjudicaciones}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <section aria-labelledby="sec-tiempos" className="mb-8">
        <h2 id="sec-tiempos" className="mb-4 text-lg font-semibold text-text-900">
          Tiempos
        </h2>
        <div className="overflow-x-auto" tabIndex={0} role="region" aria-label="Días promedio por modalidad">
          <table className="w-full border-collapse text-sm">
            <caption className="sr-only">Días promedio por modalidad</caption>
            <thead>
              <tr className="border-b border-border-subtle text-left">
                <th scope="col" className="px-3 py-2 font-medium text-text-700">Modalidad</th>
                <th scope="col" className="px-3 py-2 font-medium text-text-700">Expedientes</th>
                <th scope="col" className="px-3 py-2 font-medium text-text-700">Inicio a recepción</th>
                <th scope="col" className="px-3 py-2 font-medium text-text-700">Recepción a evaluación</th>
                <th scope="col" className="px-3 py-2 font-medium text-text-700">Evaluación a decisión</th>
                <th scope="col" className="px-3 py-2 font-medium text-text-700">Inicio a cierre</th>
              </tr>
            </thead>
            <tbody>
              {datos.tiempos.por_modalidad.map((item, idx) => (
                <tr key={`tiempos-modalidad-${item.codigo ?? "nula"}-${idx}`} className="border-b border-border-subtle">
                  <td className="px-3 py-2 break-words">{item.etiqueta}</td>
                  <td className="px-3 py-2">{item.expedientes}</td>
                  <td className="px-3 py-2">{formatearDias(item.inicio_recepcion)}</td>
                  <td className="px-3 py-2">{formatearDias(item.recepcion_evaluacion)}</td>
                  <td className="px-3 py-2">{formatearDias(item.evaluacion_decision)}</td>
                  <td className="px-3 py-2">{formatearDias(item.inicio_cierre)}</td>
                </tr>
              ))}
              <tr className="border-b border-border-subtle font-medium">
                <td className="px-3 py-2 break-words">Todas las modalidades</td>
                <td className="px-3 py-2">{datos.totales.expedientes}</td>
                <td className="px-3 py-2">{formatearDias(datos.tiempos.global.inicio_recepcion)}</td>
                <td className="px-3 py-2">{formatearDias(datos.tiempos.global.recepcion_evaluacion)}</td>
                <td className="px-3 py-2">{formatearDias(datos.tiempos.global.evaluacion_decision)}</td>
                <td className="px-3 py-2">{formatearDias(datos.tiempos.global.inicio_cierre)}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <section aria-labelledby="sec-desviaciones" className="mb-8">
        <h2 id="sec-desviaciones" className="mb-4 text-lg font-semibold text-text-900">
          Desviaciones de hitos
        </h2>
        <div className="mb-6 grid grid-cols-1 gap-4 sm:grid-cols-3">
          <div className="rounded-lg border border-border-subtle p-4">
            <p className="text-2xl font-semibold text-text-900">
              {datos.desviaciones.a_tiempo}
            </p>
            <p className="text-sm text-text-600">A tiempo</p>
          </div>
          <div className="rounded-lg border border-border-subtle p-4">
            <p className="text-2xl font-semibold text-text-900">
              {datos.desviaciones.con_atraso}
            </p>
            <p className="text-sm text-text-600">Con atraso</p>
          </div>
          <div className="rounded-lg border border-border-subtle p-4">
            <p className="text-2xl font-semibold text-text-900">
              {datos.desviaciones.vencidos}
            </p>
            <p className="text-sm text-text-600">Vencidos</p>
          </div>
        </div>
        {datos.desviaciones.hitos.length === 0 ? (
          <EmptyState
            title="Sin desviaciones"
            description="No hay hitos con desviación."
          />
        ) : (
          <div className="overflow-x-auto" tabIndex={0} role="region" aria-label="Hitos con desviación">
            <table className="w-full border-collapse text-sm">
              <caption className="sr-only">Hitos con desviación</caption>
              <thead>
                <tr className="border-b border-border-subtle text-left">
                  <th scope="col" className="px-3 py-2 font-medium text-text-700">Expediente</th>
                  <th scope="col" className="px-3 py-2 font-medium text-text-700">Hito</th>
                  <th scope="col" className="px-3 py-2 font-medium text-text-700">Fecha prevista</th>
                  <th scope="col" className="px-3 py-2 font-medium text-text-700">Fecha real</th>
                  <th scope="col" className="px-3 py-2 font-medium text-text-700">Situación</th>
                  <th scope="col" className="px-3 py-2 font-medium text-text-700">Días</th>
                </tr>
              </thead>
              <tbody>
                {datos.desviaciones.hitos.map((hito) => (
                  <tr key={`${hito.expediente_id}-${hito.hito}`} className="border-b border-border-subtle">
                    <td className="px-3 py-2 break-words">
                      <Link
                        to={`/gobierno/contrataciones/expedientes/${hito.expediente_id}`}
                        className="font-medium text-brand-700 underline"
                      >
                        {hito.expediente_numero}
                      </Link>
                    </td>
                    <td className="px-3 py-2 break-words">{hito.hito}</td>
                    <td className="px-3 py-2">
                      {formatearFechaDeNegocio(hito.fecha_prevista)}
                    </td>
                    <td className="px-3 py-2">
                      {hito.fecha_real ? formatearFechaDeNegocio(hito.fecha_real) : "—"}
                    </td>
                    <td className="px-3 py-2">
                      {hito.estado === "VENCIDO" ? "Vencido" : "Con atraso"}
                    </td>
                    <td className="px-3 py-2">{hito.dias}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <section aria-labelledby="sec-monto">
        <h2 id="sec-monto" className="mb-4 text-lg font-semibold text-text-900">
          Monto
        </h2>
        {datos.monto.disponible ? (
          <>
            <div
              className="overflow-x-auto"
              tabIndex={0}
              role="region"
              aria-label="Monto declarado por moneda"
            >
              <table className="min-w-full text-sm text-text-900">
                <thead>
                  <tr className="text-left text-xs text-text-600">
                    <th className="py-1 pr-3 font-medium">Moneda</th>
                    <th className="py-1 pr-3 font-medium">
                      Total con tributos
                    </th>
                    <th className="py-1 pr-3 font-medium">Monto sin IVA</th>
                    <th className="py-1 font-medium">Adjudicaciones</th>
                  </tr>
                </thead>
                <tbody>
                  {datos.monto.por_moneda.map((fila) => (
                    <tr
                      key={fila.moneda}
                      className="border-t border-border-subtle"
                    >
                      <td className="py-1 pr-3">{fila.moneda}</td>
                      <td className="py-1 pr-3">
                        {fila.total_con_tributos} {fila.moneda}
                      </td>
                      <td className="py-1 pr-3">
                        {fila.monto_sin_iva} {fila.moneda}
                      </td>
                      <td className="py-1">{fila.adjudicaciones}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p className="mt-2 text-sm text-text-800">
              Adjudicaciones sin monto declarado:{" "}
              {datos.monto.adjudicaciones_sin_monto}
            </p>
          </>
        ) : (
          <p className="text-sm text-text-800">{datos.monto.motivo}</p>
        )}
        <p className="mt-2 text-xs text-text-600">{datos.monto.nota}</p>
      </section>

      <p className="mt-8 text-sm text-text-600">
        Generado el {formatearInstante(datos.generado_en)}
      </p>
    </PageContent>
  );
}