import { apiFetch, ApiError } from "@/api/client";

export interface ResponsableOpcion {
  asignacion_id: string;
  codigo: string;
  funcionario: string;
  cargo: string;
  unidad: string;
  figura: string;
  desde: string;
  hasta: string | null;
  official_id: string;
  unidad_id: string | null;
}

export interface ProcesoOpcion {
  codigo: string;
  nombre: string;
}

export interface OpcionesRendicion {
  responsables: ResponsableOpcion[];
  procesos: ProcesoOpcion[];
  estados: string[];
}

export interface ObjetoEvento {
  tipo: string;
  id: string;
  ruta: string;
  capacidad: string;
}

export interface DocumentoPieza {
  documento_id: string;
  version_id: string;
  sha256: string;
}

export interface Pieza {
  id: string;
  ordinal: number | null;
  evento_id: string;
  fecha: string;
  proceso: string;
  proceso_nombre: string;
  accion: string;
  accion_etiqueta: string;
  entidad: string;
  entidad_id: string | null;
  usuario: string;
  referencia: string;
  objeto: ObjetoEvento | null;
  documentos: DocumentoPieza[];
  huella: string;
  ruta_evento: string;
}

export interface ResponsableCongelado {
  funcionario: string;
  funcionario_codigo: string;
  cargo: string;
  cargo_codigo: string;
  unidad: string;
  unidad_codigo: string;
  figura: string;
  asignacion_codigo: string;
}

export interface Participacion {
  fecha: string;
  oficio: string;
  vence: string;
  en_plazo: boolean;
  registrada_por: string;
  registrada_en: string;
}

export interface Calificacion {
  resultado: "CONFORME" | "OBJETADA";
  organo: string;
  informe_numero: string;
  informe_fecha: string;
  fundamento: string;
  registrada_por: string;
  registrada_en: string;
}

export interface Fenecimiento {
  auto_numero: string;
  auto_fecha: string;
  fundamento: string | null;
  registrado_por: string;
  registrado_en: string;
}

export interface Hallazgo {
  ordinal: number;
  referencia: string;
  objeto: ObjetoEvento | null;
}

export interface FichaRendicion {
  id: string;
  codigo: string;
  numero_version: number;
  version: string;
  estado: string;
  anterior_id: string | null;
  sustituido_por_id: string | null;
  sustitucion_motivo: string | null;
  denominacion: string;
  ejercicio: number | null;
  periodo_desde: string;
  periodo_hasta: string;
  fecha_corte: string;
  observaciones: string | null;
  ente: string;
  responsable: ResponsableCongelado;
  piezas: Pieza[];
  formado_en: string | null;
  formado_por: string | null;
  snapshot_sha256: string | null;
  informe: { sha256: string; bytes: number } | null;
  participacion: Participacion | null;
  plazo_participacion: string;
  calificacion: Calificacion | null;
  fenecimiento: Fenecimiento | null;
  hallazgos: Hallazgo[];
}

export interface CandidataPieza {
  evento_id: string;
  fecha: string;
  proceso: string;
  proceso_nombre: string;
  accion: string;
  accion_etiqueta: string;
  usuario: string;
  referencia: string;
  objeto: ObjetoEvento | null;
  incluida: boolean;
}

export interface ResumenReporte {
  concepto: string;
  fuente: string;
  filtro: string;
  periodo: string;
  conjunto: string;
  regla: string;
  resultado: number | string;
}

export interface ReporteRendicion {
  provisional: boolean;
  generado_en: string | null;
  expediente: Record<string, unknown>;
  ente: string;
  responsable: ResponsableCongelado;
  piezas: Pieza[];
  resumen: ResumenReporte[];
  hallazgos: Hallazgo[];
  snapshot_sha256: string | null;
}

export interface IntegridadPieza {
  ordinal: number;
  estado: "VIGENTE" | "DESAPARECIDA" | "ALTERADA" | "SIN_EVIDENCIA";
  detalle: string;
}

export interface Integridad {
  estado: "VALIDO" | "INCOMPLETO";
  snapshot_ok: boolean;
  informe_ok: boolean;
  piezas: IntegridadPieza[];
}

export interface HistorialItem {
  fecha: string;
  accion: string;
  accion_etiqueta: string;
  usuario: string;
  motivo: string | null;
  version: string | null;
}

export interface Paginado<T> {
  items: T[];
  total: number;
  pagina: number;
  por_pagina: number;
}

export function getOpcionesRendicion(): Promise<OpcionesRendicion> {
  return apiFetch<OpcionesRendicion>("/gobierno/rendicion/opciones");
}

