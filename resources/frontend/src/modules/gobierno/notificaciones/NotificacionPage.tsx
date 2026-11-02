import { useMemo, useState } from "react";
import { Link, useParams } from "react-router";
import { useQuery, useQueryClient } from "@tanstack/react-query";

import { apiFetch, ApiError } from "@/api/client";
import { useCompany } from "@/app/contexts/CompanyContext";
import { useAutoridad } from "@/app/autoridad/AutoridadContext";
import { useNotifications } from "@/app/contexts/NotificationContext";
import { PageContent } from "@/layout/PageContent";
import { PageHeader } from "@/components/PageHeader";
import { Button } from "@/components/Button";
import { EmptyState } from "@/components/EmptyState";
import { ErrorState } from "@/components/ErrorState";
import { LoadingState } from "@/components/LoadingState";
import { ConflictState } from "@/components/ConflictState";
import { AdjuntosPanel } from "@/modules/documentos/AdjuntosPanel";
import { formatearFecha } from "@/i18n";
import { formatearFechaDeNegocio } from "@/lib/fecha-de-negocio";
import {
  CONSULTA_NOTIFICACIONES,
  CONSULTA_ACTOS,
  Notificacion,
  VersionesNotificacion,
  IntentoEntrada,
  ETIQUETA_TIPO_PERSONA,
  ETIQUETA_ESTADO_NOTIFICACION,
  ETIQUETA_MEDIO_INTENTO,
  ETIQUETA_RESULTADO_INTENTO,
  ETIQUETA_ESTADO_ACTO,
  nombreDeActo,
} from "@/modules/gobierno/api";

import { DestinatarioFormulario, DatosDestinatario } from "./DestinatarioFormulario";
import { RegistrarIntento, ModoIntento } from "./RegistrarIntento";
import { AnularNotificacion } from "./AnularNotificacion";

type Panel =
  | { tipo: "ninguno" }
  | { tipo: "corregir" }
  | { tipo: "intento"; modo: ModoIntento }
  | { tipo: "anular" };

