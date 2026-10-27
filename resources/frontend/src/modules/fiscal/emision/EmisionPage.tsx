/** Emisión e impresión fiscal — consume correlativo y control atómicamente (FR-007-020/021/022). */
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { createColumnHelper } from "@tanstack/react-table";
import { useState } from "react";

import { apiFetch } from "@/api/client";
import type { ControlBatchSummary, FiscalDocumentSummary, NumberSeriesSummary, SalesInvoiceSummary } from "@/api/types";
import { useAutoridad } from "@/app/autoridad/AutoridadContext";
import { useNotifications } from "@/app/contexts/NotificationContext";
import { AsyncButton } from "@/components/AsyncButton";
import { DataTable } from "@/components/DataTable";
import { FormField } from "@/components/FormField";
import { PageContent } from "@/layout/PageContent";
import { PageHeader } from "@/components/PageHeader";
import { TextInput } from "@/components/TextInput";

const columnHelper = createColumnHelper<FiscalDocumentSummary>();

export function EmisionPage(): React.JSX.Element {
  const queryClient = useQueryClient();
  const { notify } = useNotifications();
  const { puede } = useAutoridad();

  const [invoiceId, setInvoiceId] = useState("");
  const [seriesId, setSeriesId] = useState("");
  const [batchId, setBatchId] = useState("");
  const [printReason, setPrintReason] = useState("");

  const documents = useQuery({
    queryKey: ["fiscal", "documents"],
    queryFn: () => apiFetch<{ items: FiscalDocumentSummary[] }>("/fiscal/documents"),
    retry: false,
  });
  const invoices = useQuery({
    queryKey: ["ventas", "facturas"],
    queryFn: () => apiFetch<{ items: SalesInvoiceSummary[] }>("/sales/invoices"),
    retry: false,
  });
  const series = useQuery({
    queryKey: ["fiscal", "number-series"],
    queryFn: () => apiFetch<{ items: NumberSeriesSummary[] }>("/fiscal/number-series"),
    retry: false,
  });
  const batches = useQuery({
    queryKey: ["fiscal", "control-batches"],
    queryFn: () => apiFetch<{ items: ControlBatchSummary[] }>("/fiscal/control-batches"),
    retry: false,
  });

  const refresh = (): void => {
    void queryClient.invalidateQueries({ queryKey: ["fiscal", "documents"] });
  };

  const emit = async (): Promise<void> => {
    if (!invoiceId || !seriesId || !batchId) {
      notify({ type: "error", title: "Faltan datos", description: "Seleccione factura, serie y lote." });
      return;
    }
    const res = await apiFetch<{ idempotent: boolean; invoice_number: string | null; control_number: string | null }>("/fiscal/documents/emit", {
      method: "POST",
      body: { business_document: `INVOICE:${invoiceId}`, series_id: seriesId, batch_id: batchId },
      idempotencyKey: `emit-${invoiceId}`,
    });
    notify({
      type: "success",
      title: res.idempotent ? "Ya emitida" : "Documento emitido",
      description: res.idempotent ? "Emisión idempotente (no duplica)." : `N° ${res.invoice_number} · control ${res.control_number}`,
    });
    setInvoiceId("");
    refresh();
  };

  const print = async (id: string): Promise<void> => {
    await apiFetch(`/fiscal/documents/${id}/print`, {
      method: "POST",
      body: { copy_type: "ORIGINAL", printer: "PRN-1", reason: printReason || "Emisión original" },
    });
    notify({ type: "success", title: "Impresión registrada", description: "Evento de impresión auditado." });
    refresh();
  };

  const columns = [
    columnHelper.accessor("business_document", { header: "Documento" }),
    columnHelper.accessor("series", { header: "Serie" }),
    columnHelper.accessor("invoice_number", { header: "Número" }),
    columnHelper.accessor("control_number", { header: "Control" }),
    columnHelper.accessor("fiscal_currency", { header: "Moneda" }),
    columnHelper.accessor("hash", { header: "Hash", cell: (info) => (info.getValue() ?? "").slice(0, 12) }),
    columnHelper.accessor("status", { header: "Estado" }),
    columnHelper.display({
      id: "actions",
      header: "Acciones",
      cell: ({ row }) => (
        <div className="flex justify-end gap-1">
          {puede("POST", `/fiscal/documents/${row.original.id}/print`) && (
            <AsyncButton size="sm" variant="secondary" onClick={() => print(row.original.id)}>
              imprimir
            </AsyncButton>
          )}
        </div>
      ),
    }),
  ];

  return (
    <PageContent maxWidth="full">
      <PageHeader
        title="Emisión e impresión fiscal"
        description="La emisión consume correlativo y número de control en transacción atómica; queda inalterable con hash (FR-007-020/021)."
        crumbs={[{ label: "Fiscal" }, { label: "Emisión" }]}
      />

      {puede("POST", "/fiscal/documents/emit") && (
      <form
        className="mb-4 flex flex-wrap items-end gap-3 rounded-lg border border-border-default bg-surface-0 p-4"
        onSubmit={(e) => e.preventDefault()}
      >
        <FormField label="Factura de venta" className="min-w-56">
          <select value={invoiceId} onChange={(e) => setInvoiceId(e.target.value)} className="h-10 w-full rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900">
            <option value="">Seleccionar factura…</option>
            {(invoices.data?.items ?? []).map((i) => (
              <option key={i.id} value={i.id}>
                {i.invoice_number ?? i.id.slice(0, 8)} · {i.total.toFixed(2)} · {i.status}
              </option>
            ))}
          </select>
        </FormField>
        <FormField label="Serie">
          <select value={seriesId} onChange={(e) => setSeriesId(e.target.value)} className="h-10 w-44 rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900">
            <option value="">Seleccionar…</option>
            {(series.data?.items ?? []).map((s) => (
              <option key={s.id} value={s.id}>{s.prefix ?? ""} · {s.document_type}</option>
            ))}
          </select>
        </FormField>
        <FormField label="Lote de control">
          <select value={batchId} onChange={(e) => setBatchId(e.target.value)} className="h-10 w-44 rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900">
            <option value="">Seleccionar…</option>
            {(batches.data?.items ?? []).map((b) => (
              <option key={b.id} value={b.id}>{b.range_from}–{b.range_to}</option>
            ))}
          </select>
        </FormField>
        <AsyncButton type="submit" variant="secondary" onClick={emit}>
          Emitir
        </AsyncButton>
      </form>
      )}

      <div className="mb-4 flex flex-wrap items-end gap-3 rounded-lg border border-border-default bg-surface-0 p-4">
        <FormField label="Motivo de reimpresión" className="min-w-64">
          <TextInput value={printReason} onChange={(e) => setPrintReason(e.target.value)} placeholder="Ej. copia para archivo" />
        </FormField>
      </div>

      <DataTable
        columns={columns}
        data={documents.data?.items ?? []}
        loading={documents.isLoading}
        error={documents.isError ? "No fue posible cargar los documentos fiscales." : null}
        getRowId={(row) => row.id}
        emptyTitle="Sin documentos fiscales"
        emptyDescription="Emita una factura para generar el documento fiscal."
      />
    </PageContent>
  );
}
