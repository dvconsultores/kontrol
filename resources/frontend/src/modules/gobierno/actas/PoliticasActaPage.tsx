import { useState } from "react";
import { Link } from "react-router";
import { keepPreviousData, useQuery } from "@tanstack/react-query";

import { useAutoridad } from "@/app/autoridad/AutoridadContext";
import { useCompany } from "@/app/contexts/CompanyContext";
import { EmptyState } from "@/components/EmptyState";
import { ErrorState } from "@/components/ErrorState";
import { FormField } from "@/components/FormField";
import { LoadingState } from "@/components/LoadingState";
import { PageContent } from "@/layout/PageContent";
import { PageHeader } from "@/components/PageHeader";
import { formatearFechaDeNegocio } from "@/lib/fecha-de-negocio";
import { listarPoliticasActa } from "./politicasActa";

export function PoliticasActaPage(): React.JSX.Element {
  const { tiene } = useAutoridad();
  const { activeCompanyId } = useCompany();

  const puedeVer = tiene("gobierno_actas:view", "empresa");
  const puedeConfigurar = tiene("gobierno_actas:configure", "empresa");

  const [q, setQ] = useState("");
  const [estado, setEstado] = useState("");

  const listado = useQuery({
    queryKey: ["gobierno-actas-politicas", activeCompanyId, estado, q],
    queryFn: () => listarPoliticasActa({ estado, q }),
    placeholderData: keepPreviousData,
    retry: false,
    enabled: puedeVer && Boolean(activeCompanyId),
  });

  if (!puedeVer) {
    return (
      <PageContent>
        <ErrorState message="No tiene permiso para ver las políticas de actas." />
      </PageContent>
    );
  }

  return (
    <PageContent>
      <PageHeader
        title="Políticas de actas"
        description="Requisitos de las actas de entrega del ente sobre el catálogo legal de N34."
        actions={
          puedeConfigurar ? (
            <Link
              to="/gobierno/actas-entrega/politicas/nueva"
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
              onChange={(e) => setEstado(e.target.value)}
              className="block w-full rounded-md border border-border-subtle bg-white px-3 py-2 text-sm text-text-900"
            >
              <option value="">Todos</option>
              <option value="BORRADOR">Borrador</option>
              <option value="VIGENTE">Vigente</option>
              <option value="CERRADA">Cerrada</option>
            </select>
          </FormField>
          <FormField label="Buscar" htmlFor="politica-buscar">
            <input
              id="politica-buscar"
              type="text"
              value={q}
              onChange={(e) => setQ(e.target.value)}
              placeholder="Código o nombre"
              className="block w-full rounded-md border border-border-subtle bg-white px-3 py-2 text-sm text-text-900"
            />
          </FormField>
        </div>
      </section>

      {listado.isLoading && <LoadingState />}

      {listado.isError && (
        <ErrorState message="No fue posible cargar las políticas de actas." />
      )}

      {listado.data && listado.data.items.length === 0 && (
        <EmptyState title="Sin políticas de actas" />
      )}

      {listado.data && listado.data.items.length > 0 && (
        <div
          className="relative overflow-x-auto"
          tabIndex={0}
          role="region"
          aria-label="Listado desplazable de políticas de actas"
        >
          <table className="w-full text-sm" aria-label="Políticas de actas">
            <caption className="sr-only">Listado de políticas de actas</caption>
            <thead>
              <tr className="border-b border-border-subtle text-left text-xs uppercase text-text-600">
                <th scope="col" className="px-3 py-2">Código</th>
                <th scope="col" className="px-3 py-2">Versión</th>
                <th scope="col" className="px-3 py-2">Nombre</th>
                <th scope="col" className="px-3 py-2">Estado</th>
                <th scope="col" className="px-3 py-2">Vigencia</th>
                <th scope="col" className="px-3 py-2">Supuestos declarados</th>
                <th scope="col" className="px-3 py-2">Requisitos</th>
              </tr>
            </thead>
            <tbody>
              {listado.data.items.map((p) => (
                <tr key={p.id} className="border-b border-border-subtle hover:bg-surface-50">
                  <td className="px-3 py-2">
                    <Link
                      to={`/gobierno/actas-entrega/politicas/${p.id}`}
                      className="font-medium text-brand-700 underline"
                    >
                      {p.codigo}
                    </Link>
                  </td>
                  <td className="px-3 py-2">v{p.numero_version}</td>
                  <td className="px-3 py-2">{p.nombre}</td>
                  <td className="px-3 py-2">{p.estado_etiqueta}</td>
                  <td className="px-3 py-2">
                    {formatearFechaDeNegocio(p.vigente_desde)} —{" "}
                    {p.vigente_hasta ? formatearFechaDeNegocio(p.vigente_hasta) : "sin fin"}
                  </td>
                  <td className="px-3 py-2">{p.total_vinculos}</td>
                  <td className="px-3 py-2">{p.total_requisitos}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </PageContent>
  );
}
