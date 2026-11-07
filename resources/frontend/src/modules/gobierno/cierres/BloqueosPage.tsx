import { useState } from "react";
import { Link } from "react-router";
import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { apiFetch, ApiError } from "@/api/client";
import { useAutoridad } from "@/app/autoridad/AutoridadContext";
import { useCompany } from "@/app/contexts/CompanyContext";
import { Button } from "@/components/Button";
import { EmptyState } from "@/components/EmptyState";
import { ErrorState } from "@/components/ErrorState";
import { LoadingState } from "@/components/LoadingState";
import { PageContent } from "@/layout/PageContent";
import { PageHeader } from "@/components/PageHeader";
import { formatearInstante } from "@/lib/fecha-de-negocio";
import {
  CONSULTA_CIERRES,
  ETIQUETAS_ACCION_CIERRE,
  POR_PAGINA_BLOQUEOS,
  consultaDeBloqueosCierre,
  rutaDeObjetoCierre,
} from "@/modules/gobierno/api";
import type {
  AccionCierre,
  BloqueosCierreListado,
} from "@/modules/gobierno/api";

function etiquetaAccion(a: string | null): string {
  if (a === null) return "—";
  if (a in ETIQUETAS_ACCION_CIERRE) {
    return ETIQUETAS_ACCION_CIERRE[a as AccionCierre];
  }
  return a;
}

