import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router";
import { apiFetch, ApiError } from "@/api/client";
import { AsyncButton } from "@/components/AsyncButton";
import { Button } from "@/components/Button";
import { Autorizado } from "@/components/Autorizado";
import { ConfirmationDialog } from "@/components/ConfirmationDialog";
import { FormField } from "@/components/FormField";
import { TextInput } from "@/components/TextInput";
import { SelectorDeTercero } from "@/modules/maestros/terceros/SelectorDeTercero";
import { formatMoney, formatDate } from "@/lib/format";
import { ImportacionLandedCost } from "./ImportacionLandedCost";
import type {
  CandidatoFactura,
  CapaDeCosto,
  DetalleCostos,
  DetalleImportacion,
  GastoImportacion,
} from "./tipos";

type Props = {
  detalle: DetalleImportacion;
  onCambios: () => void;
};

const ORIGEN_DIRECTO = "DIRECT_IMPORT_EXPENSE";
const ORIGEN_FACTURA = "LINKED_SUPPLIER_INVOICE";

function formatearFecha(fecha: string | null | undefined): string {
  if (!fecha) return "—";
  return formatDate(fecha);
}

function GastoCard({
  gasto,
  detalle,
  functionalCurrency,
  capas,
  onCambios,
}: {
  gasto: GastoImportacion;
  detalle: DetalleImportacion;
  functionalCurrency: string;
  capas: CapaDeCosto[];
  onCambios: () => void;
}): React.JSX.Element {
  const [dialogoAbierto, setDialogoAbierto] = useState(false);
  const [motivo, setMotivo] = useState("");
  const [motivoError, setMotivoError] = useState<string | null>(null);

  const anulado = gasto.status === "VOIDED";
  const tieneTasaIdentidad = gasto.rate.identity;
  const tasaTexto = tieneTasaIdentidad
    ? "Misma moneda, sin conversión"
    : `1 ${gasto.currency} = ${formatMoney(gasto.rate.value ?? "0")} ${functionalCurrency}`;

  async function confirmarAnulacion() {
    setMotivoError(null);
    if (!motivo.trim()) {
      setMotivoError("Completa el motivo de anulación.");
      return;
    }
    try {
      await apiFetch(`/importaciones/${detalle.id}/expenses/${gasto.id}/void`, {
        method: "POST",
        body: {
          version: gasto.version,
          reason: motivo,
        },
      });
      setDialogoAbierto(false);
      onCambios();
    } catch (err) {
      setMotivoError(err instanceof Error ? err.message : "No se pudo anular el gasto.");
    }
  }

  return (
    <li
      className={`rounded-md border border-border-default bg-surface-0 p-4 break-words ${
        anulado ? "opacity-70" : ""
      }`}
    >
      <div className="flex flex-wrap items-start justify-between gap-2">
        <span className="font-semibold">{gasto.concept}</span>
        {gasto.allowed_actions.void ? (
          <Autorizado operacion={["POST", `/importaciones/${detalle.id}/expenses/${gasto.id}/void`]}>
            <Button
              variant="secondary"
              size="sm"
              aria-label={`Anular gasto ${gasto.reference}`}
              onClick={() => setDialogoAbierto(true)}
            >
              Anular gasto
            </Button>
          </Autorizado>
        ) : null}
      </div>
      <dl className="mt-2 grid grid-cols-1 gap-x-6 gap-y-1 text-sm sm:grid-cols-2">
        <div>
          <dt className="text-text-600">Referencia</dt>
          <dd>{gasto.reference}</dd>
        </div>
        {gasto.supplier_name ? (
          <div>
            <dt className="text-text-600">Proveedor</dt>
            <dd>{gasto.supplier_name}</dd>
          </div>
        ) : null}
        <div>
          <dt className="text-text-600">Fecha</dt>
          <dd>{formatearFecha(gasto.expense_date)}</dd>
        </div>
        <div>
          <dt className="text-text-600">Monto</dt>
          <dd>
            {formatMoney(gasto.amount)} {gasto.currency}
          </dd>
        </div>
        <div className="sm:col-span-2">
          <dt className="text-text-600">Tasa</dt>
          <dd className="break-words">
            {tasaTexto}
            {gasto.rate.source ? ` · Fuente: ${gasto.rate.source}` : ""}
            {gasto.rate.date ? ` · ${formatearFecha(gasto.rate.date)}` : ""}
            {gasto.rate.derivation ? " · Tasa derivada" : ""}
          </dd>
        </div>
        <div>
          <dt className="text-text-600">Equivalente</dt>
          <dd>
            {formatMoney(gasto.functional_amount)} {functionalCurrency}
          </dd>
        </div>
        {gasto.invoice_number ? (
          <div>
            <dt className="text-text-600">Factura</dt>
            <dd>{gasto.invoice_number}</dd>
          </div>
        ) : null}
        {gasto.document ? (
          <div>
            <dt className="text-text-600">Documento de soporte</dt>
            <dd>{gasto.document.name}</dd>
          </div>
        ) : null}
        {gasto.username ? (
          <div>
            <dt className="text-text-600">Registrado por</dt>
            <dd>{gasto.username}</dd>
          </div>
        ) : null}
        <div>
          <dt className="text-text-600">Estado</dt>
          <dd>
            {anulado ? "Anulado" : "Registrado"}
            {anulado && gasto.void_reason ? ` · Motivo: ${gasto.void_reason}` : ""}
          </dd>
        </div>
      </dl>

      {!anulado ? (
        <ImportacionLandedCost
          gasto={gasto}
          detalle={detalle}
          capas={capas}
          onCambios={onCambios}
        />
      ) : null}

      <ConfirmationDialog
        open={dialogoAbierto}
        title="Anular gasto"
        description="El gasto queda en el historial y deja de sumar."
        confirmLabel="Anular gasto"
        danger
        onConfirm={confirmarAnulacion}
        onCancel={() => {
          setDialogoAbierto(false);
          setMotivoError(null);
        }}
      >
        <TextInput
          aria-label="Motivo de anulación"
          value={motivo}
          onChange={(e) => setMotivo(e.target.value)}
        />
        {motivoError ? (
          <div role="alert" className="mt-2 rounded-md border border-danger-200 bg-danger-50 p-3 text-sm text-danger-700">
            {motivoError}
          </div>
        ) : null}
      </ConfirmationDialog>
    </li>
  );
}

