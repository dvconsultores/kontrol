/**
 * Órdenes de venta — creación, líneas, confirmación con reserva, crédito y
 * ciclo del pedido (FR-005-011/012 · Spec 030, ADR-D0-003 v2).
 *
 * `RESERVATION TRIGGER = ORDER_CONFIRMATION`: confirmar el pedido reserva en
 * cantidad base, todo o nada. Sin crédito queda liberado a preparación; con
 * crédito espera en `SUBMITTED` hasta que la Spec 045 decide. Rechazar,
 * revertir y cancelar exigen motivo. Las acciones las dicta `allowed_actions`
 * del backend: la pantalla no inventa estados.
 */
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { createColumnHelper } from "@tanstack/react-table";
import { useState } from "react";

import { ApiError, apiFetch } from "@/api/client";
import type {
  CatalogItemSummary,
  InsufficientLine,
  PagedResult,
  Party,
  ReservationPolicy,
  SalesOrderSummary,
} from "@/api/types";
import { Autorizado } from "@/components/Autorizado";
import { useAutoridad } from "@/app/autoridad/AutoridadContext";
import { useCompany } from "@/app/contexts/CompanyContext";
import { useNotifications } from "@/app/contexts/NotificationContext";
import { AsyncButton } from "@/components/AsyncButton";
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

interface PresentationSummary {
  id: string;
  code: string;
  name: string;
  status?: string;
}

/** Etiquetas de estado del pedido (FR-030-002). */
const ESTADOS: Record<string, string> = {
  DRAFT: "Borrador",
  SUBMITTED: "Emitido · espera crédito",
  RELEASED: "Liberado a preparación",
  PREPARING: "En preparación",
  SHIPPED: "Despachado",
  CLOSED: "Cerrado",
  CANCELLED: "Cancelado",
  REJECTED: "Rechazado",
  EXPIRED: "Vencido",
};

/** Acciones con motivo obligatorio (IMP-030-035). */
type AccionConMotivo = "reject" | "revert" | "cancel";
const ACCIONES_CON_MOTIVO: Record<AccionConMotivo, { titulo: string; ruta: string; peligrosa: boolean }> = {
  reject: { titulo: "Rechazar el pedido", ruta: "reject", peligrosa: true },
  revert: { titulo: "Revertir a borrador", ruta: "revert", peligrosa: false },
  cancel: { titulo: "Cancelar el pedido", ruta: "cancel", peligrosa: true },
};

const columnHelper = createColumnHelper<SalesOrderSummary>();

function describirInsuficiencia(err: ApiError): string {
  const lineas = (err.details?.lines as InsufficientLine[] | undefined) ?? [];
  if (lineas.length === 0) return err.message;
  return lineas
    .map((l) => `producto ${l.product_id.slice(0, 8)}…: pedido ${l.requested_base}, disponible ${l.available_base}`)
    .join(" · ");
}

function reservadoDe(pedido: SalesOrderSummary): string {
  const activas = pedido.lines.flatMap((l) => (l.reservations ?? []).filter((r) => r.status === "ACTIVE"));
  if (activas.length === 0) return "—";
  const total = activas.reduce((acc, r) => acc + Number(r.base_quantity ?? r.quantity), 0);
  const sobreventa = activas.some((r) => r.oversell);
  return `${total} en base${sobreventa ? " · sobreventa" : ""}`;
}

