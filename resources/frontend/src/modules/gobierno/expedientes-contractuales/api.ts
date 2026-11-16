import type {
  ActuacionEjecucion,
  CierreEjecucion,
  EntregableEjecucion,
  FacturaEjecucion,
  HitoEjecucion,
  RecepcionEjecucion,
  ValuacionEjecucion,
} from "@/modules/gobierno/contratos/api";

export const CONSULTA_EXPEDIENTES = ["gobierno", "expedientes-contractuales"] as const;

export type TipoVigenciaExpediente = "POR_INICIAR" | "EN_PLAZO" | "VENCIDO";

export interface ItemExpedienteContractual {
  id: string;
  codigo: string;
  tipo: string;
  tipo_etiqueta: string;
  contratista: {
    nombre: string;
    documento: string;
  };
  objeto: string;
  monto_original: string;
  monto_vigente: string;
  moneda: string;
  fecha_inicio: string;
  fecha_fin_original: string;
  fecha_fin_vigente: string;
  vigencia: TipoVigenciaExpediente;
  vigencia_etiqueta: string;
  supervisor: {
    nombre: string;
    cargo: string;
  } | null;
  expediente: {
    id: string;
    numero: string;
  };
  fecha_formalizacion: string;
  modificaciones: number;
  ultimo_paquete: {
    codigo: string;
    generado_en: string;
    verificacion: "VALIDO" | null;
  } | null;
  ultima_actuacion: {
    fecha: string;
    titulo: string;
    proceso: string;
  } | null;
}

export interface ListaExpedientes {
  items: ItemExpedienteContractual[];
  total: number;
  limit: number;
  offset: number;
}

export type ResultadoIntegridad = "VERIFIED" | "MISSING" | "MISMATCH" | "NOT_APPLICABLE";

export const ETIQUETAS_INTEGRIDAD: Record<ResultadoIntegridad, string> = {
  VERIFIED: "Verificada",
  MISSING: "Ausente",
  MISMATCH: "No coincide",
  NOT_APPLICABLE: "No aplica",
};

export const ETIQUETAS_VERIFICACION: Record<string, string> = {
  VALIDO: "Válido",
  INVALIDO: "Inválido",
  INCOMPLETO: "Incompleto",
  VERSION_NO_SOPORTADA: "Versión no soportada",
};

export const ETIQUETAS_MOTIVO: Record<string, string> = {
  MANIFIESTO_AUSENTE: "Manifiesto ausente",
  MANIFIESTO_ILEGIBLE: "Manifiesto ilegible",
  PAQUETE_NO_REGISTRADO: "Paquete no registrado",
  MANIFIESTO_ALTERADO: "Manifiesto alterado",
  ARCHIVO_AUSENTE: "Archivo ausente",
  ARCHIVO_ALTERADO: "Archivo alterado",
  ARCHIVO_INESPERADO: "Archivo inesperado",
};

export interface DocumentoExpediente {
  clave: string;
  tipo: string;
  tipo_etiqueta: string;
  titulo: string;
  proceso: string;
  referencia: string;
  version: number | null;
  sha256: string | null;
  fecha: string;
  estado: "DISPONIBLE" | "RESERVADO";
  sellado: boolean;
  document_id: string | null;
  version_id: string | null;
  descarga: string | null;
  enlace: string | null;
}

export const ETIQUETAS_ESTADO_DOCUMENTO: Record<DocumentoExpediente["estado"], string> = {
  DISPONIBLE: "Disponible",
  RESERVADO: "Reservado",
};

