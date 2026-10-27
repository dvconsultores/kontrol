/**
 * MiLicencia — estado de la licencia, ruta completa (FR-001-054, DOC-07 §13.1).
 * La ve quien tiene `license:view` (FR-010-113): el backend es la autoridad —`GET /license/detail`
 * responde 401/403—; aquí se decide antes de pedir nada, para no pintar ni solicitar el detalle
 * a quien no puede verlo.
 */
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

import { apiFetch } from "@/api/client";
import type { LicenseStatus } from "@/api/types";
import { useAutoridad } from "@/app/autoridad/AutoridadContext";
import { PERMISO_DE_LICENCIA } from "@/app/contexts/LicenseContext";
import { useNotifications } from "@/app/contexts/NotificationContext";
import { AsyncButton } from "@/components/AsyncButton";
import { ErrorState } from "@/components/ErrorState";
import { ForbiddenState } from "@/components/ForbiddenState";
import { FormField } from "@/components/FormField";
import { LoadingState } from "@/components/LoadingState";
import { PageContent } from "@/layout/PageContent";
import { PageHeader } from "@/components/PageHeader";
import { TextInput } from "@/components/TextInput";

export function MiLicenciaPage(): React.JSX.Element {
  const { notify } = useNotifications();
  const { tiene } = useAutoridad();
  const [proofRef, setProofRef] = useState("");

  const permitido = tiene(PERMISO_DE_LICENCIA, "global");
  const query = useQuery({
    queryKey: ["license", "detail"],
    queryFn: () => apiFetch<LicenseStatus>("/license/detail"),
    retry: false,
    enabled: permitido,
  });

  const submitProof = async (): Promise<void> => {
    await apiFetch("/license/renewal-request", {
      method: "POST",
      body: { payment_proof_ref: proofRef },
    });
    notify({
      type: "success",
      title: "Comprobante registrado",
      description: "Su comprobante de renovación fue enviado para revisión.",
    });
    setProofRef("");
    await query.refetch();
  };

  if (!permitido) {
    return <ForbiddenState />;
  }
  if (query.isLoading) {
    return <LoadingState rows={4} />;
  }
  if (query.isError) {
    return (
      <PageContent maxWidth="md">
        <ErrorState message="No fue posible consultar el estado de la licencia." onRetry={() => void query.refetch()} />
      </PageContent>
    );
  }
  const license = query.data as LicenseStatus;

  return (
    <PageContent maxWidth="lg">
      <PageHeader
        title="Mi licencia"
        description="Estado de la licencia anual de esta instalación."
        crumbs={[{ label: "Mi licencia" }]}
      />

      <div className="grid gap-4 rounded-lg border border-border-default bg-surface-0 p-6 sm:grid-cols-2">
        <div>
          <p className="text-xs font-medium uppercase tracking-wide text-text-400">Instalación</p>
          <p className="mt-1 font-mono text-sm text-text-900">{license.installation_id}</p>
        </div>
        <div>
          <p className="text-xs font-medium uppercase tracking-wide text-text-400">Modo</p>
          <p className="mt-1 text-sm font-semibold text-text-900">
            {license.mode.replaceAll("_", " ")}
          </p>
        </div>
        <div>
          <p className="text-xs font-medium uppercase tracking-wide text-text-400">Período pagado</p>
          <p className="mt-1 text-sm text-text-900">
            {license.period_start ? new Date(license.period_start).toLocaleDateString("es-VE") : "—"}
            {" a "}
            {license.period_end ? new Date(license.period_end).toLocaleDateString("es-VE") : "—"}
          </p>
        </div>
        <div>
          <p className="text-xs font-medium uppercase tracking-wide text-text-400">Modo solo consulta desde</p>
          <p className="mt-1 text-sm text-text-900">
            {license.read_only_start ? new Date(license.read_only_start).toLocaleDateString("es-VE") : "—"}
          </p>
        </div>
      </div>

      <section className="mt-6 rounded-lg border border-border-default bg-surface-0 p-6">
        <h2 className="text-base font-semibold text-text-900">Renovación anual</h2>
        <p className="mt-1 text-sm text-text-500">
          Realice el pago y registre el comprobante. La renovación se confirma únicamente por el propietario de KONTROL.
        </p>
        <div className="mt-4 flex flex-wrap items-end gap-3">
          <FormField label="Referencia del comprobante" className="min-w-64 flex-1">
            <TextInput
              value={proofRef}
              onChange={(e) => setProofRef(e.target.value)}
              placeholder="Banco, fecha y referencia"
            />
          </FormField>
          <AsyncButton onClick={submitProof} loadingText="Registrando…">
            Cargar comprobante
          </AsyncButton>
        </div>
      </section>
    </PageContent>
  );
}
