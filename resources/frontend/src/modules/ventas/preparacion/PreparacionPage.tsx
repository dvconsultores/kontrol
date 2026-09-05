/**
 * Cola y ruta de picking — Spec 031.
 *
 * Planifica: decide de qué ubicación se recoge cuánto de cada línea y en qué
 * orden se recorre el almacén. No recoge nada; el movimiento físico es de la
 * Spec 032.
 *
 * Tres límites vienen de `D0-15` y se ven en la pantalla. La cola se ordena por
 * el momento en que cada pedido quedó liberado, sin prioridad de cliente ni
 * manual. Un plan puede quedarse a medias mientras el put-away completa lo que
 * falta, pero **no se confirma** hasta que no falte nada: el botón lo dice y el
 * backend lo impide. Y cancelar libera las asignaciones sin tocar la reserva.
 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { createColumnHelper } from "@tanstack/react-table";
import { useState } from "react";

import { ApiError, apiFetch } from "@/api/client";
import type {
  PickingCandidate,
  PickingPlan,
  PickingQueueItem,
  PickListSummary,
} from "@/api/types";
import { useNotifications } from "@/app/contexts/NotificationContext";
import { AsyncButton } from "@/components/AsyncButton";
import { DataTable } from "@/components/DataTable";
import { FormField } from "@/components/FormField";
import { PageHeader } from "@/components/PageHeader";
import { TextInput } from "@/components/TextInput";
import { PageContent } from "@/layout/PageContent";

/** Igual que en el put-away: el selector de almacén solo necesita esto. */
interface WarehouseSummary {
  id: string;
  code: string;
  name: string;
}

const colaCols = createColumnHelper<PickingQueueItem>();

function corto(id: string): string {
  return `${id.slice(0, 8)}…`;
}

