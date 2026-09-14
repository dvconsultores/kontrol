/**
 * Centro de notificaciones (Spec 047 · FR-047-001, 003, 011, 028, 029, 031).
 *
 * Leer y archivar son estados **de quien lee**: otra persona que recibió la
 * misma notificación la sigue viendo sin leer. Archivar no borra.
 */
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { clsx } from "clsx";
import { useState } from "react";

import { ApiError, apiFetch } from "@/api/client";
import { useCompany } from "@/app/contexts/CompanyContext";
import { useNotifications } from "@/app/contexts/NotificationContext";
import { AsyncButton } from "@/components/AsyncButton";
import { EmptyState } from "@/components/EmptyState";
import { ErrorState } from "@/components/ErrorState";
import { FormField } from "@/components/FormField";
import { LoadingState } from "@/components/LoadingState";
import { PageHeader } from "@/components/PageHeader";
import { Pagination } from "@/components/Pagination";
import { formatearFecha, t, tValor } from "@/i18n";
import { PageContent } from "@/layout/PageContent";

import { CONSULTAS, etiquetaCategoria, textoDeMensaje, type Notificacion, type Pagina } from "../api";
import { EnlaceOrigen, EtiquetaSeveridad, SELECTOR } from "../componentes";

const ESTADOS = ["active", "unread", "read", "archived", "all"] as const;
type Estado = (typeof ESTADOS)[number];

export function CentroNotificacionesPage(): React.JSX.Element {
  const { activeCompanyId } = useCompany();
  const { notify } = useNotifications();
  const qc = useQueryClient();
  const [estado, setEstado] = useState<Estado>("active");
  const [pagina, setPagina] = useState(0);
  const [tamano, setTamano] = useState(10);

  const lista = useQuery({
    queryKey: [...CONSULTAS, "lista", activeCompanyId, estado, pagina, tamano],
    queryFn: () =>
      apiFetch<Pagina<Notificacion>>(
        `/notifications?state=${estado}&page=${pagina + 1}&page_size=${tamano}`,
      ),
    enabled: Boolean(activeCompanyId),
  });

  async function actuar(notificacion: Notificacion, accion: "read" | "archive"): Promise<void> {
    try {
      await apiFetch(`/notifications/${notificacion.id}/${accion}`, { method: "POST", body: {} });
      await qc.invalidateQueries({ queryKey: [...CONSULTAS] });
    } catch (e) {
      notify({
        type: "error",
        title: t("centro.error_accion"),
        description: e instanceof ApiError ? e.message : undefined,
      });
    }
  }

  const items = lista.data?.items ?? [];

  return (
    <PageContent>
      <PageHeader title={t("centro.titulo")} description={t("centro.descripcion")} />

      <div className="mb-4 max-w-xs">
        <FormField label={t("comun.filtro_estado")}>
          <select
            value={estado}
            className={SELECTOR}
            onChange={(e) => {
              setEstado(e.target.value as Estado);
              setPagina(0);
            }}
          >
            {ESTADOS.map((valor) => (
              <option key={valor} value={valor}>
                {tValor("centro.estado", valor) ?? valor}
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
        <EmptyState title={t("centro.vacio")} description={t("centro.vacio_detalle")} />
      ) : (
        <ul aria-label={t("centro.lista")} className="flex flex-col gap-2">
          {items.map((n) => (
            <li
              key={n.id}
              data-testid="notificacion"
              data-id={n.id}
              className={clsx(
                "rounded-lg border bg-surface-0 p-3",
                n.read_at ? "border-border-default" : "border-text-400",
              )}
            >
              <div className="mb-1 flex flex-wrap items-center gap-2 text-xs text-text-500">
                <EtiquetaSeveridad valor={n.severity} />
                <span>{etiquetaCategoria(n.category)}</span>
                <span>{formatearFecha(n.created_at)}</span>
                <span className="font-medium text-text-700">
                  {n.read_at ? t("centro.leida") : t("centro.sin_leer")}
                </span>
                {n.mandatory ? <span>{t("centro.obligatoria")}</span> : null}
              </div>
              <p className="mb-2 text-sm text-text-900">{textoDeMensaje(n.message)}</p>
              <div className="flex flex-wrap items-center gap-3">
                <EnlaceOrigen enlace={n.link} />
                {!n.read_at ? (
                  <AsyncButton
                    size="sm"
                    variant="secondary"
                    loadingText={t("comun.procesando")}
                    onClick={() => actuar(n, "read")}
                  >
                    {t("centro.marcar_leida")}
                  </AsyncButton>
                ) : null}
                {!n.archived_at ? (
                  <AsyncButton
                    size="sm"
                    variant="secondary"
                    loadingText={t("comun.procesando")}
                    onClick={() => actuar(n, "archive")}
                  >
                    {t("centro.archivar")}
                  </AsyncButton>
                ) : null}
              </div>
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
