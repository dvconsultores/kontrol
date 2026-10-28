/**
 * Auditoría — el listado de eventos, con su contrato de respuesta declarado.
 *
 * `GET /audit/events` responde un sobre paginado, `{items, total, page,
 * page_size}`, y no un array. La pantalla lo pedía como `AuditEvent[]` y
 * `apiFetch` no podía contradecirla: su genérico es una afirmación de quien
 * llama, no una comprobación. Con la respuesta tipada aquí, quien vuelva a
 * tratar el sobre como array deja de compilar.
 *
 * La página y su tamaño viajan siempre, con los valores por defecto del
 * contrato (`page` desde 1, `page_size` hasta 100): así la ruta es una
 * plantilla plana y la guarda de completitud puede leer qué endpoint pide
 * este módulo. `q` desaparece (UI-BUSQUEDA-MUERTA cerrada en 04 con filtros
 * reales, GOV-CTL-005).
 */
import { apiFetch } from "@/api/client";
import type { AuditEvent, AuditFilters, PagedResult } from "@/api/types";

export type AuditEventPage = PagedResult<AuditEvent>;

export interface ConsultaDeAuditoria {
  page?: number;
  page_size?: number;
  desde?: string;
  hasta?: string;
  action?: string;
  entity_type?: string;
  entity_id?: string;
  username?: string;
  company_id?: string;
  scope?: "TENANT" | "COMPANY";
  request_id?: string;
}

export function listAuditEvents(consulta: ConsultaDeAuditoria = {}): Promise<AuditEventPage> {
  const params = new URLSearchParams();
  params.set("page", String(consulta.page ?? 1));
  params.set("page_size", String(consulta.page_size ?? 20));
  if (consulta.desde) params.set("desde", consulta.desde);
  if (consulta.hasta) params.set("hasta", consulta.hasta);
  if (consulta.action) params.set("action", consulta.action);
  if (consulta.entity_type) params.set("entity_type", consulta.entity_type);
  if (consulta.entity_id) params.set("entity_id", consulta.entity_id);
  if (consulta.username) params.set("username", consulta.username);
  if (consulta.company_id) params.set("company_id", consulta.company_id);
  if (consulta.scope) params.set("scope", consulta.scope);
  if (consulta.request_id) params.set("request_id", consulta.request_id);
  return apiFetch<AuditEventPage>(`/audit/events?${params.toString()}`);
}

export function getAuditFilters(): Promise<AuditFilters> {
  return apiFetch<AuditFilters>("/audit/filters");
}
