import {
  ACCIONES_COMPETENCIA,
  MATERIAS_COMPETENCIA,
} from "@/modules/gobierno/tesoreria/pagos/api";

export const RUTA_RETENCIONES = "/gobierno/tesoreria/retenciones";
export const RUTA_POLITICAS_RETENCION = "/gobierno/tesoreria/politicas-retencion";
export const API_RETENCIONES = "/gobierno/tesoreria/retenciones";

export const CONSULTA_POLITICAS_RETENCION = ["retenciones", "politicas"] as const;
export const CONSULTA_CATALOGO_RETENCION = ["retenciones", "catalogo"] as const;
export const CONSULTA_CONFIG_RETENCION = ["retenciones", "configuracion"] as const;
export const CONSULTA_LIQUIDACIONES = ["retenciones", "liquidaciones"] as const;
export const CONSULTA_COMPROBANTES = ["retenciones", "comprobantes"] as const;

export interface ConfiguracionRetencion {
  id: string;
  patron: string;
  version: number;
  ejemplo: string | null;
}

export interface ElementoCatalogoRetencion {
  id: string;
  tipo: "CONCEPTO" | "CONDICION";
  codigo: string;
  nombre: string;
  descripcion: string | null;
  clase: string | null;
  serie_comprobante: string | null;
  estado: "ACTIVO" | "INACTIVO";
  version: number;
}

export interface ReglaRetencion {
  id?: string;
  orden: number;
  concept_id: string;
  concepto_codigo?: string;
  concepto_nombre?: string;
  concepto_clase?: string;
  base_tipo: "MONTO_BRUTO" | "PORCENTAJE_DEL_BRUTO";
  base_porcentaje: string | null;
  tasa: string;
  umbral_tipo: "NINGUNO" | "MONTO" | "MULTIPLO_TASA";
  umbral_monto: string | null;
  umbral_multiplo: string | null;
  umbral_moneda_tasa: "USD" | "EUR" | null;
  sustraendo: string | null;
  tope: string | null;
  condiciones_exigidas: string[];
  exclusiones: string[];
  tipos_persona: ("NATURAL" | "JURIDICA")[] | null;
  exige_comprobante: boolean;
}

export interface PoliticaRetencion {
  id: string;
  codigo: string;
  numero_version: number;
  version_anterior_id: string | null;
  nombre: string;
  descripcion: string | null;
  moneda: "VES" | "USD" | "EUR";
  tipo_regla: "INSTITUTIONAL_POLICY" | "OPERATIONAL_CONFIGURATION";
  estado_verificacion: "PENDING_PIN";
  fuente_descripcion: string | null;
  fuente_referencia: string | null;
  fuente_documento_id: string | null;
  act_id: string | null;
  aprobador_competencia_accion: string | null;
  aprobador_competencia_materia: string | null;
  permite_ajuste: boolean;
  redondeo_decimales: number;
  redondeo_modo: "HALF_UP" | "HALF_EVEN" | "DOWN";
  vigente_desde: string | null;
  vigente_hasta: string | null;
  fundamento: string | null;
  estado: "BORRADOR" | "VIGENTE" | "CERRADA";
  reglas_count?: number;
  activada_en: string | null;
  cerrada_en: string | null;
  motivo_cierre: string | null;
  version: number;
  reglas: ReglaRetencion[];
}

export interface HistoriaRetencion {
  id: string;
  evento: string;
  numero_version: number;
  actor_id: string;
  created_at: string;
  instantanea: PoliticaRetencion | null;
}

export interface LineaLiquidacion {
  id: string;
  orden: number;
  concepto_codigo: string;
  concepto_nombre: string;
  clase: string;
  base: string;
  tasa: string;
  umbral: string;
  tasa_referencia: {
    valor: string;
    moneda: string;
    fecha_efectiva: string;
  } | null;
  aplica: boolean;
  motivo_no_aplica: string | null;
  monto_calculado: string;
  monto_aprobado: string;
  motivo_ajuste: string | null;
  ajustado_por: string | null;
  ajustado_en: string | null;
  exige_comprobante: boolean;
}

