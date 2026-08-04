/** Vehículos y conductores (FR-008-004). */
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { apiFetch } from "@/api/client";
import type { Party, TransportDriverSummary, TransportVehicleSummary } from "@/api/types";
import { useNotifications } from "@/app/contexts/NotificationContext";
import { AsyncButton } from "@/components/AsyncButton";
import { FormField } from "@/components/FormField";
import { PageContent } from "@/layout/PageContent";
import { PageHeader } from "@/components/PageHeader";
import { TextInput } from "@/components/TextInput";

export function VehiculosPage(): React.JSX.Element {
  const queryClient = useQueryClient();
  const { notify } = useNotifications();

  const [plate, setPlate] = useState("");
  const [vehicleType, setVehicleType] = useState("CAMION");
  const [partyId, setPartyId] = useState("");
  const [license, setLicense] = useState("");

  const vehicles = useQuery({
    queryKey: ["regulatorio", "vehicles"],
    queryFn: () => apiFetch<{ items: TransportVehicleSummary[] }>("/regulatory/vehicles"),
    retry: false,
  });
  const drivers = useQuery({
    queryKey: ["regulatorio", "drivers"],
    queryFn: () => apiFetch<{ items: TransportDriverSummary[] }>("/regulatory/drivers"),
    retry: false,
  });
  const parties = useQuery({
    queryKey: ["maestros", "terceros"],
    queryFn: () => apiFetch<{ items: Party[] }>("/maestros/terceros"),
    retry: false,
  });

  const refresh = (): void => {
    void queryClient.invalidateQueries({ queryKey: ["regulatorio"] });
  };

  const createVehicle = async (): Promise<void> => {
    await apiFetch("/regulatory/vehicles", { method: "POST", body: { plate, vehicle_type: vehicleType } });
    notify({ type: "success", title: "Vehículo registrado", description: plate });
    setPlate("");
    refresh();
  };

  const createDriver = async (): Promise<void> => {
    if (!partyId) return;
    await apiFetch("/regulatory/drivers", { method: "POST", body: { party_id: partyId, license: license || null } });
    notify({ type: "success", title: "Conductor registrado", description: `Licencia ${license || "—"}` });
    setLicense("");
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
        title="Vehículos y conductores"
        description="Registro de transporte y conductores para traslados regulados (FR-008-004)."
        crumbs={[{ label: "Regulatorio" }, { label: "Vehículos" }]}
      />

      {section("Registrar vehículo", (
        <form className="flex flex-wrap items-end gap-3" onSubmit={(e) => e.preventDefault()}>
          <FormField label="Placa">
            <TextInput value={plate} onChange={(e) => setPlate(e.target.value)} placeholder="Ej. ABC123" />
          </FormField>
          <FormField label="Tipo">
            <select value={vehicleType} onChange={(e) => setVehicleType(e.target.value)} className="h-10 w-40 rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900">
              <option value="CAMION">Camión</option>
              <option value="CAMIONETA">Camioneta</option>
              <option value="FURGON">Furgón</option>
              <option value="MOTO">Moto</option>
            </select>
          </FormField>
          <AsyncButton type="submit" variant="secondary" onClick={createVehicle}>Registrar</AsyncButton>
        </form>
      ))}

      {section("Vehículos", (
        <div>
          {(vehicles.data?.items ?? []).map((v) => row(v.id, `${v.plate} · ${v.vehicle_type ?? ""}`, v.status))}
          {(vehicles.data?.items ?? []).length === 0 ? <p className="text-sm text-text-500">Sin vehículos.</p> : null}
        </div>
      ))}

      {section("Registrar conductor", (
        <form className="flex flex-wrap items-end gap-3" onSubmit={(e) => e.preventDefault()}>
          <FormField label="Conductor">
            <select value={partyId} onChange={(e) => setPartyId(e.target.value)} className="h-10 w-56 rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900">
              <option value="">Seleccionar…</option>
              {(parties.data?.items ?? []).map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
            </select>
          </FormField>
          <FormField label="Licencia">
            <TextInput value={license} onChange={(e) => setLicense(e.target.value)} placeholder="Opcional" />
          </FormField>
          <AsyncButton type="submit" variant="secondary" onClick={createDriver}>Registrar</AsyncButton>
        </form>
      ))}

      {section("Conductores", (
        <div>
          {(drivers.data?.items ?? []).map((d) => row(d.id, `Conductor · licencia ${d.license ?? "—"}`, d.status))}
          {(drivers.data?.items ?? []).length === 0 ? <p className="text-sm text-text-500">Sin conductores.</p> : null}
        </div>
      ))}
    </PageContent>
  );
}