export function NotificacionPage(): React.JSX.Element {
  const { notificacionId } = useParams();
  const { activeCompanyId } = useCompany();
  const { tiene } = useAutoridad();
  const { notify } = useNotifications();
  const queryClient = useQueryClient();

  const puedeVer = tiene("gobierno_notificaciones:view", "empresa");
  const puedeEditar = tiene("gobierno_notificaciones:edit", "empresa");
  const puedeRegistrar = tiene("gobierno_notificaciones:record", "empresa");

  const [panel, setPanel] = useState<Panel>({ tipo: "ninguno" });
  const [erroresServidor, setErroresServidor] = useState<Record<string, string[]>>({});
  const [conflicto, setConflicto] = useState(false);

  const recargar = () => {
    void queryClient.invalidateQueries({ queryKey: [...CONSULTA_NOTIFICACIONES] });
    void queryClient.invalidateQueries({ queryKey: [...CONSULTA_ACTOS] });
  };

  const consultaNotificacion = useQuery({
    queryKey: [...CONSULTA_NOTIFICACIONES, activeCompanyId, "detalle", notificacionId],
    queryFn: () => apiFetch<Notificacion>(`/gobierno/notificaciones/${notificacionId}`),
    enabled: puedeVer && Boolean(activeCompanyId) && Boolean(notificacionId),
    retry: false,
  });

  const consultaVersiones = useQuery({
    queryKey: [...CONSULTA_NOTIFICACIONES, activeCompanyId, "versiones", notificacionId],
    queryFn: () => apiFetch<VersionesNotificacion>(`/gobierno/notificaciones/${notificacionId}/versiones`),
    enabled: puedeVer && Boolean(activeCompanyId) && Boolean(notificacionId),
    retry: false,
  });

  const versionesOrdenadas = useMemo(() => {
    return [...(consultaVersiones.data?.items ?? [])].sort((a, b) => b.version - a.version);
  }, [consultaVersiones.data]);

  const manejarError = (e: unknown) => {
    if (e instanceof ApiError) {
      if (e.status === 409 && e.code === "GOV_NOTIFICATION_STALE") {
        setConflicto(true);
        recargar();
        return;
      }
      if (e.status === 422 && e.code === "VALIDATION_ERROR") {
        setErroresServidor(e.fieldErrors);
        return;
      }
      if (e.status === 403) {
        notify({ type: "error", title: "No tiene permiso para esta acción" });
        return;
      }
      notify({
        type: "error",
        title: "No fue posible completar la operación",
        description: e.message,
      });
      return;
    }
    notify({ type: "error", title: "No fue posible completar la operación" });
  };

  const cabeceraSinDatos = (
    <PageHeader
      crumbs={[
        { label: "Gobierno" },
        { label: "Notificaciones administrativas", to: "/gobierno/notificaciones" },
      ]}
      title="Notificación administrativa"
    />
  );

  if (!puedeVer) {
    return (
      <PageContent>
        {cabeceraSinDatos}
        <EmptyState title="Sin acceso" description="No tiene permiso para ver esta notificación." />
      </PageContent>
    );
  }

  if (consultaNotificacion.isLoading || consultaVersiones.isLoading) {
    return (
      <PageContent>
        {cabeceraSinDatos}
        <LoadingState label="Cargando notificación…" />
      </PageContent>
    );
  }

  if (consultaNotificacion.isError) {
    const error = consultaNotificacion.error;
    if (error instanceof ApiError && error.status === 403 && error.code === "MODULE_NOT_ENTITLED") {
      return (
        <PageContent>
          {cabeceraSinDatos}
          <EmptyState
            title="Módulo no disponible"
            description="Su empresa no tiene contratado el módulo de Gobierno."
            action={<Link to="/gobierno/notificaciones">Volver a Notificaciones administrativas</Link>}
          />
        </PageContent>
      );
    }
    if (error instanceof ApiError && error.status === 403) {
      return (
        <PageContent>
          {cabeceraSinDatos}
          <EmptyState title="Sin acceso" description="No tiene permiso para ver esta notificación." />
        </PageContent>
      );
    }
    if (error instanceof ApiError && error.status === 404 && error.code === "GOV_NOTIFICATION_NOT_FOUND") {
      return (
        <PageContent>
          {cabeceraSinDatos}
          <EmptyState
            title="Notificación no encontrada"
            action={<Link to="/gobierno/notificaciones">Volver a Notificaciones administrativas</Link>}
          />
        </PageContent>
      );
    }
    return (
      <PageContent>
        {cabeceraSinDatos}
        <ErrorState message="No fue posible cargar la notificación." onRetry={() => void consultaNotificacion.refetch()} />
      </PageContent>
    );
  }

  if (consultaVersiones.isError) {
    const error = consultaVersiones.error;
    if (error instanceof ApiError && error.status === 403 && error.code === "MODULE_NOT_ENTITLED") {
      return (
        <PageContent>
          {cabeceraSinDatos}
          <EmptyState
            title="Módulo no disponible"
            description="Su empresa no tiene contratado el módulo de Gobierno."
            action={<Link to="/gobierno/notificaciones">Volver a Notificaciones administrativas</Link>}
          />
        </PageContent>
      );
    }
    if (error instanceof ApiError && error.status === 403) {
      return (
        <PageContent>
          {cabeceraSinDatos}
          <EmptyState title="Sin acceso" description="No tiene permiso para ver el historial de la notificación." />
        </PageContent>
      );
    }
    return (
      <PageContent>
        {cabeceraSinDatos}
        <ErrorState message="No fue posible cargar el historial." onRetry={() => void consultaVersiones.refetch()} />
      </PageContent>
    );
  }

  const notificacion = consultaNotificacion.data;
  const versiones = consultaVersiones.data;

  if (!notificacion || !versiones) {
    return (
      <PageContent>
        {cabeceraSinDatos}
        <ErrorState message="No fue posible cargar la notificación." onRetry={() => void consultaNotificacion.refetch()} />
      </PageContent>
    );
  }

  const crumbs = [
    { label: "Gobierno" },
    { label: "Notificaciones administrativas", to: "/gobierno/notificaciones" },
    { label: notificacion.nombre },
  ];

  const estaPendiente = notificacion.estado === "PENDIENTE";
  const actoEmitido = notificacion.acto.estado === "EMITIDO";
  const sinIntentos = notificacion.intentos.length === 0;

  const accionesCabecera = (
    <div className="flex flex-wrap items-center gap-2">
      {estaPendiente && actoEmitido && puedeRegistrar && (
        <Button variant="primary" onClick={() => setPanel({ tipo: "intento", modo: "ENTREGADA" })}>
          Registrar entrega
        </Button>
      )}
      {estaPendiente && actoEmitido && puedeRegistrar && (
        <Button variant="secondary" onClick={() => setPanel({ tipo: "intento", modo: "FALLIDA" })}>
          Registrar intento fallido
        </Button>
      )}
      {estaPendiente && actoEmitido && puedeRegistrar && notificacion.puede_publicar_en_prensa && (
        <Button variant="secondary" onClick={() => setPanel({ tipo: "intento", modo: "PRENSA" })}>
          Publicar en prensa
        </Button>
      )}
      {estaPendiente && actoEmitido && sinIntentos && puedeEditar && (
        <Button variant="secondary" onClick={() => setPanel({ tipo: "corregir" })}>
          Corregir datos
        </Button>
      )}
      {estaPendiente && actoEmitido && puedeEditar && (
        <Button variant="secondary" onClick={() => setPanel({ tipo: "anular" })}>
          Anular
        </Button>
      )}
    </div>
  );

  const corregirDatos = async (datos: DatosDestinatario) => {
    try {
      await apiFetch<Notificacion>(`/gobierno/notificaciones/${notificacion.id}`, {
        method: "PATCH",
        body: datos,
        ifMatch: String(notificacion.version),
      });
      notify({ type: "success", title: "Datos corregidos" });
      setPanel({ tipo: "ninguno" });
      setErroresServidor({});
      recargar();
    } catch (e) {
      manejarError(e);
    }
  };

  const registrarIntento = async (datos: IntentoEntrada) => {
    try {
      await apiFetch<Notificacion>(`/gobierno/notificaciones/${notificacion.id}/intentos`, {
        method: "POST",
        body: datos,
        ifMatch: String(notificacion.version),
      });
      const titulo =
        datos.medio === "PRENSA"
          ? "Publicación registrada"
          : datos.resultado === "ENTREGADA"
            ? "Entrega registrada"
            : "Intento fallido registrado";
      notify({ type: "success", title: titulo });
      setPanel({ tipo: "ninguno" });
      setErroresServidor({});
      recargar();
    } catch (e) {
      manejarError(e);
    }
  };

  const anularNotificacion = async (motivo: string) => {
    try {
      await apiFetch<Notificacion>(`/gobierno/notificaciones/${notificacion.id}/anular`, {
        method: "POST",
        body: { motivo },
        ifMatch: String(notificacion.version),
      });
      notify({ type: "success", title: "Notificación anulada" });
      setPanel({ tipo: "ninguno" });
      setErroresServidor({});
      recargar();
    } catch (e) {
      manejarError(e);
    }
  };

  const avisoEstado = () => {
    if (notificacion.estado === "PENDIENTE") {
      return (
        <p role="status" className="mb-4 rounded-md bg-surface-100 px-4 py-3 text-sm text-text-700">
          Pendiente de notificar.
          {notificacion.puede_publicar_en_prensa &&
            " Tras el intento fallido puede publicarse en prensa (LOPA art. 76)."}
        </p>
      );
    }
    if (notificacion.estado === "NOTIFICADA" && notificacion.medio_notificacion === "PERSONAL") {
      return (
        <p role="status" className="mb-4 rounded-md bg-surface-100 px-4 py-3 text-sm text-text-700">
          Notificada el {formatearFechaDeNegocio(notificacion.fecha_notificacion)}
        </p>
      );
    }
    if (notificacion.estado === "NOTIFICADA" && notificacion.medio_notificacion === "PRENSA") {
      return (
        <p role="status" className="mb-4 rounded-md bg-surface-100 px-4 py-3 text-sm text-text-700">
          Se entiende notificada el {formatearFechaDeNegocio(notificacion.fecha_notificacion)} (publicación en prensa más 15 días)
        </p>
      );
    }
    if (notificacion.estado === "ANULADA") {
      return (
        <p role="status" className="mb-4 rounded-md bg-surface-100 px-4 py-3 text-sm text-text-700">
          Anulada. Motivo: {notificacion.motivo_anulacion}
        </p>
      );
    }
    return null;
  };

  return (
    <PageContent>
      <PageHeader
        crumbs={crumbs}
        title={`Notificación a ${notificacion.nombre}`}
        status={
          <span className="inline-flex items-center rounded-full bg-surface-100 px-3 py-1 text-sm font-medium text-text-700">
            {ETIQUETA_ESTADO_NOTIFICACION[notificacion.estado]}
          </span>
        }
        actions={accionesCabecera}
      />

      {conflicto ? (
        <ConflictState
          message="Otra persona cambió la notificación mientras trabajaba. Se cargó la versión vigente."
          onReload={() => {
            setConflicto(false);
            setPanel({ tipo: "ninguno" });
          }}
        />
      ) : (
        <>
          <section aria-labelledby="estado-titulo" className="mb-8">
            <h2 id="estado-titulo" className="mb-4 text-lg font-semibold text-text-900">
              Estado
            </h2>
            {avisoEstado()}
            {estaPendiente && !actoEmitido && (
              <p role="status" className="rounded-md bg-surface-100 px-4 py-3 text-sm text-text-700">
                El acto ya no admite notificaciones (estado: {ETIQUETA_ESTADO_ACTO[notificacion.acto.estado]}).
              </p>
            )}
          </section>

          <section aria-labelledby="acto-notificado-titulo" className="mb-8">
            <h2 id="acto-notificado-titulo" className="mb-4 text-lg font-semibold text-text-900">
              Acto notificado
            </h2>
            <Link to={`/gobierno/actos/${notificacion.acto.id}`} className="text-sm text-text-900 underline">
              {nombreDeActo(notificacion.acto)}
            </Link>
            <p className="mt-1 text-sm text-text-700">{formatearFechaDeNegocio(notificacion.acto.fecha)}</p>
          </section>

          <section aria-labelledby="destinatario-titulo" className="mb-8">
            <h2 id="destinatario-titulo" className="mb-4 text-lg font-semibold text-text-900">
              Destinatario
            </h2>
            <dl className="grid gap-x-8 gap-y-4 text-sm sm:grid-cols-2">
              <div>
                <dt className="font-medium text-text-600">Tipo de persona</dt>
                <dd className="mt-1 text-text-900">{ETIQUETA_TIPO_PERSONA[notificacion.tipo_persona]}</dd>
              </div>
              <div>
                <dt className="font-medium text-text-600">Nombre o razón social</dt>
                <dd className="mt-1 text-text-900">{notificacion.nombre}</dd>
              </div>
              <div>
                <dt className="font-medium text-text-600">Cédula o RIF</dt>
                <dd className="mt-1 text-text-900">{notificacion.identificacion}</dd>
              </div>
              <div>
                <dt className="font-medium text-text-600">Domicilio o residencia</dt>
                <dd className="mt-1 text-text-900">{notificacion.domicilio}</dd>
              </div>
              {notificacion.apoderado_nombre && (
                <div>
                  <dt className="font-medium text-text-600">Apoderado</dt>
                  <dd className="mt-1 text-text-900">
                    {notificacion.apoderado_nombre} · {notificacion.apoderado_identificacion ?? "—"}
                  </dd>
                </div>
              )}
              <div className="sm:col-span-2">
                <dt className="font-medium text-text-600">Recursos que proceden</dt>
                <dd className="mt-1 whitespace-pre-line text-text-900">{notificacion.recursos}</dd>
              </div>
            </dl>
          </section>

          <section aria-labelledby="oficio-titulo" className="mb-8">
            <h2 id="oficio-titulo" className="mb-4 text-lg font-semibold text-text-900">
              Oficio y constancias
            </h2>
            <AdjuntosPanel
              resourceType="GovernmentNotification"
              resourceId={notificacion.id}
              title="Oficio y constancias"
              onChange={() => void recargar()}
            />
          </section>

          <section aria-labelledby="intentos-titulo" className="mb-8">
            <h2 id="intentos-titulo" className="mb-4 text-lg font-semibold text-text-900">
              Intentos
            </h2>
            {notificacion.intentos.length > 0 ? (
              <div className="relative overflow-x-auto" tabIndex={0} role="region" aria-label={`Intentos de notificación de ${notificacion.nombre}`}>
                <table className="w-full min-w-[720px] border-collapse text-sm">
                  <caption className="sr-only">Intentos de notificación de {notificacion.nombre}</caption>
                  <thead>
                    <tr className="border-b border-border-default text-left text-text-600">
                      <th scope="col" className="px-3 py-2 font-medium">
                        Nº
                      </th>
                      <th scope="col" className="px-3 py-2 font-medium">
                        Canal
                      </th>
                      <th scope="col" className="px-3 py-2 font-medium">
                        Resultado
                      </th>
                      <th scope="col" className="px-3 py-2 font-medium">
                        Fecha
                      </th>
                      <th scope="col" className="px-3 py-2 font-medium">
                        Detalle
                      </th>
                      <th scope="col" className="px-3 py-2 font-medium">
                        Registrado el
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {notificacion.intentos.map((intento) => (
                      <tr key={intento.numero} className="border-b border-border-subtle align-top">
                        <td className="px-3 py-2 font-mono text-text-900">{intento.numero}</td>
                        <td className="px-3 py-2 text-text-900">{ETIQUETA_MEDIO_INTENTO[intento.medio]}</td>
                        <td className="px-3 py-2 text-text-900">{ETIQUETA_RESULTADO_INTENTO[intento.resultado]}</td>
                        <td className="px-3 py-2 text-text-700">{formatearFechaDeNegocio(intento.fecha)}</td>
                        <td className="px-3 py-2 text-text-700">
                          {intento.resultado === "ENTREGADA" &&
                            `Recibido por ${intento.receptor_nombre} (${intento.receptor_identificacion})`}
                          {intento.resultado === "FALLIDA" && intento.motivo_fallo}
                          {intento.resultado === "PUBLICADA" && `${intento.diario} · ${intento.referencia}`}
                        </td>
                        <td className="px-3 py-2 text-text-700">{formatearFecha(intento.creado_en)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <p className="text-sm text-text-600">Sin intentos registrados.</p>
            )}
          </section>

          <section aria-labelledby="historial-titulo">
            <h2 id="historial-titulo" className="mb-4 text-lg font-semibold text-text-900">
              Historial
            </h2>
            <div className="relative overflow-x-auto" tabIndex={0} role="region" aria-label={`Historial de la notificación a ${notificacion.nombre}`}>
              <table className="w-full min-w-[720px] border-collapse text-sm">
                <caption className="sr-only">Historial de versiones de la notificación a {notificacion.nombre}</caption>
                <thead>
                  <tr className="border-b border-border-default text-left text-text-600">
                    <th scope="col" className="px-3 py-2 font-medium">
                      Versión
                    </th>
                    <th scope="col" className="px-3 py-2 font-medium">
                      Estado
                    </th>
                    <th scope="col" className="px-3 py-2 font-medium">
                      Motivo
                    </th>
                    <th scope="col" className="px-3 py-2 font-medium">
                      Actor
                    </th>
                    <th scope="col" className="px-3 py-2 font-medium">
                      Fecha
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {versionesOrdenadas.map((version) => (
                    <tr key={version.version} className="border-b border-border-subtle align-top">
                      <td className="px-3 py-2 font-mono text-text-900">{version.version}</td>
                      <td className="px-3 py-2 text-text-900">{ETIQUETA_ESTADO_NOTIFICACION[version.estado]}</td>
                      <td className="px-3 py-2 text-text-700">{version.motivo ?? "—"}</td>
                      <td className="px-3 py-2 text-text-700">{version.actor ?? "—"}</td>
                      <td className="px-3 py-2 text-text-700">{formatearFecha(version.creado_en)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>

          {panel.tipo === "corregir" && (
            <section className="mt-6" aria-label="Corregir los datos del destinatario">
              <DestinatarioFormulario
                key={`corregir-${notificacion.id}`}
                titulo="Corregir los datos del destinatario"
                textoConfirmar="Guardar cambios"
                inicial={{
                  tipo_persona: notificacion.tipo_persona,
                  nombre: notificacion.nombre,
                  identificacion: notificacion.identificacion,
                  domicilio: notificacion.domicilio,
                  apoderado_nombre: notificacion.apoderado_nombre,
                  apoderado_identificacion: notificacion.apoderado_identificacion,
                  recursos: notificacion.recursos,
                }}
                onConfirmar={corregirDatos}
                onCancelar={() => setPanel({ tipo: "ninguno" })}
                erroresServidor={erroresServidor}
              />
            </section>
          )}
          {panel.tipo === "intento" && (
            <section className="mt-6" aria-label="Registrar intento">
              <RegistrarIntento
                key={`intento-${panel.modo}-${notificacion.id}`}
                notificacion={notificacion}
                modo={panel.modo}
                onConfirmar={registrarIntento}
                onCancelar={() => setPanel({ tipo: "ninguno" })}
                erroresServidor={erroresServidor}
              />
            </section>
          )}
          {panel.tipo === "anular" && (
            <section className="mt-6" aria-label="Anular notificación">
              <AnularNotificacion
                key={`anular-${notificacion.id}`}
                notificacion={notificacion}
                onConfirmar={anularNotificacion}
                onCancelar={() => setPanel({ tipo: "ninguno" })}
                erroresServidor={erroresServidor}
              />
            </section>
          )}
        </>
      )}
    </PageContent>
  );
}
