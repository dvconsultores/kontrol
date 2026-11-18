import { useCallback, useState } from "react";
import { Link, useNavigate, useParams } from "react-router";
import { useQuery, useQueryClient } from "@tanstack/react-query";

import { useCompany } from "@/app/contexts/CompanyContext";
import { useNotifications } from "@/app/contexts/NotificationContext";
import { useAutoridad } from "@/app/autoridad/AutoridadContext";
import { apiFetch, ApiError } from "@/api/client";
import { AsyncButton } from "@/components/AsyncButton";
import { Button } from "@/components/Button";
import { TextInput } from "@/components/TextInput";
import { FormField } from "@/components/FormField";
import { EmptyState } from "@/components/EmptyState";
import { LoadingState } from "@/components/LoadingState";
import { PageHeader } from "@/components/PageHeader";
import { PageContent } from "@/layout/PageContent";
import { ErrorDeCarga } from "@/modules/gobierno/ocupacion/ErrorDeCarga";
import { formatearFechaDeNegocio } from "@/lib/fecha-de-negocio";
import {
  CONSULTA_POLITICAS_ASIGNACION,
  RUTA_POLITICAS_ASIGNACION,
  type PoliticaAsignacionCatalogo,
  type PoliticaAsignacionDetalle,
  etiquetaDeCodigo,
  describirLimite,
  describirAutorizacion,
} from "./politicasAsignacion";

const ETIQUETAS_EVENTO: Record<string, string> = {
  CREADA: "Creada",
  EDITADA: "Editada",
  ACTIVADA: "Activada",
  CERRADA: "Cerrada",
  SUSTITUIDA: "Sustituida",
  NUEVA_VERSION: "Nueva versión",
};

function etiquetaBooleana(v: boolean): string {
  return v ? "Sí" : "No";
}

