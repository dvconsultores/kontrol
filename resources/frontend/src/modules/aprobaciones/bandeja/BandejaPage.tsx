/**
 * Mis aprobaciones — bandeja transversal a todos los dominios (Spec 045, WF-045-01).
 *
 * El backend es la autoridad: las acciones se renderizan a partir de
 * `allowed_actions` calculado en servidor (Constitución P6, FR-045-062).
 * Modal sólo para confirmación breve con motivo (ADR-015 / P18).
 */
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { createColumnHelper } from "@tanstack/react-table";
import { useState } from "react";

import { apiFetch } from "@/api/client";
import type { ApprovalInboxItem } from "@/api/types";
import { useCompany } from "@/app/contexts/CompanyContext";
import { useNotifications } from "@/app/contexts/NotificationContext";
import { AsyncButton } from "@/components/AsyncButton";
import { ConfirmationDialog } from "@/components/ConfirmationDialog";
import { DataTable } from "@/components/DataTable";
import { EmptyState } from "@/components/EmptyState";
import { FormField } from "@/components/FormField";
import { PageHeader } from "@/components/PageHeader";
import { TextInput } from "@/components/TextInput";
import { PageContent } from "@/layout/PageContent";

const columnHelper = createColumnHelper<ApprovalInboxItem>();

type PendingAction = { item: ApprovalInboxItem; action: "approve" | "reject" | "return" } | null;

const ACTION_LABEL: Record<string, string> = {
  approve: "Aprobar",
  reject: "Rechazar",
  return: "Devolver para corrección",
};

/** El motivo es obligatorio en las decisiones negativas (FR-045-026). */
const REQUIRES_REASON = new Set(["reject", "return"]);

