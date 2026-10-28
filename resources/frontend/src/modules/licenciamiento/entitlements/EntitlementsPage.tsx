/** Entitlements por módulo — matriz vigente sincronizada (FR-010-010/011/012). */
import { useQuery } from "@tanstack/react-query";
import { createColumnHelper } from "@tanstack/react-table";

import { apiFetch } from "@/api/client";
import type { EntitlementSnapshotSummary, EntitlementsResult } from "@/api/types";
import { DataTable } from "@/components/DataTable";
import { ErrorState } from "@/components/ErrorState";
import { LoadingState } from "@/components/LoadingState";
import { PageContent } from "@/layout/PageContent";
import { PageHeader } from "@/components/PageHeader";
import { formatearInstante } from "@/lib/fecha-de-negocio";

const MODULE_LABELS: Record<string, string> = {
  ventas: "Ventas",
  compras: "Compras",
  inventario: "Inventario",
  tesoreria: "Tesorería",
  fiscal: "Fiscal",
  regulatorio: "Regulatorio",
  reportes: "Reportes",
};

interface MatrixRow {
  module: string;
  label: string;
  enabled: boolean;
}

const columnHelper = createColumnHelper<MatrixRow>();
const snapshotHelper = createColumnHelper<EntitlementSnapshotSummary>();

export function EntitlementsPage(): React.JSX.Element {
  const entitlements = useQuery({
    queryKey: ["licensing", "entitlements"],
    queryFn: () => apiFetch<EntitlementsResult>("/licensing/entitlements"),
    retry: false,
  });
  const snapshots = useQuery({
    queryKey: ["licensing", "snapshots"],
    queryFn: () => apiFetch<{ items: EntitlementSnapshotSummary[] }>("/licensing/entitlement-snapshots"),
    retry: false,
  });

  if (entitlements.isLoading) {
    return <LoadingState rows={4} />;
  }
  if (entitlements.isError) {
    return (
      <PageContent maxWidth="md">
        <ErrorState message="No fue posible cargar los entitlements." onRetry={() => void entitlements.refetch()} />
      </PageContent>
    );
  }

  const modules = entitlements.data?.modules ?? {};
  const rows: MatrixRow[] = Object.entries(modules).map(([module, enabled]) => ({
    module,
    label: MODULE_LABELS[module] ?? module,
    enabled: Boolean(enabled),
  }));

  const columns = [
    columnHelper.accessor("label", { header: "Módulo" }),
    columnHelper.accessor("module", { header: "Recurso" }),
    columnHelper.accessor("enabled", {
      header: "Entitlement",
      cell: (info) => (info.getValue() ? "Habilitado" : "Bloqueado"),
    }),
  ];

  const snapshotColumns = [
    snapshotHelper.accessor("version", { header: "Versión" }),
    snapshotHelper.accessor("taken_at", {
      header: "Tomado",
      cell: (info) => formatearInstante(info.getValue()),
    }),
    snapshotHelper.accessor("modules", {
      header: "Módulos",
      cell: (info) => Object.entries(info.getValue()).filter(([, v]) => v).length,
    }),
  ];

  return (
    <PageContent maxWidth="full">
      <PageHeader
        title="Entitlements por módulo"
        description="Matriz de módulos habilitados por la licencia (denegación por defecto en backend)."
        crumbs={[{ label: "Licenciamiento" }, { label: "Entitlements" }]}
      />

      <div className="rounded-lg border border-border-default bg-surface-0 p-6">
        <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
          <h2 className="text-base font-semibold text-text-900">Matriz vigente</h2>
          <p className="text-sm text-text-500">
            Versión: {entitlements.data?.version ?? "local"}
          </p>
        </div>
        <DataTable
          columns={columns}
          data={rows}
          loading={false}
          error={null}
          getRowId={(row) => row.module}
          emptyTitle="Sin entitlements"
          emptyDescription="Sincronice la licencia para cargar la matriz."
        />
      </div>

      <section className="mt-6 rounded-lg border border-border-default bg-surface-0 p-6">
        <h2 className="text-base font-semibold text-text-900">Snapshots de sincronización</h2>
        <p className="mt-1 text-sm text-text-500">Cada sincronización guarda un snapshot versionado de la matriz.</p>
        <div className="mt-4">
          <DataTable
            columns={snapshotColumns}
            data={snapshots.data?.items ?? []}
            loading={snapshots.isLoading}
            error={snapshots.isError ? "No fue posible cargar los snapshots." : null}
            getRowId={(row) => row.id}
            emptyTitle="Sin snapshots"
            emptyDescription="Los snapshots quedarán registrados al sincronizar."
          />
        </div>
      </section>
    </PageContent>
  );
}