export function BloqueosPage() {
  const { tiene } = useAutoridad();
  const { activeCompanyId } = useCompany();

  const [borradorAccion, setBorradorAccion] = useState("");
  const [borradorDesde, setBorradorDesde] = useState("");
  const [borradorHasta, setBorradorHasta] = useState("");

  const [filtroAccion, setFiltroAccion] = useState("");
  const [filtroDesde, setFiltroDesde] = useState("");
  const [filtroHasta, setFiltroHasta] = useState("");
  const [pagina, setPagina] = useState(1);

  const puedeVer = tiene("gobierno_cierre:view", "empresa");

  const filtrosAplicados = {
    accion_cierre: filtroAccion,
    desde: filtroDesde,
    hasta: filtroHasta,
  };

  const consultaBloqueos = useQuery({
    queryKey: [
      ...CONSULTA_CIERRES,
      "bloqueos",
      activeCompanyId,
      filtrosAplicados,
      pagina,
    ],
    queryFn: () =>
      apiFetch<BloqueosCierreListado>(
        `/gobierno/cierres/bloqueos${consultaDeBloqueosCierre(
          filtrosAplicados,
          { pagina, tamano: POR_PAGINA_BLOQUEOS },
        )}`,
      ),
    enabled: puedeVer && Boolean(activeCompanyId),
    retry: false,
    placeholderData: keepPreviousData,
  });

  const cabecera = (
    <PageHeader
      crumbs={[
        { label: "Gobierno" },
        { label: "Controles de cierre", to: "/gobierno/cierres" },
        { label: "Cierres bloqueados" },
      ]}
      title="Cierres bloqueados"
      description="Cierres que el sistema impidió: sobre qué objeto se intentó cerrar y qué controles lo bloquearon."
    />
  );

  if (!puedeVer) {
    return (
      <PageContent>
        {cabecera}
        <EmptyState
          title="Sin acceso"
          description="No tiene permiso para ver los cierres bloqueados."
        />
      </PageContent>
    );
  }

  if (consultaBloqueos.isLoading) {
    return (
      <PageContent>
        {cabecera}
        <LoadingState label="Cargando cierres bloqueados…" />
      </PageContent>
    );
  }

  if (consultaBloqueos.isError) {
    const error = consultaBloqueos.error;
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
            description="No tiene permiso para ver los cierres bloqueados."
          />
        </PageContent>
      );
    }
    return (
      <PageContent>
        {cabecera}
        <ErrorState
          message="No fue posible cargar los cierres bloqueados."
          onRetry={() => void consultaBloqueos.refetch()}
        />
      </PageContent>
    );
  }

  if (!consultaBloqueos.data) {
    return (
      <PageContent>
        {cabecera}
        <EmptyState
          title="No hay cierres bloqueados"
          description="Cuando el sistema impida un cierre por un control vigente, aparecerá aquí."
        />
      </PageContent>
    );
  }

  const bloqueos = consultaBloqueos.data.items;
  const total = consultaBloqueos.data.total;
  const totalPaginas = Math.max(1, Math.ceil(total / POR_PAGINA_BLOQUEOS));

  const hayFiltros =
    filtroAccion !== "" || filtroDesde !== "" || filtroHasta !== "";

  const aplicarFiltros = (evento: React.FormEvent<HTMLFormElement>) => {
    evento.preventDefault();
    setFiltroAccion(borradorAccion);
    setFiltroDesde(borradorDesde);
    setFiltroHasta(borradorHasta);
    setPagina(1);
  };

  const limpiarFiltros = () => {
    setBorradorAccion("");
    setBorradorDesde("");
    setBorradorHasta("");
    setFiltroAccion("");
    setFiltroDesde("");
    setFiltroHasta("");
    setPagina(1);
  };

  return (
    <PageContent>
      {cabecera}

      <form
        role="search"
        aria-label="Filtrar cierres bloqueados"
        className="mb-6"
        onSubmit={aplicarFiltros}
      >
        <div className="grid gap-3 sm:grid-cols-2">
          <label className="flex flex-col gap-1">
            <span className="text-sm font-medium text-text-700">Acción</span>
            <select
              className="w-full rounded-md border border-border-default bg-surface-0 px-3 py-2 text-sm text-text-900 focus:border-brand-600 focus:outline-brand-600"
              value={borradorAccion}
              onChange={(evento) => setBorradorAccion(evento.target.value)}
            >
              <option value="">Todas</option>
              {Object.entries(ETIQUETAS_ACCION_CIERRE).map(([codigo, etiqueta]) => (
                <option key={codigo} value={codigo}>
                  {etiqueta}
                </option>
              ))}
            </select>
          </label>
          <div className="grid grid-cols-2 gap-3">
            <label className="flex flex-col gap-1">
              <span className="text-sm font-medium text-text-700">Desde</span>
              <input
                type="date"
                className="w-full rounded-md border border-border-default bg-surface-0 px-3 py-2 text-sm text-text-900 focus:border-brand-600 focus:outline-brand-600"
                value={borradorDesde}
                onChange={(evento) => setBorradorDesde(evento.target.value)}
              />
            </label>
            <label className="flex flex-col gap-1">
              <span className="text-sm font-medium text-text-700">Hasta</span>
              <input
                type="date"
                className="w-full rounded-md border border-border-default bg-surface-0 px-3 py-2 text-sm text-text-900 focus:border-brand-600 focus:outline-brand-600"
                value={borradorHasta}
                onChange={(evento) => setBorradorHasta(evento.target.value)}
              />
            </label>
          </div>
        </div>
        <div className="mt-4 flex items-center gap-2">
          <button
            type="submit"
            className="inline-flex h-10 items-center rounded-md bg-brand-600 px-4 text-sm font-medium text-white hover:bg-brand-700"
          >
            Aplicar filtros
          </button>
          <Button variant="secondary" onClick={limpiarFiltros}>
            Limpiar
          </Button>
        </div>
      </form>

      {bloqueos.length === 0 ? (
        hayFiltros ? (
          <EmptyState
            title="Sin resultados"
            description="Ningún cierre bloqueado coincide con los filtros aplicados."
          />
        ) : (
          <EmptyState
            title="No hay cierres bloqueados"
            description="Cuando el sistema impida un cierre por un control vigente, aparecerá aquí."
          />
        )
      ) : (
        <>
          <div
            className="relative overflow-x-auto"
            tabIndex={0}
            role="region"
            aria-label="Tabla de cierres bloqueados"
          >
            <table className="w-full min-w-[860px] border-collapse text-sm">
              <caption className="sr-only">
                Cierres bloqueados por controles de cierre
              </caption>
              <thead>
                <tr className="border-b border-border-default text-left text-text-600">
                  <th scope="col" className="px-3 py-2 font-medium">
                    Fecha
                  </th>
                  <th scope="col" className="px-3 py-2 font-medium">
                    Política
                  </th>
                  <th scope="col" className="px-3 py-2 font-medium">
                    Acción
                  </th>
                  <th scope="col" className="px-3 py-2 font-medium">
                    Objeto
                  </th>
                  <th scope="col" className="px-3 py-2 font-medium">
                    Usuario
                  </th>
                  <th scope="col" className="px-3 py-2 font-medium">
                    Pendientes
                  </th>
                </tr>
              </thead>
              <tbody>
                {bloqueos.map((b) => {
                  const rutaObjeto = rutaDeObjetoCierre(
                    b.objeto_tipo,
                    b.objeto_id,
                    b.objeto_codigo,
                  );
                  return (
                    <tr
                      key={b.id}
                      className="border-b border-border-subtle align-top"
                    >
                      <td className="px-3 py-2">
                        {formatearInstante(b.instante)}
                      </td>
                      <td className="px-3 py-2">
                        {b.politica_id ? (
                          <Link
                            to={`/gobierno/cierres/${b.politica_id}`}
                            className="font-medium text-brand-700 underline"
                          >
                            {b.politica_codigo ?? "—"}
                          </Link>
                        ) : (
                          (b.politica_codigo ?? "—")
                        )}
                      </td>
                      <td className="px-3 py-2">
                        {etiquetaAccion(b.accion_cierre)}
                      </td>
                      <td className="px-3 py-2">
                        {rutaObjeto ? (
                          <Link
                            to={rutaObjeto}
                            className="font-medium text-brand-700 underline"
                          >
                            {b.objeto_codigo ?? "Abrir objeto"}
                          </Link>
                        ) : (
                          (b.objeto_codigo ?? "—")
                        )}
                      </td>
                      <td className="px-3 py-2">{b.usuario ?? "—"}</td>
                      <td className="px-3 py-2">{b.total ?? "—"}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
          {total > POR_PAGINA_BLOQUEOS && (
            <div className="mt-4 flex items-center justify-between">
              <button
                type="button"
                onClick={() => setPagina((actual) => Math.max(1, actual - 1))}
                disabled={pagina <= 1}
                className="inline-flex items-center rounded-md border border-border-default px-3 py-2 text-sm font-medium text-text-700 hover:bg-surface-hover disabled:cursor-not-allowed disabled:opacity-50"
              >
                Anterior
              </button>
              <span className="text-sm text-text-700">
                Página {pagina} de {totalPaginas}
              </span>
              <button
                type="button"
                onClick={() =>
                  setPagina((actual) => Math.min(totalPaginas, actual + 1))
                }
                disabled={pagina >= totalPaginas}
                className="inline-flex items-center rounded-md border border-border-default px-3 py-2 text-sm font-medium text-text-700 hover:bg-surface-hover disabled:cursor-not-allowed disabled:opacity-50"
              >
                Siguiente
              </button>
            </div>
          )}
        </>
      )}
      <p className="mt-4 text-sm text-text-600">
        {total} cierres bloqueados
      </p>
    </PageContent>
  );
}
