import { useState } from "react";
import { Link } from "react-router";
import { keepPreviousData, useQuery } from "@tanstack/react-query";

import { apiFetch } from "@/api/client";
import { useAutoridad } from "@/app/autoridad/AutoridadContext";
import { useCompany } from "@/app/contexts/CompanyContext";
import { EmptyState } from "@/components/EmptyState";
import { FormField } from "@/components/FormField";
import { LoadingState } from "@/components/LoadingState";
import { PageContent } from "@/layout/PageContent";
import { PageHeader } from "@/components/PageHeader";
import { ErrorDeCarga } from "@/modules/gobierno/ocupacion/ErrorDeCarga";
import { formatearFechaDeNegocio } from "@/lib/fecha-de-negocio";
import {
  CONSULTA_POLITICAS_COMISION,
  ETIQUETAS_ESTADO_POLITICA,
  type PoliticaComisionCatalogo,
  type PoliticasComisionListado,
  consultaDePoliticas,
  etiquetaDe,
} from "./politicasComision";

export function PoliticasComisionPage(): React.JSX.Element {
  const { tiene } = useAutoridad();
  const { activeCompanyId } = useCompany();

  const puedeVer = tiene("gobierno_comisiones:view", "empresa");
  const puedeConfigurar = tiene("gobierno_comisiones:configure", "empresa");

  const [q, setQ] = useState("");
  const [estado, setEstado] = useState("");

  const parametros = { q, estado };

  const listado = useQuery({
    queryKey: [...CONSULTA_POLITICAS_COMISION, activeCompanyId, "lista", parametros],
    queryFn: () =>
      apiFetch<PoliticasComisionListado>(
        `/gobierno/contrataciones/politicas-comision${consultaDePoliticas(parametros)}`,
      ),
    placeholderData: keepPreviousData,
    retry: false,
    enabled: puedeVer && Boolean(activeCompanyId),
  });

  const catalogo = useQuery<PoliticaComisionCatalogo>({
    queryKey: [...CONSULTA_POLITICAS_COMISION, activeCompanyId, "catalogo-politicas"],
    queryFn: () =>
      apiFetch<PoliticaComisionCatalogo>(
        "/gobierno/contrataciones/politicas-comision/catalogo",
      ),
    retry: false,
    enabled: puedeVer && Boolean(activeCompanyId),
  });

  if (!puedeVer) {
    return (
      <PageContent>
        <EmptyState
          title="Sin acceso"
          description="No tiene permisos para ver políticas de comisión."
        />
      </PageContent>
    );
  }

  if (!activeCompanyId) {
    return (
      <PageContent>
        <EmptyState
          title="Sin empresa"
          description="Seleccione una empresa activa."
        />
      </PageContent>
    );
  }

  const cambiarFiltro = (setter: (v: string) => void) => (v: string) => {
    setter(v);
  };

  const controlClase =
    "block w-full rounded-md border border-border-subtle bg-white px-3 py-2 text-sm text-text-900";

  return (
    <PageContent>
      <PageHeader
        crumbs={[
          { label: "Gobierno" },
          { label: "Contrataciones" },
          { label: "Políticas de comisión" },
        ]}
        title="Políticas de comisión"
        description="Cada ente define cómo se integran sus comisiones, su quórum y cómo deciden."
        actions={
          puedeConfigurar ? (
            <Link
              to={`${"/gobierno/contrataciones/politicas-comision"}/nueva`}
              className="inline-flex items-center rounded-md bg-brand-700 px-3 py-2 text-sm font-medium text-white hover:bg-brand-800"
            >
              Nueva política
            </Link>
          ) : undefined
        }
      />

      <section className="mt-4">
        <h2 className="sr-only">Filtros</h2>
        <div className="grid gap-4 sm:grid-cols-2">
          <FormField label="Estado" htmlFor="politica-estado">
            <select
              id="politica-estado"
              value={estado}
              onChange={(e) => cambiarFiltro(setEstado)(e.target.value)}
              className={controlClase}
            >
              <option value="">Todos</option>
              {(
                catalogo.data?.estados ??
                Object.entries(ETIQUETAS_ESTADO_POLITICA).map(([codigo, etiqueta]) => ({ codigo, etiqueta }))
              ).map((item) => (
                <option key={item.codigo} value={item.codigo}>
                  {item.etiqueta}
                </option>
              ))}
            </select>
          </FormField>
          <FormField label="Buscar" htmlFor="politica-buscar">
            <input
              id="politica-buscar"
              type="text"
              value={q}
              onChange={(e) => cambiarFiltro(setQ)(e.target.value)}
              placeholder="Nombre o código"
              className={controlClase}
            />
          </FormField>
        </div>
      </section>

      {listado.isLoading && <LoadingState />}

      {listado.isError && (
        <ErrorDeCarga
          message={
            listado.error instanceof Error
              ? listado.error.message
              : "No fue posible cargar las políticas de comisión."
          }
          onRetry={() => listado.refetch()}
        />
      )}

      {listado.data && listado.data.items.length === 0 && (
        <EmptyState
          title="No hay políticas de comisión"
          description="Aún no hay políticas de comisión con estos filtros."
          action={
            puedeConfigurar ? (
              <Link to="/gobierno/contrataciones/politicas-comision/nueva">Nueva política</Link>
            ) : undefined
          }
        />
      )}

      {listado.data && listado.data.items.length > 0 && (
        <div
          className="relative overflow-x-auto"
          tabIndex={0}
          role="region"
          aria-label="Tabla de políticas de comisión"
        >
          <table className="w-full text-sm">
            <caption className="sr-only">
              Listado de políticas de comisión
            </caption>
            <thead>
              <tr className="border-b border-border-subtle text-left text-xs uppercase text-text-600">
                <th scope="col" className="px-3 py-2">
                  Código
                </th>
                <th scope="col" className="px-3 py-2">
                  Versión
                </th>
                <th scope="col" className="px-3 py-2">
                  Nombre
                </th>
                <th scope="col" className="px-3 py-2">
                  Tipo de comisión
                </th>
                <th scope="col" className="px-3 py-2">
                  Estado
                </th>
                <th scope="col" className="px-3 py-2">
                  Vigencia
                </th>
                <th scope="col" className="px-3 py-2">
                  Comisiones
                </th>
              </tr>
            </thead>
            <tbody>
              {listado.data.items.map((p) => (
                <tr
                  key={p.id}
                  className="border-b border-border-subtle hover:bg-surface-50"
                >
                  <td className="px-3 py-2">
                    <Link
                      to={`${"/gobierno/contrataciones/politicas-comision"}/${p.id}`}
                      className="font-medium text-brand-700 underline"
                    >
                      {p.codigo}
                    </Link>
                  </td>
                  <td className="px-3 py-2">v{p.numero_version}</td>
                  <td className="px-3 py-2">{p.nombre}</td>
                  <td className="px-3 py-2">
                    {etiquetaDe(catalogo.data?.tipos_comision, p.tipo_comision)}
                  </td>
                  <td className="px-3 py-2">
                    {ETIQUETAS_ESTADO_POLITICA[p.estado] ?? p.estado}
                  </td>
                  <td className="px-3 py-2">
                    {p.vigente_desde
                      ? formatearFechaDeNegocio(p.vigente_desde)
                      : "—"}{" "}
                    —{" "}
                    {p.vigente_hasta
                      ? formatearFechaDeNegocio(p.vigente_hasta)
                      : "sin fin"}
                  </td>
                  <td className="px-3 py-2">{p.comisiones}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </PageContent>
  );
}
