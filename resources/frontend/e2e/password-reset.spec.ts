/**
 * E2E-RESET · Recuperación de contraseña por la interfaz real.
 *
 * Cubre el ciclo completo de recuperación de contraseña tal como lo vive una
 * persona: solicitud desde `/reset-password`, emisión del código por la orden
 * local del servidor (canal de confianza), restablecimiento de la contraseña,
 * efecto en las sesiones anteriores, exigencia continuada de MFA, consumo único
 * del código, invalidación por código posterior, accesibilidad y 320 px.
 *
 * El código de recuperación lo emite la orden local:
 * `python -m app.modules.identity_access.password_breakglass ... --salida ruta`,
 * en un directorio efímero 0700 fuera de la evidencia. Se lee con
 * `readFileSync` y se borra inmediatamente con `unlinkSync`; nunca se imprime
 * ni se deja en disco. Trazas, capturas y vídeo están apagados para que el
 * código no quede en la evidencia.
 *
 * La caducidad de 15 minutos la cubren las pruebas de backend y vitest porque
 * la E2E no controla el reloj del servidor ni puede esperar.
 */
import { readFileSync, unlinkSync } from "node:fs";
import { join, resolve } from "node:path";

import AxeBuilder from "@axe-core/playwright";
import { type APIRequestContext, type Page } from "@playwright/test";

import { expect, iniciarSesion, sesionApi, sesionDeUsuario, test } from "./helpers/sesion";
import { ejecutarPython } from "./helpers/python";

test.use({ trace: "off", screenshot: "off", video: "off" });

const API = process.env.KONTROL_E2E_API ?? "http://127.0.0.1:8000/api/v1";
const BACKEND = resolve(process.cwd(), "..", "backend");
const TENANT = "DEMO";
const PASSWORD = process.env.KONTROL_E2E_PASSWORD ?? "";
const NUEVA_CLAVE = "NuevaClave2026x";
const OTRA_CLAVE = "OtraClave2026xy";

const marcas = new Set<string>();

function marcaUnica(): string {
  let marca = "";
  do {
    marca = `${Date.now().toString(36)}${Math.random().toString(36).slice(2, 6)}`;
  } while (marcas.has(marca));
  marcas.add(marca);
  return marca;
}

type UsuarioCreado = {
  username: string;
  password: string;
};

async function crearUsuario(
  request: APIRequestContext,
  caso: string,
  { privilegiado }: { privilegiado: boolean },
): Promise<UsuarioCreado> {
  // Crea usuarios privilegiados de todo el tenant: hace falta autoridad de todo el tenant (techo de delegación, Spec 003).
  const admin = await sesionApi("admintenant", { tenant: TENANT });
  const username = `reset-${caso}-${marcaUnica()}`;

  const createResp = await request.post(`${API}/users`, {
    headers: admin.headers,
    data: {
      username,
      email: `${username}@example.com`,
      password: PASSWORD,
      must_change_password: false,
    },
  });
  expect(createResp.ok(), `crear usuario ${username}`).toBe(true);
  const user = (await createResp.json()) as { id: string };

  if (privilegiado) {
    const rolesResp = await request.get(`${API}/roles`, { headers: admin.headers });
    expect(rolesResp.ok(), "listar roles").toBe(true);
    const roles = (await rolesResp.json()) as { items: Array<{ id: string; code: string }> };
    const adminRole = roles.items.find((r) => r.code === "ADMIN");
    expect(adminRole, "rol ADMIN").toBeDefined();

    const assignResp = await request.post(`${API}/users/${user.id}/roles`, {
      headers: admin.headers,
      data: { role_id: adminRole?.id, company_id: null },
    });
    expect(assignResp.ok(), `asignar rol ADMIN a ${username}`).toBe(true);
  }

  return { username, password: PASSWORD };
}

function emitirCodigo(usuario: string): string {
  const dir = process.env.KONTROL_E2E_MFA_DIR;
  if (!dir) {
    throw new Error("KONTROL_E2E_MFA_DIR es obligatoria para emitir el código de recuperación");
  }
  const ruta = join(dir, `reset-${marcaUnica()}.txt`);
  ejecutarPython(
    [
      "-m",
      "app.modules.identity_access.password_breakglass",
      "--tenant",
      TENANT,
      "--username",
      usuario,
      "--confirm",
      usuario,
      "--salida",
      ruta,
    ],
    {
      cwd: BACKEND,
      env: {
        ...process.env,
        KONTROL_DB_URL: process.env.KONTROL_E2E_DB_URL,
        PYTHONPATH: BACKEND,
      },
      encoding: "utf8",
      timeout: 60_000,
    },
  );
  const codigo = readFileSync(ruta, "utf8").trim();
  unlinkSync(ruta);
  return codigo;
}

