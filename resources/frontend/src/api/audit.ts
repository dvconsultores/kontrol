/**
 * Auditoría — el listado de eventos, con su contrato de respuesta declarado.
 *
 * `GET /audit/events` responde un sobre paginado, `{items, total, page,
 * page_size}`, y no un array. La pantalla lo pedía como `AuditEvent[]` y
 * `apiFetch` no podía contradecirla: su genérico es una afirmación de quien
 * llama, no una comprobación. Con la respuesta tipada aquí, quien vuelva a
 * tratar el sobre como array deja de compilar.
 *
 * `q` sigue viajando tal cual lo enviaba la pantalla: la búsqueda de auditoría
 * es una decisión pendiente (`UI-BUSQUEDA-MUERTA`), no parte de este contrato.
 */
import { apiFetch } from "@/api/client";
import type { AuditEvent, PagedResult } from "@/api/types";

export type AuditEventPage = PagedResult<AuditEvent>;

export function listAuditEvents(search: string): Promise<AuditEventPage> {
  return apiFetch<AuditEventPage>(`/audit/events?q=${encodeURIComponent(search)}`);
}
