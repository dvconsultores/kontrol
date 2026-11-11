/** Cotizaciones de compra — solicitud de oferta a proveedor (FR-004-001, WF-02). */
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { createColumnHelper } from "@tanstack/react-table";
import { useState } from "react";

import { apiFetch } from "@/api/client";
import type { QuoteComparisonItem, SupplierQuoteSummary } from "@/api/types";
import { useAutoridad } from "@/app/autoridad/AutoridadContext";
import { useNotifications } from "@/app/contexts/NotificationContext";
import { Autorizado } from "@/components/Autorizado";
import { AsyncButton } from "@/components/AsyncButton";
import { ConfirmationDialog } from "@/components/ConfirmationDialog";
import { DataTable } from "@/components/DataTable";
import { FormField } from "@/components/FormField";
import { PageContent } from "@/layout/PageContent";
import { PageHeader } from "@/components/PageHeader";
import { TextInput } from "@/components/TextInput";
import { SelectorDeTercero } from "@/modules/maestros/terceros/SelectorDeTercero";
import { SelectorDeArticulo } from "@/modules/maestros/catalogo/SelectorDeArticulo";

const columnHelper = createColumnHelper<SupplierQuoteSummary>();
const comparisonColumnHelper = createColumnHelper<QuoteComparisonItem>();

function quoteStatusLabel(status: string, expired: boolean): string {
  if (status === "AWARDED") return "Adjudicada";
  if (status === "CONVERTED") return "Orden emitida";
  if (status === "ACTIVE") return expired ? "Vencida" : "Vigente";
  return status;
}

type AwardPending = { quoteId: string; quoteCode: string; supplierName: string } | null;
type OrderPending = { quoteId: string; code: string; supplierName: string } | null;

