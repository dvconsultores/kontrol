/** Almacenes — listado y alta de almacenes por empresa (FR-016/018). */
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

interface WarehouseSummary {
  id: string;
  company_id: string;
  branch_id: string | null;
  code: string;
  name: string;
  warehouse_type: string;
  status: string;
}

const WAREHOUSE_TYPES = [
  { value: "PHYSICAL", label: "Físico" },
  { value: "VIRTUAL", label: "Virtual" },
];

export function AlmacenesPage(): React.JSX.Element {
  const { activeCompany } = useCompany();
  const queryClient = useQueryClient();
  const { notify } = useNotifications();

  const [code, setCode] = useState("");
  const [name, setName] = useState("");
  const [warehouseType, setWarehouseType] = useState("PHYSICAL");
  const [branchId, setBranchId] = useState("");

  const companyId = activeCompany?.id ?? null;

  const warehouses = useQuery({
    queryKey: ["organization", "warehouses", companyId],
    queryFn: () => apiFetch<WarehouseSummary[]>(`/organization/warehouses?company_id=${encodeURIComponent(companyId ?? "")}`),
    enabled: Boolean(companyId),
    retry: false,
  });
  const branches = useQuery({
    queryKey: ["organization", "branches", companyId],
    queryFn: () => apiFetch<BranchOption[]>(`/organization/branches?company_id=${encodeURIComponent(companyId ?? "")}`),
    enabled: Boolean(companyId),
    retry: false,
  });

  const createWarehouse = async (): Promise<void> => {
    if (!companyId) {
      return;
    }
    try {
      await apiFetch("/organization/warehouses", {
        method: "POST",
        body: {
          company_id: companyId,
          branch_id: branchId || null,
          code,
          name,
          warehouse_type: warehouseType,
        },
      });
      notify({ type: "success", title: "Almacén creado", description: `${code} · ${name}` });
      setCode("");
      setName("");
      setBranchId("");
      void queryClient.invalidateQueries({ queryKey: ["organization", "warehouses"] });
    } catch (err) {
      const message = err instanceof Error ? err.message : "No fue posible crear el almacén";
      notify({ type: "error", title: "No fue posible crear el almacén", description: message });
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
        title="Almacenes"
        description="Almacenes de la empresa activa y sus ubicaciones."
        crumbs={[{ label: "Organización" }, { label: "Almacenes" }]}
      />

      {!companyId ? (
        <div className="rounded-md border border-warning-100 bg-warning-100/40 p-4 text-sm text-warning-600" role="alert">
          No hay una empresa activa. Vaya a <strong>Organización → Empresas</strong> y active la empresa para registrar almacenes.
        </div>
      ) : (
        <>
          <section className="mb-4 rounded-lg border border-border-default bg-surface-0 p-4">
            <h2 className="mb-2 text-base font-semibold text-text-900">Registrar almacén</h2>
            <form className="flex flex-wrap items-end gap-3" onSubmit={(e) => e.preventDefault()}>
              <FormField label="Código" required>
                <TextInput value={code} onChange={(e) => setCode(e.target.value)} placeholder="Ej. ALM-01" required />
              </FormField>
              <FormField label="Nombre" required>
                <TextInput value={name} onChange={(e) => setName(e.target.value)} placeholder="Nombre del almacén" required />
              </FormField>
              <FormField label="Tipo">
                <select
                  value={warehouseType}
                  onChange={(e) => setWarehouseType(e.target.value)}
                  className="h-10 w-40 rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900"
                >
                  {WAREHOUSE_TYPES.map((t) => (
                    <option key={t.value} value={t.value}>
                      {t.label}
                    </option>
                  ))}
                </select>
              </FormField>
              <FormField label="Sucursal">
                <select
                  value={branchId}
                  onChange={(e) => setBranchId(e.target.value)}
                  className="h-10 w-56 rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900"
                >
                  <option value="">Sin sucursal</option>
                  {(branches.data ?? []).map((b) => (
                    <option key={b.id} value={b.id}>
                      {b.code} · {b.name}
                    </option>
                  ))}
                </select>
              </FormField>
              <AsyncButton type="submit" variant="primary" onClick={createWarehouse}>
                Registrar
              </AsyncButton>
            </form>
          </section>

          <section className="rounded-lg border border-border-default bg-surface-0 p-4">
            <h2 className="mb-2 text-base font-semibold text-text-900">
              Almacenes de {activeCompany?.legal_name}
            </h2>
            <div>
              {warehouses.isLoading ? <p className="text-sm text-text-500">Cargando…</p> : null}
              {warehouses.isError ? (
                <p className="text-sm text-danger-600" role="alert">
                  No fue posible cargar los almacenes.
                </p>
              ) : null}
              {(warehouses.data ?? []).map((w) => row(w.id, `${w.code} · ${w.name} · ${w.warehouse_type}`, w.status))}
              {warehouses.isSuccess && (warehouses.data ?? []).length === 0 ? (
                <p className="text-sm text-text-500">Sin almacenes registrados.</p>
              ) : null}
            </div>
          </section>
        </>
      )}
    </PageContent>
  );
}
