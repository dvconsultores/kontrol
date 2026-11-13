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
import { useQueries, useQuery, useQueryClient } from "@tanstack/react-query";
import { createColumnHelper } from "@tanstack/react-table";
import { useState } from "react";
import { Link, useSearchParams } from "react-router";

import { ApiError, apiFetch } from "@/api/client";
import { Autorizado } from "@/components/Autorizado";
import { useAutoridad } from "@/app/autoridad/AutoridadContext";
import { ReportesDeRecepcion } from "@/modules/compras/importaciones/ReporteDiferencias";
import type {
  CatalogItemSummary,
  GoodsReceiptDetail,
  GoodsReceiptSummary,
  PurchaseOrderLine,
  PurchaseOrderSummary,
} from "@/api/types";
import { useCompany } from "@/app/contexts/CompanyContext";
import { useNotifications } from "@/app/contexts/NotificationContext";
import { AsyncButton } from "@/components/AsyncButton";
import { DataTable } from "@/components/DataTable";
import { FormField } from "@/components/FormField";
import { formatearInstante, instanteDesdeHoraDeCaracas } from "@/lib/fecha-de-negocio";
import { PageContent } from "@/layout/PageContent";
import { PageHeader } from "@/components/PageHeader";
import { TextInput } from "@/components/TextInput";
import { fechaDeNegocioDeInstante } from "@/lib/fecha-de-negocio";
import { AvisoDeAlmacenes } from "@/modules/organizacion/almacenes/AvisoDeAlmacenes";
import { useAlmacenesDeEmpresa } from "@/modules/organizacion/almacenes/useAlmacenesDeEmpresa";

import { CondicionDelProceso } from "./CondicionDelProceso";
import { ZonaTemporal } from "./ZonaTemporal";
import { useOrdenesRecibibles } from "./useOrdenesRecibibles";

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

// Lo que falta por recibir, sin negativos: un sobrante no deja saldo pendiente.
function pendienteDeLinea(linea: PurchaseOrderLine): number {
  return Math.max(0, Number((Number(linea.quantity_ordered) - Number(linea.quantity_received)).toFixed(6)));
}

// Vacío es «no declarado»: se envía nulo, nunca un sí por omisión.
function hechoDeclarado(valor: string): boolean | null {
  return valor === "" ? null : valor === "true";
}

interface SelectorDeHechoProps {
  etiqueta: string;
  vacio: string;
  si: string;
  no: string;
  valor: string;
  alCambiar: (valor: string) => void;
}

function SelectorDeHecho({ etiqueta, vacio, si, no, valor, alCambiar }: SelectorDeHechoProps): React.JSX.Element {
  return (
    <FormField label={etiqueta}>
      <select value={valor} onChange={(e) => alCambiar(e.target.value)} className="h-10 w-44 rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900">
        <option value="">{vacio}</option>
        <option value="true">{si}</option>
        <option value="false">{no}</option>
      </select>
    </FormField>
  );
}

/** Sí / no / sin comprobar, para las cuatro comparaciones de la etapa 4. */
function marca(valor: boolean | null | undefined): string {
  if (valor === null || valor === undefined) return "—";
  return valor ? "coincide" : "no coincide";
}

