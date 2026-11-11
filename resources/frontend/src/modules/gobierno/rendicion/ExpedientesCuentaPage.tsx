import { useState } from "react";
import { Link } from "react-router";
import { useQuery, keepPreviousData } from "@tanstack/react-query";
import { useAutoridad } from "@/app/autoridad/AutoridadContext";
import { useCompany } from "@/app/contexts/CompanyContext";
import { PageContent } from "@/layout/PageContent";
import { PageHeader } from "@/components/PageHeader";
import { Button } from "@/components/Button";
import { FormField } from "@/components/FormField";
import { TextInput } from "@/components/TextInput";
import { DateInput } from "@/components/DateInput";
import { EmptyState } from "@/components/EmptyState";
import { ErrorState } from "@/components/ErrorState";
import { LoadingState } from "@/components/LoadingState";

import { formatearFechaDeNegocio } from "@/lib/fecha-de-negocio";
import { getOpcionesRendicion, listarExpedientes, FichaRendicion } from "./api";

const ESTADOS: Record<string, string> = {
  EN_FORMACION: "En formación",
  FORMADA: "Formada",
  PARTICIPADA: "Participada",
  CALIFICADA: "Calificada",
  FENECIDA: "Fenecida",
  SUSTITUIDA: "Sustituida",
};

