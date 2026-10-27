/**
 * Edición de política — pantalla completa con URL propia (Spec 045, WF-045-05).
 *
 * Ningún umbral viene precargado: KONTROL no entrega valores de negocio
 * (Constitución P8, CL-045-12). La simulación permite verificar antes de
 * activar, sin crear solicitudes (FR-045-008).
 */
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useParams } from "react-router";

import { apiFetch } from "@/api/client";
import type { ApprovalPolicySummary } from "@/api/types";
import { useNotifications } from "@/app/contexts/NotificationContext";
import { useAutoridad } from "@/app/autoridad/AutoridadContext";
import { Autorizado } from "@/components/Autorizado";
import { AsyncButton } from "@/components/AsyncButton";
import { ErrorState } from "@/components/ErrorState";
import { FormField } from "@/components/FormField";
import { LoadingState } from "@/components/LoadingState";
import { PageHeader } from "@/components/PageHeader";
import { TextInput } from "@/components/TextInput";
import { PageContent } from "@/layout/PageContent";

const OPERATORS = [
  { value: "gt", label: "mayor que" },
  { value: "gte", label: "mayor o igual que" },
  { value: "lt", label: "menor que" },
  { value: "lte", label: "menor o igual que" },
  { value: "eq", label: "igual a" },
  { value: "ne", label: "distinto de" },
  { value: "in", label: "está en" },
  { value: "not_in", label: "no está en" },
];

const RESOLVERS = [
  { value: "ROLE", label: "Rol" },
  { value: "USER", label: "Usuario" },
  { value: "SCOPE_OWNER", label: "Responsable del alcance" },
];

const QUORUMS = [
  { value: "ANY", label: "Cualquiera" },
  { value: "ALL", label: "Todos" },
  { value: "N_OF_M", label: "N de M" },
];

const selectClass =
  "h-10 rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900";

