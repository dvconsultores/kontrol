/** MfaAlta — alta del segundo factor (forzada o voluntaria). */
import { useEffect, useRef, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { Navigate, useLocation, useNavigate } from "react-router";

import { useAuth } from "@/app/contexts/AuthContext";
import { useNotifications } from "@/app/contexts/NotificationContext";
import { AsyncButton } from "@/components/AsyncButton";
import { Button } from "@/components/Button";
import { ErrorState } from "@/components/ErrorState";
import { FormField } from "@/components/FormField";
import { MfaQrImage } from "@/components/MfaQrImage";
import { PageContent } from "@/layout/PageContent";
import { PageHeader } from "@/components/PageHeader";
import { RecoveryCodesPanel } from "@/components/RecoveryCodesPanel";
import { TextInput } from "@/components/TextInput";
import { ApiError } from "@/api/client";
import { confirmEnrollment, startEnrollment } from "@/api/mfa";
import type { AuthenticatedLogin, MfaEnrollmentStart, MfaRecoveryCodes } from "@/api/types";

type EnrollmentStep = 1 | 2 | 3 | 4;

interface EnrollmentLocationState {
  challengeToken?: string;
  tenantCode?: string;
  username?: string;
}

function isMfaRecoveryCodes(value: AuthenticatedLogin | MfaRecoveryCodes): value is MfaRecoveryCodes {
  return "recovery_codes" in value && !("access_token" in value);
}

export function MfaAltaPage(): React.JSX.Element {
  const location = useLocation();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { completeLogin } = useAuth();
  const { notify } = useNotifications();

  const state = location.state as EnrollmentLocationState | null;
  const esPublica = location.pathname.startsWith("/acceso/");
  const isChallengeEnrollment = Boolean(state?.challengeToken);

  const [step, setStep] = useState<EnrollmentStep>(1);
  const [enrollment, setEnrollment] = useState<MfaEnrollmentStart | null>(null);
  const [verificationCode, setVerificationCode] = useState("");
  const [verificationError, setVerificationError] = useState<string | null>(null);
  const [recoveryCodes, setRecoveryCodes] = useState<string[]>([]);
  const [loginFinal, setLoginFinal] = useState<AuthenticatedLogin | null>(null);
  const [savedCodesConfirmed, setSavedCodesConfirmed] = useState(false);
  const [pageError, setPageError] = useState<string | null>(null);
  const [copyNotice, setCopyNotice] = useState<string | null>(null);
  const codeRef = useRef<HTMLInputElement>(null);
  const stepHeadingRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (step === 3) {
      codeRef.current?.focus();
    } else {
      stepHeadingRef.current?.focus();
    }
  }, [step]);

  if (esPublica && !state?.challengeToken) {
    return <Navigate to="/login" replace />;
  }

  const handleStart = async (): Promise<void> => {
    setPageError(null);
    try {
      const data = await startEnrollment(state?.challengeToken);
      setEnrollment(data);
      setStep(2);
    } catch (err) {
      if (err instanceof TypeError) {
        setPageError("Sin conexión. Inténtelo de nuevo.");
        return;
      }
      if (err instanceof ApiError) {
        setPageError(getEnrollmentErrorMessage(err));
        return;
      }
      setPageError("No fue posible iniciar el alta");
    }
  };

  const validateCode = (): string | null => {
    const digits = verificationCode.replace(/\s/g, "");
    return /^\d{6}$/.test(digits) ? null : "Introduzca los 6 dígitos del código";
  };

  const getEnrollmentErrorMessage = (err: ApiError): string => {
    if (err.code === "MFA_INVALID_CODE") {
      if (typeof err.details?.attempts_remaining === "number") {
        return `Código incorrecto. Le quedan ${err.details.attempts_remaining} intentos.`;
      }
      return "Código incorrecto.";
    }
    if (err.code === "MFA_CODE_ALREADY_USED") {
      return "Ese código ya se usó. Espere al siguiente código de su aplicación.";
    }
    if (err.code === "MFA_NO_PENDING_ENROLLMENT") {
      return "El alta caducó o se reinició en otra ventana. Empiece de nuevo.";
    }
    if (err.code === "MFA_CHALLENGE_INVALID") {
      return "La verificación caducó. Inicie sesión de nuevo.";
    }
    if (err.code === "AUTH_ACCOUNT_LOCKED") {
      return "Cuenta bloqueada temporalmente por intentos fallidos.";
    }
    if (err.code === "MFA_UNAVAILABLE") {
      return "El segundo factor no está disponible. Contacte con el administrador.";
    }
    return "No fue posible verificar el código";
  };

  const handleVerify = async (): Promise<void> => {
    const validationError = validateCode();
    if (validationError) {
      setVerificationError(validationError);
      return;
    }
    setVerificationError(null);
    setPageError(null);
    try {
      const data = await confirmEnrollment(verificationCode.replace(/\s/g, ""), state?.challengeToken);
      if (isMfaRecoveryCodes(data)) {
        setRecoveryCodes(data.recovery_codes);
      } else {
        setLoginFinal(data);
        setRecoveryCodes(data.recovery_codes ?? []);
      }
      setStep(4);
    } catch (err) {
      if (err instanceof TypeError) {
        setVerificationError("Sin conexión. Inténtelo de nuevo.");
        return;
      }
      if (err instanceof ApiError) {
        const message = getEnrollmentErrorMessage(err);
        if (err.code === "MFA_NO_PENDING_ENROLLMENT") {
          setStep(1);
          setVerificationCode("");
          setVerificationError(null);
          setPageError(message);
          return;
        }
        if (err.code === "MFA_CHALLENGE_INVALID") {
          notify({ type: "error", title: "Verificación caducada", description: message });
          navigate("/login", { replace: true });
          return;
        }
        if (err.code === "AUTH_ACCOUNT_LOCKED") {
          notify({ type: "error", title: "Cuenta bloqueada", description: message });
          navigate("/login", { replace: true });
          return;
        }
        setVerificationError(message);
        return;
      }
      setVerificationError("No fue posible verificar el código");
    }
  };

  const handleFinish = (): void => {
    if (!savedCodesConfirmed) {
      return;
    }
    if (isChallengeEnrollment) {
      if (!loginFinal) {
        setPageError("No fue posible completar el alta");
        return;
      }
      completeLogin(loginFinal);
      notify({ type: "success", title: "Segundo factor activado", description: "Su cuenta está protegida." });
      setVerificationCode("");
      if (loginFinal.must_change_password) {
        navigate("/cambiar-contrasena");
      } else {
        navigate("/");
      }
    } else {
      void queryClient.invalidateQueries({ queryKey: ["security", "mfa"] });
      navigate("/seguridad/mfa");
    }
  };

  const steps = [
    { num: 1, label: "Por qué" },
    { num: 2, label: "Configure su aplicación" },
    { num: 3, label: "Verifique" },
    { num: 4, label: "Guarde sus códigos de recuperación" },
  ];

  const content = (
    <div ref={stepHeadingRef} tabIndex={-1} className="focus:outline-none">
      <ol className="mt-6 space-y-2">
        {steps.map((s) => (
          <li key={s.num} className="flex items-center gap-2 text-sm" aria-current={s.num === step ? "step" : undefined}>
            <span
              className={`flex size-6 shrink-0 items-center justify-center rounded-full text-xs font-semibold ${
                s.num === step ? "bg-brand-700 text-white" : s.num < step ? "bg-brand-100 text-brand-700" : "bg-surface-100 text-text-500"
              }`}
            >
              {s.num}
            </span>
            <span className={s.num === step ? "font-semibold text-text-900" : "text-text-500"}>{s.label}</span>
          </li>
        ))}
      </ol>

      {pageError ? (
        <div className="mt-6">
          <ErrorState message={pageError} />
        </div>
      ) : null}

        {step === 1 ? (
          <div className="mt-6 space-y-4">
            <p className="text-sm text-text-700">
              {isChallengeEnrollment
                ? "Su rol exige verificación en dos pasos. Debe activarla antes de continuar."
                : "Su cuenta quedará más protegida. Podrá usar una aplicación de autenticación y códigos de recuperación."}
            </p>
            <AsyncButton className="w-full" onClick={handleStart} loadingText="Preparando…">
              Comenzar
            </AsyncButton>
          </div>
        ) : null}

        {step === 2 && enrollment ? (
          <div className="mt-6 space-y-4">
            <p className="text-sm text-text-700">
              Escanee el código QR con su aplicación de autenticación o introduzca la clave manual.
            </p>
            <MfaQrImage dataUri={enrollment.qr_svg_data_uri} />
            <div className="rounded-md border border-border-default bg-surface-50 p-3">
              <p className="text-sm font-medium text-text-700">¿No puede escanear? Introduzca esta clave</p>
              <code
                className="mt-1 block break-all text-sm text-text-900"
                aria-label={`Clave manual: ${enrollment.manual_key.split("").join(" ")}`}
              >
                {enrollment.manual_key}
              </code>
              <Button
                variant="ghost"
                size="sm"
                className="mt-2"
                onClick={async () => {
                  try {
                    await navigator.clipboard.writeText(enrollment.manual_key);
                    setCopyNotice("Clave copiada");
                  } catch {
                    setCopyNotice("Copie la clave manualmente");
                  }
                }}
              >
                Copiar clave
              </Button>
              {copyNotice ? <p className="mt-1 text-xs text-text-600">{copyNotice}</p> : null}
            </div>
            <Button className="w-full" onClick={() => setStep(3)}>
              Siguiente
            </Button>
          </div>
        ) : null}

        {step === 3 ? (
          <div className="mt-6 space-y-4">
            <p className="text-sm text-text-700">Escriba el código de 6 dígitos que muestra su aplicación.</p>
            <FormField label="Código de verificación" required htmlFor="mfa-code" error={verificationError ?? undefined}>
              <TextInput
                ref={codeRef}
                id="mfa-code"
                value={verificationCode}
                onChange={(e) => setVerificationCode(e.target.value)}
                inputMode="numeric"
                autoComplete="one-time-code"
                maxLength={7}
                required
                invalid={Boolean(verificationError)}
              />
            </FormField>
            <div className="flex gap-2">
              <Button variant="ghost" onClick={() => setStep(2)}>
                Volver
              </Button>
              <AsyncButton className="flex-1" onClick={handleVerify} loadingText="Verificando…">
                Verificar
              </AsyncButton>
            </div>
          </div>
        ) : null}

        {step === 4 ? (
          <div className="mt-6 space-y-4">
            <p className="text-sm text-text-700">Guarde estos códigos. Podrá usarlos si pierde el acceso a su aplicación.</p>
            <RecoveryCodesPanel codes={recoveryCodes} />
            <label className="flex items-center gap-2 text-sm text-text-700">
              <input
                type="checkbox"
                checked={savedCodesConfirmed}
                onChange={(e) => setSavedCodesConfirmed(e.target.checked)}
                className="size-4"
              />
              He guardado mis códigos en un lugar seguro
            </label>
            <Button className="w-full" onClick={handleFinish} disabled={!savedCodesConfirmed}>
              Continuar
            </Button>
          </div>
        ) : null}
      </div>
    );

  if (esPublica) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-surface-50 px-4 py-8">
        <div className="w-full max-w-md rounded-lg border border-border-default bg-surface-0 p-8 shadow-sm">
          <h1 className="text-2xl font-semibold text-brand-700">Verificación en dos pasos</h1>
          <p className="mt-1 text-sm text-text-500">
            {isChallengeEnrollment
              ? "Su organización exige activar la verificación en dos pasos para continuar."
              : "Proteja su cuenta con un segundo factor de autenticación."}
          </p>
          {content}
        </div>
      </div>
    );
  }

  return (
    <PageContent maxWidth="md">
      <PageHeader
        title="Verificación en dos pasos"
        crumbs={[
          { label: "Seguridad" },
          { label: "Verificación en dos pasos", to: "/seguridad/mfa" },
          { label: "Configurar" },
        ]}
      />
      {content}
    </PageContent>
  );
}
