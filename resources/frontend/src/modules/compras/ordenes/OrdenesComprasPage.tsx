/** Órdenes de compra — creación, líneas y transiciones (FR-004-020/021, WF-04). */
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { createColumnHelper } from "@tanstack/react-table";
import { useState } from "react";

import { apiFetch } from "@/api/client";
import type { CatalogItemSummary, PagedResult, Party, PurchaseOrderSummary } from "@/api/types";
import { useAutoridad } from "@/app/autoridad/AutoridadContext";
import { useNotifications } from "@/app/contexts/NotificationContext";
import { AsyncButton } from "@/components/AsyncButton";
import { Autorizado } from "@/components/Autorizado";
import { DataTable } from "@/components/DataTable";
import { FormField } from "@/components/FormField";
import { PageContent } from "@/layout/PageContent";
import { PageHeader } from "@/components/PageHeader";
import { TextInput } from "@/components/TextInput";

const columnHelper = createColumnHelper<PurchaseOrderSummary>();

export function OrdenesComprasPage(): React.JSX.Element {
  const queryClient = useQueryClient();
  const { notify } = useNotifications();
  const { puede } = useAutoridad();

  const [newCode, setNewCode] = useState("");
  const [newSupplier, setNewSupplier] = useState("");
  const [lineOrder, setLineOrder] = useState("");
  const [lineProduct, setLineProduct] = useState("");
  const [lineQty, setLineQty] = useState("");
  const [linePrice, setLinePrice] = useState("");

  const query = useQuery({
    queryKey: ["compras", "ordenes"],
    queryFn: () => apiFetch<PagedResult<PurchaseOrderSummary>>("/purchasing/orders"),
    retry: false,
  });
  const suppliers = useQuery({
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
    void queryClient.invalidateQueries({ queryKey: ["compras", "ordenes"] });
  };

  const createOrder = async (): Promise<void> => {
    try {
      await apiFetch("/purchasing/orders", {
        method: "POST",
        body: { code: newCode, supplier_id: newSupplier, terms: null, currency: "VED" },
      });
      notify({ type: "success", title: "Orden creada", description: newCode });
      setNewCode("");
      setNewSupplier("");
      refresh();
    } catch (err) {
      const message = err instanceof Error ? err.message : "No fue posible crear la orden";
      notify({ type: "error", title: "No fue posible crear la orden", description: message });
    }
  };

  const addLine = async (): Promise<void> => {
    if (!lineOrder || !lineProduct) return;
    try {
      await apiFetch(`/purchasing/orders/${lineOrder}/lines`, {
        method: "POST",
        body: { product_id: lineProduct, quantity_ordered: Number(lineQty) || 0, unit_price: Number(linePrice) || 0, discount: 0, needs_inventory: true },
      });
      notify({ type: "success", title: "Línea agregada", description: `Orden ${lineOrder}` });
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
    await apiFetch(`/purchasing/orders/${id}/transition`, { method: "POST", body: { target } });
    refresh();
    notify({ type: "success", title: "Orden actualizada", description: `Estado → ${target}` });
  };

  const columns = [
    columnHelper.accessor("code", { header: "Código" }),
    columnHelper.accessor("supplier_id", { header: "Proveedor" }),
    columnHelper.accessor("currency", { header: "Moneda" }),
    columnHelper.accessor("status", { header: "Estado" }),
    columnHelper.display({
      id: "actions",
      header: "Acciones",
      cell: ({ row }) => {
        const a = row.original.allowed_actions;
        const transitions: Array<[string, string]> = [
          ["submit", "SUBMITTED"],
          ["approve", "APPROVED"],
          ["reject", "REJECTED"],
          ["cancel", "CANCELLED"],
          ["close", "CLOSED"],
        ];
        return (
          <div className="flex justify-end gap-1">
            {transitions
              .filter(([key]) => a[key] && puede("POST", `/purchasing/orders/${row.original.id}/transition`))
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
        title="Órdenes de compra"
        description="Creación, líneas y aprobación con totales por moneda (no sustituyen recepción ni factura)."
        crumbs={[{ label: "Compras" }, { label: "Órdenes" }]}
      />

      <Autorizado operacion={["POST", "/purchasing/orders"]}>
        <section className="mb-4 rounded-lg border border-border-default bg-surface-0 p-4">
          <h2 className="mb-2 text-base font-semibold text-text-900">Nueva orden</h2>
          <form className="flex flex-wrap items-end gap-3" onSubmit={(e) => e.preventDefault()}>
            <FormField label="Código" required>
              <TextInput value={newCode} onChange={(e) => setNewCode(e.target.value)} placeholder="Ej. OC-001" required />
            </FormField>
            <FormField label="Proveedor" required>
              <select value={newSupplier} onChange={(e) => setNewSupplier(e.target.value)} className="h-10 w-56 rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900">
                <option value="">Seleccionar…</option>
                {(suppliers.data?.items ?? []).filter((c) => (c.roles ?? []).includes("PROVEEDOR")).map((c) => (
                  <option key={c.id} value={c.id}>{c.name}</option>
                ))}
              </select>
            </FormField>
            <AsyncButton type="submit" variant="primary" onClick={createOrder}>Crear</AsyncButton>
          </form>
        </section>
      </Autorizado>

      <Autorizado operacion={["POST", "/purchasing/orders/_/lines"]}>
        <section className="mb-4 rounded-lg border border-border-default bg-surface-0 p-4">
          <h2 className="mb-2 text-base font-semibold text-text-900">Agregar línea</h2>
          <form className="flex flex-wrap items-end gap-3" onSubmit={(e) => e.preventDefault()}>
            <FormField label="Orden" required>
              <select value={lineOrder} onChange={(e) => setLineOrder(e.target.value)} className="h-10 w-56 rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900">
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
        error={query.isError ? "No fue posible cargar las órdenes." : null}
        getRowId={(row) => row.id}
        emptyTitle="Sin órdenes"
        emptyDescription="Aún no hay órdenes de compra registradas."
      />
    </PageContent>
  );
}
