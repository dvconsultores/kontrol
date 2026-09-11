/**
 * Notas de crédito y de débito — Spec 036.
 *
 * «La devolución física **no sustituye** una nota de crédito». Por eso esta
 * pantalla existe aparte de la de devoluciones: aceptar una devolución no emite
 * ninguna nota, y una nota puede no tener devolución detrás. La norma enumera
 * sus causas y solo dos traen mercancía de vuelta; las otras —descuento
 * posterior, bonificación, corrección de un precio facturado en exceso— no
 * mueven una sola unidad.
 *
 * Lo que no se decide aquí: el impuesto, que se reparte del que la factura ya
 * lleva; el tope, que es lo pendiente del original; y la numeración, que es del
 * motor fiscal. La pantalla no calcula ninguno de los tres.
 */
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { ApiError, apiFetch } from "@/api/client";
import type { CreditEligibility, SalesNote } from "@/api/types";
import { useNotifications } from "@/app/contexts/NotificationContext";
import { AsyncButton } from "@/components/AsyncButton";
import { FormField } from "@/components/FormField";
import { PageHeader } from "@/components/PageHeader";
import { TextInput } from "@/components/TextInput";
import { PageContent } from "@/layout/PageContent";

/** Las que la norma enumera. Dice «entre otros casos», así que no es una lista
 *  cerrada: se ofrecen y se admite escribir otra. */
const CAUSAS_CREDITO = [
  "Devolución de mercancía",
  "Anulación de una operación",
  "Descuento posterior",
  "Bonificación posterior",
  "Corrección de un precio facturado en exceso",
  "Disminución de cantidad",
  "Devolución de envases o depósitos",
  "Reversión total o parcial de una prestación",
];

const CAUSAS_DEBITO = [
  "Diferencia de precio",
  "Incremento de cantidad",
  "Flete posterior gravado",
  "Intereses o recargos",
  "Corrección de una base imponible inferior",
];

const SELECT =
  "h-10 w-full rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900";

function corto(id: string): string {
  return `${id.slice(0, 8)}…`;
}

