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
 *
 * Este es el único sitio del frontend donde se formatean o convierten fechas
 * (ADR-020, FR-001-253/254): los instantes se muestran en Caracas aunque el
 * navegador esté en otra zona.
 */

/** El calendario de negocio de KONTROL. Decidido por la dueña; una sola zona. */
export const ZONA_DE_NEGOCIO = "America/Caracas";

/** Marca de ausencia de valor para las fechas de negocio sin dato. */
export const SIN_VALOR = "—";

/** El texto nativo de un `Date` inválido; se conserva a propósito (Spec 001 · DATE-13). */
export const FECHA_INVALIDA = "Invalid Date";

/** Partes de un instante en la hora de pared de Caracas. */
function partesDeCaracas(instante: Date): {
  anio: number;
  mes: number;
  dia: number;
  hora: number;
  minuto: number;
  segundo: number;
} {
  const partes = new Intl.DateTimeFormat("en-CA", {
    timeZone: ZONA_DE_NEGOCIO,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hourCycle: "h23",
  }).formatToParts(instante);

  const valor = (tipo: Intl.DateTimeFormatPartTypes): number => {
    const parte = partes.find((p) => p.type === tipo)?.value ?? "0";
    return Number.parseInt(parte, 10);
  };

  return {
    anio: valor("year"),
    mes: valor("month"),
    dia: valor("day"),
    hora: valor("hour"),
    minuto: valor("minute"),
    segundo: valor("second"),
  };
}

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

/**
 * Distingue un instante ausente de uno presente pero inválido.
 *
 * Devuelve {@link SIN_VALOR} para nulo o vacío, {@link FECHA_INVALIDA} para una
 * cadena no vacía que `Date` no puede interpretar como instante, y el `Date`
 * válido en caso contrario.
 */
function instanteOTexto(iso: string | null | undefined): Date | string {
  if (!iso) return SIN_VALOR;
  const fecha = new Date(iso);
  return Number.isNaN(fecha.getTime()) ? FECHA_INVALIDA : fecha;
}

/**
 * Formatea un instante como fecha y hora en Caracas.
 *
 * Nulo o vacío se muestra con {@link SIN_VALOR}; un valor no vacío que no es un
 * instante válido se muestra con {@link FECHA_INVALIDA}.
 */
export function formatearInstante(
  iso: string | null | undefined,
  locale = "es-VE",
): string {
  const valor = instanteOTexto(iso);
  if (typeof valor === "string") return valor;
  return valor.toLocaleString(locale, { timeZone: ZONA_DE_NEGOCIO });
}

/**
 * Formatea un instante como fecha (día, mes y año) en Caracas.
 *
 * Nulo o vacío se muestra con {@link SIN_VALOR}; un valor no vacío que no es un
 * instante válido se muestra con {@link FECHA_INVALIDA}.
 */
export function formatearFechaDeInstante(
  iso: string | null | undefined,
  locale = "es-VE",
): string {
  const valor = instanteOTexto(iso);
  if (typeof valor === "string") return valor;
  return valor.toLocaleDateString(locale, {
    timeZone: ZONA_DE_NEGOCIO,
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  });
}

/**
 * Devuelve la fecha de negocio `AAAA-MM-DD` de un instante, en Caracas.
 *
 * Nulo o vacío se muestra con {@link SIN_VALOR}; un valor no vacío que no es un
 * instante válido se muestra con {@link FECHA_INVALIDA}.
 */
export function fechaDeNegocioDeInstante(
  iso: string | null | undefined,
): string {
  const valor = instanteOTexto(iso);
  if (typeof valor === "string") return valor;
  return hoyDeNegocio(valor);
}

/**
 * Convierte una fecha de negocio `AAAA-MM-DD` en `DD/MM/AAAA`.
 *
 * Usa operaciones de texto, sin construir `Date`, para no desplazar el día.
 */
export function formatearFechaDeNegocio(
  fecha: string | null | undefined,
): string {
  const coincidencia = /^(\d{4})-(\d{2})-(\d{2})$/.exec(fecha ?? "");
  if (!coincidencia) return SIN_VALOR;

  const [, anio, mes, dia] = coincidencia;
  return `${dia}/${mes}/${anio}`;
}

/**
 * Convierte una hora de pared de Caracas en un instante UTC.
 *
 * Si no casa con `AAAA-MM-DDTHH:mm[:ss[.mmm]]`, devuelve `null`. No usa desfase
 * fijo: consulta la zona para corregir el desfase real de ese instante.
 */
export function instanteDesdeHoraDeCaracas(local: string): string | null {
  const coincidencia =
    /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})(?::(\d{2})(?:\.(\d{1,3}))?)?$/.exec(
      local,
    );
  if (!coincidencia) return null;

  const [, anio, mes, dia, hora, minuto, segundo = "0", milesimas = "0"] =
    coincidencia;
  const milisegundos = Number.parseInt(milesimas.padEnd(3, "0"), 10);
  const supuesto = Date.UTC(
    Number(anio),
    Number(mes) - 1,
    Number(dia),
    Number(hora),
    Number(minuto),
    Number(segundo),
    milisegundos,
  );

  const pared = (t: number): number => {
    const p = partesDeCaracas(new Date(t));
    return (
      Date.UTC(p.anio, p.mes - 1, p.dia, p.hora, p.minuto, p.segundo) +
      (((t % 1000) + 1000) % 1000)
    );
  };

  let t = supuesto - (pared(supuesto) - supuesto);
  t = supuesto - (pared(t) - t);
  return new Date(t).toISOString();
}

/**
 * Devuelve la hora de Caracas actual en formato para un `<input type="datetime-local">`.
 */
export function horaDeCaracasParaInput(instante: Date = new Date()): string {
  const p = partesDeCaracas(instante);
  const anio = String(p.anio).padStart(4, "0");
  const mes = String(p.mes).padStart(2, "0");
  const dia = String(p.dia).padStart(2, "0");
  const hora = String(p.hora).padStart(2, "0");
  const minuto = String(p.minuto).padStart(2, "0");
  return `${anio}-${mes}-${dia}T${hora}:${minuto}`;
}

/**
 * Devuelve el instante UTC del final del día de negocio `AAAA-MM-DD`.
 */
export function finDelDiaDeNegocio(fecha: string): string | null {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(fecha)) return null;
  return instanteDesdeHoraDeCaracas(`${fecha}T23:59:59.999`);
}

/** Suma `dias` días de calendario a la fecha civil `AAAA-MM-DD` (sin zona horaria: es aritmética de calendario). */
export function sumarDiasDeNegocio(fecha: string, dias: number): string | null {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(fecha)) return null;
  if (!Number.isInteger(dias)) return null;

  const anio = Number(fecha.slice(0, 4));
  const mes = Number(fecha.slice(5, 7));
  const dia = Number(fecha.slice(8, 10));

  const validacion = new Date(Date.UTC(anio, mes - 1, dia));
  if (
    validacion.getUTCFullYear() !== anio ||
    validacion.getUTCMonth() !== mes - 1 ||
    validacion.getUTCDate() !== dia
  ) {
    return null;
  }

  const resultado = new Date(Date.UTC(anio, mes - 1, dia + dias));
  const anioResultado = String(resultado.getUTCFullYear()).padStart(4, "0");
  const mesResultado = String(resultado.getUTCMonth() + 1).padStart(2, "0");
  const diaResultado = String(resultado.getUTCDate()).padStart(2, "0");
  return `${anioResultado}-${mesResultado}-${diaResultado}`;
}
