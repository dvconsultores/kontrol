/**
 * Reglas de aviso (Spec 047 · FR-047-009, 024, 025).
 *
 * Una regla dice qué hacer con un hecho que registra otra área —avisar, crear
 * una tarea o una alerta— y, si es una tarea, cuándo recordarla y a quién
 * escalarla. Nunca decide si el hecho ocurre: eso es de la dueña del hecho.
 */
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { ApiError, apiFetch } from "@/api/client";
import { useAutoridad } from "@/app/autoridad/AutoridadContext";
import { useCompany } from "@/app/contexts/CompanyContext";
import { useNotifications } from "@/app/contexts/NotificationContext";
import { AsyncButton } from "@/components/AsyncButton";
import { EmptyState } from "@/components/EmptyState";
import { ErrorState } from "@/components/ErrorState";
import { ForbiddenState } from "@/components/ForbiddenState";
import { FormField } from "@/components/FormField";
import { LoadingState } from "@/components/LoadingState";
import { PageHeader } from "@/components/PageHeader";
import { TextInput } from "@/components/TextInput";
import { t, tValor } from "@/i18n";
import { PageContent } from "@/layout/PageContent";

import { CONSULTAS, etiquetaCategoria, type Fuente, type Prioridad, type Regla, type Severidad } from "../api";
import { SELECTOR } from "../componentes";

interface RolResumen {
  id: string;
  code: string;
  name: string;
}

const SEVERIDADES: Severidad[] = ["INFO", "WARNING", "CRITICAL"];

const minutos = (valor: string): number | null => (valor.trim() === "" ? null : Number(valor));

