import { useCallback, useState } from "react";
import { Link, useParams } from "react-router";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useCompany } from "@/app/contexts/CompanyContext";
import { useNotifications } from "@/app/contexts/NotificationContext";
import { useAutoridad } from "@/app/autoridad/AutoridadContext";
import { apiFetch } from "@/api/client";
import { AsyncButton } from "@/components/AsyncButton";
import { Button } from "@/components/Button";
import { TextInput } from "@/components/TextInput";
import { FormField } from "@/components/FormField";
import { EmptyState } from "@/components/EmptyState";
import { LoadingState } from "@/components/LoadingState";
import { PageHeader } from "@/components/PageHeader";
import { PageContent } from "@/layout/PageContent";
import { ErrorDeCarga } from "@/modules/gobierno/ocupacion/ErrorDeCarga";
import { formatearFecha } from "@/i18n";
import { formatearFechaDeNegocio } from "@/lib/fecha-de-negocio";
import {
  ComisionDetalle,
  ComisionCatalogo,
  ComisionOpciones,
  ETIQUETAS_ESTADO_COMISION,
  ETIQUETAS_SITUACION_COMISION,
  ETIQUETAS_TIPO_COMISION,
  CONSULTA_COMISIONES,
  consultaDeFecha,
} from "@/modules/gobierno/api";
import { PanelCerrar, PanelDescartar, PanelInhibicion, PanelMiembro, PanelResolverInhibicion, PanelRetirarMiembro, PanelSnc, PanelTerminarMiembro } from "./ComisionPaneles";
import type { PanelComun } from "./ComisionPaneles";

type Panel =
  | "miembro"
  | "inhibicion"
  | "resolver-inhibicion"
  | "terminar-miembro"
  | "retirar-miembro"
  | "descartar"
  | "cerrar"
  | "snc"
  | null;

interface InhibicionEnResolucion extends Record<string, unknown> {
  id: string;
  miembro_id: string;
  miembro: string;
  asunto: string;
  version: number;
}

function etiqueta(lista: { codigo: string; etiqueta: string }[] | undefined, codigo: string | null | undefined): string {
  if (!codigo) return "—";
  if (!lista) return codigo;
  const item = lista.find((x) => x.codigo === codigo);
  return item ? item.etiqueta : codigo;
}

