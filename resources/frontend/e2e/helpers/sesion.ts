/**
 * Sesión con MFA para las suites E2E (OQ-MFA-3).
 *
 * El producto exige ahora un segundo factor para las identidades de las suites.
 * Este módulo recorre el flujo real de la API —alta por desafío o verificación
 * TOTP— sin ningún atajo del producto, sin esperar pasos TOTP y sin reintentos.
 *
 * Decisión OQ-MFA-3 = A: una identidad privilegiada por worker. La siembra crea,
 * para cada usuario base, seis clones `<base>_w0` … `<base>_w5` con los mismos
 * roles y el mismo alcance de empresa. El worker se identifica con
 * `identidad(base)` y `test.info().parallelIndex`.
 *
 * El secreto TOTP es sintético y se genera en ejecución. Vive en memoria del
 * worker y en un fichero 0600 del estado efímero de la corrida para sobrevivir
 * al reinicio de un worker; nunca en el repositorio, ni en la evidencia, ni en
 * la consola.
 *
 * Las pruebas cuyo objeto es el arnés de sesión usan `@playwright/test`
 * directamente; las demás importan `test`/`expect` de este módulo.
 */
import { createHmac } from "node:crypto";
import { existsSync, readFileSync, writeFileSync } from "node:fs";
import { resolve } from "node:path";
import {
  expect,
  request as solicitudes,
  test as testBase,
  type APIRequestContext,
  type Page,
} from "@playwright/test";

const API = process.env.KONTROL_E2E_API ?? "http://127.0.0.1:8000/api/v1";
const BASE_URL = process.env.KONTROL_E2E_BASE_URL ?? "http://127.0.0.1:5173";
const TENANT = process.env.KONTROL_E2E_TENANT ?? "DEMO";
const PASSWORD = process.env.KONTROL_E2E_PASSWORD ?? "";

const MFA_DIR = process.env.KONTROL_E2E_MFA_DIR;

interface EstadoSesion {
  clave: string | null;
  ultimoPaso: number | null;
  cookie: string | null;
  token: string | null;
  tokenEn: number | null;
  reauthEn: number | null;
}

const memoria = new Map<string, EstadoSesion>();
const enElNavegador = new Map<string, string>();

/**
 * Decodifica una clave base32 RFC 4648 (mayúsculas, sin relleno; ignora
 * espacios) y calcula el código TOTP RFC 6238 (SHA-1, 6 dígitos, periodo 30 s).
 * `instanteMs` permite fijar el contador para los vectores de prueba.
 */
export function codigoTotp(claveBase32: string, instanteMs: number): string {
  const MASCARA_BASE32 = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567";
  const normalizada = claveBase32.toUpperCase().replace(/ /g, "");
  const bits: number[] = [];
  let acumulador = 0;
  let longitud = 0;

  for (const caracter of normalizada) {
    const valor = MASCARA_BASE32.indexOf(caracter);
    if (valor === -1) {
      throw new Error(`carácter no válido en clave base32: ${caracter}`);
    }
    acumulador = (acumulador << 5) | valor;
    longitud += 5;
    if (longitud >= 8) {
      bits.push((acumulador >>> (longitud - 8)) & 0xff);
      longitud -= 8;
    }
  }

  const contador = Math.floor(instanteMs / 1000 / 30);
  const mensaje = Buffer.alloc(8);
  mensaje.writeBigUInt64BE(BigInt(contador));

  const mac = createHmac("sha1", Buffer.from(bits));
  mac.update(mensaje);
  const resumen = mac.digest();
  const desplazamiento = resumen[resumen.length - 1] & 0x0f;
  const binario = (resumen.readUInt32BE(desplazamiento) & 0x7fffffff).toString();
  return binario.slice(-6).padStart(6, "0");
}

/**
 * Identidad privilegiada del worker actual. La siembra crea seis por usuario
 * base (una por `parallelIndex` 0..5).
 */
