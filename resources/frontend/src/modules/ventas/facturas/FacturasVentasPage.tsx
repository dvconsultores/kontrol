/** Facturas de venta — creación, líneas, base VES, tasa snapshot y estados (FR-005-030/031, WF-04). */
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { createColumnHelper } from "@tanstack/react-table";
import { useState } from "react";

import { apiFetch } from "@/api/client";
import type { CatalogItemSummary, PagedResult, Party, SalesInvoiceSummary } from "@/api/types";
import { useAutoridad } from "@/app/autoridad/AutoridadContext";
import { useNotifications } from "@/app/contexts/NotificationContext";
import { AsyncButton } from "@/components/AsyncButton";
import { Autorizado } from "@/components/Autorizado";
import { DataTable } from "@/components/DataTable";
import { FormField } from "@/components/FormField";
import { PageContent } from "@/layout/PageContent";
import { PageHeader } from "@/components/PageHeader";
import { TextInput } from "@/components/TextInput";

const columnHelper = createColumnHelper<SalesInvoiceSummary>();

export function FacturasVentasPage(): React.JSX.Element {
  const queryClient = useQueryClient();
  const { notify } = useNotifications();
  const { puede } = useAutoridad();

  const [newCustomer, setNewCustomer] = useState("");
  const [lineInvoice, setLineInvoice] = useState("");
  const [lineProduct, setLineProduct] = useState("");
  const [lineQty, setLineQty] = useState("");
  const [linePrice, setLinePrice] = useState("");

  const query = useQuery({
    queryKey: ["ventas", "facturas"],
    queryFn: () => apiFetch<PagedResult<SalesInvoiceSummary>>("/sales/invoices"),
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
    void queryClient.invalidateQueries({ queryKey: ["ventas", "facturas"] });
  };

  const createInvoice = async (): Promise<void> => {
    try {
      await apiFetch("/sales/invoices", {
        method: "POST",
        body: { customer_id: newCustomer, base_fiscal_currency: "VED" },
      });
      notify({ type: "success", title: "Factura creada", description: "Agregue las líneas a continuación." });
      setNewCustomer("");
      refresh();
    } catch (err) {
      const message = err instanceof Error ? err.message : "No fue posible crear la factura";
      notify({ type: "error", title: "No fue posible crear la factura", description: message });
    }
  };

  const addLine = async (): Promise<void> => {
    if (!lineInvoice || !lineProduct) return;
    try {
      await apiFetch(`/sales/invoices/${lineInvoice}/lines`, {
        method: "POST",
        body: { product_id: lineProduct, quantity: Number(lineQty) || 0, unit_price: Number(linePrice) || 0, tax_amount: 0 },
      });
      notify({ type: "success", title: "Línea agregada", description: `Factura ${lineInvoice}` });
      setLineProduct("");
      setLineQty("");
      setLinePrice("");
      refresh();
    } catch (err) {
      const message = err instanceof Error ? err.message : "No fue posible agregar la línea";
      notify({ type: "error", title: "No fue posible agregar la línea", description: message });
    }
  };

  const runTransition = async (id: string, target: string): Promise<void> => {
    await apiFetch(`/sales/invoices/${id}/transition`, { method: "POST", body: { target } });
    refresh();
    notify({ type: "success", title: "Factura actualizada", description: `Estado → ${target}` });
  };

  const columns = [
    columnHelper.accessor("invoice_number", { header: "Factura" }),
    columnHelper.accessor("customer_id", { header: "Cliente" }),
    columnHelper.accessor("base_fiscal", { header: "Base VES" }),
    columnHelper.accessor("tax_total", { header: "IVA" }),
    columnHelper.accessor("total", { header: "Total" }),
    columnHelper.accessor("status", { header: "Estado" }),
    columnHelper.display({
      id: "actions",
      header: "Acciones",
      cell: ({ row }) => {
        const a = row.original.allowed_actions;
        const transitions: Array<[string, string]> = [
          ["validate", "VALIDATED"],
          ["approve", "APPROVED"],
          ["emit", "EMITTED"],
          ["deliver", "DELIVERED"],
          ["void", "VOIDED"],
        ];
        return (
          <div className="flex justify-end gap-1">
            {transitions
              .filter(([key]) => a[key] && puede("POST", `/sales/invoices/${row.original.id}/transition`))
              .map(([key, target]) => (
                <AsyncButton key={key} size="sm" variant="secondary" onClick={() => runTransition(row.original.id, target)}>
                  {key}
                </AsyncButton>
              ))}
          </div>
        );
      },
    }),
  ];

  return (
    <PageContent maxWidth="full">
      <PageHeader
        title="Facturas de venta"
        description="Creación, líneas y estados. Documento comercial con base fiscal en VES y tasa snapshot (emisión fiscal en Spec 007)."
        crumbs={[{ label: "Ventas" }, { label: "Facturas" }]}
      />

      <Autorizado operacion={["POST", "/sales/invoices"]}>
        <section className="mb-4 rounded-lg border border-border-default bg-surface-0 p-4">
          <h2 className="mb-2 text-base font-semibold text-text-900">Nueva factura</h2>
          <form className="flex flex-wrap items-end gap-3" onSubmit={(e) => e.preventDefault()}>
            <FormField label="Cliente" required>
              <select value={newCustomer} onChange={(e) => setNewCustomer(e.target.value)} className="h-10 w-56 rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900">
                <option value="">Seleccionar…</option>
                {(customers.data?.items ?? []).filter((c) => (c.roles ?? []).includes("CLIENTE")).map((c) => (
                  <option key={c.id} value={c.id}>{c.name}</option>
                ))}
              </select>
            </FormField>
            <AsyncButton type="submit" variant="primary" onClick={createInvoice}>Crear</AsyncButton>
          </form>
        </section>
      </Autorizado>

      <Autorizado operacion={["POST", "/sales/invoices/_/lines"]}>
        <section className="mb-4 rounded-lg border border-border-default bg-surface-0 p-4">
          <h2 className="mb-2 text-base font-semibold text-text-900">Agregar línea</h2>
          <form className="flex flex-wrap items-end gap-3" onSubmit={(e) => e.preventDefault()}>
            <FormField label="Factura" required>
              <select value={lineInvoice} onChange={(e) => setLineInvoice(e.target.value)} className="h-10 w-56 rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900">
                <option value="">Seleccionar…</option>
                {(query.data?.items ?? []).map((f) => (
                  <option key={f.id} value={f.id}>{f.invoice_number || f.id.slice(0, 8)}</option>
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
            <FormField label="Precio" required>
              <TextInput type="number" value={linePrice} onChange={(e) => setLinePrice(e.target.value)} placeholder="0,00" required />
            </FormField>
            <AsyncButton type="submit" variant="secondary" onClick={addLine}>Agregar</AsyncButton>
          </form>
        </section>
      </Autorizado>

      <DataTable
        columns={columns}
        data={query.data?.items ?? []}
        loading={query.isLoading}
        error={query.isError ? "No fue posible cargar las facturas." : null}
        getRowId={(row) => row.id}
        emptyTitle="Sin facturas"
        emptyDescription="Aún no hay facturas de venta registradas."
      />
    </PageContent>
  );
}
