/** Evaluación regulatoria del despacho y contingencias (FR-008-020/022/030). */
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { createColumnHelper } from "@tanstack/react-table";
import { useState } from "react";

import { apiFetch } from "@/api/client";
import type { RegulatoryContingencySummary, RegulatoryEvaluationSummary, ShipmentSummary } from "@/api/types";
import { Autorizado } from "@/components/Autorizado";
import { useAutoridad } from "@/app/autoridad/AutoridadContext";
import { useNotifications } from "@/app/contexts/NotificationContext";
import { AsyncButton } from "@/components/AsyncButton";
import { DataTable } from "@/components/DataTable";
import { FormField } from "@/components/FormField";
import { PageContent } from "@/layout/PageContent";
import { PageHeader } from "@/components/PageHeader";
import { TextInput } from "@/components/TextInput";

const columnHelper = createColumnHelper<RegulatoryEvaluationSummary>();

export function EvaluacionPage(): React.JSX.Element {
  const queryClient = useQueryClient();
  const { notify } = useNotifications();
  const { puede } = useAutoridad();

  const [shipmentId, setShipmentId] = useState("");
  const [ruleRef, setRuleRef] = useState("");
  const [reason, setReason] = useState("");

  const shipments = useQuery({
    queryKey: ["ventas", "despachos"],
    queryFn: () => apiFetch<{ items: ShipmentSummary[] }>("/sales/shipments"),
    retry: false,
  });
  const evaluations = useQuery({
    queryKey: ["regulatorio", "evaluations"],
    queryFn: () => apiFetch<{ items: RegulatoryEvaluationSummary[] }>("/regulatory/evaluations"),
    retry: false,
  });
  const contingencies = useQuery({
    queryKey: ["regulatorio", "contingencies"],
    queryFn: () => apiFetch<{ items: RegulatoryContingencySummary[] }>("/regulatory/contingencies"),
    retry: false,
  });

  const refresh = (): void => {
    void queryClient.invalidateQueries({ queryKey: ["regulatorio"] });
  };

  const evaluate = async (): Promise<void> => {
    if (!shipmentId) {
      notify({ type: "error", title: "Falta el despacho", description: "Seleccione un despacho." });
      return;
    }
    const res = await apiFetch<{ status: string; blocked: number }>("/regulatory/evaluations", {
      method: "POST",
      body: { shipment_id: shipmentId },
    });
    notify({
      type: res.status === "BLOCKED" ? "error" : "success",
      title: "Evaluación regulatoria",
      description: res.status === "BLOCKED" ? `Despacho BLOQUEADO (${res.blocked} bloqueos).` : "Despacho sin bloqueos.",
    });
    refresh();
  };

  const override = async (id: string): Promise<void> => {
    await apiFetch(`/regulatory/evaluations/${id}/override`, { method: "POST", body: { reason: "Autorización de salida" } });
    notify({ type: "success", title: "Bloqueo anulado", description: "Salida autorizada (auditado)." });
    refresh();
  };

  const createContingency = async (): Promise<void> => {
    await apiFetch("/regulatory/contingencies", { method: "POST", body: { rule_ref: ruleRef, reason } });
    notify({ type: "success", title: "Contingencia activada", description: `Regla ${ruleRef}` });
    setRuleRef("");
    setReason("");
    refresh();
  };

  const endContingency = async (id: string): Promise<void> => {
    await apiFetch(`/regulatory/contingencies/${id}/end`, { method: "POST" });
    notify({ type: "success", title: "Contingencia finalizada", description: "Regla de contingencia desactivada." });
    refresh();
  };

  const columns = [
    columnHelper.accessor("shipment_id", { header: "Despacho" }),
    columnHelper.accessor("required", { header: "Requerido" }),
    columnHelper.accessor("blockers", { header: "Bloqueos" }),
    columnHelper.accessor("status", { header: "Estado" }),
    columnHelper.display({
      id: "actions",
      header: "Acciones",
      cell: ({ row }) =>
        row.original.status === "BLOCKED" && puede("POST", `/regulatory/evaluations/${row.original.id}/override`) ? (
          <div className="flex justify-end">
            <AsyncButton size="sm" variant="secondary" onClick={() => override(row.original.id)}>anular bloqueo</AsyncButton>
          </div>
        ) : null,
    }),
  ];

  return (
    <PageContent maxWidth="full">
      <PageHeader
        title="Evaluación regulatoria"
        description="Cada línea de despacho evalúa sus requisitos (SICA/SIGESAI/SACS); el despacho se bloquea ante faltante/vencido/no coincidencia (FR-008-020/022)."
        crumbs={[{ label: "Regulatorio" }, { label: "Evaluación" }]}
      />

      <Autorizado operacion={["POST", "/regulatory/evaluations"]}>
        <form
          className="mb-4 flex flex-wrap items-end gap-3 rounded-lg border border-border-default bg-surface-0 p-4"
          onSubmit={(e) => e.preventDefault()}
        >
          <FormField label="Despacho (005)" className="min-w-64">
            <select value={shipmentId} onChange={(e) => setShipmentId(e.target.value)} className="h-10 w-full rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900">
              <option value="">Seleccionar despacho…</option>
              {(shipments.data?.items ?? []).map((s) => (
                <option key={s.id} value={s.id}>{s.code} · {s.status}</option>
              ))}
            </select>
          </FormField>
          <AsyncButton type="submit" variant="secondary" onClick={evaluate}>
            Evaluar despacho
          </AsyncButton>
        </form>
      </Autorizado>

      <DataTable
        columns={columns}
        data={evaluations.data?.items ?? []}
        loading={evaluations.isLoading}
        error={evaluations.isError ? "No fue posible cargar las evaluaciones." : null}
        getRowId={(row) => row.id}
        emptyTitle="Sin evaluaciones"
        emptyDescription="Evalúe un despacho para consolidar sus requisitos."
      />

      <div className="mb-4 rounded-lg border border-border-default bg-surface-0 p-4">
        <h2 className="mb-2 text-base font-semibold text-text-900">Contingencia (solo con regla oficial versionada)</h2>
        <Autorizado operacion={["POST", "/regulatory/contingencies"]}>
          <form className="flex flex-wrap items-end gap-3" onSubmit={(e) => e.preventDefault()}>
            <FormField label="Regla oficial">
              <TextInput value={ruleRef} onChange={(e) => setRuleRef(e.target.value)} placeholder="Ej. OFICIAL-2026-01" />
            </FormField>
            <FormField label="Motivo">
              <TextInput value={reason} onChange={(e) => setReason(e.target.value)} placeholder="Ej. corte de suministro" />
            </FormField>
            <AsyncButton type="submit" variant="secondary" onClick={createContingency}>Activar</AsyncButton>
          </form>
        </Autorizado>
        <div className="mt-3">
          {(contingencies.data?.items ?? []).map((c) => (
            <div key={c.id} className="flex items-center justify-between border-b border-border-default px-4 py-2 text-sm last:border-b-0">
              <span className="text-text-700">{c.rule_ref} · {c.reason}</span>
              <span className="flex items-center gap-2 text-text-500">
                {c.status}
                {c.status === "ACTIVE" && puede("POST", `/regulatory/contingencies/${c.id}/end`) ? <AsyncButton size="sm" variant="secondary" onClick={() => endContingency(c.id)}>finalizar</AsyncButton> : null}
              </span>
            </div>
          ))}
          {(contingencies.data?.items ?? []).length === 0 ? <p className="text-sm text-text-500">Sin contingencias.</p> : null}
        </div>
      </div>
    </PageContent>
  );
}
