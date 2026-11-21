/** Transferencias — creación, envío, recepción por línea, valor y reversión (FR-003-060/061/062, WF-04, V4). */
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { createColumnHelper } from "@tanstack/react-table";
import { useState } from "react";

import { apiFetch } from "@/api/client";
import type { PagedResult, TransferSummary } from "@/api/types";
import { useAutoridad } from "@/app/autoridad/AutoridadContext";
import { useCompany } from "@/app/contexts/CompanyContext";
import { useNotifications } from "@/app/contexts/NotificationContext";
import { AsyncButton } from "@/components/AsyncButton";
import { Autorizado } from "@/components/Autorizado";
import { DataTable } from "@/components/DataTable";
import { FormField } from "@/components/FormField";
import { PageContent } from "@/layout/PageContent";
import { PageHeader } from "@/components/PageHeader";
import { TextInput } from "@/components/TextInput";
import { SelectorDeArticulo } from "@/modules/maestros/catalogo/SelectorDeArticulo";
import { AvisoDeAlmacenes } from "@/modules/organizacion/almacenes/AvisoDeAlmacenes";
import { useAlmacenesDeEmpresa } from "@/modules/organizacion/almacenes/useAlmacenesDeEmpresa";


const columnHelper = createColumnHelper<TransferSummary>();

const ESTADOS: Record<string, string> = {
  DRAFT: "Borrador",
  SUBMITTED: "Enviada a aprobación",
  APPROVED: "Aprobada",
  PICKING: "En preparación",
  IN_TRANSIT: "En tránsito",
  PARTIALLY_RECEIVED: "Recibida parcialmente",
  RECEIVED: "Recibida",
  CLOSED: "Cerrada",
  REVERSED: "Revertida",
  CANCELLED: "Cancelada",
  REJECTED: "Rechazada",
};

const ACCIONES: Record<string, string> = {
  submit: "Enviar a aprobación",
  approve: "Aprobar",
  confirm_ship: "Confirmar envío",
  close: "Cerrar",
};

function ruta(t: TransferSummary): string {
  return `${t.code} · ${t.origin_warehouse_name ?? t.origin_warehouse_id} → ${t.destination_warehouse_name ?? t.destination_warehouse_id}`;
}

function pendiente(sent: number, received: number | null): number {
  return Number(sent) - Number(received ?? 0);
}

function conMoneda(valor: string, moneda: string | null): string {
  return `${valor} ${moneda ?? ""}`.trim();
}