export function NotasVentasPage(): React.JSX.Element {
  const qc = useQueryClient();
  const { notify } = useNotifications();
  const [facturaId, setFacturaId] = useState("");
  const [tipo, setTipo] = useState<"CREDITO" | "DEBITO">("CREDITO");
  const [causa, setCausa] = useState(CAUSAS_CREDITO[0]);
  const [cantidades, setCantidades] = useState<Record<string, string>>({});
  const [concepto, setConcepto] = useState("");
  const [monto, setMonto] = useState("");
  const [nota, setNota] = useState<SalesNote | null>(null);
  const [serie, setSerie] = useState("");
  const [lote, setLote] = useState("");

  const elegible = useQuery({
    queryKey: ["notas", "acreditable", facturaId],
    queryFn: () => apiFetch<CreditEligibility>(`/sales/notas/acreditable/${facturaId}`),
    enabled: facturaId.length > 20,
    retry: false,
  });

  function fallo(titulo: string) {
    return (e: unknown) =>
      notify({
        type: "error",
        title: titulo,
        description: e instanceof ApiError ? e.message : undefined,
      });
  }

  async function generarCredito(): Promise<void> {
    const lineas = (elegible.data?.lines ?? [])
      .map((l) => ({ invoice_line_id: l.invoice_line_id, quantity: Number(cantidades[l.invoice_line_id] ?? 0) }))
      .filter((l) => l.quantity > 0);
    if (lineas.length === 0) {
      notify({ type: "error", title: "Indique qué cantidad se acredita" });
      return;
    }
    try {
      const n = await apiFetch<SalesNote>(`/sales/notas/credito/${facturaId}/generar`, {
        method: "POST",
        body: { cause: causa, lines: lineas },
      });
      setNota(n);
      setCantidades({});
      notify({
        type: "success",
        title: "Nota de crédito generada",
        description: `Base ${n.base_fiscal} · impuesto ${n.tax_total} · total ${n.total}`,
      });
      await qc.invalidateQueries({ queryKey: ["notas"] });
    } catch (e) {
      fallo("No se pudo generar la nota de crédito")(e);
    }
  }

  async function generarDebito(): Promise<void> {
    if (!concepto || Number(monto) <= 0) {
      notify({ type: "error", title: "Indique el concepto y su monto" });
      return;
    }
    try {
      const n = await apiFetch<SalesNote>(`/sales/notas/debito/${facturaId}/generar`, {
        method: "POST",
        body: { cause: causa, lines: [{ concept: concepto, base_fiscal: Number(monto) }] },
      });
      setNota(n);
      setConcepto("");
      setMonto("");
      notify({ type: "success", title: "Nota de débito generada", description: `Total ${n.total}` });
    } catch (e) {
      fallo("No se pudo generar la nota de débito")(e);
    }
  }

  async function emitir(): Promise<void> {
    if (!nota) return;
    if (!serie || !lote) {
      notify({ type: "error", title: "Indique la serie y el lote de control" });
      return;
    }
    const ruta = tipo === "CREDITO" ? "credito" : "debito";
    try {
      const n = await apiFetch<SalesNote>(`/sales/notas/${ruta}/${nota.id}/emitir`, {
        method: "POST",
        body: { series_id: serie, batch_id: lote },
      });
      setNota(n);
      notify({
        type: "success",
        title: "Documento fiscal emitido",
        description: `Nota ${n.invoice_number} · control ${n.control_number}`,
      });
      await qc.invalidateQueries({ queryKey: ["notas"] });
    } catch (e) {
      fallo("No se pudo emitir el documento fiscal")(e);
    }
  }

  const e = elegible.data;

  return (
    <PageContent>
      <PageHeader
        title="Notas"
        description={
          "La nota de crédito disminuye o deja sin efecto una factura emitida; la de débito " +
          "aumenta su valor. Ninguna de las dos sustituye a la devolución física."
        }
        crumbs={[{ label: "Ventas" }, { label: "Notas" }]}
      />

      <section className="mb-4 rounded-lg border border-border-default bg-surface-0 p-4">
        <div className="mb-3 flex flex-wrap items-end gap-3">
          <FormField label="Factura" required>
            <TextInput
              value={facturaId}
              onChange={(ev) => setFacturaId(ev.target.value)}
              placeholder="Identificador de la factura"
            />
          </FormField>
          <FormField label="Tipo de nota">
            <select
              value={tipo}
              onChange={(ev) => {
                const t = ev.target.value as "CREDITO" | "DEBITO";
                setTipo(t);
                setCausa(t === "CREDITO" ? CAUSAS_CREDITO[0] : CAUSAS_DEBITO[0]);
                setNota(null);
              }}
              className={SELECT}
              aria-label="Tipo de nota"
            >
              <option value="CREDITO">Nota de crédito</option>
              <option value="DEBITO">Nota de débito</option>
            </select>
          </FormField>
          <FormField label="Motivo" required>
            <select
              value={causa}
              onChange={(ev) => setCausa(ev.target.value)}
              className={SELECT}
              aria-label="Motivo"
            >
              {(tipo === "CREDITO" ? CAUSAS_CREDITO : CAUSAS_DEBITO).map((x) => (
                <option key={x} value={x}>
                  {x}
                </option>
              ))}
            </select>
          </FormField>
        </div>

        {elegible.isError ? (
          <p className="text-sm text-text-700" role="status">
            No se encontró esa factura en esta empresa.
          </p>
        ) : null}

        {e && !e.creditable ? (
          <p className="text-sm text-text-700" role="status">
            Esa factura no está emitida. Solo se ajusta una factura emitida.
          </p>
        ) : null}

        {e?.creditable && tipo === "CREDITO" ? (
          <>
            <p className="mb-2 text-sm text-text-700">
              Factura {e.invoice_number} · control {e.control_number}. El impuesto de la nota sale
              del que esta factura ya lleva, repartido en proporción: no se vuelve a clasificar la
              operación.
            </p>
            <table className="mb-3 w-full text-sm">
              <caption className="sr-only">Líneas acreditables</caption>
              <thead>
                <tr className="border-b border-border-default text-left text-text-700">
                  <th scope="col" className="py-1">Producto</th>
                  <th scope="col">Facturado</th>
                  <th scope="col">Ya acreditado</th>
                  <th scope="col">Pendiente</th>
                  <th scope="col">Acreditar ahora</th>
                </tr>
              </thead>
              <tbody>
                {e.lines.map((l) => (
                  <tr key={l.invoice_line_id} className="border-b border-border-subtle">
                    <td className="py-1 font-mono text-xs">{corto(l.product_id)}</td>
                    <td>{l.quantity}</td>
                    <td>{l.credited_quantity}</td>
                    <td>{l.creditable_quantity}</td>
                    <td>
                      <TextInput
                        aria-label={`Acreditar de ${corto(l.product_id)}`}
                        value={cantidades[l.invoice_line_id] ?? ""}
                        onChange={(ev) =>
                          setCantidades((c) => ({ ...c, [l.invoice_line_id]: ev.target.value }))
                        }
                        placeholder="0"
                      />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            <AsyncButton onClick={generarCredito}>Generar nota de crédito</AsyncButton>
          </>
        ) : null}

        {e?.creditable && tipo === "DEBITO" ? (
          <>
            <p className="mb-2 text-sm text-text-700">
              Un cargo posterior no mueve inventario: su flujo no tiene ninguna etapa física.
            </p>
            <div className="flex flex-wrap items-end gap-3">
              <FormField label="Concepto" required>
                <TextInput
                  value={concepto}
                  onChange={(ev) => setConcepto(ev.target.value)}
                  placeholder="Qué se cobra"
                />
              </FormField>
              <FormField label="Base imponible" required>
                <TextInput value={monto} onChange={(ev) => setMonto(ev.target.value)} placeholder="0.00" />
              </FormField>
              <AsyncButton onClick={generarDebito}>Generar nota de débito</AsyncButton>
            </div>
          </>
        ) : null}
      </section>

      {nota ? (
        <section className="rounded-lg border border-border-default bg-surface-0 p-4">
          <h2 className="mb-1 text-base font-semibold text-text-900">
            {tipo === "CREDITO" ? "Nota de crédito" : "Nota de débito"} {corto(nota.id)} ·{" "}
            {nota.status}
          </h2>
          <p className="mb-3 text-sm text-text-700">
            {nota.cause} · base {nota.base_fiscal} · impuesto {nota.tax_total} ·{" "}
            <strong>
              total {nota.total} {nota.currency}
            </strong>
          </p>

          {nota.issued_at ? (
            <p className="text-sm text-text-700" role="status">
              Documento fiscal emitido: nota {nota.invoice_number} · control {nota.control_number}.
              {tipo === "CREDITO"
                ? " La cuenta por cobrar quedó ajustada."
                : " El cargo tiene su propio documento por cobrar."}
            </p>
          ) : (
            <div className="flex flex-wrap items-end gap-3">
              <FormField label="Serie de numeración" required>
                <TextInput value={serie} onChange={(ev) => setSerie(ev.target.value)} />
              </FormField>
              <FormField label="Lote de control" required>
                <TextInput value={lote} onChange={(ev) => setLote(ev.target.value)} />
              </FormField>
              <AsyncButton onClick={emitir}>Emitir documento fiscal</AsyncButton>
            </div>
          )}
        </section>
      ) : null}
    </PageContent>
  );
}
