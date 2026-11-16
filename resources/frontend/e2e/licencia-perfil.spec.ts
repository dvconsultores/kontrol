/**
 * LICUX-E2E · Pantalla real «Mi licencia» con perfiles de producto y activación firmada
 * (Spec 004 delta LA/PF + fail-closed). 5 pruebas en serie; al final deja la instalación
 * con una licencia solo-gobierno.
 */
import { resolve } from "node:path";
import { writeFileSync } from "node:fs";

import { AxeBuilder } from "@axe-core/playwright";
import { expect, type APIRequestContext, type Browser, type Page } from "@playwright/test";

import { ejecutarPython } from "./helpers/python";
import {
  codigoParaReautenticar,
  entrar,
  entrarComoUsuario,
  sesionApi,
  sesionDeUsuario,
  test,
} from "./helpers/sesion";

const API = process.env.KONTROL_E2E_API ?? "http://127.0.0.1:8000/api/v1";
const BACKEND = resolve(process.cwd(), "..", "backend");
const QA = resolve(BACKEND, "..", "..", "qa");

const marca = (): string => Date.now().toString(36) + Math.random().toString(36).slice(2, 6);

function entornoDeQA(): NodeJS.ProcessEnv {
  const url = process.env.KONTROL_E2E_DB_URL;
  if (!url) {
    throw new Error("KONTROL_E2E_DB_URL es obligatoria: los ayudantes escriben y leen la base de la corrida");
  }
  return { ...process.env, KONTROL_DB_URL: url, PYTHONPATH: BACKEND };
}

interface Artefacto {
  payload: Record<string, unknown>;
  signature_hex: string;
}

/** Una licencia sintética firmada para la instalación de la corrida (o adulterada, según las opciones). */
function licenciaFirmada(licenseId: string, ...opciones: string[]): Artefacto {
  const salida = ejecutarPython([resolve(QA, "licencia_firmada.py"), licenseId, ...opciones], {
    cwd: BACKEND, env: entornoDeQA(), encoding: "utf8", timeout: 60_000,
  });
  return JSON.parse(salida) as Artefacto;
}

function anioContractual(iso: string): number {
  const d = new Date(iso);
  return d.getUTCMonth() + 1 >= 4 ? d.getUTCFullYear() : d.getUTCFullYear() - 1;
}

async function detalle(request: APIRequestContext, token: string): Promise<{ license_id: string | null; mode: string; period_end: string | null; entitlements: Record<string, unknown> }> {
  const respuesta = await request.get(`${API}/license/detail`, { headers: { Authorization: `Bearer ${token}` } });
  return (await respuesta.json()) as { license_id: string | null; mode: string; period_end: string | null; entitlements: Record<string, unknown> };
}

async function cargar(page: Page, artefacto: Artefacto, nombre: string): Promise<void> {
  const ruta = test.info().outputPath(nombre);
  writeFileSync(ruta, JSON.stringify(artefacto));
  await page.getByLabel("Archivo de licencia firmado").setInputFiles(ruta);
  await expect(page.getByText(String(artefacto.payload.license_id), { exact: true })).toBeVisible();
}

async function evidencia(page: Page, nombre: string): Promise<void> {
  for (const ancho of [1280, 390, 320]) {
    await page.setViewportSize({ width: ancho, height: 800 });
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth)).toBe(true);
    const axe = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"]).analyze();
    expect(axe.violations.filter((v) => v.impact === "serious" || v.impact === "critical")).toEqual([]);
    await page.screenshot({ path: resolve(test.info().project.outputDir, "evidencia-licux", `${nombre}-${ancho}.png`), fullPage: true });
  }
  await page.setViewportSize({ width: 1280, height: 800 });
}

function usuarioSinCrear(): string {
  const usuario = `sinlic${marca()}`;
  ejecutarPython([resolve(QA, "rol_sin_permiso.py"), "DEMO", usuario, "D1", "license:create"], {
    cwd: BACKEND, env: entornoDeQA(), encoding: "utf8", timeout: 60_000,
  });
  return usuario;
}

