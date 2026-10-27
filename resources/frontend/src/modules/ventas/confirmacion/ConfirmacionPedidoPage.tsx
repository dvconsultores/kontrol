/**
 * Confirmación independiente del pedido — Spec 033.
 *
 * El proceso lo llama «un control independiente después del picking», y explica
 * para qué: almacén prepara, confirmación verifica, facturación factura sobre un
 * pedido previamente confirmado. Es separación funcional.
 *
 * Por eso esta pantalla no recoge nada ni mueve inventario: el verificador
 * cuenta otra vez, producto por producto, y firma. **El veredicto no lo decide
 * el navegador**: se envía lo contado y el backend compara contra el pedido
 * original —no contra la preparación, que compararla consigo misma no
 * verificaría nada— y devuelve conforme o no conforme.
 */
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { createColumnHelper } from "@tanstack/react-table";
import { useState } from "react";

import { ApiError, apiFetch } from "@/api/client";
import type {
  ConfirmationResult,
  ConfirmationWorksheet,
  PendingConfirmation,
} from "@/api/types";
import { useAutoridad } from "@/app/autoridad/AutoridadContext";
import { useNotifications } from "@/app/contexts/NotificationContext";
import { AsyncButton } from "@/components/AsyncButton";
import { DataTable } from "@/components/DataTable";
import { FormField } from "@/components/FormField";
import { PageHeader } from "@/components/PageHeader";
import { TextInput } from "@/components/TextInput";
import { PageContent } from "@/layout/PageContent";

const cols = createColumnHelper<PendingConfirmation>();

function corto(id: string): string {
  return `${id.slice(0, 8)}…`;
}

interface Verificacion {
  cantidad: string;
  presentacion: boolean;
  condicion: boolean;
  nota: string;
}