export interface Expediente {
  contrato: {
    id: string;
    codigo: string;
    tipo: string;
    tipo_etiqueta: string;
    estado: string;
  };
  resumen: {
    codigo: string;
    tipo_etiqueta: string;
    contratista: {
      nombre: string;
      documento: string;
      representante: string;
    };
    objeto: string;
    monto_original: string;
    monto_vigente: string;
    moneda: string;
    fecha_inicio: string;
    fecha_fin_original: string;
    fecha_fin_vigente: string;
    vigencia: TipoVigenciaExpediente;
    vigencia_etiqueta: string;
    adjudicacion_referencia: string;
    expediente_numero: string;
    supervisor_actual: {
      referencia: string;
      nombre: string;
      cargo: string;
      unidad: string;
    } | null;
    cobertura: {
      total_asignado: string;
      completa: boolean;
      moneda: string;
    };
    ejecucion: {
      estado: string;
      mensaje: string;
    };
  };
  origen: {
    expediente: {
      id: string;
      numero: string;
      objeto: string;
      tipo_contratacion: string;
      modalidad: string;
      unidad: string;
      estado: string;
      fecha_inicio: string;
      enlace: string;
    };
    oferta: {
      id: string;
      referencia: string;
      oferente: string;
      documento: string;
      recibida_en: string;
    };
  };
  adjudicacion: {
    id: string;
    referencia: string;
    fecha: string;
    resultado: string;
    motivacion: string;
    vigente: boolean;
    acto: {
      id: string;
      etiqueta: string;
      enlace: string;
    };
    cargo: string | null;
    enlace: string;
  };
  presupuesto: {
    certificados: Array<{
      id: string;
      codigo: string;
      fecha: string;
      monto: string;
      moneda: string;
      estado: string;
      concepto: string;
      asignado_contrato: string;
      asignado_modificaciones: string;
      comprobante_sha256: string;
      enlace: string;
    }>;
    compromisos: Array<{
      id: string;
      codigo: string;
      fecha: string;
      estado: string;
      moneda: string;
      total: string;
      concepto: string;
      lineas: Array<{
        certificado_codigo: string;
        monto: string;
      }>;
      comprobante_sha256: string;
      enlace: string;
    }>;
    control: Record<string, unknown>;
    efectos: string;
  };
  instrumento: {
    original: {
      monto: string;
      moneda: string;
      fecha_inicio: string;
      fecha_fin: string;
      referencia_instrumento: string;
      fecha_formalizacion: string;
      firmante: {
        cargo: string;
        funcionario: string;
        conversion: string;
      };
      documento: {
        id: string;
        titulo: string;
        version: number;
        sha256: string;
      } | null;
      huella: string;
      enlace: string;
    };
    vigente: Record<string, unknown>;
    fecha_consulta: string;
  };
  garantias: Array<{
    instrumento_id: string;
    referencia: string;
    tipo_etiqueta: string;
    emisor: string;
    monto: string;
    moneda: string;
    vigente_desde: string;
    vigente_hasta: string;
    estado: string;
    estado_etiqueta: string;
    documento: {
      id: string;
      version: number;
      sha256: string;
    };
    eventos: Array<{
      accion: string;
      accion_etiqueta: string;
      fecha: string;
      motivo: string;
    }>;
    enlace: string;
  }>;
  modificaciones: {
    cantidad: number;
    historial: Array<Record<string, unknown>>;
  };
  supervision: {
    vigente: unknown;
    programada: unknown;
    historia: unknown;
  };
  ejecucion: EjecucionExpediente;
  fuentes_futuras: Array<{
    proceso: string;
    titulo: string;
    estado: string;
    mensaje: string;
  }>;
  actos: Array<{
    id: string;
    etiqueta: string;
    tipo: string;
    numero: string;
    fecha: string;
    estado: string;
    asunto: string;
    rol: string;
    enlace: string;
  }>;
  documentos: DocumentoExpediente[];
  cronologia_total: number;
  permisos: {
    auditoria: boolean;
    ver_paquetes: boolean;
    generar_paquete: boolean;
  };
}

export interface EjecucionExpediente {
  proceso: "CNT-03";
  estado: string;
  estado_ejecucion:
    | "SIN_INICIAR"
    | "EN_EJECUCION"
    | "TERMINADA"
    | "RECIBIDA_PROVISIONAL"
    | "RECIBIDA_DEFINITIVA"
    | "CERRADA";
  estado_etiqueta: string;
  resumen: {
    valuado_conformado: string;
    valuado_presentado: string;
    saldo: string;
    facturado: string;
    hitos_total: number;
    hitos_cumplidos: number;
    entregables_pendientes: number;
  };
  inicio: ActuacionEjecucion | null;
  terminacion: ActuacionEjecucion | null;
  cierre: CierreEjecucion | null;
  hitos: HitoEjecucion[];
  entregables: EntregableEjecucion[];
  valuaciones: ValuacionEjecucion[];
  recepciones: RecepcionEjecucion[];
  facturas: FacturaEjecucion[];
  enlace: string;
}

export interface NodoCronologia {
  orden: number;
  fecha: string;
  fecha_registro: string;
  fecha_documento: string;
  fecha_efectiva: string;
  tipo: string;
  tipo_etiqueta: string;
  proceso: string;
  fuente_id: string;
  titulo: string;
  actor: string;
  autoridad: string;
  unidad: string;
  documentos: string[];
  estado: string;
  enlace: string;
}

export interface Cronologia {
  items: NodoCronologia[];
  total: number;
  limit: number;
  offset: number;
  procesos: string[];
}

export interface EventoAuditoriaExpediente {
  id: string;
  fecha: string;
  proceso: string;
  proceso_nombre: string;
  accion: string;
  accion_etiqueta: string;
  entidad: string;
  usuario: string;
  enlace: string;
}

export interface AuditoriaExpediente {
  items: EventoAuditoriaExpediente[];
  total: number;
  limit: number;
  offset: number;
}

export interface Integridad {
  verificado_en: string;
  resumen: Record<ResultadoIntegridad, number>;
  documentos: Array<{
    clave: string;
    titulo: string;
    tipo: string;
    sha256_registrado: string;
    resultado: ResultadoIntegridad;
    detalle: string;
  }>;
}

export interface PaqueteExpediente {
  id: string;
  codigo: string;
  numero_generacion: number;
  proposito: string;
  generado_en: string;
  generado_por: string;
  corte: string;
  eventos: number;
  documentos_incluidos: number;
  documentos_excluidos: number;
  archivos: number;
  bytes: number;
  huella_paquete: string;
  huella_manifiesto: string;
  nombre_archivo: string;
  ultima_verificacion: {
    resultado: string;
    verificado_en: string;
  } | null;
}

export interface PaquetesExpediente {
  items: PaqueteExpediente[];
  total: number;
}

export interface VerificacionPaqueteExpediente {
  resultado: string;
  motivos: Array<{
    codigo: string;
    ruta: string;
  }>;
  paquete: {
    id: string;
    codigo: string;
    contrato_codigo: string;
  } | null;
  huella_archivo: string;
  bytes_archivo: number;
  identico: boolean;
  verificacion_id: string;
}

export function rutaExpediente(contratoId: string): string {
  return `/gobierno/contratos/${contratoId}/expediente`;
}

export function abreviarHuella(huella: string, cantidad = 16): string {
  return huella.length > cantidad ? `${huella.slice(0, cantidad)}…` : huella;
}