async function fingirModo(page: Page, modo: () => string | null): Promise<void> {
  await page.route("**/api/v1/license/detail", async (route) => {
    const real = await route.fetch();
    const cuerpo = (await real.json()) as Record<string, unknown>;
    const sustituto = modo();
    await route.fulfill({ response: real, json: sustituto === null ? cuerpo : { ...cuerpo, mode: sustituto } });
  });
}

test.describe.configure({ mode: "serial" });

test("LICUX-E2E-01 · PENDING autorizado → solicitud → paquete → vista previa → confirmar → reauth → activar → KONTROL Gobierno sin recargar", async ({ page, request }) => {
  test.setTimeout(240_000);
  const { token } = await sesionApi("admin");
  const antes = await detalle(request, token);
  let fingirPendiente = true;
  await fingirModo(page, () => (fingirPendiente ? "PENDING" : null));
  await entrar(page, "admin", { ruta: "/mi-licencia" });
  await expect(page.getByRole("heading", { level: 2, name: "Estado general" })).toBeVisible({ timeout: 15_000 });
  await expect(page.getByText("Pendiente de activación", { exact: true })).toBeVisible();
  await expect(page.getByRole("heading", { level: 2, name: "Solicitud de activación" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Descargar solicitud" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Copiar solicitud" })).toBeVisible();
  await expect(page.getByRole("heading", { level: 2, name: "Activar licencia" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Seleccionar archivo de licencia" })).toBeVisible();
  await expect(page.getByText("Ningún archivo seleccionado")).toBeVisible();
  await evidencia(page, "pending-autorizado");
  const descarga = page.waitForEvent("download");
  await page.getByRole("button", { name: "Descargar solicitud" }).click();
  expect((await descarga).suggestedFilename()).toMatch(/^kontrol-installation-request-.+\.json$/);
  const menu = page.getByRole("navigation", { name: "Menú principal" });
  await expect(menu.getByRole("link", { name: "Empresas", exact: true })).toBeVisible();
  await expect(menu.getByRole("link", { name: "Configuración del ente", exact: true })).toBeVisible();
  await page.evaluate(() => { Reflect.set(window, "__sinRecarga", true); });
  const anio = anioContractual(antes.period_end ?? new Date().toISOString()) + 2;
  for (const [opciones, codigo] of [[["--otra-instalacion"], "LICENSE_INSTALLATION_MISMATCH"], [["--firma-invalida"], "LICENSE_SIGNATURE_INVALID"],
                                    [["--kid", "kontrol-lic-2099-99"], "LICENSE_SIGNING_KID_UNKNOWN"]] as const) {
    const malo = licenciaFirmada(`LIC-E2E-PERFIL-NEG-${marca()}`, "--anio", String(anio), "--modulos", "gobierno", ...opciones);
    await cargar(page, malo, `negativo-${codigo}.json`);
    await page.getByRole("button", { name: "Validar y activar licencia" }).click();
    const dialogo = page.getByRole("dialog", { name: "Activar licencia" });
    await expect(dialogo).toBeVisible();
    const respuesta = page.waitForResponse((r) => new URL(r.url()).pathname.endsWith("/api/v1/license/activate") && r.request().method() === "POST");
    await dialogo.getByRole("button", { name: "Validar y activar licencia" }).click();
    expect((await respuesta).status()).toBe(423);
    await expect(page.getByRole("alert").filter({ hasText: `(${codigo})` })).toBeVisible();
    await page.getByRole("button", { name: "Quitar archivo" }).click();
  }
  expect((await detalle(request, token)).license_id).toBe(antes.license_id);
  const licenseId = `LIC-E2E-PERFIL-${marca()}`;
  const bueno = licenciaFirmada(licenseId, "--anio", String(anio), "--modulos", "gobierno");
  await cargar(page, bueno, "licencia-gobierno.json");
  await expect(page.getByText("Archivo seleccionado: licencia-gobierno.json")).toBeVisible();
  await expect(page.getByRole("heading", { level: 3, name: "Vista previa de la licencia" })).toBeVisible();
  await expect(page.getByText("KONTROL Gobierno", { exact: true })).toBeVisible();
  await expect(page.getByText(/Instalación verificada/)).toBeVisible();
  await expect(page.locator("body")).not.toContainText(bueno.signature_hex);
  await evidencia(page, "pending-vista-previa");
  let reauthInducida = false;
  await page.route("**/api/v1/license/activate", async (route) => {
    if (!reauthInducida && route.request().method() === "POST") {
      reauthInducida = true;
      await route.fulfill({ status: 403, json: { code: "REAUTH_REQUIRED", message: "Confirma tu identidad para continuar" } });
      return;
    }
    await route.continue();
  });
  await page.getByRole("button", { name: "Validar y activar licencia" }).click();
  const confirmacion = page.getByRole("dialog", { name: "Activar licencia" });
  await expect(confirmacion).toContainText("La licencia quedará vinculada a esta instalación.");
  await expect(confirmacion).toContainText("KONTROL Gobierno");
  await expect(confirmacion).toContainText(licenseId);
  fingirPendiente = false;
  await confirmacion.getByRole("button", { name: "Validar y activar licencia" }).click();
  const reauth = page.getByRole("dialog", { name: "Confirme su identidad" });
  await expect(reauth).toBeVisible({ timeout: 15_000 });
  await expect(page.getByRole("dialog", { name: "Activar licencia" })).toHaveCount(0);
  await reauth.getByLabel("Contraseña").fill(process.env.KONTROL_E2E_PASSWORD ?? "");
  await reauth.getByLabel("Código de verificación").fill(codigoParaReautenticar("admin"));
  const reautenticada = page.waitForResponse((r) => new URL(r.url()).pathname.endsWith("/api/v1/auth/reauth"));
  const activada = page.waitForResponse((r) => new URL(r.url()).pathname.endsWith("/api/v1/license/activate") && r.request().method() === "POST" && r.status() === 200);
  await reauth.getByRole("button", { name: "Confirmar" }).click();
  expect((await reautenticada).status()).toBe(200);
  const cuerpo = (await (await activada).json()) as { ok: boolean; license_id: string; mode: string };
  expect(cuerpo).toEqual({ ok: true, license_id: licenseId, mode: "FULL_ACCESS" });
  const seccionActivacion = page.locator('section[aria-labelledby="activar-licencia"]');
  await expect(seccionActivacion.getByRole("status").filter({ hasText: "Licencia activada correctamente" })).toBeVisible({ timeout: 15_000 });
  await expect(seccionActivacion.getByText(`Perfil: KONTROL Gobierno · Estado: Acceso completo · Licencia ${licenseId}`)).toBeVisible();
  await expect(page.getByRole("heading", { level: 2, name: "Activar licencia" })).toHaveCount(0);
  await expect(page.getByRole("heading", { level: 2, name: "Actualizar o reemplazar licencia" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Seleccionar nueva licencia" })).toBeVisible();
  await expect(page.getByText("KONTROL Gobierno", { exact: true })).toBeVisible();
  await expect(page.getByText("Acceso completo", { exact: true })).toBeVisible();
  await expect(page.getByText("Habilitado", { exact: true })).toBeVisible();
  await evidencia(page, "gobierno-full-access");
  const modulo = await request.get(`${API}/gobierno/modulo`, { headers: { Authorization: `Bearer ${token}` } });
  expect(modulo.status()).toBe(200);
  expect((await modulo.json()) as Record<string, unknown>).toEqual({ habilitado: true, perfil: "GOBIERNO" });
  const ordenes = await request.get(`${API}/sales/orders`, { headers: { Authorization: `Bearer ${token}` } });
  expect(ordenes.status()).toBe(403);
  expect(((await ordenes.json()) as { code?: string }).code).toBe("PRODUCT_PROFILE_DENIED");
  await expect(menu.getByRole("link", { name: "Empresas", exact: true })).toHaveCount(0, { timeout: 15_000 });
  await expect(menu.getByRole("link", { name: "Configuración del ente", exact: true })).toBeVisible();
  for (const enlace of await menu.getByRole("link").all()) {
    const href = (await enlace.getAttribute("href")) ?? "";
    expect(/^\/(organizacion|maestros|inventario|compras|ventas|tesoreria|fiscal|regulatorio|comercial|reportes)(\/|$)/.test(href)).toBe(false);
  }
  await expect(menu.getByRole("link", { name: "Mi licencia", exact: true })).toBeVisible();
  expect(await page.evaluate(() => Reflect.get(window, "__sinRecarga") === true)).toBe(true);
  const despues = await detalle(request, token);
  expect(despues.license_id).toBe(licenseId);
  expect(despues.mode).toBe("FULL_ACCESS");
  expect(despues.entitlements).toEqual({ modules: ["gobierno"] });
  const ente = page.waitForResponse((r) => new URL(r.url()).pathname.endsWith("/api/v1/gobierno/ente") && r.request().method() === "GET");
  await menu.getByRole("link", { name: "Configuración del ente", exact: true }).click();
  const respuestaEnte = await ente;
  expect(respuestaEnte.status()).toBe(404);
  expect(((await respuestaEnte.json()) as { code?: string }).code).toBe("GOV_ENTITY_NOT_FOUND");
  await expect(page.getByRole("heading", { level: 1, name: "Configuración del ente" })).toBeVisible();
  await expect(page.getByText("El ente aún no está configurado")).toBeVisible();
  await expect(page.getByText("El módulo de Gobierno no está habilitado")).toHaveCount(0);
  await page.goto("/ventas/ordenes");
  await expect(page.getByRole("heading", { name: "Acceso prohibido" })).toBeVisible({ timeout: 15_000 });
});

test("LICUX-E2E-02 · FULL_ACCESS: el administrador reemplaza la licencia por una de período posterior", async ({ page, request }) => {
  test.setTimeout(240_000);
  const { token } = await sesionApi("admin");
  const detalleActual = await detalle(request, token);
  expect(detalleActual.mode).toBe("FULL_ACCESS");
  await entrar(page, "admin", { ruta: "/mi-licencia" });
  await expect(page.getByRole("heading", { level: 2, name: "Actualizar o reemplazar licencia" })).toBeVisible({ timeout: 15_000 });
  await expect(page.getByText("Acceso completo", { exact: true })).toBeVisible();
  const nuevoId = `LIC-E2E-REEMPLAZO-${marca()}`;
  const bueno = licenciaFirmada(nuevoId, "--anio", String(anioContractual(detalleActual.period_end ?? new Date().toISOString()) + 1), "--modulos", "gobierno");
  await cargar(page, bueno, "reemplazo.json");
  await expect(page.getByText(nuevoId, { exact: true })).toBeVisible();
  let reauthInducida = false;
  await page.route("**/api/v1/license/activate", async (route) => {
    if (!reauthInducida && route.request().method() === "POST") {
      reauthInducida = true;
      await route.fulfill({ status: 403, json: { code: "REAUTH_REQUIRED", message: "Confirma tu identidad para continuar" } });
      return;
    }
    await route.continue();
  });
  await page.getByRole("button", { name: "Validar y aplicar licencia" }).click();
  const confirmacion = page.getByRole("dialog", { name: "Actualizar o reemplazar licencia" });
  await expect(confirmacion).toBeVisible();
  await confirmacion.getByRole("button", { name: "Validar y aplicar licencia" }).click();
  const reauth = page.getByRole("dialog", { name: "Confirme su identidad" });
  await expect(reauth).toBeVisible({ timeout: 15_000 });
  await reauth.getByLabel("Contraseña").fill(process.env.KONTROL_E2E_PASSWORD ?? "");
  await reauth.getByLabel("Código de verificación").fill(codigoParaReautenticar("admin"));
  const reautenticada = page.waitForResponse((r) => new URL(r.url()).pathname.endsWith("/api/v1/auth/reauth"));
  const activada = page.waitForResponse((r) => new URL(r.url()).pathname.endsWith("/api/v1/license/activate") && r.request().method() === "POST" && r.status() === 200);
  await reauth.getByRole("button", { name: "Confirmar" }).click();
  expect((await reautenticada).status()).toBe(200);
  expect((await (await activada).json()) as { ok: boolean; license_id: string; mode: string }).toEqual({ ok: true, license_id: nuevoId, mode: "FULL_ACCESS" });
  expect((await detalle(request, token)).license_id).toBe(nuevoId);
  await expect(page.locator('section[aria-labelledby="activar-licencia"]').getByRole("status").filter({ hasText: "Licencia activada correctamente" })).toBeVisible({ timeout: 15_000 });
  await expect(page.getByRole("heading", { level: 2, name: "Actualizar o reemplazar licencia" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Seleccionar nueva licencia" })).toBeVisible();
});

test("LICUX-E2E-03 · PENDING sin license:create: estado visible, permiso explicado, sin selector ni POST", async ({ page, request }) => {
  test.setTimeout(240_000);
  const usuario = usuarioSinCrear();
  await fingirModo(page, () => "PENDING");
  await entrarComoUsuario(page, usuario, { tenant: "DEMO", ruta: "/mi-licencia" });
  await expect(page.getByRole("heading", { level: 1, name: "Mi licencia" })).toBeVisible({ timeout: 15_000 });
  await expect(page.getByText("Pendiente de activación", { exact: true })).toBeVisible();
  await expect(page.getByRole("heading", { level: 2, name: "Activar o actualizar licencia" })).toBeVisible();
  await expect(page.getByText("No tiene permiso para activar o reemplazar licencias.")).toBeVisible();
  await expect(page.getByText("Se requiere license:create. Solicítelo al administrador de KONTROL.")).toBeVisible();
  await expect(page.getByLabel("Archivo de licencia firmado")).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Seleccionar archivo de licencia" })).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Validar y activar licencia" })).toHaveCount(0);
  await evidencia(page, "pending-sin-permiso");
  const { token } = await sesionDeUsuario(usuario, { tenant: "DEMO" });
  const paquete = licenciaFirmada(`LIC-E2E-SIN-PERMISO-${marca()}`, "--anio", "2099", "--modulos", "gobierno");
  const respuesta = await request.post(`${API}/license/activate`, {
    headers: { Authorization: `Bearer ${token}` },
    data: { payload: paquete.payload, signature_hex: paquete.signature_hex },
  });
  expect(respuesta.status()).toBe(403);
});

test("LICUX-E2E-04 · error al resolver el perfil: fail-closed, nunca Enterprise", async ({ page }) => {
  test.setTimeout(240_000);
  await page.route("**/api/v1/gobierno/modulo", (r) => r.fulfill({ status: 500, json: { code: "INTERNAL_ERROR", message: "x" } }));
  await entrar(page, "admin", { ruta: "/mi-licencia" });
  await expect(page.getByText("No disponible", { exact: true })).toBeVisible({ timeout: 15_000 });
  await expect(page.getByText("KONTROL Enterprise", { exact: true })).toHaveCount(0);
  const menu = page.getByRole("navigation", { name: "Menú principal" });
  await expect(menu.getByRole("link", { name: "Mi licencia", exact: true })).toBeVisible();
  await expect(menu.getByRole("link", { name: "Empresas", exact: true })).toHaveCount(0);
  await expect(menu.getByRole("link", { name: "Configuración del ente", exact: true })).toHaveCount(0);
  await page.goto("/ventas/ordenes");
  await expect(page.getByText(/No fue posible determinar el perfil de producto/)).toBeVisible();
  await page.goto("/gobierno/ente");
  await expect(page.getByText(/No fue posible determinar el perfil de producto/)).toBeVisible();
});

const SEGMENTOS_ENTERPRISE = /^\/(organizacion|maestros|inventario|compras|ventas|tesoreria|fiscal|regulatorio|comercial|reportes|homologacion|aprobaciones)(\/|$)/;
const MODULOS_MIXTOS = "gobierno,ventas,compras,inventario,tesoreria,fiscal,regulatorio,reportes";
const API_ENTERPRISE = ["/sales/quotes", "/purchasing/requisitions", "/maestros/terceros", "/organization/branches", "/treasury/banks", "/fiscal/legal-sources",
  "/regulatory/authorities", "/reporting/dashboard", "/homologation/records", "/approvals/process-types", "/inventory/movement-types", "/comercial/condiciones-pago"];
const RUTAS_ENTERPRISE = ["/ventas/ordenes", "/compras/requisiciones", "/maestros/terceros", "/organizacion/sucursales", "/tesoreria/cajas", "/fiscal/configuracion",
  "/reportes/centro", "/homologacion/actos", "/aprobaciones/bandeja"];

async function hrefsDelMenu(page: Page): Promise<string[]> {
  const menu = page.getByRole("navigation", { name: "Menú principal" });
  await expect(menu.getByRole("link", { name: "Mi licencia", exact: true })).toBeVisible({ timeout: 15_000 });
  return Promise.all((await menu.getByRole("link").all()).map(async (link) => (await link.getAttribute("href")) ?? ""));
}

async function activarPorInterfaz(page: Page, artefacto: Artefacto, nombre: string): Promise<void> {
  await cargar(page, artefacto, nombre);
  await page.getByRole("button", { name: "Validar y aplicar licencia" }).click();
  const dialogo = page.getByRole("dialog", { name: "Actualizar o reemplazar licencia" });
  await expect(dialogo).toBeVisible();
  const activada = page.waitForResponse((r) => new URL(r.url()).pathname.endsWith("/api/v1/license/activate") && r.request().method() === "POST" && r.status() === 200, { timeout: 60_000 });
  await dialogo.getByRole("button", { name: "Validar y aplicar licencia" }).click();
  const reauth = page.getByRole("dialog", { name: "Confirme su identidad" });
  const primero = await Promise.race([
    activada.then(() => "activada" as const),
    reauth.waitFor({ state: "visible", timeout: 20_000 }).then(() => "reauth" as const),
  ]);
  if (primero === "reauth") {
    await reauth.getByLabel("Contraseña").fill(process.env.KONTROL_E2E_PASSWORD ?? "");
    await reauth.getByLabel("Código de verificación").fill(await codigoParaReautenticar("admin"));
    await reauth.getByRole("button", { name: "Confirmar" }).click();
  }
  const cuerpo = (await (await activada).json()) as { ok: boolean; license_id: string };
  expect(cuerpo.ok).toBe(true);
  expect(cuerpo.license_id).toBe(String(artefacto.payload.license_id));
  await expect(page.locator('section[aria-labelledby="activar-licencia"]').getByRole("status").filter({ hasText: "Licencia activada correctamente" })).toBeVisible({ timeout: 15_000 });
}

async function comprobarSoloGobierno(page: Page, etapa: string): Promise<void> {
  const menu = page.getByRole("navigation", { name: "Menú principal" });
  await expect(menu.getByRole("link", { name: "Configuración del ente", exact: true })).toBeVisible({ timeout: 15_000 });
  await expect(menu.getByRole("link", { name: "Empresas", exact: true })).toHaveCount(0);
  const hrefs = await hrefsDelMenu(page);
  const enterprise = hrefs.filter((h) => SEGMENTOS_ENTERPRISE.test(h));
  expect(enterprise, `${etapa}: ENTERPRISE_LINKS_VISIBLE`).toEqual([]);
  expect(hrefs.filter((h) => h.startsWith("/gobierno/")).length, etapa).toBeGreaterThan(0);
}

test("LICUX-E2E-05 · OWNER_UAT_REAL_FLOW: de MIXTO real a solo-Gobierno sin interceptar nada; sin recargar, tras recargar y en sesión nueva", async ({ page, request, browser }) => {
  test.setTimeout(300_000);

  const { token } = await sesionApi("admin");
  const actual = await detalle(request, token);
  expect(actual.mode).toBe("FULL_ACCESS");
  const anio = anioContractual(actual.period_end ?? new Date().toISOString()) + 1;

  await entrar(page, "admin", { ruta: "/mi-licencia" });
  await expect(page.getByRole("heading", { level: 2, name: "Actualizar o reemplazar licencia" })).toBeVisible({ timeout: 15_000 });

  const mixto = licenciaFirmada(`LIC-E2E-OWNER-MIXTO-${marca()}`, "--anio", String(anio), "--modulos", MODULOS_MIXTOS);
  await activarPorInterfaz(page, mixto, "owner-mixto.json");
  expect(await (await request.get(`${API}/gobierno/modulo`, { headers: { Authorization: `Bearer ${token}` } })).json()).toEqual({ habilitado: true, perfil: "MIXTO" });
  const menuAntes = page.getByRole("navigation", { name: "Menú principal" });
  await expect(menuAntes.getByRole("link", { name: "Empresas", exact: true })).toBeVisible({ timeout: 15_000 });
  expect((await hrefsDelMenu(page)).filter((h) => SEGMENTOS_ENTERPRISE.test(h)).length).toBeGreaterThan(0);

  await page.evaluate(() => {
    Reflect.set(window, "__sinRecarga", true);
  });
  const gobierno = licenciaFirmada(`LIC-E2E-OWNER-GOB-${marca()}`, "--anio", String(anio + 1), "--modulos", "gobierno");
  const modulo = page.waitForResponse((r) => new URL(r.url()).pathname.endsWith("/api/v1/gobierno/modulo") && r.request().method() === "GET" && r.status() === 200, { timeout: 30_000 });
  await activarPorInterfaz(page, gobierno, "owner-gobierno.json");
  expect(await (await modulo).json()).toEqual({ habilitado: true, perfil: "GOBIERNO" });
  const tras = await detalle(request, token);
  expect(tras.license_id).toBe(String(gobierno.payload.license_id));
  expect(tras.entitlements).toEqual({ modules: ["gobierno"] });

  await comprobarSoloGobierno(page, "sin recargar");
  expect(await page.evaluate(() => Reflect.get(window, "__sinRecarga") === true)).toBe(true);
  await evidencia(page, "owner-gobierno-sin-recargar");

  for (const ruta of API_ENTERPRISE) {
    const respuesta = await request.get(`${API}${ruta}`, { headers: { Authorization: `Bearer ${token}` } });
    expect(respuesta.status(), ruta).toBe(403);
    expect(((await respuesta.json()) as { code?: string }).code, ruta).toBe("PRODUCT_PROFILE_DENIED");
  }

  for (const ruta of RUTAS_ENTERPRISE) {
    await page.goto(ruta);
    await expect(page.getByRole("heading", { name: "Acceso prohibido" })).toBeVisible({ timeout: 15_000 });
  }

  await page.goto("/mi-licencia");
  await page.reload();
  await comprobarSoloGobierno(page, "tras recargar");

  async function nuevaSesion(b: Browser): Promise<void> {
    const contexto = await b.newContext();
    const otra = await contexto.newPage();
    await entrar(otra, "admin", { ruta: "/" });
    await comprobarSoloGobierno(otra, "sesión nueva");
    await contexto.close();
  }
  await nuevaSesion(browser);
});
