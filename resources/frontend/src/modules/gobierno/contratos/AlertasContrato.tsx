import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router";

import { apiFetch } from "@/api/client";
import { useAutoridad } from "@/app/autoridad/AutoridadContext";
import { useCompany } from "@/app/contexts/CompanyContext";
import { formatearFecha } from "@/i18n";
import { type Alerta, textoDeMensaje } from "@/modules/notificaciones/api";
import { EnlaceOrigen, EtiquetaSeveridad } from "@/modules/notificaciones/componentes";

import { CONSULTA_CONTRATOS } from "./api";

export interface AlertasDelContrato {
  contrato_id: string;
  activas: number;
  items: Alerta[];
}

export function AlertasContrato({ contratoId }: { contratoId: string }): React.JSX.Element {
  const { activeCompanyId } = useCompany();
  const { tiene } = useAutoridad();
  const consulta = useQuery({
    queryKey: [...CONSULTA_CONTRATOS, activeCompanyId, "alertas", contratoId],
    queryFn: () => apiFetch<AlertasDelContrato>(`/gobierno/contratos/${contratoId}/alertas`),
    retry: false,
  });

  const puedeVerTodas = tiene("alertas:view", "empresa");
  const data = consulta.data;

  return (
    <section aria-labelledby="alertas-contrato-titulo" className="mb-6">
      <h2 id="alertas-contrato-titulo" className="text-lg font-semibold text-text-900">
        Alertas de vencimiento
      </h2>
      <p className="text-sm text-text-600">
        Las alertas informan sobre plazos; no sustituyen la decisión del supervisor ni de la autoridad.
      </p>
      {consulta.isLoading ? (
        <p className="text-sm text-text-500">Cargando alertas…</p>
      ) : consulta.isError ? (
        <p role="alert" className="text-sm text-danger-600">
          No fue posible consultar las alertas del contrato.
        </p>
      ) : (
        <>
          <p className="mt-2 text-sm font-medium text-text-900">Alertas activas: {data?.activas ?? 0}</p>
          {!data || data.items.length === 0 ? (
            <p className="text-sm text-text-600">Sin alertas activas.</p>
          ) : (
            <ul aria-label="Alertas activas del contrato" className="mt-2 flex flex-col gap-2">
              {data.items.map((a) => (
                <li key={a.id} className="rounded-lg border border-border-default bg-surface-0 p-3">
                  <div className="mb-1 flex flex-wrap items-center gap-2 text-xs text-text-500">
                    <EtiquetaSeveridad valor={a.severity} />
                    <span>{formatearFecha(a.created_at)}</span>
                  </div>
                  <p className="mb-2 break-words text-sm text-text-900">{textoDeMensaje(a.message)}</p>
                  <EnlaceOrigen enlace={a.link} />
                </li>
              ))}
            </ul>
          )}
        </>
      )}
      {puedeVerTodas ? (
        <p className="mt-2">
          <Link className="text-sm text-brand-700 underline" to="/alertas">
            Ver todas las alertas
          </Link>
        </p>
      ) : null}
    </section>
  );
}
