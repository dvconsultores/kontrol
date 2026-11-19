import { apiFetch } from "@/api/client";
import type { EvidenciaAnexo, ReglaActa } from "./api";

/** Políticas de actas de entrega (CTL-09-DELIVERY-ACT-POLICY). Tipos del contrato de la API. */

export type EstadoPoliticaActa = "BORRADOR" | "VIGENTE" | "CERRADA";
export type CodigoSupuesto = "N34_ART11" | "N34_ART12" | "N34_ART13" | "N34_ART14" | "N34_ART15" | "N34_ART16" | "N34_ART17";
export type AlcanceVinculo = "ENTE" | "UNIDAD";
export type AmbitoRequisito = "TODAS" | "ENTE" | "UNIDAD";
export type HitoPlazoPolitica = "ELABORACION" | "REMISION_UAI";
export type UnidadPlazo = "DIAS_HABILES" | "DIAS_CONTINUOS";

export interface ItemCatalogo {
  codigo: string;
  etiqueta: string;
}

export interface CatalogoPoliticaActa {
  estados: ItemCatalogo[];
  evidencias: ItemCatalogo[];
  ambitos_requisito: ItemCatalogo[];
  alcances: ItemCatalogo[];
  hitos: ItemCatalogo[];
  unidades_plazo: ItemCatalogo[];
}

/** Supuesto del catálogo legal de N34; `declarable` depende del nivel territorial del ente. */
export interface SupuestoCatalogo {
  codigo: CodigoSupuesto;
  articulo: string;
  titulo: string;
  sujeto: string;
  vinculo: "UNIVERSAL" | "DECLARADO";
  niveles: string[] | null;
  ambitos: AlcanceVinculo[];
  nota: string | null;
  anexos: { codigo: string; titulo: string; obligatorio: boolean; generable: boolean }[];
  declarable: boolean;
  motivo_no_declarable: string | null;
}

export interface OpcionesPoliticaActa {
  nivel_territorial: string | null;
  forma_organizativa: string | null;
  supuestos: SupuestoCatalogo[];
  unidades: { id: string; codigo: string; nombre: string }[];
  tipos_documento: { id: string; nombre: string }[];
  actos: { id: string; etiqueta: string }[];
  testigos_legales: { modalidad: string; testigos: number; auditor_interno: boolean; fuente: string };
  plazos_legales: { hito: string; valor: number; unidad: UnidadPlazo; base: string; fuente: string }[];
  patron_por_defecto: string;
}

export interface VinculoPolitica {
  supuesto: CodigoSupuesto;
  articulo?: string | null;
  titulo?: string | null;
  alcance: AlcanceVinculo;
  unit_id: string | null;
  unidad?: string | null;
}

export interface RequisitoPolitica {
  codigo: string;
  titulo: string;
  evidencia: EvidenciaAnexo;
  obligatorio: boolean;
  ambito: AmbitoRequisito;
  supuesto: CodigoSupuesto | null;
  document_type_id: string | null;
  document_type_nombre?: string | null;
  fuente: string | null;
}

export interface PlazoPolitica {
  hito: HitoPlazoPolitica;
  valor: number;
  unidad: UnidadPlazo;
  fuente: string | null;
  legal_valor?: number | null;
  legal_fuente?: string | null;
}

export interface PoliticaActaResumen {
  id: string;
  codigo: string;
  numero_version: number;
  nombre: string;
  estado: EstadoPoliticaActa;
  estado_etiqueta: string;
  vigente_desde: string;
  vigente_hasta: string | null;
  total_vinculos: number;
  total_requisitos: number;
  version: number;
}

export interface PoliticasActaListado {
  items: PoliticaActaResumen[];
  total: number;
  pagina: number;
  por_pagina: number;
}

export interface PoliticaActaDetalle extends PoliticaActaResumen {
  descripcion: string | null;
  fundamento: string | null;
  act_id: string | null;
  numeracion_patron: string | null;
  testigos_en_entrega: number;
  cargo_maxima_autoridad_codigo: string | null;
  version_anterior_id: string | null;
  activada_en: string | null;
  cerrada_en: string | null;
  motivo_cierre: string | null;
  vinculos: VinculoPolitica[];
  requisitos: RequisitoPolitica[];
  plazos: PlazoPolitica[];
  /** Regla que tendría un acta de la entidad con esta política (vista previa). */
  regla_ente: ReglaActa;
  historia: { evento: string; version: number; fecha: string; actor: string | null }[];
  versiones: { id: string; numero_version: number; estado: EstadoPoliticaActa }[];
  actas_que_la_usan: number;
  acciones: { editar: boolean; activar: boolean; cerrar: boolean; nueva_version: boolean };
}

