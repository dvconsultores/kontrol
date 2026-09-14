/**
 * Preferencias de aviso (Spec 047 · FR-047-018, 019).
 *
 * Solo lo configurable: una notificación obligatoria no se desactiva, y un canal
 * sin proveedor instalado no se ofrece como si funcionara.
 */
import { useQuery, useQueryClient } from "@tanstack/react-query";

import { ApiError, apiFetch } from "@/api/client";
import { useCompany } from "@/app/contexts/CompanyContext";
import { useNotifications } from "@/app/contexts/NotificationContext";
import { EmptyState } from "@/components/EmptyState";
import { ErrorState } from "@/components/ErrorState";
import { LoadingState } from "@/components/LoadingState";
import { PageHeader } from "@/components/PageHeader";
import { t, tValor } from "@/i18n";
import { PageContent } from "@/layout/PageContent";

import { CONSULTAS, etiquetaCategoria, type Preferencia } from "../api";

export function PreferenciasPage(): React.JSX.Element {
  const { activeCompanyId } = useCompany();
  const { notify } = useNotifications();
  const qc = useQueryClient();

  const preferencias = useQuery({
    queryKey: [...CONSULTAS, "preferencias", activeCompanyId],
    queryFn: () => apiFetch<Preferencia[]>("/notifications/preferences"),
    enabled: Boolean(activeCompanyId),
  });

  async function guardar(p: Preferencia, enabled: boolean): Promise<void> {
    try {
      await apiFetch("/notifications/preferences", {
        method: "PUT",
        body: { category: p.category, channel: p.channel, enabled },
      });
      notify({ type: "success", title: t("preferencias.guardada") });
      await qc.invalidateQueries({ queryKey: [...CONSULTAS, "preferencias"] });
    } catch (e) {
      notify({
        type: "error",
        title: t("preferencias.error"),
        description: e instanceof ApiError ? e.message : undefined,
      });
    }
  }

  const items = preferencias.data ?? [];

  return (
    <PageContent>
      <PageHeader title={t("preferencias.titulo")} description={t("preferencias.descripcion")} />
      {preferencias.isLoading ? (
        <LoadingState label={t("comun.cargando")} />
      ) : preferencias.isError ? (
        <ErrorState message={t("comun.error_carga")} onRetry={() => void preferencias.refetch()} />
      ) : items.length === 0 ? (
        <EmptyState title={t("preferencias.vacio")} />
      ) : (
        <ul aria-label={t("preferencias.lista")} className="flex flex-col gap-2">
          {items.map((p) => {
            const bloqueada = !p.available || (p.mandatory && p.channel === "INTERNAL");
            const canal = tValor("preferencias.canal", p.channel) ?? p.channel;
            return (
              <li
                key={`${p.category}-${p.channel}`}
                className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-border-default bg-surface-0 p-3"
              >
                <label className="flex items-center gap-2 text-sm text-text-900">
                  <input
                    type="checkbox"
                    checked={p.enabled}
                    disabled={bloqueada}
                    aria-label={t("preferencias.recibir", { categoria: etiquetaCategoria(p.category), canal })}
                    onChange={(e) => void guardar(p, e.target.checked)}
                  />
                  <span>{etiquetaCategoria(p.category)}</span>
                  <span className="text-text-500">· {canal}</span>
                </label>
                <span className="text-xs text-text-500">
                  {!p.available
                    ? t("preferencias.no_disponible")
                    : p.mandatory && p.channel === "INTERNAL"
                      ? t("preferencias.descripcion")
                      : null}
                </span>
              </li>
            );
          })}
        </ul>
      )}
    </PageContent>
  );
}
