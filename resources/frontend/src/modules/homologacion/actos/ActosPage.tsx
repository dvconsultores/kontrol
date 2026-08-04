/** Homologación fiscal — acto formal y evaluación (FR-011-001..005). */
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { createColumnHelper } from "@tanstack/react-table";
import { useState } from "react";

import { apiFetch } from "@/api/client";
import type { HomologationRecordSummary } from "@/api/types";
import { useNotifications } from "@/app/contexts/NotificationContext";
import { AsyncButton } from "@/components/AsyncButton";
import { DataTable } from "@/components/DataTable";
import { ErrorState } from "@/components/ErrorState";
import { FormField } from "@/components/FormField";
import { LoadingState } from "@/components/LoadingState";
import { PageContent } from "@/layout/PageContent";
import { PageHeader } from "@/components/PageHeader";
import { TextInput } from "@/components/TextInput";

const columnHelper = createColumnHelper<HomologationRecordSummary>();

export function ActosPage(): React.JSX.Element {
  const queryClient = useQueryClient();
  const { notify } = useNotifications();

  const [fiscalVersion, setFiscalVersion] = useState("");
  const [modality, setModality] = useState("E_FACTURA");
  const [formalActRef, setFormalActRef] = useState("");
  const [evidenceSha, setEvidenceSha] = useState("");
  const [notes, setNotes] = useState("");
  const [evaluatorAct, setEvaluatorAct] = useState("");
  const [evaluateFormalAct, setEvaluateFormalAct] = useState("");

  const records = useQuery({
    queryKey: ["homologacion", "records"],
    queryFn: () => apiFetch<{ items: HomologationRecordSummary[] }>("/homologation/records"),
    retry: false,
  });

  const invalidate = async (): Promise<void> => {
    await queryClient.invalidateQueries({ queryKey: ["homologacion"] });
  };

  const createRecord = async (): Promise<void> => {
    await apiFetch("/homologation/records", {
      method: "POST",
      body: {
        fiscal_version: fiscalVersion,
        modality,
        formal_act_ref: formalActRef || null,
        evidence_sha256: evidenceSha || null,
        notes,
      },
    });
    notify({ type: "success", title: "Acto registrado", description: `Homologación ${fiscalVersion} en borrador.` });
    setFiscalVersion("");
    setFormalActRef("");
    setEvidenceSha("");
    setNotes("");
    await invalidate();
  };

  const submit = (id: string): Promise<void> =>
    apiFetch(`/homologation/records/${id}/submit`, { method: "POST" }).then(async () => {
      notify({ type: "success", title: "Sometida", description: "La homologación quedó en evaluación." });
      await invalidate();
    });

  const evaluate = (id: string, decision: "APPROVED" | "REJECTED"): Promise<void> =>
    apiFetch(`/homologation/records/${id}/evaluate`, {
      method: "POST",
      body: { decision, formal_act_ref: decision === "APPROVED" ? evaluateFormalAct || null : null, notes: evaluatorAct || null },
    }).then(async () => {
      notify({ type: "success", title: "Evaluada", description: `Decisión: ${decision}.` });
      setEvaluatorAct("");
      setEvaluateFormalAct("");
      await invalidate();
    });

  if (records.isLoading) {
    return <LoadingState rows={4} />;
  }
  if (records.isError) {
    return (
      <PageContent maxWidth="md">
        <ErrorState message="No fue posible cargar los actos de homologación." onRetry={() => void records.refetch()} />
      </PageContent>
    );
  }

  const columns = [
    columnHelper.accessor("fiscal_version", { header: "Versión fiscal" }),
    columnHelper.accessor("modality", { header: "Modalidad" }),
    columnHelper.accessor("formal_act_ref", { header: "Acto formal" }),
    columnHelper.accessor("status", { header: "Estado" }),
    columnHelper.accessor("homologated", {
      header: "Homologado",
      cell: (info) => (info.getValue() ? "Sí" : "No"),
    }),
    columnHelper.accessor("evaluated_by", { header: "Evaluador" }),
    columnHelper.display({
      id: "actions",
      header: "Acciones",
      cell: (info) => {
        const row = info.row.original;
        return (
          <div className="flex flex-wrap gap-2">
            {row.status === "DRAFT" ? (
              <AsyncButton onClick={() => submit(row.id)} variant="secondary" loadingText="…">
                Someter
              </AsyncButton>
            ) : null}
            {row.status === "SUBMITTED" ? (
              <>
                <AsyncButton onClick={() => evaluate(row.id, "APPROVED")} variant="primary" loadingText="…">
                  Aprobar
                </AsyncButton>
                <AsyncButton onClick={() => evaluate(row.id, "REJECTED")} variant="danger" loadingText="…">
                  Rechazar
                </AsyncButton>
              </>
            ) : null}
          </div>
        );
      },
    }),
  ];

  return (
    <PageContent maxWidth="full">
      <PageHeader
        title="Homologación fiscal"
        description="Registro del acto formal, sometimiento y evaluación con segregación de funciones."
        crumbs={[{ label: "Homologación" }, { label: "Actos" }]}
      />

      <section className="rounded-lg border border-border-default bg-surface-0 p-6">
        <h2 className="text-base font-semibold text-text-900">Registrar acto de homologación</h2>
        <div className="mt-4 grid gap-4 sm:grid-cols-2">
          <FormField label="Versión fiscal">
            <TextInput value={fiscalVersion} onChange={(e) => setFiscalVersion(e.target.value)} placeholder="2026-1.0" />
          </FormField>
          <FormField label="Modalidad">
            <TextInput value={modality} onChange={(e) => setModality(e.target.value)} placeholder="E_FACTURA" />
          </FormField>
          <FormField label="Acto formal (ref.)">
            <TextInput value={formalActRef} onChange={(e) => setFormalActRef(e.target.value)} placeholder="ACT-2026-001" />
          </FormField>
          <FormField label="Evidencia SHA-256">
            <TextInput value={evidenceSha} onChange={(e) => setEvidenceSha(e.target.value)} placeholder="hash de 64 caracteres" />
          </FormField>
          <FormField label="Notas" className="sm:col-span-2">
            <TextInput value={notes} onChange={(e) => setNotes(e.target.value)} placeholder="Observaciones (opcional)" />
          </FormField>
        </div>
        <div className="mt-4">
          <AsyncButton onClick={createRecord} loadingText="Registrando…">
            Registrar acto
          </AsyncButton>
        </div>
      </section>

      <section className="mt-6 rounded-lg border border-border-default bg-surface-0 p-6">
        <h2 className="text-base font-semibold text-text-900">Evaluación</h2>
        <p className="mt-1 text-sm text-text-500">Quien creó la homologación no puede evaluarla (segregación).</p>
        <div className="mt-4 grid gap-4 sm:grid-cols-2">
          <FormField label="Evaluador (id de usuario)">
            <TextInput value={evaluatorAct} onChange={(e) => setEvaluatorAct(e.target.value)} placeholder="fiscal-1" />
          </FormField>
          <FormField label="Acto formal al aprobar">
            <TextInput value={evaluateFormalAct} onChange={(e) => setEvaluateFormalAct(e.target.value)} placeholder="ACT-2026-001" />
          </FormField>
        </div>
      </section>

      <div className="mt-6">
        <DataTable
          columns={columns}
          data={records.data?.items ?? []}
          loading={false}
          error={null}
          getRowId={(row) => row.id}
          emptyTitle="Sin actos de homologación"
          emptyDescription="Registre el primer acto formal para comenzar."
        />
      </div>
    </PageContent>
  );
}
