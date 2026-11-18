import { CONSULTA_COMISIONES } from "@/modules/gobierno/api";

export interface PoliticaComisionResumen {
  id: string;
  codigo: string;
  numero_version: number;
  nombre: string;
  tipo_comision: string;
  base_normativa: string;
  estado: "BORRADOR" | "VIGENTE" | "CERRADA";
  vigente_desde: string;
  vigente_hasta: string | null;
  aplica_apertura: boolean;
  aplica_recomendacion: boolean;
  version: number;
  comisiones: number;
}

export interface PoliticasComisionListado {
  items: PoliticaComisionResumen[];
  total: number;
}

export interface RequisitoPolitica {
  orden: number;
  etiqueta: string;
  funcion: string;
  condicion: string;
  tipo: string;
  area: string | null;
  area_etiqueta: string | null;
  position_id: string | null;
  position_nombre: string | null;
  unit_id: string | null;
  unit_nombre: string | null;
  competencia_accion: string | null;
  competencia_materia: string | null;
  official_id: string | null;
  official_nombre: string | null;
  minimo: number;
  maximo: number | null;
}

export interface DocumentoPolitica {
  document_type_id: string;
  document_type_nombre: string;
  etapa: string;
  obligatorio: boolean;
  condicion: string | null;
}

export interface MayoriaPolitica {
  tipo: string;
  cantidad: number | null;
  numerador: number | null;
  denominador: number | null;
}

export interface PoliticaComisionDetalle extends PoliticaComisionResumen {
  descripcion: string | null;
  fundamento: string | null;
  min_principales: number;
  max_principales: number | null;
  exige_impar: boolean;
  suplente_por_principal: boolean;
  exige_secretario: boolean;
  exige_suplente_secretario: boolean;
  exige_presidente: boolean;
  quorum: MayoriaPolitica;
  decision: MayoriaPolitica & { base: string };
  presidente_vota: boolean;
  presidente_dirimente: boolean;
  acto_requerido: boolean;
  acto_medio: string | null;
  requisitos: RequisitoPolitica[];
  documentos: DocumentoPolitica[];
  regla: Record<string, unknown>;
  historia: { evento: string; version: number; fecha: string; actor: string | null }[];
  versiones: { id: string; numero_version: number; estado: string }[];
  activada_en: string | null;
  cerrada_en: string | null;
  motivo_cierre: string | null;
  puede_editar: boolean;
  puede_activar: boolean;
  puede_cerrar: boolean;
  puede_versionar: boolean;
}

export interface PoliticaComisionCatalogo {
  estados: { codigo: string; etiqueta: string }[];
  tipos_comision: { codigo: string; etiqueta: string }[];
  bases_normativas: { codigo: string; etiqueta: string }[];
  tipos_mayoria: { codigo: string; etiqueta: string }[];
  bases_decision: { codigo: string; etiqueta: string }[];
  funciones: { codigo: string; etiqueta: string }[];
  condiciones: { codigo: string; etiqueta: string }[];
  tipos_requisito: { codigo: string; etiqueta: string }[];
  areas: { codigo: string; etiqueta: string }[];
  etapas: { codigo: string; etiqueta: string }[];
  medios: { codigo: string; etiqueta: string }[];
  acciones_competencia: { codigo: string; etiqueta: string }[];
  materias_competencia: { codigo: string; etiqueta: string }[];
  piso_lcp: Record<string, unknown>;
}

export interface PoliticaComisionOpciones {
  cargos: { id: string; etiqueta: string }[];
  unidades: { id: string; etiqueta: string }[];
  funcionarios: { id: string; etiqueta: string }[];
  tipos_documentales: { id: string; etiqueta: string }[];
}

export const CONSULTA_POLITICAS_COMISION = [...CONSULTA_COMISIONES, "politicas"] as const;

export const RUTA_POLITICAS = "/gobierno/contrataciones/politicas-comision";

export const ETIQUETAS_ESTADO_POLITICA: Record<string, string> = {
  BORRADOR: "Borrador",
  VIGENTE: "Vigente",
  CERRADA: "Cerrada",
};

export function consultaDePoliticas(params: { estado?: string; q?: string } = {}): string {
  const p = new URLSearchParams();
  if (params.estado) p.set("estado", params.estado);
  if (params.q) p.set("q", params.q);
  const s = p.toString();
  return s ? `?${s}` : "";
}

export function describirMayoria(m: MayoriaPolitica, etiquetas: Record<string, string>): string {
  const etiqueta = etiquetas[m.tipo] ?? m.tipo;
  if (m.tipo === "FRACCION" || m.tipo === "CALIFICADA") {
    if (m.numerador != null && m.denominador != null) {
      return `${etiqueta} (${m.numerador}/${m.denominador})`;
    }
    return etiqueta;
  }
  if (m.tipo === "NUMERO_FIJO") {
    return `${etiqueta} (${m.cantidad ?? "—"})`;
  }
  if (m.tipo === "SIMPLE") {
    return "Mayoría simple";
  }
  return etiqueta;
}

export function etiquetaDe(
  lista: { codigo: string; etiqueta: string }[] | undefined,
  codigo: string | null | undefined,
): string {
  if (!codigo) return "—";
  if (!lista) return codigo;
  const item = lista.find((x) => x.codigo === codigo);
  return item ? item.etiqueta : codigo;
}
