/**
 * Confirmación de inventario recibido — Spec 021.
 *
 * La pantalla existe porque recibir no es tener disponible. Entre que la
 * mercancía baja del camión y que se puede vender hay un conteo, una
 * comparación y una decisión, y hasta ahora el sistema se las saltaba todas.
 *
 * Tres límites deliberados. No resuelve incidencias: si queda alguna abierta,
 * la pantalla lo dice y no deja confirmar, pero el tratamiento se decide en
 * Incidencias (Spec 020). No ubica nada: confirmar no es colocar, y el
 * put-away es de la Spec 022. Y no ofrece más destinos que los dos que el
 * contrato autoriza, porque el motor rechazaría cualquier otro.
 */
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { createColumnHelper } from "@tanstack/react-table";
import { useState } from "react";
import { Link, useSearchParams } from "react-router";

import { ApiError, apiFetch } from "@/api/client";
import type {
  GoodsReceiptSummary,
  ReceiptConfirmationRow,
  ReceiptReconciliation,
  ReconciliationItem,
} from "@/api/types";
import { useAutoridad } from "@/app/autoridad/AutoridadContext";
import { useNotifications } from "@/app/contexts/NotificationContext";
import { AsyncButton } from "@/components/AsyncButton";
import { Autorizado } from "@/components/Autorizado";
import { DataTable } from "@/components/DataTable";
import { FormField } from "@/components/FormField";
import { PageHeader } from "@/components/PageHeader";
import { TextInput } from "@/components/TextInput";
import { PageContent } from "@/layout/PageContent";

/** Etapa 6 del proceso, literal. No hay más y no se inventan. */
const DIFERENCIAS = [
  { value: "CANTIDAD", label: "Cantidad" },
  { value: "SKU", label: "SKU" },
  { value: "PRESENTACION", label: "Presentación" },
  { value: "REFERENCIA", label: "Referencia" },
  { value: "UNIDAD_MEDIDA", label: "Unidad de medida" },
];

/** Los dos únicos destinos que la confirmación puede pedir. */
const DESTINOS = [
  { value: "DISPONIBLE", label: "Liberar a disponible", requiereMotivo: false },
  { value: "RECHAZADO", label: "Rechazar", requiereMotivo: true },
];

const columnas = createColumnHelper<ReconciliationItem>();

function Veredicto({ valor }: { valor: boolean | null }): React.JSX.Element {
  if (valor === null) return <span className="text-text-500">sin comparar</span>;
  return valor ? (
    <span className="text-success-700">coincide</span>
  ) : (
    <span className="font-medium text-danger-600">difiere</span>
  );
}

