/** Movimientos — registro manual y reverso de movimientos (FR-003-020/021, WF-03). */
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { createColumnHelper } from "@tanstack/react-table";
import { useState } from "react";

import { apiFetch } from "@/api/client";
import type { CatalogItemSummary, InventoryMovement, MovementType, PagedResult } from "@/api/types";
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

const columnHelper = createColumnHelper<InventoryMovement>();

export function MovimientosPage(): React.JSX.Element {
  const { activeCompany } = useCompany();
  const queryClient = useQueryClient();
  const { notify } = useNotifications();

  const [wh, setWh] = useState("");
  const [product, setProduct] = useState("");
  const [mtype, setMtype] = useState("");
  const [qty, setQty] = useState("");
  const [cost, setCost] = useState("");
  const [docRef, setDocRef] = useState("");
  const [revId, setRevId] = useState("");
  const [revReason, setRevReason] = useState("");

  const companyId = activeCompany?.id ?? null;

  const query = useQuery({
    queryKey: ["inventario", "movimientos"],
    queryFn: () => apiFetch<PagedResult<InventoryMovement>>("/inventory/movements"),
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
  const movementTypes = useQuery({
    queryKey: ["inventario", "movement-types"],
    queryFn: () => apiFetch<PagedResult<MovementType>>("/inventory/movement-types"),
    retry: false,
  });

  const refresh = (): void => {
    void queryClient.invalidateQueries({ queryKey: ["inventario", "movimientos"] });
  };

  const createMovement = async (): Promise<void> => {
    try {
      await apiFetch("/inventory/movements", {
        method: "POST",
        body: {
          warehouse_id: wh, product_id: product, movement_type_id: mtype, quantity: Number(qty) || 0,
          unit_cost: cost ? Number(cost) : null, currency: "VED", fiscal_rate: null,
          document_ref: docRef || null, location_id: null,
        },
      });
      notify({ type: "success", title: "Movimiento registrado", description: `${product} · ${qty}` });
      setWh(""); setProduct(""); setMtype(""); setQty(""); setCost(""); setDocRef("");
      refresh();
    } catch (err) {
      const message = err instanceof Error ? err.message : "No fue posible registrar el movimiento";
      notify({ type: "error", title: "No fue posible registrar el movimiento", description: message });
    }
  };

  const reverseMovement = async (): Promise<void> => {
    if (!revId) return;
    try {
      await apiFetch("/inventory/movements/reverse", {
        method: "POST",
        body: { movement_id: revId, reason: revReason || null },
      });
      notify({ type: "success", title: "Movimiento reversado", description: revId });
      setRevId(""); setRevReason("");
      refresh();
    } catch (err) {
      const message = err instanceof Error ? err.message : "No fue posible reversar el movimiento";
      notify({ type: "error", title: "No fue posible reversar el movimiento", description: message });
    }
  };

  const columns = [
    columnHelper.accessor("occurred_at", {
      header: "Fecha",
      cell: (info) => new Date(info.getValue()).toLocaleString("es-VE"),
    }),
    columnHelper.accessor("product_id", { header: "Producto" }),
    columnHelper.accessor("movement_type_id", { header: "Tipo" }),
    columnHelper.accessor("quantity", {
      header: "Cantidad",
      cell: (info) => (info.getValue() > 0 ? `+${info.getValue()}` : `${info.getValue()}`),
    }),
    columnHelper.accessor("unit_cost", { header: "Costo unit." }),
    columnHelper.accessor("document_ref", { header: "Documento" }),
    columnHelper.accessor("status", { header: "Estado" }),
  ];

  return (
    <PageContent maxWidth="full">
      <PageHeader
        title="Movimientos"
        description="Registro manual de movimientos y reversos (el kardex es inmutable)."
        crumbs={[{ label: "Inventario" }, { label: "Movimientos" }]}
      />
      <section className="mb-4 rounded-lg border border-border-default bg-surface-0 p-4">
        <h2 className="mb-2 text-base font-semibold text-text-900">Registrar movimiento</h2>
        <form className="flex flex-wrap items-end gap-3" onSubmit={(e) => e.preventDefault()}>
          <FormField label="Almacén" required>
            <select value={wh} onChange={(e) => setWh(e.target.value)} className="h-10 w-52 rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900">
              <option value="">Seleccionar…</option>
              {(warehouses.data?.items ?? []).map((w) => (
                <option key={w.id} value={w.id}>{w.code} · {w.name}</option>
              ))}
            </select>
          </FormField>
          <FormField label="Producto" required>
            <select value={product} onChange={(e) => setProduct(e.target.value)} className="h-10 w-52 rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900">
              <option value="">Seleccionar…</option>
              {(products.data?.items ?? []).map((p) => (
                <option key={p.id} value={p.id}>{p.code} · {p.name}</option>
              ))}
            </select>
          </FormField>
          <FormField label="Tipo" required>
            <select value={mtype} onChange={(e) => setMtype(e.target.value)} className="h-10 w-52 rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900">
              <option value="">Seleccionar…</option>
              {(movementTypes.data?.items ?? []).map((t) => (
                <option key={t.id} value={t.id}>{t.code} · {t.name}</option>
              ))}
            </select>
          </FormField>
          <FormField label="Cantidad (+/−)" required>
            <TextInput type="number" value={qty} onChange={(e) => setQty(e.target.value)} placeholder="0" required />
          </FormField>
          <FormField label="Costo unit.">
            <TextInput type="number" value={cost} onChange={(e) => setCost(e.target.value)} placeholder="0,00" />
          </FormField>
          <FormField label="Documento">
            <TextInput value={docRef} onChange={(e) => setDocRef(e.target.value)} placeholder="REF-0001" />
          </FormField>
          <AsyncButton type="submit" variant="primary" onClick={createMovement}>Registrar</AsyncButton>
        </form>
      </section>

      <section className="mb-4 rounded-lg border border-border-default bg-surface-0 p-4">
        <h2 className="mb-2 text-base font-semibold text-text-900">Reversar movimiento</h2>
        <form className="flex flex-wrap items-end gap-3" onSubmit={(e) => e.preventDefault()}>
          <FormField label="Movimiento" required>
            <select value={revId} onChange={(e) => setRevId(e.target.value)} className="h-10 w-72 rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900">
              <option value="">Seleccionar…</option>
              {(query.data?.items ?? []).map((m) => (
                <option key={m.id} value={m.id}>{m.document_ref ?? m.id} · {m.quantity} · {m.status}</option>
              ))}
            </select>
          </FormField>
          <FormField label="Motivo">
            <TextInput value={revReason} onChange={(e) => setRevReason(e.target.value)} placeholder="Registro erróneo" />
          </FormField>
          <AsyncButton type="submit" variant="secondary" onClick={reverseMovement}>Reversar</AsyncButton>
        </form>
      </section>

      <DataTable
        columns={columns}
        data={query.data?.items ?? []}
        loading={query.isLoading}
        error={query.isError ? "No fue posible cargar los movimientos." : null}
        getRowId={(row) => row.id}
        emptyTitle="Sin movimientos"
        emptyDescription="No hay movimientos registrados."
      />
    </PageContent>
  );
}
