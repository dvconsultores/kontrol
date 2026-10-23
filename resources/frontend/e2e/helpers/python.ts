/**
 * El intérprete de los ayudantes Python es el de la certificación en curso.
 * qa/e2e-run.py lo fija una vez en KONTROL_E2E_PYTHON; nunca un entorno virtual fijo
 * ni python/python3 del PATH. Sin la variable el ayudante no corre.
 */
import { execFileSync, type ExecFileSyncOptionsWithStringEncoding } from "node:child_process";
import { isAbsolute } from "node:path";

export function pythonDeLaCertificacion(): string {
  const python = process.env.KONTROL_E2E_PYTHON;
  if (!python || !isAbsolute(python)) {
    throw new Error("KONTROL_E2E_PYTHON es obligatoria y absoluta: los ayudantes Python corren con el intérprete de la certificación (qa/e2e-run.py)");
  }
  return python;
}

export function ejecutarPython(argumentos: readonly string[], opciones: ExecFileSyncOptionsWithStringEncoding): string {
  return execFileSync(pythonDeLaCertificacion(), argumentos, opciones);
}
