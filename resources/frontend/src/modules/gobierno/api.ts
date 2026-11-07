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

export type TipoActo =
  | "DECRETO"
  | "RESOLUCION"
  | "ORDEN"
  | "PROVIDENCIA"
  | "INSTRUCCION"
  | "CIRCULAR"
  | "OTRA_DECISION";
export type Titularidad = "TITULAR" | "DELEGACION" | "ENCARGADURIA" | "SUPLENCIA";
export type CaracterActo = "GENERAL" | "PARTICULAR" | "INTERNO";
export type MedioEficacia = "GACETA" | "PERSONAL" | "PRENSA";
export type EstadoActo = "BORRADOR" | "EMITIDO" | "EFICAZ" | "REVOCADO" | "NULO";
export type FaltanteActo =
  | "DOCUMENTO_ACTO"
  | "HECHOS"
  | "FUNDAMENTOS"
  | "DECISION"
  | "DESTINATARIO"
  | "AUTORIDAD";

export interface ActoReferido {
  id: string;
  tipo: TipoActo;
  numero: string;
  fecha: string;
}

export interface ActoReferidoCorto {
  id: string;
  tipo: TipoActo;
  numero: string;
}

export interface Acto {
  id: string;
  tipo: TipoActo;
  denominacion_tipo: string | null;
  numero: string;
  fecha: string;
  lugar: string;
  cargo: {
    id: string;
    codigo: string;
    denominacion: string;
    unidad_codigo: string;
    unidad_denominacion: string;
  };
  competencia: {
    accion: AccionCompetencia;
    materia: MateriaCompetencia;
  };
  fundamento_competencia: string;
  funcionario: string;
  titularidad: Titularidad;
  delegacion_numero: string | null;
  delegacion_fecha: string | null;
  caracter: CaracterActo;
  simple_tramite: boolean;
  destinatario: string | null;
  asunto: string;
  hechos: string | null;
  fundamentos: string | null;
  decision: string | null;
  estado: EstadoActo;
  faltantes_para_emitir: FaltanteActo[];
  documento_acto_id: string | null;
  medio: MedioEficacia | null;
  referencia_publicacion: string | null;
  fecha_publicacion_notificacion: string | null;
  documento_eficacia_id: string | null;
  fecha_eficacia: string | null;
  notificaciones: NotificacionesDelActo | null;
  revocado_por: ActoReferido | null;
  anulado_por: ActoReferido | null;
  revoca_a: ActoReferidoCorto[];
  anula_a: ActoReferidoCorto[];
  version: number;
  emitido_en: string | null;
  emitido_por: string | null;
  creado_en: string;
}

export interface ActoResumen {
  id: string;
  tipo: TipoActo;
  denominacion_tipo: string | null;
  numero: string;
  fecha: string;
  cargo_codigo: string;
  cargo_denominacion: string;
  unidad_codigo: string;
  caracter: CaracterActo;
  asunto: string;
  estado: EstadoActo;
  fecha_eficacia: string | null;
}

export interface ListaActos {
  anio: number;
  items: ActoResumen[];
  total: number;
}

export interface Autoridad {
  cargo_id: string;
  codigo: string;
  denominacion: string;
  unidad_codigo: string;
  unidad_denominacion: string;
  estado: EstadoCargo;
  competencias: {
    accion: AccionCompetencia;
    materia: MateriaCompetencia;
  }[];
}

export interface ListaAutoridades {
  fecha: string;
  items: Autoridad[];
}

export interface VersionActo {
  version: number;
  estado: EstadoActo;
  motivo: string | null;
  actor: string | null;
  creado_en: string;
  instantanea: Record<string, unknown>;
}

export interface VersionesActo {
  items: VersionActo[];
  total: number;
}

export const ETIQUETA_TIPO_ACTO: Record<TipoActo, string> = {
  DECRETO: "Decreto",
  RESOLUCION: "Resolución",
  ORDEN: "Orden",
  PROVIDENCIA: "Providencia",
  INSTRUCCION: "Instrucción",
  CIRCULAR: "Circular",
  OTRA_DECISION: "Otra decisión",
};

export const ETIQUETA_TITULARIDAD: Record<Titularidad, string> = {
  TITULAR: "Titular",
  DELEGACION: "Por delegación",
  ENCARGADURIA: "Encargado",
  SUPLENCIA: "Suplente",
};

export const ETIQUETA_CARACTER: Record<CaracterActo, string> = {
  GENERAL: "General (se publica)",
  PARTICULAR: "Particular (se notifica)",
  INTERNO: "Interno",
};

export const ETIQUETA_MEDIO: Record<MedioEficacia, string> = {
  GACETA: "Gaceta Oficial",
  PERSONAL: "Notificación personal",
  PRENSA: "Publicación en prensa",
};

export const ETIQUETA_ESTADO_ACTO: Record<EstadoActo, string> = {
  BORRADOR: "Borrador",
  EMITIDO: "Emitido",
  EFICAZ: "Eficaz",
  REVOCADO: "Revocado",
  NULO: "Nulo",
};

export function contextoDeActos(params: URLSearchParams): { anio?: number; estado?: EstadoActo } {
  const resultado: { anio?: number; estado?: EstadoActo } = {};
  const anio = params.get("anio");
  if (anio !== null && /^\d+$/.test(anio)) {
    const valor = Number(anio);
    if (valor >= 1900 && valor <= 2100) {
      resultado.anio = valor;
    }
  }
  const estado = params.get("estado");
  if (estado !== null && Object.hasOwn(ETIQUETA_ESTADO_ACTO, estado)) {
    resultado.estado = estado as EstadoActo;
  }
  return resultado;
}

export const ETIQUETA_FALTANTE_ACTO: Readonly<Record<FaltanteActo, string>> = {
  DOCUMENTO_ACTO: "El PDF firmado del acto",
  HECHOS: "Los hechos",
  FUNDAMENTOS: "Los fundamentos legales",
  DECISION: "La decisión",
  DESTINATARIO: "El destinatario",
  AUTORIDAD: "Un cargo vigente con esa competencia en la fecha del acto",
};

export const MEDIOS_POR_CARACTER: Readonly<Record<CaracterActo, readonly MedioEficacia[]>> = {
  GENERAL: ["GACETA"],
  PARTICULAR: ["PERSONAL", "PRENSA"],
  INTERNO: [],
};

/** Nombre del acto en lenguaje de negocio: «Decreto Nº 12» u «Otra decisión: <denominación> Nº 12». */
export function nombreDeActo(a: {
  tipo: TipoActo;
  denominacion_tipo?: string | null;
  numero: string;
}): string {
  return `${a.denominacion_tipo ?? ETIQUETA_TIPO_ACTO[a.tipo]} Nº ${a.numero}`;
}

export const CONSULTA_ACTOS = [...CONSULTA_GOBIERNO, "actos"] as const;

// ---------------------------------------------------------------------------
// Notificaciones administrativas (DOC-04)
// ---------------------------------------------------------------------------

export type TipoPersona = "NATURAL" | "JURIDICA";
export type EstadoNotificacion = "PENDIENTE" | "NOTIFICADA" | "ANULADA";
export type MedioIntento = "PERSONAL" | "PRENSA";
export type ResultadoIntento = "ENTREGADA" | "FALLIDA" | "PUBLICADA";

export interface ActoDeNotificacion {
  id: string;
  tipo: TipoActo;
  denominacion_tipo: string | null;
  numero: string;
  fecha: string;
  estado: EstadoActo;
}

export interface NotificacionEntrada {
  acto_id: string;
  tipo_persona: TipoPersona;
  nombre: string;
  identificacion: string;
  domicilio: string;
  apoderado_nombre: string | null;
  apoderado_identificacion: string | null;
  recursos: string;
}

export type NotificacionCambio = Partial<Omit<NotificacionEntrada, "acto_id">>;

export interface IntentoEntrada {
  medio: MedioIntento;
  resultado: ResultadoIntento;
  fecha: string;
  documento_oficio_id: string;
  documento_id: string;
  receptor_nombre: string | null;
  receptor_identificacion: string | null;
  motivo_fallo: string | null;
  diario: string | null;
  referencia: string | null;
}

export interface Intento {
  numero: number;
  medio: MedioIntento;
  resultado: ResultadoIntento;
  fecha: string;
  receptor_nombre: string | null;
  receptor_identificacion: string | null;
  motivo_fallo: string | null;
  diario: string | null;
  referencia: string | null;
  documento_id: string;
  registrado_por: string | null;
  creado_en: string;
}

