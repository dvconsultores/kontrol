import { Link, useParams } from "react-router";
import { useQuery } from "@tanstack/react-query";
import { Download } from "lucide-react";

import { apiFetch, ApiError } from "@/api/client";
import { descargarArchivo } from "@/api/descargas";
import { useCompany } from "@/app/contexts/CompanyContext";
import { useAutoridad } from "@/app/autoridad/AutoridadContext";
import { useNotifications } from "@/app/contexts/NotificationContext";
import { PageContent } from "@/layout/PageContent";
import { PageHeader } from "@/components/PageHeader";
import { AsyncButton } from "@/components/AsyncButton";

import { EmptyState } from "@/components/EmptyState";
import { ErrorState } from "@/components/ErrorState";
import { LoadingState } from "@/components/LoadingState";
import { formatearFecha } from "@/i18n";
import { formatearFechaDeNegocio } from "@/lib/fecha-de-negocio";
import {
  CONSULTA_AUDITORIA,
  ETIQUETA_METODO_MUESTREO,
  type AuditoriaMuestraDetalle,
} from "@/modules/gobierno/api";

export function MuestraPage(): React.JSX.Element {
  const { muestraId } = useParams();
  const { activeCompanyId } = useCompany();
  const { tiene } = useAutoridad();
  const { notify } = useNotifications();
  const puedeVer = tiene("gobierno_auditoria:view", "empresa");

  const consultaMuestra = useQuery({
    queryKey: [...CONSULTA_AUDITORIA, activeCompanyId, "muestra", muestraId],
    queryFn: () =>
      apiFetch<AuditoriaMuestraDetalle>(
        `/gobierno/auditoria/muestras/${muestraId}`,
      ),
    enabled:
      puedeVer && Boolean(activeCompanyId) && Boolean(muestraId),
    retry: false,
  });

  const exportarCsv = async (): Promise<void> => {
    if (!consultaMuestra.data) return;
    const muestra = consultaMuestra.data;
    try {
      await descargarArchivo(
        `/gobierno/auditoria/muestras/${muestra.id}/exportar`,
        `muestra-${muestra.codigo}.csv`,
      );
      notify({ type: "success", title: "Muestra exportada" });
    } catch {
      notify({ type: "error", title: "No fue posible exportar" });
    }
  };

  const cabeceraSinDatos = (
    <PageHeader
      crumbs={[
        { label: "Gobierno" },
        { label: "Auditoría institucional", to: "/gobierno/auditoria" },
      ]}
      title="Muestra de auditoría"
    />
  );

  if (!puedeVer) {
    return (
      <PageContent>
        {cabeceraSinDatos}
        <EmptyState
          title="Sin acceso"
          description="No tiene permiso para ver las muestras de auditoría."
        />
      </PageContent>
    );
  }

  if (consultaMuestra.isLoading) {
    return (
      <PageContent>
        {cabeceraSinDatos}
        <LoadingState label="Cargando muestra…" />
      </PageContent>
    );
  }

  if (consultaMuestra.isError) {
    const error = consultaMuestra.error;
    if (
      error instanceof ApiError &&
      error.status === 403 &&
      error.code === "MODULE_NOT_ENTITLED"
    ) {
      return (
        <PageContent>
          {cabeceraSinDatos}
          <EmptyState
            title="Módulo no disponible"
            description="Su empresa no tiene contratado el módulo de Gobierno."
            action={
              <Link to="/gobierno/auditoria">
                Volver a Auditoría institucional
              </Link>
            }
          />
        </PageContent>
      );
    }
    if (error instanceof ApiError && error.status === 403) {
      return (
        <PageContent>
          {cabeceraSinDatos}
          <EmptyState
            title="Sin acceso"
            description="No tiene permiso para ver las muestras de auditoría."
          />
        </PageContent>
      );
    }
    if (
      error instanceof ApiError &&
      error.status === 404 &&
      error.code === "GOV_AUDIT_SAMPLE_NOT_FOUND"
    ) {
      return (
        <PageContent>
          {cabeceraSinDatos}
          <EmptyState
            title="Muestra no encontrada"
            action={
              <Link to="/gobierno/auditoria">
                Volver a Auditoría institucional
              </Link>
            }
          />
        </PageContent>
      );
    }
    return (
      <PageContent>
        {cabeceraSinDatos}
        <ErrorState
          message="No fue posible cargar la muestra."
          onRetry={() => void consultaMuestra.refetch()}
        />
      </PageContent>
    );
  }

  const muestra = consultaMuestra.data;

  if (!muestra) {
    return (
      <PageContent>
        {cabeceraSinDatos}
        <ErrorState
          message="No fue posible cargar la muestra."
          onRetry={() => void consultaMuestra.refetch()}
        />
      </PageContent>
    );
  }

  const cabecera = (
    <PageHeader
      crumbs={[
        { label: "Gobierno" },
        { label: "Auditoría institucional", to: "/gobierno/auditoria" },
      ]}
      title={`Muestra ${muestra.codigo}`}
      description={muestra.titulo}
      actions={
        <AsyncButton onClick={exportarCsv} variant="secondary">
          <Download className="mr-2 h-4 w-4" aria-hidden="true" />
          Exportar CSV
        </AsyncButton>
      }
    />
  );

  const filtros = muestra.filtros ?? {};

  return (
    <PageContent>
      {cabecera}
      <section aria-labelledby="definicion-muestra">
        <h2
          id="definicion-muestra"
          className="mb-3 text-lg font-semibold text-text-900"
        >
          Definición de la muestra
        </h2>
        <dl className="grid grid-cols-1 gap-x-6 gap-y-3 md:grid-cols-2">
          <div>
            <dt className="text-sm font-medium text-text-600">Código</dt>
            <dd className="text-sm text-text-900">{muestra.codigo}</dd>
          </div>
          <div>
            <dt className="text-sm font-medium text-text-600">Método</dt>
            <dd className="text-sm text-text-900">
              {ETIQUETA_METODO_MUESTREO[muestra.metodo]}
            </dd>
          </div>
          {muestra.metodo === "ALEATORIA" && (
            <div>
              <dt className="text-sm font-medium text-text-600">Semilla</dt>
              <dd className="text-sm text-text-900">
                {muestra.semilla ?? "—"}
              </dd>
            </div>
          )}
          <div>
            <dt className="text-sm font-medium text-text-600">
              Tamaño de la población
            </dt>
            <dd className="text-sm text-text-900">
              {muestra.poblacion} eventos
            </dd>
          </div>
          <div>
            <dt className="text-sm font-medium text-text-600">
              Tamaño de la muestra
            </dt>
            <dd className="text-sm text-text-900">
              {muestra.tamano} partidas
            </dd>
          </div>
          <div className="md:col-span-2">
            <dt className="text-sm font-medium text-text-600">Criterio</dt>
            <dd className="text-sm text-text-900">{muestra.criterio}</dd>
          </div>
          <div className="md:col-span-2">
            <dt className="text-sm font-medium text-text-600">
              Justificación
            </dt>
            <dd className="text-sm text-text-900">
              {muestra.justificacion}
            </dd>
          </div>
          <div className="md:col-span-2">
            <dt className="text-sm font-medium text-text-600">
              Filtros de la población
            </dt>
            <dd className="text-sm text-text-900">
              {Object.keys(filtros).length === 0 ? (
                "Sin filtros: toda la actividad de Gobierno del ente"
              ) : (
                <ul className="list-inside list-disc">
                  {filtros.desde !== undefined && (
                    <li>Desde: {formatearFechaDeNegocio(filtros.desde)}</li>
                  )}
                  {filtros.hasta !== undefined && (
                    <li>Hasta: {formatearFechaDeNegocio(filtros.hasta)}</li>
                  )}
                  {filtros.proceso !== undefined && (
                    <li>Proceso: {filtros.proceso}</li>
                  )}
                  {filtros.accion !== undefined && (
                    <li>Acción: {filtros.accion}</li>
                  )}
                  {filtros.usuario !== undefined && (
                    <li>Usuario: {filtros.usuario}</li>
                  )}
                  {filtros.texto !== undefined && (
                    <li>Buscar: {filtros.texto}</li>
                  )}
                </ul>
              )}
            </dd>
          </div>
          <div>
            <dt className="text-sm font-medium text-text-600">
              Registrada por
            </dt>
            <dd className="text-sm text-text-900">
              {muestra.registrada_por ?? "—"}
            </dd>
          </div>
          <div>
            <dt className="text-sm font-medium text-text-600">
              Registrada el
            </dt>
            <dd className="text-sm text-text-900">
              {formatearFecha(muestra.registrada_en)}
            </dd>
          </div>
        </dl>
        <p className="mt-4 text-sm text-text-600">
          La muestra es un papel de trabajo inmutable: no se edita ni se
          borra.
        </p>
      </section>
      <section aria-labelledby="partidas-muestra" className="mt-8">
        <h2
          id="partidas-muestra"
          className="mb-3 text-lg font-semibold text-text-900"
        >
          Partidas
        </h2>
        {muestra.eventos.length === 0 ? (
          <EmptyState title="La muestra no tiene partidas" />
        ) : (
          <div
            className="relative overflow-x-auto"
            tabIndex={0}
            role="region"
            aria-label={`Partidas de la muestra ${muestra.codigo}`}
          >
            <table className="w-full min-w-[720px] border-collapse text-sm">
              <caption className="sr-only">
                Partidas de la muestra {muestra.codigo}
              </caption>
              <thead>
                <tr className="border-b border-border-default text-left text-text-600">
                  <th scope="col" className="px-3 py-2 font-medium">
                    N.º
                  </th>
                  <th scope="col" className="px-3 py-2 font-medium">
                    Fecha y hora
                  </th>
                  <th scope="col" className="px-3 py-2 font-medium">
                    Proceso
                  </th>
                  <th scope="col" className="px-3 py-2 font-medium">
                    Acción
                  </th>
                  <th scope="col" className="px-3 py-2 font-medium">
                    Objeto
                  </th>
                  <th scope="col" className="px-3 py-2 font-medium">
                    Usuario
                  </th>
                  <th scope="col" className="px-3 py-2 font-medium">
                    Motivo
                  </th>
                  <th scope="col" className="px-3 py-2 font-medium">
                    Evidencia
                  </th>
                </tr>
              </thead>
              <tbody>
                {muestra.eventos.map((evento, indice) => (
                  <tr
                    key={evento.id}
                    className="border-b border-border-subtle align-top"
                  >
                    <td className="px-3 py-2 text-text-900">{indice + 1}</td>
                    <td className="px-3 py-2 text-text-900">
                      {formatearFecha(evento.fecha)}
                    </td>
                    <td className="px-3 py-2 text-text-900">
                      {evento.proceso} · {evento.proceso_nombre}
                    </td>
                    <td className="px-3 py-2 text-text-900">
                      {evento.accion_etiqueta}
                    </td>
                    <td className="px-3 py-2 text-text-900">
                      {evento.entidad}
                      {evento.entidad_id !== null && (
                        <span className="ml-2 text-xs text-text-600">
                          {evento.entidad_id}
                        </span>
                      )}
                    </td>
                    <td className="px-3 py-2 text-text-900">
                      {evento.usuario ?? "—"}
                    </td>
                    <td className="px-3 py-2 text-text-900">
                      {evento.motivo ?? "—"}
                    </td>
                    <td className="px-3 py-2">
                      <Link
                        to={`/gobierno/auditoria?evento=${evento.id}`}
                        aria-label={`Ver evidencia de la partida ${indice + 1}`}
                      >
                        Ver evidencia
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </PageContent>
  );
}
