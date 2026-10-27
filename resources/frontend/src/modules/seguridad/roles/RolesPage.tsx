/** Roles — roles, permisos y asignación a usuarios (FR-001-040). */
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { apiFetch } from "@/api/client";
import { useNotifications } from "@/app/contexts/NotificationContext";
import { useAutoridad } from "@/app/autoridad/AutoridadContext";
import { AsyncButton } from "@/components/AsyncButton";
import { ConfirmationDialog } from "@/components/ConfirmationDialog";
import { FormField } from "@/components/FormField";
import { PageContent } from "@/layout/PageContent";
import { PageHeader } from "@/components/PageHeader";

interface RoleSummary {
  id: string;
  code: string;
  name: string;
  company_id: string | null;
  protected: boolean;
  status: string;
  permissions: string[];
  delegable: boolean;
  motivo: string | null;
}

interface UserRole {
  id: string;
  code: string;
  name: string;
  company_id: string | null;
}

interface UserSummary {
  id: string;
  username: string;
  roles: UserRole[];
}

interface CompanySummary {
  id: string;
  code: string;
  legal_name: string;
}

interface RemoveTarget {
  uid: string;
  rid: string;
  label: string;
}

const MENSAJES_DE_AUTORIDAD: Record<string, string> = {
  AUTHORITY_CEILING_EXCEEDED: "No puede conceder ni gestionar una autoridad que usted no tiene.",
  SELF_ESCALATION_FORBIDDEN: "No puede ampliar su propia autoridad.",
  CROSS_SCOPE_DELEGATION_FORBIDDEN:
    "No puede conceder autoridad fuera de las empresas en las que la tiene.",
  TARGET_OUT_OF_SCOPE: "Esa asignación está fuera de las empresas en las que usted tiene autoridad.",
  LAST_SECURITY_ADMIN_REQUIRED:
    "La empresa debe conservar al menos un administrador de seguridad. Asigne antes ese rol a otra persona.",
  ROLE_ALREADY_ASSIGNED: "El usuario ya tiene ese rol.",
  ROLE_INACTIVE: "El rol no está activo.",
};

function mensajeDeError(err: unknown, porDefecto: string): string {
  if (err instanceof Error && "code" in err && typeof err.code === "string") {
    const code = err.code;
    if (Object.hasOwn(MENSAJES_DE_AUTORIDAD, code)) return MENSAJES_DE_AUTORIDAD[code];
  }
  return err instanceof Error ? err.message : porDefecto;
}

