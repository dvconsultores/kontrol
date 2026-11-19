import { useCallback, useState } from "react";
import { Link, useNavigate, useParams } from "react-router";
import { useQuery, useQueryClient } from "@tanstack/react-query";

import { useAutoridad } from "@/app/autoridad/AutoridadContext";
import { useCompany } from "@/app/contexts/CompanyContext";
import { useNotifications } from "@/app/contexts/NotificationContext";
import { ApiError } from "@/api/client";
import { AsyncButton } from "@/components/AsyncButton";
import { Button } from "@/components/Button";
import { ErrorState } from "@/components/ErrorState";
import { FormField } from "@/components/FormField";
import { LoadingState } from "@/components/LoadingState";
import { PageContent } from "@/layout/PageContent";
import { PageHeader } from "@/components/PageHeader";
import { TextInput } from "@/components/TextInput";
import { formatearFecha } from "@/i18n";
import { formatearFechaDeNegocio } from "@/lib/fecha-de-negocio";
import {
  ETIQUETAS_EVIDENCIA,
  ETIQUETAS_HITO,
  describirPlazo,
} from "./reglaActa";
import { ReglaActaResumen } from "./ReglaActaResumen";
import {
  activarPoliticaActa,
  cerrarPoliticaActa,
  getPoliticaActa,
  nuevaVersionPoliticaActa,
} from "./politicasActa";

const ETIQUETAS_EVENTO: Record<string, string> = {
  CREADA: "Creada",
  EDITADA: "Editada",
  ACTIVADA: "Activada",
  CERRADA: "Cerrada",
  SUSTITUIDA: "Cerrada (sustituida)",
  NUEVA_VERSION: "Nueva versión",
};

const ETIQUETAS_AMBITO: Record<string, string> = {
  TODAS: "Todas las actas",
  ENTE: "Acta de la entidad",
  UNIDAD: "Acta de una unidad",
};

function etiquetaBooleana(v: boolean): string {
  return v ? "Sí" : "No";
}

