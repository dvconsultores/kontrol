/**
 * Despacho, transporte y regulación — Spec 035.
 *
 * Es el último acto del proceso y el único en el que la mercancía cruza la
 * puerta. El ¶103 dice qué se verifica antes de dejarla salir: «Pedido
 * preparado + Pedido confirmado + Factura emitida». Esta pantalla no repite
 * ninguna de esas tres cosas —cada una tiene su propia pantalla y su propia
 * Spec— sino que muestra si están, y llama a la compuerta que las comprueba.
 *
 * Lo que sale es lo que la factura dice. No hay campo de cantidad: escribirla
 * aquí sería inventar un despacho parcial que el proceso no contempla.
 */
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { createColumnHelper } from "@tanstack/react-table";
import { useState } from "react";

import { ApiError, apiFetch } from "@/api/client";
import type {
  Dispatch,
  DispatchableOrder,
  OrderDispatchStatus,
  TransportDriverSummary,
  TransportVehicleSummary,
} from "@/api/types";
import { useNotifications } from "@/app/contexts/NotificationContext";
import { AsyncButton } from "@/components/AsyncButton";
import { DataTable } from "@/components/DataTable";
import { FormField } from "@/components/FormField";
import { PageHeader } from "@/components/PageHeader";
import { TextInput } from "@/components/TextInput";
import { PageContent } from "@/layout/PageContent";

const cols = createColumnHelper<DispatchableOrder>();

const SELECT =
  "h-10 w-56 rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900";

function corto(id: string): string {
  return `${id.slice(0, 8)}…`;
}

