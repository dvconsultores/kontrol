import { useState } from "react";
import { Link } from "react-router";
import { keepPreviousData, useQuery } from "@tanstack/react-query";

import { apiFetch } from "@/api/client";
import { descargarArchivo } from "@/api/descargas";
import { useAutoridad } from "@/app/autoridad/AutoridadContext";
import { useCompany } from "@/app/contexts/CompanyContext";
import { useNotifications } from "@/app/contexts/NotificationContext";
import { Button } from "@/components/Button";
import { EmptyState } from "@/components/EmptyState";
import { FormField } from "@/components/FormField";
import { LoadingState } from "@/components/LoadingState";
import { PageContent } from "@/layout/PageContent";
import { PageHeader } from "@/components/PageHeader";
import { ErrorDeCarga } from "@/modules/gobierno/ocupacion/ErrorDeCarga";
import { formatearFechaDeNegocio } from "@/lib/fecha-de-negocio";
import {
  CONSULTA_COMISIONES,
  ETIQUETAS_ESTADO_COMISION,
  ETIQUETAS_SITUACION_COMISION,
  ETIQUETAS_TIPO_COMISION,
  type ComisionesListado,
  consultaDeComisiones,
} from "@/modules/gobierno/api";



export function ComisionesPage(): React.JSX.Element {
  const { tiene } = useAutoridad();
  const { activeCompanyId } = useCompany();
  const { notify } = useNotifications();

  const puedeVer = tiene("gobierno_comisiones:view", "empresa");
  const puedeGestionar = tiene("gobierno_comisiones:manage", "empresa");

  const [q, setQ] = useState("");
  const [status, setStatus] = useState("");
  const [tipo, setTipo] = useState("");
  const [situacion, setSituacion] = useState("");
  const [pagina, setPagina] = useState(1);

  const parametros = { q, status, tipo, situacion, pagina };

  const listado = useQuery({
    queryKey: [...CONSULTA_COMISIONES, activeCompanyId, "lista", parametros],
    queryFn: () =>
      apiFetch<ComisionesListado>(
        `/gobierno/contrataciones/comisiones${consultaDeComisiones(parametros)}`,
      ),
    placeholderData: keepPreviousData,
    retry: false,
    enabled: puedeVer && Boolean(activeCompanyId),
  });

  if (!puedeVer) {
    return (
      <PageContent>
        <EmptyState
          title="Sin acceso"
          description="No tiene permisos para ver comisiones."
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
    setPagina(1);
  };

  const controlClase =
    "block w-full rounded-md border border-border-subtle bg-white px-3 py-2 text-sm text-text-900";

  const exportarCsv = async () => {
    try {
      await descargarArchivo(
        `/gobierno/contrataciones/comisiones.csv${consultaDeComisiones({
          q,
          status,
          tipo,
          situacion,
        })}`,
        "comisiones.csv",
      );
    } catch {
      notify({ type: "error", title: "No se pudo exportar el CSV" });
    }
  };

  const totalPaginas =
    listado.data?.total && listado.data.por_pagina
      ? Math.ceil(listado.data.total / listado.data.por_pagina)
      : 0;

  return (
    <PageContent>
      <PageHeader
        crumbs={[
          { label: "Gobierno" },
          { label: "Contrataciones" },
          { label: "Comisiones" },
        ]}
        title="Comisiones de contrataciones"
        description="Quiénes integran cada comisión, por qué acto y en qué período."
        actions={
          <div className="flex items-center gap-2">
            <Button variant="secondary" onClick={exportarCsv}>
              Exportar CSV
            </Button>
            {puedeGestionar && (
              <Link
                to="/gobierno/contrataciones/comisiones/nueva"
                className="inline-flex items-center rounded-md bg-brand-700 px-3 py-2 text-sm font-medium text-white hover:bg-brand-800"
              >
                Nueva comisión
              </Link>
            )}
          </div>
        }
      />

      <section className="mt-4">
        <h2 className="sr-only">Filtros</h2>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <FormField label="Buscar" htmlFor="comision-buscar">
            <input
              id="comision-buscar"
              type="text"
              value={q}
              onChange={(e) => cambiarFiltro(setQ)(e.target.value)}
              placeholder="Nombre o código"
              className={controlClase}
            />
          </FormField>
          <FormField label="Estado" htmlFor="comision-estado">
            <select
              id="comision-estado"
              value={status}
              onChange={(e) => cambiarFiltro(setStatus)(e.target.value)}
              className={controlClase}
            >
              <option value="">Todos</option>
              {Object.entries(ETIQUETAS_ESTADO_COMISION).map(([k, v]) => (
                <option key={k} value={k}>
                  {v}
                </option>
              ))}
            </select>
          </FormField>
          <FormField label="Tipo" htmlFor="comision-tipo">
            <select
              id="comision-tipo"
              value={tipo}
              onChange={(e) => cambiarFiltro(setTipo)(e.target.value)}
              className={controlClase}
            >
              <option value="">Todos</option>
              {Object.entries(ETIQUETAS_TIPO_COMISION).map(([k, v]) => (
                <option key={k} value={k}>
                  {v}
                </option>
              ))}
            </select>
          </FormField>
          <FormField label="Vigencia" htmlFor="comision-situacion">
            <select
              id="comision-situacion"
              value={situacion}
              onChange={(e) => cambiarFiltro(setSituacion)(e.target.value)}
              className={controlClase}
            >
              <option value="">Todas</option>
              {Object.entries(ETIQUETAS_SITUACION_COMISION).map(([k, v]) => (
                <option key={k} value={k}>
                  {v}
                </option>
              ))}
            </select>
          </FormField>
        </div>
      </section>

      {listado.isLoading && <LoadingState />}

      {listado.isError && (
        <ErrorDeCarga
          message={
            listado.error instanceof Error
              ? listado.error.message
              : "No fue posible cargar las comisiones."
          }
          onRetry={() => listado.refetch()}
        />
      )}

      {listado.data && listado.data.items.length === 0 && (
        <EmptyState
          title="Sin comisiones"
          description="Aún no hay comisiones con estos filtros."
        />
      )}

      {listado.data && listado.data.items.length > 0 && (
        <>
          <div
            className="relative overflow-x-auto"
            tabIndex={0}
            role="region"
            aria-label="Tabla de comisiones de contrataciones"
          >
            <table className="w-full text-sm">
              <caption className="sr-only">
                Listado de comisiones de contrataciones
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
                    Tipo
                  </th>
                  <th scope="col" className="px-3 py-2">
                    Estado
                  </th>
                  <th scope="col" className="px-3 py-2">
                    Vigencia
                  </th>
                  <th scope="col" className="px-3 py-2">
                    Período
                  </th>
                  <th scope="col" className="px-3 py-2">
                    Acto
                  </th>
                  <th scope="col" className="px-3 py-2">
                    Miembros
                  </th>
                </tr>
              </thead>
              <tbody>
                {listado.data.items.map((c) => (
                  <tr
                    key={c.id}
                    className="border-b border-border-subtle hover:bg-surface-50"
                  >
                    <td className="px-3 py-2">
                      <Link
                        to={`/gobierno/contrataciones/comisiones/${c.id}`}
                        className="font-medium text-brand-700 underline"
                      >
                        {c.codigo}
                      </Link>
                    </td>
                    <td className="px-3 py-2">{c.nombre}</td>
                    <td className="px-3 py-2">
                      {ETIQUETAS_TIPO_COMISION[c.tipo] ?? c.tipo}
                    </td>
                    <td className="px-3 py-2">
                      {ETIQUETAS_ESTADO_COMISION[c.status] ?? c.status}
                    </td>
                    <td className="px-3 py-2">
                      {ETIQUETAS_SITUACION_COMISION[c.situacion] ?? c.situacion}
                    </td>
                    <td className="px-3 py-2">
                      {formatearFechaDeNegocio(c.desde)} —{" "}
                      {c.hasta
                        ? formatearFechaDeNegocio(c.hasta)
                        : "Sin fecha final"}
                    </td>
                    <td className="px-3 py-2">{c.acto?.etiqueta ?? "Sin acto"}</td>
                    <td className="px-3 py-2">
                      {c.miembros_principales} principales · {c.miembros_total}{" "}
                      en total
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="mt-4 flex items-center justify-between">
            <Button
              variant="secondary"
              onClick={() => setPagina((p) => Math.max(1, p - 1))}
              disabled={pagina <= 1}
            >
              Anterior
            </Button>
            <span className="text-sm text-text-700">
              Página {pagina} de {totalPaginas}
            </span>
            <Button
              variant="secondary"
              onClick={() => setPagina((p) => Math.min(totalPaginas, p + 1))}
              disabled={pagina >= totalPaginas}
            >
              Siguiente
            </Button>
          </div>
        </>
      )}
    </PageContent>
  );
}
