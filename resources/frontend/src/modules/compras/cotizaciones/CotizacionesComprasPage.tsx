/** Cotizaciones de compra — solicitud de oferta a proveedor (FR-004-001, WF-02). */
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { createColumnHelper } from "@tanstack/react-table";
import { useState } from "react";

import { apiFetch } from "@/api/client";
import type { PagedResult, Party, SupplierQuoteSummary } from "@/api/types";
import { useNotifications } from "@/app/contexts/NotificationContext";
import { Autorizado } from "@/components/Autorizado";
import { AsyncButton } from "@/components/AsyncButton";
import { DataTable } from "@/components/DataTable";
import { FormField } from "@/components/FormField";
import { PageContent } from "@/layout/PageContent";
import { PageHeader } from "@/components/PageHeader";
import { TextInput } from "@/components/TextInput";
import { SelectorDeArticulo } from "@/modules/maestros/catalogo/SelectorDeArticulo";

const columnHelper = createColumnHelper<SupplierQuoteSummary>();

export function CotizacionesComprasPage(): React.JSX.Element {
  const queryClient = useQueryClient();
  const { notify } = useNotifications();

  const [newCode, setNewCode] = useState("");
  const [newSupplier, setNewSupplier] = useState("");
  const [newValidity, setNewValidity] = useState("");
  const [newTerms, setNewTerms] = useState("");
  const [lineQuote, setLineQuote] = useState("");
  const [lineProduct, setLineProduct] = useState("");
  const [lineQty, setLineQty] = useState("");
  const [linePrice, setLinePrice] = useState("");

  const query = useQuery({
    queryKey: ["compras", "cotizaciones"],
    queryFn: () => apiFetch<{ items: SupplierQuoteSummary[] }>("/purchasing/quotes"),
    retry: false,
  });
  const suppliers = useQuery({
    queryKey: ["maestros", "terceros"],
    queryFn: () => apiFetch<PagedResult<Party>>("/maestros/terceros"),
    retry: false,
  });

  const refresh = async (): Promise<void> => {
    await queryClient.invalidateQueries({ queryKey: ["compras", "cotizaciones"] });
  };

  const createQuote = async (): Promise<void> => {
    try {
      await apiFetch("/purchasing/quotes", {
        method: "POST",
        body: {
          code: newCode, supplier_id: newSupplier,
          validity_until: newValidity || null, currency: "VED", terms: newTerms || null,
        },
      });
      notify({ type: "success", title: "Cotización creada", description: newCode });
      setNewCode(""); setNewSupplier(""); setNewValidity(""); setNewTerms("");
      void refresh();
    } catch (err) {
      const message = err instanceof Error ? err.message : "No fue posible crear la cotización";
      notify({ type: "error", title: "No fue posible crear la cotización", description: message });
    }
  };

  const addLine = async (): Promise<void> => {
    if (!lineQuote || !lineProduct) return;
    try {
      await apiFetch(`/purchasing/quotes/${lineQuote}/lines`, {
        method: "POST",
        body: {
          product_id: lineProduct, quantity: Number(lineQty) || 0, unit_price: Number(linePrice) || 0,
          discount: 0, delivery_days: null, tax_ref: null,
        },
      });
      notify({ type: "success", title: "Línea agregada", description: `Cotización ${lineQuote}` });
      setLineProduct(""); setLineQty(""); setLinePrice("");
      void refresh();
    } catch (err) {
      const message = err instanceof Error ? err.message : "No fue posible agregar la línea";
      notify({ type: "error", title: "No fue posible agregar la línea", description: message });
    }
  };

  const columns = [
    columnHelper.accessor("code", { header: "Código" }),
    columnHelper.accessor("supplier_id", { header: "Proveedor" }),
    columnHelper.accessor("currency", { header: "Moneda" }),
    columnHelper.accessor("validity_until", { header: "Válida hasta" }),
    columnHelper.accessor("status", { header: "Estado" }),
  ];

  return (
    <PageContent maxWidth="full">
      <PageHeader
        title="Cotizaciones de compra"
        description="Solicitud de oferta a proveedores y carga de líneas de producto."
        crumbs={[{ label: "Compras" }, { label: "Cotizaciones" }]}
      />
      <Autorizado operacion={["POST", "/purchasing/quotes"]}>
        <section className="mb-4 rounded-lg border border-border-default bg-surface-0 p-4">
          <h2 className="mb-2 text-base font-semibold text-text-900">Nueva cotización</h2>
          <form className="flex flex-wrap items-end gap-3" onSubmit={(e) => e.preventDefault()}>
            <FormField label="Código" required>
              <TextInput value={newCode} onChange={(e) => setNewCode(e.target.value)} placeholder="COT-0001" required />
            </FormField>
            <FormField label="Proveedor" required>
              <select value={newSupplier} onChange={(e) => setNewSupplier(e.target.value)} className="h-10 w-56 rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900">
                <option value="">Seleccionar…</option>
                {(suppliers.data?.items ?? []).map((p) => (
                  <option key={p.id} value={p.id}>{p.code} · {p.name}</option>
                ))}
              </select>
            </FormField>
            <FormField label="Válida hasta">
              <TextInput type="date" value={newValidity} onChange={(e) => setNewValidity(e.target.value)} />
            </FormField>
            <FormField label="Términos">
              <TextInput value={newTerms} onChange={(e) => setNewTerms(e.target.value)} placeholder="Crédito 30 días" />
            </FormField>
            <AsyncButton type="submit" variant="primary" onClick={createQuote}>Crear</AsyncButton>
          </form>
        </section>
      </Autorizado>

      <section className="mb-4 rounded-lg border border-border-default bg-surface-0 p-4">
        <h2 className="mb-2 text-base font-semibold text-text-900">Agregar línea</h2>
        <form className="flex flex-wrap items-end gap-3" onSubmit={(e) => e.preventDefault()}>
          <FormField label="Cotización" required>
            <select value={lineQuote} onChange={(e) => setLineQuote(e.target.value)} className="h-10 w-40 rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900">
              <option value="">Seleccionar…</option>
              {(query.data?.items ?? []).map((q) => (
                <option key={q.id} value={q.id}>{q.code}</option>
              ))}
            </select>
          </FormField>
          <Autorizado operacion={["POST", "/purchasing/quotes/_/lines"]}>
            <FormField label="Producto" required>
              <SelectorDeArticulo value={lineProduct} onChange={setLineProduct} />
            </FormField>
            <FormField label="Cantidad" required>
              <TextInput type="number" min="0" value={lineQty} onChange={(e) => setLineQty(e.target.value)} required />
            </FormField>
            <FormField label="Precio unitario" required>
              <TextInput type="number" min="0" value={linePrice} onChange={(e) => setLinePrice(e.target.value)} required />
            </FormField>
            <AsyncButton type="submit" variant="secondary" onClick={addLine}>Agregar línea</AsyncButton>
          </Autorizado>
        </form>
      </section>

      <DataTable
        columns={columns}
        data={query.data?.items ?? []}
        loading={query.isLoading}
        error={query.isError ? "No fue posible cargar las cotizaciones." : null}
        getRowId={(row) => row.id}
        emptyTitle="Sin cotizaciones"
        emptyDescription="Aún no hay cotizaciones de compra registradas."
      />
    </PageContent>
  );
}
