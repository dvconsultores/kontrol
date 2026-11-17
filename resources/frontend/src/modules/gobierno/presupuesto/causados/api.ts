import type { ApiError } from "@/api/client";

export const CONSULTA_CAUSADOS = ["gobierno", "presupuesto", "causados"] as const;
export const RUTA_POLITICAS = "/gobierno/presupuesto/politicas-causado";
export const RUTA_CAUSADOS = "/gobierno/presupuesto/causados";

export const DISPARADORES = {
  RECEIPT_ACCEPTED: "Recepción conforme del contrato",
  VALUATION_APPROVED: "Valuación conformada",
  DELIVERY_ACCEPTED: "Entrega conforme",
  INVOICE_CONFORMED: "Factura conformada",
  DOCUMENTARY: "Solo documentos exigidos",
} as const;

export const ESTADOS_POLITICA = {
  BORRADOR: "Borrador",
  VIGENTE: "Vigente",
  CERRADA: "Cerrada",
} as const;

export const TIPOS_REGLA = {
  INSTITUTIONAL_POLICY: "Política del ente",
  LEGAL_MANDATORY: "Obligación legal verificada",
} as const;

export const ETAPAS = {
  PREPARACION: "Al preparar",
  FORMALIZACION: "Al formalizar",
} as const;

export const ACCIONES_COMPETENCIA = {
  SOLICITAR: "Solicitar",
  COMPROMETER: "Comprometer",
  CAUSAR: "Causar",
  ORDENAR_PAGO: "Ordenar pago",
  PAGAR: "Pagar",
  REGISTRAR: "Registrar",
  CUSTODIAR: "Custodiar",
  APROBAR: "Aprobar",
  AUDITAR: "Auditar",
  FIRMAR: "Firmar",
} as const;

export const MATERIAS_COMPETENCIA = {
  PRESUPUESTO: "Presupuesto",
  CONTRATACIONES: "Contrataciones",
  TESORERIA: "Tesorería",
  CONTABILIDAD: "Contabilidad",
  BIENES: "Bienes",
  EXPEDIENTE: "Expediente",
} as const;

export type Disparador = keyof typeof DISPARADORES;
export type EstadoPoliticaCausado = keyof typeof ESTADOS_POLITICA;
export type TipoReglaCausado = keyof typeof TIPOS_REGLA;
export type EtapaDocumentoCausado = keyof typeof ETAPAS;
export type AccionCompetencia = keyof typeof ACCIONES_COMPETENCIA;
export type MateriaCompetencia = keyof typeof MATERIAS_COMPETENCIA;

export interface ConfiguracionNumeracionCausados {
  patron: string;
  ejemplo: string;
  version: number;
  configurado: boolean;
}

export interface DocumentoExigido {
  id: string;
  document_type_id: string;
  tipo_documental: string;
  obligatorio: boolean;
  etapa: EtapaDocumentoCausado;
  condicion: string | null;
}

export interface DocumentoExigidoCuerpo {
  document_type_id: string;
  obligatorio: boolean;
  etapa: EtapaDocumentoCausado;
  condicion?: string;
}

export interface HistoriaPoliticaCausado {
  evento: string;
  version: number;
  fecha: string;
  actor: string;
}

export interface PoliticaCausado {
  id: string;
  codigo: string;
  tipo_gasto: string;
  nombre: string;
  descripcion: string | null;
  disparador: Disparador;
  requiere_recepcion: boolean;
  requiere_valuacion: boolean;
  requiere_conformidad: boolean;
  competencia_accion: AccionCompetencia;
  competencia_materia: MateriaCompetencia;
  vigente_desde: string;
  vigente_hasta: string | null;
  fundamento: string | null;
  act_id: string | null;
  acto: string | null;
  tipo_regla: TipoReglaCausado;
  estado: EstadoPoliticaCausado;
  version: number;
  activada_en: string | null;
  cerrada_en: string | null;
  motivo_cierre: string | null;
  documentos: DocumentoExigido[];
  historia?: HistoriaPoliticaCausado[];
}

