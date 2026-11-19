import { useState } from "react";
import { Link } from "react-router";
import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { apiFetch, ApiError } from "@/api/client";
import { descargarArchivo } from "@/api/descargas";
import { useAutoridad } from "@/app/autoridad/AutoridadContext";
import { useCompany } from "@/app/contexts/CompanyContext";
import { Button } from "@/components/Button";
import { LoadingState } from "@/components/LoadingState";
import { EmptyState } from "@/components/EmptyState";
import { ErrorState } from "@/components/ErrorState";
import { PageHeader } from "@/components/PageHeader";
import { PageContent } from "@/layout/PageContent";
import { FormField } from "@/components/FormField";
import { TextInput } from "@/components/TextInput";
import { formatearFechaDeNegocio } from "@/lib/fecha-de-negocio";
import {
  CONSULTA_PAGOS,
  RUTA_PAGOS,
  ESTADOS_PAGO,
  type EstadoPago,
  type PagoResumen,
} from "./api";

const ESTADOS: Array<{ valor: "" | EstadoPago; etiqueta: string }> = [
  { valor: "", etiqueta: "Todos" },
  ...(Object.entries(ESTADOS_PAGO) as [EstadoPago, string][]).map(([valor, etiqueta]) => ({
    valor,
    etiqueta,
  })),
];

