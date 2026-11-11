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
import { getOpcionesActas, listarActas, ActaResumen } from "./api";

const ESTADOS: Record<string, string> = {
  BORRADOR: "Borrador",
  SUSCRITA: "Suscrita",
  VERIFICADA: "Verificada",
};

const AMBITOS: Record<string, string> = {
  ENTE: "Ente",
  UNIDAD: "Unidad",
};

export function ActasEntregaPage() {
  const { tiene } = useAutoridad();
  const { activeCompanyId } = useCompany();
  const puedeGestionar = tiene("gobierno_actas:manage", "empresa");
  const puedeVer = tiene("gobierno_actas:view", "empresa");

  const [estado, setEstado] = useState("");
  const [ambito, setAmbito] = useState("");
  const [texto, setTexto] = useState("");
  const [desde, setDesde] = useState("");
  const [hasta, setHasta] = useState("");
  const [pagina, setPagina] = useState(1);

  const opciones = useQuery({
    queryKey: ["gobierno-actas-opciones", activeCompanyId],
    queryFn: getOpcionesActas,
    enabled: puedeVer,
  });

  const actas = useQuery({
    queryKey: ["gobierno-actas", activeCompanyId, estado, ambito, texto, desde, hasta, pagina],
    queryFn: () =>
      listarActas({
        estado: estado || undefined,
        ambito: ambito || undefined,
        texto: texto || undefined,
        desde: desde || undefined,
        hasta: hasta || undefined,
        pagina,
        por_pagina: 20,
      }),
    placeholderData: keepPreviousData,
    enabled: puedeVer,
  });

  if (!puedeVer) {
    return <ErrorState message="No tiene permiso para ver actas de entrega." />;
  }

  const totalPaginas = actas.data ? Math.max(1, Math.ceil(actas.data.total / actas.data.por_pagina)) : 1;

  return (
    <PageContent>
      <PageHeader
        title="Actas de entrega"
        description="Actas de entrega de órganos y entidades (Normas CGR, art. 10-22)."
        actions={
          puedeGestionar ? (
            <Link to="/gobierno/actas-entrega/nueva">
              <Button variant="primary">Nueva acta</Button>
            </Link>
          ) : undefined
        }
      />

      <div className="flex flex-wrap gap-2">
        <FormField label="Estado" htmlFor="f-estado">
          <select
            id="f-estado"
            aria-label="Estado"
            className="h-10 w-full rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900 focus:border-brand-600 focus:outline-brand-600"
            value={estado}
            onChange={(e) => {
              setEstado(e.target.value);
              setPagina(1);
            }}
          >
            <option value="">Todos</option>
            {(opciones.data ? Object.keys(ESTADOS) : Object.keys(ESTADOS)).map((e) => (
              <option key={e} value={e}>
                {ESTADOS[e] ?? e}
              </option>
            ))}
          </select>
        </FormField>
        <FormField label="Ámbito" htmlFor="f-ambito">
          <select
            id="f-ambito"
            aria-label="Ámbito"
            className="h-10 w-full rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900 focus:border-brand-600 focus:outline-brand-600"
            value={ambito}
            onChange={(e) => {
              setAmbito(e.target.value);
              setPagina(1);
            }}
          >
            <option value="">Todos</option>
            {Object.entries(AMBITOS).map(([clave, etiqueta]) => (
              <option key={clave} value={clave}>
                {etiqueta}
              </option>
            ))}
          </select>
        </FormField>
        <FormField label="Texto" htmlFor="f-texto">
          <TextInput
            id="f-texto"
            value={texto}
            onChange={(e) => {
              setTexto(e.target.value);
              setPagina(1);
            }}
            placeholder="Código, funcionario..."
          />
        </FormField>
        <FormField label="Desde" htmlFor="f-desde">
          <DateInput
            id="f-desde"
            value={desde}
            onChange={(e) => {
              setDesde(e.target.value);
              setPagina(1);
            }}
          />
        </FormField>
        <FormField label="Hasta" htmlFor="f-hasta">
          <DateInput
            id="f-hasta"
            value={hasta}
            onChange={(e) => {
              setHasta(e.target.value);
              setPagina(1);
            }}
          />
        </FormField>
      </div>

      {actas.isLoading && <LoadingState />}
      {actas.isError && <ErrorState message={(actas.error as Error).message} onRetry={() => actas.refetch()} />}

      {actas.data && actas.data.items.length === 0 && (
        <EmptyState title="Sin actas" description="No se encontraron actas de entrega con los filtros seleccionados." />
      )}

      {actas.data && actas.data.items.length > 0 && (
        <table className="w-full border-collapse" aria-label="Actas de entrega">
          <caption className="sr-only">Listado de actas de entrega</caption>
          <thead>
            <tr className="border-b border-border-default text-left text-sm text-text-600">
              <th className="px-3 py-2">Código</th>
              <th className="px-3 py-2">Saliente</th>
              <th className="px-3 py-2">Receptor</th>
              <th className="px-3 py-2">Ámbito/unidad</th>
              <th className="px-3 py-2">Fecha de corte</th>
              <th className="px-3 py-2">Estado</th>
              <th className="px-3 py-2">Suscripción</th>
            </tr>
          </thead>
          <tbody>
            {actas.data.items.map((f: ActaResumen) => (
              <tr key={f.id} className="border-b border-border-default last:border-b-0" role="listitem">
                <td className="px-3 py-2">
                  <Link to={`/gobierno/actas-entrega/${f.id}`} className="font-semibold text-text-900 hover:text-brand-600">
                    {f.codigo}
                  </Link>
                </td>
                <td className="px-3 py-2">
                  <div>{f.saliente.funcionario}</div>
                  <div className="text-sm text-text-600">{f.saliente.cargo}</div>
                </td>
                <td className="px-3 py-2">{f.receptor.funcionario}</td>
                <td className="px-3 py-2">
                  {f.ambito === "ENTE" ? "Ente" : f.unidad ?? "Unidad"}
                </td>
                <td className="px-3 py-2">{formatearFechaDeNegocio(f.fecha_corte)}</td>
                <td className="px-3 py-2">{ESTADOS[f.estado] ?? f.estado}</td>
                <td className="px-3 py-2">{f.fecha_suscripcion ? formatearFechaDeNegocio(f.fecha_suscripcion) : "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      {actas.data && (
        <div className="flex items-center gap-2">
          <Button variant="secondary" size="sm" disabled={pagina <= 1} onClick={() => setPagina((p) => p - 1)}>
            Anterior
          </Button>
          <span className="text-sm text-text-600">
            Página {pagina} de {totalPaginas}
          </span>
          <Button variant="secondary" size="sm" disabled={pagina >= totalPaginas} onClick={() => setPagina((p) => p + 1)}>
            Siguiente
          </Button>
        </div>
      )}
    </PageContent>
  );
}
