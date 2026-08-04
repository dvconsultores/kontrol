/** Ingresos y egresos — ejecución de pagos/cobros contra caja o banco (FR-006-020/021/022). */
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { createColumnHelper } from "@tanstack/react-table";
import { useState } from "react";

import { apiFetch } from "@/api/client";
import type {
  BankTransactionSummary,
  CashboxSummary,
  FinancialAccountSummary,
  PaymentSummary,
} from "@/api/types";
import { useNotifications } from "@/app/contexts/NotificationContext";
import { AsyncButton } from "@/components/AsyncButton";
import { DataTable } from "@/components/DataTable";
import { FormField } from "@/components/FormField";
import { MoneyInput } from "@/components/MoneyInput";
import { PageContent } from "@/layout/PageContent";
import { PageHeader } from "@/components/PageHeader";
import { TextInput } from "@/components/TextInput";

const columnHelper = createColumnHelper<BankTransactionSummary>();

export function IngresosEgresosPage(): React.JSX.Element {
  const queryClient = useQueryClient();
  const { notify } = useNotifications();

  const [egresoPayment, setEgresoPayment] = useState("");
  const [ingresoPayment, setIngresoPayment] = useState("");
  const [targetType, setTargetType] = useState<"CASHBOX" | "ACCOUNT">("ACCOUNT");
  const [targetId, setTargetId] = useState("");

  const [accountId, setAccountId] = useState("");
  const [amount, setAmount] = useState("");
  const [reference, setReference] = useState("");
  const [direction, setDirection] = useState<"IN" | "OUT">("OUT");

  const txs = useQuery({
    queryKey: ["tesoreria", "bank-transactions"],
    queryFn: () => apiFetch<{ items: BankTransactionSummary[] }>("/treasury/bank-transactions"),
    retry: false,
  });
  const accounts = useQuery({
    queryKey: ["tesoreria", "accounts"],
    queryFn: () => apiFetch<{ items: FinancialAccountSummary[] }>("/treasury/accounts"),
    retry: false,
  });
  const cashboxes = useQuery({
    queryKey: ["tesoreria", "cashboxes"],
    queryFn: () => apiFetch<{ items: CashboxSummary[] }>("/treasury/cashboxes"),
    retry: false,
  });
  const pagos = useQuery({
    queryKey: ["compras", "payments"],
    queryFn: () => apiFetch<{ items: PaymentSummary[] }>("/purchasing/payments"),
    retry: false,
  });
  const cobros = useQuery({
    queryKey: ["ventas", "collections"],
    queryFn: () => apiFetch<{ items: PaymentSummary[] }>("/sales/collections"),
    retry: false,
  });

  const refresh = (): void => {
    void queryClient.invalidateQueries({ queryKey: ["tesoreria", "bank-transactions"] });
    void queryClient.invalidateQueries({ queryKey: ["compras", "payments"] });
    void queryClient.invalidateQueries({ queryKey: ["ventas", "collections"] });
  };

  const targets = targetType === "CASHBOX" ? cashboxes.data?.items ?? [] : accounts.data?.items ?? [];
  const targetLabel = (id: string): string => {
    const found = targets.find((t) => t.id === id);
    return found ? found.name : id;
  };

  const execute = async (kind: "egresos" | "ingresos", paymentId: string): Promise<void> => {
    if (!paymentId || !targetId) {
      notify({ type: "error", title: "Faltan datos", description: "Seleccione el pago/cobro y el destino." });
      return;
    }
    const res = await apiFetch<{ idempotent: boolean }>(`/treasury/executions/${kind}`, {
      method: "POST",
      body: { payment_id: paymentId, target_type: targetType, target_id: targetId },
      idempotencyKey: `exec-${kind}-${paymentId}`,
    });
    notify({
      type: "success",
      title: kind === "egresos" ? "Egreso ejecutado" : "Ingreso ejecutado",
      description: res.idempotent ? "Operación ya ejecutada (idempotente)." : "Transacción registrada en caja o banco.",
    });
    setEgresoPayment("");
    setIngresoPayment("");
    refresh();
  };

  const createTransaction = async (): Promise<void> => {
    if (!accountId) {
      notify({ type: "error", title: "Falta la cuenta", description: "Seleccione la cuenta bancaria." });
      return;
    }
    await apiFetch("/treasury/bank-transactions", {
      method: "POST",
      body: {
        account_id: accountId,
        direction,
        amount: Number(amount) || 0,
        reference: reference || null,
        source: "ADJUSTMENT",
      },
    });
    notify({ type: "success", title: "Transacción registrada", description: "Movimiento bancario creado." });
    setAmount("");
    setReference("");
    refresh();
  };

  const columns = [
    columnHelper.accessor("account_id", { header: "Cuenta", cell: (info) => targetLabel(info.getValue()) }),
    columnHelper.accessor("txn_date", { header: "Fecha" }),
    columnHelper.accessor("direction", { header: "Dir" }),
    columnHelper.accessor("amount", { header: "Monto" }),
    columnHelper.accessor("reference", { header: "Referencia" }),
    columnHelper.accessor("source", { header: "Fuente" }),
    columnHelper.accessor("status", { header: "Estado" }),
  ];

  return (
    <PageContent maxWidth="full">
      <PageHeader
        title="Ingresos y egresos"
        description="Ejecución de pagos (004) y cobros (005) contra caja o banco, separados de la factura y de la obligación (FR-006-020)."
        crumbs={[{ label: "Tesorería" }, { label: "Ingresos y egresos" }]}
      />

      <div className="mb-4 grid gap-4 lg:grid-cols-2">
        <form
          className="rounded-lg border border-border-default bg-surface-0 p-4"
          onSubmit={(e) => e.preventDefault()}
        >
          <h2 className="mb-2 text-base font-semibold text-text-900">Egreso (pago de 004)</h2>
          <div className="grid gap-3">
            <FormField label="Pago aprobado">
              <select
                value={egresoPayment}
                onChange={(e) => setEgresoPayment(e.target.value)}
                className="h-10 w-full rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900"
              >
                <option value="">Seleccionar pago…</option>
                {(pagos.data?.items ?? []).map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.currency} {p.amount.toFixed(2)} · {p.status}
                  </option>
                ))}
              </select>
            </FormField>
            <FormField label="Destino">
              <select
                value={targetType}
                onChange={(e) => {
                  setTargetType(e.target.value as "CASHBOX" | "ACCOUNT");
                  setTargetId("");
                }}
                className="h-10 w-full rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900"
              >
                <option value="ACCOUNT">Cuenta bancaria</option>
                <option value="CASHBOX">Caja</option>
              </select>
            </FormField>
            <FormField label={targetType === "CASHBOX" ? "Caja" : "Cuenta"}>
              <select
                value={targetId}
                onChange={(e) => setTargetId(e.target.value)}
                className="h-10 w-full rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900"
              >
                <option value="">Seleccionar…</option>
                {targets.map((t) => (
                  <option key={t.id} value={t.id}>
                    {t.name} ({t.code})
                  </option>
                ))}
              </select>
            </FormField>
            <AsyncButton type="submit" variant="secondary" onClick={() => execute("egresos", egresoPayment)}>
              Ejecutar egreso
            </AsyncButton>
          </div>
        </form>

        <form
          className="rounded-lg border border-border-default bg-surface-0 p-4"
          onSubmit={(e) => e.preventDefault()}
        >
          <h2 className="mb-2 text-base font-semibold text-text-900">Ingreso (cobro de 005)</h2>
          <div className="grid gap-3">
            <FormField label="Cobro aprobado">
              <select
                value={ingresoPayment}
                onChange={(e) => setIngresoPayment(e.target.value)}
                className="h-10 w-full rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900"
              >
                <option value="">Seleccionar cobro…</option>
                {(cobros.data?.items ?? []).map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.currency} {p.amount.toFixed(2)} · {p.status}
                  </option>
                ))}
              </select>
            </FormField>
            <FormField label="Destino">
              <select
                value={targetType}
                onChange={(e) => {
                  setTargetType(e.target.value as "CASHBOX" | "ACCOUNT");
                  setTargetId("");
                }}
                className="h-10 w-full rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900"
              >
                <option value="ACCOUNT">Cuenta bancaria</option>
                <option value="CASHBOX">Caja</option>
              </select>
            </FormField>
            <FormField label={targetType === "CASHBOX" ? "Caja" : "Cuenta"}>
              <select
                value={targetId}
                onChange={(e) => setTargetId(e.target.value)}
                className="h-10 w-full rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900"
              >
                <option value="">Seleccionar…</option>
                {targets.map((t) => (
                  <option key={t.id} value={t.id}>
                    {t.name} ({t.code})
                  </option>
                ))}
              </select>
            </FormField>
            <AsyncButton type="submit" variant="secondary" onClick={() => execute("ingresos", ingresoPayment)}>
              Ejecutar ingreso
            </AsyncButton>
          </div>
        </form>
      </div>

      <form
        className="mb-4 flex flex-wrap items-end gap-3 rounded-lg border border-border-default bg-surface-0 p-4"
        onSubmit={(e) => e.preventDefault()}
      >
        <FormField label="Cuenta" className="min-w-52">
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
        <FormField label="Tipo">
          <select
            value={direction}
            onChange={(e) => setDirection(e.target.value as "IN" | "OUT")}
            className="h-10 w-full rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900"
          >
            <option value="OUT">Egreso</option>
            <option value="IN">Ingreso</option>
          </select>
        </FormField>
        <FormField label="Monto">
          <MoneyInput value={amount} onChange={(e) => setAmount(e.target.value)} />
        </FormField>
        <FormField label="Referencia">
          <TextInput value={reference} onChange={(e) => setReference(e.target.value)} placeholder="Opcional" />
        </FormField>
        <AsyncButton type="submit" variant="secondary" onClick={createTransaction}>
          Registrar ajuste
        </AsyncButton>
      </form>

      <DataTable
        columns={columns}
        data={txs.data?.items ?? []}
        loading={txs.isLoading}
        error={txs.isError ? "No fue posible cargar las transacciones bancarias." : null}
        getRowId={(row) => row.id}
        emptyTitle="Sin transacciones bancarias"
        emptyDescription="Ejecute ingresos/egresos o registre ajustes."
      />
    </PageContent>
  );
}
