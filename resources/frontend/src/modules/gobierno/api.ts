/**
 * Contrato de la API del ente de Gobierno (GOV-0-01). El servidor es la autoridad:
 * estado, versión, faltantes y documento vinculado vienen de él.
 */
import { useQuery } from "@tanstack/react-query";

import { formatMoney } from "@/lib/format";

import { apiFetch } from "@/api/client";

export type EstadoEnte = "BORRADOR" | "ACTIVO";
export type NivelTerritorial = "NACIONAL" | "ESTADAL" | "MUNICIPAL";
export type FormaOrganizativa =
  | "ADMINISTRACION_CENTRAL"
  | "INSTITUTO_PUBLICO"
  | "SERVICIO_DESCONCENTRADO"
  | "ENTE_DESCENTRALIZADO";
export type TipoDeActo = "LEY" | "DECRETO" | "ORDENANZA" | "RESOLUCION" | "OTRO";

export interface EnteDatos {
  denominacion: string;
  siglas: string | null;
  rif: string | null;
  nivel_territorial: NivelTerritorial | null;
  forma_organizativa: FormaOrganizativa | null;
  organo_adscripcion: string | null;
  entidad_federal: string | null;
  municipio: string | null;
  acto_tipo: TipoDeActo | null;
  acto_numero: string | null;
  acto_fecha: string | null;
  acto_publicacion: string | null;
}

export interface Ente extends EnteDatos {
  id: string;
  estado: EstadoEnte;
  version: number;
  faltantes_para_activar: string[];
  documento_vinculado: boolean;
  activado_en: string | null;
  activado_por: string | null;
  creado_en: string;
  actualizado_en: string;
}

export interface VersionEnte {
  version: number;
  estado: EstadoEnte;
  motivo: string | null;
  actor_id: string | null;
  creado_en: string;
  datos: Partial<EnteDatos>;
}

export interface VersionesEnte {
  items: VersionEnte[];
  total: number;
}

export const CAMPOS_ENTE: readonly (keyof EnteDatos)[] = [
  "denominacion",
  "siglas",
  "rif",
  "nivel_territorial",
  "forma_organizativa",
  "organo_adscripcion",
  "entidad_federal",
  "municipio",
  "acto_tipo",
  "acto_numero",
  "acto_fecha",
  "acto_publicacion",
] as const;

export const ETIQUETA_ESTADO: Record<EstadoEnte, string> = {
  BORRADOR: "Borrador",
  ACTIVO: "Activo",
};

export const ETIQUETA_NIVEL: Record<NivelTerritorial, string> = {
  NACIONAL: "Nacional",
  ESTADAL: "Estadal",
  MUNICIPAL: "Municipal",
};

export const ETIQUETA_FORMA: Record<FormaOrganizativa, string> = {
  ADMINISTRACION_CENTRAL: "Administración central",
  INSTITUTO_PUBLICO: "Instituto público",
  SERVICIO_DESCONCENTRADO: "Servicio desconcentrado",
  ENTE_DESCENTRALIZADO: "Ente descentralizado",
};

export const ETIQUETA_ACTO: Record<TipoDeActo, string> = {
  LEY: "Ley",
  DECRETO: "Decreto",
  ORDENANZA: "Ordenanza",
  RESOLUCION: "Resolución",
  OTRO: "Otro",
};

export const ETIQUETA_CAMPO: Record<keyof EnteDatos, string> = {
  denominacion: "Denominación oficial",
  siglas: "Siglas",
  rif: "RIF",
  nivel_territorial: "Nivel político-territorial",
  forma_organizativa: "Forma organizativa",
  organo_adscripcion: "Órgano de adscripción",
  entidad_federal: "Entidad federal",
  municipio: "Municipio",
  acto_tipo: "Tipo de acto de creación",
  acto_numero: "Número del acto",
  acto_fecha: "Fecha del acto",
  acto_publicacion: "Publicación oficial",
};

