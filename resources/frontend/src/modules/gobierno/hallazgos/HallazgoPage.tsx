import { useState } from "react";
import { Link, useParams } from "react-router";
import { useQuery, useQueryClient } from "@tanstack/react-query";

import { apiFetch, ApiError } from "@/api/client";
import { useCompany } from "@/app/contexts/CompanyContext";
import { useAutoridad } from "@/app/autoridad/AutoridadContext";
import { useNotifications } from "@/app/contexts/NotificationContext";
import { PageContent } from "@/layout/PageContent";
import { PageHeader } from "@/components/PageHeader";
import { Button } from "@/components/Button";
import { FormField } from "@/components/FormField";
import { EmptyState } from "@/components/EmptyState";
import { ErrorState } from "@/components/ErrorState";
import { LoadingState } from "@/components/LoadingState";
import { ConflictState } from "@/components/ConflictState";
import { ConflictoSoD, detalleDeConflictoSod } from "@/modules/gobierno/sod/ConflictoSoD";
import { formatearFecha } from "@/i18n";
import {
  CONSULTA_HALLAZGOS,
  HallazgoDetalle,
  ETIQUETA_ESTADO_HALLAZGO,
  ETIQUETA_RIESGO_HALLAZGO,
  ETIQUETA_ORIGEN_HALLAZGO,
  ETIQUETA_HISTORIA_HALLAZGO,
  type DetalleConflictoSod,
  EstadoHallazgo,
  HistoriaHallazgo,
} from "@/modules/gobierno/api";
import { PlanDeAccion } from "./PlanDeAccion";

const PASOS_PROCESO: EstadoHallazgo[] = [
  "ABIERTO",
  "PLAN_DE_ACCION",
  "EN_REMEDIACION",
  "EVIDENCIA_PRESENTADA",
  "CERRADO",
];

function obtenerDetalleTexto(detalle: Record<string, unknown> | null): string | null {
  if (!detalle) return null;
  const motivo = detalle.motivo;
  if (typeof motivo === "string" && motivo.trim() !== "") return motivo;
  const nota = detalle.nota;
  if (typeof nota === "string" && nota.trim() !== "") return nota;
  return null;
}

type PanelVerificacion = null | { tipo: "verificar"; nota: string } | { tipo: "devolver"; motivo: string };

