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
  firmante: { cargo: string; funcionario: string | null } | null;
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

export const CONSULTA_CONTRATOS = [...CONSULTA_GOBIERNO, "contratos"] as const;

export const TIPOS_INSTRUMENTO: { codigo: TipoInstrumento; etiqueta: string }[] = [
  { codigo: "CONTRATO", etiqueta: "Contrato" },
  { codigo: "ORDEN_COMPRA", etiqueta: "Orden de compra" },
  { codigo: "ORDEN_SERVICIO", etiqueta: "Orden de servicio" },
];

export function rutaContrato(id: string): string {
  return `/gobierno/contratos/${id}`;
}
