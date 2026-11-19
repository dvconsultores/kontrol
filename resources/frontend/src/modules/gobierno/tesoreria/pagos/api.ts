export const RUTA_TESORERIA = "/gobierno/tesoreria";
export const RUTA_PAGOS = "/gobierno/tesoreria/pagos";
export const RUTA_POLITICAS_PAGO = "/gobierno/tesoreria/politicas-pago";
export const RUTA_MEDIOS_PAGO = "/gobierno/tesoreria/medios-pago";
export const RUTA_CONFIG_PAGOS = "/gobierno/tesoreria/pagos/configuracion";

export const CONSULTA_PAGOS = ["gobierno", "tesoreria", "pagos"] as const;
export const CONSULTA_POLITICAS_PAGO = ["gobierno", "tesoreria", "politicas-pago"] as const;
export const CONSULTA_MEDIOS_PAGO = ["gobierno", "tesoreria", "medios-pago"] as const;

export type EstadoPago =
  | "BORRADOR"
  | "PENDIENTE_AUTORIZACION"
  | "AUTORIZADO"
  | "REGISTRADO"
  | "RECHAZADO"
  | "ANULADO";

export type EstadoPoliticaPago = "BORRADOR" | "VIGENTE" | "CERRADA";
export type EstadoMedioPago = "ACTIVO" | "INACTIVO";
export type EtapaDocumentoPago = "PREPARAR" | "AUTORIZAR" | "REGISTRAR" | "ANULAR";
export type ControlDuplicado = "BLOQUEAR" | "ADVERTIR";

export interface ConfiguracionPagos {
  patron: string;
  version: number;
}

export interface MedioPago {
  id: string;
  codigo: string;
  nombre: string;
  descripcion: string | null;
  estado: EstadoMedioPago;
  vigente_desde: string;
  vigente_hasta: string | null;
  exige_referencia: boolean;
  referencia_unica: boolean;
  patron_referencia: string | null;
  fundamento: string | null;
  version: number;
}

export interface RequisitoBandaPago {
  accion: string;
  materia: string;
  cantidad: number;
}

export interface BandaPago {
  orden: number;
  monto_desde: string;
  monto_hasta: string | null;
  requisitos: RequisitoBandaPago[];
}

export interface DocumentoPoliticaPago {
  document_type_id: string;
  etiqueta?: string;
  etapa: EtapaDocumentoPago;
  obligatorio: boolean;
}

export interface PoliticaPagoResumen {
  id: string;
  codigo: string;
  numero_version: number;
  nombre: string;
  moneda: string;
  estado: EstadoPoliticaPago;
  vigente_desde: string;
  vigente_hasta: string | null;
  version: number;
}

export interface PoliticaPago extends PoliticaPagoResumen {
  descripcion: string | null;
  permite_pago_parcial: boolean;
  preparador_competencia_accion: string | null;
  preparador_competencia_materia: string | null;
  exige_cargo_autorizado_cuenta: boolean;
  control_duplicado: ControlDuplicado;
  fundamento: string | null;
  act_id: string | null;
  tipo_regla: string;
  version_anterior_id: string | null;
  medios: {
    id: string;
    codigo: string;
    nombre: string;
    estado: EstadoMedioPago;
  }[];
  bandas: BandaPago[];
  documentos: DocumentoPoliticaPago[];
  historia: {
    evento: string;
    numero_version: number;
    actor_id: string | null;
    created_at: string;
  }[];
}

export interface SaldoOrdenPago {
  monto_ordenado: string;
  monto_pagado: string;
  monto_en_tramite: string;
  pendiente_de_pagar: string;
  disponible_para_pago: string;
}

export interface PagoResumen {
  id: string;
  codigo: string | null;
  estado: EstadoPago;
  orden_codigo: string | null;
  order_id: string;
  beneficiario: string | null;
  cuenta_codigo: string | null;
  medio_codigo: string | null;
  moneda: string;
  monto: string;
  fecha_pago: string;
  fecha_valor: string | null;
  referencia_externa: string | null;
  enviado_en: string | null;
  registrado_en: string | null;
  version: number;
}

export interface ControlPago {
  codigo: string;
  cumplido: boolean;
  mensaje: string;
}

export interface ControlesPago {
  controles: ControlPago[];
  completo: boolean;
  banda: BandaPago | null;
  aprobaciones_requeridas: number | null;
  saldo: SaldoOrdenPago;
}

export interface AprobacionPago {
  actor: string | null;
  cargo: string;
  unidad: string | null;
  funcionario: string | null;
  requisito_indice: number | null;
  requisito: { accion: string; materia: string } | null;
  decision: "APROBADA" | "RECHAZADA";
  motivo: string | null;
  fecha: string;
  policy_numero_version: number;
}

