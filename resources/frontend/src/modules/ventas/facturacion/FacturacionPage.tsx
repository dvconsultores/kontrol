/**
 * Liberación y facturación — Spec 034.
 *
 * El proceso lo resume en una frase: «Almacén prepara. Confirmación verifica.
 * Facturación factura sobre un pedido previamente confirmado». Aquí se hace lo
 * tercero, y solo lo tercero: no se recoge, no se verifica de nuevo y no se
 * despacha.
 *
 * Son dos actos distintos y la pantalla los mantiene separados. **Generar la
 * factura** toma el contenido comercial del pedido —precio, descuento,
 * presentación y factor congelados—. **Emitir el documento fiscal** consume el
 * correlativo y el número de control, que asigna el motor fiscal, no esta
 * pantalla.
 */
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { createColumnHelper } from "@tanstack/react-table";
import { useState } from "react";

import { ApiError, apiFetch } from "@/api/client";
import type { BillableOrder, BillingInvoice, OrderBillingStatus } from "@/api/types";
import { useNotifications } from "@/app/contexts/NotificationContext";
import { AsyncButton } from "@/components/AsyncButton";
import { DataTable } from "@/components/DataTable";
import { FormField } from "@/components/FormField";
import { PageHeader } from "@/components/PageHeader";
import { TextInput } from "@/components/TextInput";
import { PageContent } from "@/layout/PageContent";

const cols = createColumnHelper<BillableOrder>();

function corto(id: string): string {
  return `${id.slice(0, 8)}…`;
}

