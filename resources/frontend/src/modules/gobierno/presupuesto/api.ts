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
};

export const ETIQUETAS_TIPO_PARTIDA: Record<"RECURSO" | "EGRESO", string> = {
  RECURSO: "Recurso",
  EGRESO: "Egreso",
};
