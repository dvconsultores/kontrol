import { useState } from "react";
import { Link, useParams } from "react-router";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch, ApiError } from "@/api/client";
import { useAutoridad } from "@/app/autoridad/AutoridadContext";
import { useCompany } from "@/app/contexts/CompanyContext";
import { useNotifications } from "@/app/contexts/NotificationContext";
import { EmptyState } from "@/components/EmptyState";
import { ErrorState } from "@/components/ErrorState";
import { LoadingState } from "@/components/LoadingState";
import { PageContent } from "@/layout/PageContent";
import { PageHeader } from "@/components/PageHeader";
import { formatearFecha } from "@/i18n";
import { formatearFechaDeNegocio } from "@/lib/fecha-de-negocio";
import { AdjuntosPanel } from "@/modules/documentos/AdjuntosPanel";
import { EstructuraEjercicio } from "./EstructuraEjercicio";
import { ClasificadorEjercicio } from "./ClasificadorEjercicio";
import { AccionesEjercicio } from "./AccionesEjercicio";
import {
  CONSULTA_PRESUPUESTO,
  ETIQUETAS_ESTADO_EJERCICIO,
  ETIQUETAS_HISTORIA_EJERCICIO,
  RUTA_EJERCICIOS,
  type EjercicioDetalle,
  type EscribirEjercicio,
  type ImportarPartidas,
} from "./api";

