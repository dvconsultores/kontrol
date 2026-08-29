/** Dashboard — inicio (WF-07). Indicadores por módulo y vencimientos (FR-009-001/002). */
import { useQuery } from "@tanstack/react-query";

import { apiFetch } from "@/api/client";
import type { DashboardResult, HealthResponse } from "@/api/types";
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
  const dash = useQuery({
    queryKey: ["reporting", "dashboard"],
    queryFn: () => apiFetch<DashboardResult>("/reporting/dashboard"),
    retry: false,
  });

  const ind = dash.data?.indicators;
  const ven = dash.data?.vencimientos;

  const indicatorCard = (label: string, value: string): React.JSX.Element => (
    <div className="rounded-lg border border-border-default bg-surface-0 p-4">
      <p className="text-xs font-medium uppercase tracking-wide text-text-500">{label}</p>
      <p className="mt-1 truncate text-lg font-semibold text-text-900">{value}</p>
    </div>
  );

  return (
    <PageContent maxWidth="full">
      <PageHeader
        title="Inicio"
        description="Resumen del estado de la instalación y de los módulos."
        crumbs={[{ label: "Inicio" }]}
      />

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {indicatorCard("Empresa activa", activeCompany?.legal_name ?? "—")}
        {indicatorCard("Modo de licencia", mode?.replaceAll("_", " ") ?? "Pendiente")}
        {indicatorCard("API", health.isSuccess ? health.data.status : health.isError ? "No disponible" : "Cargando…")}
        {indicatorCard("Versión", health.data?.version ?? "—")}
      </div>

      <h2 className="mt-6 mb-2 text-base font-semibold text-text-900">Indicadores</h2>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {indicatorCard("Ventas", ind ? ind.ventas.toFixed(2) : "—")}
        {indicatorCard("Compras", ind ? ind.compras.toFixed(2) : "—")}
        {indicatorCard("Tesorería (banco)", ind ? ind.tesoreria_banco.toFixed(2) : "—")}
        {indicatorCard("CxC", ind ? ind.cxc.toFixed(2) : "—")}
        {indicatorCard("CxP", ind ? ind.cxp.toFixed(2) : "—")}
        {indicatorCard("Documentos fiscales", ind ? String(ind.documentos_fiscales) : "—")}
        {indicatorCard("Despachos bloqueados", ind ? String(ind.despachos_bloqueados) : "—")}
      </div>

      <h2 className="mt-6 mb-2 text-base font-semibold text-text-900">Vencimientos y alertas</h2>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {indicatorCard("Open items vencidos", ven ? String(ven.open_items_vencidos) : "—")}
        {indicatorCard("Períodos fiscales abiertos", ven ? String(ven.periodos_fiscales_abiertos) : "—")}
        {indicatorCard("Permisos activos", ven ? String(ven.permisos_activos) : "—")}
      </div>
    </PageContent>
  );
}