export function PoliticaAsignacionPage(): React.JSX.Element {
  const { politicaId } = useParams<{ politicaId: string }>();
  const navigate = useNavigate();
  const { activeCompanyId } = useCompany();
  const { tiene } = useAutoridad();
  const { notify } = useNotifications();
  const queryClient = useQueryClient();

  const puedeVer = tiene("gobierno_ocupacion:view", "empresa");
  const puedeConfigurar = tiene("gobierno_ocupacion:configure", "empresa");
  const puedeActivar = tiene("gobierno_ocupacion:activate", "empresa");
  const puedeCerrar = tiene("gobierno_ocupacion:revoke", "empresa");
  const puedeVersionar = tiene("gobierno_ocupacion:configure", "empresa");

  const [motivoCierre, setMotivoCierre] = useState("");
  const [panelCierre, setPanelCierre] = useState(false);
  const [mensajeAlerta, setMensajeAlerta] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);

  const detalle = useQuery<PoliticaAsignacionDetalle>({
    queryKey: [...CONSULTA_POLITICAS_ASIGNACION, activeCompanyId, "ficha", politicaId],
    queryFn: () =>
      apiFetch<PoliticaAsignacionDetalle>(
        `${RUTA_POLITICAS_ASIGNACION}/${politicaId}`,
      ),
    enabled: Boolean(activeCompanyId && politicaId && puedeVer),
    retry: false,
  });

  const catalogo = useQuery<PoliticaAsignacionCatalogo>({
    queryKey: [...CONSULTA_POLITICAS_ASIGNACION, activeCompanyId, "catalogo-politicas"],
    queryFn: () =>
      apiFetch<PoliticaAsignacionCatalogo>(
        `${RUTA_POLITICAS_ASIGNACION}/catalogo`,
      ),
    retry: false,
    enabled: Boolean(activeCompanyId && puedeVer),
  });

  const recargar = useCallback(() => {
    queryClient.invalidateQueries({
      queryKey: [...CONSULTA_POLITICAS_ASIGNACION, activeCompanyId],
    });
    setMensajeAlerta(null);
  }, [activeCompanyId, queryClient]);

  const manejarError = useCallback(
    (e: unknown) => {
      const apiError = e as ApiError;
      if (apiError?.status === 409 && apiError?.code === "ORG_ASSIGNMENT_POLICY_STALE") {
        setMensajeAlerta("La política cambió; recárguela");
        recargar();
      } else if (apiError?.status && apiError.status >= 400 && apiError.status < 500) {
        setMensajeAlerta(apiError.message ?? "No fue posible completar la acción");
      } else {
        setMensajeAlerta(apiError?.message ?? "No fue posible completar la acción");
      }
    },
    [recargar],
  );

  const activar = useCallback(async () => {
    if (!detalle.data) return;
    setEnviando(true);
    setMensajeAlerta(null);
    try {
      await apiFetch<PoliticaAsignacionDetalle>(
        `${RUTA_POLITICAS_ASIGNACION}/${detalle.data.id}/activar`,
        {
          method: "POST",
          ifMatch: String(detalle.data.version),
        },
      );
      notify({ type: "success", title: "Política activada" });
      recargar();
    } catch (e) {
      manejarError(e);
    } finally {
      setEnviando(false);
    }
  }, [detalle.data, manejarError, notify, recargar]);

  const cerrar = useCallback(async () => {
    if (!detalle.data || !motivoCierre.trim() || motivoCierre.trim().length < 5 || motivoCierre.trim().length > 500) return;
    setEnviando(true);
    setMensajeAlerta(null);
    try {
      await apiFetch<PoliticaAsignacionDetalle>(
        `${RUTA_POLITICAS_ASIGNACION}/${detalle.data.id}/cerrar`,
        {
          method: "POST",
          ifMatch: String(detalle.data.version),
          body: { motivo: motivoCierre.trim() },
        },
      );
      notify({ type: "success", title: "Política cerrada" });
      setPanelCierre(false);
      setMotivoCierre("");
      recargar();
    } catch (e) {
      manejarError(e);
    } finally {
      setEnviando(false);
    }
  }, [detalle.data, manejarError, motivoCierre, notify, recargar]);

  const versionar = useCallback(async () => {
    if (!detalle.data) return;
    setEnviando(true);
    setMensajeAlerta(null);
    try {
      const nueva = await apiFetch<PoliticaAsignacionDetalle>(
        `${RUTA_POLITICAS_ASIGNACION}/${detalle.data.id}/nueva-version`,
        {
          method: "POST",
          ifMatch: String(detalle.data.version),
        },
      );
      notify({ type: "success", title: "Nueva versión creada" });
      recargar();
      navigate(`${RUTA_POLITICAS_ASIGNACION}/${nueva.id}`);
    } catch (e) {
      manejarError(e);
    } finally {
      setEnviando(false);
    }
  }, [detalle.data, manejarError, navigate, notify, recargar]);

  if (!puedeVer) {
    return (
      <PageContent>
        <EmptyState
          title="Sin acceso"
          description="No tiene permisos para ver esta política de asignación."
        />
      </PageContent>
    );
  }

  if (!activeCompanyId || !politicaId) {
    return (
      <PageContent>
        <EmptyState title="Sin empresa" description="Seleccione una empresa activa." />
      </PageContent>
    );
  }

  if (detalle.isLoading || catalogo.isLoading) {
    return (
      <PageContent>
        <LoadingState />
      </PageContent>
    );
  }

  if (detalle.isError || !detalle.data) {
    return (
      <PageContent>
        <ErrorDeCarga
          message={
            detalle.error instanceof Error
              ? detalle.error.message
              : "No fue posible cargar la política."
          }
          onRetry={() => detalle.refetch()}
        />
      </PageContent>
    );
  }

  const d = detalle.data;
  const c = catalogo.data;

  const puedeEditar = d.estado === "BORRADOR" && puedeConfigurar;
  const puedeCrearVersion = (d.estado === "VIGENTE" || d.estado === "CERRADA") && !d.existe_borrador && puedeVersionar;

  const etiquetaEmisor = () => {
    if (!d.emisor_tipo || d.emisor_tipo === "CUALQUIERA") return "Sin exigencia propia";
    if (d.emisor_tipo === "CARGO") return "Cargo designado";
    if (d.emisor_tipo === "COMPETENCIA") {
      return `Competencia: ${d.emisor_competencia_accion ?? "—"} sobre ${d.emisor_competencia_materia ?? "—"}`;
    }
    return "—";
  };

  const autorizacionTexto = () => {
    if (!d.autorizacion_requerida || !d.autorizacion_etiqueta) return "No exige";
    return describirAutorizacion({
      etiqueta: d.autorizacion_etiqueta,
      ambito: d.autorizacion_ambito ?? "TODAS",
      mas_de_dias: d.autorizacion_mas_de_dias ?? 0,
      fuente: "esta política",
    });
  };

  const competenciasTexto = () => {
    if (d.competencias.length === 0) return "Todas las del cargo";
    return d.competencias.map((comp) => `${comp.accion} · ${comp.materia}`).join(", ");
  };

  const documentosTexto = () => {
    if (d.documentos.length === 0) return "Ninguno";
    return d.documentos
      .map((doc) => {
        const etapa = doc.etapa === "ACTIVACION" ? "Activación" : "Revocación";
        const obligatorio = doc.obligatorio ? "Obligatorio" : "Opcional";
        return `${doc.document_type_nombre ?? doc.document_type_id} · ${etapa} · ${obligatorio}`;
      })
      .join(", ");
  };

  return (
    <PageContent>
      <PageHeader
        crumbs={[
          { label: "Gobierno" },
          { label: "Ocupación de cargos" },
          { label: "Políticas de asignación" },
          { label: `${d.codigo} v${d.numero_version}` },
        ]}
        title={`${d.codigo} v${d.numero_version} · ${d.nombre}`}
        description={d.estado_etiqueta ?? etiquetaDeCodigo(c?.estados, d.estado)}
        actions={
          <div className="flex flex-wrap items-center gap-2">
            {puedeEditar && (
              <Link
                to={`${RUTA_POLITICAS_ASIGNACION}/${d.id}/editar`}
                className="inline-flex items-center rounded-md border border-border-subtle bg-white px-3 py-2 text-sm font-medium text-text-900 hover:bg-surface-50"
              >
                Editar
              </Link>
            )}
            {d.estado === "BORRADOR" && puedeActivar && (
              <AsyncButton onClick={activar} disabled={enviando}>
                Activar
              </AsyncButton>
            )}
            {d.estado === "VIGENTE" && puedeCerrar && (
              <Button variant="secondary" onClick={() => setPanelCierre(true)}>
                Cerrar
              </Button>
            )}
            {puedeCrearVersion && (
              <AsyncButton onClick={versionar} disabled={enviando}>
                Nueva versión
              </AsyncButton>
            )}
          </div>
        }
      />

      {panelCierre && (
        <div className="mt-4 rounded-md border border-border-subtle bg-white p-4">
          <h2 className="text-lg font-semibold">Cerrar política</h2>
          <div className="mt-2 grid gap-4">
            <FormField label="Motivo del cierre" htmlFor="motivo-cierre">
              <TextInput
                id="motivo-cierre"
                value={motivoCierre}
                onChange={(e) => setMotivoCierre(e.target.value)}
                placeholder="Explique el motivo del cierre"
                minLength={5}
                maxLength={500}
              />
            </FormField>
            <div className="flex gap-2">
              <AsyncButton
                onClick={cerrar}
                disabled={enviando || motivoCierre.trim().length < 5 || motivoCierre.trim().length > 500}
              >
                Confirmar cierre
              </AsyncButton>
              <Button
                variant="ghost"
                onClick={() => {
                  setPanelCierre(false);
                  setMotivoCierre("");
                }}
              >
                Cancelar
              </Button>
            </div>
          </div>
        </div>
      )}

      {mensajeAlerta && (
        <div
          role="alert"
          className="mt-4 rounded-md border border-yellow-300 bg-yellow-50 p-4 text-yellow-800"
        >
          {mensajeAlerta}
        </div>
      )}

      <div className="mt-6 space-y-8">
        <section>
          <h2 className="text-lg font-semibold">Datos</h2>
          <dl className="mt-2 grid gap-2 text-sm sm:grid-cols-2">
            <div>
              <dt className="font-medium text-text-600">Figura</dt>
              <dd>{d.figura_etiqueta ?? etiquetaDeCodigo(c?.figuras, d.figura)}</dd>
            </div>
            <div>
              <dt className="font-medium text-text-600">Vigencia</dt>
              <dd>
                {d.vigente_desde
                  ? formatearFechaDeNegocio(d.vigente_desde)
                  : "—"}{" "}
                —{" "}
                {d.vigente_hasta
                  ? formatearFechaDeNegocio(d.vigente_hasta)
                  : "sin fin"}
              </dd>
            </div>
            <div>
              <dt className="font-medium text-text-600">Fundamento</dt>
              <dd>{d.fundamento || "—"}</dd>
            </div>
            <div>
              <dt className="font-medium text-text-600">Descripción</dt>
              <dd>{d.descripcion || "—"}</dd>
            </div>
            <div>
              <dt className="font-medium text-text-600">Asignaciones que la aplican</dt>
              <dd>{d.asignaciones}</dd>
            </div>
          </dl>
        </section>

        <section>
          <h2 className="text-lg font-semibold">Reglas</h2>
          <dl className="mt-2 grid gap-2 text-sm sm:grid-cols-2">
            <div>
              <dt className="font-medium text-text-600">Fin obligatorio</dt>
              <dd>{etiquetaBooleana(d.exige_fin)}</dd>
            </div>
            <div>
              <dt className="font-medium text-text-600">Máximo de días</dt>
              <dd>{d.max_dias != null ? d.max_dias : "Sin límite propio"}</dd>
            </div>
            <div>
              <dt className="font-medium text-text-600">Medio del acto</dt>
              <dd>{etiquetaDeCodigo(c?.medios, d.acto_medio) ?? "Sin exigencia propia"}</dd>
            </div>
            <div>
              <dt className="font-medium text-text-600">Emisor</dt>
              <dd>{etiquetaEmisor()}</dd>
            </div>
            <div>
              <dt className="font-medium text-text-600">Autorización especial</dt>
              <dd>{autorizacionTexto()}</dd>
            </div>
            <div>
              <dt className="font-medium text-text-600">Competencias permitidas</dt>
              <dd>{competenciasTexto()}</dd>
            </div>
            <div>
              <dt className="font-medium text-text-600">Avocación</dt>
              <dd>{d.prohibe_avocacion ? "Prohibida" : "Según la ley"}</dd>
            </div>
            <div>
              <dt className="font-medium text-text-600">Documentos</dt>
              <dd>{documentosTexto()}</dd>
            </div>
          </dl>
        </section>

        <section>
          <h2 className="text-lg font-semibold">Regla aplicada</h2>
          <dl className="mt-2 grid gap-2 text-sm sm:grid-cols-2">
            <div>
              <dt className="font-medium text-text-600">Origen</dt>
              <dd>{d.regla.origen_etiqueta}</dd>
            </div>
          </dl>
          <div className="mt-2 space-y-4">
            <div>
              <h3 className="text-sm font-semibold">Pisos legales</h3>
              {d.regla.pisos.length === 0 ? (
                <p className="mt-1 text-sm text-text-600">
                  Ningún piso legal para esta figura en el régimen del ente
                </p>
              ) : (
                <ul className="mt-1 list-disc pl-5 text-sm">
                  {d.regla.pisos.map((piso, idx) => (
                    <li key={`${piso.codigo}-${idx}`}>{piso.fuente}</li>
                  ))}
                </ul>
              )}
            </div>
            <div>
              <h3 className="text-sm font-semibold">Límites</h3>
              {d.regla.limites.length === 0 ? (
                <p className="mt-1 text-sm text-text-600">Sin límites adicionales</p>
              ) : (
                <ul className="mt-1 list-disc pl-5 text-sm">
                  {d.regla.limites.map((limite, idx) => (
                    <li key={idx}>{describirLimite(limite)}</li>
                  ))}
                </ul>
              )}
            </div>
            <div>
              <h3 className="text-sm font-semibold">Autorizaciones</h3>
              {d.regla.autorizaciones.length === 0 ? (
                <p className="mt-1 text-sm text-text-600">Sin autorizaciones especiales</p>
              ) : (
                <ul className="mt-1 list-disc pl-5 text-sm">
                  {d.regla.autorizaciones.map((autorizacion, idx) => (
                    <li key={idx}>{describirAutorizacion(autorizacion)}</li>
                  ))}
                </ul>
              )}
            </div>
            {d.regla.acto_medio && (
              <div>
                <h3 className="text-sm font-semibold">Medio del acto</h3>
                <p className="mt-1 text-sm">{d.regla.acto_medio.mensaje}</p>
              </div>
            )}
          </div>
        </section>

        <section>
          <h2 className="text-lg font-semibold">Historia</h2>
          {d.historia.length === 0 ? (
            <p className="mt-2 text-sm text-text-600">Sin historia</p>
          ) : (
            <div className="relative overflow-x-auto" tabIndex={0} role="region" aria-label="Historia de la política">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-border-subtle text-left text-xs uppercase text-text-600">
                    <th scope="col" className="px-3 py-2">Evento</th>
                    <th scope="col" className="px-3 py-2">Versión</th>
                    <th scope="col" className="px-3 py-2">Fecha</th>
                    <th scope="col" className="px-3 py-2">Actor</th>
                  </tr>
                </thead>
                <tbody>
                  {d.historia.map((h, idx) => (
                    <tr key={`${h.evento}-${h.version}-${idx}`} className="border-b border-border-subtle">
                      <td className="px-3 py-2">
                        {ETIQUETAS_EVENTO[h.evento] ?? h.evento}
                      </td>
                      <td className="px-3 py-2">v{h.version}</td>
                      <td className="px-3 py-2">{formatearFechaDeNegocio(h.fecha)}</td>
                      <td className="px-3 py-2">{h.actor ?? "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>

        <section>
          <h2 className="text-lg font-semibold">Versiones</h2>
          {d.versiones.length === 0 ? (
            <p className="mt-2 text-sm text-text-600">Sin versiones</p>
          ) : (
            <ul className="mt-2 space-y-2 text-sm">
              {d.versiones.map((v) => (
                <li key={v.id}>
                  <Link
                    to={`${RUTA_POLITICAS_ASIGNACION}/${v.id}`}
                    className="font-medium text-brand-700 underline"
                  >
                    v{v.numero_version} · {v.estado}
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>
    </PageContent>
  );
}
