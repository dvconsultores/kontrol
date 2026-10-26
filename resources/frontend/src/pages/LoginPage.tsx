/** Login — inicio de sesión seguro (US-006, FR-001-020/021/023). */
import { useEffect, useRef, useState } from "react";
import { Navigate, useNavigate } from "react-router";

import { useAuth } from "@/app/contexts/AuthContext";
import { useNotifications } from "@/app/contexts/NotificationContext";
import { AsyncButton } from "@/components/AsyncButton";
import { Button } from "@/components/Button";
import { FormField } from "@/components/FormField";
import { TextInput } from "@/components/TextInput";
import { ApiError, apiFetch } from "@/api/client";
import { verifyMfa } from "@/api/mfa";
import type { LoginResponse, SetupStatus } from "@/api/types";

type MfaMethod = "totp" | "recovery";

export function LoginPage(): React.JSX.Element {
  const { isAuthenticated, login, completeLogin } = useAuth();
  const { notify } = useNotifications();
  const navigate = useNavigate();

  const [tenantCode, setTenantCode] = useState("");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [needsSetup, setNeedsSetup] = useState(false);

  const [mfaStep, setMfaStep] = useState<"credentials" | "verify">("credentials");
  const [challengeToken, setChallengeToken] = useState<string | null>(null);
  const [mfaMethod, setMfaMethod] = useState<MfaMethod>("totp");
  const [mfaCode, setMfaCode] = useState("");
  const [mfaError, setMfaError] = useState<string | null>(null);
  const mfaCodeRef = useRef<HTMLInputElement>(null);

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

  useEffect(() => {
    if (mfaStep === "verify") {
      mfaCodeRef.current?.focus();
    }
  }, [mfaStep, mfaMethod]);

  if (isAuthenticated) {
    return <Navigate to="/" replace />;
  }

  const handleLoginSuccess = (data: LoginResponse): void => {
    if (data.status !== "AUTHENTICATED") {
      return;
    }
    if (data.recovery_codes_remaining !== null && data.recovery_codes_remaining !== undefined) {
      const remaining = data.recovery_codes_remaining;
      if (remaining >= 0 && remaining <= 3) {
        notify({
          type: "warning",
          title: "Códigos de recuperación",
          description: `Le quedan ${remaining} códigos de recuperación: genere otros en Mi seguridad.`,
        });
      }
    }
    notify({ type: "success", title: "Sesión iniciada", description: `Bienvenido, ${data.user.username}` });
    if (data.must_change_password) {
      navigate("/cambiar-contrasena");
    } else {
      navigate("/");
    }
  };

  const resetMfaChallenge = (): void => {
    setMfaStep("credentials");
    setChallengeToken(null);
    setMfaMethod("totp");
    setMfaCode("");
    setMfaError(null);
    setPassword("");
  };

  const handleSubmit = async (): Promise<void> => {
    setError(null);
    try {
      const data = await login(tenantCode, username, password);
      if (data.status === "AUTHENTICATED") {
        handleLoginSuccess(data);
      } else if (data.status === "MFA_ENROLLMENT_REQUIRED") {
        navigate("/acceso/mfa/alta", {
          state: {
            challengeToken: data.challenge_token,
            tenantCode,
            username,
          },
        });
      } else if (data.status === "MFA_REQUIRED") {
        setChallengeToken(data.challenge_token);
        setMfaStep("verify");
        setMfaError(null);
        setMfaCode("");
        setMfaMethod(data.methods.includes("RECOVERY_CODE") && !data.methods.includes("TOTP") ? "recovery" : "totp");
      }
    } catch (err) {
      const message =
        err instanceof TypeError
          ? "Sin conexión. Inténtelo de nuevo."
          : err instanceof ApiError
            ? err.message
            : "No fue posible iniciar sesión";
      setError(message);
      notify({ type: "error", title: "No fue posible iniciar sesión", description: message });
    }
  };

  const validateMfaCode = (): string | null => {
    if (mfaMethod === "totp") {
      const digits = mfaCode.replace(/\s/g, "");
      return /^\d{6}$/.test(digits) ? null : "Introduzca los 6 dígitos del código";
    }
    return /^[A-Za-z2-7]{4}(-?[A-Za-z2-7]{4}){3}$/.test(mfaCode.trim())
      ? null
      : "Formato: XXXX-XXXX-XXXX-XXXX";
  };

  const getMfaErrorMessage = (err: unknown): string => {
    if (err instanceof TypeError) {
      return "Sin conexión. Inténtelo de nuevo.";
    }
    if (err instanceof ApiError) {
      if (err.code === "MFA_INVALID_CODE") {
        if (typeof err.details?.attempts_remaining === "number") {
          return `Código incorrecto. Le quedan ${err.details.attempts_remaining} intentos.`;
        }
        return "Código incorrecto.";
      }
      if (err.code === "MFA_CODE_ALREADY_USED") {
        return "Ese código ya se usó. Espere al siguiente código de su aplicación.";
      }
      if (err.code === "MFA_UNAVAILABLE") {
        return "El segundo factor no está disponible. Contacte con el administrador.";
      }
    }
    return "No fue posible verificar el código";
  };

  const handleVerifyMfa = async (): Promise<void> => {
    const validationError = validateMfaCode();
    if (validationError) {
      setMfaError(validationError);
      return;
    }
    if (!challengeToken) {
      resetMfaChallenge();
      setError("La verificación caducó. Inicie sesión de nuevo.");
      return;
    }
    setMfaError(null);
    try {
      const secret = mfaMethod === "totp" ? { code: mfaCode.replace(/\s/g, "") } : { recoveryCode: mfaCode.trim() };
      const data = await verifyMfa(challengeToken, secret);
      if (data.status === "AUTHENTICATED") {
        completeLogin(data);
        handleLoginSuccess(data);
      }
    } catch (err) {
      if (err instanceof ApiError && err.code === "MFA_CHALLENGE_INVALID") {
        resetMfaChallenge();
        setError("La verificación caducó. Inicie sesión de nuevo.");
        return;
      }
      if (err instanceof ApiError && err.code === "AUTH_ACCOUNT_LOCKED") {
        resetMfaChallenge();
        setError("Cuenta bloqueada temporalmente por intentos fallidos.");
        return;
      }
      setMfaError(getMfaErrorMessage(err));
    }
  };

  const handleBackToCredentials = (): void => {
    resetMfaChallenge();
    setError(null);
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-surface-50 px-4">
      <div className="w-full max-w-md rounded-lg border border-border-default bg-surface-0 p-8 shadow-sm">
        <h1 className="text-2xl font-semibold text-brand-700">KONTROL</h1>
        {mfaStep === "credentials" ? (
          <>
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
          </>
        ) : (
          <>
            <h2 className="mt-1 text-xl font-semibold text-text-900">Verificación en dos pasos</h2>
            <p className="mt-1 text-sm text-text-500">
              {mfaMethod === "totp"
                ? "Escriba el código de 6 dígitos de su aplicación de autenticación"
                : "Escriba uno de sus códigos de recuperación"}
            </p>

            <form
              className="mt-6 space-y-4"
              onSubmit={(e) => {
                e.preventDefault();
                void handleVerifyMfa();
              }}
              noValidate
            >
              <FormField
                label={mfaMethod === "totp" ? "Código de verificación" : "Código de recuperación"}
                required
                htmlFor={mfaMethod === "totp" ? "mfa-code" : "recovery-code"}
                error={mfaError ?? undefined}
              >
                <TextInput
                  ref={mfaCodeRef}
                  id={mfaMethod === "totp" ? "mfa-code" : "recovery-code"}
                  value={mfaCode}
                  onChange={(e) => setMfaCode(e.target.value)}
                  inputMode={mfaMethod === "totp" ? "numeric" : "text"}
                  autoComplete={mfaMethod === "totp" ? "one-time-code" : "off"}
                  maxLength={mfaMethod === "totp" ? 7 : 19}
                  required
                  invalid={Boolean(mfaError)}
                />
              </FormField>
              <AsyncButton type="submit" className="w-full" onClick={handleVerifyMfa} loadingText="Verificando…">
                Verificar
              </AsyncButton>
            </form>

            <div className="mt-4 text-center text-sm">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => {
                  setMfaMethod((prev) => (prev === "totp" ? "recovery" : "totp"));
                  setMfaCode("");
                  setMfaError(null);
                }}
                className="font-medium text-brand-700"
              >
                {mfaMethod === "totp" ? "Usar un código de recuperación" : "Usar el código de la aplicación"}
              </Button>
            </div>

            <p className="mt-3 text-center text-xs text-text-500">Si no tiene la aplicación ni códigos de recuperación, pida a un administrador que restablezca su verificación en dos pasos.</p>

            <div className="mt-2 text-center">
              <Button variant="ghost" size="sm" onClick={handleBackToCredentials} className="font-medium text-text-600">
                Volver
              </Button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
