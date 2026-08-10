/** Ubicaciones — ubicaciones dentro de almacenes (FR-016/019). */
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

interface WarehouseOption {
  id: string;
  code: string;
  name: string;
}

interface LocationSummary {
  id: string;
  warehouse_id: string;
  code: string;
  zone: string | null;
  aisle: string | null;
  rack: string | null;
  status: string;
}

export function UbicacionesPage(): React.JSX.Element {
  const { activeCompany } = useCompany();
  const queryClient = useQueryClient();
  const { notify } = useNotifications();

  const [warehouseId, setWarehouseId] = useState("");
  const [code, setCode] = useState("");
  const [zone, setZone] = useState("");
  const [aisle, setAisle] = useState("");
  const [rack, setRack] = useState("");

  const companyId = activeCompany?.id ?? null;

  const warehouses = useQuery({
    queryKey: ["organization", "warehouses", companyId],
    queryFn: () => apiFetch<WarehouseOption[]>(`/organization/warehouses?company_id=${encodeURIComponent(companyId ?? "")}`),
    enabled: Boolean(companyId),
    retry: false,
  });
  const locations = useQuery({
    queryKey: ["organization", "locations", warehouseId],
    queryFn: () => apiFetch<LocationSummary[]>(`/organization/locations?warehouse_id=${encodeURIComponent(warehouseId)}`),
    enabled: Boolean(companyId),
    retry: false,
  });

  const createLocation = async (): Promise<void> => {
    if (!warehouseId) {
      notify({ type: "warning", title: "Falta almacén", description: "Seleccione el almacén de la ubicación." });
      return;
    }
    try {
      await apiFetch("/organization/locations", {
        method: "POST",
        body: { warehouse_id: warehouseId, code, zone: zone || null, aisle: aisle || null, rack: rack || null },
      });
      notify({ type: "success", title: "Ubicación creada", description: code });
      setCode("");
      setZone("");
      setAisle("");
      setRack("");
      void queryClient.invalidateQueries({ queryKey: ["organization", "locations"] });
    } catch (err) {
      const message = err instanceof Error ? err.message : "No fue posible crear la ubicación";
      notify({ type: "error", title: "No fue posible crear la ubicación", description: message });
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
        title="Ubicaciones"
        description="Ubicaciones dentro de los almacenes de la empresa activa."
        crumbs={[{ label: "Organización" }, { label: "Ubicaciones" }]}
      />

      {!companyId ? (
        <div className="rounded-md border border-warning-100 bg-warning-100/40 p-4 text-sm text-warning-600" role="alert">
          No hay una empresa activa. Vaya a <strong>Organización → Empresas</strong> y active la empresa para registrar ubicaciones.
        </div>
      ) : (
        <>
          <section className="mb-4 rounded-lg border border-border-default bg-surface-0 p-4">
            <h2 className="mb-2 text-base font-semibold text-text-900">Registrar ubicación</h2>
            <form className="flex flex-wrap items-end gap-3" onSubmit={(e) => e.preventDefault()}>
              <FormField label="Almacén" required>
                <select
                  value={warehouseId}
                  onChange={(e) => setWarehouseId(e.target.value)}
                  className="h-10 w-56 rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900"
                >
                  <option value="">Seleccionar…</option>
                  {(warehouses.data ?? []).map((w) => (
                    <option key={w.id} value={w.id}>
                      {w.code} · {w.name}
                    </option>
                  ))}
                </select>
              </FormField>
              <FormField label="Código" required>
                <TextInput value={code} onChange={(e) => setCode(e.target.value)} placeholder="Ej. A-01-02-03" required />
              </FormField>
              <FormField label="Zona">
                <TextInput value={zone} onChange={(e) => setZone(e.target.value)} placeholder="Opcional" />
              </FormField>
              <FormField label="Pasillo">
                <TextInput value={aisle} onChange={(e) => setAisle(e.target.value)} placeholder="Opcional" />
              </FormField>
              <FormField label="Estante">
                <TextInput value={rack} onChange={(e) => setRack(e.target.value)} placeholder="Opcional" />
              </FormField>
              <AsyncButton type="submit" variant="primary" onClick={createLocation}>
                Registrar
              </AsyncButton>
            </form>
          </section>

          <section className="rounded-lg border border-border-default bg-surface-0 p-4">
            <h2 className="mb-2 text-base font-semibold text-text-900">Ubicaciones de {activeCompany?.legal_name}</h2>
            <div>
              {locations.isLoading ? <p className="text-sm text-text-500">Cargando…</p> : null}
              {locations.isError ? (
                <p className="text-sm text-danger-600" role="alert">
                  No fue posible cargar las ubicaciones.
                </p>
              ) : null}
              {(locations.data ?? []).map((l) =>
                row(l.id, `${l.code} · ${l.zone ?? ""} ${l.aisle ?? ""} ${l.rack ?? ""}`.trim(), l.status),
              )}
              {locations.isSuccess && (locations.data ?? []).length === 0 ? (
                <p className="text-sm text-text-500">Sin ubicaciones registradas.</p>
              ) : null}
            </div>
          </section>
        </>
      )}
    </PageContent>
  );
}
