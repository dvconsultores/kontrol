/**
 * Separación de la caché por empresa (ARCH-MC-001, N6).
 *
 * El problema no es que una consulta vaya mal etiquetada: es que dos empresas
 * distintas comparten una misma entrada de caché. Si `["ventas","ordenes"]`
 * identifica a la vez las órdenes de A y las de B, cambiar de empresa muestra
 * las de A bajo el rótulo de B hasta que llegue la respuesta nueva —y si la
 * consulta está fresca, no llega nunca.
 *
 * Se resuelve en el único sitio donde no se puede olvidar: la función que la
 * caché usa para convertir una clave en su identidad. Con 271 consultas
 * repartidas por la aplicación, confiar en que cada una recuerde añadir la
 * empresa sería confiar en que ninguna se olvide.
 *
 * Invalidar al cambiar de empresa **no** sustituye a esto. Invalidar marca lo
 * viejo como caducado; separar hace que lo de A y lo de B nunca hayan sido la
 * misma cosa.
 */
import { hashKey, type QueryKey } from "@tanstack/react-query";

/**
 * Raíces que **no** dependen de la empresa.
 *
 * Corta a propósito: en KONTROL casi todo lo es. Lo que se enumera es la
 * excepción, así que una consulta nueva que nadie recuerde clasificar queda
 * separada por empresa, que es el lado seguro de equivocarse.
 */
const RAICES_SIN_EMPRESA = new Set([
  "auth",
  "license",
  "licencia",
  "health",
  "diagnostics",
  "system",
  "organizacion-empresas",
  "empresas",
  "tenants",
  "setup",
]);

export function esClaveDeEmpresa(key: QueryKey): boolean {
  const raiz = Array.isArray(key) ? key[0] : key;
  return !(typeof raiz === "string" && RAICES_SIN_EMPRESA.has(raiz));
}

/**
 * Identidad de una clave, teniendo en cuenta la empresa activa.
 *
 * `resolver` se consulta en cada cálculo a propósito: cuando el usuario cambia
 * de empresa, la misma clave pasa a tener otra identidad y los observadores
 * dejan de ver la entrada anterior. Eso es lo que hace imposible que un dato
 * de A aparezca bajo B, en vez de solo improbable.
 */
export function crearHashDeClave(
  resolver: () => string | null,
): (key: QueryKey) => string {
  return (key: QueryKey): string => {
    if (!esClaveDeEmpresa(key)) {
      return hashKey(key);
    }
    return hashKey(["@empresa", resolver() ?? "@sin-empresa", ...(Array.isArray(key) ? key : [key])]);
  };
}
