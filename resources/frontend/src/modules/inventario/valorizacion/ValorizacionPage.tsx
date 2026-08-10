/** Valorización y costos — valor total, capas y perfiles de costeo (FR-003-050/051, WF-08). */
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { createColumnHelper } from "@tanstack/react-table";
import { useState } from "react";

import { apiFetch } from "@/api/client";
import type { CostLayer, CostingProfile, ValuationResult } from "@/api/types";
import { useNotifications } from "@/app/contexts/NotificationContext";
import { AsyncButton } from "@/components/AsyncButton";
import { DataTable } from "@/components/DataTable";
import { FormField } from "@/components/FormField";
import { PageContent } from "@/layout/PageContent";
import { PageHeader } from "@/components/PageHeader";
import { TextInput } from "@/components/TextInput";

const layerHelper = createColumnHelper<CostLayer>();
const profileHelper = createColumnHelper<CostingProfile>();

export function ValorizacionPage(): React.JSX.Element {
  const queryClient = useQueryClient();
  const { notify } = useNotifications();

  const [profileCode, setProfileCode] = useState("");
  const [profileMethod, setProfileMethod] = useState<"AVERAGE" | "FIFO">("AVERAGE");
  const [profileCurrency, setProfileCurrency] = useState("VED");
  const [profileProduct, setProfileProduct] = useState("");

  const valuation = useQuery({
    queryKey: ["inventario", "valuation"],
    queryFn: () => apiFetch<ValuationResult>("/inventory/valuation"),
    retry: false,
  });
  const costLayers = useQuery({
    queryKey: ["inventario", "cost-layers"],
    queryFn: () => apiFetch<{ items: CostLayer[] }>("/inventory/cost-layers"),
    retry: false,
  });
  const profiles = useQuery({
    queryKey: ["inventario", "costing-profiles"],
    queryFn: () => apiFetch<{ items: CostingProfile[] }>("/inventory/costing-profiles"),
    retry: false,
  });

  const createProfile = async (): Promise<void> => {
    try {
      await apiFetch("/inventory/costing-profiles", {
        method: "POST",
        body: {
          code: profileCode, method: profileMethod, currency: profileCurrency,
          product_id: profileProduct || null, global_scope: false,
          effective_from: null, effective_to: null,
        },
      });
      notify({ type: "success", title: "Perfil creado", description: profileCode });
      setProfileCode(""); setProfileProduct("");
      void queryClient.invalidateQueries({ queryKey: ["inventario", "costing-profiles"] });
    } catch (err) {
      const message = err instanceof Error ? err.message : "No fue posible crear el perfil";
      notify({ type: "error", title: "No fue posible crear el perfil", description: message });
    }
  };

  const layerColumns = [
    layerHelper.accessor("product_id", { header: "Producto" }),
    layerHelper.accessor("warehouse_id", { header: "Almacén" }),
    layerHelper.accessor("quantity_remaining", { header: "Cant. restante" }),
    layerHelper.accessor("unit_cost", { header: "Costo unit." }),
    layerHelper.accessor("landed_cost", { header: "Costo aterrizado" }),
    layerHelper.accessor("status", { header: "Estado" }),
  ];

  const profileColumns = [
    profileHelper.accessor("code", { header: "Código" }),
    profileHelper.accessor("method", { header: "Método" }),
    profileHelper.accessor("currency", { header: "Moneda" }),
    profileHelper.accessor("product_id", { header: "Producto" }),
    profileHelper.accessor("version", { header: "Versión" }),
    profileHelper.accessor("status", { header: "Estado" }),
  ];

  return (
    <PageContent maxWidth="full">
      <PageHeader
        title="Valorización y costos"
        description="Valor total del inventario, capas de costo FIFO/AVG y perfiles de costeo."
        crumbs={[{ label: "Inventario" }, { label: "Valorización" }]}
      />
      <div className="mb-4 rounded-lg border border-border-default bg-surface-0 p-4">
        <p className="text-sm text-text-500">Valor total del inventario</p>
        <p className="text-2xl font-semibold text-text-900">
          {valuation.data ? `${valuation.data.valuation.toFixed(2)} ${valuation.data.currency}` : "—"}
        </p>
      </div>

      <section className="mb-4 rounded-lg border border-border-default bg-surface-0 p-4">
        <h2 className="mb-2 text-base font-semibold text-text-900">Nuevo perfil de costeo</h2>
        <form className="flex flex-wrap items-end gap-3" onSubmit={(e) => e.preventDefault()}>
          <FormField label="Código" required>
            <TextInput value={profileCode} onChange={(e) => setProfileCode(e.target.value)} placeholder="PERFIL-FIFO-1" required />
          </FormField>
          <FormField label="Método">
            <select value={profileMethod} onChange={(e) => setProfileMethod(e.target.value as "AVERAGE" | "FIFO")} className="h-10 w-44 rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900">
              <option value="AVERAGE">Promedio</option>
              <option value="FIFO">FIFO</option>
            </select>
          </FormField>
          <FormField label="Moneda">
            <select value={profileCurrency} onChange={(e) => setProfileCurrency(e.target.value)} className="h-10 w-36 rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900">
              <option value="VED">VED</option>
              <option value="USD">USD</option>
            </select>
          </FormField>
          <FormField label="Producto (global si vacío)">
            <TextInput value={profileProduct} onChange={(e) => setProfileProduct(e.target.value)} placeholder="ID producto" />
          </FormField>
          <AsyncButton type="submit" variant="primary" onClick={createProfile}>Crear perfil</AsyncButton>
        </form>
      </section>

      <h2 className="mb-2 text-base font-semibold text-text-900">Capas de costo</h2>
      <div className="mb-6">
        <DataTable
          columns={layerColumns}
          data={costLayers.data?.items ?? []}
          loading={costLayers.isLoading}
          error={costLayers.isError ? "No fue posible cargar las capas de costo." : null}
          getRowId={(row) => row.id}
          emptyTitle="Sin capas de costo"
          emptyDescription="No hay capas de costo registradas."
        />
      </div>

      <h2 className="mb-2 text-base font-semibold text-text-900">Perfiles de costeo</h2>
      <DataTable
        columns={profileColumns}
        data={profiles.data?.items ?? []}
        loading={profiles.isLoading}
        error={profiles.isError ? "No fue posible cargar los perfiles." : null}
        getRowId={(row) => row.id}
        emptyTitle="Sin perfiles de costeo"
        emptyDescription="Aún no hay perfiles de costeo."
      />
    </PageContent>
  );
}