export function ReglasPage(): React.JSX.Element {
  const { activeCompanyId } = useCompany();
  const { tiene, puede } = useAutoridad();
  const { notify } = useNotifications();
  const qc = useQueryClient();
  const permitido = tiene("notificaciones:configure", "empresa");

  const [codigo, setCodigo] = useState("");
  const [evento, setEvento] = useState("");
  const [efecto, setEfecto] = useState("");
  const [severidad, setSeveridad] = useState<Severidad>("INFO");
  const [obligatoria, setObligatoria] = useState(false);
  const [cierre, setCierre] = useState(false);
  const [prioridad, setPrioridad] = useState("");
  const [recordar, setRecordar] = useState("");
  const [repetir, setRepetir] = useState("");
  const [escalarTras, setEscalarTras] = useState("");
  const [escalarRol, setEscalarRol] = useState("");

  const reglas = useQuery({
    queryKey: [...CONSULTAS, "reglas", activeCompanyId],
    queryFn: () => apiFetch<Regla[]>("/notifications/rules"),
    enabled: Boolean(activeCompanyId) && permitido,
    retry: false,
  });
  const fuentes = useQuery({
    queryKey: [...CONSULTAS, "fuentes", activeCompanyId],
    queryFn: () => apiFetch<Fuente[]>("/notifications/sources"),
    enabled: Boolean(activeCompanyId) && permitido,
  });
  const prioridades = useQuery({
    queryKey: [...CONSULTAS, "prioridades", activeCompanyId],
    queryFn: () => apiFetch<Prioridad[]>("/tasks/priorities"),
    enabled: Boolean(activeCompanyId) && permitido,
  });
  const roles = useQuery({
    queryKey: [...CONSULTAS, "roles"],
    queryFn: () => apiFetch<{ items: RolResumen[] }>("/roles"),
    enabled: permitido && puede("GET", "/roles"),
  });

  if (!permitido || (reglas.error instanceof ApiError && reglas.error.status === 403)) {
    return <ForbiddenState />;
  }

  const fuente = (fuentes.data ?? []).find((f) => `${f.source}|${f.event_type}` === evento);
  const esTarea = efecto === "TASK";

  async function crear(): Promise<void> {
    if (!codigo.trim() || !fuente || !efecto) {
      notify({ type: "error", title: t("reglas.codigo_requerido") });
      return;
    }
    try {
      await apiFetch("/notifications/rules", {
        method: "POST",
        body: {
          code: codigo.trim(),
          source: fuente.source,
          event_type: fuente.event_type,
          effect: efecto,
          severity: severidad,
          mandatory: obligatoria,
          auto_close: cierre,
          priority_code: esTarea && prioridad ? prioridad : null,
          reminder_offset_minutes: esTarea ? minutos(recordar) : null,
          reminder_repeat_minutes: esTarea ? minutos(repetir) : null,
          escalation_after_minutes: esTarea ? minutos(escalarTras) : null,
          escalation_role_id: esTarea && escalarRol ? escalarRol : null,
        },
      });
      notify({ type: "success", title: t("reglas.creada") });
      setCodigo("");
      await qc.invalidateQueries({ queryKey: [...CONSULTAS, "reglas"] });
    } catch (e) {
      notify({ type: "error", title: t("reglas.error"), description: e instanceof ApiError ? e.message : undefined });
    }
  }

  async function desactivar(regla: Regla): Promise<void> {
    try {
      await apiFetch(`/notifications/rules/${regla.id}/deactivate`, { method: "POST", body: {} });
      notify({ type: "success", title: t("reglas.desactivada") });
      await qc.invalidateQueries({ queryKey: [...CONSULTAS, "reglas"] });
    } catch (e) {
      notify({ type: "error", title: t("reglas.error"), description: e instanceof ApiError ? e.message : undefined });
    }
  }

  const lista = reglas.data ?? [];

  return (
    <PageContent>
      <PageHeader title={t("reglas.titulo")} description={t("reglas.descripcion")} />

      {puede("POST", "/notifications/rules") ? (
      <section className="mb-4 rounded-lg border border-border-default bg-surface-0 p-4">
        <h2 className="mb-3 text-base font-semibold text-text-900">{t("reglas.nueva")}</h2>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
          <FormField label={t("reglas.codigo")} required>
            <TextInput value={codigo} onChange={(e) => setCodigo(e.target.value)} />
          </FormField>
          <FormField label={t("reglas.evento")} required>
            <select
              value={evento}
              className={SELECTOR}
              onChange={(e) => {
                setEvento(e.target.value);
                setEfecto("");
              }}
            >
              <option value="">{t("comun.elegir")}</option>
              {(fuentes.data ?? []).map((f) => (
                <option key={`${f.source}|${f.event_type}`} value={`${f.source}|${f.event_type}`}>
                  {etiquetaCategoria(f.event_type)}
                </option>
              ))}
            </select>
          </FormField>
          <FormField label={t("reglas.efecto")} required>
            <select value={efecto} className={SELECTOR} onChange={(e) => setEfecto(e.target.value)}>
              <option value="">{t("comun.elegir")}</option>
              {(fuente?.effects ?? []).map((valor) => (
                <option key={valor} value={valor}>
                  {tValor("reglas.efecto", valor) ?? valor}
                </option>
              ))}
            </select>
          </FormField>
          <FormField label={t("reglas.severidad")}>
            <select value={severidad} className={SELECTOR} onChange={(e) => setSeveridad(e.target.value as Severidad)}>
              {SEVERIDADES.map((valor) => (
                <option key={valor} value={valor}>
                  {tValor("severidad", valor) ?? valor}
                </option>
              ))}
            </select>
          </FormField>
          <label className="flex items-center gap-2 self-end pb-2 text-sm text-text-700">
            <input type="checkbox" checked={obligatoria} onChange={(e) => setObligatoria(e.target.checked)} />
            {t("reglas.obligatoria")}
          </label>
          <label className="flex items-center gap-2 self-end pb-2 text-sm text-text-700">
            <input type="checkbox" checked={cierre} onChange={(e) => setCierre(e.target.checked)} />
            {t("reglas.cierre")}
          </label>
        </div>

        {esTarea ? (
          <fieldset className="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
            <legend className="mb-1 text-sm font-medium text-text-700">{t("reglas.solo_tareas")}</legend>
            <FormField label={t("tareas.prioridad")}>
              <select value={prioridad} className={SELECTOR} onChange={(e) => setPrioridad(e.target.value)}>
                <option value="">{t("comun.ninguno")}</option>
                {(prioridades.data ?? []).map((p) => (
                  <option key={p.id} value={p.code}>
                    {p.name}
                  </option>
                ))}
              </select>
            </FormField>
            <FormField label={t("reglas.recordar_antes")}>
              <TextInput type="number" min={0} value={recordar} onChange={(e) => setRecordar(e.target.value)} />
            </FormField>
            <FormField label={t("reglas.repetir_cada")}>
              <TextInput type="number" min={1} value={repetir} onChange={(e) => setRepetir(e.target.value)} />
            </FormField>
            <FormField label={t("reglas.escalar_tras")}>
              <TextInput type="number" min={1} value={escalarTras} onChange={(e) => setEscalarTras(e.target.value)} />
            </FormField>
            <FormField label={t("reglas.escalar_a")}>
              <select value={escalarRol} className={SELECTOR} onChange={(e) => setEscalarRol(e.target.value)}>
                <option value="">{t("comun.ninguno")}</option>
                {(roles.data?.items ?? []).map((r) => (
                  <option key={r.id} value={r.id}>
                    {r.name}
                  </option>
                ))}
              </select>
            </FormField>
          </fieldset>
        ) : null}

        <div className="mt-3">
          <AsyncButton loadingText={t("comun.procesando")} onClick={crear}>
            {t("reglas.crear")}
          </AsyncButton>
        </div>
      </section>
      ) : null}

      <section>
        <h2 className="mb-2 text-base font-semibold text-text-900">{t("reglas.lista")}</h2>
        {reglas.isLoading ? (
          <LoadingState label={t("comun.cargando")} />
        ) : reglas.isError ? (
          <ErrorState message={t("comun.error_carga")} onRetry={() => void reglas.refetch()} />
        ) : lista.length === 0 ? (
          <EmptyState title={t("reglas.vacio")} />
        ) : (
          <ul className="flex flex-col gap-2">
            {lista.map((r) => (
              <li
                key={r.id}
                className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-border-default bg-surface-0 p-3 text-sm"
              >
                <div className="flex flex-wrap items-center gap-2">
                  <span className="font-mono text-text-900">{r.code}</span>
                  <span className="text-text-700">{etiquetaCategoria(r.event_type)}</span>
                  <span className="text-text-700">{tValor("reglas.efecto", r.effect) ?? r.effect}</span>
                  <span className="text-text-500">{tValor("severidad", r.severity) ?? r.severity}</span>
                  <span className="text-text-500">{r.active ? t("reglas.activa") : t("reglas.inactiva")}</span>
                </div>
                {r.active && puede("POST", `/notifications/rules/${r.id}/deactivate`) ? (
                  <AsyncButton size="sm" variant="secondary" loadingText={t("comun.procesando")} onClick={() => desactivar(r)}>
                    {t("reglas.desactivar")}
                  </AsyncButton>
                ) : null}
              </li>
            ))}
          </ul>
        )}
      </section>
    </PageContent>
  );
}
