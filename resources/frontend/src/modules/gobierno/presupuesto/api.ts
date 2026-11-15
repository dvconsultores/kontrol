export type EstadoEjercicio = "BORRADOR" | "APROBADO" | "RECONDUCIDO" | "CERRADO";

export type EjercicioResumen = {
  id: string;
  anio: number;
  moneda_funcional: string;
  estado: EstadoEjercicio;
  version: number;
  congelado: boolean;
  reconduccion_definitiva: boolean;
  precompromiso_activo: boolean;
};

export type NivelProgramatico = {
  orden: number;
  nombre: string;
};

export type CategoriaProgramatica = {
  id: string;
  nivel_orden: number;
  nivel_nombre: string;
  parent_id: string | null;
  codigo: string;
  codigo_completo: string;
  denominacion: string;
};

export type ClasificadorEjercicio = {
  edicion: string;
  fecha_edicion: string | null;
  procedencia: string;
  documento_id: string | null;
  documento_sha256: string | null;
  partidas_recurso: number;
  partidas_egreso: number;
};

export type FundamentoEjercicio = {
  tipo: "ORDENANZA" | "RECONDUCCION";
  referencia: string;
  fecha: string;
  documento_id: string | null;
  documento_sha256: string | null;
  huella: string;
  en: string;
};

export type HistoriaEjercicio = {
  tipo: string;
  detalle: Record<string, unknown> | null;
  en: string;
};

export type PartidaClasificador = {
  id: string;
  tipo: "RECURSO" | "EGRESO";
  codigo: string;
  denominacion: string;
  nivel: number;
  codigo_padre: string | null;
  vigente_desde: string;
  vigente_hasta: string | null;
};

export type EjercicioDetalle = EjercicioResumen & {
  precompromiso_desde: string | null;
  niveles: NivelProgramatico[];
  categorias: CategoriaProgramatica[];
  clasificador: ClasificadorEjercicio | null;
  fundamentos: FundamentoEjercicio[];
  faltantes: string[];
  historia: HistoriaEjercicio[];
  fijado_en: string | null;
  cerrado_en: string | null;
  motivo_cierre: string | null;
};

export type EscribirEjercicio = (
  ruta: string,
  method: "PUT" | "POST" | "PATCH" | "DELETE",
  body?: unknown,
) => Promise<EjercicioDetalle>;

export type EscribirBloque = <T>(
  ruta: string,
  method: "PUT" | "POST" | "PATCH" | "DELETE",
  body?: unknown,
) => Promise<T>;

export type ImportarPartidas = (archivo: File) => Promise<EjercicioDetalle>;

export const CONSULTA_PRESUPUESTO = ["gobierno", "presupuesto"] as const;
export const RUTA_EJERCICIOS = "/gobierno/presupuesto/ejercicios";

export interface PlanVista {
  version: number;
  congelado: boolean;
  plan: {
    denominacion: string;
    documento_id: string | null;
    documento_sha256: string | null;
  } | null;
  objetivos: {
    id: string;
    codigo: string;
    descripcion: string;
  }[];
  vinculos: {
    categoria_id: string;
    codigo_completo: string;
    denominacion: string;
    unidad: {
      id: string;
      codigo: string;
      nombre: string;
    } | null;
    objetivo: {
      id: string;
      codigo: string;
    } | null;
  }[];
  metas: {
    id: string;
    categoria_id: string;
    codigo_completo: string;
    descripcion: string;
    unidad_medida: string;
    cantidad: string;
    indicador: string;
    formula: string | null;
  }[];
  unidades_disponibles: {
    id: string;
    codigo: string;
    nombre: string;
  }[];
  estructura_organizativa: {
    estado: string;
  } | null;
}

export type ObjetivoPlan = PlanVista["objetivos"][number];
export type VinculoCategoria = PlanVista["vinculos"][number];
export type MetaFisica = PlanVista["metas"][number];
export type UnidadDisponible = PlanVista["unidades_disponibles"][number];

export interface FuentesVista {
  version: number;
  congelado: boolean;
  items: {
    id: string;
    codigo: string;
    denominacion: string;
    procedencia: string;
    documento_id: string | null;
    documento_sha256: string | null;
    vigente_desde: string | null;
    vigente_hasta: string | null;
    restricciones: {
      id: string;
      descripcion: string;
      fundamento: string;
      partidas: string[];
    }[];
  }[];
}