export function ExpedientesCuentaPage() {
  const { tiene } = useAutoridad();
  const { activeCompanyId } = useCompany();
  const puedeFormar = tiene("gobierno_rendicion:form", "empresa");
  const puedeVer = tiene("gobierno_rendicion:view", "empresa");

  const [estado, setEstado] = useState("");
  const [texto, setTexto] = useState("");
  const [desde, setDesde] = useState("");
  const [hasta, setHasta] = useState("");
  const [responsable, setResponsable] = useState("");
  const [unidad, setUnidad] = useState("");
  const [pagina, setPagina] = useState(1);

  const opciones = useQuery({ queryKey: ["gobierno-rendicion-opciones", activeCompanyId], queryFn: getOpcionesRendicion, enabled: puedeVer });

  const expedientes = useQuery({
    queryKey: ["gobierno-rendicion-expedientes", activeCompanyId, estado, texto, desde, hasta, responsable, unidad, pagina],
    queryFn: () =>
      listarExpedientes({
        estado: estado || undefined,
        texto: texto || undefined,
        desde: desde || undefined,
        hasta: hasta || undefined,
        responsable: responsable || undefined,
        unidad: unidad || undefined,
        pagina,
        por_pagina: 20,
      }),
    placeholderData: keepPreviousData,
    enabled: puedeVer,
  });

  if (!puedeVer) {
    return <ErrorState message="No tiene permiso para ver expedientes de cuenta." />;
  }

  const unidades = Array.from(new Set((opciones.data?.responsables ?? []).map((r) => r.unidad_id).filter(Boolean) as string[]));

  const totalPaginas = expedientes.data ? Math.max(1, Math.ceil(expedientes.data.total / expedientes.data.por_pagina)) : 1;

  return (
    <PageContent>
      <PageHeader
        title="Expedientes de cuenta"
        description="Formación, participación, calificación y fenecimiento de la cuenta."
        actions={
          puedeFormar ? (
            <Link to="/gobierno/rendicion/nuevo">
              <Button variant="primary">Nuevo expediente</Button>
            </Link>
          ) : undefined
        }
      />

      <div className="flex flex-wrap gap-2">
        <FormField label="Estado" htmlFor="f-estado">
          <select id="f-estado" className="h-10 w-full rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900 focus:border-brand-600 focus:outline-brand-600" value={estado} onChange={(e) => { setEstado(e.target.value); setPagina(1); }}>
            <option value="">Todos</option>
            {(opciones.data?.estados ?? Object.keys(ESTADOS)).map((e) => (
              <option key={e} value={e}>{ESTADOS[e] ?? e}</option>
            ))}
          </select>
        </FormField>
        <FormField label="Texto" htmlFor="f-texto">
          <TextInput id="f-texto" value={texto} onChange={(e) => { setTexto(e.target.value); setPagina(1); }} placeholder="Código, denominación..." />
        </FormField>
        <FormField label="Desde" htmlFor="f-desde">
          <DateInput id="f-desde" value={desde} onChange={(e) => { setDesde(e.target.value); setPagina(1); }} />
        </FormField>
        <FormField label="Hasta" htmlFor="f-hasta">
          <DateInput id="f-hasta" value={hasta} onChange={(e) => { setHasta(e.target.value); setPagina(1); }} />
        </FormField>
        <FormField label="Responsable" htmlFor="f-responsable">
          <select id="f-responsable" className="h-10 w-full rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900 focus:border-brand-600 focus:outline-brand-600" value={responsable} onChange={(e) => { setResponsable(e.target.value); setPagina(1); }}>
            <option value="">Todos</option>
            {(opciones.data?.responsables ?? []).map((r) => (
              <option key={r.asignacion_id} value={r.official_id}>{r.funcionario} · {r.cargo}</option>
            ))}
          </select>
        </FormField>
        <FormField label="Unidad" htmlFor="f-unidad">
          <select id="f-unidad" className="h-10 w-full rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900 focus:border-brand-600 focus:outline-brand-600" value={unidad} onChange={(e) => { setUnidad(e.target.value); setPagina(1); }}>
            <option value="">Todas</option>
            {unidades.map((u) => {
              const responsableU = opciones.data?.responsables.find((r) => r.unidad_id === u);
              return <option key={u} value={u}>{responsableU?.unidad ?? u}</option>;
            })}
          </select>
        </FormField>
      </div>

      {expedientes.isLoading && <LoadingState />}
      {expedientes.isError && <ErrorState message={(expedientes.error as Error).message} onRetry={() => expedientes.refetch()} />}

      {expedientes.data && expedientes.data.items.length === 0 && (
        <EmptyState title="Sin expedientes" description="No se encontraron expedientes con los filtros seleccionados." />
      )}

      {expedientes.data && expedientes.data.items.length > 0 && (
        <div className="flex flex-col gap-3">
          <ul className="flex flex-col gap-3">
            {expedientes.data.items.map((f: FichaRendicion) => (
              <li key={f.id} className="rounded-md border border-border-default bg-surface-0 p-4">
                <div className="flex flex-wrap items-baseline gap-2">
                  <Link to={`/gobierno/rendicion/${f.id}`} className="font-semibold text-text-900 hover:text-brand-600">
                    {f.codigo} · v{f.numero_version}
                  </Link>
                  <span className="text-sm text-text-600">{ESTADOS[f.estado] ?? f.estado}</span>
                  {f.calificacion && <span className="text-sm text-text-600">Calificación: {f.calificacion.resultado}</span>}
                </div>
                <div className="break-words min-w-0 text-text-900">{f.denominacion}</div>
                <div className="text-sm text-text-600">
                  {formatearFechaDeNegocio(f.periodo_desde)} – {formatearFechaDeNegocio(f.periodo_hasta)}
                </div>
                <div className="text-sm text-text-600">{f.responsable.funcionario} · {f.responsable.cargo}</div>
                <div className="text-sm text-text-600">{f.piezas.length} piezas</div>
              </li>
            ))}
          </ul>
        </div>
      )}

      {expedientes.data && (
        <div className="flex items-center gap-2">
          <Button variant="secondary" size="sm" disabled={pagina <= 1} onClick={() => setPagina((p) => p - 1)}>Anterior</Button>
          <span className="text-sm text-text-600">Página {pagina} de {totalPaginas}</span>
          <Button variant="secondary" size="sm" disabled={pagina >= totalPaginas} onClick={() => setPagina((p) => p + 1)}>Siguiente</Button>
        </div>
      )}
    </PageContent>
  );
}