export function HallazgoPage(): React.JSX.Element {
  const { hallazgoId } = useParams();
  const { activeCompanyId } = useCompany();
  const { tiene } = useAutoridad();
  const { notify } = useNotifications();
  const queryClient = useQueryClient();

  const [panelVerificacion, setPanelVerificacion] = useState<PanelVerificacion>(null);
  const [verificacionNota, setVerificacionNota] = useState("");
  const [devolucionMotivo, setDevolucionMotivo] = useState("");
  const [erroresServidor, setErroresServidor] = useState<Record<string, string[]>>({});
  const [conflicto, setConflicto] = useState(false);
  const [alertaAutoVerificacion, setAlertaAutoVerificacion] = useState<string | null>(null);
  const [conflictoSod, setConflictoSod] = useState<DetalleConflictoSod | null>(null);

  const claveDetalle = [...CONSULTA_HALLAZGOS, activeCompanyId, "detalle", hallazgoId];

  const consultaDetalle = useQuery({
    queryKey: claveDetalle,
    queryFn: () => apiFetch<HallazgoDetalle>(`/gobierno/hallazgos/${hallazgoId}`),
    enabled: Boolean(activeCompanyId && hallazgoId),
    retry: false,
  });

  const puedeGestionar = tiene("gobierno_hallazgos:manage", "empresa");
  const puedeVerificar = tiene("gobierno_hallazgos:verify", "empresa");
  const puedeVerAuditoria = tiene("gobierno_auditoria:view", "empresa");

  const recargar = () => {
    void queryClient.invalidateQueries({ queryKey: [...CONSULTA_HALLAZGOS] });
  };

  const manejarError = (e: unknown) => {
    const sod = detalleDeConflictoSod(e);
    if (sod) {
      setConflictoSod(sod);
      recargar();
      return;
    }
    if (e instanceof ApiError) {
      if (e.status === 409 && e.code === "GOV_FINDING_STALE") {
        setConflicto(true);
        recargar();
        return;
      }
      if (e.status === 409 && e.code === "GOV_FINDING_SELF_VERIFICATION") {
        setAlertaAutoVerificacion(
          "Quien registró la evidencia o presentó el hallazgo no puede verificarlo. Debe hacerlo otro usuario de Control Interno.",
        );
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
      notify({ type: "warning", title: e.message });
      return;
    }
    notify({ type: "error", title: "No fue posible completar la operación" });
  };

  const cabeceraSinDetalle = (
    <PageHeader
      crumbs={[{ label: "Gobierno" }, { label: "Hallazgos y acciones correctivas", to: "/gobierno/hallazgos" }]}
      title="Hallazgo"
    />
  );

  if (consultaDetalle.isLoading) {
    return (
      <PageContent>
        {cabeceraSinDetalle}
        <LoadingState label="Cargando hallazgo…" />
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
            action={<Link to="/gobierno/hallazgos">Volver a Hallazgos y acciones correctivas</Link>}
          />
        </PageContent>
      );
    }
    if (error instanceof ApiError && error.status === 403) {
      return (
        <PageContent>
          {cabeceraSinDetalle}
          <EmptyState title="Sin acceso" description="No tiene permiso para ver este hallazgo." />
        </PageContent>
      );
    }
    if (error instanceof ApiError && error.status === 404 && error.code === "GOV_FINDING_NOT_FOUND") {
      return (
        <PageContent>
          {cabeceraSinDetalle}
          <EmptyState
            title="Hallazgo no encontrado"
            description="El hallazgo no existe o no pertenece a este ente."
            action={<Link to="/gobierno/hallazgos">Volver a Hallazgos y acciones correctivas</Link>}
          />
        </PageContent>
      );
    }
    return (
      <PageContent>
        {cabeceraSinDetalle}
        <ErrorState message="No fue posible cargar el hallazgo." onRetry={() => void consultaDetalle.refetch()} />
      </PageContent>
    );
  }

  const detalle = consultaDetalle.data;
  if (!detalle) {
    return (
      <PageContent>
        {cabeceraSinDetalle}
        <ErrorState message="No fue posible cargar el hallazgo." onRetry={() => void consultaDetalle.refetch()} />
      </PageContent>
    );
  }

  if (conflicto) {
    return (
      <PageContent>
        <PageHeader
          crumbs={[{ label: "Gobierno" }, { label: "Hallazgos y acciones correctivas", to: "/gobierno/hallazgos" }]}
          title={`Hallazgo ${detalle.codigo}`}
          description={detalle.titulo}
        />
        <ConflictState
          message="El hallazgo cambió; recárguelo."
          onReload={() => {
            setConflicto(false);
            void consultaDetalle.refetch();
          }}
        />
      </PageContent>
    );
  }

  const noTieneAccionesTodasLasRecomendaciones =
    detalle.recomendaciones.length === 0 ||
    detalle.recomendaciones.some(
      (recomendacion) =>
        !detalle.acciones.some((accion) => accion.recomendacion_id === recomendacion.id),
    );

  const hayAccionesPendientes =
    detalle.estado === "EN_REMEDIACION" &&
    detalle.acciones.some((accion) => accion.estado !== "COMPLETADA");

  const indicePasoActual = PASOS_PROCESO.indexOf(detalle.estado);

  const escribirDetalle = async (
    ruta: string,
    body: Record<string, unknown>,
    mensajeExito: string,
  ) => {
    try {
      const nuevoDetalle = await apiFetch<HallazgoDetalle>(ruta, {
        method: "POST",
        body,
        ifMatch: String(detalle.version),
      });
      queryClient.setQueryData(claveDetalle, nuevoDetalle);
      void queryClient.invalidateQueries({ queryKey: [...CONSULTA_HALLAZGOS] });
      notify({ type: "success", title: mensajeExito });
      setErroresServidor({});
      setAlertaAutoVerificacion(null);
      return nuevoDetalle;
    } catch (e) {
      manejarError(e);
      throw e;
    }
  };

  const registrarPlan = async () => {
    try {
      await escribirDetalle(`/gobierno/hallazgos/${detalle.id}/plan`, {}, "Plan de acción registrado");
    } catch {
      return;
    }
  };

  const iniciarEjecucion = async () => {
    try {
      await escribirDetalle(`/gobierno/hallazgos/${detalle.id}/ejecucion`, {}, "Ejecución iniciada");
    } catch {
      return;
    }
  };

  const presentarVerificacion = async () => {
    try {
      await escribirDetalle(`/gobierno/hallazgos/${detalle.id}/presentar`, {}, "Hallazgo presentado a verificación");
    } catch {
      return;
    }
  };

  const verificarHallazgo = async () => {
    try {
      await escribirDetalle(
        `/gobierno/hallazgos/${detalle.id}/verificar`,
        { nota: verificacionNota },
        "Hallazgo verificado y cerrado",
      );
    } catch {
      return;
    }
    setPanelVerificacion(null);
    setVerificacionNota("");
  };

  const devolverHallazgo = async () => {
    try {
      await escribirDetalle(
        `/gobierno/hallazgos/${detalle.id}/devolver`,
        { motivo: devolucionMotivo },
        "Hallazgo devuelto",
      );
    } catch {
      return;
    }
    setPanelVerificacion(null);
    setDevolucionMotivo("");
  };

  const onSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
  };

  const accionesCabecera = (
    <div className="flex flex-wrap items-center gap-2">
      {detalle.estado === "ABIERTO" && puedeGestionar && (
        <>
          <Button
            variant="primary"
            disabled={noTieneAccionesTodasLasRecomendaciones}
            aria-describedby="ayuda-plan-accion"
            onClick={() => void registrarPlan()}
          >
            Registrar plan
          </Button>
          <p id="ayuda-plan-accion" className="sr-only">
            Cada recomendación necesita al menos una acción correctiva.
          </p>
        </>
      )}
      {detalle.estado === "PLAN_DE_ACCION" && puedeGestionar && (
        <Button variant="primary" onClick={() => void iniciarEjecucion()}>
          Iniciar ejecución
        </Button>
      )}
      {detalle.estado === "EN_REMEDIACION" && puedeGestionar && (
        <>
          <Button
            variant="primary"
            disabled={hayAccionesPendientes}
            aria-describedby="ayuda-presentar"
            onClick={() => void presentarVerificacion()}
          >
            Presentar a verificación
          </Button>
          <p id="ayuda-presentar" className="sr-only">
            Todas las acciones deben estar completadas antes de presentar a verificación.
          </p>
        </>
      )}
      {detalle.estado === "EVIDENCIA_PRESENTADA" && puedeVerificar && (
        <>
          <Button variant="primary" onClick={() => setPanelVerificacion({ tipo: "verificar", nota: "" })}>
            Verificar y cerrar
          </Button>
          <Button variant="secondary" onClick={() => setPanelVerificacion({ tipo: "devolver", motivo: "" })}>
            Devolver
          </Button>
        </>
      )}
    </div>
  );

  const seccionVerificacion = (
    <section aria-labelledby="verificacion-titulo" className="mb-8">
      <h2 id="verificacion-titulo" className="mb-4 text-lg font-semibold text-text-900">
        Verificación
      </h2>
      {(detalle.estado === "CERRADO" || detalle.estado === "EVIDENCIA_PRESENTADA") &&
      (detalle.presentado_por || detalle.presentado_en || detalle.verificado_por || detalle.verificado_en) ? (
        <dl className="grid grid-cols-1 gap-x-8 gap-y-3 md:grid-cols-2">
          <div>
            <dt className="text-sm text-text-600">Presentado por</dt>
            <dd className="text-text-900">{detalle.presentado_por ?? "—"}</dd>
          </div>
          <div>
            <dt className="text-sm text-text-600">Presentado en</dt>
            <dd className="text-text-900">{detalle.presentado_en ? formatearFecha(detalle.presentado_en) : "—"}</dd>
          </div>
          <div>
            <dt className="text-sm text-text-600">Verificado por</dt>
            <dd className="text-text-900">{detalle.verificado_por ?? "—"}</dd>
          </div>
          <div>
            <dt className="text-sm text-text-600">Verificado en</dt>
            <dd className="text-text-900">{detalle.verificado_en ? formatearFecha(detalle.verificado_en) : "—"}</dd>
          </div>
          <div className="md:col-span-2">
            <dt className="text-sm text-text-600">Nota de verificación</dt>
            <dd className="whitespace-pre-wrap text-text-900">{detalle.nota_verificacion ?? "—"}</dd>
          </div>
        </dl>
      ) : (
        <p className="text-text-700">Pendiente</p>
      )}
    </section>
  );

  const seccionHistoria = (
    <section aria-labelledby="historia-titulo" className="mb-8">
      <h2 id="historia-titulo" className="mb-4 text-lg font-semibold text-text-900">
        Historia
      </h2>
      <div
        className="relative overflow-x-auto"
        tabIndex={0}
        role="region"
        aria-label={`Historia del hallazgo ${detalle.codigo}`}
      >
        <table className="w-full min-w-[720px] border-collapse text-sm">
          <caption className="sr-only">Historia del hallazgo {detalle.codigo}</caption>
          <thead>
            <tr className="border-b border-border-default text-left text-text-600">
              <th scope="col" className="px-3 py-2 font-medium">
                Fecha
              </th>
              <th scope="col" className="px-3 py-2 font-medium">
                Evento
              </th>
              <th scope="col" className="px-3 py-2 font-medium">
                Estado
              </th>
              <th scope="col" className="px-3 py-2 font-medium">
                Detalle
              </th>
              <th scope="col" className="px-3 py-2 font-medium">
                Usuario
              </th>
            </tr>
          </thead>
          <tbody>
            {detalle.historia.map((historia: HistoriaHallazgo) => (
              <tr key={historia.id} className="border-b border-border-subtle align-top">
                <td className="px-3 py-2 text-text-700">{formatearFecha(historia.created_at)}</td>
                <td className="px-3 py-2 text-text-900">
                  {ETIQUETA_HISTORIA_HALLAZGO[historia.tipo] ?? historia.tipo}
                </td>
                <td className="px-3 py-2 text-text-700">
                  {historia.estado_desde
                    ? ETIQUETA_ESTADO_HALLAZGO[historia.estado_desde] ?? historia.estado_desde
                    : "—"}
                  {historia.estado_hasta && historia.estado_hasta !== historia.estado_desde
                    ? ` → ${ETIQUETA_ESTADO_HALLAZGO[historia.estado_hasta] ?? historia.estado_hasta}`
                    : ""}
                </td>
                <td className="px-3 py-2 text-text-700">{obtenerDetalleTexto(historia.detalle) ?? "—"}</td>
                <td className="px-3 py-2 text-text-700">{historia.created_by ?? "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );

  const panelVerificacionRender =
    panelVerificacion?.tipo === "verificar" ? (
      <section aria-labelledby="verificar-titulo" className="mb-8 rounded-lg border border-border-subtle p-4">
        <h2 id="verificar-titulo" className="mb-4 text-lg font-semibold text-text-900">
          Verificar y cerrar
        </h2>
        <form onSubmit={onSubmit}>
          <FormField
            label="Nota de verificación"
            htmlFor="nota-verificacion"
            required
            error={erroresServidor.nota?.[0]}
          >
            <textarea
              id="nota-verificacion"
              className="w-full rounded-md border border-border-default bg-surface px-3 py-2 text-text-900"
              minLength={10}
              maxLength={2000}
              value={verificacionNota}
              onChange={(e) => setVerificacionNota(e.target.value)}
            />
          </FormField>
          <div className="mt-4 flex gap-2">
            <Button
              variant="primary"
              disabled={verificacionNota.trim().length < 10 || verificacionNota.length > 2000}
              onClick={() => void verificarHallazgo()}
            >
              Confirmar verificación
            </Button>
            <Button variant="secondary" onClick={() => setPanelVerificacion(null)}>
              Cancelar
            </Button>
          </div>
        </form>
      </section>
    ) : panelVerificacion?.tipo === "devolver" ? (
      <section aria-labelledby="devolver-titulo" className="mb-8 rounded-lg border border-border-subtle p-4">
        <h2 id="devolver-titulo" className="mb-4 text-lg font-semibold text-text-900">
          Devolver
        </h2>
        <form onSubmit={onSubmit}>
          <FormField
            label="Motivo de la devolución"
            htmlFor="motivo-devolucion"
            required
            error={erroresServidor.motivo?.[0]}
          >
            <textarea
              id="motivo-devolucion"
              className="w-full rounded-md border border-border-default bg-surface px-3 py-2 text-text-900"
              minLength={10}
              maxLength={2000}
              value={devolucionMotivo}
              onChange={(e) => setDevolucionMotivo(e.target.value)}
            />
          </FormField>
          <div className="mt-4 flex gap-2">
            <Button
              variant="primary"
              disabled={devolucionMotivo.trim().length < 10 || devolucionMotivo.length > 2000}
              onClick={() => void devolverHallazgo()}
            >
              Confirmar devolución
            </Button>
            <Button variant="secondary" onClick={() => setPanelVerificacion(null)}>
              Cancelar
            </Button>
          </div>
        </form>
      </section>
    ) : null;

  return (
    <PageContent>
      <PageHeader
        crumbs={[{ label: "Gobierno" }, { label: "Hallazgos y acciones correctivas", to: "/gobierno/hallazgos" }]}
        title={`Hallazgo ${detalle.codigo}`}
        description={detalle.titulo}
        actions={accionesCabecera}
      />

      {conflictoSod && <ConflictoSoD detalle={conflictoSod} onCerrar={() => setConflictoSod(null)} />}

      {alertaAutoVerificacion && (
        <div role="alert" className="mb-4 rounded-md border border-error-300 bg-error-50 p-3 text-error-800">
          {alertaAutoVerificacion}
        </div>
      )}

      <section aria-labelledby="estado-titulo" className="mb-8">
        <h2 id="estado-titulo" className="mb-4 text-lg font-semibold text-text-900">
          Estado
        </h2>
        <span className="inline-flex items-center rounded-full bg-primary-100 px-3 py-1 text-sm font-medium text-primary-800">
          {ETIQUETA_ESTADO_HALLAZGO[detalle.estado]}
        </span>
        <ol className="mt-4 flex flex-col gap-2 sm:flex-row sm:items-center sm:gap-1">
          {PASOS_PROCESO.map((paso, indice) => (
            <li key={paso} className="flex items-center gap-2">
              <span
                className={
                  indice === indicePasoActual
                    ? "rounded-full bg-primary-100 px-3 py-1 text-sm font-medium text-primary-800"
                    : "rounded-full bg-surface-muted px-3 py-1 text-sm text-text-600"
                }
                aria-current={indice === indicePasoActual ? "step" : undefined}
              >
                {ETIQUETA_ESTADO_HALLAZGO[paso]}
              </span>
              {indice < PASOS_PROCESO.length - 1 && (
                <span className="text-text-400" aria-hidden="true">
                  →
                </span>
              )}
            </li>
          ))}
        </ol>
      </section>

      <section aria-labelledby="hallazgo-titulo" className="mb-8">
        <h2 id="hallazgo-titulo" className="mb-4 text-lg font-semibold text-text-900">
          Hallazgo
        </h2>
        <dl className="grid grid-cols-1 gap-x-8 gap-y-3 md:grid-cols-2">
          <div>
            <dt className="text-sm text-text-600">Riesgo</dt>
            <dd className="text-text-900">{ETIQUETA_RIESGO_HALLAZGO[detalle.riesgo] ?? detalle.riesgo}</dd>
          </div>
          <div>
            <dt className="text-sm text-text-600">Condición</dt>
            <dd className="text-text-900">{detalle.condicion}</dd>
          </div>
          <div>
            <dt className="text-sm text-text-600">Criterio</dt>
            <dd className="text-text-900">{detalle.criterio}</dd>
          </div>
          <div>
            <dt className="text-sm text-text-600">Causa</dt>
            <dd className="text-text-900">{detalle.causa}</dd>
          </div>
          <div>
            <dt className="text-sm text-text-600">Efecto</dt>
            <dd className="text-text-900">{detalle.efecto}</dd>
          </div>
          <div>
            <dt className="text-sm text-text-600">Registrado por</dt>
            <dd className="text-text-900">{detalle.created_by ?? "—"}</dd>
          </div>
          <div>
            <dt className="text-sm text-text-600">Registrado el</dt>
            <dd className="text-text-900">{formatearFecha(detalle.created_at)}</dd>
          </div>
        </dl>
      </section>

      <section aria-labelledby="origen-titulo" className="mb-8">
        <h2 id="origen-titulo" className="mb-4 text-lg font-semibold text-text-900">
          Origen
        </h2>
        {detalle.origen === "MUESTRA" && detalle.muestra ? (
          <div className="space-y-2">
            {puedeVerAuditoria ? (
              <Link
                to={`/gobierno/auditoria/muestras/${detalle.muestra.id}`}
                className="text-primary-700 underline"
              >
                Muestra {detalle.muestra.codigo} · {detalle.muestra.titulo}
              </Link>
            ) : (
              <p className="text-text-700">
                Muestra {detalle.muestra.codigo} · {detalle.muestra.titulo}
              </p>
            )}
            {detalle.partidas.map((partidaId, indice) => (
              <div key={partidaId}>
                {puedeVerAuditoria ? (
                  <Link
                    to={`/gobierno/auditoria?evento=${partidaId}`}
                    className="text-primary-700 underline"
                  >
                    Ver evidencia de la partida {indice + 1}
                  </Link>
                ) : (
                  <p className="text-text-700">Ver evidencia de la partida {indice + 1}</p>
                )}
              </div>
            ))}
          </div>
        ) : (
          <p className="text-text-700">{detalle.origen_descripcion ?? ETIQUETA_ORIGEN_HALLAZGO[detalle.origen] ?? detalle.origen}</p>
        )}
      </section>

      <PlanDeAccion
        hallazgo={detalle}
        onActualizado={(d) => queryClient.setQueryData(claveDetalle, d)}
        onError={manejarError}
      />

      {seccionVerificacion}

      {panelVerificacionRender}

      {seccionHistoria}
    </PageContent>
  );
}
