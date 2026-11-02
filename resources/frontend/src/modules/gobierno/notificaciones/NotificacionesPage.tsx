import { useMemo, useState } from "react";
import { Link } from "react-router";
import { useQuery } from "@tanstack/react-query";
import { Download } from "lucide-react";

import { apiFetch, ApiError } from "@/api/client";
import { descargarArchivo } from "@/api/descargas";
import { useAutoridad } from "@/app/autoridad/AutoridadContext";
import { useNotifications } from "@/app/contexts/NotificationContext";
import { PageContent } from "@/layout/PageContent";
import { PageHeader } from "@/components/PageHeader";
import { AsyncButton } from "@/components/AsyncButton";
import { TextInput } from "@/components/TextInput";
import { FormField } from "@/components/FormField";
import { EmptyState } from "@/components/EmptyState";
import { ErrorState } from "@/components/ErrorState";
import { LoadingState } from "@/components/LoadingState";
import { hoyDeNegocio, formatearFechaDeNegocio } from "@/lib/fecha-de-negocio";
import {
  CONSULTA_NOTIFICACIONES,
  ETIQUETA_ESTADO_NOTIFICACION,
  ETIQUETA_TIPO_PERSONA,
  nombreDeActo,
  type ListaNotificaciones,
} from "@/modules/gobierno/api";

const CLASE_SELECT =
  "h-10 w-full rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900 focus:border-brand-600 focus:outline-brand-600";

