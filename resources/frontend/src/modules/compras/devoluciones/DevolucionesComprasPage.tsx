/** Devoluciones de compra — registro y líneas (FR-004-060, WF-03). */
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { createColumnHelper } from "@tanstack/react-table";
import { useState } from "react";

import { apiFetch } from "@/api/client";
import type { CatalogItemSummary, PagedResult, ReturnSummary } from "@/api/types";
import { useAutoridad } from "@/app/autoridad/AutoridadContext";
import { useNotifications } from "@/app/contexts/NotificationContext";
import { AsyncButton } from "@/components/AsyncButton";
import { DataTable } from "@/components/DataTable";
import { FormField } from "@/components/FormField";
import { PageContent } from "@/layout/PageContent";
import { PageHeader } from "@/components/PageHeader";
import { TextInput } from "@/components/TextInput";

const columnHelper = createColumnHelper<ReturnSummary>();

const CONDITIONS = [
  { value: "DEFECTUOSO", label: "Defectuoso" },
  { value: "NO_CONFORME", label: "No conforme" },
  { value: "EXCESO", label: "Exceso" },
  { value: "DANADO", label: "Dañado" },
];

const DESTINATIONS = [
  { value: "CUARENTENA", label: "Cuarentena" },
  { value: "DEVOLUCION", label: "Devolución" },
  { value: "DESCARTE", label: "Descarte" },
];

