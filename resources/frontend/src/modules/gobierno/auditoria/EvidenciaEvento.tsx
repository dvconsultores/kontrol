import { X } from "lucide-react";
import { Link } from "react-router";
import { useQuery } from "@tanstack/react-query";

import { apiFetch, ApiError } from "@/api/client";
import { useAutoridad } from "@/app/autoridad/AutoridadContext";
import { useCompany } from "@/app/contexts/CompanyContext";
import { Button } from "@/components/Button";
import { EmptyState } from "@/components/EmptyState";
import { ErrorState } from "@/components/ErrorState";
import { LoadingState } from "@/components/LoadingState";
import { formatearFecha } from "@/i18n";
import {
  AuditoriaEventoDetalle,
  CONSULTA_AUDITORIA,
} from "@/modules/gobierno/api";

export function EvidenciaEvento({
  eventoId,
  onCerrar,
}: {
  eventoId: string;
  onCerrar: () => void;
}): React.JSX.Element {
  const { tiene } = useAutoridad();
  const { activeCompanyId } = useCompany();

  const consulta = useQuery({
    queryKey: [...CONSULTA_AUDITORIA, activeCompanyId, "evento", eventoId],
    queryFn: () =>
      apiFetch<AuditoriaEventoDetalle>(
        `/gobierno/auditoria/eventos/${eventoId}`,
      ),
    retry: false,
    enabled: Boolean(activeCompanyId),
  });

  const detalle = consulta.data;

  const seccionDetalle = (valor: unknown): React.ReactNode => {
    if (valor === null) return "—";
    if (typeof valor === "string") return valor;
    if (typeof valor === "number" || typeof valor === "boolean")
      return String(valor);
    return <code>{JSON.stringify(valor)}</code>;
  };

  const pintarSeccion = (titulo: string, seccion: unknown) => {
    if (
      seccion === null ||
      typeof seccion !== "object" ||
      Object.keys(seccion as Record<string, unknown>).length === 0
    ) {
      return null;
    }
    const entradas = Object.entries(seccion as Record<string, unknown>).sort(
      ([claveA], [claveB]) => claveA.localeCompare(claveB),
    );
    return (
      <section key={titulo} className="mt-4">
        <h3 className="text-sm font-semibold text-text-900">{titulo}</h3>
        <dl className="mt-2 grid gap-2 sm:grid-cols-2">
          {entradas.map(([clave, valor]) => (
            <div key={clave}>
              <dt className="text-sm font-medium text-text-600">{clave}</dt>
              <dd className="text-text-900">{seccionDetalle(valor)}</dd>
            </div>
          ))}
        </dl>
      </section>
    );
  };

  const errorApi = consulta.error instanceof ApiError ? consulta.error : null;

  const cabecera = (
    <div className="mb-4 flex items-start justify-between gap-4">
      <h2
        id="evidencia-evento-titulo"
        className="text-lg font-semibold text-text-900"
      >
        Evidencia del evento
      </h2>
      <Button
        variant="ghost"
        onClick={onCerrar}
        aria-label="Cerrar la evidencia"
      >
        <X className="h-4 w-4" aria-hidden="true" />
        Cerrar la evidencia
      </Button>
    </div>
  );

  if (consulta.isLoading) {
    return (
      <section
        aria-labelledby="evidencia-evento-titulo"
        className="mt-8 border-t border-border-default pt-6"
      >
        {cabecera}
        <LoadingState label="Cargando la evidencia…" />
      </section>
    );
  }

  if (consulta.isError) {
    if (errorApi?.status === 404 && errorApi?.code === "GOV_AUDIT_EVENT_NOT_FOUND") {
      return (
        <section
          aria-labelledby="evidencia-evento-titulo"
          className="mt-8 border-t border-border-default pt-6"
        >
          {cabecera}
          <EmptyState
            title="Evento no encontrado"
            description="El evento no existe en la auditoría de este ente."
          />
        </section>
      );
    }
    return (
      <section
        aria-labelledby="evidencia-evento-titulo"
        className="mt-8 border-t border-border-default pt-6"
      >
        {cabecera}
        <ErrorState
          message="No fue posible cargar la evidencia."
          onRetry={() => void consulta.refetch()}
        />
      </section>
    );
  }

  if (!detalle) {
    return (
      <section
        aria-labelledby="evidencia-evento-titulo"
        className="mt-8 border-t border-border-default pt-6"
      >
        {cabecera}
        <ErrorState
          message="No fue posible cargar la evidencia."
          onRetry={() => void consulta.refetch()}
        />
      </section>
    );
  }

  const secciones = [
    ["before", "Antes"],
    ["after", "Después"],
    ["evidence", "Evidencia"],
  ] as const;

  const haySecciones = secciones.some(
    ([clave]) =>
      detalle.detalle[clave] !== null &&
      typeof detalle.detalle[clave] === "object" &&
      Object.keys(detalle.detalle[clave] as Record<string, unknown>).length > 0,
  );

  return (
    <section
      aria-labelledby="evidencia-evento-titulo"
      className="mt-8 border-t border-border-default pt-6"
    >
      {cabecera}

      <dl className="mb-6 grid gap-4 sm:grid-cols-2">
        <div>
          <dt className="text-sm font-medium text-text-600">Fecha y hora</dt>
          <dd className="text-text-900">{formatearFecha(detalle.fecha)}</dd>
        </div>
        <div>
          <dt className="text-sm font-medium text-text-600">Proceso</dt>
          <dd className="text-text-900">
            {detalle.proceso} · {detalle.proceso_nombre}
          </dd>
        </div>
        <div>
          <dt className="text-sm font-medium text-text-600">Acción</dt>
          <dd className="text-text-900">
            {detalle.accion_etiqueta} (<code>{detalle.accion}</code>)
          </dd>
        </div>
        <div>
          <dt className="text-sm font-medium text-text-600">Usuario</dt>
          <dd className="text-text-900">{detalle.usuario ?? "—"}</dd>
        </div>
        <div>
          <dt className="text-sm font-medium text-text-600">Motivo</dt>
          <dd className="text-text-900">{detalle.motivo ?? "—"}</dd>
        </div>
        <div>
          <dt className="text-sm font-medium text-text-600">Correlación</dt>
          <dd className="text-text-900">{detalle.request_id ?? "—"}</dd>
        </div>
        <div>
          <dt className="text-sm font-medium text-text-600">Objeto</dt>
          <dd className="text-text-900">
            {detalle.entidad} · {detalle.entidad_id}
          </dd>
        </div>
      </dl>

      <h3 className="text-sm font-semibold text-text-900">Qué cambió</h3>
      {!haySecciones ? (
        <p className="mt-2 text-sm text-text-600">
          El evento no registra detalle.
        </p>
      ) : (
        secciones.map(([clave, titulo]) =>
          pintarSeccion(titulo, detalle.detalle[clave]),
        )
      )}

      {detalle.documentos.length > 0 && (
        <section className="mt-6">
          <h3 className="text-sm font-semibold text-text-900">
            Documentos vinculados
          </h3>
          <ul className="mt-2 list-inside list-disc space-y-1">
            {detalle.documentos.map((documento) => (
              <li key={documento} className="text-text-900">
                {tiene("documentos:view", "empresa") ? (
                  <Link
                    to={`/documentos/${documento}`}
                    aria-label={`Abrir el documento ${documento}`}
                  >
                    <code>{documento}</code>
                  </Link>
                ) : (
                  <code>{documento}</code>
                )}
              </li>
            ))}
          </ul>
        </section>
      )}

      <section className="mt-6">
        <h3 className="text-sm font-semibold text-text-900">
          Objeto de negocio
        </h3>
        {detalle.objeto ? (
          tiene(detalle.objeto.capacidad, "empresa") ? (
            <Link to={detalle.objeto.ruta} className="mt-2 inline-block">
              Ir al objeto
            </Link>
          ) : (
            <p className="mt-2 text-sm text-text-600">
              No tiene permiso para abrir el objeto.
            </p>
          )
        ) : (
          <p className="mt-2 text-sm text-text-600">
            El objeto ya no está disponible o no tiene pantalla propia.
          </p>
        )}
      </section>
    </section>
  );
}
