import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/api/client";
import type { PagedResult } from "@/api/types";
import { useCompany } from "@/app/contexts/CompanyContext";
import { Autorizado } from "@/components/Autorizado";
import { Pagination } from "@/components/Pagination";
import { formatearInstante } from "@/lib/fecha-de-negocio";
import type { PartyAuditItem } from "./tipos";

function HistorialContenido({ partyId }: { partyId: string }) {
  const { activeCompany } = useCompany();
  const companyId = activeCompany?.id;
  const [pageIndex, setPageIndex] = useState(0);
  const [pageSize, setPageSize] = useState(25);

  const query = useQuery({
    queryKey: [
      "maestros",
      "tercero-historial",
      companyId,
      partyId,
      pageIndex,
      pageSize,
    ],
    queryFn: () =>
      apiFetch<PagedResult<PartyAuditItem>>(
        `/maestros/terceros/${partyId}/audit?page=${pageIndex + 1}&page_size=${pageSize}`,
      ),
  });

  if (query.isLoading) return <p>Cargando historial…</p>;

  if (query.isError) {
    return <p role="alert">No fue posible cargar el historial.</p>;
  }

  const data = query.data;
  if (!data) return null;

  return (
    <section className="rounded-lg border border-border-default bg-surface-0 p-6">
      <h2 className="mb-4 text-lg font-semibold text-text-900">Historial</h2>
      {data.items.length === 0 ? (
        <p>Sin eventos registrados.</p>
      ) : (
        <ol className="space-y-4">
          {data.items.map((item) => {
            const claves = Array.from(
              new Set([
                ...Object.keys(item.details.before ?? {}),
                ...Object.keys(item.details.after ?? {}),
              ]),
            );
            return (
              <li key={item.id} className="space-y-1">
                <p>{formatearInstante(item.event_time)}</p>
                <p>{item.action_label}</p>
                <p>{item.username ?? "Sistema"}</p>
                {item.reason && <p>{`Motivo: ${item.reason}`}</p>}
                {claves.map((clave) => {
                  const antes =
                    clave in (item.details.before ?? {})
                      ? String(item.details.before?.[clave])
                      : "—";
                  const despues =
                    clave in (item.details.after ?? {})
                      ? String(item.details.after?.[clave])
                      : "—";
                  return <p key={clave}>{`${clave}: ${antes} → ${despues}`}</p>;
                })}
              </li>
            );
          })}
        </ol>
      )}
      <Pagination
        pageIndex={pageIndex}
        pageSize={pageSize}
        total={data.total}
        onPageChange={setPageIndex}
        onPageSizeChange={(newSize) => {
          setPageSize(newSize);
          setPageIndex(0);
        }}
      />
    </section>
  );
}

export function TerceroHistorial({ partyId }: { partyId: string }) {
  return (
    <Autorizado operacion={["GET", `/maestros/terceros/${partyId}/audit`]}>
      <HistorialContenido partyId={partyId} />
    </Autorizado>
  );
}
