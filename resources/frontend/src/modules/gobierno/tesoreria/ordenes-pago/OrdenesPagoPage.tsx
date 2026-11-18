import { useMemo, useState } from "react";
import { Link } from "react-router";
import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { apiFetch, ApiError } from "@/api/client";
import { descargarArchivo } from "@/api/descargas";
import { useAutoridad } from "@/app/autoridad/AutoridadContext";
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
  CONSULTA_ORDENES,
  RUTA_ORDENES,
  consultaOrdenes,
  etiquetaEstadoOrden,
  type EstadoOrdenPago,
  type OrdenPago,
} from "./api";

interface Ejercicio {
  id: string;
  anio: string;
  moneda_funcional: string;
  estado: "BORRADOR" | "APROBADO" | "RECONDUCIDO" | "CERRADO";
  version: number;
}

interface EjerciciosRespuesta {
  items: Ejercicio[];
  total: number;
}


const ESTADOS: Array<{
  valor: "" | EstadoOrdenPago;
  etiqueta: string;
}> = [
  { valor: "", etiqueta: "Todos" },
  { valor: "BORRADOR", etiqueta: "Borrador" },
  { valor: "EMITIDA", etiqueta: "Emitida" },
  { valor: "ANULADA", etiqueta: "Anulada" },
];

