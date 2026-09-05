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
import { PICK_DISCREPANCY_KINDS } from "@/api/types";
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
  const [parada, setParada] = useState<string | null>(null);
  const [recogido, setRecogido] = useState("");
  const [diferencia, setDiferencia] = useState("");
  const [nota, setNota] = useState("");
  const [area, setArea] = useState("");

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
    // `preparacion` devuelve lo mismo que el detalle más lo recogido: sirve para
    // las dos fases y evita que la pantalla tenga dos verdades del mismo plan.
    queryFn: () => apiFetch<PickingPlan>(`/sales/picking/${planId}/preparacion`),
    enabled: Boolean(planId),
  });

  const ubicaciones = useQuery({
    queryKey: ["picking", "ubicaciones", plan.data?.warehouse_id],
    queryFn: () =>
      apiFetch<{ items: { id: string; code: string; name: string | null }[] }>(
        `/inventory/putaway/ubicaciones?warehouse_id=${plan.data?.warehouse_id}`,
      ),
    enabled: Boolean(plan.data?.warehouse_id),
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

  async function recogerParada(): Promise<void> {
    if (!planId || !parada) return;
    try {
      await apiFetch(`/sales/picking/${planId}/recoger`, {
        method: "POST",
        body: {
          line_id: parada,
          quantity: recogido || "0",
          discrepancy_kind: diferencia || null,
          discrepancy_note: nota || null,
        },
      });
      notify({ type: "success", title: "Recogida registrada" });
      setParada(null);
      await refrescar();
    } catch (e) {
      fallo("No se pudo registrar la recogida")(e);
    }
  }

  async function consolidar(): Promise<void> {
    if (!planId || !area) {
      notify({ type: "error", title: "Elija el Área de Confirmación" });
      return;
    }
    try {
      await apiFetch(`/sales/picking/${planId}/consolidar`, {
        method: "POST",
        body: { location_id: area },
      });
      notify({ type: "success", title: "Pedido consolidado y trasladado" });
      await refrescar();
    } catch (e) {
      fallo("No se pudo consolidar")(e);
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
          {p.status === "CONFIRMED" && p.picking ? (
            <section className="mt-4 border-t border-border-default pt-4">
              <h3 className="mb-2 text-sm font-semibold text-text-900">Recorrido de preparación</h3>
              <p className="mb-3 text-sm text-text-700">
                Registre lo que encuentra en cada parada. Recoger menos de lo planificado exige
                indicar el motivo; la diferencia queda registrada y libera la parte no encontrada.
              </p>
              <table className="mb-3 w-full text-sm">
                <caption className="sr-only">Paradas del recorrido</caption>
                <thead>
                  <tr className="border-b border-border-default text-left text-text-700">
                    <th scope="col" className="py-1">#</th>
                    <th scope="col">Ubicación</th>
                    <th scope="col">Planificado</th>
                    <th scope="col">Recogido</th>
                    <th scope="col">Motivo</th>
                    <th scope="col">Acción</th>
                  </tr>
                </thead>
                <tbody>
                  {p.picking.map((s) => (
                    <tr key={s.id} className="border-b border-border-subtle">
                      <td className="py-1">{s.sequence}</td>
                      <td className="font-mono text-xs">{corto(s.location_id)}</td>
                      <td>{s.planned_base_quantity}</td>
                      <td>{s.picked_base_quantity ?? <span className="text-text-500">—</span>}</td>
                      <td className="text-xs">{s.discrepancy_kind ?? ""}</td>
                      <td>
                        {s.picked_at ? (
                          <span className="text-text-500">Registrada</span>
                        ) : (
                          <button
                            type="button"
                            onClick={() => {
                              setParada(s.id);
                              setRecogido(s.planned_base_quantity);
                              setDiferencia("");
                              setNota("");
                            }}
                            className="text-sm font-medium text-primary-700 underline"
                          >
                            Registrar recogida
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>

              {parada ? (
                <div className="mb-3 flex flex-wrap items-end gap-3">
                  <FormField label="Cantidad recogida" help="En unidad base">
                    <TextInput value={recogido} onChange={(e) => setRecogido(e.target.value)} />
                  </FormField>
                  <FormField label="Motivo de la diferencia" help="Solo si recoge de menos">
                    <select
                      value={diferencia}
                      onChange={(e) => setDiferencia(e.target.value)}
                      className="h-10 w-72 rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900"
                    >
                      <option value="">Sin diferencia</option>
                      {PICK_DISCREPANCY_KINDS.map((k) => (
                        <option key={k} value={k}>
                          {k.replaceAll("_", " ").toLowerCase()}
                        </option>
                      ))}
                    </select>
                  </FormField>
                  <FormField label="Observación">
                    <TextInput value={nota} onChange={(e) => setNota(e.target.value)} />
                  </FormField>
                  <AsyncButton onClick={recogerParada}>Confirmar recogida</AsyncButton>
                </div>
              ) : null}

              <div className="flex flex-wrap items-end gap-3">
                <FormField label="Área de Confirmación" required help="Ubicación del mismo almacén">
                  <select
                    value={area}
                    onChange={(e) => setArea(e.target.value)}
                    className="h-10 w-72 rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900"
                  >
                    <option value="">Seleccionar…</option>
                    {(ubicaciones.data?.items ?? []).map((l) => (
                      <option key={l.id} value={l.id}>
                        {l.code}
                        {l.name ? ` · ${l.name}` : ""}
                      </option>
                    ))}
                  </select>
                </FormField>
                <AsyncButton onClick={consolidar} disabled={!p.route_complete}>
                  Consolidar y trasladar
                </AsyncButton>
              </div>
              {!p.route_complete ? (
                <p className="mt-3 text-sm text-text-500" role="status">
                  Falta registrar alguna parada. El pedido se consolida cuando se ha recorrido el
                  almacén entero, no antes.
                </p>
              ) : null}
            </section>
          ) : null}

          {p.status === "CLOSED" ? (
            <p className="mt-4 text-sm text-text-700" role="status">
              Pedido preparado y trasladado al Área de Confirmación. Queda pendiente del control
              independiente, que no se hace desde aquí.
            </p>
          ) : null}

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
