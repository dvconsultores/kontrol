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
 * este módulo. `q` sigue viajando cuando la pantalla lo envía: la búsqueda
 * de auditoría es una decisión pendiente (`UI-BUSQUEDA-MUERTA`), no parte
 * de este contrato.
 */
import { apiFetch } from "@/api/client";
import type { AuditEvent, PagedResult } from "@/api/types";

export type AuditEventPage = PagedResult<AuditEvent>;

export interface ConsultaDeAuditoria {
  q?: string;
  page?: number;
  page_size?: number;
}

export function listAuditEvents(consulta: ConsultaDeAuditoria = {}): Promise<AuditEventPage> {
  const params = new URLSearchParams();
  if (consulta.q) params.set("q", consulta.q);
  params.set("page", String(consulta.page ?? 1));
  params.set("page_size", String(consulta.page_size ?? 20));
  return apiFetch<AuditEventPage>(`/audit/events?${params.toString()}`);
}
