import { useState } from "react";
import { Link } from "react-router";
import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { apiFetch, ApiError } from "@/api/client";
import { useAutoridad } from "@/app/autoridad/AutoridadContext";
import { useCompany } from "@/app/contexts/CompanyContext";
import { formatMoney } from "@/lib/format";
import { PageContent } from "@/layout/PageContent";
import { PageHeader } from "@/components/PageHeader";
import { EmptyState } from "@/components/EmptyState";
import { ErrorState } from "@/components/ErrorState";
import { LoadingState } from "@/components/LoadingState";
import {
  CONSULTA_CAJA,
  ETIQUETAS_ESTADO_PROGRAMA,
  MONEDAS_CUENTA,
  consultaDeProgramas,
} from "@/modules/gobierno/api";
import type {
  EstadoPrograma,
  MonedaPrograma,
  ProgramasListado,
} from "@/modules/gobierno/api";

export function ProgramasPage(): React.JSX.Element {
  const { tiene } = useAutoridad();
  const { activeCompanyId } = useCompany();
  const [ejercicio, setEjercicio] = useState("");
  const [moneda, setMoneda] = useState<MonedaPrograma | "">("");
  const [estado, setEstado] = useState<EstadoPrograma | "">("");

  const puedeVer = tiene("gobierno_caja:view", "empresa");
  const puedeGestionar = tiene("gobierno_caja:manage", "empresa");

  const consultaProgramas = useQuery({
    queryKey: [
      ...CONSULTA_CAJA,
      "programas",
      activeCompanyId,
      ejercicio,
      moneda,
      estado,
    ],
    queryFn: () =>
      apiFetch<ProgramasListado>(
        `/gobierno/tesoreria/programas${consultaDeProgramas({
          ejercicio,
          moneda,
          estado,
        })}`,
      ),
    enabled: puedeVer && Boolean(activeCompanyId),
    retry: false,
    placeholderData: keepPreviousData,
  });

  const cabecera = (
    <PageHeader
      crumbs={[{ label: "Gobierno" }, { label: "Tesorería" }]}
      title="Programación financiera"
      description="Programación de flujos de caja por ejercicio, mes y moneda; es disponibilidad de caja proyectada, no presupuesto ni saldo bancario."
      actions={
        <div className="flex flex-wrap items-center gap-2">
          {puedeGestionar ? (
            <Link
              to="/gobierno/tesoreria/programacion/nuevo"
              className="inline-flex h-10 items-center rounded-md border border-border-default px-3 text-sm font-medium text-text-700 hover:bg-surface-100"
            >
              Nuevo programa
            </Link>
          ) : null}
          <Link
            to="/gobierno/tesoreria/rubros"
            className="inline-flex h-10 items-center rounded-md border border-border-default px-3 text-sm font-medium text-text-700 hover:bg-surface-100"
          >
            Rubros de caja
          </Link>
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
          description="No tiene permiso para ver la programación financiera."
        />
      </PageContent>
    );
  }

  if (consultaProgramas.isLoading) {
    return (
      <PageContent>
        {cabecera}
        <LoadingState label="Cargando programas…" />
      </PageContent>
    );
  }

  if (consultaProgramas.isError) {
    const error = consultaProgramas.error;
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
            description="No tiene permiso para ver la programación financiera."
          />
        </PageContent>
      );
    }
    return (
      <PageContent>
        {cabecera}
        <ErrorState
          message="No fue posible cargar los programas."
          onRetry={() => void consultaProgramas.refetch()}
        />
      </PageContent>
    );
  }

  if (!consultaProgramas.data) {
    return (
      <PageContent>
        {cabecera}
        <EmptyState
          title="No hay programas"
          description="Registre el primer programa de caja."
          action={
            puedeGestionar ? (
              <Link
                to="/gobierno/tesoreria/programacion/nuevo"
                className="inline-flex h-10 items-center rounded-md border border-border-default px-3 text-sm font-medium text-text-700 hover:bg-surface-100"
              >
                Nuevo programa
              </Link>
            ) : undefined
          }
        />
      </PageContent>
    );
  }

  const programas = consultaProgramas.data.items;
  const resumen = consultaProgramas.data.resumen;
  const hayFiltros = Boolean(ejercicio || moneda || estado);

  const alternarEstado = (nuevoEstado: EstadoPrograma) => {
    setEstado((actual) => (actual === nuevoEstado ? "" : nuevoEstado));
  };

  return (
    <PageContent>
      {cabecera}

      <section aria-labelledby="resumen-programas-titulo" className="mb-8">
        <h2 id="resumen-programas-titulo" className="sr-only">
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
            onClick={() => alternarEstado("CERRADO")}
            aria-pressed={estado === "CERRADO"}
            className="rounded-md border border-border-subtle bg-surface-0 p-4 text-left"
          >
            <span className="block text-2xl font-semibold">
              {resumen.cerrados}
            </span>
            <span className="text-sm text-text-600">Cerrados</span>
          </button>
        </div>
      </section>

      <form
        role="search"
        aria-label="Filtrar programas"
        className="mb-6"
        onSubmit={(evento) => evento.preventDefault()}
      >
        <div className="grid gap-3 sm:grid-cols-3">
          <label className="flex max-w-xs flex-col gap-1">
            <span className="text-sm font-medium text-text-700">Ejercicio</span>
            <input
              type="number"
              min={2000}
              max={2100}
              className="w-full rounded-md border border-border-default bg-surface-0 px-3 py-2 text-sm text-text-900 focus:border-brand-600 focus:outline-brand-600"
              value={ejercicio}
              onChange={(evento) => setEjercicio(evento.target.value)}
              placeholder="Todos"
            />
          </label>
          <label className="flex max-w-xs flex-col gap-1">
            <span className="text-sm font-medium text-text-700">Moneda</span>
            <select
              className="w-full rounded-md border border-border-default bg-surface-0 px-3 py-2 text-sm text-text-900 focus:border-brand-600 focus:outline-brand-600"
              value={moneda}
              onChange={(evento) =>
                setMoneda(evento.target.value as MonedaPrograma | "")
              }
            >
              <option value="">Todos</option>
              {MONEDAS_CUENTA.map((monedaCuenta) => (
                <option key={monedaCuenta} value={monedaCuenta}>
                  {monedaCuenta}
                </option>
              ))}
            </select>
          </label>
          <label className="flex max-w-xs flex-col gap-1">
            <span className="text-sm font-medium text-text-700">Estado</span>
            <select
              className="w-full rounded-md border border-border-default bg-surface-0 px-3 py-2 text-sm text-text-900 focus:border-brand-600 focus:outline-brand-600"
              value={estado}
              onChange={(evento) =>
                setEstado(evento.target.value as EstadoPrograma | "")
              }
            >
              <option value="">Todos</option>
              <option value="BORRADOR">
                {ETIQUETAS_ESTADO_PROGRAMA.BORRADOR}
              </option>
              <option value="VIGENTE">
                {ETIQUETAS_ESTADO_PROGRAMA.VIGENTE}
              </option>
              <option value="CERRADO">
                {ETIQUETAS_ESTADO_PROGRAMA.CERRADO}
              </option>
            </select>
          </label>
        </div>
      </form>

      {programas.length === 0 ? (
        hayFiltros ? (
          <EmptyState
            title="No hay programas"
            description="No hay programas con estos filtros."
          />
        ) : (
          <EmptyState
            title="No hay programas"
            description="Registre el primer programa de caja."
            action={
              puedeGestionar ? (
                <Link
                  to="/gobierno/tesoreria/programacion/nuevo"
                  className="inline-flex h-10 items-center rounded-md border border-border-default px-3 text-sm font-medium text-text-700 hover:bg-surface-100"
                >
                  Nuevo programa
                </Link>
              ) : undefined
            }
          />
        )
      ) : (
        <div
          className="relative overflow-x-auto"
          tabIndex={0}
          role="region"
          aria-label="Tabla de programas"
        >
          <table className="w-full min-w-[800px] border-collapse text-sm">
            <caption className="sr-only">
              Programas de caja del ente
            </caption>
            <thead>
              <tr className="border-b border-border-default text-left text-text-600">
                <th scope="col" className="px-3 py-2 font-medium">
                  Código
                </th>
                <th scope="col" className="px-3 py-2 font-medium">
                  Ejercicio
                </th>
                <th scope="col" className="px-3 py-2 font-medium">
                  Moneda
                </th>
                <th scope="col" className="px-3 py-2 font-medium">
                  Estado
                </th>
                <th scope="col" className="px-3 py-2 font-medium">
                  Versión vigente
                </th>
                <th scope="col" className="px-3 py-2 font-medium">
                  Disponibilidad inicial declarada
                </th>
              </tr>
            </thead>
            <tbody>
              {programas.map((programa) => {
                const estadoTexto = ETIQUETAS_ESTADO_PROGRAMA[programa.estado];

                return (
                  <tr
                    key={programa.id}
                    className="border-b border-border-subtle align-top"
                  >
                    <td className="px-3 py-2">
                      <Link
                        to={`/gobierno/tesoreria/programacion/${programa.id}`}
                        aria-label={`Abrir el programa ${programa.codigo}`}
                        className="font-medium text-brand-700 underline"
                      >
                        {programa.codigo}
                      </Link>
                    </td>
                    <td className="px-3 py-2 text-text-900">
                      {programa.ejercicio}
                    </td>
                    <td className="px-3 py-2">{programa.moneda}</td>
                    <td className="px-3 py-2">{estadoTexto}</td>
                    <td className="px-3 py-2">
                      {programa.version_vigente ?? "—"}
                    </td>
                    <td className="px-3 py-2">
                      {programa.disponibilidad_inicial != null
                        ? `${formatMoney(programa.disponibilidad_inicial)} ${programa.moneda}`
                        : "—"}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </PageContent>
  );
}
