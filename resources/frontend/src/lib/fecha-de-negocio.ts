/**
 * La fecha de negocio en el navegador (Spec 001 · POLICY-CLOCK-LOCAL).
 *
 * El backend es la autoridad: decide qué política rige, si una cotización venció o
 * qué versión de una regla se aplica. Pero hay pantallas que **envían** una fecha de
 * negocio en el cuerpo de la petición, y ahí el navegador sí decide.
 *
 * `new Date().toISOString().slice(0, 10)` da el día en **UTC**, y
 * `toLocaleDateString()` da el del navegador. Ninguno de los dos es el calendario de
 * la empresa: a las nueve de la noche en Caracas, el primero ya está en mañana.
 *
 * Esto no sustituye al backend; evita que el navegador le mande un día equivocado.
 */

/** El calendario de negocio de KONTROL. Decidido por la dueña; una sola zona. */
export const ZONA_DE_NEGOCIO = "America/Caracas";

/**
 * El día de negocio en formato `AAAA-MM-DD`, para enviar al servidor.
 *
 * Usa `Intl` en lugar de aritmética de husos: es la API nativa que sabe de zonas, y
 * `en-CA` da directamente el orden ISO.
 */
export function hoyDeNegocio(instante: Date = new Date()): string {
  return new Intl.DateTimeFormat("en-CA", {
    timeZone: ZONA_DE_NEGOCIO,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).format(instante);
}