export interface Notificacion {
  id: string;
  acto: ActoDeNotificacion;
  tipo_persona: TipoPersona;
  nombre: string;
  identificacion: string;
  domicilio: string;
  apoderado_nombre: string | null;
  apoderado_identificacion: string | null;
  recursos: string;
  documento_oficio_id: string | null;
  estado: EstadoNotificacion;
  fecha_notificacion: string | null;
  medio_notificacion: MedioIntento | null;
  motivo_anulacion: string | null;
  intentos: Intento[];
  puede_publicar_en_prensa: boolean;
  version: number;
  creado_en: string;
}

export interface NotificacionResumen {
  id: string;
  acto: ActoDeNotificacion;
  tipo_persona: TipoPersona;
  nombre: string;
  identificacion: string;
  estado: EstadoNotificacion;
  intentos: number;
  fecha_notificacion: string | null;
  medio_notificacion: MedioIntento | null;
}

export interface ListaNotificaciones {
  anio: number;
  items: NotificacionResumen[];
  total: number;
}

export interface VersionNotificacion {
  version: number;
  estado: EstadoNotificacion;
  motivo: string | null;
  actor: string | null;
  creado_en: string;
  instantanea: Record<string, unknown>;
}

export interface VersionesNotificacion {
  items: VersionNotificacion[];
  total: number;
}

export interface NotificacionesDelActo {
  total: number;
  notificadas: number;
  pendientes: number;
}

export const ETIQUETA_TIPO_PERSONA: Record<TipoPersona, string> = {
  NATURAL: "Persona natural",
  JURIDICA: "Persona jurídica",
};

export const ETIQUETA_ESTADO_NOTIFICACION: Record<EstadoNotificacion, string> = {
  PENDIENTE: "Pendiente",
  NOTIFICADA: "Notificada",
  ANULADA: "Anulada",
};

export const ETIQUETA_MEDIO_INTENTO: Record<MedioIntento, string> = {
  PERSONAL: "Notificación personal",
  PRENSA: "Publicación en prensa",
};

export const ETIQUETA_RESULTADO_INTENTO: Record<ResultadoIntento, string> = {
  ENTREGADA: "Entregada",
  FALLIDA: "Intento fallido",
  PUBLICADA: "Publicada",
};

// LOPA art. 76: se entiende notificado 15 días después de la publicación.
export const DIAS_PRENSA = 15;

export const CONSULTA_NOTIFICACIONES = [...CONSULTA_GOBIERNO, "notificaciones"] as const;

// ORG-07: matriz auditable de autoridad (GOV-ORG-010), proyección de lectura de los cargos de ORG-03.
export interface MatrizEjercicio { ejercicio: number; estado: EstadoEstructura; }
export interface MatrizEjercicios { items: MatrizEjercicio[]; }
export interface MatrizUnidadFiltro { id: string; codigo: string; denominacion: string; ruta: string; }
export interface MatrizCargoFiltro { id: string; codigo: string; denominacion: string; }
export interface MatrizFiltros { unidades: MatrizUnidadFiltro[]; cargos: MatrizCargoFiltro[]; }
export interface MatrizVersionDeFila { version: number; registrada_en: string; motivo: string | null; }
export interface MatrizFila {
  id: string; cargo_id: string; cargo_codigo: string; cargo_denominacion: string; unidad_id: string;
  unidad_codigo: string | null; unidad_denominacion: string | null; ruta_unidad: string;
  accion: AccionCompetencia; materia: MateriaCompetencia; tipo_limite: TipoDeLimite; monto: string | null;
  moneda: MonedaDeLimite | null; fundamento: string | null; vigente_desde: string; vigente_hasta: string | null;
  estado_cargo: EstadoCargo; acto_soporte: string[]; version: MatrizVersionDeFila; origen: "CARGO";
}
export interface MatrizAutoridad {
  ejercicio: number; fecha: string; estructura: { estado: EstadoEstructura }; items: MatrizFila[];
  total: number; cargos: number; pagina: number; por_pagina: number;
}
export interface MatrizDocumento { documento_id: string; titulo: string; }
export interface MatrizCargo {
  id: string; codigo: string; denominacion: string; unidad_codigo: string | null; unidad_denominacion: string | null;
  ruta_unidad: string; estado: EstadoCargo; vigente_desde: string; vigente_hasta: string | null;
}
export interface MatrizCompetenciaDeVersion {
  accion: AccionCompetencia; materia: MateriaCompetencia; tipo_limite: TipoDeLimite; monto: string | null;
  moneda: MonedaDeLimite | null; fundamento: string | null;
}
export interface MatrizVersion {
  version: number; estado: EstadoCargo; motivo: string | null; creado_en: string; competencias: MatrizCompetenciaDeVersion[];
}
export interface MatrizDetalleCargo { cargo: MatrizCargo; acto_soporte: MatrizDocumento[]; versiones: MatrizVersion[]; }
/** Filtros de la matriz; los vacíos no viajan. */
export interface FiltrosMatriz {
  fecha?: string; unidad_id?: string; cargo_id?: string; accion?: AccionCompetencia | ""; materia?: MateriaCompetencia | ""; texto?: string;
}
/** Cadena de consulta («?a=1&b=2» o «») con los filtros no vacíos, en el orden fecha, unidad_id, cargo_id, accion, materia, texto, y
 *  después los extra (p. ej. pagina y por_pagina) en el orden recibido. `texto` viaja recortado. */
function valorDeConsulta(valor: string | number | undefined): string | undefined {
  if (valor === undefined) return undefined;
  const texto = typeof valor === "number" ? String(valor) : valor;
  if (texto.trim() === "") return undefined;
  return texto;
}

export function consultaDeMatriz(
  filtros: FiltrosMatriz,
  paginacion: { pagina?: number; por_pagina?: number } = {},
): string {
  const params = new URLSearchParams();
  const fecha = valorDeConsulta(filtros.fecha);
  if (fecha !== undefined) params.append("fecha", fecha);
  const unidadId = valorDeConsulta(filtros.unidad_id);
  if (unidadId !== undefined) params.append("unidad_id", unidadId);
  const cargoId = valorDeConsulta(filtros.cargo_id);
  if (cargoId !== undefined) params.append("cargo_id", cargoId);
  const accion = valorDeConsulta(filtros.accion);
  if (accion !== undefined) params.append("accion", accion);
  const materia = valorDeConsulta(filtros.materia);
  if (materia !== undefined) params.append("materia", materia);
  const texto = valorDeConsulta(filtros.texto?.trim());
  if (texto !== undefined) params.append("texto", texto);
  const pagina = valorDeConsulta(paginacion.pagina);
  if (pagina !== undefined) params.append("pagina", pagina);
  const porPagina = valorDeConsulta(paginacion.por_pagina);
  if (porPagina !== undefined) params.append("por_pagina", porPagina);
  const cadena = params.toString();
  return cadena === "" ? "" : `?${cadena}`;
}
export const POR_PAGINA_MATRIZ = 50;
export const CONSULTA_AUTORIDAD = [...CONSULTA_GOBIERNO, "autoridad"] as const;

// CTL-04: consulta y muestreo read-only del auditor (GOV-CTL-005), proyección de la bitácora de Gobierno.
export type MetodoMuestreo = "TODAS" | "ESPECIFICA" | "ALEATORIA";

export const ETIQUETA_METODO_MUESTREO: Record<MetodoMuestreo, string> = {
  TODAS: "Todas las partidas",
  ESPECIFICA: "Partidas específicas",
  ALEATORIA: "Selección aleatoria",
};

export interface FiltrosAuditoria {
  desde?: string;
  hasta?: string;
  proceso?: string;
  accion?: string;
  usuario?: string;
  texto?: string;
}

export interface AuditoriaProceso {
  codigo: string;
  nombre: string;
}

export interface AuditoriaAccion {
  codigo: string;
  entidad: string;
  etiqueta: string;
  proceso: string;
}

export interface AuditoriaFiltros {
  procesos: AuditoriaProceso[];
  acciones: AuditoriaAccion[];
}

export interface AuditoriaEvento {
  id: string;
  fecha: string;
  proceso: string;
  proceso_nombre: string;
  accion: string;
  accion_etiqueta: string;
  entidad: string;
  entidad_id: string | null;
  usuario: string | null;
  motivo: string | null;
  request_id: string | null;
}

export interface AuditoriaObjeto {
  tipo: string;
  id: string;
  ruta: string;
  capacidad: string;
}

export interface AuditoriaEventoDetalle extends AuditoriaEvento {
  detalle: Record<string, unknown>;
  documentos: string[];
  objeto: AuditoriaObjeto | null;
}

export interface AuditoriaEventos {
  items: AuditoriaEvento[];
  total: number;
  pagina: number;
  por_pagina: number;
}

export interface AuditoriaMuestra {
  id: string;
  codigo: string;
  titulo: string;
  criterio: string;
  justificacion: string;
  metodo: MetodoMuestreo;
  semilla: number | null;
  tamano: number;
  poblacion: number;
  filtros: FiltrosAuditoria;
  registrada_por: string | null;
  registrada_en: string;
}