export type FuenteFinanciamiento = FuentesVista["items"][number];
export type RestriccionUso = FuenteFinanciamiento["restricciones"][number];

export interface PresupuestoAprobadoVista {
  version: number;
  congelado: boolean;
  moneda: string;
  ingresos: {
    id: string;
    partida: { id: string; codigo: string; denominacion: string };
    monto: string;
  }[];
  creditos: {
    id: string;
    categoria: { id: string; codigo_completo: string; denominacion: string };
    unidad: { id: string; codigo: string; nombre: string } | null;
    partida: { id: string; codigo: string; denominacion: string };
    fuente: { id: string; codigo: string; denominacion: string };
    monto: string;
  }[];
  existencias_tesoro: {
    monto: string;
    fecha_corte: string;
    documento_id: string;
    documento_sha256: string;
  } | null;
  totales: {
    ingresos: string;
    creditos: string;
    existencias: string;
    holgura_tesoro: string;
    disponible: string;
    diferencia: string;
    cuadra: boolean;
  };
  opciones: {
    categorias: { id: string; codigo_completo: string; denominacion: string }[];
    partidas_egreso: { id: string; codigo: string; denominacion: string }[];
    partidas_recurso: { id: string; codigo: string; denominacion: string }[];
    fuentes: {
      id: string;
      codigo: string;
      denominacion: string;
      partidas_permitidas: string[] | null;
    }[];
  };
}

export interface RefEtiqueta { id: string; etiqueta: string }
export interface DisponibilidadVista { anio: number; estado: EstadoEjercicio; moneda: string; certificable: boolean;
  items: { credito_id: string; categoria: RefEtiqueta; unidad: RefEtiqueta | null; partida: RefEtiqueta; fuente: RefEtiqueta; credito: string; certificado: string; comprometido: string; disponible: string }[];
  totales: { credito: string; certificado: string; comprometido: string; disponible: string };
  filtros: { categorias: RefEtiqueta[]; unidades: RefEtiqueta[]; partidas: RefEtiqueta[]; fuentes: RefEtiqueta[] };
  firmantes: { cargo_id: string; etiqueta: string; unidad: string }[]; expedientes: RefEtiqueta[] }
export interface Certificacion { id: string; codigo: string; estado: "VIGENTE" | "ANULADA"; fecha: string; emitida_en: string; monto: string; consumido: string; remanente: string; situacion: SituacionCertificado; saldo_antes: string;
  saldo_despues: string; moneda: string; concepto: string; expediente_id: string | null; expediente_referencia: string; credito_id: string; categoria: string;
  unidad: string | null; partida: string; fuente: string; firmante_cargo: string; firmante_unidad: string; firmante_funcionario: string | null; emitida_por: string;
  huella: string; documento_nombre: string; documento_sha256: string; anulada_en: string | null; anulada_por: string | null; motivo_anulacion: string | null }
export interface CertificacionesVista { items: Certificacion[] }

export type SituacionCertificado = "DISPONIBLE" | "PARCIALMENTE_CONSUMIDA" | "AGOTADA" | "ANULADA";

export const ETIQUETAS_SITUACION_CERTIFICADO: Record<SituacionCertificado, string> = {
  DISPONIBLE: "Disponible",
  PARCIALMENTE_CONSUMIDA: "Parcialmente consumida",
  AGOTADA: "Agotada",
  ANULADA: "Anulada",
};

export interface CertificadoOpcion { certificado_id: string; codigo: string; credito_id: string; categoria: string; unidad: string | null; partida: string;
  fuente: string; expediente_id: string | null; expediente_referencia: string; monto: string; consumido: string; remanente: string;
  situacion: SituacionCertificado; etiqueta: string }

export interface AutoridadOpcion { cargo_id: string; etiqueta: string; unidad: string; limite_tipo: "SIN_LIMITE" | "MONTO"; limite_monto: string | null;
  limite_moneda: string | null; limite: string }

export interface OpcionesCompromisoVista { anio: number; estado: EstadoEjercicio; moneda: string; comprometible: boolean;
  certificados: CertificadoOpcion[]; autoridades: AutoridadOpcion[]; soportes: RefEtiqueta[] }

