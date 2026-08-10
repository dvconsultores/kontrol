/** Sesiones — sesiones activas del usuario y revocación (FR-001-014). */
import { useQuery, useQueryClient } from "@tanstack/react-query";

import { apiFetch } from "@/api/client";
import { useNotifications } from "@/app/contexts/NotificationContext";
import { AsyncButton } from "@/components/AsyncButton";
import { PageContent } from "@/layout/PageContent";
import { PageHeader } from "@/components/PageHeader";

interface SessionSummary {
  id: string;
  ip: string | null;
  user_agent: string | null;
  created_at: string;
  expires_at: string;
  revoked: boolean;
}

export function SesionesPage(): React.JSX.Element {
  const queryClient = useQueryClient();
  const { notify } = useNotifications();

  const query = useQuery({
    queryKey: ["security", "sessions"],
    queryFn: () => apiFetch<SessionSummary[]>("/auth/sessions"),
    retry: false,
  });

  const revoke = async (id: string): Promise<void> => {
    try {
      await apiFetch(`/auth/sessions/${id}`, { method: "DELETE" });
      notify({ type: "success", title: "Sesión revocada", description: "La sesión ya no es válida." });
      void queryClient.invalidateQueries({ queryKey: ["security", "sessions"] });
    } catch (err) {
      const message = err instanceof Error ? err.message : "No fue posible revocar la sesión";
      notify({ type: "error", title: "No fue posible revocar la sesión", description: message });
    }
  };

  const row = (key: string, label: string, value: string, action?: React.JSX.Element): React.JSX.Element => (
    <div key={key} className="flex items-center justify-between border-b border-border-default px-4 py-2 text-sm last:border-b-0">
      <div>
        <span className="text-text-700">{label}</span>
        <span className="ml-2 text-text-500">{value}</span>
      </div>
      {action}
    </div>
  );

  return (
    <PageContent maxWidth="full">
      <PageHeader
        title="Sesiones"
        description="Sesiones activas de su cuenta. Puede revocar las que no reconozca."
        crumbs={[{ label: "Seguridad" }, { label: "Sesiones" }]}
      />

      <section className="rounded-lg border border-border-default bg-surface-0 p-4">
        <h2 className="mb-2 text-base font-semibold text-text-900">Mis sesiones</h2>
        <div>
          {query.isLoading ? <p className="text-sm text-text-500">Cargando…</p> : null}
          {query.isError ? <p className="text-sm text-danger-600" role="alert">No fue posible cargar las sesiones.</p> : null}
          {(query.data ?? []).map((s) =>
            row(
              s.id,
              s.revoked ? "Revocada" : "Activa",
              `${s.ip ?? "—"} · ${s.user_agent ?? ""} · vence ${new Date(s.expires_at).toLocaleString("es-VE")}`.trim(),
              s.revoked ? undefined : (
                <AsyncButton variant="ghost" size="sm" onClick={() => revoke(s.id)}>
                  Revocar
                </AsyncButton>
              ),
            ),
          )}
          {query.isSuccess && (query.data ?? []).length === 0 ? <p className="text-sm text-text-500">Sin sesiones.</p> : null}
        </div>
      </section>
    </PageContent>
  );
}
