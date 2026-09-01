/**
 * Errores de contexto de empresa (ARCH-MC-001, N6).
 *
 * Distinguirlos de los de autenticación importa: que el servidor rechace la
 * empresa activa no significa que la sesión haya caducado. Tratarlo como tal
 * expulsaría al usuario por haber perdido el acceso a **una** de sus empresas.
 */
import { ApiError } from "@/api/client";

export const CODIGOS_DE_CONTEXTO = new Set([
  "COMPANY_CONTEXT_REQUIRED",
  "COMPANY_NOT_FOUND",
  "COMPANY_INACTIVE",
]);

export function esErrorDeContexto(error: unknown): boolean {
  return error instanceof ApiError && CODIGOS_DE_CONTEXTO.has(error.code);
}

/**
 * Un error de contexto **no** debe reintentarse.
 *
 * Reintentar contra una empresa que el servidor acaba de rechazar produce el
 * mismo rechazo indefinidamente: el bucle que §322 describe. Lo que corresponde
 * es soltar el contexto y volver a preguntar qué empresas son operables.
 */
export function debeReintentar(intentos: number, error: unknown): boolean {
  if (esErrorDeContexto(error)) {
    return false;
  }
  if (error instanceof ApiError && (error.status === 403 || error.status === 404)) {
    return false;
  }
  return intentos < 1;
}

export function mensajeDeContexto(error: unknown): string | null {
  if (!(error instanceof ApiError)) {
    return null;
  }
  switch (error.code) {
    case "COMPANY_CONTEXT_REQUIRED":
      return "Seleccione la empresa en la que desea operar.";
    case "COMPANY_NOT_FOUND":
      return "La empresa seleccionada ya no está disponible para su usuario.";
    case "COMPANY_INACTIVE":
      return "La empresa seleccionada está inactiva.";
    default:
      return null;
  }
}
