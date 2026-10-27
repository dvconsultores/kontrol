/** Sucursales — listado y alta de sucursales por empresa (FR-016/017). */
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { apiFetch } from "@/api/client";
import { useCompany } from "@/app/contexts/CompanyContext";
import { useNotifications } from "@/app/contexts/NotificationContext";
import { Autorizado } from "@/components/Autorizado";
import { AsyncButton } from "@/components/AsyncButton";
import { FormField } from "@/components/FormField";
import { PageContent } from "@/layout/PageContent";
import { PageHeader } from "@/components/PageHeader";
import { TextInput } from "@/components/TextInput";

interface BranchSummary {
  id: string;
  company_id: string;
  code: string;
  name: string;
  status: string;
}

export function SucursalesPage(): React.JSX.Element {
  const { activeCompany } = useCompany();
  const queryClient = useQueryClient();
  const { notify } = useNotifications();

  const [code, setCode] = useState("");
  const [name, setName] = useState("");
  const [address, setAddress] = useState("");
  const [manager, setManager] = useState("");

  const companyId = activeCompany?.id ?? null;

  const query = useQuery({
    queryKey: ["organization", "branches", companyId],
    queryFn: () => apiFetch<BranchSummary[]>(`/organization/branches?company_id=${encodeURIComponent(companyId ?? "")}`),
    enabled: Boolean(companyId),
    retry: false,
  });

  const createBranch = async (): Promise<void> => {
    if (!companyId) {
      return;
    }
    try {
      await apiFetch("/organization/branches", {
        method: "POST",
        body: {
          company_id: companyId,
          code,
          name,
          address: address || null,
          manager: manager || null,
        },
      });
      notify({ type: "success", title: "Sucursal creada", description: `${code} · ${name}` });
      setCode("");
      setName("");
      setAddress("");
      setManager("");
      void queryClient.invalidateQueries({ queryKey: ["organization", "branches"] });
    } catch (err) {
      const message = err instanceof Error ? err.message : "No fue posible crear la sucursal";
      notify({ type: "error", title: "No fue posible crear la sucursal", description: message });
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
        title="Sucursales"
        description="Dependencias de la empresa activa."
        crumbs={[{ label: "Organización" }, { label: "Sucursales" }]}
      />

      {!companyId ? (
        <div className="rounded-md border border-warning-100 bg-warning-100/40 p-4 text-sm text-warning-600" role="alert">
          No hay una empresa activa. Vaya a <strong>Organización → Empresas</strong> y active la empresa para registrar sucursales.
        </div>
      ) : (
        <>
          <Autorizado operacion={["POST", "/organization/branches"]}>
            <section className="mb-4 rounded-lg border border-border-default bg-surface-0 p-4">
              <h2 className="mb-2 text-base font-semibold text-text-900">Registrar sucursal</h2>
              <form className="flex flex-wrap items-end gap-3" onSubmit={(e) => e.preventDefault()}>
                <FormField label="Código" required>
                  <TextInput value={code} onChange={(e) => setCode(e.target.value)} placeholder="Ej. SUC-01" required />
                </FormField>
                <FormField label="Nombre" required>
                  <TextInput value={name} onChange={(e) => setName(e.target.value)} placeholder="Nombre de la sucursal" required />
                </FormField>
                <FormField label="Dirección">
                  <TextInput value={address} onChange={(e) => setAddress(e.target.value)} placeholder="Opcional" />
                </FormField>
                <FormField label="Encargado">
                  <TextInput value={manager} onChange={(e) => setManager(e.target.value)} placeholder="Opcional" />
                </FormField>
                <AsyncButton type="submit" variant="primary" onClick={createBranch}>
                  Registrar
                </AsyncButton>
              </form>
            </section>
          </Autorizado>

          <section className="rounded-lg border border-border-default bg-surface-0 p-4">
            <h2 className="mb-2 text-base font-semibold text-text-900">
              Sucursales de {activeCompany?.legal_name}
            </h2>
            <div>
              {query.isLoading ? <p className="text-sm text-text-500">Cargando…</p> : null}
              {query.isError ? (
                <p className="text-sm text-danger-600" role="alert">
                  No fue posible cargar las sucursales.
                </p>
              ) : null}
              {(query.data ?? []).map((b) => row(b.id, `${b.code} · ${b.name}`, b.status))}
              {query.isSuccess && (query.data ?? []).length === 0 ? (
                <p className="text-sm text-text-500">Sin sucursales registradas.</p>
              ) : null}
            </div>
          </section>
        </>
      )}
    </PageContent>
  );
}
