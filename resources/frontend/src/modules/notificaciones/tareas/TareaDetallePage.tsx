/**
 * Detalle de una tarea (Spec 047 · FR-047-006, 007, §46).
 *
 * Las acciones que se pintan son las que el servidor calcula para quien mira
 * (`allowed_actions`). Reasignar envía la versión leída: si otra persona cambió
 * la tarea entretanto, el servidor responde con conflicto y la pantalla se
 * recarga, en vez de pisar el cambio ajeno.
 */
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useParams } from "react-router";

import { ApiError, apiFetch } from "@/api/client";
import { useAuth } from "@/app/contexts/AuthContext";
import { useCompany } from "@/app/contexts/CompanyContext";
import { useNotifications } from "@/app/contexts/NotificationContext";
import { AsyncButton } from "@/components/AsyncButton";
import { ErrorState } from "@/components/ErrorState";
import { FormField } from "@/components/FormField";
import { LoadingState } from "@/components/LoadingState";
import { NotFoundState } from "@/components/NotFoundState";
import { PageHeader } from "@/components/PageHeader";
import { TextInput } from "@/components/TextInput";
import { formatearFecha, t, tValor } from "@/i18n";
import { PageContent } from "@/layout/PageContent";

import { CONSULTAS, textoDeMensaje, type TareaDetalle } from "../api";
import { EnlaceOrigen, SELECTOR } from "../componentes";

interface UsuarioResumen {
  id: string;
  username: string;
}

type Accion = "start" | "complete" | "cancel" | "reassign";

