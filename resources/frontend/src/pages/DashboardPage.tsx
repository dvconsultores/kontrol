/** Dashboard — inicio (WF-07). Indicadores y alertas por rol. */
import { useQuery } from "@tanstack/react-query";

import { apiFetch } from "@/api/client";
import type { HealthResponse } from "@/api/types";
import { useCompany } from "@/app/contexts/CompanyContext";
import { useLicense } from "@/app/contexts/LicenseContext";
import { PageContent } from "@/layout/PageContent";
import { PageHeader } from "@/components/PageHeader";

export function DashboardPage(): React.JSX.Element {
  const { activeCompany } = useCompany();
  const { mode } = useLicense();

  const health = useQuery({
    queryKey: ["health"],
    queryFn: () => apiFetch<HealthResponse>("/health/ready"),
    retry: false,
  });

  return (
    <PageContent maxWidth="full">
      <PageHeader
        title="Inicio"
        description="Resumen del estado de la instalación."
        crumbs={[{ label: "Inicio" }]}
      />

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <div className="rounded-lg border border-border-default bg-surface-0 p-4">
          <p className="text-xs font-medium uppercase tracking-wide text-text-400">Empresa activa</p>
          <p className="mt-1 truncate text-lg font-semibold text-text-900">
            {activeCompany?.legal_name ?? "—"}
          </p>
        </div>
        <div className="rounded-lg border border-border-default bg-surface-0 p-4">
          <p className="text-xs font-medium uppercase tracking-wide text-text-400">Modo de licencia</p>
          <p className="mt-1 text-lg font-semibold text-text-900">{mode?.replaceAll("_", " ") ?? "Pendiente"}</p>
        </div>
        <div className="rounded-lg border border-border-default bg-surface-0 p-4">
          <p className="text-xs font-medium uppercase tracking-wide text-text-400">API</p>
          <p className="mt-1 text-lg font-semibold text-text-900">
            {health.isSuccess ? health.data.status : health.isError ? "No disponible" : "Cargando…"}
          </p>
        </div>
        <div className="rounded-lg border border-border-default bg-surface-0 p-4">
          <p className="text-xs font-medium uppercase tracking-wide text-text-400">Versión</p>
          <p className="mt-1 text-lg font-semibold text-text-900">{health.data?.version ?? "—"}</p>
        </div>
      </div>
    </PageContent>
  );
}