export function TransferenciasPage(): React.JSX.Element {
  const { activeCompany } = useCompany();
  const queryClient = useQueryClient();
  const { notify } = useNotifications();
  const { puede } = useAutoridad();

  const [newCode, setNewCode] = useState("");
  const [newOrigin, setNewOrigin] = useState("");
  const [newDestination, setNewDestination] = useState("");
  const [lineProduct, setLineProduct] = useState("");
  const [lineQty, setLineQty] = useState("");
  const [receiptId, setReceiptId] = useState("");
  const [receiptLines, setReceiptLines] = useState<Record<string, string>>({});
  const [reverseId, setReverseId] = useState("");
  const [reverseReason, setReverseReason] = useState("");

  const companyId = activeCompany?.id ?? null;

  const query = useQuery({
    queryKey: ["inventario", "transferencias"],
    queryFn: () => apiFetch<PagedResult<TransferSummary>>("/inventory/transfers"),
    retry: false,
  });
  const warehouses = useAlmacenesDeEmpresa(companyId);
  const transferencias = query.data?.items ?? [];
  const enRecepcion = transferencias.find((t) => t.id === receiptId);

  const refrescar = (): Promise<void> => queryClient.invalidateQueries({ queryKey: ["inventario", "transferencias"] });

  const createTransfer = async (): Promise<void> => {
    if (!lineProduct) {
      notify({ type: "error", title: "Falta el producto", description: "Agregue al menos una línea de producto." });
      return;
    }
    try {
      await apiFetch("/inventory/transfers", {
        method: "POST",
        body: {
          code: newCode, origin_warehouse_id: newOrigin, destination_warehouse_id: newDestination,
          request_ref: null,
          lines: [{ product_id: lineProduct, quantity_sent: Number(lineQty) || 0, lot_id: null, serial_id: null }],
        },
      });
      notify({ type: "success", title: "Transferencia creada", description: newCode });
      setNewCode(""); setNewOrigin(""); setNewDestination(""); setLineProduct(""); setLineQty("");
      void refrescar();
    } catch (err) {
      const message = err instanceof Error ? err.message : "No fue posible crear la transferencia";
      notify({ type: "error", title: "No fue posible crear la transferencia", description: message });
    }
  };

  const runTransition = async (id: string, target: string): Promise<void> => {
    await apiFetch(`/inventory/transfers/${id}/transition`, { method: "POST", body: { target } });
    await refrescar();
    notify({ type: "success", title: "Transferencia actualizada", description: ESTADOS[target] ?? target });
  };

  const registerReceipt = async (): Promise<void> => {
    if (!enRecepcion) {
      notify({ type: "error", title: "Falta la transferencia", description: "Seleccione la transferencia que llega." });
      return;
    }
    const received: Record<string, number> = {};
    let completa = true;
    for (const line of enRecepcion.lines) {
      const falta = pendiente(line.quantity_sent, line.quantity_received);
      const cantidad = Number(receiptLines[line.id] ?? falta);
      if (cantidad > 0) received[line.id] = cantidad;
      if (cantidad < falta) completa = false;
    }
    if (Object.keys(received).length === 0) {
      notify({ type: "error", title: "Sin cantidades", description: "Indique al menos una cantidad mayor que cero." });
      return;
    }
    try {
      await apiFetch(`/inventory/transfers/${enRecepcion.id}/transition`, {
        method: "POST",
        body: { target: completa ? "RECEIVED" : "PARTIALLY_RECEIVED", received },
      });
      notify({ type: "success", title: "Recepción registrada", description: enRecepcion.code });
      setReceiptId(""); setReceiptLines({});
      void refrescar();
    } catch (err) {
      const message = err instanceof Error ? err.message : "No fue posible registrar la recepción";
      notify({ type: "error", title: "No fue posible registrar la recepción", description: message });
    }
  };

  const reverseTransfer = async (): Promise<void> => {
    const motivo = reverseReason.trim();
    if (!reverseId) {
      notify({ type: "error", title: "Falta la transferencia", description: "Seleccione la transferencia que desea revertir." });
      return;
    }
    if (!motivo) {
      notify({ type: "error", title: "Falta el motivo", description: "Indique el motivo de la reversión." });
      return;
    }
    if (motivo.length > 300) {
      notify({ type: "error", title: "Motivo demasiado largo", description: "El motivo admite como máximo 300 caracteres." });
      return;
    }
    try {
      await apiFetch(`/inventory/transfers/${reverseId}/reverse`, { method: "POST", body: { reason: motivo } });
      notify({ type: "success", title: "Transferencia revertida", description: motivo });
      setReverseId(""); setReverseReason("");
      void refrescar();
    } catch (err) {
      const message = err instanceof Error ? err.message : "No fue posible revertir la transferencia";
      notify({ type: "error", title: "No fue posible revertir la transferencia", description: message });
    }
  };

  const columns = [
    columnHelper.accessor("code", { header: "Código" }),
    columnHelper.accessor((t) => t.origin_warehouse_name ?? t.origin_warehouse_id, { id: "origen", header: "Origen" }),
    columnHelper.accessor((t) => t.destination_warehouse_name ?? t.destination_warehouse_id, { id: "destino", header: "Destino" }),
    columnHelper.accessor((t) => ESTADOS[t.status] ?? t.status, { id: "estado", header: "Estado" }),
    columnHelper.accessor((t) => conMoneda(t.value_sent, t.currency), { id: "valor", header: "Valor enviado" }),
    columnHelper.accessor((t) => conMoneda(t.value_in_transit, t.currency), { id: "transito", header: "En tránsito" }),
    columnHelper.display({
      id: "actions",
      header: "Acciones",
      cell: ({ row }) => {
        const a = row.original.allowed_actions;
        const transitions: Array<[string, string]> = [
          ["submit", "SUBMITTED"],
          ["approve", "APPROVED"],
          ["confirm_ship", "IN_TRANSIT"],
          ["close", "CLOSED"],
        ];
        const canTransition = puede("POST", `/inventory/transfers/${row.original.id}/transition`);
        return (
          <div className="flex justify-end gap-1">
            {transitions
              .filter(([key]) => a[key] && canTransition)
              .map(([key, target]) => (
                <AsyncButton key={key} size="sm" variant="secondary" onClick={() => runTransition(row.original.id, target)}>
                  {ACCIONES[key] ?? key}
                </AsyncButton>
              ))}
          </div>
        );
      },
    }),
  ];

  const claseSelect = "h-10 w-80 rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900";

  return (
    <PageContent maxWidth="full">
      <PageHeader
        title="Transferencias"
        description="Movimiento de mercancía entre almacenes: la cantidad y su valor salen del origen y llegan al destino."
        crumbs={[{ label: "Inventario" }, { label: "Transferencias" }]}
      />
      <Autorizado operacion={["POST", "/inventory/transfers"]}>
      <section className="mb-4 rounded-lg border border-border-default bg-surface-0 p-4">
        <h2 className="mb-2 text-base font-semibold text-text-900">Nueva transferencia</h2>
        <form className="flex flex-wrap items-end gap-3" onSubmit={(e) => e.preventDefault()}>
          <FormField label="Código" required>
            <TextInput value={newCode} onChange={(e) => setNewCode(e.target.value)} placeholder="TR-0001" required />
          </FormField>
          <AvisoDeAlmacenes consulta={warehouses} />
          <FormField label="Almacén origen" required>
            <select value={newOrigin} onChange={(e) => setNewOrigin(e.target.value)} className="h-10 w-56 rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900">
              <option value="">Seleccionar…</option>
              {(warehouses.data?.items ?? []).map((w) => (
                <option key={w.id} value={w.id}>{w.code} · {w.name}</option>
              ))}
            </select>
          </FormField>
          <FormField label="Almacén destino" required>
            <select value={newDestination} onChange={(e) => setNewDestination(e.target.value)} className="h-10 w-56 rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900">
              <option value="">Seleccionar…</option>
              {(warehouses.data?.items ?? []).map((w) => (
                <option key={w.id} value={w.id}>{w.code} · {w.name}</option>
              ))}
            </select>
          </FormField>
          <FormField label="Producto" required>
            <SelectorDeArticulo value={lineProduct} onChange={setLineProduct} itemType="PRODUCT" />
          </FormField>
          <FormField label="Cantidad" required>
            <TextInput type="number" value={lineQty} onChange={(e) => setLineQty(e.target.value)} placeholder="0" required />
          </FormField>
          <AsyncButton type="submit" variant="primary" onClick={createTransfer}>Crear</AsyncButton>
        </form>
      </section>
      </Autorizado>

      <Autorizado operacion={["POST", `/inventory/transfers/${receiptId || "_"}/transition`]}>
      <section className="mb-4 rounded-lg border border-border-default bg-surface-0 p-4">
        <h2 className="mb-2 text-base font-semibold text-text-900">Registrar recepción</h2>
        <form className="flex flex-wrap items-end gap-3" onSubmit={(e) => e.preventDefault()}>
          <FormField label="Transferencia que llega" required>
            <select value={receiptId} onChange={(e) => { setReceiptId(e.target.value); setReceiptLines({}); }} className={claseSelect}>
              <option value="">Seleccionar…</option>
              {transferencias.filter((t) => t.allowed_actions.confirm_receipt).map((t) => (
                <option key={t.id} value={t.id}>{ruta(t)}</option>
              ))}
            </select>
          </FormField>
          {(enRecepcion?.lines ?? []).map((line) => {
            const falta = pendiente(line.quantity_sent, line.quantity_received);
            return (
              <FormField
                key={line.id}
                label={`Recibir ahora · ${line.product_name ?? line.product_id} (enviado ${line.quantity_sent}, recibido ${line.quantity_received ?? 0})`}
              >
                <TextInput
                  type="number"
                  min={0}
                  value={receiptLines[line.id] ?? String(falta)}
                  onChange={(e) => setReceiptLines((prev) => ({ ...prev, [line.id]: e.target.value }))}
                />
              </FormField>
            );
          })}
          <AsyncButton type="submit" variant="primary" onClick={registerReceipt}>Registrar recepción</AsyncButton>
        </form>
      </section>
      </Autorizado>

      <Autorizado operacion={["POST", `/inventory/transfers/${reverseId || "_"}/reverse`]}>
      <section className="mb-4 rounded-lg border border-border-default bg-surface-0 p-4">
        <h2 className="mb-2 text-base font-semibold text-text-900">Revertir transferencia</h2>
        <form className="flex flex-wrap items-end gap-3" onSubmit={(e) => e.preventDefault()}>
          <FormField label="Transferencia recibida" required>
            <select value={reverseId} onChange={(e) => setReverseId(e.target.value)} className={claseSelect}>
              <option value="">Seleccionar…</option>
              {transferencias.filter((t) => t.allowed_actions.reverse).map((t) => (
                <option key={t.id} value={t.id}>{ruta(t)}</option>
              ))}
            </select>
          </FormField>
          <FormField label="Motivo" required>
            <TextInput value={reverseReason} onChange={(e) => setReverseReason(e.target.value)} placeholder="Destino equivocado" required />
          </FormField>
          <AsyncButton type="submit" variant="secondary" onClick={reverseTransfer}>Revertir</AsyncButton>
        </form>
      </section>
      </Autorizado>

      <DataTable
        columns={columns}
        data={transferencias}
        loading={query.isLoading}
        error={query.isError ? "No fue posible cargar las transferencias." : null}
        getRowId={(row) => row.id}
        emptyTitle="Sin transferencias"
        emptyDescription="Aún no hay transferencias registradas."
      />
    </PageContent>
  );
}
