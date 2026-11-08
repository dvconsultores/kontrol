import { Link, useParams } from "react-router";
import { useQuery } from "@tanstack/react-query";
import { apiFetch, ApiError } from "@/api/client";
import { useAutoridad } from "@/app/autoridad/AutoridadContext";
import { useCompany } from "@/app/contexts/CompanyContext";
import { EmptyState } from "@/components/EmptyState";
import { LoadingState } from "@/components/LoadingState";
import { PageHeader } from "@/components/PageHeader";
import { PageContent } from "@/layout/PageContent";
import { formatearFecha } from "@/i18n";
import { ErrorDeCarga } from "@/modules/gobierno/ocupacion/ErrorDeCarga";
import {
  BitacoraEventoDetalle,
  CONSULTA_BITACORA,
  ETIQUETAS_ESTADO_CONTEXTO,
  ETIQUETAS_MOTIVO_SIN_AUTORIDAD,
  ETIQUETAS_RESULTADO_BITACORA,
} from "@/modules/gobierno/api";

export function BitacoraEventoPage() {
  const { eventoId } = useParams<{ eventoId: string }>();
  const { tiene } = useAutoridad();
  const { activeCompanyId } = useCompany();
  const puedeVer = tiene("gobierno_auditoria:view", "empresa");

  const eventoQuery = useQuery({
    queryKey: [...CONSULTA_BITACORA, "evento", activeCompanyId, eventoId],
    queryFn: () =>
      apiFetch<BitacoraEventoDetalle>(`/gobierno/bitacora/${eventoId}`).then(
        (r) => r
      ),
    enabled: puedeVer && Boolean(activeCompanyId) && Boolean(eventoId),
    retry: false,
  });

  if (!puedeVer) {
    return (
      <PageContent>
        <EmptyState title="Sin acceso" description="No tienes permisos para ver este evento." />
      </PageContent>
    );
  }

  if (!activeCompanyId) {
    return (
      <PageContent>
        <EmptyState title="Sin empresa" description="Selecciona una empresa para continuar." />
      </PageContent>
    );
  }

  if (eventoQuery.isLoading) {
    return <LoadingState />;
  }

  if (eventoQuery.isError) {
    const error = eventoQuery.error;
    if (error instanceof ApiError && error.status === 404) {
      return (
        <PageContent>
          <PageHeader
            crumbs={[
              { label: "Gobierno" },
              { label: "Bitácora institucional", to: "/gobierno/bitacora" },
              { label: "Evento no encontrado" },
            ]}
            title="Evento no encontrado"
            description="El evento solicitado no existe o no está disponible."
          />
          <EmptyState
            title="Evento no encontrado"
            description="El evento solicitado no existe o no está disponible."
            action={
              <Link
                to="/gobierno/bitacora"
                className="inline-flex items-center rounded-md border border-border-subtle bg-white px-3 py-2 text-sm font-medium text-text-900 hover:bg-surface-100"
              >
                Volver a la Bitácora institucional
              </Link>
            }
          />
        </PageContent>
      );
    }
    return (
      <ErrorDeCarga
        message="No se pudo cargar el evento."
        onRetry={() => eventoQuery.refetch()}
      />
    );
  }

  if (!eventoQuery.data) {
    return null;
  }

  const evento = eventoQuery.data;
  const contexto = evento.contexto ?? null;
  const detalleEntries = Object.entries(evento.detalle ?? {}).filter(
    ([, valor]) => valor !== null && valor !== undefined && valor !== ""
  );

  return (
    <PageContent>
      <PageHeader
        crumbs={[
          { label: "Gobierno" },
          { label: "Bitácora institucional", to: "/gobierno/bitacora" },
          { label: evento.accion_etiqueta },
        ]}
        title={evento.accion_etiqueta}
        description="Detalle del evento en la bitácora institucional."
      />

      <section aria-labelledby="evento-titulo" className="mb-8">
        <h2 id="evento-titulo" className="mb-4 text-lg font-semibold">
          Evento
        </h2>
        <dl className="grid gap-4 sm:grid-cols-2">
          <div>
            <dt className="text-sm font-medium text-text-700">Fecha</dt>
            <dd className="mt-1 text-text-900">{formatearFecha(evento.fecha)}</dd>
          </div>
          <div>
            <dt className="text-sm font-medium text-text-700">Resultado</dt>
            <dd className="mt-1 text-text-900">
              {ETIQUETAS_RESULTADO_BITACORA[evento.resultado] ?? evento.resultado}
            </dd>
          </div>
          <div>
            <dt className="text-sm font-medium text-text-700">Proceso</dt>
            <dd className="mt-1 text-text-900">{evento.proceso_nombre}</dd>
          </div>
          <div>
            <dt className="text-sm font-medium text-text-700">Acción</dt>
            <dd className="mt-1 text-text-900">{evento.accion_etiqueta}</dd>
          </div>
          {evento.motivo && (
            <div>
              <dt className="text-sm font-medium text-text-700">Motivo</dt>
              <dd className="mt-1 text-text-900">{evento.motivo}</dd>
            </div>
          )}
          <div>
            <dt className="text-sm font-medium text-text-700">Objeto</dt>
            <dd className="mt-1 text-text-900">
              {evento.entidad}
              {evento.objeto && evento.objeto.ruta && tiene(evento.objeto.capacidad, "empresa") && (
                <>
                  {" · "}
                  <Link
                    to={evento.objeto.ruta}
                    className="font-medium text-brand-700 underline"
                  >
                    Abrir el objeto
                  </Link>
                </>
              )}
            </dd>
          </div>
        </dl>
      </section>

      <section aria-labelledby="actor-titulo" className="mb-8">
        <h2 id="actor-titulo" className="mb-4 text-lg font-semibold">
          Actor técnico
        </h2>
        <dl className="grid gap-4 sm:grid-cols-2">
          <div>
            <dt className="text-sm font-medium text-text-700">Usuario técnico</dt>
            <dd className="mt-1 text-text-900">{evento.usuario ?? "—"}</dd>
          </div>
          <div>
            <dt className="text-sm font-medium text-text-700">Sesión</dt>
            <dd className="mt-1 text-text-900">{evento.sesion_id ?? "—"}</dd>
          </div>
          <div>
            <dt className="text-sm font-medium text-text-700">IP</dt>
            <dd className="mt-1 text-text-900">{evento.ip ?? "—"}</dd>
          </div>
          <div>
            <dt className="text-sm font-medium text-text-700">Correlación</dt>
            <dd className="mt-1 text-text-900">{evento.request_id ?? "—"}</dd>
          </div>
        </dl>
      </section>

      <section aria-labelledby="contexto-titulo" className="mb-8">
        <h2 id="contexto-titulo" className="mb-4 text-lg font-semibold">
          Contexto institucional en el momento del evento
        </h2>
        {contexto?.funcionario == null ? (
          <>
            <p className="text-text-900">
              {ETIQUETAS_ESTADO_CONTEXTO[evento.estado_contexto] ??
                ETIQUETAS_ESTADO_CONTEXTO.SIN_VINCULO}
            </p>
            {contexto?.ente && (
              <dl className="mt-4 grid gap-4 sm:grid-cols-2">
                <div>
                  <dt className="text-sm font-medium text-text-700">Ente</dt>
                  <dd className="mt-1 text-text-900">{contexto.ente.nombre}</dd>
                </div>
              </dl>
            )}
          </>
        ) : (
          <>
            <dl className="grid gap-4 sm:grid-cols-2">
              <div>
                <dt className="text-sm font-medium text-text-700">Actor efectivo</dt>
                <dd className="mt-1 text-text-900">{contexto.funcionario.nombre}</dd>
              </div>
              <div>
                <dt className="text-sm font-medium text-text-700">Vínculo</dt>
                <dd className="mt-1 text-text-900">{contexto.vinculo?.codigo ?? "—"}</dd>
              </div>
              <div>
                <dt className="text-sm font-medium text-text-700">Ente</dt>
                <dd className="mt-1 text-text-900">{contexto.ente?.nombre ?? "—"}</dd>
              </div>
              <div>
                <dt className="text-sm font-medium text-text-700">Autoridad a esa fecha</dt>
                <dd className="mt-1 text-text-900">
                  {contexto.tiene_autoridad
                    ? "Sí"
                    : `No${contexto.motivo_sin_autoridad ? ` · ${(ETIQUETAS_MOTIVO_SIN_AUTORIDAD as Record<string, string>)[contexto.motivo_sin_autoridad] ?? contexto.motivo_sin_autoridad}` : ""}`}
                </dd>
              </div>
              <div>
                <dt className="text-sm font-medium text-text-700">Fecha de negocio</dt>
                <dd className="mt-1 text-text-900">{contexto.fecha}</dd>
              </div>
              <div>
                <dt className="text-sm font-medium text-text-700">Roles</dt>
                <dd className="mt-1 text-text-900">
                  {contexto.roles.map((r) => r.nombre).join(", ") || "—"}
                </dd>
              </div>
              <div>
                <dt className="text-sm font-medium text-text-700">Categorías</dt>
                <dd className="mt-1 text-text-900">
                  {contexto.categorias.join(", ") || "—"}
                </dd>
              </div>
            </dl>

            {contexto.ocupaciones.length > 0 ? (
              <ul className="mt-6 space-y-4">
                {contexto.ocupaciones.map((ocupacion, index) => (
                  <li key={`${ocupacion.cargo_id}-${ocupacion.unidad_id}-${index}`} className="rounded-md border border-border-subtle p-4">
                    <dl className="grid gap-4 sm:grid-cols-2">
                      <div>
                        <dt className="text-sm font-medium text-text-700">Cargo</dt>
                        <dd className="mt-1 text-text-900">{ocupacion.cargo}</dd>
                      </div>
                      <div>
                        <dt className="text-sm font-medium text-text-700">Unidad</dt>
                        <dd className="mt-1 text-text-900">{ocupacion.unidad}</dd>
                      </div>
                      <div>
                        <dt className="text-sm font-medium text-text-700">Figura</dt>
                        <dd className="mt-1 text-text-900">{ocupacion.figura_etiqueta}</dd>
                      </div>
                      <div>
                        <dt className="text-sm font-medium text-text-700">Ejercicio</dt>
                        <dd className="mt-1 text-text-900">
                          {ocupacion.ejerce ? "Ejerce" : "No ejerce"}
                        </dd>
                      </div>
                    </dl>
                    {ocupacion.autoridad.length > 0 && (
                      <p className="mt-3 text-sm text-text-700">
                        Competencias:{" "}
                        {ocupacion.autoridad
                          .map((a) => `${a.accion} · ${a.materia}`)
                          .join(", ")}
                      </p>
                    )}
                  </li>
                ))}
              </ul>
            ) : (
              <p className="mt-4 text-text-900">
                Sin ocupación vigente en ese momento.
              </p>
            )}
          </>
        )}
      </section>

      <section aria-labelledby="cambios-titulo">
        <h2 id="cambios-titulo" className="mb-4 text-lg font-semibold">
          Qué cambió
        </h2>
        {detalleEntries.length === 0 ? (
          <p className="text-text-900">Este evento no registra cambios.</p>
        ) : (
          detalleEntries.map(([clave, valor]) => (
            <div key={clave} className="mb-4">
              <h3 className="mb-2 text-sm font-medium text-text-700">{clave}</h3>
              <pre
                className="overflow-x-auto rounded bg-surface-100 p-2 text-xs"
                tabIndex={0}
              >
                {JSON.stringify(valor, null, 2)}
              </pre>
            </div>
          ))
        )}
      </section>
    </PageContent>
  );
}
