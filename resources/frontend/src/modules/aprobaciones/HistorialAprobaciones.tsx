/**
 * Historial de aprobaciones de un documento (Spec 045, WF-045-06).
 *
 * Panel embebido reutilizable desde cualquier entidad: no es una ruta propia.
 * Muestra la cadena completa, incluidas las solicitudes encadenadas tras una
 * devolución (FR-045-030) y la delegación con la que se ejerció cada decisión
 * (FR-045-045).
 */
import { useQuery } from "@tanstack/react-query";

import { apiFetch } from "@/api/client";
import type { ApprovalDocumentStatus } from "@/api/types";
import { ErrorState } from "@/components/ErrorState";
import { LoadingState } from "@/components/LoadingState";

const REQUEST_LABEL: Record<string, string> = {
  DRAFT: "Borrador",
  PENDING: "Pendiente",
  IN_REVIEW: "En revisión",
  APPROVED: "Aprobada",
  REJECTED: "Rechazada",
  RETURNED: "Devuelta",
  CANCELLED: "Cancelada",
  OBSOLETE: "Obsoleta",
};

const DECISION_ICON: Record<string, string> = {
  APPROVE: "✓",
  REJECT: "✕",
  RETURN: "↩",
  CANCEL: "—",
};

export interface HistorialAprobacionesProps {
  companyId: string;
  documentType: string;
  documentId: string;
}

export function HistorialAprobaciones({
  companyId,
  documentType,
  documentId,
}: HistorialAprobacionesProps): React.JSX.Element | null {
  const query = useQuery({
    queryKey: ["aprobaciones", "by-document", companyId, documentType, documentId],
    queryFn: () =>
      apiFetch<ApprovalDocumentStatus>(
        `/approvals/requests/by-document?document_type=${encodeURIComponent(documentType)}` +
          `&document_id=${encodeURIComponent(documentId)}`,
      ),
    enabled: Boolean(companyId && documentId),
    retry: false,
  });

  if (query.isLoading) return <LoadingState rows={2} label="Cargando aprobaciones…" />;
  if (query.error) {
    return <ErrorState message="No fue posible cargar el historial de aprobaciones." />;
  }

  const requests = query.data?.requests ?? [];
  if (requests.length === 0) {
    return (
      <section aria-labelledby="aprobaciones-title" className="rounded-lg border border-border-default bg-surface-0 p-4">
        <h2 id="aprobaciones-title" className="text-base font-semibold text-text-900">
          Aprobaciones
        </h2>
        <p className="mt-2 text-sm text-text-500">Este documento no ha requerido aprobación.</p>
      </section>
    );
  }

  return (
    <section aria-labelledby="aprobaciones-title" className="rounded-lg border border-border-default bg-surface-0 p-4">
      <h2 id="aprobaciones-title" className="mb-3 text-base font-semibold text-text-900">
        Aprobaciones
      </h2>
      <ol className="flex flex-col gap-4">
        {[...requests].reverse().map((req, index) => (
          <li key={req.id} className="border-l-2 border-border-default pl-3">
            <p className="text-sm font-semibold text-text-900">
              Solicitud #{requests.length - index} · {REQUEST_LABEL[req.status] ?? req.status} ·
              política v{req.policy_version}
            </p>
            {req.resolution_reason ? (
              <p className="text-sm text-text-500">«{req.resolution_reason}»</p>
            ) : null}
            <ul className="mt-1 flex flex-col gap-1">
              {req.steps.map((step) => (
                <li key={step.id} className="text-sm text-text-900">
                  Nivel {step.level_order} · {step.status}
                  {step.decisions.map((d, i) => (
                    <span key={`${step.id}-d-${i}`} className="ml-2 text-text-500">
                      {DECISION_ICON[d.decision] ?? ""} {d.actor_id}
                      {d.on_behalf_of_id ? ` (por delegación de ${d.on_behalf_of_id})` : ""}
                      {d.reason ? ` — «${d.reason}»` : ""}
                    </span>
                  ))}
                </li>
              ))}
            </ul>
          </li>
        ))}
      </ol>
    </section>
  );
}