export function CotizacionesComprasPage(): React.JSX.Element {
  const queryClient = useQueryClient();
  const { notify } = useNotifications();
  const { puede } = useAutoridad();

  const [newCode, setNewCode] = useState("");
  const [newSupplier, setNewSupplier] = useState("");
  const [newValidity, setNewValidity] = useState("");
  const [newTerms, setNewTerms] = useState("");
  const [lineQuote, setLineQuote] = useState("");
  const [lineProduct, setLineProduct] = useState("");
  const [lineQty, setLineQty] = useState("");
  const [linePrice, setLinePrice] = useState("");

  const [comparisonProductId, setComparisonProductId] = useState("");
  const [awardPending, setAwardPending] = useState<AwardPending>(null);
  const [awardReason, setAwardReason] = useState("");
  const [orderPending, setOrderPending] = useState<OrderPending>(null);
  const [orderCode, setOrderCode] = useState("");

  const query = useQuery({
    queryKey: ["compras", "cotizaciones"],
    queryFn: () => apiFetch<{ items: SupplierQuoteSummary[] }>("/purchasing/quotes"),
    retry: false,
  });

  const comparisonQuery = useQuery({
    queryKey: ["compras", "cotizaciones", "comparacion", comparisonProductId],
    queryFn: () =>
      apiFetch<{ items: QuoteComparisonItem[] }>(`/purchasing/quotes/comparison?product_id=${comparisonProductId}`),
    enabled: comparisonProductId !== "",
    retry: false,
  });

  const refresh = async (): Promise<void> => {
    await queryClient.invalidateQueries({ queryKey: ["compras", "cotizaciones"] });
  };

  const createQuote = async (): Promise<void> => {
    try {
      await apiFetch("/purchasing/quotes", {
        method: "POST",
        body: {
          code: newCode, supplier_id: newSupplier,
          validity_until: newValidity || null, currency: "VED", terms: newTerms || null,
        },
      });
      notify({ type: "success", title: "Cotización creada", description: newCode });
      setNewCode(""); setNewSupplier(""); setNewValidity(""); setNewTerms("");
      void refresh();
    } catch (err) {
      const message = err instanceof Error ? err.message : "No fue posible crear la cotización";
      notify({ type: "error", title: "No fue posible crear la cotización", description: message });
    }
  };

  const addLine = async (): Promise<void> => {
    if (!lineQuote || !lineProduct) return;
    try {
      await apiFetch(`/purchasing/quotes/${lineQuote}/lines`, {
        method: "POST",
        body: {
          product_id: lineProduct, quantity: Number(lineQty) || 0, unit_price: Number(linePrice) || 0,
          discount: 0, delivery_days: null, tax_ref: null,
        },
      });
      notify({ type: "success", title: "Línea agregada", description: `Cotización ${lineQuote}` });
      setLineProduct(""); setLineQty(""); setLinePrice("");
      void refresh();
    } catch (err) {
      const message = err instanceof Error ? err.message : "No fue posible agregar la línea";
      notify({ type: "error", title: "No fue posible agregar la línea", description: message });
    }
  };

  const confirmAward = async (): Promise<void> => {
    if (!awardPending) return;
    if (!awardReason.trim()) {
      notify({ type: "error", title: "Indique el motivo de la adjudicación." });
      return;
    }
    try {
      await apiFetch(`/purchasing/quotes/${awardPending.quoteId}/award`, {
        method: "POST",
        body: { reason: awardReason.trim() },
      });
      notify({ type: "success", title: "Cotización adjudicada", description: awardPending.quoteCode });
      setAwardPending(null);
      setAwardReason("");
      void refresh();
    } catch (err) {
      const message = err instanceof Error ? err.message : "No fue posible adjudicar la cotización";
      notify({ type: "error", title: "No fue posible adjudicar la cotización", description: message });
    }
  };

  const confirmOrder = async (): Promise<void> => {
    if (!orderPending) return;
    try {
      const result = await apiFetch<{ order: { code: string }; created: boolean }>(
        `/purchasing/quotes/${orderPending.quoteId}/order`,
        { method: "POST", body: { code: orderCode.trim() } },
      );
      notify({
        type: "success",
        title: result.created ? "Orden de compra emitida" : "La orden ya existía",
        description: result.order.code,
      });
      setOrderPending(null);
      setOrderCode("");
      await queryClient.invalidateQueries({ queryKey: ["compras", "cotizaciones"] });
      await queryClient.invalidateQueries({ queryKey: ["compras", "ordenes"] });
    } catch (err) {
      const message = err instanceof Error ? err.message : "No fue posible emitir la orden de compra";
      notify({ type: "error", title: "No fue posible emitir la orden de compra", description: message });
    }
  };

  const columns = [
    columnHelper.accessor("code", { header: "Código" }),
    columnHelper.accessor("supplier_name", {
      header: "Proveedor",
      cell: ({ getValue }) => getValue() ?? "—",
    }),
    columnHelper.accessor("currency", { header: "Moneda" }),
    columnHelper.accessor("validity_until", {
      header: "Válida hasta",
      cell: ({ getValue }) => getValue() ?? "Sin vencimiento",
    }),
    columnHelper.accessor("status", {
      header: "Estado",
      cell: ({ row }) => quoteStatusLabel(row.original.status, row.original.expired),
    }),
    columnHelper.accessor("line_count", { header: "Líneas" }),
    columnHelper.display({
      id: "acciones",
      header: "Acciones",
      cell: ({ row }) => {
        const quote = row.original;
        if (quote.order_id) {
          return <span className="text-sm text-text-600">Orden emitida</span>;
        }
        if (quote.status === "AWARDED" && puede("POST", `/purchasing/quotes/${quote.id}/order`)) {
          return (
            <AsyncButton
              size="sm"
              variant="primary"
              aria-label={`Emitir orden ${quote.code}`}
              onClick={async () => {
                setOrderCode(`OC-${quote.code}`);
                setOrderPending({ quoteId: quote.id, code: quote.code, supplierName: quote.supplier_name ?? "—" });
              }}
            >
              Emitir orden
            </AsyncButton>
          );
        }
        return null;
      },
    }),
  ];

  const comparisonColumns = [
    comparisonColumnHelper.accessor("quote_code", { header: "Cotización" }),
    comparisonColumnHelper.accessor("supplier_name", {
      header: "Proveedor",
      cell: ({ getValue }) => getValue() ?? "—",
    }),
    comparisonColumnHelper.accessor("currency", { header: "Moneda" }),
    comparisonColumnHelper.accessor("quantity", { header: "Cantidad" }),
    comparisonColumnHelper.accessor("unit_price", { header: "Precio unitario" }),
    comparisonColumnHelper.accessor("discount", { header: "Descuento" }),
    comparisonColumnHelper.accessor("line_amount", { header: "Importe" }),
    comparisonColumnHelper.accessor("delivery_days", {
      header: "Entrega (días)",
      cell: ({ getValue }) => getValue() ?? "—",
    }),
    comparisonColumnHelper.accessor("validity_until", {
      header: "Válida hasta",
      cell: ({ getValue }) => getValue() ?? "Sin vencimiento",
    }),
    comparisonColumnHelper.accessor("quote_status", {
      header: "Estado",
      cell: ({ row }) => quoteStatusLabel(row.original.quote_status, row.original.expired),
    }),
    comparisonColumnHelper.display({
      id: "accion",
      header: "Acción",
      cell: ({ row }) => {
        const item = row.original;
        if (item.can_award && puede("POST", `/purchasing/quotes/${item.quote_id}/award`)) {
          return (
            <AsyncButton
              size="sm"
              variant="primary"
              aria-label={`Adjudicar ${item.quote_code}`}
              onClick={async () => {
                setAwardReason("");
                setAwardPending({
                  quoteId: item.quote_id,
                  quoteCode: item.quote_code,
                  supplierName: item.supplier_name ?? "—",
                });
              }}
            >
              Adjudicar
            </AsyncButton>
          );
        }
        return null;
      },
    }),
  ];

  return (
    <PageContent maxWidth="full">
      <PageHeader
        title="Cotizaciones de compra"
        description="Solicitud de oferta a proveedores y carga de líneas de producto."
        crumbs={[{ label: "Compras" }, { label: "Cotizaciones" }]}
      />
      <Autorizado operacion={["POST", "/purchasing/quotes"]}>
        <section className="mb-4 rounded-lg border border-border-default bg-surface-0 p-4">
          <h2 className="mb-2 text-base font-semibold text-text-900">Nueva cotización</h2>
          <form className="flex flex-wrap items-end gap-3" onSubmit={(e) => e.preventDefault()}>
            <FormField label="Código" required>
              <TextInput value={newCode} onChange={(e) => setNewCode(e.target.value)} placeholder="COT-0001" required />
            </FormField>
            <FormField label="Proveedor" required>
              <SelectorDeTercero value={newSupplier} onChange={setNewSupplier} role="PROVEEDOR" soloActivos />
            </FormField>
            <FormField label="Válida hasta">
              <TextInput type="date" value={newValidity} onChange={(e) => setNewValidity(e.target.value)} />
            </FormField>
            <FormField label="Términos">
              <TextInput value={newTerms} onChange={(e) => setNewTerms(e.target.value)} placeholder="Crédito 30 días" />
            </FormField>
            <AsyncButton type="submit" variant="primary" onClick={createQuote}>Crear</AsyncButton>
          </form>
        </section>
      </Autorizado>

      <section className="mb-4 rounded-lg border border-border-default bg-surface-0 p-4">
        <h2 className="mb-2 text-base font-semibold text-text-900">Agregar línea</h2>
        <form className="flex flex-wrap items-end gap-3" onSubmit={(e) => e.preventDefault()}>
          <FormField label="Cotización" required>
            <select value={lineQuote} onChange={(e) => setLineQuote(e.target.value)} className="h-10 w-40 rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900">
              <option value="">Seleccionar…</option>
              {(query.data?.items ?? []).map((q) => (
                <option key={q.id} value={q.id}>{q.code}</option>
              ))}
            </select>
          </FormField>
          <Autorizado operacion={["POST", "/purchasing/quotes/_/lines"]}>
            <FormField label="Producto" required>
              <SelectorDeArticulo value={lineProduct} onChange={setLineProduct} />
            </FormField>
            <FormField label="Cantidad" required>
              <TextInput type="number" min="0" value={lineQty} onChange={(e) => setLineQty(e.target.value)} required />
            </FormField>
            <FormField label="Precio unitario" required>
              <TextInput type="number" min="0" value={linePrice} onChange={(e) => setLinePrice(e.target.value)} required />
            </FormField>
            <AsyncButton type="submit" variant="secondary" onClick={addLine}>Agregar línea</AsyncButton>
          </Autorizado>
        </form>
      </section>

      <section className="mb-4 rounded-lg border border-border-default bg-surface-0 p-4">
        <h2 className="mb-2 text-base font-semibold text-text-900">Comparar ofertas</h2>
        <FormField label="Artículo a comparar">
          <SelectorDeArticulo id="comparar-producto" value={comparisonProductId} onChange={setComparisonProductId} />
        </FormField>
        {comparisonProductId !== "" ? (
          <DataTable
            columns={comparisonColumns}
            data={comparisonQuery.data?.items ?? []}
            loading={comparisonQuery.isLoading}
            error={comparisonQuery.isError ? "No fue posible cargar la comparación." : null}
            getRowId={(row) => row.quote_id}
            emptyTitle="Sin ofertas para este producto"
          />
        ) : null}
      </section>

      <DataTable
        columns={columns}
        data={query.data?.items ?? []}
        loading={query.isLoading}
        error={query.isError ? "No fue posible cargar las cotizaciones." : null}
        getRowId={(row) => row.id}
        emptyTitle="Sin cotizaciones"
        emptyDescription="Aún no hay cotizaciones de compra registradas."
      />

      <ConfirmationDialog
        open={awardPending !== null}
        title="Adjudicar cotización"
        description={awardPending ? `${awardPending.quoteCode} · ${awardPending.supplierName}` : undefined}
        confirmLabel="Adjudicar"
        onConfirm={confirmAward}
        onCancel={() => {
          setAwardPending(null);
          setAwardReason("");
        }}
      >
        <FormField label="Motivo de la adjudicación" required>
          <TextInput
            value={awardReason}
            onChange={(e) => setAwardReason(e.target.value)}
            placeholder="Indique el motivo de la adjudicación"
            required
          />
        </FormField>
      </ConfirmationDialog>

      <ConfirmationDialog
        open={orderPending !== null}
        title="Emitir orden de compra"
        description={orderPending ? `${orderPending.code} · ${orderPending.supplierName}` : undefined}
        confirmLabel="Emitir orden"
        onConfirm={confirmOrder}
        onCancel={() => {
          setOrderPending(null);
          setOrderCode("");
        }}
      >
        <FormField label="Código de la orden" required>
          <TextInput
            value={orderCode}
            onChange={(e) => setOrderCode(e.target.value)}
            required
          />
        </FormField>
      </ConfirmationDialog>
    </PageContent>
  );
}