export function DevolucionesComprasPage(): React.JSX.Element {
  const queryClient = useQueryClient();
  const { notify } = useNotifications();
  const { puede } = useAutoridad();

  const [newCode, setNewCode] = useState("");
  const [newDoc, setNewDoc] = useState("");
  const [newReason, setNewReason] = useState("");
  const [newCondition, setNewCondition] = useState("DEFECTUOSO");
  const [newDestination, setNewDestination] = useState("CUARENTENA");
  const [lineReturn, setLineReturn] = useState("");
  const [lineProduct, setLineProduct] = useState("");
  const [lineQty, setLineQty] = useState("");
  const [lineCondition, setLineCondition] = useState("DEFECTUOSO");

  const query = useQuery({
    queryKey: ["compras", "returns"],
    queryFn: () => apiFetch<{ items: ReturnSummary[] }>("/purchasing/returns"),
    retry: false,
  });
  const products = useQuery({
    queryKey: ["maestros", "productos"],
    queryFn: () => apiFetch<PagedResult<CatalogItemSummary>>(`/maestros/catalogos/items?status=ACTIVE`),
    retry: false,
  });

  const refresh = (): void => {
    void queryClient.invalidateQueries({ queryKey: ["compras", "returns"] });
  };

  const createReturn = async (): Promise<void> => {
    try {
      await apiFetch("/purchasing/returns", {
        method: "POST",
        body: {
          code: newCode, source_document: newDoc || null, reason: newReason,
          condition: newCondition, inventory_destination: newDestination,
        },
      });
      notify({ type: "success", title: "Devolución registrada", description: newCode });
      setNewCode(""); setNewDoc(""); setNewReason("");
      refresh();
    } catch (err) {
      const message = err instanceof Error ? err.message : "No fue posible registrar la devolución";
      notify({ type: "error", title: "No fue posible registrar la devolución", description: message });
    }
  };

  const addLine = async (): Promise<void> => {
    if (!lineReturn || !lineProduct) return;
    try {
      await apiFetch(`/purchasing/returns/${lineReturn}/lines`, {
        method: "POST",
        body: { product_id: lineProduct, quantity: Number(lineQty) || 0, condition: lineCondition },
      });
      notify({ type: "success", title: "Línea agregada", description: `Devolución ${lineReturn}` });
      setLineProduct(""); setLineQty("");
      refresh();
    } catch (err) {
      const message = err instanceof Error ? err.message : "No fue posible agregar la línea";
      notify({ type: "error", title: "No fue posible agregar la línea", description: message });
    }
  };

  const columns = [
    columnHelper.accessor("code", { header: "Código" }),
    columnHelper.accessor("source_document", { header: "Documento origen" }),
    columnHelper.accessor("condition", { header: "Condición" }),
    columnHelper.accessor("inventory_destination", { header: "Destino" }),
    columnHelper.accessor("status", { header: "Estado" }),
  ];

  return (
    <PageContent maxWidth="full">
      <PageHeader
        title="Devoluciones de compra"
        description="Devoluciones a proveedores y destino del inventario."
        crumbs={[{ label: "Compras" }, { label: "Devoluciones" }]}
      />
      {puede("POST", "/purchasing/returns") ? (
        <section className="mb-4 rounded-lg border border-border-default bg-surface-0 p-4">
          <h2 className="mb-2 text-base font-semibold text-text-900">Nueva devolución</h2>
          <form className="flex flex-wrap items-end gap-3" onSubmit={(e) => e.preventDefault()}>
            <FormField label="Código" required>
              <TextInput value={newCode} onChange={(e) => setNewCode(e.target.value)} placeholder="DEV-0001" required />
            </FormField>
            <FormField label="Documento origen">
              <TextInput value={newDoc} onChange={(e) => setNewDoc(e.target.value)} placeholder="FAC-0001" />
            </FormField>
            <FormField label="Motivo" required>
              <TextInput value={newReason} onChange={(e) => setNewReason(e.target.value)} placeholder="Producto dañado al recibir" required />
            </FormField>
            <FormField label="Condición">
              <select value={newCondition} onChange={(e) => setNewCondition(e.target.value)} className="h-10 w-44 rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900">
                {CONDITIONS.map((c) => <option key={c.value} value={c.value}>{c.label}</option>)}
              </select>
            </FormField>
            <FormField label="Destino">
              <select value={newDestination} onChange={(e) => setNewDestination(e.target.value)} className="h-10 w-44 rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900">
                {DESTINATIONS.map((d) => <option key={d.value} value={d.value}>{d.label}</option>)}
              </select>
            </FormField>
            <AsyncButton type="submit" variant="primary" onClick={createReturn}>Registrar</AsyncButton>
          </form>
        </section>
      ) : null}

      {puede("POST", "/purchasing/returns/_/lines") ? (
        <section className="mb-4 rounded-lg border border-border-default bg-surface-0 p-4">
          <h2 className="mb-2 text-base font-semibold text-text-900">Agregar línea</h2>
          <form className="flex flex-wrap items-end gap-3" onSubmit={(e) => e.preventDefault()}>
            <FormField label="Devolución" required>
              <select value={lineReturn} onChange={(e) => setLineReturn(e.target.value)} className="h-10 w-56 rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900">
                <option value="">Seleccionar…</option>
                {(query.data?.items ?? []).map((o) => (
                  <option key={o.id} value={o.id}>{o.code}</option>
                ))}
              </select>
            </FormField>
            <FormField label="Producto" required>
              <select value={lineProduct} onChange={(e) => setLineProduct(e.target.value)} className="h-10 w-56 rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900">
                <option value="">Seleccionar…</option>
                {(products.data?.items ?? []).map((p) => (
                  <option key={p.id} value={p.id}>{p.code} · {p.name}</option>
                ))}
              </select>
            </FormField>
            <FormField label="Cantidad" required>
              <TextInput type="number" value={lineQty} onChange={(e) => setLineQty(e.target.value)} placeholder="0" required />
            </FormField>
            <FormField label="Condición">
              <select value={lineCondition} onChange={(e) => setLineCondition(e.target.value)} className="h-10 w-44 rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900">
                {CONDITIONS.map((c) => <option key={c.value} value={c.value}>{c.label}</option>)}
              </select>
            </FormField>
            <AsyncButton type="submit" variant="secondary" onClick={addLine}>Agregar</AsyncButton>
          </form>
        </section>
      ) : null}

      <DataTable
        columns={columns}
        data={query.data?.items ?? []}
        loading={query.isLoading}
        error={query.isError ? "No fue posible cargar las devoluciones." : null}
        getRowId={(row) => row.id}
        emptyTitle="Sin devoluciones"
        emptyDescription="Aún no hay devoluciones registradas."
      />
    </PageContent>
  );
}
