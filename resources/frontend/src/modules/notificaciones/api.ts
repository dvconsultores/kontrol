/**
 * Contratos de la API de la Spec 047 y utilidades de presentación.
 *
 * El servidor es la autoridad: los contadores, la visibilidad y las acciones
 * permitidas vienen de él. Aquí no se cuenta ni se decide nada.
 */
import { t, tValor } from "@/i18n";

export type Severidad = "INFO" | "WARNING" | "CRITICAL";
export type EstadoTarea = "OPEN" | "IN_PROGRESS" | "COMPLETED" | "CANCELLED" | "RESOLVED_BY_SOURCE";

export interface Mensaje {
  key: string;
  params: Record<string, unknown>;
  text: string | null;
  render_error: string | null;
}

export interface Enlace {
  source_type: string;
  source_id: string;
  source_item_id: string | null;
  route_key: string;
}

export interface Pagina<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}

export interface Notificacion {
  id: string;
  category: string;
  severity: Severidad;
  mandatory: boolean;
  message: Mensaje;
  link: Enlace;
  created_at: string;
  read_at: string | null;
  archived_at: string | null;
}

export interface Tarea {
  id: string;
  task_type: string;
  status: EstadoTarea;
  message: Mensaje;
  link: Enlace;
  priority_code: string | null;
  priority_rank: number | null;
  assignee_user_id: string | null;
  due_at: string | null;
  overdue: boolean;
  closed_at: string | null;
  version: number;
  created_at: string;
}

export interface EventoTarea {
  id: string;
  event_type: string;
  actor_type: "SYSTEM" | "USER";
  actor_user_id: string | null;
  from_user_id: string | null;
  to_user_id: string | null;
  reason: string | null;
  occurred_at: string;
}

export interface TareaDetalle extends Tarea {
  candidates: string[];
  history: EventoTarea[];
  allowed_actions: string[];
}

export interface Alerta {
  id: string;
  category: string;
  severity: Severidad;
  status: "ACTIVE" | "RESOLVED";
  message: Mensaje;
  link: Enlace;
  created_at: string;
  resolved_at: string | null;
}

export interface Contadores {
  unread_notifications: number;
  open_tasks: number;
  overdue_tasks: number;
  active_alerts: number;
}

export interface Regla {
  id: string;
  code: string;
  source: string;
  event_type: string;
  effect: "NOTIFICATION" | "TASK" | "ALERT";
  severity: Severidad;
  mandatory: boolean;
  priority_code: string | null;
  reminder_offset_minutes: number | null;
  reminder_repeat_minutes: number | null;
  escalation_after_minutes: number | null;
  escalation_role_id: string | null;
  auto_close: boolean;
  active: boolean;
  created_at: string;
}

export interface Fuente {
  source: string;
  event_type: string;
  effects: string[];
}

export interface Prioridad {
  id: string;
  code: string;
  name: string;
  rank: number;
}

export interface Preferencia {
  category: string;
  channel: "INTERNAL" | "EMAIL";
  enabled: boolean;
  mandatory: boolean;
  available: boolean;
}

/** Sondeo de la campana. No hay WebSocket ni SSE en KONTROL (§50). */
export const INTERVALO_SONDEO_MS = 60_000;

/** Raíz de todas las consultas de la 047: invalidarla refresca también la campana. */
export const CONSULTAS = ["notificaciones"] as const;

export function textoDeMensaje(mensaje: Mensaje): string {
  return mensaje.text ?? t("comun.mensaje_no_disponible");
}

const ENLACES: Record<string, { ruta: (enlace: Enlace) => string; permiso: string }> = {
  approval_inbox: { ruta: () => "/aprobaciones/bandeja", permiso: "aprobaciones:view" },
};

/** Adónde lleva el origen y qué permiso exige. `null` si la ruta no se conoce. */
export function destinoDeEnlace(enlace: Enlace): { ruta: string; permiso: string } | null {
  const destino = ENLACES[enlace.route_key];
  return destino ? { ruta: destino.ruta(enlace), permiso: destino.permiso } : null;
}

export function etiquetaCategoria(categoria: string): string {
  return tValor("categoria", categoria) ?? categoria;
}
