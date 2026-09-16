/** Conciliación bancaria asistida con reglas y resolución manual auditada (FR-006-030/031). */
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { createColumnHelper } from "@tanstack/react-table";
import { useState } from "react";

import { apiFetch } from "@/api/client";
import type { BankTransactionSummary, FinancialAccountSummary, ReconciliationSummary } from "@/api/types";
import { useNotifications } from "@/app/contexts/NotificationContext";
import { AsyncButton } from "@/components/AsyncButton";
import { Button } from "@/components/Button";
import { DataTable } from "@/components/DataTable";
import { FormField } from "@/components/FormField";
import { PageContent } from "@/layout/PageContent";
import { PageHeader } from "@/components/PageHeader";
import { TextInput } from "@/components/TextInput";
import { formatMoney } from "@/lib/format";

/** Saldo del estado de cuenta: texto exacto del servidor, sin `Number` (FLOAT-038-C). */
const saldo = (valor: string | null): string => (valor === null ? "—" : formatMoney(valor));

const columnHelper = createColumnHelper<ReconciliationSummary>();

export function ConciliacionPage(): React.JSX.Element {
  const queryClient = useQueryClient();
  const { notify } = useNotifications();

  const [accountId, setAccountId] = useState("");
  const [statementRef, setStatementRef] = useState("");
  const [selected, setSelected] = useState<ReconciliationSummary | null>(null);
  const [newTxId, setNewTxId] = useState("");
  const [resolveType, setResolveType] = useState<"MATCHED" | "DIFFERENCE" | "COMMISSION" | "FX">("DIFFERENCE");
  const [resolveLineId, setResolveLineId] = useState("");

  const reconciliations = useQuery({
    queryKey: ["tesoreria", "reconciliations"],
    queryFn: () => apiFetch<{ items: ReconciliationSummary[] }>("/treasury/reconciliations"),
    retry: false,
  });
  const accounts = useQuery({
    queryKey: ["tesoreria", "accounts"],
    queryFn: () => apiFetch<{ items: FinancialAccountSummary[] }>("/treasury/accounts"),
    retry: false,
  });
  const txs = useQuery({
    queryKey: ["tesoreria", "bank-transactions"],
    queryFn: () => apiFetch<{ items: BankTransactionSummary[] }>("/treasury/bank-transactions"),
    retry: false,
  });

  const accountName = (id: string): string => (accounts.data?.items ?? []).find((a) => a.id === id)?.name ?? id;
  const txRef = (id: string | null): string =>
    id ? (txs.data?.items ?? []).find((t) => t.id === id)?.reference ?? id : "—";

  const refresh = (): void => {
    void queryClient.invalidateQueries({ queryKey: ["tesoreria", "reconciliations"] });
  };

  const create = async (): Promise<void> => {
    if (!accountId) {
      notify({ type: "error", title: "Falta la cuenta", description: "Seleccione la cuenta a conciliar." });
      return;
    }
    await apiFetch("/treasury/reconciliations", {
      method: "POST",
      body: { account_id: accountId, statement_ref: statementRef || null },
    });
    notify({ type: "success", title: "Conciliación creada", description: "Agregue líneas del estado de cuenta." });
    setAccountId("");
    setStatementRef("");
    refresh();
  };

  const runAction = async (id: string, action: string): Promise<void> => {
    if (action === "match") {
      const res = await apiFetch<{ matched: number }>(`/treasury/reconciliations/${id}/match`, { method: "POST" });
      notify({ type: "success", title: "Emparejamiento", description: `${res.matched} líneas propuestas por reglas.` });
    } else {
      const targets: Record<string, string> = { in_progress: "IN_PROGRESS", review: "REVIEW", approve: "APPROVED", reject: "REJECTED" };
      await apiFetch(`/treasury/reconciliations/${id}/transition`, { method: "POST", body: { target: targets[action] } });
      notify({ type: "success", title: "Conciliación actualizada", description: `Estado → ${targets[action]}` });
    }
    refresh();
  };

  const addLine = async (): Promise<void> => {
    if (!selected || !newTxId) return;
    await apiFetch(`/treasury/reconciliations/${selected.id}/lines`, {
      method: "POST",
      body: { bank_transaction_id: newTxId },
    });
    notify({ type: "success", title: "Línea agregada", description: "Movimiento del estado de cuenta incorporado." });
    setNewTxId("");
    refresh();
  };

  const resolveLine = async (): Promise<void> => {
    if (!resolveLineId) return;
    await apiFetch(`/treasury/reconciliation-lines/${resolveLineId}/resolve`, {
      method: "POST",
      body: { resolution_type: resolveType },
    });
    notify({ type: "success", title: "Resolución registrada", description: "Resolución manual auditada guardada." });
    setResolveLineId("");
    refresh();
  };

  const columns = [
    columnHelper.accessor("account_id", { header: "Cuenta", cell: (info) => accountName(info.getValue()) }),
    columnHelper.accessor("statement_date", { header: "Fecha estado" }),
    columnHelper.accessor("statement_ref", { header: "Referencia" }),
    columnHelper.accessor("opening_balance", { header: "Inicial", cell: (c) => saldo(c.getValue()) }),
    columnHelper.accessor("closing_balance", { header: "Final", cell: (c) => saldo(c.getValue()) }),
    columnHelper.accessor("status", { header: "Estado" }),
    columnHelper.display({
      id: "actions",
      header: "Acciones",
      cell: ({ row }) => {
        const a = row.original.allowed_actions;
        const actions: Array<[string, string]> = [
          ["match", "emparejar"],
          ["in_progress", "en proceso"],
          ["review", "revisión"],
          ["approve", "aprobar"],
          ["reject", "rechazar"],
        ];
        return (
          <div className="flex justify-end gap-1">
            <Button size="sm" variant="ghost" onClick={() => setSelected(row.original)}>
              detalle
            </Button>
            {actions
              .filter(([key]) => a[key])
              .map(([key, label]) => (
                <AsyncButton key={key} size="sm" variant={key === "reject" ? "danger" : "secondary"} onClick={() => runAction(row.original.id, key)}>
                  {label}
                </AsyncButton>
              ))}
          </div>
        );
      },
    }),
  ];

  const unmatched = (selected?.lines ?? []).filter((l) => l.status === "UNMATCHED");

  return (
    <PageContent maxWidth="full">
      <PageHeader
        title="Conciliación bancaria"
        description="Asistida por reglas (match score) con resolución manual auditada; comisiones y diferencias no alteran el IVA original (FR-006-030/032)."
        crumbs={[{ label: "Tesorería" }, { label: "Conciliación" }]}
      />

      <form
        className="mb-4 flex flex-wrap items-end gap-3 rounded-lg border border-border-default bg-surface-0 p-4"
        onSubmit={(e) => e.preventDefault()}
      >
        <FormField label="Cuenta" className="min-w-56">
          <select
            value={accountId}
            onChange={(e) => setAccountId(e.target.value)}
            className="h-10 w-full rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900"
          >
            <option value="">Seleccionar cuenta…</option>
            {(accounts.data?.items ?? []).map((a) => (
              <option key={a.id} value={a.id}>
                {a.name} ({a.code})
              </option>
            ))}
          </select>
        </FormField>
        <FormField label="Referencia del estado">
          <TextInput value={statementRef} onChange={(e) => setStatementRef(e.target.value)} placeholder="Ej. EXT-2026-08" />
        </FormField>
        <AsyncButton type="submit" variant="secondary" onClick={create}>
          Crear conciliación
        </AsyncButton>
      </form>

      <DataTable
        columns={columns}
        data={reconciliations.data?.items ?? []}
        loading={reconciliations.isLoading}
        error={reconciliations.isError ? "No fue posible cargar las conciliaciones." : null}
        getRowId={(row) => row.id}
        emptyTitle="Sin conciliaciones"
        emptyDescription="Cree una conciliación para una cuenta bancaria."
      />

      {selected ? (
        <div className="mt-4 rounded-lg border border-border-default bg-surface-0 p-4">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-base font-semibold text-text-900">
              Conciliación {selected.statement_ref ?? selected.id.slice(0, 8)} · {selected.status}
            </h2>
            <Button size="sm" variant="ghost" onClick={() => setSelected(null)}>
              cerrar panel
            </Button>
          </div>

          <form
            className="mb-3 flex flex-wrap items-end gap-3"
            onSubmit={(e) => e.preventDefault()}
          >
            <FormField label="Movimiento del estado de cuenta">
              <select
                value={newTxId}
                onChange={(e) => setNewTxId(e.target.value)}
                className="h-10 w-80 rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900"
              >
                <option value="">Seleccionar transacción…</option>
                {(txs.data?.items ?? []).map((t) => (
                  <option key={t.id} value={t.id}>
                    {t.txn_date ?? ""} · {formatMoney(t.amount)} · {t.reference ?? t.source}
                  </option>
                ))}
              </select>
            </FormField>
            <AsyncButton type="submit" variant="secondary" size="sm" onClick={addLine}>
              Agregar línea
            </AsyncButton>
          </form>

          <div className="mb-2 grid gap-1 text-sm">
            {selected.lines.length === 0 ? (
              <p className="text-text-500">Sin líneas aún.</p>
            ) : (
              selected.lines.map((l) => (
                <div key={l.id} className="flex items-center justify-between rounded border border-border-default px-3 py-1.5">
                  <span className="text-text-700">
                    {txRef(l.bank_transaction_id)} · score {l.match_score ?? "—"} · {l.matched_by}
                  </span>
                  <span className="text-text-500">{l.status}</span>
                </div>
              ))
            )}
          </div>

          {unmatched.length > 0 ? (
            <form
              className="flex flex-wrap items-end gap-3"
              onSubmit={(e) => e.preventDefault()}
            >
              <FormField label="Línea sin emparejar">
                <select
                  value={resolveLineId}
                  onChange={(e) => setResolveLineId(e.target.value)}
                  className="h-10 w-72 rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900"
                >
                  <option value="">Seleccionar línea…</option>
                  {unmatched.map((l) => (
                    <option key={l.id} value={l.id}>
                      {txRef(l.bank_transaction_id)}
                    </option>
                  ))}
                </select>
              </FormField>
              <FormField label="Tipo de resolución">
                <select
                  value={resolveType}
                  onChange={(e) => setResolveType(e.target.value as typeof resolveType)}
                  className="h-10 w-48 rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900"
                >
                  <option value="MATCHED">Conciliado</option>
                  <option value="DIFFERENCE">Diferencia</option>
                  <option value="COMMISSION">Comisión</option>
                  <option value="FX">Diferencia cambiaria</option>
                </select>
              </FormField>
              <AsyncButton type="submit" variant="secondary" size="sm" onClick={resolveLine}>
                Resolver manualmente
              </AsyncButton>
            </form>
          ) : null}
        </div>
      ) : null}
    </PageContent>
  );
}
