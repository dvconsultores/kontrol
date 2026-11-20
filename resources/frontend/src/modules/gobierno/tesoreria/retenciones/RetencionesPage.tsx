import { useState } from "react";
import { Link } from "react-router";
import { keepPreviousData, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch, ApiError } from "@/api/client";
import { descargarArchivo, mensajeDeDescarga } from "@/api/descargas";
import { useAutoridad } from "@/app/autoridad/AutoridadContext";
import { useNotifications } from "@/app/contexts/NotificationContext";
import { Button } from "@/components/Button";
import { ConfirmationDialog } from "@/components/ConfirmationDialog";
import { EmptyState } from "@/components/EmptyState";
import { ErrorState } from "@/components/ErrorState";
import { FormField } from "@/components/FormField";
import { LoadingState } from "@/components/LoadingState";
import { PageContent } from "@/layout/PageContent";
import { PageHeader } from "@/components/PageHeader";
import { formatearFechaDeNegocio, formatearInstante } from "@/lib/fecha-de-negocio";
import {
  API_RETENCIONES,
  Comprobante,
  CONSULTA_COMPROBANTES,
  CONSULTA_LIQUIDACIONES,
  ESTADOS_COMPROBANTE,
  ESTADOS_LIQUIDACION,
} from "./api";

type Pestana = "liquidaciones" | "comprobantes";

interface LiquidacionResumen {
  id: string;
  payment_id: string;
  pago_codigo: string;
  policy_codigo: string;
  policy_numero_version: number;
  estado: string;
  fecha_referencia: string;
  moneda: string;
  bruto: string;
  total_retenido: string;
  neto: string;
  beneficiario_nombre: string | null;
  comprobantes: number;
}



