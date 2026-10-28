import { readFileSync, readdirSync, statSync } from "node:fs";
import { join, relative, resolve } from "node:path";

import ts from "typescript";
import { describe, expect, it } from "vitest";

interface Ruta {
  method: string;
  path: string;
  query: string[];
}

interface Resultado {
  violaciones: string[];
  conConsulta: number;
  sinResolver: string[];
}

const SRC = resolve(process.cwd(), "src");

const EXCEPCIONES: Record<string, string> = {
  "components/AsyncCombobox.tsx":
    "La ruta llega por la propiedad searchUrl; cada uso JSX se comprueba aparte.",
};

function ficheros(dir: string): string[] {
  const salida: string[] = [];

  for (const nombre of readdirSync(dir)) {
    const ruta = join(dir, nombre);

    if (statSync(ruta).isDirectory()) {
      salida.push(...ficheros(ruta));
      continue;
    }

    const rel = relative(SRC, ruta).split("\\").join("/");
    if (
      (!nombre.endsWith(".ts") && !nombre.endsWith(".tsx")) ||
      nombre.endsWith(".test.ts") ||
      nombre.endsWith(".test.tsx") ||
      nombre.endsWith(".d.ts") ||
      rel.startsWith("tests/")
    ) {
      continue;
    }

    salida.push(ruta);
  }

  return salida;
}

function nombresDePropiedades(nodo: ts.ObjectLiteralExpression): string[] {
  const nombres: string[] = [];

  for (const propiedad of nodo.properties) {
    if (
      ts.isPropertyAssignment(propiedad) &&
      (ts.isIdentifier(propiedad.name) || ts.isStringLiteral(propiedad.name))
    ) {
      nombres.push(propiedad.name.text);
    }

    if (
      ts.isShorthandPropertyAssignment(propiedad) &&
      ts.isIdentifier(propiedad.name)
    ) {
      nombres.push(propiedad.name.text);
    }
  }

  return nombres;
}

function normalizar(p: string): string {
  return p.replace(/\{[^}]*\}/g, "{}");
}

