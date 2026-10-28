/** MiMfaPage — verificación en dos pasos del usuario autenticado (Spec 002/003). */
import { useState } from "react";
import { useNavigate } from "react-router";
import { useQuery, useQueryClient } from "@tanstack/react-query";

import { ApiError } from "@/api/client";
import { getMfaStatus, regenerateRecoveryCodes, removeOwnFactor } from "@/api/mfa";
import { useNotifications } from "@/app/contexts/NotificationContext";
import { AsyncButton } from "@/components/AsyncButton";
import { Button } from "@/components/Button";
import { ConfirmationDialog } from "@/components/ConfirmationDialog";
import { ErrorState } from "@/components/ErrorState";
import { LoadingState } from "@/components/LoadingState";
import { PageContent } from "@/layout/PageContent";
import { PageHeader } from "@/components/PageHeader";
import { RecoveryCodesPanel } from "@/components/RecoveryCodesPanel";
import { formatearFechaDeInstante } from "@/lib/fecha-de-negocio";

export function MiMfaPage(): React.JSX.Element {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { notify } = useNotifications();
  const [confirmRemove, setConfirmRemove] = useState(false);
  const [showCodes, setShowCodes] = useState(false);
  const [codesConfirmed, setCodesConfirmed] = useState(false);
  const [codes, setCodes] = useState<string[]>([]);
  const [removing, setRemoving] = useState(false);

  const query = useQuery({
    queryKey: ["security", "mfa"],
    queryFn: getMfaStatus,
    retry: false,
  });

  const refresh = async (): Promise<void> => {
    await queryClient.invalidateQueries({ queryKey: ["security", "mfa"] });
  };

  const errorMessage = (err: unknown, fallback: string): string => {
    if (err instanceof TypeError) {
      return "Sin conexión. Inténtelo de nuevo.";
    }
    if (err instanceof ApiError) {
      if (err.code === "MFA_REQUIRED_BY_POLICY") {
        return "Su política no permite quitar la verificación.";
      }
      if (err.code === "MFA_NOT_CONFIGURED") {
        return "La verificación no está configurada.";
      }
      return err.message;
    }
    return fallback;
  };

  const handleRegenerate = async (): Promise<void> => {
    try {
      const data = await regenerateRecoveryCodes();
      setCodes(data.recovery_codes);
      setShowCodes(true);
      setCodesConfirmed(false);
      await refresh();
      notify({ type: "success", title: "Códigos generados", description: "Guarde estos códigos; no volverá a verlos." });
    } catch (err) {
      notify({ type: "error", title: "No fue posible generar los códigos", description: errorMessage(err, "No fue posible generar los códigos") });
    }
  };

  const handleRemove = async (): Promise<void> => {
    if (removing) {
      return;
    }
    setRemoving(true);
    try {
      await removeOwnFactor();
      setConfirmRemove(false);
      await refresh();
      notify({ type: "success", title: "Verificación quitada", description: "La verificación en dos pasos fue quitada." });
    } catch (err) {
      if (err instanceof ApiError && (err.code === "MFA_REQUIRED_BY_POLICY" || err.code === "MFA_NOT_CONFIGURED")) {
        await refresh();
      }
      notify({
        type: "error",
        title: "No fue posible quitar la verificación",
        description: errorMessage(err, "No fue posible quitar la verificación"),
      });
      setConfirmRemove(false);
    } finally {
      setRemoving(false);
    }
  };

  const data = query.data;

  if (query.isLoading) {
    return (
      <PageContent maxWidth="sm">
        <PageHeader
          title="Verificación en dos pasos"
          description="Gestione el segundo factor de su cuenta."
          crumbs={[{ label: "Seguridad" }, { label: "Verificación en dos pasos" }]}
        />
        <LoadingState />
      </PageContent>
    );
  }

  if (query.isError) {
    const err = query.error;
    const requestId = err instanceof ApiError ? err.requestId : undefined;
    const message = err instanceof Error ? err.message : "No fue posible cargar el estado del MFA.";
    return (
      <PageContent maxWidth="sm">
        <PageHeader
          title="Verificación en dos pasos"
          description="Gestione el segundo factor de su cuenta."
          crumbs={[{ label: "Seguridad" }, { label: "Verificación en dos pasos" }]}
        />
        <ErrorState
          message={message}
          requestId={requestId}
          onRetry={() => {
            void query.refetch();
          }}
        />
      </PageContent>
    );
  }

  if (!data) {
    return (
      <PageContent maxWidth="sm">
        <PageHeader
          title="Verificación en dos pasos"
          description="Gestione el segundo factor de su cuenta."
          crumbs={[{ label: "Seguridad" }, { label: "Verificación en dos pasos" }]}
        />
        <p className="text-sm text-text-500">No fue posible cargar el estado del MFA.</p>
      </PageContent>
    );
  }

  return (
    <PageContent maxWidth="sm">
      <PageHeader
        title="Verificación en dos pasos"
        description="Gestione el segundo factor de su cuenta."
        crumbs={[{ label: "Seguridad" }, { label: "Verificación en dos pasos" }]}
      />
      <div className="space-y-4 rounded-lg border border-border-default bg-surface-0 p-4 sm:p-6">
        {!data.enabled ? (
          <div className="space-y-4">
            <p className="text-sm font-medium text-text-900">Desactivada</p>
            {data.required ? (
              <p className="text-sm text-danger-600" role="status">
                Su rol exige verificación en dos pasos.
              </p>
            ) : null}
            <Button variant="primary" onClick={() => navigate("/seguridad/mfa/alta")}>
              Configurar
            </Button>
          </div>
        ) : (
          <div className="space-y-4">
            <p className="text-sm text-text-900">
              Activa desde <span className="font-medium">{data.activated_at ? formatearFechaDeInstante(data.activated_at) : "—"}</span>
            </p>
            <p className="text-sm text-text-900">
              Códigos de recuperación disponibles: <span className="font-medium">{data.recovery_codes_remaining}</span>
            </p>
            {data.recovery_codes_remaining <= 3 ? (
              <p className="text-sm text-warning-600" role="status">
                Debe regenerar los códigos de recuperación.
              </p>
            ) : null}
            <div className="flex flex-col gap-2 sm:flex-row">
              <AsyncButton variant="secondary" onClick={handleRegenerate} loadingText="Generando…">
                Generar códigos nuevos
              </AsyncButton>
              <Button variant="secondary" onClick={() => navigate("/seguridad/mfa/alta")}>
                Reemplazar la aplicación
              </Button>
            </div>
            {showCodes ? (
              <div className="space-y-3">
                <RecoveryCodesPanel codes={codes} />
                <label className="flex items-center gap-2 text-sm text-text-700">
                  <input
                    type="checkbox"
                    checked={codesConfirmed}
                    onChange={(e) => setCodesConfirmed(e.target.checked)}
                  />
                  He guardado mis códigos
                </label>
                <Button variant="secondary" disabled={!codesConfirmed} onClick={() => setShowCodes(false)}>
                  Ocultar códigos
                </Button>
              </div>
            ) : null}
            {data.required === false ? (
              <div className="mt-4 border-t border-border-default pt-4">
                <Button variant="danger" onClick={() => setConfirmRemove(true)}>
                  Quitar la verificación
                </Button>
              </div>
            ) : (
              <p className="mt-4 border-t border-border-default pt-4 text-sm text-text-500">
                Su política no permite quitarla
              </p>
            )}
          </div>
        )}
      </div>

      <ConfirmationDialog
        open={confirmRemove}
        title="Quitar la verificación en dos pasos"
        description="Su cuenta quedará protegida solo por la contraseña."
        confirmLabel="Quitar"
        danger
        onConfirm={handleRemove}
        onCancel={() => setConfirmRemove(false)}
      />
    </PageContent>
  );
}
