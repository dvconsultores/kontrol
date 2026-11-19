import { CONSULTA_OCUPACION } from "@/modules/gobierno/api";

/** Políticas de asignación de ORG-04 (ORG-04-AUTHORITY-ASSIGNMENT-POLICY). Tipos del contrato de la API. */

export type EstadoPoliticaAsignacion = "BORRADOR" | "VIGENTE" | "CERRADA";

export interface PoliticaAsignacionResumen {
  id: string;
  codigo: string;
  numero_version: number;
  nombre: string;
  figura: string;
  figura_etiqueta: string;
  estado: EstadoPoliticaAsignacion;
  estado_etiqueta: string;
  vigente_desde: string;
  vigente_hasta: string | null;
  version: number;
  asignaciones: number;
}

export interface PoliticasAsignacionListado {
  items: PoliticaAsignacionResumen[];
  total: number;
}

export interface CompetenciaPermitida {
  accion: string;
  materia: string;
}

export interface DocumentoPoliticaAsignacion {
  document_type_id: string;
  document_type_nombre?: string;
  etapa: "ACTIVACION" | "REVOCACION";
  obligatorio: boolean;
}

export interface PisoLegal {
  codigo: string;
  fuente: string;
  version: string;
}

export interface LimiteRegla {
  valor: number;
  unidad: "DIAS" | "ANIOS";
  ambito: "TODAS" | "MAXIMA_AUTORIDAD";
  mensaje: string;
  fuente: string;
}

export interface AutorizacionRegla {
  etiqueta: string;
  ambito: "TODAS" | "MAXIMA_AUTORIDAD";
  mas_de_dias: number;
  fuente: string;
}

/** Regla aplicada: pisos legales del régimen del ente más la política vigente. La UI no codifica normas. */
export interface ReglaAsignacion {
  origen: "POLITICA" | "PISO_LEGAL" | "HISTORICA";
  origen_etiqueta: string;
  politica: { id: string; codigo: string; numero_version: number; nombre: string } | null;
  regla_version: string;
  figura: string;
  nivel_territorial: string | null;
  pisos: PisoLegal[];
  fundamentos: string[];
  exige_fin: boolean;
  limites: LimiteRegla[];
  acto_medio: { medio: string; mensaje: string } | null;
  emisor: {
    regla: "DELEGANTE" | "OTRO_CARGO" | "CUALQUIERA";
    tipo: "CUALQUIERA" | "CARGO" | "COMPETENCIA";
    position_id: string | null;
    accion: string | null;
    materia: string | null;
  };
  autorizaciones: AutorizacionRegla[];
  competencias_permitidas: CompetenciaPermitida[] | null;
  admite_avocacion: boolean;
  documentos: DocumentoPoliticaAsignacion[];
}

export interface PoliticaAsignacionHistoria {
  evento: string;
  version: number;
  fecha: string;
  actor: string | null;
}

export interface PoliticaAsignacionDetalle extends PoliticaAsignacionResumen {
  descripcion: string | null;
  fundamento: string | null;
  act_id: string | null;
  exige_fin: boolean;
  max_dias: number | null;
  acto_medio: string | null;
  emisor_tipo: "CUALQUIERA" | "CARGO" | "COMPETENCIA";
  emisor_position_id: string | null;
  emisor_competencia_accion: string | null;
  emisor_competencia_materia: string | null;
  autorizacion_requerida: boolean;
  autorizacion_etiqueta: string | null;
  autorizacion_ambito: "TODAS" | "MAXIMA_AUTORIDAD" | null;
  autorizacion_mas_de_dias: number | null;
  prohibe_avocacion: boolean;
  competencias: CompetenciaPermitida[];
  documentos: DocumentoPoliticaAsignacion[];
  regla: ReglaAsignacion;
  historia: PoliticaAsignacionHistoria[];
  versiones: { id: string; numero_version: number; estado: EstadoPoliticaAsignacion }[];
  activada_en: string | null;
  cerrada_en: string | null;
  motivo_cierre: string | null;
  version_anterior_id: string | null;
  existe_borrador: boolean;
}

export interface OpcionCodigo {
  codigo: string;
  etiqueta: string;
}

export interface PoliticaAsignacionCatalogo {
  figuras: OpcionCodigo[];
  estados: OpcionCodigo[];
  medios: OpcionCodigo[];
  emisor_tipos: OpcionCodigo[];
  ambitos: OpcionCodigo[];
  etapas: OpcionCodigo[];
  acciones: OpcionCodigo[];
  materias: OpcionCodigo[];
}

