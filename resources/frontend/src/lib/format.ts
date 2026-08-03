/** Utilidades de formato (DOC-08 §9.3/9.4). */
import { format as dfFormat } from "date-fns";
import { es } from "date-fns/locale";

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
  const date = typeof value === "string" ? new Date(value) : value;
  return dfFormat(date, pattern, { locale: es });
}

/** Convierte un string decimal a entero de escala fija (evita flotantes). */
export function toScaledInt(value: string, decimals = 2): number {
  const [intPart = "0", decPart = ""] = value.trim().split(".");
  const dec = decPart.padEnd(decimals, "0").slice(0, decimals);
  return Number(`${intPart}${dec}`);
}
