/** Lotes — trazabilidad por lote con transiciones (FR-003-040/041, WF-06). */
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { createColumnHelper } from "@tanstack/react-table";
import { useState } from "react";

import { apiFetch } from "@/api/client";
import type { CatalogItemSummary, InventoryLot, PagedResult } from "@/api/types";
import { useNotifications } from "@/app/contexts/NotificationContext";
import { AsyncButton } from "@/components/AsyncButton";
import { DataTable } from "@/components/DataTable";
import { FormField } from "@/components/FormField";
import { PageContent } from "@/layout/PageContent";
import { PageHeader } from "@/components/PageHeader";
import { TextInput } from "@/components/TextInput";

const columnHelper = createColumnHelper<InventoryLot>();

const LOT_TRANSITIONS: Record<string, string[]> = {
  DISPONIBLE: ["RESERVADO", "TRANSITO", "CUARENTENA"],
  RESERVADO: ["DISPONIBLE", "TRANSITO", "VENDIDO"],
  TRANSITO: ["DISPONIBLE", "CUARENTENA", "RECHAZADO"],
  CUARENTENA: ["DISPONIBLE", "RECHAZADO", "DESECHO"],
  VENCIDO: ["DESECHO"],
  RECHAZADO: ["DESECHO"],
};

export function LotesPage(): React.JSX.Element {
  const queryClient = useQueryClient();
  const { notify } = useNotifications();

  const [newProduct, setNewProduct] = useState("");
  const [newNumber, setNewNumber] = useState("");
  const [newExpiry, setNewExpiry] = useState("");
  const [newSupplier, setNewSupplier] = useState("");

  const query = useQuery({
    queryKey: ["inventario", "lotes"],
    queryFn: () => apiFetch<PagedResult<InventoryLot>>("/inventory/lots"),
    retry: false,
  });
  const products = useQuery({
    queryKey: ["maestros", "productos"],
    queryFn: () => apiFetch<PagedResult<CatalogItemSummary>>(`/maestros/catalogos/items?status=ACTIVE`),
    retry: false,
  });

  const refresh = (): void => {
    void queryClient.invalidateQueries({ queryKey: ["inventario", "lotes"] });
  };

  const createLot = async (): Promise<void> => {
    try {
      await apiFetch("/inventory/lots", {
        method: "POST",
        body: {
          product_id: newProduct, lot_number: newNumber,
          manufacture_date: null, expiry_date: newExpiry || null,
          supplier_id: newSupplier || null, receipt_ref: null,
        },
      });
      notify({ type: "success", title: "Lote creado", description: newNumber });
      setNewProduct(""); setNewNumber(""); setNewExpiry(""); setNewSupplier("");
      refresh();
    } catch (err) {
      const message = err instanceof Error ? err.message : "No fue posible crear el lote";
      notify({ type: "error", title: "No fue posible crear el lote", description: message });
    }
  };

  const runTransition = async (id: string, target: string): Promise<void> => {
    await apiFetch(`/inventory/lots/${id}/transition`, { method: "POST", body: { target } });
    notify({ type: "success", title: "Lote actualizado", description: `Estado → ${target}` });
    refresh();
  };

  const columns = [
    columnHelper.accessor("lot_number", { header: "Lote" }),
    columnHelper.accessor("product_id", { header: "Producto" }),
    columnHelper.accessor("expiry_date", { header: "Vence" }),
    columnHelper.accessor("supplier_id", { header: "Proveedor" }),
    columnHelper.accessor("status", { header: "Estado" }),
    columnHelper.display({
      id: "actions",
      header: "Acciones",
      cell: ({ row }) => {
        const targets = LOT_TRANSITIONS[row.original.status] ?? [];
        return (
          <div className="flex justify-end gap-1">
            {targets.map((target) => (
              <AsyncButton key={target} size="sm" variant="secondary" onClick={() => runTransition(row.original.id, target)}>
                {target.toLowerCase()}
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
        title="Lotes"
        description="Trazabilidad por lote: vencimiento, proveedor y transiciones de estado."
        crumbs={[{ label: "Inventario" }, { label: "Lotes" }]}
      />
      <section className="mb-4 rounded-lg border border-border-default bg-surface-0 p-4">
        <h2 className="mb-2 text-base font-semibold text-text-900">Nuevo lote</h2>
        <form className="flex flex-wrap items-end gap-3" onSubmit={(e) => e.preventDefault()}>
          <FormField label="Producto" required>
            <select value={newProduct} onChange={(e) => setNewProduct(e.target.value)} className="h-10 w-56 rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900">
              <option value="">Seleccionar…</option>
              {(products.data?.items ?? []).map((p) => (
                <option key={p.id} value={p.id}>{p.code} · {p.name}</option>
              ))}
            </select>
          </FormField>
          <FormField label="Número de lote" required>
            <TextInput value={newNumber} onChange={(e) => setNewNumber(e.target.value)} placeholder="LOT-0001" required />
          </FormField>
          <FormField label="Vencimiento">
            <TextInput type="date" value={newExpiry} onChange={(e) => setNewExpiry(e.target.value)} />
          </FormField>
          <FormField label="Proveedor">
            <TextInput value={newSupplier} onChange={(e) => setNewSupplier(e.target.value)} placeholder="ID proveedor" />
          </FormField>
          <AsyncButton type="submit" variant="primary" onClick={createLot}>Crear</AsyncButton>
        </form>
      </section>

      <DataTable
        columns={columns}
        data={query.data?.items ?? []}
        loading={query.isLoading}
        error={query.isError ? "No fue posible cargar los lotes." : null}
        getRowId={(row) => row.id}
        emptyTitle="Sin lotes"
        emptyDescription="Aún no hay lotes registrados."
      />
    </PageContent>
  );
}