export function PoliticaActaPage(): React.JSX.Element {
  const { politicaId } = useParams<{ politicaId: string }>();
  const navigate = useNavigate();
  const { activeCompanyId } = useCompany();
  const { tiene } = useAutoridad();
  const { notify } = useNotifications();
  const queryClient = useQueryClient();

  const puedeVer = tiene("gobierno_actas:view", "empresa");
  const puedeConfigurar = tiene("gobierno_actas:configure", "empresa");
  const puedeActivar = tiene("gobierno_actas:activate", "empresa");

  const [motivoCierre, setMotivoCierre] = useState("");
  const [panelCierre, setPanelCierre] = useState(false);
  const [mensajeAlerta, setMensajeAlerta] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);

  const detalle = useQuery({
    queryKey: ["gobierno-actas-politica", activeCompanyId, politicaId],
    queryFn: () => getPoliticaActa(politicaId ?? ""),
    enabled: Boolean(activeCompanyId && politicaId && puedeVer),
    retry: false,
  });

  const invalidar = useCallback(() => {
    queryClient.invalidateQueries({
      queryKey: ["gobierno-actas-politica", activeCompanyId],
    });
    queryClient.invalidateQueries({
      queryKey: ["gobierno-actas-politicas", activeCompanyId],
    });
    setMensajeAlerta(null);
  }, [activeCompanyId, queryClient]);

  const manejarError = useCallback((e: unknown) => {
    const apiError = e as ApiError;
    setMensajeAlerta(apiError?.message ?? "No fue posible completar la acción");
  }, []);

  const activar = useCallback(async () => {
    if (!detalle.data) return;
    setEnviando(true);
    setMensajeAlerta(null);
    try {
      await activarPoliticaActa(detalle.data.id, detalle.data.version);
      notify({ type: "success", title: "Política activada" });
      invalidar();
    } catch (e) {
      manejarError(e);
    } finally {
      setEnviando(false);
    }
  }, [detalle.data, invalidar, manejarError, notify]);

  const cerrar = useCallback(async () => {
    if (!detalle.data || !motivoCierre.trim()) return;
    setEnviando(true);
    setMensajeAlerta(null);
    try {
      await cerrarPoliticaActa(detalle.data.id, detalle.data.version, motivoCierre.trim());
      notify({ type: "success", title: "Política cerrada" });
      setPanelCierre(false);
      setMotivoCierre("");
      invalidar();
    } catch (e) {
      manejarError(e);
    } finally {
      setEnviando(false);
    }
  }, [detalle.data, invalidar, manejarError, motivoCierre, notify]);

  const versionar = useCallback(async () => {
    if (!detalle.data) return;
    setEnviando(true);
    setMensajeAlerta(null);
    try {
      const nueva = await nuevaVersionPoliticaActa(detalle.data.id);
      notify({ type: "success", title: "Nueva versión creada" });
      invalidar();
      navigate(`/gobierno/actas-entrega/politicas/${nueva.id}/editar`);
    } catch (e) {
      manejarError(e);
    } finally {
      setEnviando(false);
    }
  }, [detalle.data, invalidar, manejarError, navigate, notify]);

  if (!puedeVer) {
    return (
      <PageContent>
        <ErrorState message="No tiene permiso para ver las políticas de actas." />
      </PageContent>
    );
  }

  if (!activeCompanyId || !politicaId) {
    return (
      <PageContent>
        <ErrorState message="Seleccione una empresa activa." />
      </PageContent>
    );
  }

  if (detalle.isLoading) {
    return (
      <PageContent>
        <LoadingState />
      </PageContent>
    );
  }

  if (detalle.isError || !detalle.data) {
    return (
      <PageContent>
        <ErrorState message="No fue posible cargar la política." />
      </PageContent>
    );
  }

  const d = detalle.data;

  const acciones = d.acciones;
  const puedeEditar = acciones.editar && puedeConfigurar;
  const puedeActivarPolitica = acciones.activar && puedeActivar;
  const puedeNuevaVersion = acciones.nueva_version && puedeConfigurar;
  const puedeCerrarPolitica = acciones.cerrar && puedeActivar;

  return (
    <PageContent>
      <PageHeader
        title={`Política ${d.codigo} v${d.numero_version}`}
        description={d.estado_etiqueta}
        actions={
          <div className="flex flex-wrap items-center gap-2">
            {puedeEditar && (
              <Link
                to={`/gobierno/actas-entrega/politicas/${d.id}/editar`}
                className="inline-flex items-center rounded-md border border-border-subtle bg-white px-3 py-2 text-sm font-medium text-text-900 hover:bg-surface-50"
              >
                Editar
              </Link>
            )}
            {puedeActivarPolitica && (
              <AsyncButton onClick={activar} disabled={enviando}>
                Activar
              </AsyncButton>
            )}
            {puedeNuevaVersion && (
              <AsyncButton onClick={versionar} disabled={enviando}>
                Nueva versión
              </AsyncButton>
            )}
            {puedeCerrarPolitica && (
              <Button variant="secondary" onClick={() => setPanelCierre(true)}>
                Cerrar política
              </Button>
            )}
          </div>
        }
      />

      {panelCierre && (
        <div className="mt-4 rounded-md border border-border-subtle bg-white p-4">
          <h2 className="text-lg font-semibold">Cerrar política</h2>
          <div className="mt-2 space-y-4">
            <FormField label="Motivo del cierre" htmlFor="p-motivo-cierre">
              <TextInput
                id="p-motivo-cierre"
                value={motivoCierre}
                onChange={(e) => setMotivoCierre(e.target.value)}
                placeholder="Explique el motivo del cierre"
              />
            </FormField>
            <div className="flex gap-2">
              <AsyncButton onClick={cerrar} disabled={enviando || !motivoCierre.trim()}>
                Cerrar política
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
              <dt className="font-medium text-text-600">Nombre</dt>
              <dd>{d.nombre}</dd>
            </div>
            <div>
              <dt className="font-medium text-text-600">Descripción</dt>
              <dd>{d.descripcion || "—"}</dd>
            </div>
            <div>
              <dt className="font-medium text-text-600">Fundamento</dt>
              <dd>{d.fundamento || "—"}</dd>
            </div>
            <div>
              <dt className="font-medium text-text-600">Vigencia</dt>
              <dd>
                {formatearFechaDeNegocio(d.vigente_desde)} —{" "}
                {d.vigente_hasta ? formatearFechaDeNegocio(d.vigente_hasta) : "sin fin"}
              </dd>
            </div>
            <div>
              <dt className="font-medium text-text-600">Numeración</dt>
              <dd>{d.numeracion_patron ?? "Formato por defecto"}</dd>
            </div>
            <div>
              <dt className="font-medium text-text-600">Testigos en la entrega</dt>
              <dd>{d.testigos_en_entrega}</dd>
            </div>
            <div>
              <dt className="font-medium text-text-600">Cargo de máxima autoridad (código)</dt>
              <dd>{d.cargo_maxima_autoridad_codigo ?? "—"}</dd>
            </div>
            <div>
              <dt className="font-medium text-text-600">Actas que la usan</dt>
              <dd>{d.actas_que_la_usan}</dd>
            </div>
          </dl>
        </section>

        <section>
          <h2 className="text-lg font-semibold">Supuestos declarados</h2>
          {d.vinculos.length === 0 ? (
            <p className="mt-2 text-sm text-text-600">Sin supuestos declarados: solo rigen los anexos universales del catálogo legal.</p>
          ) : (
            <div className="relative overflow-x-auto" tabIndex={0} role="region" aria-label="Supuestos declarados desplazables">
              <table className="w-full text-sm" aria-label="Supuestos declarados">
                <thead>
                  <tr className="border-b border-border-subtle text-left text-xs uppercase text-text-600">
                    <th scope="col" className="px-3 py-2">Supuesto</th>
                    <th scope="col" className="px-3 py-2">Alcance</th>
                  </tr>
                </thead>
                <tbody>
                  {d.vinculos.map((v, idx) => (
                    <tr key={`${v.supuesto}-${v.unit_id ?? "ente"}-${idx}`} className="border-b border-border-subtle">
                      <td className="px-3 py-2">
                        N34 art. {v.articulo ?? v.supuesto} · {v.titulo ?? ""}
                      </td>
                      <td className="px-3 py-2">
                        {v.alcance === "ENTE" ? "Entidad" : `Unidad: ${v.unidad ?? "—"}`}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>

        <section>
          <h2 className="text-lg font-semibold">Requisitos del ente</h2>
          <div className="relative overflow-x-auto" tabIndex={0} role="region" aria-label="Requisitos del ente desplazables">
            <table className="w-full text-sm" aria-label="Requisitos del ente">
              <thead>
                <tr className="border-b border-border-subtle text-left text-xs uppercase text-text-600">
                  <th scope="col" className="px-3 py-2">Código</th>
                  <th scope="col" className="px-3 py-2">Requisito</th>
                  <th scope="col" className="px-3 py-2">Evidencia</th>
                  <th scope="col" className="px-3 py-2">Obligatorio</th>
                  <th scope="col" className="px-3 py-2">Ámbito</th>
                  <th scope="col" className="px-3 py-2">Supuesto</th>
                  <th scope="col" className="px-3 py-2">Tipo documental</th>
                  <th scope="col" className="px-3 py-2">Fuente</th>
                </tr>
              </thead>
              <tbody>
                {d.requisitos.map((r, idx) => (
                  <tr key={`${r.codigo}-${idx}`} className="border-b border-border-subtle">
                    <td className="px-3 py-2">{r.codigo}</td>
                    <td className="px-3 py-2">{r.titulo}</td>
                    <td className="px-3 py-2">{ETIQUETAS_EVIDENCIA[r.evidencia]}</td>
                    <td className="px-3 py-2">{etiquetaBooleana(r.obligatorio)}</td>
                    <td className="px-3 py-2">{ETIQUETAS_AMBITO[r.ambito]}</td>
                    <td className="px-3 py-2">{r.supuesto ?? "—"}</td>
                    <td className="px-3 py-2">{r.document_type_nombre ?? "—"}</td>
                    <td className="px-3 py-2">{r.fuente ?? "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        <section>
          <h2 className="text-lg font-semibold">Plazos internos</h2>
          <div className="relative overflow-x-auto" tabIndex={0} role="region" aria-label="Plazos internos desplazables">
            <table className="w-full text-sm" aria-label="Plazos internos">
              <thead>
                <tr className="border-b border-border-subtle text-left text-xs uppercase text-text-600">
                  <th scope="col" className="px-3 py-2">Hito</th>
                  <th scope="col" className="px-3 py-2">Plazo</th>
                  <th scope="col" className="px-3 py-2">Plazo legal</th>
                  <th scope="col" className="px-3 py-2">Fuente</th>
                </tr>
              </thead>
              <tbody>
                {d.plazos.map((p, idx) => (
                  <tr key={`${p.hito}-${idx}`} className="border-b border-border-subtle">
                    <td className="px-3 py-2">{ETIQUETAS_HITO[p.hito]}</td>
                    <td className="px-3 py-2">{describirPlazo(p)}</td>
                    <td className="px-3 py-2">
                      {p.legal_valor != null ? `${p.legal_valor} días hábiles` : "—"}
                    </td>
                    <td className="px-3 py-2">{p.fuente ?? "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        <section>
          <p className="text-sm text-text-600">
            Vista previa: regla de un acta de la entidad con esta política.
          </p>
          <ReglaActaResumen regla={d.regla_ente} />
        </section>

        <section>
          <h2 className="text-lg font-semibold">Historia</h2>
          {d.historia.length === 0 ? (
            <p className="mt-2 text-sm text-text-600">Sin historia</p>
          ) : (
            <ul className="mt-2 space-y-2 text-sm">
              {d.historia.map((h, idx) => (
                <li key={`${h.evento}-${h.version}-${idx}`}>
                  {formatearFecha(h.fecha)} · {ETIQUETAS_EVENTO[h.evento] ?? h.evento} ·{" "}
                  {h.actor ?? "—"}
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
                    to={`/gobierno/actas-entrega/politicas/${v.id}`}
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