export function PoliticaDetallePage(): React.JSX.Element {
  const { policyId = "" } = useParams();
  const { notify } = useNotifications();
  const queryClient = useQueryClient();
  const { puede } = useAutoridad();

  const [ruleName, setRuleName] = useState("");
  const [field, setField] = useState("amount_base");
  const [operator, setOperator] = useState("gt");
  const [value, setValue] = useState("");
  const [levelRule, setLevelRule] = useState("");
  const [levelOrder, setLevelOrder] = useState("1");
  const [resolverType, setResolverType] = useState("ROLE");
  const [resolverRef, setResolverRef] = useState("");
  const [quorumType, setQuorumType] = useState("ANY");
  const [quorumN, setQuorumN] = useState("");
  const [slaHours, setSlaHours] = useState("");
  const [simulation, setSimulation] = useState<string | null>(null);
  const [simAmount, setSimAmount] = useState("");

  const query = useQuery({
    queryKey: ["aprobaciones", "policy", policyId],
    queryFn: () => apiFetch<ApprovalPolicySummary>(`/approvals/policies/${policyId}`),
    enabled: Boolean(policyId),
    retry: false,
  });

  const policy = query.data;
  const editable = policy?.status === "DRAFT";
  const refresh = (): void => {
    void queryClient.invalidateQueries({ queryKey: ["aprobaciones", "policy", policyId] });
  };

  const run = async (label: string, fn: () => Promise<unknown>): Promise<void> => {
    try {
      await fn();
      notify({ type: "success", title: label });
      refresh();
    } catch (err) {
      const message = err instanceof Error ? err.message : "La operación no pudo completarse";
      notify({ type: "error", title: `No fue posible: ${label.toLowerCase()}`, description: message });
    }
  };

  const toggleFlag = async (
    key: "requires_segregation" | "allow_self_approval" | "distinct_actors_across_levels",
    next: boolean,
  ): Promise<void> => {
    await run("Política actualizada", () =>
      apiFetch(`/approvals/policies/${policyId}`, { method: "PATCH", body: { [key]: next } }),
    );
  };

  const addRule = async (): Promise<void> => {
    await run("Regla añadida", () =>
      apiFetch(`/approvals/policies/${policyId}/rules`, {
        method: "POST",
        body: {
          name: ruleName,
          conditions: [
            { field, operator, value: Number.isNaN(Number(value)) ? value : Number(value) },
          ],
        },
      }),
    );
    setRuleName("");
    setValue("");
  };

  const addLevel = async (): Promise<void> => {
    await run("Nivel añadido", () =>
      apiFetch(`/approvals/policies/${policyId}/rules/${levelRule}/levels`, {
        method: "POST",
        body: {
          level_order: Number(levelOrder),
          resolver_type: resolverType,
          resolver_ref: resolverRef,
          quorum_type: quorumType,
          quorum_n: quorumN ? Number(quorumN) : null,
          sla_hours: slaHours ? Number(slaHours) : null,
        },
      }),
    );
    setResolverRef("");
  };

  const simulate = async (): Promise<void> => {
    if (!policy) return;
    try {
      const out = await apiFetch<{
        requires_approval: boolean;
        levels?: { level_order: number }[];
        fingerprint_fields?: string[];
        reason?: string;
      }>("/approvals/evaluate", {
        method: "POST",
        body: {
          company_id: policy.company_id,
          process_type: policy.process_type,
          context: { amount: Number(simAmount || 0), currency: policy.base_currency },
          // Simula ESTA versión, aunque sea borrador (FR-045-008).
          policy_id: policy.id,
        },
      });
      setSimulation(
        out.requires_approval
          ? `Requiere ${out.levels?.length ?? 0} nivel(es). Campos de la huella: ${(out.fingerprint_fields ?? []).join(", ")}.`
          : `No requiere aprobación (${out.reason ?? "ninguna regla aplica"}).`,
      );
    } catch (err) {
      setSimulation(err instanceof Error ? err.message : "No fue posible simular");
    }
  };

  if (query.isLoading) return <LoadingState label="Cargando política…" />;
  if (query.error || !policy) {
    return <ErrorState message="No fue posible cargar la política." onRetry={refresh} />;
  }

  return (
    <PageContent maxWidth="full">
      <PageHeader
        title={`${policy.process_type} v${policy.version}`}
        description={
          editable
            ? "Borrador editable. Al activarla, la versión anterior cierra su vigencia."
            : "Versión no editable. Para cambiarla, cree una versión nueva."
        }
        crumbs={[
          { label: "Aprobaciones" },
          { label: "Políticas", to: "/aprobaciones/politicas" },
          { label: `v${policy.version}` },
        ]}
        actions={
          editable ? (
            <Autorizado operacion={["POST", `/approvals/policies/${policyId}/activate`]}>
              <AsyncButton
                variant="primary"
                onClick={() =>
                  run("Política activada", () =>
                    apiFetch(`/approvals/policies/${policyId}/activate`, { method: "POST" }),
                  )
                }
              >
                Activar
              </AsyncButton>
            </Autorizado>
          ) : policy.status === "ACTIVE" ? (
            <Autorizado operacion={["POST", `/approvals/policies/${policyId}/close`]}>
              <AsyncButton
                variant="secondary"
                onClick={() =>
                  run("Política cerrada", () =>
                    apiFetch(`/approvals/policies/${policyId}/close`, { method: "POST" }),
                  )
                }
              >
                Cerrar vigencia
              </AsyncButton>
            </Autorizado>
          ) : null
        }
      />

      <section className="mb-4 rounded-lg border border-border-default bg-surface-0 p-4">
        <h2 className="mb-3 text-base font-semibold text-text-900">General</h2>
        <div className="flex flex-col gap-2 text-sm text-text-900">
          <label className="flex items-center gap-2">
            <input
              type="checkbox"
              className="h-4 w-4"
              disabled={!editable || !puede("PATCH", `/approvals/policies/${policyId}`)}
              checked={policy.requires_segregation}
              onChange={(e) => void toggleFlag("requires_segregation", e.target.checked)}
            />
            Exigir segregación de funciones (quien crea no aprueba)
          </label>
          <label className="flex items-center gap-2">
            <input
              type="checkbox"
              className="h-4 w-4"
              disabled={!editable || !puede("PATCH", `/approvals/policies/${policyId}`)}
              checked={policy.allow_self_approval}
              onChange={(e) => void toggleFlag("allow_self_approval", e.target.checked)}
            />
            Permitir autoaprobación
          </label>
          <label className="flex items-center gap-2">
            <input
              type="checkbox"
              className="h-4 w-4"
              disabled={!editable || !puede("PATCH", `/approvals/policies/${policyId}`)}
              checked={policy.distinct_actors_across_levels}
              onChange={(e) => void toggleFlag("distinct_actors_across_levels", e.target.checked)}
            />
            Exigir aprobadores distintos entre niveles
          </label>
          <p className="mt-1 text-text-500">Moneda base de evaluación: {policy.base_currency}</p>
        </div>
      </section>

      <section className="mb-4 rounded-lg border border-border-default bg-surface-0 p-4">
        <h2 className="mb-1 text-base font-semibold text-text-900">Reglas</h2>
        <p className="mb-3 text-sm text-text-500">
          Las condiciones de una regla se cumplen todas a la vez. Varias reglas equivalen a «o».
        </p>
        {policy.rules.length === 0 ? (
          <p className="text-sm text-text-500">Sin reglas. Una política sin reglas no puede activarse.</p>
        ) : (
          <ul className="mb-4 flex flex-col gap-3">
            {policy.rules.map((rule) => (
              <li key={rule.id} className="rounded-md border border-border-default p-3">
                <p className="text-sm font-semibold text-text-900">{rule.name}</p>
                <ul className="mt-1 text-sm text-text-500">
                  {rule.conditions.map((c, i) => (
                    <li key={`${rule.id}-c-${i}`}>
                      {c.field} {OPERATORS.find((o) => o.value === c.operator)?.label ?? c.operator}{" "}
                      {String(c.value ?? "")}
                    </li>
                  ))}
                </ul>
                <p className="mt-2 text-xs uppercase tracking-wide text-text-500">Niveles</p>
                {rule.levels.length === 0 ? (
                  <p className="text-sm text-text-500">Sin niveles definidos.</p>
                ) : (
                  <ol className="text-sm text-text-900">
                    {rule.levels.map((lv) => (
                      <li key={lv.id ?? lv.level_order}>
                        {lv.level_order}. {RESOLVERS.find((r) => r.value === lv.resolver_type)?.label}{" "}
                        {lv.resolver_ref} · cuórum{" "}
                        {QUORUMS.find((q) => q.value === lv.quorum_type)?.label}
                        {lv.quorum_n ? ` (${lv.quorum_n})` : ""}
                        {lv.sla_hours ? ` · SLA ${lv.sla_hours} h` : ""}
                      </li>
                    ))}
                  </ol>
                )}
                <p className="mt-2 text-xs text-text-500">
                  Campos de la huella: {rule.condition_fields.join(", ") || "—"}
                </p>
              </li>
            ))}
          </ul>
        )}

        {editable && puede("POST", `/approvals/policies/${policyId}/rules`) ? (
          <>
            <form className="flex flex-wrap items-end gap-3" onSubmit={(e) => e.preventDefault()}>
              <FormField label="Nombre de la regla" required>
                <TextInput value={ruleName} onChange={(e) => setRuleName(e.target.value)} required />
              </FormField>
              <FormField label="Campo">
                <TextInput value={field} onChange={(e) => setField(e.target.value)} />
              </FormField>
              <FormField label="Operador">
                <select
                  className={selectClass}
                  value={operator}
                  onChange={(e) => setOperator(e.target.value)}
                  aria-label="Operador de la condición"
                >
                  {OPERATORS.map((o) => (
                    <option key={o.value} value={o.value}>
                      {o.label}
                    </option>
                  ))}
                </select>
              </FormField>
              <FormField label="Valor">
                <TextInput value={value} onChange={(e) => setValue(e.target.value)} />
              </FormField>
              <AsyncButton type="submit" variant="secondary" onClick={addRule}>
                Añadir regla
              </AsyncButton>
            </form>

            <form className="mt-4 flex flex-wrap items-end gap-3" onSubmit={(e) => e.preventDefault()}>
              <FormField label="Regla" required>
                <select
                  className={selectClass}
                  value={levelRule}
                  onChange={(e) => setLevelRule(e.target.value)}
                  aria-label="Regla a la que se añade el nivel"
                >
                  <option value="">Seleccione…</option>
                  {policy.rules.map((r) => (
                    <option key={r.id} value={r.id}>
                      {r.name}
                    </option>
                  ))}
                </select>
              </FormField>
              <FormField label="Orden">
                <TextInput
                  type="number"
                  value={levelOrder}
                  onChange={(e) => setLevelOrder(e.target.value)}
                />
              </FormField>
              <FormField label="Resuelve">
                <select
                  className={selectClass}
                  value={resolverType}
                  onChange={(e) => setResolverType(e.target.value)}
                  aria-label="Tipo de resolutor"
                >
                  {RESOLVERS.map((r) => (
                    <option key={r.value} value={r.value}>
                      {r.label}
                    </option>
                  ))}
                </select>
              </FormField>
              <FormField label="Referencia" required>
                <TextInput
                  value={resolverRef}
                  onChange={(e) => setResolverRef(e.target.value)}
                  placeholder="Código de rol o id de usuario"
                  required
                />
              </FormField>
              <FormField label="Cuórum">
                <select
                  className={selectClass}
                  value={quorumType}
                  onChange={(e) => setQuorumType(e.target.value)}
                  aria-label="Tipo de cuórum"
                >
                  {QUORUMS.map((q) => (
                    <option key={q.value} value={q.value}>
                      {q.label}
                    </option>
                  ))}
                </select>
              </FormField>
              {quorumType === "N_OF_M" ? (
                <FormField label="N" required>
                  <TextInput
                    type="number"
                    value={quorumN}
                    onChange={(e) => setQuorumN(e.target.value)}
                    required
                  />
                </FormField>
              ) : null}
              <FormField label="SLA (horas)">
                <TextInput type="number" value={slaHours} onChange={(e) => setSlaHours(e.target.value)} />
              </FormField>
              <Autorizado operacion={["POST", `/approvals/policies/${policyId}/rules/${levelRule}/levels`]}>
                <AsyncButton type="submit" variant="secondary" onClick={addLevel}>
                  Añadir nivel
                </AsyncButton>
              </Autorizado>
            </form>
          </>
        ) : null}
      </section>

      <section className="rounded-lg border border-border-default bg-surface-0 p-4">
        <h2 className="mb-1 text-base font-semibold text-text-900">Simulación</h2>
        <p className="mb-3 text-sm text-text-500">
          Verifica qué niveles aplicarían sin crear ninguna solicitud.
        </p>
        <form className="flex flex-wrap items-end gap-3" onSubmit={(e) => e.preventDefault()}>
          <FormField label={`Monto (${policy.base_currency})`}>
            <TextInput type="number" value={simAmount} onChange={(e) => setSimAmount(e.target.value)} />
          </FormField>
          <AsyncButton type="submit" variant="secondary" onClick={simulate}>
            Simular
          </AsyncButton>
        </form>
        {simulation ? <p className="mt-3 text-sm text-text-900">{simulation}</p> : null}
      </section>
    </PageContent>
  );
}
