import { apiFetch, ApiError } from "@/api/client";

export interface Responsable {
  funcionario: string;
  funcionario_codigo: string;
  cargo: string;
  cargo_codigo: string;
  unidad: string;
  unidad_codigo: string;
  figura: string;
  asignacion_codigo: string;
}

export interface ReceptorResumen {
  funcionario: string;
  funcionario_codigo: string;
}

export interface ActaResumen {
  id: string;
  codigo: string;
  estado: "BORRADOR" | "SUSCRITA" | "VERIFICADA";
  ambito: "ENTE" | "UNIDAD";
  unidad: string | null;
  saliente: Responsable;
  receptor: ReceptorResumen;
  fecha_corte: string;
  fecha_suscripcion: string | null;
}

export interface ActaAnexo {
  codigo: string;
  titulo: string;
  obligatorio: boolean;
  generable: boolean;
  incluir_generado: boolean;
  documento_ids: string[];
  constancia: string | null;
  resuelto: boolean;
  documentos_congelados: unknown[];
  origen: "LEGAL" | "POLITICA";
  supuesto: string | null;
  fuente: string | null;
  evidencia: EvidenciaAnexo;
  declaracion: string | null;
  document_type_id: string | null;
}

/** Tipo de evidencia con que se resuelve un anexo (D-AE-04). */
export type EvidenciaAnexo = "DOCUMENTO" | "CERTIFICACION" | "DECLARACION" | "DATO";

/** Supuesto de N34 que aplica al acta: el art. 11 siempre; los arts. 12-17 solo si la política los declara. */
export interface SupuestoRegla {
  codigo: string;
  articulo: string;
  titulo: string;
  sujeto: string;
  vinculo: "UNIVERSAL" | "DECLARADO";
  alcance: "ENTE" | "UNIDAD" | null;
  motivo: string;
  nota: string | null;
}

export interface AnexoRegla {
  codigo: string;
  titulo: string;
  obligatorio: boolean;
  generable: boolean;
  evidencia: EvidenciaAnexo;
  fuente: string | null;
  origen: "LEGAL" | "POLITICA";
  supuesto: string | null;
  document_type_id: string | null;
  document_type_nombre: string | null;
}

export type HitoPlazo = "ELABORACION" | "REMISION_UAI" | "OBSERVACIONES";

export interface PlazoRegla {
  hito: HitoPlazo;
  valor: number;
  unidad: "DIAS_HABILES" | "DIAS_CONTINUOS";
  base: "TOMA_DE_POSESION" | "SUSCRIPCION";
  fuente: string | null;
  origen: "LEGAL" | "POLITICA";
}

export interface PlazoEstado extends PlazoRegla {
  base_fecha: string | null;
  vence: string | null;
  hecho: string | null;
  estado: "REGISTRADO" | "SIN_CALENDARIO_HABIL" | "PENDIENTE" | "CUMPLIDO" | "CUMPLIDO_FUERA_DE_PLAZO" | "VENCIDO" | "EN_PLAZO";
}

/** Quién entrega y quién recibe, resuelto con Ocupación de cargos (ORG-04) y congelado en el acta. */
export interface ResponsabilidadActa {
  fecha_efectiva: string;
  ambito: "ENTE" | "UNIDAD";
  unit_id: string | null;
  saliente: {
    assignment_id: string;
    official_id: string;
    figura: string;
    cargo_id: string;
    cargo: string;
    desde: string | null;
    situacion_al_corte: string;
  };
  receptor: {
    official_id: string;
    funcionario: string;
    assignment_id: string | null;
    desde: string | null;
    situacion_al_corte: string | null;
    relacion: "SUCESOR" | "DESIGNADO";
  };
}

