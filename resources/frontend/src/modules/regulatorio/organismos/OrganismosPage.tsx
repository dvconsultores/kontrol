/** Organismos y perfiles regulatorios (FR-008-001/002/003/005). */
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { apiFetch } from "@/api/client";
import type {
  OfficialRegistrationSummary,
  PermitTypeSummary,
  RegulatoryAuthoritySummary,
  RegulatoryProfileSummary,
} from "@/api/types";
import { useNotifications } from "@/app/contexts/NotificationContext";
import { AsyncButton } from "@/components/AsyncButton";
import { FormField } from "@/components/FormField";
import { PageContent } from "@/layout/PageContent";
import { PageHeader } from "@/components/PageHeader";
import { TextInput } from "@/components/TextInput";

export function OrganismosPage(): React.JSX.Element {
  const queryClient = useQueryClient();
  const { notify } = useNotifications();

  const [name, setName] = useState("SICA");
  const [permitName, setPermitName] = useState("");
  const [authorityId, setAuthorityId] = useState("");
  const [profileDocs, setProfileDocs] = useState("SICA, SIGESAI");

  const authorities = useQuery({
    queryKey: ["regulatorio", "authorities"],
    queryFn: () => apiFetch<{ items: RegulatoryAuthoritySummary[] }>("/regulatory/authorities"),
    retry: false,
  });
  const permitTypes = useQuery({
    queryKey: ["regulatorio", "permit-types"],
    queryFn: () => apiFetch<{ items: PermitTypeSummary[] }>("/regulatory/permit-types"),
    retry: false,
  });
  const registrations = useQuery({
    queryKey: ["regulatorio", "official-registrations"],
    queryFn: () => apiFetch<{ items: OfficialRegistrationSummary[] }>("/regulatory/official-registrations"),
    retry: false,
  });
  const profiles = useQuery({
    queryKey: ["regulatorio", "profiles"],
    queryFn: () => apiFetch<{ items: RegulatoryProfileSummary[] }>("/regulatory/profiles"),
    retry: false,
  });

  const refresh = (): void => {
    void queryClient.invalidateQueries({ queryKey: ["regulatorio"] });
  };

  const createAuthority = async (): Promise<void> => {
    await apiFetch("/regulatory/authorities", { method: "POST", body: { code: name.replace(/\s+/g, "_").toUpperCase(), name } });
    notify({ type: "success", title: "Autoridad creada", description: name });
    setName("");
    refresh();
  };

  const createPermitType = async (): Promise<void> => {
    if (!authorityId) return;
    await apiFetch("/regulatory/permit-types", { method: "POST", body: { authority_id: authorityId, code: permitName.replace(/\s+/g, "-").toUpperCase(), name: permitName } });
    notify({ type: "success", title: "Tipo de permiso creado", description: permitName });
    setPermitName("");
    refresh();
  };

  const createProfile = async (): Promise<void> => {
    const docs = profileDocs.split(",").map((d) => d.trim()).filter(Boolean);
    await apiFetch("/regulatory/profiles", { method: "POST", body: { operation: "DESPACHO", required_documents: docs } });
    notify({ type: "success", title: "Perfil creado", description: `Exige: ${docs.join(", ")}` });
    refresh();
  };

  const section = (title: string, body: React.JSX.Element): React.JSX.Element => (
    <div className="mb-4 rounded-lg border border-border-default bg-surface-0 p-4">
      <h2 className="mb-2 text-base font-semibold text-text-900">{title}</h2>
      {body}
    </div>
  );

  const row = (key: string, label: string, value: string): React.JSX.Element => (
    <div key={key} className="flex items-center justify-between border-b border-border-default px-4 py-2 text-sm last:border-b-0">
      <span className="text-text-700">{label}</span>
      <span className="text-text-500">{value}</span>
    </div>
  );

  return (
    <PageContent maxWidth="full">
      <PageHeader
        title="Organismos y perfiles"
        description="Autoridades (SENIAT, SUNAGRO, INSAI, SACS), tipos de permiso, registros y perfiles regulatorios (FR-008-001/002/003/005)."
        crumbs={[{ label: "Regulatorio" }, { label: "Organismos" }]}
      />

      {section("Registrar autoridad", (
        <form className="flex flex-wrap items-end gap-3" onSubmit={(e) => e.preventDefault()}>
          <FormField label="Nombre">
            <TextInput value={name} onChange={(e) => setName(e.target.value)} placeholder="Ej. SICA" />
          </FormField>
          <AsyncButton type="submit" variant="secondary" onClick={createAuthority}>Crear</AsyncButton>
        </form>
      ))}

      {section("Autoridades", (
        <div>
          {(authorities.data?.items ?? []).map((a) => row(a.id, `${a.name} (${a.code})`, a.status))}
          {(authorities.data?.items ?? []).length === 0 ? <p className="text-sm text-text-500">Sin autoridades.</p> : null}
        </div>
      ))}

      {section("Tipo de permiso", (
        <form className="flex flex-wrap items-end gap-3" onSubmit={(e) => e.preventDefault()}>
          <FormField label="Autoridad">
            <select value={authorityId} onChange={(e) => setAuthorityId(e.target.value)} className="h-10 w-52 rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900">
              <option value="">Seleccionar…</option>
              {(authorities.data?.items ?? []).map((a) => <option key={a.id} value={a.id}>{a.name}</option>)}
            </select>
          </FormField>
          <FormField label="Nombre">
            <TextInput value={permitName} onChange={(e) => setPermitName(e.target.value)} />
          </FormField>
          <AsyncButton type="submit" variant="secondary" onClick={createPermitType}>Crear</AsyncButton>
        </form>
      ))}

      {section("Tipos de permiso", (
        <div>
          {(permitTypes.data?.items ?? []).map((t) => row(t.id, t.name, `${t.scope ?? ""} · ${t.status}`))}
          {(permitTypes.data?.items ?? []).length === 0 ? <p className="text-sm text-text-500">Sin tipos de permiso.</p> : null}
        </div>
      ))}

      {section("Perfil regulatorio (DESPACHO)", (
        <form className="flex flex-wrap items-end gap-3" onSubmit={(e) => e.preventDefault()}>
          <FormField label="Documentos requeridos" className="min-w-72">
            <TextInput value={profileDocs} onChange={(e) => setProfileDocs(e.target.value)} placeholder="Ej. SICA, SIGESAI, SACS" />
          </FormField>
          <AsyncButton type="submit" variant="secondary" onClick={createProfile}>Crear perfil</AsyncButton>
        </form>
      ))}

      {section("Perfiles", (
        <div>
          {(profiles.data?.items ?? []).map((p) => row(p.id, `${p.operation} v${p.version}`, p.required_documents ?? ""))}
          {(profiles.data?.items ?? []).length === 0 ? <p className="text-sm text-text-500">Sin perfiles.</p> : null}
        </div>
      ))}

      {section("Registros oficiales", (
        <div>
          {(registrations.data?.items ?? []).map((r) => row(r.id, `${r.ref_number} · ${r.scope}`, r.status))}
          {(registrations.data?.items ?? []).length === 0 ? <p className="text-sm text-text-500">Sin registros oficiales.</p> : null}
        </div>
      ))}
    </PageContent>
  );
}