export function BandejaPage(): React.JSX.Element {
  const { activeCompany } = useCompany();
  const { notify } = useNotifications();
  const queryClient = useQueryClient();

  const [processType, setProcessType] = useState("");
  const [onlyOverdue, setOnlyOverdue] = useState(false);
  const [pending, setPending] = useState<PendingAction>(null);
  const [reason, setReason] = useState("");

  const companyId = activeCompany?.id ?? "";
  const query = useQuery({
    queryKey: ["aprobaciones", "inbox", companyId, processType, onlyOverdue],
    queryFn: () =>
      apiFetch<{ total: number; items: ApprovalInboxItem[] }>(
        `/approvals/inbox?company_id=${encodeURIComponent(companyId)}` +
          (processType ? `&process_type=${encodeURIComponent(processType)}` : "") +
          (onlyOverdue ? "&only_overdue=true" : ""),
      ),
    enabled: Boolean(companyId),
    retry: false,
  });

  const refresh = (): void => {
    void queryClient.invalidateQueries({ queryKey: ["aprobaciones", "inbox"] });
  };

  const confirmDecision = async (): Promise<void> => {
    if (!pending) return;
    const { item, action } = pending;
    if (REQUIRES_REASON.has(action) && !reason.trim()) {
      notify({
        type: "error",
        title: "Falta el motivo",
        description: "Indique el motivo para continuar.",
      });
      return;
    }
    try {
      await apiFetch(`/approvals/steps/${item.step_id}/${action}`, {
        method: "POST",
        ifMatch: String(item.step_version),
        body: { reason: reason.trim() || null },
      });
      notify({
        type: "success",
        title: `${ACTION_LABEL[action]}: hecho`,
        description: `${item.document_type} ${item.document_id}`,
      });
      setPending(null);
      setReason("");
      refresh();
    } catch (err) {
      const message = err instanceof Error ? err.message : "No fue posible registrar la decisión";
      notify({ type: "error", title: "No fue posible registrar la decisión", description: message });
    }
  };

  const columns = [
    columnHelper.accessor("process_type", { header: "Proceso" }),
    columnHelper.display({
      id: "document",
      header: "Documento",
      cell: ({ row }) => `${row.original.document_type} ${row.original.document_id}`,
    }),
    columnHelper.accessor("requested_by", {
      header: "Solicitante",
      cell: (info) => info.getValue() ?? "—",
    }),
    columnHelper.accessor("amount_base", {
      header: "Monto (base)",
      cell: (info) => {
        const value = info.getValue();
        return value === null
          ? "—"
          : `${value.toLocaleString("es-VE", { minimumFractionDigits: 2 })} ${info.row.original.base_currency ?? ""}`;
      },
    }),
    columnHelper.accessor("level_order", {
      header: "Nivel",
      cell: (info) => `Nivel ${info.getValue()}`,
    }),
    columnHelper.display({
      id: "due",
      header: "Vence",
      cell: ({ row }) =>
        row.original.due_at ? (
          <span className={row.original.overdue ? "font-semibold text-danger-600" : undefined}>
            {row.original.overdue ? "Vencido" : new Date(row.original.due_at).toLocaleString("es-VE")}
          </span>
        ) : (
          "—"
        ),
    }),
    columnHelper.display({
      id: "actions",
      header: "Acciones",
      cell: ({ row }) => (
        <div className="flex justify-end gap-1">
          {row.original.allowed_actions.map((action) => (
            <AsyncButton
              key={action}
              size="sm"
              variant={action === "approve" ? "primary" : "secondary"}
              aria-label={`${ACTION_LABEL[action]} ${row.original.document_id}`}
              onClick={async () => {
                setReason("");
                setPending({ item: row.original, action: action as "approve" | "reject" | "return" });
              }}
            >
              {ACTION_LABEL[action]}
            </AsyncButton>
          ))}
        </div>
      ),
    }),
  ];

  const items = query.data?.items ?? [];

  return (
    <PageContent maxWidth="full">
      <PageHeader
        title="Mis aprobaciones"
        description="Solicitudes de cualquier módulo que esperan tu decisión. El monto se muestra en moneda base."
        crumbs={[{ label: "Aprobaciones" }, { label: "Mis aprobaciones" }]}
      />

      <section className="mb-4 flex flex-wrap items-end gap-3 rounded-lg border border-border-default bg-surface-0 p-4">
        <FormField label="Proceso">
          <TextInput
            value={processType}
            onChange={(e) => setProcessType(e.target.value)}
            placeholder="Todos los procesos"
          />
        </FormField>
        <label className="flex h-10 items-center gap-2 text-sm text-text-900">
          <input
            type="checkbox"
            checked={onlyOverdue}
            onChange={(e) => setOnlyOverdue(e.target.checked)}
            className="h-4 w-4"
          />
          Solo vencidas
        </label>
      </section>

      {!query.isLoading && items.length === 0 ? (
        <EmptyState
          title="No tienes aprobaciones pendientes"
          description="Cuando una operación requiera tu decisión, aparecerá aquí."
        />
      ) : (
        <DataTable
          data={items}
          columns={columns}
          loading={query.isLoading}
          error={query.error instanceof Error ? query.error.message : null}
          emptyTitle="No tienes aprobaciones pendientes"
          emptyDescription="Cuando una operación requiera tu decisión, aparecerá aquí."
          getRowId={(row) => row.step_id}
        />
      )}

      <ConfirmationDialog
        open={pending !== null}
        title={pending ? ACTION_LABEL[pending.action] : ""}
        description={
          pending
            ? `${pending.item.document_type} ${pending.item.document_id} · nivel ${pending.item.level_order}`
            : undefined
        }
        confirmLabel={pending ? ACTION_LABEL[pending.action] : "Confirmar"}
        danger={pending?.action === "reject"}
        onConfirm={confirmDecision}
        onCancel={() => {
          setPending(null);
          setReason("");
        }}
      >
        {pending && REQUIRES_REASON.has(pending.action) ? (
          <FormField label="Motivo" required>
            <TextInput
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              placeholder="Indique el motivo de la decisión"
              required
            />
          </FormField>
        ) : null}
      </ConfirmationDialog>
    </PageContent>
  );
}
