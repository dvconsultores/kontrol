/** Notas fiscales — referencia obligatoria y límites al saldo ajustable (FR-007-030/031). */
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { createColumnHelper } from "@tanstack/react-table";
import { useState } from "react";

import { apiFetch } from "@/api/client";
import type { CreditDebitNoteSummary, SalesInvoiceSummary } from "@/api/types";
import { useNotifications } from "@/app/contexts/NotificationContext";
import { AsyncButton } from "@/components/AsyncButton";
import { DataTable } from "@/components/DataTable";
import { FormField } from "@/components/FormField";
import { MoneyInput } from "@/components/MoneyInput";
import { PageContent } from "@/layout/PageContent";
import { PageHeader } from "@/components/PageHeader";
import { TextInput } from "@/components/TextInput";

const columnHelper = createColumnHelper<CreditDebitNoteSummary>();

export function NotasPage(): React.JSX.Element {
  const queryClient = useQueryClient();
  const { notify } = useNotifications();

  const [invoiceId, setInvoiceId] = useState("");
  const [noteType, setNoteType] = useState<"CREDIT" | "DEBIT">("CREDIT");
  const [cause, setCause] = useState("");
  const [amount, setAmount] = useState("");

  const notes = useQuery({
    queryKey: ["fiscal", "notes"],
    queryFn: () => apiFetch<{ items: CreditDebitNoteSummary[] }>("/fiscal/credit-debit-notes"),
    retry: false,
  });
  const invoices = useQuery({
    queryKey: ["ventas", "facturas"],
    queryFn: () => apiFetch<{ items: SalesInvoiceSummary[] }>("/sales/invoices"),
    retry: false,
  });

  const createNote = async (): Promise<void> => {
    if (!invoiceId) {
      notify({ type: "error", title: "Falta la factura", description: "Seleccione la factura original." });
      return;
    }
    await apiFetch("/fiscal/credit-debit-notes", {
      method: "POST",
      body: { original_document: `INVOICE:${invoiceId}`, note_type: noteType, cause, amount: Number(amount) || 0 },
    });
    notify({ type: "success", title: "Nota emitida", description: `${noteType} por ${amount} referenciando la factura.` });
    setCause("");
    setAmount("");
    void queryClient.invalidateQueries({ queryKey: ["fiscal", "notes"] });
  };

  const columns = [
    columnHelper.accessor("original_document", { header: "Factura original" }),
    columnHelper.accessor("note_type", { header: "Tipo" }),
    columnHelper.accessor("cause", { header: "Causal" }),
    columnHelper.accessor("amount", { header: "Monto" }),
    columnHelper.accessor("status", { header: "Estado" }),
  ];

  return (
    <PageContent maxWidth="full">
      <PageHeader
        title="Notas fiscales"
        description="Notas de crédito/débito con referencia obligatoria y límite al saldo ajustable de la factura (FR-007-030/031)."
        crumbs={[{ label: "Fiscal" }, { label: "Notas" }]}
      />

      <form
        className="mb-4 flex flex-wrap items-end gap-3 rounded-lg border border-border-default bg-surface-0 p-4"
        onSubmit={(e) => e.preventDefault()}
      >
        <FormField label="Factura original" className="min-w-56">
          <select value={invoiceId} onChange={(e) => setInvoiceId(e.target.value)} className="h-10 w-full rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900">
            <option value="">Seleccionar factura…</option>
            {(invoices.data?.items ?? []).map((i) => (
              <option key={i.id} value={i.id}>{i.invoice_number ?? i.id.slice(0, 8)} · {i.total.toFixed(2)}</option>
            ))}
          </select>
        </FormField>
        <FormField label="Tipo">
          <select value={noteType} onChange={(e) => setNoteType(e.target.value as typeof noteType)} className="h-10 w-44 rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900">
            <option value="CREDIT">Nota de crédito</option>
            <option value="DEBIT">Nota de débito</option>
          </select>
        </FormField>
        <FormField label="Monto">
          <MoneyInput value={amount} onChange={(e) => setAmount(e.target.value)} />
        </FormField>
        <FormField label="Causal">
          <TextInput value={cause} onChange={(e) => setCause(e.target.value)} placeholder="Ej. devolución parcial" />
        </FormField>
        <AsyncButton type="submit" variant="secondary" onClick={createNote}>
          Emitir nota
        </AsyncButton>
      </form>

      <DataTable
        columns={columns}
        data={notes.data?.items ?? []}
        loading={notes.isLoading}
        error={notes.isError ? "No fue posible cargar las notas fiscales." : null}
        getRowId={(row) => row.id}
        emptyTitle="Sin notas fiscales"
        emptyDescription="Emita una nota referenciando una factura."
      />
    </PageContent>
  );
}