export function DespachoPage(): React.JSX.Element {
  const qc = useQueryClient();
  const { notify } = useNotifications();
  const [orderId, setOrderId] = useState<string | null>(null);
  const [codigo, setCodigo] = useState("");
  const [destino, setDestino] = useState("");
  const [transporte, setTransporte] = useState("");
  const [vehiculo, setVehiculo] = useState("");
  const [conductor, setConductor] = useState("");

  const pendientes = useQuery({
    queryKey: ["despacho", "pendientes"],
    queryFn: () => apiFetch<{ items: DispatchableOrder[] }>("/sales/despacho/pendientes"),
  });

  const estado = useQuery({
    queryKey: ["despacho", "estado", orderId],
    queryFn: () => apiFetch<OrderDispatchStatus>(`/sales/despacho/${orderId}/despacho`),
    enabled: Boolean(orderId),
  });

  const vehiculos = useQuery({
    queryKey: ["regulatorio", "vehiculos"],
    queryFn: () => apiFetch<{ items: TransportVehicleSummary[] }>("/regulatory/vehicles"),
    retry: false,
  });

  const conductores = useQuery({
    queryKey: ["regulatorio", "conductores"],
    queryFn: () => apiFetch<{ items: TransportDriverSummary[] }>("/regulatory/drivers"),
    retry: false,
  });

  function fallo(titulo: string) {
    return (e: unknown) =>
      notify({
        type: "error",
        title: titulo,
        description: e instanceof ApiError ? e.message : undefined,
      });
  }

  async function refrescar(): Promise<void> {
    await qc.invalidateQueries({ queryKey: ["despacho"] });
  }

  async function registrar(): Promise<void> {
    const fila = pendientes.data?.items.find((o) => o.order_id === orderId);
    if (!orderId || !fila) return;
    if (!codigo || !destino || !transporte) {
      notify({
        type: "error",
        title: "Faltan datos de la salida",
        description: "Indique el código, el destino y a quién se entrega la mercancía.",
      });
      return;
    }
    try {
      await apiFetch("/sales/shipments", {
        method: "POST",
        body: {
          code: codigo,
          order_id: orderId,
          origin_warehouse_id: null,
          destination: destino,
          transport: transporte,
          vehicle_id: vehiculo || null,
          driver_id: conductor || null,
          lines: null,
        },
      });
      notify({ type: "success", title: "Despacho registrado", description: codigo });
      setCodigo("");
      setDestino("");
      setTransporte("");
      setVehiculo("");
      setConductor("");
      await refrescar();
    } catch (e) {
      fallo("No se pudo registrar el despacho")(e);
    }
  }

  async function validar(sh: Dispatch): Promise<void> {
    try {
      await apiFetch(`/sales/shipments/${sh.id}/validate`, { method: "POST", body: {} });
      notify({
        type: "success",
        title: "Salida autorizada",
        description: "Preparado, confirmado, facturado y sin bloqueo regulatorio.",
      });
      await refrescar();
    } catch (e) {
      fallo("La salida no fue autorizada")(e);
    }
  }

  async function confirmar(sh: Dispatch): Promise<void> {
    try {
      await apiFetch(`/sales/shipments/${sh.id}/confirm`, { method: "POST", body: {} });
      notify({
        type: "success",
        title: "Salida registrada",
        description: "La mercancía salió del almacén y la reserva quedó consumida.",
      });
      await refrescar();
    } catch (e) {
      fallo("No se pudo registrar la salida")(e);
    }
  }

  const columnas = [
    cols.accessor("code", { header: "Pedido" }),
    cols.accessor("invoice_number", {
      header: "Factura",
      cell: (c) => c.getValue() ?? "sin emitir",
    }),
    cols.accessor("shipment_status", {
      header: "Despacho",
      cell: (c) => c.getValue() ?? "sin registrar",
    }),
    cols.display({
      id: "accion",
      header: "Acción",
      cell: (c) => (
        <button
          type="button"
          onClick={() => setOrderId(c.row.original.order_id)}
          className="text-sm font-medium text-primary-700 underline"
        >
          {c.row.original.shipment_id ? "Ver despacho" : "Preparar salida"}
        </button>
      ),
    }),
  ];

  const e = estado.data;
  const sh = e?.shipment ?? null;

  return (
    <PageContent>
      <PageHeader
        title="Despacho"
        description={
          "Antes de que la mercancía salga se verifica que corresponda: pedido preparado, " +
          "pedido confirmado y factura emitida, más los requisitos regulatorios que apliquen."
        }
        crumbs={[{ label: "Ventas" }, { label: "Despacho" }]}
      />

      <section className="mb-4">
        <h2 className="mb-2 text-base font-semibold text-text-900">Pedidos por despachar</h2>
        <DataTable
          data={pendientes.data?.items ?? []}
          columns={columnas}
          loading={pendientes.isLoading}
          error={pendientes.isError ? "No fue posible cargar la cola de despacho." : null}
          getRowId={(row) => row.order_id}
          emptyTitle="Nada por despachar"
          emptyDescription="Ningún pedido facturado espera salida."
        />
      </section>

      {e ? (
        <section className="rounded-lg border border-border-default bg-surface-0 p-4">
          <h2 className="mb-1 text-base font-semibold text-text-900">
            Pedido {corto(e.order_id)} · {e.order_status}
          </h2>

          {!sh ? (
            <>
              <p className="mb-3 text-sm text-text-700">
                La salida lleva lo que la factura dice. Indique a dónde va y quién la lleva:
                puede ser un transportista, el propio cliente o el responsable del traslado.
              </p>
              <form className="flex flex-wrap items-end gap-3" onSubmit={(ev) => ev.preventDefault()}>
                <FormField label="Código" required>
                  <TextInput
                    value={codigo}
                    onChange={(ev) => setCodigo(ev.target.value)}
                    placeholder="DESP-0001"
                  />
                </FormField>
                <FormField label="Destino" required>
                  <TextInput
                    value={destino}
                    onChange={(ev) => setDestino(ev.target.value)}
                    placeholder="Dirección de entrega"
                  />
                </FormField>
                <FormField label="Se entrega a" required>
                  <TextInput
                    value={transporte}
                    onChange={(ev) => setTransporte(ev.target.value)}
                    placeholder="Transportista, cliente o responsable"
                  />
                </FormField>
                <FormField label="Vehículo">
                  <select
                    value={vehiculo}
                    onChange={(ev) => setVehiculo(ev.target.value)}
                    className={SELECT}
                    aria-label="Vehículo"
                  >
                    <option value="">Sin registrar</option>
                    {(vehiculos.data?.items ?? [])
                      .filter((v) => v.status === "ACTIVE")
                      .map((v) => (
                        <option key={v.id} value={v.id}>
                          {v.plate}
                          {v.vehicle_type ? ` · ${v.vehicle_type}` : ""}
                        </option>
                      ))}
                  </select>
                </FormField>
                <FormField label="Conductor">
                  <select
                    value={conductor}
                    onChange={(ev) => setConductor(ev.target.value)}
                    className={SELECT}
                    aria-label="Conductor"
                  >
                    <option value="">Sin registrar</option>
                    {(conductores.data?.items ?? [])
                      .filter((d) => d.status === "ACTIVE")
                      .map((d) => (
                        <option key={d.id} value={d.id}>
                          {d.license ?? corto(d.party_id)}
                        </option>
                      ))}
                  </select>
                </FormField>
                <AsyncButton onClick={registrar}>Registrar despacho</AsyncButton>
              </form>
            </>
          ) : (
            <>
              <p className="mb-3 text-sm text-text-700">
                {sh.code} · {sh.status} · destino {sh.destination ?? "—"} · se entrega a{" "}
                {sh.transport ?? "—"}
                {sh.vehicle_id ? ` · vehículo ${corto(sh.vehicle_id)}` : ""}
                {sh.driver_id ? ` · conductor ${corto(sh.driver_id)}` : ""}
              </p>

              <table className="mb-3 w-full text-sm">
                <caption className="sr-only">Líneas del despacho</caption>
                <thead>
                  <tr className="border-b border-border-default text-left text-text-700">
                    <th scope="col" className="py-1">Producto</th>
                    <th scope="col">Cantidad</th>
                    <th scope="col">En unidad base</th>
                    <th scope="col">Lote</th>
                  </tr>
                </thead>
                <tbody>
                  {sh.lines.map((l, i) => (
                    <tr key={`${l.product_id}-${i}`} className="border-b border-border-subtle">
                      <td className="py-1 font-mono text-xs">{corto(l.product_id)}</td>
                      <td>{l.quantity}</td>
                      <td>{l.base_quantity ?? "—"}</td>
                      <td className="font-mono text-xs">{l.lot_id ? corto(l.lot_id) : "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>

              {sh.regulatory_status ? (
                <p className="mb-3 text-sm text-text-700" role="status">
                  Regulatorio: {sh.regulatory_status === "CLEARED" ? "sin impedimento" : "bloqueado"}.
                  Se valida contra lo registrado en el sistema; KONTROL no emite permisos ni los
                  verifica en línea.
                </p>
              ) : null}

              {sh.status === "DRAFT" ? (
                <>
                  <p className="mb-3 text-sm text-text-700">
                    Validar comprueba las cuatro cosas de una vez: que hay preparación consolidada,
                    que alguien distinto confirmó el pedido, que la factura está emitida y que no
                    falta ningún requisito regulatorio.
                  </p>
                  <AsyncButton onClick={() => validar(sh)}>Validar salida</AsyncButton>
                </>
              ) : null}

              {sh.status === "READY" ? (
                <>
                  <p className="mb-3 text-sm text-text-700">
                    Confirmar registra la salida física: la mercancía deja de estar preparada y la
                    reserva se consume. No vuelve al disponible.
                  </p>
                  <AsyncButton onClick={() => confirmar(sh)}>Confirmar salida física</AsyncButton>
                </>
              ) : null}

              {sh.status === "SHIPPED" ? (
                <p className="text-sm text-text-700" role="status">
                  Mercancía despachada el {sh.dispatched_at?.slice(0, 16).replace("T", " ")}. El
                  pedido queda en poder del transporte hasta su entrega.
                </p>
              ) : null}
            </>
          )}
        </section>
      ) : null}
    </PageContent>
  );
}
