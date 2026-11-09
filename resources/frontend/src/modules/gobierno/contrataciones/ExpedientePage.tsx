import { useState, type ReactNode } from "react";
import { Link, useParams } from "react-router";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/api/client";
import { useAutoridad } from "@/app/autoridad/AutoridadContext";
import { useCompany } from "@/app/contexts/CompanyContext";
import { useNotifications } from "@/app/contexts/NotificationContext";
import { Button } from "@/components/Button";
import { EmptyState } from "@/components/EmptyState";
import { LoadingState } from "@/components/LoadingState";
import { PageHeader } from "@/components/PageHeader";
import { PageContent } from "@/layout/PageContent";
import { ErrorDeCarga } from "@/modules/gobierno/ocupacion/ErrorDeCarga";
import { formatearFechaDeNegocio } from "@/lib/fecha-de-negocio";
import { AdjuntosPanel } from "@/modules/documentos/AdjuntosPanel";
import { CONSULTA_EXPEDIENTES } from "../api";
import type {
  ExpedienteDetalle,
  ExpedienteCatalogo,
  ExpedienteOpciones,
  ExpedienteCronologia,
  ExpedienteEvento,
  ExpedienteHito,

  ExpedienteResponsable,
} from "../api";
import {
  PanelResponsable,
  PanelTerminarResponsable,
  PanelComision,
  PanelActuacion,
  PanelFolio,
  PanelHito,
  PanelActualizarHito,
  PanelCerrar,
  PanelDescartar,
  type PanelExpediente,
} from "./ExpedientePaneles";

type PanelAbierto =
  | "responsable"
  | "terminar"
  | "comision"
  | "actuacion"
  | "decision"
  | "rectificar"
  | "folio"
  | "hito"
  | "actualizar-hito"
  | "cerrar"
  | "descartar"
  | null;

interface ApiErr {
  status?: number;
  code?: string;
  message?: string;
  fieldErrors?: Record<string, string[]>;
}

function ListaEventos({
  expedienteId,
  version,
  clases,
  accion,
}: {
  expedienteId: string;
  version: number;
  clases?: string;
  accion?: (e: ExpedienteEvento) => ReactNode;
}) {
  const [pagina, setPagina] = useState(1);
  const query = useQuery({
    queryKey: ["gobierno", "expedientes", expedienteId, "cronologia", clases ?? "todas", pagina, version],
    queryFn: () =>
      apiFetch<ExpedienteCronologia>(
        `/gobierno/contrataciones/expedientes/${expedienteId}/cronologia?pagina=${pagina}${clases ? `&clases=${clases}` : ""}`,
      ),
  });

  if (query.isLoading) {
    return <LoadingState />;
  }
  if (query.isError) {
    return <ErrorDeCarga message="No se pudo cargar la cronología" onRetry={() => query.refetch()} />;
  }
  const datos = query.data;
  if (!datos || datos.items.length === 0) {
    return <p className="text-sm text-text-700">Sin registros</p>;
  }

  return (
    <div className="space-y-3">
      <ol className="space-y-3">
        {datos.items.map((e) => (
          <li key={e.id} className="rounded-md border border-border-subtle p-3">
            <div className="text-xs text-text-600">
              {formatearFechaDeNegocio(e.fecha)} · {e.clase_etiqueta}
            </div>
            <div className="text-sm font-semibold text-text-900">{e.titulo}</div>
            {e.resultado && <div className="text-sm text-text-700">Resultado: {e.resultado}</div>}
            {e.detalle && <div className="text-sm text-text-700">{e.detalle}</div>}
            {e.responsable && (
              <div className="text-sm text-text-700">Responsable: {e.responsable}</div>
            )}
            {e.acto_etiqueta && <div className="text-sm text-text-700">Acto: {e.acto_etiqueta}</div>}
            {e.folio_etiqueta && <div className="text-sm text-text-700">Documento: {e.folio_etiqueta}</div>}
            {e.hito_etiqueta && <div className="text-sm text-text-700">Hito: {e.hito_etiqueta}</div>}
            {e.motivo && <div className="text-sm text-text-700">Motivo: {e.motivo}</div>}
            {e.rectifica_secuencia && (
              <div className="text-sm text-text-700">Rectifica el registro {e.rectifica_secuencia}</div>
            )}
            {e.rectificada_por_secuencia && (
              <div className="text-sm text-text-700">Rectificado por el registro {e.rectificada_por_secuencia}</div>
            )}
            <div className="mt-2 text-xs text-text-600">
              Registro {e.secuencia} · por {e.actor} · expediente {e.estado_etiqueta}
            </div>
            {accion && <div className="mt-2">{accion(e)}</div>}
          </li>
        ))}
      </ol>
      {datos.total > 50 && (
        <div className="flex justify-end gap-2">
          <Button variant="secondary" onClick={() => setPagina((p) => Math.max(1, p - 1))} disabled={pagina === 1}>
            Anterior
          </Button>
          <Button
            variant="secondary"
            onClick={() => setPagina((p) => p + 1)}
            disabled={pagina * 50 >= datos.total}
          >
            Siguiente
          </Button>
        </div>
      )}
    </div>
  );
}