export interface LineaCompromiso { linea: number; certificado_id: string; certificado_codigo: string; credito_id: string; categoria: string;
  unidad: string | null; partida: string; fuente: string; monto: string }

export interface TasaUsada {
  tasa_id: string;
  moneda: string;
  moneda_cotizacion: string;
  fecha_efectiva: string;
  valor: string;
  fuente: string;
  fuente_referencia: string;
  version: number;
  evidencia_sha256: string | null;
}

export interface ConversionLimite {
  requiere_conversion: boolean;
  moneda_operacion: string;
  moneda_limite: string;
  fecha: string;
  tasas: TasaUsada[];
  total: string;
  limite: string;
  total_ves: string | null;
  limite_ves: string | null;
  dentro_del_limite: boolean;
  resultado: "DENTRO_DEL_LIMITE" | "EXCEDE_LIMITE" | "SIN_TASA";
  monedas_sin_tasa: string[];
}

export interface VerificacionLimite {
  cargo_id: string;
  limite_tipo: string;
  limite: string;
  verificacion: ConversionLimite | null;
}

export interface Compromiso { id: string; codigo: string; estado: "VIGENTE" | "ANULADO"; fecha: string; emitido_en: string; total: string; moneda: string;
  concepto: string; expediente_id: string | null; expediente_referencia: string; autoridad_cargo: string; autoridad_unidad: string;
  autoridad_funcionario: string | null; limite: string; soporte_documento_id: string; soporte: string; soporte_sha256: string; emitido_por: string;
  huella: string; documento_nombre: string; documento_sha256: string; anulado_en: string | null; anulado_por: string | null;
  motivo_anulacion: string | null; lineas: LineaCompromiso[]; conversion: ConversionLimite | null }

export interface CompromisosVista { items: Compromiso[] }

export const ETIQUETAS_ESTADO_EJERCICIO: Record<EstadoEjercicio, string> = {
  BORRADOR: "Borrador",
  APROBADO: "Aprobado",
  RECONDUCIDO: "Reconducido",
  CERRADO: "Cerrado",
};

export const ETIQUETAS_HISTORIA_EJERCICIO: Record<string, string> = {
  CREADO: "Ejercicio creado",
  NIVELES_CONFIGURADOS: "Niveles configurados",
  CATEGORIA_CREADA: "Categoría creada",
  CATEGORIA_MODIFICADA: "Categoría modificada",
  CATEGORIA_ELIMINADA: "Categoría eliminada",
  CLASIFICADOR_REGISTRADO: "Clasificador registrado",
  PROCEDENCIA_MODIFICADA: "Procedencia modificada",
  PARTIDA_CREADA: "Partida creada",
  PARTIDA_ELIMINADA: "Partida eliminada",
  PARTIDAS_IMPORTADAS: "Partidas importadas",
  APROBADO: "Aprobado por ordenanza",
  RECONDUCIDO: "Reconducido",
  CERRADO: "Cerrado",
  PRECOMPROMISO_CAMBIADO: "Precompromiso modificado",
  INGRESO_REGISTRADO: "Ingreso estimado registrado",
  INGRESO_MODIFICADO: "Ingreso estimado modificado",
  INGRESO_ELIMINADO: "Ingreso estimado eliminado",
  CREDITO_REGISTRADO: "Crédito registrado",
  CREDITO_MODIFICADO: "Crédito modificado",
  CREDITO_ELIMINADO: "Crédito eliminado",
  EXISTENCIAS_REGISTRADAS: "Existencias del Tesoro declaradas",
  EXISTENCIAS_ELIMINADAS: "Existencias del Tesoro retiradas",
  CERTIFICACION_EMITIDA: "Certificación de disponibilidad emitida",
  CERTIFICACION_ANULADA: "Certificación de disponibilidad anulada",
  COMPROMISO_REGISTRADO: "Compromiso presupuestario registrado",
  COMPROMISO_ANULADO: "Compromiso presupuestario anulado",
};

export const ETIQUETAS_TIPO_PARTIDA: Record<"RECURSO" | "EGRESO", string> = {
  RECURSO: "Recurso",
  EGRESO: "Egreso",
};
