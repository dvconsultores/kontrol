/**
 * Incidencias de recepción — Spec 020.
 *
 * El proceso manda registrar las diferencias, generar su evidencia y
 * escalarlas a Compras. Esta pantalla hace esas tres cosas y registra el
 * tratamiento decidido.
 *
 * Dos límites que la pantalla respeta a propósito. No vuelve a pedir producto,
 * unidad ni presentación: ya viven en la línea de recepción, y pedirlos otra
 * vez crearía dos verdades para el mismo hecho. Y registrar el tratamiento no
 * lo ejecuta: confirmar el inventario es de la Spec 021.
 */
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { createColumnHelper } from "@tanstack/react-table";
import { useState } from "react";

import { ApiError, apiFetch } from "@/api/client";
import type {
  GoodsReceiptDetail,
  GoodsReceiptSummary,
  IncidentOutcome,
  ReceiptIncident,
} from "@/api/types";
import { useNotifications } from "@/app/contexts/NotificationContext";
import { Autorizado } from "@/components/Autorizado";
import { useAutoridad } from "@/app/autoridad/AutoridadContext";
import { AsyncButton } from "@/components/AsyncButton";
import { ConfirmationDialog } from "@/components/ConfirmationDialog";
import { DataTable } from "@/components/DataTable";
import { FormField } from "@/components/FormField";
import { PageContent } from "@/layout/PageContent";
import { PageHeader } from "@/components/PageHeader";
import { TextInput } from "@/components/TextInput";

/** Los cinco tipos del proceso. El documental no lleva línea ni cantidad. */
const TIPOS: Array<{ value: string; label: string; conLinea: boolean }> = [
  { value: "FALTANTE", label: "Faltante", conLinea: true },
  { value: "SOBRANTE", label: "Sobrante", conLinea: true },
  { value: "DANO", label: "Daño", conLinea: true },
  { value: "REFERENCIA_INCORRECTA", label: "Referencia incorrecta", conLinea: true },
  { value: "DIFERENCIA_DOCUMENTAL", label: "Diferencia documental", conLinea: false },
];

/** Los cuatro tratamientos del proceso. El ajuste exige autorización. */
const TRATAMIENTOS: Array<{ value: string; label: string; requiereAprobacion: boolean }> = [
  { value: "AJUSTE_AUTORIZADO", label: "Ajuste autorizado", requiereAprobacion: true },
  { value: "RECLAMO_PROVEEDOR", label: "Reclamo al proveedor", requiereAprobacion: false },
  { value: "INVESTIGACION_INTERNA", label: "Investigación interna", requiereAprobacion: false },
  { value: "CUARENTENA", label: "Mercancía en cuarentena", requiereAprobacion: false },
];

const ESTADOS: Record<string, string> = {
  REGISTRADA: "Registrada",
  ESCALADA: "Escalada a Compras",
  PENDIENTE_AUTORIZACION: "Pendiente de autorización",
  RESUELTA: "Resuelta",
  ANULADA: "Anulada",
};

const etiqueta = (lista: Array<{ value: string; label: string }>, v: string | null): string =>
  lista.find((x) => x.value === v)?.label ?? v ?? "—";

const columnHelper = createColumnHelper<ReceiptIncident>();