export function ConfirmacionPage(): React.JSX.Element {
  const qc = useQueryClient();
  const { notify } = useNotifications();
  const { puede } = useAutoridad();
  const [searchParams] = useSearchParams();
  const [receiptId, setReceiptId] = useState(() => searchParams.get("recepcion") ?? "");
  const importacion = searchParams.get("importacion");
  const [conteos, setConteos] = useState<Record<string, string>>({});
  const [diferencias, setDiferencias] = useState<Record<string, string[]>>({});
  const [destinos, setDestinos] = useState<Record<string, string>>({});
  const [cantidades, setCantidades] = useState<Record<string, string>>({});
  const [motivos, setMotivos] = useState<Record<string, string>>({});

  const recepciones = useQuery({
    queryKey: ["confirmacion", "recepciones"],
    queryFn: () => apiFetch<{ items: GoodsReceiptSummary[] }>("/purchasing/receipts"),
  });

  const conciliacion = useQuery({
    queryKey: ["confirmacion", "conciliacion", receiptId],
    queryFn: () =>
      apiFetch<ReceiptReconciliation>(`/purchasing/receipts/${receiptId}/conciliacion`),
    enabled: Boolean(receiptId),
  });

  const confirmadas = useQuery({
    queryKey: ["confirmacion", "hechas", receiptId],
    queryFn: () =>
      apiFetch<{ items: ReceiptConfirmationRow[] }>(
        `/purchasing/receipts/${receiptId}/confirmacion-inventario`,
      ),
    enabled: Boolean(receiptId),
  });

  const aceptadas = (recepciones.data?.items ?? []).filter(
    (r) => r.status === "ACCEPTED" || r.status === "PARTIALLY_ACCEPTED",
  );

  async function contar(lineId: string): Promise<void> {
    try {
      await apiFetch(`/purchasing/receipts/${receiptId}/lines/${lineId}/conteo`, {
        method: "POST",
        body: {
          counted_base_quantity: conteos[lineId] ?? "0",
          difference_kinds: diferencias[lineId] ?? [],
        },
      });
      notify({ type: "success", title: "Conteo registrado" });
      await qc.invalidateQueries({ queryKey: ["confirmacion", "conciliacion", receiptId] });
    } catch (e) {
      notify({
        type: "error",
        title: "No se registró el conteo",
        description: e instanceof ApiError ? e.message : undefined,
      });
    }
  }

  async function confirmar(): Promise<void> {
    const decisions = (conciliacion.data?.items ?? [])
      .filter((x) => Number(cantidades[x.receipt_line_id] ?? 0) > 0)
      .map((x) => ({
        receipt_line_id: x.receipt_line_id,
        target_state: destinos[x.receipt_line_id] ?? "DISPONIBLE",
        base_quantity: cantidades[x.receipt_line_id],
        reason: motivos[x.receipt_line_id] || null,
      }));
    if (decisions.length === 0) {
      notify({ type: "error", title: "Indique al menos una cantidad a confirmar" });
      return;
    }
    try {
      await apiFetch(`/purchasing/receipts/${receiptId}/confirmacion-inventario`, {
        method: "POST",
        body: { decisions },
      });
      notify({ type: "success", title: "Inventario confirmado" });
      setCantidades({});
      setMotivos({});
      await qc.invalidateQueries({ queryKey: ["confirmacion"] });
    } catch (e) {
      notify({
        type: "error",
        title: "No se confirmó el inventario",
        description: e instanceof ApiError ? e.message : undefined,
      });
    }
  }

  const cols = [
    columnas.accessor("product_id", {
      header: "Producto",
      cell: (c) => <span className="font-mono text-xs">{c.getValue().slice(0, 8)}…</span>,
    }),
    columnas.accessor("base_quantity_received", { header: "Recibido (base)" }),
    columnas.accessor("counted_base_quantity", {
      header: "Contado",
      cell: (c) => c.getValue() ?? <span className="text-text-500">sin contar</span>,
    }),
    columnas.accessor("matches_order", {
      header: "Contra la orden",
      cell: (c) => <Veredicto valor={c.getValue()} />,
    }),
    columnas.accessor("matches_physical", {
      header: "Contra lo recibido",
      cell: (c) => <Veredicto valor={c.getValue()} />,
    }),
    columnas.accessor("pending_base", { header: "Pendiente" }),
  ];

  const listo = conciliacion.data?.ready_for_confirmation ?? false;
  const yaConfirmada = conciliacion.data?.confirmation_status === "CONFIRMADA";

  return (
    <PageContent>
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
        title="Confirmación de inventario"
        description={
          "Contar lo recibido, compararlo contra la orden y la recepción física, y decidir qué se " +
          "libera y qué se rechaza. Ubicar la mercancía es del put-away, no de esta pantalla."
        }
        crumbs={[{ label: "Inventario" }, { label: "Confirmación" }]}
      />

      <section className="mb-4 rounded-lg border border-border-default bg-surface-0 p-4">
        <FormField label="Recepción aceptada" required>
          <select
            value={receiptId}
            onChange={(e) => setReceiptId(e.target.value)}
            className="h-10 w-64 rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900"
          >
            <option value="">Seleccionar…</option>
            {aceptadas.map((r) => (
              <option key={r.id} value={r.id}>
                {r.code}
              </option>
            ))}
          </select>
        </FormField>
      </section>

      {conciliacion.data ? (
        <>
          <section className="mb-4 rounded-lg border border-border-default bg-surface-0 p-4">
            <h2 className="mb-2 text-base font-semibold text-text-900">Estado de la conciliación</h2>
            <dl className="grid grid-cols-2 gap-3 text-sm md:grid-cols-4">
              <div>
                <dt className="text-text-500">Confirmación</dt>
                <dd className="font-medium">{conciliacion.data.confirmation_status}</dd>
              </div>
              <div>
                <dt className="text-text-500">Calidad</dt>
                <dd className="font-medium">{conciliacion.data.quality_status}</dd>
              </div>
              <div>
                <dt className="text-text-500">Packing list</dt>
                <dd>
                  <Veredicto valor={conciliacion.data.packing_list_match} />
                </dd>
              </div>
              <div>
                <dt className="text-text-500">Incidencias sin resolver</dt>
                <dd className="font-medium">{conciliacion.data.incidents.unresolved}</dd>
              </div>
            </dl>
            {!listo && !yaConfirmada ? (
              <p className="mt-3 text-sm text-danger-600" role="status">
                {conciliacion.data.incidents.unresolved > 0
                  ? "Hay incidencias sin resolver: se tratan en Incidencias antes de confirmar."
                  : "Faltan líneas por contar."}
              </p>
            ) : null}
          </section>

          <DataTable
            data={conciliacion.data.items}
            columns={cols}
            emptyTitle="Sin líneas"
            emptyDescription="Esta recepción no tiene líneas que conciliar."
          />

          {!yaConfirmada ? (
            <section className="mt-4 rounded-lg border border-border-default bg-surface-0 p-4">
              <h2 className="mb-3 text-base font-semibold text-text-900">
                Conteo y decisión por línea
              </h2>
              {conciliacion.data.items.map((x) => (
                <div
                  key={x.receipt_line_id}
                  className="mb-4 flex flex-wrap items-end gap-3 border-b border-border-default pb-4 last:border-0"
                >
                  <FormField label="Contado (base)">
                    <TextInput
                      value={conteos[x.receipt_line_id] ?? ""}
                      onChange={(e) =>
                        setConteos({ ...conteos, [x.receipt_line_id]: e.target.value })
                      }
                      placeholder={x.base_quantity_received}
                    />
                  </FormField>
                  <FormField label="Diferencia observada" help="Del conjunto del proceso">
                    <select
                      multiple
                      value={diferencias[x.receipt_line_id] ?? []}
                      onChange={(e) =>
                        setDiferencias({
                          ...diferencias,
                          [x.receipt_line_id]: Array.from(e.target.selectedOptions).map(
                            (o) => o.value,
                          ),
                        })
                      }
                      className="h-24 w-48 rounded-md border border-border-default bg-surface-0 px-3 py-1 text-sm text-text-900"
                    >
                      {DIFERENCIAS.map((d) => (
                        <option key={d.value} value={d.value}>
                          {d.label}
                        </option>
                      ))}
                    </select>
                  </FormField>
                  {puede(
                    "POST",
                    `/purchasing/receipts/${receiptId}/lines/${x.receipt_line_id}/conteo`,
                  ) ? (
                    <AsyncButton onClick={() => contar(x.receipt_line_id)} variant="secondary">
                      Registrar conteo
                    </AsyncButton>
                  ) : null}

                  <FormField label="Destino">
                    <select
                      value={destinos[x.receipt_line_id] ?? "DISPONIBLE"}
                      onChange={(e) =>
                        setDestinos({ ...destinos, [x.receipt_line_id]: e.target.value })
                      }
                      className="h-10 w-48 rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900"
                    >
                      {DESTINOS.map((d) => (
                        <option key={d.value} value={d.value}>
                          {d.label}
                        </option>
                      ))}
                    </select>
                  </FormField>
                  <FormField label="Cantidad a confirmar" help="En unidad base">
                    <TextInput
                      value={cantidades[x.receipt_line_id] ?? ""}
                      onChange={(e) =>
                        setCantidades({ ...cantidades, [x.receipt_line_id]: e.target.value })
                      }
                      placeholder={x.pending_base}
                    />
                  </FormField>
                  {(destinos[x.receipt_line_id] ?? "DISPONIBLE") === "RECHAZADO" ? (
                    <FormField label="Motivo del rechazo" required>
                      <TextInput
                        value={motivos[x.receipt_line_id] ?? ""}
                        onChange={(e) =>
                          setMotivos({ ...motivos, [x.receipt_line_id]: e.target.value })
                        }
                      />
                    </FormField>
                  ) : null}
                </div>
              ))}
              <Autorizado
                operacion={[
                  "POST",
                  `/purchasing/receipts/${receiptId}/confirmacion-inventario`,
                ]}
              >
                <AsyncButton onClick={confirmar} disabled={!listo}>
                  Confirmar inventario
                </AsyncButton>
              </Autorizado>
            </section>
          ) : null}

          {(confirmadas.data?.items ?? []).length > 0 ? (
            <section className="mt-4 rounded-lg border border-border-default bg-surface-0 p-4">
              <h2 className="mb-2 text-base font-semibold text-text-900">Decisiones tomadas</h2>
              <ul className="text-sm">
                {(confirmadas.data?.items ?? []).map((c) => (
                  <li key={c.id} className="py-1">
                    {c.base_quantity} · {c.source_state} → <strong>{c.target_state}</strong>
                    {c.reason ? ` · ${c.reason}` : ""}
                  </li>
                ))}
              </ul>
            </section>
          ) : null}
        </>
      ) : null}
    </PageContent>
  );
}
