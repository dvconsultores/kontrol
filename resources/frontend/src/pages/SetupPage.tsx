/** Setup — asistente seguro de inicialización (US-004, FR-001-010). */
import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { apiFetch } from "@/api/client";
import { useNotifications } from "@/app/contexts/NotificationContext";
import { AsyncButton } from "@/components/AsyncButton";
import { FormField } from "@/components/FormField";
import { PageContent } from "@/layout/PageContent";
import { PageHeader } from "@/components/PageHeader";
import { TextInput } from "@/components/TextInput";

export function SetupPage(): React.JSX.Element {
  const navigate = useNavigate();
  const { notify } = useNotifications();

  const [tenantCode, setTenantCode] = useState("");
  const [tenantName, setTenantName] = useState("");
  const [companyCode, setCompanyCode] = useState("");
  const [companyLegalName, setCompanyLegalName] = useState("");
  const [companyRif, setCompanyRif] = useState("");
  const [adminUsername, setAdminUsername] = useState("");
  const [adminPassword, setAdminPassword] = useState("");
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (): Promise<void> => {
    setError(null);
    try {
      await apiFetch("/setup/initialize", {
        method: "POST",
        body: {
          tenant_code: tenantCode,
          tenant_name: tenantName,
          company_code: companyCode,
          company_legal_name: companyLegalName,
          company_rif: companyRif,
          admin_username: adminUsername,
          admin_password: adminPassword,
        },
      });
      notify({
        type: "success",
        title: "Instalación inicializada",
        description: "La empresa y el administrador se crearon correctamente. Inicie sesión.",
      });
      navigate("/login");
    } catch (err) {
      const message = err instanceof Error ? err.message : "No fue posible inicializar la instalación";
      setError(message);
      notify({ type: "error", title: "No fue posible inicializar", description: message });
    }
  };

  return (
    <div className="flex min-h-screen items-start justify-center bg-surface-50 py-10">
      <PageContent maxWidth="md">
        <PageHeader
          title="Configuración inicial"
          description="Cree la empresa y el administrador de esta instalación. No existen credenciales fijas."
          crumbs={[{ label: "Configuración inicial" }]}
        />
        <form
          className="space-y-4 rounded-lg border border-border-default bg-surface-0 p-6"
          onSubmit={(e) => {
            e.preventDefault();
            void handleSubmit();
          }}
          noValidate
        >
          <fieldset>
            <legend className="text-sm font-semibold text-text-700">Tenant (instalación)</legend>
            <div className="mt-3 grid gap-4 sm:grid-cols-2">
              <FormField label="Código" required>
                <TextInput value={tenantCode} onChange={(e) => setTenantCode(e.target.value)} required />
              </FormField>
              <FormField label="Nombre" required>
                <TextInput value={tenantName} onChange={(e) => setTenantName(e.target.value)} required />
              </FormField>
            </div>
          </fieldset>

          <fieldset>
            <legend className="text-sm font-semibold text-text-700">Empresa inicial</legend>
            <div className="mt-3 grid gap-4 sm:grid-cols-2">
              <FormField label="Código" required>
                <TextInput value={companyCode} onChange={(e) => setCompanyCode(e.target.value)} required />
              </FormField>
              <FormField label="Razón social" required>
                <TextInput value={companyLegalName} onChange={(e) => setCompanyLegalName(e.target.value)} required />
              </FormField>
              <FormField label="RIF" required help="Identificador se trata como texto.">
                <TextInput value={companyRif} onChange={(e) => setCompanyRif(e.target.value)} required />
              </FormField>
            </div>
          </fieldset>

          <fieldset>
            <legend className="text-sm font-semibold text-text-700">Administrador</legend>
            <div className="mt-3 grid gap-4 sm:grid-cols-2">
              <FormField label="Usuario" required>
                <TextInput value={adminUsername} onChange={(e) => setAdminUsername(e.target.value)} required />
              </FormField>
              <FormField
                label="Contraseña"
                required
                help="Mínimo 10 caracteres; mayúscula, minúscula y número. Deberá cambiarla en el primer acceso."
                error={error ?? undefined}
              >
                <TextInput
                  type="password"
                  value={adminPassword}
                  onChange={(e) => setAdminPassword(e.target.value)}
                  required
                  invalid={Boolean(error)}
                />
              </FormField>
            </div>
          </fieldset>

          <AsyncButton type="submit" onClick={handleSubmit} loadingText="Inicializando…" className="mt-2">
            Inicializar instalación
          </AsyncButton>
        </form>
      </PageContent>
    </div>
  );
}
