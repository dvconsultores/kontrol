// @vitest-environment node
/**
 * Contrato estructural y pruebas de procesos reales para el lanzador central de los ayudantes Python.
 */
import { existsSync, mkdtempSync, readFileSync, readdirSync, realpathSync, rmSync, statSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, relative } from "node:path";

import ts from "typescript";
import { afterEach, beforeEach, describe, expect, it } from "vitest";

import { ejecutarPython, pythonDeLaCertificacion } from "../../e2e/helpers/python";

const RAIZ = join(__dirname, "..", "..");
const EXTENSIONES = new Set([".ts", ".mts", ".js", ".mjs"]);

function esEspecificadorDeModulo(nodo: ts.Node): boolean {
  if (ts.isStringLiteralLike(nodo)) {
    const padre = nodo.parent;
    if (padre && (ts.isImportDeclaration(padre) || ts.isExportDeclaration(padre))) {
      return padre.moduleSpecifier === nodo;
    }
    if (padre && ts.isCallExpression(padre)) {
      const esRequire = ts.isIdentifier(padre.expression) && padre.expression.text === "require";
      const esImportDinamico = padre.expression.kind === ts.SyntaxKind.ImportKeyword;
      if (esRequire || esImportDinamico) {
        return padre.arguments[0] === nodo;
      }
    }
  }
  return false;
}

function obtenerLiteral(nodo: ts.Node): ts.StringLiteralLike | ts.TemplateHead | ts.TemplateMiddle | ts.TemplateTail | undefined {
  if (ts.isStringLiteral(nodo) || ts.isNoSubstitutionTemplateLiteral(nodo)) {
    return nodo;
  }
  if (ts.isTemplateHead(nodo) || ts.isTemplateMiddle(nodo) || ts.isTemplateTail(nodo)) {
    return nodo;
  }
  return undefined;
}

function ficherosBajo(directorio: string): string[] {
  const salida: string[] = [];
  for (const nombre of readdirSync(directorio)) {
    const ruta = join(directorio, nombre);
    if (statSync(ruta).isDirectory()) {
      salida.push(...ficherosBajo(ruta));
    } else {
      const extension = nombre.slice(nombre.lastIndexOf("."));
      if (EXTENSIONES.has(extension)) {
        salida.push(relative(RAIZ, ruta).split("\\").join("/"));
      }
    }
  }
  return salida.sort();
}

function crearFuente(fichero: string, contenido: string): ts.SourceFile {
  const esScript = fichero.endsWith(".js") || fichero.endsWith(".mjs");
  return ts.createSourceFile(fichero, contenido, ts.ScriptTarget.Latest, true, esScript ? ts.ScriptKind.JS : ts.ScriptKind.TS);
}

function fuentes(): Array<[string, ts.SourceFile]> {
  return ficherosBajo(join(RAIZ, "e2e")).map((fichero) => [fichero, crearFuente(fichero, readFileSync(join(RAIZ, fichero), "utf8"))]);
}

function literales(fuente: ts.SourceFile): Array<{ fichero: string; texto: string }> {
  const resultado: Array<{ fichero: string; texto: string }> = [];
  const visitar = (nodo: ts.Node): void => {
    const literal = obtenerLiteral(nodo);
    if (literal && !esEspecificadorDeModulo(literal)) {
      resultado.push({ fichero: fuente.fileName, texto: literal.text });
    }
    ts.forEachChild(nodo, visitar);
  };
  visitar(fuente);
  return resultado;
}

function llamadasDeProceso(fuente: ts.SourceFile): Array<{ fichero: string; nombre: string; primero: string }> {
  const nombres = new Set(["execFileSync", "execFile", "execSync", "exec", "spawn", "spawnSync", "fork"]);
  const resultado: Array<{ fichero: string; nombre: string; primero: string }> = [];
  const visitar = (nodo: ts.Node): void => {
    if (ts.isCallExpression(nodo)) {
      let nombre: string | undefined;
      if (ts.isIdentifier(nodo.expression)) {
        nombre = nodo.expression.text;
      } else if (ts.isPropertyAccessExpression(nodo.expression)) {
        nombre = nodo.expression.name.text;
      }
      if (nombre && nombres.has(nombre)) {
        resultado.push({
          fichero: fuente.fileName,
          nombre,
          primero: nodo.arguments[0]?.getText() ?? "",
        });
      }
    }
    ts.forEachChild(nodo, visitar);
  };
  visitar(fuente);
  return resultado;
}

function llamadasEjecutarPython(fuente: ts.SourceFile): number {
  let cuenta = 0;
  const visitar = (nodo: ts.Node): void => {
    if (ts.isCallExpression(nodo) && ts.isIdentifier(nodo.expression) && nodo.expression.text === "ejecutarPython") {
      cuenta++;
    }
    ts.forEachChild(nodo, visitar);
  };
  visitar(fuente);
  return cuenta;
}