export function PreparacionPage(): React.JSX.Element {
  const qc = useQueryClient();
  const { notify } = useNotifications();
  const [almacen, setAlmacen] = useState("");
  const [pedido, setPedido] = useState<PickingQueueItem | null>(null);
  const [planId, setPlanId] = useState<string | null>(null);
  const [lineaId, setLineaId] = useState("");
  const [ubicacion, setUbicacion] = useState("");
  const [cantidad, setCantidad] = useState("");
  const [motivo, setMotivo] = useState("");

  // El almacenista trabaja en un almacén. Sin este filtro la cola mezcla los de
  // todos y deja de ser una cola de trabajo.
  const almacenes = useQuery({
    queryKey: ["picking", "almacenes"],
    queryFn: () => apiFetch<{ items: WarehouseSummary[] }>("/organization/warehouses?limit=500"),
  });

  const cola = useQuery({
    queryKey: ["picking", "cola", almacen],
    queryFn: () =>
      apiFetch<{ items: PickingQueueItem[] }>(
        `/sales/picking/cola${almacen ? `?warehouse_id=${almacen}` : ""}`,
      ),
  });

  const plan = useQuery({
    queryKey: ["picking", "plan", planId],
    queryFn: () => apiFetch<PickingPlan>(`/sales/picking/${planId}`),
    enabled: Boolean(planId),
  });

  const candidatas = useQuery({
    queryKey: ["picking", "candidatas", planId, lineaId],
    queryFn: () =>
      apiFetch<{ items: PickingCandidate[] }>(
        `/sales/picking/${planId}/candidatas?order_line_id=${lineaId}`,
      ),
    enabled: Boolean(planId && lineaId),
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
    await qc.invalidateQueries({ queryKey: ["picking"] });
  }

  const abrirPlan = useMutation({
    mutationFn: async (item: PickingQueueItem) => {
      const existentes = await apiFetch<{ items: PickListSummary[] }>(
        `/sales/pick-lists?order_id=${item.order_id}`,
      );
      const vivo = existentes.items.find((p) => p.status === "DRAFT" || p.status === "CONFIRMED");
      if (vivo) return vivo.id;
      const creado = await apiFetch<{ id: string }>("/sales/pick-lists", {
        method: "POST",
        body: {
          code: `PICK-${item.code}`,
          order_id: item.order_id,
          warehouse_id: item.warehouse_id,
        },
      });
      return creado.id;
    },
    onSuccess: (id, item) => {
      setPlanId(id);
      setPedido(item);
      setLineaId("");
      void refrescar();
    },
    onError: fallo("No se pudo abrir el plan"),
  });

  async function asignar(): Promise<void> {
    if (!planId || !lineaId || !ubicacion) {
      notify({ type: "error", title: "Elija la línea y la ubicación de origen" });
      return;
    }
    try {
      await apiFetch(`/sales/picking/${planId}/asignaciones`, {
        method: "POST",
        body: { order_line_id: lineaId, location_id: ubicacion, quantity: cantidad || "0" },
      });
      notify({ type: "success", title: "Asignación registrada" });
      setUbicacion("");
      setCantidad("");
      await refrescar();
    } catch (e) {
      fallo("No se pudo asignar")(e);
    }
  }

  async function accion(ruta: string, titulo: string, cuerpo?: object): Promise<void> {
    if (!planId) return;
    try {
      await apiFetch(`/sales/picking/${planId}/${ruta}`, { method: "POST", body: cuerpo ?? {} });
      notify({ type: "success", title: titulo });
      setMotivo("");
      await refrescar();
    } catch (e) {
      fallo(`No se pudo ${titulo.toLowerCase()}`)(e);
    }
  }

  const cols = [
    colaCols.accessor("position", { header: "Puesto" }),
    colaCols.accessor("code", { header: "Pedido" }),
    colaCols.accessor("released_at", {
      header: "Liberado",
      cell: (c) => c.getValue()?.replace("T", " ").slice(0, 19) ?? "—",
    }),
    colaCols.display({
      id: "accion",
      header: "Acción",
      cell: (c) => (
        <button
          type="button"
          onClick={() => abrirPlan.mutate(c.row.original)}
          className="text-sm font-medium text-primary-700 underline"
        >
          Planificar
        </button>
      ),
    }),
  ];

  const p = plan.data;
  const editable = p?.status === "DRAFT";

  return (
    <PageContent>
      <PageHeader
        title="Preparación de pedidos"
        description={
          "Cola de picking y recorrido por ubicación. Decide de dónde se recoge cada línea; no " +
          "mueve mercancía."
        }
        crumbs={[{ label: "Ventas" }, { label: "Preparación" }]}
      />

      <section className="mb-4">
        <h2 className="mb-2 text-base font-semibold text-text-900">Cola</h2>
        <div className="mb-3">
          <FormField label="Almacén">
            <select
              value={almacen}
              onChange={(e) => {
                setAlmacen(e.target.value);
                setPlanId(null);
                setPedido(null);
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
        </div>
        <p className="mb-3 text-sm text-text-700">
          Por orden de liberación. Un pedido retenido por crédito entra cuando se libera, no cuando
          se emitió.
        </p>
        <DataTable
          data={cola.data?.items ?? []}
          columns={cols}
          emptyTitle="Nada por preparar"
          emptyDescription="Ningún pedido liberado espera preparación."
        />
      </section>

      {p ? (
        <section className="rounded-lg border border-border-default bg-surface-0 p-4">
          <h2 className="mb-1 text-base font-semibold text-text-900">
            Plan {p.code} · {p.status}
          </h2>
          <p className="mb-3 text-sm text-text-700">
            Pedido {pedido?.code ?? corto(p.order_id)}. Falta por asignar:{" "}
            <strong>{p.remaining_base_quantity}</strong> en unidad base.
          </p>

          <table className="mb-4 w-full text-sm">
            <caption className="sr-only">Demanda por línea del pedido</caption>
            <thead>
              <tr className="border-b border-border-default text-left text-text-700">
                <th scope="col" className="py-1">Línea</th>
                <th scope="col">Requerido</th>
                <th scope="col">Asignado</th>
                <th scope="col">Falta</th>
                <th scope="col">Acción</th>
              </tr>
            </thead>
            <tbody>
              {p.demand.map((d) => (
                <tr key={d.order_line_id} className="border-b border-border-subtle">
                  <td className="py-1 font-mono text-xs">{corto(d.order_line_id)}</td>
                  <td>{d.required_base_quantity}</td>
                  <td>{d.allocated_base_quantity}</td>
                  <td>{d.remaining_base_quantity}</td>
                  <td>
                    {editable ? (
                      <button
                        type="button"
                        onClick={() => setLineaId(d.order_line_id)}
                        className="text-sm font-medium text-primary-700 underline"
                      >
                        Ver ubicaciones
                      </button>
                    ) : null}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          {editable && lineaId ? (
            <div className="mb-4 flex flex-wrap items-end gap-3">
              <FormField label="Ubicación de origen" required help="Solo existencia ubicada y vendible">
                <select
                  value={ubicacion}
                  onChange={(e) => setUbicacion(e.target.value)}
                  className="h-10 w-80 rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900"
                >
                  <option value="">Seleccionar…</option>
                  {(candidatas.data?.items ?? []).map((c) => (
                    <option key={c.location_id} value={c.location_id}>
                      {corto(c.location_id)} — asignable {c.allocatable} de {c.on_hand}
                    </option>
                  ))}
                </select>
              </FormField>
              <FormField label="Cantidad" help="En unidad base">
                <TextInput value={cantidad} onChange={(e) => setCantidad(e.target.value)} />
              </FormField>
              <AsyncButton onClick={asignar}>Asignar desde la ubicación</AsyncButton>
            </div>
          ) : null}

          <h3 className="mb-2 text-sm font-semibold text-text-900">Recorrido</h3>
          {p.route.length === 0 ? (
            <p className="mb-4 text-sm text-text-500">Todavía no hay ninguna ubicación asignada.</p>
          ) : (
            <ol className="mb-4 text-sm text-text-700">
              {p.route.map((r) => (
                <li key={r.id}>
                  {r.sequence}. Ubicación {corto(r.location_id)} — {r.base_quantity}
                </li>
              ))}
            </ol>
          )}

          <div className="flex flex-wrap items-end gap-3">
            {editable ? (
              <AsyncButton
                onClick={() => accion("confirmar", "Plan confirmado")}
                disabled={!p.confirmable}
              >
                Confirmar plan
              </AsyncButton>
            ) : null}
            {p.status === "DRAFT" || p.status === "CONFIRMED" ? (
              <>
                <FormField label="Motivo" required help="Obligatorio para cancelar">
                  <TextInput value={motivo} onChange={(e) => setMotivo(e.target.value)} />
                </FormField>
                <AsyncButton
                  onClick={() => accion("cancelar", "Plan cancelado", { reason: motivo })}
                  variant="secondary"
                >
                  Cancelar plan
                </AsyncButton>
              </>
            ) : null}
          </div>
          {editable && !p.confirmable ? (
            <p className="mt-3 text-sm text-text-500" role="status">
              No se puede confirmar mientras falte cantidad por asignar. Si la mercancía todavía no
              está ubicada, el plan espera: el put-away la coloca y el recorrido se completa.
            </p>
          ) : null}
        </section>
      ) : null}
    </PageContent>
  );
}
