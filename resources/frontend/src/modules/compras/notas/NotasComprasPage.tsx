/** Notas de crédito de proveedor — emisión y posteo (FR-004-050, WF-03). */
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { createColumnHelper } from "@tanstack/react-table";
import { useState } from "react";

import { apiFetch } from "@/api/client";
import type { CreditNoteSummary, PagedResult, Party } from "@/api/types";
import { useAutoridad } from "@/app/autoridad/AutoridadContext";
import { useNotifications } from "@/app/contexts/NotificationContext";
import { Autorizado } from "@/components/Autorizado";
import { AsyncButton } from "@/components/AsyncButton";
import { DataTable } from "@/components/DataTable";
import { FormField } from "@/components/FormField";
import { PageContent } from "@/layout/PageContent";
import { PageHeader } from "@/components/PageHeader";
import { TextInput } from "@/components/TextInput";

const columnHelper = createColumnHelper<CreditNoteSummary>();

export function NotasComprasPage(): React.JSX.Element {
  const queryClient = useQueryClient();
  const { notify } = useNotifications();
  const { puede } = useAutoridad();

  const [newSupplier, setNewSupplier] = useState("");
  const [newNumber, setNewNumber] = useState("");
  const [newAmount, setNewAmount] = useState("");
  const [newInvoiceRef, setNewInvoiceRef] = useState("");

  const notes = useQuery({
    queryKey: ["compras", "credit-notes"],
    queryFn: () => apiFetch<{ items: CreditNoteSummary[] }>("/purchasing/credit-notes"),
    retry: false,
  });
  const suppliers = useQuery({
    queryKey: ["maestros", "terceros"],
    queryFn: () => apiFetch<PagedResult<Party>>("/maestros/terceros"),
    retry: false,
  });

  const refresh = (): void => {
    void queryClient.invalidateQueries({ queryKey: ["compras", "credit-notes"] });
  };

  const createNote = async (): Promise<void> => {
    try {
      await apiFetch("/purchasing/credit-notes", {
        method: "POST",
        body: { supplier_id: newSupplier, number: newNumber, amount: Number(newAmount) || 0, invoice_ref: newInvoiceRef || null, currency: "VED" },
      });
      notify({ type: "success", title: "Nota emitida", description: newNumber });
      setNewNumber(""); setNewAmount(""); setNewInvoiceRef("");
      refresh();
    } catch (err) {
      const message = err instanceof Error ? err.message : "No fue posible emitir la nota";
      notify({ type: "error", title: "No fue posible emitir la nota", description: message });
    }
  };

  const postNote = async (id: string): Promise<void> => {
    await apiFetch(`/purchasing/credit-notes/${id}/post`, { method: "POST", body: {} });
    notify({ type: "success", title: "Nota posteada", description: id });
    refresh();
  };

  const columns = [
    columnHelper.accessor("number", { header: "Número" }),
    columnHelper.accessor("party_id", { header: "Proveedor" }),
    columnHelper.accessor("invoice_ref", { header: "Factura ref." }),
    columnHelper.accessor("amount", { header: "Monto" }),
    columnHelper.accessor("applied", { header: "Aplicado" }),
    columnHelper.accessor("status", { header: "Estado" }),
    columnHelper.display({
      id: "actions",
      header: "Acciones",
      cell: ({ row }) => (
        <div className="flex justify-end gap-1">
          {row.original.status === "DRAFT" && puede("POST", `/purchasing/credit-notes/${row.original.id}/post`) ? (
            <AsyncButton size="sm" variant="secondary" onClick={() => postNote(row.original.id)}>postear</AsyncButton>
          ) : null}
        </div>
      ),
    }),
  ];

  return (
    <PageContent maxWidth="full">
      <PageHeader
        title="Notas de crédito de proveedor"
        description="Emisión y posteo de notas de crédito de compras."
        crumbs={[{ label: "Compras" }, { label: "Notas de crédito" }]}
      />
      <Autorizado operacion={["POST", "/purchasing/credit-notes"]}>
      <section className="mb-4 rounded-lg border border-border-default bg-surface-0 p-4">
        <h2 className="mb-2 text-base font-semibold text-text-900">Emitir nota</h2>
        <form className="flex flex-wrap items-end gap-3" onSubmit={(e) => e.preventDefault()}>
          <FormField label="Proveedor" required>
            <select value={newSupplier} onChange={(e) => setNewSupplier(e.target.value)} className="h-10 w-56 rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900">
              <option value="">Seleccionar…</option>
              {(suppliers.data?.items ?? []).map((c) => (
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
      </Autorizado>

      <DataTable
        columns={columns}
        data={notes.data?.items ?? []}
        loading={notes.isLoading}
        error={notes.isError ? "No fue posible cargar las notas de crédito." : null}
        getRowId={(row) => row.id}
        emptyTitle="Sin notas de crédito"
        emptyDescription="Aún no hay notas de crédito de proveedor."
      />
    </PageContent>
  );
}
