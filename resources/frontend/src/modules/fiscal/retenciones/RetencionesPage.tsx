/** Retenciones — reglas versionadas y ciclo completo (FR-007-040/041). */
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { createColumnHelper } from "@tanstack/react-table";
import { useState } from "react";

import { apiFetch } from "@/api/client";
import type { Party, WithholdingRuleSummary, WithholdingSummary } from "@/api/types";
import { useAutoridad } from "@/app/autoridad/AutoridadContext";
import { useNotifications } from "@/app/contexts/NotificationContext";
import { AsyncButton } from "@/components/AsyncButton";
import { Autorizado } from "@/components/Autorizado";
import { DataTable } from "@/components/DataTable";
import { FormField } from "@/components/FormField";
import { MoneyInput } from "@/components/MoneyInput";
import { PageContent } from "@/layout/PageContent";
import { PageHeader } from "@/components/PageHeader";
import { TextInput } from "@/components/TextInput";

const columnHelper = createColumnHelper<WithholdingSummary>();

export function RetencionesPage(): React.JSX.Element {
  const queryClient = useQueryClient();
  const { notify } = useNotifications();
  const { puede } = useAutoridad();

  const [taxType, setTaxType] = useState<"IVA" | "ISLR">("IVA");
  const [code, setCode] = useState("RT-IVA");
  const [rate, setRate] = useState("3");
  const [partyId, setPartyId] = useState("");
  const [base, setBase] = useState("");

  const rules = useQuery({
    queryKey: ["fiscal", "withholding-rules"],
    queryFn: () => apiFetch<{ items: WithholdingRuleSummary[] }>("/fiscal/withholding-rules"),
    retry: false,
  });
  const withholdings = useQuery({
    queryKey: ["fiscal", "withholdings"],
    queryFn: () => apiFetch<{ items: WithholdingSummary[] }>("/fiscal/withholdings"),
    retry: false,
  });
  const parties = useQuery({
    queryKey: ["maestros", "terceros"],
    queryFn: () => apiFetch<{ items: Party[] }>("/maestros/terceros"),
    retry: false,
  });

  const refresh = (): void => {
    void queryClient.invalidateQueries({ queryKey: ["fiscal", "withholdings"] });
    void queryClient.invalidateQueries({ queryKey: ["fiscal", "withholding-rules"] });
  };

  const createRule = async (): Promise<void> => {
    await apiFetch("/fiscal/withholding-rules", {
      method: "POST",
      body: { tax_type: taxType, code, rate: Number(rate) || 0, concept: `${taxType} ${rate}%` },
    });
    notify({ type: "success", title: "Regla de retención creada", description: `${code} · ${rate}%` });
    refresh();
  };

  const calculate = async (): Promise<void> => {
    if (!partyId) {
      notify({ type: "error", title: "Falta el tercero", description: "Seleccione el tercero." });
      return;
    }
    const res = await apiFetch<{ id: string; amount: number; status: string }>("/fiscal/withholdings/calculate", {
      method: "POST",
      body: { party_id: partyId, tax_type: taxType, code, base: Number(base) || 0 },
    });
    notify({ type: "success", title: "Retención calculada", description: `${res.amount.toFixed(2)} · ${res.status}` });
    setBase("");
    refresh();
  };

  const transition = async (id: string, target: string): Promise<void> => {
    await apiFetch(`/fiscal/withholdings/${id}/transition`, { method: "POST", body: { target } });
    notify({ type: "success", title: "Retención actualizada", description: `Estado → ${target}` });
    refresh();
  };

  const certificate = async (id: string): Promise<void> => {
    await apiFetch(`/fiscal/withholdings/${id}/certificate`, {
      method: "POST",
      body: { certificate_ref: `COMP-${id.slice(0, 8)}` },
    });
    notify({ type: "success", title: "Comprobante emitido", description: "Retención con comprobante (EMITIDA)." });
    refresh();
  };

  const columns = [
    columnHelper.accessor("party_id", { header: "Tercero" }),
    columnHelper.accessor("tax_type", { header: "Tipo" }),
    columnHelper.accessor("base", { header: "Base" }),
    columnHelper.accessor("amount", { header: "Monto" }),
    columnHelper.accessor("period", { header: "Período" }),
    columnHelper.accessor("status", { header: "Estado" }),
    columnHelper.display({
      id: "actions",
      header: "Acciones",
      cell: ({ row }) => {
        const s = row.original.status;
        return (
          <div className="flex justify-end gap-1">
            {s === "CALCULADA" && puede("POST", `/fiscal/withholdings/${row.original.id}/transition`) ? <AsyncButton size="sm" variant="secondary" onClick={() => transition(row.original.id, "PRACTICADA")}>practicar</AsyncButton> : null}
            {s === "PRACTICADA" && puede("POST", `/fiscal/withholdings/${row.original.id}/certificate`) ? <AsyncButton size="sm" variant="secondary" onClick={() => certificate(row.original.id)}>comprobante</AsyncButton> : null}
            {s === "EMITIDA" && puede("POST", `/fiscal/withholdings/${row.original.id}/transition`) ? <AsyncButton size="sm" variant="secondary" onClick={() => transition(row.original.id, "DECLARADA")}>declarar</AsyncButton> : null}
            {s === "DECLARADA" && puede("POST", `/fiscal/withholdings/${row.original.id}/transition`) ? <AsyncButton size="sm" variant="secondary" onClick={() => transition(row.original.id, "PAGADA")}>pagar</AsyncButton> : null}
            {s === "PAGADA" && puede("POST", `/fiscal/withholdings/${row.original.id}/transition`) ? <AsyncButton size="sm" variant="secondary" onClick={() => transition(row.original.id, "CONCILIADA")}>conciliar</AsyncButton> : null}
          </div>
        );
      },
    }),
  ];

  return (
    <PageContent maxWidth="full">
      <PageHeader
        title="Retenciones"
        description="Reglas versionadas (IVA/ISLR) y ciclo calculada → practicada → comprobante → declarada → pagada → conciliada (FR-007-040/041)."
        crumbs={[{ label: "Fiscal" }, { label: "Retenciones" }]}
      />

      <div className="mb-4 grid gap-4 lg:grid-cols-2">
        <form className="rounded-lg border border-border-default bg-surface-0 p-4" onSubmit={(e) => e.preventDefault()}>
          <h2 className="mb-2 text-base font-semibold text-text-900">Regla de retención</h2>
          <div className="grid gap-3">
            <FormField label="Tipo">
              <select value={taxType} onChange={(e) => setTaxType(e.target.value as typeof taxType)} className="h-10 w-full rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900">
                <option value="IVA">IVA</option>
                <option value="ISLR">ISLR</option>
              </select>
            </FormField>
            <FormField label="Código">
              <TextInput value={code} onChange={(e) => setCode(e.target.value)} />
            </FormField>
            <FormField label="Tasa (%)">
              <MoneyInput value={rate} onChange={(e) => setRate(e.target.value)} />
            </FormField>
            <Autorizado operacion={["POST", "/fiscal/withholding-rules"]}>
              <AsyncButton type="submit" variant="secondary" onClick={createRule}>
                Crear regla
              </AsyncButton>
            </Autorizado>
          </div>
          <div className="mt-3 rounded-md border border-border-default p-3 text-sm">
            <p className="font-medium text-text-700">Reglas</p>
            {(rules.data?.items ?? []).map((r) => (
              <p key={r.id} className="mt-1 text-text-700">{r.code} · {r.tax_type} · {r.rate}% · {r.status}</p>
            ))}
            {(rules.data?.items ?? []).length === 0 ? <p className="mt-1 text-text-500">Sin reglas.</p> : null}
          </div>
        </form>

        <form className="rounded-lg border border-border-default bg-surface-0 p-4" onSubmit={(e) => e.preventDefault()}>
          <h2 className="mb-2 text-base font-semibold text-text-900">Calcular retención</h2>
          <div className="grid gap-3">
            <FormField label="Tercero">
              <select value={partyId} onChange={(e) => setPartyId(e.target.value)} className="h-10 w-full rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900">
                <option value="">Seleccionar…</option>
                {(parties.data?.items ?? []).map((p) => (
                  <option key={p.id} value={p.id}>{p.name}</option>
                ))}
              </select>
            </FormField>
            <FormField label="Base">
              <MoneyInput value={base} onChange={(e) => setBase(e.target.value)} />
            </FormField>
            <Autorizado operacion={["POST", "/fiscal/withholdings/calculate"]}>
              <AsyncButton type="submit" variant="secondary" onClick={calculate}>
                Calcular con regla {code}
              </AsyncButton>
            </Autorizado>
          </div>
        </form>
      </div>

      <DataTable
        columns={columns}
        data={withholdings.data?.items ?? []}
        loading={withholdings.isLoading}
        error={withholdings.isError ? "No fue posible cargar las retenciones." : null}
        getRowId={(row) => row.id}
        emptyTitle="Sin retenciones"
        emptyDescription="Calcule una retención con una regla vigente."
      />
    </PageContent>
  );
}
