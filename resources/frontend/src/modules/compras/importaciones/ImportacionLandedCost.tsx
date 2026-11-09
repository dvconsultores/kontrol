import { useEffect, useState } from "react";
import { apiFetch, ApiError } from "@/api/client";
import { AsyncButton } from "@/components/AsyncButton";
import { Button } from "@/components/Button";
import { Autorizado } from "@/components/Autorizado";
import { ConfirmationDialog } from "@/components/ConfirmationDialog";
import { FormField } from "@/components/FormField";
import { TextInput } from "@/components/TextInput";
import { formatMoney, formatDate } from "@/lib/format";
import { formatearInstante } from "@/lib/fecha-de-negocio";
import type {
  AplicacionCosto,
  CapaDeCosto,
  GastoImportacion,
  VistaPrevia,
} from "./tipos";

type Props = {
  gasto: GastoImportacion;
  detalle: { id: string };
  capas: CapaDeCosto[];
  onCambios: () => void;
};

const CRITERIO_POR_VALOR = "VALUE";
const CRITERIO_POR_CANTIDAD = "QUANTITY";
const CRITERIO_MANUAL = "MANUAL";

const CRITERIOS: Array<{ value: string; label: string }> = [
  { value: CRITERIO_POR_VALOR, label: "Por valor" },
  { value: CRITERIO_POR_CANTIDAD, label: "Por cantidad" },
  { value: CRITERIO_MANUAL, label: "Manual" },
];

const CLASIFICACIONES: Array<{ value: string; label: string }> = [
  { value: "UNDETERMINED", label: "Sin determinar" },
  { value: "CAPITALIZABLE", label: "Capitalizable" },
  { value: "NOT_CAPITALIZABLE", label: "No capitalizable" },
];

function formatearCriterio(criterio: string): string {
  const coincide = CRITERIOS.find((item) => item.value === criterio);
  return coincide?.label ?? criterio;
}

function formatearParticipacion(participacion: string): string {
  const numero = Number(participacion);
  if (!Number.isFinite(numero)) return "0,00";
  return `${(numero * 100).toFixed(2)} %`;
}

