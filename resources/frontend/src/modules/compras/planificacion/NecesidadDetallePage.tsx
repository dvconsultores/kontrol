import { Link, useParams } from "react-router";
import { useQuery } from "@tanstack/react-query";
import { createColumnHelper } from "@tanstack/react-table";

import { apiFetch } from "@/api/client";
import { Autorizado } from "@/components/Autorizado";
import { Button } from "@/components/Button";
import { DataTable } from "@/components/DataTable";
import { PageHeader } from "@/components/PageHeader";
import { PageContent } from "@/layout/PageContent";

type Need = {
  id: string;
  status: "ACTIVE" | "RESOLVED";
  trigger_method: string;
  triggered_at: string | null;
  resolved_at: string | null;
  resolution_reason: string | null;
  last_evaluated_at: string | null;
  product: { id: string; code: string; name: string };
  warehouse: { id: string; code: string; name: string };
  trigger: {
    policy_id: string | null;
    policy_code: string | null;
    policy_version: number | null;
    available: string | null;
    on_hand: string | null;
    reserved: string | null;
    reorder_point: string | null;
    projected_demand: string | null;
    avg_daily_demand: string | null;
    safety_stock: string | null;
    recommended_quantity: string | null;
    rotation_band_code: string | null;
    calculated_at: string | null;
  };
  current: {
    policy_version: number | null;
    available: string | null;
    reorder_point: string | null;
    projected_demand: string | null;
    recommended_quantity: string | null;
    rotation_band_code: string | null;
  };
  alert_id: string | null;
  trigger_snapshot: Record<string, unknown> | null;
  requisitions: Array<{
    requisition_id: string;
    requisition_code: string;
    requisition_status: string;
    line_id: string;
    requested_base_quantity: string;
    calculated_at: string | null;
  }>;
};

const columnHelper = createColumnHelper<Need["requisitions"][number]>();

function formatear(valor: string | null | undefined): string {
  if (valor === null || valor === undefined) return "—";
  return valor;
}

const ETIQUETAS_RESOLUCION: Record<string, string> = {
  CONDITION_CLEARED: "La condición dejó de cumplirse",
  PLAN_UNAVAILABLE: "La planificación ya no está disponible",
  POLICY_DISABLED: "Se apagó la detección automática",
  PRODUCT_INACTIVE: "Producto inactivo",
  WAREHOUSE_INACTIVE: "Almacén inactivo",
};