export function RecepcionesPage(): React.JSX.Element {
  const queryClient = useQueryClient();
  const { notify } = useNotifications();
  const { puede } = useAutoridad();
  const { activeCompany } = useCompany();

  const [newCode, setNewCode] = useState("");
  const [newOrder, setNewOrder] = useState("");
  const [newWarehouse, setNewWarehouse] = useState("");
  const [newScheduled, setNewScheduled] = useState("");
  const [newPackingList, setNewPackingList] = useState("");
  const [newInvoice, setNewInvoice] = useState("");
  const [newPackages, setNewPackages] = useState("");

  const [searchParams] = useSearchParams();
  const [selected, setSelected] = useState<string>(() => searchParams.get("recepcion") ?? "");
  const importacion = searchParams.get("importacion");
  const [lineOrderLine, setLineOrderLine] = useState("");
  const [linePresentation, setLinePresentation] = useState("");
  const [lineReceived, setLineReceived] = useState("");
  const [lineAccepted, setLineAccepted] = useState("");
  const [lineCondition, setLineCondition] = useState("");
  const [lineIdentification, setLineIdentification] = useState("");
  const [lineReference, setLineReference] = useState("");
  const [lineDamaged, setLineDamaged] = useState("");
  const [lineDamageNotes, setLineDamageNotes] = useState("");
  const [lineLot, setLineLot] = useState("");
  const [lineExpiry, setLineExpiry] = useState("");
  const [lineSerials, setLineSerials] = useState("");

  const [packagesReceived, setPackagesReceived] = useState("");
  const [inspectionNotes, setInspectionNotes] = useState("");
  const [packingListMatch, setPackingListMatch] = useState("");
  const [invoiceMatch, setInvoiceMatch] = useState("");
  const [orderMatch, setOrderMatch] = useState("");
  const [documentationMatch, setDocumentationMatch] = useState("");
  const [cancelReason, setCancelReason] = useState("");

  const query = useQuery({
    queryKey: ["compras", "recepciones"],
    queryFn: () => apiFetch<{ items: GoodsReceiptSummary[] }>("/purchasing/receipts"),
    retry: false,
  });
  const ordenesRecibibles = useOrdenesRecibibles(activeCompany?.id ?? null);
  // Una orden que sale de la lista, por búsqueda o por cambio de empresa, no se envía.
  const ordenElegida = ordenesRecibibles.ordenes.some((o) => o.id === newOrder) ? newOrder : "";
  const detail = useQuery({
    queryKey: ["compras", "recepcion", selected],
    queryFn: () => apiFetch<GoodsReceiptDetail>(`/purchasing/receipts/${selected}`),
    enabled: Boolean(selected),
    retry: false,
  });
  const d = detail.data;
  // Las líneas salen del detalle de la orden de la recepción: el listado está paginado.
  const orden = useQuery({
    queryKey: ["compras", "orden", d?.order_id],
    queryFn: () => apiFetch<PurchaseOrderSummary>(`/purchasing/orders/${d?.order_id}`),
    enabled: Boolean(d?.order_id),
    retry: false,
  });
  const lineasDeOrden = orden.data?.lines ?? [];
  const lineaElegida = lineasDeOrden.find((l) => l.id === lineOrderLine);
  const productoDeLinea = lineaElegida?.product_id ?? "";
  const presentations = useQuery({
    queryKey: ["maestros", "presentaciones", productoDeLinea],
    queryFn: () => apiFetch<PresentationSummary[]>(`/maestros/productos/${productoDeLinea}/presentaciones`),
    enabled: Boolean(productoDeLinea),
    retry: false,
  });
  // Una presentación de otra línea no se envía.
  const presentacionElegida = (presentations.data ?? []).some((p) => p.id === linePresentation) ? linePresentation : "";
  // Por identificador: el producto puede estar inactivo o fuera de la primera página del catálogo.
  const idsDeProducto = [...new Set([...lineasDeOrden, ...(d?.lines ?? [])].map((l) => l.product_id))];
  const productos = useQueries({
    queries: idsDeProducto.map((id) => ({
      queryKey: ["maestros", "producto", id],
      queryFn: () => apiFetch<CatalogItemSummary>(`/maestros/catalogos/items/${id}`),
      retry: false,
    })),
  });
  const nombreDeProducto = (id: string): string => {
    const producto = productos[idsDeProducto.indexOf(id)]?.data;
    return producto ? `${producto.code} · ${producto.name}` : "Producto sin identificar";
  };
  const etiquetaDeLinea = (linea: PurchaseOrderLine): string =>
    `${nombreDeProducto(linea.product_id)} — pedido ${Number(linea.quantity_ordered)}, recibido ${Number(linea.quantity_received)}, pendiente ${pendienteDeLinea(linea)}${linea.destination_warehouse ? `, destino ${linea.destination_warehouse.code}` : ""}`;

  const warehouses = useAlmacenesDeEmpresa(activeCompany?.id ?? null);
  // Una selección que ya no está en la lista, por ejemplo de otra empresa, no se envía.
  // Solo un almacén activo recibe mercancía; el backend lo exige también.
  const almacenesActivos = (warehouses.data?.items ?? []).filter((w) => w.status === "ACTIVE");
  const almacenElegido = almacenesActivos.some((w) => w.id === newWarehouse) ? newWarehouse : "";

  const refresh = async (): Promise<void> => {
    await queryClient.invalidateQueries({ queryKey: ["compras", "recepciones"] });
    await queryClient.invalidateQueries({ queryKey: ["compras", "recepcion"] });
    await queryClient.invalidateQueries({ queryKey: ["compras", "orden"] });
    await queryClient.invalidateQueries({ queryKey: ["compras", "ordenes-recibibles"] });
  };

  const fallo = (titulo: string, err: unknown): void => {
    const message = err instanceof ApiError ? err.message : err instanceof Error ? err.message : titulo;
    notify({ type: "error", title: titulo, description: message });
  };

  const limpiarLinea = (): void => {
    setLineOrderLine("");
    setLinePresentation("");
    setLineReceived("");
    setLineAccepted("");
    setLineCondition("");
    setLineIdentification("");
    setLineReference("");
    setLineDamaged("");
    setLineDamageNotes("");
    setLineLot("");
    setLineExpiry("");
    setLineSerials("");
  };

  // Lo capturado para una línea no pasa a otra recepción, aunque sea de la misma orden.
  const elegirRecepcion = (id: string): void => {
    setSelected(id);
    limpiarLinea();
    setPackagesReceived("");
    setInspectionNotes("");
    setPackingListMatch("");
    setInvoiceMatch("");
    setOrderMatch("");
    setDocumentationMatch("");
    setCancelReason("");
  };

  const createReceipt = async (): Promise<void> => {
    if (!ordenElegida) {
      notify({ type: "error", title: "No fue posible crear la recepción", description: "Seleccione una orden de compra." });
      return;
    }
    if (!almacenElegido) {
      notify({ type: "error", title: "No fue posible crear la recepción", description: "Seleccione un almacén." });
      return;
    }
    try {
      const body: Record<string, unknown> = {
        code: newCode,
        order_id: ordenElegida,
        warehouse_id: almacenElegido,
        packing_list_ref: newPackingList || null,
        supplier_invoice_ref: newInvoice || null,
        packages_declared: newPackages === "" ? null : Number(newPackages),
      };
      if (newScheduled) body.unloading_scheduled_at = instanteDesdeHoraDeCaracas(newScheduled) ?? undefined;
      const rec = await apiFetch<GoodsReceiptDetail>("/purchasing/receipts", { method: "POST", body });
      notify({ type: "success", title: "Recepción creada", description: newCode });
      elegirRecepcion(rec.id);
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

  const anular = async (id: string): Promise<void> => {
    const motivo = cancelReason.trim();
    if (!motivo) {
      notify({ type: "error", title: "No fue posible anular la recepción", description: "Indique el motivo." });
      return;
    }
    await runAction(id, "cancel", { reason: motivo });
    setCancelReason("");
  };

  const addLine = async (): Promise<void> => {
    if (!selected) return;
    if (!lineaElegida) {
      notify({ type: "error", title: "No fue posible registrar la línea", description: "Seleccione la línea de la orden." });
      return;
    }
    try {
      const recibido = Number(lineReceived) || 0;
      const aceptado = lineAccepted === "" ? recibido : Number(lineAccepted);
      await apiFetch(`/purchasing/receipts/${selected}/lines`, {
        method: "POST",
        body: {
          order_line_id: lineaElegida.id,
          product_id: lineaElegida.product_id,
          quantity_received: recibido,
          quantity_accepted: aceptado,
          quantity_rejected: recibido - aceptado,
          presentation_id: presentacionElegida || null,
          physical_condition: lineCondition || null,
          damaged_quantity: lineDamaged === "" ? null : Number(lineDamaged),
          damage_notes: lineDamageNotes || null,
          identification_ok: hechoDeclarado(lineIdentification),
          reference_ok: hechoDeclarado(lineReference),
          lot_number: lineLot || null,
          expiry_date: lineExpiry || null,
          serials: lineSerials ? lineSerials.split(",").map((x) => x.trim()).filter(Boolean) : null,
        },
      });
      notify({ type: "success", title: "Línea recibida", description: `${recibido} registrado` });
      limpiarLinea();
      await refresh();
    } catch (err) {
      fallo("No fue posible registrar la línea", err);
    }
  };

  const columns = [
    columnHelper.accessor("code", { header: "Código" }),
    columnHelper.accessor("order_code", { header: "Orden", cell: ({ getValue }) => getValue() ?? "—" }),
    columnHelper.accessor("status", { header: "Estado", cell: ({ getValue }) => ESTADOS[getValue()] ?? getValue() }),
    // Spec 018 · §3: la condición del proceso, tal como la deriva el backend.
    columnHelper.display({
      id: "condicion",
      header: "Condición",
      cell: ({ row }) => (
        <CondicionDelProceso
          condicion={row.original.process_condition}
          receiptId={row.original.id}
          importacionId={importacion ?? undefined}
        />
      ),
    }),
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
    columnHelper.accessor("unloading_scheduled_at", {
      header: "Descarga programada",
      cell: ({ getValue }) => (getValue() ? formatearInstante(getValue()) : "Sin programar"),
    }),
    columnHelper.accessor("temporary_location_label", {
      header: "Zona temporal",
      cell: ({ getValue }) => getValue() ?? "Sin registrar",
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
            <AsyncButton size="sm" variant="secondary" onClick={async () => elegirRecepcion(r.id)}>
              detalle
            </AsyncButton>
            {abierta && !r.arrival_at && puedeReceiptId("arrival") ? (
              <AsyncButton size="sm" variant="secondary" onClick={() => runAction(r.id, "arrival")}>
                confirmar arribo
              </AsyncButton>
            ) : null}
            {/* Los botones salen de allowed_actions que publica el backend; el estado no decide. */}
            {r.allowed_actions?.confirm && puedeReceiptId("confirm") ? (
              <AsyncButton size="sm" variant="secondary" onClick={() => runAction(r.id, "confirm")}>
                confirmar
              </AsyncButton>
            ) : null}
            {r.allowed_actions?.send_to_quality && puedeReceiptId("quality") ? (
              <AsyncButton size="sm" variant="secondary" onClick={() => runAction(r.id, "quality", {})}>
                enviar a calidad
              </AsyncButton>
            ) : null}
            {r.allowed_actions?.record_quality && puedeReceiptId("quality") ? (
              <AsyncButton size="sm" variant="secondary" onClick={() => runAction(r.id, "quality", { quality_status: "APPROVED" })}>
                conforme
              </AsyncButton>
            ) : null}
            {r.allowed_actions?.record_quality && puedeReceiptId("quality") ? (
              <AsyncButton size="sm" variant="secondary" onClick={() => runAction(r.id, "quality", { quality_status: "REJECTED" })}>
                no conforme
              </AsyncButton>
            ) : null}
            {r.allowed_actions?.accept && puedeReceiptId("accept") ? (
              <AsyncButton size="sm" variant="primary" onClick={() => runAction(r.id, "accept")}>
                aceptar
              </AsyncButton>
            ) : null}
            {r.allowed_actions?.close && puedeReceiptId("close") ? (
              <AsyncButton size="sm" variant="secondary" onClick={() => runAction(r.id, "close")}>
                cerrar
              </AsyncButton>
            ) : null}
          </div>
        );
      },
    }),
  ];

  return (
    <PageContent maxWidth="full">
      {importacion ? (
        <div className="mb-4">
          <Link
            to={`/compras/importaciones/${importacion}`}
            className="text-sm font-medium text-brand-600 hover:text-brand-700"
          >
            Volver al expediente
          </Link>
        </div>
      ) : null}
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
          {ordenesRecibibles.consulta.isFetchNextPageError ? <p role="alert" className="w-full text-sm text-danger-600">No fue posible cargar más órdenes.</p> : null}
          {ordenesRecibibles.consulta.isError && !ordenesRecibibles.consulta.isFetchNextPageError ? <p role="alert" className="w-full text-sm text-danger-600">No fue posible cargar las órdenes.</p> : null}
          {ordenesRecibibles.consulta.isLoading ? <p role="status" className="w-full text-sm text-text-500">Cargando órdenes…</p> : null}
          {ordenesRecibibles.consulta.data && ordenesRecibibles.ordenes.length === 0 ? <p role="status" className="w-full text-sm text-text-500">No hay órdenes por recibir.</p> : null}
          {ordenesRecibibles.consulta.hasNextPage ? <p role="status" className="w-full text-sm text-text-500">{`Mostrando ${ordenesRecibibles.ordenes.length} de ${ordenesRecibibles.total} órdenes.`}</p> : null}
          <FormField label="Buscar orden" help="Por código">
            <TextInput value={ordenesRecibibles.busqueda} onChange={(e) => ordenesRecibibles.setBusqueda(e.target.value)} placeholder="OC-0001" />
          </FormField>
          <FormField label="Orden de compra" required>
            <select value={ordenElegida} onChange={(e) => setNewOrder(e.target.value)} required className="h-10 w-56 rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900">
              <option value="">Seleccionar…</option>
              {ordenesRecibibles.ordenes.map((o) => (
                <option key={o.id} value={o.id}>{o.code}</option>
              ))}
            </select>
          </FormField>
          {ordenesRecibibles.consulta.hasNextPage ? (
            <AsyncButton variant="secondary" onClick={async () => { await ordenesRecibibles.consulta.fetchNextPage(); }}>
              Cargar más órdenes
            </AsyncButton>
          ) : null}
          <AvisoDeAlmacenes consulta={warehouses} />
          {warehouses.data && warehouses.data.items.length > 0 && almacenesActivos.length === 0 ? <p role="status" className="w-full text-sm text-text-500">Esta empresa no tiene almacenes activos.</p> : null}
          <FormField label="Almacén" required>
            <select value={almacenElegido} onChange={(e) => setNewWarehouse(e.target.value)} required className="h-10 w-56 rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900">
              <option value="">Seleccionar…</option>
              {almacenesActivos.map((w) => (
                <option key={w.id} value={w.id}>{w.code} · {w.name}</option>
              ))}
            </select>
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
            <div className="mb-3">
              <p className="mb-1 text-sm font-medium text-text-800">Condición del proceso</p>
              <CondicionDelProceso
                condicion={d.process_condition}
                receiptId={d.id}
                importacionId={importacion ?? undefined}
              />
            </div>
            <div className="mb-3">
              <p className="mb-1 text-sm font-medium text-text-800">Zona temporal</p>
              <p className="text-sm text-text-700">{d.temporary_location?.label ?? "Sin registrar"}</p>
              {d.can_set_temporary_location ? (
                <ZonaTemporal receiptId={d.id} codigo={d.code} onGuardada={refresh} />
              ) : null}
            </div>
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
              <SelectorDeHecho etiqueta="Packing list comparado" vacio="No comparado" si="Coincide" no="No coincide" valor={packingListMatch} alCambiar={setPackingListMatch} />
              <SelectorDeHecho etiqueta="Factura comparada" vacio="No comparado" si="Coincide" no="No coincide" valor={invoiceMatch} alCambiar={setInvoiceMatch} />
              <SelectorDeHecho etiqueta="Orden comparada" vacio="No comparado" si="Coincide" no="No coincide" valor={orderMatch} alCambiar={setOrderMatch} />
              <SelectorDeHecho etiqueta="Documentación comparada" vacio="No comparado" si="Coincide" no="No coincide" valor={documentationMatch} alCambiar={setDocumentationMatch} />
              {puede("POST", `/purchasing/receipts/${d.id}/inspection`) ? (
                <AsyncButton
                  variant="secondary"
                  onClick={() =>
                    runAction(d.id, "inspection", {
                      packing_list_match: hechoDeclarado(packingListMatch),
                      supplier_invoice_match: hechoDeclarado(invoiceMatch),
                      order_match: hechoDeclarado(orderMatch),
                      documentation_match: hechoDeclarado(documentationMatch),
                      packages_received: packagesReceived === "" ? null : Number(packagesReceived),
                      notes: inspectionNotes || null,
                    })
                  }
                >
                  Registrar inspección
                </AsyncButton>
              ) : null}
            </form>
          </section>

          {d.allowed_actions?.cancel && puede("POST", `/purchasing/receipts/${d.id}/cancel`) ? (
            <section className="mt-4 rounded-lg border border-border-default bg-surface-0 p-4">
              <h2 className="mb-2 text-base font-semibold text-text-900">Anulación</h2>
              <form className="flex flex-wrap items-end gap-3" onSubmit={(e) => e.preventDefault()}>
                <FormField label="Motivo de anulación" required help="Solo un borrador se anula; el motivo queda en la auditoría">
                  <TextInput value={cancelReason} onChange={(e) => setCancelReason(e.target.value)} maxLength={255} />
                </FormField>
                <AsyncButton variant="secondary" onClick={() => anular(d.id)}>
                  Anular recepción
                </AsyncButton>
              </form>
            </section>
          ) : null}
          <Autorizado operacion={["POST", `/purchasing/receipts/${d.id}/lines`]}>
          <section className="mt-4 rounded-lg border border-border-default bg-surface-0 p-4">
            <h2 className="mb-2 text-base font-semibold text-text-900">Recibir una línea</h2>
            <form className="flex flex-wrap items-end gap-3" onSubmit={(e) => e.preventDefault()}>
              {orden.isError ? <p role="alert" className="w-full text-sm text-danger-600">No fue posible cargar las líneas de la orden.</p> : null}
              {orden.isLoading ? <p role="status" className="w-full text-sm text-text-500">Cargando líneas de la orden…</p> : null}
              {orden.data && lineasDeOrden.length === 0 ? <p role="status" className="w-full text-sm text-text-500">La orden no tiene líneas.</p> : null}
              {productos.some((p) => p.isError) ? <p role="alert" className="w-full text-sm text-danger-600">No fue posible identificar algunos productos de la orden.</p> : null}
              <FormField label="Línea de la orden" required>
                <select value={lineaElegida?.id ?? ""} onChange={(e) => { setLineOrderLine(e.target.value); setLinePresentation(""); }} required className="h-10 w-96 max-w-full rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900">
                  <option value="">Seleccionar…</option>
                  {lineasDeOrden.map((l) => (
                    <option key={l.id} value={l.id}>{etiquetaDeLinea(l)}</option>
                  ))}
                </select>
              </FormField>
              <FormField label="Producto" help="Lo define la línea de la orden">
                <TextInput value={lineaElegida ? nombreDeProducto(lineaElegida.product_id) : ""} readOnly />
              </FormField>
              <FormField label="Presentación" help="Con la que llegó; el inventario entra en unidad base">
                <select value={presentacionElegida} onChange={(e) => setLinePresentation(e.target.value)} className="h-10 w-48 rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900" disabled={!lineaElegida}>
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
                  <option value="">No observado</option>
                  <option value="BUENO">Bueno</option>
                  <option value="DAÑADO">Dañado</option>
                  <option value="PARCIAL">Parcialmente dañado</option>
                </select>
              </FormField>
              <SelectorDeHecho etiqueta="Identificación" vacio="No observada" si="Correcta" no="Incorrecta" valor={lineIdentification} alCambiar={setLineIdentification} />
              <SelectorDeHecho etiqueta="Referencia" vacio="No observada" si="Correcta" no="Incorrecta" valor={lineReference} alCambiar={setLineReference} />
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
                      <td className="pr-4">{nombreDeProducto(l.product_id)}</td>
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
          <ReportesDeRecepcion recepcionId={d.id} />
        </>
      ) : null}
    </PageContent>
  );
}