export function IncidenciasPage(): React.JSX.Element {
  const queryClient = useQueryClient();
  const { notify } = useNotifications();
  const { puede } = useAutoridad();

  const [receiptId, setReceiptId] = useState("");
  const [newCode, setNewCode] = useState("");
  const [newType, setNewType] = useState("DANO");
  const [newLine, setNewLine] = useState("");
  const [newQuantity, setNewQuantity] = useState("");
  const [newDescription, setNewDescription] = useState("");
  const [selected, setSelected] = useState<ReceiptIncident | null>(null);
  const [resolution, setResolution] = useState("RECLAMO_PROVEEDOR");
  const [reason, setReason] = useState("");
  const [aAnular, setAAnular] = useState<ReceiptIncident | null>(null);
  const [motivoAnulacion, setMotivoAnulacion] = useState("");

  const incidents = useQuery({
    queryKey: ["compras", "incidencias"],
    queryFn: () => apiFetch<{ items: ReceiptIncident[] }>("/purchasing/incidencias"),
    retry: false,
  });
  const receipts = useQuery({
    queryKey: ["compras", "recepciones"],
    queryFn: () => apiFetch<{ items: GoodsReceiptSummary[] }>("/purchasing/receipts"),
    retry: false,
  });
  const receipt = useQuery({
    queryKey: ["compras", "recepcion", receiptId],
    queryFn: () => apiFetch<GoodsReceiptDetail>(`/purchasing/receipts/${receiptId}`),
    enabled: Boolean(receiptId),
    retry: false,
  });
  const outcome = useQuery({
    queryKey: ["compras", "incidencias", "resultado", receiptId],
    queryFn: () => apiFetch<IncidentOutcome>(`/purchasing/receipts/${receiptId}/incidencias/resultado`),
    enabled: Boolean(receiptId),
    retry: false,
  });

  const tipoActual = TIPOS.find((t) => t.value === newType) ?? TIPOS[0];

  const refresh = async (): Promise<void> => {
    await queryClient.invalidateQueries({ queryKey: ["compras", "incidencias"] });
  };

  const fallo = (titulo: string, err: unknown): void => {
    const message = err instanceof ApiError ? err.message : err instanceof Error ? err.message : titulo;
    notify({ type: "error", title: titulo, description: message });
  };

  const registrar = async (): Promise<void> => {
    if (!receiptId) return;
    try {
      const body: Record<string, unknown> = {
        code: newCode,
        incident_type: newType,
        description: newDescription || null,
      };
      if (tipoActual.conLinea) {
        body.receipt_line_id = newLine;
        body.affected_base_quantity = Number(newQuantity) || 0;
      }
      await apiFetch(`/purchasing/receipts/${receiptId}/incidencias`, { method: "POST", body });
      notify({ type: "success", title: "Incidencia registrada", description: newCode });
      setNewCode("");
      setNewQuantity("");
      setNewDescription("");
      await refresh();
    } catch (err) {
      fallo("No fue posible registrar la incidencia", err);
    }
  };

  const accion = async (inc: ReceiptIncident, ruta: string, body: unknown): Promise<void> => {
    try {
      const actualizada = await apiFetch<ReceiptIncident>(
        `/purchasing/receipts/${inc.receipt_id}/incidencias/${inc.id}/${ruta}`,
        { method: "POST", body },
      );
      notify({
        type: "success",
        title: "Incidencia actualizada",
        description: ESTADOS[actualizada.status] ?? actualizada.status,
      });
      setSelected(null);
      setReason("");
      await refresh();
    } catch (err) {
      fallo("No fue posible actualizar la incidencia", err);
    }
  };

  const columns = [
    columnHelper.accessor("code", { header: "Código" }),
    columnHelper.accessor("incident_type", {
      header: "Tipo",
      cell: ({ getValue }) => etiqueta(TIPOS, getValue()),
    }),
    columnHelper.accessor("affected_base_quantity", {
      header: "Cantidad base",
      cell: ({ getValue }) => getValue() ?? "—",
    }),
    columnHelper.accessor("status", {
      header: "Estado",
      cell: ({ getValue }) => ESTADOS[getValue()] ?? getValue(),
    }),
    columnHelper.accessor("resolution", {
      header: "Tratamiento",
      cell: ({ getValue }) => etiqueta(TRATAMIENTOS, getValue() as string | null),
    }),
    columnHelper.display({
      id: "actions",
      header: "Acciones",
      cell: ({ row }) => {
        const inc = row.original;
        const viva = inc.status !== "RESUELTA" && inc.status !== "ANULADA";
        return (
          <div className="flex justify-end gap-1">
            {inc.status === "REGISTRADA" && puede("POST", `/purchasing/receipts/${inc.receipt_id}/incidencias/${inc.id}/escalate`) ? (
              <AsyncButton size="sm" variant="secondary"
                onClick={() => accion(inc, "escalate", { notes: null })}>
                escalar
              </AsyncButton>
            ) : null}
            {viva && puede("POST", `/purchasing/receipts/${inc.receipt_id}/incidencias/${inc.id}/resolve`) ? (
              <AsyncButton size="sm" variant="primary" onClick={async () => setSelected(inc)}>
                tratar
              </AsyncButton>
            ) : null}
            {viva && puede("POST", `/purchasing/receipts/${inc.receipt_id}/incidencias/${inc.id}/cancel`) ? (
              <AsyncButton size="sm" variant="secondary" onClick={async () => setAAnular(inc)}>
                anular
              </AsyncButton>
            ) : null}
          </div>
        );
      },
    }),
  ];

  const lineas = receipt.data?.lines ?? [];

  return (
    <PageContent maxWidth="full">
      <PageHeader
        title="Incidencias de recepción"
        description="Registrar las diferencias observadas al recibir, adjuntar su evidencia y escalarlas a Compras. El tratamiento se decide aquí; confirmarlo contra el inventario es de la confirmación de inventario."
        crumbs={[{ label: "Compras" }, { label: "Incidencias" }]}
      />

      <section className="mb-4 rounded-lg border border-border-default bg-surface-0 p-4">
        <h2 className="mb-2 text-base font-semibold text-text-900">Registrar una diferencia</h2>
        <Autorizado operacion={["POST", `/purchasing/receipts/${receiptId || "_"}/incidencias`]}>
        <form className="flex flex-wrap items-end gap-3" onSubmit={(e) => e.preventDefault()}>
          <FormField label="Recepción" required>
            <select value={receiptId} onChange={(e) => { setReceiptId(e.target.value); setNewLine(""); }} className="h-10 w-56 rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900">
              <option value="">Seleccionar…</option>
              {(receipts.data?.items ?? []).map((r) => (
                <option key={r.id} value={r.id}>{r.code}</option>
              ))}
            </select>
          </FormField>
          <FormField label="Código" required>
            <TextInput value={newCode} onChange={(e) => setNewCode(e.target.value)} placeholder="INC-0001" required />
          </FormField>
          <FormField label="Tipo" required>
            <select value={newType} onChange={(e) => setNewType(e.target.value)} className="h-10 w-52 rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900">
              {TIPOS.map((t) => (
                <option key={t.value} value={t.value}>{t.label}</option>
              ))}
            </select>
          </FormField>
          {tipoActual.conLinea ? (
            <>
              <FormField label="Línea recibida" required help="Producto, unidad y presentación salen de ella">
                <select value={newLine} onChange={(e) => setNewLine(e.target.value)} className="h-10 w-56 rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900" disabled={!receiptId}>
                  <option value="">Seleccionar…</option>
                  {lineas.map((l) => (
                    <option key={l.id} value={l.id}>
                      {l.product_id.slice(0, 8)}… · recibido {l.quantity_received}
                      {l.base_quantity_received ? ` (${l.base_quantity_received} base)` : ""}
                    </option>
                  ))}
                </select>
              </FormField>
              <FormField label="Cantidad afectada" required help="En unidad base">
                <TextInput type="number" min="0" value={newQuantity} onChange={(e) => setNewQuantity(e.target.value)} required />
              </FormField>
            </>
          ) : null}
          <FormField label="Descripción">
            <TextInput value={newDescription} onChange={(e) => setNewDescription(e.target.value)} placeholder="Qué diferencia se observó" />
          </FormField>
          <AsyncButton type="submit" variant="primary" onClick={registrar}>Registrar</AsyncButton>
        </form>
        </Autorizado>
        {outcome.data ? (
          <p className="mt-3 text-sm text-text-500">
            {outcome.data.total === 0
              ? "Esta recepción no tiene diferencias registradas."
              : `${outcome.data.total} incidencia(s), ${outcome.data.unresolved} sin tratar. ${
                  outcome.data.ready_for_confirmation
                    ? "Todo tratado: lista para la confirmación de inventario."
                    : "La confirmación de inventario espera a que se traten."
                }`}
          </p>
        ) : null}
      </section>

      <DataTable
        columns={columns}
        data={incidents.data?.items ?? []}
        loading={incidents.isLoading}
        error={incidents.isError ? "No fue posible cargar las incidencias." : null}
        getRowId={(row) => row.id}
        emptyTitle="Sin incidencias"
        emptyDescription="Ninguna recepción ha registrado diferencias."
      />

      <ConfirmationDialog
        open={selected !== null}
        title={selected ? `Tratamiento de ${selected.code}` : ""}
        description="El tratamiento queda registrado con su motivo. El ajuste autorizado pasa antes por aprobación."
        confirmLabel="Registrar tratamiento"
        onConfirm={async () => {
          if (!selected) return;
          await accion(selected, "resolve", { resolution, reason: reason.trim() });
        }}
        onCancel={() => { setSelected(null); setReason(""); }}
      >
        <FormField label="Tratamiento" required>
          <select value={resolution} onChange={(e) => setResolution(e.target.value)} className="h-10 w-full rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900">
            {TRATAMIENTOS.map((t) => (
              <option key={t.value} value={t.value}>
                {t.label}{t.requiereAprobacion ? " (requiere autorización)" : ""}
              </option>
            ))}
          </select>
        </FormField>
        <FormField label="Motivo" required>
          <TextInput value={reason} onChange={(e) => setReason(e.target.value)} placeholder="Por qué se decide así" required />
        </FormField>
      </ConfirmationDialog>

      <ConfirmationDialog
        open={aAnular !== null}
        title={aAnular ? `Anular ${aAnular.code}` : ""}
        description="Se registró por error. La cantidad que comprometía queda libre."
        confirmLabel="Anular"
        danger
        onConfirm={async () => {
          if (!aAnular) return;
          await accion(aAnular, "cancel", { reason: motivoAnulacion.trim() });
          setAAnular(null);
          setMotivoAnulacion("");
        }}
        onCancel={() => { setAAnular(null); setMotivoAnulacion(""); }}
      >
        <FormField label="Motivo" required>
          <TextInput value={motivoAnulacion} onChange={(e) => setMotivoAnulacion(e.target.value)} placeholder="Ej. se registró en la línea equivocada" required />
        </FormField>
      </ConfirmationDialog>
    </PageContent>
  );
}
