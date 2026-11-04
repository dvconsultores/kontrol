import { useState } from "react";
import { Link, useSearchParams } from "react-router";
import { useQuery } from "@tanstack/react-query";
import { apiFetch, ApiError } from "@/api/client";
import { useAutoridad } from "@/app/autoridad/AutoridadContext";
import { useCompany } from "@/app/contexts/CompanyContext";
import { Button } from "@/components/Button";
import { EmptyState } from "@/components/EmptyState";
import { ErrorState } from "@/components/ErrorState";
import { LoadingState } from "@/components/LoadingState";
import { FormField } from "@/components/FormField";
import { TextInput } from "@/components/TextInput";
import { PageContent } from "@/layout/PageContent";
import { PageHeader } from "@/components/PageHeader";
import { formatearFecha } from "@/i18n";
import {
  CONSULTA_SOD,
  ETIQUETAS_PROCESO_SOD,
  POR_PAGINA_CONFLICTOS_SOD,
  consultaDeConflictosSod,
  rutaDeObjetoSod,
} from "@/modules/gobierno/api";
import type {
  CatalogoSod,
  ConflictosSodListado,
  ProcesoSod,
} from "@/modules/gobierno/api";

type ProcesoAccionesSod = {
  proceso: ProcesoSod;
  nombre: string;
  objeto: string;
  acciones: {
    codigo: string;
    etiqueta: string;
    crea_objeto: boolean;
  }[];
};

function etiquetaProceso(p: string | null): string {
  if (p === null) return "—";
  if (p === "DOC-02" || p === "CTL-06") {
    return ETIQUETAS_PROCESO_SOD[p];
  }
  return p;
}