async function abrirSolicitud(page: Page): Promise<void> {
  await page.goto("/reset-password");
  await page.waitForLoadState("networkidle");
}

async function pasoCodigoDesdeSolicitud(page: Page): Promise<void> {
  await page.getByRole("button", { name: "Tengo un código" }).click();
  await page.waitForLoadState("networkidle");
}

async function rellenarSolicitud(page: Page, usuario: string): Promise<void> {
  await page.getByLabel("Empresa (código)").fill(TENANT);
  await page.getByLabel("Usuario").fill(usuario);
  await page.getByRole("button", { name: "Solicitar recuperación" }).click();
  await page.waitForLoadState("networkidle");
}

async function restablecer(page: Page, usuario: string, codigo: string, clave: string): Promise<void> {
  await abrirSolicitud(page);
  await rellenarSolicitud(page, usuario);
  await pasoCodigoDesdeSolicitud(page);
  await page.getByLabel("Código de recuperación de contraseña").fill(codigo);
  await page.getByLabel(/^Nueva contraseña/).fill(clave);
  await page.getByLabel("Confirmar nueva contraseña").fill(clave);
  await page.getByRole("button", { name: "Restablecer contraseña" }).click();
  await page.waitForLoadState("networkidle");
}

async function resetCompleto(page: Page, usuario: string, codigo: string, clave: string): Promise<void> {
  await restablecer(page, usuario, codigo, clave);
  await expect(page.getByRole("status")).toContainText("Por seguridad se cerraron todas sus sesiones");
  expect(page.url()).not.toContain(codigo);
  const almacenamientos = await page.evaluate(() => ({
    local: JSON.stringify(window.localStorage),
    sesion: JSON.stringify(window.sessionStorage),
  }));
  expect(almacenamientos.local).not.toContain(codigo);
  expect(almacenamientos.sesion).not.toContain(codigo);
}

async function loginFormulario(page: Page, usuario: string, clave: string): Promise<void> {
  await page.goto("/login");
  await page.waitForLoadState("networkidle");
  await page.getByLabel("Empresa (código)").fill(TENANT);
  await page.getByLabel("Usuario").fill(usuario);
  await page.getByLabel("Contraseña").fill(clave);
  await page.getByRole("button", { name: "Iniciar sesión" }).click();
  await page.waitForLoadState("networkidle");
}