export interface AuditoriaMuestraDetalle extends AuditoriaMuestra {
  eventos: AuditoriaEvento[];
}

export interface AuditoriaMuestras {
  items: AuditoriaMuestra[];
}

export interface AuditoriaMuestraNueva {
  titulo: string;
  criterio: string;
  justificacion: string;
  metodo: MetodoMuestreo;
  filtros: FiltrosAuditoria;
  semilla?: number;
  tamano?: number;
  eventos?: string[];
}

export function consultaDeAuditoria(
  filtros: FiltrosAuditoria,
  paginacion: { pagina?: number; por_pagina?: number } = {},
): string {
  const params = new URLSearchParams();
  const desde = valorDeConsulta(filtros.desde);
  if (desde !== undefined) params.append("desde", desde);
  const hasta = valorDeConsulta(filtros.hasta);
  if (hasta !== undefined) params.append("hasta", hasta);
  const proceso = valorDeConsulta(filtros.proceso);
  if (proceso !== undefined) params.append("proceso", proceso);
  const accion = valorDeConsulta(filtros.accion);
  if (accion !== undefined) params.append("accion", accion);
  const usuario = valorDeConsulta(filtros.usuario?.trim());
  if (usuario !== undefined) params.append("usuario", usuario);
  const texto = valorDeConsulta(filtros.texto?.trim());
  if (texto !== undefined) params.append("texto", texto);
  const pagina = valorDeConsulta(paginacion.pagina);
  if (pagina !== undefined) params.append("pagina", pagina);
  const porPagina = valorDeConsulta(paginacion.por_pagina);
  if (porPagina !== undefined) params.append("por_pagina", porPagina);
  const cadena = params.toString();
  return cadena === "" ? "" : `?${cadena}`;
}

export function filtrosLimpios(filtros: FiltrosAuditoria): FiltrosAuditoria {
  const limpios: FiltrosAuditoria = {};
  const desde = valorDeConsulta(filtros.desde);
  if (desde !== undefined) limpios.desde = desde;
  const hasta = valorDeConsulta(filtros.hasta);
  if (hasta !== undefined) limpios.hasta = hasta;
  const proceso = valorDeConsulta(filtros.proceso);
  if (proceso !== undefined) limpios.proceso = proceso;
  const accion = valorDeConsulta(filtros.accion);
  if (accion !== undefined) limpios.accion = accion;
  const usuario = valorDeConsulta(filtros.usuario?.trim());
  if (usuario !== undefined) limpios.usuario = usuario;
  const texto = valorDeConsulta(filtros.texto?.trim());
  if (texto !== undefined) limpios.texto = texto;
  return limpios;
}

export const POR_PAGINA_AUDITORIA = 50;
export const CONSULTA_AUDITORIA = [...CONSULTA_GOBIERNO, "auditoria"] as const;

// CTL-06: hallazgos, recomendaciones y planes de acción correctiva (GOV-CTL-008).
export type EstadoHallazgo = "ABIERTO" | "PLAN_DE_ACCION" | "EN_REMEDIACION" | "EVIDENCIA_PRESENTADA" | "CERRADO";
export type RiesgoHallazgo = "ALTO" | "MEDIO" | "BAJO";
export type OrigenHallazgo = "MUESTRA" | "INDEPENDIENTE";
export type EstadoAccionCorrectiva = "PENDIENTE" | "EN_CURSO" | "COMPLETADA";
export type TipoHistoriaHallazgo =
  | "CREADO"
  | "RECOMENDACION"
  | "ACCION"
  | "PLAN"
  | "EJECUCION"
  | "AVANCE"
  | "PRESENTADO"
  | "VERIFICADO"
  | "DEVUELTO";

export const ETIQUETA_ESTADO_HALLAZGO: Record<EstadoHallazgo, string> = {
  ABIERTO: "Abierto",
  PLAN_DE_ACCION: "Plan de acción",
  EN_REMEDIACION: "En remediación",
  EVIDENCIA_PRESENTADA: "Pendiente de verificación",
  CERRADO: "Cerrado",
};

export const ETIQUETA_RIESGO_HALLAZGO: Record<RiesgoHallazgo, string> = {
  ALTO: "Alto",
  MEDIO: "Medio",
  BAJO: "Bajo",
};

export const ETIQUETA_ORIGEN_HALLAZGO: Record<OrigenHallazgo, string> = {
  MUESTRA: "Muestra de auditoría",
  INDEPENDIENTE: "Independiente",
};

export const ETIQUETA_ESTADO_ACCION: Record<EstadoAccionCorrectiva, string> = {
  PENDIENTE: "Pendiente",
  EN_CURSO: "En curso",
  COMPLETADA: "Completada",
};

export const ETIQUETA_HISTORIA_HALLAZGO: Record<TipoHistoriaHallazgo, string> = {
  CREADO: "Hallazgo registrado",
  RECOMENDACION: "Recomendación añadida",
  ACCION: "Acción correctiva añadida",
  PLAN: "Plan de acción registrado",
  EJECUCION: "Ejecución iniciada",
  AVANCE: "Avance registrado",
  PRESENTADO: "Presentado a verificación",
  VERIFICADO: "Verificado y cerrado",
  DEVUELTO: "Devuelto a remediación",
};

export interface RecomendacionHallazgo {
  id: string;
  orden: number;
  texto: string;
  created_by: string | null;
  created_at: string;
}

export interface AvanceAccion {
  id: string;
  nota: string;
  porcentaje: number;
  documento_id: string | null;
  created_by: string | null;
  created_at: string;
}

export interface AccionCorrectiva {
  id: string;
  recomendacion_id: string;
  orden: number;
  descripcion: string;
  cargo_id: string;
  cargo_codigo: string;
  cargo_denominacion: string;
  unidad_id: string;
  unidad_nombre: string;
  ejercicio: number;
  fecha_objetivo: string;
  porcentaje: number;
  estado: EstadoAccionCorrectiva;
  vencida: boolean;
  documentos: string[];
  avances: AvanceAccion[];
}

export interface HistoriaHallazgo {
  id: string;
  tipo: TipoHistoriaHallazgo;
  estado_desde: EstadoHallazgo | null;
  estado_hasta: EstadoHallazgo | null;
  detalle: Record<string, unknown> | null;
  created_by: string | null;
  created_at: string;
}

export interface MuestraDeHallazgo {
  id: string;
  codigo: string;
  titulo: string;
}

export interface HallazgoDetalle {
  id: string;
  codigo: string;
  titulo: string;
  condicion: string;
  criterio: string;
  causa: string;
  efecto: string;
  riesgo: RiesgoHallazgo;
  origen: OrigenHallazgo;
  origen_descripcion: string | null;
  muestra: MuestraDeHallazgo | null;
  partidas: string[];
  estado: EstadoHallazgo;
  version: number;
  presentado_por: string | null;
  presentado_en: string | null;
  verificado_por: string | null;
  verificado_en: string | null;
  nota_verificacion: string | null;
  created_by: string | null;
  created_at: string;
  recomendaciones: RecomendacionHallazgo[];
  acciones: AccionCorrectiva[];
  historia: HistoriaHallazgo[];
}

export interface HallazgoResumen {
  id: string;
  codigo: string;
  titulo: string;
  riesgo: RiesgoHallazgo;
  estado: EstadoHallazgo;
  origen: OrigenHallazgo;
  acciones_total: number;
  acciones_vencidas: number;
  created_at: string;
}

export interface ResumenHallazgos {
  abiertos: number;
  pendientes_verificacion: number;
  acciones_vencidas: number;
  cerrados: number;
}

export interface HallazgosListado {
  items: HallazgoResumen[];
  total: number;
  pagina: number;
  por_pagina: number;
  resumen: ResumenHallazgos;
}

export interface CargoResponsable {
  id: string;
  codigo: string;
  denominacion: string;
  unidad_nombre: string;
  ejercicio: number;
}

export interface CargosResponsables {
  items: CargoResponsable[];
}

export interface FiltrosHallazgos {
  estado?: EstadoHallazgo | "";
  riesgo?: RiesgoHallazgo | "";
  origen?: OrigenHallazgo | "";
  vencidas?: boolean;
  texto?: string;
  abiertos?: boolean;
  riesgo_minimo?: RiesgoHallazgo;
}

export interface HallazgoNuevo {
  titulo: string;
  condicion: string;
  criterio: string;
  causa: string;
  efecto: string;
  riesgo: RiesgoHallazgo;
  origen: OrigenHallazgo;
  muestra_id?: string;
  partidas?: string[];
  origen_descripcion?: string;
}

export interface AccionNueva {
  recomendacion_id: string;
  descripcion: string;
  cargo_id: string;
  fecha_objetivo: string;
}

