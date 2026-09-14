/**
 * Localización de la interfaz (Spec 047 · OQ-047-02).
 *
 * Catálogo `es` en V1; `en` está DEFERRED. Añadir un idioma es añadir su
 * catálogo aquí: ni las pantallas ni los contratos de la API cambian.
 *
 * Los mensajes de dominio (notificaciones, tareas, alertas) no pasan por aquí:
 * los compone el servidor desde `message_key` y sus parámetros.
 */
import { es } from "./es";

export const IDIOMA = "es";

const CATALOGOS = { es } as const;
const LOCALES = { es: "es-VE" } as const;
const VARIABLE = /\{([a-z_][a-z0-9_]*)\}/g;

export type ClaveUI = keyof typeof es;
export type Parametros = Record<string, string | number>;

/** Texto de la interfaz. Un parámetro que falta deja su marcador a la vista. */
export function t(clave: ClaveUI, parametros: Parametros = {}): string {
  return CATALOGOS[IDIOMA][clave].replace(VARIABLE, (entera, nombre: string) =>
    nombre in parametros ? String(parametros[nombre]) : entera,
  );
}

/** Etiqueta de un valor que llega del servidor, o `null` si el catálogo no la tiene. */
export function tValor(prefijo: string, valor: string): string | null {
  const clave = `${prefijo}.${valor}`;
  const catalogo: Record<string, string> = CATALOGOS[IDIOMA];
  return clave in catalogo ? catalogo[clave] : null;
}

export function formatearFecha(iso: string | null | undefined): string {
  return iso ? new Date(iso).toLocaleString(LOCALES[IDIOMA]) : t("comun.sin_valor");
}

export const IDIOMAS_DISPONIBLES = Object.keys(CATALOGOS);
