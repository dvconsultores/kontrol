/** Ajustes — motivo/evidencia/aprobación (FR-003-072/073, WF-02). */
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { createColumnHelper } from "@tanstack/react-table";
import { useState } from "react";

import { apiFetch } from "@/api/client";
import type { CatalogItemSummary, InventoryAdjustment, PagedResult } from "@/api/types";
import { useAutoridad } from "@/app/autoridad/AutoridadContext";
import { useCompany } from "@/app/contexts/CompanyContext";
import { useNotifications } from "@/app/contexts/NotificationContext";
import { AsyncButton } from "@/components/AsyncButton";
import { Autorizado } from "@/components/Autorizado";
import { DataTable } from "@/components/DataTable";
import { FormField } from "@/components/FormField";
import { PageContent } from "@/layout/PageContent";
import { PageHeader } from "@/components/PageHeader";
import { TextInput } from "@/components/TextInput";

interface WarehouseSummary {
  id: string;
  code: string;
  name: string;
}

const columnHelper = createColumnHelper<InventoryAdjustment>();

export function AjustesPage(): React.JSX.Element {
  const { activeCompany } = useCompany();
  const queryClient = useQueryClient();
  const { notify } = useNotifications();
  const { puede } = useAutoridad();

  const [newWarehouse, setNewWarehouse] = useState("");
  const [newProduct, setNewProduct] = useState("");
  const [newQty, setNewQty] = useState("");
  const [newReason, setNewReason] = useState("");
  const [newEvidence, setNewEvidence] = useState("");
  const [newCost, setNewCost] = useState("");

  const companyId = activeCompany?.id ?? null;

  const query = useQuery({
    queryKey: ["inventario", "ajustes"],
    queryFn: () => apiFetch<PagedResult<InventoryAdjustment>>("/inventory/adjustments"),
    retry: false,
  });
  const warehouses = useQuery({
    queryKey: ["organizacion", "almacenes", companyId],
    queryFn: () => apiFetch<{ items: WarehouseSummary[] }>(`/organization/warehouses?company_id=${companyId}`),
    enabled: Boolean(companyId),
    retry: false,
  });
  const products = useQuery({
    queryKey: ["maestros", "productos"],
    queryFn: () => apiFetch<PagedResult<CatalogItemSummary>>(`/maestros/catalogos/items?status=ACTIVE`),
    retry: false,
  });

  const createAdjustment = async (): Promise<void> => {
    try {
      await apiFetch("/inventory/adjustments", {
        method: "POST",
        body: {
          warehouse_id: newWarehouse, product_id: newProduct, quantity: Number(newQty) || 0,
          reason: newReason, evidence_ref: newEvidence || null,
          unit_cost: newCost ? Number(newCost) : null, currency: "VED",
        },
      });
      notify({ type: "success", title: "Ajuste creado", description: newReason });
      setNewWarehouse(""); setNewProduct(""); setNewQty(""); setNewReason(""); setNewEvidence(""); setNewCost("");
      void queryClient.invalidateQueries({ queryKey: ["inventario", "ajustes"] });
    } catch (err) {
      const message = err instanceof Error ? err.message : "No fue posible crear el ajuste";
      notify({ type: "error", title: "No fue posible crear el ajuste", description: message });
    }
  };

  const runTransition = async (id: string, target: string): Promise<void> => {
    await apiFetch(`/inventory/adjustments/${id}/transition`, { method: "POST", body: { target } });
    await queryClient.invalidateQueries({ queryKey: ["inventario", "ajustes"] });
    notify({ type: "success", title: "Ajuste actualizado", description: `Estado → ${target}` });
  };

  const columns = [
    columnHelper.accessor("product_id", { header: "Producto" }),
    columnHelper.accessor("quantity", { header: "Cantidad" }),
    columnHelper.accessor("reason", { header: "Motivo" }),
    columnHelper.accessor("unit_cost", { header: "Costo unit." }),
    columnHelper.accessor("status", { header: "Estado" }),
    columnHelper.display({
      id: "actions",
      header: "Acciones",
      cell: ({ row }) => {
        const a = row.original.allowed_actions;
        if (!puede("POST", `/inventory/adjustments/${row.original.id}/transition`)) {
          return null;
        }
        const transitions: Array<[string, string]> = [
          ["submit", "SUBMITTED"],
          ["approve", "APPROVED"],
          ["reject", "REJECTED"],
          ["apply", "APPLIED"],
        ];
        return (
          <div className="flex justify-end gap-1">
            {transitions
              .filter(([key]) => a[key])
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
        title="Ajustes de inventario"
        description="Ajustes con motivo, evidencia y aprobación. Nunca editan el saldo: generan movimientos."
        crumbs={[{ label: "Inventario" }, { label: "Ajustes" }]}
      />
      <Autorizado operacion={["POST", "/inventory/adjustments"]}>
      <section className="mb-4 rounded-lg border border-border-default bg-surface-0 p-4">
        <h2 className="mb-2 text-base font-semibold text-text-900">Nuevo ajuste</h2>
        <form className="flex flex-wrap items-end gap-3" onSubmit={(e) => e.preventDefault()}>
          <FormField label="Almacén" required>
            <select value={newWarehouse} onChange={(e) => setNewWarehouse(e.target.value)} className="h-10 w-56 rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900">
              <option value="">Seleccionar…</option>
              {(warehouses.data?.items ?? []).map((w) => (
                <option key={w.id} value={w.id}>{w.code} · {w.name}</option>
              ))}
            </select>
          </FormField>
          <FormField label="Producto" required>
            <select value={newProduct} onChange={(e) => setNewProduct(e.target.value)} className="h-10 w-56 rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900">
              <option value="">Seleccionar…</option>
              {(products.data?.items ?? []).map((p) => (
                <option key={p.id} value={p.id}>{p.code} · {p.name}</option>
              ))}
            </select>
          </FormField>
          <FormField label="Cantidad (+/−)" required>
            <TextInput type="number" value={newQty} onChange={(e) => setNewQty(e.target.value)} placeholder="0" required />
          </FormField>
          <FormField label="Motivo" required>
            <TextInput value={newReason} onChange={(e) => setNewReason(e.target.value)} placeholder="Daño detectado en conteo" required />
          </FormField>
          <FormField label="Evidencia">
            <TextInput value={newEvidence} onChange={(e) => setNewEvidence(e.target.value)} placeholder="REF-0001" />
          </FormField>
          <FormField label="Costo unit.">
            <TextInput type="number" value={newCost} onChange={(e) => setNewCost(e.target.value)} placeholder="0,00" />
          </FormField>
          <AsyncButton type="submit" variant="primary" onClick={createAdjustment}>Crear</AsyncButton>
        </form>
      </section>
      </Autorizado>

      <DataTable
        columns={columns}
        data={query.data?.items ?? []}
        loading={query.isLoading}
        error={query.isError ? "No fue posible cargar los ajustes." : null}
        getRowId={(row) => row.id}
        emptyTitle="Sin ajustes"
        emptyDescription="Aún no hay ajustes registrados."
      />
    </PageContent>
  );
}
