/** Eventos de licencia — historial inmutable (FR-010-032). */
import { useQuery } from "@tanstack/react-query";
import { createColumnHelper } from "@tanstack/react-table";

import { apiFetch } from "@/api/client";
import type { LicenseEventItem } from "@/api/types";
import { DataTable } from "@/components/DataTable";
import { ErrorState } from "@/components/ErrorState";
import { LoadingState } from "@/components/LoadingState";
import { PageContent } from "@/layout/PageContent";
import { PageHeader } from "@/components/PageHeader";

const columnHelper = createColumnHelper<LicenseEventItem>();

export function EventosPage(): React.JSX.Element {
  const events = useQuery({
    queryKey: ["licensing", "events"],
    queryFn: () => apiFetch<LicenseEventItem[]>("/license/history"),
    retry: false,
  });

  if (events.isLoading) {
    return <LoadingState rows={4} />;
  }
  if (events.isError) {
    return (
      <PageContent maxWidth="md">
        <ErrorState message="No fue posible cargar los eventos de licencia." onRetry={() => void events.refetch()} />
      </PageContent>
    );
  }

  const columns = [
    columnHelper.accessor("created_at", {
      header: "Fecha",
      cell: (info) => new Date(info.getValue()).toLocaleString("es-VE"),
    }),
    columnHelper.accessor("event_type", { header: "Evento" }),
    columnHelper.accessor("source", { header: "Origen" }),
    columnHelper.accessor("detail", {
      header: "Detalle",
      cell: (info) => JSON.stringify(info.getValue() ?? {}),
    }),
  ];

  return (
    <PageContent maxWidth="full">
      <PageHeader
        title="Eventos de licencia"
        description="Activación, sincronización, renovación y cambios de modo (historial inmutable)."
        crumbs={[{ label: "Licenciamiento" }, { label: "Eventos" }]}
      />

      <DataTable
        columns={columns}
        data={events.data ?? []}
        loading={false}
        error={null}
        getRowId={(row) => row.id}
        emptyTitle="Sin eventos"
        emptyDescription="Los eventos de licencia quedarán registrados aquí."
      />
    </PageContent>
  );
}
