/**
 * Campana de la cabecera (Spec 047 · FR-047-030).
 *
 * El número lo cuenta el servidor para la empresa activa; aquí nunca se trae la
 * lista para contarla. Se refresca por sondeo y cada vez que otra pantalla de la
 * 047 invalida sus consultas.
 */
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Bell } from "lucide-react";
import { useEffect, useReducer } from "react";
import { Link } from "react-router";

import { apiFetch } from "@/api/client";
import { useCompany } from "@/app/contexts/CompanyContext";
import { t } from "@/i18n";

import { CONSULTAS, INTERVALO_SONDEO_MS, type Contadores } from "./api";

export function NotificationBell(): React.JSX.Element | null {
  const { activeCompanyId } = useCompany();
  const qc = useQueryClient();
  const [, reconstruir] = useReducer((n: number) => n + 1, 0);

  // La campana vive en la cabecera, que no se remonta al cambiar de empresa.
  // `AppShell` retira entonces las consultas de empresa en un efecto que corre
  // **después** del de esta campana, y la dejaría escuchando una consulta
  // descartada hasta el siguiente sondeo. Si retira la suya, se vuelve a construir.
  useEffect(
    () =>
      qc.getQueryCache().subscribe((evento) => {
        const clave = evento.query.queryKey;
        if (evento.type === "removed" && clave[0] === CONSULTAS[0] && clave[1] === "contadores") {
          reconstruir();
        }
      }),
    [qc],
  );

  const contadores = useQuery({
    queryKey: [...CONSULTAS, "contadores", activeCompanyId],
    queryFn: () => apiFetch<Contadores>("/notifications/counts"),
    enabled: Boolean(activeCompanyId),
    refetchInterval: INTERVALO_SONDEO_MS,
  });
  if (!activeCompanyId) {
    return null;
  }
  const sinLeer = contadores.data?.unread_notifications ?? 0;
  return (
    <Link
      to="/notificaciones"
      data-testid="campana"
      aria-label={t("campana.etiqueta", { count: sinLeer })}
      className="relative inline-flex size-9 items-center justify-center rounded-md text-text-500 hover:bg-surface-100"
    >
      <Bell className="size-5" aria-hidden="true" />
      {sinLeer > 0 ? (
        <span
          aria-hidden="true"
          data-testid="campana-contador"
          className="absolute -right-0.5 -top-0.5 min-w-5 rounded-full bg-danger-600 px-1 text-center text-xs font-semibold text-white"
        >
          {sinLeer}
        </span>
      ) : null}
    </Link>
  );
}
