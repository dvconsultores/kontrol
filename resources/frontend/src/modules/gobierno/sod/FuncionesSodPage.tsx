import { useState } from "react";
import { Link } from "react-router";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch, ApiError } from "@/api/client";
import { descargarArchivo } from "@/api/descargas";
import { useAutoridad } from "@/app/autoridad/AutoridadContext";
import { useCompany } from "@/app/contexts/CompanyContext";
import { useNotifications } from "@/app/contexts/NotificationContext";
import { PageContent } from "@/layout/PageContent";
import { PageHeader } from "@/components/PageHeader";
import { EmptyState } from "@/components/EmptyState";
import { ErrorState } from "@/components/ErrorState";
import { LoadingState } from "@/components/LoadingState";
import { formatearFechaDeNegocio } from "@/lib/fecha-de-negocio";
import {
  CONSULTA_SOD_FUNCIONES,
  ETIQUETAS_ESTADO_REGLA_SOD,
  consultaDeConflictosFuncion,
} from "@/modules/gobierno/api";
import type {
  CatalogoFunciones,
  ConflictosFuncionListado,
  EstadoReglaFuncion,
  FuncionProcedimiento,
  ReglaFuncionDetalle,
  ReglasFuncionListado,
} from "@/modules/gobierno/api";

export function FuncionesSodPage() {
  const { tiene } = useAutoridad();
  const { activeCompanyId } = useCompany();
  const { notify } = useNotifications();
  const queryClient = useQueryClient();

  const [estado, setEstado] = useState<EstadoReglaFuncion | "">("");
  const [desde, setDesde] = useState("");
  const [hasta, setHasta] = useState("");
  const [rolConflictos, setRolConflictos] = useState<FuncionProcedimiento | "">("");
  const [formulario, setFormulario] = useState({
    nombre: "",
    descripcion: "",
    rol_a: "" as FuncionProcedimiento | "",
    rol_b: "" as FuncionProcedimiento | "",
    fundamento: "",
    vigente_desde: "",
    vigente_hasta: "",
  });
  const [cierre, setCierre] = useState<{ id: string; version: number } | null>(null);
  const [motivoCierre, setMotivoCierre] = useState("");

  const puedeVer = tiene("gobierno_sod:view", "empresa");
  const puedeGestionar = tiene("gobierno_sod:manage", "empresa");
  const puedeActivar = tiene("gobierno_sod:activate", "empresa");

  const catalogo = useQuery({
    queryKey: [...CONSULTA_SOD_FUNCIONES, "catalogo", activeCompanyId],
    queryFn: () => apiFetch<CatalogoFunciones>("/gobierno/sod/funciones"),
    enabled: puedeVer && Boolean(activeCompanyId),
    retry: false,
  });

  const reglas = useQuery({
    queryKey: [...CONSULTA_SOD_FUNCIONES, "reglas", activeCompanyId, estado],
    queryFn: () =>
      apiFetch<ReglasFuncionListado>(
        `/gobierno/sod/funciones/reglas${estado ? `?estado=${estado}` : ""}`,
      ),
    enabled: puedeVer && Boolean(activeCompanyId),
    retry: false,
  });

  const conflictos = useQuery({
    queryKey: [...CONSULTA_SOD_FUNCIONES, "conflictos", activeCompanyId, desde, hasta, rolConflictos],
    queryFn: () =>
      apiFetch<ConflictosFuncionListado>(
        `/gobierno/sod/funciones/conflictos${consultaDeConflictosFuncion({
          desde,
          hasta,
          rol: rolConflictos,
        })}`,
      ),
    enabled: puedeVer && Boolean(activeCompanyId),
    retry: false,
  });

  const refrescar = async () => {
    await queryClient.invalidateQueries({ queryKey: CONSULTA_SOD_FUNCIONES });
  };

  const crear = useMutation({
    mutationFn: () =>
      apiFetch<ReglaFuncionDetalle>("/gobierno/sod/funciones/reglas", {
        method: "POST",
        body: {
          nombre: formulario.nombre,
          descripcion: formulario.descripcion,
          rol_a: formulario.rol_a,
          rol_b: formulario.rol_b,
          fundamento: formulario.fundamento,
          vigente_desde: formulario.vigente_desde || undefined,
          vigente_hasta: formulario.vigente_hasta || null,
        },
      }),
    onSuccess: async (regla) => {
      notify({ type: "success", title: `Regla ${regla.codigo} registrada como borrador.` });
      setFormulario({ nombre: "", descripcion: "", rol_a: "", rol_b: "", fundamento: "", vigente_desde: "", vigente_hasta: "" });
      await refrescar();
    },
    onError: (error) => {
      notify({ type: "error", title: mensajeDeError(error) });
    },
  });

  const activar = useMutation({
    mutationFn: (regla: { id: string; version: number }) =>
      apiFetch<ReglaFuncionDetalle>(`/gobierno/sod/funciones/reglas/${regla.id}/activar`, {
        method: "POST",
        body: {},
        ifMatch: String(regla.version),
      }),
    onSuccess: async (regla) => {
      notify({ type: "success", title: `Regla ${regla.codigo} en vigor.` });
      await refrescar();
    },
    onError: (error) => notify({ type: "error", title: mensajeDeError(error) }),
  });

  const cerrar = useMutation({
    mutationFn: (datos: { id: string; version: number; motivo: string }) =>
      apiFetch<ReglaFuncionDetalle>(`/gobierno/sod/funciones/reglas/${datos.id}/cerrar`, {
        method: "POST",
        body: { motivo: datos.motivo },
        ifMatch: String(datos.version),
      }),
    onSuccess: async (regla) => {
      notify({ type: "success", title: `Regla ${regla.codigo} cerrada.` });
      setCierre(null);
      setMotivoCierre("");
      await refrescar();
    },
    onError: (error) => notify({ type: "error", title: mensajeDeError(error) }),
  });

  const exportarCsv = async () => {
    try {
      const nombre = await descargarArchivo(
        `/gobierno/sod/funciones/conflictos.csv${consultaDeConflictosFuncion({
          desde,
          hasta,
          rol: rolConflictos,
        })}`,
        "funciones-incompatibles",
      );
      notify({ type: "success", title: `Descargado ${nombre}` });
    } catch {
      notify({ type: "error", title: "No se pudo exportar el listado de conflictos" });
    }
  };

  const cabecera = (
    <PageHeader
      crumbs={[{ label: "Gobierno" }, { label: "Contrataciones" }]}
      title="Funciones incompatibles"
      description="Matriz institucional de funciones del procedimiento de contratación que no puede ejercer la misma persona, y los conflictos reales que existen en los expedientes."
      actions={
        <Link
          to="/gobierno/sod"
          className="inline-flex h-10 items-center rounded-md border border-border-default px-3 text-sm font-medium text-text-700 hover:bg-surface-100"
        >
          Reglas por acción
        </Link>
      }
    />
  );

  if (!puedeVer) {
    return (
      <PageContent>
        {cabecera}
        <EmptyState title="Sin acceso" description="No tiene permiso para ver las funciones incompatibles." />
      </PageContent>
    );
  }

  if (catalogo.isLoading || reglas.isLoading) {
    return (
      <PageContent>
        {cabecera}
        <LoadingState label="Cargando la matriz de funciones…" />
      </PageContent>
    );
  }

  if (catalogo.isError || reglas.isError) {
    const error = catalogo.error ?? reglas.error;
    if (error instanceof ApiError && error.status === 403 && error.code === "MODULE_NOT_ENTITLED") {
      return (
        <PageContent>
          {cabecera}
          <EmptyState
            title="Módulo no habilitado"
            description="El módulo de Gobierno no está habilitado en la licencia."
          />
        </PageContent>
      );
    }
    return (
      <PageContent>
        {cabecera}
        <ErrorState
          message="No fue posible cargar la matriz de funciones."
          onRetry={() => {
            void catalogo.refetch();
            void reglas.refetch();
          }}
        />
      </PageContent>
    );
  }

  const funciones = (catalogo.data?.funciones ?? []).filter((f) => f.disponible);
  const noDisponibles = (catalogo.data?.funciones ?? []).filter((f) => !f.disponible);
  const reglasVisibles = reglas.data?.items ?? [];
  const conflictosVisibles = conflictos.data?.items ?? [];
  const formularioCompleto =
    formulario.nombre.trim().length >= 3 &&
    formulario.descripcion.trim().length >= 10 &&
    formulario.fundamento.trim().length >= 10 &&
    Boolean(formulario.rol_a) &&
    Boolean(formulario.rol_b) &&
    formulario.rol_a !== formulario.rol_b;

  return (
    <PageContent>
      {cabecera}

      <section aria-labelledby="funciones-aviso" className="mb-8 rounded-md border border-border-subtle bg-surface-0 p-4">
        <h2 id="funciones-aviso" className="text-base font-semibold text-text-900">
          Qué funciones vigila la matriz
        </h2>
        <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-text-700">
          {funciones.map((funcion) => (
            <li key={funcion.codigo}>
              <span className="font-medium">{funcion.etiqueta}</span> — {funcion.fuente}
            </li>
          ))}
          {noDisponibles.map((funcion) => (
            <li key={funcion.codigo} className="text-text-600">
              <span className="font-medium">{funcion.etiqueta}</span>: no disponible. Requiere{" "}
              {funcion.requisito_habilitante}.
            </li>
          ))}
        </ul>
      </section>

      <section aria-labelledby="matriz-titulo" className="mb-8">
        <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
          <h2 id="matriz-titulo" className="text-lg font-semibold text-text-900">
            Matriz institucional
          </h2>
          <label className="flex items-center gap-2 text-sm text-text-700">
            <span>Estado</span>
            <select
              className="rounded-md border border-border-default bg-surface-0 px-3 py-2 text-sm text-text-900 focus:border-brand-600 focus:outline-brand-600"
              value={estado}
              onChange={(evento) => setEstado(evento.target.value as EstadoReglaFuncion | "")}
            >
              <option value="">Todos</option>
              <option value="VIGENTE">{ETIQUETAS_ESTADO_REGLA_SOD.VIGENTE}</option>
              <option value="BORRADOR">{ETIQUETAS_ESTADO_REGLA_SOD.BORRADOR}</option>
              <option value="CERRADA">{ETIQUETAS_ESTADO_REGLA_SOD.CERRADA}</option>
            </select>
          </label>
        </div>

        {reglasVisibles.length === 0 ? (
          <EmptyState
            title="Aún no hay reglas de funciones"
            description={
              puedeGestionar
                ? "Declare el primer par de funciones incompatibles en el formulario de abajo."
                : "No hay reglas con este filtro."
            }
          />
        ) : (
          <ul className="space-y-3">
            {reglasVisibles.map((regla) => (
              <li key={regla.id} className="rounded-md border border-border-subtle bg-surface-0 p-4">
                <div className="flex flex-wrap items-baseline justify-between gap-2">
                  <p className="text-sm font-semibold text-text-900">
                    {regla.codigo} · {regla.nombre}
                  </p>
                  <p className="text-xs text-text-600">
                    {ETIQUETAS_ESTADO_REGLA_SOD[regla.estado]}
                    {regla.en_vigor ? " · en vigor" : ""}
                  </p>
                </div>
                <p className="mt-1 text-sm text-text-700">
                  {(regla.rol_a_etiqueta ?? regla.rol_a) + " ≠ " + (regla.rol_b_etiqueta ?? regla.rol_b)}
                </p>
                <p className="mt-1 text-xs text-text-600">
                  Desde {formatearFechaDeNegocio(regla.vigente_desde)}
                  {regla.vigente_hasta ? ` hasta ${formatearFechaDeNegocio(regla.vigente_hasta)}` : ""}
                </p>
                <div className="mt-3 flex flex-wrap gap-2">
                  {puedeActivar && regla.estado === "BORRADOR" ? (
                    <button
                      type="button"
                      className="inline-flex h-9 items-center rounded-md border border-border-default px-3 text-sm font-medium text-text-700 hover:bg-surface-100"
                      onClick={() => activar.mutate({ id: regla.id, version: regla.version })}
                    >
                      Activar desde hoy
                    </button>
                  ) : null}
                  {puedeActivar && regla.estado === "VIGENTE" ? (
                    <button
                      type="button"
                      className="inline-flex h-9 items-center rounded-md border border-border-default px-3 text-sm font-medium text-text-700 hover:bg-surface-100"
                      onClick={() => {
                        setCierre({ id: regla.id, version: regla.version });
                        setMotivoCierre("");
                      }}
                    >
                      Cerrar regla
                    </button>
                  ) : null}
                </div>
                {cierre?.id === regla.id ? (
                  <form
                    className="mt-3 flex flex-col gap-2 rounded-md border border-border-subtle p-3"
                    onSubmit={(evento) => {
                      evento.preventDefault();
                      cerrar.mutate({ id: regla.id, version: regla.version, motivo: motivoCierre });
                    }}
                  >
                    <label className="flex flex-col gap-1 text-sm text-text-700">
                      <span>Motivo del cierre</span>
                      <input
                        className="rounded-md border border-border-default bg-surface-0 px-3 py-2 text-sm text-text-900"
                        value={motivoCierre}
                        minLength={10}
                        required
                        onChange={(evento) => setMotivoCierre(evento.target.value)}
                      />
                    </label>
                    <div className="flex gap-2">
                      <button
                        type="submit"
                        className="inline-flex h-9 items-center rounded-md border border-border-default px-3 text-sm font-medium text-text-700 hover:bg-surface-100"
                      >
                        Confirmar cierre
                      </button>
                      <button
                        type="button"
                        className="inline-flex h-9 items-center rounded-md px-3 text-sm text-text-600"
                        onClick={() => setCierre(null)}
                      >
                        Cancelar
                      </button>
                    </div>
                  </form>
                ) : null}
              </li>
            ))}
          </ul>
        )}
      </section>

      {puedeGestionar ? (
        <section aria-labelledby="nueva-regla-titulo" className="mb-8">
          <h2 id="nueva-regla-titulo" className="mb-3 text-lg font-semibold text-text-900">
            Declarar un par de funciones incompatibles
          </h2>
          <form
            className="grid gap-3 rounded-md border border-border-subtle bg-surface-0 p-4 sm:grid-cols-2"
            onSubmit={(evento) => {
              evento.preventDefault();
              crear.mutate();
            }}
          >
            <label className="flex flex-col gap-1 text-sm text-text-700 sm:col-span-2">
              <span>Nombre de la regla</span>
              <input
                className="rounded-md border border-border-default bg-surface-0 px-3 py-2 text-sm text-text-900"
                value={formulario.nombre}
                minLength={3}
                required
                onChange={(evento) => setFormulario((f) => ({ ...f, nombre: evento.target.value }))}
              />
            </label>
            <label className="flex flex-col gap-1 text-sm text-text-700">
              <span>Función A</span>
              <select
                className="rounded-md border border-border-default bg-surface-0 px-3 py-2 text-sm text-text-900"
                value={formulario.rol_a}
                required
                onChange={(evento) =>
                  setFormulario((f) => ({ ...f, rol_a: evento.target.value as FuncionProcedimiento }))
                }
              >
                <option value="">Seleccione…</option>
                {funciones.map((funcion) => (
                  <option key={funcion.codigo} value={funcion.codigo}>
                    {funcion.etiqueta}
                  </option>
                ))}
              </select>
            </label>
            <label className="flex flex-col gap-1 text-sm text-text-700">
              <span>Función B</span>
              <select
                className="rounded-md border border-border-default bg-surface-0 px-3 py-2 text-sm text-text-900"
                value={formulario.rol_b}
                required
                onChange={(evento) =>
                  setFormulario((f) => ({ ...f, rol_b: evento.target.value as FuncionProcedimiento }))
                }
              >
                <option value="">Seleccione…</option>
                {funciones
                  .filter((funcion) => funcion.codigo !== formulario.rol_a)
                  .map((funcion) => (
                    <option key={funcion.codigo} value={funcion.codigo}>
                      {funcion.etiqueta}
                    </option>
                  ))}
              </select>
            </label>
            <label className="flex flex-col gap-1 text-sm text-text-700 sm:col-span-2">
              <span>Riesgo que evita</span>
              <textarea
                className="rounded-md border border-border-default bg-surface-0 px-3 py-2 text-sm text-text-900"
                value={formulario.descripcion}
                minLength={10}
                required
                rows={2}
                onChange={(evento) => setFormulario((f) => ({ ...f, descripcion: evento.target.value }))}
              />
            </label>
            <label className="flex flex-col gap-1 text-sm text-text-700 sm:col-span-2">
              <span>Fundamento</span>
              <input
                className="rounded-md border border-border-default bg-surface-0 px-3 py-2 text-sm text-text-900"
                value={formulario.fundamento}
                minLength={10}
                required
                onChange={(evento) => setFormulario((f) => ({ ...f, fundamento: evento.target.value }))}
              />
            </label>
            <label className="flex flex-col gap-1 text-sm text-text-700">
              <span>Vigente desde (vacío = hoy)</span>
              <input
                type="date"
                className="rounded-md border border-border-default bg-surface-0 px-3 py-2 text-sm text-text-900"
                value={formulario.vigente_desde}
                onChange={(evento) => setFormulario((f) => ({ ...f, vigente_desde: evento.target.value }))}
              />
            </label>
            <label className="flex flex-col gap-1 text-sm text-text-700">
              <span>Vigente hasta (opcional)</span>
              <input
                type="date"
                className="rounded-md border border-border-default bg-surface-0 px-3 py-2 text-sm text-text-900"
                value={formulario.vigente_hasta}
                onChange={(evento) => setFormulario((f) => ({ ...f, vigente_hasta: evento.target.value }))}
              />
            </label>
            <div className="sm:col-span-2">
              <button
                type="submit"
                disabled={!formularioCompleto || crear.isPending}
                className="inline-flex h-10 items-center rounded-md bg-brand-600 px-4 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-50"
              >
                Registrar borrador
              </button>
            </div>
          </form>
        </section>
      ) : null}

      <section aria-labelledby="conflictos-titulo">
        <div className="mb-3 flex flex-wrap items-end justify-between gap-3">
          <h2 id="conflictos-titulo" className="text-lg font-semibold text-text-900">
            Conflictos en el período
          </h2>
          <div className="flex flex-wrap items-end gap-2">
            <label className="flex flex-col gap-1 text-sm text-text-700">
              <span>Desde</span>
              <input
                type="date"
                className="rounded-md border border-border-default bg-surface-0 px-3 py-2 text-sm text-text-900"
                value={desde}
                onChange={(evento) => setDesde(evento.target.value)}
              />
            </label>
            <label className="flex flex-col gap-1 text-sm text-text-700">
              <span>Hasta</span>
              <input
                type="date"
                className="rounded-md border border-border-default bg-surface-0 px-3 py-2 text-sm text-text-900"
                value={hasta}
                onChange={(evento) => setHasta(evento.target.value)}
              />
            </label>
            <label className="flex flex-col gap-1 text-sm text-text-700">
              <span>Función</span>
              <select
                className="rounded-md border border-border-default bg-surface-0 px-3 py-2 text-sm text-text-900"
                value={rolConflictos}
                onChange={(evento) =>
                  setRolConflictos(evento.target.value as FuncionProcedimiento | "")
                }
              >
                <option value="">Todas</option>
                {funciones.map((funcion) => (
                  <option key={funcion.codigo} value={funcion.codigo}>
                    {funcion.etiqueta}
                  </option>
                ))}
              </select>
            </label>
            <button
              type="button"
              className="inline-flex h-10 items-center rounded-md border border-border-default px-3 text-sm font-medium text-text-700 hover:bg-surface-100"
              onClick={() => void exportarCsv()}
            >
              Exportar CSV
            </button>
          </div>
        </div>

        {conflictos.isError ? (
          <ErrorState
            message="No fue posible cargar los conflictos."
            onRetry={() => void conflictos.refetch()}
          />
        ) : conflictosVisibles.length === 0 ? (
          <EmptyState
            title="Sin conflictos en el período"
            description="Ninguna persona ejerció dos funciones incompatibles en los expedientes del período."
          />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[52rem] border-collapse text-sm">
              <caption className="sr-only">
                Conflictos de funciones incompatibles del período
              </caption>
              <thead>
                <tr className="border-b border-border-subtle text-left text-xs uppercase tracking-wide text-text-600">
                  <th scope="col" className="px-3 py-2">Expediente</th>
                  <th scope="col" className="px-3 py-2">Fecha</th>
                  <th scope="col" className="px-3 py-2">Regla</th>
                  <th scope="col" className="px-3 py-2">Funciones</th>
                  <th scope="col" className="px-3 py-2">Persona</th>
                  <th scope="col" className="px-3 py-2">Evidencia</th>
                </tr>
              </thead>
              <tbody>
                {conflictosVisibles.map((conflicto) => (
                  <tr
                    key={`${conflicto.expediente_id}-${conflicto.regla_id}-${conflicto.actor}`}
                    className="border-b border-border-subtle align-top"
                  >
                    <td className="px-3 py-2">
                      <Link
                        className="text-brand-700 underline"
                        to={`/gobierno/contrataciones/expedientes/${conflicto.expediente_id}`}
                      >
                        {conflicto.expediente_numero}
                      </Link>
                    </td>
                    <td className="px-3 py-2">{formatearFechaDeNegocio(conflicto.fecha)}</td>
                    <td className="px-3 py-2">{conflicto.regla_codigo}</td>
                    <td className="px-3 py-2">
                      {(conflicto.rol_a_etiqueta ?? conflicto.rol_a) +
                        " ≠ " +
                        (conflicto.rol_b_etiqueta ?? conflicto.rol_b)}
                    </td>
                    <td className="px-3 py-2">{conflicto.actor_nombre ?? conflicto.actor}</td>
                    <td className="px-3 py-2">
                      <ul className="space-y-1 text-xs text-text-600">
                        {conflicto.evidencia.map((evidencia) => (
                          <li key={`${evidencia.rol}-${evidencia.registro_id}`}>
                            {evidencia.registro} ({formatearFechaDeNegocio(evidencia.fecha)})
                            {evidencia.etiqueta ? ` · ${evidencia.etiqueta}` : ""}
                          </li>
                        ))}
                      </ul>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </PageContent>
  );
}

function mensajeDeError(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.code === "GOV_SOD_ROLE_RULE_OVERLAP") return "Ya hay una regla en vigor para ese par de funciones.";
    if (error.code === "GOV_SOD_ROLE_RULE_STALE") return "La regla cambió desde que la abrió; recárguela.";
    if (error.status === 403) return error.message || "No tiene permiso para esta operación.";
    return error.message || "No fue posible completar la operación.";
  }
  return "No fue posible completar la operación.";
}
