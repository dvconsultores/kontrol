/** Cajas — sesiones, arqueo, pre-cierre y cierre (FR-006-001/002/003/004, WF-05). */
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { createColumnHelper } from "@tanstack/react-table";
import { useState } from "react";

import { apiFetch } from "@/api/client";
import type { CashSessionSummary, CashboxSummary } from "@/api/types";
import { useAutoridad } from "@/app/autoridad/AutoridadContext";
import { useNotifications } from "@/app/contexts/NotificationContext";
import { AsyncButton } from "@/components/AsyncButton";
import { Button } from "@/components/Button";
import { DataTable } from "@/components/DataTable";
import { FormField } from "@/components/FormField";
import { MoneyInput } from "@/components/MoneyInput";
import { PageContent } from "@/layout/PageContent";
import { PageHeader } from "@/components/PageHeader";
import { TextInput } from "@/components/TextInput";
import { isZeroDecimal, toDecimalString } from "@/lib/decimal";
import { formatMoney } from "@/lib/format";

const columnHelper = createColumnHelper<CashSessionSummary>();

/** Importe de la sesión para mostrar: texto exacto del servidor, sin `Number` (Spec 038 · FLOAT-038-B). */
const importe = (valor: string | null): string => (valor === null ? "—" : formatMoney(valor));

export function CajasPage(): React.JSX.Element {
  const queryClient = useQueryClient();
  const { notify } = useNotifications();
  const { puede } = useAutoridad();

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
    // Spec 038 · FLOAT-038-C: el fondo de apertura sale como texto exacto. `Number`
    // lo habría redondeado en el navegador, antes de que nadie pudiera validarlo.
    const apertura = toDecimalString(openedAmount);
    if (apertura === null) {
      notify({ type: "error", title: "Importe inválido", description: "Use números con hasta dos decimales, por ejemplo 1234,56." });
      return;
    }
    await apiFetch("/treasury/cash-sessions", {
      method: "POST",
      body: { cashbox_id: cashboxId, opened_amount: apertura },
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
    // Spec 038 · FLOAT-038-B: el conteo viaja como texto exacto; `Number` lo habría
    // redondeado antes de salir del navegador.
    const conteo = toDecimalString(countedAmount);
    if (!conteo) {
      notify({ type: "error", title: "Conteo inválido", description: "Use números con hasta dos decimales, por ejemplo 1234,56." });
      return;
    }
    await apiFetch(`/treasury/cash-sessions/${selected.id}/arqueo`, {
      method: "POST",
      body: { counted_amount: conteo },
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
    columnHelper.accessor("opened_amount", { header: "Fondo", cell: (info) => importe(info.getValue()) }),
    columnHelper.accessor("expected_amount", { header: "Esperado", cell: (info) => importe(info.getValue()) }),
    columnHelper.accessor("counted_amount", { header: "Conteo", cell: (info) => importe(info.getValue()) }),
    columnHelper.accessor("difference", { header: "Diferencia", cell: (info) => importe(info.getValue()) }),
    columnHelper.accessor("status", { header: "Estado" }),
    columnHelper.display({
      id: "actions",
      header: "Acciones",
      cell: ({ row }) => {
        const a = row.original.allowed_actions;
        return (
          <div className="flex justify-end gap-1">
            {a.arqueo && puede("POST", `/treasury/cash-sessions/${row.original.id}/arqueo`) ? (
              <Button
                size="sm"
                variant="secondary"
                onClick={() => {
                  setSelected(row.original);
                  setCountedAmount(row.original.expected_amount);
                }}
              >
                arqueo
              </Button>
            ) : null}
            {a.pre_close && puede("POST", `/treasury/cash-sessions/${row.original.id}/pre-close`) ? (
              <AsyncButton size="sm" variant="secondary" onClick={() => runTransition(row.original.id, "pre-close", "PRE_CLOSED")}>
                pre-cierre
              </AsyncButton>
            ) : null}
            {a.close && puede("POST", `/treasury/cash-sessions/${row.original.id}/close`) ? (
              <Button
                size="sm"
                variant="secondary"
                onClick={() => {
                  setSelected(row.original);
                  setApproveDiff(!isZeroDecimal(row.original.difference));
                }}
              >
                cerrar
              </Button>
            ) : null}
            {a.reject && puede("POST", `/treasury/cash-sessions/${row.original.id}/reject`) ? (
              <AsyncButton size="sm" variant="danger" onClick={() => runTransition(row.original.id, "reject", "REJECTED")}>
                rechazar
              </AsyncButton>
            ) : null}
          </div>
        );
      },
    }),
  ];

  // Cero exacto, sobre el texto del servidor: un céntimo es diferencia.
  const hayDiferencia = selected ? !isZeroDecimal(selected.difference) : false;

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
        hidden={!puede("POST", "/treasury/cash-sessions")}
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
            {selected.status === "PRE_CLOSED" ? "Cierre" : "Arqueo"} de sesión
          </h2>
          <p className="mb-3 text-sm text-text-500">
            Esperado: {importe(selected.expected_amount)} · Conteo actual: {importe(selected.counted_amount)} ·
            Diferencia: {importe(selected.difference)}
          </p>
          {/* El arqueo se hace sobre una sesión abierta: es la única que lo permite. */}
          {selected.status === "OPEN" && puede("POST", `/treasury/cash-sessions/${selected.id}/arqueo`) ? (
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
          {selected.status === "PRE_CLOSED" && puede("POST", `/treasury/cash-sessions/${selected.id}/close`) ? (
            <form
              className="flex flex-wrap items-end gap-3"
              onSubmit={(e) => e.preventDefault()}
            >
              {hayDiferencia ? (
                <FormField label="Aprobar diferencia">
                  <label className="flex h-10 items-center gap-2 text-sm text-text-700">
                    <input type="checkbox" checked={approveDiff} onChange={(e) => setApproveDiff(e.target.checked)} />
                    Aprobar diferencia de {importe(selected.difference)}
                  </label>
                </FormField>
              ) : null}
              <FormField label="Justificación" className="min-w-56">
                <TextInput value={approvalNote} onChange={(e) => setApprovalNote(e.target.value)} placeholder="Opcional" />
              </FormField>
              <Button variant="secondary" onClick={() => setSelected(null)}>
                Cancelar
              </Button>
              <AsyncButton type="submit" variant="primary" onClick={doClose} disabled={hayDiferencia && !approveDiff}>
                Cerrar caja
              </AsyncButton>
            </form>
          ) : null}
        </div>
      ) : null}
    </PageContent>
  );
}
