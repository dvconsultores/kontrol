import { useState } from "react";
import { Link } from "react-router";
import { keepPreviousData, useQuery } from "@tanstack/react-query";
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
  CONSULTA_CIERRES,
  ETIQUETAS_ESTADO_POLITICA_CIERRE,
  ETIQUETAS_ACCION_CIERRE,
  consultaDePoliticasCierre,
} from "@/modules/gobierno/api";
import type {
  EstadoPoliticaCierre,
  AccionCierre,
  PoliticasCierreListado,
} from "@/modules/gobierno/api";

export function PoliticasPage() {
  const { tiene } = useAutoridad();
  const { activeCompanyId } = useCompany();
  const [estado, setEstado] = useState<EstadoPoliticaCierre | "">("");
  const [accion, setAccion] = useState<AccionCierre | "">("");

  const puedeVer = tiene("gobierno_cierre:view", "empresa");
  const puedeGestionar = tiene("gobierno_cierre:manage", "empresa");

  const consultaPoliticas = useQuery({
    queryKey: [...CONSULTA_CIERRES, "politicas", activeCompanyId, estado, accion],
    queryFn: () =>
      apiFetch<PoliticasCierreListado>(
        `/gobierno/cierres/politicas${consultaDePoliticasCierre({ estado, accion_cierre: accion })}`,
      ),
    enabled: puedeVer && Boolean(activeCompanyId),
    placeholderData: keepPreviousData,
    retry: false,
  });

  const cabecera = (
    <PageHeader
      crumbs={[{ label: "Gobierno" }, { label: "Controles de cierre" }]}
      title="Controles de cierre"
      description="Políticas que impiden cerrar una estructura o un programa mientras existan controles materiales pendientes."
      actions={
        <div className="flex flex-wrap items-center gap-2">
          <Link
            to="/gobierno/cierres/bloqueos"
            className="inline-flex h-10 items-center rounded-md border border-border-default px-3 text-sm font-medium text-text-700 hover:bg-surface-100"
          >
            Cierres bloqueados
          </Link>
          {puedeGestionar ? (
            <Link
              to="/gobierno/cierres/nueva"
              className="inline-flex h-10 items-center rounded-md border border-border-default px-3 text-sm font-medium text-text-700 hover:bg-surface-100"
            >
              Nueva política
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
          description="No tiene permiso para ver las políticas de cierre."
        />
      </PageContent>
    );
  }

  if (consultaPoliticas.isLoading) {
    return (
      <PageContent>
        {cabecera}
        <LoadingState label="Cargando políticas…" />
      </PageContent>
    );
  }

  if (consultaPoliticas.isError) {
    const error = consultaPoliticas.error;
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
            description="No tiene permiso para ver las políticas de cierre."
          />
        </PageContent>
      );
    }
    return (
      <PageContent>
        {cabecera}
        <ErrorState
          message="No fue posible cargar las políticas."
          onRetry={() => void consultaPoliticas.refetch()}
        />
      </PageContent>
    );
  }

  if (!consultaPoliticas.data) {
    return (
      <PageContent>
        {cabecera}
        <EmptyState
          title="Aún no hay políticas"
          description={
            puedeGestionar
              ? "Registre la primera política con «Nueva política»."
              : "No hay políticas con estos filtros."
          }
        />
      </PageContent>
    );
  }

  const politicas = consultaPoliticas.data.items;
  const resumen = consultaPoliticas.data.resumen;

  const alternarEstado = (nuevoEstado: EstadoPoliticaCierre) => {
    setEstado((actual) => (actual === nuevoEstado ? "" : nuevoEstado));
  };

  return (
    <PageContent>
      {cabecera}

      <section aria-labelledby="resumen-cierres-titulo" className="mb-8">
        <h2 id="resumen-cierres-titulo" className="sr-only">
          Resumen
        </h2>
        <div className="grid gap-3 sm:grid-cols-3">
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
            onClick={() => alternarEstado("RETIRADA")}
            aria-pressed={estado === "RETIRADA"}
            className="rounded-md border border-border-subtle bg-surface-0 p-4 text-left"
          >
            <span className="block text-2xl font-semibold">
              {resumen.retiradas}
            </span>
            <span className="text-sm text-text-600">Retiradas</span>
          </button>
        </div>
      </section>

      <form
        role="search"
        aria-label="Filtrar políticas"
        className="mb-6"
        onSubmit={(evento) => evento.preventDefault()}
      >
        <div className="grid gap-3 sm:grid-cols-2">
          <label className="flex flex-col gap-1">
            <span className="text-sm font-medium text-text-700">Acción</span>
            <select
              className="w-full rounded-md border border-border-default bg-surface-0 px-3 py-2 text-sm text-text-900 focus:border-brand-600 focus:outline-brand-600"
              value={accion}
              onChange={(evento) =>
                setAccion(evento.target.value as AccionCierre | "")
              }
            >
              <option value="">Todas</option>
              <option value="ORG02_CERRAR_ESTRUCTURA">
                {ETIQUETAS_ACCION_CIERRE.ORG02_CERRAR_ESTRUCTURA}
              </option>
              <option value="TRE02_CERRAR_PROGRAMA">
                {ETIQUETAS_ACCION_CIERRE.TRE02_CERRAR_PROGRAMA}
              </option>
            </select>
          </label>
          <label className="flex flex-col gap-1">
            <span className="text-sm font-medium text-text-700">Estado</span>
            <select
              className="w-full rounded-md border border-border-default bg-surface-0 px-3 py-2 text-sm text-text-900 focus:border-brand-600 focus:outline-brand-600"
              value={estado}
              onChange={(evento) =>
                setEstado(evento.target.value as EstadoPoliticaCierre | "")
              }
            >
              <option value="">Todos</option>
              <option value="BORRADOR">
                {ETIQUETAS_ESTADO_POLITICA_CIERRE.BORRADOR}
              </option>
              <option value="VIGENTE">
                {ETIQUETAS_ESTADO_POLITICA_CIERRE.VIGENTE}
              </option>
              <option value="RETIRADA">
                {ETIQUETAS_ESTADO_POLITICA_CIERRE.RETIRADA}
              </option>
            </select>
          </label>
        </div>
      </form>

      {politicas.length === 0 ? (
        estado || accion ? (
          <EmptyState
            title="Sin resultados"
            description="No hay políticas con estos filtros."
          />
        ) : (
          <EmptyState
            title="Aún no hay políticas"
            description={
              puedeGestionar
                ? "Registre la primera política con «Nueva política»."
                : "Todavía no se ha registrado ninguna política."
            }
          />
        )
      ) : (
        <div
          className="relative overflow-x-auto"
          tabIndex={0}
          role="region"
          aria-label="Tabla de políticas de cierre"
        >
          <table className="w-full min-w-[760px] border-collapse text-sm">
            <caption className="sr-only">Políticas de cierre</caption>
            <thead>
              <tr className="border-b border-border-default text-left text-text-600">
                <th scope="col" className="px-3 py-2 font-medium">
                  Código
                </th>
                <th scope="col" className="px-3 py-2 font-medium">
                  Nombre
                </th>
                <th scope="col" className="px-3 py-2 font-medium">
                  Acción
                </th>
                <th scope="col" className="px-3 py-2 font-medium">
                  Estado
                </th>
                <th scope="col" className="px-3 py-2 font-medium">
                  Vigente desde
                </th>
                <th scope="col" className="px-3 py-2 font-medium">
                  Efectiva hoy
                </th>
              </tr>
            </thead>
            <tbody>
              {politicas.map((politica) => (
                <tr
                  key={politica.id}
                  className="border-b border-border-subtle align-top"
                >
                  <td className="px-3 py-2">
                    <Link
                      to={`/gobierno/cierres/${politica.id}`}
                      aria-label={`Abrir la política ${politica.codigo}`}
                      className="font-medium text-brand-700 underline"
                    >
                      {politica.codigo}
                    </Link>
                  </td>
                  <td className="px-3 py-2 text-text-900">
                    {politica.nombre}
                  </td>
                  <td className="px-3 py-2">
                    {ETIQUETAS_ACCION_CIERRE[politica.accion_cierre]}
                  </td>
                  <td className="px-3 py-2">
                    {ETIQUETAS_ESTADO_POLITICA_CIERRE[politica.estado]}
                  </td>
                  <td className="px-3 py-2">
                    {formatearFechaDeNegocio(politica.vigente_desde)}
                  </td>
                  <td className="px-3 py-2">
                    {politica.efectiva_hoy ? "Sí" : "No"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </PageContent>
  );
}
