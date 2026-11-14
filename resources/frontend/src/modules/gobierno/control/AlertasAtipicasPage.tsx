import { useState } from "react";
import { Link } from "react-router";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch, ApiError } from "@/api/client";
import { useAutoridad } from "@/app/autoridad/AutoridadContext";
import { useCompany } from "@/app/contexts/CompanyContext";
import { useNotifications } from "@/app/contexts/NotificationContext";
import { Button } from "@/components/Button";
import { EmptyState } from "@/components/EmptyState";
import { LoadingState } from "@/components/LoadingState";
import { PageHeader } from "@/components/PageHeader";
import { PageContent } from "@/layout/PageContent";
import { formatearFecha } from "@/i18n";
import { ErrorDeCarga } from "@/modules/gobierno/ocupacion/ErrorDeCarga";
import { CONSULTA_GOBIERNO } from "@/modules/gobierno/api";

type TipoAlerta = {
  codigo: string;
  etiqueta: string;
  descripcion: string;
  disponible: boolean;
  motivo_no_disponible: string | null;
  requisito_habilitante: string | null;
  total: number;
  pendientes: number;
};

type Sujeto = {
  etiqueta: string;
  valor: string;
};

type Revision = {
  resultado: "SIN_OBSERVACION" | "REQUIERE_SEGUIMIENTO";
  resultado_etiqueta: string;
  observacion: string;
  revisada_por: string | null;
  revisada_en: string;
};

type Alerta = {
  clave: string;
  tipo: string;
  tipo_etiqueta: string;
  fecha: string;
  titulo: string;
  detalle: string;
  sujetos: Sujeto[];
  estado: "PENDIENTE" | "REVISADA";
  vigente: boolean;
  es_sujeto: boolean;
  revision: Revision | null;
};

type Alertas = {
  aviso: string;
  tipos: TipoAlerta[];
  alertas: Alerta[];
};

type RevisionBody = {
  clave: string;
  resultado: "SIN_OBSERVACION" | "REQUIERE_SEGUIMIENTO";
  observacion: string;
};