export function EjercicioPresupuestarioPage() {
  const { ejercicioId } = useParams();
  const { activeCompanyId } = useCompany();
  const { tiene } = useAutoridad();
  const { notify } = useNotifications();
  const queryClient = useQueryClient();

  const claveDetalle = [...CONSULTA_PRESUPUESTO, activeCompanyId, "detalle", ejercicioId];

  const consultaDetalle = useQuery({
    queryKey: claveDetalle,
    queryFn: () => apiFetch<EjercicioDetalle>(`${RUTA_EJERCICIOS}/${ejercicioId}`),
    enabled: Boolean(activeCompanyId && ejercicioId),
    retry: false,
  });

  const puedeGestionar = tiene("gobierno_presupuesto:manage", "empresa");
  const puedeAprobar = tiene("gobierno_presupuesto:approve", "empresa");
  const puedeCerrar = tiene("gobierno_presupuesto:close", "empresa");

  const [erroresServidor, setErroresServidor] = useState<Record<string, string[]>>({});
  const [alerta, setAlerta] = useState<string | null>(null);

  const manejarError = (e: unknown) => {
    if (e instanceof ApiError && e.status === 409 && e.code === "GOV_BUDGET_YEAR_STALE") {
      setAlerta(
        "El ejercicio cambió desde que lo abrió. Se recargaron los datos; revise y vuelva a intentarlo.",
      );
      void queryClient.invalidateQueries({ queryKey: [...CONSULTA_PRESUPUESTO] });
      return;
    }
    if (e instanceof ApiError && e.status === 409) {
      setAlerta(e.message);
      return;
    }
    if (e instanceof ApiError && e.status === 422) {
      setErroresServidor(e.fieldErrors ?? {});
      setAlerta(e.message);
      if (e.code === "GOV_BUDGET_YEAR_INCOMPLETE") {
        void queryClient.invalidateQueries({ queryKey: [...CONSULTA_PRESUPUESTO] });
      }
      return;
    }
    if (e instanceof ApiError && e.status === 403) {
      notify({ type: "error", title: "No tiene permiso para esta acción" });
      return;
    }
    notify({
      type: "error",
      title: "No fue posible completar la acción.",
    });
  };

  const escribir: EscribirEjercicio = async (ruta, method, body) => {
    try {
      const nuevoDetalle = await apiFetch<EjercicioDetalle>(`${RUTA_EJERCICIOS}/${ejercicioId}${ruta}`, {
        method,
        body: body as Record<string, unknown> | undefined,
        ifMatch: String(consultaDetalle.data?.version),
      });
      queryClient.setQueryData(claveDetalle, nuevoDetalle);
      void queryClient.invalidateQueries({ queryKey: [...CONSULTA_PRESUPUESTO] });
      setErroresServidor({});
      setAlerta(null);
      return nuevoDetalle;
    } catch (e) {
      manejarError(e);
      throw e;
    }
  };

  const importar: ImportarPartidas = async (archivo) => {
    try {
      const datos = new FormData();
      datos.append("archivo", archivo);
      const nuevoDetalle = await apiFetch<EjercicioDetalle>(
        `${RUTA_EJERCICIOS}/${ejercicioId}/clasificador/importar`,
        {
          method: "POST",
          body: datos,
          ifMatch: String(consultaDetalle.data?.version),
        },
      );
      queryClient.setQueryData(claveDetalle, nuevoDetalle);
      void queryClient.invalidateQueries({ queryKey: [...CONSULTA_PRESUPUESTO] });
      setErroresServidor({});
      setAlerta(null);
      return nuevoDetalle;
    } catch (e) {
      manejarError(e);
      throw e;
    }
  };

  const cabeceraSinDetalle = (
    <PageHeader
      crumbs={[
        { label: "Gobierno" },
        {
          label: "Presupuesto",
          to: RUTA_EJERCICIOS,
        },
        { label: "Ejercicio presupuestario" },
      ]}
      title="Ejercicio presupuestario"
    />
  );

  if (consultaDetalle.isLoading) {
    return (
      <PageContent>
        {cabeceraSinDetalle}
        <LoadingState label="Cargando ejercicio presupuestario…" />
      </PageContent>
    );
  }

  if (consultaDetalle.isError) {
    const error = consultaDetalle.error;
    if (error instanceof ApiError && error.status === 403 && error.code === "MODULE_NOT_ENTITLED") {
      return (
        <PageContent>
          {cabeceraSinDetalle}
          <EmptyState
            title="Módulo no habilitado"
            description="Su empresa no tiene contratado el módulo de Gobierno."
            action={<Link to={RUTA_EJERCICIOS}>Volver a Ejercicios presupuestarios</Link>}
          />
        </PageContent>
      );
    }
    if (error instanceof ApiError && error.status === 403) {
      return (
        <PageContent>
          {cabeceraSinDetalle}
          <EmptyState
            title="Sin acceso"
            description="No tiene permiso para ver este ejercicio presupuestario."
            action={<Link to={RUTA_EJERCICIOS}>Volver a Ejercicios presupuestarios</Link>}
          />
        </PageContent>
      );
    }
    return (
      <PageContent>
        {cabeceraSinDetalle}
        <ErrorState
          message="No fue posible cargar el ejercicio presupuestario."
          onRetry={() => void consultaDetalle.refetch()}
        />
      </PageContent>
    );
  }

  const detalle = consultaDetalle.data;
  if (!detalle) {
    return (
      <PageContent>
        {cabeceraSinDetalle}
        <EmptyState
          title="Ejercicio no encontrado"
          description="No existe el ejercicio presupuestario solicitado."
          action={<Link to={RUTA_EJERCICIOS}>Volver a Ejercicios presupuestarios</Link>}
        />
      </PageContent>
    );
  }

  const cabecera = (
    <PageHeader
      crumbs={[
        { label: "Gobierno" },
        {
          label: "Presupuesto",
          to: RUTA_EJERCICIOS,
        },
        { label: `Ejercicio ${detalle.anio}`, to: `${RUTA_EJERCICIOS}/${detalle.id}` },
      ]}
      title={`Ejercicio presupuestario ${detalle.anio}`}
      status={ETIQUETAS_ESTADO_EJERCICIO[detalle.estado]}
    />
  );

  const detalleResumen = (valor: string | null, formatearCivil = false) => {
    if (!valor) return "—";
    return formatearCivil ? formatearFechaDeNegocio(valor) : formatearFecha(valor);
  };

  return (
    <PageContent>
      {cabecera}

      {alerta ? (
        <div role="alert" className="mb-6 rounded-md border border-warning-600 bg-warning-100 p-3 text-sm text-text-900">
          {alerta}
        </div>
      ) : null}

      <section aria-labelledby="resumen-titulo" className="mb-8">
        <h2 id="resumen-titulo" className="mb-4 text-lg font-semibold text-text-900">
          Resumen
        </h2>
        <dl className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <div>
            <dt className="text-sm font-medium text-text-700">Estado</dt>
            <dd className="text-sm text-text-900">{ETIQUETAS_ESTADO_EJERCICIO[detalle.estado]}</dd>
          </div>
          <div>
            <dt className="text-sm font-medium text-text-700">Moneda funcional</dt>
            <dd className="text-sm text-text-900">{detalle.moneda_funcional}</dd>
          </div>
          <div>
            <dt className="text-sm font-medium text-text-700">Precompromiso</dt>
            <dd className="text-sm text-text-900">
              {detalle.precompromiso_activo ? "Activo" : "No activo"}
              {detalle.precompromiso_desde
                ? ` desde ${formatearFechaDeNegocio(detalle.precompromiso_desde)}`
                : ""}
            </dd>
          </div>
          <div>
            <dt className="text-sm font-medium text-text-700">Fijado el</dt>
            <dd className="text-sm text-text-900">{detalleResumen(detalle.fijado_en, true)}</dd>
          </div>
          <div>
            <dt className="text-sm font-medium text-text-700">Cerrado el</dt>
            <dd className="text-sm text-text-900">{detalleResumen(detalle.cerrado_en, true)}</dd>
          </div>
        </dl>
        {detalle.reconduccion_definitiva ? (
          <p className="mt-4 rounded-md border border-info-600 bg-info-100 p-3 text-sm text-text-900">
            La reconducción ya es definitiva (LOPPM art. 236)
          </p>
        ) : null}
        {detalle.congelado ? (
          <p className="mt-4 rounded-md border border-info-600 bg-info-100 p-3 text-sm text-text-900">
            El ejercicio está fijado: su estructura y su clasificador ya no se pueden modificar
          </p>
        ) : null}
      </section>

      {detalle.estado === "BORRADOR" && detalle.faltantes.length > 0 ? (
        <section aria-labelledby="pendiente-titulo" className="mb-8">
          <h2 id="pendiente-titulo" className="mb-4 text-lg font-semibold text-text-900">
            Pendiente para fijar
          </h2>
          <ul className="list-inside list-disc space-y-1 text-sm text-text-900">
            {detalle.faltantes.map((falta) => (
              <li key={falta}>{falta}</li>
            ))}
          </ul>
        </section>
      ) : null}

      <EstructuraEjercicio
        detalle={detalle}
        puedeGestionar={puedeGestionar}
        escribir={escribir}
        erroresServidor={erroresServidor}
      />

      <ClasificadorEjercicio
        detalle={detalle}
        puedeGestionar={puedeGestionar}
        escribir={escribir}
        importar={importar}
        erroresServidor={erroresServidor}
      />

      <AccionesEjercicio
        detalle={detalle}
        puedeAprobar={puedeAprobar}
        puedeCerrar={puedeCerrar}
        escribir={escribir}
        erroresServidor={erroresServidor}
      />

      <section aria-labelledby="fundamento-titulo" className="mb-8">
        <h2 id="fundamento-titulo" className="mb-4 text-lg font-semibold text-text-900">
          Fundamento
        </h2>
        {detalle.fundamentos.length === 0 ? (
          <p className="text-sm text-text-700">Aún no hay fundamento registrado.</p>
        ) : (
          <div className="relative overflow-x-auto" tabIndex={0} role="region" aria-label="Tabla de fundamentos del ejercicio">
            <table className="w-full border-collapse text-left">
              <caption className="sr-only">Fundamento del ejercicio</caption>
              <thead>
                <tr className="border-b border-border-subtle">
                  <th scope="col" className="px-3 py-2 text-sm font-medium text-text-700">Tipo</th>
                  <th scope="col" className="px-3 py-2 text-sm font-medium text-text-700">Referencia</th>
                  <th scope="col" className="px-3 py-2 text-sm font-medium text-text-700">Fecha</th>
                  <th scope="col" className="px-3 py-2 text-sm font-medium text-text-700">Huella</th>
                </tr>
              </thead>
              <tbody>
                {detalle.fundamentos.map((fundamento, indice) => (
                  <tr key={`${fundamento.tipo}-${indice}`} className="border-b border-border-subtle">
                    <td className="px-3 py-2 text-sm text-text-900">
                      {fundamento.tipo === "ORDENANZA" ? "Ordenanza" : "Reconducción"}
                    </td>
                    <td className="px-3 py-2 text-sm text-text-900">{fundamento.referencia}</td>
                    <td className="px-3 py-2 text-sm text-text-900">
                      {formatearFechaDeNegocio(fundamento.fecha)}
                    </td>
                    <td className="px-3 py-2 text-sm text-text-900">
                      <span title={fundamento.huella}>
                        {fundamento.huella.slice(0, 12)}
                        {fundamento.huella.length > 12 ? "…" : ""}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <section aria-labelledby="documentos-titulo" className="mb-8">
        <AdjuntosPanel
          resourceType="GovernmentBudgetYear"
          resourceId={detalle.id}
          title="Documentos del ejercicio"
          onChange={() => void consultaDetalle.refetch()}
        />
      </section>

      <section aria-labelledby="historia-titulo">
        <h2 id="historia-titulo" className="mb-4 text-lg font-semibold text-text-900">
          Historia
        </h2>
        <div className="relative overflow-x-auto" tabIndex={0} role="region" aria-label="Tabla de historia del ejercicio">
          <table className="w-full border-collapse text-left">
            <caption className="sr-only">Historia del ejercicio</caption>
            <thead>
              <tr className="border-b border-border-subtle">
                <th scope="col" className="px-3 py-2 text-sm font-medium text-text-700">Evento</th>
                <th scope="col" className="px-3 py-2 text-sm font-medium text-text-700">Fecha</th>
                <th scope="col" className="px-3 py-2 text-sm font-medium text-text-700">Detalle</th>
              </tr>
            </thead>
            <tbody>
              {detalle.historia.map((h, indice) => {
                const detalleTexto = h.detalle
                  ? Object.entries(h.detalle)
                      .map(([clave, valor]) => `${clave}: ${String(valor)}`)
                      .join(" · ")
                  : "—";
                return (
                  <tr key={`${h.tipo}-${h.en}-${indice}`} className="border-b border-border-subtle">
                    <td className="px-3 py-2 text-sm text-text-900">
                      {ETIQUETAS_HISTORIA_EJERCICIO[h.tipo] ?? h.tipo}
                    </td>
                    <td className="px-3 py-2 text-sm text-text-900">{formatearFecha(h.en)}</td>
                    <td className="px-3 py-2 text-sm text-text-900">{detalleTexto}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </section>
    </PageContent>
  );
}
