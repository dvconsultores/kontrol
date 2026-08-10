/** Establecimientos — puntos de emisión por sucursal (FR-016/019). */
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { apiFetch } from "@/api/client";
import { useCompany } from "@/app/contexts/CompanyContext";
import { useNotifications } from "@/app/contexts/NotificationContext";
import { AsyncButton } from "@/components/AsyncButton";
import { FormField } from "@/components/FormField";
import { PageContent } from "@/layout/PageContent";
import { PageHeader } from "@/components/PageHeader";
import { TextInput } from "@/components/TextInput";

interface BranchOption {
  id: string;
  code: string;
  name: string;
}

interface EstablishmentSummary {
  id: string;
  branch_id: string;
  code: string;
  name: string;
  issuance_enabled: boolean;
  status: string;
}

export function EstablecimientosPage(): React.JSX.Element {
  const { activeCompany } = useCompany();
  const queryClient = useQueryClient();
  const { notify } = useNotifications();

  const [branchId, setBranchId] = useState("");
  const [code, setCode] = useState("");
  const [name, setName] = useState("");
  const [fiscalAddress, setFiscalAddress] = useState("");

  const companyId = activeCompany?.id ?? null;

  const branches = useQuery({
    queryKey: ["organization", "branches", companyId],
    queryFn: () => apiFetch<BranchOption[]>(`/organization/branches?company_id=${encodeURIComponent(companyId ?? "")}`),
    enabled: Boolean(companyId),
    retry: false,
  });
  const establishments = useQuery({
    queryKey: ["organization", "establishments", branchId],
    queryFn: () => apiFetch<EstablishmentSummary[]>(`/organization/establishments?branch_id=${encodeURIComponent(branchId)}`),
    enabled: Boolean(companyId),
    retry: false,
  });

  const createEstablishment = async (): Promise<void> => {
    if (!branchId) {
      notify({ type: "warning", title: "Falta sucursal", description: "Seleccione la sucursal del establecimiento." });
      return;
    }
    try {
      await apiFetch("/organization/establishments", {
        method: "POST",
        body: { branch_id: branchId, code, name, fiscal_address: fiscalAddress || null },
      });
      notify({ type: "success", title: "Establecimiento creado", description: `${code} · ${name}` });
      setCode("");
      setName("");
      setFiscalAddress("");
      void queryClient.invalidateQueries({ queryKey: ["organization", "establishments"] });
    } catch (err) {
      const message = err instanceof Error ? err.message : "No fue posible crear el establecimiento";
      notify({ type: "error", title: "No fue posible crear el establecimiento", description: message });
    }
  };

  const row = (key: string, label: string, value: string): React.JSX.Element => (
    <div
      key={key}
      className="flex items-center justify-between border-b border-border-default px-4 py-2 text-sm last:border-b-0"
    >
      <span className="text-text-700">{label}</span>
      <span className="text-text-500">{value}</span>
    </div>
  );

  return (
    <PageContent maxWidth="full">
      <PageHeader
        title="Establecimientos"
        description="Puntos de emisión de la empresa activa, por sucursal."
        crumbs={[{ label: "Organización" }, { label: "Establecimientos" }]}
      />

      {!companyId ? (
        <div className="rounded-md border border-warning-100 bg-warning-100/40 p-4 text-sm text-warning-600" role="alert">
          No hay una empresa activa. Vaya a <strong>Organización → Empresas</strong> y active la empresa para registrar establecimientos.
        </div>
      ) : (
        <>
          <section className="mb-4 rounded-lg border border-border-default bg-surface-0 p-4">
            <h2 className="mb-2 text-base font-semibold text-text-900">Registrar establecimiento</h2>
            <form className="flex flex-wrap items-end gap-3" onSubmit={(e) => e.preventDefault()}>
              <FormField label="Sucursal" required>
                <select
                  value={branchId}
                  onChange={(e) => setBranchId(e.target.value)}
                  className="h-10 w-56 rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900"
                >
                  <option value="">Seleccionar…</option>
                  {(branches.data ?? []).map((b) => (
                    <option key={b.id} value={b.id}>
                      {b.code} · {b.name}
                    </option>
                  ))}
                </select>
              </FormField>
              <FormField label="Código" required>
                <TextInput value={code} onChange={(e) => setCode(e.target.value)} placeholder="Ej. EST-01" required />
              </FormField>
              <FormField label="Nombre" required>
                <TextInput value={name} onChange={(e) => setName(e.target.value)} placeholder="Nombre del establecimiento" required />
              </FormField>
              <FormField label="Dirección fiscal">
                <TextInput value={fiscalAddress} onChange={(e) => setFiscalAddress(e.target.value)} placeholder="Opcional" />
              </FormField>
              <AsyncButton type="submit" variant="primary" onClick={createEstablishment}>
                Registrar
              </AsyncButton>
            </form>
          </section>

          <section className="rounded-lg border border-border-default bg-surface-0 p-4">
            <h2 className="mb-2 text-base font-semibold text-text-900">Establecimientos de {activeCompany?.legal_name}</h2>
            <div>
              {establishments.isLoading ? <p className="text-sm text-text-500">Cargando…</p> : null}
              {establishments.isError ? (
                <p className="text-sm text-danger-600" role="alert">
                  No fue posible cargar los establecimientos.
                </p>
              ) : null}
              {(establishments.data ?? []).map((e) =>
                row(e.id, `${e.code} · ${e.name} · emisión ${e.issuance_enabled ? "habilitada" : "deshabilitada"}`, e.status),
              )}
              {establishments.isSuccess && (establishments.data ?? []).length === 0 ? (
                <p className="text-sm text-text-500">Sin establecimientos registrados.</p>
              ) : null}
            </div>
          </section>
        </>
      )}
    </PageContent>
  );
}
