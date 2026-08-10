/** Conteos — planes, líneas y diferencias (FR-003-070/071, WF-05). */
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { createColumnHelper } from "@tanstack/react-table";
import { useState } from "react";

import { apiFetch } from "@/api/client";
import type { CatalogItemSummary, PagedResult, StockCount } from "@/api/types";
import { useCompany } from "@/app/contexts/CompanyContext";
import { useNotifications } from "@/app/contexts/NotificationContext";
import { AsyncButton } from "@/components/AsyncButton";
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

const columnHelper = createColumnHelper<StockCount>();

export function ConteosPage(): React.JSX.Element {
  const { activeCompany } = useCompany();
  const queryClient = useQueryClient();
  const { notify } = useNotifications();

  const [newCode, setNewCode] = useState("");
  const [newWarehouse, setNewWarehouse] = useState("");
  const [newPolicy, setNewPolicy] = useState("PER_PRODUCT");
  const [lineCount, setLineCount] = useState("");
  const [lineProduct, setLineProduct] = useState("");
  const [lineExpected, setLineExpected] = useState("");
  const [lineCounted, setLineCounted] = useState("");

  const companyId = activeCompany?.id ?? null;

  const query = useQuery({
    queryKey: ["inventario", "conteos"],
    queryFn: () => apiFetch<PagedResult<StockCount>>("/inventory/counts"),
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

  const refresh = (): void => {
    void queryClient.invalidateQueries({ queryKey: ["inventario", "conteos"] });
  };

  const createCount = async (): Promise<void> => {
    try {
      await apiFetch("/inventory/counts", {
        method: "POST",
        body: { code: newCode, warehouse_id: newWarehouse, plan_ref: null, scope: [], freeze_policy: newPolicy },
      });
      notify({ type: "success", title: "Conteo creado", description: newCode });
      setNewCode(""); setNewWarehouse("");
      refresh();
    } catch (err) {
      const message = err instanceof Error ? err.message : "No fue posible crear el conteo";
      notify({ type: "error", title: "No fue posible crear el conteo", description: message });
    }
  };

  const addLine = async (): Promise<void> => {
    if (!lineCount || !lineProduct) return;
    try {
      await apiFetch(`/inventory/counts/${lineCount}/lines`, {
        method: "POST",
        body: { product_id: lineProduct, expected_qty: Number(lineExpected) || 0, counted_qty: lineCounted ? Number(lineCounted) : null, location_id: null, lot_id: null },
      });
      notify({ type: "success", title: "Línea agregada", description: `Conteo ${lineCount}` });
      setLineProduct(""); setLineExpected(""); setLineCounted("");
      refresh();
    } catch (err) {
      const message = err instanceof Error ? err.message : "No fue posible agregar la línea";
      notify({ type: "error", title: "No fue posible agregar la línea", description: message });
    }
  };

  const runTransition = async (id: string, target: string): Promise<void> => {
    await apiFetch(`/inventory/counts/${id}/transition`, { method: "POST", body: { target } });
    await queryClient.invalidateQueries({ queryKey: ["inventario", "conteos"] });
    notify({ type: "success", title: "Conteo actualizado", description: `Estado → ${target}` });
  };

  const columns = [
    columnHelper.accessor("code", { header: "Código" }),
    columnHelper.accessor("warehouse_id", { header: "Almacén" }),
    columnHelper.accessor("freeze_policy", { header: "Congelamiento" }),
    columnHelper.accessor("status", { header: "Estado" }),
    columnHelper.display({
      id: "actions",
      header: "Acciones",
      cell: ({ row }) => {
        const a = row.original.allowed_actions;
        const transitions: Array<[string, string]> = [
          ["freeze", "FROZEN"],
          ["submit", "SUBMITTED"],
          ["approve", "APPROVED"],
          ["close", "CLOSED"],
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
        title="Conteos"
        description="Planes de conteo: congelamiento, diferencias y aprobación."
        crumbs={[{ label: "Inventario" }, { label: "Conteos" }]}
      />
      <section className="mb-4 rounded-lg border border-border-default bg-surface-0 p-4">
        <h2 className="mb-2 text-base font-semibold text-text-900">Nuevo conteo</h2>
        <form className="flex flex-wrap items-end gap-3" onSubmit={(e) => e.preventDefault()}>
          <FormField label="Código" required>
            <TextInput value={newCode} onChange={(e) => setNewCode(e.target.value)} placeholder="CT-0001" required />
          </FormField>
          <FormField label="Almacén" required>
            <select value={newWarehouse} onChange={(e) => setNewWarehouse(e.target.value)} className="h-10 w-56 rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900">
              <option value="">Seleccionar…</option>
              {(warehouses.data?.items ?? []).map((w) => (
                <option key={w.id} value={w.id}>{w.code} · {w.name}</option>
              ))}
            </select>
          </FormField>
          <FormField label="Congelamiento">
            <select value={newPolicy} onChange={(e) => setNewPolicy(e.target.value)} className="h-10 w-44 rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900">
              <option value="PER_PRODUCT">Por producto</option>
              <option value="FULL">Total</option>
              <option value="NONE">Ninguno</option>
            </select>
          </FormField>
          <AsyncButton type="submit" variant="primary" onClick={createCount}>Crear</AsyncButton>
        </form>
      </section>

      <section className="mb-4 rounded-lg border border-border-default bg-surface-0 p-4">
        <h2 className="mb-2 text-base font-semibold text-text-900">Agregar línea</h2>
        <form className="flex flex-wrap items-end gap-3" onSubmit={(e) => e.preventDefault()}>
          <FormField label="Conteo" required>
            <select value={lineCount} onChange={(e) => setLineCount(e.target.value)} className="h-10 w-56 rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900">
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
          <FormField label="Esperado" required>
            <TextInput type="number" value={lineExpected} onChange={(e) => setLineExpected(e.target.value)} placeholder="0" required />
          </FormField>
          <FormField label="Contado">
            <TextInput type="number" value={lineCounted} onChange={(e) => setLineCounted(e.target.value)} placeholder="0" />
          </FormField>
          <AsyncButton type="submit" variant="secondary" onClick={addLine}>Agregar</AsyncButton>
        </form>
      </section>

      <DataTable
        columns={columns}
        data={query.data?.items ?? []}
        loading={query.isLoading}
        error={query.isError ? "No fue posible cargar los conteos." : null}
        getRowId={(row) => row.id}
        emptyTitle="Sin conteos"
        emptyDescription="Aún no hay planes de conteo registrados."
      />
    </PageContent>
  );
}