export function AlertasAtipicasPage() {
  const { tiene } = useAutoridad();
  const { activeCompanyId } = useCompany();
  const { notify } = useNotifications();
  const queryClient = useQueryClient();

  const puedeVer = tiene("gobierno_alertas:view", "empresa");
  const puedeRevisar = tiene("gobierno_alertas:review", "empresa");

  const [tipoFiltro, setTipoFiltro] = useState("");
  const [estadoFiltro, setEstadoFiltro] = useState("");
  const [abierta, setAbierta] = useState<string | null>(null);
  const [resultado, setResultado] = useState<"SIN_OBSERVACION" | "REQUIERE_SEGUIMIENTO" | null>(null);
  const [observacion, setObservacion] = useState("");
  const [enviando, setEnviando] = useState(false);
  const [erroresCampo, setErroresCampo] = useState<Record<string, string[]>>({});
  const [errorGeneral, setErrorGeneral] = useState<string | null>(null);

  const alertasQuery = useQuery({
    queryKey: [...CONSULTA_GOBIERNO, "control", "alertas", activeCompanyId],
    queryFn: () => apiFetch<Alertas>("/gobierno/control/alertas"),
    enabled: puedeVer && Boolean(activeCompanyId),
    retry: false,
  });

  if (!puedeVer) {
    return (
      <PageContent>
        <EmptyState title="Sin acceso" description="No tiene permiso para ver esta información" />
      </PageContent>
    );
  }

  if (!activeCompanyId) {
    return (
      <PageContent>
        <EmptyState title="Sin empresa" description="Selecciona una empresa para continuar." />
      </PageContent>
    );
  }

  const pageHeader = (
    <PageHeader
      crumbs={[{ label: "Gobierno" }, { label: "Alertas de operaciones atípicas" }]}
      title="Alertas de operaciones atípicas"
      description="Señales sobre operaciones reales del ente para que Control Interno las revise."
    />
  );

  if (alertasQuery.isLoading) {
    return (
      <PageContent>
        {pageHeader}
        <LoadingState />
      </PageContent>
    );
  }

  if (alertasQuery.isError) {
    const error = alertasQuery.error as { status?: number };
    const mensaje =
      error?.status === 403
        ? "No tiene permiso para ver esta información"
        : "No se pudieron cargar las alertas.";
    return (
      <PageContent>
        {pageHeader}
        <ErrorDeCarga message={mensaje} onRetry={() => alertasQuery.refetch()} />
      </PageContent>
    );
  }

  const datos = alertasQuery.data as Alertas;

  const alertasFiltradas = datos.alertas.filter((alerta) => {
    if (tipoFiltro && alerta.tipo !== tipoFiltro) return false;
    if (estadoFiltro && alerta.estado !== estadoFiltro) return false;
    return true;
  });

  const observacionRecortada = observacion.trim();
  const formularioValido = resultado !== null && observacionRecortada.length >= 10;

  const abrirFormulario = (alerta: Alerta) => {
    setAbierta(alerta.clave);
    setResultado(null);
    setObservacion("");
    setErroresCampo({});
    setErrorGeneral(null);
  };

  const cerrarFormulario = () => {
    setAbierta(null);
    setResultado(null);
    setObservacion("");
    setErroresCampo({});
    setErrorGeneral(null);
    setEnviando(false);
  };

  const enviarRevision = async (alerta: Alerta) => {
    if (!formularioValido || enviando) return;

    setEnviando(true);
    setErroresCampo({});
    setErrorGeneral(null);

    const body: RevisionBody = {
      clave: alerta.clave,
      resultado: resultado as "SIN_OBSERVACION" | "REQUIERE_SEGUIMIENTO",
      observacion: observacionRecortada,
    };

    try {
      await apiFetch<Alerta>("/gobierno/control/alertas/revisiones", {
        method: "POST",
        body,
      });
      notify({ type: "success", title: "Revisión registrada" });
      cerrarFormulario();
      await queryClient.invalidateQueries({
        queryKey: [...CONSULTA_GOBIERNO, "control", "alertas"],
      });
    } catch (e) {
      if (e instanceof ApiError) {
        if (e.status === 422) {
          if (e.fieldErrors && Object.keys(e.fieldErrors).length > 0) {
            setErroresCampo(e.fieldErrors);
          } else {
            setErrorGeneral(e.message || "No se pudo registrar la revisión.");
          }
        } else if (e.status === 409 || e.status === 404 || e.status === 403) {
          setErrorGeneral(e.message);
          await queryClient.invalidateQueries({
            queryKey: [...CONSULTA_GOBIERNO, "control", "alertas"],
          });
        } else {
          setErrorGeneral("No se pudo registrar la revisión.");
        }
      } else {
        setErrorGeneral("No se pudo registrar la revisión.");
      }
    } finally {
      setEnviando(false);
    }
  };

  return (
    <PageContent>
      {pageHeader}

      <p role="note" className="mb-8 text-text-600">
        {datos.aviso}
      </p>

      <section aria-labelledby="sec-tipos-alerta" className="mb-8">
        <h2 id="sec-tipos-alerta" className="mb-4 text-lg font-semibold text-text-900">
          Tipos de alerta
        </h2>
        <div className="overflow-x-auto" tabIndex={0} role="region" aria-label="Tipos de alerta">
          <table aria-label="Tipos de alerta" className="w-full border-collapse text-left">
            <thead>
              <tr className="border-b border-border-subtle">
                <th className="py-2 pr-4 font-semibold text-text-900">Tipo</th>
                <th className="py-2 pr-4 font-semibold text-text-900">Detección</th>
                <th className="py-2 pr-4 font-semibold text-text-900">Pendientes</th>
                <th className="py-2 font-semibold text-text-900">Total</th>
              </tr>
            </thead>
            <tbody>
              {datos.tipos.map((tipo) => (
                <tr key={tipo.codigo} className="border-b border-border-subtle align-top">
                  <td className="py-3 pr-4">
                    <p className="font-semibold text-text-900">{tipo.etiqueta}</p>
                    <p className="text-sm text-text-600">{tipo.descripcion}</p>
                  </td>
                  <td className="py-3 pr-4">
                    {tipo.disponible ? (
                      <p className="text-text-900">Disponible</p>
                    ) : (
                      <div>
                        <p className="text-text-900">No disponible</p>
                        {tipo.motivo_no_disponible && (
                          <p className="text-sm text-text-600">{tipo.motivo_no_disponible}</p>
                        )}
                        {tipo.requisito_habilitante && (
                          <p className="text-sm text-text-600">
                            Requiere: {tipo.requisito_habilitante}
                          </p>
                        )}
                      </div>
                    )}
                  </td>
                  <td className="py-3 pr-4 text-text-900">{tipo.pendientes}</td>
                  <td className="py-3 text-text-900">{tipo.total}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <div className="mb-8 flex flex-wrap gap-4">
        <div>
          <label htmlFor="filtro-tipo" className="mb-1 block text-sm font-medium text-text-900">
            Tipo
          </label>
          <select
            id="filtro-tipo"
            value={tipoFiltro}
            onChange={(e) => setTipoFiltro(e.target.value)}
            className="rounded-lg border border-border-subtle bg-white p-2 text-text-900"
          >
            <option value="">Todos</option>
            {datos.tipos
              .filter((tipo) => tipo.disponible)
              .map((tipo) => (
                <option key={tipo.codigo} value={tipo.codigo}>
                  {tipo.etiqueta}
                </option>
              ))}
          </select>
        </div>
        <div>
          <label htmlFor="filtro-estado" className="mb-1 block text-sm font-medium text-text-900">
            Estado
          </label>
          <select
            id="filtro-estado"
            value={estadoFiltro}
            onChange={(e) => setEstadoFiltro(e.target.value)}
            className="rounded-lg border border-border-subtle bg-white p-2 text-text-900"
          >
            <option value="">Todas</option>
            <option value="PENDIENTE">Pendientes</option>
            <option value="REVISADA">Revisadas</option>
          </select>
        </div>
      </div>

      <section aria-labelledby="sec-alertas" className="mb-8">
        <h2 id="sec-alertas" className="mb-4 text-lg font-semibold text-text-900">
          Alertas
        </h2>
        {alertasFiltradas.length === 0 ? (
          <EmptyState
            title="Sin alertas"
            description="No hay alertas con los filtros aplicados."
          />
        ) : (
          <ul aria-label="Alertas" className="space-y-4">
            {alertasFiltradas.map((alerta) => (
              <li
                key={alerta.clave}
                className="rounded-lg border border-border-subtle p-4 break-words"
              >
                <div className="mb-2 flex flex-wrap items-center gap-2">
                  <span className="text-text-900">
                    {alerta.tipo_etiqueta} · {formatearFecha(alerta.fecha)}
                  </span>
                  <span
                    className={
                      alerta.estado === "PENDIENTE"
                        ? "rounded-full bg-amber-100 px-2 py-1 text-xs font-medium text-amber-800"
                        : "rounded-full bg-green-100 px-2 py-1 text-xs font-medium text-green-800"
                    }
                  >
                    {alerta.estado === "PENDIENTE" ? "Pendiente" : "Revisada"}
                  </span>
                </div>

                <h3 className="mb-1 text-base font-semibold text-text-900">{alerta.titulo}</h3>
                <p className="mb-3 text-text-600">{alerta.detalle}</p>

                <dl className="mb-3">
                  {alerta.sujetos.map((sujeto) => (
                    <div key={`${sujeto.etiqueta}-${sujeto.valor}`} className="mb-1">
                      <dt className="inline font-medium text-text-900">{sujeto.etiqueta}: </dt>
                      <dd className="inline text-text-600">{sujeto.valor}</dd>
                    </div>
                  ))}
                </dl>

                {alerta.revision && (
                  <div className="mb-3">
                    <p className="text-text-900">
                      Revisada por {alerta.revision.revisada_por ?? "usuario no identificado"} el{" "}
                      {formatearFecha(alerta.revision.revisada_en)}:{" "}
                      {alerta.revision.resultado_etiqueta}.
                    </p>
                    <p className="text-text-600">{alerta.revision.observacion}</p>
                    {!alerta.vigente && <p className="text-text-600">Ya no se detecta.</p>}
                    {alerta.revision.resultado === "REQUIERE_SEGUIMIENTO" && (
                      <Link to="/gobierno/hallazgos/nuevo" className="text-blue-600 hover:underline">
                        Registrar hallazgo
                      </Link>
                    )}
                  </div>
                )}

                {alerta.estado === "PENDIENTE" && puedeRevisar && (
                  <div className="mt-3">
                    {alerta.es_sujeto ? (
                      <p className="text-text-600">
                        No puede revisar esta alerta porque es sujeto de ella.
                      </p>
                    ) : abierta === alerta.clave ? (
                      <form
                        aria-label={`Revisión de ${alerta.titulo}`}
                        className="mt-3 rounded-lg border border-border-subtle p-4"
                        onSubmit={(e) => {
                          e.preventDefault();
                          enviarRevision(alerta);
                        }}
                      >
                        <fieldset className="mb-3">
                          <legend className="mb-2 font-medium text-text-900">Resultado</legend>
                          <div className="flex flex-wrap gap-4">
                            <label className="flex items-center gap-2 text-text-900">
                              <input
                                type="radio"
                                name={`resultado-${alerta.clave}`}
                                value="SIN_OBSERVACION"
                                checked={resultado === "SIN_OBSERVACION"}
                                onChange={() => setResultado("SIN_OBSERVACION")}
                              />
                              Sin observación
                            </label>
                            <label className="flex items-center gap-2 text-text-900">
                              <input
                                type="radio"
                                name={`resultado-${alerta.clave}`}
                                value="REQUIERE_SEGUIMIENTO"
                                checked={resultado === "REQUIERE_SEGUIMIENTO"}
                                onChange={() => setResultado("REQUIERE_SEGUIMIENTO")}
                              />
                              Requiere seguimiento
                            </label>
                          </div>
                        </fieldset>

                        <div className="mb-3">
                          <label
                            htmlFor={`observacion-${alerta.clave}`}
                            className="mb-1 block text-sm font-medium text-text-900"
                          >
                            Observación
                          </label>
                          <textarea
                            id={`observacion-${alerta.clave}`}
                            value={observacion}
                            onChange={(e) => setObservacion(e.target.value)}
                            className="w-full rounded-lg border border-border-subtle p-2 text-text-900"
                            rows={3}
                            maxLength={2000}
                          />
                          <p className="mt-1 text-xs text-text-600">{observacion.length}/2000</p>
                          {erroresCampo.observacion && (
                            <p role="alert" className="mt-1 text-sm text-red-600">
                              {erroresCampo.observacion[0]}
                            </p>
                          )}
                        </div>

                        {erroresCampo.resultado && (
                          <p role="alert" className="mb-3 text-sm text-red-600">
                            {erroresCampo.resultado[0]}
                          </p>
                        )}

                        {errorGeneral && (
                          <p role="alert" className="mb-3 text-sm text-red-600">
                            {errorGeneral}
                          </p>
                        )}

                        <div className="flex flex-wrap gap-3">
                          <Button
                            type="submit"
                            variant="primary"
                            disabled={enviando || !formularioValido}
                          >
                            Registrar revisión
                          </Button>
                          <Button
                            type="button"
                            variant="secondary"
                            onClick={cerrarFormulario}
                            disabled={enviando}
                          >
                            Cancelar
                          </Button>
                        </div>
                      </form>
                    ) : (
                      <Button variant="secondary" onClick={() => abrirFormulario(alerta)}>
                        Revisar
                      </Button>
                    )}
                  </div>
                )}
              </li>
            ))}
          </ul>
        )}
      </section>
    </PageContent>
  );
}
