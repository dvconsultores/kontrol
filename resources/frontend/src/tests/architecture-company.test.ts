/**
 * Pruebas de arquitectura del contexto de empresa (ARCH-MC-001, N6).
 *
 * Buscan por estructura, sobre el código real, lo que ninguna prueba funcional
 * ve: una pantalla que llame al servidor por fuera del cliente central, una
 * consulta que caiga en el tenant cuando falta la empresa, o un formulario que
 * lea la empresa al enviar en vez de al abrirse.
 *
 * No comprueban nombres de variables ni comentarios: un comentario correcto se
 * puede escribir encima de un defecto.
 */
import { readFileSync, readdirSync, statSync } from "node:fs";
import { join } from "node:path";

import { describe, expect, it } from "vitest";

const RAIZ = join(__dirname, "..");

function fuentes(dir: string = RAIZ): string[] {
  const salida: string[] = [];
  for (const entrada of readdirSync(dir)) {
    if (entrada === "node_modules" || entrada.startsWith(".")) continue;
    const ruta = join(dir, entrada);
    if (statSync(ruta).isDirectory()) {
      salida.push(...fuentes(ruta));
    } else if (/\.tsx?$/.test(entrada) && !/\.test\.tsx?$/.test(entrada)) {
      salida.push(ruta);
    }
  }
  return salida;
}

const ARCHIVOS = fuentes().map((ruta) => ({
  ruta: ruta.slice(RAIZ.length + 1),
  texto: readFileSync(ruta, "utf8"),
}));

/** El cliente central es el único autorizado a hablar con la API. */
const CLIENTE_CENTRAL = "api/client.ts";

