/** Facturas del proveedor — creación, líneas, duplicidad y estados (FR-004-040/041/042, WF-04). */
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { createColumnHelper } from "@tanstack/react-table";
import { useState } from "react";

import { apiFetch } from "@/api/client";
import type { PagedResult, SupplierInvoiceSummary } from "@/api/types";
import { useAutoridad } from "@/app/autoridad/AutoridadContext";
import { useNotifications } from "@/app/contexts/NotificationContext";
import { AsyncButton } from "@/components/AsyncButton";
import { Autorizado } from "@/components/Autorizado";
import { DataTable } from "@/components/DataTable";
import { FormField } from "@/components/FormField";
import { PageContent } from "@/layout/PageContent";
import { PageHeader } from "@/components/PageHeader";
import { TextInput } from "@/components/TextInput";
import { SelectorDeTercero } from "@/modules/maestros/terceros/SelectorDeTercero";
import { SelectorDeArticulo } from "@/modules/maestros/catalogo/SelectorDeArticulo";

const columnHelper = createColumnHelper<SupplierInvoiceSummary>();

export function FacturasProveedorPage(): React.JSX.Element {
  const queryClient = useQueryClient();
  const { notify } = useNotifications();
  const { puede } = useAutoridad();

  const [newSupplier, setNewSupplier] = useState("");
  const [newNumber, setNewNumber] = useState("");
  const [newControl, setNewControl] = useState("");
  const [lineInvoice, setLineInvoice] = useState("");
  const [lineProduct, setLineProduct] = useState("");
  const [lineQty, setLineQty] = useState("");
  const [linePrice, setLinePrice] = useState("");

  const query = useQuery({
    queryKey: ["compras", "facturas"],
    queryFn: () => apiFetch<PagedResult<SupplierInvoiceSummary>>("/purchasing/supplier-invoices"),
    retry: false,
  });

  const refresh = (): void => {
    void queryClient.invalidateQueries({ queryKey: ["compras", "facturas"] });
  };

  const createInvoice = async (): Promise<void> => {
    try {
      await apiFetch("/purchasing/supplier-invoices", {
        method: "POST",
        body: { supplier_id: newSupplier, invoice_number: newNumber, control_number: newControl || null, issue_date: null, currency: "VED" },
      });
      notify({ type: "success", title: "Factura creada", description: newNumber });
      setNewSupplier("");
      setNewNumber("");
      setNewControl("");
      refresh();
    } catch (err) {
      const message = err instanceof Error ? err.message : "No fue posible crear la factura";
      notify({ type: "error", title: "No fue posible crear la factura", description: message });
    }
  };

  const addLine = async (): Promise<void> => {
    if (!lineInvoice || !lineProduct) return;
    try {
      await apiFetch(`/purchasing/supplier-invoices/${lineInvoice}/lines`, {
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
    await apiFetch(`/purchasing/supplier-invoices/${id}/transition`, { method: "POST", body: { target } });
    refresh();
    notify({ type: "success", title: "Factura actualizada", description: `Estado → ${target}` });
  };

  const columns = [
    columnHelper.accessor("invoice_number", { header: "Factura" }),
    columnHelper.accessor("control_number", { header: "Control" }),
    columnHelper.accessor("supplier_id", { header: "Proveedor" }),
    columnHelper.accessor("total", { header: "Total" }),
    columnHelper.accessor("status", { header: "Estado" }),
    columnHelper.display({
      id: "actions",
      header: "Acciones",
      cell: ({ row }) => {
        const a = row.original.allowed_actions;
        const mayTransition = puede("POST", `/purchasing/supplier-invoices/${row.original.id}/transition`);
        const transitions: Array<[string, string]> = [
          ["validate", "VALIDATED"],
          ["match", "MATCHED"],
          ["approve", "APPROVED"],
          ["post", "POSTED"],
        ];
        return (
          <div className="flex justify-end gap-1">
            {transitions
              .filter(([key]) => a[key] && mayTransition)
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
        title="Facturas del proveedor"
        description="Creación, líneas y validación de duplicidad y conciliación previa a postear."
        crumbs={[{ label: "Compras" }, { label: "Facturas" }]}
      />

      <Autorizado operacion={["POST", "/purchasing/supplier-invoices"]}>
        <section className="mb-4 rounded-lg border border-border-default bg-surface-0 p-4">
          <h2 className="mb-2 text-base font-semibold text-text-900">Nueva factura</h2>
          <form className="flex flex-wrap items-end gap-3" onSubmit={(e) => e.preventDefault()}>
            <FormField label="Proveedor" required>
              <SelectorDeTercero value={newSupplier} onChange={setNewSupplier} role="PROVEEDOR" soloActivos />
            </FormField>
            <FormField label="N.º de factura" required>
              <TextInput value={newNumber} onChange={(e) => setNewNumber(e.target.value)} placeholder="Ej. F-0001" required />
            </FormField>
            <FormField label="N.º de control">
              <TextInput value={newControl} onChange={(e) => setNewControl(e.target.value)} placeholder="Opcional" />
            </FormField>
            <AsyncButton type="submit" variant="primary" onClick={createInvoice}>Crear</AsyncButton>
          </form>
        </section>
      </Autorizado>

      <Autorizado operacion={["POST", "/purchasing/supplier-invoices/_/lines"]}>
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
              <SelectorDeArticulo value={lineProduct} onChange={setLineProduct} />
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
        emptyDescription="Aún no hay facturas de proveedor registradas."
      />
    </PageContent>
  );
}
