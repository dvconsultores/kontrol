/** Configuración central y sincronización de licencias (FR-010-001/002/003). */
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { apiFetch } from "@/api/client";
import type { CentralConfig, LicensingOverview } from "@/api/types";
import { useNotifications } from "@/app/contexts/NotificationContext";
import { Autorizado } from "@/components/Autorizado";
import { AsyncButton } from "@/components/AsyncButton";
import { ErrorState } from "@/components/ErrorState";
import { FormField } from "@/components/FormField";
import { LoadingState } from "@/components/LoadingState";
import { PageContent } from "@/layout/PageContent";
import { PageHeader } from "@/components/PageHeader";
import { TextInput } from "@/components/TextInput";

export function ConfiguracionCentralPage(): React.JSX.Element {
  const queryClient = useQueryClient();
  const { notify } = useNotifications();

  const overview = useQuery({
    queryKey: ["licensing", "overview"],
    queryFn: () => apiFetch<LicensingOverview>("/licensing/overview"),
    retry: false,
  });

  const [serverUrl, setServerUrl] = useState("");
  const [graceDays, setGraceDays] = useState("7");
  const [saving, setSaving] = useState(false);

  const config: CentralConfig | null = overview.data?.central_config ?? null;

  const saveConfig = async (): Promise<void> => {
    setSaving(true);
    try {
      await apiFetch("/licensing/central-config", {
        method: "PUT",
        body: {
          server_url: serverUrl || config?.server_url || "",
          grace_days: Number(graceDays) || 7,
          sync_policy: config?.sync_policy ?? { mode: "MANUAL" },
          enabled: true,
        },
      });
      notify({ type: "success", title: "Configuración guardada", description: "El servidor central quedó configurado." });
      await queryClient.invalidateQueries({ queryKey: ["licensing"] });
    } finally {
      setSaving(false);
    }
  };

  const runSync = async (): Promise<void> => {
    await apiFetch("/licensing/sync", { method: "POST" });
    notify({ type: "success", title: "Sincronización completa", description: "La licencia fue verificada contra el servidor central." });
    await queryClient.invalidateQueries({ queryKey: ["licensing"] });
  };

  if (overview.isLoading) {
    return <LoadingState rows={4} />;
  }
  if (overview.isError) {
    return (
      <PageContent maxWidth="md">
        <ErrorState message="No fue posible consultar el licenciamiento central." onRetry={() => void overview.refetch()} />
      </PageContent>
    );
  }

  const data = overview.data as LicensingOverview;
  const status = data.status;
  const offline = data.offline;

  return (
    <PageContent maxWidth="lg">
      <PageHeader
        title="Configuración central"
        description="Servidor central de licencias, sincronización y tolerancia offline."
        crumbs={[{ label: "Licenciamiento" }, { label: "Configuración central" }]}
      />

      <section className="rounded-lg border border-border-default bg-surface-0 p-6">
        <h2 className="text-base font-semibold text-text-900">Servidor central de licencias</h2>
        <p className="mt-1 text-sm text-text-500">
          El licenciamiento central verifica la licencia, sincroniza los entitlements por módulo y registra cada ejecución.
        </p>
        <div className="mt-4 grid gap-4 sm:grid-cols-2">
          <FormField label="URL del servidor central" className="sm:col-span-2">
            <TextInput
              value={serverUrl || (config?.server_url ?? "")}
              onChange={(e) => setServerUrl(e.target.value)}
              placeholder="https://central.kontrol.example"
            />
          </FormField>
          <FormField label="Gracia offline (días)">
            <TextInput
              value={graceDays || String(config?.grace_days ?? 7)}
              onChange={(e) => setGraceDays(e.target.value)}
              inputMode="numeric"
            />
          </FormField>
          <FormField label="Estado de conexión">
            <p className="mt-1 text-sm font-semibold text-text-900">
              {config?.status === "CONNECTED" ? "Conectado" : config ? "Desconectado" : "Sin configurar"}
            </p>
          </FormField>
        </div>
        <div className="mt-4 flex flex-wrap items-center gap-3">
          <Autorizado operacion={["PUT", "/licensing/central-config"]}>
            <AsyncButton onClick={saveConfig} loadingText="Guardando…" disabled={saving}>
              Guardar configuración
            </AsyncButton>
          </Autorizado>
          <Autorizado operacion={["POST", "/licensing/sync"]}>
            <AsyncButton onClick={runSync} variant="primary" loadingText="Sincronizando…">
              Sincronizar ahora
            </AsyncButton>
          </Autorizado>
        </div>
      </section>

      <section className="mt-6 grid gap-4 rounded-lg border border-border-default bg-surface-0 p-6 sm:grid-cols-3">
        <div>
          <p className="text-xs font-medium uppercase tracking-wide text-text-400">Modo</p>
          <p className="mt-1 text-sm font-semibold text-text-900">{status.mode.replaceAll("_", " ")}</p>
        </div>
        <div>
          <p className="text-xs font-medium uppercase tracking-wide text-text-400">Última sincronización</p>
          <p className="mt-1 text-sm text-text-900">
            {data.last_sync ? new Date(data.last_sync.ran_at).toLocaleString("es-VE") : "Nunca"}
          </p>
        </div>
        <div>
          <p className="text-xs font-medium uppercase tracking-wide text-text-400">Estado offline</p>
          <p className="mt-1 text-sm text-text-900">
            {offline.offline_valid ? `Válida (${offline.grace_days_left} días de gracia)` : "Gracia agotada"}
          </p>
        </div>
      </section>
    </PageContent>
  );
}
