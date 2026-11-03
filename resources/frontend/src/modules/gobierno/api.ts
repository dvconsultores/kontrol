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
