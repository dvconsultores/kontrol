/** ResetPassword — recuperación de contraseña olvidada (US-006, FR-001-026).
 * Flujo en dos pasos: 1) solicitud con empresa + usuario, 2) confirmación con
 * el token entregado (en la fundación el token se devuelve en la respuesta;
 * en producción llega por correo seguro).
 */
import { useState } from "react";
import { useNavigate } from "react-router";

import { apiFetch } from "@/api/client";
import { useNotifications } from "@/app/contexts/NotificationContext";
import { AsyncButton } from "@/components/AsyncButton";
import { Button } from "@/components/Button";
import { FormField } from "@/components/FormField";
import { TextInput } from "@/components/TextInput";

interface ResetRequestResponse {
  ok: boolean;
  reset_token?: string;
}

export function ResetPasswordPage(): React.JSX.Element {
  const navigate = useNavigate();
  const { notify } = useNotifications();

  const [tenantCode, setTenantCode] = useState("");
  const [username, setUsername] = useState("");
  const [token, setToken] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [requested, setRequested] = useState(false);
  const [tokenHint, setTokenHint] = useState<string | null>(null);

  const handleRequest = async (): Promise<void> => {
    setError(null);
    try {
      const data = await apiFetch<ResetRequestResponse>("/auth/password-reset/request", {
        method: "POST",
        body: { tenant_code: tenantCode, username },
      });
      setRequested(true);
      if (data.reset_token) {
        setToken(data.reset_token);
        setTokenHint("Modo demostración: el token se muestra aquí. En producción se envía por correo seguro.");
      }
      notify({ type: "success", title: "Solicitud recibida", description: "Revise su correo para continuar." });
    } catch (err) {
      const message = err instanceof Error ? err.message : "No fue posible solicitar el restablecimiento";
      setError(message);
      notify({ type: "error", title: "No fue posible solicitar el restablecimiento", description: message });
    }
  };

  const handleConfirm = async (): Promise<void> => {
    setError(null);
    if (newPassword !== confirmPassword) {
      setError("Las contraseñas no coinciden");
      return;
    }
    try {
      await apiFetch("/auth/password-reset/confirm", {
        method: "POST",
        body: { token, new_password: newPassword },
      });
      notify({ type: "success", title: "Contraseña restablecida", description: "Ya puede iniciar sesión con su nueva contraseña." });
      navigate("/login");
    } catch (err) {
      const message = err instanceof Error ? err.message : "No fue posible restablecer la contraseña";
      setError(message);
      notify({ type: "error", title: "No fue posible restablecer la contraseña", description: message });
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-surface-50 px-4">
      <div className="w-full max-w-md rounded-lg border border-border-default bg-surface-0 p-8 shadow-sm">
        <h1 className="text-2xl font-semibold text-brand-700">KONTROL</h1>
        <p className="mt-1 text-sm text-text-500">
          {requested ? "Confirme su nueva contraseña" : "Recupere el acceso a su cuenta"}
        </p>

        {tokenHint ? (
          <div className="mt-4 rounded-md border border-info-100 bg-info-100/40 p-3 text-sm text-text-700">
            {tokenHint}
            <div className="mt-1 font-mono text-xs text-text-600">Token: {token}</div>
          </div>
        ) : null}

        {requested ? (
          <form
            className="mt-6 space-y-4"
            onSubmit={(e) => {
              e.preventDefault();
              void handleConfirm();
            }}
            noValidate
          >
            <FormField
              label="Nueva contraseña"
              required
              error={error ?? undefined}
              help="Mínimo 10 caracteres; mayúscula, minúscula y número."
            >
              <TextInput
                id="reset-password"
                type="password"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                autoComplete="new-password"
                required
                invalid={Boolean(error)}
              />
            </FormField>
            <FormField label="Confirmar nueva contraseña" required htmlFor="reset-password-confirm">
              <TextInput
                id="reset-password-confirm"
                type="password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                autoComplete="new-password"
                required
              />
            </FormField>
            <AsyncButton type="submit" className="w-full" onClick={handleConfirm} loadingText="Guardando…">
              Restablecer contraseña
            </AsyncButton>
          </form>
        ) : (
          <form
            className="mt-6 space-y-4"
            onSubmit={(e) => {
              e.preventDefault();
              void handleRequest();
            }}
            noValidate
          >
            <FormField label="Empresa (código)" required htmlFor="reset-tenant">
              <TextInput
                id="reset-tenant"
                value={tenantCode}
                onChange={(e) => setTenantCode(e.target.value)}
                autoComplete="organization"
                required
              />
            </FormField>
            <FormField label="Usuario" required htmlFor="reset-username">
              <TextInput
                id="reset-username"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                autoComplete="username"
                required
              />
            </FormField>
            <AsyncButton type="submit" className="w-full" onClick={handleRequest} loadingText="Enviando solicitud…">
              Solicitar restablecimiento
            </AsyncButton>
          </form>
        )}

        <div className="mt-4 text-center text-sm">
          <Button variant="ghost" size="sm" onClick={() => navigate("/login")} className="font-medium text-brand-700">
            Volver al inicio de sesión
          </Button>
        </div>
      </div>
    </div>
  );
}
