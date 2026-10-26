/** ResetPassword — recuperación de contraseña olvidada (US-006, FR-001-026).
 * Flujo en tres pasos: solicitud, código entregado por soporte y confirmación.
 */
import { useState } from "react";
import { useNavigate } from "react-router";

import { apiFetch, ApiError } from "@/api/client";
import { AsyncButton } from "@/components/AsyncButton";
import { Button } from "@/components/Button";
import { FormField } from "@/components/FormField";
import { TextInput } from "@/components/TextInput";

type Paso = "solicitar" | "codigo" | "hecho";

interface ResetRequestResponse {
  ok: boolean;
}

export function ResetPasswordPage(): React.JSX.Element {
  const navigate = useNavigate();

  const [paso, setPaso] = useState<Paso>("solicitar");
  const [tenantCode, setTenantCode] = useState("");
  const [username, setUsername] = useState("");
  const [token, setToken] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");

  const [tenantError, setTenantError] = useState<string | null>(null);
  const [usernameError, setUsernameError] = useState<string | null>(null);
  const [requestError, setRequestError] = useState<string | null>(null);
  const [solicitado, setSolicitado] = useState(false);
  const [tokenError, setTokenError] = useState<string | null>(null);
  const [passwordError, setPasswordError] = useState<string | null>(null);
  const [confirmError, setConfirmError] = useState<string | null>(null);

  const resetErrors = (): void => {
    setTenantError(null);
    setUsernameError(null);
    setRequestError(null);
    setTokenError(null);
    setPasswordError(null);
    setConfirmError(null);
  };

  const handleRequest = async (): Promise<void> => {
    resetErrors();
    setSolicitado(false);

    let hasLocalError = false;
    if (!tenantCode.trim()) {
      setTenantError("Indique la empresa");
      hasLocalError = true;
    }
    if (!username.trim()) {
      setUsernameError("Indique el usuario");
      hasLocalError = true;
    }
    if (hasLocalError) return;

    try {
      await apiFetch<ResetRequestResponse>("/auth/password-reset/request", {
        method: "POST",
        body: { tenant_code: tenantCode, username },
      });
      setSolicitado(true);
    } catch (err) {
      if (err instanceof TypeError) {
        setRequestError("Sin conexión. Inténtelo de nuevo.");
      } else if (err instanceof Error) {
        setRequestError(err.message);
      } else {
        setRequestError("No fue posible solicitar el restablecimiento");
      }
    }
  };

  const irAlPasoCodigo = (): void => {
    resetErrors();
    setSolicitado(false);
    setPaso("codigo");
  };

  const handleConfirm = async (): Promise<void> => {
    resetErrors();

    if (!token.trim()) {
      setTokenError("Indique el código");
      return;
    }

    if (newPassword !== confirmPassword) {
      setConfirmError("Las contraseñas no coinciden");
      return;
    }

    try {
      await apiFetch("/auth/password-reset/confirm", {
        method: "POST",
        body: { token, new_password: newPassword },
      });
      setToken("");
      setNewPassword("");
      setConfirmPassword("");
      setPaso("hecho");
    } catch (err) {
      if (err instanceof TypeError) {
        setTokenError("Sin conexión. Inténtelo de nuevo.");
        return;
      }

      if (err instanceof ApiError) {
        if (err.code === "RESET_TOKEN_INVALID") {
          setTokenError("El código no es válido. Compruébelo o pida uno nuevo al soporte.");
          return;
        }
        if (err.code === "RESET_TOKEN_EXPIRED") {
          setTokenError("El código caducó (dura 15 minutos). Pida uno nuevo al soporte.");
          setToken("");
          return;
        }
        if (err.code === "RESET_TOKEN_USED") {
          setTokenError("Ese código ya se usó o fue reemplazado por otro más reciente. Pida uno nuevo al soporte.");
          setToken("");
          return;
        }
        if (err.code === "PASSWORD_POLICY") {
          const fieldErrors = err.fieldErrors.new_password ?? [];
          if (fieldErrors.length > 0) {
            setPasswordError(fieldErrors.join(" "));
          } else if (err.message) {
            setPasswordError(err.message);
          } else {
            setPasswordError("La contraseña no cumple la política de seguridad.");
          }
          return;
        }
      }

      const message = err instanceof Error ? err.message : "No fue posible restablecer la contraseña";
      setTokenError(message);
    }
  };

  const subtitle: Record<Paso, string> = {
    solicitar: "Recupere el acceso a su cuenta",
    codigo: "Use el código que le dio el soporte",
    hecho: "Contraseña actualizada",
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-surface-50 px-4">
      <div className="w-full max-w-md rounded-lg border border-border-default bg-surface-0 p-8 shadow-sm">
        <h1 className="text-2xl font-semibold text-brand-700">KONTROL</h1>
        <p className="mt-1 text-sm text-text-500">{subtitle[paso]}</p>

        {paso === "solicitar" ? (
          <>
            {requestError ? (
              <div role="alert" className="mt-4 rounded-md border border-error-100 bg-error-100/40 p-3 text-sm text-text-700">
                {requestError}
              </div>
            ) : null}

            {solicitado ? (
              <div
                role="status"
                className="mt-4 rounded-md border border-info-100 bg-info-100/40 p-3 text-sm text-text-700"
              >
                Si la cuenta puede recuperarse, el soporte de su organización le dará un código de recuperación. Cuando lo
                tenga, pulse «Tengo un código».
              </div>
            ) : null}

            <form
              className="mt-6 space-y-4"
              onSubmit={(e) => {
                e.preventDefault();
                void handleRequest();
              }}
              noValidate
            >
              <FormField
                label="Empresa (código)"
                required
                htmlFor="reset-tenant"
                error={tenantError ?? undefined}
              >
                <TextInput
                  id="reset-tenant"
                  value={tenantCode}
                  onChange={(e) => setTenantCode(e.target.value)}
                  autoComplete="organization"
                  required
                  invalid={Boolean(tenantError)}
                />
              </FormField>
              <FormField label="Usuario" required htmlFor="reset-username" error={usernameError ?? undefined}>
                <TextInput
                  id="reset-username"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  autoComplete="username"
                  required
                  invalid={Boolean(usernameError)}
                />
              </FormField>
              <AsyncButton type="submit" className="w-full" onClick={handleRequest} loadingText="Enviando…">
                Solicitar recuperación
              </AsyncButton>
            </form>

            <div className="mt-4 text-center">
              <Button variant="ghost" size="sm" onClick={irAlPasoCodigo} className="font-medium text-brand-700">
                Tengo un código
              </Button>
            </div>
          </>
        ) : null}

        {paso === "codigo" ? (
          <form
            className="mt-6 space-y-4"
            onSubmit={(e) => {
              e.preventDefault();
              void handleConfirm();
            }}
            noValidate
          >
            <FormField
              label="Código de recuperación de contraseña"
              required
              htmlFor="reset-code"
              error={tokenError ?? undefined}
              help="Se lo entrega el soporte; caduca a los 15 minutos y sirve una sola vez."
            >
              <TextInput
                id="reset-code"
                value={token}
                onChange={(e) => setToken(e.target.value)}
                autoComplete="off"
                spellCheck={false}
                maxLength={64}
                required
                invalid={Boolean(tokenError)}
              />
            </FormField>
            <FormField
              label="Nueva contraseña"
              required
              htmlFor="reset-password"
              error={passwordError ?? undefined}
              help="Mínimo 10 caracteres; mayúscula, minúscula y número."
            >
              <TextInput
                id="reset-password"
                type="password"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                autoComplete="new-password"
                required
                invalid={Boolean(passwordError)}
              />
            </FormField>
            <FormField
              label="Confirmar nueva contraseña"
              required
              htmlFor="reset-password-confirm"
              error={confirmError ?? undefined}
            >
              <TextInput
                id="reset-password-confirm"
                type="password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                autoComplete="new-password"
                required
                invalid={Boolean(confirmError)}
              />
            </FormField>
            <AsyncButton type="submit" className="w-full" onClick={handleConfirm} loadingText="Guardando…">
              Restablecer contraseña
            </AsyncButton>

            <div className="mt-4 text-center">
              <Button variant="ghost" size="sm" onClick={() => setPaso("solicitar")} className="font-medium text-brand-700">
                Volver a solicitar
              </Button>
            </div>
          </form>
        ) : null}

        {paso === "hecho" ? (
          <>
            <div role="status" className="mt-6 rounded-md border border-success-100 bg-success-100/40 p-3 text-sm text-text-700">
              Por seguridad se cerraron todas sus sesiones. Inicie sesión con la nueva contraseña; si usa verificación en
              dos pasos, se la pediremos igual.
            </div>
            <Button className="mt-6 w-full" onClick={() => navigate("/login")}>
              Ir al inicio de sesión
            </Button>
          </>
        ) : null}

        <div className="mt-4 text-center text-sm">
          <Button variant="ghost" size="sm" onClick={() => navigate("/login")} className="font-medium text-brand-700">
            Volver al inicio de sesión
          </Button>
        </div>
      </div>
    </div>
  );
}
