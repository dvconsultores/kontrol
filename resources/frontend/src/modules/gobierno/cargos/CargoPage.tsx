import { useMemo, useState } from "react";
import { Link, useNavigate, useParams } from "react-router";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Pencil, Plus, Trash2 } from "lucide-react";

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
import { formatearFechaDeNegocio } from "@/lib/fecha-de-negocio";
import {
  CONSULTA_CARGOS,
  CONSULTA_ESTRUCTURAS,
  Cargo,
  Competencia,
  Estructura,
  ETIQUETA_ACCION,
  ETIQUETA_ESTADO_CARGO,
  ETIQUETA_MATERIA,
  ETIQUETA_FALTANTE_CARGO,
  VersionesCargo,
  VersionCargo,
  describirLimite,
} from "@/modules/gobierno/api";

import { CargoFormulario, CambiosCargo } from "./CargoFormulario";
import { CompetenciaFormulario, DatosCompetencia } from "./CompetenciaFormulario";
import { DesactivarCargo } from "./DesactivarCargo";
import { RetirarCompetencia } from "./RetirarCompetencia";

type Panel =
  | { tipo: "ninguno" }
  | { tipo: "editar" }
  | { tipo: "agregar" }
  | { tipo: "cambiar"; competencia: Competencia }
  | { tipo: "retirar"; competencia: Competencia }
  | { tipo: "desactivar" };

type Confirmacion = null | "activar" | "eliminar";

