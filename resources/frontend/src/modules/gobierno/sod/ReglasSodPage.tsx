import { useState } from "react";
import { Link } from "react-router";
import { useQuery } from "@tanstack/react-query";
import { apiFetch, ApiError } from "@/api/client";
import { useAutoridad } from "@/app/autoridad/AutoridadContext";
import { useCompany } from "@/app/contexts/CompanyContext";
import { PageContent } from "@/layout/PageContent";
import { PageHeader } from "@/components/PageHeader";
import { EmptyState } from "@/components/EmptyState";
import { ErrorState } from "@/components/ErrorState";
import { LoadingState } from "@/components/LoadingState";
import { formatearFechaDeNegocio } from "@/lib/fecha-de-negocio";
import {
  CONSULTA_SOD,
  ETIQUETAS_ESTADO_REGLA_SOD,
  ETIQUETAS_PROCESO_SOD,
  consultaDeReglasSod,
  flechaSod,
} from "@/modules/gobierno/api";
import type {
  EstadoReglaSod,
  ProcesoSod,
  ReglasSodListado,
} from "@/modules/gobierno/api";

export function ReglasSodPage() {
  const { tiene } = useAutoridad();
  const { activeCompanyId } = useCompany();
  const [estado, setEstado] = useState<EstadoReglaSod | "">("");
  const [proceso, setProceso] = useState<ProcesoSod | "">("");

  const puedeVer = tiene("gobierno_sod:view", "empresa");
  const puedeGestionar = tiene("gobierno_sod:manage", "empresa");

  const consultaReglas = useQuery({
    queryKey: [...CONSULTA_SOD, "reglas", activeCompanyId, estado, proceso],
    queryFn: () =>
      apiFetch<ReglasSodListado>(
        `/gobierno/sod/reglas${consultaDeReglasSod({ estado, proceso })}`,
      ),
    enabled: puedeVer && Boolean(activeCompanyId),
    retry: false,
  });

  const cabecera = (
    <PageHeader
      crumbs={[{ label: "Gobierno" }, { label: "Segregación de funciones" }]}
      title="Segregación de funciones"
      description="Reglas que impiden que una misma persona realice dos acciones incompatibles sobre el mismo acto o hallazgo."
      actions={
        <div className="flex flex-wrap items-center gap-2">
          <Link
            to="/gobierno/sod/conflictos"
            className="inline-flex h-10 items-center rounded-md border border-border-default px-3 text-sm font-medium text-text-700 hover:bg-surface-100"
          >
            Ver conflictos
          </Link>
          {puedeGestionar ? (
            <Link
              to="/gobierno/sod/nueva"
              className="inline-flex h-10 items-center rounded-md border border-border-default px-3 text-sm font-medium text-text-700 hover:bg-surface-100"
            >
              Nueva regla
            </Link>
          ) : null}
        </div>
      }
    />
  );

  if (!puedeVer) {
    return (
      <PageContent>
        {cabecera}
        <EmptyState
          title="Sin acceso"
          description="No tiene permiso para ver las reglas de segregación de funciones."
        />
      </PageContent>
    );
  }

  if (consultaReglas.isLoading) {
    return (
      <PageContent>
        {cabecera}
        <LoadingState label="Cargando reglas…" />
      </PageContent>
    );
  }

  if (consultaReglas.isError) {
    const error = consultaReglas.error;
    if (
      error instanceof ApiError &&
      error.status === 403 &&
      error.code === "MODULE_NOT_ENTITLED"
    ) {
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
    if (error instanceof ApiError && error.status === 403) {
      return (
        <PageContent>
          {cabecera}
          <EmptyState
            title="Sin acceso"
            description="No tiene permiso para ver las reglas de segregación de funciones."
          />
        </PageContent>
      );
    }
    return (
      <PageContent>
        {cabecera}
        <ErrorState
          message="No fue posible cargar las reglas."
          onRetry={() => void consultaReglas.refetch()}
        />
      </PageContent>
    );
  }

  if (!consultaReglas.data) {
    return (
      <PageContent>
        {cabecera}
        <EmptyState
          title="Aún no hay reglas"
          description={
            puedeGestionar
              ? "Registre la primera regla con «Nueva regla»."
              : "No hay reglas con estos filtros."
          }
        />
      </PageContent>
    );
  }

  const reglas = consultaReglas.data.items;
  const resumen = consultaReglas.data.resumen;

  const alternarEstado = (nuevoEstado: EstadoReglaSod) => {
    setEstado((actual) => (actual === nuevoEstado ? "" : nuevoEstado));
  };

  return (
    <PageContent>
      {cabecera}

      <section aria-labelledby="resumen-sod-titulo" className="mb-8">
        <h2 id="resumen-sod-titulo" className="sr-only">
          Resumen
        </h2>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <button
            type="button"
            onClick={() => alternarEstado("VIGENTE")}
            aria-pressed={estado === "VIGENTE"}
            className="rounded-md border border-border-subtle bg-surface-0 p-4 text-left"
          >
            <span className="block text-2xl font-semibold">
              {resumen.vigentes}
            </span>
            <span className="text-sm text-text-600">Vigentes</span>
          </button>
          <button
            type="button"
            onClick={() => alternarEstado("BORRADOR")}
            aria-pressed={estado === "BORRADOR"}
            className="rounded-md border border-border-subtle bg-surface-0 p-4 text-left"
          >
            <span className="block text-2xl font-semibold">
              {resumen.borradores}
            </span>
            <span className="text-sm text-text-600">Borradores</span>
          </button>
          <button
            type="button"
            onClick={() => alternarEstado("CERRADA")}
            aria-pressed={estado === "CERRADA"}
            className="rounded-md border border-border-subtle bg-surface-0 p-4 text-left"
          >
            <span className="block text-2xl font-semibold">
              {resumen.cerradas}
            </span>
            <span className="text-sm text-text-600">Cerradas</span>
          </button>
          <Link
            to="/gobierno/sod/conflictos"
            className="rounded-md border border-border-subtle bg-surface-0 p-4 text-left"
          >
            <span className="block text-2xl font-semibold">
              {resumen.conflictos_30_dias}
            </span>
            <span className="text-sm text-text-600">
              Conflictos en 30 días
            </span>
          </Link>
        </div>
      </section>

      <form role="search" aria-label="Filtrar reglas" className="mb-6" onSubmit={(evento) => evento.preventDefault()}>
        <div className="grid gap-3 sm:grid-cols-2">
          <label className="flex flex-col gap-1">
            <span className="text-sm font-medium text-text-700">Estado</span>
            <select
              className="w-full rounded-md border border-border-default bg-surface-0 px-3 py-2 text-sm text-text-900 focus:border-brand-600 focus:outline-brand-600"
              value={estado}
              onChange={(evento) =>
                setEstado(evento.target.value as EstadoReglaSod | "")
              }
            >
              <option value="">Todos</option>
              <option value="VIGENTE">
                {ETIQUETAS_ESTADO_REGLA_SOD.VIGENTE}
              </option>
              <option value="BORRADOR">
                {ETIQUETAS_ESTADO_REGLA_SOD.BORRADOR}
              </option>
              <option value="CERRADA">
                {ETIQUETAS_ESTADO_REGLA_SOD.CERRADA}
              </option>
            </select>
          </label>
          <label className="flex flex-col gap-1">
            <span className="text-sm font-medium text-text-700">Proceso</span>
            <select
              className="w-full rounded-md border border-border-default bg-surface-0 px-3 py-2 text-sm text-text-900 focus:border-brand-600 focus:outline-brand-600"
              value={proceso}
              onChange={(evento) =>
                setProceso(evento.target.value as ProcesoSod | "")
              }
            >
              <option value="">Todos</option>
              <option value="DOC-02">{ETIQUETAS_PROCESO_SOD["DOC-02"]}</option>
              <option value="CTL-06">{ETIQUETAS_PROCESO_SOD["CTL-06"]}</option>
            </select>
          </label>
        </div>
      </form>

      {reglas.length === 0 ? (
        <EmptyState
          title="Aún no hay reglas"
          description={
            puedeGestionar
              ? "Registre la primera regla con «Nueva regla»."
              : "No hay reglas con estos filtros."
          }
        />
      ) : (
        <>
          <div
            className="relative overflow-x-auto"
            tabIndex={0}
            role="region"
            aria-label="Tabla de reglas de segregación de funciones"
          >
            <table className="w-full min-w-[760px] border-collapse text-sm">
              <caption className="sr-only">
                Reglas de segregación de funciones
              </caption>
              <thead>
                <tr className="border-b border-border-default text-left text-text-600">
                  <th scope="col" className="px-3 py-2 font-medium">
                    Código
                  </th>
                  <th scope="col" className="px-3 py-2 font-medium">
                    Nombre
                  </th>
                  <th scope="col" className="px-3 py-2 font-medium">
                    Proceso
                  </th>
                  <th scope="col" className="px-3 py-2 font-medium">
                    Incompatibilidad
                  </th>
                  <th scope="col" className="px-3 py-2 font-medium">
                    Vigencia
                  </th>
                  <th scope="col" className="px-3 py-2 font-medium">
                    Estado
                  </th>
                </tr>
              </thead>
              <tbody>
                {reglas.map((regla) => (
                  <tr
                    key={regla.id}
                    className="border-b border-border-subtle align-top"
                  >
                    <td className="px-3 py-2">
                      <Link
                        to={`/gobierno/sod/${regla.id}`}
                        aria-label={`Abrir la regla ${regla.codigo}`}
                        className="font-medium text-brand-700 underline"
                      >
                        {regla.codigo}
                      </Link>
                    </td>
                    <td className="px-3 py-2 text-text-900">{regla.nombre}</td>
                    <td className="px-3 py-2">
                      {ETIQUETAS_PROCESO_SOD[regla.proceso]}
                    </td>
                    <td className="px-3 py-2">
                      {`${regla.accion_a_etiqueta} ${flechaSod(regla.bidireccional)} ${regla.accion_b_etiqueta}`}
                    </td>
                    <td className="px-3 py-2">
                      {`Desde ${formatearFechaDeNegocio(regla.vigente_desde)}${
                        regla.vigente_hasta
                          ? ` hasta ${formatearFechaDeNegocio(regla.vigente_hasta)}`
                          : " · sin fecha de fin"
                      }`}
                    </td>
                    <td className="px-3 py-2">
                      {`${ETIQUETAS_ESTADO_REGLA_SOD[regla.estado]}${
                        regla.en_vigor ? " · en vigor" : ""
                      }`}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </PageContent>
  );
}
