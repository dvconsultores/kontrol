import { useState } from "react";
import { Link } from "react-router";
import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { useAutoridad } from "@/app/autoridad/AutoridadContext";
import { useCompany } from "@/app/contexts/CompanyContext";
import { EmptyState } from "@/components/EmptyState";
import { LoadingState } from "@/components/LoadingState";
import { PageHeader } from "@/components/PageHeader";
import { TextInput } from "@/components/TextInput";
import { PageContent } from "@/layout/PageContent";
import { ErrorDeCarga } from "@/modules/gobierno/ocupacion/ErrorDeCarga";
import { formatearFechaDeNegocio } from "@/lib/fecha-de-negocio";
import { apiFetch } from "@/api/client";
import {
  CONSULTA_EXPEDIENTES,
  consultaDeExpedientes,
  type ExpedienteCatalogo,
  type ExpedienteOpciones,
  type ExpedientesListado,
} from "@/modules/gobierno/api";

const control =
  "block w-full rounded-md border border-border-subtle bg-white px-3 py-2 text-sm text-text-900 focus:border-brand-600 focus:outline-none focus:ring-1 focus:ring-brand-600";

const POR_PAGINA = 25;

export function ExpedientesPage() {
  const { tiene } = useAutoridad();
  const { activeCompanyId } = useCompany();
  const puedeVer = tiene("gobierno_expedientes:view", "empresa");
  const puedeEditar = tiene("gobierno_expedientes:manage", "empresa");

  const [q, setQ] = useState("");
  const [status, setStatus] = useState("");
  const [unidadId, setUnidadId] = useState("");
  const [responsableId, setResponsableId] = useState("");
  const [modalidad, setModalidad] = useState("");
  const [desde, setDesde] = useState("");
  const [hasta, setHasta] = useState("");
  const [pagina, setPagina] = useState(1);

  const reset = <T,>(setter: (v: T) => void) => (v: T) => {
    setter(v);
    setPagina(1);
  };

  const catalogoQuery = useQuery({
    queryKey: [...CONSULTA_EXPEDIENTES, activeCompanyId, "catalogo"],
    queryFn: () => apiFetch<ExpedienteCatalogo>("/gobierno/contrataciones/expedientes/catalogo"),
    enabled: puedeVer && Boolean(activeCompanyId),
    retry: false,
  });

  const opcionesQuery = useQuery({
    queryKey: [...CONSULTA_EXPEDIENTES, activeCompanyId, "opciones"],
    queryFn: () => apiFetch<ExpedienteOpciones>("/gobierno/contrataciones/expedientes/opciones"),
    enabled: puedeVer && Boolean(activeCompanyId),
    retry: false,
  });

  const parametros = { q, status, unidad_id: unidadId, responsable_id: responsableId, modalidad, desde, hasta, pagina };
  const listadoQuery = useQuery({
    queryKey: [...CONSULTA_EXPEDIENTES, activeCompanyId, "lista", parametros],
    queryFn: () => apiFetch<ExpedientesListado>(consultaDeExpedientes(parametros)),
    enabled: puedeVer && Boolean(activeCompanyId),
    retry: false,
    placeholderData: keepPreviousData,
  });

  const crumbs = [{ label: "Gobierno", to: "/gobierno" }, { label: "Contrataciones" }, { label: "Expedientes" }];

  if (!puedeVer) {
    return (
      <PageContent>
        <PageHeader crumbs={crumbs} title="Expedientes de contratación" />
        <EmptyState title="Sin acceso" description="No tiene permisos para consultar expedientes." />
      </PageContent>
    );
  }

  if (!activeCompanyId) {
    return (
      <PageContent>
        <PageHeader crumbs={crumbs} title="Expedientes de contratación" />
        <EmptyState title="Sin empresa" description="Seleccione una empresa para consultar expedientes." />
      </PageContent>
    );
  }

  if (listadoQuery.isLoading) {
    return (
      <PageContent>
        <PageHeader crumbs={crumbs} title="Expedientes de contratación" />
        <LoadingState />
      </PageContent>
    );
  }

  if (listadoQuery.isError) {
    return (
      <PageContent>
        <PageHeader crumbs={crumbs} title="Expedientes de contratación" />
        <ErrorDeCarga message="No se pudieron cargar los expedientes." onRetry={() => listadoQuery.refetch()} />
      </PageContent>
    );
  }

  const listado = listadoQuery.data;
  const items = listado?.items ?? [];
  const totalPaginas = listado ? Math.max(1, Math.ceil(listado.total / POR_PAGINA)) : 1;
  const estados = catalogoQuery.data?.estados ?? [];
  const unidades = opcionesQuery.data?.unidades ?? [];
  const funcionarios = opcionesQuery.data?.funcionarios ?? [];
  const modalidades = catalogoQuery.data?.modalidades ?? [];

  return (
    <PageContent>
      <PageHeader
        crumbs={crumbs}
        title="Expedientes de contratación"
        actions={
          puedeEditar ? (
            <Link to="/gobierno/contrataciones/expedientes/nuevo" className="inline-flex items-center rounded-md bg-brand-700 px-3 py-2 text-sm font-medium text-white hover:bg-brand-800">
              Nuevo expediente
            </Link>
          ) : undefined
        }
      />

      <div className="mb-4 grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <div>
          <label htmlFor="expediente-buscar" className="mb-1 block text-xs font-medium text-text-700">Buscar</label>
          <TextInput id="expediente-buscar" className={control} placeholder="Número u objeto" value={q} onChange={(e) => reset(setQ)(e.target.value)} />
        </div>
        <div>
          <label htmlFor="expediente-estado" className="mb-1 block text-xs font-medium text-text-700">Estado</label>
          <select id="expediente-estado" className={control} value={status} onChange={(e) => reset(setStatus)(e.target.value)}>
            <option value="">Todos</option>
            {estados.map((o) => (
              <option key={o.codigo} value={o.codigo}>{o.etiqueta}</option>
            ))}
          </select>
        </div>
        <div>
          <label htmlFor="expediente-unidad" className="mb-1 block text-xs font-medium text-text-700">Unidad</label>
          <select id="expediente-unidad" className={control} value={unidadId} onChange={(e) => reset(setUnidadId)(e.target.value)}>
            <option value="">Todas</option>
            {unidades.map((o) => (
              <option key={o.id} value={o.id}>{o.nombre}</option>
            ))}
          </select>
        </div>
        <div>
          <label htmlFor="expediente-responsable" className="mb-1 block text-xs font-medium text-text-700">Responsable</label>
          <select id="expediente-responsable" className={control} value={responsableId} onChange={(e) => reset(setResponsableId)(e.target.value)}>
            <option value="">Todos</option>
            {funcionarios.map((o) => (
              <option key={o.id} value={o.id}>{o.nombre}</option>
            ))}
          </select>
        </div>
        <div>
          <label htmlFor="expediente-modalidad" className="mb-1 block text-xs font-medium text-text-700">Modalidad declarada</label>
          <select id="expediente-modalidad" className={control} value={modalidad} onChange={(e) => reset(setModalidad)(e.target.value)}>
            <option value="">Todas</option>
            {modalidades.map((o) => (
              <option key={o.codigo} value={o.codigo}>{o.etiqueta}</option>
            ))}
          </select>
        </div>
        <div>
          <label htmlFor="expediente-desde" className="mb-1 block text-xs font-medium text-text-700">Iniciado desde</label>
          <TextInput id="expediente-desde" type="date" className={control} value={desde} onChange={(e) => reset(setDesde)(e.target.value)} />
        </div>
        <div>
          <label htmlFor="expediente-hasta" className="mb-1 block text-xs font-medium text-text-700">Iniciado hasta</label>
          <TextInput id="expediente-hasta" type="date" className={control} value={hasta} onChange={(e) => reset(setHasta)(e.target.value)} />
        </div>
      </div>

      {items.length === 0 ? (
        <EmptyState title="Sin expedientes" description="No hay expedientes que coincidan con los filtros." />
      ) : (
        <>
          <div className="overflow-x-auto" tabIndex={0}>
            <table className="min-w-full divide-y divide-border-subtle text-sm">
              <caption className="sr-only">Expedientes de contratación</caption>
              <thead>
                <tr className="text-left text-xs font-medium uppercase text-text-600">
                  <th scope="col" className="px-3 py-2">Número</th>
                  <th scope="col" className="px-3 py-2">Objeto</th>
                  <th scope="col" className="px-3 py-2">Tipo</th>
                  <th scope="col" className="px-3 py-2">Modalidad declarada</th>
                  <th scope="col" className="px-3 py-2">Unidad</th>
                  <th scope="col" className="px-3 py-2">Responsable</th>
                  <th scope="col" className="px-3 py-2">Próximo hito</th>
                  <th scope="col" className="px-3 py-2">Estado</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border-subtle">
                {items.map((e) => (
                  <tr key={e.id}>
                    <td className="px-3 py-2">
                      <Link to={`/gobierno/contrataciones/expedientes/${e.id}`} className="text-brand-700 hover:underline">{e.numero}</Link>
                    </td>
                    <td className="px-3 py-2">{e.objeto}</td>
                    <td className="px-3 py-2">{e.tipo_etiqueta}</td>
                    <td className="px-3 py-2">{e.modalidad_etiqueta ?? "Sin declarar"}</td>
                    <td className="px-3 py-2">{e.unidad_nombre}</td>
                    <td className="px-3 py-2">{e.responsable || "Sin responsable"}</td>
                    <td className="px-3 py-2">
                      {e.proximo_hito ? (
                        <span>
                          {e.proximo_hito.nombre} · {formatearFechaDeNegocio(e.proximo_hito.fecha_prevista)}
                          {e.proximo_hito.fecha_superada ? " (Fecha prevista superada)" : ""}
                        </span>
                      ) : (
                        "Sin hitos pendientes"
                      )}
                    </td>
                    <td className="px-3 py-2">{e.status_etiqueta}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="mt-4 flex items-center justify-between text-sm">
            <span>Página {listado?.pagina ?? 1} de {totalPaginas}</span>
            <div className="flex gap-2">
              <button type="button" className="rounded-md border border-border-subtle px-3 py-1 disabled:opacity-50" disabled={pagina <= 1} onClick={() => setPagina((p) => Math.max(1, p - 1))}>
                Anterior
              </button>
              <button type="button" className="rounded-md border border-border-subtle px-3 py-1 disabled:opacity-50" disabled={pagina >= totalPaginas} onClick={() => setPagina((p) => p + 1)}>
                Siguiente
              </button>
            </div>
          </div>
        </>
      )}
    </PageContent>
  );
}
