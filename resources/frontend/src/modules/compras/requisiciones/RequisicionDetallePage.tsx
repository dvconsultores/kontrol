import { useEffect, useState } from "react";
import { Link, useParams, useSearchParams } from "react-router";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { createColumnHelper } from "@tanstack/react-table";

import { ApiError, apiFetch } from "@/api/client";
import { useAutoridad } from "@/app/autoridad/AutoridadContext";
import { useNotifications } from "@/app/contexts/NotificationContext";
import { AsyncButton } from "@/components/AsyncButton";
import { DataTable } from "@/components/DataTable";
import { FormField } from "@/components/FormField";
import { PageHeader } from "@/components/PageHeader";
import { TextInput } from "@/components/TextInput";
import { PageContent } from "@/layout/PageContent";
import { SelectorDeArticulo } from "@/modules/maestros/catalogo/SelectorDeArticulo";

type Linea = {
  id: string;
  product_id: string;
  product_code: string;
  product_name: string;
  quantity: string;
  unit_id: string;
  notes: string | null;
  plan: Snapshot | null;
};

type Snapshot = {
  status: string;
  policy_code: string | null;
  policy_version: number | null;
  recommended_quantity: string | null;
  requested_base_quantity: string;
  difference: string | null;
  accepted_recommendation: boolean;
  calculated_at: string | null;
  replenishment_need_id: string | null;
};

type DetalleRequisicion = {
  id: string;
  code: string;
  status: string;
  warehouse_id: string | null;
  warehouse_code: string | null;
  need_date: string | null;
  lines: Linea[];
};

type Plan = {
  status: "OK" | "PLAN_NOT_CONFIGURED" | "INSUFFICIENT_HISTORY";
  policy: { id: string; code: string; version: number } | null;
  demand_source: string | null;
  window_start: string | null;
  window_end: string | null;
  lookback_days: number | null;
  horizon_days: number | null;
  lead_time_days: number | null;
  history_partial: boolean | null;
  observed_history_days: number | null;
  net_demand: string | null;
  avg_daily_demand: string | null;
  projected_demand: string | null;
  safety_stock: string | null;
  reorder_point: string | null;
  on_hand: string | null;
  reserved: string | null;
  available: string | null;
  open_supply_available: boolean;
  open_supply?: string | null;
  rotation_metric: string | null;
  demand_velocity: string | null;
  turnover: string | null;
  rotation_band: { id: string; code: string; name: string } | null;
  coverage_days: string | number | null;
  recommended_quantity: string | null;
  product_code: string;
  product_name: string;
  warehouse_code: string;
};

type Need = {
  id: string;
  product: { id: string; code: string; name: string };
  warehouse: { id: string; code: string; name: string };
  trigger: { recommended_quantity: string | null };
  current: { recommended_quantity: string | null };
};

const columnHelper = createColumnHelper<Linea>();

function formatearNumero(valor: string | null | undefined): string {
  if (valor === null || valor === undefined) return "—";
  return valor;
}

