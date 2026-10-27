/** Cotizaciones — sin reserva de inventario (FR-005-001, WF-02).
 *
 * El precio **no se teclea**: lo resuelve la autoridad comercial de la Spec 012
 * y la línea guarda de qué versión salió. Dejarlo en blanco es lo normal;
 * escribirlo es la excepción y exige un motivo.
 */
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { createColumnHelper } from "@tanstack/react-table";
import { useState } from "react";
import { NavLink } from "react-router";

import { apiFetch } from "@/api/client";
import type { CatalogItemSummary, PagedResult, Party, SalesQuoteSummary } from "@/api/types";
import { useNotifications } from "@/app/contexts/NotificationContext";
import { Autorizado } from "@/components/Autorizado";
import { AsyncButton } from "@/components/AsyncButton";
import { DataTable } from "@/components/DataTable";
import { FormField } from "@/components/FormField";
import { PageContent } from "@/layout/PageContent";
import { PageHeader } from "@/components/PageHeader";
import { TextInput } from "@/components/TextInput";

const columnHelper = createColumnHelper<SalesQuoteSummary>();

export function CotizacionesPage(): React.JSX.Element {
  const queryClient = useQueryClient();
  const { notify } = useNotifications();

  const [newCode, setNewCode] = useState("");
  const [newCustomer, setNewCustomer] = useState("");
  const [lineQuote, setLineQuote] = useState("");
  const [lineProduct, setLineProduct] = useState("");
  const [lineQty, setLineQty] = useState("");
  const [linePrice, setLinePrice] = useState("");
  const [lineReason, setLineReason] = useState("");

  const query = useQuery({
    queryKey: ["ventas", "cotizaciones"],
    queryFn: () => apiFetch<{ items: SalesQuoteSummary[] }>("/sales/quotes"),
    retry: false,
  });
  const customers = useQuery({
    queryKey: ["maestros", "terceros"],
    queryFn: () => apiFetch<PagedResult<Party>>("/maestros/terceros"),
    retry: false,
  });
  const products = useQuery({
    queryKey: ["maestros", "productos"],
    queryFn: () => apiFetch<PagedResult<CatalogItemSummary>>(`/maestros/catalogos/items?status=ACTIVE`),
    retry: false,
  });

  const refresh = (): void => {
    void queryClient.invalidateQueries({ queryKey: ["ventas", "cotizaciones"] });
  };

  const createQuote = async (): Promise<void> => {
    try {
      await apiFetch("/sales/quotes", {
        method: "POST",
        body: { code: newCode, customer_id: newCustomer, price_list: null, validity_until: null, currency: "VED" },
      });
      notify({ type: "success", title: "Cotización creada", description: newCode });
      setNewCode("");
      setNewCustomer("");
      refresh();
    } catch (err) {
      const message = err instanceof Error ? err.message : "No fue posible crear la cotización";
      notify({ type: "error", title: "No fue posible crear la cotización", description: message });
    }
  };

  const addLine = async (): Promise<void> => {
    if (!lineQuote || !lineProduct) return;
    try {
      await apiFetch(`/sales/quotes/${lineQuote}/lines`, {
        method: "POST",
        body: {
          product_id: lineProduct,
          quantity: Number(lineQty) || 0,
          // Vacío significa «resuélvelo tú». Enviar 0 sería decir que el
          // producto es gratis, que es otra cosa.
          unit_price: linePrice === "" ? null : Number(linePrice),
          manual_reason: linePrice === "" ? null : lineReason || null,
          discount: 0,
          tax_ref: null,
        },
      });
      notify({ type: "success", title: "Línea agregada", description: `Cotización ${lineQuote}` });
      setLineProduct("");
      setLineQty("");
      setLinePrice("");
      setLineReason("");
      refresh();
    } catch (err) {
      const message = err instanceof Error ? err.message : "No fue posible agregar la línea";
      notify({ type: "error", title: "No fue posible agregar la línea", description: message });
    }
  };

  const columns = [
    columnHelper.accessor("code", { header: "Código" }),
    columnHelper.accessor("customer_id", { header: "Cliente" }),
    columnHelper.accessor("currency", { header: "Moneda" }),
    columnHelper.accessor("status", { header: "Estado" }),
    columnHelper.display({
      id: "acciones",
      header: "",
      cell: ({ row }) => (
        <NavLink
          to={`/ventas/cotizaciones/${row.original.id}`}
          className="text-sm font-medium text-primary-600 hover:underline"
        >
          Ver detalle
        </NavLink>
      ),
    }),
  ];

  return (
    <PageContent maxWidth="full">
      <PageHeader
        title="Cotizaciones"
        description="Cotizaciones de venta sin reservar inventario."
        crumbs={[{ label: "Ventas" }, { label: "Cotizaciones" }]}
      />
      <Autorizado operacion={["POST", "/sales/quotes"]}>
        <section className="mb-4 rounded-lg border border-border-default bg-surface-0 p-4">
          <h2 className="mb-2 text-base font-semibold text-text-900">Nueva cotización</h2>
          <form className="flex flex-wrap items-end gap-3" onSubmit={(e) => e.preventDefault()}>
            <FormField label="Código" required>
              <TextInput value={newCode} onChange={(e) => setNewCode(e.target.value)} placeholder="COT-0001" required />
            </FormField>
            <FormField label="Cliente" required>
              <select value={newCustomer} onChange={(e) => setNewCustomer(e.target.value)} className="h-10 w-56 rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900">
                <option value="">Seleccionar…</option>
                {(customers.data?.items ?? []).map((c) => (
                  <option key={c.id} value={c.id}>{c.code} · {c.name}</option>
                ))}
              </select>
            </FormField>
            <AsyncButton type="submit" variant="primary" onClick={createQuote}>Crear</AsyncButton>
          </form>
        </section>
      </Autorizado>

      <Autorizado operacion={["POST", "/sales/quotes/_/lines"]}>
        <section className="mb-4 rounded-lg border border-border-default bg-surface-0 p-4">
          <h2 className="mb-2 text-base font-semibold text-text-900">Agregar línea</h2>
          <form className="flex flex-wrap items-end gap-3" onSubmit={(e) => e.preventDefault()}>
            <FormField label="Cotización" required>
              <select value={lineQuote} onChange={(e) => setLineQuote(e.target.value)} className="h-10 w-56 rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900">
                <option value="">Seleccionar…</option>
                {(query.data?.items ?? []).map((o) => (
                  <option key={o.id} value={o.id}>{o.code}</option>
                ))}
              </select>
            </FormField>
            <FormField label="Producto" required>
              <select value={lineProduct} onChange={(e) => setLineProduct(e.target.value)} className="h-10 w-56 rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900">
                <option value="">Seleccionar…</option>
                {(products.data?.items ?? []).map((p) => (
                  <option key={p.id} value={p.id}>{p.code} · {p.name}</option>
                ))}
              </select>
            </FormField>
            <FormField label="Cantidad" required>
              <TextInput type="number" value={lineQty} onChange={(e) => setLineQty(e.target.value)} placeholder="0" required />
            </FormField>
            <FormField label="Precio" help="Vacío: lo resuelve la lista de precios vigente">
              <TextInput type="number" value={linePrice} onChange={(e) => setLinePrice(e.target.value)} placeholder="Automático" />
            </FormField>
            {linePrice !== "" ? (
              <FormField label="Motivo del precio manual" required>
                <TextInput
                  value={lineReason}
                  onChange={(e) => setLineReason(e.target.value)}
                  placeholder="Por qué difiere del precio de lista"
                  required
                />
              </FormField>
            ) : null}
            <AsyncButton
              type="submit"
              variant="secondary"
              disabled={!lineQuote || !lineProduct || !lineQty || (linePrice !== "" && !lineReason)}
              onClick={addLine}
            >
              Agregar
            </AsyncButton>
          </form>
        </section>
      </Autorizado>

      <DataTable
        columns={columns}
        data={query.data?.items ?? []}
        loading={query.isLoading}
        error={query.isError ? "No fue posible cargar las cotizaciones." : null}
        getRowId={(row) => row.id}
        emptyTitle="Sin cotizaciones"
        emptyDescription="Aún no hay cotizaciones registradas."
      />
    </PageContent>
  );
}