export function identidad(baseUsuario: string, indice: number = testBase.info().parallelIndex): string {
  if (!Number.isInteger(indice) || indice < 0 || indice > 5) {
    throw new Error(
      `indice de worker ${indice} fuera de 0..5: la siembra crea seis identidades por usuario base`,
    );
  }
  return `${baseUsuario}_w${indice}`;
}

function claveEstado(tenant: string, usuario: string): string {
  return `${tenant}__${usuario}`;
}

function rutaEstado(tenant: string, usuario: string): string {
  if (!MFA_DIR) {
    throw new Error(
      "KONTROL_E2E_MFA_DIR es obligatoria para la sesión con MFA: la corrida canónica la define " +
      "en un directorio 0700 del estado efímero y la borra al terminar",
    );
  }
  return resolve(MFA_DIR, `${claveEstado(tenant, usuario)}.json`);
}

function estadoVacio(): EstadoSesion {
  return { clave: null, ultimoPaso: null, cookie: null, token: null, tokenEn: null, reauthEn: null };
}

function leerEstado(tenant: string, usuario: string): EstadoSesion {
  const clave = claveEstado(tenant, usuario);
  const enMemoria = memoria.get(clave);
  if (enMemoria) {
    return { ...enMemoria };
  }

  if (!MFA_DIR) {
    throw new Error(
      "KONTROL_E2E_MFA_DIR es obligatoria para la sesión con MFA: la corrida canónica la define " +
      "en un directorio 0700 del estado efímero y la borra al terminar",
    );
  }
  const ruta = rutaEstado(tenant, usuario);
  if (!existsSync(ruta)) {
    return estadoVacio();
  }
  const contenido = JSON.parse(readFileSync(ruta, "utf8")) as Partial<EstadoSesion>;
  const estado: EstadoSesion = {
    clave: typeof contenido.clave === "string" ? contenido.clave : null,
    ultimoPaso: typeof contenido.ultimoPaso === "number" ? contenido.ultimoPaso : null,
    cookie: typeof contenido.cookie === "string" ? contenido.cookie : null,
    token: typeof contenido.token === "string" ? contenido.token : null,
    tokenEn: typeof contenido.tokenEn === "number" ? contenido.tokenEn : null,
    reauthEn: typeof contenido.reauthEn === "number" ? contenido.reauthEn : null,
  };
  memoria.set(clave, estado);
  return { ...estado };
}

function guardarEstado(tenant: string, usuario: string, estado: EstadoSesion): void {
  memoria.set(claveEstado(tenant, usuario), estado);
  const ruta = rutaEstado(tenant, usuario);
  writeFileSync(ruta, JSON.stringify(estado), { mode: 0o600 });
}

/**
 * Devuelve un paso TOTP libre para el usuario. El servidor acepta el paso
 * actual y ±1, y rechaza uno <= al último usado. El arnés no espera: si el
 * mismo paso ya se usó, emplea el siguiente (+1). Si el último paso usado es
 * mayor que el actual, no hay paso libre sin esperar.
 */
function pasoLibre(estado: EstadoSesion, usuario: string): number {
  const actual = Math.floor(Date.now() / 30000);
  const ultimo = estado.ultimoPaso;
  if (ultimo === null || actual > ultimo) {
    return actual;
  }
  if (ultimo === actual) {
    return actual + 1;
  }
  throw new Error(
    `no hay paso TOTP libre para ${usuario} (último ${ultimo}, actual ${actual}): ` +
    "el arnés no espera; esta prueba inicia sesión con el mismo usuario demasiadas veces",
  );
}

function cookieDe(respuesta: Awaited<ReturnType<APIRequestContext["post"]>>): string {
  const cabeceras = respuesta.headersArray();
  for (const cabecera of cabeceras) {
    if (cabecera.name.toLowerCase() === "set-cookie") {
      const valor = cabecera.value;
      if (valor.startsWith("kontrol_refresh=")) {
        const partes = valor.split(";");
        return partes[0].slice("kontrol_refresh=".length);
      }
    }
  }
  throw new Error("la respuesta no incluye la cookie kontrol_refresh");
}

