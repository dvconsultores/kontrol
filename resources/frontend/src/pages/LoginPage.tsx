/** Login — inicio de sesión seguro (US-006, FR-001-020/021/023). */
import { useEffect, useState } from "react";
import { Navigate, useNavigate } from "react-router";

import { useAuth } from "@/app/contexts/AuthContext";
import { useNotifications } from "@/app/contexts/NotificationContext";
import { AsyncButton } from "@/components/AsyncButton";
import { Button } from "@/components/Button";
import { FormField } from "@/components/FormField";
import { TextInput } from "@/components/TextInput";
import { apiFetch } from "@/api/client";
import type { SetupStatus } from "@/api/types";

export function LoginPage(): React.JSX.Element {
  const { isAuthenticated, login } = useAuth();
  const { notify } = useNotifications();
  const navigate = useNavigate();

  const [tenantCode, setTenantCode] = useState("");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [needsSetup, setNeedsSetup] = useState(false);

  // En instalaciones nuevas, ofrecer el asistente de configuración desde el inicio.
  useEffect(() => {
    let cancelled = false;
    apiFetch<SetupStatus>("/setup/status")
      .then((status) => {
        if (!cancelled && !status.initialized) {
          setNeedsSetup(true);
        }
      })
      .catch(() => {
        // Sin red o backend no disponible: se reintentará tras un login fallido.
      });
    return () => {
      cancelled = true;
    };
  }, []);

  if (isAuthenticated) {
    return <Navigate to="/" replace />;
  }

  const handleSubmit = async (): Promise<void> => {
    setError(null);
    try {
      const data = await login(tenantCode, username, password);
      notify({ type: "success", title: "Sesión iniciada", description: `Bienvenido, ${data.user.username}` });
      if (data.must_change_password) {
        navigate("/cambiar-contrasena");
      } else {
        navigate("/");
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : "No fue posible iniciar sesión";
      setError(message);
      notify({ type: "error", title: "No fue posible iniciar sesión", description: message });
      // Si la instalación no está inicializada, ofrecer el asistente.
      try {
        const status = await apiFetch<SetupStatus>("/setup/status");
        if (!status.initialized) {
          setNeedsSetup(true);
        }
      } catch {
        // ignorar
      }
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-surface-50 px-4">
      <div className="w-full max-w-md rounded-lg border border-border-default bg-surface-0 p-8 shadow-sm">
        <h1 className="text-2xl font-semibold text-brand-700">KONTROL</h1>
        <p className="mt-1 text-sm text-text-500">Inicie sesión para continuar</p>

        <form
          className="mt-6 space-y-4"
          onSubmit={(e) => {
            e.preventDefault();
            void handleSubmit();
          }}
          noValidate
        >
          <FormField label="Empresa (código)" required htmlFor="tenant-code">
            <TextInput
              id="tenant-code"
              value={tenantCode}
              onChange={(e) => setTenantCode(e.target.value)}
              autoComplete="organization"
              required
            />
          </FormField>
          <FormField label="Usuario" required htmlFor="username">
            <TextInput
              id="username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              autoComplete="username"
              required
            />
          </FormField>
          <FormField label="Contraseña" required htmlFor="password" error={error ?? undefined}>
            <TextInput
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="current-password"
              required
              invalid={Boolean(error)}
            />
          </FormField>
          <AsyncButton type="submit" className="w-full" onClick={handleSubmit} loadingText="Iniciando sesión…">
            Iniciar sesión
          </AsyncButton>
        </form>

        {needsSetup ? (
          <div className="mt-4 rounded-md border border-warning-100 bg-warning-100/40 p-3 text-sm text-text-700">
            Esta instalación aún no ha sido inicializada.{" "}
            <Button variant="ghost" size="sm" onClick={() => navigate("/setup")} className="px-1 font-medium text-brand-700">
              Ir al asistente de configuración
            </Button>
          </div>
        ) : null}

        <div className="mt-4 text-center text-sm">
          <Button variant="ghost" size="sm" onClick={() => navigate("/reset-password")} className="font-medium text-brand-700">
            ¿Olvidó su contraseña?
          </Button>
        </div>
      </div>
    </div>
  );
}
