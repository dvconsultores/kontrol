import { useState } from "react";
import { Link, useSearchParams } from "react-router";
import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/api/client";
import { useAutoridad } from "@/app/autoridad/AutoridadContext";
import { useCompany } from "@/app/contexts/CompanyContext";
import { Button } from "@/components/Button";
import { EmptyState } from "@/components/EmptyState";
import { FormField } from "@/components/FormField";
import { LoadingState } from "@/components/LoadingState";
import { PageHeader } from "@/components/PageHeader";
import { PageContent } from "@/layout/PageContent";
import { ErrorDeCarga } from "@/modules/gobierno/ocupacion/ErrorDeCarga";
import { formatearFechaDeNegocio } from "@/lib/fecha-de-negocio";
import { CONSULTA_EXPEDIENTES, rutaExpediente, type ListaExpedientes } from "./api";

const LIMITE = 25;

interface Filtros {
  codigo: string;
  expediente: string;
  contratista: string;
  tipo: string;
  vigencia: string;
  supervisor: string;
  desde: string;
  hasta: string;
}

const FILTROS_VACIOS: Filtros = {
  codigo: "",
  expediente: "",
  contratista: "",
  tipo: "",
  vigencia: "",
  supervisor: "",
  desde: "",
  hasta: "",
};

export function ExpedientesContractualesPage() {
  const { tiene } = useAutoridad();
  const { activeCompanyId } = useCompany();
  const [searchParams, setSearchParams] = useSearchParams();
  const [filtros, setFiltros] = useState<Filtros>({
    codigo: searchParams.get("codigo") ?? "",
    expediente: searchParams.get("expediente") ?? "",
    contratista: searchParams.get("contratista") ?? "",
    tipo: searchParams.get("tipo") ?? "",
    vigencia: searchParams.get("vigencia") ?? "",
    supervisor: searchParams.get("supervisor") ?? "",
    desde: searchParams.get("desde") ?? "",
    hasta: searchParams.get("hasta") ?? "",
  });
  const offset = Number(searchParams.get("offset") ?? "0");

  const puedeVer = tiene("gobierno_contratos:view", "empresa");

  const consulta = useQuery({
    queryKey: [...CONSULTA_EXPEDIENTES, activeCompanyId, searchParams.toString()],
    queryFn: () => apiFetch<ListaExpedientes>(`/gobierno/expedientes-contractuales?${searchParams.toString()}`),
    enabled: puedeVer && Boolean(activeCompanyId),
    placeholderData: keepPreviousData,
  });

  function actualizarFiltro(campo: keyof Filtros, valor: string) {
    setFiltros((previos) => ({ ...previos, [campo]: valor }));
  }

  function construirParams(conOffset: number): URLSearchParams {
    const params = new URLSearchParams();
    if (filtros.codigo.trim() !== "") params.set("codigo", filtros.codigo.trim());
    if (filtros.expediente.trim() !== "") params.set("expediente", filtros.expediente.trim());
    if (filtros.contratista.trim() !== "") params.set("contratista", filtros.contratista.trim());
    if (filtros.tipo.trim() !== "") params.set("tipo", filtros.tipo.trim());
    if (filtros.vigencia.trim() !== "") params.set("vigencia", filtros.vigencia.trim());
    if (filtros.supervisor.trim() !== "") params.set("supervisor", filtros.supervisor.trim());
    if (filtros.desde.trim() !== "") params.set("desde", filtros.desde.trim());
    if (filtros.hasta.trim() !== "") params.set("hasta", filtros.hasta.trim());
    params.set("limit", String(LIMITE));
    params.set("offset", String(conOffset));
    return params;
  }

  function buscar() {
    setSearchParams(construirParams(0));
  }

  function limpiar() {
    setFiltros(FILTROS_VACIOS);
    setSearchParams(new URLSearchParams({ limit: String(LIMITE), offset: "0" }));
  }

  if (!puedeVer) {
    return (
      <PageContent>
        <PageHeader crumbs={[{ label: "Gobierno" }, { label: "Expedientes contractuales" }]} title="Expedientes contractuales" />
        <EmptyState title="Sin acceso" description="No tiene permiso para consultar expedientes contractuales." />
      </PageContent>
    );
  }

  const total = consulta.data?.total ?? 0;
  const desde = total === 0 ? 0 : offset + 1;
  const hasta = Math.min(offset + LIMITE, total);

  return (
    <PageContent>
      <PageHeader
        crumbs={[{ label: "Gobierno" }, { label: "Expedientes contractuales" }]}
        title="Expedientes contractuales"
        description="Consulta para control fiscal y rendición de cuentas. Solo lectura."
      />

      <section aria-labelledby="filtros-titulo" className="mb-6 rounded-md border border-border-subtle bg-white p-4">
        <h2 id="filtros-titulo" className="text-lg font-semibold text-text-900">
          Filtros
        </h2>
        <div className="mt-3 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <FormField label="Código del contrato" htmlFor="filtro-codigo">
            <input
              id="filtro-codigo"
              value={filtros.codigo}
              onChange={(e) => actualizarFiltro("codigo", e.target.value)}
              className="w-full rounded-md border border-border-subtle px-3 py-2 text-sm"
              placeholder="CT-2026-0001"
            />
          </FormField>
          <FormField label="Expediente de contratación" htmlFor="filtro-expediente">
            <input
              id="filtro-expediente"
              value={filtros.expediente}
              onChange={(e) => actualizarFiltro("expediente", e.target.value)}
              className="w-full rounded-md border border-border-subtle px-3 py-2 text-sm"
              placeholder="Número de expediente"
            />
          </FormField>
          <FormField label="Contratista" htmlFor="filtro-contratista">
            <input
              id="filtro-contratista"
              value={filtros.contratista}
              onChange={(e) => actualizarFiltro("contratista", e.target.value)}
              className="w-full rounded-md border border-border-subtle px-3 py-2 text-sm"
              placeholder="Nombre o documento"
            />
          </FormField>
          <FormField label="Tipo de instrumento" htmlFor="filtro-tipo">
            <select
              id="filtro-tipo"
              value={filtros.tipo}
              onChange={(e) => actualizarFiltro("tipo", e.target.value)}
              className="w-full rounded-md border border-border-subtle px-3 py-2 text-sm"
            >
              <option value="">Todos</option>
              <option value="CONTRATO">Contrato</option>
              <option value="ORDEN_COMPRA">Orden de compra</option>
              <option value="ORDEN_SERVICIO">Orden de servicio</option>
            </select>
          </FormField>
          <FormField label="Vigencia" htmlFor="filtro-vigencia">
            <select
              id="filtro-vigencia"
              value={filtros.vigencia}
              onChange={(e) => actualizarFiltro("vigencia", e.target.value)}
              className="w-full rounded-md border border-border-subtle px-3 py-2 text-sm"
            >
              <option value="">Todas</option>
              <option value="POR_INICIAR">Por iniciar</option>
              <option value="EN_PLAZO">En plazo</option>
              <option value="VENCIDO">Vencido</option>
            </select>
          </FormField>
          <FormField label="Supervisor" htmlFor="filtro-supervisor">
            <input
              id="filtro-supervisor"
              value={filtros.supervisor}
              onChange={(e) => actualizarFiltro("supervisor", e.target.value)}
              className="w-full rounded-md border border-border-subtle px-3 py-2 text-sm"
              placeholder="Nombre del supervisor"
            />
          </FormField>
          <FormField label="Formalizado desde" htmlFor="filtro-desde">
            <input
              id="filtro-desde"
              type="date"
              value={filtros.desde}
              onChange={(e) => actualizarFiltro("desde", e.target.value)}
              className="w-full rounded-md border border-border-subtle px-3 py-2 text-sm"
            />
          </FormField>
          <FormField label="Formalizado hasta" htmlFor="filtro-hasta">
            <input
              id="filtro-hasta"
              type="date"
              value={filtros.hasta}
              onChange={(e) => actualizarFiltro("hasta", e.target.value)}
              className="w-full rounded-md border border-border-subtle px-3 py-2 text-sm"
            />
          </FormField>
        </div>
        <div className="mt-4 flex gap-2">
          <Button variant="primary" onClick={buscar}>
            Buscar
          </Button>
          <Button variant="secondary" onClick={limpiar}>
            Limpiar
          </Button>
        </div>
      </section>

      {consulta.isLoading ? <LoadingState /> : null}

      {consulta.isError ? (
        <ErrorDeCarga
          message={
            consulta.error instanceof Error
              ? consulta.error.message
              : "No se pudieron cargar los expedientes contractuales."
          }
          onRetry={() => void consulta.refetch()}
        />
      ) : null}

      {consulta.data && consulta.data.items.length === 0 ? (
        <EmptyState title="No hay expedientes con estos filtros" description="Pruebe con otros criterios de búsqueda." />
      ) : null}

      {consulta.data && consulta.data.items.length > 0 ? (
        <section aria-labelledby="tabla-titulo" className="mb-6">
          <h2 id="tabla-titulo" className="text-lg font-semibold text-text-900">
            Expedientes
          </h2>
          <div role="region" aria-label="Expedientes contractuales" tabIndex={0} className="overflow-x-auto">
            <table className="mt-3 w-full min-w-[900px] border-collapse text-left text-sm">
              <thead>
                <tr className="border-b border-border-subtle text-text-600">
                  <th scope="col" className="py-2 pr-3 font-medium">Contrato</th>
                  <th scope="col" className="py-2 pr-3 font-medium">Contratista</th>
                  <th scope="col" className="py-2 pr-3 font-medium">Objeto</th>
                  <th scope="col" className="py-2 pr-3 font-medium">Monto vigente</th>
                  <th scope="col" className="py-2 pr-3 font-medium">Vigencia</th>
                  <th scope="col" className="py-2 pr-3 font-medium">Supervisor</th>
                  <th scope="col" className="py-2 pr-3 font-medium">Expediente de contratación</th>
                  <th scope="col" className="py-2 pr-3 font-medium">Formalizado</th>
                  <th scope="col" className="py-2 pr-3 font-medium">Último paquete</th>
                  <th scope="col" className="py-2 pr-3 font-medium">Última actuación</th>
                </tr>
              </thead>
              <tbody>
                {consulta.data.items.map((item) => (
                  <tr key={item.id} className="border-b border-border-subtle align-top">
                    <td className="py-2 pr-3">
                      <Link className="font-medium text-brand-700 underline" to={rutaExpediente(item.id)}>
                        {item.codigo}
                      </Link>
                    </td>
                    <td className="py-2 pr-3 text-text-900">{item.contratista.nombre}</td>
                    <td className="py-2 pr-3 text-text-900">{item.objeto}</td>
                    <td className="py-2 pr-3 text-text-900">
                      {item.monto_vigente} {item.moneda}
                    </td>
                    <td className="py-2 pr-3 text-text-900">{item.vigencia_etiqueta}</td>
                    <td className="py-2 pr-3 text-text-900">
                      {item.supervisor ? `${item.supervisor.nombre} · ${item.supervisor.cargo}` : "—"}
                    </td>
                    <td className="py-2 pr-3 text-text-900">{item.expediente.numero}</td>
                    <td className="py-2 pr-3 text-text-900">{formatearFechaDeNegocio(item.fecha_formalizacion)}</td>
                    <td className="py-2 pr-3 text-text-900">
                      {item.ultimo_paquete ? (
                        <span>
                          {item.ultimo_paquete.codigo}
                          {item.ultimo_paquete.verificacion === "VALIDO" ? " · Válido" : ""}
                        </span>
                      ) : (
                        "Sin paquete"
                      )}
                    </td>
                    <td className="py-2 pr-3 text-text-900">
                      {item.ultima_actuacion
                        ? `${formatearFechaDeNegocio(item.ultima_actuacion.fecha)} · ${item.ultima_actuacion.titulo}`
                        : "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="mt-3 flex items-center justify-between text-sm text-text-600">
            <span>
              Mostrando {desde}–{hasta} de {total}
            </span>
            <div className="flex gap-2">
              <Button variant="secondary" disabled={offset === 0} onClick={() => setSearchParams(construirParams(Math.max(0, offset - LIMITE)))}>
                Anterior
              </Button>
              <Button
                variant="secondary"
                disabled={offset + LIMITE >= total}
                onClick={() => setSearchParams(construirParams(offset + LIMITE))}
              >
                Siguiente
              </Button>
            </div>
          </div>
        </section>
      ) : null}
    </PageContent>
  );
}
