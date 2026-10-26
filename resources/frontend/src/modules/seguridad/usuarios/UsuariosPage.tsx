/** Usuarios — listado y alta de usuarios (FR-001-020, WF-01). */
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { apiFetch, ApiError } from "@/api/client";
import { resetUserMfa } from "@/api/mfa";
import { useAuth } from "@/app/contexts/AuthContext";
import { useNotifications } from "@/app/contexts/NotificationContext";
import { AsyncButton } from "@/components/AsyncButton";
import { Button } from "@/components/Button";
import { ConfirmationDialog } from "@/components/ConfirmationDialog";
import { FormField } from "@/components/FormField";
import { PageContent } from "@/layout/PageContent";
import { PageHeader } from "@/components/PageHeader";
import { TextInput } from "@/components/TextInput";

interface UserRole {
  id: string;
  code: string;
  name: string;
}

interface UserSummary {
  id: string;
  username: string;
  email: string | null;
  status: string;
  must_change_password: boolean;
  last_login: string | null;
  roles: UserRole[];
}

export function UsuariosPage(): React.JSX.Element {
  const queryClient = useQueryClient();
  const { notify } = useNotifications();
  const { user, hasPermission } = useAuth();

  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [objetivo, setObjetivo] = useState<{ id: string; username: string } | null>(null);

  const query = useQuery({
    queryKey: ["security", "users"],
    queryFn: () => apiFetch<UserSummary[]>("/users"),
    retry: false,
  });

  const createUser = async (): Promise<void> => {
    try {
      await apiFetch("/users", {
        method: "POST",
        body: { username, email: email || null, password, must_change_password: true },
      });
      notify({ type: "success", title: "Usuario creado", description: username });
      setUsername("");
      setEmail("");
      setPassword("");
      void queryClient.invalidateQueries({ queryKey: ["security", "users"] });
    } catch (err) {
      const message = err instanceof Error ? err.message : "No fue posible crear el usuario";
      notify({ type: "error", title: "No fue posible crear el usuario", description: message });
    }
  };

  const row = (key: string, label: string, value: string, action?: React.ReactNode): React.JSX.Element => (
    <div
      key={key}
      className="flex items-center justify-between border-b border-border-default px-4 py-2 text-sm last:border-b-0"
    >
      <span className="text-text-700">{label}</span>
      <span className="flex items-center gap-2">
        <span className="text-text-500">{value}</span>
        {action}
      </span>
    </div>
  );

  const handleResetMfa = async (): Promise<void> => {
    if (!objetivo) {
      return;
    }
    try {
      await resetUserMfa(objetivo.id);
      notify({
        type: "success",
        title: "Verificación restablecida",
        description: `${objetivo.username} tendrá que volver a configurarla en su próximo inicio de sesión.`,
      });
      setObjetivo(null);
    } catch (err) {
      if (err instanceof TypeError) {
        notify({ type: "error", title: "No fue posible restablecer la verificación", description: "Sin conexión. Inténtelo de nuevo." });
        return;
      }
      const { code, message } = err instanceof ApiError
        ? { code: err.code, message: err.message }
        : { code: "", message: err instanceof Error ? err.message : "No fue posible restablecer la verificación" };
      const mensaje =
        code === "MFA_NOT_CONFIGURED"
          ? "Este usuario no tiene la verificación configurada."
          : code === "MFA_RESET_CEILING"
            ? "No puede restablecer a un usuario con más permisos que usted."
            : code === "PERMISSION_DENIED"
              ? "No tiene permiso para esta acción."
              : message;
      notify({ type: "error", title: "No fue posible restablecer la verificación", description: mensaje });
    }
  };

  return (
    <PageContent maxWidth="full">
      <PageHeader
        title="Usuarios"
        description="Usuarios de la instalación y sus roles."
        crumbs={[{ label: "Seguridad" }, { label: "Usuarios" }]}
      />

      <section className="mb-4 rounded-lg border border-border-default bg-surface-0 p-4">
        <h2 className="mb-2 text-base font-semibold text-text-900">Registrar usuario</h2>
        <form className="flex flex-wrap items-end gap-3" onSubmit={(e) => e.preventDefault()}>
          <FormField label="Usuario" required>
            <TextInput value={username} onChange={(e) => setUsername(e.target.value)} placeholder="Nombre de usuario" required />
          </FormField>
          <FormField label="Correo">
            <TextInput type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="Opcional" />
          </FormField>
          <FormField label="Contraseña" required help="Mínimo 10 caracteres; mayúscula, minúscula y número.">
            <TextInput type="password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="Temporal" required />
          </FormField>
          <AsyncButton type="submit" variant="primary" onClick={createUser}>
            Registrar
          </AsyncButton>
        </form>
      </section>

      <section className="rounded-lg border border-border-default bg-surface-0 p-4">
        <h2 className="mb-2 text-base font-semibold text-text-900">Usuarios</h2>
        <div>
          {query.isLoading ? <p className="text-sm text-text-500">Cargando…</p> : null}
          {query.isError ? (
            <p className="text-sm text-danger-600" role="alert">
              No fue posible cargar los usuarios.
            </p>
          ) : null}
          {(query.data ?? []).map((u) =>
            row(
              u.id,
              `${u.username} · ${u.email ?? "sin correo"} · Roles: ${u.roles.map((r) => r.code).join(", ") || "—"}`,
              u.status,
              hasPermission("users:mfa_reset") && u.id !== user?.id ? (
                <Button variant="secondary" size="sm" onClick={() => setObjetivo({ id: u.id, username: u.username })}>
                  Restablecer verificación
                </Button>
              ) : null,
            ),
          )}
          {query.isSuccess && (query.data ?? []).length === 0 ? (
            <p className="text-sm text-text-500">Sin usuarios registrados.</p>
          ) : null}
        </div>
      </section>

      <ConfirmationDialog
        open={objetivo !== null}
        title="Restablecer la verificación en dos pasos"
        description={`${objetivo?.username ?? ""} tendrá que volver a configurarla en su próximo inicio de sesión. Se cerrarán sus sesiones.`}
        confirmLabel="Restablecer"
        danger
        onConfirm={handleResetMfa}
        onCancel={() => setObjetivo(null)}
      />
    </PageContent>
  );
}
