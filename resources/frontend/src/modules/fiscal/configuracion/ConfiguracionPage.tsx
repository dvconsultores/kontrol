/** Configuración fiscal — fuentes legales, reglas versionadas y perfiles (FR-007-001/002/003/004). */
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { apiFetch } from "@/api/client";
import type { LegalSourceSummary, TaxRuleSummary } from "@/api/types";
import { useNotifications } from "@/app/contexts/NotificationContext";
import { AsyncButton } from "@/components/AsyncButton";
import { FormField } from "@/components/FormField";
import { MoneyInput } from "@/components/MoneyInput";
import { PageContent } from "@/layout/PageContent";
import { PageHeader } from "@/components/PageHeader";
import { TextInput } from "@/components/TextInput";

export function ConfiguracionPage(): React.JSX.Element {
  const queryClient = useQueryClient();
  const { notify } = useNotifications();

  const [authority, setAuthority] = useState("SENIAT");
  const [sourceType, setSourceType] = useState("GACETA");
  const [number, setNumber] = useState("");
  const [taxCode, setTaxCode] = useState("IVA_GENERAL");
  const [rate, setRate] = useState("16");
  const [base, setBase] = useState("");

  const sources = useQuery({
    queryKey: ["fiscal", "legal-sources"],
    queryFn: () => apiFetch<{ items: LegalSourceSummary[] }>("/fiscal/legal-sources"),
    retry: false,
  });
  const rules = useQuery({
    queryKey: ["fiscal", "tax-rules"],
    queryFn: () => apiFetch<{ items: TaxRuleSummary[] }>("/fiscal/tax-rule-versions"),
    retry: false,
  });

  const refresh = (): void => {
    void queryClient.invalidateQueries({ queryKey: ["fiscal"] });
  };

  const createSource = async (): Promise<void> => {
    await apiFetch("/fiscal/legal-sources", { method: "POST", body: { authority, source_type: sourceType, number: number || null } });
    notify({ type: "success", title: "Fuente legal creada", description: `${authority} ${number}` });
    setNumber("");
    refresh();
  };

  const activateSource = async (id: string): Promise<void> => {
    await apiFetch(`/fiscal/legal-sources/${id}/activate`, { method: "POST" });
    notify({ type: "success", title: "Fuente activada", description: "Fuente legal validada." });
    refresh();
  };

  const createRule = async (): Promise<void> => {
    await apiFetch("/fiscal/tax-rule-versions", { method: "POST", body: { tax_code: taxCode, rate: { percent: Number(rate) || 0 } } });
    notify({ type: "success", title: "Regla creada", description: `${taxCode} al ${rate}% (borrador).` });
    refresh();
  };

  const approveRule = async (id: string): Promise<void> => {
    await apiFetch(`/fiscal/tax-rule-versions/${id}/approve`, { method: "POST" });
    notify({ type: "success", title: "Regla aprobada", description: "Versión activa." });
    refresh();
  };

  const calculate = async (): Promise<void> => {
    const res = await apiFetch<{ amount: number; rate: number }>("/fiscal/tax-calculations", {
      method: "POST",
      body: { tax_code: taxCode, base: Number(base) || 0 },
    });
    notify({ type: "success", title: "Cálculo fiscal", description: `Base ${base} · tasa ${res.rate}% · impuesto ${res.amount.toFixed(2)}` });
    setBase("");
  };

  const row = (label: string, value: string, key: string, action?: { onClick: () => Promise<void>; label: string }): React.JSX.Element => (
    <div key={key} className="flex items-center justify-between border-b border-border-default px-4 py-2 text-sm last:border-b-0">
      <span className="text-text-700">{label}</span>
      <span className="flex items-center gap-2 text-text-500">
        {value}
        {action ? <AsyncButton size="sm" variant="secondary" onClick={action.onClick}>{action.label}</AsyncButton> : null}
      </span>
    </div>
  );

  return (
    <PageContent maxWidth="full">
      <PageHeader
        title="Configuración fiscal"
        description="Reglas versionadas con fuente legal (sin solape de vigentes); los impuestos nunca se hardcodean (FR-007-001/002)."
        crumbs={[{ label: "Fiscal" }, { label: "Configuración" }]}
      />

      <div className="mb-4 grid gap-4 lg:grid-cols-2">
        <form className="rounded-lg border border-border-default bg-surface-0 p-4" onSubmit={(e) => e.preventDefault()}>
          <h2 className="mb-2 text-base font-semibold text-text-900">Fuente legal</h2>
          <div className="grid gap-3">
            <FormField label="Autoridad">
              <TextInput value={authority} onChange={(e) => setAuthority(e.target.value)} />
            </FormField>
            <FormField label="Tipo">
              <select value={sourceType} onChange={(e) => setSourceType(e.target.value)} className="h-10 w-full rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900">
                <option value="GACETA">Gaceta</option>
                <option value="DECRETO">Decreto</option>
                <option value="LEY">Ley</option>
                <option value="PROVIDENCIA">Providencia</option>
              </select>
            </FormField>
            <FormField label="Número">
              <TextInput value={number} onChange={(e) => setNumber(e.target.value)} placeholder="Ej. 42.000" />
            </FormField>
            <AsyncButton type="submit" variant="secondary" onClick={createSource}>
              Crear fuente
            </AsyncButton>
          </div>
        </form>

        <form className="rounded-lg border border-border-default bg-surface-0 p-4" onSubmit={(e) => e.preventDefault()}>
          <h2 className="mb-2 text-base font-semibold text-text-900">Regla versionada</h2>
          <div className="grid gap-3">
            <FormField label="Código fiscal">
              <TextInput value={taxCode} onChange={(e) => setTaxCode(e.target.value)} placeholder="Ej. IVA_GENERAL" />
            </FormField>
            <FormField label="Tasa (%)">
              <MoneyInput value={rate} onChange={(e) => setRate(e.target.value)} />
            </FormField>
            <AsyncButton type="submit" variant="secondary" onClick={createRule}>
              Crear regla (borrador)
            </AsyncButton>
          </div>
          <div className="mt-3 rounded-md border border-border-default p-3 text-sm">
            <p className="font-medium text-text-700">Reglas</p>
            {(rules.data?.items ?? []).map((r) => (
              <div key={r.id} className="mt-1 flex items-center justify-between">
                <span className="text-text-700">
                  {r.tax_code} · v{r.version} · {r.status}
                </span>
                {r.status === "DRAFT" ? (
                  <AsyncButton size="sm" variant="secondary" onClick={() => approveRule(r.id)}>aprobar</AsyncButton>
                ) : null}
              </div>
            ))}
            {(rules.data?.items ?? []).length === 0 ? <p className="mt-1 text-text-500">Sin reglas aún.</p> : null}
          </div>
        </form>
      </div>

      <div className="mb-4 rounded-lg border border-border-default bg-surface-0 p-4">
        <h2 className="mb-2 text-base font-semibold text-text-900">Cálculo de prueba</h2>
        <form className="flex flex-wrap items-end gap-3" onSubmit={(e) => e.preventDefault()}>
          <FormField label="Base">
            <MoneyInput value={base} onChange={(e) => setBase(e.target.value)} />
          </FormField>
          <AsyncButton type="submit" variant="secondary" onClick={calculate}>
            Calcular con regla activa
          </AsyncButton>
        </form>
      </div>

      <div className="rounded-lg border border-border-default bg-surface-0 p-4">
        <h2 className="mb-2 text-base font-semibold text-text-900">Fuentes legales</h2>
        {(sources.data?.items ?? []).map((s) =>
          row(`${s.authority} · ${s.source_type}${s.number ? ` · ${s.number}` : ""}`, s.status, s.id,
            s.status !== "ACTIVE" ? { onClick: () => activateSource(s.id), label: "activar" } : undefined),
        )}
        {(sources.data?.items ?? []).length === 0 ? <p className="text-sm text-text-500">Sin fuentes legales.</p> : null}
      </div>
    </PageContent>
  );
}
