/** Cajas — sesiones, arqueo, pre-cierre y cierre (FR-006-001/002/003/004, WF-05). */
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { createColumnHelper } from "@tanstack/react-table";
import { useState } from "react";

import { apiFetch } from "@/api/client";
import type { CashSessionSummary, CashboxSummary } from "@/api/types";
import { useNotifications } from "@/app/contexts/NotificationContext";
import { AsyncButton } from "@/components/AsyncButton";
import { Button } from "@/components/Button";
import { DataTable } from "@/components/DataTable";
import { FormField } from "@/components/FormField";
import { MoneyInput } from "@/components/MoneyInput";
import { PageContent } from "@/layout/PageContent";
import { PageHeader } from "@/components/PageHeader";
import { TextInput } from "@/components/TextInput";

const columnHelper = createColumnHelper<CashSessionSummary>();

export function CajasPage(): React.JSX.Element {
  const queryClient = useQueryClient();
  const { notify } = useNotifications();

  // Apertura de caja
  const [cashboxId, setCashboxId] = useState("");
  const [openedAmount, setOpenedAmount] = useState("0");

  // Sesión seleccionada para arqueo/cierre
  const [selected, setSelected] = useState<CashSessionSummary | null>(null);
  const [countedAmount, setCountedAmount] = useState("");
  const [approveDiff, setApproveDiff] = useState(false);
  const [approvalNote, setApprovalNote] = useState("");

  const sessions = useQuery({
    queryKey: ["tesoreria", "cash-sessions"],
    queryFn: () => apiFetch<{ items: CashSessionSummary[] }>("/treasury/cash-sessions"),
    retry: false,
  });
  const cashboxes = useQuery({
    queryKey: ["tesoreria", "cashboxes"],
    queryFn: () => apiFetch<{ items: CashboxSummary[] }>("/treasury/cashboxes"),
    retry: false,
  });

  const refresh = (): void => {
    void queryClient.invalidateQueries({ queryKey: ["tesoreria", "cash-sessions"] });
    void queryClient.invalidateQueries({ queryKey: ["tesoreria", "cashboxes"] });
  };

  const openSession = async (): Promise<void> => {
    if (!cashboxId) {
      notify({ type: "error", title: "Falta la caja", description: "Seleccione la caja a abrir." });
      return;
    }
    await apiFetch("/treasury/cash-sessions", {
      method: "POST",
      body: { cashbox_id: cashboxId, opened_amount: Number(openedAmount) || 0 },
    });
    notify({ type: "success", title: "Caja abierta", description: "La sesión de caja fue abierta." });
    setCashboxId("");
    setOpenedAmount("0");
    refresh();
  };

  const runTransition = async (id: string, endpoint: string, target: string): Promise<void> => {
    await apiFetch(`/treasury/cash-sessions/${id}/${endpoint}`, {
      method: "POST",
      body: endpoint === "reject" ? {} : { target },
    });
    notify({ type: "success", title: "Sesión actualizada", description: `Estado → ${target}` });
    refresh();
  };

  const doArqueo = async (): Promise<void> => {
    if (!selected) return;
    await apiFetch(`/treasury/cash-sessions/${selected.id}/arqueo`, {
      method: "POST",
      body: { counted_amount: Number(countedAmount) || 0 },
    });
    notify({ type: "success", title: "Arqueo registrado", description: "Conteo y diferencia calculados." });
    setSelected(null);
    refresh();
  };

  const doClose = async (): Promise<void> => {
    if (!selected) return;
    await apiFetch(`/treasury/cash-sessions/${selected.id}/close`, {
      method: "POST",
      body: { difference_approved: approveDiff, approval_note: approvalNote || null },
    });
    notify({ type: "success", title: "Caja cerrada", description: "La sesión fue cerrada correctamente." });
    setSelected(null);
    setApproveDiff(false);
    setApprovalNote("");
    refresh();
  };

  const columns = [
    columnHelper.accessor("cashbox_id", { header: "Caja" }),
    columnHelper.accessor("opened_at", { header: "Apertura" }),
    columnHelper.accessor("opened_amount", { header: "Fondo" }),
    columnHelper.accessor("expected_amount", { header: "Esperado" }),
    columnHelper.accessor("counted_amount", { header: "Conteo" }),
    columnHelper.accessor("difference", { header: "Diferencia" }),
    columnHelper.accessor("status", { header: "Estado" }),
    columnHelper.display({
      id: "actions",
      header: "Acciones",
      cell: ({ row }) => {
        const a = row.original.allowed_actions;
        return (
          <div className="flex justify-end gap-1">
            {a.arqueo ? (
              <Button
                size="sm"
                variant="secondary"
                onClick={() => {
                  setSelected(row.original);
                  setCountedAmount(String(row.original.expected_amount ?? 0));
                }}
              >
                arqueo
              </Button>
            ) : null}
            {a.pre_close ? (
              <AsyncButton size="sm" variant="secondary" onClick={() => runTransition(row.original.id, "pre-close", "PRE_CLOSED")}>
                pre-cierre
              </AsyncButton>
            ) : null}
            {a.close ? (
              <Button
                size="sm"
                variant="secondary"
                onClick={() => {
                  setSelected(row.original);
                  setApproveDiff((row.original.difference ?? 0) !== 0);
                }}
              >
                cerrar
              </Button>
            ) : null}
            {a.reject ? (
              <AsyncButton size="sm" variant="danger" onClick={() => runTransition(row.original.id, "reject", "REJECTED")}>
                rechazar
              </AsyncButton>
            ) : null}
          </div>
        );
      },
    }),
  ];

  const diff = selected ? (selected.difference ?? 0) : 0;

  return (
    <PageContent maxWidth="full">
      <PageHeader
        title="Cajas y arqueo"
        description="Sesiones de caja: apertura → movimientos → arqueo → pre-cierre → cierre con diferencias aprobadas (FR-006-002/003)."
        crumbs={[{ label: "Tesorería" }, { label: "Cajas" }]}
      />

      <form
        className="mb-4 flex flex-wrap items-end gap-3 rounded-lg border border-border-default bg-surface-0 p-4"
        onSubmit={(e) => e.preventDefault()}
      >
        <FormField label="Caja" className="min-w-56">
          <select
            value={cashboxId}
            onChange={(e) => setCashboxId(e.target.value)}
            className="h-10 w-full rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900"
          >
            <option value="">Seleccionar caja…</option>
            {(cashboxes.data?.items ?? []).map((c) => (
              <option key={c.id} value={c.id}>
                {c.name} ({c.code})
              </option>
            ))}
          </select>
        </FormField>
        <FormField label="Fondo inicial">
          <MoneyInput value={openedAmount} onChange={(e) => setOpenedAmount(e.target.value)} />
        </FormField>
        <AsyncButton type="submit" variant="secondary" onClick={openSession}>
          Abrir caja
        </AsyncButton>
      </form>

      <DataTable
        columns={columns}
        data={sessions.data?.items ?? []}
        loading={sessions.isLoading}
        error={sessions.isError ? "No fue posible cargar las sesiones de caja." : null}
        getRowId={(row) => row.id}
        emptyTitle="Sin sesiones de caja"
        emptyDescription="Abra una caja para iniciar una sesión."
      />

      {selected ? (
        <div className="mt-4 rounded-lg border border-border-default bg-surface-0 p-4">
          <h2 className="mb-2 text-base font-semibold text-text-900">
            {selected.status === "ARCHED" ? "Arqueo" : "Cierre"} de sesión
          </h2>
          <p className="mb-3 text-sm text-text-500">
            Esperado: {selected.expected_amount.toFixed(2)} · Conteo actual: {selected.counted_amount ?? "—"} ·
            Diferencia: {diff.toFixed(2)}
          </p>
          {selected.status === "ARCHED" ? (
            <form
              className="flex flex-wrap items-end gap-3"
              onSubmit={(e) => e.preventDefault()}
            >
              <FormField label="Conteo">
                <MoneyInput value={countedAmount} onChange={(e) => setCountedAmount(e.target.value)} />
              </FormField>
              <Button variant="secondary" onClick={() => setSelected(null)}>
                Cancelar
              </Button>
              <AsyncButton type="submit" variant="primary" onClick={doArqueo}>
                Registrar arqueo
              </AsyncButton>
            </form>
          ) : null}
          {selected.status === "PRE_CLOSED" ? (
            <form
              className="flex flex-wrap items-end gap-3"
              onSubmit={(e) => e.preventDefault()}
            >
              {diff !== 0 ? (
                <FormField label="Aprobar diferencia">
                  <label className="flex h-10 items-center gap-2 text-sm text-text-700">
                    <input type="checkbox" checked={approveDiff} onChange={(e) => setApproveDiff(e.target.checked)} />
                    Aprobar diferencia de {diff.toFixed(2)}
                  </label>
                </FormField>
              ) : null}
              <FormField label="Justificación" className="min-w-56">
                <TextInput value={approvalNote} onChange={(e) => setApprovalNote(e.target.value)} placeholder="Opcional" />
              </FormField>
              <Button variant="secondary" onClick={() => setSelected(null)}>
                Cancelar
              </Button>
              <AsyncButton type="submit" variant="primary" onClick={doClose} disabled={diff !== 0 && !approveDiff}>
                Cerrar caja
              </AsyncButton>
            </form>
          ) : null}
        </div>
      ) : null}
    </PageContent>
  );
}