describe("contrato estructural", () => {
  const analizadas = fuentes();

  it("ningún literal de cadena que no sea especificador de módulo contiene .venv en e2e/", () => {
    const literalesProhibidos: string[] = [];
    for (const [fichero, fuente] of analizadas) {
      for (const literal of literales(fuente)) {
        if (literal.texto.includes(".venv")) {
          literalesProhibidos.push(`${fichero}: ${literal.texto}`);
        }
      }
    }
    expect(literalesProhibidos).toEqual([]);
  });

  it("ningún literal de cadena que no sea especificador de módulo es python/python3 del PATH", () => {
    const patron = /(^|\/)python3?(\.\d+)?$/;
    const malos: string[] = [];
    for (const [fichero, fuente] of analizadas) {
      for (const literal of literales(fuente)) {
        if (patron.test(literal.texto)) {
          malos.push(`${fichero}: ${literal.texto}`);
        }
      }
    }
    expect(malos).toEqual([]);
  });

  it("las llamadas a mecanismos de ejecución de procesos son exactamente las esperadas", () => {
    const llamadas = analizadas.flatMap(([, fuente]) => llamadasDeProceso(fuente));
    expect(llamadas).toEqual([
      { fichero: "e2e/global-setup.ts", nombre: "execFileSync", primero: '"bash"' },
      { fichero: "e2e/helpers/python.ts", nombre: "execFileSync", primero: "pythonDeLaCertificacion()" },
    ]);
  });

  it("inventario positivo exacto de llamadas a ejecutarPython", () => {
    const esperado: Record<string, number> = {
      "e2e/delegation-ceiling.spec.ts": 1,
      "e2e/diagnostico.spec.ts": 1,
      "e2e/helpers/planificador.ts": 1,
      "e2e/helpers/usuario.ts": 1,
      "e2e/inicio-version.spec.ts": 1,
      "e2e/licencia-import.spec.ts": 2,
      "e2e/licencia-periodo.spec.ts": 1,
      "e2e/licencia-revision.spec.ts": 1,
      "e2e/licencia-rotacion.spec.ts": 1,
      "e2e/licencia-sync.spec.ts": 1,
      "e2e/licencia.spec.ts": 1,
      "e2e/password-reset.spec.ts": 1,
      "e2e/roles-alta.spec.ts": 1,
    };
    const real: Record<string, number> = {};
    for (const [fichero, fuente] of analizadas) {
      const cuenta = llamadasEjecutarPython(fuente);
      if (cuenta > 0) {
        real[fichero] = cuenta;
      }
    }
    expect(real).toEqual(esperado);
  });
});

describe("el lanzador usa la autoridad y no la cambia", () => {
  let temporal: string;
  let ayudante: string;
  let marca: string;
  let original: string | undefined;

  beforeEach(() => {
    temporal = realpathSync(mkdtempSync(join(tmpdir(), "kontrol-python-")));
    ayudante = join(temporal, "ayudante.cjs");
    marca = join(temporal, "marca.txt");
    original = process.env.KONTROL_E2E_PYTHON;
  });

  afterEach(() => {
    if (original === undefined) {
      delete process.env.KONTROL_E2E_PYTHON;
    } else {
      process.env.KONTROL_E2E_PYTHON = original;
    }
    rmSync(temporal, { recursive: true, force: true });
  });

  it("sin KONTROL_E2E_PYTHON pythonDeLaCertificacion lanza y ejecutarPython no ejecuta", () => {
    delete process.env.KONTROL_E2E_PYTHON;
    writeFileSync(ayudante, `require("node:fs").writeFileSync(${JSON.stringify(marca)}, "si");`);
    expect(() => pythonDeLaCertificacion()).toThrow(/KONTROL_E2E_PYTHON/);
    expect(() => ejecutarPython([ayudante], { encoding: "utf8" })).toThrow(/KONTROL_E2E_PYTHON/);
    expect(existsSync(marca)).toBe(false);
  });

  it("con KONTROL_E2E_PYTHON relativa lanza y no ejecuta", () => {
    process.env.KONTROL_E2E_PYTHON = "python3";
    writeFileSync(ayudante, `require("node:fs").writeFileSync(${JSON.stringify(marca)}, "si");`);
    expect(() => pythonDeLaCertificacion()).toThrow(/KONTROL_E2E_PYTHON/);
    expect(() => ejecutarPython([ayudante], { encoding: "utf8" })).toThrow(/KONTROL_E2E_PYTHON/);
    expect(existsSync(marca)).toBe(false);
  });

  it("usa exactamente el intérprete indicado y preserva argumentos, cwd y env", () => {
    process.env.KONTROL_E2E_PYTHON = process.execPath;
    writeFileSync(
      ayudante,
      `process.stdout.write(JSON.stringify({argumentos: process.argv.slice(2), cwd: process.cwd(), marca: process.env.MARCA_DEL_LANZADOR ?? null, ejecutable: process.execPath}));`,
    );
    const salida = JSON.parse(
      ejecutarPython([ayudante, "uno", "dos tres"], {
        cwd: temporal,
        env: { ...process.env, MARCA_DEL_LANZADOR: "m" },
        encoding: "utf8",
      }),
    ) as { argumentos: string[]; cwd: string; marca: string | null; ejecutable: string };
    expect(salida.argumentos).toEqual(["uno", "dos tres"]);
    expect(salida.cwd).toBe(realpathSync(temporal));
    expect(salida.marca).toBe("m");
    expect(salida.ejecutable).toBe(process.execPath);
  });

  it("propaga el status de salida del ayudante", () => {
    process.env.KONTROL_E2E_PYTHON = process.execPath;
    writeFileSync(ayudante, `process.exit(7);`);
    let error: unknown;
    try {
      ejecutarPython([ayudante], { encoding: "utf8" });
    } catch (e) {
      error = e;
    }
    expect(error, "tiene que lanzar").toBeInstanceOf(Error);
    expect((error as { status?: number }).status).toBe(7);
  });
});
