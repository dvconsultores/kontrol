import { useState } from "react";
import { Link } from "react-router";
import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/api/client";
import { useAutoridad } from "@/app/autoridad/AutoridadContext";
import { useCompany } from "@/app/contexts/CompanyContext";
import { useNotifications } from "@/app/contexts/NotificationContext";
import { Button } from "@/components/Button";
import { EmptyState } from "@/components/EmptyState";
import { ErrorDeCarga } from "@/modules/gobierno/ocupacion/ErrorDeCarga";
import { LoadingState } from "@/components/LoadingState";
import { FormField } from "@/components/FormField";
import { PageContent } from "@/layout/PageContent";
import { PageHeader } from "@/components/PageHeader";
import { descargarArchivo } from "@/api/descargas";
import {
  CONSULTA_OCUPACION,
  consultaDeAsignaciones,
  ETIQUETAS_ESTADO_ASIGNACION,
  ETIQUETAS_SITUACION_ASIGNACION,
} from "@/modules/gobierno/api";
import type {
  AsignacionesListado,
  AsignacionResumen,
  CatalogoOcupacion,
} from "@/modules/gobierno/api";

export function AsignacionesPage() {
  const { tiene } = useAutoridad();
  const { activeCompanyId } = useCompany();
  const { notify } = useNotifications();
  const puedeVer = tiene("gobierno_ocupacion:view", "empresa");
  const puedeGestionar = tiene("gobierno_ocupacion:manage", "empresa");

  const [figura, setFigura] = useState("");
  const [estado, setEstado] = useState("");
  const [fecha, setFecha] = useState("");
  const [pagina, setPagina] = useState(1);
  const [exportando, setExportando] = useState(false);

  const catalogoQuery = useQuery({
    queryKey: [...CONSULTA_OCUPACION, activeCompanyId, "catalogo"],
    queryFn: () =>
      apiFetch<CatalogoOcupacion>("/gobierno/ocupacion/catalogo"),
    enabled: puedeVer && Boolean(activeCompanyId),
    retry: false,
  });

  const asignacionesQuery = useQuery({
    queryKey: [
      ...CONSULTA_OCUPACION,
      activeCompanyId,
      "asignaciones",
      { figura, estado, fecha, pagina },
    ],
    queryFn: () =>
      apiFetch<AsignacionesListado>(
        `/gobierno/ocupacion/asignaciones${consultaDeAsignaciones({
          figura,
          estado,
          fecha,
          pagina,
        })}`,
      ),
    enabled: puedeVer && Boolean(activeCompanyId),
    placeholderData: keepPreviousData,
    retry: false,
  });

  if (!puedeVer) {
    return (
      <PageContent>
        <EmptyState title="Sin acceso" description="No tiene permiso para ver esta sección." />
      </PageContent>
    );
  }

  if (!activeCompanyId) {
    return (
      <PageContent>
        <EmptyState title="Sin empresa" description="Seleccione una empresa para continuar." />
      </PageContent>
    );
  }

  const cambiarFiltros = (
    setter: (valor: string) => void,
    valor: string,
  ) => {
    setter(valor);
    setPagina(1);
  };

  const exportarCsv = async () => {
    if (exportando) return;
    setExportando(true);
    try {
      await descargarArchivo(
        `/gobierno/ocupacion/asignaciones.csv${consultaDeAsignaciones({
          figura,
          estado,
          fecha,
        })}`,
        "asignaciones.csv",
      );
    } catch {
      notify({ type: "error", title: "No fue posible exportar" });
    } finally {
      setExportando(false);
    }
  };

  const totalPaginas =
    asignacionesQuery.data?.total && asignacionesQuery.data.total > 0
      ? Math.ceil(asignacionesQuery.data.total / asignacionesQuery.data.por_pagina)
      : 0;

  return (
    <PageContent>
      <PageHeader
        crumbs={[
          { label: "Gobierno" },
          { label: "Ocupación de cargos", to: "/gobierno/ocupacion" },
          { label: "Asignaciones" },
        ]}
        title="Asignaciones"
        description="Titularidades, encargadurías, suplencias, comisiones y delegaciones registradas."
        actions={
          <div className="flex flex-wrap items-center gap-2">
            <Button variant="secondary" onClick={exportarCsv} disabled={exportando}>
              Exportar CSV
            </Button>
            {puedeGestionar ? (
              <Link
                to="/gobierno/ocupacion/asignaciones/nueva"
                className="inline-flex items-center rounded-md bg-brand-700 px-3 py-2 text-sm font-medium text-white hover:bg-brand-800"
              >
                Nueva asignación
              </Link>
            ) : null}
          </div>
        }
      />

      <section aria-labelledby="filtros-asignaciones" className="mb-8">
        <h2 id="filtros-asignaciones" className="sr-only">
          Filtros de asignaciones
        </h2>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          <FormField label="Figura" htmlFor="figura">
            <select
              id="figura"
              className="block w-full rounded-md border border-border-subtle bg-white px-3 py-2 text-sm text-text-900 focus:border-brand-500 focus:outline-none"
              value={figura}
              onChange={(e) => cambiarFiltros(setFigura, e.target.value)}
            >
              <option value="">Todas</option>
              {catalogoQuery.data?.figuras?.map((f) => (
                <option key={f.codigo} value={f.codigo}>
                  {f.etiqueta}
                </option>
              ))}
            </select>
          </FormField>
          <FormField label="Estado" htmlFor="estado">
            <select
              id="estado"
              className="block w-full rounded-md border border-border-subtle bg-white px-3 py-2 text-sm text-text-900 focus:border-brand-500 focus:outline-none"
              value={estado}
              onChange={(e) => cambiarFiltros(setEstado, e.target.value)}
            >
              <option value="">Todos</option>
              {Object.entries(ETIQUETAS_ESTADO_ASIGNACION).map(([valor, etiqueta]) => (
                <option key={valor} value={valor}>
                  {etiqueta}
                </option>
              ))}
            </select>
          </FormField>
          <FormField label="Fecha" htmlFor="fecha">
            <input
              type="date"
              id="fecha"
              className="block w-full rounded-md border border-border-subtle bg-white px-3 py-2 text-sm text-text-900 focus:border-brand-500 focus:outline-none"
              value={fecha}
              onChange={(e) => cambiarFiltros(setFecha, e.target.value)}
            />
          </FormField>
        </div>
      </section>

      {asignacionesQuery.isLoading ? (
        <LoadingState />
      ) : asignacionesQuery.isError ? (
        <ErrorDeCarga message="No fue posible cargar las asignaciones." onRetry={asignacionesQuery.refetch} />
      ) : asignacionesQuery.data?.items.length === 0 ? (
        <EmptyState
          title="Sin asignaciones"
          description="No hay asignaciones que coincidan con los filtros seleccionados."
        />
      ) : (
        <>
          <div
            className="relative overflow-x-auto"
            tabIndex={0}
            role="region"
            aria-label="Tabla de asignaciones de cargo"
          >
            <table className="w-full border-collapse text-left">
              <caption className="sr-only">Asignaciones de cargo</caption>
              <thead>
                <tr className="border-b border-border-subtle">
                  <th scope="col" className="px-3 py-2 text-sm font-medium text-text-700">
                    Código
                  </th>
                  <th scope="col" className="px-3 py-2 text-sm font-medium text-text-700">
                    Funcionario
                  </th>
                  <th scope="col" className="px-3 py-2 text-sm font-medium text-text-700">
                    Cargo
                  </th>
                  <th scope="col" className="px-3 py-2 text-sm font-medium text-text-700">
                    Figura
                  </th>
                  <th scope="col" className="px-3 py-2 text-sm font-medium text-text-700">
                    Vigencia
                  </th>
                  <th scope="col" className="px-3 py-2 text-sm font-medium text-text-700">
                    Situación
                  </th>
                  <th scope="col" className="px-3 py-2 text-sm font-medium text-text-700">
                    Acto
                  </th>
                </tr>
              </thead>
              <tbody>
                {asignacionesQuery.data?.items.map((a: AsignacionResumen) => (
                  <tr key={a.id} className="border-b border-border-subtle">
                    <td className="px-3 py-2 text-sm text-text-900">
                      <Link
                        to={`/gobierno/ocupacion/asignaciones/${a.id}`}
                        className="font-medium text-brand-700 underline"
                      >
                        {a.codigo}
                      </Link>
                    </td>
                    <td className="px-3 py-2 text-sm text-text-900">
                      {a.funcionario.nombre}
                      <span className="block text-xs text-text-500">
                        {a.funcionario.documento}
                      </span>
                    </td>
                    <td className="px-3 py-2 text-sm text-text-900">{a.cargo.nombre}</td>
                    <td className="px-3 py-2 text-sm text-text-900">
                      {a.figura_etiqueta}
                    </td>
                    <td className="px-3 py-2 text-sm text-text-900">{a.situacion}</td>
                    <td className="px-3 py-2 text-sm text-text-900">
                      {ETIQUETAS_SITUACION_ASIGNACION[a.situacion] ?? a.situacion}
                    </td>
                    <td className="px-3 py-2 text-sm text-text-900">
                      {a.acto.tipo} {a.acto.numero}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="mt-4 flex flex-wrap items-center justify-between gap-2">
            <Button
              variant="secondary"
              disabled={pagina <= 1 || asignacionesQuery.isFetching}
              onClick={() => setPagina((p) => Math.max(1, p - 1))}
            >
              Anterior
            </Button>
            <p className="text-sm text-text-700">
              Página {pagina} de {totalPaginas}
            </p>
            <Button
              variant="secondary"
              disabled={pagina >= totalPaginas || asignacionesQuery.isFetching}
              onClick={() => setPagina((p) => p + 1)}
            >
              Siguiente
            </Button>
          </div>
        </>
      )}
    </PageContent>
  );
}