/** Regla aplicada al acta: catálogo legal de N34 más la política del ente. La UI no codifica normas. */
export interface ReglaActa {
  origen: "POLITICA" | "LEGAL" | "HISTORICA";
  origen_etiqueta: string;
  politica: { id: string; codigo: string; numero_version: number; nombre: string } | null;
  regla_version: string;
  norma: { codigo: string; version: string; titulo: string; instrumento: string; gaceta: string; vigente_desde: string };
  fecha: string;
  ambito: "ENTE" | "UNIDAD";
  unit_id: string | null;
  unidad: string | null;
  nivel_territorial: string | null;
  forma_organizativa: string | null;
  supuestos: SupuestoRegla[];
  anexos: AnexoRegla[];
  testigos: {
    levantada_por_receptor: { modalidad: string; testigos: number; auditor_interno: boolean; fuente: string };
    entrega: { minimo: number; fuente: string | null };
  };
  plazos: PlazoRegla[];
  numeracion: { patron: string; origen: "POLITICA" | "DEFECTO" };
  fundamentos: string[];
  avisos: string[];
  responsabilidad?: ResponsabilidadActa;
}

export interface ActaDocumento {
  id: string;
  title: string;
}

export interface ActaTestigo {
  nombre: string;
  documento: string;
}

export interface ActaObservacion {
  fecha: string;
  texto: string;
  registrada_por: string;
  registrada_en: string;
}

export interface ActaVerificacion {
  numero: string;
  fecha: string;
  resultado: "CONFORME" | "CON_OBSERVACIONES";
  fundamento: string;
  verificada_por: string;
  verificada_en: string;
}

export interface ActaFicha extends ActaResumen {
  version: string;
  modalidad: "ENTREGA" | "LEVANTADA_POR_RECEPTOR";
  testigos: ActaTestigo[];
  auditor: { funcionario: string; codigo: string } | null;
  motivo: string;
  fundamento: string;
  lugar: string;
  anexos: ActaAnexo[];
  anexos_pendientes: string[];
  documentos_del_acta: ActaDocumento[];
  errores_deficiencias: string | null;
  suscrita_por: string | null;
  suscrita_en: string | null;
  snapshot_sha256: string | null;
  informe: { sha256: string; bytes: number } | null;
  remision_uai_fecha: string | null;
  observaciones: ActaObservacion[];
  verificacion: ActaVerificacion | null;
  regla: ReglaActa;
  regla_congelada: boolean;
  responsabilidad: ResponsabilidadActa | null;
  plazos: PlazoEstado[];
}

export interface OpcionOcupacion {
  asignacion_id: string;
  codigo: string;
  funcionario: string;
  cargo: string;
  unidad: string;
  figura: string;
  estado: string;
  desde: string;
  hasta: string | null;
  fin_efectivo: string | null;
  maxima_autoridad: boolean;
}

export interface OpcionFuncionario {
  official_id: string;
  codigo: string;
  nombre: string;
}

export interface OpcionAnexo {
  codigo: string;
  titulo: string;
  obligatorio: boolean;
  generable: boolean;
}

export interface OpcionesActas {
  ocupaciones: OpcionOcupacion[];
  funcionarios: OpcionFuncionario[];
  anexos: OpcionAnexo[];
  nivel_territorial: string | null;
}

export interface ListadoActas {
  items: ActaResumen[];
  total: number;
  pagina: number;
  por_pagina: number;
}

export interface HistorialItem {
  fecha: string;
  accion: string;
  accion_etiqueta: string;
  usuario: string;
  motivo: string | null;
  version: string | null;
}

export function getOpcionesActas(): Promise<OpcionesActas> {
  return apiFetch<OpcionesActas>("/gobierno/actas-entrega/opciones");
}

export function listarActas(params: {
  estado?: string;
  ambito?: string;
  texto?: string;
  desde?: string;
  hasta?: string;
  pagina?: number;
  por_pagina?: number;
}): Promise<ListadoActas> {
  const consultaListado = new URLSearchParams();
  if (params.estado) consultaListado.set("estado", params.estado);
  if (params.ambito) consultaListado.set("ambito", params.ambito);
  if (params.texto) consultaListado.set("texto", params.texto);
  if (params.desde) consultaListado.set("desde", params.desde);
  if (params.hasta) consultaListado.set("hasta", params.hasta);
  consultaListado.set("pagina", String(params.pagina ?? 1));
  consultaListado.set("por_pagina", String(params.por_pagina ?? 20));
  return apiFetch<ListadoActas>(`/gobierno/actas-entrega/actas?${consultaListado}`);
}