export function NecesidadDetallePage(): React.JSX.Element {
  const { needId } = useParams<{ needId: string }>();

  const detalleQuery = useQuery({
    queryKey: ["planificacion", "necesidad", needId],
    queryFn: () => apiFetch<Need>(`/planning/replenishment-needs/${needId}`),
    retry: false,
  });

  const need = detalleQuery.data;

  const columns = [
    columnHelper.accessor("requisition_code", {
      header: "Requisición",
      cell: ({ row }) => (
        <Link to={`/compras/requisiciones/${row.original.requisition_id}`}>
          {row.original.requisition_code}
        </Link>
      ),
    }),
    columnHelper.accessor("requisition_status", { header: "Estado" }),
    columnHelper.accessor("requested_base_quantity", { header: "Cantidad" }),
  ];

  if (detalleQuery.isLoading) {
    return (
      <PageContent maxWidth="lg">
        <div role="status">Cargando necesidad…</div>
      </PageContent>
    );
  }

  if (detalleQuery.isError || !need) {
    return (
      <PageContent maxWidth="lg">
        <div role="alert">No fue posible cargar la necesidad.</div>
      </PageContent>
    );
  }

  return (
    <PageContent maxWidth="lg">
      <PageHeader
        title={`${need.product.code} · ${need.product.name}`}
        crumbs={[
          { label: "Compras", to: "/compras" },
          { label: "Necesidades de reposición", to: "/compras/planificacion/necesidades" },
          { label: need.product.code },
        ]}
      />
      <p className="mb-6 text-sm">{need.warehouse.name}</p>

      <section className="rounded-lg border border-border-default bg-surface-0 p-6">
        {need.status === "ACTIVE" ? (
          <p>Necesita reposición</p>
        ) : (
          <p>
            Resuelta: {ETIQUETAS_RESOLUCION[need.resolution_reason ?? ""] ?? need.resolution_reason ?? "—"}
            {need.resolved_at ? ` · ${formatear(need.resolved_at)}` : ""}
          </p>
        )}
      </section>

      <section className="mt-6 rounded-lg border border-border-default bg-surface-0 p-6">
        <h2 className="mb-4 text-lg font-semibold">Por qué se generó</h2>
        <p>
          Se generó porque el disponible ({formatear(need.trigger.available)}) era menor o igual
          que el punto de reorden ({formatear(need.trigger.reorder_point)}), con la política{" "}
          {need.trigger.policy_code} v{need.trigger.policy_version}.
        </p>
        <dl className="mt-4 grid gap-2 text-sm md:grid-cols-2">
          <div>
            <dt className="font-medium">Demanda media diaria</dt>
            <dd>{formatear(need.trigger.avg_daily_demand)}</dd>
          </div>
          <div>
            <dt className="font-medium">Proyección</dt>
            <dd>{formatear(need.trigger.projected_demand)}</dd>
          </div>
          <div>
            <dt className="font-medium">Stock de seguridad</dt>
            <dd>{formatear(need.trigger.safety_stock)}</dd>
          </div>
          <div>
            <dt className="font-medium">Existencia</dt>
            <dd>{formatear(need.trigger.on_hand)}</dd>
          </div>
          <div>
            <dt className="font-medium">Reservado</dt>
            <dd>{formatear(need.trigger.reserved)}</dd>
          </div>
          <div>
            <dt className="font-medium">Disponible</dt>
            <dd>{formatear(need.trigger.available)}</dd>
          </div>
          <div>
            <dt className="font-medium">Punto de reorden</dt>
            <dd>{formatear(need.trigger.reorder_point)}</dd>
          </div>
          <div>
            <dt className="font-medium">Rotación</dt>
            <dd>{need.trigger.rotation_band_code ?? "Sin banda"}</dd>
          </div>
          <div>
            <dt className="font-medium">Cantidad sugerida</dt>
            <dd>{formatear(need.trigger.recommended_quantity)}</dd>
          </div>
        </dl>
      </section>

      <section className="mt-6 rounded-lg border border-border-default bg-surface-0 p-6">
        <h2 className="mb-4 text-lg font-semibold">Situación actual</h2>
        <dl className="grid gap-2 text-sm md:grid-cols-2">
          <div>
            <dt className="font-medium">Disponible</dt>
            <dd>{formatear(need.current.available)}</dd>
          </div>
          <div>
            <dt className="font-medium">Punto de reorden</dt>
            <dd>{formatear(need.current.reorder_point)}</dd>
          </div>
          <div>
            <dt className="font-medium">Proyección</dt>
            <dd>{formatear(need.current.projected_demand)}</dd>
          </div>
          <div>
            <dt className="font-medium">Cantidad sugerida</dt>
            <dd>{formatear(need.current.recommended_quantity)}</dd>
          </div>
          <div>
            <dt className="font-medium">Rotación</dt>
            <dd>{need.current.rotation_band_code ?? "Sin banda"}</dd>
          </div>
          <div>
            <dt className="font-medium">Última evaluación</dt>
            <dd>{formatear(need.last_evaluated_at)}</dd>
          </div>
        </dl>
      </section>

      <section className="mt-6 rounded-lg border border-border-default bg-surface-0 p-6">
        <h2 className="mb-4 text-lg font-semibold">Requisiciones creadas desde esta necesidad</h2>
        <DataTable
          columns={columns}
          data={need.requisitions}
          loading={false}
          error={null}
          getRowId={(row) => row.requisition_id}
          emptyTitle="Sin requisiciones"
          emptyDescription="Todavía no hay requisiciones."
        />
        <p className="mt-4 text-sm">
          Crear una requisición no resuelve la necesidad: se resuelve cuando cambia la situación
          del inventario.
        </p>
      </section>

      {need.status === "ACTIVE" ? (
        <div className="mt-6 flex justify-end">
          <Autorizado operacion={["POST", "/purchasing/requisitions"]}>
            <Link to={`/compras/requisiciones/nueva?necesidad=${need.id}`}>
              <Button>Crear requisición</Button>
            </Link>
          </Autorizado>
        </div>
      ) : null}
    </PageContent>
  );
}