function analizar(
  fichero: string,
  fuente: ts.SourceFile,
  rutas: Ruta[],
): Resultado {
  const violaciones: string[] = [];
  const sinResolver: string[] = [];
  let conConsulta = 0;

  const declaraciones = new Map<string, ts.Expression[]>();
  const urlSearchParams = new Map<string, Set<string>>();

  const visitarDeclaraciones = (nodo: ts.Node): void => {
    if (
      ts.isVariableDeclaration(nodo) &&
      ts.isIdentifier(nodo.name) &&
      nodo.initializer
    ) {
      const nombre = nodo.name.text;
      const previos = declaraciones.get(nombre) ?? [];
      previos.push(nodo.initializer);
      declaraciones.set(nombre, previos);

      if (
        ts.isNewExpression(nodo.initializer) &&
        ts.isIdentifier(nodo.initializer.expression) &&
        nodo.initializer.expression.text === "URLSearchParams"
      ) {
        const nombres = new Set<string>();
        const argumento = nodo.initializer.arguments?.[0];

        if (argumento && ts.isObjectLiteralExpression(argumento)) {
          for (const nombre of nombresDePropiedades(argumento)) {
            nombres.add(nombre);
          }
        }

        urlSearchParams.set(nombre, nombres);
      }
    }

    ts.forEachChild(nodo, visitarDeclaraciones);
  };

  visitarDeclaraciones(fuente);

  const visitarUsosDeURLSearchParams = (nodo: ts.Node): void => {
    if (
      ts.isCallExpression(nodo) &&
      ts.isPropertyAccessExpression(nodo.expression) &&
      (nodo.expression.name.text === "set" ||
        nodo.expression.name.text === "append") &&
      ts.isIdentifier(nodo.expression.expression)
    ) {
      const nombre = nodo.expression.expression.text;
      const nombres = urlSearchParams.get(nombre);

      if (nombres) {
        const argumento = nodo.arguments[0];

        if (argumento && ts.isStringLiteral(argumento)) {
          nombres.add(argumento.text);
        } else {
          sinResolver.push(
            `${fichero}: nombre no literal en ${nombre}.${
              nodo.expression.name.text
            }`,
          );
        }
      }
    }

    ts.forEachChild(nodo, visitarUsosDeURLSearchParams);
  };

  visitarUsosDeURLSearchParams(fuente);

  const consultaDe = (nombre: string): string => {
    const nombres = urlSearchParams.get(nombre);

    if (!nombres) {
      return "";
    }

    return [...nombres].sort().map((n) => `${n}=`).join("&");
  };

  const planoCache = new Map<ts.Node, string | null>();

  const plano = (nodo: ts.Node | undefined): string | null => {
    if (!nodo) {
      return null;
    }

    const cacheado = planoCache.get(nodo);
    if (cacheado !== undefined) {
      return cacheado;
    }

    let resultado: string | null = null;

    if (ts.isStringLiteral(nodo) || ts.isNoSubstitutionTemplateLiteral(nodo)) {
      resultado = nodo.text;
    } else if (ts.isTemplateExpression(nodo)) {
      let texto = nodo.head.text;
      for (const span of nodo.templateSpans) {
        texto += trozoExpr(span.expression);
        texto += span.literal.text;
      }
      resultado = texto;
    } else if (
      ts.isBinaryExpression(nodo) &&
      nodo.operatorToken.kind === ts.SyntaxKind.PlusToken
    ) {
      const izquierdo = plano(nodo.left);
      const derecho = plano(nodo.right);
      resultado =
        izquierdo === null || derecho === null ? null : izquierdo + derecho;
    } else if (ts.isParenthesizedExpression(nodo)) {
      resultado = plano(nodo.expression);
    } else if (ts.isConditionalExpression(nodo)) {
      const verdadero = plano(nodo.whenTrue);
      const falso = plano(nodo.whenFalse);
      resultado =
        verdadero === null || falso === null ? null : verdadero + falso;
    } else if (ts.isIdentifier(nodo)) {
      const nombre = nodo.text;
      const inicializadores = declaraciones.get(nombre);

      if (urlSearchParams.has(nombre)) {
        resultado = consultaDe(nombre);
      } else if (inicializadores) {
        resultado = inicializadores
          .map((inicializador) => plano(inicializador))
          .filter((valor): valor is string => valor !== null)
          .join("");
        resultado = resultado.length > 0 ? resultado : null;
      }
    } else if (
      ts.isCallExpression(nodo) &&
      ts.isPropertyAccessExpression(nodo.expression) &&
      nodo.expression.name.text === "toString" &&
      ts.isIdentifier(nodo.expression.expression) &&
      urlSearchParams.has(nodo.expression.expression.text)
    ) {
      resultado = consultaDe(nodo.expression.expression.text);
    }

    planoCache.set(nodo, resultado);
    return resultado;
  };

  const trozoExpr = (nodo: ts.Node): string => {
    const valor = plano(nodo);
    return valor === null ? "{}" : valor;
  };

  const contieneInterrogacionOVariableDeConsulta = (
    nodo: ts.Node,
  ): boolean => {
    if (
      ts.isTemplateHead(nodo) ||
      ts.isTemplateMiddle(nodo) ||
      ts.isTemplateTail(nodo) ||
      ts.isStringLiteral(nodo)
    ) {
      return nodo.text.includes("?");
    }

    if (ts.isIdentifier(nodo) && urlSearchParams.has(nodo.text)) {
      return true;
    }

    let encontrado = false;
    ts.forEachChild(nodo, (hijo) => {
      if (contieneInterrogacionOVariableDeConsulta(hijo)) {
        encontrado = true;
      }
    });

    return encontrado;
  };

  const comprobarRuta = (
    method: string,
    camino: string,
    consulta: string,
    linea: number,
  ): void => {
    const ruta = rutas.find(
      (r) =>
        r.method === method &&
        normalizar(r.path) === normalizar(camino),
    );

    if (!ruta) {
      violaciones.push(
        `${fichero}:${linea} ${method} ${camino}: ruta no encontrada en la instantánea`,
      );
      return;
    }

    const nombres = [
      ...new Set(
        [...consulta.matchAll(/(?:^|[?&])([A-Za-z_][A-Za-z0-9_]*)=/g)].map(
          (coincidencia) => coincidencia[1],
        ),
      ),
    ];

    for (const nombre of nombres) {
      if (!ruta.query.includes(nombre)) {
        violaciones.push(
          `${fichero}:${linea} ${method} ${camino}: «${nombre}» no declarado`,
        );
      }
    }
  };

  const visitar = (nodo: ts.Node): void => {
    if (
      ts.isCallExpression(nodo) &&
      ((ts.isIdentifier(nodo.expression) &&
        (nodo.expression.text === "apiFetch" ||
          nodo.expression.text === "descargarArchivo")) ||
        (ts.isPropertyAccessExpression(nodo.expression) &&
          nodo.expression.name.text === "apiFetch"))
    ) {
      let method = "GET";

      if (
        ts.isIdentifier(nodo.expression) &&
        nodo.expression.text === "apiFetch"
      ) {
        const segundo = nodo.arguments[1];
        if (segundo && ts.isObjectLiteralExpression(segundo)) {
          const methodProp = segundo.properties.find(
            (propiedad) =>
              ts.isPropertyAssignment(propiedad) &&
              ts.isIdentifier(propiedad.name) &&
              propiedad.name.text === "method" &&
              ts.isStringLiteral(propiedad.initializer),
          );

          if (methodProp && ts.isPropertyAssignment(methodProp)) {
            method = (methodProp.initializer as ts.StringLiteral).text.toUpperCase();
          }
        }
      }

      const argumento = nodo.arguments[0];
      if (!argumento) {
        ts.forEachChild(nodo, visitar);
        return;
      }

      const texto = plano(argumento);
      const linea =
        fuente.getLineAndCharacterOfPosition(argumento.getStart()).line + 1;

      if (texto !== null && texto.includes("?")) {
        const camino = texto.split("?")[0];
        const consulta = texto.slice(camino.length + 1);

        if (!camino.startsWith("/")) {
          sinResolver.push(`${fichero}:${linea}`);
          ts.forEachChild(nodo, visitar);
          return;
        }

        conConsulta += 1;
        comprobarRuta(method, camino, consulta, linea);
      } else if (
        texto === null &&
        contieneInterrogacionOVariableDeConsulta(argumento)
      ) {
        sinResolver.push(`${fichero}:${linea}`);
      }
    }

    if (
      (ts.isJsxSelfClosingElement(nodo) ||
        ts.isJsxOpeningElement(nodo)) &&
      ts.isIdentifier(nodo.tagName) &&
      nodo.tagName.text === "AsyncCombobox"
    ) {
      const atributos = nodo.attributes.properties;

      const searchUrl = atributos.find(
        (atributo) =>
          ts.isJsxAttribute(atributo) &&
          ts.isIdentifier(atributo.name) &&
          atributo.name.text === "searchUrl",
      );
      const itemType = atributos.some(
        (atributo) =>
          ts.isJsxAttribute(atributo) &&
          ts.isIdentifier(atributo.name) &&
          atributo.name.text === "itemType",
      );

      const linea =
        fuente.getLineAndCharacterOfPosition(nodo.getStart()).line + 1;

      if (
        !searchUrl ||
        !ts.isJsxAttribute(searchUrl) ||
        !searchUrl.initializer
      ) {
        violaciones.push(`${fichero}:${linea} searchUrl no literal`);
        ts.forEachChild(nodo, visitar);
        return;
      }

      const valor =
        ts.isStringLiteral(searchUrl.initializer)
          ? searchUrl.initializer.text
          : null;

      if (valor === null) {
        violaciones.push(`${fichero}:${linea} searchUrl no literal`);
        ts.forEachChild(nodo, visitar);
        return;
      }

      conConsulta += 1;
      const ruta = rutas.find(
        (r) => r.method === "GET" && normalizar(r.path) === normalizar(valor),
      );

      if (!ruta) {
        violaciones.push(
          `${fichero}:${linea} GET ${valor}: ruta no encontrada en la instantánea`,
        );
        ts.forEachChild(nodo, visitar);
        return;
      }

      for (const requerido of ["q", "page_size"]) {
        if (!ruta.query.includes(requerido)) {
          violaciones.push(
            `${fichero}:${linea} GET ${valor}: «${requerido}» no declarado`,
          );
        }
      }

      if (itemType && !ruta.query.includes("item_type")) {
        violaciones.push(
          `${fichero}:${linea} GET ${valor}: «item_type» no declarado`,
        );
      }
    }

    ts.forEachChild(nodo, visitar);
  };

  visitar(fuente);

  return { violaciones, conConsulta, sinResolver };
}

