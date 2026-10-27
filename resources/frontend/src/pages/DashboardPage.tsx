/** Dashboard — inicio (WF-07). Indicadores por módulo y vencimientos (FR-009-001/002). */
import { useQuery } from "@tanstack/react-query";

import { apiFetch } from "@/api/client";
import type { DashboardResult, DiagnosticsResponse, HealthResponse } from "@/api/types";
import { useAutoridad } from "@/app/autoridad/AutoridadContext";
import { useCompany } from "@/app/contexts/CompanyContext";
import { useLicense } from "@/app/contexts/LicenseContext";
import { PageContent } from "@/layout/PageContent";
import { PageHeader } from "@/components/PageHeader";

/** El permiso que gobierna leer la versión: el del diagnóstico, que es quien la publica (FR-001-084). */
export const PERMISO_DE_VERSION = "license:view";
/** Lo que se muestra cuando el servidor no entrega una versión utilizable: un estado dicho, nunca un hueco ni un número inventado. */
export const VERSION_NO_DISPONIBLE = "No disponible";

/** La versión que se pinta, a partir de lo que responde el diagnóstico (PANEL-VERSION-VACIA, FR-001-084). */
export function versionMostrada(diagnostico: { version?: unknown } | undefined): string {
  const version = diagnostico?.version;
  return typeof version === "string" && version.trim() !== "" ? version : VERSION_NO_DISPONIBLE;
}

export function DashboardPage(): React.JSX.Element {
  const { activeCompany } = useCompany();
  const { mode } = useLicense();
  const { tiene } = useAutoridad();
  const puedeVerVersion = tiene(PERMISO_DE_VERSION, "global");

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
  // La versión la publica el diagnóstico (con sesión y `license:view`), no el health: se pide solo a quien
  // puede verla y la tarjeta no existe para los demás, como el enlace a «Mi licencia» (FR-001-042).
  const diagnostico = useQuery({
    queryKey: ["diagnostics"],
    queryFn: () => apiFetch<DiagnosticsResponse>("/system/diagnostics"),
    enabled: puedeVerVersion,
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
        {puedeVerVersion
          ? indicatorCard(
              "Versión",
              diagnostico.isSuccess ? versionMostrada(diagnostico.data) : diagnostico.isError ? VERSION_NO_DISPONIBLE : "Cargando…",
            )
          : null}
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
