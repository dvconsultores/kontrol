import { CONSULTA_GOBIERNO } from "@/modules/gobierno/api";

export type EstadoContrato = "BORRADOR" | "FORMALIZADO";
export type TipoInstrumento = "CONTRATO" | "ORDEN_COMPRA" | "ORDEN_SERVICIO";

export interface ContratoResumen {
  id: string;
  identificacion: string;
  codigo: string | null;
  estado: EstadoContrato;
  estado_etiqueta: string;
  tipo: TipoInstrumento | null;
  tipo_etiqueta: string | null;
  expediente_numero: string;
  decision_referencia: string;
  contratista_nombre: string;
  monto: string;
  moneda: string;
  fecha_inicio: string | null;
  fecha_fin: string | null;
}

export interface CertificadoElegible {
  id: string;
  codigo: string;
  monto: string;
  saldo_libre: string;
  moneda: string;
  anio: number;
  partida: string;
  fuente: string;
  concepto: string;
}

export interface GarantiaContrato {
  instrumento_id: string;
  referencia: string;
  tipo_etiqueta: string;
  emisor: string;
  monto: string;
  moneda: string;
  vigente_hasta: string;
  estado: string;
}

export interface DocumentoElegible {
  id: string;
  titulo: string;
  version: number;
}

export interface FirmanteOpcion {
  cargo_id: string;
  cargo: string;
  limite: {
    cargo: string | null;
    tipo_limite: string | null;
    monto: string | null;
    moneda: string | null;
    etiqueta: string;
  };
  control: {
    estado: string;
    estado_etiqueta: string;
    permite: boolean;
    mensaje: string;
  };
}

export interface Contrato {
  id: string;
  version: number;
  estado: EstadoContrato;
  estado_etiqueta: string;
  tipo: TipoInstrumento | null;
  tipo_etiqueta: string | null;
  codigo: string | null;
  identificacion: string;
  expediente: { id: string; numero: string };
  decision: { id: string; referencia: string; fecha: string; acto: string; vigente: boolean };
  oferta: { id: string; referencia: string };
  contratista: { nombre: string; documento: string; representante: string | null };
  objeto: string;
  descripcion_complementaria: string | null;
  monto: string;
  moneda: string;
  fecha_inicio: string | null;
  fecha_fin: string | null;
  referencia_instrumento: string | null;
  documento: { id: string; titulo: string; version: number; sha256: string } | null;
  cobertura: {
    asignaciones: {
      certificado_id: string;
      codigo: string;
      monto: string;
      moneda: string;
      anio: number;
      partida: string;
      fuente: string;
      estado: string;
    }[];
    total_asignado: string;
    faltante: string;
    completa: boolean;
  };
  garantias: GarantiaContrato[];
  moneda_oferta?: string | null;
  compromisos?: { total: string; moneda: string; estado: string; permite: boolean; mensaje: string };
  modificaciones?: {
    cantidad: number;
    borrador_id: string | null;
    vigente: { monto: string; fecha_fin: string | null; codigo: string | null };
  } | null;
  firmante: { cargo: string; funcionario: string | null; conversion?: ConversionFirmante | null } | null;
  fecha_formalizacion: string | null;
  formalizado_en: string | null;
  huella: string | null;
  opciones: null | {
    certificados_elegibles: CertificadoElegible[];
    garantias_elegibles: GarantiaContrato[];
    documentos_elegibles: DocumentoElegible[];
    firmantes: FirmanteOpcion[];
  };
  pendientes: string[];
  puede_formalizar: boolean;
}

export type TipoModificacion = "ADENDA" | "PRORROGA" | "MODIFICACION" | "VARIACION";
export type EstadoModificacion = "BORRADOR" | "FORMALIZADA";

export interface TasaConversion {
  tasa_id: string;
  moneda: string;
  valor: string;
  fecha_efectiva: string;
  version: number;
  fuente: string;
  fuente_referencia: string;
}

export interface ConversionFirmante {
  moneda_operacion: string;
  moneda_limite: string;
  fecha: string;
  tasas: TasaConversion[];
  total_ves: string | null;
  limite_ves: string | null;
  resultado: string;
}

export interface NodoModificacion {
  id: string;
  codigo: string;
  numero: number;
  tipo: TipoModificacion;
  tipo_etiqueta: string;
  fecha_instrumento: string;
  vigente_desde: string;
  motivo: string;
  plazo: { anterior: string; nuevo: string } | null;
  monto: { anterior: string; delta: string; nuevo: string } | null;
  condiciones: string | null;
  firmante: { cargo: string; funcionario: string | null };
  documento: { titulo: string; version: number; sha256: string };
  huella: string;
  formalizado_en: string;
  cobertura_adicional: { codigo: string; monto: string }[];
}

