/** Perfiles fiscales — perfiles de producto/servicio (FR-002-090). */
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { apiFetch } from "@/api/client";
import { useNotifications } from "@/app/contexts/NotificationContext";
import { Autorizado } from "@/components/Autorizado";
import { AsyncButton } from "@/components/AsyncButton";
import { FormField } from "@/components/FormField";
import { PageContent } from "@/layout/PageContent";
import { PageHeader } from "@/components/PageHeader";
import { TextInput } from "@/components/TextInput";

interface ProfileSummary {
  id: string;
  code: string;
  name: string;
  profile_type: string;
  version: string;
  status: string;
  approval_status: string;
}

const PROFILE_TYPES = ["INVENTORY", "SERVICIO", "VENTA", "COMPRA"];
const TAX_CLASSIFICATIONS = ["GRAVADO", "EXENTO", "EXONERADO"];
const TRACE_LEVELS = ["NONE", "PARTIAL", "FULL"];

export function PerfilesFiscalesPage(): React.JSX.Element {
  const queryClient = useQueryClient();
  const { notify } = useNotifications();

  const [code, setCode] = useState("");
  const [name, setName] = useState("");
  const [profileType, setProfileType] = useState("INVENTORY");
  const [taxClassification, setTaxClassification] = useState("GRAVADO");
  const [traceLevel, setTraceLevel] = useState("NONE");
  const [stockable, setStockable] = useState(false);
  const [requiresSica, setRequiresSica] = useState(false);
  const [requiresSigesai, setRequiresSigesai] = useState(false);
  const [requiresSacs, setRequiresSacs] = useState(false);

  const query = useQuery({
    queryKey: ["maestros", "perfiles"],
    queryFn: () => apiFetch<ProfileSummary[]>("/maestros/perfiles"),
    retry: false,
  });

  const createProfile = async (): Promise<void> => {
    try {
      await apiFetch("/maestros/perfiles", {
        method: "POST",
        body: {
          code,
          name,
          profile_type: profileType,
          effective_from: null,
          effective_to: null,
          stockable,
          lot: false,
          serial: false,
          expiry: false,
          trace_level: traceLevel,
          tax_classification: taxClassification,
          islr_concept_ref: null,
          requires_sica: requiresSica,
          requires_sigesai: requiresSigesai,
          requires_sacs: requiresSacs,
        },
      });
      notify({ type: "success", title: "Perfil creado", description: `${code} · ${name}` });
      setCode("");
      setName("");
      void queryClient.invalidateQueries({ queryKey: ["maestros", "perfiles"] });
    } catch (err) {
      const message = err instanceof Error ? err.message : "No fue posible crear el perfil";
      notify({ type: "error", title: "No fue posible crear el perfil", description: message });
    }
  };

  const row = (key: string, label: string, value: string): React.JSX.Element => (
    <div key={key} className="flex items-center justify-between border-b border-border-default px-4 py-2 text-sm last:border-b-0">
      <span className="text-text-700">{label}</span>
      <span className="text-text-500">{value}</span>
    </div>
  );

  const checkbox = (label: string, checked: boolean, onChange: (v: boolean) => void): React.JSX.Element => (
    <label className="flex items-center gap-2 text-sm text-text-700">
      <input type="checkbox" checked={checked} onChange={(e) => onChange(e.target.checked)} className="h-4 w-4" />
      {label}
    </label>
  );

  return (
    <PageContent maxWidth="full">
      <PageHeader
        title="Perfiles fiscales"
        description="Perfiles de inventario/tributarios para productos y servicios."
        crumbs={[{ label: "Maestros" }, { label: "Perfiles fiscales" }]}
      />

      <Autorizado operacion={["POST", "/maestros/perfiles"]}>
        <section className="mb-4 rounded-lg border border-border-default bg-surface-0 p-4">
          <h2 className="mb-2 text-base font-semibold text-text-900">Crear perfil</h2>
          <form className="flex flex-wrap items-end gap-3" onSubmit={(e) => e.preventDefault()}>
            <FormField label="Código" required>
              <TextInput value={code} onChange={(e) => setCode(e.target.value)} placeholder="Ej. PERF-01" required />
            </FormField>
            <FormField label="Nombre" required>
              <TextInput value={name} onChange={(e) => setName(e.target.value)} placeholder="Nombre del perfil" required />
            </FormField>
            <FormField label="Tipo">
              <select value={profileType} onChange={(e) => setProfileType(e.target.value)} className="h-10 w-44 rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900">
                {PROFILE_TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
              </select>
            </FormField>
            <FormField label="Clasificación fiscal">
              <select value={taxClassification} onChange={(e) => setTaxClassification(e.target.value)} className="h-10 w-44 rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900">
                {TAX_CLASSIFICATIONS.map((t) => <option key={t} value={t}>{t}</option>)}
              </select>
            </FormField>
            <FormField label="Trazabilidad">
              <select value={traceLevel} onChange={(e) => setTraceLevel(e.target.value)} className="h-10 w-36 rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900">
                {TRACE_LEVELS.map((t) => <option key={t} value={t}>{t}</option>)}
              </select>
            </FormField>
            <div className="flex flex-wrap gap-4 pb-2">
              {checkbox("Inventariable", stockable, setStockable)}
              {checkbox("Requiere SICA", requiresSica, setRequiresSica)}
              {checkbox("Requiere SIGESAI", requiresSigesai, setRequiresSigesai)}
              {checkbox("Requiere SACS", requiresSacs, setRequiresSacs)}
            </div>
            <AsyncButton type="submit" variant="primary" onClick={createProfile}>
              Crear
            </AsyncButton>
          </form>
        </section>
      </Autorizado>

      <section className="rounded-lg border border-border-default bg-surface-0 p-4">
        <h2 className="mb-2 text-base font-semibold text-text-900">Perfiles</h2>
        <div>
          {query.isLoading ? <p className="text-sm text-text-500">Cargando…</p> : null}
          {query.isError ? <p className="text-sm text-danger-600" role="alert">No fue posible cargar los perfiles.</p> : null}
          {(query.data ?? []).map((p) =>
            row(p.id, `${p.code} · ${p.name} · ${p.profile_type}`.trim(), `${p.status}/${p.approval_status}`),
          )}
          {query.isSuccess && (query.data ?? []).length === 0 ? <p className="text-sm text-text-500">Sin perfiles registrados.</p> : null}
        </div>
      </section>
    </PageContent>
  );
}
