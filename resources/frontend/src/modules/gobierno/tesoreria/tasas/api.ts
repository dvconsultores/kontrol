import { formatMoney } from "@/lib/format";

export type EstadoTasa = "BORRADOR" | "APROBADA" | "SUSTITUIDA" | "ANULADA";

export interface TasaOficial {
  id: string;
  moneda: string;
  moneda_cotizacion: string;
  fecha_efectiva: string;
  valor: string;
  fuente: string;
  fuente_referencia: string;
  publicada_en: string | null;
  estado: EstadoTasa;
  version: number;
  sustituye_id: string | null;
  motivo_correccion: string | null;
  capturada_por: string;
  capturada_en: string;
  aprobada_por: string | null;
  aprobada_en: string | null;
  evidencia_documento_id: string | null;
  evidencia_sha256: string | null;
  sustituida_en: string | null;
  anulada_por: string | null;
  anulada_en: string | null;
  motivo_anulacion: string | null;
}

export interface TasaOficialDetalle extends TasaOficial {
  historia: TasaOficial[];
}

export interface TasasOficialesVista {
  items: TasaOficial[];
  monedas: string[];
  estados: string[];
}

export interface FiltrosTasas {
  moneda?: string;
  estado?: string;
  desde?: string;
  hasta?: string;
}

export const CONSULTA_TASAS = ["gobierno", "tasas"] as const;

export const ETIQUETAS_ESTADO_TASA: Record<EstadoTasa, string> = {
  BORRADOR: "Borrador",
  APROBADA: "Aprobada",
  SUSTITUIDA: "Sustituida",
  ANULADA: "Anulada",
};

export function consultaDeTasas(f: FiltrosTasas): string {
  const params = new URLSearchParams();
  if (f.moneda) params.set("moneda", f.moneda);
  if (f.estado) params.set("estado", f.estado);
  if (f.desde) params.set("desde", f.desde);
  if (f.hasta) params.set("hasta", f.hasta);
  const result = params.toString();
  return result ? `?${result}` : "";
}

export function normalizarTasa(texto: string): string {
  const sinEspacios = texto.replace(/\s+/g, "");
  if (sinEspacios.includes(",")) {
    return sinEspacios.replace(/\./g, "").replace(",", ".");
  }
  return sinEspacios;
}

/**
 * Formatea un valor decimal representado como texto.
 *
 * Reglas:
 * - Quita espacios.
 * - Separa en entero y decimal por ".".
 * - Quita los ceros de cola del decimal.
 * - Si queda con menos de `minimoDecimales` cifras, rellena con ceros.
 * - No trunca cifras significativas (si hay más, se muestran todas).
 * - Devuelve `formatMoney` con miles usando "." y decimal usando ",".
 *
 * Ejemplos:
 * - "900.500000000000" (8) -> "900,50000000"
 * - "905.123456789000" (8) -> "905,123456789"
 * - "1000.000000000000" (8) -> "1.000,00000000"
 * - "450000.000000000000000000" (2) -> "450.000,00"
 * - "900" (8) -> "900,00000000"
 */
export function formatearDecimal(valor: string, minimoDecimales: number): string {
  const sinEspacios = valor.replace(/\s+/g, "");
  const [entero = "", decimal = ""] = sinEspacios.split(".");

  let decimalSinCeros = decimal.replace(/0+$/, "");
  if (decimalSinCeros.length < minimoDecimales) {
    decimalSinCeros = decimalSinCeros.padEnd(minimoDecimales, "0");
  }

  if (minimoDecimales === 0 && decimalSinCeros === "") {
    return formatMoney(entero);
  }

  return formatMoney(`${entero}.${decimalSinCeros}`);
}

export function expresionTasa(t: { moneda: string; valor: string }): string {
  return `1 ${t.moneda} = ${formatearDecimal(t.valor, 8)} VES`;
}
