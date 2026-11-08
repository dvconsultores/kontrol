import { useState } from "react";
import { Link } from "react-router";
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
import { formatearFecha } from "@/i18n";
import { ErrorDeCarga } from "@/modules/gobierno/ocupacion/ErrorDeCarga";
import {
  BitacoraEvento,
  BitacoraEventos,
  BitacoraFiltros,
  CONSULTA_BITACORA,
  consultaDeBitacora,
  ETIQUETAS_ESTADO_CONTEXTO,
  ETIQUETAS_RESULTADO_BITACORA,
} from "@/modules/gobierno/api";

type FiltrosBorrador = {
  desde: string;
  hasta: string;
  resultado: string;
  accion: string;
  usuario: string;
  funcionario_id: string;
  unidad_id: string;
  request_id: string;
};

const filtrosVacios: FiltrosBorrador = {
  desde: "",
  hasta: "",
  resultado: "",
  accion: "",
  usuario: "",
  funcionario_id: "",
  unidad_id: "",
  request_id: "",
};

export function BitacoraPage() {
  const { tiene } = useAutoridad();
  const { activeCompanyId } = useCompany();
  const puedeVer = tiene("gobierno_auditoria:view", "empresa");

  const [borrador, setBorrador] = useState<FiltrosBorrador>(filtrosVacios);
  const [aplicados, setAplicados] = useState<FiltrosBorrador>(filtrosVacios);
  const [pagina, setPagina] = useState(1);

  const filtrosQuery = useQuery({
    queryKey: [...CONSULTA_BITACORA, "filtros", activeCompanyId],
    queryFn: () =>
      apiFetch<BitacoraFiltros>("/gobierno/bitacora/filtros"),
    enabled: puedeVer && Boolean(activeCompanyId),
    retry: false,
  });

  const eventosQuery = useQuery({
    queryKey: [...CONSULTA_BITACORA, activeCompanyId, aplicados, pagina],
    queryFn: () =>
      apiFetch<BitacoraEventos>(
        `/gobierno/bitacora${consultaDeBitacora({ ...aplicados, pagina })}`
      ),
    placeholderData: keepPreviousData,
    enabled: puedeVer && Boolean(activeCompanyId),
    retry: false,
  });

  if (!puedeVer) {
    return (
      <PageContent>
        <EmptyState title="Sin acceso" description="No tienes permisos para ver la bitácora institucional." />
      </PageContent>
    );
  }

  if (!activeCompanyId) {
    return (
      <PageContent>
        <EmptyState title="Sin empresa" description="Selecciona una empresa para continuar." />
      </PageContent>
    );
  }

  const acciones = filtrosQuery.data?.acciones ?? [];
  const accionesUnicas = acciones.filter(
    (a, index, arr) => arr.findIndex((x) => x.codigo === a.codigo) === index
  );

  function manejarSubmit(e: React.FormEvent) {
    e.preventDefault();
    setAplicados(borrador);
    setPagina(1);
  }

  function actualizarCampo(campo: keyof FiltrosBorrador, valor: string) {
    setBorrador((prev) => ({ ...prev, [campo]: valor }));
  }

  const totalPaginas = Math.max(
    1,
    Math.ceil((eventosQuery.data?.total ?? 0) / (eventosQuery.data?.por_pagina ?? 10))
  );

  return (
    <PageContent>
      <PageHeader
        crumbs={[{ label: "Gobierno" }, { label: "Bitácora institucional" }]}
        title="Bitácora institucional"
        description="Quién operó, a qué funcionario representaba y con qué autoridad, tal como era en el momento del evento."
      />

      <form
        onSubmit={manejarSubmit}
        className="mb-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4"
      >
        <FormField label="Desde" htmlFor="bitacora-desde">
          <input
            id="bitacora-desde"
            type="date"
            value={borrador.desde}
            onChange={(e) => actualizarCampo("desde", e.target.value)}
            className="block w-full rounded-md border border-border-subtle bg-white px-3 py-2 text-sm text-text-900"
          />
        </FormField>
        <FormField label="Hasta" htmlFor="bitacora-hasta">
          <input
            id="bitacora-hasta"
            type="date"
            value={borrador.hasta}
            onChange={(e) => actualizarCampo("hasta", e.target.value)}
            className="block w-full rounded-md border border-border-subtle bg-white px-3 py-2 text-sm text-text-900"
          />
        </FormField>
        <FormField label="Resultado" htmlFor="bitacora-resultado">
          <select
            id="bitacora-resultado"
            value={borrador.resultado}
            onChange={(e) => actualizarCampo("resultado", e.target.value)}
            className="block w-full rounded-md border border-border-subtle bg-white px-3 py-2 text-sm text-text-900"
          >
            <option value="">Todos</option>
            {Object.entries(ETIQUETAS_RESULTADO_BITACORA).map(([codigo, etiqueta]) => (
              <option key={codigo} value={codigo}>
                {etiqueta}
              </option>
            ))}
          </select>
        </FormField>
        <FormField label="Acción" htmlFor="bitacora-accion">
          <select
            id="bitacora-accion"
            value={borrador.accion}
            onChange={(e) => actualizarCampo("accion", e.target.value)}
            className="block w-full rounded-md border border-border-subtle bg-white px-3 py-2 text-sm text-text-900"
          >
            <option value="">Todas</option>
            {accionesUnicas.map((a) => (
              <option key={`${a.codigo}${a.entidad}`} value={a.codigo}>
                {a.etiqueta}
              </option>
            ))}
          </select>
        </FormField>
        <FormField label="Usuario técnico" htmlFor="bitacora-usuario">
          <input
            id="bitacora-usuario"
            type="text"
            value={borrador.usuario}
            onChange={(e) => actualizarCampo("usuario", e.target.value)}
            className="block w-full rounded-md border border-border-subtle bg-white px-3 py-2 text-sm text-text-900"
          />
        </FormField>
        <FormField label="Funcionario" htmlFor="bitacora-funcionario">
          <select
            id="bitacora-funcionario"
            value={borrador.funcionario_id}
            onChange={(e) => actualizarCampo("funcionario_id", e.target.value)}
            className="block w-full rounded-md border border-border-subtle bg-white px-3 py-2 text-sm text-text-900"
          >
            <option value="">Todos</option>
            {filtrosQuery.data?.funcionarios.map((f) => (
              <option key={f.id} value={f.id}>
                {f.nombre}
              </option>
            ))}
          </select>
        </FormField>
        <FormField label="Unidad" htmlFor="bitacora-unidad">
          <select
            id="bitacora-unidad"
            value={borrador.unidad_id}
            onChange={(e) => actualizarCampo("unidad_id", e.target.value)}
            className="block w-full rounded-md border border-border-subtle bg-white px-3 py-2 text-sm text-text-900"
          >
            <option value="">Todas</option>
            {filtrosQuery.data?.unidades.map((u) => (
              <option key={u.id} value={u.id}>
                {u.nombre}
              </option>
            ))}
          </select>
        </FormField>
        <FormField label="Correlación" htmlFor="bitacora-correlacion">
          <input
            id="bitacora-correlacion"
            type="text"
            value={borrador.request_id}
            onChange={(e) => actualizarCampo("request_id", e.target.value)}
            className="block w-full rounded-md border border-border-subtle bg-white px-3 py-2 text-sm text-text-900"
          />
        </FormField>
        <div className="flex items-end">
          <Button type="submit" variant="primary">
            Filtrar
          </Button>
        </div>
      </form>

      {eventosQuery.isLoading && <LoadingState />}
      {eventosQuery.isError && (
        <ErrorDeCarga
          message="No se pudo cargar la bitácora institucional."
          onRetry={() => eventosQuery.refetch()}
        />
      )}
      {eventosQuery.data && eventosQuery.data.items.length === 0 && (
        <EmptyState title="Sin eventos" description="No hay eventos con estos filtros." />
      )}
      {eventosQuery.data && eventosQuery.data.items.length > 0 && (
        <>
          <div
            className="relative overflow-x-auto"
            tabIndex={0}
            role="region"
            aria-label="Tabla de la bitácora institucional"
          >
            <table className="w-full border-collapse text-sm">
              <caption className="sr-only">Eventos de la bitácora institucional</caption>
              <thead>
                <tr className="border-b border-border-subtle text-left">
                  <th className="px-3 py-2 font-medium text-text-700">Fecha</th>
                  <th className="px-3 py-2 font-medium text-text-700">Resultado</th>
                  <th className="px-3 py-2 font-medium text-text-700">Acción</th>
                  <th className="px-3 py-2 font-medium text-text-700">Usuario técnico</th>
                  <th className="px-3 py-2 font-medium text-text-700">Actor efectivo</th>
                  <th className="px-3 py-2 font-medium text-text-700">Cargo</th>
                  <th className="px-3 py-2 font-medium text-text-700">Unidad</th>
                </tr>
              </thead>
              <tbody>
                {eventosQuery.data.items.map((evento: BitacoraEvento) => (
                  <tr key={evento.id} className="border-b border-border-subtle">
                    <td className="px-3 py-2">
                      <Link
                        to={`/gobierno/bitacora/${evento.id}`}
                        className="font-medium text-brand-700 underline"
                      >
                        {formatearFecha(evento.fecha)}
                      </Link>
                    </td>
                    <td className="px-3 py-2">
                      {ETIQUETAS_RESULTADO_BITACORA[evento.resultado] ?? evento.resultado}
                    </td>
                    <td className="px-3 py-2">
                      <div>{evento.accion_etiqueta}</div>
                      <div className="text-xs text-text-500">{evento.proceso_nombre}</div>
                    </td>
                    <td className="px-3 py-2">{evento.usuario ?? "—"}</td>
                    <td className="px-3 py-2">
                      {evento.funcionario ??
                        ETIQUETAS_ESTADO_CONTEXTO[evento.estado_contexto] ??
                        "—"}
                    </td>
                    <td className="px-3 py-2">{evento.cargos.join(", ") || "—"}</td>
                    <td className="px-3 py-2">{evento.unidades.join(", ") || "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="mt-4 flex items-center justify-between">
            <Button
              variant="secondary"
              disabled={pagina <= 1}
              onClick={() => setPagina((p) => Math.max(1, p - 1))}
            >
              Anterior
            </Button>
            <span className="text-sm text-text-700">
              Página {pagina} de {totalPaginas}
            </span>
            <Button
              variant="secondary"
              disabled={pagina >= totalPaginas}
              onClick={() => setPagina((p) => Math.min(totalPaginas, p + 1))}
            >
              Siguiente
            </Button>
          </div>
        </>
      )}
    </PageContent>
  );
}
