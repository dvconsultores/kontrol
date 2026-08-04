/** Transferencias y depósitos entre cajas/cuentas (FR-006-023). */
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { createColumnHelper } from "@tanstack/react-table";
import { useState } from "react";

import { apiFetch } from "@/api/client";
import type { CashboxSummary, FinancialAccountSummary, TreasuryTransferSummary } from "@/api/types";
import { useNotifications } from "@/app/contexts/NotificationContext";
import { AsyncButton } from "@/components/AsyncButton";
import { DataTable } from "@/components/DataTable";
import { FormField } from "@/components/FormField";
import { MoneyInput } from "@/components/MoneyInput";
import { PageContent } from "@/layout/PageContent";
import { PageHeader } from "@/components/PageHeader";
import { TextInput } from "@/components/TextInput";

const columnHelper = createColumnHelper<TreasuryTransferSummary>();

type Leg = { type: "CASHBOX" | "ACCOUNT"; id: string };

export function TransferenciasPage(): React.JSX.Element {
  const queryClient = useQueryClient();
  const { notify } = useNotifications();

  const [from, setFrom] = useState<Leg>({ type: "ACCOUNT", id: "" });
  const [to, setTo] = useState<Leg>({ type: "ACCOUNT", id: "" });
  const [amount, setAmount] = useState("");
  const [reference, setReference] = useState("");

  const transfers = useQuery({
    queryKey: ["tesoreria", "transfers"],
    queryFn: () => apiFetch<{ items: TreasuryTransferSummary[] }>("/treasury/transfers"),
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

  const optionsFor = (leg: Leg): Array<{ id: string; label: string }> =>
    leg.type === "CASHBOX"
      ? (cashboxes.data?.items ?? []).map((c) => ({ id: c.id, label: `${c.name} (${c.code})` }))
      : (accounts.data?.items ?? []).map((a) => ({ id: a.id, label: `${a.name} (${a.code})` }));

  const nameOf = (leg: Leg | null): string => {
    if (!leg) return "—";
    return optionsFor(leg).find((o) => o.id === leg.id)?.label ?? leg.id;
  };

  const submit = async (): Promise<void> => {
    if (!from.id || !to.id) {
      notify({ type: "error", title: "Faltan datos", description: "Seleccione origen y destino." });
      return;
    }
    await apiFetch("/treasury/transfers", {
      method: "POST",
      body: {
        amount: Number(amount) || 0,
        currency: "VED",
        from_cashbox_id: from.type === "CASHBOX" ? from.id : null,
        from_account_id: from.type === "ACCOUNT" ? from.id : null,
        to_cashbox_id: to.type === "CASHBOX" ? to.id : null,
        to_account_id: to.type === "ACCOUNT" ? to.id : null,
        reference: reference || null,
      },
    });
    notify({ type: "success", title: "Transferencia registrada", description: "Movimientos de origen y destino creados." });
    setAmount("");
    setReference("");
    void queryClient.invalidateQueries({ queryKey: ["tesoreria", "transfers"] });
  };

  const columns = [
    columnHelper.accessor("from_cashbox_id", {
      header: "Origen",
      cell: ({ row }) => nameOf(
        row.original.from_cashbox_id
          ? { type: "CASHBOX", id: row.original.from_cashbox_id }
          : { type: "ACCOUNT", id: row.original.from_account_id ?? "" },
      ),
    }),
    columnHelper.accessor("to_cashbox_id", {
      header: "Destino",
      cell: ({ row }) => nameOf(
        row.original.to_cashbox_id
          ? { type: "CASHBOX", id: row.original.to_cashbox_id }
          : { type: "ACCOUNT", id: row.original.to_account_id ?? "" },
      ),
    }),
    columnHelper.accessor("amount", { header: "Monto" }),
    columnHelper.accessor("currency", { header: "Moneda" }),
    columnHelper.accessor("value_date", { header: "Fecha valor" }),
    columnHelper.accessor("reference", { header: "Referencia" }),
    columnHelper.accessor("status", { header: "Estado" }),
  ];

  const legSelect = (
    leg: Leg,
    setLeg: (l: Leg) => void,
    label: string,
  ): React.JSX.Element => (
    <div className="flex gap-2">
      <FormField label={label}>
        <select
          value={leg.type}
          onChange={(e) => setLeg({ type: e.target.value as Leg["type"], id: "" })}
          className="h-10 w-40 rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900"
        >
          <option value="ACCOUNT">Cuenta</option>
          <option value="CASHBOX">Caja</option>
        </select>
      </FormField>
      <FormField label="Selección">
        <select
          value={leg.id}
          onChange={(e) => setLeg({ ...leg, id: e.target.value })}
          className="h-10 w-56 rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900"
        >
          <option value="">Seleccionar…</option>
          {optionsFor(leg).map((o) => (
            <option key={o.id} value={o.id}>
              {o.label}
            </option>
          ))}
        </select>
      </FormField>
    </div>
  );

  return (
    <PageContent maxWidth="full">
      <PageHeader
        title="Transferencias y depósitos"
        description="Movimientos entre cajas y cuentas bancarias con registro en origen y destino (FR-006-023)."
        crumbs={[{ label: "Tesorería" }, { label: "Transferencias" }]}
      />

      <form
        className="mb-4 flex flex-wrap items-end gap-3 rounded-lg border border-border-default bg-surface-0 p-4"
        onSubmit={(e) => e.preventDefault()}
      >
        {legSelect(from, setFrom, "Origen")}
        {legSelect(to, setTo, "Destino")}
        <FormField label="Monto">
          <MoneyInput value={amount} onChange={(e) => setAmount(e.target.value)} />
        </FormField>
        <FormField label="Referencia">
          <TextInput value={reference} onChange={(e) => setReference(e.target.value)} placeholder="Opcional" />
        </FormField>
        <AsyncButton type="submit" variant="secondary" onClick={submit}>
          Transferir
        </AsyncButton>
      </form>

      <DataTable
        columns={columns}
        data={transfers.data?.items ?? []}
        loading={transfers.isLoading}
        error={transfers.isError ? "No fue posible cargar las transferencias." : null}
        getRowId={(row) => row.id}
        emptyTitle="Sin transferencias"
        emptyDescription="Registre una transferencia o depósito."
      />
    </PageContent>
  );
}