export function getReglaActa(assignmentId: string, fechaCorte: string): Promise<ReglaActa> {
  const consulta = new URLSearchParams({ assignment_id: assignmentId, fecha_corte: fechaCorte });
  return apiFetch<ReglaActa>(`/gobierno/actas-entrega/regla?${consulta}`);
}

/** Testigos que exige la regla para la modalidad elegida (art. 9 o la política en la entrega). */
export function testigosExigidos(regla: ReglaActa, modalidad: "ENTREGA" | "LEVANTADA_POR_RECEPTOR"): number {
  return modalidad === regla.testigos.levantada_por_receptor.modalidad
    ? regla.testigos.levantada_por_receptor.testigos
    : regla.testigos.entrega.minimo;
}

export function getActa(id: string): Promise<ActaFicha> {
  return apiFetch<ActaFicha>(`/gobierno/actas-entrega/actas/${id}`);
}

export function crearActa(body: {
  assignment_id: string;
  receptor_official_id: string;
  receptor_assignment_id: null;
  modalidad: "ENTREGA" | "LEVANTADA_POR_RECEPTOR";
  testigos: ActaTestigo[];
  auditor_official_id: string | null;
  motivo: string;
  fundamento: string;
  lugar: string;
  fecha_corte: string;
}): Promise<ActaFicha> {
  return apiFetch<ActaFicha>("/gobierno/actas-entrega/actas", { method: "POST", body });
}

export function actualizarActa(id: string, version: string, body: {
  version: string;
  receptor_official_id: string;
  receptor_assignment_id: null;
  modalidad: "ENTREGA" | "LEVANTADA_POR_RECEPTOR";
  testigos: ActaTestigo[];
  auditor_official_id: string | null;
  motivo: string;
  fundamento: string;
  lugar: string;
  fecha_corte: string;
}): Promise<ActaFicha> {
  return apiFetch<ActaFicha>(`/gobierno/actas-entrega/actas/${id}`, { method: "PUT", body, ifMatch: version });
}

export function verAnexoGenerado(id: string, codigo: string): Promise<Record<string, unknown>> {
  return apiFetch<Record<string, unknown>>(`/gobierno/actas-entrega/actas/${id}/anexos/${codigo}/vista`);
}

export function actualizarAnexo(id: string, codigo: string, body: {
  incluir_generado?: boolean;
  documento_ids?: string[];
  constancia?: string;
  declaracion?: string;
}): Promise<ActaFicha> {
  return apiFetch<ActaFicha>(`/gobierno/actas-entrega/actas/${id}/anexos/${codigo}`, { method: "PUT", body });
}

export function suscribirActa(id: string, body: { fecha_suscripcion: string; errores_deficiencias: string | null }): Promise<ActaFicha> {
  return apiFetch<ActaFicha>(`/gobierno/actas-entrega/actas/${id}/suscribir`, { method: "POST", body });
}

export function remitirActa(id: string, body: { fecha: string }): Promise<ActaFicha> {
  return apiFetch<ActaFicha>(`/gobierno/actas-entrega/actas/${id}/remision`, { method: "POST", body });
}

export function observarActa(id: string, body: { fecha: string; texto: string }): Promise<ActaFicha> {
  return apiFetch<ActaFicha>(`/gobierno/actas-entrega/actas/${id}/observaciones`, { method: "POST", body });
}

export function verificarActa(id: string, body: { numero: string; fecha: string; resultado: "CONFORME" | "CON_OBSERVACIONES"; fundamento: string }): Promise<ActaFicha> {
  return apiFetch<ActaFicha>(`/gobierno/actas-entrega/actas/${id}/verificacion`, { method: "POST", body });
}


export function getIntegridadActa(id: string): Promise<Record<string, unknown>> {
  return apiFetch<Record<string, unknown>>(`/gobierno/actas-entrega/actas/${id}/integridad`);
}

export function getHistorialActa(id: string): Promise<{ items: HistorialItem[] }> {
  return apiFetch<{ items: HistorialItem[] }>(`/gobierno/actas-entrega/actas/${id}/historial`);
}

export { ApiError };