export function ExpedientePage() {
  const { expedienteId } = useParams<{ expedienteId: string }>();
  const id = expedienteId ?? "";
  const { activeCompanyId } = useCompany();
  const { tiene } = useAutoridad();
  const { notify } = useNotifications();
  const queryClient = useQueryClient();

  const puedeVer = tiene("gobierno_expedientes:view", "empresa");
  const puedeGestionar = tiene("gobierno_expedientes:manage", "empresa");
  const puedeCerrar = tiene("gobierno_expedientes:close", "empresa");
  const puedeVerDoc = tiene("documentos:view", "empresa");
  const puedeVerActo = tiene("gobierno_actos:view", "empresa");
  const puedeVerComision = tiene("gobierno_comisiones:view", "empresa");
  const puedeVerBitacora = tiene("gobierno_auditoria:view", "empresa");

  const detalleQuery = useQuery({
    queryKey: [...CONSULTA_EXPEDIENTES, activeCompanyId, "detalle", id],
    queryFn: () => apiFetch<ExpedienteDetalle>(`/gobierno/contrataciones/expedientes/${id}`),
    enabled: Boolean(id && activeCompanyId && puedeVer),
  });
  const catalogoQuery = useQuery({
    queryKey: [...CONSULTA_EXPEDIENTES, activeCompanyId, "catalogo"],
    queryFn: () => apiFetch<ExpedienteCatalogo>("/gobierno/contrataciones/expedientes/catalogo"),
    enabled: Boolean(activeCompanyId && puedeVer),
  });
  const opcionesQuery = useQuery({
    queryKey: [...CONSULTA_EXPEDIENTES, activeCompanyId, "opciones", id],
    queryFn: () => apiFetch<ExpedienteOpciones>("/gobierno/contrataciones/expedientes/opciones"),
    enabled: Boolean(id && activeCompanyId && puedeGestionar),
  });

  const [panel, setPanel] = useState<PanelAbierto>(null);
  const [responsableEdicion, setResponsableEdicion] = useState<ExpedienteResponsable | null>(null);
  const [hitoEdicion, setHitoEdicion] = useState<ExpedienteHito | null>(null);
  const [rectificado, setRectificado] = useState<ExpedienteEvento | null>(null);
  const [enviando, setEnviando] = useState(false);
  const [errores, setErrores] = useState<Record<string, string[]>>({});
  const [alerta, setAlerta] = useState<string | null>(null);

  if (!activeCompanyId) {
    return (
      <PageContent>
        <EmptyState title="Sin empresa" description="Seleccione una empresa para continuar." />
      </PageContent>
    );
  }
  if (!puedeVer) {
    return (
      <PageContent>
        <EmptyState title="Sin acceso" description="No tiene permiso para consultar expedientes." />
      </PageContent>
    );
  }
  if (detalleQuery.isLoading) {
    return (
      <PageContent>
        <LoadingState />
      </PageContent>
    );
  }
  if (detalleQuery.isError) {
    const err = detalleQuery.error as ApiErr;
    if (err?.status === 404) {
      return (
        <PageContent>
          <EmptyState title="Expediente no encontrado" description="El expediente no existe o no está disponible." />
        </PageContent>
      );
    }
    return (
      <PageContent>
        <ErrorDeCarga message="No se pudo cargar el expediente" onRetry={() => detalleQuery.refetch()} />
      </PageContent>
    );
  }
  const detalle = detalleQuery.data;
  if (!detalle) {
    return (
      <PageContent>
        <LoadingState />
      </PageContent>
    );
  }

  const catalogo = catalogoQuery.data;
  const opciones = opcionesQuery.data;
  const abierto = detalle.status === "ABIERTO";
  const soloConsulta = !abierto;
  const sinContenido =
    detalle.folios.length === 0 &&
    detalle.hitos.length === 0 &&
    detalle.totales.actuaciones === 0 &&
    detalle.totales.decisiones === 0;

  const comun: PanelExpediente = {
    detalle,
    catalogo,
    opciones,
    enviando,
    errores,
    alerta,
    cerrarPanel: () => {
      setPanel(null);
      setErrores({});
      setAlerta(null);
      setResponsableEdicion(null);
      setHitoEdicion(null);
      setRectificado(null);
    },
    escribir: async (ruta, cuerpo) => {
      setEnviando(true);
      setErrores({});
      setAlerta(null);
      try {
        await apiFetch(`/gobierno/contrataciones/expedientes/${id}${ruta}`, {
          method: "POST",
          body: cuerpo,
          ifMatch: String(detalle.version),
        });
        await queryClient.invalidateQueries({ queryKey: [...CONSULTA_EXPEDIENTES, activeCompanyId] });
        notify({ type: "success", title: "Expediente actualizado" });
        setPanel(null);
        setResponsableEdicion(null);
        setHitoEdicion(null);
        setRectificado(null);
      } catch (e) {
        const err = e as ApiErr;
        if (err?.code === "GOV_PROCUREMENT_FILE_STALE") {
          setAlerta("El expediente cambió; recárguelo");
          await queryClient.invalidateQueries({ queryKey: [...CONSULTA_EXPEDIENTES, activeCompanyId] });
        } else {
          setErrores(err?.fieldErrors ?? {});
          setAlerta(err?.message ?? "No se pudo completar la acción");
        }
      } finally {
        setEnviando(false);
      }
    },
  };

  function abrir(nuevo: PanelAbierto) {
    setErrores({});
    setAlerta(null);
    setPanel(nuevo);
  }

  const hayPanel = panel !== null;

  function renderPanel() {
    if (panel === "responsable") {
      return <PanelResponsable comun={comun} />;
    }
    if (panel === "terminar" && responsableEdicion) {
      return <PanelTerminarResponsable comun={comun} responsable={responsableEdicion} />;
    }
    if (panel === "comision") {
      return <PanelComision comun={comun} />;
    }
    if (panel === "actuacion") {
      return <PanelActuacion comun={comun} clase="ACTUACION" rectifica={null} />;
    }
    if (panel === "decision") {
      return <PanelActuacion comun={comun} clase="DECISION" rectifica={null} />;
    }
    if (panel === "rectificar" && rectificado) {
      return <PanelActuacion comun={comun} clase="ACTUACION" rectifica={rectificado} />;
    }
    if (panel === "folio") {
      return <PanelFolio comun={comun} />;
    }
    if (panel === "hito") {
      return <PanelHito comun={comun} />;
    }
    if (panel === "actualizar-hito" && hitoEdicion) {
      return <PanelActualizarHito comun={comun} hito={hitoEdicion} />;
    }
    if (panel === "cerrar") {
      return <PanelCerrar comun={comun} />;
    }
    if (panel === "descartar") {
      return <PanelDescartar comun={comun} />;
    }
    return null;
  }

  return (
    <PageContent>
      <PageHeader
        crumbs={[
          { label: "Gobierno", to: "/gobierno" },
          { label: "Contrataciones", to: "/gobierno/contrataciones" },
          { label: "Expedientes", to: "/gobierno/contrataciones/expedientes" },
          { label: detalle.numero },
        ]}
        title={`Expediente ${detalle.numero}`}
        description={detalle.objeto}
        status={
          <span className="rounded-full bg-surface-100 px-2 py-0.5 text-xs font-medium text-text-700">
            {detalle.status_etiqueta}
          </span>
        }
        actions={
          abierto ? (
            <div className="flex gap-2">
              {puedeGestionar && (
                <Link to={`/gobierno/contrataciones/expedientes/${detalle.id}/editar`}>
                  <Button variant="secondary">Editar</Button>
                </Link>
              )}
              {puedeCerrar && (
                <Button variant="secondary" onClick={() => abrir("cerrar")}>
                  Cerrar expediente
                </Button>
              )}
              {puedeGestionar && sinContenido && (
                <Button variant="danger" onClick={() => abrir("descartar")}>
                  Descartar
                </Button>
              )}
            </div>
          ) : undefined
        }
      />

      {soloConsulta && (
        <div className="mt-4 rounded-md bg-surface-100 px-3 py-2 text-sm text-text-700">
          {detalle.status_etiqueta} el {detalle.cierre_fecha ? formatearFechaDeNegocio(detalle.cierre_fecha) : "—"}:{" "}
          {detalle.cierre_motivo ?? "—"}. Solo consulta.
        </div>
      )}

      <section aria-labelledby="sec-situacion" className="mt-6">
        <h2 id="sec-situacion" className="text-lg font-semibold text-text-900">
          Situación
        </h2>
        <div className="mt-3 rounded-md border border-border-subtle p-4">
          <dl className="grid gap-4 sm:grid-cols-2">
            <div>
              <dt className="text-xs font-medium text-text-600">Siguiente acción</dt>
              <dd className="text-sm text-text-900">{detalle.siguiente_accion || "Sin acciones sugeridas"}</dd>
              <dd className="text-xs text-text-600">Orientación: no decide ni bloquea</dd>
            </div>
            <div>
              <dt className="text-xs font-medium text-text-600">Próximo hito</dt>
              {detalle.proximo_hito ? (
                <>
                  <dd className="text-sm text-text-900">{detalle.proximo_hito.nombre}</dd>
                  <dd className="text-xs text-text-600">
                    {detalle.proximo_hito.fecha_prevista ? formatearFechaDeNegocio(detalle.proximo_hito.fecha_prevista) : "sin fecha"}
                    {detalle.proximo_hito.fecha_superada ? " · Fecha prevista superada" : ""}
                  </dd>
                </>
              ) : (
                <dd className="text-sm text-text-900">Sin próximo hito</dd>
              )}
            </div>
            <div>
              <dt className="text-xs font-medium text-text-600">Última actuación</dt>
              <dd className="text-sm text-text-900">{detalle.ultima_actuacion ? `${detalle.ultima_actuacion.clase_etiqueta}: ${detalle.ultima_actuacion.titulo} (${formatearFechaDeNegocio(detalle.ultima_actuacion.fecha)})` : "—"}</dd>
            </div>
            <div>
              <dt className="text-xs font-medium text-text-600">Responsable</dt>
              <dd className="text-sm text-text-900">{detalle.responsable ?? "Sin responsable"}</dd>
            </div>
            <div>
              <dt className="text-xs font-medium text-text-600">Comisión</dt>
              <dd className="text-sm text-text-900">
                {detalle.comision_detalle
                  ? `${detalle.comision_detalle.codigo} · ${detalle.comision_detalle.nombre}`
                  : detalle.comision_no_aplica_motivo
                    ? "No interviene comisión"
                    : "Sin comisión vinculada"}
              </dd>
            </div>
          </dl>
          <div className="mt-4">
            <h3 className="text-sm font-semibold text-text-900">Pendiente</h3>
            {detalle.pendientes.length === 0 ? (
              <p className="text-sm text-text-700">Sin pendientes</p>
            ) : (
              <ul className="list-disc pl-5 text-sm text-text-700">
                {detalle.pendientes.map((p, i) => (
                  <li key={i}>{p.texto}</li>
                ))}
              </ul>
            )}
          </div>
        </div>
      </section>

      {hayPanel && (
        <div className="mt-4 rounded-md border border-border-subtle p-4">{renderPanel()}</div>
      )}

      <section aria-labelledby="sec-identificacion" className="mt-6">
        <h2 id="sec-identificacion" className="text-lg font-semibold text-text-900">
          Identificación
        </h2>
        <dl className="mt-3 grid gap-3 sm:grid-cols-2">
          <div>
            <dt className="text-xs font-medium text-text-600">Número</dt>
            <dd className="text-sm text-text-900">{detalle.numero}</dd>
          </div>
          <div>
            <dt className="text-xs font-medium text-text-600">Fecha de iniciación</dt>
            <dd className="text-sm text-text-900">{formatearFechaDeNegocio(detalle.fecha_inicio)}</dd>
          </div>
          <div className="sm:col-span-2">
            <dt className="text-xs font-medium text-text-600">Objeto</dt>
            <dd className="text-sm text-text-900">{detalle.objeto}</dd>
          </div>
          <div>
            <dt className="text-xs font-medium text-text-600">Partes</dt>
            <dd className="text-sm text-text-900">{detalle.partes ?? "—"}</dd>
          </div>
          <div>
            <dt className="text-xs font-medium text-text-600">Tipo</dt>
            <dd className="text-sm text-text-900">{detalle.tipo_etiqueta}</dd>
          </div>
          <div>
            <dt className="text-xs font-medium text-text-600">Unidad responsable</dt>
            <dd className="text-sm text-text-900">{detalle.unidad_nombre ?? "—"}</dd>
          </div>
          <div>
            <dt className="text-xs font-medium text-text-600">Registrado por</dt>
            <dd className="text-sm text-text-900">{detalle.creado_por}</dd>
          </div>
          <div className="sm:col-span-2">
            <dt className="text-xs font-medium text-text-600">Modalidad declarada</dt>
            <dd className="text-sm text-text-900">
              {detalle.modalidad_declarada ? (
                <>
                  {detalle.modalidad_etiqueta} <span className="text-xs text-text-600">(Declarada)</span>
                  {detalle.modalidad_fundamento && (
                    <span className="block text-xs text-text-600">Fundamento: {detalle.modalidad_fundamento}</span>
                  )}
                  {detalle.modalidad_fuente && (
                    <span className="block text-xs text-text-600">Fuente: {detalle.modalidad_fuente}</span>
                  )}
                </>
              ) : (
                "Sin declarar"
              )}
            </dd>
            {catalogo?.aviso_modalidad && (
              <dd className="mt-1 text-xs text-text-600">{catalogo.aviso_modalidad}</dd>
            )}
          </div>
        </dl>
      </section>

      <section aria-labelledby="sec-responsables" className="mt-6">
        <h2 id="sec-responsables" className="text-lg font-semibold text-text-900">
          Responsables
        </h2>
        <div className="relative mt-3 overflow-x-auto" tabIndex={0} role="region" aria-label="Responsables del expediente">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-xs font-medium text-text-600">
                <th className="px-2 py-1">Nombre</th>
                <th className="px-2 py-1">Cargo</th>
                <th className="px-2 py-1">Unidad</th>
                <th className="px-2 py-1">Rol</th>
                <th className="px-2 py-1">Desde</th>
                <th className="px-2 py-1">Hasta</th>
                <th className="px-2 py-1">Motivo</th>
                <th className="px-2 py-1">
                  <span className="sr-only">Acciones</span>
                </th>
              </tr>
            </thead>
            <tbody>
              {detalle.responsables.map((r) => (
                <tr key={r.id} className="border-t border-border-subtle">
                  <td className="px-2 py-1">{r.nombre}</td>
                  <td className="px-2 py-1">{r.cargo ?? "—"}</td>
                  <td className="px-2 py-1">{r.unidad ?? "—"}</td>
                  <td className="px-2 py-1">{r.rol_etiqueta}</td>
                  <td className="px-2 py-1">{formatearFechaDeNegocio(r.desde)}</td>
                  <td className="px-2 py-1">{r.fin_efectivo ? formatearFechaDeNegocio(r.fin_efectivo) : "Vigente"}</td>
                  <td className="px-2 py-1">{r.motivo_fin ?? "—"}</td>
                  <td className="px-2 py-1">
                    {!r.fin_efectivo && abierto && puedeGestionar && (
                      <Button
                        variant="secondary"
                        onClick={() => {
                          setResponsableEdicion(r);
                          abrir("terminar");
                        }}
                      >
                        Terminar
                      </Button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {abierto && puedeGestionar && (
          <div className="mt-3">
            <Button variant="secondary" onClick={() => abrir("responsable")}>
              Asignar responsable
            </Button>
          </div>
        )}
      </section>

      <section aria-labelledby="sec-comision" className="mt-6">
        <h2 id="sec-comision" className="text-lg font-semibold text-text-900">
          Comisión
        </h2>
        <div className="mt-3 space-y-2">
          {detalle.comision_detalle ? (
            <p className="text-sm text-text-900">
              {detalle.comision_detalle.codigo} · {detalle.comision_detalle.nombre} ·{" "}
              {detalle.comision_detalle.situacion_etiqueta}
              {puedeVerComision && (
                <>
                  {" "}
                  <Link
                    to={`/gobierno/contrataciones/comisiones/${detalle.comision_detalle.id}`}
                    className="text-brand-600 underline"
                  >
                    Abrir comisión
                  </Link>
                </>
              )}
            </p>
          ) : detalle.comision_no_aplica_motivo ? (
            <p className="text-sm text-text-900">No interviene comisión — {detalle.comision_no_aplica_motivo}</p>
          ) : (
            <p className="text-sm text-text-700">Sin comisión vinculada</p>
          )}
          {abierto && puedeGestionar && (
            <Button variant="secondary" onClick={() => abrir("comision")}>
              {detalle.comision_detalle || detalle.comision_no_aplica_motivo ? "Cambiar comisión" : "Vincular comisión"}
            </Button>
          )}
        </div>
      </section>

      <section aria-labelledby="sec-actuaciones" className="mt-6">
        <h2 id="sec-actuaciones" className="text-lg font-semibold text-text-900">
          Actuaciones y decisiones
        </h2>
        {abierto && puedeGestionar && (
          <div className="mt-2 flex gap-2">
            <Button variant="secondary" onClick={() => abrir("actuacion")}>
              Registrar actuación
            </Button>
            <Button variant="secondary" onClick={() => abrir("decision")}>
              Registrar decisión
            </Button>
          </div>
        )}
        <div className="mt-3">
          <ListaEventos
            expedienteId={detalle.id}
            version={detalle.version}
            clases="ACTUACION,DECISION"
            accion={(e) =>
              abierto && puedeGestionar && !e.rectificada_por_secuencia ? (
                <Button
                  variant="secondary"
                  onClick={() => {
                    setRectificado(e);
                    abrir("rectificar");
                  }}
                >
                  Rectificar
                </Button>
              ) : null
            }
          />
        </div>
      </section>

      <section aria-labelledby="sec-documentos" className="mt-6">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h2 id="sec-documentos" className="text-lg font-semibold text-text-900">Documentos y actos</h2>
          {abierto && puedeGestionar && (
            <Button onClick={() => abrir("folio")}>Incorporar al expediente</Button>
          )}
        </div>
        {detalle.folios.length === 0 ? (
          <p className="mt-2 text-sm text-text-600">Sin folios</p>
        ) : (
          <div className="mt-2 overflow-x-auto" tabIndex={0} role="region" aria-label="Folios del expediente">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-text-600">
                  <th className="px-2 py-1">Folio</th>
                  <th className="px-2 py-1">Clase</th>
                  <th className="px-2 py-1">Tipo</th>
                  <th className="px-2 py-1">Título</th>
                  <th className="px-2 py-1">Versión</th>
                  <th className="px-2 py-1">Fecha del documento</th>
                  <th className="px-2 py-1">Incorporado</th>
                  <th className="px-2 py-1">Hito</th>
                  <th className="px-2 py-1">Reserva</th>
                </tr>
              </thead>
              <tbody>
                {detalle.folios.map((f) => (
                  <tr key={f.id} className="border-t border-border">
                    <td className="px-2 py-1">{f.numero}</td>
                    <td className="px-2 py-1">{f.clase_etiqueta}</td>
                    <td className="px-2 py-1">{f.tipo_etiqueta}</td>
                    <td className="px-2 py-1">
                      {f.documento_id && puedeVerDoc ? (
                        <Link to={`/documentos/${f.documento_id}`}>{f.etiqueta}</Link>
                      ) : f.acto_id && puedeVerActo ? (
                        <Link to={`/gobierno/actos/${f.acto_id}`}>{f.etiqueta}</Link>
                      ) : (
                        f.etiqueta
                      )}
                    </td>
                    <td className="px-2 py-1">{f.version_numero ?? "—"}</td>
                    <td className="px-2 py-1">{formatearFechaDeNegocio(f.fecha_documento) || "—"}</td>
                    <td className="px-2 py-1">
                      {formatearFechaDeNegocio(f.fecha_incorporacion) || "—"}
                      {f.incorporado_por ? ` por ${f.incorporado_por}` : ""}
                    </td>
                    <td className="px-2 py-1">{f.hito ?? "—"}</td>
                    <td className="px-2 py-1">{f.reservado ? `Reservado: ${f.motivo_reserva}` : "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        <details className="mt-4">
          <summary className="cursor-pointer text-sm font-medium text-text-800">
            Contenido del expediente (RLCP art. 32)
          </summary>
          <h3 className="mt-3 text-sm font-semibold text-text-900">Selección del contratista</h3>
          <ul className="mt-1 list-disc pl-5 text-sm text-text-700">
            {detalle.contenido
              .filter((c) => c.grupo === "SELECCION")
              .map((c) => (
                <li key={c.clase}>
                  {c.etiqueta}
                  {c.folios > 0 ? ` · Incorporado (${c.folios})` : " · Sin incorporar"}
                  {c.condicional ? " · según el caso" : ""}
                  {` (${c.fuente})`}
                </li>
              ))}
          </ul>
          <h3 className="mt-3 text-sm font-semibold text-text-900">Administración del contrato</h3>
          <ul className="mt-1 list-disc pl-5 text-sm text-text-700">
            {detalle.contenido
              .filter((c) => c.grupo === "ADMINISTRACION")
              .map((c) => (
                <li key={c.clase}>
                  {c.etiqueta}
                  {c.folios > 0 ? ` · Incorporado (${c.folios})` : " · Sin incorporar"}
                  {c.condicional ? " · según el caso" : ""}
                  {` (${c.fuente})`}
                </li>
              ))}
          </ul>
          <p className="mt-2 text-xs text-text-600">
            Aviso: varios documentos dependen de la modalidad y de la etapa.
          </p>
        </details>
        {abierto && puedeGestionar && (
          <div className="mt-4">
            <h3 className="text-sm font-semibold text-text-900">Cargar un documento nuevo</h3>
            <AdjuntosPanel
              resourceType="GovernmentProcurementFile"
              resourceId={detalle.id}
              title="Archivos del expediente"
            />
            <p className="mt-2 text-xs text-text-600">Después incorpórelo para asignarle folio.</p>
          </div>
        )}
      </section>

      <section aria-labelledby="sec-hitos" className="mt-6">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h2 id="sec-hitos" className="text-lg font-semibold text-text-900">Hitos y lapsos</h2>
          {abierto && puedeGestionar && (
            <Button onClick={() => abrir("hito")}>Registrar hito</Button>
          )}
        </div>
        <p className="mt-1 text-sm text-text-600">{catalogo?.aviso_lapsos}</p>
        {detalle.hitos.length === 0 ? (
          <p className="mt-2 text-sm text-text-600">Sin hitos</p>
        ) : (
          <div className="mt-2 overflow-x-auto" tabIndex={0} role="region" aria-label="Hitos del expediente">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-text-600">
                  <th className="px-2 py-1">Hito</th>
                  <th className="px-2 py-1">Fuente</th>
                  <th className="px-2 py-1">Prevista</th>
                  <th className="px-2 py-1">Real</th>
                  <th className="px-2 py-1">Responsable</th>
                  <th className="px-2 py-1">Estado</th>
                  <th className="px-2 py-1">Acciones</th>
                </tr>
              </thead>
              <tbody>
                {detalle.hitos.map((h) => (
                  <tr key={h.id} className="border-t border-border">
                    <td className="px-2 py-1">{h.nombre}</td>
                    <td className="px-2 py-1">{h.fuente ?? "—"}</td>
                    <td className="px-2 py-1">{formatearFechaDeNegocio(h.fecha_prevista) || "—"}</td>
                    <td className="px-2 py-1">{formatearFechaDeNegocio(h.fecha_real) || "—"}</td>
                    <td className="px-2 py-1">{h.responsable ?? "—"}</td>
                    <td className="px-2 py-1">
                      {h.estado_etiqueta}
                      {h.fecha_superada ? " · Fecha prevista superada" : ""}
                      {h.motivo_no_aplica ? ` · ${h.motivo_no_aplica}` : ""}
                    </td>
                    <td className="px-2 py-1">
                      {abierto && puedeGestionar && (
                        <Button
                          aria-label={`Actualizar ${h.nombre}`}
                          onClick={() => {
                            setHitoEdicion(h);
                            abrir("actualizar-hito");
                          }}
                        >
                          Actualizar
                        </Button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <section aria-labelledby="sec-cronologia" className="mt-6">
        <h2 id="sec-cronologia" className="text-lg font-semibold text-text-900">Cronología</h2>
        <ListaEventos expedienteId={detalle.id} version={detalle.version} />
      </section>

      <section aria-labelledby="sec-auditoria" className="mt-6">
        <h2 id="sec-auditoria" className="text-lg font-semibold text-text-900">Auditoría</h2>
        <p className="mt-1 text-sm text-text-600">
          Cada acción queda en la bitácora institucional con su actor, cargo, sesión e IP. La cronología cuenta el negocio; la bitácora es la auditoría.
        </p>
        <p className="mt-2 text-sm">
          {puedeVerBitacora ? (
            <Link to="/gobierno/bitacora">Abrir bitácora</Link>
          ) : (
            <span className="text-text-600">Requiere permiso de auditoría</span>
          )}
        </p>
      </section>
    </PageContent>
  );
}
