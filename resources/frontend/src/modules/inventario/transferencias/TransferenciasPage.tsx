/** Transferencias — creación, líneas y transiciones de estado (FR-003-060/061, WF-04). */
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { createColumnHelper } from "@tanstack/react-table";
import { useState } from "react";

import { apiFetch } from "@/api/client";
import type { CatalogItemSummary, PagedResult, TransferSummary } from "@/api/types";
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

const columnHelper = createColumnHelper<TransferSummary>();

export function TransferenciasPage(): React.JSX.Element {
  const { activeCompany } = useCompany();
  const queryClient = useQueryClient();
  const { notify } = useNotifications();
  const { puede } = useAutoridad();

  const [newCode, setNewCode] = useState("");
  const [newOrigin, setNewOrigin] = useState("");
  const [newDestination, setNewDestination] = useState("");
  const [lineProduct, setLineProduct] = useState("");
  const [lineQty, setLineQty] = useState("");

  const companyId = activeCompany?.id ?? null;

  const query = useQuery({
    queryKey: ["inventario", "transferencias"],
    queryFn: () => apiFetch<PagedResult<TransferSummary>>("/inventory/transfers"),
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

  const createTransfer = async (): Promise<void> => {
    if (!lineProduct) {
      notify({ type: "error", title: "Falta el producto", description: "Agregue al menos una línea de producto." });
      return;
    }
    try {
      await apiFetch("/inventory/transfers", {
        method: "POST",
        body: {
          code: newCode, origin_warehouse_id: newOrigin, destination_warehouse_id: newDestination,
          request_ref: null,
          lines: [{ product_id: lineProduct, quantity_sent: Number(lineQty) || 0, lot_id: null, serial_id: null }],
        },
      });
      notify({ type: "success", title: "Transferencia creada", description: newCode });
      setNewCode(""); setNewOrigin(""); setNewDestination(""); setLineProduct(""); setLineQty("");
      void queryClient.invalidateQueries({ queryKey: ["inventario", "transferencias"] });
    } catch (err) {
      const message = err instanceof Error ? err.message : "No fue posible crear la transferencia";
      notify({ type: "error", title: "No fue posible crear la transferencia", description: message });
    }
  };

  const runTransition = async (id: string, target: string): Promise<void> => {
    await apiFetch(`/inventory/transfers/${id}/transition`, { method: "POST", body: { target } });
    await queryClient.invalidateQueries({ queryKey: ["inventario", "transferencias"] });
    notify({ type: "success", title: "Transferencia actualizada", description: `Estado → ${target}` });
  };

  const columns = [
    columnHelper.accessor("code", { header: "Código" }),
    columnHelper.accessor("origin_warehouse_id", { header: "Origen" }),
    columnHelper.accessor("destination_warehouse_id", { header: "Destino" }),
    columnHelper.accessor("status", { header: "Estado" }),
    columnHelper.display({
      id: "actions",
      header: "Acciones",
      cell: ({ row }) => {
        const a = row.original.allowed_actions;
        const transitions: Array<[string, string]> = [
          ["submit", "SUBMITTED"],
          ["approve", "APPROVED"],
          ["confirm_ship", "IN_TRANSIT"],
          ["confirm_receipt", "RECEIVED"],
          ["close", "CLOSED"],
        ];
        const canTransition = puede("POST", `/inventory/transfers/${row.original.id}/transition`);
        return (
          <div className="flex justify-end gap-1">
            {transitions
              .filter(([key]) => a[key] && canTransition)
              .map(([key, target]) => (
                <AsyncButton key={key} size="sm" variant="secondary" onClick={() => runTransition(row.original.id, target)}>
                  {key.replace("_", " ")}
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
        title="Transferencias"
        description="Movimiento de mercancía entre almacenes con máquina de estados."
        crumbs={[{ label: "Inventario" }, { label: "Transferencias" }]}
      />
      <Autorizado operacion={["POST", "/inventory/transfers"]}>
      <section className="mb-4 rounded-lg border border-border-default bg-surface-0 p-4">
        <h2 className="mb-2 text-base font-semibold text-text-900">Nueva transferencia</h2>
        <form className="flex flex-wrap items-end gap-3" onSubmit={(e) => e.preventDefault()}>
          <FormField label="Código" required>
            <TextInput value={newCode} onChange={(e) => setNewCode(e.target.value)} placeholder="TR-0001" required />
          </FormField>
          <FormField label="Almacén origen" required>
            <select value={newOrigin} onChange={(e) => setNewOrigin(e.target.value)} className="h-10 w-56 rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900">
              <option value="">Seleccionar…</option>
              {(warehouses.data?.items ?? []).map((w) => (
                <option key={w.id} value={w.id}>{w.code} · {w.name}</option>
              ))}
            </select>
          </FormField>
          <FormField label="Almacén destino" required>
            <select value={newDestination} onChange={(e) => setNewDestination(e.target.value)} className="h-10 w-56 rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900">
              <option value="">Seleccionar…</option>
              {(warehouses.data?.items ?? []).map((w) => (
                <option key={w.id} value={w.id}>{w.code} · {w.name}</option>
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
          <AsyncButton type="submit" variant="primary" onClick={createTransfer}>Crear</AsyncButton>
        </form>
      </section>
      </Autorizado>

      <DataTable
        columns={columns}
        data={query.data?.items ?? []}
        loading={query.isLoading}
        error={query.isError ? "No fue posible cargar las transferencias." : null}
        getRowId={(row) => row.id}
        emptyTitle="Sin transferencias"
        emptyDescription="Aún no hay transferencias registradas."
      />
    </PageContent>
  );
}
