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
  CONSULTA_IDENTIDAD,
  consultaDeVinculos,
  ETIQUETAS_ESTADO_VINCULO,
  ETIQUETAS_SITUACION_VINCULO,
} from "@/modules/gobierno/api";
import type {
  VinculosListado,
  VinculoResumen,
  CatalogoIdentidad,
} from "@/modules/gobierno/api";

export function VinculosPage() {
  const { tiene } = useAutoridad();
  const { activeCompanyId } = useCompany();
  const { notify } = useNotifications();
  const puedeVer = tiene("gobierno_identidad:view", "empresa");
  const puedeGestionar = tiene("gobierno_identidad:manage", "empresa");

  const [estado, setEstado] = useState("");
  const [fecha, setFecha] = useState("");
  const [pagina, setPagina] = useState(1);
  const [exportando, setExportando] = useState(false);

  const catalogoQuery = useQuery({
    queryKey: [...CONSULTA_IDENTIDAD, activeCompanyId, "catalogo"],
    queryFn: () =>
      apiFetch<CatalogoIdentidad>("/gobierno/identidad/catalogo"),
    enabled: puedeVer && Boolean(activeCompanyId),
    retry: false,
  });

  const vinculosQuery = useQuery({
    queryKey: [
      ...CONSULTA_IDENTIDAD,
      activeCompanyId,
      "vinculos",
      { estado, fecha, pagina },
    ],
    queryFn: () =>
      apiFetch<VinculosListado>(
        `/gobierno/identidad/vinculos${consultaDeVinculos({
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
        `/gobierno/identidad/vinculos.csv${consultaDeVinculos({
          estado,
          fecha,
        })}`,
        "vinculos.csv",
      );
    } catch {
      notify({ type: "error", title: "No fue posible exportar" });
    } finally {
      setExportando(false);
    }
  };

  const totalPaginas =
    vinculosQuery.data?.total && vinculosQuery.data.total > 0
      ? Math.ceil(vinculosQuery.data.total / vinculosQuery.data.por_pagina)
      : 0;

  return (
    <PageContent>
      <PageHeader
        crumbs={[
          { label: "Gobierno" },
          { label: "Identidad institucional", to: "/gobierno/identidad" },
          { label: "Vínculos" },
        ]}
        title="Identidad institucional"
        description="Qué cuenta corresponde a qué funcionario, y desde cuándo. La autoridad no viene del vínculo: se deriva de la ocupación del cargo."
        actions={
          <div className="flex flex-wrap items-center gap-2">
            <Button variant="secondary" onClick={exportarCsv} disabled={exportando}>
              Exportar CSV
            </Button>
            {puedeGestionar ? (
              <Link
                to="/gobierno/identidad/vinculos/nuevo"
                className="inline-flex items-center rounded-md bg-brand-700 px-3 py-2 text-sm font-medium text-white hover:bg-brand-800"
              >
                Nuevo vínculo
              </Link>
            ) : null}
            <Link
              to="/gobierno/identidad/categorias"
              className="inline-flex items-center rounded-md bg-white px-3 py-2 text-sm font-medium text-text-900 border border-border-subtle hover:bg-gray-50"
            >
              Categorías y separación
            </Link>
            <Link
              to="/gobierno/identidad/mi-contexto"
              className="inline-flex items-center rounded-md bg-white px-3 py-2 text-sm font-medium text-text-900 border border-border-subtle hover:bg-gray-50"
            >
              Mi contexto institucional
            </Link>
          </div>
        }
      />

      <section aria-labelledby="filtros-vinculos" className="mb-8">
        <h2 id="filtros-vinculos" className="sr-only">
          Filtros de vínculos
        </h2>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-2">
          <FormField label="Estado" htmlFor="estado">
            <select
              id="estado"
              className="block w-full rounded-md border border-border-subtle bg-white px-3 py-2 text-sm text-text-900 focus:border-brand-500 focus:outline-none"
              value={estado}
              onChange={(e) => cambiarFiltros(setEstado, e.target.value)}
            >
              <option value="">Todos</option>
              {(catalogoQuery.data?.estados ?? []).map((valor) => (
                <option key={valor} value={valor}>
                  {ETIQUETAS_ESTADO_VINCULO[valor]}
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

      {vinculosQuery.isLoading ? (
        <LoadingState />
      ) : vinculosQuery.isError ? (
        <ErrorDeCarga message="No fue posible cargar los vínculos." onRetry={vinculosQuery.refetch} />
      ) : vinculosQuery.data?.items.length === 0 ? (
        <EmptyState
          title="Sin vínculos"
          description="Aún no hay vínculos registrados con estos filtros."
        />
      ) : (
        <>
          <div
            className="relative overflow-x-auto"
            tabIndex={0}
            role="region"
            aria-label="Tabla de vínculos cuenta-funcionario"
          >
            <table className="w-full border-collapse text-left">
              <caption className="sr-only">Vínculos cuenta–funcionario</caption>
              <thead>
                <tr className="border-b border-border-subtle">
                  <th scope="col" className="px-3 py-2 text-sm font-medium text-text-700">
                    Código
                  </th>
                  <th scope="col" className="px-3 py-2 text-sm font-medium text-text-700">
                    Cuenta
                  </th>
                  <th scope="col" className="px-3 py-2 text-sm font-medium text-text-700">
                    Funcionario
                  </th>
                  <th scope="col" className="px-3 py-2 text-sm font-medium text-text-700">
                    Vigencia
                  </th>
                  <th scope="col" className="px-3 py-2 text-sm font-medium text-text-700">
                    Estado
                  </th>
                  <th scope="col" className="px-3 py-2 text-sm font-medium text-text-700">
                    Situación
                  </th>
                </tr>
              </thead>
              <tbody>
                {vinculosQuery.data?.items.map((v: VinculoResumen) => (
                  <tr key={v.id} className="border-b border-border-subtle">
                    <td className="px-3 py-2 text-sm text-text-900">
                      <Link
                        to={`/gobierno/identidad/vinculos/${v.id}`}
                        className="font-medium text-brand-700 underline"
                      >
                        {v.codigo}
                      </Link>
                    </td>
                    <td className="px-3 py-2 text-sm text-text-900">
                      {v.cuenta.usuario}
                    </td>
                    <td className="px-3 py-2 text-sm text-text-900">
                      {v.funcionario.nombre}
                      <span className="block text-xs text-text-500">
                        {v.funcionario.documento}
                      </span>
                    </td>
                    <td className="px-3 py-2 text-sm text-text-900">
                      {v.desde}
                      {v.fin_efectivo ?? v.hasta ? (
                        <>
                          {" — "}
                          {v.fin_efectivo ?? v.hasta}
                        </>
                      ) : (
                        "Sin fecha final"
                      )}
                    </td>
                    <td className="px-3 py-2 text-sm text-text-900">
                      {ETIQUETAS_ESTADO_VINCULO[v.status]}
                    </td>
                    <td className="px-3 py-2 text-sm text-text-900">
                      {ETIQUETAS_SITUACION_VINCULO[v.situacion]}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="mt-4 flex flex-wrap items-center justify-between gap-2">
            <Button
              variant="secondary"
              disabled={pagina <= 1 || vinculosQuery.isFetching}
              onClick={() => setPagina((p) => Math.max(1, p - 1))}
            >
              Anterior
            </Button>
            <p className="text-sm text-text-700">
              Página {pagina} de {totalPaginas}
            </p>
            <Button
              variant="secondary"
              disabled={pagina >= totalPaginas || vinculosQuery.isFetching}
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