export function RolesPage(): React.JSX.Element {
  const queryClient = useQueryClient();
  const { notify } = useNotifications();
  const { puede } = useAutoridad();
  const [userId, setUserId] = useState("");
  const [roleId, setRoleId] = useState("");
  const [companyId, setCompanyId] = useState("");
  const [toRemove, setToRemove] = useState<RemoveTarget | null>(null);

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
  const companies = useQuery({
    queryKey: ["security", "companies"],
    queryFn: () =>
      apiFetch<{ items: CompanySummary[]; total: number; page: number; page_size: number }>(
        "/organization/companies?page=1&page_size=100",
      ),
    retry: false,
  });

  const refresh = (): void => {
    void queryClient.invalidateQueries({ queryKey: ["security"] });
  };

  const assign = async (): Promise<void> => {
    if (!userId || !roleId) return;
    try {
      const body: { role_id: string; company_id?: string } = { role_id: roleId };
      if (companyId) body.company_id = companyId;
      await apiFetch(`/users/${userId}/roles`, { method: "POST", body });
      notify({ type: "success", title: "Rol asignado", description: "La asignación fue registrada." });
      setRoleId("");
      setCompanyId("");
      refresh();
    } catch (err) {
      notify({
        type: "error",
        title: "No fue posible asignar el rol",
        description: mensajeDeError(err, "No fue posible asignar el rol"),
      });
    }
  };

  const confirmRemove = async (): Promise<void> => {
    if (!toRemove) return;
    try {
      await apiFetch(`/users/${toRemove.uid}/roles/${toRemove.rid}`, { method: "DELETE" });
      notify({ type: "success", title: "Rol quitado", description: toRemove.label });
      refresh();
    } catch (err) {
      notify({
        type: "error",
        title: "No fue posible quitar el rol",
        description: mensajeDeError(err, "No fue posible quitar el rol"),
      });
    } finally {
      setToRemove(null);
    }
  };

  const companyName = (id: string | null): string => {
    if (!id) return "";
    const found = (companies.data?.items ?? []).find((c) => c.id === id);
    return found ? found.legal_name : id;
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
          <FormField label="Usuario" htmlFor="rol-usuario" required>
            <select
              id="rol-usuario"
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
          <FormField label="Rol" htmlFor="rol-rol" required>
            <select
              id="rol-rol"
              value={roleId}
              onChange={(e) => setRoleId(e.target.value)}
              className="h-10 w-56 rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900"
            >
              <option value="">Seleccionar…</option>
              {(roles.data?.items ?? []).map((r) => (
                <option key={r.id} value={r.id} disabled={!r.delegable}>
                  {r.name} ({r.code}){!r.delegable ? " — fuera de su autoridad" : ""}
                </option>
              ))}
            </select>
          </FormField>
          <FormField
            label="Empresa"
            htmlFor="rol-empresa"
            help="El rol solo valdrá en la empresa elegida. Solo puede conceder autoridad en las empresas donde usted la tiene."
          >
            <select
              id="rol-empresa"
              value={companyId}
              onChange={(e) => setCompanyId(e.target.value)}
              className="h-10 w-64 rounded-md border border-border-default bg-surface-0 px-3 text-sm text-text-900"
            >
              <option value="">Todas las empresas en las que opera</option>
              {(companies.data?.items ?? []).map((c) => (
                <option key={c.id} value={c.id}>
                  {c.legal_name}
                </option>
              ))}
            </select>
          </FormField>
          {puede("POST", `/users/${userId || "_"}/roles`) ? (
            <AsyncButton type="submit" variant="primary" onClick={assign}>
              Asignar
            </AsyncButton>
          ) : null}
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
                    {r.name} <span className="text-text-500">({r.code})</span>
                  </span>
                  <span className="flex items-center gap-2">
                    {r.delegable ? (
                      <span className="text-xs text-text-500">Puede delegarlo</span>
                    ) : (
                      <span className="text-xs text-text-500">Fuera de su autoridad</span>
                    )}
                    {r.protected ? <span className="text-xs text-text-500">protegido</span> : null}
                  </span>
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
                  <span
                    key={r.id}
                    className="inline-flex items-center gap-1 rounded border border-border-default px-2 py-0.5 text-xs text-text-600"
                  >
                    {r.name}
                    {r.company_id ? ` · ${companyName(r.company_id)}` : ""}
                    {puede("DELETE", `/users/${u.id}/roles/${r.id}`) ? (
                      <button
                        type="button"
                        onClick={() =>
                          setToRemove({
                            uid: u.id,
                            rid: r.id,
                            label: `${u.username} · ${r.name}`,
                          })
                        }
                        className="text-text-500 hover:text-danger-600"
                        aria-label={`Quitar rol ${r.name} a ${u.username}`}
                      >
                        ×
                      </button>
                    ) : null}
                  </span>
                ))}
                {(u.roles ?? []).length === 0 ? <span className="text-xs text-text-500">sin roles</span> : null}
              </div>
            </div>
          ))}
        </section>
      </div>

      <ConfirmationDialog
        open={toRemove !== null}
        title="Quitar rol"
        description={
          toRemove
            ? `${toRemove.label}: el usuario dejará de tener ese rol. Si es su propio rol, perderá esa autoridad.`
            : ""
        }
        confirmLabel="Quitar"
        danger
        onConfirm={confirmRemove}
        onCancel={() => setToRemove(null)}
      />
    </PageContent>
  );
}