export interface Liquidacion {
  id: string;
  payment_id: string;
  pago_codigo: string;
  pago_estado: string;
  policy_id: string;
  policy_codigo: string;
  policy_numero_version: number;
  estado: "CALCULADA" | "APROBADA" | "APLICADA" | "ANULADA";
  fecha_referencia: string;
  moneda: string;
  bruto: string;
  total_retenido: string;
  neto: string;
  conceptos: string[];
  beneficiario: {
    nombre: string;
    identificacion_fiscal: string;
    tipo_persona: string;
    condiciones: string[];
  };
  permite_ajuste: boolean;
  politica_fuente: {
    tipo_regla: string;
    estado_verificacion: string;
    fuente_descripcion: string | null;
    fuente_referencia: string | null;
  };
  calculado_por: string;
  calculado_en: string;
  aprobado_por: string | null;
  aprobado_en: string | null;
  aprobador_cargo_codigo: string | null;
  aprobador_cargo_nombre: string | null;
  aprobador_funcionario_nombre: string | null;
  aplicado_en: string | null;
  anulado_por: string | null;
  anulado_en: string | null;
  motivo_anulacion: string | null;
  huella: string;
  version: number;
  lineas: LineaLiquidacion[];
  comprobantes: {
    id: string;
    codigo: string;
    estado: string;
    concepto_codigo: string;
    monto: string;
    sustituye_a_id: string | null;
    emitido_en: string;
  }[];
}

export interface MontosPago {
  bruto: string;
  total_retenido: string;
  neto: string;
  moneda: string;
  liquidacion_id: string | null;
  estado_liquidacion: string | null;
  definitivo: boolean;
}

export interface Comprobante {
  id: string;
  codigo: string;
  numero: string;
  serie: string | null;
  estado: "EMITIDO" | "ANULADO";
  settlement_id: string | null;
  payment_id: string;
  pago_codigo: string;
  concepto_codigo: string;
  concepto_nombre: string;
  clase: string;
  beneficiario_nombre: string;
  identificacion_fiscal: string;
  monto: string;
  moneda: string;
  fecha_emision: string;
  emitido_en: string;
  anulado_en: string | null;
  motivo_anulacion: string | null;
  sustituye_a_id: string | null;
  sustituido_por_id: string | null;
  huella: string;
  snapshot: string | null;
}

export interface OpcionesRetencion {
  pago: {
    id: string;
    codigo: string;
    estado: string;
    moneda: string;
    monto: string;
    fecha_pago: string;
  };
  politicas: {
    id: string;
    codigo: string;
    numero_version: number;
    nombre: string;
    permite_ajuste: boolean;
    conceptos: string[];
  }[];
  conceptos: ElementoCatalogoRetencion[];
  condiciones: ElementoCatalogoRetencion[];
  tipos_persona: string[];
  liquidacion: Liquidacion | null;
}

export const ESTADOS_POLITICA_RETENCION: Record<string, string> = {
  BORRADOR: "Borrador",
  VIGENTE: "Vigente",
  CERRADA: "Cerrada",
};

export const ESTADOS_LIQUIDACION: Record<string, string> = {
  CALCULADA: "Calculada",
  APROBADA: "Aprobada",
  APLICADA: "Aplicada",
  ANULADA: "Anulada",
};

export const ESTADOS_COMPROBANTE: Record<string, string> = {
  EMITIDO: "Emitido",
  ANULADO: "Anulado",
};

export const CLASES_CONCEPTO: Record<string, string> = {
  TRIBUTARIA: "Tributaria",
  CONTRACTUAL: "Contractual",
  OTRA: "Otra",
};

export const BASES: Record<string, string> = {
  MONTO_BRUTO: "Monto bruto del pago",
  PORCENTAJE_DEL_BRUTO: "Porcentaje del bruto",
};

export const UMBRALES: Record<string, string> = {
  NINGUNO: "Sin umbral",
  MONTO: "Monto fijo",
  MULTIPLO_TASA: "Múltiplo de una tasa oficial",
};

export const TIPOS_PERSONA: Record<string, string> = {
  NATURAL: "Natural",
  JURIDICA: "Jurídica",
};

export const MOTIVOS_NO_APLICA: Record<string, string> = {
  CONCEPTO_NO_SELECCIONADO: "Concepto no elegido",
  TIPO_PERSONA: "Tipo de persona",
  CONDICION_FALTANTE: "Falta una condición exigida",
  EXCLUSION: "Excluido por condición",
  UMBRAL: "Por debajo del umbral",
  SIN_MONTO: "Sin monto a retener",
};

export const MODOS_REDONDEO: Record<string, string> = {
  HALF_UP: "HALF_UP",
  HALF_EVEN: "HALF_EVEN",
  DOWN: "DOWN",
};

export { ACCIONES_COMPETENCIA, MATERIAS_COMPETENCIA };
