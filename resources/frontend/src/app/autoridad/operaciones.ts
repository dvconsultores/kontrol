// Autoridad de la UI como proyección del backend: resuelve una llamada a su operación
// del catálogo (`GET /auth/operations`) y la evalúa con las capacidades del usuario (Spec 003, ADR-018).
export type Alcance = "COMPANY" | "TENANT" | "GLOBAL";
export interface Operacion { method: string; path: string; capabilities: string[]; scope: Alcance }
export interface Conjuntos { empresa: ReadonlySet<string>; tenant: ReadonlySet<string>; global: ReadonlySet<string> }
export type Motivo = "PERMISSION_DENIED" | "COMPANY_SCOPE_FORBIDDEN";
export interface Evaluacion { permitido: boolean; motivo: Motivo | null; alcance: Alcance | null }
/** Una operación del catálogo, ya partida en segmentos, con su número de segmentos literales. */
interface Entrada { operacion: Operacion; segmentos: string[]; literales: number }
/** Índice por método y número de segmentos (`MÉTODO:n`). */
export interface Indice { porClave: Map<string, Entrada[]> }

const PREFIJO_API = "/api/v1";

/**
 * Convierte una ruta concreta o patrón en sus segmentos, descartando
 * query string, prefijo de API y elementos vacíos.
 */
function segmentos(ruta: string): string[] {
  const sinQuery = ruta.split("?")[0] ?? "";
  const sinPrefijo = sinQuery.startsWith(PREFIJO_API)
    ? sinQuery.slice(PREFIJO_API.length)
    : sinQuery;
  return sinPrefijo.split("/").filter((parte) => parte.length > 0);
}

function esPlantilla(segmento: string): boolean {
  return (
    segmento.startsWith("{") &&
    segmento.endsWith("}") &&
    segmento.length > 2
  );
}

export function crearIndice(operaciones: readonly Operacion[]): Indice {
  const porClave = new Map<string, Entrada[]>();

  operaciones.forEach((operacion) => {
    const segmentosOperacion = segmentos(operacion.path);
    const literales = segmentosOperacion.filter(
      (segmento) => !esPlantilla(segmento),
    ).length;
    const clave = `${operacion.method.toUpperCase()}:${segmentosOperacion.length}`;
    const lista = porClave.get(clave) ?? [];
    lista.push({
      operacion,
      segmentos: segmentosOperacion,
      literales,
    });
    porClave.set(clave, lista);
  });

  return { porClave };
}

export function resolver(
  indice: Indice,
  metodo: string,
  ruta: string,
): Operacion | null {
  const segmentosSolicitados = segmentos(ruta);
  const clave = `${metodo.toUpperCase()}:${segmentosSolicitados.length}`;
  const candidatas = indice.porClave.get(clave) ?? [];

  let mejor: Entrada | null = null;

  for (const entrada of candidatas) {
    const coincide = entrada.segmentos.every((patron, indiceSegmento) => {
      const segmento = segmentosSolicitados[indiceSegmento];
      if (segmento === undefined || segmento === "") {
        return false;
      }
      return esPlantilla(patron) || patron === segmento;
    });

    if (!coincide) {
      continue;
    }

    if (
      mejor === null ||
      entrada.literales > mejor.literales
    ) {
      mejor = entrada;
    }
  }

  return mejor?.operacion ?? null;
}

export function evaluar(
  operacion: Operacion | null,
  conjuntos: Conjuntos,
): Evaluacion {
  if (operacion === null) {
    return {
      permitido: false,
      motivo: "PERMISSION_DENIED",
      alcance: null,
    };
  }

  if (operacion.capabilities.length === 0) {
    return {
      permitido: true,
      motivo: null,
      alcance: operacion.scope,
    };
  }

  const conjuntoPorAlcance: Record<Alcance, ReadonlySet<string>> = {
    COMPANY: conjuntos.empresa,
    TENANT: conjuntos.tenant,
    GLOBAL: conjuntos.global,
  };

  const conjuntoObjetivo = conjuntoPorAlcance[operacion.scope];
  const todasDentro = operacion.capabilities.every((capacidad) =>
    conjuntoObjetivo.has(capacidad),
  );

  if (todasDentro) {
    return {
      permitido: true,
      motivo: null,
      alcance: operacion.scope,
    };
  }

  const todasEnGlobal =
    operacion.scope !== "GLOBAL" &&
    operacion.capabilities.every((capacidad) =>
      conjuntos.global.has(capacidad),
    );

  const motivo: Motivo = todasEnGlobal
    ? "COMPANY_SCOPE_FORBIDDEN"
    : "PERMISSION_DENIED";

  return {
    permitido: false,
    motivo,
    alcance: operacion.scope,
  };
}