export function ConfirmacionPedidoPage(): React.JSX.Element {
  const qc = useQueryClient();
  const { notify } = useNotifications();
  const { puede } = useAutoridad();
  const [orderId, setOrderId] = useState<string | null>(null);
  const [verificado, setVerificado] = useState<Record<string, Verificacion>>({});
  const [notas, setNotas] = useState("");
  const [resultado, setResultado] = useState<ConfirmationResult | null>(null);

  const pendientes = useQuery({
    queryKey: ["confirmacion", "pendientes"],
    queryFn: () => apiFetch<{ items: PendingConfirmation[] }>("/sales/confirmacion/pendientes"),
  });

  const hoja = useQuery({
    queryKey: ["confirmacion", "hoja", orderId],
    queryFn: () => apiFetch<ConfirmationWorksheet>(`/sales/confirmacion/${orderId}`),
    enabled: Boolean(orderId),
  });

  function abrir(item: PendingConfirmation): void {
    setOrderId(item.order_id);
    setVerificado({});
    setNotas("");
    setResultado(null);
  }

  /** Los valores de partida de una línea que todavía nadie ha tocado. */
  const EN_BLANCO: Verificacion = { cantidad: "", presentacion: true, condicion: true, nota: "" };

  function cambiar(linea: string, campo: keyof Verificacion, valor: string | boolean): void {
    // Se parte de lo ya verificado —o de los valores en blanco si es la primera
    // vez— y encima va el campo que cambia. Antes los valores por defecto se
    // escribían **antes** del `...prev[linea]` que los pisaba: mismo resultado,
    // pero con claves repetidas que `tsc -b` rechaza (TS2783), y con ello la
    // build entera.
    setVerificado((prev) => ({
      ...prev,
      [linea]: { ...(prev[linea] ?? EN_BLANCO), [campo]: valor },
    }));
  }

  async function confirmar(): Promise<void> {
    const h = hoja.data;
    if (!orderId || !h) return;
    const faltan = h.lines.filter((l) => !verificado[l.order_line_id]?.cantidad);
    if (faltan.length) {
      notify({
        type: "error",
        title: "El control es completo o no es control",
        description: `Faltan ${faltan.length} línea(s) por contar.`,
      });
      return;
    }
    try {
      const r = await apiFetch<ConfirmationResult>(`/sales/confirmacion/${orderId}`, {
        method: "POST",
        body: {
          notes: notas || null,
          lines: h.lines.map((l) => ({
            order_line_id: l.order_line_id,
            checked_base_quantity: verificado[l.order_line_id].cantidad,
            presentation_ok: verificado[l.order_line_id].presentacion,
            condition_ok: verificado[l.order_line_id].condicion,
            note: verificado[l.order_line_id].nota || null,
          })),
        },
      });
      setResultado(r);
      notify({
        type: r.status === "CONFIRMED" ? "success" : "error",
        title:
          r.status === "CONFIRMED"
            ? "Pedido formalmente confirmado"
            : "Pedido no conforme: regresa a preparación",
      });
      await qc.invalidateQueries({ queryKey: ["confirmacion"] });
    } catch (e) {
      notify({
        type: "error",
        title: "No se pudo registrar el control",
        description: e instanceof ApiError ? e.message : undefined,
      });
    }
  }

  const columnas = [
    cols.accessor("code", { header: "Pedido" }),
    cols.accessor("updated_at", {
      header: "Preparado",
      cell: (c) => c.getValue()?.replace("T", " ").slice(0, 19) ?? "—",
    }),
    cols.display({
      id: "accion",
      header: "Acción",
      cell: (c) => (
        <button
          type="button"
          onClick={() => abrir(c.row.original)}
          className="text-sm font-medium text-primary-700 underline"
        >
          Verificar
        </button>
      ),
    }),
  ];

  const h = hoja.data;

  return (
    <PageContent>
      <PageHeader
        title="Confirmación de pedido"
        description={
          "Control independiente sobre el pedido ya preparado. Se cuenta otra vez y se compara " +
          "contra el pedido original, no contra la preparación."
        }
        crumbs={[{ label: "Ventas" }, { label: "Confirmación" }]}
      />

      <section className="mb-4">
        <h2 className="mb-2 text-base font-semibold text-text-900">Pendientes de control</h2>
        <DataTable
          data={pendientes.data?.items ?? []}
          columns={columnas}
          emptyTitle="Nada por verificar"
          emptyDescription="Ningún pedido preparado espera el control independiente."
        />
      </section>

      {h ? (
        <section className="rounded-lg border border-border-default bg-surface-0 p-4">
          <h2 className="mb-1 text-base font-semibold text-text-900">Pedido {h.code}</h2>
          <p className="mb-3 text-sm text-text-700">
            Preparado por {h.prepared_by.map(corto).join(", ") || "—"}.
            {h.same_user_allowed
              ? " Esta empresa permite que quien preparó confirme."
              : " Quien preparó el pedido no puede confirmarlo."}
          </p>

          <table className="mb-4 w-full text-sm">
            <caption className="sr-only">Líneas del pedido a verificar</caption>
            <thead>
              <tr className="border-b border-border-default text-left text-text-700">
                <th scope="col" className="py-1">Producto</th>
                <th scope="col">Pedido</th>
                <th scope="col">Preparado</th>
                <th scope="col">Contado</th>
                <th scope="col">Presentación</th>
                <th scope="col">Condición</th>
              </tr>
            </thead>
            <tbody>
              {h.lines.map((l) => (
                <tr key={l.order_line_id} className="border-b border-border-subtle">
                  <td className="py-1 font-mono text-xs">{corto(l.product_id)}</td>
                  <td>{l.required_base_quantity}</td>
                  <td>{l.prepared_base_quantity}</td>
                  <td>
                    <TextInput
                      aria-label={`Cantidad contada de ${corto(l.product_id)}`}
                      value={verificado[l.order_line_id]?.cantidad ?? ""}
                      onChange={(e) => cambiar(l.order_line_id, "cantidad", e.target.value)}
                    />
                  </td>
                  <td>
                    <input
                      type="checkbox"
                      aria-label={`Presentación correcta de ${corto(l.product_id)}`}
                      checked={verificado[l.order_line_id]?.presentacion ?? true}
                      onChange={(e) => cambiar(l.order_line_id, "presentacion", e.target.checked)}
                    />
                  </td>
                  <td>
                    <input
                      type="checkbox"
                      aria-label={`Condición apta de ${corto(l.product_id)}`}
                      checked={verificado[l.order_line_id]?.condicion ?? true}
                      onChange={(e) => cambiar(l.order_line_id, "condicion", e.target.checked)}
                    />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          <div className="flex flex-wrap items-end gap-3">
            <FormField label="Observaciones">
              <TextInput value={notas} onChange={(e) => setNotas(e.target.value)} />
            </FormField>
            {puede("POST", "/sales/confirmacion/_") ? (
              <AsyncButton onClick={confirmar}>Registrar control</AsyncButton>
            ) : null}
          </div>

          {h.attempts.length ? (
            <div className="mt-4">
              <h3 className="mb-2 text-sm font-semibold text-text-900">Intentos anteriores</h3>
              <ul className="text-sm text-text-700">
                {h.attempts.map((a) => (
                  <li key={a.id}>
                    #{a.attempt} · {a.status} · {a.checked_at?.replace("T", " ").slice(0, 19)}
                    {a.notes ? ` · ${a.notes}` : ""}
                  </li>
                ))}
              </ul>
            </div>
          ) : null}

          {resultado ? (
            <div className="mt-4 rounded-md border border-border-default p-3" role="status">
              <p className="mb-2 text-sm font-semibold text-text-900">
                Intento #{resultado.attempt}: {resultado.status}
              </p>
              <ul className="text-sm text-text-700">
                {resultado.lines
                  .filter((l) => !l.conforms)
                  .map((l, i) => (
                    <li key={`${l.order_line_id ?? "extra"}-${i}`}>
                      {corto(l.product_id)} — {l.difference_kind}: pedido{" "}
                      {l.required_base_quantity}, preparado {l.prepared_base_quantity}, contado{" "}
                      {l.checked_base_quantity}
                    </li>
                  ))}
              </ul>
              {resultado.status === "REJECTED" ? (
                <p className="mt-2 text-sm text-text-700">
                  El pedido regresa a preparación con la incidencia registrada.
                </p>
              ) : null}
            </div>
          ) : null}
        </section>
      ) : null}
    </PageContent>
  );
}
