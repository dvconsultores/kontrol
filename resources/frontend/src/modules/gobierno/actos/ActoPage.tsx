import { useMemo, useState } from "react";
import { Link, useNavigate, useParams } from "react-router";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Pencil, Trash2 } from "lucide-react";

import { apiFetch, ApiError } from "@/api/client";
import { useCompany } from "@/app/contexts/CompanyContext";
import { useAutoridad } from "@/app/autoridad/AutoridadContext";
import { useNotifications } from "@/app/contexts/NotificationContext";
import { PageContent } from "@/layout/PageContent";
import { PageHeader } from "@/components/PageHeader";
import { Button } from "@/components/Button";
import { ConfirmationDialog } from "@/components/ConfirmationDialog";
import { EmptyState } from "@/components/EmptyState";
import { ErrorState } from "@/components/ErrorState";
import { LoadingState } from "@/components/LoadingState";
import { ConflictState } from "@/components/ConflictState";
import { AdjuntosPanel } from "@/modules/documentos/AdjuntosPanel";
import { formatearFecha } from "@/i18n";
import { formatearFechaDeNegocio, hoyDeNegocio } from "@/lib/fecha-de-negocio";
import {
  CONSULTA_ACTOS,
  Acto,
  ETIQUETA_ACCION,
  ETIQUETA_CARACTER,
  ETIQUETA_ESTADO_ACTO,
  ETIQUETA_FALTANTE_ACTO,
  ETIQUETA_MATERIA,
  ETIQUETA_MEDIO,
  ETIQUETA_TITULARIDAD,
  VersionesActo,
  nombreDeActo,
  type MedioEficacia,
} from "@/modules/gobierno/api";

import { ActoFormulario, DatosActo } from "./ActoFormulario";
import { EmitirActo } from "./EmitirActo";
import { RegistrarEficacia } from "./RegistrarEficacia";
import { NotificacionesDelActo } from "@/modules/gobierno/notificaciones/NotificacionesDelActo";
import { CorregirActo, CorreccionActo } from "./CorregirActo";
import { ReferenciarActo } from "./ReferenciarActo";

type Panel =
  | { tipo: "ninguno" }
  | { tipo: "editar" }
  | { tipo: "emitir" }
  | { tipo: "registrarEficacia" }
  | { tipo: "corregir" }
  | { tipo: "referenciar"; modo: "revocar" | "anular" };

type Confirmacion = null | "eliminar";

