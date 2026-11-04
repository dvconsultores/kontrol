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
import { formatearFecha } from "@/i18n";
import { VerificarPaquete } from "@/modules/gobierno/paquetes/VerificarPaquete";
import {
  CONSULTA_PAQUETES,
  POR_PAGINA_PAQUETES,
  consultaDePaquetes,
  abreviarHuella,
  formatearBytes,
  type PaquetesListado,
} from "@/modules/gobierno/api";

export function PaquetesPage() {
  const { tiene } = useAutoridad();
  const { activeCompanyId } = useCompany();
  const [pagina, setPagina] = useState(1);

  const puedeVer = tiene("gobierno_paquetes:view", "empresa");

  const consultaPaquetes = useQuery({
    queryKey: [...CONSULTA_PAQUETES, activeCompanyId, pagina],
    queryFn: () =>
      apiFetch<PaquetesListado>(
        `/gobierno/paquetes${consultaDePaquetes(
          {},
          { pagina, por_pagina: POR_PAGINA_PAQUETES },
        )}`,
      ),
    enabled: puedeVer && Boolean(activeCompanyId),
    retry: false,
  });

  const cabecera = (
    <PageHeader
      crumbs={[{ label: "Gobierno" }, { label: "Paquetes de auditoría" }]}
      title="Paquetes de auditoría"
      description="Paquetes exportables generados desde muestras de auditoría, con su índice, manifiesto y huellas, y la verificación de cualquier copia."
    />
  );

  if (!puedeVer) {
    return (
      <PageContent>
        {cabecera}
        <EmptyState
          title="Sin acceso"
          description="No tiene permiso para ver los paquetes de auditoría."
        />
      </PageContent>
    );
  }

  if (consultaPaquetes.isLoading) {
    return (
      <PageContent>
        {cabecera}
        <LoadingState label="Cargando paquetes…" />
      </PageContent>
    );
  }

  if (consultaPaquetes.isError) {
    const error = consultaPaquetes.error;
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
            description="No tiene permiso para ver los paquetes de auditoría."
          />
        </PageContent>
      );
    }
    return (
      <PageContent>
        {cabecera}
        <ErrorState
          message="No fue posible cargar los paquetes."
          onRetry={() => void consultaPaquetes.refetch()}
        />
      </PageContent>
    );
  }

  if (!consultaPaquetes.data) {
    return (
      <PageContent>
        {cabecera}
        <EmptyState
          title="Aún no se ha generado ningún paquete"
          description="Genere uno desde una muestra en Gobierno › Auditoría institucional."
        />
      </PageContent>
    );
  }

  const paquetes = consultaPaquetes.data.items;
  const total = consultaPaquetes.data.total;
  const totalPaginas = Math.max(1, Math.ceil(total / POR_PAGINA_PAQUETES));

  return (
    <PageContent>
      {cabecera}
      {paquetes.length === 0 ? (
        <EmptyState
          title="Aún no se ha generado ningún paquete"
          description="Genere uno desde una muestra en Gobierno › Auditoría institucional."
        />
      ) : (
        <>
          <div
            className="relative overflow-x-auto"
            tabIndex={0}
            role="region"
            aria-label="Tabla de paquetes de auditoría"
          >
            <table className="w-full min-w-[760px] border-collapse text-sm">
              <caption className="sr-only">
                Paquetes de auditoría generados
              </caption>
              <thead>
                <tr className="border-b border-border-default text-left text-text-600">
                  <th scope="col" className="px-3 py-2 font-medium">
                    Código
                  </th>
                  <th scope="col" className="px-3 py-2 font-medium">
                    Muestra
                  </th>
                  <th scope="col" className="px-3 py-2 font-medium">
                    Generado
                  </th>
                  <th scope="col" className="px-3 py-2 font-medium">
                    Por
                  </th>
                  <th scope="col" className="px-3 py-2 font-medium">
                    Contenido
                  </th>
                  <th scope="col" className="px-3 py-2 font-medium">
                    Tamaño
                  </th>
                  <th scope="col" className="px-3 py-2 font-medium">
                    Huella
                  </th>
                </tr>
              </thead>
              <tbody>
                {paquetes.map((p) => (
                  <tr
                    key={p.id}
                    className="border-b border-border-subtle align-top"
                  >
                    <td className="px-3 py-2 text-text-900">
                      <Link
                        to={`/gobierno/paquetes/${p.id}`}
                        className="font-medium text-brand-700 underline"
                        aria-label={`Abrir el paquete ${p.codigo}`}
                      >
                        {p.codigo}
                      </Link>
                    </td>
                    <td className="px-3 py-2 text-text-900">
                      {p.muestra_codigo}
                    </td>
                    <td className="px-3 py-2 text-text-700">
                      {formatearFecha(p.generado_en)}
                    </td>
                    <td className="px-3 py-2 text-text-700">
                      {p.generado_por ?? "—"}
                    </td>
                    <td className="px-3 py-2 text-text-700">
                      {`${p.eventos} eventos · ${p.documentos_incluidos} documentos · ${p.hallazgos} hallazgos`}
                    </td>
                    <td className="px-3 py-2 text-text-700">
                      {formatearBytes(p.bytes)}
                    </td>
                    <td className="px-3 py-2 text-text-900">
                      <span className="font-mono text-xs">
                        {abreviarHuella(p.huella_paquete)}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {total > POR_PAGINA_PAQUETES && (
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
      <VerificarPaquete />
    </PageContent>
  );
}