export function RetencionesPage() {
  const { tiene } = useAutoridad();
  const { notify } = useNotifications();
  const queryClient = useQueryClient();

  const puedeVer = tiene("gobierno_retenciones:view", "empresa");
  const puedeAnularComprobante = tiene("gobierno_retenciones:cancel", "empresa");

  const [pestana, setPestana] = useState<Pestana>("liquidaciones");
  const [estadoLiquidacion, setEstadoLiquidacion] = useState("");
  const [desde, setDesde] = useState("");
  const [hasta, setHasta] = useState("");
  const [estadoComprobante, setEstadoComprobante] = useState("");

  const [dialogoAnular, setDialogoAnular] = useState<Comprobante | null>(null);
  const [motivo, setMotivo] = useState("");
  const [sustituir, setSustituir] = useState(false);
  const [nombreCorregido, setNombreCorregido] = useState("");
  const [identificacionCorregida, setIdentificacionCorregida] = useState("");
  const [anulando, setAnulando] = useState(false);
  const [errorAnulacion, setErrorAnulacion] = useState<string | null>(null);

  const filtrosLiquidaciones = new URLSearchParams();
  if (estadoLiquidacion) filtrosLiquidaciones.set("estado", estadoLiquidacion);
  if (desde) filtrosLiquidaciones.set("desde", desde);
  if (hasta) filtrosLiquidaciones.set("hasta", hasta);
  const queryLiquidaciones = filtrosLiquidaciones.toString();

  const liquidacionesQuery = useQuery({
    queryKey: [...CONSULTA_LIQUIDACIONES, queryLiquidaciones],
    queryFn: async () => {
      return apiFetch<LiquidacionResumen[]>(
        `/gobierno/tesoreria/retenciones/liquidaciones?${queryLiquidaciones}`,
      );
    },
    placeholderData: keepPreviousData,
    enabled: puedeVer && pestana === "liquidaciones",
  });

  const filtrosComprobantes = new URLSearchParams();
  if (estadoComprobante)
    filtrosComprobantes.set("estado", estadoComprobante);
  const queryComprobantes = filtrosComprobantes.toString();

  const comprobantesQuery = useQuery({
    queryKey: [...CONSULTA_COMPROBANTES, queryComprobantes],
    queryFn: async () => {
      return apiFetch<Comprobante[]>(
        `/gobierno/tesoreria/retenciones/comprobantes?${queryComprobantes}`,
      );
    },
    placeholderData: keepPreviousData,
    enabled: puedeVer && pestana === "comprobantes",
  });

  const descargarCsv = async () => {
    try {
      await descargarArchivo(
        `/gobierno/tesoreria/retenciones/liquidaciones.csv?${queryLiquidaciones}`,
        "liquidaciones-retencion.csv",
      );
    } catch (error) {
      notify({
        type: "error",
        title: "Error",
        description: mensajeDeDescarga(error),
      });
    }
  };

  const descargarPdf = async (comprobante: Comprobante) => {
    try {
      await descargarArchivo(
        `${API_RETENCIONES}/comprobantes/${comprobante.id}/pdf`,
        `comprobante-${comprobante.codigo}.pdf`,
      );
    } catch (error) {
      notify({
        type: "error",
        title: "Error",
        description: mensajeDeDescarga(error),
      });
    }
  };

  const abrirAnulacion = (comprobante: Comprobante) => {
    setDialogoAnular(comprobante);
    setMotivo("");
    setSustituir(false);
    setNombreCorregido(comprobante.beneficiario_nombre);
    setIdentificacionCorregida(comprobante.identificacion_fiscal);
    setErrorAnulacion(null);
  };

  const anularComprobante = async () => {
    if (!dialogoAnular) return;
    if (motivo.trim().length < 10) {
      setErrorAnulacion("El motivo debe tener al menos 10 caracteres.");
      return;
    }
    if (anulando) return;
    setAnulando(true);
    setErrorAnulacion(null);
    try {
      await apiFetch(
        `${API_RETENCIONES}/comprobantes/${dialogoAnular.id}/anular`,
        {
          method: "POST",
          body: {
            motivo,
            sustituir,
            beneficiario: sustituir
              ? {
                  nombre: nombreCorregido,
                  identificacion_fiscal: identificacionCorregida,
                }
              : undefined,
          },
        },
      );
      setDialogoAnular(null);
      notify({ type: "success", title: "Comprobante anulado" });
      await queryClient.invalidateQueries({
        queryKey: CONSULTA_COMPROBANTES,
      });
      await queryClient.invalidateQueries({
        queryKey: ["gobierno", "tesoreria", "pagos"],
      });
    } catch (error) {
      setErrorAnulacion(
        error instanceof ApiError
          ? error.message
          : "No fue posible anular el comprobante.",
      );
    } finally {
      setAnulando(false);
    }
  };

  return (
    <PageContent>
      <PageHeader
        title="Retenciones"
        description="Liquidaciones de retenciones de los pagos y sus comprobantes."
      />

      <div role="tablist" aria-label="Secciones de retenciones" className="mt-6 flex gap-2 border-b border-border-default">
        <button
          role="tab"
          aria-selected={pestana === "liquidaciones"}
          onClick={() => setPestana("liquidaciones")}
          className={`px-4 py-2 text-sm font-medium ${
            pestana === "liquidaciones"
              ? "border-b-2 border-primary text-primary"
              : "text-muted-foreground"
          }`}
        >
          Liquidaciones
        </button>
        <button
          role="tab"
          aria-selected={pestana === "comprobantes"}
          onClick={() => setPestana("comprobantes")}
          className={`px-4 py-2 text-sm font-medium ${
            pestana === "comprobantes"
              ? "border-b-2 border-primary text-primary"
              : "text-muted-foreground"
          }`}
        >
          Comprobantes
        </button>
      </div>

      {pestana === "liquidaciones" && (
        <div role="tabpanel" aria-label="Liquidaciones" className="mt-6">
          <div className="flex flex-wrap gap-3">
            <FormField label="Estado" htmlFor="filtro-estado-liquidacion">
              <select
                id="filtro-estado-liquidacion"
                className="rounded-md border border-border-default px-3 py-2"
                value={estadoLiquidacion}
                onChange={(event) => setEstadoLiquidacion(event.target.value)}
              >
                <option value="">Todos</option>
                {Object.entries(ESTADOS_LIQUIDACION).map(([valor, etiqueta]) => (
                  <option key={valor} value={valor}>
                    {etiqueta}
                  </option>
                ))}
              </select>
            </FormField>
            <FormField label="Desde" htmlFor="filtro-desde">
              <input
                id="filtro-desde"
                type="date"
                className="rounded-md border border-border-default px-3 py-2"
                value={desde}
                onChange={(event) => setDesde(event.target.value)}
              />
            </FormField>
            <FormField label="Hasta" htmlFor="filtro-hasta">
              <input
                id="filtro-hasta"
                type="date"
                className="rounded-md border border-border-default px-3 py-2"
                value={hasta}
                onChange={(event) => setHasta(event.target.value)}
              />
            </FormField>
            <div className="self-end">
              <Button variant="secondary" onClick={descargarCsv}>
                Descargar CSV
              </Button>
            </div>
          </div>

          {liquidacionesQuery.isLoading ? (
            <LoadingState />
          ) : liquidacionesQuery.isError ? (
            <ErrorState
              title="No se pudieron cargar las liquidaciones"
              message={
                liquidacionesQuery.error instanceof ApiError
                  ? liquidacionesQuery.error.message
                  : "Error inesperado"
              }
            />
          ) : liquidacionesQuery.data?.length === 0 ? (
            <EmptyState
              title="Sin resultados"
              description="Aún no hay liquidaciones de retenciones"
            />
          ) : (
            <div
              role="region"
              aria-label="Liquidaciones de retenciones (desplazable)"
              tabIndex={0}
              className="mt-4 overflow-x-auto"
            >
              <table
                className="w-full text-sm"
                aria-label="Liquidaciones de retenciones"
              >
                <thead>
                  <tr className="border-b border-border-default text-left">
                    <th className="px-3 py-2">Pago</th>
                    <th className="px-3 py-2">Política</th>
                    <th className="px-3 py-2">Estado</th>
                    <th className="px-3 py-2">Fecha</th>
                    <th className="px-3 py-2">Moneda</th>
                    <th className="px-3 py-2">Bruto</th>
                    <th className="px-3 py-2">Retenido</th>
                    <th className="px-3 py-2">Neto</th>
                    <th className="px-3 py-2">Beneficiario</th>
                    <th className="px-3 py-2">Comprobantes</th>
                  </tr>
                </thead>
                <tbody>
                  {liquidacionesQuery.data?.map((liquidacion) => (
                    <tr
                      key={liquidacion.id}
                      className="border-b border-border-default"
                    >
                      <td className="px-3 py-2">
                        <Link
                          to={`/gobierno/tesoreria/pagos/${liquidacion.payment_id}`}
                          className="text-primary hover:underline"
                        >
                          {liquidacion.pago_codigo}
                        </Link>
                      </td>
                      <td className="px-3 py-2">
                        {liquidacion.policy_codigo} · v
                        {liquidacion.policy_numero_version}
                      </td>
                      <td className="px-3 py-2">
                        {ESTADOS_LIQUIDACION[liquidacion.estado] ??
                          liquidacion.estado}
                      </td>
                      <td className="px-3 py-2">
                        {formatearFechaDeNegocio(liquidacion.fecha_referencia)}
                      </td>
                      <td className="px-3 py-2">{liquidacion.moneda}</td>
                      <td className="px-3 py-2">{liquidacion.bruto}</td>
                      <td className="px-3 py-2">{liquidacion.total_retenido}</td>
                      <td className="px-3 py-2">{liquidacion.neto}</td>
                      <td className="px-3 py-2">
                        {liquidacion.beneficiario_nombre ?? "—"}
                      </td>
                      <td className="px-3 py-2">
                        {liquidacion.comprobantes}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {pestana === "comprobantes" && (
        <div role="tabpanel" aria-label="Comprobantes" className="mt-6">
          <div className="flex flex-wrap gap-3">
            <FormField label="Estado" htmlFor="filtro-estado-comprobante">
              <select
                id="filtro-estado-comprobante"
                className="rounded-md border border-border-default px-3 py-2"
                value={estadoComprobante}
                onChange={(event) => setEstadoComprobante(event.target.value)}
              >
                <option value="">Todos</option>
                {Object.entries(ESTADOS_COMPROBANTE).map(([valor, etiqueta]) => (
                  <option key={valor} value={valor}>
                    {etiqueta}
                  </option>
                ))}
              </select>
            </FormField>
          </div>

          {comprobantesQuery.isLoading ? (
            <LoadingState />
          ) : comprobantesQuery.isError ? (
            <ErrorState
              title="No se pudieron cargar los comprobantes"
              message={
                comprobantesQuery.error instanceof ApiError
                  ? comprobantesQuery.error.message
                  : "Error inesperado"
              }
            />
          ) : comprobantesQuery.data?.length === 0 ? (
            <EmptyState
              title="Sin resultados"
              description="Aún no hay comprobantes de retención"
            />
          ) : (
            <div
              role="region"
              aria-label="Comprobantes de retención (desplazable)"
              tabIndex={0}
              className="mt-4 overflow-x-auto"
            >
              <table
                className="w-full text-sm"
                aria-label="Comprobantes de retención"
              >
                <thead>
                  <tr className="border-b border-border-default text-left">
                    <th className="px-3 py-2">Código</th>
                    <th className="px-3 py-2">Concepto</th>
                    <th className="px-3 py-2">Beneficiario</th>
                    <th className="px-3 py-2">Monto</th>
                    <th className="px-3 py-2">Estado</th>
                    <th className="px-3 py-2">Emitido</th>
                    <th className="px-3 py-2">Pago</th>
                    <th className="px-3 py-2">Acciones</th>
                  </tr>
                </thead>
                <tbody>
                  {comprobantesQuery.data?.map((comprobante) => (
                    <tr
                      key={comprobante.id}
                      className="border-b border-border-default"
                    >
                      <td className="px-3 py-2">{comprobante.codigo}</td>
                      <td className="px-3 py-2">
                        {comprobante.concepto_codigo} ·{" "}
                        {comprobante.concepto_nombre}
                      </td>
                      <td className="px-3 py-2">
                        {comprobante.beneficiario_nombre}
                      </td>
                      <td className="px-3 py-2">
                        {comprobante.monto} {comprobante.moneda}
                      </td>
                      <td className="px-3 py-2">
                        {ESTADOS_COMPROBANTE[comprobante.estado] ??
                          comprobante.estado}
                      </td>
                      <td className="px-3 py-2">
                        {formatearInstante(comprobante.emitido_en)}
                      </td>
                      <td className="px-3 py-2">
                        <Link
                          to={`/gobierno/tesoreria/pagos/${comprobante.payment_id}`}
                          className="text-primary hover:underline"
                        >
                          {comprobante.pago_codigo}
                        </Link>
                      </td>
                      <td className="px-3 py-2">
                        <div className="flex gap-2">
                          <Button
                            variant="secondary"
                            onClick={() => descargarPdf(comprobante)}
                          >
                            Descargar PDF
                          </Button>
                          {comprobante.estado === "EMITIDO" &&
                            puedeAnularComprobante && (
                              <Button
                                variant="secondary"
                                onClick={() => abrirAnulacion(comprobante)}
                              >
                                Anular
                              </Button>
                            )}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      <ConfirmationDialog
        open={dialogoAnular !== null}
        onCancel={() => setDialogoAnular(null)}
        onConfirm={anularComprobante}
        title="Anular comprobante de retención"
        confirmLabel="Anular"
      >
        <div className="space-y-3">
          <FormField label="Motivo" htmlFor="motivo-anulacion">
            <textarea
              id="motivo-anulacion"
              className="w-full rounded-md border border-border-default px-3 py-2"
              value={motivo}
              onChange={(event) => setMotivo(event.target.value)}
              rows={3}
            />
          </FormField>
          <label className="flex items-center gap-2">
            <input
              type="checkbox"
              checked={sustituir}
              onChange={(event) => setSustituir(event.target.checked)}
            />
            <span>Emitir un comprobante sustituto</span>
          </label>
          {sustituir && (
            <>
              <FormField label="Nombre corregido" htmlFor="nombre-corregido">
                <input
                  id="nombre-corregido"
                  className="w-full rounded-md border border-border-default px-3 py-2"
                  value={nombreCorregido}
                  onChange={(event) => setNombreCorregido(event.target.value)}
                />
              </FormField>
              <FormField
                label="Identificación fiscal corregida"
                htmlFor="identificacion-corregida"
              >
                <input
                  id="identificacion-corregida"
                  className="w-full rounded-md border border-border-default px-3 py-2"
                  value={identificacionCorregida}
                  onChange={(event) =>
                    setIdentificacionCorregida(event.target.value)
                  }
                />
              </FormField>
            </>
          )}
          {errorAnulacion && (
            <p className="text-sm text-red-600" role="alert">
              {errorAnulacion}
            </p>
          )}
        </div>
      </ConfirmationDialog>
    </PageContent>
  );
}