export function listarExpedientes(params: {
  estado?: string;
  texto?: string;
  desde?: string;
  hasta?: string;
  responsable?: string;
  unidad?: string;
  pagina?: number;
  por_pagina?: number;
}): Promise<Paginado<FichaRendicion>> {
  const consultaListado = new URLSearchParams();
  if (params.estado) consultaListado.set("estado", params.estado);
  if (params.texto) consultaListado.set("texto", params.texto);
  if (params.desde) consultaListado.set("desde", params.desde);
  if (params.hasta) consultaListado.set("hasta", params.hasta);
  if (params.responsable) consultaListado.set("responsable", params.responsable);
  if (params.unidad) consultaListado.set("unidad", params.unidad);
  consultaListado.set("pagina", String(params.pagina ?? 1));
  consultaListado.set("por_pagina", String(params.por_pagina ?? 20));
  return apiFetch<Paginado<FichaRendicion>>(`/gobierno/rendicion/expedientes?${consultaListado}`);
}

export function crearExpediente(body: {
  denominacion: string;
  ejercicio?: number;
  periodo_desde: string;
  periodo_hasta: string;
  fecha_corte: string;
  assignment_id: string;
  observaciones?: string;
}): Promise<FichaRendicion> {
  return apiFetch<FichaRendicion>("/gobierno/rendicion/expedientes", { method: "POST", body });
}

export function getExpediente(id: string): Promise<FichaRendicion> {
  return apiFetch<FichaRendicion>(`/gobierno/rendicion/expedientes/${id}`);
}

export function listarCandidatas(
  id: string,
  params: { proceso?: string; texto?: string; pagina?: number; por_pagina?: number },
): Promise<Paginado<CandidataPieza>> {
  const consultaCandidatas = new URLSearchParams();
  if (params.proceso) consultaCandidatas.set("proceso", params.proceso);
  if (params.texto) consultaCandidatas.set("texto", params.texto);
  consultaCandidatas.set("pagina", String(params.pagina ?? 1));
  consultaCandidatas.set("por_pagina", String(params.por_pagina ?? 10));
  return apiFetch<Paginado<CandidataPieza>>(`/gobierno/rendicion/expedientes/${id}/candidatas?${consultaCandidatas}`);
}

export function incorporarPieza(id: string, eventoId: string): Promise<Pieza> {
  return apiFetch<Pieza>(`/gobierno/rendicion/expedientes/${id}/piezas`, { method: "POST", body: { evento_id: eventoId } });
}

export function retirarPieza(id: string, piezaId: string): Promise<void> {
  return apiFetch<void>(`/gobierno/rendicion/expedientes/${id}/piezas/${piezaId}`, { method: "DELETE" });
}

export function formarCuenta(id: string): Promise<FichaRendicion> {
  return apiFetch<FichaRendicion>(`/gobierno/rendicion/expedientes/${id}/formar`, { method: "POST", body: {} });
}

export function getReporte(id: string): Promise<ReporteRendicion> {
  return apiFetch<ReporteRendicion>(`/gobierno/rendicion/expedientes/${id}/reporte`);
}

export function getIntegridad(id: string): Promise<Integridad> {
  return apiFetch<Integridad>(`/gobierno/rendicion/expedientes/${id}/integridad`);
}

export function registrarParticipacion(id: string, body: { fecha: string; oficio: string }): Promise<FichaRendicion> {
  return apiFetch<FichaRendicion>(`/gobierno/rendicion/expedientes/${id}/participacion`, { method: "POST", body });
}

export function registrarCalificacion(
  id: string,
  body: { resultado: "CONFORME" | "OBJETADA"; organo: string; informe_numero: string; informe_fecha: string; fundamento: string },
): Promise<FichaRendicion> {
  return apiFetch<FichaRendicion>(`/gobierno/rendicion/expedientes/${id}/calificacion`, { method: "POST", body });
}

export function registrarFenecimiento(
  id: string,
  body: { auto_numero: string; auto_fecha: string; fundamento?: string },
): Promise<FichaRendicion> {
  return apiFetch<FichaRendicion>(`/gobierno/rendicion/expedientes/${id}/fenecimiento`, { method: "POST", body });
}

export function nuevaVersion(id: string, body: { motivo: string }): Promise<FichaRendicion> {
  return apiFetch<FichaRendicion>(`/gobierno/rendicion/expedientes/${id}/nueva-version`, { method: "POST", body });
}

export function actualizarExpediente(id: string, version: string, body: { denominacion: string; ejercicio?: number; periodo_desde: string; periodo_hasta: string; fecha_corte: string; assignment_id: string; observaciones?: string }): Promise<FichaRendicion> {
  return apiFetch<FichaRendicion>(`/gobierno/rendicion/expedientes/${id}`, { method: "PUT", body, ifMatch: version });
}

export function getHistorial(id: string): Promise<{ items: HistorialItem[] }> {
  return apiFetch<{ items: HistorialItem[] }>(`/gobierno/rendicion/expedientes/${id}/historial`);
}

export { ApiError };