export function PagosPage() {
  const { tiene } = useAutoridad();
  const { activeCompanyId } = useCompany();
  const puedeVer = tiene("gobierno_pagos:view", "empresa");
  const puedeGestionar = tiene("gobierno_pagos:manage", "empresa");

  const [filtroEstado, setFiltroEstado] = useState<"" | EstadoPago>("");
  const [filtroOrden, setFiltroOrden] = useState("");
  const [filtroBeneficiario, setFiltroBeneficiario] = useState("");
  const [filtroDesde, setFiltroDesde] = useState("");
  const [filtroHasta, setFiltroHasta] = useState("");
  const [filtroCuenta, setFiltroCuenta] = useState("");
  const [filtroMedio, setFiltroMedio] = useState("");
  const [filtroMoneda, setFiltroMoneda] = useState("");
  const [filtroBusqueda, setFiltroBusqueda] = useState("");

  const pagosQuery = useQuery({
    queryKey: [
      ...CONSULTA_PAGOS,
      "lista",
      activeCompanyId,
      filtroEstado,
      filtroOrden,
      filtroBeneficiario,
      filtroDesde,
      filtroHasta,
      filtroCuenta,
      filtroMedio,
      filtroMoneda,
      filtroBusqueda,
    ],
    queryFn: async () => {
      const parametros = new URLSearchParams();
      if (filtroEstado) parametros.set("estado", filtroEstado);
      if (filtroOrden) parametros.set("order_id", filtroOrden);
      if (filtroBeneficiario) parametros.set("beneficiario", filtroBeneficiario);
      if (filtroDesde) parametros.set("desde", filtroDesde);
      if (filtroHasta) parametros.set("hasta", filtroHasta);
      if (filtroCuenta) parametros.set("account_id", filtroCuenta);
      if (filtroMedio) parametros.set("method_id", filtroMedio);
      if (filtroMoneda) parametros.set("moneda", filtroMoneda);
      if (filtroBusqueda) parametros.set("q", filtroBusqueda);
      const query = parametros.toString();
      return await apiFetch<PagoResumen[]>(`/gobierno/tesoreria/pagos${query ? `?${query}` : ""}`);
    },
    enabled: puedeVer,
    placeholderData: keepPreviousData,
  });

  if (!puedeVer) {
    return (
      <PageContent>
        <EmptyState
          title="No tiene permiso para consultar pagos"
          description="Su rol no incluye la capacidad de consulta de pagos de tesorería."
        />
      </PageContent>
    );
  }

  const descargarCsv = async () => {
    const parametros = new URLSearchParams();
    if (filtroEstado) parametros.set("estado", filtroEstado);
    if (filtroOrden) parametros.set("order_id", filtroOrden);
    if (filtroBeneficiario) parametros.set("beneficiario", filtroBeneficiario);
    if (filtroDesde) parametros.set("desde", filtroDesde);
    if (filtroHasta) parametros.set("hasta", filtroHasta);
    if (filtroCuenta) parametros.set("account_id", filtroCuenta);
    if (filtroMedio) parametros.set("method_id", filtroMedio);
    if (filtroMoneda) parametros.set("moneda", filtroMoneda);
    if (filtroBusqueda) parametros.set("q", filtroBusqueda);
    const query = parametros.toString();
    await descargarArchivo(
      `/gobierno/tesoreria/pagos/reporte.csv${query ? `?${query}` : ""}`,
      "pagos.csv",
    );
  };

  const limpiarFiltros = () => {
    setFiltroEstado("");
    setFiltroOrden("");
    setFiltroBeneficiario("");
    setFiltroDesde("");
    setFiltroHasta("");
    setFiltroCuenta("");
    setFiltroMedio("");
    setFiltroMoneda("");
    setFiltroBusqueda("");
  };

  return (
    <PageContent>
      <PageHeader
        crumbs={[
          { label: "Gobierno", to: "/gobierno" },
          { label: "Tesorería", to: RUTA_PAGOS },
          { label: "Pagos" },
        ]}
        title="Pagos"
        description="Consulta y gestión de pagos de tesorería"
        actions={
          <>
            {puedeGestionar && (
              <Link
                to={`${RUTA_PAGOS}/nuevo`}
                className="inline-flex items-center rounded-md bg-blue-600 px-3 py-2 text-sm font-medium text-white hover:bg-blue-700"
              >
                Nuevo pago
              </Link>
            )}
            <Button variant="secondary" onClick={() => void descargarCsv()}>
              Descargar CSV
            </Button>
          </>
        }
      />

      <div className="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <FormField label="Estado" htmlFor="pagos-estado">
          <select
            id="pagos-estado"
            value={filtroEstado}
            onChange={(event) => setFiltroEstado(event.target.value as "" | EstadoPago)}
            className="block w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
          >
            {ESTADOS.map((estado) => (
              <option key={estado.valor} value={estado.valor}>
                {estado.etiqueta}
              </option>
            ))}
          </select>
        </FormField>

        <FormField label="Orden" htmlFor="pagos-orden">
          <TextInput
            id="pagos-orden"
            value={filtroOrden}
            onChange={(event) => setFiltroOrden(event.target.value)}
            placeholder="Código o identificador"
          />
        </FormField>

        <FormField label="Beneficiario" htmlFor="pagos-beneficiario">
          <TextInput
            id="pagos-beneficiario"
            value={filtroBeneficiario}
            onChange={(event) => setFiltroBeneficiario(event.target.value)}
            placeholder="Nombre o razón social"
          />
        </FormField>

        <FormField label="Desde" htmlFor="pagos-desde">
          <TextInput
            id="pagos-desde"
            type="date"
            value={filtroDesde}
            onChange={(event) => setFiltroDesde(event.target.value)}
          />
        </FormField>

        <FormField label="Hasta" htmlFor="pagos-hasta">
          <TextInput
            id="pagos-hasta"
            type="date"
            value={filtroHasta}
            onChange={(event) => setFiltroHasta(event.target.value)}
          />
        </FormField>

        <FormField label="Cuenta" htmlFor="pagos-cuenta">
          <TextInput
            id="pagos-cuenta"
            value={filtroCuenta}
            onChange={(event) => setFiltroCuenta(event.target.value)}
            placeholder="Código de cuenta"
          />
        </FormField>

        <FormField label="Medio" htmlFor="pagos-medio">
          <TextInput
            id="pagos-medio"
            value={filtroMedio}
            onChange={(event) => setFiltroMedio(event.target.value)}
            placeholder="Código de medio"
          />
        </FormField>

        <FormField label="Moneda" htmlFor="pagos-moneda">
          <TextInput
            id="pagos-moneda"
            value={filtroMoneda}
            onChange={(event) => setFiltroMoneda(event.target.value)}
            placeholder="USD, VES…"
          />
        </FormField>

        <FormField label="Buscar" htmlFor="pagos-buscar" className="sm:col-span-2">
          <TextInput
            id="pagos-buscar"
            value={filtroBusqueda}
            onChange={(event) => setFiltroBusqueda(event.target.value)}
            placeholder="Código, concepto o referencia"
          />
        </FormField>
      </div>

      <div className="mt-4 flex justify-end">
        <Button variant="ghost" size="sm" onClick={limpiarFiltros}>
          Limpiar filtros
        </Button>
      </div>

      <p className="mt-4 text-sm text-slate-600">
        KONTROL registra pagos ejecutados por la Tesorería; no envía órdenes al banco.
      </p>

      {pagosQuery.isLoading && <LoadingState label="Cargando pagos" />}

      {pagosQuery.isError && (
        <ErrorState
          title="No se pudieron cargar los pagos"
          message={
            pagosQuery.error instanceof Error
              ? pagosQuery.error.message
              : "No se pudo completar la acción."
          }
          requestId={pagosQuery.error instanceof ApiError ? pagosQuery.error.requestId : undefined}
          onRetry={() => void pagosQuery.refetch()}
        />
      )}

      {pagosQuery.isSuccess && pagosQuery.data.length === 0 && (
        <EmptyState
          title="Aún no hay pagos"
          description="Los pagos se preparan sobre órdenes de pago emitidas."
        />
      )}

      {pagosQuery.isSuccess && pagosQuery.data.length > 0 && (
        <div
          className="mt-6 overflow-x-auto"
          tabIndex={0}
          role="region"
          aria-label="Lista de pagos"
        >
          <table className="min-w-full divide-y divide-slate-200">
            <thead className="bg-slate-50">
              <tr>
                <th scope="col" className="px-3 py-2 text-left text-xs font-semibold text-slate-700">
                  Código
                </th>
                <th scope="col" className="px-3 py-2 text-left text-xs font-semibold text-slate-700">
                  Estado
                </th>
                <th scope="col" className="px-3 py-2 text-left text-xs font-semibold text-slate-700">
                  Orden
                </th>
                <th scope="col" className="px-3 py-2 text-left text-xs font-semibold text-slate-700">
                  Beneficiario
                </th>
                <th scope="col" className="px-3 py-2 text-left text-xs font-semibold text-slate-700">
                  Cuenta
                </th>
                <th scope="col" className="px-3 py-2 text-left text-xs font-semibold text-slate-700">
                  Medio
                </th>
                <th scope="col" className="px-3 py-2 text-left text-xs font-semibold text-slate-700">
                  Moneda
                </th>
                <th scope="col" className="px-3 py-2 text-right text-xs font-semibold text-slate-700">
                  Monto
                </th>
                <th scope="col" className="px-3 py-2 text-left text-xs font-semibold text-slate-700">
                  Fecha de pago
                </th>
                <th scope="col" className="px-3 py-2 text-left text-xs font-semibold text-slate-700">
                  Fecha valor
                </th>
                <th scope="col" className="px-3 py-2 text-left text-xs font-semibold text-slate-700">
                  Referencia
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200">
              {pagosQuery.data.map((pago) => (
                <tr key={pago.id}>
                  <td className="whitespace-nowrap px-3 py-2 text-sm">
                    <Link
                      to={`${RUTA_PAGOS}/${pago.id}`}
                      className="text-blue-700 hover:underline"
                    >
                      {pago.codigo ?? "Borrador"}
                    </Link>
                  </td>
                  <td className="whitespace-nowrap px-3 py-2 text-sm">
                    {ESTADOS_PAGO[pago.estado]}
                  </td>
                  <td className="whitespace-nowrap px-3 py-2 text-sm">
                    {pago.orden_codigo ?? "—"}
                  </td>
                  <td className="px-3 py-2 text-sm">{pago.beneficiario ?? "—"}</td>
                  <td className="whitespace-nowrap px-3 py-2 text-sm">
                    {pago.cuenta_codigo ?? "—"}
                  </td>
                  <td className="whitespace-nowrap px-3 py-2 text-sm">
                    {pago.medio_codigo ?? "—"}
                  </td>
                  <td className="whitespace-nowrap px-3 py-2 text-sm">{pago.moneda}</td>
                  <td className="whitespace-nowrap px-3 py-2 text-right text-sm">
                    {pago.monto}
                  </td>
                  <td className="whitespace-nowrap px-3 py-2 text-sm">
                    {formatearFechaDeNegocio(pago.fecha_pago)}
                  </td>
                  <td className="whitespace-nowrap px-3 py-2 text-sm">
                    {pago.fecha_valor ? formatearFechaDeNegocio(pago.fecha_valor) : "—"}
                  </td>
                  <td className="whitespace-nowrap px-3 py-2 text-sm">
                    {pago.referencia_externa ?? "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </PageContent>
  );
}