export interface PoliticaAsignacionOpciones {
  cargos: { id: string; etiqueta: string }[];
  tipos_documentales: { id: string; etiqueta: string }[];
  nivel_territorial: string | null;
  pisos: { codigo: string; fuente: string; version: string; figuras: string[]; niveles: string[] | null }[];
}

/** Cuerpo de crear y editar (PoliticaAsignacionIn). */
export interface PoliticaAsignacionEntrada {
  codigo: string;
  nombre: string;
  descripcion: string | null;
  figura: string;
  fundamento: string | null;
  act_id: string | null;
  vigente_desde: string;
  vigente_hasta: string | null;
  exige_fin: boolean;
  max_dias: number | null;
  acto_medio: string | null;
  emisor_tipo: "CUALQUIERA" | "CARGO" | "COMPETENCIA";
  emisor_position_id: string | null;
  emisor_competencia_accion: string | null;
  emisor_competencia_materia: string | null;
  autorizacion_requerida: boolean;
  autorizacion_etiqueta: string | null;
  autorizacion_ambito: "TODAS" | "MAXIMA_AUTORIDAD" | null;
  autorizacion_mas_de_dias: number | null;
  prohibe_avocacion: boolean;
  competencias: CompetenciaPermitida[];
  documentos: { document_type_id: string; etapa: "ACTIVACION" | "REVOCACION"; obligatorio: boolean }[];
}

export const CONSULTA_POLITICAS_ASIGNACION = [...CONSULTA_OCUPACION, "politicas"] as const;

/** Ruta de la API y de la pantalla (coinciden). */
export const RUTA_POLITICAS_ASIGNACION = "/gobierno/ocupacion/politicas";

export const FIGURAS_DELEGACION = ["DELEGACION_ATRIBUCIONES", "DELEGACION_FIRMA"];

export function consultaDePoliticasAsignacion(params: { estado?: string; figura?: string; q?: string } = {}): string {
  const p = new URLSearchParams();
  if (params.estado) p.set("estado", params.estado);
  if (params.figura) p.set("figura", params.figura);
  if (params.q) p.set("q", params.q);
  const s = p.toString();
  return s ? `?${s}` : "";
}

export function etiquetaDeCodigo(lista: OpcionCodigo[] | undefined, codigo: string | null | undefined): string {
  if (!codigo) return "—";
  return lista?.find((x) => x.codigo === codigo)?.etiqueta ?? codigo;
}

/** Texto de un límite de duración de la regla, para mostrarlo tal cual lo fija la regla. */
export function describirLimite(limite: LimiteRegla): string {
  const unidad = limite.unidad === "ANIOS" ? (limite.valor === 1 ? "año" : "años") : "días";
  const ambito = limite.ambito === "MAXIMA_AUTORIDAD" ? " (suplencia de la máxima autoridad)" : "";
  return `Máximo ${limite.valor} ${unidad}${ambito} · ${limite.fuente}`;
}

/** Texto de una autorización especial exigida por la regla. */
export function describirAutorizacion(a: AutorizacionRegla): string {
  const cuando = a.mas_de_dias > 0 ? `con más de ${a.mas_de_dias} días` : "siempre";
  const ambito = a.ambito === "MAXIMA_AUTORIDAD" ? " en la suplencia de la máxima autoridad" : "";
  return `${a.etiqueta}: ${cuando}${ambito} (${a.fuente})`;
}

/**
 * Autorizaciones que la regla exige a una vigencia concreta: la misma condición que valida el backend
 * (`autorizaciones_exigidas`). Sin fecha de fin, toda autorización aplicable se exige.
 */
export function autorizacionesExigidas(
  regla: ReglaAsignacion | null | undefined,
  desde: string,
  hasta: string | null,
  maximaAutoridad: boolean,
): AutorizacionRegla[] {
  if (!regla) return [];
  return regla.autorizaciones.filter((a) => {
    if (a.ambito === "MAXIMA_AUTORIDAD" && !maximaAutoridad) return false;
    if (!hasta || !desde) return true;
    const dias = Math.round((Date.parse(hasta) - Date.parse(desde)) / 86_400_000) + 1;
    return dias > a.mas_de_dias;
  });
}