export function RequisicionDetallePage(): React.JSX.Element {
  const { requisitionId } = useParams<{ requisitionId: string }>();
  const [searchParams] = useSearchParams();
  const necessityId = searchParams.get("necesidad");
  const queryClient = useQueryClient();
  const { notify } = useNotifications();
  const { puede } = useAutoridad();

  const [productoId, setProductoId] = useState("");
  const [cantidadManual, setCantidadManual] = useState("");

  const detalleQuery = useQuery({
    queryKey: ["compras", "requisicion", requisitionId],
    queryFn: () => apiFetch<DetalleRequisicion>(`/planning/requisitions/${requisitionId}`),
    retry: false,
  });

  const detalle = detalleQuery.data;
  const warehouseId = detalle?.warehouse_id ?? null;

  const necesidadQuery = useQuery({
    queryKey: ["planificacion", "necesidad", necessityId],
    queryFn: () => apiFetch<Need>(`/planning/replenishment-needs/${necessityId}`),
    enabled: Boolean(necessityId) && detalle?.status === "DRAFT" && Boolean(warehouseId),
    retry: false,
  });

  const need = necesidadQuery.data;

  useEffect(() => {
    if (need && detalle?.warehouse_id === need.warehouse.id) {
      if (!productoId) {
        setProductoId(need.product.id);
      }
      if (!cantidadManual) {
        setCantidadManual(need.current.recommended_quantity ?? need.trigger.recommended_quantity ?? "");
      }
    }
  }, [need, detalle?.warehouse_id, productoId, cantidadManual]);

  const planQuery = useQuery({
    queryKey: ["planificacion", "plan", warehouseId, productoId],
    queryFn: () =>
      apiFetch<Plan>(`/planning/plan?warehouse_id=${warehouseId}&product_id=${productoId}`),
    enabled: Boolean(warehouseId) && Boolean(productoId),
    retry: false,
  });

  const plan = planQuery.data;
  const puedeAgregarLineas = puede("POST", "/planning/requisitions/_/lines");
  const esDraft = detalle?.status === "DRAFT";
  const mostrarFormulario = esDraft && puedeAgregarLineas;

  const limpiarYRefrescar = async (): Promise<void> => {
    setProductoId("");
    setCantidadManual("");
    await queryClient.invalidateQueries({ queryKey: ["compras", "requisicion", requisitionId] });
  };

  const manejarErrorAgregado = async (err: unknown): Promise<void> => {
    if (err instanceof ApiError && err.code === "PLANNING_POLICY_STALE") {
      notify({ type: "error", title: "La política cambió", description: "Revisa la nueva sugerencia." });
      await queryClient.invalidateQueries({ queryKey: ["planificacion", "plan", warehouseId, productoId] });
      return;
    }
    notify({ type: "error", title: "No fue posible agregar la línea", description: err instanceof Error ? err.message : "Error desconocido." });
  };

  const usarSugerencia = async (): Promise<void> => {
    if (!productoId) return;
    try {
      await apiFetch(`/planning/requisitions/${requisitionId}/lines`, {
        method: "POST",
        body: {
          product_id: productoId,
          use_recommendation: true,
          expected_policy_version: plan?.policy?.version ?? null,
          ...(necessityId ? { replenishment_need_id: necessityId } : {}),
        },
      });
      notify({ type: "success", title: "Línea agregada" });
      await limpiarYRefrescar();
    } catch (err) {
      await manejarErrorAgregado(err);
    }
  };

  const agregarCantidadManual = async (): Promise<void> => {
    const cantidad = Number(cantidadManual);
    if (!cantidadManual.trim() || !Number.isFinite(cantidad) || cantidad <= 0) {
      notify({ type: "error", title: "Indica una cantidad mayor que cero" });
      return;
    }
    if (!productoId) return;
    try {
      await apiFetch(`/planning/requisitions/${requisitionId}/lines`, {
        method: "POST",
        body: {
          product_id: productoId,
          quantity: String(cantidad),
          use_recommendation: false,
          expected_policy_version: plan?.policy?.version ?? null,
          ...(necessityId ? { replenishment_need_id: necessityId } : {}),
        },
      });
      notify({ type: "success", title: "Línea agregada" });
      await limpiarYRefrescar();
    } catch (err) {
      await manejarErrorAgregado(err);
    }
  };

  const columns = [
    columnHelper.display({
      id: "producto",
      header: "Producto",
      cell: ({ row }) => `${row.original.product_code} · ${row.original.product_name}`,
    }),
    columnHelper.accessor("quantity", { header: "Cantidad (base)" }),
    columnHelper.display({
      id: "sugerida",
      header: "Sugerida",
      cell: ({ row }) => formatearNumero(row.original.plan?.recommended_quantity),
    }),
    columnHelper.display({
      id: "diferencia",
      header: "Diferencia",
      cell: ({ row }) => formatearNumero(row.original.plan?.difference),
    }),
    columnHelper.display({
      id: "origen",
      header: "Origen",
      cell: ({ row }) => (row.original.plan?.accepted_recommendation ? "Sugerencia aceptada" : "Cantidad manual"),
    }),
    columnHelper.display({
      id: "politica",
      header: "Política",
      cell: ({ row }) =>
        row.original.plan?.policy_code
          ? `${row.original.plan.policy_code} v${row.original.plan.policy_version ?? "?"}`
          : "Sin política",
    }),
    columnHelper.display({
      id: "necesidad",
      header: "Necesidad",
      cell: ({ row }) =>
        row.original.plan?.replenishment_need_id ? (
          <Link to={`/compras/planificacion/necesidades/${row.original.plan.replenishment_need_id}`}>
            Ver necesidad
          </Link>
        ) : (
          "—"
        ),
    }),
    columnHelper.display({
      id: "calculada",
      header: "Calculada",
      cell: ({ row }) => formatearNumero(row.original.plan?.calculated_at),
    }),
  ];

  const sugerenciaDeshabilitada =
    plan?.status !== "OK" || plan?.recommended_quantity === null || Number(plan.recommended_quantity) <= 0;

  const estadosCarga = detalleQuery.isLoading ? (
    <div role="status">Cargando requisición…</div>
  ) : null;
  const estadoError = detalleQuery.isError ? (
    <div role="alert">No fue posible cargar la requisición.</div>
  ) : null;

  return (
    <PageContent maxWidth="full">
      <PageHeader
        title={detalle ? `Requisición ${detalle.code}` : "Requisición"}
        crumbs={[
          { label: "Compras", to: "/compras" },
          { label: "Requisiciones", to: "/compras/requisiciones" },
          { label: detalle?.code ?? "…" },
        ]}
      />
      {estadosCarga}
      {estadoError}
      {detalle ? (
        <>
          <div className="mb-6 flex flex-wrap gap-4 text-sm">
            <span>Estado: {detalle.status}</span>
            <span>Almacén: {detalle.warehouse_code ?? "Sin almacén"}</span>
            <span>Necesidad: {detalle.need_date ?? "—"}</span>
          </div>

          {need && detalle.warehouse_id === need.warehouse.id ? (
            <div role="status" className="mb-4">
              Línea para la necesidad de reposición de {need.product.code}. Puedes cambiar la
              cantidad.
            </div>
          ) : null}

          <DataTable
            columns={columns}
            data={detalle.lines}
            loading={false}
            error={null}
            getRowId={(row) => row.id}
            emptyTitle="Sin líneas"
            emptyDescription="Aún no hay líneas en esta requisición."
          />

          {mostrarFormulario ? (
            detalle.warehouse_id ? (
              <section className="mt-8 rounded-lg border border-border-default bg-surface-0 p-6">
                <h2 className="mb-4 text-lg font-semibold">Agregar línea</h2>
                <FormField label="Producto" required>
                  <SelectorDeArticulo value={productoId} onChange={setProductoId} itemType="PRODUCT" />
                </FormField>

                {productoId ? (
                  planQuery.isLoading ? (
                    <div role="status">Cargando planificación…</div>
                  ) : planQuery.isError ? (
                    <div role="alert">No fue posible cargar la planificación.</div>
                  ) : plan ? (
                    <section aria-labelledby="panel-plan" className="mt-4">
                      <h3 id="panel-plan" className="font-medium">
                        Planificación del producto
                      </h3>
                      {plan.status === "PLAN_NOT_CONFIGURED" ? (
                        <div role="status" className="mt-2">
                          Sin política de planificación para este almacén: escribe la cantidad a mano.
                        </div>
                      ) : plan.status === "INSUFFICIENT_HISTORY" ? (
                        <div role="status" className="mt-2">
                          Sin historia suficiente del producto en este almacén: no hay sugerencia.
                        </div>
                      ) : (
                        <>
                          <dl className="mt-2 grid gap-2 text-sm md:grid-cols-2">
                            <div>
                              <dt className="font-medium">Política</dt>
                              <dd>
                                {plan.policy ? `${plan.policy.code} v${plan.policy.version}` : "—"}
                              </dd>
                            </div>
                            <div>
                              <dt className="font-medium">Ventana</dt>
                              <dd>
                                {plan.lookback_days !== null && plan.lookback_days !== undefined
                                  ? `${plan.lookback_days} días${plan.history_partial ? ` · historia parcial: ${plan.observed_history_days ?? "—"} días` : ""}`
                                  : "—"}
                              </dd>
                            </div>
                            <div>
                              <dt className="font-medium">Demanda neta</dt>
                              <dd>{formatearNumero(plan.net_demand)}</dd>
                            </div>
                            <div>
                              <dt className="font-medium">Media diaria</dt>
                              <dd>{formatearNumero(plan.avg_daily_demand)}</dd>
                            </div>
                            <div>
                              <dt className="font-medium">Proyección</dt>
                              <dd>
                                {plan.horizon_days !== null && plan.horizon_days !== undefined
                                  ? `${plan.horizon_days} días`
                                  : "—"}
                              </dd>
                            </div>
                            <div>
                              <dt className="font-medium">Stock de seguridad</dt>
                              <dd>{formatearNumero(plan.safety_stock)}</dd>
                            </div>
                            <div>
                              <dt className="font-medium">Punto de reorden</dt>
                              <dd>{formatearNumero(plan.reorder_point)}</dd>
                            </div>
                            <div>
                              <dt className="font-medium">Existencia</dt>
                              <dd>{formatearNumero(plan.on_hand)}</dd>
                            </div>
                            <div>
                              <dt className="font-medium">Reservado</dt>
                              <dd>{formatearNumero(plan.reserved)}</dd>
                            </div>
                            <div>
                              <dt className="font-medium">Disponible</dt>
                              <dd>{formatearNumero(plan.available)}</dd>
                            </div>
                            <div>
                              <dt className="font-medium">Cobertura</dt>
                              <dd>
                                {plan.coverage_days !== null && plan.coverage_days !== undefined
                                  ? `${plan.coverage_days} días`
                                  : "—"}
                              </dd>
                            </div>
                            <div>
                              <dt className="font-medium">Rotación</dt>
                              <dd>
                                {plan.rotation_band
                                  ? `${plan.rotation_band.name} (${plan.rotation_band.code})`
                                  : "Sin banda"}
                              </dd>
                            </div>
                            <div>
                              <dt className="font-medium">Velocidad</dt>
                              <dd>
                                {plan.demand_velocity !== null && plan.demand_velocity !== undefined
                                  ? `${plan.demand_velocity} / día`
                                  : "—"}
                              </dd>
                            </div>
                            <div>
                              <dt className="font-medium">Suministro abierto</dt>
                              <dd>{plan.open_supply_available ? formatearNumero(plan.open_supply) : "No disponible"}</dd>
                            </div>
                          </dl>
                          <div className="mt-3 font-semibold">
                            Cantidad sugerida: {formatearNumero(plan.recommended_quantity)}
                          </div>
                        </>
                      )}

                      <div className="mt-4">
                        <AsyncButton
                          variant="secondary"
                          disabled={sugerenciaDeshabilitada}
                          onClick={usarSugerencia}
                        >
                          Usar cantidad sugerida
                        </AsyncButton>
                      </div>

                      <div className="mt-4 grid gap-4 md:grid-cols-2">
                        <FormField label="Cantidad en unidad base">
                          <TextInput
                            type="number"
                            min={0}
                            value={cantidadManual}
                            onChange={(e) => setCantidadManual(e.target.value)}
                          />
                        </FormField>
                        <div className="flex items-end">
                          <AsyncButton onClick={agregarCantidadManual}>
                            Agregar con esta cantidad
                          </AsyncButton>
                        </div>
                      </div>
                    </section>
                  ) : null
                ) : null}
              </section>
            ) : (
              <div role="status" className="mt-6">
                Esta requisición no tiene almacén: no se puede planificar ni agregar líneas desde aquí.
              </div>
            )
          ) : null}
        </>
      ) : null}
    </PageContent>
  );
}