export function TareaDetallePage(): React.JSX.Element {
  const { taskId = "" } = useParams();
  const { activeCompanyId } = useCompany();
  const { hasPermission } = useAuth();
  const { notify } = useNotifications();
  const qc = useQueryClient();
  const [motivo, setMotivo] = useState("");
  const [destino, setDestino] = useState("");

  const tarea = useQuery({
    queryKey: [...CONSULTAS, "tarea", activeCompanyId, taskId],
    queryFn: () => apiFetch<TareaDetalle>(`/tasks/${taskId}`),
    enabled: Boolean(activeCompanyId && taskId),
    retry: false,
  });
  const usuarios = useQuery({
    queryKey: [...CONSULTAS, "usuarios"],
    queryFn: () => apiFetch<UsuarioResumen[]>("/users"),
    enabled: hasPermission("users:view") && hasPermission("tareas:assign"),
    retry: false,
  });

  const nombre = (id: string | null): string =>
    id
      ? (usuarios.data?.find((u) => u.id === id)?.username ?? t("tarea.persona", { id: id.slice(0, 8) }))
      : t("tarea.sin_asignar");

  async function ejecutar(accion: Accion): Promise<void> {
    const actual = tarea.data;
    if (!actual) return;
    try {
      if (accion === "cancel") {
        if (!motivo.trim()) {
          notify({ type: "error", title: t("tarea.motivo_requerido") });
          return;
        }
        await apiFetch(`/tasks/${actual.id}/cancel`, { method: "POST", body: { reason: motivo.trim() } });
      } else if (accion === "reassign") {
        if (!destino) return;
        await apiFetch(`/tasks/${actual.id}/reassign`, {
          method: "POST",
          ifMatch: String(actual.version),
          body: { assignee_user_id: destino, reason: motivo.trim() || null },
        });
      } else {
        await apiFetch(`/tasks/${actual.id}/${accion}`, { method: "POST", body: {} });
      }
      notify({ type: "success", title: t("tarea.accion_hecha") });
      setMotivo("");
      setDestino("");
    } catch (e) {
      if (e instanceof ApiError && e.status === 409) {
        notify({ type: "warning", title: t("tarea.conflicto") });
      } else {
        notify({
          type: "error",
          title: t("tarea.error_accion"),
          description: e instanceof ApiError ? e.message : undefined,
        });
      }
    } finally {
      await qc.invalidateQueries({ queryKey: [...CONSULTAS] });
    }
  }

  if (tarea.isLoading) {
    return (
      <PageContent>
        <LoadingState label={t("comun.cargando")} />
      </PageContent>
    );
  }
  if (tarea.error instanceof ApiError && tarea.error.status === 404) {
    return <NotFoundState title={t("tarea.no_encontrada")} backTo="/tareas" backLabel={t("tarea.volver")} />;
  }
  if (tarea.isError || !tarea.data) {
    return (
      <PageContent>
        <ErrorState message={t("comun.error_carga")} onRetry={() => void tarea.refetch()} />
      </PageContent>
    );
  }

  const datos = tarea.data;
  const acciones = new Set(datos.allowed_actions);
  const opciones = usuarios.data
    ? usuarios.data.map((u) => ({ id: u.id, etiqueta: u.username }))
    : datos.candidates.map((id) => ({ id, etiqueta: nombre(id) }));

  return (
    <PageContent>
      <PageHeader title={t("tarea.titulo")} description={textoDeMensaje(datos.message)} />

      <section className="mb-4 rounded-lg border border-border-default bg-surface-0 p-4">
        <dl className="grid grid-cols-1 gap-x-6 gap-y-2 text-sm sm:grid-cols-2">
          <div>
            <dt className="text-text-500">{t("tarea.estado")}</dt>
            <dd data-testid="tarea-estado" className="font-medium text-text-900">
              {tValor("tareas.estado", datos.status) ?? datos.status}
            </dd>
          </div>
          <div>
            <dt className="text-text-500">{t("tarea.asignada_a")}</dt>
            <dd data-testid="tarea-asignada" className="text-text-900">{nombre(datos.assignee_user_id)}</dd>
          </div>
          <div>
            <dt className="text-text-500">{t("tarea.prioridad")}</dt>
            <dd className="text-text-900">{datos.priority_code ?? t("tareas.sin_prioridad")}</dd>
          </div>
          <div>
            <dt className="text-text-500">{t("tarea.vencimiento")}</dt>
            <dd className="text-text-900">
              {datos.due_at ? formatearFecha(datos.due_at) : t("tareas.sin_vencimiento")}
              {datos.overdue ? <span className="ml-2 font-semibold text-danger-600">{t("tareas.vencida")}</span> : null}
            </dd>
          </div>
          <div>
            <dt className="text-text-500">{t("tarea.origen")}</dt>
            <dd>
              <EnlaceOrigen enlace={datos.link} />
            </dd>
          </div>
          <div>
            <dt className="text-text-500">{t("tarea.candidatos", { count: datos.candidates.length })}</dt>
          </div>
        </dl>
      </section>

      {acciones.size > 0 ? (
        <section className="mb-4 rounded-lg border border-border-default bg-surface-0 p-4">
          <h2 className="mb-2 text-base font-semibold text-text-900">{t("tarea.acciones")}</h2>
          <p className="mb-3 text-sm text-text-500">{t("tarea.completar_aviso")}</p>
          <div className="mb-3 flex flex-wrap gap-2">
            {acciones.has("start") ? (
              <AsyncButton variant="secondary" loadingText={t("comun.procesando")} onClick={() => ejecutar("start")}>
                {t("tarea.iniciar")}
              </AsyncButton>
            ) : null}
            {acciones.has("complete") ? (
              <AsyncButton loadingText={t("comun.procesando")} onClick={() => ejecutar("complete")}>
                {t("tarea.completar")}
              </AsyncButton>
            ) : null}
          </div>
          {acciones.has("reassign") || acciones.has("cancel") ? (
            <div className="grid grid-cols-1 items-end gap-3 sm:grid-cols-3">
              <FormField label={t("tarea.motivo")}>
                <TextInput value={motivo} onChange={(e) => setMotivo(e.target.value)} />
              </FormField>
              {acciones.has("reassign") ? (
                <FormField label={t("tarea.reasignar_a")}>
                  <select value={destino} className={SELECTOR} onChange={(e) => setDestino(e.target.value)}>
                    <option value="">{t("comun.elegir")}</option>
                    {opciones.map((o) => (
                      <option key={o.id} value={o.id}>
                        {o.etiqueta}
                      </option>
                    ))}
                  </select>
                </FormField>
              ) : null}
              <div className="flex flex-wrap gap-2">
                {acciones.has("reassign") ? (
                  <AsyncButton
                    variant="secondary"
                    disabled={!destino}
                    loadingText={t("comun.procesando")}
                    onClick={() => ejecutar("reassign")}
                  >
                    {t("tarea.reasignar")}
                  </AsyncButton>
                ) : null}
                {acciones.has("cancel") ? (
                  <AsyncButton variant="secondary" loadingText={t("comun.procesando")} onClick={() => ejecutar("cancel")}>
                    {t("tarea.cancelar")}
                  </AsyncButton>
                ) : null}
              </div>
            </div>
          ) : null}
        </section>
      ) : null}

      <section className="rounded-lg border border-border-default bg-surface-0 p-4">
        <h2 className="mb-2 text-base font-semibold text-text-900">{t("tarea.historial")}</h2>
        <ol data-testid="tarea-historial" className="flex flex-col gap-2 text-sm">
          {datos.history.map((evento) => (
            <li key={evento.id} className="flex flex-wrap gap-2 border-b border-border-default pb-2">
              <span className="font-medium text-text-900">{tValor("evento", evento.event_type) ?? evento.event_type}</span>
              <span className="text-text-500">{formatearFecha(evento.occurred_at)}</span>
              <span className="text-text-700">
                {evento.actor_type === "SYSTEM" ? t("evento.sistema") : nombre(evento.actor_user_id)}
              </span>
              {evento.to_user_id ? <span className="text-text-700">→ {nombre(evento.to_user_id)}</span> : null}
              {evento.reason ? <span className="text-text-500">{evento.reason}</span> : null}
            </li>
          ))}
        </ol>
      </section>
    </PageContent>
  );
}
