/** Notas de venta — crédito y débito, posteo y aplicación a CxC (FR-005-050/051, WF-05). */
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { createColumnHelper } from "@tanstack/react-table";
import { useState } from "react";

import { apiFetch } from "@/api/client";
import type { CreditNoteSummary, DebitNoteSummary, OpenItem, PagedResult, Party } from "@/api/types";
import { useNotifications } from "@/app/contexts/NotificationContext";
import { AsyncButton } from "@/components/AsyncButton";
import { DataTable } from "@/components/DataTable";
import { FormField } from "@/components/FormField";
import { PageContent } from "@/layout/PageContent";
import { PageHeader } from "@/components/PageHeader";
import { TextInput } from "@/components/TextInput";

const creditHelper = createColumnHelper<CreditNoteSummary>();
const debitHelper = createColumnHelper<DebitNoteSummary>();

export function NotasVentasPage(): React.JSX.Element {
  const queryClient = useQueryClient();
  const { notify } = useNotifications();

  const [noteType, setNoteType] = useState<"CREDIT" | "DEBIT">("CREDIT");
  const [newCustomer, setNewCustomer] = useState("");
  const [newNumber, setNewNumber] = useState("");
  const [newAmount, setNewAmount] = useState("");
  const [newInvoiceRef, setNewInvoiceRef] = useState("");
  const [applyNoteId, setApplyNoteId] = useState("");
  const [applyOpenItem, setApplyOpenItem] = useState("");
  const [applyAmount, setApplyAmount] = useState("");

  const creditNotes = useQuery({
    queryKey: ["ventas", "credit-notes"],
    queryFn: () => apiFetch<{ items: CreditNoteSummary[] }>("/sales/credit-notes"),
    retry: false,
  });
  const debitNotes = useQuery({
    queryKey: ["ventas", "debit-notes"],
    queryFn: () => apiFetch<{ items: DebitNoteSummary[] }>("/sales/debit-notes"),
    retry: false,
  });
  const customers = useQuery({
    queryKey: ["maestros", "terceros"],
    queryFn: () => apiFetch<PagedResult<Party>>("/maestros/terceros"),
    retry: false,
  });
  const openItems = useQuery({
    queryKey: ["ventas", "open-items"],
    queryFn: () => apiFetch<{ items: OpenItem[] }>("/sales/open-items"),
    retry: false,
  });

  const refresh = (): void => {
    void queryClient.invalidateQueries({ queryKey: ["ventas", "credit-notes"] });
    void queryClient.invalidateQueries({ queryKey: ["ventas", "debit-notes"] });
  };

  const createNote = async (): Promise<void> => {
    try {
      if (noteType === "CREDIT") {
        await apiFetch("/sales/credit-notes", {
          method: "POST",
          body: { customer_id: newCustomer, number: newNumber, amount: Number(newAmount) || 0, invoice_ref: newInvoiceRef || null, currency: "VED" },
        });
      } else {
        await apiFetch("/sales/debit-notes", {
          method: "POST",
          body: { customer_id: newCustomer, number: newNumber, amount: Number(newAmount) || 0, invoice_ref: newInvoiceRef || null, currency: "VED" },
        });
      }
      notify({ type: "success", title: "Nota emitida", description: `${newNumber} (${noteType})` });
      setNewNumber(""); setNewAmount(""); setNewInvoiceRef("");
      refresh();
    } catch (err) {
      const message = err instanceof Error ? err.message : "No fue posible emitir la nota";
      notify({ type: "error", title: "No fue posible emitir la nota", description: message });
    }
  };

  const postNote = async (id: string): Promise<void> => {
    await apiFetch(`/sales/credit-notes/${id}/post`, { method: "POST", body: {} });
    notify({ type: "success", title: "Nota posteada", description: id });
    refresh();
  };

  const applyNote = async (): Promise<void> => {
    if (!applyNoteId || !applyOpenItem) return;
    try {
      await apiFetch(`/sales/credit-notes/${applyNoteId}/apply`, {
        method: "POST",
        body: { target_open_item_id: applyOpenItem, amount: Number(applyAmount) || 0, currency: "VED" },
      });
      notify({ type: "success", title: "Nota aplicada", description: `a ${applyOpenItem}` });
      setApplyNoteId(""); setApplyOpenItem(""); setApplyAmount("");
      refresh();
      void queryClient.invalidateQueries({ queryKey: ["ventas", "open-items"] });
    } catch (err) {
      const message = err instanceof Error ? err.message : "No fue posible aplicar la nota";
      notify({ type: "error", title: "No fue posible aplicar la nota", description: message });
    }
  };

  const creditColumns = [
    creditHelper.accessor("number", { header: "Número" }),
    creditHelper.accessor("party_id", { header: "Cliente" }),
    creditHelper.accessor("invoice_ref", { header: "Factura ref." }),
    creditHelper.accessor("amount", { header: "Monto" }),
    creditHelper.accessor("applied", { header: "Aplicado" }),
    creditHelper.accessor("status", { header: "Estado" }),
    creditHelper.display({
      id: "actions",
      header: "Acciones",
      cell: ({ row }) => (
        <div className="flex justify-end gap-1">
          {row.original.status === "DRAFT" ? (
            <AsyncButton size="sm" variant="secondary" onClick={() => postNote(row.original.id)}>postear</AsyncButton>
          ) : null}
        </div>
      ),
    }),
  ];

  const debitColumns = [
    debitHelper.accessor("number", { header: "Número" }),
    debitHelper.accessor("customer_id", { header: "Cliente" }),
    debitHelper.accessor("invoice_ref", { header: "Factura ref." }),
    debitHelper.accessor("amount", { header: "Monto" }),
    debitHelper.accessor("status", { header: "Estado" }),
  ];

  return (
    <PageContent maxWidth="full">
      <PageHeader
        title="Notas de venta"
        description="Notas de crédito y débito: emisión, posteo y aplicación a cuentas por cobrar."
        crumbs={[{ label: "Ventas" }, { label: "Notas" }]}
      />
      <section className="mb-4 rounded-lg border border-border-default bg-surface-0 p-4">
        <h2 className="mb-2 text-base font-semibold text-text-900">Emitir nota</h2>
        <form className="flex flex-wrap items-end gap-3" onSubmit={(e) => e.preventDefault()}>
          <FormField label="Tipo">
            <select value={noteType} onChange={(e) => setNoteType(e.target.value as "CREDIT" | "DEBIT")} className="h-10 w-44 rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900">
              <option value="CREDIT">Crédito</option>
              <option value="DEBIT">Débito</option>
            </select>
          </FormField>
          <FormField label="Cliente" required>
            <select value={newCustomer} onChange={(e) => setNewCustomer(e.target.value)} className="h-10 w-56 rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900">
              <option value="">Seleccionar…</option>
              {(customers.data?.items ?? []).map((c) => (
                <option key={c.id} value={c.id}>{c.code} · {c.name}</option>
              ))}
            </select>
          </FormField>
          <FormField label="Número" required>
            <TextInput value={newNumber} onChange={(e) => setNewNumber(e.target.value)} placeholder="NC-0001" required />
          </FormField>
          <FormField label="Monto" required>
            <TextInput type="number" value={newAmount} onChange={(e) => setNewAmount(e.target.value)} placeholder="0,00" required />
          </FormField>
          <FormField label="Factura ref.">
            <TextInput value={newInvoiceRef} onChange={(e) => setNewInvoiceRef(e.target.value)} placeholder="FAC-0001" />
          </FormField>
          <AsyncButton type="submit" variant="primary" onClick={createNote}>Emitir</AsyncButton>
        </form>
      </section>

      <section className="mb-4 rounded-lg border border-border-default bg-surface-0 p-4">
        <h2 className="mb-2 text-base font-semibold text-text-900">Aplicar nota de crédito a CxC</h2>
        <form className="flex flex-wrap items-end gap-3" onSubmit={(e) => e.preventDefault()}>
          <FormField label="Nota" required>
            <select value={applyNoteId} onChange={(e) => setApplyNoteId(e.target.value)} className="h-10 w-56 rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900">
              <option value="">Seleccionar…</option>
              {(creditNotes.data?.items ?? [])
                .filter((n) => n.status === "POSTED")
                .map((n) => (
                  <option key={n.id} value={n.id}>{n.number} · saldo {n.amount - n.applied}</option>
                ))}
            </select>
          </FormField>
          <FormField label="Documento a aplicar" required>
            <select value={applyOpenItem} onChange={(e) => setApplyOpenItem(e.target.value)} className="h-10 w-56 rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900">
              <option value="">Seleccionar…</option>
              {(openItems.data?.items ?? []).map((o) => (
                <option key={o.id} value={o.id}>{o.source_document ?? o.id} · saldo {o.balance}</option>
              ))}
            </select>
          </FormField>
          <FormField label="Monto" required>
            <TextInput type="number" value={applyAmount} onChange={(e) => setApplyAmount(e.target.value)} placeholder="0,00" required />
          </FormField>
          <AsyncButton type="submit" variant="secondary" onClick={applyNote}>Aplicar</AsyncButton>
        </form>
      </section>

      <h2 className="mb-2 text-base font-semibold text-text-900">Notas de crédito</h2>
      <div className="mb-6">
        <DataTable
          columns={creditColumns}
          data={creditNotes.data?.items ?? []}
          loading={creditNotes.isLoading}
          error={creditNotes.isError ? "No fue posible cargar las notas de crédito." : null}
          getRowId={(row) => row.id}
          emptyTitle="Sin notas de crédito"
          emptyDescription="Aún no hay notas de crédito."
        />
      </div>

      <h2 className="mb-2 text-base font-semibold text-text-900">Notas de débito</h2>
      <DataTable
        columns={debitColumns}
        data={debitNotes.data?.items ?? []}
        loading={debitNotes.isLoading}
        error={debitNotes.isError ? "No fue posible cargar las notas de débito." : null}
        getRowId={(row) => row.id}
        emptyTitle="Sin notas de débito"
        emptyDescription="Aún no hay notas de débito."
      />
    </PageContent>
  );
}
