import { Link } from "react-router";
import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/api/client";
import { useCompany } from "@/app/contexts/CompanyContext";
import { EmptyState } from "@/components/EmptyState";
import { ErrorState } from "@/components/ErrorState";
import { LoadingState } from "@/components/LoadingState";
import { formatearFecha } from "@/i18n";
import {
  CONSULTA_PAQUETES,
  abreviarHuella,
  consultaDePaquetes,
  formatearBytes,
  type PaquetesListado,
} from "@/modules/gobierno/api";

export function PaquetesDeLaMuestra({ muestraId }: { muestraId: string }): React.JSX.Element {
  const { activeCompanyId } = useCompany();
  const consulta = useQuery({
    queryKey: [...CONSULTA_PAQUETES, "muestra", activeCompanyId, muestraId],
    queryFn: () =>
      apiFetch<PaquetesListado>(
        `/gobierno/paquetes${consultaDePaquetes({ muestra_id: muestraId }, { por_pagina: 100 })}`,
      ),
    enabled: Boolean(activeCompanyId),
    retry: false,
  });

  return (
    <section aria-labelledby="paquetes-muestra" className="mt-8">
      <h2 id="paquetes-muestra" className="text-lg font-semibold text-text-900">
        Paquetes de esta muestra
      </h2>
      {consulta.isLoading ? (
        <LoadingState label="Cargando paquetes…" />
      ) : consulta.isError ? (
        <ErrorState
          message="No fue posible cargar los paquetes."
          onRetry={() => void consulta.refetch()}
        />
      ) : !consulta.data || consulta.data.items.length === 0 ? (
        <EmptyState title="Aún no se ha generado ningún paquete para esta muestra" />
      ) : (
        <ul className="mt-2 space-y-1">
          {consulta.data.items.map((p) => (
            <li key={p.id}>
              <Link to={`/gobierno/paquetes/${p.id}`}>{p.codigo}</Link> ·{" "}
              {formatearFecha(p.generado_en)} · {formatearBytes(p.bytes)} ·{" "}
              <span className="font-mono text-xs">{abreviarHuella(p.huella_paquete)}</span>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
