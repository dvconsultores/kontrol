export const RUTA_ORDENES = "/gobierno/tesoreria";
export const RUTA_POLITICAS_OP = "/gobierno/tesoreria/politicas-orden-pago";
export const RUTA_CONFIG_OP = "/gobierno/tesoreria/ordenes-pago/configuracion";

export const CONSULTA_ORDENES = ["gobierno", "tesoreria", "ordenes-pago"] as const;
export const CONSULTA_POLITICAS_OP = "gobierno-politicas-orden-pago";

export type EstadoOrdenPago = "BORRADOR" | "EMITIDA" | "ANULADA";

export interface LineaOrdenPago {
  cause_id: string;
  codigo: string;
  compromiso_codigo: string;
  beneficiario: string;
  fecha_efectiva: string;
  monto_causado: string;
  monto_ordenado: string;
  pendiente_de_ordenar: string;
  monto_asignado: string;
}

export interface DocumentoOrdenPago {
  document_id: string;
  titulo: string;
  tipo: string | null;
  sha256: string | null;
  [k: string]: unknown;
}

export interface AutoridadOrdenPago {
  cargo_id: string | null;
  cargo: string | null;
  unidad: string | null;
  funcionario_id: string | null;
  funcionario: string | null;
  usuario_id: string | null;
}

export interface EventoHistoria {
  evento: string;
  fecha: string;
  actor: string;
}

export interface Control {
  codigo: string;
  cumplido: boolean;
  mensaje: string;
}

export interface Controles {
  controles: Control[];
  completo: boolean;
}

export interface OrdenPago {
  id: string;
  codigo: string | null;
  numero: number | null;
  estado: EstadoOrdenPago;
  year_id: string;
  anio: number;
  fecha_orden: string;
  concepto: string;
  moneda: string;
  monto: string;
  beneficiario: string;
  policy: {
    id: string;
    codigo: string;
    nombre: string;
    version: number;
  };
  lineas: LineaOrdenPago[];
  documentos: DocumentoOrdenPago[];
  autoridad: AutoridadOrdenPago;
  emitida_en: string | null;
  emitida_por: string | null;
  anulada_en: string | null;
  motivo_anulacion: string | null;
  huella: string | null;
  version: number;
  monto_pagado: string;
  pendiente_de_pagar: string;
  siguiente_paso: string | null;
  historia: EventoHistoria[];
  controles?: Controles;
}

export interface ObligacionElegible {
  id: string;
  codigo: string;
  beneficiario: string;
  moneda: string;
  fecha_efectiva: string;
  monto_causado: string;
  monto_ordenado: string;
  pendiente_de_ordenar: string;
  compromiso_codigo: string;
  tipo_gasto: string;
  elegible: boolean;
  motivo: string | null;
}

export interface OpcionesOrden {
  obligaciones: ObligacionElegible[];
  politicas: Array<{
    id: string;
    codigo: string;
    nombre: string;
    tipo_gasto: string | null;
    documentos: unknown[];
  }>;
  documentos: Array<{
    id: string;
    titulo: string;
    tipo: string;
    document_type_id: string;
  }>;
  cargos: Array<{
    id: string;
    codigo: string;
    nombre: string;
  }>;
}

export interface PoliticaOrdenPago {
  id: string;
  codigo: string;
  nombre: string;
  descripcion: string | null;
  tipo_gasto: string | null;
  requiere_expediente_completo: boolean;
  competencia_accion: string;
  competencia_materia: string;
  vigente_desde: string;
  vigente_hasta: string | null;
  fundamento: string | null;
  act_id: string | null;
  acto: string | null;
  tipo_regla: string;
  estado: "BORRADOR" | "VIGENTE" | "CERRADA";
  version: number;
  activada_en: string | null;
  cerrada_en: string | null;
  motivo_cierre: string | null;
  documentos: unknown[];
  historia: Array<{
    evento: string;
    version: number;
    fecha: string;
    actor: string;
  }>;
}

export interface ConfiguracionNumeracionOP {
  patron: string;
  ejemplo: string;
  version: number;
  configurado: boolean;
}

export interface OrdenLineaBody {
  cause_id: string;
  monto: string;
}

export interface OrdenCreateBody {
  policy_id: string;
  fecha_orden: string;
  concepto: string;
  lineas: OrdenLineaBody[];
  documentos?: string[];
  autoridad_cargo_id?: string | null;
}

export interface OrdenUpdateBody {
  policy_id?: string | null;
  fecha_orden?: string | null;
  concepto?: string | null;
  lineas?: OrdenLineaBody[] | null;
  documentos?: string[] | null;
  autoridad_cargo_id?: string | null;
}

export interface PoliticaDocumentoBody {
  document_type_id: string;
  obligatorio?: boolean;
  etapa?: string;
  condicion?: string | null;
}

export interface PoliticaCreateBody {
  codigo: string;
  nombre: string;
  descripcion?: string | null;
  tipo_gasto?: string | null;
  requiere_expediente_completo?: boolean;
  competencia_accion?: string;
  competencia_materia?: string;
  vigente_desde: string;
  vigente_hasta?: string | null;
  fundamento?: string | null;
  act_id?: string | null;
  tipo_regla?: string;
  documentos?: PoliticaDocumentoBody[];
}

export function consultaOrdenes(
  yearId: string,
  filtros: {
    estado?: string;
    desde?: string;
    hasta?: string;
    beneficiario?: string;
    moneda?: string;
    cause_id?: string;
    commitment_id?: string;
    q?: string;
  } = {},
): string {
  const params = new URLSearchParams();
  if (filtros.estado) params.set("estado", filtros.estado);
  if (filtros.desde) params.set("desde", filtros.desde);
  if (filtros.hasta) params.set("hasta", filtros.hasta);
  if (filtros.beneficiario) params.set("beneficiario", filtros.beneficiario);
  if (filtros.moneda) params.set("moneda", filtros.moneda);
  if (filtros.cause_id) params.set("cause_id", filtros.cause_id);
  if (filtros.commitment_id) params.set("commitment_id", filtros.commitment_id);
  if (filtros.q) params.set("q", filtros.q);
  const query = params.toString();
  return `${RUTA_ORDENES}/ejercicios/${yearId}/ordenes-pago${query ? `?${query}` : ""}`;
}

export function etiquetaEstadoOrden(estado: EstadoOrdenPago): string {
  const etiquetas: Record<EstadoOrdenPago, string> = {
    BORRADOR: "Borrador",
    EMITIDA: "Emitida",
    ANULADA: "Anulada",
  };
  return etiquetas[estado];
}

export function etiquetaControl(codigo: string): string {
  const mapa: Record<string, string> = {
    POLITICA: "Política",
    COMPATIBILIDAD: "Compatibilidad de las obligaciones",
    FALTA_BENEFICIARIO: "Beneficiario",
    SALDO_INSUFICIENTE: "Saldo disponible",
    FALTA_EVIDENCIA: "Expediente",
    FALTA_DOCUMENTO: "Documentos",
    FECHA: "Fecha",
    FALTA_AUTORIDAD: "Autoridad",
    LIMITE: "Límite",
    SOD: "Segregación de funciones",
  };
  return mapa[codigo] ?? codigo;
}

export function formatearMonto(valor: string, moneda: string): string {
  const [entero, decimal] = valor.split(".");
  const enteroConSeparador = entero.replace(/\B(?=(\d{3})+(?!\d))/g, ".");
  const decimalParte = decimal ? `,${decimal}` : ",00";
  return `${enteroConSeparador}${decimalParte} ${moneda}`;
}
