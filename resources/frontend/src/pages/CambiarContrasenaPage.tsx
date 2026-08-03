/** CambiarContrasena — cambio de contraseña (US-005, FR-001-011). */
import { useState } from "react";
import { useNavigate } from "react-router";

import { apiFetch } from "@/api/client";
import { useNotifications } from "@/app/contexts/NotificationContext";
import { AsyncButton } from "@/components/AsyncButton";
import { FormField } from "@/components/FormField";
import { PageContent } from "@/layout/PageContent";
import { PageHeader } from "@/components/PageHeader";
import { TextInput } from "@/components/TextInput";

export function CambiarContrasenaPage(): React.JSX.Element {
  const navigate = useNavigate();
  const { notify } = useNotifications();
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (): Promise<void> => {
    setError(null);
    if (next !== confirm) {
      setError("Las contraseñas no coinciden");
      return;
    }
    try {
      await apiFetch("/auth/change-password", {
        method: "POST",
        body: { current_password: current, new_password: next },
      });
      notify({ type: "success", title: "Contraseña actualizada", description: "Su contraseña fue cambiada correctamente." });
      navigate("/");
    } catch (err) {
      const message = err instanceof Error ? err.message : "No fue posible cambiar la contraseña";
      setError(message);
      notify({ type: "error", title: "No fue posible cambiar la contraseña", description: message });
    }
  };

  return (
    <PageContent maxWidth="sm">
      <PageHeader
        title="Cambiar contraseña"
        description="Por seguridad, debe cambiar su contraseña inicial."
        crumbs={[{ label: "Cambiar contraseña" }]}
      />
      <form
        className="space-y-4 rounded-lg border border-border-default bg-surface-0 p-6"
        onSubmit={(e) => {
          e.preventDefault();
          void handleSubmit();
        }}
        noValidate
      >
        <FormField label="Contraseña actual" required>
          <TextInput type="password" value={current} onChange={(e) => setCurrent(e.target.value)} required />
        </FormField>
        <FormField
          label="Nueva contraseña"
          required
          error={error ?? undefined}
          help="Mínimo 10 caracteres; mayúscula, minúscula y número."
        >
          <TextInput type="password" value={next} onChange={(e) => setNext(e.target.value)} required invalid={Boolean(error)} />
        </FormField>
        <FormField label="Confirmar nueva contraseña" required>
          <TextInput type="password" value={confirm} onChange={(e) => setConfirm(e.target.value)} required />
        </FormField>
        <AsyncButton type="submit" onClick={handleSubmit} loadingText="Guardando…">
          Guardar contraseña
        </AsyncButton>
      </form>
    </PageContent>
  );
}
