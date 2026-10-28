/**
 * Recepciones — recepción física contra orden de compra (Spec 019).
 *
 * El proceso documentado tiene doce etapas y ocho son de esta pantalla:
 * confirmar el arribo, programar la descarga, recibir, comparar contra los
 * documentos, inspeccionar, validar bultos y estado, declarar la conformidad y
 * emitir el acta.
 *
 * Lo que se captura aquí no se reconstruye después: cuando el camión se va, la
 * presentación con la que llegó la mercancía, los bultos que bajaron y lo que
 * se vio al abrirlos solo existen si alguien los anotó.
 */
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { createColumnHelper } from "@tanstack/react-table";
import { useState } from "react";

import { ApiError, apiFetch } from "@/api/client";
import { Autorizado } from "@/components/Autorizado";
import { useAutoridad } from "@/app/autoridad/AutoridadContext";
import type {
  CatalogItemSummary,
  GoodsReceiptDetail,
  GoodsReceiptSummary,
  PagedResult,
} from "@/api/types";
import { useNotifications } from "@/app/contexts/NotificationContext";
import { AsyncButton } from "@/components/AsyncButton";
import { DataTable } from "@/components/DataTable";
import { FormField } from "@/components/FormField";
import { formatearInstante, instanteDesdeHoraDeCaracas } from "@/lib/fecha-de-negocio";
import { PageContent } from "@/layout/PageContent";
import { PageHeader } from "@/components/PageHeader";
import { TextInput } from "@/components/TextInput";
import { fechaDeNegocioDeInstante } from "@/lib/fecha-de-negocio";

interface PurchaseOrderSummary {
  id: string;
  code: string;
  status: string;
}

interface PresentationSummary {
  id: string;
  code: string;
  name: string;
}

const ESTADOS: Record<string, string> = {
  DRAFT: "Borrador",
  CONFIRMED: "Confirmada",
  QUALITY_PENDING: "Pendiente de calidad",
  ACCEPTED: "Aceptada",
  PARTIALLY_ACCEPTED: "Aceptada parcialmente",
  REJECTED: "Rechazada",
  CLOSED: "Cerrada",
  CANCELLED: "Anulada",
};

const columnHelper = createColumnHelper<GoodsReceiptSummary>();

/** Sí / no / sin comprobar, para las cuatro comparaciones de la etapa 4. */
function marca(valor: boolean | null | undefined): string {
  if (valor === null || valor === undefined) return "—";
  return valor ? "coincide" : "no coincide";
}

