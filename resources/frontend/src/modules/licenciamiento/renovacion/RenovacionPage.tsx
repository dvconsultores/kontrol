/** Renovación central con comprobante (FR-010-020/021). */
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { createColumnHelper } from "@tanstack/react-table";
import { useState } from "react";

import { apiFetch } from "@/api/client";
import type { RenewalRequestSummary } from "@/api/types";
import { useAutoridad } from "@/app/autoridad/AutoridadContext";
import { useNotifications } from "@/app/contexts/NotificationContext";
import { AsyncButton } from "@/components/AsyncButton";
import { Autorizado } from "@/components/Autorizado";
import { DataTable } from "@/components/DataTable";
import { ErrorState } from "@/components/ErrorState";
import { FormField } from "@/components/FormField";
import { LoadingState } from "@/components/LoadingState";
import { PageContent } from "@/layout/PageContent";
import { PageHeader } from "@/components/PageHeader";
import { TextInput } from "@/components/TextInput";

const columnHelper = createColumnHelper<RenewalRequestSummary>();

export function RenovacionPage(): React.JSX.Element {
  const queryClient = useQueryClient();
  const { puede } = useAutoridad();
  const { notify } = useNotifications();
  const [proofRef, setProofRef] = useState("");
  const [notes, setNotes] = useState("");

  const requests = useQuery({
    queryKey: ["licensing", "renewals"],
    queryFn: () => apiFetch<{ items: RenewalRequestSummary[] }>("/licensing/renewal-requests"),
    retry: false,
  });

  const invalidate = async (): Promise<void> => {
    await queryClient.invalidateQueries({ queryKey: ["licensing"] });
  };

  const createRequest = async (): Promise<void> => {
    await apiFetch("/licensing/renewal-requests", {
      method: "POST",
      body: { payment_proof_ref: proofRef, notes },
    });
    notify({ type: "success", title: "Solicitud registrada", description: "El comprobante fue enviado para verificación." });
    setProofRef("");
    setNotes("");
    await invalidate();
  };

  const transition = (id: string, target: string): Promise<void> =>
    apiFetch(`/licensing/renewal-requests/${id}/transition`, { method: "POST", body: { target } }).then(async () => {
      notify({ type: "success", title: "Estado actualizado", description: `Renovación en estado ${target}.` });
      await invalidate();
    });

  if (requests.isLoading) {
    return <LoadingState rows={4} />;
  }
  if (requests.isError) {
    return (
      <PageContent maxWidth="md">
        <ErrorState message="No fue posible cargar las solicitudes de renovación." onRetry={() => void requests.refetch()} />
      </PageContent>
    );
  }

  const columns = [
    columnHelper.accessor("created_at", {
      header: "Fecha",
      cell: (info) => new Date(info.getValue()).toLocaleString("es-VE"),
    }),
    columnHelper.accessor("payment_proof_ref", { header: "Comprobante" }),
    columnHelper.accessor("status", { header: "Estado" }),
    columnHelper.accessor("notes", { header: "Notas" }),
    columnHelper.display({
      id: "actions",
      header: "Acciones",
      cell: (info) => {
        const row = info.row.original;
        const canTransition = puede("POST", `/licensing/renewal-requests/${row.id}/transition`);
        const canVerify = row.status === "REPORTED" && canTransition;
        const canIssue = row.status === "VERIFIED" && canTransition;
        return (
          <div className="flex flex-wrap gap-2">
            {canVerify ? (
              <AsyncButton onClick={() => transition(row.id, "VERIFIED")} variant="secondary" loadingText="…">
                Verificar
              </AsyncButton>
            ) : null}
            {canIssue ? (
              <AsyncButton onClick={() => transition(row.id, "ISSUED")} variant="primary" loadingText="…">
                Emitir
              </AsyncButton>
            ) : null}
            {(row.status === "REPORTED" || row.status === "VERIFIED") && canTransition ? (
              <AsyncButton onClick={() => transition(row.id, "REJECTED")} variant="danger" loadingText="…">
                Rechazar
              </AsyncButton>
            ) : null}
          </div>
        );
      },
    }),
  ];

  return (
    <PageContent maxWidth="full">
      <PageHeader
        title="Renovación central"
        description="Solicitud de renovación con comprobante y workflow REPORTED → VERIFIED → ISSUED / REJECTED."
        crumbs={[{ label: "Licenciamiento" }, { label: "Renovación" }]}
      />

      <Autorizado operacion={["POST", "/licensing/renewal-requests"]}>
        <section className="rounded-lg border border-border-default bg-surface-0 p-6">
          <h2 className="text-base font-semibold text-text-900">Nueva solicitud de renovación</h2>
          <div className="mt-4 grid gap-4 sm:grid-cols-2">
            <FormField label="Referencia del comprobante">
              <TextInput value={proofRef} onChange={(e) => setProofRef(e.target.value)} placeholder="Banco, fecha y referencia" />
            </FormField>
            <FormField label="Notas">
              <TextInput value={notes} onChange={(e) => setNotes(e.target.value)} placeholder="Observaciones (opcional)" />
            </FormField>
          </div>
          <div className="mt-4">
            <AsyncButton onClick={createRequest} loadingText="Registrando…">
              Solicitar renovación
            </AsyncButton>
          </div>
        </section>
      </Autorizado>

      <div className="mt-6">
        <DataTable
          columns={columns}
          data={requests.data?.items ?? []}
          loading={false}
          error={null}
          getRowId={(row) => row.id}
          emptyTitle="Sin solicitudes"
          emptyDescription="Registre un comprobante para iniciar la renovación."
        />
      </div>
    </PageContent>
  );
}