export interface AvanceNuevo {
  nota: string;
  porcentaje: number;
  documento_id?: string;
}

export function contextoDeHallazgos(params: URLSearchParams): Pick<FiltrosHallazgos, "abiertos" | "riesgo_minimo"> {
  const contexto: Pick<FiltrosHallazgos, "abiertos" | "riesgo_minimo"> = {};
  if (params.get("abiertos") === "true") contexto.abiertos = true;
  const riesgo = params.get("riesgo_minimo");
  if (riesgo !== null && Object.hasOwn(ETIQUETA_RIESGO_HALLAZGO, riesgo)) {
    contexto.riesgo_minimo = riesgo as RiesgoHallazgo;
  }
  return contexto;
}

export function consultaDeHallazgos(
  filtros: FiltrosHallazgos,
  paginacion: { pagina?: number; por_pagina?: number } = {},
): string {
  const params = new URLSearchParams();
  const estado = valorDeConsulta(filtros.estado);
  if (estado !== undefined) params.append("estado", estado);
  const riesgo = valorDeConsulta(filtros.riesgo);
  if (riesgo !== undefined) params.append("riesgo", riesgo);
  const origen = valorDeConsulta(filtros.origen);
  if (origen !== undefined) params.append("origen", origen);
  const texto = valorDeConsulta(filtros.texto?.trim());
  if (texto !== undefined) params.append("texto", texto);
  if (filtros.vencidas === true) params.append("vencidas", "true");
  if (filtros.abiertos === true) params.append("abiertos", "true");
  if (filtros.riesgo_minimo !== undefined) params.append("riesgo_minimo", filtros.riesgo_minimo);
  const pagina = valorDeConsulta(paginacion.pagina);
  if (pagina !== undefined) params.append("pagina", pagina);
  const porPagina = valorDeConsulta(paginacion.por_pagina);
  if (porPagina !== undefined) params.append("por_pagina", porPagina);
  const cadena = params.toString();
  return cadena === "" ? "" : `?${cadena}`;
}

export const POR_PAGINA_HALLAZGOS = 50;
export const CONSULTA_HALLAZGOS = [...CONSULTA_GOBIERNO, "hallazgos"] as const;
export const RESOURCE_TYPE_ACCION_CORRECTIVA = "GovernmentCorrectiveAction";

// ---------------------------------------------------------------------------
// DOC-08 · paquete de auditoría exportable (GOV-DOC-010)
// ---------------------------------------------------------------------------

export type EstadoDocumentoPaquete = "INCLUIDO" | "EXCLUIDO";
export type MotivoExclusionPaquete = "SIN_PERMISO" | "NO_DISPONIBLE";
export type ResultadoVerificacionPaquete = "VALIDO" | "INVALIDO" | "INCOMPLETO" | "VERSION_NO_SOPORTADA";
export type TipoReferenciaPaquete = "evento" | "objeto" | "accion_correctiva" | "avance";

export interface ReferenciaPaquete { tipo: TipoReferenciaPaquete; id: string; }
export interface DocumentoDelPaquete {
  id: string; estado: EstadoDocumentoPaquete; motivo: MotivoExclusionPaquete | null; version: number | null;
  bytes: number | null; sha256: string | null; referencias: ReferenciaPaquete[];
}
export interface MuestraDelPaquete {
  id: string; codigo: string; titulo: string; metodo: string; semilla: number | null; poblacion: number; tamano: number;
  creada_en: string; creada_por: string | null;
}
export interface LimitesPaquete { eventos: number; documentos: number; bytes: number; }
export interface VistaPreviaPaquete {
  muestra: MuestraDelPaquete; eventos: number; documentos_incluidos: number; documentos_excluidos: number; hallazgos: number;
  bytes_estimados: number; documentos: DocumentoDelPaquete[]; limites: LimitesPaquete; excede_limite: boolean;
  motivo_limite: string | null; paquetes_previos: number;
}
export interface EventoDelPaquete {
  orden: number; id: string; fecha: string; proceso: string; accion: string; entidad: string; entidad_id: string | null;
  usuario: string | null; objeto: { tipo: string; id: string } | null; documentos: string[];
}
export interface HallazgoDelPaquete {
  id: string; codigo: string; titulo: string; riesgo: string; estado: string; partidas: string[]; acciones: string[]; documentos: string[];
}
export interface MotivoVerificacionPaquete { codigo: string; ruta: string | null; }
export interface VerificacionPaquete {
  id: string; resultado: ResultadoVerificacionPaquete; motivos: MotivoVerificacionPaquete[]; huella_archivo: string;
  bytes_archivo: number; identico: boolean; verificado_por: string | null; verificado_en: string;
}
export interface PaqueteResumen {
  id: string; codigo: string; muestra_id: string; muestra_codigo: string; numero_generacion: number; titulo: string;
  generado_por: string | null; generado_en: string; bytes: number; huella_paquete: string; eventos: number;
  documentos_incluidos: number; documentos_excluidos: number; hallazgos: number;
}
export interface PaqueteDetalle extends PaqueteResumen {
  muestra_titulo: string; proposito: string; version_manifiesto: number; huella_manifiesto: string; archivos: number;
  nombre_archivo: string;
  contenido: { eventos: EventoDelPaquete[]; documentos: DocumentoDelPaquete[]; hallazgos: HallazgoDelPaquete[] };
  verificaciones: VerificacionPaquete[];
}
export interface PaquetesListado { items: PaqueteResumen[]; total: number; pagina: number; por_pagina: number; }
export interface ResultadoDeVerificacionPaquete {
  resultado: ResultadoVerificacionPaquete; motivos: MotivoVerificacionPaquete[]; paquete: { id: string; codigo: string } | null;
  huella_archivo: string; bytes_archivo: number; identico: boolean; verificacion_id: string | null;
}

export const ETIQUETAS_MOTIVO_EXCLUSION: Record<MotivoExclusionPaquete, string> = {
  SIN_PERMISO: "Sin permiso para el documento",
  NO_DISPONIBLE: "No disponible (sin analizar, alterado o ausente)",
};
export const ETIQUETAS_RESULTADO_VERIFICACION: Record<ResultadoVerificacionPaquete, string> = {
  VALIDO: "Válido", INVALIDO: "Inválido", INCOMPLETO: "Incompleto", VERSION_NO_SOPORTADA: "Versión no soportada",
};
export const ETIQUETAS_MOTIVO_VERIFICACION: Record<string, string> = {
  MANIFIESTO_AUSENTE: "Falta el manifiesto", MANIFIESTO_ILEGIBLE: "El manifiesto no se puede leer",
  PAQUETE_NO_REGISTRADO: "El paquete no está registrado en este ente", MANIFIESTO_ALTERADO: "El manifiesto fue alterado",
  ARCHIVO_ALTERADO: "Archivo alterado", ARCHIVO_INESPERADO: "Archivo no declarado en el manifiesto", ARCHIVO_AUSENTE: "Falta un archivo",
};
export const ETIQUETAS_REFERENCIA_PAQUETE: Record<TipoReferenciaPaquete, string> = {
  evento: "Evento", objeto: "Objeto de negocio", accion_correctiva: "Acción correctiva", avance: "Avance",
};
export const AVISO_HUELLA_PAQUETE = "La huella SHA-256 prueba la integridad del paquete; no es una firma electrónica.";
export const POR_PAGINA_PAQUETES = 20;
export const CONSULTA_PAQUETES = [...CONSULTA_GOBIERNO, "paquetes"] as const;

export function consultaDePaquetes(
  filtros: { muestra_id?: string },
  paginacion: { pagina?: number; por_pagina?: number } = {},
): string {
  const params = new URLSearchParams();
  const muestraId = valorDeConsulta(filtros.muestra_id);
  if (muestraId !== undefined) params.append("muestra_id", muestraId);
  const pagina = valorDeConsulta(paginacion.pagina);
  if (pagina !== undefined) params.append("pagina", pagina);
  const porPagina = valorDeConsulta(paginacion.por_pagina);
  if (porPagina !== undefined) params.append("por_pagina", porPagina);
  const cadena = params.toString();
  return cadena === "" ? "" : `?${cadena}`;
}

export function formatearBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  const valor = bytes < 1024 * 1024 ? bytes / 1024 : bytes / (1024 * 1024);
  const sufijo = bytes < 1024 * 1024 ? " KB" : " MB";
  return `${valor.toLocaleString("es-VE", { maximumFractionDigits: 1 })}${sufijo}`;
}

export function abreviarHuella(huella: string): string { return huella.length > 16 ? `${huella.slice(0, 12)}…` : huella; }

// ---------------------------------------------------------------------------
// CTL-01 · matriz de segregación de funciones (GOV-CTL-001)
// ---------------------------------------------------------------------------