export interface Pago {
  id: string;
  codigo: string | null;
  numero: number | null;
  estado: EstadoPago;
  version: number;
  concepto: string;
  moneda: string;
  monto: string;
  fecha_pago: string;
  fecha_valor: string | null;
  referencia_externa: string | null;
  huella: string | null;
  duplicado_confirmado: boolean;
  motivo_duplicado: string | null;
  orden: {
    id: string;
    codigo: string | null;
    beneficiario: string | null;
    moneda: string;
    fecha_orden: string;
  } & SaldoOrdenPago;
  politica: {
    id: string;
    codigo: string;
    nombre: string;
    numero_version: number;
  };
  regla: Record<string, unknown> | null;
  cuenta: {
    id: string;
    codigo: string;
    denominacion: string;
    moneda: string;
    numero_enmascarado: string;
  };
  medio: {
    id: string;
    codigo: string;
    nombre: string;
    exige_referencia: boolean;
    referencia_unica: boolean;
    patron_referencia: string | null;
  };
  preparador: {
    usuario: string | null;
    cargo: string | null;
    funcionario: string | null;
  };
  enviado_por: string | null;
  enviado_en: string | null;
  aprobaciones_requeridas: number | null;
  aprobaciones: AprobacionPago[];
  documentos: {
    etapa: EtapaDocumentoPago;
    document_id: string;
    titulo: string;
    tipo: string | null;
    sha256: string | null;
  }[];
  documentos_preparar: string[];
  registrado_por: string | null;
  registrado_en: string | null;
  rechazado_por: string | null;
  rechazado_en: string | null;
  motivo_rechazo: string | null;
  anulado_por: string | null;
  anulado_en: string | null;
  motivo_anulacion: string | null;
  historia: {
    evento: string;
    actor: string | null;
    fecha: string;
    instantanea: Record<string, unknown>;
  }[];
  ejecucion_externa: boolean;
  fronteras: {
    retenciones: string;
    conciliacion: string;
    reverso: string;
    contabilidad: string;
  };
  controles: ControlesPago | null;
}

export interface OpcionesPago {
  ordenes: ({
    id: string;
    codigo: string | null;
    beneficiario: string | null;
    moneda: string;
    fecha_orden: string;
    year_id: string;
  } & SaldoOrdenPago)[];
  politicas: {
    id: string;
    codigo: string;
    numero_version: number;
    nombre: string;
    moneda: string;
    permite_pago_parcial: boolean;
    control_duplicado: ControlDuplicado;
    medios: string[];
  }[];
  cuentas: {
    id: string;
    codigo: string;
    denominacion: string;
    moneda: string;
    numero_enmascarado: string;
  }[];
  medios: {
    id: string;
    codigo: string;
    nombre: string;
    exige_referencia: boolean;
    referencia_unica: boolean;
    patron_referencia: string | null;
  }[];
  cargos: {
    id: string;
    codigo: string;
    nombre: string;
    competencias: string[];
  }[];
  documentos: {
    id: string;
    titulo: string;
    tipo: string | null;
    document_type_id: string;
  }[];
}

export const ESTADOS_PAGO: Record<EstadoPago, string> = {
  BORRADOR: "Borrador",
  PENDIENTE_AUTORIZACION: "Pendiente de autorización",
  AUTORIZADO: "Autorizado",
  REGISTRADO: "Pago registrado",
  RECHAZADO: "Rechazado",
  ANULADO: "Anulado",
};

export const ESTADOS_POLITICA_PAGO: Record<EstadoPoliticaPago, string> = {
  BORRADOR: "Borrador",
  VIGENTE: "Vigente",
  CERRADA: "Cerrada",
};

export const ETAPAS_DOCUMENTO_PAGO: Record<EtapaDocumentoPago, string> = {
  PREPARAR: "Preparar",
  AUTORIZAR: "Autorizar",
  REGISTRAR: "Registrar",
  ANULAR: "Anular",
};

export const ACCIONES_COMPETENCIA = [
  "SOLICITAR",
  "COMPROMETER",
  "CAUSAR",
  "ORDENAR_PAGO",
  "PAGAR",
  "REGISTRAR",
  "CUSTODIAR",
  "APROBAR",
  "AUDITAR",
  "FIRMAR",
] as const;

export const MATERIAS_COMPETENCIA = [
  "PRESUPUESTO",
  "CONTRATACIONES",
  "TESORERIA",
  "CONTABILIDAD",
  "BIENES",
  "EXPEDIENTE",
] as const;