export function RecepcionesPage(): React.JSX.Element {
  const queryClient = useQueryClient();
  const { notify } = useNotifications();
  const { puede } = useAutoridad();

  const [newCode, setNewCode] = useState("");
  const [newOrder, setNewOrder] = useState("");
  const [newWarehouse, setNewWarehouse] = useState("");
  const [newScheduled, setNewScheduled] = useState("");
  const [newPackingList, setNewPackingList] = useState("");
  const [newInvoice, setNewInvoice] = useState("");
  const [newPackages, setNewPackages] = useState("");

  const [selected, setSelected] = useState<string>("");
  const [lineOrderLine, setLineOrderLine] = useState("");
  const [lineProduct, setLineProduct] = useState("");
  const [linePresentation, setLinePresentation] = useState("");
  const [lineReceived, setLineReceived] = useState("");
  const [lineAccepted, setLineAccepted] = useState("");
  const [lineCondition, setLineCondition] = useState("BUENO");
  const [lineDamaged, setLineDamaged] = useState("");
  const [lineDamageNotes, setLineDamageNotes] = useState("");
  const [lineLot, setLineLot] = useState("");
  const [lineExpiry, setLineExpiry] = useState("");
  const [lineSerials, setLineSerials] = useState("");

  const [packagesReceived, setPackagesReceived] = useState("");
  const [inspectionNotes, setInspectionNotes] = useState("");

  const query = useQuery({
    queryKey: ["compras", "recepciones"],
    queryFn: () => apiFetch<{ items: GoodsReceiptSummary[] }>("/purchasing/receipts"),
    retry: false,
  });
  const orders = useQuery({
    queryKey: ["compras", "ordenes"],
    queryFn: () => apiFetch<PagedResult<PurchaseOrderSummary>>("/purchasing/orders"),
    retry: false,
  });
  const products = useQuery({
    queryKey: ["maestros", "productos"],
    queryFn: () => apiFetch<PagedResult<CatalogItemSummary>>("/maestros/catalogos/items?status=ACTIVE"),
    retry: false,
  });
  const presentations = useQuery({
    queryKey: ["maestros", "presentaciones", lineProduct],
    queryFn: () => apiFetch<PresentationSummary[]>(`/maestros/productos/${lineProduct}/presentaciones`),
    enabled: Boolean(lineProduct),
    retry: false,
  });
  const detail = useQuery({
    queryKey: ["compras", "recepcion", selected],
    queryFn: () => apiFetch<GoodsReceiptDetail>(`/purchasing/receipts/${selected}`),
    enabled: Boolean(selected),
    retry: false,
  });

  const refresh = async (): Promise<void> => {
    await queryClient.invalidateQueries({ queryKey: ["compras", "recepciones"] });
    await queryClient.invalidateQueries({ queryKey: ["compras", "recepcion"] });
  };

  const fallo = (titulo: string, err: unknown): void => {
    const message = err instanceof ApiError ? err.message : err instanceof Error ? err.message : titulo;
    notify({ type: "error", title: titulo, description: message });
  };

  const createReceipt = async (): Promise<void> => {
    try {
      const body: Record<string, unknown> = {
        code: newCode,
        order_id: newOrder,
        warehouse_id: newWarehouse,
        packing_list_ref: newPackingList || null,
        supplier_invoice_ref: newInvoice || null,
        packages_declared: newPackages === "" ? null : Number(newPackages),
      };
      if (newScheduled) body.unloading_scheduled_at = instanteDesdeHoraDeCaracas(newScheduled) ?? undefined;
      const rec = await apiFetch<GoodsReceiptDetail>("/purchasing/receipts", { method: "POST", body });
      notify({ type: "success", title: "Recepción creada", description: newCode });
      setSelected(rec.id);
      setNewCode("");
      setNewPackingList("");
      setNewInvoice("");
      setNewPackages("");
      setNewScheduled("");
      await refresh();
    } catch (err) {
      fallo("No fue posible crear la recepción", err);
    }
  };

  const runAction = async (id: string, action: string, body?: unknown): Promise<void> => {
    try {
      await apiFetch(`/purchasing/receipts/${id}/${action}`, { method: "POST", body: body ?? {} });
      await refresh();
      notify({ type: "success", title: "Recepción actualizada", description: action });
    } catch (err) {
      fallo("No fue posible actualizar la recepción", err);
    }
  };

  const addLine = async (): Promise<void> => {
    if (!selected || !lineOrderLine || !lineProduct) return;
    try {
      const recibido = Number(lineReceived) || 0;
      const aceptado = lineAccepted === "" ? recibido : Number(lineAccepted);
      await apiFetch(`/purchasing/receipts/${selected}/lines`, {
        method: "POST",
        body: {
          order_line_id: lineOrderLine,
          product_id: lineProduct,
          quantity_received: recibido,
          quantity_accepted: aceptado,
          quantity_rejected: recibido - aceptado,
          presentation_id: linePresentation || null,
          physical_condition: lineCondition || null,
          damaged_quantity: lineDamaged === "" ? null : Number(lineDamaged),
          damage_notes: lineDamageNotes || null,
          identification_ok: true,
          reference_ok: true,
          lot_number: lineLot || null,
          expiry_date: lineExpiry || null,
          serials: lineSerials ? lineSerials.split(",").map((x) => x.trim()).filter(Boolean) : null,
        },
      });
      notify({ type: "success", title: "Línea recibida", description: `${recibido} registrado` });
      setLineReceived("");
      setLineAccepted("");
      setLineDamaged("");
      setLineDamageNotes("");
      setLineLot("");
      setLineExpiry("");
      setLineSerials("");
      await refresh();
    } catch (err) {
      fallo("No fue posible registrar la línea", err);
    }
  };

  const columns = [
    columnHelper.accessor("code", { header: "Código" }),
    columnHelper.accessor("order_id", { header: "Orden", cell: ({ getValue }) => getValue().slice(0, 8) + "…" }),
    columnHelper.accessor("status", { header: "Estado", cell: ({ getValue }) => ESTADOS[getValue()] ?? getValue() }),
    columnHelper.accessor("quality_status", { header: "Conformidad" }),
    columnHelper.accessor("arrival_at", {
      header: "Arribo",
      cell: ({ getValue }) => (getValue() ? formatearInstante(getValue()) : "sin confirmar"),
    }),
    columnHelper.display({
      id: "bultos",
      header: "Bultos",
      cell: ({ row }) => {
        const r = row.original;
        if (r.packages_declared == null && r.packages_received == null) return "—";
        return `${r.packages_received ?? "?"} de ${r.packages_declared ?? "?"}`;
      },
    }),
    columnHelper.accessor("record_issued_at", {
      header: "Acta",
      cell: ({ getValue }) => fechaDeNegocioDeInstante(getValue()),
    }),
    columnHelper.display({
      id: "actions",
      header: "Acciones",
      cell: ({ row }) => {
        const r = row.original;
        const abierta = r.status === "DRAFT" || r.status === "CONFIRMED";
        const puedeReceiptId = (accion: string) => puede("POST", `/purchasing/receipts/${r.id}/${accion}`);
        return (
          <div className="flex justify-end gap-1">
            <AsyncButton size="sm" variant="secondary" onClick={async () => setSelected(r.id)}>
              detalle
            </AsyncButton>
            {abierta && !r.arrival_at && puedeReceiptId("arrival") ? (
              <AsyncButton size="sm" variant="secondary" onClick={() => runAction(r.id, "arrival")}>
                confirmar arribo
              </AsyncButton>
            ) : null}
            {r.status === "DRAFT" && puedeReceiptId("confirm") ? (
              <AsyncButton size="sm" variant="secondary" onClick={() => runAction(r.id, "confirm")}>
                confirmar
              </AsyncButton>
            ) : null}
            {r.status === "CONFIRMED" && r.quality_status !== "APPROVED" && puedeReceiptId("quality") ? (
              <AsyncButton size="sm" variant="secondary" onClick={() => runAction(r.id, "quality", { quality_status: "APPROVED" })}>
                conforme
              </AsyncButton>
            ) : null}
            {r.status === "CONFIRMED" && r.quality_status === "APPROVED" && puedeReceiptId("accept") ? (
              <AsyncButton size="sm" variant="primary" onClick={() => runAction(r.id, "accept")}>
                aceptar
              </AsyncButton>
            ) : null}
          </div>
        );
      },
    }),
  ];

  const d = detail.data;

  return (
    <PageContent maxWidth="full">
      <PageHeader
        title="Recepciones"
        description="Recepción física contra orden: arribo, bultos, comparación documental, inspección, lote, serial y vencimiento. La mercancía queda en el almacén; ubicarla es del put-away."
        crumbs={[{ label: "Compras" }, { label: "Recepciones" }]}
      />

      <Autorizado operacion={["POST", "/purchasing/receipts"]}>
      <section className="mb-4 rounded-lg border border-border-default bg-surface-0 p-4">
        <h2 className="mb-2 text-base font-semibold text-text-900">Nueva recepción</h2>
        <form className="flex flex-wrap items-end gap-3" onSubmit={(e) => e.preventDefault()}>
          <FormField label="Código" required>
            <TextInput value={newCode} onChange={(e) => setNewCode(e.target.value)} placeholder="REC-0001" required />
          </FormField>
          <FormField label="Orden de compra" required>
            <select value={newOrder} onChange={(e) => setNewOrder(e.target.value)} className="h-10 w-56 rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900">
              <option value="">Seleccionar…</option>
              {(orders.data?.items ?? []).filter((o) => ["APPROVED", "PARTIALLY_RECEIVED", "RECEIVED"].includes(o.status)).map((o) => (
                <option key={o.id} value={o.id}>{o.code}</option>
              ))}
            </select>
          </FormField>
          <FormField label="Almacén" required>
            <TextInput value={newWarehouse} onChange={(e) => setNewWarehouse(e.target.value)} placeholder="Identificador del almacén" required />
          </FormField>
          <FormField label="Descarga programada" help="Etapa 2 del proceso · hora de Caracas">
            <TextInput type="datetime-local" value={newScheduled} onChange={(e) => setNewScheduled(e.target.value)} />
          </FormField>
          <FormField label="Packing list" help="Contra qué se comparará">
            <TextInput value={newPackingList} onChange={(e) => setNewPackingList(e.target.value)} placeholder="PL-0001" />
          </FormField>
          <FormField label="Factura del proveedor">
            <TextInput value={newInvoice} onChange={(e) => setNewInvoice(e.target.value)} placeholder="FAC-0001" />
          </FormField>
          <FormField label="Bultos declarados">
            <TextInput type="number" min="0" value={newPackages} onChange={(e) => setNewPackages(e.target.value)} />
          </FormField>
          <AsyncButton type="submit" variant="primary" onClick={createReceipt}>Crear</AsyncButton>
        </form>
      </section>
      </Autorizado>

      <DataTable
        columns={columns}
        data={query.data?.items ?? []}
        loading={query.isLoading}
        error={query.isError ? "No fue posible cargar las recepciones." : null}
        getRowId={(row) => row.id}
        emptyTitle="Sin recepciones"
        emptyDescription="Aún no hay recepciones registradas."
      />

      {d ? (
        <>
          <section className="mt-4 rounded-lg border border-border-default bg-surface-0 p-4">
            <h2 className="mb-2 text-base font-semibold text-text-900">Inspección de {d.code}</h2>
            <p className="mb-3 text-sm text-text-500">
              Packing list {d.packing_list_ref ?? "—"}: {marca(d.packing_list_match)} · Factura {d.supplier_invoice_ref ?? "—"}: {marca(d.supplier_invoice_match)} · Orden: {marca(d.order_match)} · Documentación: {marca(d.documentation_match)}
              {d.inspected_at ? ` · inspeccionada el ${formatearInstante(d.inspected_at)}` : " · sin inspeccionar"}
            </p>
            <form className="flex flex-wrap items-end gap-3" onSubmit={(e) => e.preventDefault()}>
              <FormField label="Bultos contados" help={`Declarados: ${d.packages_declared ?? "—"}`}>
                <TextInput type="number" min="0" value={packagesReceived} onChange={(e) => setPackagesReceived(e.target.value)} />
              </FormField>
              <FormField label="Observaciones">
                <TextInput value={inspectionNotes} onChange={(e) => setInspectionNotes(e.target.value)} placeholder="Lo que se vio al abrir" />
              </FormField>
              {puede("POST", `/purchasing/receipts/${d.id}/inspection`) ? (
                <AsyncButton
                  variant="secondary"
                  onClick={() =>
                    runAction(d.id, "inspection", {
                      packing_list_match: true,
                      supplier_invoice_match: true,
                      order_match: true,
                      documentation_match: true,
                      packages_received: packagesReceived === "" ? null : Number(packagesReceived),
                      notes: inspectionNotes || null,
                    })
                  }
                >
                  Registrar inspección conforme
                </AsyncButton>
              ) : null}
              {puede("POST", `/purchasing/receipts/${d.id}/inspection`) ? (
                <AsyncButton
                  variant="secondary"
                  onClick={() =>
                    runAction(d.id, "inspection", {
                      packing_list_match: false,
                      supplier_invoice_match: false,
                      order_match: false,
                      documentation_match: false,
                      packages_received: packagesReceived === "" ? null : Number(packagesReceived),
                      notes: inspectionNotes || null,
                    })
                  }
                >
                  Registrar diferencias
                </AsyncButton>
              ) : null}
            </form>
          </section>

          <Autorizado operacion={["POST", `/purchasing/receipts/${d.id}/lines`]}>
          <section className="mt-4 rounded-lg border border-border-default bg-surface-0 p-4">
            <h2 className="mb-2 text-base font-semibold text-text-900">Recibir una línea</h2>
            <form className="flex flex-wrap items-end gap-3" onSubmit={(e) => e.preventDefault()}>
              <FormField label="Línea de la orden" required>
                <TextInput value={lineOrderLine} onChange={(e) => setLineOrderLine(e.target.value)} placeholder="Identificador de la línea" required />
              </FormField>
              <FormField label="Producto" required>
                <select value={lineProduct} onChange={(e) => { setLineProduct(e.target.value); setLinePresentation(""); }} className="h-10 w-52 rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900">
                  <option value="">Seleccionar…</option>
                  {(products.data?.items ?? []).map((p) => (
                    <option key={p.id} value={p.id}>{p.code} · {p.name}</option>
                  ))}
                </select>
              </FormField>
              <FormField label="Presentación" help="Con la que llegó; el inventario entra en unidad base">
                <select value={linePresentation} onChange={(e) => setLinePresentation(e.target.value)} className="h-10 w-48 rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900" disabled={!lineProduct}>
                  <option value="">Unidad base</option>
                  {(presentations.data ?? []).map((p) => (
                    <option key={p.id} value={p.id}>{p.code} · {p.name}</option>
                  ))}
                </select>
              </FormField>
              <FormField label="Recibido" required>
                <TextInput type="number" min="0" value={lineReceived} onChange={(e) => setLineReceived(e.target.value)} required />
              </FormField>
              <FormField label="Aceptado" help="Vacío: todo lo recibido">
                <TextInput type="number" min="0" value={lineAccepted} onChange={(e) => setLineAccepted(e.target.value)} />
              </FormField>
              <FormField label="Estado físico">
                <select value={lineCondition} onChange={(e) => setLineCondition(e.target.value)} className="h-10 w-40 rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900">
                  <option value="BUENO">Bueno</option>
                  <option value="DAÑADO">Dañado</option>
                  <option value="PARCIAL">Parcialmente dañado</option>
                </select>
              </FormField>
              <FormField label="Cantidad dañada">
                <TextInput type="number" min="0" value={lineDamaged} onChange={(e) => setLineDamaged(e.target.value)} />
              </FormField>
              <FormField label="Detalle del daño">
                <TextInput value={lineDamageNotes} onChange={(e) => setLineDamageNotes(e.target.value)} placeholder="Qué se vio" />
              </FormField>
              <FormField label="Lote">
                <TextInput value={lineLot} onChange={(e) => setLineLot(e.target.value)} placeholder="L-0001" />
              </FormField>
              <FormField label="Vencimiento">
                <TextInput type="date" value={lineExpiry} onChange={(e) => setLineExpiry(e.target.value)} />
              </FormField>
              <FormField label="Seriales" help="Separados por coma">
                <TextInput value={lineSerials} onChange={(e) => setLineSerials(e.target.value)} placeholder="S-1, S-2" />
              </FormField>
              <AsyncButton type="submit" variant="secondary" onClick={addLine}>Registrar</AsyncButton>
            </form>

            <div className="mt-3 overflow-x-auto" tabIndex={0} role="region" aria-label={`Líneas de la recepción ${d.code}`}>
              <table className="min-w-full text-sm">
                <caption className="sr-only">Líneas recibidas de {d.code}</caption>
                <thead>
                  <tr className="text-left text-text-500">
                    <th scope="col" className="pr-4">Producto</th>
                    <th scope="col" className="pr-4">Recibido</th>
                    <th scope="col" className="pr-4">En base</th>
                    <th scope="col" className="pr-4">Factor</th>
                    <th scope="col" className="pr-4">Estado</th>
                    <th scope="col" className="pr-4">Dañado</th>
                    <th scope="col" className="pr-4">Sobrante</th>
                    <th scope="col" className="pr-4">Lote</th>
                  </tr>
                </thead>
                <tbody>
                  {d.lines.map((l) => (
                    <tr key={l.id}>
                      <td className="pr-4">{l.product_id.slice(0, 8)}…</td>
                      <td className="pr-4">{l.quantity_received}</td>
                      <td className="pr-4">{l.base_quantity_received ?? "—"}</td>
                      <td className="pr-4">{l.conversion_factor_snapshot ?? "—"}</td>
                      <td className="pr-4">{l.physical_condition ?? "—"}</td>
                      <td className="pr-4">{l.damaged_quantity ?? "—"}</td>
                      <td className="pr-4">{l.overage_base_quantity ?? "—"}</td>
                      <td className="pr-4">{l.lot_number ?? "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
          </Autorizado>
        </>
      ) : null}
    </PageContent>
  );
}