function errorDeMFA(respuesta: { status: number; json: unknown }, operacion: string, usuario: string): Error {
  const codigo =
    typeof respuesta.json === "object" &&
    respuesta.json !== null &&
    "code" in respuesta.json &&
    typeof respuesta.json.code === "string"
      ? respuesta.json.code
      : "sin código";
  return new Error(`${operacion} de ${usuario}: estado ${respuesta.status}, código ${codigo}`);
}

async function conContexto<T>(fn: (r: APIRequestContext) => Promise<T>): Promise<T> {
  const r = await solicitudes.newContext();
  try {
    return await fn(r);
  } finally {
    await r.dispose();
  }
}

/** Extrae el `X-Request-ID` de una respuesta autenticada o lanza. */
function rastroDe(respuesta: Awaited<ReturnType<APIRequestContext["post"]>>, usuario: string): string {
  const rastro = respuesta.headers()["x-request-id"];
  if (!rastro) {
    throw new Error(`login de ${usuario}: la respuesta no incluye la cabecera X-Request-ID`);
  }
  return rastro;
}

/**
 * Inicia sesión por el flujo real del producto y deja el estado listo para
 * `sesionApi`. El login deja la reautenticación hecha.
 */
export async function iniciarSesion(
  usuario: string,
  opciones?: { tenant?: string; password?: string },
): Promise<{ token: string; cookie: string; rastro: string }> {
  return conContexto(async (request) => {
    const tenant = opciones?.tenant ?? TENANT;
    const password = opciones?.password ?? PASSWORD;
    let estado = leerEstado(tenant, usuario);

    const respuestaLogin = await request.post(`${API}/auth/login`, {
      data: { tenant_code: tenant, username: usuario, password },
    });
    if (!respuestaLogin.ok()) {
      throw errorDeMFA(
        { status: respuestaLogin.status(), json: await respuestaLogin.json().catch(() => null) },
        `login`,
        usuario,
      );
    }
    const cuerpoLogin = (await respuestaLogin.json()) as {
      status?: string;
      challenge_token?: string;
      access_token?: string;
      code?: string;
    };
    const estadoLogin = cuerpoLogin.status;

    if (estadoLogin === "AUTHENTICATED") {
      const token = cuerpoLogin.access_token;
      if (!token) {
        throw new Error(`login de ${usuario}: respuesta AUTHENTICATED sin access_token`);
      }
      estado.token = token;
      estado.tokenEn = Date.now();
      estado.cookie = cookieDe(respuestaLogin);
      estado.reauthEn = Date.now();
      guardarEstado(tenant, usuario, estado);
      estado = leerEstado(tenant, usuario);
      return { token, cookie: estado.cookie ?? "", rastro: rastroDe(respuestaLogin, usuario) };
    }

    if (!cuerpoLogin.challenge_token) {
      throw errorDeMFA({ status: 200, json: cuerpoLogin }, `login`, usuario);
    }

    if (estadoLogin === "MFA_ENROLLMENT_REQUIRED") {
      const respuestaAlta = await request.post(`${API}/auth/mfa/enrollment`, {
        data: { challenge_token: cuerpoLogin.challenge_token },
      });
      if (!respuestaAlta.ok()) {
        throw errorDeMFA(
          { status: respuestaAlta.status(), json: await respuestaAlta.json().catch(() => null) },
          `enrollment`,
          usuario,
        );
      }
      const cuerpoAlta = (await respuestaAlta.json()) as { manual_key?: string };
      if (!cuerpoAlta.manual_key) {
        throw new Error(`enrollment de ${usuario}: respuesta sin manual_key`);
      }
      estado.clave = cuerpoAlta.manual_key;
      estado.ultimoPaso = null;
      guardarEstado(tenant, usuario, estado);
      estado = leerEstado(tenant, usuario);

      const pasoAlta = pasoLibre(estado, usuario);
      const codigoAlta = codigoTotp(estado.clave ?? "", pasoAlta * 30000);
      const respuestaConfirmacion = await request.post(`${API}/auth/mfa/enrollment/confirm`, {
        data: { challenge_token: cuerpoLogin.challenge_token, code: codigoAlta },
      });
      if (!respuestaConfirmacion.ok()) {
        throw errorDeMFA(
          { status: respuestaConfirmacion.status(), json: await respuestaConfirmacion.json().catch(() => null) },
          `confirm`,
          usuario,
        );
      }
      const cuerpoConfirmacion = (await respuestaConfirmacion.json()) as { access_token?: string };
      if (!cuerpoConfirmacion.access_token) {
        throw new Error(`confirm de ${usuario}: respuesta sin access_token`);
      }
      estado.ultimoPaso = pasoAlta;
      estado.token = cuerpoConfirmacion.access_token;
      estado.tokenEn = Date.now();
      estado.cookie = cookieDe(respuestaConfirmacion);
      estado.reauthEn = Date.now();
      guardarEstado(tenant, usuario, estado);
      estado = leerEstado(tenant, usuario);
      return { token: estado.token ?? "", cookie: estado.cookie ?? "", rastro: rastroDe(respuestaConfirmacion, usuario) };
    }

    if (estadoLogin === "MFA_REQUIRED") {
      if (!estado.clave) {
        throw new Error(
          `${usuario} ya tiene factor y este proceso no conoce su clave; ` +
          "el arnés no espera ni salta el MFA",
        );
      }
      const pasoVerificacion = pasoLibre(estado, usuario);
      const codigoVerificacion = codigoTotp(estado.clave, pasoVerificacion * 30000);
      const respuestaVerificacion = await request.post(`${API}/auth/mfa/verify`, {
        data: { challenge_token: cuerpoLogin.challenge_token, code: codigoVerificacion },
      });
      if (!respuestaVerificacion.ok()) {
        throw errorDeMFA(
          { status: respuestaVerificacion.status(), json: await respuestaVerificacion.json().catch(() => null) },
          `verify`,
          usuario,
        );
      }
      const cuerpoVerificacion = (await respuestaVerificacion.json()) as { access_token?: string };
      if (!cuerpoVerificacion.access_token) {
        throw new Error(`verify de ${usuario}: respuesta sin access_token`);
      }
      estado.ultimoPaso = pasoVerificacion;
      estado.token = cuerpoVerificacion.access_token;
      estado.tokenEn = Date.now();
      estado.cookie = cookieDe(respuestaVerificacion);
      estado.reauthEn = Date.now();
      guardarEstado(tenant, usuario, estado);
      estado = leerEstado(tenant, usuario);
      return { token: estado.token ?? "", cookie: estado.cookie ?? "", rastro: rastroDe(respuestaVerificacion, usuario) };
    }

    throw errorDeMFA({ status: 200, json: cuerpoLogin }, `login`, usuario);
  });
}