export function NotificacionesPage(): React.JSX.Element {
  const { tiene } = useAutoridad();
  const { notify } = useNotifications();

  const anioActual = Number(hoyDeNegocio().slice(0, 4));
  const anios = useMemo(
    () => Array.from({ length: 6 }, (_, i) => anioActual - i),
    [anioActual],
  );

  const [anio, setAnio] = useState(anioActual);
  const [estado, setEstado] = useState("");
  const [busqueda, setBusqueda] = useState("");

  const puedeVer = tiene("gobierno_notificaciones:view", "empresa");

  const consultaNotificaciones = useQuery({
    queryKey: [...CONSULTA_NOTIFICACIONES, "lista", anio],
    queryFn: () =>
      apiFetch<ListaNotificaciones>(`/gobierno/notificaciones?anio=${anio}`),
    enabled: puedeVer,
    retry: false,
  });

  const exportarCsv = async () => {
    try {
      await descargarArchivo(
        `/gobierno/notificaciones/exportar?anio=${anio}`,
        `notificaciones-${anio}.csv`,
      );
      notify({ type: "success", title: "Notificaciones exportadas" });
    } catch {
      notify({ type: "error", title: "No fue posible exportar" });
    }
  };

  const notificacionesFiltradas = useMemo(() => {
    const items = consultaNotificaciones.data?.items ?? [];
    const texto = busqueda.trim().toLowerCase();
    return items.filter((notificacion) => {
      if (
        texto &&
        !nombreDeActo(notificacion.acto).toLowerCase().includes(texto) &&
        !notificacion.nombre.toLowerCase().includes(texto) &&
        !notificacion.identificacion.toLowerCase().includes(texto)
      ) {
        return false;
      }
      if (estado && notificacion.estado !== estado) return false;
      return true;
    });
  }, [consultaNotificaciones.data?.items, busqueda, estado]);

  const crumbs = [
    { label: "Gobierno" },
    { label: "Notificaciones administrativas", to: "/gobierno/notificaciones" },
  ];
  const cabecera = (
    <PageHeader
      crumbs={crumbs}
      title="Notificaciones administrativas"
      description="Notificación de actos particulares a cada interesado (LOPA arts. 73–76)."
    />
  );

  if (!puedeVer) {
    return (
      <PageContent>
        {cabecera}
        <EmptyState
          title="Sin acceso"
          description="No tiene permiso para ver las notificaciones administrativas."
        />
      </PageContent>
    );
  }

  if (consultaNotificaciones.isLoading) {
    return (
      <PageContent>
        {cabecera}
        <LoadingState label="Cargando notificaciones administrativas…" />
      </PageContent>
    );
  }

  if (consultaNotificaciones.isError) {
    const error = consultaNotificaciones.error;
    if (
      error instanceof ApiError &&
      error.status === 403 &&
      error.code === "MODULE_NOT_ENTITLED"
    ) {
      return (
        <PageContent>
          {cabecera}
          <EmptyState
            title="Módulo no disponible"
            description="El módulo de Gobierno no está habilitado."
          />
        </PageContent>
      );
    }
    if (error instanceof ApiError && error.status === 403) {
      return (
        <PageContent>
          {cabecera}
          <EmptyState
            title="Sin acceso"
            description="No tiene permiso para ver las notificaciones administrativas."
          />
        </PageContent>
      );
    }
    if (
      error instanceof ApiError &&
      error.status === 404 &&
      error.code === "GOV_ENTITY_NOT_FOUND"
    ) {
      return (
        <PageContent>
          {cabecera}
          <EmptyState
            title="Primero configure el ente"
            action={
              <Link
                to="/gobierno/ente"
                className="font-medium text-brand-700 underline"
              >
                Ir a Configuración del ente
              </Link>
            }
          />
        </PageContent>
      );
    }
    return (
      <PageContent>
        {cabecera}
        <ErrorState
          message="No fue posible cargar las notificaciones."
          onRetry={() => void consultaNotificaciones.refetch()}
        />
      </PageContent>
    );
  }

  if (!consultaNotificaciones.data) {
    return (
      <PageContent>
        {cabecera}
        <ErrorState
          message="No fue posible cargar las notificaciones."
          onRetry={() => void consultaNotificaciones.refetch()}
        />
      </PageContent>
    );
  }

  const accionesCabecera = (
    <div className="flex flex-wrap items-center gap-2">
      {puedeVer && (
        <AsyncButton onClick={exportarCsv} variant="secondary">
          <Download className="mr-2 h-4 w-4" aria-hidden="true" />
          Exportar CSV
        </AsyncButton>
      )}
    </div>
  );

  return (
    <PageContent>
      <PageHeader
        crumbs={crumbs}
        title="Notificaciones administrativas"
        description="Notificación de actos particulares a cada interesado (LOPA arts. 73–76)."
        actions={accionesCabecera}
      />

      <section aria-labelledby="notificaciones-titulo" className="mb-8">
        <h2
          id="notificaciones-titulo"
          className="mb-4 text-lg font-semibold text-text-900"
        >
          Notificaciones
        </h2>

        <div className="mb-4 flex flex-wrap items-end gap-3">
          <FormField label="Año" htmlFor="filtro-anio" className="min-w-28">
            <select
              id="filtro-anio"
              className={CLASE_SELECT}
              value={anio}
              onChange={(e) => setAnio(Number(e.target.value))}
            >
              {anios.map((valor) => (
                <option key={valor} value={valor}>
                  {valor}
                </option>
              ))}
            </select>
          </FormField>
          <FormField
            label="Estado"
            htmlFor="filtro-estado"
            className="min-w-40"
          >
            <select
              id="filtro-estado"
              className={CLASE_SELECT}
              value={estado}
              onChange={(e) => setEstado(e.target.value)}
            >
              <option value="">Todos</option>
              {Object.entries(ETIQUETA_ESTADO_NOTIFICACION).map(
                ([valor, etiqueta]) => (
                  <option key={valor} value={valor}>
                    {etiqueta}
                  </option>
                ),
              )}
            </select>
          </FormField>
          <FormField
            label="Buscar"
            htmlFor="filtro-busqueda"
            className="min-w-56 flex-1"
          >
            <TextInput
              id="filtro-busqueda"
              value={busqueda}
              onChange={(e) => setBusqueda(e.target.value)}
              placeholder="Acto, destinatario o identificación"
            />
          </FormField>
        </div>

      {consultaNotificaciones.data.total === 0 ? (
        <EmptyState
          title={`Sin notificaciones en ${anio}`}
          description="Las notificaciones se registran desde un acto particular emitido."
          action={
            <Link
              to="/gobierno/actos"
              className="font-medium text-brand-700 underline"
            >
              Ir a Actos administrativos
            </Link>
          }
        />
      ) : notificacionesFiltradas.length === 0 ? (
        <EmptyState title="Ninguna notificación coincide con los filtros" />
      ) : (
        <>
          <div className="relative overflow-x-auto">
            <table className="w-full min-w-[760px] border-collapse text-sm">
              <caption className="sr-only">
                Notificaciones de {anio}
              </caption>
              <thead>
                <tr className="border-b border-border-default text-left text-text-600">
                  <th scope="col" className="px-3 py-2 font-medium">
                    Acto
                  </th>
                  <th scope="col" className="px-3 py-2 font-medium">
                    Destinatario
                  </th>
                  <th scope="col" className="px-3 py-2 font-medium">
                    Identificación
                  </th>
                  <th scope="col" className="px-3 py-2 font-medium">
                    Estado
                  </th>
                  <th scope="col" className="px-3 py-2 font-medium">
                    Intentos
                  </th>
                  <th scope="col" className="px-3 py-2 font-medium">
                    Notificada el
                  </th>
                </tr>
              </thead>
              <tbody>
                {notificacionesFiltradas.map((notificacion) => (
                  <tr
                    key={notificacion.id}
                    className="border-b border-border-subtle align-top"
                  >
                    <td className="px-3 py-2 text-text-900">
                      <Link
                        to={`/gobierno/actos/${notificacion.acto.id}`}
                        className="font-medium text-brand-700 underline"
                        aria-label={`Abrir el acto ${nombreDeActo(notificacion.acto)}`}
                      >
                        {nombreDeActo(notificacion.acto)}
                      </Link>
                    </td>
                    <td className="px-3 py-2 text-text-900">
                      <Link
                        to={`/gobierno/notificaciones/${notificacion.id}`}
                        className="font-medium text-brand-700 underline"
                        aria-label={`Abrir la notificación a ${notificacion.nombre}`}
                      >
                        {notificacion.nombre}
                      </Link>
                      <div className="text-xs text-text-600">
                        {ETIQUETA_TIPO_PERSONA[notificacion.tipo_persona]}
                      </div>
                    </td>
                    <td className="px-3 py-2 text-text-700">
                      {notificacion.identificacion}
                    </td>
                    <td className="px-3 py-2 text-text-700">
                      {ETIQUETA_ESTADO_NOTIFICACION[notificacion.estado]}
                    </td>
                    <td className="px-3 py-2 text-text-700">
                      {notificacion.intentos}
                    </td>
                    <td className="px-3 py-2 text-text-700">
                      {notificacion.fecha_notificacion
                        ? `${formatearFechaDeNegocio(notificacion.fecha_notificacion)}${
                            notificacion.medio_notificacion === "PRENSA"
                              ? " (prensa)"
                              : ""
                          }`
                        : "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="mt-3 text-sm text-text-600">
            {notificacionesFiltradas.length} de{" "}
            {consultaNotificaciones.data.total} notificaciones
          </p>
        </>
      )}
      </section>
    </PageContent>
  );
}