export function FacturacionPage(): React.JSX.Element {
  const qc = useQueryClient();
  const { notify } = useNotifications();
  const [orderId, setOrderId] = useState<string | null>(null);
  const [serie, setSerie] = useState("");
  const [lote, setLote] = useState("");

  const pendientes = useQuery({
    queryKey: ["facturacion", "pendientes"],
    queryFn: () => apiFetch<{ items: BillableOrder[] }>("/sales/facturacion/pendientes"),
  });

  const estado = useQuery({
    queryKey: ["facturacion", "estado", orderId],
    queryFn: () => apiFetch<OrderBillingStatus>(`/sales/facturacion/${orderId}/factura`),
    enabled: Boolean(orderId),
  });

  function fallo(titulo: string) {
    return (e: unknown) =>
      notify({
        type: "error",
        title: titulo,
        description: e instanceof ApiError ? e.message : undefined,
      });
  }

  async function refrescar(): Promise<void> {
    await qc.invalidateQueries({ queryKey: ["facturacion"] });
  }

  async function solicitar(id: string): Promise<void> {
    try {
      await apiFetch(`/sales/facturacion/${id}/solicitar`, { method: "POST", body: {} });
      notify({ type: "success", title: "Facturación solicitada" });
      setOrderId(id);
      await refrescar();
    } catch (e) {
      fallo("No se pudo solicitar la facturación")(e);
    }
  }

  async function generar(): Promise<void> {
    if (!orderId) return;
    try {
      const f = await apiFetch<BillingInvoice>(`/sales/facturacion/${orderId}/generar`, {
        method: "POST",
        body: {},
      });
      notify({
        type: "success",
        title: "Factura generada",
        description: `Total ${f.total} ${f.currency}`,
      });
      await refrescar();
    } catch (e) {
      fallo("No se pudo generar la factura")(e);
    }
  }

  async function emitir(): Promise<void> {
    const f = estado.data?.invoice;
    if (!f) return;
    if (!serie || !lote) {
      notify({ type: "error", title: "Indique la serie y el lote de control" });
      return;
    }
    try {
      await apiFetch(`/sales/facturacion/${f.id}/emitir`, {
        method: "POST",
        body: { series_id: serie, batch_id: lote },
      });
      notify({ type: "success", title: "Documento fiscal emitido" });
      await refrescar();
    } catch (e) {
      fallo("No se pudo emitir el documento fiscal")(e);
    }
  }

  const columnas = [
    cols.accessor("code", { header: "Pedido" }),
    cols.accessor("status", { header: "Estado" }),
    cols.display({
      id: "accion",
      header: "Acción",
      cell: (c) => (
        <button
          type="button"
          onClick={() =>
            c.row.original.status === "CONFIRMED"
              ? void solicitar(c.row.original.order_id)
              : setOrderId(c.row.original.order_id)
          }
          className="text-sm font-medium text-primary-700 underline"
        >
          {c.row.original.status === "CONFIRMED" ? "Solicitar facturación" : "Facturar"}
        </button>
      ),
    }),
  ];

  const e = estado.data;
  const factura = e?.invoice;

  return (
    <PageContent>
      <PageHeader
        title="Facturación"
        description={
          "Se factura sobre un pedido previamente confirmado. Generar la factura toma lo " +
          "comercial del pedido; emitir consume el correlativo y el número de control."
        }
        crumbs={[{ label: "Ventas" }, { label: "Facturación" }]}
      />

      <section className="mb-4">
        <h2 className="mb-2 text-base font-semibold text-text-900">Pedidos por facturar</h2>
        <DataTable
          data={pendientes.data?.items ?? []}
          columns={columnas}
          emptyTitle="Nada por facturar"
          emptyDescription="Ningún pedido confirmado espera factura."
        />
      </section>

      {e ? (
        <section className="rounded-lg border border-border-default bg-surface-0 p-4">
          <h2 className="mb-1 text-base font-semibold text-text-900">
            Pedido {corto(e.order_id)} · {e.order_status}
          </h2>

          {!factura ? (
            <>
              <p className="mb-3 text-sm text-text-700">
                La factura se construye con el precio, el descuento y la presentación congelados en
                el pedido. El maestro de hoy no participa.
              </p>
              <AsyncButton onClick={generar}>Generar factura</AsyncButton>
            </>
          ) : (
            <>
              <table className="mb-3 w-full text-sm">
                <caption className="sr-only">Líneas de la factura</caption>
                <thead>
                  <tr className="border-b border-border-default text-left text-text-700">
                    <th scope="col" className="py-1">Producto</th>
                    <th scope="col">Cantidad</th>
                    <th scope="col">Base</th>
                    <th scope="col">Precio</th>
                    <th scope="col">Impuesto</th>
                    <th scope="col">Total</th>
                  </tr>
                </thead>
                <tbody>
                  {factura.lines.map((l, i) => (
                    <tr key={`${l.product_id}-${i}`} className="border-b border-border-subtle">
                      <td className="py-1 font-mono text-xs">{corto(l.product_id)}</td>
                      <td>{l.quantity}</td>
                      <td>{l.base_quantity ?? "—"}</td>
                      <td>{l.unit_price}</td>
                      <td>{l.tax_amount}</td>
                      <td>{l.total}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <p className="mb-3 text-sm text-text-700">
                Base {factura.base_fiscal} · Impuesto {factura.tax_total} ·{" "}
                <strong>Total {factura.total} {factura.currency}</strong>
              </p>
              {factura.lines_without_tax > 0 && factura.status !== "EMITTED" ? (
                <p className="mb-3 text-sm text-text-500" role="status">
                  {factura.lines_without_tax} línea(s) sin clasificación fiscal facturan sin
                  impuesto. Verifíquelo antes de emitir.
                </p>
              ) : null}

              {factura.status === "EMITTED" ? (
                <p className="text-sm text-text-700" role="status">
                  Documento fiscal emitido. Factura {factura.invoice_number} · control{" "}
                  {factura.control_number}. El pedido puede pasar a despacho.
                </p>
              ) : (
                <div className="flex flex-wrap items-end gap-3">
                  <FormField label="Serie de numeración" required>
                    <TextInput value={serie} onChange={(ev) => setSerie(ev.target.value)} />
                  </FormField>
                  <FormField label="Lote de control" required>
                    <TextInput value={lote} onChange={(ev) => setLote(ev.target.value)} />
                  </FormField>
                  <AsyncButton onClick={emitir}>Emitir documento fiscal</AsyncButton>
                </div>
              )}
            </>
          )}
        </section>
      ) : null}
    </PageContent>
  );
}