/** Como `sesionApi`, para un usuario creado en la prueba (sin la identidad del worker). */
export async function sesionDeUsuario(
  usuario: string,
  opciones?: { tenant?: string; empresa?: string; password?: string },
): Promise<{ token: string; headers: Record<string, string> }> {
  const password = opciones?.password ?? PASSWORD;
  return conContexto(async (request) => {
    const tenant = opciones?.tenant ?? TENANT;
    let estado = leerEstado(tenant, usuario);

    const valoraAhora = () => {
      const ahora = Date.now();
      const tokenVale =
        estado.token !== null && estado.tokenEn !== null && ahora - estado.tokenEn < 10 * 60 * 1000;
      return { ahora, tokenVale };
    };

    let { ahora, tokenVale } = valoraAhora();

    if (!tokenVale && estado.cookie) {
      const respuestaRefresh = await request.post(`${API}/auth/refresh`, {
        headers: { Cookie: `kontrol_refresh=${estado.cookie}` },
      });
      if (respuestaRefresh.ok()) {
        const cuerpoRefresh = (await respuestaRefresh.json()) as { access_token?: string };
        if (!cuerpoRefresh.access_token) {
          throw new Error(`refresh de ${usuario}: respuesta sin access_token`);
        }
        estado.token = cuerpoRefresh.access_token;
        estado.tokenEn = Date.now();
        estado.cookie = cookieDe(respuestaRefresh);
        guardarEstado(tenant, usuario, estado);
        estado = leerEstado(tenant, usuario);
      } else if (respuestaRefresh.status() === 401) {
        await iniciarSesion(usuario, { tenant, password });
        estado = leerEstado(tenant, usuario);
      } else {
        throw errorDeMFA(
          { status: respuestaRefresh.status(), json: await respuestaRefresh.json().catch(() => null) },
          `refresh`,
          usuario,
        );
      }
      ({ ahora, tokenVale } = valoraAhora());
    }

    if (!estado.token || !estado.tokenEn) {
      await iniciarSesion(usuario, { tenant, password });
      estado = leerEstado(tenant, usuario);
      ({ ahora, tokenVale } = valoraAhora());
    }

    if (estado.reauthEn === null || ahora - estado.reauthEn > 120 * 1000) {
      const pasoReauth = pasoLibre(estado, usuario);
      const codigoReauth = estado.clave === null ? null : codigoTotp(estado.clave, pasoReauth * 30000);
      const datosReauth: { password: string; code?: string } = { password };
      if (codigoReauth !== null) {
        datosReauth.code = codigoReauth;
      }
      const respuestaReauth = await request.post(`${API}/auth/reauth`, {
        headers: { Authorization: `Bearer ${estado.token}` },
        data: datosReauth,
      });
      if (!respuestaReauth.ok()) {
        throw errorDeMFA(
          { status: respuestaReauth.status(), json: await respuestaReauth.json().catch(() => null) },
          `reauth`,
          usuario,
        );
      }
      estado.ultimoPaso = pasoReauth;
      estado.reauthEn = Date.now();
      guardarEstado(tenant, usuario, estado);
      estado = leerEstado(tenant, usuario);
    }

    return {
      token: estado.token ?? "",
      headers: {
        Authorization: `Bearer ${estado.token ?? ""}`,
        ...(opciones?.empresa ? { "X-Kontrol-Company": opciones.empresa } : {}),
      },
    };
  });
}