describe("arquitectura del contexto de empresa", () => {
  it("ninguna pantalla llama a la API por fuera del cliente central", () => {
    // Una llamada directa se saltaría la cabecera de empresa sin que nadie lo
    // notara: respondería con normalidad, en la empresa equivocada o en
    // ninguna.
    const culpables = ARCHIVOS.filter(({ ruta, texto }) => {
      if (ruta === CLIENTE_CENTRAL) return false;
      // `fetch(` a un endpoint propio. Se permiten URLs absolutas externas y
      // el `fetch` que los propios tests sustituyen.
      const llamadas = texto.match(/\bfetch\s*\(\s*[`"']\/api\//g) ?? [];
      const axios = texto.match(/\baxios\s*[.(]/g) ?? [];
      return llamadas.length > 0 || axios.length > 0;
    }).map((a) => a.ruta);

    expect(culpables, `llamadas fuera del cliente central: ${culpables.join(", ")}`).toEqual([]);
  });

  it("nadie usa el tenant como empresa cuando falta la empresa", () => {
    // El defecto original de KONTROL, escrito en una línea: `company ?? tenant`.
    // Con una empresa por tenant era invisible; con dos, guarda en la que no es.
    const patron = /(company[_A-Za-z]*)\s*(\?\?|\|\|)\s*[A-Za-z_.]*tenant/i;
    const culpables = ARCHIVOS.filter(({ texto }) => patron.test(texto)).map((a) => a.ruta);
    expect(culpables, `hay un repliegue de empresa a tenant: ${culpables.join(", ")}`).toEqual([]);
  });

  it("la empresa activa no se guarda solo en localStorage", () => {
    // `localStorage` se comparte entre pestañas del mismo origen. Si fuera la
    // única fuente del contexto operativo, cambiar de empresa en una pestaña
    // cambiaría la otra por debajo, con un formulario a medio llenar dentro.
    const contexto = ARCHIVOS.find((a) => a.ruta === "app/contexts/CompanyContext.tsx");
    expect(contexto).toBeDefined();
    expect(contexto!.texto).toContain("sessionStorage");
  });

  it("el cliente central resuelve la empresa en un único punto", () => {
    const cliente = ARCHIVOS.find((a) => a.ruta === CLIENTE_CENTRAL)!;
    // Exactamente una asignación de la cabecera en todo el frontend.
    const asignaciones = ARCHIVOS.flatMap(({ ruta, texto }) =>
      (texto.match(/headers\[[^\]]*COMPANY_HEADER[^\]]*\]\s*=|["']X-Kontrol-Company["']\s*\]\s*=/g) ?? [])
        .map(() => ruta));
    expect(asignaciones).toEqual([CLIENTE_CENTRAL]);
    expect(cliente.texto).toContain("setCompanyResolver");
  });

  it("la identidad de las consultas de empresa incorpora la empresa", () => {
    // Invalidar no basta: invalidar marca lo viejo como caducado, separar hace
    // que lo de A y lo de B nunca hayan sido la misma entrada.
    const main = ARCHIVOS.find((a) => a.ruta === "main.tsx")!;
    expect(main.texto).toContain("queryKeyHashFn");
    expect(main.texto).toContain("crearHashDeClave");
  });

  it("el cambio de empresa descarta lo que era de la anterior", () => {
    const shell = ARCHIVOS.find((a) => a.ruta === "app/AppShell.tsx")!;
    expect(shell.texto).toContain("removeQueries");
    expect(shell.texto).toContain("cancelQueries");
  });

  it("el formulario fija su empresa al abrirse, no al enviar", () => {
    const guarda = ARCHIVOS.find((a) => a.ruta === "app/company/useCompanyScope.ts")!;
    // La empresa vive en una referencia que se congela en la primera
    // renderización: leerla al enviar es justamente el error que evita.
    expect(guarda.texto).toContain("useRef");
    expect(guarda.texto).toContain("CompanyMismatchError");
    // Y no se recalcula en cada render a partir de la activa.
    expect(guarda.texto).not.toMatch(/abierta\.current\s*=\s*activeCompanyId/);
  });

  it("las pantallas de negocio no se pintan sin empresa resuelta", () => {
    const shell = ARCHIVOS.find((a) => a.ruta === "app/AppShell.tsx")!;
    expect(shell.texto).toMatch(/estado\s*!==\s*["']READY["']/);
  });

  /** Ficheros que convierten en archivo contenido ya obtenido por el cliente central: construyen el Blob en memoria
   *  y no hablan con la API. Lista cerrada; añadir uno exige justificarlo aquí. */
  const DESCARGAS_DE_CONTENIDO_LOCAL = new Set(["lib/solicitud-de-activacion.ts"]);

  it("las descargas también llevan el contexto de empresa", () => {
    // Una descarga es donde más fácil se pierde el contexto: basta con abrir
    // una URL directa o poner un `href` y el navegador va sin la cabecera. Aquí
    // se comprueba que el binario se pide por el cliente central y solo después
    // se convierte en enlace local.
    const descargan = ARCHIVOS.filter(({ texto }) => texto.includes("createObjectURL"));
    const descarganDelServidor = descargan.filter(({ ruta }) => !DESCARGAS_DE_CONTENIDO_LOCAL.has(ruta));
    expect(descarganDelServidor.length).toBeGreaterThan(0);
    for (const { ruta, texto } of descarganDelServidor) {
      const tipoBlob = texto.includes('responseType: "blob"');
      const tipoArchivo = texto.includes('responseType: "archivo"');
      expect(tipoBlob || tipoArchivo, `${ruta} construye la descarga sin pasar por el cliente`).toBe(
        true);
      expect(texto, `${ruta} no usa el cliente central`).toContain("apiFetch");
    }
    for (const ruta of DESCARGAS_DE_CONTENIDO_LOCAL) {
      const fichero = ARCHIVOS.find(({ ruta: rutaArchivo }) => rutaArchivo === ruta);
      expect(fichero, `La descarga local ${ruta} no existe en ARCHIVOS`).toBeDefined();
      if (!fichero) continue;
      const { texto } = fichero;
      expect(texto, `${ruta} debe construir el Blob en memoria`).toContain("new Blob(");
      expect(texto, `${ruta} no debe hacer fetch`).not.toContain("fetch(");
      expect(texto, `${ruta} no debe usar apiFetch`).not.toContain("apiFetch");
      expect(texto, `${ruta} no debe usar XMLHttpRequest`).not.toContain("XMLHttpRequest");
      expect(texto, `${ruta} no debe usar axios`).not.toContain("axios");
      expect(texto, `${ruta} no debe llamar a /api/`).not.toMatch(/[`"']\/api\//);
    }
  });

  it("ningún enlace de descarga apunta directamente a la API", () => {
    // `<a href="/api/...">` o `window.location = "/api/..."` saldrían sin
    // cabecera de empresa y sin token.
    const culpables = ARCHIVOS.filter(({ texto }) =>
      /href\s*=\s*[{"'`]\s*[`"']?\/api\//.test(texto) ||
      /window\.location[^=]*=\s*[`"']\/api\//.test(texto)).map((a) => a.ruta);
    expect(culpables, `enlaces directos a la API: ${culpables.join(", ")}`).toEqual([]);
  });

  it("ningún fichero fuera del cliente central escribe una URL /api/v1/ propia", () => {
    // Una URL a la API construida a mano sale sin cabecera de empresa ni token,
    // aunque se asigne a un `href` mediante una variable.
    const culpables = ARCHIVOS.filter(({ ruta, texto }) =>
      ruta !== CLIENTE_CENTRAL && texto.includes("/api/v1/")).map(({ ruta }) => ruta);
    expect(culpables, `URLs /api/v1/ fuera del cliente central: ${culpables.join(", ")}`).toEqual(
      []);
  });
});
