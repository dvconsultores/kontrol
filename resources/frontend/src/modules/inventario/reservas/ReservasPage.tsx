/** Reservas — reservas de existencias para documentos (FR-003-020/021, WF-03). */
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { createColumnHelper } from "@tanstack/react-table";
import { useState } from "react";

import { apiFetch } from "@/api/client";
import type { CatalogItemSummary, PagedResult, Reservation } from "@/api/types";
import { useAutoridad } from "@/app/autoridad/AutoridadContext";
import { useCompany } from "@/app/contexts/CompanyContext";
import { useNotifications } from "@/app/contexts/NotificationContext";
import { AsyncButton } from "@/components/AsyncButton";
import { Autorizado } from "@/components/Autorizado";
import { ConfirmationDialog } from "@/components/ConfirmationDialog";
import { DataTable } from "@/components/DataTable";
import { FormField } from "@/components/FormField";
import { PageContent } from "@/layout/PageContent";
import { PageHeader } from "@/components/PageHeader";
import { TextInput } from "@/components/TextInput";
import { fechaDeNegocioDeInstante } from "@/lib/fecha-de-negocio";

interface WarehouseSummary {
  id: string;
  code: string;
  name: string;
}

const columnHelper = createColumnHelper<Reservation>();

export function ReservasPage(): React.JSX.Element {
  const { activeCompany } = useCompany();
  const queryClient = useQueryClient();
  const { notify } = useNotifications();
  const { puede } = useAutoridad();

  const [newProduct, setNewProduct] = useState("");
  const [newWarehouse, setNewWarehouse] = useState("");
  const [newQty, setNewQty] = useState("");
  const [newDoc, setNewDoc] = useState("");
  const [newExpiry, setNewExpiry] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [aLiberar, setALiberar] = useState<string | null>(null);
  const [motivo, setMotivo] = useState("");

  const companyId = activeCompany?.id ?? null;

  const reservationsUrl = statusFilter ? `/inventory/reservations?status=${statusFilter}` : "/inventory/reservations";

  const query = useQuery({
    queryKey: ["inventario", "reservas", statusFilter],
    queryFn: () => apiFetch<{ items: Reservation[] }>(reservationsUrl),
    retry: false,
  });
  const products = useQuery({
    queryKey: ["maestros", "productos"],
    queryFn: () => apiFetch<PagedResult<CatalogItemSummary>>(`/maestros/catalogos/items?status=ACTIVE`),
    retry: false,
  });
  const warehouses = useQuery({
    queryKey: ["organizacion", "almacenes", companyId],
    queryFn: () => apiFetch<{ items: WarehouseSummary[] }>(`/organization/warehouses?company_id=${companyId}`),
    enabled: Boolean(companyId),
    retry: false,
  });

  const refresh = (): void => {
    void queryClient.invalidateQueries({ queryKey: ["inventario", "reservas"] });
  };

  const createReservation = async (): Promise<void> => {
    try {
      await apiFetch("/inventory/reservations", {
        method: "POST",
        body: {
          source_document: newDoc || null, product_id: newProduct, warehouse_id: newWarehouse,
          quantity: Number(newQty) || 0, lot_id: null, serial_id: null,
          expires_in_days: newExpiry ? Number(newExpiry) : null,
        },
      });
      notify({ type: "success", title: "Reserva creada", description: `${newQty} uds. reservadas` });
      setNewProduct(""); setNewWarehouse(""); setNewQty(""); setNewDoc(""); setNewExpiry("");
      refresh();
    } catch (err) {
      const message = err instanceof Error ? err.message : "No fue posible crear la reserva";
      notify({ type: "error", title: "No fue posible crear la reserva", description: message });
    }
  };

  const release = async (id: string, reason: string): Promise<void> => {
    try {
      await apiFetch(`/inventory/reservations/${id}/release`, { method: "POST", body: { reason } });
      notify({ type: "success", title: "Reserva liberada", description: reason });
      refresh();
    } catch (err) {
      const message = err instanceof Error ? err.message : "No fue posible liberar la reserva";
      notify({ type: "error", title: "No fue posible liberar la reserva", description: message });
    }
  };

  const expireAll = async (): Promise<void> => {
    try {
      const res = await apiFetch<{ expired: number }>("/inventory/reservations/expire", { method: "POST" });
      notify({ type: "success", title: "Vencidas", description: `${res.expired} reservas vencidas liberadas.` });
      refresh();
    } catch (err) {
      const message = err instanceof Error ? err.message : "No fue posible expirar las reservas";
      notify({ type: "error", title: "No fue posible expirar las reservas", description: message });
    }
  };

  const columns = [
    columnHelper.accessor("source_document", { header: "Documento origen", cell: ({ getValue }) => getValue() ?? "—" }),
    columnHelper.accessor("trigger", {
      header: "Origen",
      cell: ({ getValue, row }) =>
        row.original.source_type === "SALES_ORDER" ? `Pedido · ${getValue() ?? ""}` : getValue() ?? "MANUAL",
    }),
    columnHelper.accessor("product_id", { header: "Producto" }),
    columnHelper.accessor("warehouse_id", { header: "Almacén" }),
    columnHelper.accessor("quantity", { header: "Cantidad" }),
    columnHelper.accessor("base_quantity", { header: "Base", cell: ({ getValue }) => getValue() ?? "—" }),
    columnHelper.accessor("status", {
      header: "Estado",
      cell: ({ getValue, row }) => `${getValue()}${row.original.oversell ? " · sobreventa" : ""}`,
    }),
    columnHelper.accessor("expires_at", { header: "Vence", cell: ({ getValue }) => fechaDeNegocioDeInstante(getValue()) }),
    columnHelper.accessor("release_reason", { header: "Motivo", cell: ({ getValue }) => getValue() ?? "" }),
    columnHelper.display({
      id: "actions",
      header: "Acciones",
      cell: ({ row }) => (
        <div className="flex justify-end gap-1">
          {/* Las reservas de pedido viven lo que vive el pedido: se cancela o se
              revierte el pedido, nunca se sueltan por debajo (R-D0-03-6). */}
          {row.original.status === "ACTIVE" && row.original.source_type !== "SALES_ORDER" && puede("POST", `/inventory/reservations/${row.original.id}/release`) ? (
            <AsyncButton size="sm" variant="secondary" onClick={async () => setALiberar(row.original.id)}>Liberar</AsyncButton>
          ) : null}
        </div>
      ),
    }),
  ];

  return (
    <PageContent maxWidth="full">
      <PageHeader
        title="Reservas"
        description="Reservas manuales y de pedidos. Las de pedido nacen al confirmarlo (ORDER_CONFIRMATION) y se liberan desde el pedido; las manuales se liberan aquí con motivo."
        crumbs={[{ label: "Inventario" }, { label: "Reservas" }]}
      />
      <Autorizado operacion={["POST", "/inventory/reservations"]}>
        <section className="mb-4 rounded-lg border border-border-default bg-surface-0 p-4">
          <h2 className="mb-2 text-base font-semibold text-text-900">Nueva reserva</h2>
          <form className="flex flex-wrap items-end gap-3" onSubmit={(e) => e.preventDefault()}>
            <FormField label="Producto" required>
              <select value={newProduct} onChange={(e) => setNewProduct(e.target.value)} className="h-10 w-56 rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900">
                <option value="">Seleccionar…</option>
                {(products.data?.items ?? []).map((p) => (
                  <option key={p.id} value={p.id}>{p.code} · {p.name}</option>
                ))}
              </select>
            </FormField>
            <FormField label="Almacén" required>
              <select value={newWarehouse} onChange={(e) => setNewWarehouse(e.target.value)} className="h-10 w-48 rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900">
                <option value="">Seleccionar…</option>
                {(warehouses.data?.items ?? []).map((w) => (
                  <option key={w.id} value={w.id}>{w.code} · {w.name}</option>
                ))}
              </select>
            </FormField>
            <FormField label="Cantidad" required>
              <TextInput type="number" min="0" value={newQty} onChange={(e) => setNewQty(e.target.value)} required />
            </FormField>
            <FormField label="Documento origen">
              <TextInput value={newDoc} onChange={(e) => setNewDoc(e.target.value)} placeholder="ORD-0001" />
            </FormField>
            <FormField label="Vence en (días)">
              <TextInput type="number" min="1" value={newExpiry} onChange={(e) => setNewExpiry(e.target.value)} placeholder="Opcional" />
            </FormField>
            <AsyncButton type="submit" variant="primary" onClick={createReservation}>Reservar</AsyncButton>
          </form>
        </section>
      </Autorizado>

      <div className="mb-4 flex items-center gap-2">
        <select aria-label="Filtrar por estado" value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)} className="h-10 w-48 rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900">
          <option value="">Todos los estados</option>
          <option value="ACTIVE">Activa</option>
          <option value="RELEASED">Liberada</option>
          <option value="EXPIRED">Vencida</option>
          <option value="FULFILLED">Consumida</option>
        </select>
        <Autorizado operacion={["POST", "/inventory/reservations/expire"]}>
          <AsyncButton variant="secondary" onClick={expireAll}>Expirar manuales vencidas</AsyncButton>
        </Autorizado>
      </div>

      <DataTable
        columns={columns}
        data={query.data?.items ?? []}
        loading={query.isLoading}
        error={query.isError ? "No fue posible cargar las reservas." : null}
        getRowId={(row) => row.id}
        emptyTitle="Sin reservas"
        emptyDescription="Aún no hay reservas registradas."
      />
      <ConfirmationDialog
        open={aLiberar !== null}
        title="Liberar reserva manual"
        description="Indique el motivo. Quedará en la reserva y en la auditoría."
        confirmLabel="Liberar"
        onConfirm={async () => {
          if (!aLiberar) return;
          await release(aLiberar, motivo.trim());
          setALiberar(null);
          setMotivo("");
        }}
        onCancel={() => { setALiberar(null); setMotivo(""); }}
      >
        <FormField label="Motivo" required>
          <TextInput value={motivo} onChange={(e) => setMotivo(e.target.value)} placeholder="Ej. Se vendió por otro canal" required />
        </FormField>
      </ConfirmationDialog>
    </PageContent>
  );
}