test.describe("E2E-RESET · recuperación de contraseña", () => {
  test("01 · la solicitud responde igual exista o no la cuenta", async ({ page, request }) => {
    const existente = await crearUsuario(request, "solicitud", { privilegiado: false });
    const inexistente = `nadie-${marcaUnica()}`;

    const respExistente = await request.post(`${API}/auth/password-reset/request`, {
      data: { tenant_code: TENANT, username: existente.username },
    });
    expect(respExistente.status()).toBe(202);
    expect(await respExistente.json()).toEqual({ ok: true });

    const respInexistente = await request.post(`${API}/auth/password-reset/request`, {
      data: { tenant_code: TENANT, username: inexistente },
    });
    expect(respInexistente.status()).toBe(202);
    expect(await respInexistente.json()).toEqual({ ok: true });

    await abrirSolicitud(page);
    await rellenarSolicitud(page, inexistente);
    await expect(page.getByRole("status")).toContainText("Si la cuenta puede recuperarse");
  });

  test("02 · código por la orden local → contraseña nueva por la interfaz → hecho", async ({ page, request }) => {
    const usuario = await crearUsuario(request, "emitido", { privilegiado: false });
    const codigo = emitirCodigo(usuario.username);

    await resetCompleto(page, usuario.username, codigo, NUEVA_CLAVE);
    await expect(page.getByRole("status")).toContainText("Por seguridad se cerraron todas sus sesiones");
    await expect(page.getByRole("button", { name: "Ir al inicio de sesión" })).toBeVisible();
  });

  test("03 · la sesión anterior deja de valer y la contraseña vieja tampoco", async ({ page, request }) => {
    const usuario = await crearUsuario(request, "sesiones", { privilegiado: false });
    const antes = await sesionDeUsuario(usuario.username, { tenant: TENANT });
    const codigo = emitirCodigo(usuario.username);

    await resetCompleto(page, usuario.username, codigo, NUEVA_CLAVE);

    const mfaResp = await request.get(`${API}/auth/mfa`, { headers: antes.headers });
    expect(mfaResp.status()).toBe(401);

    await loginFormulario(page, usuario.username, PASSWORD);
    await expect(page.locator("#password-error")).toContainText("Credenciales inválidas");
    expect(new URL(page.url()).pathname).toBe("/login");

    await loginFormulario(page, usuario.username, NUEVA_CLAVE);
    await expect(page).toHaveURL("/");
  });

  test("04 · el MFA se sigue exigiendo tras el reset", async ({ page, request }) => {
    const privilegiado = await crearUsuario(request, "mfa", { privilegiado: true });
    await iniciarSesion(privilegiado.username, { tenant: TENANT });
    const codigo = emitirCodigo(privilegiado.username);

    await resetCompleto(page, privilegiado.username, codigo, NUEVA_CLAVE);

    await loginFormulario(page, privilegiado.username, NUEVA_CLAVE);
    await expect(page.locator("#mfa-code")).toBeVisible();
    await expect(page.getByRole("heading", { name: "Verificación en dos pasos" })).toBeVisible();
  });

  test("05 · un código usado no vuelve a servir", async ({ page, request }) => {
    const usuario = await crearUsuario(request, "consumido", { privilegiado: false });
    const codigo = emitirCodigo(usuario.username);

    await resetCompleto(page, usuario.username, codigo, NUEVA_CLAVE);

    await abrirSolicitud(page);
    await rellenarSolicitud(page, usuario.username);
    await pasoCodigoDesdeSolicitud(page);
    await page.getByLabel("Código de recuperación de contraseña").fill(codigo);
    await page.getByLabel(/^Nueva contraseña/).fill(OTRA_CLAVE);
    await page.getByLabel("Confirmar nueva contraseña").fill(OTRA_CLAVE);
    await page.getByRole("button", { name: "Restablecer contraseña" }).click();
    await page.waitForLoadState("networkidle");
    await expect(page.getByText("Ese código ya se usó o fue reemplazado")).toBeVisible();
  });

  test("06 · un código nuevo invalida el anterior", async ({ page, request }) => {
    const usuario = await crearUsuario(request, "reemplazo", { privilegiado: false });
    const c1 = emitirCodigo(usuario.username);
    const c2 = emitirCodigo(usuario.username);
    expect(c1).not.toBe(c2);

    await abrirSolicitud(page);
    await rellenarSolicitud(page, usuario.username);
    await pasoCodigoDesdeSolicitud(page);
    await page.getByLabel("Código de recuperación de contraseña").fill(c1);
    await page.getByLabel(/^Nueva contraseña/).fill(NUEVA_CLAVE);
    await page.getByLabel("Confirmar nueva contraseña").fill(NUEVA_CLAVE);
    await page.getByRole("button", { name: "Restablecer contraseña" }).click();
    await page.waitForLoadState("networkidle");
    await expect(page.getByText("Ese código ya se usó o fue reemplazado")).toBeVisible();

    await resetCompleto(page, usuario.username, c2, OTRA_CLAVE);
  });

  test("07 · accesibilidad y 320 px", async ({ page, request }) => {
    const usuario = await crearUsuario(request, "a11y", { privilegiado: false });

    await abrirSolicitud(page);
    await rellenarSolicitud(page, usuario.username);
    await expect(page.getByRole("status")).toContainText("Si la cuenta puede recuperarse");
    const axeSolicitar = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"])
      .analyze();
    const gravesSolicitar = axeSolicitar.violations.filter((v) => v.impact === "serious" || v.impact === "critical");
    expect(gravesSolicitar).toEqual([]);

    await pasoCodigoDesdeSolicitud(page);
    const axeCodigo = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"])
      .analyze();
    const gravesCodigo = axeCodigo.violations.filter((v) => v.impact === "serious" || v.impact === "critical");
    expect(gravesCodigo).toEqual([]);

    await page.setViewportSize({ width: 320, height: 800 });
    await abrirSolicitud(page);
    await expect
      .poll(() => page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth))
      .toBe(true);

    await rellenarSolicitud(page, usuario.username);
    await pasoCodigoDesdeSolicitud(page);
    await expect
      .poll(() => page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth))
      .toBe(true);
  });
});
