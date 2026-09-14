/**
 * Alertas (Spec 047 · FR-047-010).
 *
 * Una alerta señala una condición; no es una tarea ni pide una acción formal.
 */
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

import { ApiError, apiFetch } from "@/api/client";
import { useAuth } from "@/app/contexts/AuthContext";
import { useCompany } from "@/app/contexts/CompanyContext";
import { EmptyState } from "@/components/EmptyState";
import { ErrorState } from "@/components/ErrorState";
import { ForbiddenState } from "@/components/ForbiddenState";
import { FormField } from "@/components/FormField";
import { LoadingState } from "@/components/LoadingState";
import { PageHeader } from "@/components/PageHeader";
import { Pagination } from "@/components/Pagination";
import { formatearFecha, t, tValor } from "@/i18n";
import { PageContent } from "@/layout/PageContent";

import { CONSULTAS, etiquetaCategoria, textoDeMensaje, type Alerta, type Pagina } from "../api";
import { EnlaceOrigen, EtiquetaSeveridad, SELECTOR } from "../componentes";

const ESTADOS = ["ACTIVE", "RESOLVED"] as const;

export function AlertasPage(): React.JSX.Element {
  const { activeCompanyId } = useCompany();
  const { hasPermission } = useAuth();
  const [estado, setEstado] = useState<(typeof ESTADOS)[number] | "">("ACTIVE");
  const [pagina, setPagina] = useState(0);
  const [tamano, setTamano] = useState(10);
  const permitido = hasPermission("alertas:view");

  const lista = useQuery({
    queryKey: [...CONSULTAS, "alertas", activeCompanyId, estado, pagina, tamano],
    queryFn: () =>
      apiFetch<Pagina<Alerta>>(
        `/alerts?page=${pagina + 1}&page_size=${tamano}${estado ? `&status=${estado}` : ""}`,
      ),
    enabled: Boolean(activeCompanyId) && permitido,
    retry: false,
  });

  if (!permitido || (lista.error instanceof ApiError && lista.error.status === 403)) {
    return <ForbiddenState />;
  }
  const items = lista.data?.items ?? [];

  return (
    <PageContent>
      <PageHeader title={t("alertas.titulo")} description={t("alertas.descripcion")} />
      <div className="mb-4 max-w-xs">
        <FormField label={t("comun.filtro_estado")}>
          <select
            value={estado}
            className={SELECTOR}
            onChange={(e) => {
              setEstado(e.target.value as (typeof ESTADOS)[number] | "");
              setPagina(0);
            }}
          >
            <option value="">{t("comun.todas")}</option>
            {ESTADOS.map((valor) => (
              <option key={valor} value={valor}>
                {tValor("alertas.estado", valor) ?? valor}
              </option>
            ))}
          </select>
        </FormField>
      </div>

      {lista.isLoading ? (
        <LoadingState label={t("comun.cargando")} />
      ) : lista.isError ? (
        <ErrorState message={t("comun.error_carga")} onRetry={() => void lista.refetch()} />
      ) : items.length === 0 ? (
        <EmptyState title={t("alertas.vacio")} />
      ) : (
        <ul aria-label={t("alertas.lista")} className="flex flex-col gap-2">
          {items.map((a) => (
            <li key={a.id} data-testid="alerta" className="rounded-lg border border-border-default bg-surface-0 p-3">
              <div className="mb-1 flex flex-wrap items-center gap-2 text-xs text-text-500">
                <EtiquetaSeveridad valor={a.severity} />
                <span>{etiquetaCategoria(a.category)}</span>
                <span>{formatearFecha(a.created_at)}</span>
                <span className="font-medium text-text-700">{tValor("alertas.estado", a.status) ?? a.status}</span>
                {a.resolved_at ? <span>{t("alertas.resuelta_el", { fecha: formatearFecha(a.resolved_at) })}</span> : null}
              </div>
              <p className="mb-2 text-sm text-text-900">{textoDeMensaje(a.message)}</p>
              <EnlaceOrigen enlace={a.link} />
            </li>
          ))}
        </ul>
      )}

      <Pagination
        pageIndex={pagina}
        pageSize={tamano}
        total={lista.data?.total ?? 0}
        onPageChange={setPagina}
        onPageSizeChange={(valor) => {
          setTamano(valor);
          setPagina(0);
        }}
      />
    </PageContent>
  );
}