export const ETIQUETA_FALTANTE: Readonly<Record<string, string>> = {
  DENOMINACION: "Denominación oficial",
  NIVEL_TERRITORIAL: "Nivel político-territorial",
  FORMA_ORGANIZATIVA: "Forma organizativa",
  ORGANO_ADSCRIPCION: "Órgano de adscripción",
  ENTIDAD_FEDERAL: "Entidad federal",
  MUNICIPIO: "Municipio",
  ACTO_TIPO: "Tipo de acto de creación",
  ACTO_NUMERO: "Número del acto",
  ACTO_FECHA: "Fecha del acto",
  ACTO_PUBLICACION: "Publicación oficial",
  DOCUMENTO_ACTO: "Documento del acto de creación",
};

export const CONSULTA_GOBIERNO = ["gobierno"] as const;

export function useModuloGobierno(): boolean {
  const { data } = useQuery({
    queryKey: ["licencia", "modulo", "gobierno"],
    queryFn: () => apiFetch<{ habilitado: boolean }>("/gobierno/modulo"),
    staleTime: 300_000,
    retry: false,
  });
  return data?.habilitado === true;
}

export type EstadoEstructura = "BORRADOR" | "VIGENTE" | "CERRADA";
export type EstadoUnidad = "ACTIVA" | "INACTIVA";
export type TipoDeUnidad =
  | "ORGANO"
  | "UNIDAD_ADMINISTRATIVA"
  | "UNIDAD_EJECUTORA_LOCAL"
  | "DEPENDENCIA"
  | "SEDE"
  | "CENTRO_GESTOR";

export interface Unidad {
  id: string;
  codigo: string;
  denominacion: string;
  tipo: TipoDeUnidad;
  unidad_superior_id: string | null;
  nivel: number;
  estado: EstadoUnidad;
  vigente_desde: string;
  vigente_hasta: string | null;
  version: number;
}

export interface Estructura {
  id: string;
  ejercicio: number;
  estado: EstadoEstructura;
  version: number;
  copiada_de: number | null;
  publicada_en: string | null;
  publicada_por: string | null;
  cerrada_en: string | null;
  cerrada_por: string | null;
  documento_vinculado: boolean;
  faltantes_para_publicar: string[];
  unidades: Unidad[];
  creado_en: string;
}

export interface EstructuraResumen {
  ejercicio: number;
  estado: EstadoEstructura;
  version: number;
  unidades_activas: number;
  publicada_en: string | null;
  cerrada_en: string | null;
}

export interface ListaEstructuras {
  items: EstructuraResumen[];
  total: number;
}

export interface VersionUnidad {
  version: number;
  estado: EstadoUnidad;
  motivo: string | null;
  actor_id: string | null;
  creado_en: string;
  datos: Record<string, unknown>;
}

export interface VersionesUnidad {
  items: VersionUnidad[];
  total: number;
}

export const ETIQUETA_ESTADO_ESTRUCTURA: Record<EstadoEstructura, string> = {
  BORRADOR: "Borrador",
  VIGENTE: "Vigente",
  CERRADA: "Cerrada",
};

export const ETIQUETA_ESTADO_UNIDAD: Record<EstadoUnidad, string> = {
  ACTIVA: "Activa",
  INACTIVA: "Inactiva",
};

export const ETIQUETA_TIPO_UNIDAD: Record<TipoDeUnidad, string> = {
  ORGANO: "Órgano",
  UNIDAD_ADMINISTRATIVA: "Unidad administrativa",
  UNIDAD_EJECUTORA_LOCAL: "Unidad ejecutora local",
  DEPENDENCIA: "Dependencia",
  SEDE: "Sede",
  CENTRO_GESTOR: "Centro gestor",
};

export const ETIQUETA_FALTANTE_ESTRUCTURA: Readonly<Record<string, string>> = {
  UNIDADES: "Al menos una unidad activa",
  DOCUMENTO_ACTO: "Acto que aprueba la estructura",
  ENTE_ACTIVO: "El ente debe estar activo (Gobierno › Configuración del ente)",
};

export const CONSULTA_ESTRUCTURAS = [...CONSULTA_GOBIERNO, "estructuras"] as const;