export type ProcesoSod = "DOC-02" | "CTL-06" | "TRE-01" | "TRE-02" | "CTL-10" | "ORG-04";
export type EstadoReglaSod = "BORRADOR" | "VIGENTE" | "CERRADA";

export interface AccionSod { codigo: string; etiqueta: string; crea_objeto: boolean; }
export interface ProcesoAccionesSod { proceso: ProcesoSod; nombre: string; objeto: string; acciones: AccionSod[]; }
export interface CatalogoSod { procesos: ProcesoAccionesSod[]; }
export interface HistoriaSod { tipo: string; detalle: Record<string, unknown> | null; registrado_por: string | null; registrado_en: string; }

export interface ReglaSodResumen {
  id: string; codigo: string; nombre: string; proceso: ProcesoSod; accion_a: string; accion_a_etiqueta: string; accion_b: string; accion_b_etiqueta: string;
  bidireccional: boolean; alcance: string; modo: string; vigente_desde: string; vigente_hasta: string | null; estado: EstadoReglaSod; en_vigor: boolean; version: number;
}

export interface ReglaSodDetalle extends ReglaSodResumen {
  descripcion: string; creada_por: string | null; creada_en: string; activada_por: string | null; activada_en: string | null;
  cerrada_por: string | null; cerrada_en: string | null; motivo_cierre: string | null; conflictos: number; historia: HistoriaSod[];
}

export interface ResumenSod { borradores: number; vigentes: number; cerradas: number; conflictos_30_dias: number; }
export interface ReglasSodListado { items: ReglaSodResumen[]; resumen: ResumenSod; }

export interface ReglaSodEntrada {
  nombre: string; descripcion: string; proceso: ProcesoSod; accion_a: string; accion_b: string; bidireccional: boolean; vigente_desde: string; vigente_hasta: string | null;
}

export type ReglaSodCambios = Partial<Omit<ReglaSodEntrada, "proceso">>;

export interface ConflictoSod {
  id: string; fecha: string; usuario: string | null; regla_id: string | null; regla_codigo: string | null; regla_nombre: string | null; proceso: string | null;
  accion: string | null; accion_etiqueta: string | null; accion_previa: string | null; accion_previa_etiqueta: string | null; objeto_tipo: string | null; objeto_id: string | null;
}

export interface ConflictosSodListado { items: ConflictoSod[]; total: number; pagina: number; por_pagina: number; }

/** `details` del 409 GOV_SOD_CONFLICT que devuelven DOC-02 y CTL-06. */
export interface DetalleConflictoSod {
  regla_codigo: string; regla_nombre: string; accion: string; accion_etiqueta: string; accion_previa: string; accion_previa_etiqueta: string;
  objeto_tipo: string; objeto_id: string; previa_en: string;
}

export const ETIQUETAS_ESTADO_REGLA_SOD: Record<EstadoReglaSod, string> = { BORRADOR: "Borrador", VIGENTE: "Vigente", CERRADA: "Cerrada" };
export const ETIQUETAS_PROCESO_SOD: Record<ProcesoSod, string> = { "DOC-02": "Actos administrativos", "CTL-06": "Hallazgos y acciones correctivas", "TRE-01": "Cuentas bancarias públicas", "TRE-02": "Programación financiera", "CTL-10": "Controles de cierre", "ORG-04": "Ocupación de cargos" };
export const ETIQUETAS_HISTORIA_SOD: Record<string, string> = { CREADA: "Registrada", EDITADA: "Modificada", ACTIVADA: "Activada", CERRADA: "Cerrada" };

export const POR_PAGINA_CONFLICTOS_SOD = 20;
export const CONSULTA_SOD = [...CONSULTA_GOBIERNO, "sod"] as const;

/** Ruta de la ficha del objeto bloqueado: acto → /gobierno/actos/{id}; hallazgo → /gobierno/hallazgos/{id}; otro → null. */
export function rutaDeObjetoSod(tipo: string | null, id: string | null): string | null {
  if (!tipo || !id) return null;
  if (tipo === "GovernmentAct") return `/gobierno/actos/${id}`;
  if (tipo === "GovernmentFinding") return `/gobierno/hallazgos/${id}`;
  if (tipo === "GovernmentBankAccount") return `/gobierno/tesoreria/cuentas/${id}`;
  if (tipo === "GovernmentCashProgram") return `/gobierno/tesoreria/programacion/${id}`;
  if (tipo === "GovernmentClosurePolicy") return `/gobierno/cierres/${id}`;
  if (tipo === "GovernmentAssignment") return `/gobierno/ocupacion/asignaciones/${id}`;
  return null;
}

/** Flecha de la regla: "⇄" si es bidireccional, "→" si no. */
export function flechaSod(bidireccional: boolean): string {
  return bidireccional ? "⇄" : "→";
}

/** Cadena de consulta de /gobierno/sod/reglas (estado, proceso; omite vacíos). */
export function consultaDeReglasSod(filtros: { estado?: string; proceso?: string }): string {
  const qs = new URLSearchParams();
  const estado = valorDeConsulta(filtros.estado);
  const proceso = valorDeConsulta(filtros.proceso);
  if (estado) qs.set("estado", estado);
  if (proceso) qs.set("proceso", proceso);
  const s = qs.toString();
  return s ? `?${s}` : "";
}

// CTL-10 · Controles materiales de cierre (GOV-CTL-012)
export type AccionCierre = "ORG02_CERRAR_ESTRUCTURA" | "TRE02_CERRAR_PROGRAMA";
export type EstadoPoliticaCierre = "BORRADOR" | "VIGENTE" | "RETIRADA";
export type TipoControlCierre = "HALLAZGOS_ABIERTOS" | "ACTOS_SIN_EFICACIA";
export type RiesgoMinimoCierre = "ALTO" | "MEDIO" | "BAJO";

export interface ControlCierre {
  id: string;
  tipo: TipoControlCierre;
  riesgo_minimo: RiesgoMinimoCierre | null;
  materialidad: string;
}

export interface HistoriaCierre {
  evento: string;
  detalle: Record<string, unknown> | null;
  usuario: string | null;
  instante: string;
}

export interface PoliticaCierreResumen {
  id: string;
  codigo: string;
  nombre: string;
  accion_cierre: AccionCierre;
  fundamento: string;
  estado: EstadoPoliticaCierre;
  vigente_desde: string;
  vigente_hasta: string | null;
  efectiva_hoy: boolean;
  version: number;
}

export interface PoliticaCierreDetalle extends PoliticaCierreResumen {
  activada_por: string | null;
  activada_en: string | null;
  retirada_por: string | null;
  retirada_en: string | null;
  motivo_retiro: string | null;
  controles: ControlCierre[];
  historia: HistoriaCierre[];
}

export interface ResumenCierres {
  borradores: number;
  vigentes: number;
  retiradas: number;
}

export interface PoliticasCierreListado {
  items: PoliticaCierreResumen[];
  total: number;
  resumen: ResumenCierres;
}

export interface ItemCatalogoCierre {
  codigo: string;
  etiqueta: string;
}

export interface TipoCatalogoCierre extends ItemCatalogoCierre {
  requiere_riesgo: boolean;
}

export interface CatalogoCierres {
  acciones: ItemCatalogoCierre[];
  tipos: TipoCatalogoCierre[];
}

export interface PoliticaCierreEntrada {
  nombre: string;
  accion_cierre: AccionCierre;
  fundamento: string;
  vigente_desde: string;
  vigente_hasta: string | null;
}

export type PoliticaCierreCambios = Partial<Omit<PoliticaCierreEntrada, "accion_cierre">>;

export interface ControlCierreEntrada {
  tipo: TipoControlCierre;
  riesgo_minimo: RiesgoMinimoCierre | null;
  materialidad: string;
}

export interface PendienteDeCierre {
  codigo: string | null;
  numero: string | null;
  titulo: string | null;
  asunto: string | null;
  ruta: string;
}

export interface ControlBloqueante {
  tipo: TipoControlCierre;
  etiqueta: string;
  materialidad: string;
  pendientes: number;
  muestra: PendienteDeCierre[];
  ruta_lista: string;
}

export interface DetalleBloqueoCierre {
  politica_codigo: string;
  politica_nombre: string;
  proceso: string;
  objeto_codigo: string;
  total: number;
  dueno: string;
  controles: ControlBloqueante[];
}

export interface BloqueoCierre {
  id: string;
  instante: string;
  politica_id: string | null;
  politica_codigo: string | null;
  accion_cierre: string | null;
  objeto_tipo: string | null;
  objeto_id: string | null;
  objeto_codigo: string | null;
  total: number | null;
  usuario: string | null;
}

export interface BloqueosCierreListado {
  items: BloqueoCierre[];
  total: number;
  pagina: number;
  tamano: number;
}

