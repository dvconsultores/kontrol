import { useState } from "react";
import { Link } from "react-router";
import { useQuery } from "@tanstack/react-query";
import { createColumnHelper } from "@tanstack/react-table";

import { apiFetch } from "@/api/client";
import { useCompany } from "@/app/contexts/CompanyContext";
import { Button } from "@/components/Button";
import { DataTable } from "@/components/DataTable";
import { FormField } from "@/components/FormField";
import { PageHeader } from "@/components/PageHeader";
import { TextInput } from "@/components/TextInput";
import { PageContent } from "@/layout/PageContent";
import { AvisoDeAlmacenes } from "@/modules/organizacion/almacenes/AvisoDeAlmacenes";
import { useAlmacenesDeEmpresa } from "@/modules/organizacion/almacenes/useAlmacenesDeEmpresa";

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
};

const columnHelper = createColumnHelper<Need>();

function formatear(valor: string | null | undefined): string {
  if (valor === null || valor === undefined) return "—";
  return valor;
}

export function NecesidadesPage(): React.JSX.Element {
  const { activeCompany } = useCompany();
  const [estado, setEstado] = useState("ACTIVE");
  const [almacen, setAlmacen] = useState("");
  const [q, setQ] = useState("");

  const almacenesQuery = useAlmacenesDeEmpresa(activeCompany?.id ?? null);

  const necesidadesQuery = useQuery({
    queryKey: ["planificacion", "necesidades", estado, almacen, q],
    queryFn: () => {
      const params = new URLSearchParams();
      if (estado) params.set("status", estado);
      if (almacen) params.set("warehouse_id", almacen);
      if (q.trim()) params.set("q", q.trim());
      return apiFetch<{ items: Need[]; total: number; page: number; page_size: number }>(
        `/planning/replenishment-needs?${params.toString()}`,
      );
    },
  });

  const columns = [
    columnHelper.display({
      id: "producto",
      header: "Producto",
      cell: ({ row }) => `${row.original.product.code} · ${row.original.product.name}`,
    }),
    columnHelper.accessor("warehouse", {
      header: "Almacén",
      cell: (info) => info.getValue().code,
    }),
    columnHelper.display({
      id: "estado",
      header: "Estado",
      cell: ({ row }) => (row.original.status === "ACTIVE" ? "Necesita reposición" : "Resuelta"),
    }),
    columnHelper.display({
      id: "disponible",
      header: "Disponible",
      cell: ({ row }) => formatear(row.original.current.available),
    }),
    columnHelper.display({
      id: "reorder",
      header: "Punto de reorden",
      cell: ({ row }) => formatear(row.original.current.reorder_point),
    }),
    columnHelper.display({
      id: "proyeccion",
      header: "Proyección",
      cell: ({ row }) => formatear(row.original.current.projected_demand),
    }),
    columnHelper.display({
      id: "rotacion",
      header: "Rotación",
      cell: ({ row }) => row.original.current.rotation_band_code ?? "Sin banda",
    }),
    columnHelper.display({
      id: "sugerido",
      header: "Sugerido",
      cell: ({ row }) => formatear(row.original.current.recommended_quantity),
    }),
    columnHelper.accessor("triggered_at", {
      header: "Detectada",
      cell: (info) => formatear(info.getValue()),
    }),
    columnHelper.accessor("last_evaluated_at", {
      header: "Última evaluación",
      cell: (info) => formatear(info.getValue()),
    }),
    columnHelper.display({
      id: "ver",
      header: "Ver",
      cell: ({ row }) => (
        <Link to={`/compras/planificacion/necesidades/${row.original.id}`}>
          <Button variant="secondary" size="sm">
            Ver
          </Button>
        </Link>
      ),
    }),
  ];

  return (
    <PageContent maxWidth="full">
      <PageHeader
        title="Necesidades de reposición"
        crumbs={[
          { label: "Compras", to: "/compras" },
          { label: "Necesidades de reposición" },
        ]}
        description="Detección automática. La decisión de comprar es tuya: el sistema no crea requisiciones ni órdenes de compra."
      />
      <div className="grid gap-4 md:grid-cols-3">
        <FormField label="Estado">
          <select value={estado} onChange={(e) => setEstado(e.target.value)}>
            <option value="ACTIVE">Activas</option>
            <option value="RESOLVED">Resueltas</option>
            <option value="">Todas</option>
          </select>
        </FormField>
        <FormField label="Almacén">
          <select value={almacen} onChange={(e) => setAlmacen(e.target.value)}>
            <option value="">Todos</option>
            {(almacenesQuery.data?.items ?? []).map((a) => (
              <option key={a.id} value={a.id}>
                {a.code} - {a.name}
              </option>
            ))}
          </select>
        </FormField>
        <FormField label="Buscar producto">
          <TextInput value={q} onChange={(e) => setQ(e.target.value)} />
        </FormField>
      </div>
      <AvisoDeAlmacenes consulta={almacenesQuery} />
      <DataTable
        columns={columns}
        data={necesidadesQuery.data?.items ?? []}
        loading={necesidadesQuery.isLoading}
        error={necesidadesQuery.isError ? "No fue posible cargar las necesidades." : null}
        getRowId={(row) => row.id}
        emptyTitle="Sin necesidades"
        emptyDescription="La detección automática se activa en Maestros → Planificación de abastecimiento."
      />
    </PageContent>
  );
}