export interface HistoriaModificaciones {
  contrato: {
    id: string;
    codigo: string | null;
    identificacion: string;
    tipo_etiqueta: string | null;
    estado: string;
    contratista_nombre: string;
    objeto: string;
    moneda: string;
  };
  original: {
    monto: string;
    moneda: string;
    fecha_inicio: string | null;
    fecha_fin: string | null;
    huella: string | null;
  };
  vigente: {
    fecha: string;
    monto: string;
    fecha_fin: string | null;
    modificacion_codigo: string | null;
    programadas: string[];
  };
  ultima: {
    monto: string;
    fecha_fin: string | null;
    vigente_desde: string | null;
    modificacion_codigo: string | null;
  };
  historial: NodoModificacion[];
  borrador: { id: string; tipo: TipoModificacion; tipo_etiqueta: string } | null;
  puede_crear: boolean;
  motivo_no_crear: string | null;
}

export interface FichaModificacion {
  id: string;
  version: number;
  estado: EstadoModificacion;
  estado_etiqueta: string;
  tipo: TipoModificacion;
  tipo_etiqueta: string;
  codigo: string | null;
  identificacion: string;
  contrato: { id: string; codigo: string | null };
  moneda: string;
  fecha_instrumento: string | null;
  vigente_desde: string | null;
  motivo: string | null;
  nueva_fecha_fin: string | null;
  delta_monto: string | null;
  condiciones: string | null;
  referencia_instrumento: string | null;
  documento: { id: string; titulo: string; version: number; sha256: string } | null;
  base: { monto: string; fecha_fin: string | null; numero: number };
  propuesta: { monto_nuevo: string | null; fecha_fin_nueva: string | null };
  cobertura: {
    existente_valida: string;
    requerida_adicional: string;
    asignaciones: {
      certificado_id: string;
      codigo: string;
      monto: string;
      moneda: string;
      anio: number | null;
      partida: string;
      fuente: string;
      estado: string | null;
    }[];
    total_asignado: string;
    completa: boolean;
  };
  compromisos: { total: string | null; moneda: string | null; permite: boolean; aplica: boolean; mensaje?: string };
  firmante: {
    cargo: string | null;
    funcionario: string | null;
    limite: string | null;
    conversion: ConversionFirmante | null;
  } | null;
  formalizado_en: string | null;
  huella: string | null;
  opciones: {
    certificados_elegibles: CertificadoElegible[];
    documentos_elegibles: DocumentoElegible[];
    firmantes: FirmanteOpcion[];
  } | null;
  pendientes: string[];
  puede_formalizar: boolean;
}

export const CONSULTA_CONTRATOS = [...CONSULTA_GOBIERNO, "contratos"] as const;

export const TIPOS_INSTRUMENTO: { codigo: TipoInstrumento; etiqueta: string }[] = [
  { codigo: "CONTRATO", etiqueta: "Contrato" },
  { codigo: "ORDEN_COMPRA", etiqueta: "Orden de compra" },
  { codigo: "ORDEN_SERVICIO", etiqueta: "Orden de servicio" },
];

export const TIPOS_MODIFICACION: { codigo: TipoModificacion; etiqueta: string }[] = [
  { codigo: "ADENDA", etiqueta: "Adenda" },
  { codigo: "PRORROGA", etiqueta: "Prórroga" },
  { codigo: "MODIFICACION", etiqueta: "Modificación" },
  { codigo: "VARIACION", etiqueta: "Variación" },
];

export function rutaContrato(id: string): string {
  return `/gobierno/contratos/${id}`;
}

export function rutaModificaciones(contratoId: string): string {
  return `/gobierno/contratos/${contratoId}/modificaciones`;
}

export function rutaModificacion(contratoId: string, modificacionId: string): string {
  return `/gobierno/contratos/${contratoId}/modificaciones/${modificacionId}`;
}

export interface DesignacionSupervisor {
  id: string;
  referencia: string;
  situacion: "EN_EJERCICIO" | "PROGRAMADA" | "CONCLUIDA";
  situacion_etiqueta: string;
  numero: number;
  estado: "VIGENTE" | "SUSTITUIDA";
  estado_etiqueta: string;
  funcionario: { id: string; nombre: string; documento: string };
  asignacion_id: string;
  figura: string;
  figura_etiqueta: string;
  cargo: { id: string; codigo: string; nombre: string };
  unidad: { id: string; nombre: string };
  acto: { id: string; etiqueta: string; emisor_cargo: string };
  desde: string;
  hasta: string | null;
  motivo: string | null;
  sustituye: string | null;
  registrado_en: string;
}

export interface Supervision {
  contrato: {
    id: string;
    codigo: string | null;
    estado: string;
    fecha_formalizacion: string | null;
    fecha_fin: string | null;
  };
  vigente: DesignacionSupervisor | null;
  programada: DesignacionSupervisor | null;
  ultima_id: string | null;
  historia: DesignacionSupervisor[];
  puede_designar: boolean;
}

export interface OpcionSupervisorFuncionario {
  id: string;
  nombre: string;
  documento: string;
  ocupaciones: {
    asignacion_id: string;
    figura_etiqueta: string;
    cargo_id: string;
    cargo: string;
    unidad_id: string | null;
    unidad: string | null;
  }[];
}

export interface OpcionesSupervision {
  fecha: string;
  vigente_id: string | null;
  funcionarios: OpcionSupervisorFuncionario[];
  actos: {
    id: string;
    etiqueta: string;
    emisor_cargo: string;
    fecha: string;
    fecha_eficacia: string | null;
  }[];
}