export function ActoPage(): React.JSX.Element {
  const { actoId } = useParams();
  const { activeCompanyId } = useCompany();
  const { tiene } = useAutoridad();
  const { notify } = useNotifications();
  const queryClient = useQueryClient();
  const navigate = useNavigate();

  const [panel, setPanel] = useState<Panel>({ tipo: "ninguno" });
  const [erroresServidor, setErroresServidor] = useState<Record<string, string[]>>({});
  const [confirmar, setConfirmar] = useState<Confirmacion>(null);
  const [conflicto, setConflicto] = useState(false);

  const recargar = () => {
    void queryClient.invalidateQueries({ queryKey: [...CONSULTA_ACTOS] });
  };

  const consultaActo = useQuery({
    queryKey: [...CONSULTA_ACTOS, activeCompanyId, "detalle", actoId],
    queryFn: () => apiFetch<Acto>(`/gobierno/actos/${actoId}`),
    enabled: Boolean(activeCompanyId) && Boolean(actoId),
    retry: false,
  });

  const consultaVersiones = useQuery({
    queryKey: [...CONSULTA_ACTOS, activeCompanyId, "versiones", actoId],
    queryFn: () => apiFetch<VersionesActo>(`/gobierno/actos/${actoId}/versiones`),
    enabled: Boolean(activeCompanyId) && Boolean(actoId),
    retry: false,
  });

  const versionesOrdenadas = useMemo(() => {
    return [...(consultaVersiones.data?.items ?? [])].sort((a, b) => b.version - a.version);
  }, [consultaVersiones.data]);

  const manejarError = (e: unknown) => {
    if (e instanceof ApiError) {
      if (e.status === 409 && e.code === "GOV_ACT_STALE") {
        setConflicto(true);
        recargar();
        return;
      }
      if (e.status === 422 && e.code === "VALIDATION_ERROR") {
        setErroresServidor(e.fieldErrors);
        return;
      }
      if (e.status === 422 && e.code === "GOV_ACT_INCOMPLETE") {
        const lista: unknown = e.details?.faltantes;
        const faltantes = Array.isArray(lista)
          ? lista.map((c) => ETIQUETA_FALTANTE_ACTO[String(c) as keyof typeof ETIQUETA_FALTANTE_ACTO] ?? String(c)).join(", ")
          : "";
        notify({ type: "error", title: "Falta información para esta acción", description: faltantes });
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

  const cabeceraSinActo = (
    <PageHeader
      crumbs={[{ label: "Gobierno" }, { label: "Actos administrativos", to: "/gobierno/actos" }]}
      title="Acto administrativo"
    />
  );

  if (consultaActo.isLoading || consultaVersiones.isLoading) {
    return (
      <PageContent>
        {cabeceraSinActo}
        <LoadingState label="Cargando acto…" />
      </PageContent>
    );
  }

  if (consultaActo.isError) {
    const error = consultaActo.error;
    if (error instanceof ApiError && error.status === 403 && error.code === "MODULE_NOT_ENTITLED") {
      return (
        <PageContent>
          {cabeceraSinActo}
          <EmptyState
            title="Módulo no disponible"
            description="Su empresa no tiene contratado el módulo de Gobierno."
            action={<Link to="/gobierno/actos">Volver a Actos administrativos</Link>}
          />
        </PageContent>
      );
    }
    if (error instanceof ApiError && error.status === 403) {
      return (
        <PageContent>
          {cabeceraSinActo}
          <EmptyState title="Sin acceso" description="No tiene permiso para ver este acto." />
        </PageContent>
      );
    }
    if (error instanceof ApiError && error.status === 404 && error.code === "GOV_ACT_NOT_FOUND") {
      return (
        <PageContent>
          {cabeceraSinActo}
          <EmptyState
            title="El acto no existe o no pertenece a este ente"
            action={<Link to="/gobierno/actos">Volver a Actos administrativos</Link>}
          />
        </PageContent>
      );
    }
    return (
      <PageContent>
        {cabeceraSinActo}
        <ErrorState message="No fue posible cargar el acto." onRetry={() => void consultaActo.refetch()} />
      </PageContent>
    );
  }

  if (consultaVersiones.isError) {
    const error = consultaVersiones.error;
    if (error instanceof ApiError && error.status === 403 && error.code === "MODULE_NOT_ENTITLED") {
      return (
        <PageContent>
          {cabeceraSinActo}
          <EmptyState
            title="Módulo no disponible"
            description="Su empresa no tiene contratado el módulo de Gobierno."
            action={<Link to="/gobierno/actos">Volver a Actos administrativos</Link>}
          />
        </PageContent>
      );
    }
    if (error instanceof ApiError && error.status === 403) {
      return (
        <PageContent>
          {cabeceraSinActo}
          <EmptyState title="Sin acceso" description="No tiene permiso para ver el historial del acto." />
        </PageContent>
      );
    }
    return (
      <PageContent>
        {cabeceraSinActo}
        <ErrorState message="No fue posible cargar el historial." onRetry={() => void consultaVersiones.refetch()} />
      </PageContent>
    );
  }

  const acto = consultaActo.data;
  const versiones = consultaVersiones.data;

  if (!acto || !versiones) {
    return (
      <PageContent>
        {cabeceraSinActo}
        <ErrorState
          message="No fue posible cargar el acto."
          onRetry={() => void consultaActo.refetch()}
        />
      </PageContent>
    );
  }

  const crumbs = [
    { label: "Gobierno" },
    { label: "Actos administrativos", to: "/gobierno/actos" },
    { label: nombreDeActo(acto) },
  ];

  const puedeEditar = tiene("gobierno_actos:edit", "empresa");
  const puedeEmitir = tiene("gobierno_actos:issue", "empresa");
  const puedeAnular = tiene("gobierno_actos:annul", "empresa");

  const faltantesSinDocumento = acto.faltantes_para_emitir.filter((f) => f !== "DOCUMENTO_ACTO");
  const faltantesSinDocumentoEtiquetas = faltantesSinDocumento
    .map((f) => ETIQUETA_FALTANTE_ACTO[f] ?? f)
    .join(", ");

  const accionesCabecera = (
    <div className="flex flex-wrap items-center gap-2">
      {acto.estado === "BORRADOR" && puedeEditar && (
        <Button variant="secondary" onClick={() => setPanel({ tipo: "editar" })}>
          <Pencil className="mr-2 h-4 w-4" aria-hidden="true" />
          Editar
        </Button>
      )}
      {acto.estado === "BORRADOR" && puedeEditar && (
        <Button variant="secondary" onClick={() => setConfirmar("eliminar")}>
          <Trash2 className="mr-2 h-4 w-4" aria-hidden="true" />
          Eliminar
        </Button>
      )}
      {acto.estado === "BORRADOR" && puedeEmitir && (
        <Button
          variant="primary"
          disabled={faltantesSinDocumento.length > 0}
          aria-describedby="requisitos-emitir"
          onClick={() => setPanel({ tipo: "emitir" })}
        >
          Emitir
        </Button>
      )}
      {acto.estado === "EMITIDO" && acto.caracter === "GENERAL" && puedeEmitir && (
        <Button variant="primary" onClick={() => setPanel({ tipo: "registrarEficacia" })}>
          Registrar la publicación
        </Button>
      )}
      {(acto.estado === "EMITIDO" || acto.estado === "EFICAZ") && puedeEmitir && (
        <Button variant="secondary" onClick={() => setPanel({ tipo: "corregir" })}>
          Corregir error material
        </Button>
      )}
      {(acto.estado === "EMITIDO" || acto.estado === "EFICAZ") && puedeAnular && (
        <>
          <Button variant="secondary" onClick={() => setPanel({ tipo: "referenciar", modo: "revocar" })}>
            Registrar revocación
          </Button>
          <Button variant="secondary" onClick={() => setPanel({ tipo: "referenciar", modo: "anular" })}>
            Registrar nulidad
          </Button>
        </>
      )}
    </div>
  );

  const guardarActo = async (datos: DatosActo) => {
    try {
      await apiFetch<Acto>(`/gobierno/actos/${acto.id}`, {
        method: "PATCH",
        body: datos,
        ifMatch: String(acto.version),
      });
      notify({ type: "success", title: "Acto actualizado" });
      setPanel({ tipo: "ninguno" });
      setErroresServidor({});
      recargar();
    } catch (e) {
      manejarError(e);
    }
  };

  const emitirActo = async (datos: { documento_acto_id: string; fecha_eficacia: string | null }) => {
    try {
      await apiFetch<Acto>(`/gobierno/actos/${acto.id}/emitir`, {
        method: "POST",
        body: datos,
        ifMatch: String(acto.version),
      });
      notify({ type: "success", title: "Acto emitido" });
      setPanel({ tipo: "ninguno" });
      setErroresServidor({});
      recargar();
    } catch (e) {
      manejarError(e);
    }
  };

  const registrarEficacia = async (datos: {
    medio: MedioEficacia;
    referencia: string | null;
    fecha: string;
    documento_eficacia_id: string;
    fecha_eficacia: string | null;
  }) => {
    try {
      await apiFetch<Acto>(`/gobierno/actos/${acto.id}/eficacia`, {
        method: "POST",
        body: datos,
        ifMatch: String(acto.version),
      });
      notify({ type: "success", title: "Eficacia registrada" });
      setPanel({ tipo: "ninguno" });
      setErroresServidor({});
      recargar();
    } catch (e) {
      manejarError(e);
    }
  };

  const corregirActo = async (correccion: CorreccionActo) => {
    try {
      await apiFetch<Acto>(`/gobierno/actos/${acto.id}/corregir`, {
        method: "POST",
        body: correccion,
        ifMatch: String(acto.version),
      });
      notify({ type: "success", title: "Corrección registrada" });
      setPanel({ tipo: "ninguno" });
      setErroresServidor({});
      recargar();
    } catch (e) {
      manejarError(e);
    }
  };

  const referenciarActo = async (datos: { acto_id_referencia: string; motivo: string }) => {
    if (panel.tipo !== "referenciar") return;
    const endpoint = panel.modo === "revocar" ? "revocar" : "anular";
    try {
      await apiFetch<Acto>(`/gobierno/actos/${acto.id}/${endpoint}`, {
        method: "POST",
        body: datos,
        ifMatch: String(acto.version),
      });
      notify({
        type: "success",
        title: panel.modo === "revocar" ? "Revocación registrada" : "Nulidad registrada",
      });
      setPanel({ tipo: "ninguno" });
      setErroresServidor({});
      recargar();
    } catch (e) {
      manejarError(e);
    }
  };

  const eliminarActo = async () => {
    try {
      await apiFetch<void>(`/gobierno/actos/${acto.id}`, {
        method: "DELETE",
        ifMatch: String(acto.version),
      });
      notify({ type: "success", title: "Acto eliminado" });
      recargar();
      navigate("/gobierno/actos");
    } catch (e) {
      manejarError(e);
    } finally {
      setConfirmar(null);
    }
  };

  const hoyNegocio = hoyDeNegocio();

  const avisoEstado = () => {
    if (acto.estado === "EMITIDO") {
      return (
        <p role="status" className="mb-4 rounded-md bg-surface-100 px-4 py-3 text-sm text-text-700">
          Emitido, pendiente de {acto.caracter === "GENERAL" ? "publicación en Gaceta" : "notificación"}.
        </p>
      );
    }
    if (acto.estado === "EFICAZ" && acto.fecha_eficacia) {
      const fecha = formatearFechaDeNegocio(acto.fecha_eficacia);
      const esFutura = acto.fecha_eficacia > hoyNegocio;
      return (
        <p role="status" className="mb-4 rounded-md bg-surface-100 px-4 py-3 text-sm text-text-700">
          {esFutura ? `Eficaz a partir de ${fecha}` : `Eficaz desde ${fecha}`}.
        </p>
      );
    }
    if (acto.estado === "REVOCADO" && acto.revocado_por) {
      const referido = acto.revocado_por;
      return (
        <p role="status" className="mb-4 rounded-md bg-surface-100 px-4 py-3 text-sm text-text-700">
          Revocado por{" "}
          <Link to={`/gobierno/actos/${referido.id}`} className="font-medium text-text-900 underline">
            {nombreDeActo(referido)}
          </Link>{" "}
          del {formatearFechaDeNegocio(referido.fecha)}.
        </p>
      );
    }
    if (acto.estado === "NULO" && acto.anulado_por) {
      const referido = acto.anulado_por;
      return (
        <p role="status" className="mb-4 rounded-md bg-surface-100 px-4 py-3 text-sm text-text-700">
          Declarado nulo por{" "}
          <Link to={`/gobierno/actos/${referido.id}`} className="font-medium text-text-900 underline">
            {nombreDeActo(referido)}
          </Link>{" "}
          del {formatearFechaDeNegocio(referido.fecha)}.
        </p>
      );
    }
    return null;
  };

  return (
    <PageContent>
      <PageHeader
        crumbs={crumbs}
        title={nombreDeActo(acto)}
        status={
          <span className="inline-flex items-center rounded-full bg-surface-100 px-3 py-1 text-sm font-medium text-text-700">
            {ETIQUETA_ESTADO_ACTO[acto.estado]}
          </span>
        }
        actions={accionesCabecera}
      />

      {conflicto ? (
        <ConflictState
          message="Otra persona cambió el acto mientras trabajaba. Se cargó la versión vigente."
          onReload={() => {
            setConflicto(false);
            setPanel({ tipo: "ninguno" });
          }}
        />
      ) : (
        <>
          {avisoEstado()}

          {acto.estado === "BORRADOR" && acto.faltantes_para_emitir.length > 0 && (
            <section id="requisitos-emitir" aria-labelledby="requisitos-emitir-titulo" className="mb-8">
              <h2 id="requisitos-emitir-titulo" className="mb-2 text-lg font-semibold text-text-900">
                Requisitos para emitir
              </h2>
              <p className="text-sm text-text-700">Para emitirlo falta:</p>
              <ul className="mt-2 list-disc pl-6 text-sm text-text-700">
                {acto.faltantes_para_emitir.map((f) => (
                  <li key={f}>{ETIQUETA_FALTANTE_ACTO[f]}</li>
                ))}
              </ul>
              {faltantesSinDocumento.length > 0 && (
                <p className="mt-2 text-sm font-medium text-error-700">
                  Complete primero: {faltantesSinDocumentoEtiquetas}.
                </p>
              )}
            </section>
          )}

          <section aria-labelledby="datos-acto-titulo" className="mb-8">
            <h2 id="datos-acto-titulo" className="mb-4 text-lg font-semibold text-text-900">
              Datos del acto
            </h2>
            <dl className="grid gap-x-8 gap-y-4 text-sm sm:grid-cols-2">
              <div>
                <dt className="font-medium text-text-600">Tipo</dt>
                <dd className="mt-1 text-text-900">{nombreDeActo(acto)}</dd>
              </div>
              <div>
                <dt className="font-medium text-text-600">Número</dt>
                <dd className="mt-1 font-mono text-text-900">{acto.numero}</dd>
              </div>
              <div>
                <dt className="font-medium text-text-600">Fecha</dt>
                <dd className="mt-1 text-text-900">{formatearFechaDeNegocio(acto.fecha)}</dd>
              </div>
              <div>
                <dt className="font-medium text-text-600">Lugar</dt>
                <dd className="mt-1 text-text-900">{acto.lugar}</dd>
              </div>
              <div>
                <dt className="font-medium text-text-600">Carácter</dt>
                <dd className="mt-1 text-text-900">{ETIQUETA_CARACTER[acto.caracter]}</dd>
              </div>
              {acto.simple_tramite && (
                <div>
                  <dt className="font-medium text-text-600">Simple trámite</dt>
                  <dd className="mt-1 text-text-900">Sí</dd>
                </div>
              )}
              <div className="sm:col-span-2">
                <dt className="font-medium text-text-600">Destinatario</dt>
                <dd className="mt-1 text-text-900">{acto.destinatario ?? "—"}</dd>
              </div>
              <div className="sm:col-span-2">
                <dt className="font-medium text-text-600">Asunto</dt>
                <dd className="mt-1 text-text-900">{acto.asunto}</dd>
              </div>
            </dl>
          </section>

          <section aria-labelledby="autoridad-titulo" className="mb-8">
            <h2 id="autoridad-titulo" className="mb-4 text-lg font-semibold text-text-900">
              Autoridad
            </h2>
            <dl className="grid gap-x-8 gap-y-4 text-sm sm:grid-cols-2">
              <div>
                <dt className="font-medium text-text-600">Cargo</dt>
                <dd className="mt-1 text-text-900">
                  {acto.cargo.unidad_codigo} · {acto.cargo.codigo} — {acto.cargo.denominacion}
                </dd>
              </div>
              <div>
                <dt className="font-medium text-text-600">Competencia</dt>
                <dd className="mt-1 text-text-900">
                  {ETIQUETA_ACCION[acto.competencia.accion]} · {ETIQUETA_MATERIA[acto.competencia.materia]}
                </dd>
              </div>
              <div className="sm:col-span-2">
                <dt className="font-medium text-text-600">Fundamento</dt>
                <dd className="mt-1 text-text-900">{acto.fundamento_competencia}</dd>
              </div>
              <div>
                <dt className="font-medium text-text-600">Funcionario</dt>
                <dd className="mt-1 text-text-900">{acto.funcionario}</dd>
              </div>
              <div>
                <dt className="font-medium text-text-600">Titularidad</dt>
                <dd className="mt-1 text-text-900">{ETIQUETA_TITULARIDAD[acto.titularidad]}</dd>
              </div>
              {acto.titularidad === "DELEGACION" && acto.delegacion_numero && (
                <div className="sm:col-span-2">
                  <dt className="font-medium text-text-600">Por delegación</dt>
                  <dd className="mt-1 text-text-900">
                    acto Nº {acto.delegacion_numero}
                    {acto.delegacion_fecha ? ` del ${formatearFechaDeNegocio(acto.delegacion_fecha)}` : ""}
                  </dd>
                </div>
              )}
            </dl>
          </section>

          <section aria-labelledby="motivacion-titulo" className="mb-8">
            <h2 id="motivacion-titulo" className="mb-4 text-lg font-semibold text-text-900">
              Motivación y decisión
            </h2>
            <dl className="grid gap-x-8 gap-y-4 text-sm">
              <div>
                <dt className="font-medium text-text-600">Hechos</dt>
                <dd className="mt-1 whitespace-pre-line text-text-900">{acto.hechos ?? "—"}</dd>
              </div>
              <div>
                <dt className="font-medium text-text-600">Fundamentos legales</dt>
                <dd className="mt-1 whitespace-pre-line text-text-900">{acto.fundamentos ?? "—"}</dd>
              </div>
              <div>
                <dt className="font-medium text-text-600">Decisión</dt>
                <dd className="mt-1 whitespace-pre-line text-text-900">{acto.decision ?? "—"}</dd>
              </div>
            </dl>
          </section>

          <section aria-labelledby="eficacia-titulo" className="mb-8">
            <h2 id="eficacia-titulo" className="mb-4 text-lg font-semibold text-text-900">
              Eficacia
            </h2>
            <dl className="grid gap-x-8 gap-y-4 text-sm sm:grid-cols-2">
              <div>
                <dt className="font-medium text-text-600">Medio</dt>
                <dd className="mt-1 text-text-900">{acto.medio ? ETIQUETA_MEDIO[acto.medio] : "—"}</dd>
              </div>
              <div>
                <dt className="font-medium text-text-600">Referencia</dt>
                <dd className="mt-1 text-text-900">{acto.referencia_publicacion ?? "—"}</dd>
              </div>
              <div>
                <dt className="font-medium text-text-600">
                  {acto.caracter === "GENERAL" ? "Fecha de publicación" : "Fecha de notificación"}
                </dt>
                <dd className="mt-1 text-text-900">
                  {acto.fecha_publicacion_notificacion
                    ? formatearFechaDeNegocio(acto.fecha_publicacion_notificacion)
                    : "—"}
                </dd>
              </div>
              <div>
                <dt className="font-medium text-text-600">Fecha de eficacia</dt>
                <dd className="mt-1 text-text-900">
                  {acto.fecha_eficacia ? formatearFechaDeNegocio(acto.fecha_eficacia) : "—"}
                </dd>
              </div>
            </dl>
          </section>

          {acto.caracter === "PARTICULAR" && acto.estado !== "BORRADOR" && (
            <section aria-labelledby="notificaciones-acto-titulo" className="mb-8">
              <h2 id="notificaciones-acto-titulo" className="mb-4 text-lg font-semibold text-text-900">
                Notificaciones
              </h2>
              <NotificacionesDelActo acto={acto} />
            </section>
          )}

          <section aria-labelledby="relaciones-titulo" className="mb-8">
            <h2 id="relaciones-titulo" className="mb-4 text-lg font-semibold text-text-900">
              Relaciones
            </h2>
            {acto.revoca_a.length > 0 || acto.anula_a.length > 0 ? (
              <dl className="grid gap-x-8 gap-y-4 text-sm sm:grid-cols-2">
                {acto.revoca_a.length > 0 && (
                  <div>
                    <dt className="font-medium text-text-600">Revoca a</dt>
                    <dd className="mt-1">
                      <ul className="list-inside list-disc space-y-1 text-text-900">
                        {acto.revoca_a.map((ref) => (
                          <li key={ref.id}>
                            <Link to={`/gobierno/actos/${ref.id}`} className="text-text-900 underline">
                              {nombreDeActo(ref)}
                            </Link>
                          </li>
                        ))}
                      </ul>
                    </dd>
                  </div>
                )}
                {acto.anula_a.length > 0 && (
                  <div>
                    <dt className="font-medium text-text-600">Anula a</dt>
                    <dd className="mt-1">
                      <ul className="list-inside list-disc space-y-1 text-text-900">
                        {acto.anula_a.map((ref) => (
                          <li key={ref.id}>
                            <Link to={`/gobierno/actos/${ref.id}`} className="text-text-900 underline">
                              {nombreDeActo(ref)}
                            </Link>
                          </li>
                        ))}
                      </ul>
                    </dd>
                  </div>
                )}
              </dl>
            ) : (
              <p className="text-sm text-text-600">Este acto no revoca ni anula otros actos.</p>
            )}
          </section>

          <section aria-labelledby="documentos-acto-titulo" className="mb-8">
            <h2 id="documentos-acto-titulo" className="mb-4 text-lg font-semibold text-text-900">
              Documentos del acto
            </h2>
            <AdjuntosPanel
              resourceType="GovernmentAct"
              resourceId={acto.id}
              title="Documentos del acto"
              onChange={() => void recargar()}
            />
          </section>

          <section aria-labelledby="historial-titulo">
            <h2 id="historial-titulo" className="mb-4 text-lg font-semibold text-text-900">
              Historial
            </h2>
            <div className="relative overflow-x-auto" tabIndex={0} role="region" aria-label={`Historial del acto ${nombreDeActo(acto)}`}>
              <table className="w-full min-w-[720px] border-collapse text-sm">
                <caption className="sr-only">Historial de versiones del acto {nombreDeActo(acto)}</caption>
                <thead>
                  <tr className="border-b border-border-default text-left text-text-600">
                    <th scope="col" className="px-3 py-2 font-medium">
                      Versión
                    </th>
                    <th scope="col" className="px-3 py-2 font-medium">
                      Estado
                    </th>
                    <th scope="col" className="px-3 py-2 font-medium">
                      Fecha
                    </th>
                    <th scope="col" className="px-3 py-2 font-medium">
                      Motivo
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {versionesOrdenadas.map((version) => (
                    <tr key={version.version} className="border-b border-border-subtle align-top">
                      <td className="px-3 py-2 font-mono text-text-900">{version.version}</td>
                      <td className="px-3 py-2 text-text-900">{ETIQUETA_ESTADO_ACTO[version.estado]}</td>
                      <td className="px-3 py-2 text-text-700">{formatearFecha(version.creado_en)}</td>
                      <td className="px-3 py-2 text-text-700">{version.motivo ?? "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>

          {panel.tipo === "editar" && (
            <div className="mt-6">
              <ActoFormulario
                key={`editar-${acto.id}`}
                modo="editar"
                acto={acto}
                onGuardar={guardarActo}
                onCancelar={() => setPanel({ tipo: "ninguno" })}
                erroresServidor={erroresServidor}
              />
            </div>
          )}
          {panel.tipo === "emitir" && (
            <div className="mt-6">
              <EmitirActo
                key={`emitir-${acto.id}`}
                acto={acto}
                onConfirmar={emitirActo}
                onCancelar={() => setPanel({ tipo: "ninguno" })}
                erroresServidor={erroresServidor}
              />
            </div>
          )}
          {panel.tipo === "registrarEficacia" && (
            <div className="mt-6">
              <RegistrarEficacia
                key={`eficacia-${acto.id}`}
                acto={acto}
                onConfirmar={registrarEficacia}
                onCancelar={() => setPanel({ tipo: "ninguno" })}
                erroresServidor={erroresServidor}
              />
            </div>
          )}
          {panel.tipo === "corregir" && (
            <div className="mt-6">
              <CorregirActo
                key={`corregir-${acto.id}`}
                acto={acto}
                onConfirmar={corregirActo}
                onCancelar={() => setPanel({ tipo: "ninguno" })}
                erroresServidor={erroresServidor}
              />
            </div>
          )}
          {panel.tipo === "referenciar" && (
            <div className="mt-6">
              <ReferenciarActo
                key={`referenciar-${panel.modo}-${acto.id}`}
                acto={acto}
                modo={panel.modo}
                onConfirmar={referenciarActo}
                onCancelar={() => setPanel({ tipo: "ninguno" })}
                erroresServidor={erroresServidor}
              />
            </div>
          )}
        </>
      )}

      <ConfirmationDialog
        open={confirmar === "eliminar"}
        title={`Eliminar el borrador ${nombreDeActo(acto)}`}
        description="¿Eliminar este borrador?"
        confirmLabel="Eliminar"
        danger
        onConfirm={eliminarActo}
        onCancel={() => setConfirmar(null)}
      />
    </PageContent>
  );
}