export function ConflictosSodPage() {
  const { tiene } = useAutoridad();
  const { activeCompanyId } = useCompany();
  const [searchParams, setSearchParams] = useSearchParams();

  const [borradorProceso, setBorradorProceso] = useState<ProcesoSod | "">("");
  const [borradorAccion, setBorradorAccion] = useState("");
  const [borradorUsuario, setBorradorUsuario] = useState("");
  const [borradorDesde, setBorradorDesde] = useState("");
  const [borradorHasta, setBorradorHasta] = useState("");

  const [filtroProceso, setFiltroProceso] = useState<ProcesoSod | "">("");
  const [filtroAccion, setFiltroAccion] = useState("");
  const [filtroUsuario, setFiltroUsuario] = useState("");
  const [filtroDesde, setFiltroDesde] = useState("");
  const [filtroHasta, setFiltroHasta] = useState("");
  const [pagina, setPagina] = useState(1);

  const reglaId = searchParams.get("regla_id");

  const puedeVer = tiene("gobierno_sod:view", "empresa");

  const consultaCatalogo = useQuery({
    queryKey: [...CONSULTA_SOD, "acciones", activeCompanyId],
    queryFn: () => apiFetch<CatalogoSod>("/gobierno/sod/acciones"),
    enabled: puedeVer && Boolean(activeCompanyId),
    retry: false,
  });

  const filtrosAplicados = {
    proceso: filtroProceso,
    accion: filtroAccion,
    usuario: filtroUsuario,
    desde: filtroDesde,
    hasta: filtroHasta,
  };

  const consultaConflictos = useQuery({
    queryKey: [
      ...CONSULTA_SOD,
      "conflictos",
      activeCompanyId,
      reglaId,
      filtrosAplicados,
      pagina,
    ],
    queryFn: () =>
      apiFetch<ConflictosSodListado>(
        `/gobierno/sod/conflictos${consultaDeConflictosSod(
          { regla_id: reglaId ?? undefined, ...filtrosAplicados },
          { pagina, por_pagina: POR_PAGINA_CONFLICTOS_SOD },
        )}`,
      ),
    enabled: puedeVer && Boolean(activeCompanyId),
    retry: false,
  });

  const cabecera = (
    <PageHeader
      crumbs={[
        { label: "Gobierno" },
        { label: "Segregación de funciones", to: "/gobierno/sod" },
        { label: "Conflictos" },
      ]}
      title="Conflictos de segregación de funciones"
      description="Intentos bloqueados: quién intentó qué acción, sobre qué acto o hallazgo y por qué regla."
    />
  );

  if (!puedeVer) {
    return (
      <PageContent>
        {cabecera}
        <EmptyState
          title="Sin acceso"
          description="No tiene permiso para ver los conflictos de segregación de funciones."
        />
      </PageContent>
    );
  }

  if (consultaConflictos.isLoading) {
    return (
      <PageContent>
        {cabecera}
        <LoadingState label="Cargando conflictos…" />
      </PageContent>
    );
  }

  if (consultaConflictos.isError) {
    const error = consultaConflictos.error;
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
            description="No tiene permiso para ver los conflictos de segregación de funciones."
          />
        </PageContent>
      );
    }
    return (
      <PageContent>
        {cabecera}
        <ErrorState
          message="No fue posible cargar los conflictos."
          onRetry={() => void consultaConflictos.refetch()}
        />
      </PageContent>
    );
  }

  if (!consultaConflictos.data) {
    return (
      <PageContent>
        {cabecera}
        <EmptyState
          title="No hay intentos bloqueados"
          description="Cuando alguien intente realizar una acción incompatible con una regla vigente, aparecerá aquí."
        />
      </PageContent>
    );
  }

  const conflictos = consultaConflictos.data.items;
  const total = consultaConflictos.data.total;
  const totalPaginas = Math.max(
    1,
    Math.ceil(total / POR_PAGINA_CONFLICTOS_SOD),
  );

  const catalogo = consultaCatalogo.data;
  const procesos: ProcesoAccionesSod[] = catalogo?.procesos ?? [];
  const procesoSeleccionado = procesos.find(
    (p) => p.proceso === borradorProceso,
  );
  const acciones = procesoSeleccionado?.acciones ?? [];

  const aplicarFiltros = (evento: React.FormEvent<HTMLFormElement>) => {
    evento.preventDefault();
    setFiltroProceso(borradorProceso);
    setFiltroAccion(borradorAccion);
    setFiltroUsuario(borradorUsuario);
    setFiltroDesde(borradorDesde);
    setFiltroHasta(borradorHasta);
    setPagina(1);
  };

  const limpiarFiltros = () => {
    setBorradorProceso("");
    setBorradorAccion("");
    setBorradorUsuario("");
    setBorradorDesde("");
    setBorradorHasta("");
    setFiltroProceso("");
    setFiltroAccion("");
    setFiltroUsuario("");
    setFiltroDesde("");
    setFiltroHasta("");
    setPagina(1);
  };

  const quitarFiltroDeRegla = () => {
    const nuevos = new URLSearchParams(searchParams);
    nuevos.delete("regla_id");
    setSearchParams(nuevos);
    setPagina(1);
  };

  return (
    <PageContent>
      {cabecera}

      {reglaId ? (
        <div className="mb-6 flex items-center justify-between rounded-md border border-border-subtle bg-surface-0 p-4">
          <span className="text-sm text-text-700">
            Filtrando por una regla.
          </span>
          <Button variant="secondary" onClick={quitarFiltroDeRegla}>
            Quitar filtro de regla
          </Button>
        </div>
      ) : null}

      <form
        role="search"
        aria-label="Filtrar conflictos"
        className="mb-6"
        onSubmit={aplicarFiltros}
      >
        <div className="grid gap-3 sm:grid-cols-2">
          <label className="flex flex-col gap-1">
            <span className="text-sm font-medium text-text-700">Proceso</span>
            <select
              className="w-full rounded-md border border-border-default bg-surface-0 px-3 py-2 text-sm text-text-900 focus:border-brand-600 focus:outline-brand-600"
              value={borradorProceso}
              onChange={(evento) => {
                setBorradorProceso(evento.target.value as ProcesoSod | "");
                setBorradorAccion("");
              }}
            >
              <option value="">Todos</option>
              {procesos.map((p) => (
                <option key={p.proceso} value={p.proceso}>
                  {p.nombre}
                </option>
              ))}
            </select>
          </label>
          <label className="flex flex-col gap-1">
            <span className="text-sm font-medium text-text-700">
              Acción intentada
            </span>
            <select
              className="w-full rounded-md border border-border-default bg-surface-0 px-3 py-2 text-sm text-text-900 focus:border-brand-600 focus:outline-brand-600"
              value={borradorAccion}
              onChange={(evento) => setBorradorAccion(evento.target.value)}
              disabled={!borradorProceso}
            >
              <option value="">Todas</option>
              {acciones.map((accion) => (
                <option key={accion.codigo} value={accion.codigo}>
                  {accion.etiqueta}
                </option>
              ))}
            </select>
          </label>
          <FormField label="Usuario" htmlFor="conf-usuario" help="Nombre de usuario exacto">
            <TextInput
              id="conf-usuario"
              name="conf-usuario"
              value={borradorUsuario}
              onChange={(evento) => setBorradorUsuario(evento.target.value)}
            />
          </FormField>
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

      {conflictos.length === 0 ? (
        <EmptyState
          title="No hay intentos bloqueados"
          description="Cuando alguien intente realizar una acción incompatible con una regla vigente, aparecerá aquí."
        />
      ) : (
        <>
          <div
            className="relative overflow-x-auto"
            tabIndex={0}
            role="region"
            aria-label="Tabla de conflictos de segregación de funciones"
          >
            <table className="w-full min-w-[760px] border-collapse text-sm">
              <caption className="sr-only">
                Intentos bloqueados por segregación de funciones
              </caption>
              <thead>
                <tr className="border-b border-border-default text-left text-text-600">
                  <th scope="col" className="px-3 py-2 font-medium">
                    Fecha
                  </th>
                  <th scope="col" className="px-3 py-2 font-medium">
                    Usuario
                  </th>
                  <th scope="col" className="px-3 py-2 font-medium">
                    Regla
                  </th>
                  <th scope="col" className="px-3 py-2 font-medium">
                    Proceso
                  </th>
                  <th scope="col" className="px-3 py-2 font-medium">
                    Acción intentada
                  </th>
                  <th scope="col" className="px-3 py-2 font-medium">
                    Acción previa
                  </th>
                  <th scope="col" className="px-3 py-2 font-medium">
                    Objeto
                  </th>
                </tr>
              </thead>
              <tbody>
                {conflictos.map((c) => {
                  const rutaObjeto = rutaDeObjetoSod(
                    c.objeto_tipo,
                    c.objeto_id,
                  );
                  return (
                    <tr
                      key={c.id}
                      className="border-b border-border-subtle align-top"
                    >
                      <td className="px-3 py-2">{formatearFecha(c.fecha)}</td>
                      <td className="px-3 py-2">{c.usuario ?? "—"}</td>
                      <td className="px-3 py-2">
                        {c.regla_id ? (
                          <div className="flex flex-col gap-1">
                            <Link
                              to={`/gobierno/sod/${c.regla_id}`}
                              className="font-medium text-brand-700 underline"
                            >
                              {c.regla_codigo}
                            </Link>
                            <span className="text-text-600">
                              {c.regla_nombre}
                            </span>
                          </div>
                        ) : (
                          c.regla_codigo ?? "—"
                        )}
                      </td>
                      <td className="px-3 py-2">
                        {etiquetaProceso(c.proceso)}
                      </td>
                      <td className="px-3 py-2">
                        {c.accion_etiqueta ?? c.accion ?? "—"}
                      </td>
                      <td className="px-3 py-2">
                        {c.accion_previa_etiqueta ?? c.accion_previa ?? "—"}
                      </td>
                      <td className="px-3 py-2">
                        {rutaObjeto ? (
                          <Link
                            to={rutaObjeto}
                            className="font-medium text-brand-700 underline"
                          >
                            {c.objeto_tipo === "GovernmentAct"
                              ? "Abrir acto"
                              : "Abrir hallazgo"}
                          </Link>
                        ) : (
                          "—"
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
          {total > POR_PAGINA_CONFLICTOS_SOD && (
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
        {total} intentos bloqueados
      </p>
    </PageContent>
  );
}