export const CONSULTA_CIERRES = [...CONSULTA_GOBIERNO, "cierres"] as const;
export const POR_PAGINA_BLOQUEOS = 20;

export const ETIQUETAS_ESTADO_POLITICA_CIERRE: Record<EstadoPoliticaCierre, string> = {
  BORRADOR: "Borrador",
  VIGENTE: "Vigente",
  RETIRADA: "Retirada",
};

export const ETIQUETAS_ACCION_CIERRE: Record<AccionCierre, string> = {
  ORG02_CERRAR_ESTRUCTURA: "Cerrar estructura del ejercicio",
  TRE02_CERRAR_PROGRAMA: "Cerrar programa financiero",
};

export const ETIQUETAS_TIPO_CONTROL_CIERRE: Record<TipoControlCierre, string> = {
  HALLAZGOS_ABIERTOS: "Hallazgos abiertos",
  ACTOS_SIN_EFICACIA: "Actos sin eficacia",
};

export const ETIQUETAS_RIESGO_CIERRE: Record<RiesgoMinimoCierre, string> = {
  ALTO: "Alto",
  MEDIO: "Medio o superior",
  BAJO: "Cualquier riesgo",
};

export const ETIQUETAS_HISTORIA_CIERRE: Record<string, string> = {
  CREADA: "Registrada",
  ACTUALIZADA: "Modificada",
  CONTROL_ANADIDO: "Control añadido",
  CONTROL_RETIRADO: "Control quitado",
  ACTIVADA: "Activada",
  RETIRADA: "Retirada",
};

export function consultaDePoliticasCierre(filtros: { estado?: string; accion_cierre?: string }): string {
  const busqueda = new URLSearchParams();
  const estado = valorDeConsulta(filtros.estado);
  if (estado) busqueda.set("estado", estado);
  const accion = valorDeConsulta(filtros.accion_cierre);
  if (accion) busqueda.set("accion_cierre", accion);
  const cadena = busqueda.toString();
  return cadena ? `?${cadena}` : "";
}

export function consultaDeBloqueosCierre(
  filtros: { accion_cierre?: string; desde?: string; hasta?: string },
  paginacion: { pagina?: number; tamano?: number } = {},
): string {
  const busqueda = new URLSearchParams();
  const accion = valorDeConsulta(filtros.accion_cierre);
  if (accion) busqueda.set("accion_cierre", accion);
  const desde = valorDeConsulta(filtros.desde);
  if (desde) busqueda.set("desde", desde);
  const hasta = valorDeConsulta(filtros.hasta);
  if (hasta) busqueda.set("hasta", hasta);
  if (paginacion.pagina !== undefined) busqueda.set("pagina", String(paginacion.pagina));
  if (paginacion.tamano !== undefined) busqueda.set("tamano", String(paginacion.tamano));
  const cadena = busqueda.toString();
  return cadena ? `?${cadena}` : "";
}

export function rutaDeObjetoCierre(tipo: string | null, id: string | null, codigo: string | null): string | null {
  if (tipo === "GovernmentCashProgram" && id) return `/gobierno/tesoreria/programacion/${id}`;
  if (tipo === "GovernmentStructure" && codigo) {
    const coincidencia = /^EST-(\d{4})$/.exec(codigo);
    if (coincidencia) return `/gobierno/estructura/${coincidencia[1]}`;
  }
  return null;
}

// TRE-01 · Cuentas bancarias públicas (GOV-TRE-001)
export type EstadoBanco = "ACTIVO" | "INACTIVO";
export type EstadoCuenta = "BORRADOR" | "VIGENTE" | "INACTIVA" | "CERRADA";
export type TipoCuenta = "CORRIENTE" | "AHORRO";
export type MonedaCuenta = "VES" | "USD" | "EUR";

export interface Banco { id: string; codigo: string; nombre: string; estado: EstadoBanco; version: number; }
export interface BancosListado { items: Banco[]; }
export interface BancoEntrada { codigo: string; nombre: string; }
export interface BancoCambios { nombre?: string; estado?: EstadoBanco; }

export interface ActoReferencia { id: string; tipo: string; numero: string; fecha: string; estado: string; asunto: string; }

export interface CuentaResumen {
  id: string; codigo: string; denominacion: string; banco_id: string; banco_codigo: string; banco_nombre: string; tipo: TipoCuenta; moneda: MonedaCuenta;
  numero_enmascarado: string; vigente_desde: string; vigente_hasta: string | null; estado: EstadoCuenta; en_vigor: boolean; acto_sin_efecto: boolean;
  autorizados_en_vigor: number; version: number;
}
export interface AutorizadoCuenta {
  id: string; cargo_id: string; cargo_codigo: string; cargo_denominacion: string; cargo_unidad: string; cargo_vigente: boolean; acto_alta: ActoReferencia;
  vigente_desde: string; vigente_hasta: string | null; acto_fin: ActoReferencia | null; motivo_fin: string | null; en_vigor: boolean;
  registrada_por: string | null; registrada_en: string; terminada_por: string | null; terminada_en: string | null;
}
export interface HistoriaCuenta { tipo: string; detalle: Record<string, unknown> | null; registrado_por: string | null; registrado_en: string; }
export interface CuentaDetalle extends CuentaResumen {
  acto: ActoReferencia | null; registrada_por: string | null; registrada_en: string; activada_por: string | null; activada_en: string | null;
  cerrada_por: string | null; cerrada_en: string | null; fecha_cierre: string | null; motivo_cierre: string | null;
  autorizados: AutorizadoCuenta[]; historia: HistoriaCuenta[];
}
export interface ResumenCuentas { borradores: number; vigentes: number; inactivas: number; cerradas: number; }
export interface CuentasListado { items: CuentaResumen[]; resumen: ResumenCuentas; }
export interface CuentaEntrada {
  denominacion: string; banco_id: string; tipo: TipoCuenta; numero: string; moneda: MonedaCuenta; vigente_desde: string; vigente_hasta: string | null;
}
export type CuentaCambios = Partial<CuentaEntrada>;
export interface NumeroCuenta { numero: string; }
export interface CuentasOpciones {
  bancos: { id: string; codigo: string; nombre: string }[];
  cargos: { id: string; codigo: string; denominacion: string; unidad: string }[];
  actos: ActoReferencia[];
}

export const ETIQUETAS_ESTADO_CUENTA: Record<EstadoCuenta, string> = { BORRADOR: "Borrador", VIGENTE: "Vigente", INACTIVA: "Inactiva", CERRADA: "Cerrada" };
export const ETIQUETAS_TIPO_CUENTA: Record<TipoCuenta, string> = { CORRIENTE: "Corriente", AHORRO: "Ahorro" };
export const ETIQUETAS_ESTADO_BANCO: Record<EstadoBanco, string> = { ACTIVO: "Activo", INACTIVO: "Inactivo" };
export const ETIQUETAS_HISTORIA_CUENTA: Record<string, string> = {
  CREADA: "Registrada", EDITADA: "Modificada", ACTO_VINCULADO: "Acto vinculado", ACTIVADA: "Activada", INACTIVADA: "Inactivada", REACTIVADA: "Reactivada",
  CERRADA: "Cerrada", AUTORIZADO_ALTA: "Cargo autorizado", AUTORIZADO_FIN: "Autorización terminada",
};
export const MONEDAS_CUENTA: MonedaCuenta[] = ["VES", "USD", "EUR"];
export const CONSULTA_CUENTAS = [...CONSULTA_GOBIERNO, "tesoreria"] as const;

// TRE-02 · Programación financiera y disponibilidad de caja (GOV-TRE-002)
export type TipoRubro = "INGRESO" | "DESEMBOLSO";
export type EstadoRubro = "ACTIVO" | "INACTIVO";
export type MonedaPrograma = MonedaCuenta;
export type EstadoPrograma = "BORRADOR" | "VIGENTE" | "CERRADO" | "DESCARTADO";
export type EstadoVersion = "BORRADOR" | "VIGENTE" | "SUPERADA" | "DESCARTADA" | "CERRADA";

export interface Rubro {
  id: string;
  codigo: string;
  nombre: string;
  tipo: TipoRubro;
  estado: EstadoRubro;
  version: number;
}

export interface RubrosListado {
  items: Rubro[];
}

export interface RubroEntrada {
  codigo: string;
  nombre: string;
  tipo: TipoRubro;
}

export interface RubroCambios {
  nombre?: string;
  estado?: EstadoRubro;
}

export interface ProgramaEntrada {
  ejercicio: number;
  moneda: MonedaPrograma;
  mes_inicial: number;
}

export interface DeclaracionPrograma {
  id: string;
  cuenta_id: string;
  cuenta_codigo: string;
  cuenta_denominacion: string;
  banco_nombre: string;
  monto: string;
  fecha_corte: string;
  fundamento: string;
  declarado_por: string | null;
  declarado_en: string;
}

