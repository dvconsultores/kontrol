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
  CONSULTA_POLITICAS_COMISION,
  ETIQUETAS_ESTADO_POLITICA,
  describirMayoria,
  etiquetaDe,
  type PoliticaComisionCatalogo,
  type PoliticaComisionDetalle,
} from "./politicasComision";

const ETIQUETAS_EVENTO: Record<string, string> = {
  CREADA: "Creada",
  EDITADA: "Editada",
  ACTIVADA: "Activada",
  CERRADA: "Cerrada",
  SUSTITUIDA: "Sustituida por una versión nueva",
  NUEVA_VERSION: "Nueva versión creada",
};

function etiquetaBooleana(v: boolean): string {
  return v ? "Sí" : "No";
}

function referenciaDe(requisito: PoliticaComisionDetalle["requisitos"][number]): string {
  if (requisito.area_etiqueta) return requisito.area_etiqueta;
  if (requisito.position_nombre) return requisito.position_nombre;
  if (requisito.unit_nombre) return requisito.unit_nombre;
  if (requisito.competencia_accion && requisito.competencia_materia) {
    return `${requisito.competencia_accion} · ${requisito.competencia_materia}`;
  }
  if (requisito.official_nombre) return requisito.official_nombre;
  return "—";
}

export function PoliticaComisionPage(): React.JSX.Element {
  const { politicaId } = useParams<{ politicaId: string }>();
  const navigate = useNavigate();
  const { activeCompanyId } = useCompany();
  const { tiene } = useAutoridad();
  const { notify } = useNotifications();
  const queryClient = useQueryClient();

  const puedeVer = tiene("gobierno_comisiones:view", "empresa");
  const puedeConfigurar = tiene("gobierno_comisiones:configure", "empresa");
  const puedeActivar = tiene("gobierno_comisiones:activate", "empresa");
  const puedeCerrar = tiene("gobierno_comisiones:close", "empresa");

  const [motivoCierre, setMotivoCierre] = useState("");
  const [panelCierre, setPanelCierre] = useState(false);
  const [errorActivacion, setErrorActivacion] = useState<string[] | null>(null);
  const [mensajeAlerta, setMensajeAlerta] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);

  const detalle = useQuery<PoliticaComisionDetalle>({
    queryKey: [...CONSULTA_POLITICAS_COMISION, activeCompanyId, "ficha", politicaId],
    queryFn: () =>
      apiFetch<PoliticaComisionDetalle>(
        `/gobierno/contrataciones/politicas-comision/${politicaId}`,
      ),
    enabled: Boolean(activeCompanyId && politicaId && puedeVer),
    retry: false,
  });

  const catalogo = useQuery<PoliticaComisionCatalogo>({
    queryKey: [...CONSULTA_POLITICAS_COMISION, activeCompanyId, "catalogo-politicas"],
    queryFn: () =>
      apiFetch<PoliticaComisionCatalogo>(
        "/gobierno/contrataciones/politicas-comision/catalogo",
      ),
    retry: false,
    enabled: Boolean(activeCompanyId && puedeVer),
  });

  const recargar = useCallback(() => {
    queryClient.invalidateQueries({
      queryKey: [...CONSULTA_POLITICAS_COMISION, activeCompanyId],
    });
    setMensajeAlerta(null);
    setErrorActivacion(null);
  }, [activeCompanyId, queryClient]);

  const manejarError = useCallback(
    (e: unknown) => {
      const apiError = e as ApiError;
      if (apiError?.status === 409 && apiError?.code === "GOV_COMMISSION_POLICY_STALE") {
        setMensajeAlerta("La política cambió; recárguela");
        recargar();
      } else if (apiError?.status === 409 && apiError?.code === "GOV_COMMISSION_POLICY_CLOSED") {
        setMensajeAlerta(apiError.message ?? "La política ya está cerrada");
        recargar();
      } else if (apiError?.status === 422 && apiError?.code === "GOV_COMMISSION_POLICY_INVALID") {
        const motivos = (apiError.details as { motivos?: string[] } | undefined)?.motivos;
        setErrorActivacion(motivos && motivos.length > 0 ? motivos : [apiError.message ?? "No se puede activar la política"]);
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
    setErrorActivacion(null);
    setMensajeAlerta(null);
    try {
      await apiFetch<PoliticaComisionDetalle>(
        `/gobierno/contrataciones/politicas-comision/${detalle.data.id}/activar`,
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
    if (!detalle.data || !motivoCierre.trim()) return;
    setEnviando(true);
    setMensajeAlerta(null);
    try {
      await apiFetch<PoliticaComisionDetalle>(
        `/gobierno/contrataciones/politicas-comision/${detalle.data.id}/cerrar`,
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
      const nueva = await apiFetch<PoliticaComisionDetalle>(
        `/gobierno/contrataciones/politicas-comision/${detalle.data.id}/nueva-version`,
        {
          method: "POST",
          ifMatch: String(detalle.data.version),
        },
      );
      notify({ type: "success", title: "Nueva versión creada" });
      recargar();
      navigate(`/gobierno/contrataciones/politicas-comision/${nueva.id}`);
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
          description="No tiene permisos para ver esta política de comisión."
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

  const aplicaProcesos: string[] = [];
  if (d.aplica_apertura) aplicaProcesos.push("Apertura de ofertas");
  if (d.aplica_recomendacion) aplicaProcesos.push("Recomendación");

  return (
    <PageContent>
      <PageHeader
        crumbs={[
          { label: "Gobierno" },
          { label: "Contrataciones" },
          { label: "Políticas de comisión" },
          { label: `${d.codigo} v${d.numero_version}` },
        ]}
        title={`${d.codigo} v${d.numero_version} · ${d.nombre}`}
        description={ETIQUETAS_ESTADO_POLITICA[d.estado] ?? d.estado}
        actions={
          <div className="flex flex-wrap items-center gap-2">
            {d.puede_editar && puedeConfigurar && (
              <Link
                to={`/gobierno/contrataciones/politicas-comision/${d.id}/editar`}
                className="inline-flex items-center rounded-md border border-border-subtle bg-white px-3 py-2 text-sm font-medium text-text-900 hover:bg-surface-50"
              >
                Editar
              </Link>
            )}
            {d.puede_activar && puedeActivar && (
              <AsyncButton onClick={activar} disabled={enviando}>
                Activar
              </AsyncButton>
            )}
            {d.puede_cerrar && puedeCerrar && (
              <Button variant="secondary" onClick={() => setPanelCierre(true)}>
                Cerrar
              </Button>
            )}
            {d.puede_versionar && puedeConfigurar && (
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
              />
            </FormField>
            <div className="flex gap-2">
              <AsyncButton
                onClick={cerrar}
                disabled={enviando || !motivoCierre.trim()}
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

      {errorActivacion && (
        <div
          role="alert"
          className="mt-4 rounded-md border border-red-300 bg-red-50 p-4 text-red-800"
        >
          <h2 className="text-sm font-semibold">No se puede activar la política</h2>
          <ul className="mt-2 list-disc pl-5 text-sm">
            {errorActivacion.map((motivo) => (
              <li key={motivo}>{motivo}</li>
            ))}
          </ul>
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
          <h2 className="text-lg font-semibold">Identidad y vigencia</h2>
          <dl className="mt-2 grid gap-2 text-sm sm:grid-cols-2">
            <div>
              <dt className="font-medium text-text-600">Tipo de comisión</dt>
              <dd>{etiquetaDe(c?.tipos_comision, d.tipo_comision)}</dd>
            </div>
            <div>
              <dt className="font-medium text-text-600">Procesos</dt>
              <dd>{aplicaProcesos.length > 0 ? aplicaProcesos.join(", ") : "—"}</dd>
            </div>
            <div>
              <dt className="font-medium text-text-600">Base normativa</dt>
              <dd>{etiquetaDe(c?.bases_normativas, d.base_normativa)}</dd>
            </div>
            <div>
              <dt className="font-medium text-text-600">Fundamento</dt>
              <dd>{d.fundamento || "—"}</dd>
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
          </dl>
        </section>

        <section>
          <h2 className="text-lg font-semibold">Composición</h2>
          <dl className="mt-2 grid gap-2 text-sm sm:grid-cols-2">
            <div>
              <dt className="font-medium text-text-600">Principales (mínimo y máximo)</dt>
              <dd>
                {d.min_principales} — {d.max_principales ?? "sin máximo"}
              </dd>
            </div>
            <div>
              <dt className="font-medium text-text-600">Número impar</dt>
              <dd>{etiquetaBooleana(d.exige_impar)}</dd>
            </div>
            <div>
              <dt className="font-medium text-text-600">Suplente por principal</dt>
              <dd>{etiquetaBooleana(d.suplente_por_principal)}</dd>
            </div>
            <div>
              <dt className="font-medium text-text-600">Secretario</dt>
              <dd>{etiquetaBooleana(d.exige_secretario)}</dd>
            </div>
            <div>
              <dt className="font-medium text-text-600">Suplente del secretario</dt>
              <dd>{etiquetaBooleana(d.exige_suplente_secretario)}</dd>
            </div>
            <div>
              <dt className="font-medium text-text-600">Presidente</dt>
              <dd>{etiquetaBooleana(d.exige_presidente)}</dd>
            </div>
          </dl>
          {d.base_normativa === "LCP_ART14" && (
            <p className="mt-2 text-sm text-text-600">
              Piso legal LCP art. 14: el ente puede endurecerlo, no rebajarlo.
            </p>
          )}
        </section>

        <section>
          <h2 className="text-lg font-semibold">Requisitos de integración</h2>
          {d.requisitos.length === 0 ? (
            <p className="mt-2 text-sm text-text-600">Sin requisitos adicionales</p>
          ) : (
            <div className="relative overflow-x-auto" tabIndex={0}>
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-border-subtle text-left text-xs uppercase text-text-600">
                    <th scope="col" className="px-3 py-2">Etiqueta</th>
                    <th scope="col" className="px-3 py-2">Función</th>
                    <th scope="col" className="px-3 py-2">Condición</th>
                    <th scope="col" className="px-3 py-2">Tipo</th>
                    <th scope="col" className="px-3 py-2">Referencia</th>
                    <th scope="col" className="px-3 py-2">Mínimo</th>
                    <th scope="col" className="px-3 py-2">Máximo</th>
                  </tr>
                </thead>
                <tbody>
                  {d.requisitos.map((r) => (
                    <tr key={r.orden} className="border-b border-border-subtle">
                      <td className="px-3 py-2">{r.etiqueta}</td>
                      <td className="px-3 py-2">{etiquetaDe(c?.funciones, r.funcion)}</td>
                      <td className="px-3 py-2">{etiquetaDe(c?.condiciones, r.condicion)}</td>
                      <td className="px-3 py-2">{etiquetaDe(c?.tipos_requisito, r.tipo)}</td>
                      <td className="px-3 py-2">{referenciaDe(r)}</td>
                      <td className="px-3 py-2">{r.minimo ?? "—"}</td>
                      <td className="px-3 py-2">{r.maximo ?? "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>

        <section>
          <h2 className="text-lg font-semibold">Quórum y decisión</h2>
          <dl className="mt-2 grid gap-2 text-sm sm:grid-cols-2">
            <div>
              <dt className="font-medium text-text-600">Quórum</dt>
              <dd>
                {describirMayoria(d.quorum, {
                  ...Object.fromEntries((c?.tipos_mayoria ?? []).map((x) => [x.codigo, x.etiqueta])),
                })}
              </dd>
            </div>
            <div>
              <dt className="font-medium text-text-600">Decisión</dt>
              <dd>
                {describirMayoria(d.decision, {
                  ...Object.fromEntries((c?.tipos_mayoria ?? []).map((x) => [x.codigo, x.etiqueta])),
                })}{" "}
                · base {etiquetaDe(c?.bases_decision, d.decision.base)}
              </dd>
            </div>
            <div>
              <dt className="font-medium text-text-600">El presidente vota</dt>
              <dd>{etiquetaBooleana(d.presidente_vota)}</dd>
            </div>
            <div>
              <dt className="font-medium text-text-600">Voto dirimente</dt>
              <dd>{etiquetaBooleana(d.presidente_dirimente)}</dd>
            </div>
          </dl>
        </section>

        <section>
          <h2 className="text-lg font-semibold">Documentos exigidos</h2>
          {d.documentos.length === 0 ? (
            <p className="mt-2 text-sm text-text-600">Sin documentos exigidos</p>
          ) : (
            <div className="relative overflow-x-auto" tabIndex={0}>
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-border-subtle text-left text-xs uppercase text-text-600">
                    <th scope="col" className="px-3 py-2">Tipo documental</th>
                    <th scope="col" className="px-3 py-2">Etapa</th>
                    <th scope="col" className="px-3 py-2">Obligatorio</th>
                  </tr>
                </thead>
                <tbody>
                  {d.documentos.map((doc) => (
                    <tr key={doc.document_type_id} className="border-b border-border-subtle">
                      <td className="px-3 py-2">{doc.document_type_nombre}</td>
                      <td className="px-3 py-2">{etiquetaDe(c?.etapas, doc.etapa)}</td>
                      <td className="px-3 py-2">{etiquetaBooleana(doc.obligatorio)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>

        <section>
          <h2 className="text-lg font-semibold">Historia</h2>
          {d.historia.length === 0 ? (
            <p className="mt-2 text-sm text-text-600">Sin historia</p>
          ) : (
            <ul className="mt-2 space-y-2 text-sm">
              {d.historia.map((h, idx) => (
                <li key={`${h.evento}-${h.version}-${idx}`} className="flex gap-2">
                  <span className="font-medium">
                    {ETIQUETAS_EVENTO[h.evento] ?? h.evento}
                  </span>
                  <span className="text-text-600">
                    · v{h.version} · {formatearFechaDeNegocio(h.fecha)}
                    {h.actor ? ` · ${h.actor}` : ""}
                  </span>
                </li>
              ))}
            </ul>
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
                    to={`/gobierno/contrataciones/politicas-comision/${v.id}`}
                    className="font-medium text-brand-700 underline"
                  >
                    v{v.numero_version} · {ETIQUETAS_ESTADO_POLITICA[v.estado] ?? v.estado}
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