export function CargoPage(): React.JSX.Element {
  const { ejercicio: ejercicioParam, cargoId } = useParams();
  const ejercicio = Number(ejercicioParam);
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
    void queryClient.invalidateQueries({ queryKey: [...CONSULTA_CARGOS] });
  };

  const consultaCargo = useQuery({
    queryKey: [...CONSULTA_CARGOS, activeCompanyId, ejercicio, cargoId],
    queryFn: () => apiFetch<Cargo>(`/gobierno/estructuras/${ejercicio}/cargos/${cargoId}`),
    enabled: Boolean(activeCompanyId) && Number.isInteger(ejercicio) && Boolean(cargoId),
    retry: false,
  });

  const consultaEstructura = useQuery({
    queryKey: [...CONSULTA_ESTRUCTURAS, activeCompanyId, ejercicio],
    queryFn: () => apiFetch<Estructura>(`/gobierno/estructuras/${ejercicio}`),
    enabled: Boolean(activeCompanyId) && Number.isInteger(ejercicio),
    retry: false,
  });

  const consultaVersiones = useQuery({
    queryKey: [...CONSULTA_CARGOS, activeCompanyId, ejercicio, cargoId, "versiones"],
    queryFn: () => apiFetch<VersionesCargo>(`/gobierno/estructuras/${ejercicio}/cargos/${cargoId}/versiones`),
    enabled: Boolean(activeCompanyId) && Number.isInteger(ejercicio) && Boolean(cargoId),
    retry: false,
  });

  const versionesOrdenadas = useMemo(() => {
    return [...(consultaVersiones.data?.items ?? [])].sort((a, b) => b.version - a.version);
  }, [consultaVersiones.data]);

  const manejarError = (e: unknown) => {
    if (e instanceof ApiError) {
      if (e.status === 409 && e.code === "GOV_POSITION_STALE") {
        setConflicto(true);
        recargar();
        return;
      }
      if (e.status === 422 && e.code === "VALIDATION_ERROR") {
        setErroresServidor(e.fieldErrors);
        return;
      }
      if (e.status === 409 && e.code === "GOV_POSITION_CODE_DUPLICATE") {
        setErroresServidor({ codigo: [e.message] });
        return;
      }
      if (e.status === 422 && e.code === "GOV_POSITION_INVALID_UNIT") {
        setErroresServidor({ unidad_id: [e.message] });
        return;
      }
      if (e.status === 409 && e.code === "GOV_COMPETENCY_DUPLICATE") {
        setErroresServidor({ materia: [e.message] });
        return;
      }
      if (e.status === 422 && e.code === "GOV_POSITION_REASON_REQUIRED") {
        setErroresServidor({ motivo: [e.message] });
        return;
      }
      if (e.status === 422 && e.code === "GOV_POSITION_INCOMPLETE") {
        const lista: unknown = e.details?.faltantes;
        const faltantes = Array.isArray(lista)
          ? lista.map((c) => ETIQUETA_FALTANTE_CARGO[String(c)] ?? String(c)).join(", ")
          : "";
        notify({ type: "error", title: "No se puede poner en vigor", description: faltantes });
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

  if (consultaCargo.isLoading || consultaEstructura.isLoading || consultaVersiones.isLoading) {
    return (
      <PageContent>
        <LoadingState label="Cargando cargo…" />
      </PageContent>
    );
  }

  if (consultaCargo.isError) {
    const error = consultaCargo.error;
    if (error instanceof ApiError && error.status === 403 && error.code === "MODULE_NOT_ENTITLED") {
      return (
        <PageContent>
          <EmptyState
            title="Módulo no disponible"
            description="Su empresa no tiene contratado el módulo de Gobierno."
            action={<Link to="/gobierno/cargos">Volver a Cargos y competencias</Link>}
          />
        </PageContent>
      );
    }
    if (error instanceof ApiError && error.status === 403) {
      return (
        <PageContent>
          <EmptyState title="Sin acceso" description="No tiene permiso para ver este cargo." />
        </PageContent>
      );
    }
    if (error instanceof ApiError && error.status === 404 && error.code === "GOV_POSITION_NOT_FOUND") {
      return (
        <PageContent>
          <EmptyState
            title="El cargo no existe en este ejercicio"
            action={<Link to={`/gobierno/cargos/${ejercicio}`}>Volver a los cargos</Link>}
          />
        </PageContent>
      );
    }
    return (
      <PageContent>
        <ErrorState message="No fue posible cargar el cargo." onRetry={() => void consultaCargo.refetch()} />
      </PageContent>
    );
  }

  if (consultaEstructura.isError) {
    const error = consultaEstructura.error;
    if (error instanceof ApiError && error.status === 403 && error.code === "MODULE_NOT_ENTITLED") {
      return (
        <PageContent>
          <EmptyState
            title="Módulo no disponible"
            description="Su empresa no tiene contratado el módulo de Gobierno."
            action={<Link to="/gobierno/cargos">Volver a Cargos y competencias</Link>}
          />
        </PageContent>
      );
    }
    if (error instanceof ApiError && error.status === 403) {
      return (
        <PageContent>
          <EmptyState title="Sin acceso" description="No tiene permiso para ver esta estructura." />
        </PageContent>
      );
    }
    if (error instanceof ApiError && error.status === 404 && error.code === "GOV_STRUCTURE_NOT_FOUND") {
      return (
        <PageContent>
          <EmptyState
            title={`No hay estructura para el ejercicio ${ejercicio}`}
            action={<Link to="/gobierno/estructura">Volver a Estructura organizativa</Link>}
          />
        </PageContent>
      );
    }
    return (
      <PageContent>
        <ErrorState message="No fue posible cargar la estructura." onRetry={() => void consultaEstructura.refetch()} />
      </PageContent>
    );
  }

  if (consultaVersiones.isError) {
    const error = consultaVersiones.error;
    if (error instanceof ApiError && error.status === 403 && error.code === "MODULE_NOT_ENTITLED") {
      return (
        <PageContent>
          <EmptyState
            title="Módulo no disponible"
            description="Su empresa no tiene contratado el módulo de Gobierno."
            action={<Link to="/gobierno/cargos">Volver a Cargos y competencias</Link>}
          />
        </PageContent>
      );
    }
    if (error instanceof ApiError && error.status === 403) {
      return (
        <PageContent>
          <EmptyState title="Sin acceso" description="No tiene permiso para ver el historial del cargo." />
        </PageContent>
      );
    }
    return (
      <PageContent>
        <ErrorState message="No fue posible cargar el historial." onRetry={() => void consultaVersiones.refetch()} />
      </PageContent>
    );
  }

  const cargo = consultaCargo.data;
  const estructura = consultaEstructura.data;
  const versiones = consultaVersiones.data;

  if (!cargo || !estructura || !versiones) {
    return (
      <PageContent>
        <ErrorState
          message="No fue posible cargar el cargo."
          onRetry={() => void consultaCargo.refetch()}
        />
      </PageContent>
    );
  }

  const cerrada = estructura.estado === "CERRADA";
  const puedeEditar =
    tiene("gobierno_cargos:edit", "empresa") && !cerrada && cargo.estado !== "INACTIVO";
  const puedePublicar = tiene("gobierno_cargos:publish", "empresa") && !cerrada;
  const puedeCambiarCompetencias =
    puedeEditar && (cargo.estado === "BORRADOR" || puedePublicar);

  const crumbs = [
    { label: "Gobierno" },
    { label: "Cargos y competencias", to: "/gobierno/cargos" },
    { label: String(ejercicio), to: `/gobierno/cargos/${ejercicio}` },
    { label: cargo.codigo },
  ];

  const hayFaltantes = cargo.faltantes_para_activar.length > 0;

  const accionesCabecera = (
    <div className="flex flex-wrap items-center gap-2">
      {puedeEditar && (
        <Button variant="secondary" onClick={() => setPanel({ tipo: "editar" })}>
          <Pencil className="mr-2 h-4 w-4" aria-hidden="true" />
          Editar
        </Button>
      )}
      {puedePublicar && cargo.estado === "BORRADOR" && (
        <Button
          variant="primary"
          disabled={hayFaltantes}
          aria-describedby="requisitos-activar"
          onClick={() => setConfirmar("activar")}
        >
          Poner en vigor
        </Button>
      )}
      {puedePublicar && cargo.estado === "VIGENTE" && (
        <Button variant="secondary" onClick={() => setPanel({ tipo: "desactivar" })}>
          Desactivar
        </Button>
      )}
      {puedeEditar && cargo.estado === "BORRADOR" && (
        <Button variant="secondary" onClick={() => setConfirmar("eliminar")}>
          <Trash2 className="mr-2 h-4 w-4" aria-hidden="true" />
          Eliminar
        </Button>
      )}
    </div>
  );

  const guardarCargo = async (cambios: CambiosCargo, motivo: string | null) => {
    try {
      await apiFetch<Cargo>(`/gobierno/estructuras/${ejercicio}/cargos/${cargo.id}`, {
        method: "PATCH",
        body: { ...cambios, ...(motivo ? { motivo } : {}) },
        ifMatch: String(cargo.version),
      });
      notify({ type: "success", title: "Cargo actualizado" });
      setPanel({ tipo: "ninguno" });
      setErroresServidor({});
      recargar();
    } catch (e) {
      manejarError(e);
    }
  };

  const guardarCompetencia = async (datos: DatosCompetencia, motivo: string | null) => {
    try {
      if (panel.tipo === "agregar") {
        await apiFetch<Competencia>(`/gobierno/estructuras/${ejercicio}/cargos/${cargo.id}/competencias`, {
          method: "POST",
          body: { ...datos, ...(motivo ? { motivo } : {}) },
          ifMatch: String(cargo.version),
        });
        notify({ type: "success", title: "Competencia agregada" });
      } else if (panel.tipo === "cambiar") {
        await apiFetch<Competencia>(
          `/gobierno/estructuras/${ejercicio}/cargos/${cargo.id}/competencias/${panel.competencia.id}`,
          {
            method: "PATCH",
            body: {
              tipo_limite: datos.tipo_limite,
              monto: datos.monto,
              moneda: datos.moneda,
              fundamento: datos.fundamento,
              ...(motivo ? { motivo } : {}),
            },
            ifMatch: String(cargo.version),
          },
        );
        notify({ type: "success", title: "Límite actualizado" });
      }
      setPanel({ tipo: "ninguno" });
      setErroresServidor({});
      recargar();
    } catch (e) {
      manejarError(e);
    }
  };

  const retirarCompetencia = async (motivo: string | null) => {
    if (panel.tipo !== "retirar") return;
    try {
      await apiFetch<void>(
        `/gobierno/estructuras/${ejercicio}/cargos/${cargo.id}/competencias/${panel.competencia.id}/retirar`,
        {
          method: "POST",
          body: motivo ? { motivo } : {},
          ifMatch: String(cargo.version),
        },
      );
      notify({ type: "success", title: "Competencia retirada" });
      setPanel({ tipo: "ninguno" });
      setErroresServidor({});
      recargar();
    } catch (e) {
      manejarError(e);
    }
  };

  const desactivarCargo = async (fecha: string, motivo: string) => {
    try {
      await apiFetch<Cargo>(`/gobierno/estructuras/${ejercicio}/cargos/${cargo.id}/desactivar`, {
        method: "POST",
        body: { fecha, motivo },
        ifMatch: String(cargo.version),
      });
      notify({ type: "success", title: "Cargo desactivado" });
      setPanel({ tipo: "ninguno" });
      setErroresServidor({});
      recargar();
    } catch (e) {
      manejarError(e);
    }
  };

  const activarCargo = async () => {
    try {
      await apiFetch<Cargo>(`/gobierno/estructuras/${ejercicio}/cargos/${cargo.id}/activar`, {
        method: "POST",
        ifMatch: String(cargo.version),
      });
      notify({ type: "success", title: "Cargo en vigor" });
      setPanel({ tipo: "ninguno" });
      setErroresServidor({});
      recargar();
    } catch (e) {
      manejarError(e);
    } finally {
      setConfirmar(null);
    }
  };

  const eliminarCargo = async () => {
    try {
      await apiFetch<void>(`/gobierno/estructuras/${ejercicio}/cargos/${cargo.id}`, {
        method: "DELETE",
        ifMatch: String(cargo.version),
      });
      notify({ type: "success", title: "Cargo eliminado" });
      setPanel({ tipo: "ninguno" });
      setErroresServidor({});
      recargar();
      queryClient.invalidateQueries({ queryKey: [...CONSULTA_CARGOS, activeCompanyId, ejercicio] });
      navigate(`/gobierno/cargos/${ejercicio}`);
    } catch (e) {
      if (e instanceof ApiError && e.status === 409 && e.code === "GOV_POSITION_HAS_DOCUMENTS") {
        notify({ type: "warning", title: e.message });
        setConfirmar(null);
        return;
      }
      manejarError(e);
    } finally {
      setConfirmar(null);
    }
  };


  const unidades = estructura.unidades;

  return (
    <PageContent>
      <PageHeader
        crumbs={crumbs}
        title={`${cargo.codigo} — ${cargo.denominacion}`}
        description={`Unidad ${cargo.unidad_codigo} — ${cargo.unidad_denominacion}`}
        status={
          <span className="inline-flex items-center rounded-full bg-surface-100 px-3 py-1 text-sm font-medium text-text-700">
            {ETIQUETA_ESTADO_CARGO[cargo.estado]}
          </span>
        }
        actions={accionesCabecera}
      />

      {conflicto ? (
        <ConflictState
          message="Otra persona cambió el cargo mientras trabajaba. Se cargó la versión vigente."
          onReload={() => {
            setConflicto(false);
            setPanel({ tipo: "ninguno" });
          }}
        />
      ) : (
        <>
          {cerrada && (
            <p role="status" className="mb-4 rounded-md bg-surface-100 px-4 py-3 text-sm text-text-700">
              Ejercicio cerrado: el cargo es de solo lectura.
            </p>
          )}

          {cargo.estado === "INACTIVO" && (
            <p role="status" className="mb-4 rounded-md bg-surface-100 px-4 py-3 text-sm text-text-700">
              Cargo inactivo: su vigencia terminó el {formatearFechaDeNegocio(cargo.vigente_hasta ?? cargo.vigente_desde)}; no tiene autoridad.
            </p>
          )}

          {cargo.estado === "BORRADOR" && (
            <section id="requisitos-activar" aria-labelledby="requisitos-activar-titulo" className="mb-8">
              <h2 id="requisitos-activar-titulo" className="mb-2 text-lg font-semibold text-text-900">
                Requisitos para poner en vigor
              </h2>
              {hayFaltantes ? (
                <>
                  <p className="text-sm text-text-700">Para poner en vigor falta:</p>
                  <ul className="mt-2 list-disc pl-6 text-sm text-text-700">
                    {cargo.faltantes_para_activar.map((c) => (
                      <li key={c}>{ETIQUETA_FALTANTE_CARGO[c] ?? c}</li>
                    ))}
                  </ul>
                </>
              ) : (
                <p role="status" className="text-sm text-text-700">
                  El cargo está completo y puede ponerse en vigor.
                </p>
              )}
            </section>
          )}

          <section aria-labelledby="datos-cargo-titulo" className="mb-8">
            <h2 id="datos-cargo-titulo" className="mb-4 text-lg font-semibold text-text-900">
              Datos del cargo
            </h2>
            <dl className="grid gap-x-8 gap-y-4 text-sm sm:grid-cols-2">
              <div>
                <dt className="font-medium text-text-600">Código</dt>
                <dd className="mt-1 font-mono text-text-900">{cargo.codigo}</dd>
              </div>
              <div>
                <dt className="font-medium text-text-600">Denominación</dt>
                <dd className="mt-1 text-text-900">{cargo.denominacion}</dd>
              </div>
              <div>
                <dt className="font-medium text-text-600">Unidad</dt>
                <dd className="mt-1 text-text-900">
                  {cargo.unidad_codigo} — {cargo.unidad_denominacion}
                </dd>
              </div>
              <div>
                <dt className="font-medium text-text-600">Vigencia</dt>
                <dd className="mt-1 text-text-900">
                  {formatearFechaDeNegocio(cargo.vigente_desde)} –{" "}
                  {cargo.vigente_hasta ? formatearFechaDeNegocio(cargo.vigente_hasta) : "—"}
                </dd>
              </div>
              <div>
                <dt className="font-medium text-text-600">Puesto en vigor</dt>
                <dd className="mt-1 text-text-900">
                  {cargo.activado_en ? formatearFecha(cargo.activado_en) : "—"}
                </dd>
              </div>
            </dl>
          </section>

          <section aria-labelledby="competencias-titulo" className="mb-8">
            <div className="mb-4 flex items-center justify-between">
              <h2 id="competencias-titulo" className="text-lg font-semibold text-text-900">
                Competencias y límites
              </h2>
              {puedeCambiarCompetencias && (
                <Button variant="primary" onClick={() => setPanel({ tipo: "agregar" })}>
                  <Plus className="mr-2 h-4 w-4" aria-hidden="true" />
                  Agregar competencia
                </Button>
              )}
            </div>

            {cargo.estado === "VIGENTE" && puedeEditar && !puedePublicar && (
              <p className="mb-3 text-sm text-text-600">
                Solo quien puede poner cargos en vigor cambia sus competencias.
              </p>
            )}

            {cargo.competencias.length === 0 ? (
              <p className="text-sm text-text-600">Este cargo aún no tiene competencias.</p>
            ) : (
              <div className="relative overflow-x-auto" tabIndex={0} role="region" aria-label={`Competencias del cargo ${cargo.codigo}`}>
                <table className="w-full min-w-[720px] border-collapse text-sm">
                  <caption className="sr-only">Competencias del cargo {cargo.codigo}</caption>
                  <thead>
                    <tr className="border-b border-border-default text-left text-text-600">
                      <th scope="col" className="px-3 py-2 font-medium">
                        Acción
                      </th>
                      <th scope="col" className="px-3 py-2 font-medium">
                        Materia
                      </th>
                      <th scope="col" className="px-3 py-2 font-medium">
                        Límite
                      </th>
                      <th scope="col" className="px-3 py-2 font-medium">
                        Fundamento
                      </th>
                      {puedeCambiarCompetencias && (
                        <th scope="col" className="px-3 py-2 font-medium">
                          Acciones
                        </th>
                      )}
                    </tr>
                  </thead>
                  <tbody>
                    {cargo.competencias.map((competencia) => (
                      <tr key={competencia.id} className="border-b border-border-subtle align-top">
                        <td className="px-3 py-2 text-text-900">{ETIQUETA_ACCION[competencia.accion]}</td>
                        <td className="px-3 py-2 text-text-900">{ETIQUETA_MATERIA[competencia.materia]}</td>
                        <td className="px-3 py-2 text-text-700">{describirLimite(competencia)}</td>
                        <td className="px-3 py-2 text-text-700">{competencia.fundamento ?? "—"}</td>
                        {puedeCambiarCompetencias && (
                          <td className="px-3 py-2">
                            <div className="flex flex-wrap gap-1">
                              <Button
                                variant="ghost"
                                size="sm"
                                aria-label={`Cambiar el límite de ${ETIQUETA_ACCION[competencia.accion]} · ${ETIQUETA_MATERIA[competencia.materia]}`}
                                onClick={() => setPanel({ tipo: "cambiar", competencia })}
                              >
                                Cambiar límite
                              </Button>
                              <Button
                                variant="ghost"
                                size="sm"
                                aria-label={`Retirar ${ETIQUETA_ACCION[competencia.accion]} · ${ETIQUETA_MATERIA[competencia.materia]}`}
                                onClick={() => setPanel({ tipo: "retirar", competencia })}
                              >
                                Retirar
                              </Button>
                            </div>
                          </td>
                        )}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            {panel.tipo === "editar" && (
              <div className="mt-6">
                <CargoFormulario
                  key={`editar-${cargo.id}`}
                  modo="editar"
                  ejercicio={ejercicio}
                  unidades={unidades}
                  cargo={cargo}
                  onGuardar={guardarCargo}
                  onCancelar={() => setPanel({ tipo: "ninguno" })}
                  erroresServidor={erroresServidor}
                />
              </div>
            )}
            {panel.tipo === "agregar" && (
              <div className="mt-6">
                <CompetenciaFormulario
                  key={`agregar-${cargo.id}`}
                  modo="agregar"
                  cargoCodigo={cargo.codigo}
                  cargoVigente={cargo.estado === "VIGENTE"}
                  competenciasExistentes={cargo.competencias}
                  onGuardar={guardarCompetencia}
                  onCancelar={() => setPanel({ tipo: "ninguno" })}
                  erroresServidor={erroresServidor}
                />
              </div>
            )}
            {panel.tipo === "cambiar" && (
              <div className="mt-6">
                <CompetenciaFormulario
                  key={`cambiar-${panel.competencia.id}`}
                  modo="cambiar"
                  cargoCodigo={cargo.codigo}
                  cargoVigente={cargo.estado === "VIGENTE"}
                  competencia={panel.competencia}
                  competenciasExistentes={cargo.competencias}
                  onGuardar={guardarCompetencia}
                  onCancelar={() => setPanel({ tipo: "ninguno" })}
                  erroresServidor={erroresServidor}
                />
              </div>
            )}
            {panel.tipo === "retirar" && (
              <div className="mt-6">
                <RetirarCompetencia
                  key={`retirar-${panel.competencia.id}`}
                  competencia={panel.competencia}
                  cargoVigente={cargo.estado === "VIGENTE"}
                  onConfirmar={retirarCompetencia}
                  onCancelar={() => setPanel({ tipo: "ninguno" })}
                  erroresServidor={erroresServidor}
                />
              </div>
            )}
            {panel.tipo === "desactivar" && (
              <div className="mt-6">
                <DesactivarCargo
                  key={`desactivar-${cargo.id}`}
                  cargo={cargo}
                  ejercicio={ejercicio}
                  onConfirmar={desactivarCargo}
                  onCancelar={() => setPanel({ tipo: "ninguno" })}
                  erroresServidor={erroresServidor}
                />
              </div>
            )}
          </section>

          <section aria-labelledby="acto-titulo" className="mb-8">
            <h2 id="acto-titulo" className="mb-4 text-lg font-semibold text-text-900">
              Acto del cargo
            </h2>
            <AdjuntosPanel
              resourceType="GovernmentPosition"
              resourceId={cargo.id}
              title="Acto del cargo"
              onChange={() => void recargar()}
            />
            {cargo.estado === "BORRADOR" && !cargo.documento_vinculado && (
              <p className="mt-2 text-sm text-text-600">
                Adjunte la resolución o el reglamento que fija sus competencias y límites para ponerlo en vigor.
              </p>
            )}
          </section>

          <section aria-labelledby="historial-titulo">
            <h2 id="historial-titulo" className="mb-4 text-lg font-semibold text-text-900">
              Historial
            </h2>
            <div className="relative overflow-x-auto" tabIndex={0} role="region" aria-label={`Historial del cargo ${cargo.codigo}`}>
              <table className="w-full min-w-[720px] border-collapse text-sm">
                <caption className="sr-only">Historial de versiones del cargo {cargo.codigo}</caption>
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
                    <th scope="col" className="px-3 py-2 font-medium">
                      Competencias
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {versionesOrdenadas.map((version: VersionCargo) => {
                    const competencias = Array.isArray(version.datos.competencias)
                      ? version.datos.competencias.length
                      : 0;
                    return (
                      <tr key={version.version} className="border-b border-border-subtle align-top">
                        <td className="px-3 py-2 font-mono text-text-900">{version.version}</td>
                        <td className="px-3 py-2 text-text-900">{ETIQUETA_ESTADO_CARGO[version.estado]}</td>
                        <td className="px-3 py-2 text-text-700">{formatearFecha(version.creado_en)}</td>
                        <td className="px-3 py-2 text-text-700">{version.motivo ?? "—"}</td>
                        <td className="px-3 py-2 text-text-700">{competencias}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </section>
        </>
      )}

      <ConfirmationDialog
        open={confirmar === "activar"}
        title={`Poner en vigor el cargo ${cargo.codigo}`}
        description="Desde ahora el cargo tendrá las competencias y límites registrados. Los cambios posteriores exigirán motivo."
        confirmLabel="Poner en vigor"
        onConfirm={activarCargo}
        onCancel={() => setConfirmar(null)}
      />
      <ConfirmationDialog
        open={confirmar === "eliminar"}
        title={`Eliminar el cargo ${cargo.codigo}`}
        description="Solo se eliminan cargos de un borrador."
        confirmLabel="Eliminar"
        danger
        onConfirm={eliminarCargo}
        onCancel={() => setConfirmar(null)}
      />
    </PageContent>
  );
}