export function OrdenesPagoPage() {
  const { tiene } = useAutoridad();
  const puedeVer = tiene("gobierno_ordenes_pago:view", "empresa");
  const puedeGestionar = tiene("gobierno_ordenes_pago:manage", "empresa");

  const ejerciciosQuery = useQuery({
    queryKey: ["gobierno", "presupuesto", "ejercicios"],
    queryFn: () => apiFetch<EjerciciosRespuesta>("/gobierno/presupuesto/ejercicios"),
    enabled: puedeVer,
  });

  const ejerciciosDisponibles = useMemo(
    () =>
      (ejerciciosQuery.data?.items ?? []).filter(
        (ejercicio) =>
          ejercicio.estado === "APROBADO" || ejercicio.estado === "RECONDUCIDO",
      ),
    [ejerciciosQuery.data],
  );

  const ejercicioPorDefecto = useMemo(() => {
    if (ejerciciosDisponibles.length === 0) return null;
    return ejerciciosDisponibles.reduce((mayor, ejercicio) =>
      Number(ejercicio.anio) > Number(mayor.anio) ? ejercicio : mayor,
    );
  }, [ejerciciosDisponibles]);

  const [ejercicioId, setEjercicioId] = useState<string>("");
  const ejercicioSeleccionado =
    ejerciciosDisponibles.find((ejercicio) => ejercicio.id === ejercicioId) ??
    ejercicioPorDefecto;

  const [filtroEstado, setFiltroEstado] = useState<"" | EstadoOrdenPago>("");
  const [filtroDesde, setFiltroDesde] = useState("");
  const [filtroHasta, setFiltroHasta] = useState("");
  const [filtroBeneficiario, setFiltroBeneficiario] = useState("");
  const [filtroMoneda, setFiltroMoneda] = useState("");
  const [filtroBusqueda, setFiltroBusqueda] = useState("");

  const ordenesQuery = useQuery({
    queryKey: [
      ...CONSULTA_ORDENES,
      "lista",
      ejercicioSeleccionado?.id ?? "",
      filtroEstado,
      filtroDesde,
      filtroHasta,
      filtroBeneficiario,
      filtroMoneda,
      filtroBusqueda,
    ],
    queryFn: () =>
      apiFetch<OrdenPago[]>(
        consultaOrdenes(ejercicioSeleccionado?.id ?? "", {
          estado: filtroEstado || undefined,
          desde: filtroDesde || undefined,
          hasta: filtroHasta || undefined,
          beneficiario: filtroBeneficiario || undefined,
          moneda: filtroMoneda || undefined,
          q: filtroBusqueda || undefined,
        }),
      ),
    enabled: puedeVer && Boolean(ejercicioSeleccionado),
    placeholderData: keepPreviousData,
  });

  if (!puedeVer) {
    return (
      <PageContent>
        <EmptyState
          title="No tiene permiso para consultar órdenes de pago"
          description="Su rol no incluye la capacidad de consulta de órdenes de pago."
        />
      </PageContent>
    );
  }

  const descargarCsv = async () => {
    if (!ejercicioSeleccionado) return;
    const parametros = new URLSearchParams();
    if (filtroEstado) parametros.set("estado", filtroEstado);
    if (filtroDesde) parametros.set("desde", filtroDesde);
    if (filtroHasta) parametros.set("hasta", filtroHasta);
    if (filtroBeneficiario) parametros.set("beneficiario", filtroBeneficiario);
    if (filtroMoneda) parametros.set("moneda", filtroMoneda);
    if (filtroBusqueda) parametros.set("q", filtroBusqueda);
    const query = parametros.toString();
    await descargarArchivo(
      `/gobierno/tesoreria/ejercicios/${ejercicioSeleccionado.id}/ordenes-pago/reporte.csv${query ? `?${query}` : ""}`,
      `ordenes-de-pago-${ejercicioSeleccionado.anio}.csv`,
    );
  };

  const limpiarFiltros = () => {
    setFiltroEstado("");
    setFiltroDesde("");
    setFiltroHasta("");
    setFiltroBeneficiario("");
    setFiltroMoneda("");
    setFiltroBusqueda("");
  };

  const codigosCausados = (orden: OrdenPago): string =>
    orden.lineas.map((linea) => linea.codigo).join(", ");

  return (
    <PageContent>
      <PageHeader
        crumbs={[
          { label: "Gobierno", to: "/gobierno" },
          { label: "Tesorería", to: RUTA_ORDENES },
          { label: "Órdenes de pago" },
        ]}
        title="Órdenes de pago"
        description="Consulta y gestión de órdenes de pago del ejercicio"
        actions={
          <>
            {puedeGestionar && ejercicioSeleccionado && (
              <Link
                to={`/gobierno/tesoreria/ordenes-pago/nueva?ejercicio=${ejercicioSeleccionado.id}`}
                className="inline-flex items-center rounded-md bg-blue-600 px-3 py-2 text-sm font-medium text-white hover:bg-blue-700"
              >
                Nueva orden de pago
              </Link>
            )}
            <Button variant="secondary" onClick={() => void descargarCsv()}>
              Descargar CSV
            </Button>
          </>
        }
      />

      <div className="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <FormField label="Ejercicio" htmlFor="ordenes-ejercicio">
          <select
            id="ordenes-ejercicio"
            value={ejercicioSeleccionado?.id ?? ""}
            onChange={(event) => setEjercicioId(event.target.value)}
            className="block w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
          >
            {ejerciciosDisponibles.map((ejercicio) => (
              <option key={ejercicio.id} value={ejercicio.id}>
                {ejercicio.anio}
              </option>
            ))}
          </select>
        </FormField>

        <FormField label="Estado" htmlFor="ordenes-estado">
          <select
            id="ordenes-estado"
            value={filtroEstado}
            onChange={(event) => setFiltroEstado(event.target.value as "" | EstadoOrdenPago)}
            className="block w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
          >
            {ESTADOS.map((estado) => (
              <option key={estado.valor} value={estado.valor}>
                {estado.etiqueta}
              </option>
            ))}
          </select>
        </FormField>

        <FormField label="Desde" htmlFor="ordenes-desde">
          <TextInput
            id="ordenes-desde"
            type="date"
            value={filtroDesde}
            onChange={(event) => setFiltroDesde(event.target.value)}
          />
        </FormField>

        <FormField label="Hasta" htmlFor="ordenes-hasta">
          <TextInput
            id="ordenes-hasta"
            type="date"
            value={filtroHasta}
            onChange={(event) => setFiltroHasta(event.target.value)}
          />
        </FormField>

        <FormField label="Beneficiario" htmlFor="ordenes-beneficiario">
          <TextInput
            id="ordenes-beneficiario"
            value={filtroBeneficiario}
            onChange={(event) => setFiltroBeneficiario(event.target.value)}
            placeholder="Nombre o razón social"
          />
        </FormField>

        <FormField label="Moneda" htmlFor="ordenes-moneda">
          <TextInput
            id="ordenes-moneda"
            value={filtroMoneda}
            onChange={(event) => setFiltroMoneda(event.target.value)}
            placeholder="USD, VES…"
          />
        </FormField>

        <FormField label="Buscar" htmlFor="ordenes-buscar" className="sm:col-span-2">
          <TextInput
            id="ordenes-buscar"
            value={filtroBusqueda}
            onChange={(event) => setFiltroBusqueda(event.target.value)}
            placeholder="Causado, compromiso o texto libre"
          />
        </FormField>
      </div>

      <div className="mt-4 flex justify-end">
        <Button variant="ghost" size="sm" onClick={limpiarFiltros}>
          Limpiar filtros
        </Button>
      </div>

      {ejerciciosQuery.isLoading && <LoadingState label="Cargando ejercicios presupuestarios" />}

      {ejerciciosQuery.isError && (
        <ErrorState
          title="No se pudieron cargar los ejercicios presupuestarios"
          message={
            ejerciciosQuery.error instanceof Error
              ? ejerciciosQuery.error.message
              : "No se pudo completar la acción."
          }
          requestId={
            ejerciciosQuery.error instanceof ApiError ? ejerciciosQuery.error.requestId : undefined
          }
          onRetry={() => void ejerciciosQuery.refetch()}
        />
      )}

      {ejerciciosQuery.isSuccess && ejerciciosDisponibles.length === 0 && (
        <EmptyState
          title="No hay ejercicios presupuestarios aprobados"
          description="Las órdenes de pago se preparan sobre un ejercicio aprobado o reconducido en Presupuesto."
        />
      )}

      {ordenesQuery.isLoading && <LoadingState label="Cargando órdenes de pago" />}

      {ordenesQuery.isError && (
        <ErrorState
          title="No se pudieron cargar las órdenes de pago"
          message={
            ordenesQuery.error instanceof Error
              ? ordenesQuery.error.message
              : "No se pudo completar la acción."
          }
          requestId={
            ordenesQuery.error instanceof ApiError ? ordenesQuery.error.requestId : undefined
          }
          onRetry={() => void ordenesQuery.refetch()}
        />
      )}

      {ordenesQuery.isSuccess && ordenesQuery.data.length === 0 && (
        <EmptyState
          title="Aún no hay órdenes de pago en este ejercicio"
          description="Las órdenes de pago aparecerán aquí cuando existan."
        />
      )}

      {ordenesQuery.isSuccess && ordenesQuery.data.length > 0 && (
        <div
          className="mt-6 overflow-x-auto"
          tabIndex={0}
          role="region"
          aria-label="Tabla de órdenes de pago"
        >
          <table className="min-w-full divide-y divide-slate-200">
            <thead className="bg-slate-50">
              <tr>
                <th scope="col" className="px-3 py-2 text-left text-xs font-semibold text-slate-700">
                  Código
                </th>
                <th scope="col" className="px-3 py-2 text-left text-xs font-semibold text-slate-700">
                  Fecha
                </th>
                <th scope="col" className="px-3 py-2 text-left text-xs font-semibold text-slate-700">
                  Beneficiario
                </th>
                <th scope="col" className="px-3 py-2 text-right text-xs font-semibold text-slate-700">
                  Monto
                </th>
                <th scope="col" className="px-3 py-2 text-left text-xs font-semibold text-slate-700">
                  Moneda
                </th>
                <th scope="col" className="px-3 py-2 text-left text-xs font-semibold text-slate-700">
                  Estado
                </th>
                <th scope="col" className="px-3 py-2 text-left text-xs font-semibold text-slate-700">
                  Causados
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200">
              {ordenesQuery.data.map((orden) => (
                <tr key={orden.id}>
                  <td className="whitespace-nowrap px-3 py-2 text-sm">
                    {orden.codigo ? (
                      <Link
                        to={`${RUTA_ORDENES}/ordenes-pago/${orden.id}`}
                        className="text-blue-700 hover:underline"
                      >
                        {orden.codigo}
                      </Link>
                    ) : (
                      <Link
                        to={`${RUTA_ORDENES}/ordenes-pago/${orden.id}`}
                        className="text-blue-700 hover:underline"
                      >
                        Borrador
                      </Link>
                    )}
                  </td>
                  <td className="whitespace-nowrap px-3 py-2 text-sm">
                    {formatearFechaDeNegocio(orden.fecha_orden)}
                  </td>
                  <td className="px-3 py-2 text-sm">{orden.beneficiario ?? "—"}</td>
                  <td className="whitespace-nowrap px-3 py-2 text-right text-sm">
                    {orden.monto}
                  </td>
                  <td className="whitespace-nowrap px-3 py-2 text-sm">{orden.moneda}</td>
                  <td className="whitespace-nowrap px-3 py-2 text-sm">
                    {etiquetaEstadoOrden(orden.estado)}
                  </td>
                  <td className="px-3 py-2 text-sm">{codigosCausados(orden)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </PageContent>
  );
}
