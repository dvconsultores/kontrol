/** Picking y despacho — pick lists y envíos con validación (FR-005-020/021/022, WF-04). */
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { createColumnHelper } from "@tanstack/react-table";
import { useState } from "react";

import { apiFetch } from "@/api/client";
import type { PickListSummary, SalesOrderSummary, ShipmentSummary } from "@/api/types";
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

const pickHelper = createColumnHelper<PickListSummary>();
const shipmentHelper = createColumnHelper<ShipmentSummary>();

export function DespachoPage(): React.JSX.Element {
  const { activeCompany } = useCompany();
  const queryClient = useQueryClient();
  const { notify } = useNotifications();

  const [plCode, setPlCode] = useState("");
  const [plOrder, setPlOrder] = useState("");
  const [plWarehouse, setPlWarehouse] = useState("");
  const [shCode, setShCode] = useState("");
  const [shOrder, setShOrder] = useState("");
  const [shWarehouse, setShWarehouse] = useState("");
  const [shDestination, setShDestination] = useState("");
  const [shTransport, setShTransport] = useState("");

  const companyId = activeCompany?.id ?? null;

  const pickLists = useQuery({
    queryKey: ["ventas", "pick-lists"],
    queryFn: () => apiFetch<{ items: PickListSummary[] }>("/sales/pick-lists"),
    retry: false,
  });
  const shipments = useQuery({
    queryKey: ["ventas", "shipments"],
    queryFn: () => apiFetch<{ items: ShipmentSummary[] }>("/sales/shipments"),
    retry: false,
  });
  const orders = useQuery({
    queryKey: ["ventas", "ordenes"],
    queryFn: () => apiFetch<{ items: SalesOrderSummary[] }>("/sales/orders"),
    retry: false,
  });
  const warehouses = useQuery({
    queryKey: ["organizacion", "almacenes", companyId],
    queryFn: () => apiFetch<{ items: WarehouseSummary[] }>(`/organization/warehouses?company_id=${companyId}`),
    enabled: Boolean(companyId),
    retry: false,
  });

  const refresh = (): void => {
    void queryClient.invalidateQueries({ queryKey: ["ventas", "pick-lists"] });
    void queryClient.invalidateQueries({ queryKey: ["ventas", "shipments"] });
  };

  const createPickList = async (): Promise<void> => {
    try {
      await apiFetch("/sales/pick-lists", {
        method: "POST",
        body: { code: plCode, order_id: plOrder, warehouse_id: plWarehouse, lines: null },
      });
      notify({ type: "success", title: "Pick list creada", description: plCode });
      setPlCode(""); setPlOrder(""); setPlWarehouse("");
      refresh();
    } catch (err) {
      const message = err instanceof Error ? err.message : "No fue posible crear la pick list";
      notify({ type: "error", title: "No fue posible crear la pick list", description: message });
    }
  };

  const createShipment = async (): Promise<void> => {
    try {
      await apiFetch("/sales/shipments", {
        method: "POST",
        body: {
          code: shCode, order_id: shOrder, origin_warehouse_id: shWarehouse,
          destination: shDestination || null, transport: shTransport || null, lines: null,
        },
      });
      notify({ type: "success", title: "Despacho creado", description: shCode });
      setShCode(""); setShOrder(""); setShWarehouse(""); setShDestination(""); setShTransport("");
      refresh();
    } catch (err) {
      const message = err instanceof Error ? err.message : "No fue posible crear el despacho";
      notify({ type: "error", title: "No fue posible crear el despacho", description: message });
    }
  };

  const runShipmentAction = async (id: string, action: "validate" | "confirm"): Promise<void> => {
    await apiFetch(`/sales/shipments/${id}/${action}`, { method: "POST", body: {} });
    notify({ type: "success", title: "Despacho actualizado", description: `${id} → ${action}` });
    refresh();
  };

  const pickColumns = [
    pickHelper.accessor("code", { header: "Código" }),
    pickHelper.accessor("order_id", { header: "Orden" }),
    pickHelper.accessor("warehouse_id", { header: "Almacén" }),
    pickHelper.accessor("status", { header: "Estado" }),
  ];

  const shipmentColumns = [
    shipmentHelper.accessor("code", { header: "Código" }),
    shipmentHelper.accessor("order_id", { header: "Orden" }),
    shipmentHelper.accessor("origin_warehouse_id", { header: "Almacén origen" }),
    shipmentHelper.accessor("status", { header: "Estado" }),
    shipmentHelper.accessor("validation_status", { header: "Validación" }),
    shipmentHelper.display({
      id: "actions",
      header: "Acciones",
      cell: ({ row }) => (
        <div className="flex justify-end gap-1">
          {row.original.validation_status === "PENDING" ? (
            <AsyncButton size="sm" variant="secondary" onClick={() => runShipmentAction(row.original.id, "validate")}>validar</AsyncButton>
          ) : null}
          {row.original.status === "VALIDATED" ? (
            <AsyncButton size="sm" variant="secondary" onClick={() => runShipmentAction(row.original.id, "confirm")}>confirmar</AsyncButton>
          ) : null}
        </div>
      ),
    }),
  ];

  return (
    <PageContent maxWidth="full">
      <PageHeader
        title="Picking y despacho"
        description="Pick lists y envíos: creación, validación y confirmación."
        crumbs={[{ label: "Ventas" }, { label: "Despacho" }]}
      />
      <section className="mb-4 rounded-lg border border-border-default bg-surface-0 p-4">
        <h2 className="mb-2 text-base font-semibold text-text-900">Nueva pick list</h2>
        <form className="flex flex-wrap items-end gap-3" onSubmit={(e) => e.preventDefault()}>
          <FormField label="Código" required>
            <TextInput value={plCode} onChange={(e) => setPlCode(e.target.value)} placeholder="PK-0001" required />
          </FormField>
          <FormField label="Orden" required>
            <select value={plOrder} onChange={(e) => setPlOrder(e.target.value)} className="h-10 w-56 rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900">
              <option value="">Seleccionar…</option>
              {(orders.data?.items ?? [])
                .filter((o) => o.status === "RESERVED" || o.status === "PREPARING")
                .map((o) => (
                  <option key={o.id} value={o.id}>{o.code} · {o.status}</option>
                ))}
            </select>
          </FormField>
          <FormField label="Almacén" required>
            <select value={plWarehouse} onChange={(e) => setPlWarehouse(e.target.value)} className="h-10 w-56 rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900">
              <option value="">Seleccionar…</option>
              {(warehouses.data?.items ?? []).map((w) => (
                <option key={w.id} value={w.id}>{w.code} · {w.name}</option>
              ))}
            </select>
          </FormField>
          <AsyncButton type="submit" variant="primary" onClick={createPickList}>Crear</AsyncButton>
        </form>
      </section>

      <section className="mb-4 rounded-lg border border-border-default bg-surface-0 p-4">
        <h2 className="mb-2 text-base font-semibold text-text-900">Nuevo despacho</h2>
        <form className="flex flex-wrap items-end gap-3" onSubmit={(e) => e.preventDefault()}>
          <FormField label="Código" required>
            <TextInput value={shCode} onChange={(e) => setShCode(e.target.value)} placeholder="DESP-0001" required />
          </FormField>
          <FormField label="Orden" required>
            <select value={shOrder} onChange={(e) => setShOrder(e.target.value)} className="h-10 w-56 rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900">
              <option value="">Seleccionar…</option>
              {(orders.data?.items ?? [])
                .filter((o) => o.status === "RESERVED" || o.status === "PREPARING" || o.status === "SHIPPED")
                .map((o) => (
                  <option key={o.id} value={o.id}>{o.code} · {o.status}</option>
                ))}
            </select>
          </FormField>
          <FormField label="Almacén origen" required>
            <select value={shWarehouse} onChange={(e) => setShWarehouse(e.target.value)} className="h-10 w-56 rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900">
              <option value="">Seleccionar…</option>
              {(warehouses.data?.items ?? []).map((w) => (
                <option key={w.id} value={w.id}>{w.code} · {w.name}</option>
              ))}
            </select>
          </FormField>
          <FormField label="Destino">
            <TextInput value={shDestination} onChange={(e) => setShDestination(e.target.value)} placeholder="Dirección de entrega" />
          </FormField>
          <FormField label="Transporte">
            <TextInput value={shTransport} onChange={(e) => setShTransport(e.target.value)} placeholder="Empresa de transporte" />
          </FormField>
          <AsyncButton type="submit" variant="primary" onClick={createShipment}>Crear</AsyncButton>
        </form>
      </section>

      <h2 className="mb-2 text-base font-semibold text-text-900">Pick lists</h2>
      <div className="mb-6">
        <DataTable
          columns={pickColumns}
          data={pickLists.data?.items ?? []}
          loading={pickLists.isLoading}
          error={pickLists.isError ? "No fue posible cargar las pick lists." : null}
          getRowId={(row) => row.id}
          emptyTitle="Sin pick lists"
          emptyDescription="Aún no hay pick lists."
        />
      </div>

      <h2 className="mb-2 text-base font-semibold text-text-900">Despachos</h2>
      <DataTable
        columns={shipmentColumns}
        data={shipments.data?.items ?? []}
        loading={shipments.isLoading}
        error={shipments.isError ? "No fue posible cargar los despachos." : null}
        getRowId={(row) => row.id}
        emptyTitle="Sin despachos"
        emptyDescription="Aún no hay despachos."
      />
    </PageContent>
  );
}
