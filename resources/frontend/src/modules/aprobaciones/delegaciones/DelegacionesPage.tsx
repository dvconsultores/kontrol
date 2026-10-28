/**
 * Delegaciones de aprobación (Spec 045, WF-045-06 · FR-045-042..046).
 *
 * Una delegación es acotada en ámbito y vigencia, revocable y auditada.
 * Revocarla no invalida las decisiones ya tomadas bajo ella (P5).
 */
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { createColumnHelper } from "@tanstack/react-table";
import { useState } from "react";

import { apiFetch } from "@/api/client";
import type { ApprovalDelegationSummary } from "@/api/types";
import { useAutoridad } from "@/app/autoridad/AutoridadContext";
import { useCompany } from "@/app/contexts/CompanyContext";
import { useNotifications } from "@/app/contexts/NotificationContext";
import { AsyncButton } from "@/components/AsyncButton";
import { Autorizado } from "@/components/Autorizado";
import { ConfirmationDialog } from "@/components/ConfirmationDialog";
import { DataTable } from "@/components/DataTable";
import { FormField } from "@/components/FormField";
import { PageHeader } from "@/components/PageHeader";
import { TextInput } from "@/components/TextInput";
import { PageContent } from "@/layout/PageContent";
import { finDelDiaDeNegocio, formatearFechaDeInstante } from "@/lib/fecha-de-negocio";

const columnHelper = createColumnHelper<ApprovalDelegationSummary>();

export function DelegacionesPage(): React.JSX.Element {
  const { activeCompany } = useCompany();
  const { puede } = useAutoridad();
  const { notify } = useNotifications();
  const queryClient = useQueryClient();

  const [grantor, setGrantor] = useState("");
  const [grantee, setGrantee] = useState("");
  const [scope, setScope] = useState("");
  const [validTo, setValidTo] = useState("");
  const [reason, setReason] = useState("");
  const [toRevoke, setToRevoke] = useState<ApprovalDelegationSummary | null>(null);

  const companyId = activeCompany?.id ?? "";
  const query = useQuery({
    queryKey: ["aprobaciones", "delegations", companyId],
    queryFn: () =>
      apiFetch<{ items: ApprovalDelegationSummary[] }>(
        `/approvals/delegations?company_id=${encodeURIComponent(companyId)}`,
      ),
    enabled: Boolean(companyId),
    retry: false,
  });

  const refresh = (): void => {
    void queryClient.invalidateQueries({ queryKey: ["aprobaciones", "delegations"] });
  };

  const create = async (): Promise<void> => {
    try {
      await apiFetch("/approvals/delegations", {
        method: "POST",
        body: {
          company_id: companyId,
          grantor_id: grantor,
          grantee_id: grantee,
          scope_process_type: scope || null,
          valid_to: validTo ? finDelDiaDeNegocio(validTo) : null,
          reason: reason || null,
          is_temporary_substitution: Boolean(validTo),
        },
      });
      notify({ type: "success", title: "Delegación creada" });
      setGrantor("");
      setGrantee("");
      setScope("");
      setValidTo("");
      setReason("");
      refresh();
    } catch (err) {
      const message = err instanceof Error ? err.message : "No fue posible crear la delegación";
      notify({ type: "error", title: "No fue posible crear la delegación", description: message });
    }
  };

  const revoke = async (): Promise<void> => {
    if (!toRevoke) return;
    try {
      await apiFetch(`/approvals/delegations/${toRevoke.id}/revoke`, { method: "POST" });
      notify({
        type: "success",
        title: "Delegación revocada",
        description: "Las decisiones ya tomadas bajo ella siguen siendo válidas.",
      });
      setToRevoke(null);
      refresh();
    } catch (err) {
      const message = err instanceof Error ? err.message : "No fue posible revocar";
      notify({ type: "error", title: "No fue posible revocar", description: message });
    }
  };

  const columns = [
    columnHelper.accessor("grantor_id", { header: "Delega" }),
    columnHelper.accessor("grantee_id", { header: "En" }),
    columnHelper.accessor("scope_process_type", {
      header: "Ámbito",
      cell: (info) => info.getValue() ?? "Todos los procesos",
    }),
    columnHelper.accessor("valid_to", {
      header: "Hasta",
      cell: (info) =>
        info.getValue() ? formatearFechaDeInstante(info.getValue() as string) : "Sin límite",
    }),
    columnHelper.accessor("status", {
      header: "Estado",
      cell: (info) => (info.getValue() === "ACTIVE" ? "Activa" : "Revocada"),
    }),
    columnHelper.display({
      id: "actions",
      header: "Acciones",
      cell: ({ row }) =>
        row.original.status === "ACTIVE" &&
        puede("POST", `/approvals/delegations/${row.original.id}/revoke`) ? (
          <div className="flex justify-end">
            <AsyncButton
              size="sm"
              variant="secondary"
              aria-label={`Revocar delegación de ${row.original.grantor_id}`}
              onClick={async () => setToRevoke(row.original)}
            >
              Revocar
            </AsyncButton>
          </div>
        ) : null,
    }),
  ];

  return (
    <PageContent maxWidth="full">
      <PageHeader
        title="Delegaciones"
        description="Autorizaciones temporales para resolver aprobaciones en nombre de otra persona. No eluden la segregación de funciones."
        crumbs={[{ label: "Aprobaciones" }, { label: "Delegaciones" }]}
      />

      <Autorizado operacion={["POST", "/approvals/delegations"]}>
        <section className="mb-4 rounded-lg border border-border-default bg-surface-0 p-4">
          <h2 className="mb-2 text-base font-semibold text-text-900">Nueva delegación</h2>
          <form className="flex flex-wrap items-end gap-3" onSubmit={(e) => e.preventDefault()}>
            <FormField label="Delega (usuario)" required>
              <TextInput value={grantor} onChange={(e) => setGrantor(e.target.value)} required />
            </FormField>
            <FormField label="En (usuario)" required>
              <TextInput value={grantee} onChange={(e) => setGrantee(e.target.value)} required />
            </FormField>
            <FormField label="Ámbito (proceso)">
              <TextInput
                value={scope}
                onChange={(e) => setScope(e.target.value.toUpperCase())}
                placeholder="Todos"
              />
            </FormField>
            <FormField label="Hasta" help="Incluido: vence al final de ese día, hora de Caracas">
              <TextInput type="date" value={validTo} onChange={(e) => setValidTo(e.target.value)} />
            </FormField>
            <FormField label="Motivo">
              <TextInput value={reason} onChange={(e) => setReason(e.target.value)} />
            </FormField>
            <AsyncButton type="submit" variant="primary" onClick={create}>
              Crear delegación
            </AsyncButton>
          </form>
        </section>
      </Autorizado>

      <DataTable
        data={query.data?.items ?? []}
        columns={columns}
        loading={query.isLoading}
        error={query.error instanceof Error ? query.error.message : null}
        emptyTitle="Sin delegaciones"
        emptyDescription="Cree una delegación cuando un aprobador vaya a ausentarse."
        getRowId={(row) => row.id}
      />

      <ConfirmationDialog
        open={toRevoke !== null}
        title="Revocar delegación"
        description="Dejará de poder resolver en nombre del delegante. Las decisiones ya tomadas siguen siendo válidas."
        confirmLabel="Revocar"
        danger
        onConfirm={revoke}
        onCancel={() => setToRevoke(null)}
      />
    </PageContent>
  );
}
