/**
 * Put-away — Spec 022.
 *
 * Coloca físicamente en una ubicación la mercancía que la confirmación dejó
 * disponible pero sin ubicar. Es un traslado de ubicación y nada más: el estado
 * de la mercancía no cambia y el compromiso con el cliente tampoco.
 *
 * Tres límites deliberados, todos de `D0-14`. No recomienda ubicación: los
 * atributos que haría falta considerar —familia, rotación, volumen— no existen
 * en el maestro, y las zonas del proceso están sin validar; elige la persona,
 * de entre las que el backend declara elegibles. La capacidad se muestra y no
 * se aplica, porque su unidad es texto libre. Y no asigna nada al picking: eso
 * es de la Spec 031.
 */
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { createColumnHelper } from "@tanstack/react-table";
import { useState } from "react";

import { ApiError, apiFetch } from "@/api/client";
import { listAllWarehouses } from "@/api/organization";
import type { InventoryBalance, PutAwayLocation } from "@/api/types";
import { useNotifications } from "@/app/contexts/NotificationContext";
import { AsyncButton } from "@/components/AsyncButton";
import { DataTable } from "@/components/DataTable";
import { FormField } from "@/components/FormField";
import { PageHeader } from "@/components/PageHeader";
import { TextInput } from "@/components/TextInput";
import { PageContent } from "@/layout/PageContent";

const columnas = createColumnHelper<InventoryBalance>();

export function PutAwayPage(): React.JSX.Element {
  const qc = useQueryClient();
  const { notify } = useNotifications();
  const [warehouseId, setWarehouseId] = useState("");
  const [seleccion, setSeleccion] = useState<InventoryBalance | null>(null);
  const [destino, setDestino] = useState("");
  const [cantidad, setCantidad] = useState("");

  const almacenes = useQuery({
    queryKey: ["putaway", "almacenes"],
    // El listado se pagina (`limit` ≤ 100): se recorren las páginas hasta
    // reunir `total`, para que el selector no trunque en silencio.
    queryFn: async () => ({ items: await listAllWarehouses() }),
  });

  const pendientes = useQuery({
    queryKey: ["putaway", "pendientes", warehouseId],
    queryFn: () =>
      apiFetch<{ items: InventoryBalance[] }>(
        `/inventory/putaway/pendientes${warehouseId ? `?warehouse_id=${warehouseId}` : ""}`,
      ),
  });

  const ubicaciones = useQuery({
    queryKey: ["putaway", "ubicaciones", warehouseId],
    queryFn: () =>
      apiFetch<{ items: PutAwayLocation[] }>(
        `/inventory/putaway/ubicaciones?warehouse_id=${warehouseId}`,
      ),
    enabled: Boolean(warehouseId),
  });

  async function ubicar(): Promise<void> {
    if (!seleccion || !destino) {
      notify({ type: "error", title: "Elija la mercancía y la ubicación de destino" });
      return;
    }
    try {
      await apiFetch("/inventory/putaway", {
        method: "POST",
        body: {
          product_id: seleccion.product_id,
          warehouse_id: seleccion.warehouse_id,
          target_location_id: destino,
          quantity: cantidad || seleccion.qty_on_hand,
          state: seleccion.state,
          lot_id: seleccion.lot_id,
          serial_id: seleccion.serial_id,
        },
      });
      notify({ type: "success", title: "Mercancía ubicada" });
      setSeleccion(null);
      setDestino("");
      setCantidad("");
      await qc.invalidateQueries({ queryKey: ["putaway"] });
    } catch (e) {
      notify({
        type: "error",
        title: "No se pudo ubicar",
        description: e instanceof ApiError ? e.message : undefined,
      });
    }
  }

  const cols = [
    columnas.accessor("product_id", {
      header: "Producto",
      cell: (c) => <span className="font-mono text-xs">{c.getValue().slice(0, 8)}…</span>,
    }),
    columnas.accessor("state", { header: "Estado" }),
    columnas.accessor("qty_on_hand", { header: "Sin ubicar" }),
    columnas.accessor("lot_id", {
      header: "Lote",
      cell: (c) => c.getValue() ?? <span className="text-text-500">—</span>,
    }),
    columnas.display({
      id: "accion",
      header: "Acción",
      cell: (c) => (
        <button
          type="button"
          onClick={() => {
            setSeleccion(c.row.original);
            setCantidad(String(c.row.original.qty_on_hand));
          }}
          className="text-sm font-medium text-primary-700 underline"
        >
          Elegir ubicación
        </button>
      ),
    }),
  ];

  return (
    <PageContent>
      <PageHeader
        title="Put-away"
        description={
          "Colocar en su ubicación física la mercancía ya confirmada. Cambia dónde está, no qué " +
          "es ni a quién está comprometida."
        }
        crumbs={[{ label: "Inventario" }, { label: "Put-away" }]}
      />

      <section className="mb-4 rounded-lg border border-border-default bg-surface-0 p-4">
        <FormField label="Almacén" required>
          <select
            value={warehouseId}
            onChange={(e) => {
              setWarehouseId(e.target.value);
              setSeleccion(null);
              setDestino("");
            }}
            className="h-10 w-64 rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900"
          >
            <option value="">Todos</option>
            {(almacenes.data?.items ?? []).map((w) => (
              <option key={w.id} value={w.id}>
                {w.code} · {w.name}
              </option>
            ))}
          </select>
        </FormField>
      </section>

      <DataTable
        data={pendientes.data?.items ?? []}
        columns={cols}
        emptyTitle="Nada por ubicar"
        emptyDescription="Toda la mercancía confirmada tiene ya su ubicación física."
      />

      {seleccion ? (
        <section className="mt-4 rounded-lg border border-border-default bg-surface-0 p-4">
          <h2 className="mb-3 text-base font-semibold text-text-900">Colocar la mercancía</h2>
          <p className="mb-3 text-sm text-text-700">
            {seleccion.qty_on_hand} en estado <strong>{seleccion.state}</strong>, sin ubicar.
          </p>
          <div className="flex flex-wrap items-end gap-3">
            <FormField label="Ubicación de destino" required help="Del mismo almacén">
              <select
                value={destino}
                onChange={(e) => setDestino(e.target.value)}
                className="h-10 w-72 rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900"
                disabled={!warehouseId}
              >
                <option value="">Seleccionar…</option>
                {(ubicaciones.data?.items ?? []).map((l) => (
                  <option key={l.id} value={l.id}>
                    {l.code}
                    {l.name ? ` · ${l.name}` : ""}
                    {l.capacity.units !== null
                      ? ` — capacidad declarada ${l.capacity.units}${
                          l.capacity.uom ? ` ${l.capacity.uom}` : ""
                        }`
                      : ""}
                  </option>
                ))}
              </select>
            </FormField>
            <FormField label="Cantidad" help="En unidad base">
              <TextInput value={cantidad} onChange={(e) => setCantidad(e.target.value)} />
            </FormField>
            <AsyncButton onClick={ubicar}>Confirmar ubicación</AsyncButton>
          </div>
          {!warehouseId ? (
            <p className="mt-3 text-sm text-text-500" role="status">
              Elija primero un almacén para ver sus ubicaciones.
            </p>
          ) : null}
          <p className="mt-3 text-xs text-text-500">
            La capacidad de una ubicación es informativa: no impide colocar. Su unidad todavía no
            está tipada contra el catálogo, y comparar contra ella daría una precisión que el dato
            no tiene.
          </p>
        </section>
      ) : null}
    </PageContent>
  );
}