export interface PoliticaCausadoCuerpo {
  codigo: string;
  tipo_gasto: string;
  nombre: string;
  descripcion?: string;
  disparador: Disparador;
  requiere_recepcion: boolean;
  requiere_valuacion: boolean;
  requiere_conformidad: boolean;
  competencia_accion: AccionCompetencia;
  competencia_materia: MateriaCompetencia;
  vigente_desde: string;
  vigente_hasta?: string;
  fundamento?: string;
  act_id?: string;
  tipo_regla?: TipoReglaCausado;
  documentos: DocumentoExigidoCuerpo[];
}

export interface TipoDocumento {
  id: string;
  code: string;
  name: string;
}

export interface Causado {
  id: string;
  codigo: string | null;
  numero: string | null;
  estado: "BORRADOR" | "FORMALIZADO" | "ANULADO";
  version: number;
  year_id: string;
  anio: string;
  compromiso: {
    id: string;
    codigo: string;
    concepto: string;
    total: string;
    causado: string;
    pendiente: string;
  };
  politica: {
    id: string;
    codigo: string;
    nombre: string;
    tipo_gasto: string;
    disparador: Disparador;
    version: number;
  };
  fecha_efectiva: string;
  registrado_en: string;
  moneda: string;
  monto: string;
  concepto: string;
  beneficiario: string | null;
  fuente_tipo: string | null;
  fuente_id: string | null;
  autoridad_cargo_id: string | null;
  autoridad: {
    cargo: string;
    unidad: string;
    funcionario: string;
  } | null;
  lineas: Array<{
    id: string;
    linea_compromiso_id: string;
    linea: string;
    partida: string;
    categoria: string;
    comprometido: string;
    causado_otros: string;
    monto: string;
    pendiente_tras: string;
  }>;
  evidencias: Array<{
    id: string;
    tipo: string;
    recurso_id: string;
    etiqueta: string;
    estado: string;
    fecha: string;
    sha256: string;
  }>;
  formalizado_en: string | null;
  formalizado_por: string | null;
  anulado_en: string | null;
  motivo_anulacion: string | null;
  huella: string | null;
  monto_ordenado: string;
  pendiente_de_ordenar: string;
  controles: Array<{
    codigo: string;
    cumplido: boolean;
    mensaje: string;
  }>;
  historia: Array<{
    evento: string;
    fecha: string;
    actor: string;
  }>;
}

export interface CausadoResumen {
  id: string;
  codigo: string | null;
  estado: "BORRADOR" | "FORMALIZADO" | "ANULADO";
  fecha_efectiva: string;
  compromiso_id: string;
  compromiso_codigo: string;
  beneficiario: string | null;
  concepto: string;
  monto: string;
  moneda: string;
  pendiente_compromiso: string;
  unidad: string;
  responsable: string;
}

export interface CausadosListado {
  items: CausadoResumen[];
  total: number;
}

export interface OpcionesCausado {
  anio: string;
  moneda: string;
  compromisos: Array<{
    id: string;
    codigo: string;
    concepto: string;
    fecha: string;
    moneda: string;
    total: string;
    causado: string;
    pendiente: string;
    lineas: Array<{
      id: string;
      linea: string;
      partida: string;
      categoria: string;
      unidad: string;
      comprometido: string;
      causado: string;
      pendiente: string;
    }>;
  }>;
  politicas: PoliticaCausado[];
  cargos: Array<{
    id: string;
    etiqueta: string;
    competencias: string[];
  }>;
  evidencias: Array<{
    tipo: string;
    id: string;
    etiqueta: string;
    estado: string;
    fecha: string;
    valida: boolean;
  }>;
  documentos: Array<{
    id: string;
    etiqueta: string;
    tipo_documental_id: string;
    tipo_documental: string;
  }>;
}

export type ApiErrorCausados = ApiError;