/**
 * Devuelve token y cabeceras para una identidad del worker, refrescando la
 * sesión si el token va a caducar o la cookie lo permite, y reautenticando si
 * la reautenticación ha expirado.
 */
export async function sesionApi(
  baseUsuario: string,
  opciones?: { tenant?: string; empresa?: string },
): Promise<{ token: string; headers: Record<string, string> }> {
  return sesionDeUsuario(identidad(baseUsuario), opciones);
}

/** Como `entrar`, para un usuario creado en la prueba (sin la identidad del worker). */
export async function entrarComoUsuario(
  page: Page,
  usuario: string,
  opciones?: { tenant?: string; ruta?: string; password?: string },
): Promise<void> {
  const tenant = opciones?.tenant ?? TENANT;
  const password = opciones?.password ?? PASSWORD;
  let estado = leerEstado(tenant, usuario);

  await sesionDeUsuario(usuario, { tenant, password });
  estado = leerEstado(tenant, usuario);

  if (!estado.cookie) {
    const sesion = await iniciarSesion(usuario, { tenant, password });
    estado = leerEstado(tenant, usuario);
    estado.cookie = sesion.cookie;
    estado.token = sesion.token;
    guardarEstado(tenant, usuario, estado);
    estado = leerEstado(tenant, usuario);
  }

  const cookie = estado.cookie;
  if (!cookie) {
    throw new Error(`sesión de interfaz de ${usuario}: sin cookie para el navegador`);
  }

  const dominio = new URL(BASE_URL).hostname;
  await page.context().addCookies([
    {
      name: "kontrol_refresh",
      value: cookie,
      domain: dominio,
      path: "/api/v1/auth",
      httpOnly: true,
      sameSite: "Lax",
    },
  ]);

  estado = leerEstado(tenant, usuario);
  estado.cookie = null;
  guardarEstado(tenant, usuario, estado);
  enElNavegador.set(claveEstado(tenant, usuario), usuario);

  const refresco = page.waitForResponse((respuesta) => {
    return respuesta.url().includes("/auth/refresh") && respuesta.status() === 200;
  });
  await page.goto(opciones?.ruta ?? "/");
  await refresco;
  if (new URL(page.url()).pathname === "/login") {
    throw new Error(`sesión de interfaz de ${usuario}: la aplicación quedó en /login`);
  }
}

