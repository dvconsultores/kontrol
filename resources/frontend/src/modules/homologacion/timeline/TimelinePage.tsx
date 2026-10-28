/** Timeline de homologación y liberación (FR-011-020). */
import { useQuery } from "@tanstack/react-query";
import { createColumnHelper } from "@tanstack/react-table";

import { apiFetch } from "@/api/client";
import type { HomologationTimelineItem } from "@/api/types";
import { DataTable } from "@/components/DataTable";
import { ErrorState } from "@/components/ErrorState";
import { LoadingState } from "@/components/LoadingState";
import { PageContent } from "@/layout/PageContent";
import { PageHeader } from "@/components/PageHeader";
import { formatearInstante } from "@/lib/fecha-de-negocio";

const columnHelper = createColumnHelper<HomologationTimelineItem>();

const SOURCE_LABELS: Record<string, string> = {
  HOMOLOGATION: "Homologación",
  RELEASE: "Liberación",
};

export function TimelinePage(): React.JSX.Element {
  const timeline = useQuery({
    queryKey: ["homologacion", "timeline"],
    queryFn: () => apiFetch<{ items: HomologationTimelineItem[] }>("/homologation/timeline"),
    retry: false,
  });

  if (timeline.isLoading) {
    return <LoadingState rows={4} />;
  }
  if (timeline.isError) {
    return (
      <PageContent maxWidth="md">
        <ErrorState message="No fue posible cargar el timeline." onRetry={() => void timeline.refetch()} />
      </PageContent>
    );
  }

  const columns = [
    columnHelper.accessor("created_at", {
      header: "Fecha",
      cell: (info) => formatearInstante(info.getValue()),
    }),
    columnHelper.accessor("source", {
      header: "Tipo",
      cell: (info) => SOURCE_LABELS[info.getValue()] ?? info.getValue(),
    }),
    columnHelper.accessor("event_type", { header: "Evento" }),
    columnHelper.accessor("created_by", { header: "Usuario" }),
    columnHelper.accessor("detail", {
      header: "Detalle",
      cell: (info) => JSON.stringify(info.getValue() ?? {}),
    }),
  ];

  return (
    <PageContent maxWidth="full">
      <PageHeader
        title="Timeline de homologación y liberación"
        description="Registro inmutable (append-only) del proceso formal (integridad y trazabilidad)."
        crumbs={[{ label: "Homologación" }, { label: "Timeline" }]}
      />

      <DataTable
        columns={columns}
        data={timeline.data?.items ?? []}
        loading={false}
        error={null}
        getRowId={(row) => row.id}
        emptyTitle="Sin eventos"
        emptyDescription="Los eventos de homologación y liberación quedarán registrados aquí."
      />
    </PageContent>
  );
}