describe("Contrato de consulta del frontend (FR-001-271)", () => {
  const instantanea = JSON.parse(
    readFileSync(
      join(SRC, "tests", "fixtures", "openapi-routes.json"),
      "utf8",
    ),
  ) as { routes: Ruta[] };

  const resultados = ficheros(SRC).map((fichero) => {
    const rel = relative(SRC, fichero).split("\\").join("/");
    const fuente = ts.createSourceFile(
      fichero,
      readFileSync(fichero, "utf8"),
      ts.ScriptTarget.Latest,
      true,
      fichero.endsWith(".tsx") ? ts.ScriptKind.TSX : ts.ScriptKind.TS,
    );

    return { rel, resultado: analizar(rel, fuente, instantanea.routes) };
  });

  it("QC-01: no hay violaciones de consulta", () => {
    const violaciones = resultados.flatMap(
      ({ resultado }) => resultado.violaciones,
    );
    expect(violaciones).toEqual([]);
  });

  it("QC-02: no hay llamadas sin resolver fuera de las excepciones", () => {
    const sinResolver = resultados.flatMap(({ rel, resultado }) =>
      EXCEPCIONES[rel] ? [] : resultado.sinResolver,
    );
    expect(sinResolver).toEqual([]);
  });

  it("QC-03: la guarda detecta al menos 40 llamadas con consulta", () => {
    const total = resultados.reduce(
      (suma, { resultado }) => suma + resultado.conConsulta,
      0,
    );
    expect(total).toBeGreaterThanOrEqual(40);
  });

  it("QC-04: las excepciones existen como ficheros", () => {
    for (const excepcion of Object.keys(EXCEPCIONES)) {
      expect(
        ficheros(SRC).some(
          (f) => relative(SRC, f).split("\\").join("/") === excepcion,
        ),
      ).toBe(true);
    }
  });

  it("QC-05: detecta un parámetro no declarado en una cadena plana", () => {
    const texto = "const a = () => apiFetch(`/inventory/balances?q=${x}&page=1`);";
    const fuente = ts.createSourceFile(
      "sintetico.tsx",
      texto,
      ts.ScriptTarget.Latest,
      true,
      ts.ScriptKind.TSX,
    );
    const rutas: Ruta[] = [
      { method: "GET", path: "/inventory/balances", query: ["page"] },
    ];

    const resultado = analizar("sintetico.tsx", fuente, rutas);

    expect(resultado.violaciones).toHaveLength(1);
    expect(resultado.violaciones[0]).toContain("q");
  });

  it("QC-06: detecta un parámetro no declarado mediante URLSearchParams", () => {
    const texto =
      'const p = new URLSearchParams({ page: "1" }); p.set("company_id", c); apiFetch(`/approvals/inbox?${p.toString()}`);';
    const fuente = ts.createSourceFile(
      "sintetico.tsx",
      texto,
      ts.ScriptTarget.Latest,
      true,
      ts.ScriptKind.TSX,
    );
    const rutas: Ruta[] = [
      { method: "GET", path: "/approvals/inbox", query: ["page"] },
    ];

    const resultado = analizar("sintetico.tsx", fuente, rutas);

    expect(resultado.violaciones.some((v) => v.includes("company_id"))).toBe(
      true,
    );
  });

  it("QC-07: detecta un parámetro no declarado en una rama condicional", () => {
    const texto = 'apiFetch("/x?a=1" + (f ? "&zz=1" : ""));';
    const fuente = ts.createSourceFile(
      "sintetico.tsx",
      texto,
      ts.ScriptTarget.Latest,
      true,
      ts.ScriptKind.TSX,
    );
    const rutas: Ruta[] = [{ method: "GET", path: "/x", query: ["a"] }];

    const resultado = analizar("sintetico.tsx", fuente, rutas);

    expect(resultado.violaciones.some((v) => v.includes("zz"))).toBe(true);
  });

  it("QC-08: permite parámetros dinámicos de ruta", () => {
    const texto = "apiFetch(`/x/${id}?a=1`);";
    const fuente = ts.createSourceFile(
      "sintetico.tsx",
      texto,
      ts.ScriptTarget.Latest,
      true,
      ts.ScriptKind.TSX,
    );
    const rutas: Ruta[] = [
      { method: "GET", path: "/x/{item_id}", query: ["a"] },
    ];

    const resultado = analizar("sintetico.tsx", fuente, rutas);

    expect(resultado.violaciones).toEqual([]);
    expect(resultado.conConsulta).toBe(1);
  });

  it("QC-09: AsyncCombobox exige item_type cuando se declara itemType", () => {
    const texto = '<AsyncCombobox searchUrl="/s" itemType="PRODUCT" />';
    const fuente = ts.createSourceFile(
      "sintetico.tsx",
      texto,
      ts.ScriptTarget.Latest,
      true,
      ts.ScriptKind.TSX,
    );
    const rutas: Ruta[] = [
      { method: "GET", path: "/s", query: ["page_size", "q"] },
    ];

    const resultado = analizar("sintetico.tsx", fuente, rutas);

    expect(resultado.violaciones.some((v) => v.includes("item_type"))).toBe(
      true,
    );
  });

  it("QC-10: las rutas dinámicas no resueltas se anotan en sinResolver", () => {
    const texto = "apiFetch(`${base}?q=${x}`);";
    const fuente = ts.createSourceFile(
      "sintetico.tsx",
      texto,
      ts.ScriptTarget.Latest,
      true,
      ts.ScriptKind.TSX,
    );
    const rutas: Ruta[] = [];

    const resultado = analizar("sintetico.tsx", fuente, rutas);

    expect(resultado.violaciones).toEqual([]);
    expect(resultado.sinResolver).toHaveLength(1);
  });
});