function CapaCard({ capa }: { capa: CapaDeCosto }): React.JSX.Element {
  return (
    <li className="rounded-md border border-border-default bg-surface-0 p-4 break-words">
      <div className="flex items-center justify-between gap-2">
        <span className="font-semibold">Recepción {capa.receipt_code}</span>
        {capa.partially_consumed ? (
          <span className="rounded-full bg-warning-100 px-2 py-0.5 text-xs text-warning-800">
            Parcialmente consumida
          </span>
        ) : null}
      </div>
      <dl className="mt-2 grid grid-cols-1 gap-x-6 gap-y-1 text-sm sm:grid-cols-2">
        <div>
          <dt className="text-text-600">Producto</dt>
          <dd>{capa.product_name ?? "—"}</dd>
        </div>
        <div>
          <dt className="text-text-600">Almacén</dt>
          <dd>{capa.warehouse_name ?? "—"}</dd>
        </div>
        <div>
          <dt className="text-text-600">Cantidad recibida</dt>
          <dd>{capa.quantity_in}</dd>
        </div>
        <div>
          <dt className="text-text-600">Restante</dt>
          <dd>{capa.quantity_remaining}</dd>
        </div>
        <div>
          <dt className="text-text-600">Costo unitario</dt>
          <dd>
            {formatMoney(capa.unit_cost)} {capa.currency}
          </dd>
        </div>
        <div>
          <dt className="text-text-600">Costo de importación aplicado</dt>
          <dd>
            {formatMoney(capa.landed_cost)} {capa.currency}
          </dd>
        </div>
        <div>
          <dt className="text-text-600">Costo efectivo</dt>
          <dd>
            {formatMoney(capa.effective_unit_cost)} {capa.currency}
          </dd>
        </div>
        <div>
          <dt className="text-text-600">Valor en inventario</dt>
          <dd>
            {formatMoney(capa.value)} {capa.currency}
          </dd>
        </div>
      </dl>
    </li>
  );
}