export interface DeclaracionEntrada {
  cuenta_id: string;
  monto: string;
  fecha_corte: string;
  fundamento: string;
}

export interface LineaPrograma {
  id: string;
  rubro_id: string;
  rubro_codigo: string;
  rubro_nombre: string;
  tipo: TipoRubro;
  mes: number;
  monto: string;
}

export interface LineaEntrada {
  rubro_id: string;
  mes: number;
  monto: string;
}

export interface MesDisponibilidad {
  mes: number;
  inicial: string;
  ingresos: string;
  desembolsos: string;
  final: string;
  deficit: boolean;
}

export interface VersionPrograma {
  numero: number;
  estado: EstadoVersion;
  motivo: string | null;
  activada_por: string | null;
  activada_en: string | null;
  registrado_por: string | null;
  registrado_en: string;
}

export interface HistoriaPrograma {
  version_numero: number;
  tipo: string;
  detalle: Record<string, unknown> | null;
  registrado_por: string | null;
  registrado_en: string;
}

export interface ProgramaResumen {
  id: string;
  codigo: string;
  ejercicio: number;
  moneda: MonedaPrograma;
  mes_inicial: number;
  estado: EstadoPrograma;
  version: number;
  version_vigente: number | null;
  disponibilidad_inicial: string;
}

export interface ResumenProgramas {
  borradores: number;
  vigentes: number;
  cerrados: number;
}

export interface ProgramasListado {
  items: ProgramaResumen[];
  resumen: ResumenProgramas;
}

export interface ProgramaDetalle extends ProgramaResumen {
  version_vista: number;
  borrador_numero: number | null;
  cerrado_por: string | null;
  cerrado_en: string | null;
  motivo_cierre: string | null;
  registrado_por: string | null;
  registrado_en: string;
  declaraciones: DeclaracionPrograma[];
  lineas: LineaPrograma[];
  meses: MesDisponibilidad[];
  hay_deficit: boolean;
  versiones: VersionPrograma[];
  historia: HistoriaPrograma[];
}

export interface OpcionesPrograma {
  cuentas: { id: string; codigo: string; denominacion: string; banco_nombre: string }[];
  rubros: { id: string; codigo: string; nombre: string; tipo: TipoRubro }[];
}

export const ETIQUETAS_TIPO_RUBRO: Record<TipoRubro, string> = { INGRESO: "Ingreso", DESEMBOLSO: "Desembolso" };
export const ETIQUETAS_ESTADO_RUBRO: Record<EstadoRubro, string> = { ACTIVO: "Activo", INACTIVO: "Inactivo" };
export const ETIQUETAS_ESTADO_PROGRAMA: Record<EstadoPrograma, string> = { BORRADOR: "Borrador", VIGENTE: "Vigente", CERRADO: "Cerrado", DESCARTADO: "Descartado" };
export const ETIQUETAS_ESTADO_VERSION: Record<EstadoVersion, string> = { BORRADOR: "Borrador", VIGENTE: "Vigente", SUPERADA: "Superada", DESCARTADA: "Descartada", CERRADA: "Cerrada" };
export const ETIQUETAS_HISTORIA_PROGRAMA: Record<string, string> = { CREADO: "Programa registrado", DECLARACION: "Disponibilidad declarada", LINEA: "Línea programada", ACTIVADO: "Versión activada", REPROGRAMADO: "Reprogramación abierta", DESCARTADO: "Borrador descartado", CERRADO: "Programa cerrado" };
export const NOMBRES_DE_MES: string[] = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"];
export const CONSULTA_CAJA = [...CONSULTA_GOBIERNO, "caja"] as const;

export function consultaDeProgramas(filtros: { ejercicio?: string; moneda?: string; estado?: string }): string {
  const qs = new URLSearchParams();
  const ejercicio = valorDeConsulta(filtros.ejercicio);
  const moneda = valorDeConsulta(filtros.moneda);
  const estado = valorDeConsulta(filtros.estado);
  if (ejercicio) qs.set("ejercicio", ejercicio);
  if (moneda) qs.set("moneda", moneda);
  if (estado) qs.set("estado", estado);
  const s = qs.toString();
  return s ? `?${s}` : "";
}

export function consultaDeRubros(filtros: { estado?: string; tipo?: string }): string {
  const qs = new URLSearchParams();
  const estado = valorDeConsulta(filtros.estado);
  const tipo = valorDeConsulta(filtros.tipo);
  if (estado) qs.set("estado", estado);
  if (tipo) qs.set("tipo", tipo);
  const s = qs.toString();
  return s ? `?${s}` : "";
}

/** Cadena de consulta de /gobierno/tesoreria/cuentas (estado, banco, moneda y cargo; omite vacíos). */
export function consultaDeCuentas(filtros: { estado?: string; banco_id?: string; moneda?: string; cargo_id?: string }): string {
  const qs = new URLSearchParams();
  const estado = valorDeConsulta(filtros.estado);
  const bancoId = valorDeConsulta(filtros.banco_id);
  const moneda = valorDeConsulta(filtros.moneda);
  const cargoId = valorDeConsulta(filtros.cargo_id);
  if (estado) qs.set("estado", estado);
  if (bancoId) qs.set("banco_id", bancoId);
  if (moneda) qs.set("moneda", moneda);
  if (cargoId) qs.set("cargo_id", cargoId);
  const s = qs.toString();
  return s ? `?${s}` : "";
}

/** Texto corto de un acto para selectores y fichas. */
export function textoDeActo(acto: ActoReferencia): string {
  return `${acto.tipo} ${acto.numero} · ${acto.asunto}`;
}

/** Cadena de consulta de /gobierno/sod/conflictos. */
export function consultaDeConflictosSod(
  filtros: { regla_id?: string; proceso?: string; accion?: string; usuario?: string; desde?: string; hasta?: string },
  paginacion: { pagina?: number; por_pagina?: number } = {},
): string {
  const qs = new URLSearchParams();
  const reglaId = valorDeConsulta(filtros.regla_id);
  const proceso = valorDeConsulta(filtros.proceso);
  const accion = valorDeConsulta(filtros.accion);
  const usuario = valorDeConsulta(filtros.usuario);
  const desde = valorDeConsulta(filtros.desde);
  const hasta = valorDeConsulta(filtros.hasta);
  if (reglaId) qs.set("regla_id", reglaId);
  if (proceso) qs.set("proceso", proceso);
  if (accion) qs.set("accion", accion);
  if (usuario) qs.set("usuario", usuario);
  if (desde) qs.set("desde", desde);
  if (hasta) qs.set("hasta", hasta);
  if (paginacion.pagina !== undefined) qs.set("pagina", String(paginacion.pagina));
  if (paginacion.por_pagina !== undefined) qs.set("por_pagina", String(paginacion.por_pagina));
  const s = qs.toString();
  return s ? `?${s}` : "";
}

// ORG-04 · Ocupación de cargos (GOV-ORG-004, GOV-ORG-009)
export type FiguraAsignacion = "TITULAR" | "ENCARGADURIA" | "SUPLENCIA" | "COMISION_SERVICIO" | "DELEGACION_ATRIBUCIONES" | "DELEGACION_FIRMA";
export type EstadoAsignacion = "BORRADOR" | "ACTIVO" | "REVOCADO" | "FINALIZADO" | "DESCARTADO";
export type SituacionAsignacion = "BORRADOR" | "DESCARTADA" | "FUTURA" | "VIGENTE" | "VENCIDA" | "REVOCADA" | "FINALIZADA" | "SIN_EFECTO";
export type EstadoFuncionario = "ACTIVO" | "INACTIVO";
export type TipoDocumentoFuncionario = "V" | "E" | "P";
export type AccionCompetenciaOcupacion = "SOLICITAR" | "COMPROMETER" | "CAUSAR" | "ORDENAR_PAGO" | "PAGAR" | "REGISTRAR" | "CUSTODIAR" | "APROBAR" | "AUDITAR" | "FIRMAR";
export type MateriaCompetenciaOcupacion = "PRESUPUESTO" | "CONTRATACIONES" | "TESORERIA" | "CONTABILIDAD" | "BIENES" | "EXPEDIENTE";

export interface FuncionarioResumen {
  id: string;
  codigo: string;
  nombre: string;
  documento: string;
  estado: EstadoFuncionario;
  version: number;
  creado_en: string;
}

export interface FuncionariosListado {
  items: FuncionarioResumen[];
  total: number;
  pagina: number;
  por_pagina: number;
}

export interface HistoriaOcupacion {
  id: string;
  tipo: string;
  detalle: Record<string, unknown> | null;
  actor: string | null;
  creado_en: string;
}

export interface ReferenciaFuncionario {
  id: string;
  codigo: string;
  nombre: string;
  documento: string;
}