/**
 * Entra en la interfaz sin pasar por el formulario: obtiene la sesión por API
 * y coloca la cookie en el navegador. El navegador es el dueño de la cadena;
 * al terminar cada prueba, `test` devuelve la cookie al estado.
 */
export async function entrar(page: Page, baseUsuario: string, opciones?: { tenant?: string; ruta?: string }): Promise<void> {
  return entrarComoUsuario(page, identidad(baseUsuario), opciones);
}

interface ExtrasSesion {
  _cadenaDeSesion: void;
}

export const test = testBase.extend<ExtrasSesion>({
  _cadenaDeSesion: [
    async ({ context }, use) => {
      await use();
      const cookies = await context.cookies();
      const dominioEsperado = new URL(BASE_URL).hostname;
      for (const [clave] of enElNavegador.entries()) {
        const cookie = cookies.find(
          (c) => c.name === "kontrol_refresh" && c.value && c.domain === dominioEsperado,
        );
        if (cookie) {
          const [tenant, nombreUsuario] = clave.split("__");
          const estado = leerEstado(tenant, nombreUsuario);
          estado.cookie = cookie.value;
          guardarEstado(tenant, nombreUsuario, estado);
        }
        enElNavegador.delete(clave);
      }
    },
    { auto: true },
  ],
});

export { expect };

/**
 * Para las pruebas cuyo objeto es el formulario de acceso: asegura antes el
 * factor con `sesionApi` (sin tocar el navegador) y recorre el formulario real
 * con el código TOTP.
 */
export async function entrarPorFormulario(page: Page, baseUsuario: string, opciones?: { tenant?: string }): Promise<void> {
  const tenant = opciones?.tenant ?? TENANT;
  const usuario = identidad(baseUsuario);
  await sesionApi(baseUsuario, { tenant });
  let estado = leerEstado(tenant, usuario);

  await page.goto("/login");
  await page.getByLabel(/Empresa \(código\)/).fill(tenant);
  await page.getByLabel(/Usuario/).fill(usuario);
  await page.getByLabel(/Contraseña/).fill(PASSWORD);
  await page.getByRole("button", { name: "Iniciar sesión" }).click();
  await page.getByLabel(/Código de verificación/).waitFor({ state: "visible" });

  const paso = pasoLibre(estado, usuario);
  const codigo = codigoTotp(estado.clave ?? "", paso * 30000);
  await page.getByLabel(/Código de verificación/).fill(codigo);
  await page.getByRole("button", { name: "Verificar" }).click();
  await page.waitForURL((url) => url.pathname !== "/login", { timeout: 20000 });

  estado = leerEstado(tenant, usuario);
  estado.ultimoPaso = paso;
  guardarEstado(tenant, usuario, estado);
}