export interface PoliticaActaEntrada {
  codigo: string;
  nombre: string;
  descripcion: string | null;
  fundamento: string | null;
  act_id: string | null;
  vigente_desde: string;
  vigente_hasta: string | null;
  numeracion_patron: string | null;
  testigos_en_entrega: number;
  cargo_maxima_autoridad_codigo: string | null;
  vinculos: { supuesto: CodigoSupuesto; alcance: AlcanceVinculo; unit_id: string | null }[];
  requisitos: Omit<RequisitoPolitica, "document_type_nombre">[];
  plazos: Omit<PlazoPolitica, "legal_valor" | "legal_fuente">[];
}

export interface VistaPreviaNumeracion {
  valido: boolean;
  motivo: string | null;
  ejemplos: string[];
}

const BASE = "/gobierno/actas-entrega/politicas";

export function getCatalogoPoliticasActa(): Promise<CatalogoPoliticaActa> {
  return apiFetch<CatalogoPoliticaActa>(`${BASE}/catalogo`);
}

export function getOpcionesPoliticasActa(): Promise<OpcionesPoliticaActa> {
  return apiFetch<OpcionesPoliticaActa>(`${BASE}/opciones`);
}

export function listarPoliticasActa(params: { estado?: string; q?: string; pagina?: number } = {}): Promise<PoliticasActaListado> {
  const consultaListado = new URLSearchParams();
  if (params.estado) consultaListado.set("estado", params.estado);
  if (params.q) consultaListado.set("q", params.q);
  if (params.pagina) consultaListado.set("pagina", String(params.pagina));
  const sufijo = consultaListado.toString();
  return apiFetch<PoliticasActaListado>(sufijo ? `${BASE}?${sufijo}` : BASE);
}

export function getPoliticaActa(id: string): Promise<PoliticaActaDetalle> {
  return apiFetch<PoliticaActaDetalle>(`${BASE}/${id}`);
}

export function crearPoliticaActa(body: PoliticaActaEntrada): Promise<PoliticaActaDetalle> {
  return apiFetch<PoliticaActaDetalle>(BASE, { method: "POST", body });
}

export function editarPoliticaActa(id: string, version: number, body: PoliticaActaEntrada): Promise<PoliticaActaDetalle> {
  return apiFetch<PoliticaActaDetalle>(`${BASE}/${id}`, { method: "PUT", body, ifMatch: String(version) });
}

export function activarPoliticaActa(id: string, version: number): Promise<PoliticaActaDetalle> {
  return apiFetch<PoliticaActaDetalle>(`${BASE}/${id}/activar`, { method: "POST", ifMatch: String(version) });
}

export function cerrarPoliticaActa(id: string, version: number, motivo: string): Promise<PoliticaActaDetalle> {
  return apiFetch<PoliticaActaDetalle>(`${BASE}/${id}/cerrar`, { method: "POST", body: { motivo }, ifMatch: String(version) });
}

export function nuevaVersionPoliticaActa(id: string): Promise<PoliticaActaDetalle> {
  return apiFetch<PoliticaActaDetalle>(`${BASE}/${id}/nueva-version`, { method: "POST" });
}

export function vistaPreviaNumeracion(patron: string, anio?: number): Promise<VistaPreviaNumeracion> {
  const consultaVista = new URLSearchParams({ patron });
  if (anio) consultaVista.set("anio", String(anio));
  return apiFetch<VistaPreviaNumeracion>(`${BASE}/numeracion/vista-previa?${consultaVista}`);
}

/** Convierte el detalle en la entrada de la API, para editar o volver a enviar. */
export function entradaDesdeDetalle(d: PoliticaActaDetalle): PoliticaActaEntrada {
  return {
    codigo: d.codigo,
    nombre: d.nombre,
    descripcion: d.descripcion,
    fundamento: d.fundamento,
    act_id: d.act_id,
    vigente_desde: d.vigente_desde,
    vigente_hasta: d.vigente_hasta,
    numeracion_patron: d.numeracion_patron,
    testigos_en_entrega: d.testigos_en_entrega,
    cargo_maxima_autoridad_codigo: d.cargo_maxima_autoridad_codigo,
    vinculos: d.vinculos.map((v) => ({ supuesto: v.supuesto, alcance: v.alcance, unit_id: v.unit_id })),
    requisitos: d.requisitos.map((r) => ({
      codigo: r.codigo,
      titulo: r.titulo,
      evidencia: r.evidencia,
      obligatorio: r.obligatorio,
      ambito: r.ambito,
      supuesto: r.supuesto,
      document_type_id: r.document_type_id,
      fuente: r.fuente,
    })),
    plazos: d.plazos.map((p) => ({ hito: p.hito, valor: p.valor, unidad: p.unidad, fuente: p.fuente })),
  };
}
