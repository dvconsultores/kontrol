/**
 * El mundo multiempresa de N6, tal y como quedó sembrado.
 *
 * Las pruebas de N6 ya leían del disco los identificadores en vez de fijarlos:
 * sembrar de nuevo genera otros, y una prueba con ids a mano acaba pasando por
 * el motivo equivocado —el id ya no existe, así que claro que se rechaza—. Los
 * **nombres** seguían escritos a mano, y eso las ataba a una siembra concreta:
 * la empresa A es la que ya hubiera en el tenant, y se llama «Demo C.A.» en la
 * base del E2E y de otra manera en la pila SQLite autónoma. Comprobar el nombre
 * literal era comprobar qué guion había corrido.
 *
 * Aquí se lee todo del mismo sitio —`qa/n6_world.py` lo escribe— para que haya
 * una sola autoridad sobre qué mundo hay delante.
 */
import { readFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

export interface MundoN6 {
  empresa_a: string;
  empresa_b: string;
  empresa_c: string;
  tenant_1: string;
  tenant_2: string;
  nombre_a: string;
  nombre_b: string;
  nombre_c: string;
  tercero_a: string;
  tercero_b: string;
  tercero_c: string;
  documento_b: string;
  documento_c: string;
  producto_b: string;
  producto_c: string;
  doc_b: string;
  doc_c: string;
  prod_b: string;
  prod_c: string;
}

const RUTA = process.env.KONTROL_QA_IDS_FILE ?? join(tmpdir(), "kontrol-n6-ids.json");

export function mundoN6(): MundoN6 {
  let crudo: string;
  try {
    crudo = readFileSync(RUTA, "utf8");
  } catch {
    throw new Error(
      `no está el mundo de N6 en ${RUTA}: siémbrelo con «bash qa/e2e-seed.sh <URL de la base>» ` +
      "sobre la misma base contra la que corre esta suite",
    );
  }
  const mundo = JSON.parse(crudo) as Partial<MundoN6>;
  for (const clave of ["empresa_a", "empresa_b", "empresa_c", "nombre_a", "nombre_b"] as const) {
    if (!mundo[clave]) {
      throw new Error(`el mundo de N6 en ${RUTA} no trae «${clave}»: vuelva a sembrarlo`);
    }
  }
  return mundo as MundoN6;
}