export function OrdenesVentasPage(): React.JSX.Element {
  const { activeCompany } = useCompany();
  const { puede } = useAutoridad();
  const queryClient = useQueryClient();
  const { notify } = useNotifications();
  const companyId = activeCompany?.id ?? null;

  const [newCode, setNewCode] = useState("");
  const [newCustomer, setNewCustomer] = useState("");
  const [newWarehouse, setNewWarehouse] = useState("");
  const [lineOrder, setLineOrder] = useState("");
  const [lineProduct, setLineProduct] = useState("");
  const [linePresentation, setLinePresentation] = useState("");
  const [lineQty, setLineQty] = useState("");
  const [linePrice, setLinePrice] = useState("");
  const [ttl, setTtl] = useState("");
  const [pendiente, setPendiente] = useState<{ id: string; accion: AccionConMotivo } | null>(null);
  const [motivo, setMotivo] = useState("");

  const query = useQuery({
    queryKey: ["ventas", "ordenes"],
    queryFn: () => apiFetch<PagedResult<SalesOrderSummary>>("/sales/orders"),
    retry: false,
  });
  const customers = useQuery({
    queryKey: ["maestros", "terceros"],
    queryFn: () => apiFetch<PagedResult<Party>>("/maestros/terceros"),
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
  const presentations = useQuery({
    queryKey: ["maestros", "presentaciones", lineProduct],
    queryFn: () => apiFetch<PresentationSummary[]>(`/maestros/productos/${lineProduct}/presentaciones`),
    enabled: Boolean(lineProduct),
    retry: false,
  });
  const policy = useQuery({
    queryKey: ["ventas", "politica-reserva", companyId],
    queryFn: () => apiFetch<ReservationPolicy>("/sales/settings/reservation"),
    enabled: Boolean(companyId),
    retry: false,
  });

  const refresh = (): void => {
    void queryClient.invalidateQueries({ queryKey: ["ventas", "ordenes"] });
  };

  const fallo = (titulo: string, err: unknown): void => {
    if (err instanceof ApiError && err.code === "INSUFFICIENT_AVAILABLE") {
      notify({ type: "error", title: "No hay disponible suficiente", description: describirInsuficiencia(err) });
      return;
    }
    const message = err instanceof Error ? err.message : titulo;
    notify({ type: "error", title: titulo, description: message });
  };

  const createOrder = async (): Promise<void> => {
    try {
      await apiFetch("/sales/orders", {
        method: "POST",
        body: { code: newCode, customer_id: newCustomer, warehouse_id: newWarehouse || null, margin: null, currency: "VED" },
      });
      notify({ type: "success", title: "Pedido creado", description: newCode });
      setNewCode("");
      setNewCustomer("");
      setNewWarehouse("");
      refresh();
    } catch (err) {
      fallo("No fue posible crear el pedido", err);
    }
  };

  const addLine = async (): Promise<void> => {
    if (!lineOrder || !lineProduct) return;
    try {
      const body: Record<string, unknown> = {
        product_id: lineProduct,
        quantity: Number(lineQty) || 0,
        discount: 0,
        needs_inventory: true,
        presentation_id: linePresentation || null,
      };
      // Sin precio, lo resuelve la autoridad comercial (Spec 012/029).
      if (linePrice.trim() !== "") body.unit_price = Number(linePrice);
      await apiFetch(`/sales/orders/${lineOrder}/lines`, { method: "POST", body });
      notify({ type: "success", title: "Línea agregada", description: `Pedido ${lineOrder.slice(0, 8)}…` });
      setLineProduct("");
      setLinePresentation("");
      setLineQty("");
      setLinePrice("");
      refresh();
    } catch (err) {
      fallo("No fue posible agregar la línea", err);
    }
  };

  const ejecutar = async (id: string, ruta: string, body?: Record<string, unknown>): Promise<void> => {
    try {
      const pedido = await apiFetch<SalesOrderSummary>(`/sales/orders/${id}/${ruta}`, { method: "POST", body: body ?? {} });
      refresh();
      notify({ type: "success", title: "Pedido actualizado", description: ESTADOS[pedido.status] ?? pedido.status });
    } catch (err) {
      fallo("No fue posible actualizar el pedido", err);
    }
  };

  const confirmarConMotivo = async (): Promise<void> => {
    if (!pendiente) return;
    await ejecutar(pendiente.id, ACCIONES_CON_MOTIVO[pendiente.accion].ruta, { reason: motivo.trim() });
    setPendiente(null);
    setMotivo("");
  };

  const expirar = async (): Promise<void> => {
    try {
      const res = await apiFetch<{ expired_reservations: number; expired_orders: number }>(
        "/sales/orders/expire-reservations",
        { method: "POST", body: {} },
      );
      notify({
        type: "success",
        title: "Vencimientos procesados",
        description: `${res.expired_reservations} reservas y ${res.expired_orders} pedidos vencidos.`,
      });
      refresh();
    } catch (err) {
      fallo("No fue posible procesar los vencimientos", err);
    }
  };

  const guardarPolitica = async (): Promise<void> => {
    try {
      const dias = ttl.trim() === "" ? null : Number(ttl);
      const res = await apiFetch<ReservationPolicy>("/sales/settings/reservation", {
        method: "PUT",
        body: { reservation_ttl_days: dias },
      });
      notify({
        type: "success",
        title: "Política guardada",
        description: res.reservation_ttl_days ? `Vigencia ${res.reservation_ttl_days} días mientras espera crédito` : "Sin vencimiento",
      });
      void queryClient.invalidateQueries({ queryKey: ["ventas", "politica-reserva"] });
    } catch (err) {
      fallo("No fue posible guardar la política", err);
    }
  };

  const seleccionado = (query.data?.items ?? []).find((o) => o.id === lineOrder) ?? null;

  const columns = [
    columnHelper.accessor("code", { header: "Código" }),
    columnHelper.accessor("customer_id", { header: "Cliente", cell: ({ getValue }) => getValue().slice(0, 8) + "…" }),
    columnHelper.accessor("warehouse_id", { header: "Almacén", cell: ({ getValue }) => getValue()?.slice(0, 8) ?? "—" }),
    columnHelper.accessor("status", {
      header: "Estado",
      cell: ({ getValue }) => ESTADOS[getValue()] ?? getValue(),
    }),
    columnHelper.display({ id: "reservado", header: "Reservado", cell: ({ row }) => reservadoDe(row.original) }),
    columnHelper.accessor("status_reason", { header: "Motivo", cell: ({ getValue }) => getValue() ?? "" }),
    columnHelper.display({
      id: "actions",
      header: "Acciones",
      cell: ({ row }) => {
        const a = row.original.allowed_actions;
        const id = row.original.id;
        const puedeTransicionar = puede("POST", `/sales/orders/${id}/transition`);
        return (
          <div className="flex justify-end gap-1">
            {a.confirm && puede("POST", `/sales/orders/${id}/submit`) ? (
              <AsyncButton size="sm" variant="primary" onClick={() => ejecutar(id, "submit")}>Confirmar</AsyncButton>
            ) : null}
            {a.release && puede("POST", `/sales/orders/${id}/release`) ? (
              <AsyncButton size="sm" variant="secondary" onClick={() => ejecutar(id, "release")}>Liberar</AsyncButton>
            ) : null}
            {a.reject && puede("POST", `/sales/orders/${id}/reject`) ? (
              <AsyncButton size="sm" variant="secondary" onClick={async () => setPendiente({ id, accion: "reject" })}>Rechazar</AsyncButton>
            ) : null}
            {a.revert && puede("POST", `/sales/orders/${id}/revert`) ? (
              <AsyncButton size="sm" variant="secondary" onClick={async () => setPendiente({ id, accion: "revert" })}>Revertir</AsyncButton>
            ) : null}
            {a.cancel && puede("POST", `/sales/orders/${id}/cancel`) ? (
              <AsyncButton size="sm" variant="secondary" onClick={async () => setPendiente({ id, accion: "cancel" })}>Cancelar</AsyncButton>
            ) : null}
            {a.close && puedeTransicionar ? (
              <AsyncButton size="sm" variant="secondary" onClick={() => ejecutar(id, "transition", { target: "CLOSED" })}>Cerrar</AsyncButton>
            ) : null}
          </div>
        );
      },
    }),
  ];

  return (
    <PageContent maxWidth="full">
      <PageHeader
        title="Órdenes de venta"
        description="Al confirmar el pedido se reserva el inventario en cantidad base, todo o nada. Sin crédito queda liberado a preparación; con crédito espera la decisión."
        crumbs={[{ label: "Ventas" }, { label: "Órdenes" }]}
      />

      <section className="mb-4 rounded-lg border border-border-default bg-surface-0 p-4">
        <h2 className="mb-2 text-base font-semibold text-text-900">Nuevo pedido</h2>
        <Autorizado operacion={["POST", "/sales/orders"]}>
        <form className="flex flex-wrap items-end gap-3" onSubmit={(e) => e.preventDefault()}>
          <FormField label="Código" required>
            <TextInput value={newCode} onChange={(e) => setNewCode(e.target.value)} placeholder="Ej. ORD-001" required />
          </FormField>
          <FormField label="Cliente" required>
            <select value={newCustomer} onChange={(e) => setNewCustomer(e.target.value)} className="h-10 w-56 rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900">
              <option value="">Seleccionar…</option>
              {(customers.data?.items ?? []).filter((c) => (c.roles ?? []).includes("CLIENTE")).map((c) => (
                <option key={c.id} value={c.id}>{c.name}</option>
              ))}
            </select>
          </FormField>
          <FormField label="Almacén" help="Obligatorio para confirmar pedidos con inventario">
            <select value={newWarehouse} onChange={(e) => setNewWarehouse(e.target.value)} className="h-10 w-56 rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900">
              <option value="">Sin almacén</option>
              {(warehouses.data?.items ?? []).map((w) => (
                <option key={w.id} value={w.id}>{w.code} · {w.name}</option>
              ))}
            </select>
          </FormField>
          <AsyncButton type="submit" variant="primary" onClick={createOrder}>Crear</AsyncButton>
        </form>
        </Autorizado>
      </section>

      <section className="mb-4 rounded-lg border border-border-default bg-surface-0 p-4">
        <h2 className="mb-2 text-base font-semibold text-text-900">Agregar línea</h2>
        <Autorizado operacion={["POST", "/sales/orders/_/lines"]}>
        <form className="flex flex-wrap items-end gap-3" onSubmit={(e) => e.preventDefault()}>
          <FormField label="Pedido" required>
            <select value={lineOrder} onChange={(e) => setLineOrder(e.target.value)} className="h-10 w-56 rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900">
              <option value="">Seleccionar…</option>
              {(query.data?.items ?? []).map((o) => (
                <option key={o.id} value={o.id}>{o.code} · {ESTADOS[o.status] ?? o.status}</option>
              ))}
            </select>
          </FormField>
          <FormField label="Producto" required>
            <select value={lineProduct} onChange={(e) => { setLineProduct(e.target.value); setLinePresentation(""); }} className="h-10 w-56 rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900">
              <option value="">Seleccionar…</option>
              {(products.data?.items ?? []).map((p) => (
                <option key={p.id} value={p.id}>{p.code} · {p.name}</option>
              ))}
            </select>
          </FormField>
          <FormField label="Presentación" help="La reserva se hace en unidad base">
            <select value={linePresentation} onChange={(e) => setLinePresentation(e.target.value)} className="h-10 w-48 rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900" disabled={!lineProduct}>
              <option value="">Unidad base</option>
              {(presentations.data ?? []).map((p) => (
                <option key={p.id} value={p.id}>{p.code} · {p.name}</option>
              ))}
            </select>
          </FormField>
          <FormField label="Cantidad" required>
            <TextInput type="number" min="0" value={lineQty} onChange={(e) => setLineQty(e.target.value)} placeholder="0" required />
          </FormField>
          <FormField label="Precio" help="Vacío: lo resuelve la lista de precios">
            <TextInput type="number" min="0" value={linePrice} onChange={(e) => setLinePrice(e.target.value)} placeholder="Automático" />
          </FormField>
          <AsyncButton type="submit" variant="secondary" onClick={addLine}>Agregar</AsyncButton>
        </form>
        {seleccionado ? (
          <div className="mt-3 overflow-x-auto" tabIndex={0} role="region" aria-label={`Líneas del pedido ${seleccionado.code}`}>
            <table className="min-w-full text-sm">
              <caption className="sr-only">Líneas del pedido {seleccionado.code}</caption>
              <thead>
                <tr className="text-left text-text-500">
                  <th scope="col" className="pr-4">Producto</th>
                  <th scope="col" className="pr-4">Cantidad</th>
                  <th scope="col" className="pr-4">Base</th>
                  <th scope="col" className="pr-4">Precio</th>
                  <th scope="col" className="pr-4">Reserva</th>
                </tr>
              </thead>
              <tbody>
                {seleccionado.lines.map((l) => {
                  const activa = (l.reservations ?? []).find((r) => r.status === "ACTIVE");
                  const ultima = (l.reservations ?? [])[(l.reservations ?? []).length - 1];
                  return (
                    <tr key={l.id}>
                      <td className="pr-4">{l.product_id.slice(0, 8)}…</td>
                      <td className="pr-4">{String(l.quantity)}</td>
                      <td className="pr-4">{l.base_quantity ?? "—"}</td>
                      <td className="pr-4">{String(l.unit_price)}</td>
                      <td className="pr-4">
                        {activa
                          ? `Activa · ${activa.base_quantity ?? activa.quantity}${activa.oversell ? " · sobreventa" : ""}${activa.expires_at ? ` · vence ${fechaDeNegocioDeInstante(activa.expires_at)}` : ""}`
                          : ultima
                            ? `${ultima.status}${ultima.release_reason ? ` · ${ultima.release_reason}` : ""}`
                            : l.needs_inventory
                              ? "Sin reserva"
                              : "Servicio"}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        ) : null}
        </Autorizado>
      </section>

      <section className="mb-4 rounded-lg border border-border-default bg-surface-0 p-4">
        <h2 className="mb-2 text-base font-semibold text-text-900">Política de reserva</h2>
        <p className="mb-2 text-sm text-text-500">
          Disparador: {policy.data?.reservation_trigger ?? "ORDER_CONFIRMATION"} (fijo). La vigencia solo aplica mientras el pedido espera crédito.
        </p>
        <Autorizado operacion={["PUT", "/sales/settings/reservation"]}>
        <form className="flex flex-wrap items-end gap-3" onSubmit={(e) => e.preventDefault()}>
          <FormField label="Vigencia (días)" help={policy.data?.reservation_ttl_days ? `Actual: ${policy.data.reservation_ttl_days}` : "Actual: sin vencimiento"}>
            <TextInput type="number" min="1" value={ttl} onChange={(e) => setTtl(e.target.value)} placeholder="Sin vencimiento" />
          </FormField>
          <AsyncButton type="submit" variant="secondary" onClick={guardarPolitica}>Guardar</AsyncButton>
        </form>
        </Autorizado>
        <Autorizado operacion={["POST", "/sales/orders/expire-reservations"]}>
          <AsyncButton variant="secondary" onClick={expirar}>Procesar vencimientos</AsyncButton>
        </Autorizado>
      </section>

      <DataTable
        columns={columns}
        data={query.data?.items ?? []}
        loading={query.isLoading}
        error={query.isError ? "No fue posible cargar las órdenes." : null}
        getRowId={(row) => row.id}
        emptyTitle="Sin órdenes"
        emptyDescription="Aún no hay órdenes de venta registradas."
      />

      <ConfirmationDialog
        open={pendiente !== null}
        title={pendiente ? ACCIONES_CON_MOTIVO[pendiente.accion].titulo : ""}
        description="Indique el motivo. Quedará en el pedido y en la auditoría; la reserva se libera completa."
        confirmLabel="Confirmar"
        danger={pendiente ? ACCIONES_CON_MOTIVO[pendiente.accion].peligrosa : false}
        onConfirm={confirmarConMotivo}
        onCancel={() => { setPendiente(null); setMotivo(""); }}
      >
        <FormField label="Motivo" required>
          <TextInput value={motivo} onChange={(e) => setMotivo(e.target.value)} placeholder="Ej. El cliente desistió" required />
        </FormField>
      </ConfirmationDialog>
    </PageContent>
  );
}
