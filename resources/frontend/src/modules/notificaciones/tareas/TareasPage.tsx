/**
 * Mis tareas (Spec 047 · FR-047-005..009, 029).
 *
 * Completar una tarea no ejecuta la operación del documento: una tarea
 * «atender aprobación» se cierra cuando la aprobación ocurre de verdad en su
 * bandeja, no porque alguien la marque aquí.
 */
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Link } from "react-router";

import { apiFetch } from "@/api/client";
import { useAutoridad } from "@/app/autoridad/AutoridadContext";
import { useCompany } from "@/app/contexts/CompanyContext";
import { EmptyState } from "@/components/EmptyState";
import { ErrorState } from "@/components/ErrorState";
import { FormField } from "@/components/FormField";
import { LoadingState } from "@/components/LoadingState";
import { PageHeader } from "@/components/PageHeader";
import { Pagination } from "@/components/Pagination";
import { formatearFecha, t, tValor } from "@/i18n";
import { PageContent } from "@/layout/PageContent";

import { CONSULTAS, textoDeMensaje, type EstadoTarea, type Pagina, type Prioridad, type Tarea } from "../api";
import { SELECTOR } from "../componentes";

const AMBITOS = ["involved", "mine", "pool", "all"] as const;
const ESTADOS: EstadoTarea[] = ["OPEN", "IN_PROGRESS", "COMPLETED", "CANCELLED", "RESOLVED_BY_SOURCE"];

export function TareasPage(): React.JSX.Element {
  const { activeCompanyId } = useCompany();
  const { tiene } = useAutoridad();
  const [ambito, setAmbito] = useState<(typeof AMBITOS)[number]>("involved");
  const [estado, setEstado] = useState<EstadoTarea | "">("OPEN");
  const [soloVencidas, setSoloVencidas] = useState(false);
  const [prioridad, setPrioridad] = useState("");
  const [pagina, setPagina] = useState(0);
  const [tamano, setTamano] = useState(10);

  const parametros = new URLSearchParams({ scope: ambito, page: String(pagina + 1), page_size: String(tamano) });
  if (estado) parametros.set("status", estado);
  if (soloVencidas) parametros.set("overdue", "true");
  if (prioridad) parametros.set("priority", prioridad);

  const lista = useQuery({
    queryKey: [...CONSULTAS, "tareas", activeCompanyId, parametros.toString()],
    queryFn: () => apiFetch<Pagina<Tarea>>(`/tasks?${parametros.toString()}`),
    enabled: Boolean(activeCompanyId),
  });
  const prioridades = useQuery({
    queryKey: [...CONSULTAS, "prioridades", activeCompanyId],
    queryFn: () => apiFetch<Prioridad[]>("/tasks/priorities"),
    enabled: Boolean(activeCompanyId),
  });

  const reiniciar = (): void => setPagina(0);
  const items = lista.data?.items ?? [];

  return (
    <PageContent>
      <PageHeader title={t("tareas.titulo")} description={t("tareas.descripcion")} />

      <div className="mb-4 grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <FormField label={t("tareas.ambito")}>
          <select
            value={ambito}
            className={SELECTOR}
            onChange={(e) => {
              setAmbito(e.target.value as (typeof AMBITOS)[number]);
              reiniciar();
            }}
          >
            {AMBITOS.filter((a) => a !== "all" || tiene("tareas:view", "empresa")).map((a) => (
              <option key={a} value={a}>
                {tValor("tareas.ambito", a) ?? a}
              </option>
            ))}
          </select>
        </FormField>
        <FormField label={t("comun.filtro_estado")}>
          <select
            value={estado}
            className={SELECTOR}
            onChange={(e) => {
              setEstado(e.target.value as EstadoTarea | "");
              reiniciar();
            }}
          >
            <option value="">{t("comun.todas")}</option>
            {ESTADOS.map((valor) => (
              <option key={valor} value={valor}>
                {tValor("tareas.estado", valor) ?? valor}
              </option>
            ))}
          </select>
        </FormField>
        <FormField label={t("tareas.prioridad")}>
          <select
            value={prioridad}
            className={SELECTOR}
            onChange={(e) => {
              setPrioridad(e.target.value);
              reiniciar();
            }}
          >
            <option value="">{t("comun.todas")}</option>
            {(prioridades.data ?? []).map((p) => (
              <option key={p.id} value={p.code}>
                {p.name}
              </option>
            ))}
          </select>
        </FormField>
        <label className="flex items-center gap-2 self-end pb-2 text-sm text-text-700">
          <input
            type="checkbox"
            checked={soloVencidas}
            onChange={(e) => {
              setSoloVencidas(e.target.checked);
              reiniciar();
            }}
          />
          {t("tareas.solo_vencidas")}
        </label>
      </div>

      {lista.isLoading ? (
        <LoadingState label={t("comun.cargando")} />
      ) : lista.isError ? (
        <ErrorState message={t("comun.error_carga")} onRetry={() => void lista.refetch()} />
      ) : items.length === 0 ? (
        <EmptyState title={t("tareas.vacio")} description={t("tareas.vacio_detalle")} />
      ) : (
        <ul aria-label={t("tareas.lista")} className="flex flex-col gap-2">
          {items.map((tarea) => (
            <li key={tarea.id} data-testid="tarea" className="rounded-lg border border-border-default bg-surface-0 p-3">
              <div className="mb-1 flex flex-wrap items-center gap-2 text-xs text-text-500">
                <span className="font-medium text-text-700">{tValor("tareas.estado", tarea.status) ?? tarea.status}</span>
                <span>
                  {tarea.due_at ? t("tareas.vence", { fecha: formatearFecha(tarea.due_at) }) : t("tareas.sin_vencimiento")}
                </span>
                {tarea.overdue ? <span className="font-semibold text-danger-600">{t("tareas.vencida")}</span> : null}
                <span>{tarea.priority_code ?? t("tareas.sin_prioridad")}</span>
              </div>
              <p className="mb-2 text-sm text-text-900">{textoDeMensaje(tarea.message)}</p>
              <Link to={`/tareas/${tarea.id}`} className="text-sm font-medium text-text-900 underline underline-offset-2">
                {t("tareas.ver")}
              </Link>
            </li>
          ))}
        </ul>
      )}

      <Pagination
        pageIndex={pagina}
        pageSize={tamano}
        total={lista.data?.total ?? 0}
        onPageChange={setPagina}
        onPageSizeChange={(valor) => {
          setTamano(valor);
          reiniciar();
        }}
      />
    </PageContent>
  );
}
