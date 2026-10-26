/**
 * Contexto de reautenticación (ADR-015, P18).
 * Diálogo compartido de confirmación breve que el cliente invoca ante
 * `403 REAUTH_REQUIRED`. Registra el handler con `setReauthHandler`.
 */
import {
  createContext,
  useContext,
  useEffect,
  useRef,
  useState,
  type ReactNode,
} from "react";

import { reauthenticate } from "@/api/mfa";
import { ApiError, setReauthHandler } from "@/api/client";
import { ConfirmationDialog } from "@/components/ConfirmationDialog";
import { FormField } from "@/components/FormField";
import { Button } from "@/components/Button";
import { TextInput } from "@/components/TextInput";
import { useNotifications } from "@/app/contexts/NotificationContext";

interface ReauthContextValue {
  /** Invoca el diálogo de reautenticación y devuelve `true` si tuvo éxito. */
  reauth: () => Promise<boolean>;
}

const ReauthContext = createContext<ReauthContextValue | null>(null);

export function ReauthProvider({ children }: { children: ReactNode }): React.JSX.Element {
  const { notify } = useNotifications();
  const [open, setOpen] = useState(false);
  const [password, setPassword] = useState("");
  const [segundo, setSegundo] = useState("");
  const [useRecovery, setUseRecovery] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const resolvers = useRef<((ok: boolean) => void) | null>(null);
  const passwordRef = useRef<HTMLInputElement>(null);

  const abrir = (): Promise<boolean> => {
    setOpen(true);
    return new Promise<boolean>((resolve) => {
      resolvers.current = resolve;
    });
  };

  useEffect(() => {
    setReauthHandler(() => abrir());
    return () => setReauthHandler(null);
  }, []);

  useEffect(() => {
    if (open) {
      passwordRef.current?.focus();
    }
  }, [open]);

  const limpiar = (): void => {
    setPassword("");
    setSegundo("");
    setUseRecovery(false);
    setError(null);
  };

  const cerrar = (ok: boolean): void => {
    const resolver = resolvers.current;
    resolvers.current = null;
    setOpen(false);
    limpiar();
    resolver?.(ok);
  };

  const handleConfirm = async (): Promise<void> => {
    setError(null);
    const factor = useRecovery
      ? segundo.trim()
        ? { recoveryCode: segundo.trim() }
        : undefined
      : segundo.trim()
        ? { code: segundo.trim() }
        : undefined;
    try {
      await reauthenticate(password, factor);
      cerrar(true);
    } catch (err) {
      if (err instanceof TypeError) {
        setError("Sin conexión. Inténtelo de nuevo.");
        return;
      }
      if (err instanceof ApiError) {
        if (err.code === "REAUTH_FAILED") {
          setError("Contraseña o código incorrectos.");
          return;
        }
        if (err.code === "AUTH_ACCOUNT_LOCKED") {
          cerrar(false);
          notify({
            type: "error",
            title: "Cuenta bloqueada",
            description: "Cuenta bloqueada temporalmente por intentos fallidos.",
          });
          return;
        }
      }
      setError("No fue posible confirmar su identidad. Inténtelo de nuevo.");
    }
  };

  const handleCancel = (): void => {
    cerrar(false);
  };

  const value: ReauthContextValue = { reauth: abrir };

  return (
    <ReauthContext.Provider value={value}>
      {children}
      <ConfirmationDialog
        open={open}
        title="Confirme su identidad"
        description="Esta operación es sensible. Escriba su contraseña y el código de su aplicación."
        confirmLabel="Confirmar"
        onConfirm={handleConfirm}
        onCancel={handleCancel}
      >
        <div className="space-y-4">
          <FormField label="Contraseña" required htmlFor="reauth-password">
            <TextInput
              ref={passwordRef}
              id="reauth-password"
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </FormField>
          <FormField
            label={useRecovery ? "Código de recuperación" : "Código de verificación"}
            htmlFor="reauth-code"
            error={error ?? undefined}
          >
            <TextInput
              id="reauth-code"
              type="text"
              inputMode={useRecovery ? "text" : "numeric"}
              autoComplete={useRecovery ? "off" : "one-time-code"}
              value={segundo}
              onChange={(e) => setSegundo(e.target.value)}
              invalid={Boolean(error)}
            />
          </FormField>
          <Button variant="ghost" size="sm" type="button" onClick={() => setUseRecovery((v) => !v)}>
            {useRecovery ? "Usar el código de la aplicación" : "Usar un código de recuperación"}
          </Button>
        </div>
      </ConfirmationDialog>
    </ReauthContext.Provider>
  );
}

export function useReauth(): ReauthContextValue {
  const ctx = useContext(ReauthContext);
  if (!ctx) {
    throw new Error("useReauth debe usarse dentro de <ReauthProvider>");
  }
  return ctx;
}
