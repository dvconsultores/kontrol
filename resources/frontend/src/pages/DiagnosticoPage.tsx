/** Diagnóstico — estado de servicios e instalación (FR-001-084). */
import { useQuery } from "@tanstack/react-query";

import { apiFetch } from "@/api/client";
import type { HealthResponse } from "@/api/types";
import { ErrorState } from "@/components/ErrorState";
import { LoadingState } from "@/components/LoadingState";
import { PageContent } from "@/layout/PageContent";
import { PageHeader } from "@/components/PageHeader";

export function DiagnosticoPage(): React.JSX.Element {
  const query = useQuery({
    queryKey: ["diagnostics"],
    queryFn: () => apiFetch<HealthResponse>("/system/diagnostics"),
    retry: false,
  });

  return (
    <PageContent maxWidth="md">
      <PageHeader
        title="Diagnóstico"
        description="Estado de los servicios de esta instalación."
        crumbs={[{ label: "Diagnóstico" }]}
      />
      {query.isLoading ? <LoadingState rows={4} /> : null}
      {query.isError ? (
        <ErrorState message="No fue posible obtener el diagnóstico." onRetry={() => void query.refetch()} />
      ) : null}
      {query.data ? (
        <div className="rounded-lg border border-border-default bg-surface-0 p-6">
          <p className="text-xs font-medium uppercase tracking-wide text-text-400">Versión</p>
          <p className="mt-1 text-sm font-semibold text-text-900">{query.data.version}</p>
          <ul className="mt-4 space-y-2">
            {Object.entries(query.data.services).map(([name, status]) => (
              <li key={name} className="flex items-center justify-between border-b border-border-default py-2">
                <span className="text-sm text-text-700">{name}</span>
                <span
                  className={`rounded px-2 py-0.5 text-xs font-medium ${
                    status === "ok" ? "bg-success-100 text-success-600" : "bg-danger-100 text-danger-600"
                  }`}
                >
                  {status}
                </span>
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </PageContent>
  );
}
