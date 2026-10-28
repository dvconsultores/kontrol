/** Utilidades de formato (DOC-08 §9.3/9.4). */
import { format as dfFormat } from "date-fns";
import { es } from "date-fns/locale";

import { horaDeCaracasParaInput } from "./fecha-de-negocio";

/**
 * Formatea un monto como string decimal (nunca flotante binario).
 * El separador de miles se muestra según locale; el valor interno es string.
 */
export function formatMoney(value: string | number, decimals = 2): string {
  const normalized = typeof value === "number" ? value.toFixed(decimals) : value;
  const [integer, decimal] = normalized.split(".");
  const withThousand = integer.replace(/\B(?=(\d{3})+(?!\d))/g, ".");
  return decimal ? `${withThousand},${decimal}` : withThousand;
}

/** Formatea una fecha ISO como fecha de pantalla en es-VE. */
export function formatDate(value: string | Date, pattern = "dd/MM/yyyy"): string {
  if (typeof value === "string" && /^\d{4}-\d{2}-\d{2}$/.test(value)) {
    const [anio, mes, dia] = value.split("-").map(Number);
    return dfFormat(new Date(anio, mes - 1, dia), pattern, { locale: es });
  }

  const instante = typeof value === "string" ? new Date(value) : value;
  const local = horaDeCaracasParaInput(instante);
  const [fecha, tiempo] = local.split("T");
  const [anio, mes, dia] = fecha.split("-").map(Number);
  const [hora, minuto] = tiempo.split(":").map(Number);
  return dfFormat(new Date(anio, mes - 1, dia, hora, minuto), pattern, {
    locale: es,
  });
}

/** Convierte un string decimal a entero de escala fija (evita flotantes). */
export function toScaledInt(value: string, decimals = 2): number {
  const [intPart = "0", decPart = ""] = value.trim().split(".");
  const dec = decPart.padEnd(decimals, "0").slice(0, decimals);
  return Number(`${intPart}${dec}`);
}