export function ComisionPage() {
  const { comisionId } = useParams<{ comisionId: string }>();
  const { activeCompanyId } = useCompany();
  const { tiene } = useAutoridad();
  const { notify } = useNotifications();
  const queryClient = useQueryClient();
  const [fecha, setFecha] = useState("");
  const [panel, setPanel] = useState<Panel>(null);
  const [enviando, setEnviando] = useState(false);
  const [erroresServidor, setErroresServidor] = useState<Record<string, string[]>>({});
  const [alertaCambio, setAlertaCambio] = useState<string | null>(null);
  const [inhibicionEnResolucion, setInhibicionEnResolucion] = useState<InhibicionEnResolucion | null>(null);
  const [miembroEnTerminacion, setMiembroEnTerminacion] = useState<{ id: string; nombre: string } | null>(null);
  const [miembroEnRetiro, setMiembroEnRetiro] = useState<{ id: string; nombre: string } | null>(null);

  const puedeVer = tiene("gobierno_comisiones:view", "empresa");
  const puedeGestionar = puedeVer && tiene("gobierno_comisiones:manage", "empresa");
  const puedeActivar = puedeVer && tiene("gobierno_comisiones:activate", "empresa");
  const puedeCerrar = puedeVer && tiene("gobierno_comisiones:close", "empresa");
  const puedeVerActo = tiene("gobierno_actos:view", "empresa");

  const claveDetalle = [...CONSULTA_COMISIONES, activeCompanyId, "ficha", comisionId, fecha];
  const { data: detalle, isLoading, isError, error } = useQuery<ComisionDetalle>({
    queryKey: claveDetalle,
    queryFn: () =>
      apiFetch<ComisionDetalle>(
        `/gobierno/contrataciones/comisiones/${comisionId}${consultaDeFecha(fecha)}`,
      ),
    enabled: Boolean(activeCompanyId && comisionId && puedeVer),
    retry: false,
  });

  const { data: catalogo } = useQuery<ComisionCatalogo>({
    queryKey: [...CONSULTA_COMISIONES, activeCompanyId, "catalogo-comisiones"],
    queryFn: () => apiFetch<ComisionCatalogo>("/gobierno/contrataciones/comisiones/catalogo"),
    enabled: Boolean(activeCompanyId && puedeVer),
    retry: false,
  });

  const { data: opciones } = useQuery<ComisionOpciones>({
    queryKey: [...CONSULTA_COMISIONES, activeCompanyId, "opciones-comisiones"],
    queryFn: () => apiFetch<ComisionOpciones>("/gobierno/contrataciones/comisiones/opciones"),
    enabled: Boolean(activeCompanyId && puedeGestionar),
    retry: false,
  });

  const recargar = useCallback(() => {
    setErroresServidor({});
    setAlertaCambio(null);
    setPanel(null);
    queryClient.invalidateQueries({ queryKey: [...CONSULTA_COMISIONES, activeCompanyId] });
  }, [activeCompanyId, queryClient]);

  const manejarError = useCallback(
    (e: unknown) => {
      const apiError = e as {
        status?: number;
        code?: string;
        message?: string;
        fieldErrors?: Record<string, string[]>;
      };
      if (apiError?.status === 409 && apiError?.code === "GOV_COMMITTEE_STALE") {
        setAlertaCambio("La comisión cambió; recárguela");
        queryClient.invalidateQueries({ queryKey: [...CONSULTA_COMISIONES, activeCompanyId] });
      } else if (apiError?.status === 409 && apiError?.code === "GOV_COMMITTEE_INCOMPLETE") {
        setAlertaCambio(apiError.message ?? "La comisión está incompleta");
        queryClient.invalidateQueries({ queryKey: [...CONSULTA_COMISIONES, activeCompanyId] });
      } else if (apiError?.status && apiError.status >= 400 && apiError.status < 500) {
        if (apiError.fieldErrors) {
          setErroresServidor(apiError.fieldErrors);
        }
        if (apiError.message) {
          setAlertaCambio(apiError.message);
        }
      } else if (apiError?.status && apiError.status >= 500) {
        setAlertaCambio(apiError.message ?? "Error del servidor");
      } else {
        setAlertaCambio(apiError?.message ?? "No fue posible completar la acción");
      }
    },
    [activeCompanyId, queryClient],
  );

  const escribir = useCallback(
    async (ruta: string, metodo: "POST" | "DELETE", cuerpo: Record<string, unknown>, version: number) => {
      setEnviando(true);
      try {
        await apiFetch<ComisionDetalle>(ruta, {
          method: metodo,
          body: metodo === "DELETE" ? undefined : cuerpo,
          ifMatch: String(version),
        });
        recargar();
        notify({ type: "success", title: "Comisión actualizada" });
      } catch (e) {
        manejarError(e);
      } finally {
        setEnviando(false);
      }
    },
    [manejarError, notify, recargar],
  );

  const cerrarPanel = useCallback(() => {
    setPanel(null);
    setInhibicionEnResolucion(null);
    setMiembroEnTerminacion(null);
    setMiembroEnRetiro(null);
    setErroresServidor({});
    setAlertaCambio(null);
  }, []);

  if (!puedeVer) {
    return (
      <PageContent>
        <EmptyState
          title="Sin acceso"
          description="No tiene permiso para ver comisiones."
          action={<Link to="/gobierno/contrataciones/comisiones">Volver a Comisiones</Link>}
        />
      </PageContent>
    );
  }

  if (!activeCompanyId) {
    return (
      <PageContent>
        <EmptyState
          title="Sin empresa"
          description="Seleccione una empresa para ver la comisión."
          action={<Link to="/gobierno/contrataciones/comisiones">Volver a Comisiones</Link>}
        />
      </PageContent>
    );
  }

  if (isLoading) {
    return (
      <PageContent>
        <LoadingState />
      </PageContent>
    );
  }

  if (isError || !detalle) {
    const status = (error as { status?: number })?.status;
    if (status === 404) {
      return (
        <PageContent>
          <EmptyState
            title="Comisión no encontrada"
            description="No existe la comisión solicitada."
            action={<Link to="/gobierno/contrataciones/comisiones">Volver a Comisiones</Link>}
          />
        </PageContent>
      );
    }
    return <ErrorDeCarga message="No fue posible cargar la comisión." />;
  }

  const estado = detalle.status;
  const miembrosAnteriores = detalle.miembros.filter((m) => m.fin_efectivo);

  const abrirPanel = (p: Exclude<Panel, null>) => {
    setPanel(p);
    setErroresServidor({});
    setAlertaCambio(null);
  };

const renderPanel = () => {
  const comun: PanelComun = { detalle, comisionId: comisionId ?? "", catalogo, opciones, enviando, erroresServidor, alertaCambio, escribir, cerrarPanel };
  if (panel === "miembro" && puedeGestionar) return <PanelMiembro comun={comun} />;
  if (panel === "inhibicion" && puedeGestionar) return <PanelInhibicion comun={comun} />;
  if (panel === "resolver-inhibicion" && inhibicionEnResolucion && puedeActivar) return <PanelResolverInhibicion comun={comun} inhibicion={inhibicionEnResolucion} />;
  if (panel === "terminar-miembro" && miembroEnTerminacion && puedeCerrar) return <PanelTerminarMiembro comun={comun} miembro={miembroEnTerminacion} />;
  if (panel === "retirar-miembro" && miembroEnRetiro && puedeGestionar) return <PanelRetirarMiembro comun={comun} miembro={miembroEnRetiro} />;
  if (panel === "descartar" && puedeGestionar) return <PanelDescartar comun={comun} />;
  if (panel === "cerrar" && puedeCerrar) return <PanelCerrar comun={comun} />;
  if (panel === "snc" && puedeGestionar) return <PanelSnc comun={comun} />;
  return null;
};

  const etiquetaEstado = ETIQUETAS_ESTADO_COMISION[detalle.status] ?? detalle.status;
  const etiquetaSituacion = ETIQUETAS_SITUACION_COMISION[detalle.situacion] ?? detalle.situacion;
  const acciones = [];
  if (estado === "BORRADOR") {
    if (puedeGestionar) {
      acciones.push(
        <Link key="editar" to={`/gobierno/contrataciones/comisiones/${comisionId}/editar`}>
          <Button type="button" variant="secondary">
            Editar
          </Button>
        </Link>,
      );
      acciones.push(
        <Button key="miembro" type="button" variant="secondary" onClick={() => abrirPanel("miembro")}>
          Añadir miembro
        </Button>,
      );
    }
    if (puedeActivar) {
      acciones.push(
        <AsyncButton
          key="activar"
          variant="primary"
          onClick={async () => {
            await escribir(`/gobierno/contrataciones/comisiones/${comisionId}/activar`, "POST", {}, detalle.version);
          }}
        >
          Activar
        </AsyncButton>,
      );
    }
    if (puedeGestionar) {
      acciones.push(
        <Button key="descartar" type="button" variant="danger" onClick={() => abrirPanel("descartar")}>
          Descartar
        </Button>,
      );
    }
  } else if (estado === "VIGENTE") {
    if (puedeGestionar) {
      acciones.push(
        <Button key="designar" type="button" variant="secondary" onClick={() => abrirPanel("miembro")}>
          Designar miembro
        </Button>,
      );
      acciones.push(
        <Button key="inhibicion" type="button" variant="secondary" onClick={() => abrirPanel("inhibicion")}>
          Declarar inhibición
        </Button>,
      );
      acciones.push(
        <Button key="snc" type="button" variant="secondary" onClick={() => abrirPanel("snc")}>
          Registrar notificación al SNC
        </Button>,
      );
    }
    if (puedeCerrar) {
      acciones.push(
        <Button key="cerrar" type="button" variant="danger" onClick={() => abrirPanel("cerrar")}>
          Cerrar comisión
        </Button>,
      );
    }
  }

  const faltantes = detalle.faltantes ?? [];

  return (
    <PageContent>
      <PageHeader
        crumbs={[
          { label: "Gobierno", to: "/gobierno" },
          { label: "Contrataciones", to: "/gobierno/contrataciones" },
          { label: "Comisiones", to: "/gobierno/contrataciones/comisiones" },
          { label: detalle.codigo },
        ]}
        title={detalle.nombre}
        description={etiquetaEstado === etiquetaSituacion ? `${detalle.codigo} · ${etiquetaEstado}` : `${detalle.codigo} · ${etiquetaEstado} · ${etiquetaSituacion}`}
        actions={acciones}
      />

      {estado === "BORRADOR" && faltantes.length > 0 ? (
        <section aria-labelledby="faltantes-titulo" className="mb-8">
          <h2 id="faltantes-titulo" className="mb-4 text-lg font-semibold text-text-900">
            Para activar falta
          </h2>
          <ul className="list-disc pl-5 text-sm text-text-700">
            {faltantes.map((f) => (
              <li key={f}>{f}</li>
            ))}
          </ul>
        </section>
      ) : null}

      {estado === "VIGENTE" && faltantes.length > 0 ? (
        <section aria-labelledby="incompleta-titulo" className="mb-8">
          <h2 id="incompleta-titulo" className="mb-4 text-lg font-semibold text-text-900">
            Composición incompleta
          </h2>
          <ul className="list-disc pl-5 text-sm text-text-700">
            {faltantes.map((f) => (
              <li key={f}>{f}</li>
            ))}
          </ul>
        </section>
      ) : null}

      {detalle.snc_pendiente ? (
        <p role="status" className="mb-8 text-sm font-medium text-amber-700">
          Falta registrar la notificación de la designación al SNC (LCP art. 14).
        </p>
      ) : null}

      {renderPanel()}

      <section aria-labelledby="datos-titulo" className="mb-8">
        <h2 id="datos-titulo" className="mb-4 text-lg font-semibold text-text-900">
          Datos de la comisión
        </h2>
        <dl className="grid grid-cols-1 gap-4 md:grid-cols-2">
          <div>
            <dt className="text-sm font-medium text-text-600">Código</dt>
            <dd className="text-sm text-text-900">{detalle.codigo}</dd>
          </div>
          <div>
            <dt className="text-sm font-medium text-text-600">Tipo</dt>
            <dd className="text-sm text-text-900">{ETIQUETAS_TIPO_COMISION[detalle.tipo] ?? detalle.tipo}</dd>
          </div>
          <div>
            <dt className="text-sm font-medium text-text-600">Objeto</dt>
            <dd className="text-sm text-text-900">{detalle.objeto ?? "—"}</dd>
          </div>
          <div>
            <dt className="text-sm font-medium text-text-600">Vigencia</dt>
            <dd className="text-sm text-text-900">
              {formatearFechaDeNegocio(detalle.desde)} — {detalle.hasta ? formatearFechaDeNegocio(detalle.hasta) : "Sin fecha final"}
            </dd>
          </div>
          <div>
            <dt className="text-sm font-medium text-text-600">Estado</dt>
            <dd className="text-sm text-text-900">{ETIQUETAS_ESTADO_COMISION[detalle.status] ?? detalle.status}</dd>
          </div>
          <div>
            <dt className="text-sm font-medium text-text-600">Situación</dt>
            <dd className="text-sm text-text-900">{ETIQUETAS_SITUACION_COMISION[detalle.situacion] ?? detalle.situacion}</dd>
          </div>
          <div>
            <dt className="text-sm font-medium text-text-600">Acto</dt>
            <dd className="text-sm text-text-900">
              {detalle.acto ? (
                <>
                  {detalle.acto.etiqueta}
                  {puedeVerActo ? (
                    <>
                      {" · "}
                      <Link to={`/gobierno/actos/${detalle.acto.id}`} className="text-brand-700 underline">
                        Abrir el acto
                      </Link>
                    </>
                  ) : null}
                </>
              ) : (
                "Sin acto"
              )}
            </dd>
          </div>
          <div>
            <dt className="text-sm font-medium text-text-600">Emisor del acto</dt>
            <dd className="text-sm text-text-900">{detalle.acto?.emisor ?? "—"}</dd>
          </div>
          <div>
            <dt className="text-sm font-medium text-text-600">Medio de publicación</dt>
            <dd className="text-sm text-text-900">{detalle.acto?.medio ?? "—"}</dd>
          </div>
          <div>
            <dt className="text-sm font-medium text-text-600">Regla aplicada</dt>
            <dd className="text-sm text-text-900">{detalle.regla_version ?? "Se fija al activar"}</dd>
          </div>
          <div>
            <dt className="text-sm font-medium text-text-600">Notificación al SNC</dt>
            <dd className="text-sm text-text-900">
              {detalle.snc_notificada_en
                ? `${formatearFechaDeNegocio(detalle.snc_notificada_en)}${detalle.snc_referencia ? ` · ${detalle.snc_referencia}` : ""}`
                : "Sin registrar"}
            </dd>
          </div>
          {detalle.fin_efectivo ? (
            <>
              <div>
                <dt className="text-sm font-medium text-text-600">Fin</dt>
                <dd className="text-sm text-text-900">{formatearFechaDeNegocio(detalle.fin_efectivo)}</dd>
              </div>
              <div>
                <dt className="text-sm font-medium text-text-600">Motivo de cierre</dt>
                <dd className="text-sm text-text-900">{detalle.motivo_cierre ?? "—"}</dd>
              </div>
            </>
          ) : null}
        </dl>
      </section>

      <section aria-labelledby="composicion-titulo" className="mb-8">
        <h2 id="composicion-titulo" className="mb-4 text-lg font-semibold text-text-900">
          Composición
        </h2>
        <FormField label="Consultar a la fecha" htmlFor="comision-fecha-consulta">
          <TextInput
            id="comision-fecha-consulta"
            type="date"
            value={fecha}
            onChange={(e) => setFecha(e.target.value)}
            className="w-full max-w-xs"
          />
        </FormField>
        {detalle.es_historica ? (
          <p role="status" className="mt-2 text-sm text-amber-700">
            Composición al {formatearFechaDeNegocio(detalle.fecha)}. No concede nada hoy.
          </p>
        ) : null}
        {detalle.composicion.length === 0 ? (
          <EmptyState title="Sin miembros" description="No hay miembros en la composición." />
        ) : (
          <div className="mt-4 overflow-x-auto rounded-lg border border-border-subtle" role="region" tabIndex={0} aria-label="Composición actual">
            <table className="min-w-full divide-y divide-border-subtle">
              <caption className="sr-only">Composición de la comisión</caption>
              <thead className="bg-surface-50">
                <tr>
                  <th scope="col" className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-text-600">Funcionario</th>
                  <th scope="col" className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-text-600">Función</th>
                  <th scope="col" className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-text-600">Área</th>
                  <th scope="col" className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-text-600">Condición</th>
                  <th scope="col" className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-text-600">Suple a</th>
                  <th scope="col" className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-text-600">Desde</th>
                  <th scope="col" className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-text-600">Certificación SNC</th>
                  <th scope="col" className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-text-600">Acciones</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border-subtle bg-white">
                {detalle.composicion.map((m) => (
                  <tr key={m.id}>
                    <td className="px-4 py-3 text-sm text-text-900">
                      <div>{m.funcionario.nombre}</div>
                      <div className="text-xs text-text-600">
                        {m.funcionario.cargos.join(", ") || "Sin cargo vigente"} · {m.funcionario.unidades.join(", ") || "Sin unidad"}
                      </div>
                    </td>
                    <td className="px-4 py-3 text-sm text-text-900">{m.funcion === "MIEMBRO" ? "Miembro" : "Secretario"}</td>
                    <td className="px-4 py-3 text-sm text-text-900">{etiqueta(catalogo?.areas, m.area)}</td>
                    <td className="px-4 py-3 text-sm text-text-900">{m.condicion === "PRINCIPAL" ? "Principal" : "Suplente"}</td>
                    <td className="px-4 py-3 text-sm text-text-900">{m.suplente_de ?? "—"}</td>
                    <td className="px-4 py-3 text-sm text-text-900">{formatearFechaDeNegocio(m.desde)}</td>
                    <td className="px-4 py-3 text-sm text-text-900">{m.certificacion_snc ?? "—"}</td>
                    <td className="px-4 py-3 text-sm text-text-900">
                      {estado === "BORRADOR" && puedeGestionar ? (
                        <Button
                          type="button"
                          variant="ghost"
                          size="sm"
                          aria-label={`Retirar a ${m.funcionario.nombre}`}
                          onClick={() => {
                            setMiembroEnRetiro({ id: m.id, nombre: m.funcionario.nombre });
                            abrirPanel("retirar-miembro");
                          }}
                        >
                          Retirar
                        </Button>
                      ) : null}
                      {estado === "VIGENTE" && puedeCerrar && !detalle.es_historica && !m.fin_efectivo ? (
                        <Button
                          type="button"
                          variant="ghost"
                          size="sm"
                          aria-label={`Terminar a ${m.funcionario.nombre}`}
                          onClick={() => {
                            setMiembroEnTerminacion({ id: m.id, nombre: m.funcionario.nombre });
                            abrirPanel("terminar-miembro");
                          }}
                        >
                          Terminar
                        </Button>
                      ) : null}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {miembrosAnteriores.length > 0 ? (
        <section aria-labelledby="anteriores-titulo" className="mb-8">
          <h2 id="anteriores-titulo" className="mb-4 text-lg font-semibold text-text-900">
            Miembros anteriores
          </h2>
          <div className="overflow-x-auto rounded-lg border border-border-subtle" role="region" tabIndex={0} aria-label="Miembros anteriores">
            <table className="min-w-full divide-y divide-border-subtle">
              <caption className="sr-only">Miembros anteriores</caption>
              <thead className="bg-surface-50">
                <tr>
                  <th scope="col" className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-text-600">Funcionario</th>
                  <th scope="col" className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-text-600">Función</th>
                  <th scope="col" className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-text-600">Condición</th>
                  <th scope="col" className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-text-600">Desde</th>
                  <th scope="col" className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-text-600">Hasta</th>
                  <th scope="col" className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-text-600">Causa</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border-subtle bg-white">
                {miembrosAnteriores.map((m) => (
                  <tr key={m.id}>
                    <td className="px-4 py-3 text-sm text-text-900">{m.funcionario.nombre}</td>
                    <td className="px-4 py-3 text-sm text-text-900">{m.funcion === "MIEMBRO" ? "Miembro" : "Secretario"}</td>
                    <td className="px-4 py-3 text-sm text-text-900">{m.condicion === "PRINCIPAL" ? "Principal" : "Suplente"}</td>
                    <td className="px-4 py-3 text-sm text-text-900">{formatearFechaDeNegocio(m.desde)}</td>
                    <td className="px-4 py-3 text-sm text-text-900">{m.fin_efectivo ? formatearFechaDeNegocio(m.fin_efectivo) : "—"}</td>
                    <td className="px-4 py-3 text-sm text-text-900">{etiqueta(catalogo?.causas_fin, m.causa_fin)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      ) : null}

      <section aria-labelledby="inhibiciones-titulo" className="mb-8">
        <h2 id="inhibiciones-titulo" className="mb-4 text-lg font-semibold text-text-900">
          Inhibiciones
        </h2>
        {detalle.inhibiciones.length === 0 ? (
          <EmptyState title="Sin inhibiciones" description="No hay inhibiciones declaradas." />
        ) : (
          <div className="overflow-x-auto rounded-lg border border-border-subtle" role="region" tabIndex={0} aria-label="Inhibiciones">
            <table className="min-w-full divide-y divide-border-subtle">
              <caption className="sr-only">Inhibiciones declaradas</caption>
              <thead className="bg-surface-50">
                <tr>
                  <th scope="col" className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-text-600">Miembro</th>
                  <th scope="col" className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-text-600">Suplente que actúa</th>
                  <th scope="col" className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-text-600">Asunto</th>
                  <th scope="col" className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-text-600">Causal</th>
                  <th scope="col" className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-text-600">Fecha</th>
                  <th scope="col" className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-text-600">Estado</th>
                  <th scope="col" className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-text-600">Resolución</th>
                  <th scope="col" className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-text-600">Acciones</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border-subtle bg-white">
                {detalle.inhibiciones.map((inh) => (
                  <tr key={inh.id}>
                    <td className="px-4 py-3 text-sm text-text-900">{inh.miembro}</td>
                    <td className="px-4 py-3 text-sm text-text-900">{inh.suplente ?? "—"}</td>
                    <td className="px-4 py-3 text-sm text-text-900">{inh.asunto}</td>
                    <td className="px-4 py-3 text-sm text-text-900">{inh.causal_etiqueta}</td>
                    <td className="px-4 py-3 text-sm text-text-900">{formatearFechaDeNegocio(inh.fecha)}</td>
                    <td className="px-4 py-3 text-sm text-text-900">
                      {inh.estado === "DECLARADA" ? "Declarada" : inh.estado === "ACEPTADA" ? "Aceptada" : "Rechazada"}
                    </td>
                    <td className="px-4 py-3 text-sm text-text-900">{inh.motivo_resolucion ?? "—"}</td>
                    <td className="px-4 py-3 text-sm text-text-900">
                      {inh.estado === "DECLARADA" && puedeActivar ? (
                        <Button
                          type="button"
                          variant="ghost"
                          size="sm"
                          aria-label={`Resolver inhibición de ${inh.miembro}`}
                          onClick={() => {
                            setInhibicionEnResolucion({
                              id: inh.id,
                              miembro_id: inh.miembro_id,
                              miembro: inh.miembro,
                              asunto: inh.asunto,
                              version: inh.version,
                            });
                            abrirPanel("resolver-inhibicion");
                          }}
                        >
                          Resolver
                        </Button>
                      ) : null}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <section aria-labelledby="historia-titulo" className="mb-8">
        <h2 id="historia-titulo" className="mb-4 text-lg font-semibold text-text-900">
          Historia
        </h2>
        <ul className="space-y-3">
          {detalle.historia.map((h, idx) => (
            <li key={`${h.tipo}-${h.fecha}-${idx}`} className="rounded-lg border border-border-subtle p-3">
              <div className="text-sm font-medium text-text-900">{formatearFecha(h.fecha)}</div>
              <div className="text-xs text-text-600">{h.usuario ?? "Sistema"}</div>
              <div className="mt-1 text-sm text-text-700">{h.descripcion}</div>
            </li>
          ))}
        </ul>
      </section>
    </PageContent>
  );
}
