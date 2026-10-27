/** Períodos y libros fiscales — reconstruibles desde documentos y eventos (FR-007-050/051/052). */
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { apiFetch } from "@/api/client";
import type { BookResult, FiscalPeriodSummary } from "@/api/types";
import { useAutoridad } from "@/app/autoridad/AutoridadContext";
import { useNotifications } from "@/app/contexts/NotificationContext";
import { Autorizado } from "@/components/Autorizado";
import { AsyncButton } from "@/components/AsyncButton";
import { FormField } from "@/components/FormField";
import { PageContent } from "@/layout/PageContent";
import { PageHeader } from "@/components/PageHeader";
import { TextInput } from "@/components/TextInput";

const BOOK_TYPES = ["VENTAS", "COMPRAS", "RETENCIONES", "IGTF"] as const;

export function LibrosPage(): React.JSX.Element {
  const queryClient = useQueryClient();
  const { notify } = useNotifications();
  const { puede } = useAutoridad();

  const [bookType, setBookType] = useState<(typeof BOOK_TYPES)[number]>("VENTAS");
  const [period, setPeriod] = useState("");
  const [periodKey, setPeriodKey] = useState("");
  const [taxType, setTaxType] = useState("IVA");

  const book = useQuery({
    queryKey: ["fiscal", "books", bookType, period],
    queryFn: () => apiFetch<BookResult>(`/fiscal/books/${bookType}?period=${period || "0"}`),
    retry: false,
    enabled: true,
  });
  const periods = useQuery({
    queryKey: ["fiscal", "periods"],
    queryFn: () => apiFetch<{ items: FiscalPeriodSummary[] }>("/fiscal/periods"),
    retry: false,
  });

  const createPeriod = async (): Promise<void> => {
    await apiFetch("/fiscal/periods", {
      method: "POST",
      body: { tax_type: taxType, period_key: periodKey },
    });
    notify({ type: "success", title: "Período creado", description: `${taxType} · ${periodKey}` });
    setPeriodKey("");
    void queryClient.invalidateQueries({ queryKey: ["fiscal", "periods"] });
  };

  const transitionPeriod = async (id: string, target: string): Promise<void> => {
    await apiFetch(`/fiscal/periods/${id}/transition`, { method: "POST", body: { target } });
    notify({ type: "success", title: "Período actualizado", description: `Estado → ${target}` });
    void queryClient.invalidateQueries({ queryKey: ["fiscal", "periods"] });
  };

  const bookTotal = (row: Record<string, unknown>): number =>
    Number(row.total ?? row.amount ?? row.igft_amount ?? 0);

  return (
    <PageContent maxWidth="full">
      <PageHeader
        title="Períodos y libros fiscales"
        description="Libros reconstruibles desde documentos y eventos (nunca tablas editables); períodos con cierre/reapertura aprobados (FR-007-050/051)."
        crumbs={[{ label: "Fiscal" }, { label: "Libros" }]}
      />

      <div className="mb-4 grid gap-4 lg:grid-cols-2">
        <form className="rounded-lg border border-border-default bg-surface-0 p-4" onSubmit={(e) => e.preventDefault()}>
          <h2 className="mb-2 text-base font-semibold text-text-900">Libro reconstruible</h2>
          <div className="flex flex-wrap items-end gap-3">
            <FormField label="Tipo de libro">
              <select value={bookType} onChange={(e) => setBookType(e.target.value as typeof bookType)} className="h-10 w-44 rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900">
                {BOOK_TYPES.map((b) => <option key={b} value={b}>{b}</option>)}
              </select>
            </FormField>
            <FormField label="Período">
              <TextInput value={period} onChange={(e) => setPeriod(e.target.value)} placeholder="2026-01" />
            </FormField>
            <AsyncButton type="submit" variant="secondary" onClick={() => queryClient.invalidateQueries({ queryKey: ["fiscal", "books"] })}>
              Generar
            </AsyncButton>
          </div>
          <div className="mt-3 flex gap-6 rounded-md border border-border-default p-3 text-sm">
            <span className="text-text-700">Registros: <b>{book.data?.count ?? 0}</b></span>
            <span className="text-text-700">Total: <b>{book.data?.total.toFixed(2) ?? "0.00"}</b></span>
          </div>
        </form>

        <form className="rounded-lg border border-border-default bg-surface-0 p-4" onSubmit={(e) => e.preventDefault()}>
          <h2 className="mb-2 text-base font-semibold text-text-900">Período fiscal</h2>
          <div className="flex flex-wrap items-end gap-3">
            <FormField label="Impuesto">
              <select value={taxType} onChange={(e) => setTaxType(e.target.value)} className="h-10 w-36 rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900">
                <option value="IVA">IVA</option>
                <option value="ISLR">ISLR</option>
                <option value="IGTF">IGTF</option>
                <option value="RETENCION">Retención</option>
              </select>
            </FormField>
            <FormField label="Período">
              <TextInput value={periodKey} onChange={(e) => setPeriodKey(e.target.value)} placeholder="2026-01" />
            </FormField>
            <Autorizado operacion={["POST", "/fiscal/periods"]}>
              <AsyncButton type="submit" variant="secondary" onClick={createPeriod}>
                Crear
              </AsyncButton>
            </Autorizado>
          </div>
          <div className="mt-3 rounded-md border border-border-default p-3 text-sm">
            {(periods.data?.items ?? []).map((p) => (
              <div key={p.id} className="flex items-center justify-between py-0.5">
                <span className="text-text-700">{p.tax_type} · {p.period_key} · {p.status}</span>
                <span className="flex gap-1">
                  {p.status === "OPEN" && puede("POST", "/fiscal/periods/_/transition") ? <AsyncButton size="sm" variant="secondary" onClick={() => transitionPeriod(p.id, "CLOSED")}>cerrar</AsyncButton> : null}
                  {p.status === "CLOSED" && puede("POST", "/fiscal/periods/_/transition") ? <AsyncButton size="sm" variant="secondary" onClick={() => transitionPeriod(p.id, "REOPENED")}>reabrir</AsyncButton> : null}
                </span>
              </div>
            ))}
            {(periods.data?.items ?? []).length === 0 ? <p className="text-text-500">Sin períodos.</p> : null}
          </div>
        </form>
      </div>

      <div className="overflow-hidden rounded-lg border border-border-default">
        <table className="w-full text-left text-sm">
          <thead className="bg-surface-100 text-text-500">
            <tr>
              <th className="px-4 py-2 font-medium">Documento</th>
              <th className="px-4 py-2 font-medium">Número</th>
              <th className="px-4 py-2 font-medium">Control</th>
              <th className="px-4 py-2 font-medium">Monto</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border-default">
            {(book.data?.rows ?? []).map((row, idx) => (
              <tr key={`${String(row.document ?? "")}-${idx}`}>
                <td className="px-4 py-1.5 text-text-700">{String(row.document ?? row.event_type ?? "")}</td>
                <td className="px-4 py-1.5 text-text-700">{String(row.number ?? row.id ?? "")}</td>
                <td className="px-4 py-1.5 text-text-500">{String(row.control ?? row.rule_ref ?? "")}</td>
                <td className="px-4 py-1.5 text-text-700 tabular-nums">{bookTotal(row).toFixed(2)}</td>
              </tr>
            ))}
            {(book.data?.rows ?? []).length === 0 ? (
              <tr><td colSpan={4} className="px-4 py-3 text-text-500">Sin registros para el libro {bookType}.</td></tr>
            ) : null}
          </tbody>
        </table>
      </div>
    </PageContent>
  );
}