export function ImportacionCostos({ detalle, onCambios }: Props): React.JSX.Element {
  const [origen, setOrigen] = useState<string>(ORIGEN_DIRECTO);
  const [concepto, setConcepto] = useState("");
  const [proveedorId, setProveedorId] = useState("");
  const [referencia, setReferencia] = useState("");
  const [moneda, setMoneda] = useState("");
  const [fecha, setFecha] = useState("");
  const [facturaId, setFacturaId] = useState("");
  const [monto, setMonto] = useState("");
  const [documentoId, setDocumentoId] = useState("");
  const [errorFormulario, setErrorFormulario] = useState<string | null>(null);
  const [tasaNoDisponible, setTasaNoDisponible] = useState(false);
  const [exitoFormulario, setExitoFormulario] = useState<string | null>(null);

  const costosQuery = useQuery({
    queryKey: ["importaciones", detalle.id, "costos"],
    queryFn: async () => {
      return apiFetch<DetalleCostos>(`/importaciones/${detalle.id}/costs`);
    },
  });

  const facturasQuery = useQuery({
    queryKey: ["importaciones", detalle.id, "expense-invoice-candidates"],
    queryFn: async () => {
      const respuesta = await apiFetch<{ items: CandidatoFactura[] }>(
        `/importaciones/${detalle.id}/expense-invoice-candidates?page=1&page_size=100`,
      );
      return respuesta.items ?? [];
    },
    enabled: origen === ORIGEN_FACTURA,
  });

  const costos = costosQuery.data;
  const functionalCurrency = costos?.functional_currency ?? "";

  async function registrarGasto() {
    setErrorFormulario(null);
    setExitoFormulario(null);
    setTasaNoDisponible(false);

    const esDirecto = origen === ORIGEN_DIRECTO;
    const montoNormalizado = monto.replace(",", ".");

    if (!concepto.trim() || !montoNormalizado.trim()) {
      setErrorFormulario("Completa los campos obligatorios.");
      return;
    }
    if (esDirecto && (!proveedorId || !referencia.trim() || !moneda || !fecha)) {
      setErrorFormulario("Completa los campos obligatorios.");
      return;
    }
    if (!esDirecto && !facturaId) {
      setErrorFormulario("Completa los campos obligatorios.");
      return;
    }

    const body: Record<string, string> = {
      kind: origen,
      concept: concepto,
      amount: montoNormalizado,
    };

    if (esDirecto) {
      body.supplier_id = proveedorId;
      body.reference = referencia;
      body.currency = moneda;
      body.expense_date = fecha;
    } else {
      body.supplier_invoice_id = facturaId;
      if (fecha) body.expense_date = fecha;
    }

    if (documentoId) body.import_document_id = documentoId;

    try {
      await apiFetch(`/importaciones/${detalle.id}/expenses`, {
        method: "POST",
        body,
      });
      setExitoFormulario("Gasto registrado.");
      setConcepto("");
      setProveedorId("");
      setReferencia("");
      setMoneda("");
      setFecha("");
      setFacturaId("");
      setMonto("");
      setDocumentoId("");
      setOrigen(ORIGEN_DIRECTO);
      onCambios();
    } catch (err) {
      const mensaje = err instanceof Error ? err.message : "No se pudo registrar el gasto.";
      setErrorFormulario(mensaje);
      setTasaNoDisponible(err instanceof ApiError && err.code === "RATE_NOT_AVAILABLE");
    }
  }

  return (
    <section id="costos" className="rounded-lg border border-border-default bg-surface-0 p-6">
      <h2 className="mb-4 text-lg font-semibold text-text-900">Costos de importación</h2>

      {costosQuery.isLoading ? (
        <p className="text-sm text-text-600">Cargando costos…</p>
      ) : null}
      {costosQuery.isError ? (
        <div className="mb-4">
          <div role="alert" className="mb-3 rounded-md border border-danger-200 bg-danger-50 p-3 text-sm text-danger-700">
            No se pudieron cargar los costos.
          </div>
          <Button type="button" variant="secondary" onClick={() => void costosQuery.refetch()}>
            Reintentar
          </Button>
        </div>
      ) : null}

      {costos && !costosQuery.isError ? (
        <>
          <h3 className="mb-2 mt-6 text-md font-semibold text-text-900">Resumen</h3>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 rounded-md border border-border-default bg-surface-0 p-4 text-sm">
            <div>
              <span className="block text-text-600">Gastos registrados</span>
              <span>{costos.totals.count}</span>
            </div>
            <div>
              <span className="block text-text-600">Total en {functionalCurrency}</span>
              <span>{formatMoney(costos.totals.functional_total)}</span>
            </div>
            <div>
              <span className="block text-text-600">Por moneda de origen</span>
              {costos.totals.by_currency.length > 0 ? (
                costos.totals.by_currency.map((item) => (
                  <span key={item.currency} className="block">
                    {formatMoney(item.amount)} {item.currency}
                  </span>
                ))
              ) : (
                <span>Sin gastos</span>
              )}
            </div>
          </div>

          <h3 className="mb-2 mt-6 text-md font-semibold text-text-900">Mercancía según capas de costo</h3>
          {costos.goods_totals.length > 0 ? (
            <ul className="text-sm">
              {costos.goods_totals.map((item) => (
                <li key={item.currency}>
                  {formatMoney(item.amount)} {item.currency}
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-text-600">Sin capas de costo todavía</p>
          )}

          <h3 className="mb-2 mt-6 text-md font-semibold text-text-900">Valor en inventario</h3>
          {costos.inventory_totals.length > 0 ? (
            <ul className="text-sm">
              {costos.inventory_totals.map((item) => (
                <li key={item.currency}>
                  {formatMoney(item.amount)} {item.currency}
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-text-600">Sin valor en inventario</p>
          )}

          <h3 className="mb-2 mt-6 text-md font-semibold text-text-900">Gastos</h3>
          {costos.expenses.length === 0 ? (
            <p className="text-sm text-text-600">Todavía no hay gastos registrados.</p>
          ) : (
            <ul className="space-y-3">
              {costos.expenses.map((gasto) => (
                <GastoCard
                  key={gasto.id}
                  gasto={gasto}
                  detalle={detalle}
                  functionalCurrency={functionalCurrency}
                  capas={costos.layers}
                  onCambios={onCambios}
                />
              ))}
            </ul>
          )}

          <h3 className="mb-2 mt-6 text-md font-semibold text-text-900">Registrar gasto</h3>
          {costos.can_register ? (
            <Autorizado operacion={["POST", `/importaciones/${detalle.id}/expenses`]}>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <FormField label="Origen" required>
                  <select
                    className="h-10 w-full rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900"
                    value={origen}
                    onChange={(e) => {
                      setOrigen(e.target.value);
                      setErrorFormulario(null);
                    }}
                  >
                    <option value={ORIGEN_DIRECTO}>Gasto directo</option>
                    <option value={ORIGEN_FACTURA}>Factura de proveedor</option>
                  </select>
                </FormField>

                <FormField label="Concepto" required>
                  <TextInput
                    value={concepto}
                    onChange={(e) => setConcepto(e.target.value)}
                  />
                </FormField>

                {origen === ORIGEN_DIRECTO ? (
                  <>
                    <FormField label="Proveedor" required>
                      <SelectorDeTercero
                        soloActivos
                        value={proveedorId}
                        onChange={(id) => setProveedorId(id)}
                      />
                    </FormField>
                    <FormField label="Referencia" required>
                      <TextInput
                        value={referencia}
                        onChange={(e) => setReferencia(e.target.value)}
                      />
                    </FormField>
                    <FormField label="Moneda" required>
                      <select
                        className="h-10 w-full rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900"
                        value={moneda}
                        onChange={(e) => setMoneda(e.target.value)}
                      >
                        <option value="" disabled>
                          Selecciona una moneda
                        </option>
                        {costos.currencies.map((codigo) => (
                          <option key={codigo} value={codigo}>
                            {codigo}
                          </option>
                        ))}
                      </select>
                    </FormField>
                    <FormField label="Fecha" required>
                      <TextInput
                        type="date"
                        value={fecha}
                        onChange={(e) => setFecha(e.target.value)}
                      />
                    </FormField>
                  </>
                ) : (
                  <>
                    <FormField label="Factura" required>
                      <select
                        className="h-10 w-full rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900"
                        value={facturaId}
                        onChange={(e) => setFacturaId(e.target.value)}
                      >
                        <option value="" disabled>
                          Selecciona una factura
                        </option>
                        {(facturasQuery.data ?? []).map((factura) => (
                          <option key={factura.id} value={factura.id}>
                            {factura.invoice_number} · {factura.supplier_name ?? "—"} · disponible{" "}
                            {formatMoney(factura.available)} {factura.currency}
                          </option>
                        ))}
                      </select>
                      {facturasQuery.isSuccess && (facturasQuery.data?.length ?? 0) === 0 ? (
                        <p className="mt-1 text-sm text-text-600">No hay facturas con saldo disponible.</p>
                      ) : null}
                      <p className="mt-1 text-sm text-text-600">
                        Indica solo la parte de la factura que corresponde a esta importación.
                      </p>
                    </FormField>
                    <FormField label="Fecha">
                      <TextInput
                        type="date"
                        value={fecha}
                        onChange={(e) => setFecha(e.target.value)}
                      />
                    </FormField>
                  </>
                )}

                <FormField label="Monto" required>
                  <TextInput
                    inputMode="decimal"
                    value={monto}
                    onChange={(e) => setMonto(e.target.value)}
                  />
                </FormField>
                <FormField label="Documento de soporte">
                  <select
                    className="h-10 w-full rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900"
                    value={documentoId}
                    onChange={(e) => setDocumentoId(e.target.value)}
                  >
                    <option value="">Sin documento</option>
                    {detalle.documents.map((documento) => (
                      <option key={documento.id} value={documento.id}>
                        {documento.name}
                      </option>
                    ))}
                  </select>
                </FormField>
              </div>

              {errorFormulario ? (
                <div role="alert" className="mt-3 rounded-md border border-danger-200 bg-danger-50 p-3 text-sm text-danger-700">
                  {errorFormulario}
                  {tasaNoDisponible ? (
                    <div className="mt-1">
                      <Link to="/tesoreria/tasas" className="text-brand-600 hover:text-brand-700">
                        Registrar tasa en Tesorería
                      </Link>
                    </div>
                  ) : null}
                </div>
              ) : null}
              {exitoFormulario ? (
                <div role="status" className="mt-3 rounded-md border border-success-200 bg-success-50 p-3 text-sm text-success-700">
                  {exitoFormulario}
                </div>
              ) : null}

              <div className="mt-3">
                <AsyncButton type="button" onClick={registrarGasto}>
                  Registrar gasto
                </AsyncButton>
              </div>
            </Autorizado>
          ) : (
            <p className="text-sm text-text-600">Los gastos se registran después de vincular la orden de compra.</p>
          )}

          <h3 className="mb-2 mt-6 text-md font-semibold text-text-900">Capas de costo de esta importación</h3>
          {costos.layers.length === 0 ? (
            <p className="text-sm text-text-600">Aún no hay capas: se crean al aceptar la recepción.</p>
          ) : (
            <ul className="space-y-3">
              {costos.layers.map((capa) => (
                <CapaCard key={`${capa.receipt_code}-${capa.product_code}`} capa={capa} />
              ))}
            </ul>
          )}
        </>
      ) : null}

    </section>
  );
}
