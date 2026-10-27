/** Aprobaciones regulatorias — solicitudes y transiciones (FR-008-040, WF-09). */
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { createColumnHelper } from "@tanstack/react-table";
import { useState } from "react";

import { apiFetch } from "@/api/client";
import type { ApprovalRequestSummary } from "@/api/types";
import { Autorizado } from "@/components/Autorizado";
import { useAutoridad } from "@/app/autoridad/AutoridadContext";
import { useNotifications } from "@/app/contexts/NotificationContext";
import { AsyncButton } from "@/components/AsyncButton";
import { DataTable } from "@/components/DataTable";
import { FormField } from "@/components/FormField";
import { PageContent } from "@/layout/PageContent";
import { PageHeader } from "@/components/PageHeader";
import { TextInput } from "@/components/TextInput";

const columnHelper = createColumnHelper<ApprovalRequestSummary>();

const RISK_LEVELS = ["BAJO", "MEDIO", "ALTO", "CRITICO"];

export function AprobacionesPage(): React.JSX.Element {
  const queryClient = useQueryClient();
  const { notify } = useNotifications();
  const { puede } = useAutoridad();

  const [objRef, setObjRef] = useState("");
  const [ruleRef, setRuleRef] = useState("");
  const [risk, setRisk] = useState("BAJO");
  const [amount, setAmount] = useState("");
  const [deadline, setDeadline] = useState("");

  const query = useQuery({
    queryKey: ["regulatorio", "approval-requests"],
    queryFn: () => apiFetch<{ items: ApprovalRequestSummary[] }>("/regulatory/approval-requests"),
    retry: false,
  });

  const refresh = (): void => {
    void queryClient.invalidateQueries({ queryKey: ["regulatorio", "approval-requests"] });
  };

  const createRequest = async (): Promise<void> => {
    try {
      await apiFetch("/regulatory/approval-requests", {
        method: "POST",
        body: {
          object_ref: objRef, rule_ref: ruleRef || null, risk, amount: amount ? Number(amount) : null,
          deadline: deadline || null,
        },
      });
      notify({ type: "success", title: "Solicitud creada", description: objRef });
      setObjRef(""); setRuleRef(""); setAmount(""); setDeadline("");
      refresh();
    } catch (err) {
      const message = err instanceof Error ? err.message : "No fue posible crear la solicitud";
      notify({ type: "error", title: "No fue posible crear la solicitud", description: message });
    }
  };

  const runTransition = async (id: string, target: string): Promise<void> => {
    await apiFetch(`/regulatory/approval-requests/${id}/transition`, { method: "POST", body: { target } });
    notify({ type: "success", title: "Solicitud actualizada", description: `Decisión → ${target}` });
    refresh();
  };

  const columns = [
    columnHelper.accessor("object_ref", { header: "Objeto" }),
    columnHelper.accessor("rule_ref", { header: "Regla" }),
    columnHelper.accessor("risk", { header: "Riesgo" }),
    columnHelper.accessor("amount", { header: "Monto", cell: (info) => info.getValue()?.toFixed(2) ?? "—" }),
    columnHelper.accessor("status", { header: "Estado" }),
    columnHelper.accessor("decision", { header: "Decisión" }),
    columnHelper.display({
      id: "actions",
      header: "Acciones",
      cell: ({ row }) =>
        row.original.status === "PENDING" && puede("POST", `/regulatory/approval-requests/${row.original.id}/transition`) ? (
          <div className="flex justify-end gap-1">
            <AsyncButton size="sm" variant="secondary" onClick={() => runTransition(row.original.id, "APPROVED")}>
              aprobar
            </AsyncButton>
            <AsyncButton size="sm" variant="secondary" onClick={() => runTransition(row.original.id, "REJECTED")}>
              rechazar
            </AsyncButton>
          </div>
        ) : null,
    }),
  ];

  return (
    <PageContent maxWidth="full">
      <PageHeader
        title="Aprobaciones regulatorias"
        description="Solicitudes de aprobación por regla oficial: crear, aprobar o rechazar (auditado)."
        crumbs={[{ label: "Regulatorio" }, { label: "Aprobaciones" }]}
      />
      <Autorizado operacion={["POST", "/regulatory/approval-requests"]}>
        <section className="mb-4 rounded-lg border border-border-default bg-surface-0 p-4">
          <h2 className="mb-2 text-base font-semibold text-text-900">Nueva solicitud</h2>
          <form className="flex flex-wrap items-end gap-3" onSubmit={(e) => e.preventDefault()}>
            <FormField label="Objeto" required>
              <TextInput value={objRef} onChange={(e) => setObjRef(e.target.value)} placeholder="Ej. Despacho DESP-0001" required />
            </FormField>
            <FormField label="Regla oficial">
              <TextInput value={ruleRef} onChange={(e) => setRuleRef(e.target.value)} placeholder="OFICIAL-2026-01" />
            </FormField>
            <FormField label="Riesgo">
              <select value={risk} onChange={(e) => setRisk(e.target.value)} className="h-10 w-44 rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900">
                {RISK_LEVELS.map((r) => (
                  <option key={r} value={r}>{r}</option>
                ))}
              </select>
            </FormField>
            <FormField label="Monto">
              <TextInput type="number" value={amount} onChange={(e) => setAmount(e.target.value)} placeholder="0,00" />
            </FormField>
            <FormField label="Vence">
              <TextInput type="date" value={deadline} onChange={(e) => setDeadline(e.target.value)} />
            </FormField>
            <AsyncButton type="submit" variant="primary" onClick={createRequest}>Crear solicitud</AsyncButton>
          </form>
        </section>
      </Autorizado>

      <DataTable
        columns={columns}
        data={query.data?.items ?? []}
        loading={query.isLoading}
        error={query.isError ? "No fue posible cargar las solicitudes." : null}
        getRowId={(row) => row.id}
        emptyTitle="Sin solicitudes"
        emptyDescription="Aún no hay solicitudes de aprobación."
      />
    </PageContent>
  );
}
