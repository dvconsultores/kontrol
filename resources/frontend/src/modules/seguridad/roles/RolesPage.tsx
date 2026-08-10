/** Roles — roles, permisos y asignación a usuarios (FR-001-040). */
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { apiFetch } from "@/api/client";
import { useNotifications } from "@/app/contexts/NotificationContext";
import { AsyncButton } from "@/components/AsyncButton";
import { FormField } from "@/components/FormField";
import { PageContent } from "@/layout/PageContent";
import { PageHeader } from "@/components/PageHeader";

interface RoleSummary {
  id: string;
  code: string;
  name: string;
  protected: boolean;
  status: string;
  permissions: string[];
}

interface UserSummary {
  id: string;
  username: string;
  roles: { id: string; code: string; name: string }[];
}

export function RolesPage(): React.JSX.Element {
  const queryClient = useQueryClient();
  const { notify } = useNotifications();
  const [userId, setUserId] = useState("");
  const [roleId, setRoleId] = useState("");

  const roles = useQuery({
    queryKey: ["security", "roles"],
    queryFn: () => apiFetch<{ items: RoleSummary[] }>("/roles"),
    retry: false,
  });
  const users = useQuery({
    queryKey: ["security", "users"],
    queryFn: () => apiFetch<UserSummary[]>("/users"),
    retry: false,
  });

  const refresh = (): void => {
    void queryClient.invalidateQueries({ queryKey: ["security"] });
  };

  const assign = async (): Promise<void> => {
    if (!userId || !roleId) return;
    try {
      await apiFetch(`/users/${userId}/roles`, { method: "POST", body: { role_id: roleId } });
      notify({ type: "success", title: "Rol asignado", description: "La asignación fue registrada." });
      setRoleId("");
      refresh();
    } catch (err) {
      const message = err instanceof Error ? err.message : "No fue posible asignar el rol";
      notify({ type: "error", title: "No fue posible asignar el rol", description: message });
    }
  };

  const remove = async (uid: string, rid: string, label: string): Promise<void> => {
    try {
      await apiFetch(`/users/${uid}/roles/${rid}`, { method: "DELETE" });
      notify({ type: "success", title: "Rol quitado", description: label });
      refresh();
    } catch (err) {
      const message = err instanceof Error ? err.message : "No fue posible quitar el rol";
      notify({ type: "error", title: "No fue posible quitar el rol", description: message });
    }
  };

  return (
    <PageContent maxWidth="full">
      <PageHeader
        title="Roles y permisos"
        description="Roles de la instalación y su asignación a usuarios."
        crumbs={[{ label: "Seguridad" }, { label: "Roles" }]}
      />

      <section className="mb-4 rounded-lg border border-border-default bg-surface-0 p-4">
        <h2 className="mb-2 text-base font-semibold text-text-900">Asignar rol a usuario</h2>
        <form className="flex flex-wrap items-end gap-3" onSubmit={(e) => e.preventDefault()}>
          <FormField label="Usuario" required>
            <select
              value={userId}
              onChange={(e) => setUserId(e.target.value)}
              className="h-10 w-56 rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900"
            >
              <option value="">Seleccionar…</option>
              {(users.data ?? []).map((u) => (
                <option key={u.id} value={u.id}>
                  {u.username}
                </option>
              ))}
            </select>
          </FormField>
          <FormField label="Rol" required>
            <select
              value={roleId}
              onChange={(e) => setRoleId(e.target.value)}
              className="h-10 w-56 rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900"
            >
              <option value="">Seleccionar…</option>
              {(roles.data?.items ?? []).map((r) => (
                <option key={r.id} value={r.id}>
                  {r.name} ({r.code})
                </option>
              ))}
            </select>
          </FormField>
          <AsyncButton type="submit" variant="primary" onClick={assign}>
            Asignar
          </AsyncButton>
        </form>
      </section>

      <div className="grid gap-4 lg:grid-cols-2">
        <section className="rounded-lg border border-border-default bg-surface-0 p-4">
          <h2 className="mb-2 text-base font-semibold text-text-900">Roles y permisos</h2>
          {roles.isLoading ? <p className="text-sm text-text-500">Cargando…</p> : null}
          <ul className="divide-y divide-border-default">
            {(roles.data?.items ?? []).map((r) => (
              <li key={r.id} className="py-2 text-sm">
                <div className="flex items-center justify-between">
                  <span className="font-medium text-text-900">
                    {r.name} <span className="text-text-400">({r.code})</span>
                  </span>
                  {r.protected ? <span className="text-xs text-text-400">protegido</span> : null}
                </div>
                <p className="mt-1 text-xs text-text-500">{r.permissions.join(" · ") || "sin permisos"}</p>
              </li>
            ))}
          </ul>
          {(roles.data?.items ?? []).length === 0 ? <p className="text-sm text-text-500">Sin roles.</p> : null}
        </section>

        <section className="rounded-lg border border-border-default bg-surface-0 p-4">
          <h2 className="mb-2 text-base font-semibold text-text-900">Asignaciones actuales</h2>
          {(users.data ?? []).map((u) => (
            <div key={u.id} className="border-b border-border-default py-2 text-sm last:border-b-0">
              <span className="font-medium text-text-900">{u.username}</span>
              <div className="mt-1 flex flex-wrap gap-2">
                {(u.roles ?? []).map((r) => (
                  <span key={r.id} className="inline-flex items-center gap-1 rounded border border-border-default px-2 py-0.5 text-xs text-text-600">
                    {r.name}
                    <button
                      type="button"
                      onClick={() => void remove(u.id, r.id, `${u.username} · ${r.name}`)}
                      className="text-text-400 hover:text-danger-600"
                      aria-label={`Quitar rol ${r.name} a ${u.username}`}
                    >
                      ×
                    </button>
                  </span>
                ))}
                {(u.roles ?? []).length === 0 ? <span className="text-xs text-text-400">sin roles</span> : null}
              </div>
            </div>
          ))}
        </section>
      </div>
    </PageContent>
  );
}
