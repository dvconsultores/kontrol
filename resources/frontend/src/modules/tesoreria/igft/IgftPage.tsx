/** IGTF por regla y evento — reglas versionadas, sin confundir con IVA adicional (FR-006-040/041). */
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { createColumnHelper } from "@tanstack/react-table";
import { useState } from "react";

import { apiFetch } from "@/api/client";
import type { FiscalRuleSummary, IgftEventSummary } from "@/api/types";
import { useNotifications } from "@/app/contexts/NotificationContext";
import { Autorizado } from "@/components/Autorizado";
import { AsyncButton } from "@/components/AsyncButton";
import { DataTable } from "@/components/DataTable";
import { FormField } from "@/components/FormField";
import { MoneyInput } from "@/components/MoneyInput";
import { isZeroDecimal, toDecimalString } from "@/lib/decimal";
import { formatMoney } from "@/lib/format";
import { PageContent } from "@/layout/PageContent";
import { PageHeader } from "@/components/PageHeader";
import { TextInput } from "@/components/TextInput";

const columnHelper = createColumnHelper<IgftEventSummary>();

export function IgftPage(): React.JSX.Element {
  const queryClient = useQueryClient();
  const { notify } = useNotifications();

  // Regla
  const [ruleCode, setRuleCode] = useState("IGFT-2026");
  const [rate, setRate] = useState("0.03");

  // Evaluación
  const [eventType, setEventType] = useState<"PAYMENT" | "COLLECTION" | "TRANSFER">("PAYMENT");
  const [amount, setAmount] = useState("");
  const [currency] = useState("VED");
  const [sourceDoc, setSourceDoc] = useState("");

  const events = useQuery({
    queryKey: ["tesoreria", "igft-events"],
    queryFn: () => apiFetch<{ items: IgftEventSummary[] }>("/treasury/igft-events"),
    retry: false,
  });
  const rules = useQuery({
    queryKey: ["tesoreria", "fiscal-rules"],
    queryFn: () => apiFetch<{ items: FiscalRuleSummary[] }>("/treasury/fiscal-rules"),
    retry: false,
  });

  const refresh = (): void => {
    void queryClient.invalidateQueries({ queryKey: ["tesoreria", "igft-events"] });
    void queryClient.invalidateQueries({ queryKey: ["tesoreria", "fiscal-rules"] });
  };

  const createRule = async (): Promise<void> => {
    await apiFetch("/treasury/fiscal-rules", {
      method: "POST",
      body: { rule_code: ruleCode, name: "IGFT operaciones", rule_type: "IGTF", version: "1.0", params: JSON.stringify({ rate: Number(rate) || 0 }) },
    });
    notify({ type: "success", title: "Regla IGTF creada", description: "Regla versionada vigente." });
    refresh();
  };

  const evaluate = async (): Promise<void> => {
    // Spec 038 · FLOAT-038-C: la base imponible viaja como texto exacto y el importe
    // calculado vuelve como texto. El impuesto no cambia; cambia cómo se transporta.
    const base = toDecimalString(amount);
    if (!base || isZeroDecimal(base)) {
      notify({ type: "error", title: "Base inválida", description: "Indique un importe mayor que cero, con hasta dos decimales." });
      return;
    }
    const res = await apiFetch<{ igft_amount: string | null }>("/treasury/igft-events/evaluate", {
      method: "POST",
      body: { event_type: eventType, source_document: sourceDoc || null, amount: base, currency },
    });
    notify({
      type: "success",
      title: "Evento IGTF evaluado",
      description: `IGTF calculado: ${res.igft_amount === null ? "—" : formatMoney(res.igft_amount)} (independiente del IVA).`,
    });
    setAmount("");
    refresh();
  };

  const columns = [
    columnHelper.accessor("event_type", { header: "Evento" }),
    columnHelper.accessor("source_document", { header: "Documento" }),
    columnHelper.accessor("amount", { header: "Base", cell: (c) => formatMoney(c.getValue()) }),
    columnHelper.accessor("currency", { header: "Moneda" }),
    columnHelper.accessor("rate_snapshot", { header: "Tasa" }),
    columnHelper.accessor("igft_amount", { header: "IGTF", cell: (c) => { const v = c.getValue(); return v === null ? "—" : formatMoney(v); } }),
    columnHelper.accessor("evaluated_at", { header: "Fecha" }),
    columnHelper.accessor("status", { header: "Estado" }),
  ];

  return (
    <PageContent maxWidth="full">
      <PageHeader
        title="IGTF por regla y evento"
        description="Evaluación por regla versionada y evento; el IGTF nunca se confunde ni se suma con el IVA adicional (FR-006-040/041). Motor fiscal completo en Spec 007."
        crumbs={[{ label: "Tesorería" }, { label: "IGTF" }]}
      />

      <div className="mb-4 grid gap-4 lg:grid-cols-2">
        <form
          className="rounded-lg border border-border-default bg-surface-0 p-4"
          onSubmit={(e) => e.preventDefault()}
        >
          <h2 className="mb-2 text-base font-semibold text-text-900">Regla versionada</h2>
          <div className="grid gap-3">
            <FormField label="Código">
              <TextInput value={ruleCode} onChange={(e) => setRuleCode(e.target.value)} />
            </FormField>
            <FormField label="Tasa IGTF (%)">
              <MoneyInput value={rate} onChange={(e) => setRate(e.target.value)} />
            </FormField>
            <Autorizado operacion={["POST", "/treasury/fiscal-rules"]}>
              <AsyncButton type="submit" variant="secondary" onClick={createRule}>
                Crear regla
              </AsyncButton>
            </Autorizado>
          </div>
          <div className="mt-3 rounded-md border border-border-default p-3 text-sm text-text-500">
            <p className="font-medium text-text-700">Reglas vigentes</p>
            {(rules.data?.items ?? []).map((r) => (
              <p key={r.id} className="mt-1">
                {r.rule_code} · v{r.version} · {r.params}
              </p>
            ))}
            {(rules.data?.items ?? []).length === 0 ? <p className="mt-1">Sin reglas aún.</p> : null}
          </div>
        </form>

        <form
          className="rounded-lg border border-border-default bg-surface-0 p-4"
          onSubmit={(e) => e.preventDefault()}
        >
          <h2 className="mb-2 text-base font-semibold text-text-900">Evaluar evento</h2>
          <div className="grid gap-3">
            <FormField label="Evento">
              <select
                value={eventType}
                onChange={(e) => setEventType(e.target.value as typeof eventType)}
                className="h-10 w-full rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900"
              >
                <option value="PAYMENT">Pago (egreso)</option>
                <option value="COLLECTION">Cobro (ingreso)</option>
                <option value="TRANSFER">Transferencia</option>
              </select>
            </FormField>
            <FormField label="Monto base (sin IVA)">
              <MoneyInput value={amount} onChange={(e) => setAmount(e.target.value)} currency={currency} />
            </FormField>
            <FormField label="Documento">
              <TextInput value={sourceDoc} onChange={(e) => setSourceDoc(e.target.value)} placeholder="Opcional" />
            </FormField>
            <Autorizado operacion={["POST", "/treasury/igft-events/evaluate"]}>
              <AsyncButton type="submit" variant="secondary" onClick={evaluate}>
                Evaluar IGTF
              </AsyncButton>
            </Autorizado>
          </div>
        </form>
      </div>

      <DataTable
        columns={columns}
        data={events.data?.items ?? []}
        loading={events.isLoading}
        error={events.isError ? "No fue posible cargar los eventos IGTF." : null}
        getRowId={(row) => row.id}
        emptyTitle="Sin eventos IGTF"
        emptyDescription="Evalúe un evento con una regla vigente."
      />
    </PageContent>
  );
}
