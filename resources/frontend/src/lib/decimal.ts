/**
 * Texto decimal exacto para dinero (Spec 038 · FLOAT-038-A).
 *
 * El importe nunca pasa por `Number`: un `double` de JavaScript no distingue
 * 1234567890123456.78 de 1234567890123456.8. Lo que escribe el usuario se
 * normaliza como texto; el backend sigue siendo la autoridad y rechaza lo que
 * no cabe.
 */

/**
 * Normaliza una entrada de importe a texto canónico con `scale` decimales.
 *
 * Acepta punto o coma como separador decimal y ceros a la izquierda
 * (`"001,2"` → `"1.20"`). Devuelve `null` si no es un decimal sin signo o si
 * tiene más decimales que `scale`: no redondea.
 */
export function toDecimalString(input: string, scale = 2): string | null {
  const match = /^([0-9]+)(?:[.,]([0-9]*))?$/.exec(input.trim());
  if (!match) return null;
  const [, integer, fraction = ""] = match;
  if (fraction.length > scale) return null;
  const whole = integer.replace(/^0+(?=[0-9])/, "");
  return scale === 0 ? whole : `${whole}.${fraction.padEnd(scale, "0")}`;
}

/**
 * `true` si el texto decimal vale exactamente cero (`"0"`, `"0.00"`, `"-0.00"`).
 *
 * Decide sin `Number` y sin tolerancia: `"0.01"` no es cero (Spec 038 ·
 * FLOAT-038-B). `null` —todavía sin diferencia— cuenta como cero.
 */
export function isZeroDecimal(value: string | null): boolean {
  return value === null || /^[+-]?0+(\.0+)?$/.test(value.trim());
}