export type EstadoCargo = "BORRADOR" | "VIGENTE" | "INACTIVO";
export type AccionCompetencia =
  | "SOLICITAR"
  | "COMPROMETER"
  | "CAUSAR"
  | "ORDENAR_PAGO"
  | "PAGAR"
  | "REGISTRAR"
  | "CUSTODIAR"
  | "APROBAR"
  | "AUDITAR"
  | "FIRMAR";
export type MateriaCompetencia =
  | "PRESUPUESTO"
  | "CONTRATACIONES"
  | "TESORERIA"
  | "CONTABILIDAD"
  | "BIENES"
  | "EXPEDIENTE";
export type TipoDeLimite = "SIN_LIMITE" | "MONTO";
export type MonedaDeLimite = "VES" | "USD" | "EUR";

export interface Competencia {
  id: string;
  accion: AccionCompetencia;
  materia: MateriaCompetencia;
  tipo_limite: TipoDeLimite;
  monto: string | null;
  moneda: MonedaDeLimite | null;
  fundamento: string | null;
}

export interface Cargo {
  id: string;
  codigo: string;
  denominacion: string;
  unidad_id: string;
  unidad_codigo: string;
  unidad_denominacion: string;
  estado: EstadoCargo;
  vigente_desde: string;
  vigente_hasta: string | null;
  version: number;
  competencias: Competencia[];
  faltantes_para_activar: string[];
  documento_vinculado: boolean;
  activado_en: string | null;
  activado_por: string | null;
  creado_en: string;
}

export interface ListaCargos {
  estructura: { ejercicio: number; estado: EstadoEstructura; version: number };
  items: Cargo[];
  total: number;
}

export interface VersionCargo {
  version: number;
  estado: EstadoCargo;
  motivo: string | null;
  actor_id: string | null;
  creado_en: string;
  datos: Record<string, unknown>;
}

export interface VersionesCargo {
  items: VersionCargo[];
  total: number;
}

export const ETIQUETA_ESTADO_CARGO: Record<EstadoCargo, string> = {
  BORRADOR: "Borrador",
  VIGENTE: "Vigente",
  INACTIVO: "Inactivo",
};

export const ETIQUETA_ACCION: Record<AccionCompetencia, string> = {
  SOLICITAR: "Solicitar",
  COMPROMETER: "Comprometer",
  CAUSAR: "Causar",
  ORDENAR_PAGO: "Ordenar el pago",
  PAGAR: "Pagar",
  REGISTRAR: "Registrar",
  CUSTODIAR: "Custodiar",
  APROBAR: "Aprobar",
  AUDITAR: "Auditar",
  FIRMAR: "Firmar",
};

export const ETIQUETA_MATERIA: Record<MateriaCompetencia, string> = {
  PRESUPUESTO: "Presupuesto",
  CONTRATACIONES: "Contrataciones",
  TESORERIA: "Tesorería",
  CONTABILIDAD: "Contabilidad",
  BIENES: "Bienes públicos",
  EXPEDIENTE: "Expediente y documentos",
};

export const ETIQUETA_MONEDA: Record<MonedaDeLimite, string> = {
  VES: "Bolívares (VES)",
  USD: "Dólares (USD)",
  EUR: "Euros (EUR)",
};

export const ETIQUETA_FALTANTE_CARGO: Readonly<Record<string, string>> = {
  ESTRUCTURA_VIGENTE:
    "La estructura del ejercicio debe estar vigente (Gobierno › Estructura organizativa)",
  COMPETENCIAS: "Al menos una competencia",
  DOCUMENTO_ACTO: "Acto del cargo",
};

/** Límite en lenguaje de negocio: «Sin límite» o «Hasta 50.000,00 USD por operación» (PDD-ORG03-07). */
export function describirLimite(
  c: Pick<Competencia, "tipo_limite" | "monto" | "moneda">,
): string {
  if (c.tipo_limite === "SIN_LIMITE" || c.monto === null) return "Sin límite";
  return `Hasta ${formatMoney(c.monto)} ${c.moneda ?? ""} por operación`;
}

export const CONSULTA_CARGOS = [...CONSULTA_GOBIERNO, "cargos"] as const;
