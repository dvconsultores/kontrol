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
  CONSULTA_POLITICAS_ASIGNACION,
  RUTA_POLITICAS_ASIGNACION,
  type PoliticaAsignacionCatalogo,
  type PoliticasAsignacionListado,
  consultaDePoliticasAsignacion,
  etiquetaDeCodigo,
} from "./politicasAsignacion";

export function PoliticasAsignacionPage(): React.JSX.Element {
  const { tiene } = useAutoridad();
  const { activeCompanyId } = useCompany();

  const puedeVer = tiene("gobierno_ocupacion:view", "empresa");
  const puedeConfigurar = tiene("gobierno_ocupacion:configure", "empresa");

  const [q, setQ] = useState("");
  const [estado, setEstado] = useState("");
  const [figura, setFigura] = useState("");

  const parametros = { q, estado, figura };

  const listado = useQuery({
    queryKey: [...CONSULTA_POLITICAS_ASIGNACION, activeCompanyId, "lista", parametros],
    queryFn: () =>
      apiFetch<PoliticasAsignacionListado>(
        `${RUTA_POLITICAS_ASIGNACION}${consultaDePoliticasAsignacion(parametros)}`,
      ),
    placeholderData: keepPreviousData,
    retry: false,
    enabled: puedeVer && Boolean(activeCompanyId),
  });

  const catalogo = useQuery<PoliticaAsignacionCatalogo>({
    queryKey: [...CONSULTA_POLITICAS_ASIGNACION, activeCompanyId, "catalogo-politicas"],
    queryFn: () =>
      apiFetch<PoliticaAsignacionCatalogo>(
        `${RUTA_POLITICAS_ASIGNACION}/catalogo`,
      ),
    retry: false,
    enabled: puedeVer && Boolean(activeCompanyId),
  });

  if (!puedeVer) {
    return (
      <PageContent>
        <EmptyState
          title="Sin acceso"
          description="No tiene permisos para ver políticas de asignación."
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
          { label: "Ocupación de cargos" },
          { label: "Políticas de asignación" },
        ]}
        title="Políticas de asignación"
        description="Reglas del ente para titulares, encargadurías, suplencias, comisiones de servicio y delegaciones. Los pisos legales del régimen del ente se aplican siempre."
        actions={
          puedeConfigurar ? (
            <Link
              to={`${RUTA_POLITICAS_ASIGNACION}/nueva`}
              className="inline-flex items-center rounded-md bg-brand-700 px-3 py-2 text-sm font-medium text-white hover:bg-brand-800"
            >
              Nueva política
            </Link>
          ) : undefined
        }
      />

      <section className="mt-4">
        <h2 className="sr-only">Filtros</h2>
        <div className="grid gap-4 sm:grid-cols-3">
          <FormField label="Estado" htmlFor="politica-estado">
            <select
              id="politica-estado"
              value={estado}
              onChange={(e) => cambiarFiltro(setEstado)(e.target.value)}
              className={controlClase}
            >
              <option value="">Todos</option>
              {(catalogo.data?.estados ?? []).map((item) => (
                <option key={item.codigo} value={item.codigo}>
                  {item.etiqueta}
                </option>
              ))}
            </select>
          </FormField>
          <FormField label="Figura" htmlFor="politica-figura">
            <select
              id="politica-figura"
              value={figura}
              onChange={(e) => cambiarFiltro(setFigura)(e.target.value)}
              className={controlClase}
            >
              <option value="">Todas</option>
              {(catalogo.data?.figuras ?? []).map((item) => (
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
              placeholder="Código o nombre"
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
              : "No fue posible cargar las políticas de asignación."
          }
          onRetry={() => listado.refetch()}
        />
      )}

      {listado.data && listado.data.items.length === 0 && (
        <EmptyState
          title="No hay políticas de asignación"
          description="Sin política, cada asignación aplica solo los pisos legales del régimen del ente."
          action={
            puedeConfigurar ? (
              <Link to={`${RUTA_POLITICAS_ASIGNACION}/nueva`}>Nueva política</Link>
            ) : undefined
          }
        />
      )}

      {listado.data && listado.data.items.length > 0 && (
        <div
          className="relative overflow-x-auto"
          tabIndex={0}
          role="region"
          aria-label="Listado desplazable de políticas de asignación"
        >
          <table className="w-full text-sm" aria-label="Tabla de políticas de asignación">
            <caption className="sr-only">
              Listado de políticas de asignación
            </caption>
            <thead>
              <tr className="border-b border-border-subtle text-left text-xs uppercase text-text-600">
                <th scope="col" className="px-3 py-2">
                  Código
                </th>
                <th scope="col" className="px-3 py-2">
                  Nombre
                </th>
                <th scope="col" className="px-3 py-2">
                  Figura
                </th>
                <th scope="col" className="px-3 py-2">
                  Versión
                </th>
                <th scope="col" className="px-3 py-2">
                  Estado
                </th>
                <th scope="col" className="px-3 py-2">
                  Vigencia
                </th>
                <th scope="col" className="px-3 py-2">
                  Asignaciones
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
                      to={`${RUTA_POLITICAS_ASIGNACION}/${p.id}`}
                      className="font-medium text-brand-700 underline"
                    >
                      {p.codigo}
                    </Link>
                  </td>
                  <td className="px-3 py-2">{p.nombre}</td>
                  <td className="px-3 py-2">
                    {etiquetaDeCodigo(catalogo.data?.figuras, p.figura) ?? p.figura_etiqueta}
                  </td>
                  <td className="px-3 py-2">v{p.numero_version}</td>
                  <td className="px-3 py-2">
                    {etiquetaDeCodigo(catalogo.data?.estados, p.estado) ?? p.estado_etiqueta}
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
                  <td className="px-3 py-2">{p.asignaciones}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </PageContent>
  );
}
