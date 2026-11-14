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
import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router";

import { ApiError, apiFetch } from "@/api/client";
import type {
  GoodsReceiptSummary,
  ReceiptConfirmationRow,
  ReceiptCountPolicy,
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

/**
 * Los dos únicos destinos que la confirmación puede pedir: DISPONIBLE y
 * RECHAZADO. No se muestran en un select porque confirmar reparte cada línea
 * entre ambos; el contrato no autoriza ninguno más y el motor rechazaría
 * cualquier otro.
 */

function cantidad(valor: string | undefined): number {
  const n = Number(valor);
  return Number.isNaN(n) || valor === "" ? 0 : n;
}

function formatear(n: number): string {
  return String(Math.round(n * 1e6) / 1e6);
}

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
  const [aDisponible, setADisponible] = useState<Record<string, string>>({});
  const [rechazadas, setRechazadas] = useState<Record<string, string>>({});
  const [motivos, setMotivos] = useState<Record<string, string>>({});
  const [politicaConteoLocal, setPoliticaConteoLocal] = useState(false);

  const recepciones = useQuery({
    queryKey: ["confirmacion", "recepciones"],
    queryFn: () => apiFetch<{ items: GoodsReceiptSummary[] }>("/purchasing/receipts"),
  });

  const politicaConteo = useQuery({
    queryKey: ["confirmacion", "politica-conteo"],
    queryFn: () => apiFetch<ReceiptCountPolicy>("/purchasing/settings/receipt-count"),
  });

  useEffect(() => {
    if (politicaConteo.data) {
      setPoliticaConteoLocal(politicaConteo.data.receipt_count_same_user_allowed);
    }
  }, [politicaConteo.data]);

  async function guardarPolitica(): Promise<void> {
    try {
      await apiFetch("/purchasing/settings/receipt-count", {
        method: "PUT",
        body: { receipt_count_same_user_allowed: politicaConteoLocal },
      });
      notify({ type: "success", title: "Política de conteo guardada" });
      await qc.invalidateQueries({ queryKey: ["confirmacion", "politica-conteo"] });
    } catch (e) {
      notify({
        type: "error",
        title: "No se guardó la política",
        description: e instanceof ApiError ? e.message : undefined,
      });
    }
  }

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
      .filter((x) => Number(x.base_quantity_accepted ?? 0) > 0)
      .flatMap((x) => {
        const decisiones: Array<{
          receipt_line_id: string;
          target_state: "DISPONIBLE" | "RECHAZADO";
          base_quantity: string;
          reason?: string | null;
        }> = [];
        const disp = cantidad(aDisponible[x.receipt_line_id]);
        const rech = cantidad(rechazadas[x.receipt_line_id]);
        if (disp > 0) {
          decisiones.push({
            receipt_line_id: x.receipt_line_id,
            target_state: "DISPONIBLE",
            base_quantity: aDisponible[x.receipt_line_id],
          });
        }
        if (rech > 0) {
          decisiones.push({
            receipt_line_id: x.receipt_line_id,
            target_state: "RECHAZADO",
            base_quantity: rechazadas[x.receipt_line_id],
            reason: motivos[x.receipt_line_id],
          });
        }
        return decisiones;
      });
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
      setADisponible({});
      setRechazadas({});
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
    columnas.accessor("product_code", {
      header: "Producto",
      cell: (c) => {
        const codigo = c.row.original.product_code;
        const nombre = c.row.original.product_name;
        if (!codigo && !nombre) return <span>—</span>;
        return (
          <span>
            {codigo}
            {nombre ? ` · ${nombre}` : ""}
          </span>
        );
      },
    }),
    columnas.accessor("base_quantity_received", { header: "Recibido (base)" }),
    columnas.accessor("base_quantity_accepted", { header: "Aceptado (base)" }),
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
    columnas.accessor("pending_decision_base", { header: "Pendiente por decidir" }),
  ];

  const listo = conciliacion.data?.ready_for_confirmation ?? false;
  const yaConfirmada = conciliacion.data?.confirmation_status === "CONFIRMADA";

  const repartoCompleto = (conciliacion.data?.items ?? [])
    .filter((x) => Number(x.base_quantity_accepted ?? 0) > 0)
    .every((x) => {
      const aceptado = Number(x.base_quantity_accepted);
      const disp = cantidad(aDisponible[x.receipt_line_id]);
      const rech = cantidad(rechazadas[x.receipt_line_id]);
      const pendiente = Math.round((aceptado - disp - rech) * 1e6) / 1e6;
      const motivoOk = rech > 0
        ? (motivos[x.receipt_line_id] ?? "").trim() !== ""
        : true;
      return disp >= 0 && rech >= 0 && pendiente === 0 && motivoOk;
    });

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

      {politicaConteo.data?.independent_count_required ? (
        <p role="note" className="mb-4 text-sm text-text-700">
          Conteo independiente activo: quien registró o aceptó la recepción no puede contar sus
          líneas; debe contarlas otra persona.
        </p>
      ) : (
        <p role="note" className="mb-4 text-sm text-text-700">
          Conteo independiente desactivado por la empresa: quien recibe puede contar.
        </p>
      )}

      <section className="mb-4 rounded-lg border border-border-default bg-surface-0 p-4">
        <h2 className="mb-2 text-base font-semibold text-text-900">Política de conteo</h2>
        <Autorizado operacion={["PUT", "/purchasing/settings/receipt-count"]}>
          <div className="flex items-center gap-3">
            <input
              type="checkbox"
              id="receipt-count-same-user"
              checked={politicaConteoLocal}
              onChange={(e) => setPoliticaConteoLocal(e.target.checked)}
              className="h-4 w-4 rounded border-border-default text-brand-600 focus:ring-brand-500"
            />
            <label htmlFor="receipt-count-same-user" className="text-sm text-text-900">
              Permitir que quien recibe cuente la mercancía
            </label>
            <AsyncButton onClick={guardarPolitica} variant="secondary">
              Guardar política
            </AsyncButton>
          </div>
        </Autorizado>
      </section>

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

                  {(() => {
                    const aceptado = Number(x.base_quantity_accepted ?? 0);
                    if (aceptado <= 0) {
                      return (
                        <p className="text-sm text-text-500">Sin cantidad aceptada que decidir.</p>
                      );
                    }
                    const disp = cantidad(aDisponible[x.receipt_line_id]);
                    const rech = cantidad(rechazadas[x.receipt_line_id]);
                    const pendiente =
                      Math.round((aceptado - disp - rech) * 1e6) / 1e6;
                    return (
                      <>
                        <p>Cantidad aceptada: {formatear(aceptado)}</p>
                        <FormField label="A disponible" help="En unidad base">
                          <TextInput
                            value={aDisponible[x.receipt_line_id] ?? ""}
                            onChange={(e) =>
                              setADisponible({
                                ...aDisponible,
                                [x.receipt_line_id]: e.target.value,
                              })
                            }
                            placeholder={x.pending_decision_base}
                          />
                        </FormField>
                        <FormField label="Rechazada" help="En unidad base">
                          <TextInput
                            value={rechazadas[x.receipt_line_id] ?? ""}
                            onChange={(e) =>
                              setRechazadas({
                                ...rechazadas,
                                [x.receipt_line_id]: e.target.value,
                              })
                            }
                          />
                        </FormField>
                        {rech > 0 ? (
                          <FormField label="Motivo del rechazo" required>
                            <TextInput
                              value={motivos[x.receipt_line_id] ?? ""}
                              onChange={(e) =>
                                setMotivos({
                                  ...motivos,
                                  [x.receipt_line_id]: e.target.value,
                                })
                              }
                            />
                          </FormField>
                        ) : null}
                        {pendiente >= 0 ? (
                          <p role="status">
                            Pendiente por decidir: {formatear(pendiente)}
                          </p>
                        ) : (
                          <p role="alert" className="text-sm text-danger-600">
                            Excede lo aceptado en {formatear(-pendiente)}.
                          </p>
                        )}
                      </>
                    );
                  })()}
                </div>
              ))}
              <Autorizado
                operacion={[
                  "POST",
                  `/purchasing/receipts/${receiptId}/confirmacion-inventario`,
                ]}
              >
                <AsyncButton onClick={confirmar} disabled={!listo || !repartoCompleto}>
                  Confirmar inventario
                </AsyncButton>
              </Autorizado>
              {listo && !repartoCompleto ? (
                <p role="status" className="mt-2 text-sm text-text-700">
                  Decida la totalidad de lo aceptado de cada línea antes de confirmar.
                </p>
              ) : null}
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