export interface ReferenciaCargoOcupacion {
  id: string;
  codigo: string;
  nombre: string;
  unidad_id: string;
  unidad: string;
  ejercicio: number;
}

export interface ReferenciaActoOcupacion {
  id: string;
  tipo: string;
  numero: string;
  fecha: string;
  status: string;
  fecha_eficacia: string | null;
  medio: string | null;
  emisor_cargo_id: string;
  emisor_cargo: string;
  funcionario: string;
  asunto: string;
}

export interface CompetenciaOcupacion {
  accion: AccionCompetenciaOcupacion;
  materia: MateriaCompetenciaOcupacion;
  tipo_limite: string;
  monto: string | null;
  moneda: string | null;
}

export interface AsignacionResumen {
  id: string;
  codigo: string;
  figura: FiguraAsignacion;
  figura_etiqueta: string;
  funcionario: ReferenciaFuncionario;
  cargo: ReferenciaCargoOcupacion;
  cargo_origen: ReferenciaCargoOcupacion | null;
  acto: ReferenciaActoOcupacion;
  desde: string;
  hasta: string | null;
  fin_efectivo: string | null;
  status: EstadoAsignacion;
  situacion: SituacionAsignacion;
  version: number;
}

export interface AvocacionOcupacion {
  id: string;
  asunto: string;
  acto: ReferenciaActoOcupacion;
  actor: string | null;
  creado_en: string;
}

export interface AsignacionDetalle extends AsignacionResumen {
  fundamento: string;
  rendicion: string | null;
  maxima_autoridad: boolean;
  autorizacion_concejo: string | null;
  declara_delegable: boolean;
  acto_revocacion: ReferenciaActoOcupacion | null;
  motivo_fin: string | null;
  competencias: CompetenciaOcupacion[];
  autoridad: CompetenciaOcupacion[];
  ejerce: boolean;
  registrada_por: string | null;
  activada_por: string | null;
  activada_en: string | null;
  terminada_por: string | null;
  terminada_en: string | null;
  historia: HistoriaOcupacion[];
  avocaciones: AvocacionOcupacion[];
}

export interface AsignacionesListado {
  items: AsignacionResumen[];
  total: number;
  pagina: number;
  por_pagina: number;
  fecha: string;
}

export interface FuncionarioDetalle extends FuncionarioResumen {
  historia: HistoriaOcupacion[];
  asignaciones: AsignacionResumen[];
}

export interface OcupacionCargoFila {
  cargo: ReferenciaCargoOcupacion;
  titular: AsignacionResumen | null;
  ejerce: AsignacionResumen | null;
  vacante: boolean;
  delegaciones: number;
}

export interface OcupacionListado {
  ejercicio: number;
  fecha: string;
  items: OcupacionCargoFila[];
  total: number;
  pagina: number;
  por_pagina: number;
}

export interface CargoOcupacion {
  cargo: ReferenciaCargoOcupacion;
  fecha: string;
  titular: AsignacionResumen | null;
  ejerce: AsignacionResumen | null;
  vacante: boolean;
  delegaciones: AsignacionResumen[];
  competencias: CompetenciaOcupacion[];
  historial: AsignacionResumen[];
}

export interface FiguraCatalogo {
  codigo: string;
  etiqueta: string;
  grupo: string;
  base_legal: string;
  descripcion: string;
}

export interface InstrumentoCatalogo {
  codigo: string;
  etiqueta: string;
}

export interface CatalogoOcupacion {
  figuras: FiguraCatalogo[];
  instrumentos: InstrumentoCatalogo[];
  situaciones: string[];
}

export interface OpcionFuncionario {
  id: string;
  codigo: string;
  nombre: string;
}

export interface OpcionCargoOcupacion {
  id: string;
  codigo: string;
  nombre: string;
  unidad: string;
  ejercicio: number;
  competencias: CompetenciaOcupacion[];
}

export interface OpcionActoOcupacion {
  id: string;
  numero: string;
  tipo: string;
  fecha: string;
  fecha_eficacia: string | null;
  medio: string | null;
  emisor_cargo_id: string;
  emisor_cargo: string;
  asunto: string;
}

export interface OpcionesOcupacion {
  funcionarios: OpcionFuncionario[];
  cargos: OpcionCargoOcupacion[];
  actos: OpcionActoOcupacion[];
}

export interface FuncionarioEntrada {
  nombre: string;
  tipo_documento: TipoDocumentoFuncionario;
  numero_documento: string;
}

export interface AsignacionEntrada {
  funcionario_id: string;
  cargo_id: string;
  figura: FiguraAsignacion;
  cargo_origen_id: string | null;
  acto_id: string;
  desde: string;
  hasta: string | null;
  fundamento: string;
  rendicion: string | null;
  maxima_autoridad: boolean;
  autorizacion_concejo: string | null;
  declara_delegable: boolean;
  competencias: { accion: AccionCompetenciaOcupacion; materia: MateriaCompetenciaOcupacion }[];
}

export const CONSULTA_OCUPACION = [...CONSULTA_GOBIERNO, "ocupacion"] as const;
export const POR_PAGINA_OCUPACION = 50;

export const ETIQUETAS_SITUACION_ASIGNACION: Record<SituacionAsignacion, string> = {
  BORRADOR: "Borrador",
  DESCARTADA: "Descartada",
  FUTURA: "Futura",
  VIGENTE: "Vigente",
  VENCIDA: "Vencida",
  REVOCADA: "Revocada",
  FINALIZADA: "Finalizada",
  SIN_EFECTO: "Sin efecto",
};

export const ETIQUETAS_ESTADO_ASIGNACION: Record<EstadoAsignacion, string> = {
  BORRADOR: "Borrador",
  ACTIVO: "Activa",
  REVOCADO: "Revocada",
  FINALIZADO: "Finalizada",
  DESCARTADO: "Descartada",
};

export const ETIQUETAS_ESTADO_FUNCIONARIO: Record<EstadoFuncionario, string> = {
  ACTIVO: "Activo",
  INACTIVO: "Inactivo",
};

export const ETIQUETAS_TIPO_DOCUMENTO_FUNCIONARIO: Record<TipoDocumentoFuncionario, string> = {
  V: "Venezolano",
  E: "Extranjero",
  P: "Pasaporte",
};

export const ETIQUETAS_HISTORIA_OCUPACION: Record<string, string> = {
  CREADO: "Registrado",
  EDITADO: "Modificado",
  CREADA: "Registrada",
  EDITADA: "Modificada",
  ACTIVADA: "Activada",
  DESCARTADA: "Descartada",
  REVOCADA: "Revocada",
  FINALIZADA: "Finalizada",
  AVOCADA: "Competencia avocada",
};

export function esDelegacion(figura: FiguraAsignacion): boolean {
  return figura === "DELEGACION_ATRIBUCIONES" || figura === "DELEGACION_FIRMA";
}

export function exigeCargoOrigen(figura: FiguraAsignacion): boolean {
  return figura === "SUPLENCIA" || figura === "COMISION_SERVICIO" || esDelegacion(figura);
}

export function exigeFechaFinal(figura: FiguraAsignacion): boolean {
  return figura === "SUPLENCIA" || figura === "COMISION_SERVICIO";
}

export function consultaDeOcupacion(f: { ejercicio: number; fecha?: string; texto?: string; pagina?: number }): string {
  const params = new URLSearchParams();
  params.set("ejercicio", String(f.ejercicio));
  if (f.fecha) params.set("fecha", f.fecha);
  if (f.texto) params.set("texto", f.texto);
  if (f.pagina && f.pagina > 1) params.set("pagina", String(f.pagina));
  const qs = params.toString();
  return qs ? `?${qs}` : "";
}

export function consultaDeAsignaciones(f: { figura?: string; estado?: string; funcionario_id?: string; cargo_id?: string; fecha?: string; pagina?: number }): string {
  const params = new URLSearchParams();
  if (f.figura) params.set("figura", f.figura);
  if (f.estado) params.set("estado", f.estado);
  if (f.funcionario_id) params.set("funcionario_id", f.funcionario_id);
  if (f.cargo_id) params.set("cargo_id", f.cargo_id);
  if (f.fecha) params.set("fecha", f.fecha);
  if (f.pagina && f.pagina > 1) params.set("pagina", String(f.pagina));
  const qs = params.toString();
  return qs ? `?${qs}` : "";
}

export function consultaDeFuncionarios(f: { texto?: string; estado?: string; pagina?: number }): string {
  const params = new URLSearchParams();
  if (f.texto) params.set("texto", f.texto);
  if (f.estado) params.set("estado", f.estado);
  if (f.pagina && f.pagina > 1) params.set("pagina", String(f.pagina));
  const qs = params.toString();
  return qs ? `?${qs}` : "";
}