export function ImportacionLandedCost({ gasto, detalle, capas, onCambios }: Props): React.JSX.Element {
  const [clasificacion, setClasificacion] = useState<string>(gasto.capitalization);
  const [criterio, setCriterio] = useState<string>("");
  const [importesManuales, setImportesManuales] = useState<Record<string, string>>({});
  const [vistaPrevia, setVistaPrevia] = useState<VistaPrevia | null>(null);
  const [errorVistaPrevia, setErrorVistaPrevia] = useState<string | null>(null);
  const [dialogoAplicarAbierto, setDialogoAplicarAbierto] = useState(false);
  const [dialogoRevertirAbierto, setDialogoRevertirAbierto] = useState(false);
  const [aplicacionARevertir, setAplicacionARevertir] = useState<AplicacionCosto | null>(null);
  const [motivoReversion, setMotivoReversion] = useState("");
  const [motivoReversionError, setMotivoReversionError] = useState<string | null>(null);

  const aplicacionVigente = gasto.applications.find(
    (aplicacion) => aplicacion.status === "APPLIED",
  );

  useEffect(() => {
    setClasificacion(gasto.capitalization);
  }, [gasto.capitalization]);

  async function guardarClasificacion() {
    setErrorVistaPrevia(null);
    try {
      await apiFetch(`/importaciones/${detalle.id}/expenses/${gasto.id}/classification`, {
        method: "POST",
        body: {
          version: gasto.version,
          capitalization: clasificacion,
        },
      });
      onCambios();
    } catch (err) {
      setErrorVistaPrevia(err instanceof Error ? err.message : "No se pudo guardar la clasificación.");
    }
  }

  async function generarVistaPrevia() {
    setErrorVistaPrevia(null);
    try {
      const body: Record<string, unknown> = { criterion: criterio };
      if (criterio === CRITERIO_MANUAL) {
        body.manual_amounts = importesManuales;
      }
      const respuesta = await apiFetch<VistaPrevia>(
        `/importaciones/${detalle.id}/expenses/${gasto.id}/allocation-preview`,
        {
          method: "POST",
          body,
        },
      );
      setVistaPrevia(respuesta);
    } catch (err) {
      setErrorVistaPrevia(err instanceof Error ? err.message : "No se pudo generar la vista previa.");
    }
  }

  async function confirmarAplicacion() {
    if (!vistaPrevia) return;
    setErrorVistaPrevia(null);
    try {
      const body: Record<string, unknown> = {
        criterion: criterio,
        preview_token: vistaPrevia.preview_token,
      };
      if (criterio === CRITERIO_MANUAL) {
        body.manual_amounts = importesManuales;
      }
      await apiFetch(`/importaciones/${detalle.id}/expenses/${gasto.id}/apply`, {
        method: "POST",
        body,
      });
      setDialogoAplicarAbierto(false);
      setVistaPrevia(null);
      onCambios();
    } catch (err) {
      setDialogoAplicarAbierto(false);
      const mensaje = err instanceof Error ? err.message : "No se pudo aplicar el costo.";
      setErrorVistaPrevia(mensaje);
      if (err instanceof ApiError && err.code === "IMPORT_COST_PREVIEW_STALE") {
        setVistaPrevia(null);
      }
    }
  }

  async function confirmarReversion() {
    if (!aplicacionARevertir) return;
    setMotivoReversionError(null);
    if (!motivoReversion.trim()) {
      setMotivoReversionError("Completa el motivo de reversión.");
      return;
    }
    try {
      await apiFetch(
        `/importaciones/${detalle.id}/cost-applications/${aplicacionARevertir.id}/reverse`,
        {
          method: "POST",
          body: {
            version: aplicacionARevertir.version,
            reason: motivoReversion,
          },
        },
      );
      setDialogoRevertirAbierto(false);
      setMotivoReversion("");
      setAplicacionARevertir(null);
      onCambios();
    } catch (err) {
      setMotivoReversionError(err instanceof Error ? err.message : "No se pudo revertir la aplicación.");
    }
  }

  return (
    <div className="mt-4 border-t border-border-default pt-4">
      {gasto.allowed_actions.classify ? (
        <div className="mt-2 flex flex-wrap items-end gap-2">
          <FormField label="Clasificación del costo">
            <select
              className="h-10 w-full rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900"
              value={clasificacion}
              onChange={(e) => setClasificacion(e.target.value)}
              aria-label="Clasificación del costo"
            >
              {CLASIFICACIONES.map((item) => (
                <option key={item.value} value={item.value}>
                  {item.label}
                </option>
              ))}
            </select>
          </FormField>
          <Autorizado
            operacion={["POST", `/importaciones/${detalle.id}/expenses/${gasto.id}/classification`]}
          >
            <AsyncButton type="button" onClick={guardarClasificacion}>
              Guardar clasificación
            </AsyncButton>
          </Autorizado>
        </div>
      ) : (
        <p className="mt-1 text-sm text-text-600">
          {CLASIFICACIONES.find((item) => item.value === gasto.capitalization)?.label ?? gasto.capitalization}
        </p>
      )}

      {gasto.status === "REGISTERED" && !aplicacionVigente ? (
        <div className="mt-4">
          <fieldset>
            <legend className="font-medium text-text-900">Criterio de reparto</legend>
            <div className="mt-2 space-y-2">
              {CRITERIOS.map((item) => (
                <label key={item.value} className="flex items-center gap-2 text-sm">
                  <input
                    type="radio"
                    name={`criterio-${gasto.id}`}
                    value={item.value}
                    checked={criterio === item.value}
                    onChange={() => {
                      setCriterio(item.value);
                      setVistaPrevia(null);
                    }}
                  />
                  {item.label}
                </label>
              ))}
            </div>
          </fieldset>

          {criterio === CRITERIO_MANUAL ? (
            <div className="mt-3 space-y-3">
              {capas.map((capa) => (
                <FormField
                  key={capa.layer_id}
                  label={`${capa.product_name ?? "Producto sin nombre"} · ${capa.receipt_code} (${capa.currency})`}
                >
                  <TextInput
                    inputMode="decimal"
                    value={importesManuales[capa.layer_id] ?? ""}
                    onChange={(e) => {
                      setVistaPrevia(null);
                      setImportesManuales((previo) => ({
                        ...previo,
                        [capa.layer_id]: e.target.value,
                      }));
                    }}
                  />
                </FormField>
              ))}
            </div>
          ) : null}

          <div className="mt-3">
            <Autorizado
              operacion={["POST", `/importaciones/${detalle.id}/expenses/${gasto.id}/allocation-preview`]}
            >
              <AsyncButton
                type="button"
                disabled={!criterio}
                onClick={generarVistaPrevia}
              >
                Generar vista previa
              </AsyncButton>
            </Autorizado>
          </div>
        </div>
      ) : null}

      {errorVistaPrevia ? (
        <div role="alert" className="mt-3 rounded-md border border-danger-200 bg-danger-50 p-3 text-sm text-danger-700">
          {errorVistaPrevia}
        </div>
      ) : null}

      {vistaPrevia ? (
        <div className="mt-4 rounded-md border border-border-default bg-surface-0 p-4">
          <h4 className="font-semibold text-text-900">Vista previa: aún no se ha aplicado nada</h4>
          <dl className="mt-2 grid grid-cols-1 gap-x-6 gap-y-1 text-sm sm:grid-cols-2">
            <div>
              <dt className="text-text-600">Gasto original</dt>
              <dd>
                {formatMoney(vistaPrevia.expense.amount)} {vistaPrevia.expense.currency}
              </dd>
            </div>
            <div>
              <dt className="text-text-600">Tasa</dt>
              <dd>
                {vistaPrevia.expense.rate_identity
                  ? "Misma moneda, sin conversión"
                  : `1 ${vistaPrevia.expense.currency} = ${formatMoney(vistaPrevia.expense.rate_value)}`}
                {vistaPrevia.expense.rate_date ? ` · ${formatDate(vistaPrevia.expense.rate_date)}` : ""}
              </dd>
            </div>
            <div>
              <dt className="text-text-600">Importe de valoración</dt>
              <dd>
                {formatMoney(vistaPrevia.valuation_amount)} {vistaPrevia.valuation_currency}
              </dd>
            </div>
            <div>
              <dt className="text-text-600">Repartido</dt>
              <dd>
                {formatMoney(vistaPrevia.distributed_total)} {vistaPrevia.valuation_currency}
              </dd>
            </div>
            <div>
              <dt className="text-text-600">Cuadre</dt>
              <dd>
                {Number(vistaPrevia.difference) === 0
                  ? "El reparto cuadra exactamente"
                  : `Diferencia: ${formatMoney(vistaPrevia.difference)} ${vistaPrevia.valuation_currency}`}
              </dd>
            </div>
          </dl>

          <div className="mt-3 overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead>
                <tr className="border-b border-border-default text-left text-text-600">
                  <th className="py-2 pr-3 font-medium">Producto</th>
                  <th className="py-2 pr-3 font-medium">Base</th>
                  <th className="py-2 pr-3 font-medium">Participación</th>
                  <th className="py-2 pr-3 font-medium">Importe asignado</th>
                  <th className="py-2 pr-3 font-medium">Costo actual</th>
                  <th className="py-2 pr-3 font-medium">Landed cost</th>
                  <th className="py-2 pr-3 font-medium">Costo resultante</th>
                </tr>
              </thead>
              <tbody>
                {vistaPrevia.lines.map((linea) => (
                  <tr key={linea.layer_id} className="border-b border-border-default">
                    <td className="py-2 pr-3">{linea.product_name ?? "—"}</td>
                    <td className="py-2 pr-3">
                      <div>{formatMoney(linea.base)}</div>
                      <div className="text-xs text-text-600">{linea.base_label}</div>
                    </td>
                    <td className="py-2 pr-3">{formatearParticipacion(linea.participation)}</td>
                    <td className="py-2 pr-3">
                      {formatMoney(linea.allocated_amount)} {vistaPrevia.valuation_currency}
                    </td>
                    <td className="py-2 pr-3">
                      {formatMoney(linea.before_unit_cost)} {vistaPrevia.valuation_currency}
                    </td>
                    <td className="py-2 pr-3">
                      {formatMoney(linea.after_landed_cost)} {vistaPrevia.valuation_currency}
                    </td>
                    <td className="py-2 pr-3">
                      {formatMoney(linea.after_unit_cost)} {vistaPrevia.valuation_currency}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {vistaPrevia.blocks.length > 0 ? (
            <div className="mt-3 space-y-2">
              {vistaPrevia.blocks.map((bloque) => (
                <div
                  key={bloque.code}
                  role="alert"
                  className="rounded-md border border-warning-200 bg-warning-50 p-3 text-sm text-warning-800"
                >
                  {bloque.message}
                </div>
              ))}
            </div>
          ) : null}

          {vistaPrevia.can_apply && gasto.allowed_actions.apply ? (
            <div className="mt-3">
              <Autorizado
                operacion={["POST", `/importaciones/${detalle.id}/expenses/${gasto.id}/apply`]}
              >
                <Button type="button" onClick={() => setDialogoAplicarAbierto(true)}>
                  Aplicar costo
                </Button>
              </Autorizado>
            </div>
          ) : null}
        </div>
      ) : null}

      {gasto.applications.length > 0 ? (
        <div className="mt-4">
          <h4 className="font-semibold text-text-900">Historial de aplicación</h4>
          <div className="mt-2 space-y-3">
            {gasto.applications.map((aplicacion) => (
              <div key={aplicacion.id} className="rounded-md border border-border-default p-3">
                <div className="flex flex-wrap items-center justify-between gap-2 text-sm">
                  <span className="font-medium">
                    {aplicacion.status === "APPLIED" ? "Aplicado" : "Revertido"}
                  </span>
                  <span>
                    {formatearCriterio(aplicacion.criterion)} · {formatMoney(aplicacion.valuation_amount)}{" "}
                    {aplicacion.valuation_currency}
                  </span>
                </div>
                <p className="mt-1 text-sm text-text-600">
                  {aplicacion.status === "APPLIED"
                    ? `${aplicacion.applied_by_name ?? "—"} · ${aplicacion.applied_at ? formatearInstante(aplicacion.applied_at) : "—"}`
                    : `${aplicacion.reversed_by_name ?? "—"} · ${aplicacion.reversed_at ? formatearInstante(aplicacion.reversed_at) : "—"}`}
                </p>
                {aplicacion.reversal_reason ? (
                  <p className="mt-1 text-sm text-text-600">Motivo: {aplicacion.reversal_reason}</p>
                ) : null}
                <div className="mt-2 overflow-x-auto">
                  <table className="min-w-full text-sm">
                    <thead>
                      <tr className="border-b border-border-default text-left text-text-600">
                        <th className="py-2 pr-3 font-medium">Producto</th>
                        <th className="py-2 pr-3 font-medium">Importe asignado</th>
                        <th className="py-2 pr-3 font-medium">Costo anterior</th>
                        <th className="py-2 pr-3 font-medium">Costo resultante</th>
                      </tr>
                    </thead>
                    <tbody>
                      {aplicacion.allocations.map((asignacion, indice) => (
                        <tr key={`${aplicacion.id}-${indice}`} className="border-b border-border-default">
                          <td className="py-2 pr-3">{asignacion.product_name ?? "—"}</td>
                          <td className="py-2 pr-3">
                            {formatMoney(asignacion.allocated_amount)} {aplicacion.valuation_currency}
                          </td>
                          <td className="py-2 pr-3">
                            {formatMoney(asignacion.before_unit_cost)} {aplicacion.valuation_currency}
                          </td>
                          <td className="py-2 pr-3">
                            {formatMoney(asignacion.after_unit_cost)} {aplicacion.valuation_currency}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                {aplicacion.status === "APPLIED" && aplicacion.can_reverse ? (
                  <div className="mt-2">
                    <Autorizado
                      operacion={["POST", `/importaciones/${detalle.id}/cost-applications/${aplicacion.id}/reverse`]}
                    >
                      <Button
                        type="button"
                        variant="secondary"
                        size="sm"
                        onClick={() => {
                          setMotivoReversion("");
                          setMotivoReversionError(null);
                          setAplicacionARevertir(aplicacion);
                          setDialogoRevertirAbierto(true);
                        }}
                      >
                        Revertir aplicación
                      </Button>
                    </Autorizado>
                  </div>
                ) : null}
                {aplicacion.status === "APPLIED" && !aplicacion.can_reverse ? (
                  <p className="mt-2 text-sm text-text-600">
                    No se puede revertir: el inventario ya se consumió.
                  </p>
                ) : null}
              </div>
            ))}
          </div>
        </div>
      ) : null}

      <ConfirmationDialog
        open={dialogoAplicarAbierto}
        title="Aplicar costo de importación"
        confirmLabel="Confirmar aplicación"
        onConfirm={confirmarAplicacion}
        onCancel={() => setDialogoAplicarAbierto(false)}
      >
        {vistaPrevia ? (
          <dl className="space-y-1 text-sm">
            <div>
              <dt className="text-text-600">Concepto</dt>
              <dd>{vistaPrevia.expense.concept}</dd>
            </div>
            <div>
              <dt className="text-text-600">Criterio</dt>
              <dd>{formatearCriterio(vistaPrevia.criterion)}</dd>
            </div>
            <div>
              <dt className="text-text-600">Importe de valoración</dt>
              <dd>
                {formatMoney(vistaPrevia.valuation_amount)} {vistaPrevia.valuation_currency}
              </dd>
            </div>
            <div>
              <dt className="text-text-600">Número de líneas</dt>
              <dd>{vistaPrevia.lines.length}</dd>
            </div>
            <div>
              <dt className="text-text-600">Total distribuido</dt>
              <dd>
                {formatMoney(vistaPrevia.distributed_total)} {vistaPrevia.valuation_currency}
              </dd>
            </div>
          </dl>
        ) : null}
      </ConfirmationDialog>

      <ConfirmationDialog
        open={dialogoRevertirAbierto}
        title="Revertir aplicación"
        confirmLabel="Confirmar reversión"
        danger
        onConfirm={confirmarReversion}
        onCancel={() => {
          setDialogoRevertirAbierto(false);
          setMotivoReversionError(null);
          setAplicacionARevertir(null);
        }}
      >
        <TextInput
          aria-label="Motivo de reversión"
          value={motivoReversion}
          onChange={(e) => setMotivoReversion(e.target.value)}
        />
        {motivoReversionError ? (
          <div role="alert" className="mt-2 rounded-md border border-danger-200 bg-danger-50 p-3 text-sm text-danger-700">
            {motivoReversionError}
          </div>
        ) : null}
      </ConfirmationDialog>
    </div>
  );
}
