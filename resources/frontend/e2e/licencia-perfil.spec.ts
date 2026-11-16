/**
 * LICACT-E2E · Activar una licencia firmada desde «Mi licencia» y ver KONTROL Gobierno
 * (Spec 004 delta LA/PF). Corre al final (proyecto licencia-perfil): deja la instalación
 * con una licencia solo-gobierno.
 */
import { resolve } from "node:path";
import { writeFileSync } from "node:fs";

import { AxeBuilder } from "@axe-core/playwright";
import { expect, type APIRequestContext, type Page } from "@playwright/test";

import { ejecutarPython } from "./helpers/python";
import { codigoParaReautenticar, entrar, sesionApi, test } from "./helpers/sesion";

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

test.describe.configure({ mode: "serial" });

test("LICACT-E2E-01 · PENDING → paquete firmado → vista previa → confirmar → reauth → activar → KONTROL Gobierno sin recargar", async ({ page, request }) => {
  test.setTimeout(240_000);
  const { token } = await sesionApi("admin");
  const antes = await detalle(request, token);
  let fingirPendiente = true;
  await page.route("**/api/v1/license/detail", async (route) => {
    const real = await route.fetch();
    const cuerpo = (await real.json()) as Record<string, unknown>;
    await route.fulfill({ response: real, json: fingirPendiente ? { ...cuerpo, mode: "PENDING" } : cuerpo });
  });
  await entrar(page, "admin", { ruta: "/mi-licencia" });
  await expect(page.getByRole("heading", { level: 2, name: "Activar licencia" })).toBeVisible({ timeout: 15_000 });
  // Instalación MIXTA de QA: se ven Gobierno y Empresa.
  const menu = page.getByRole("navigation", { name: "Menú principal" });
  await expect(menu.getByRole("link", { name: "Empresas", exact: true })).toBeVisible();
  await expect(menu.getByRole("link", { name: "Configuración del ente", exact: true })).toBeVisible();
  await page.evaluate(() => { (window as unknown as { __sinRecarga?: boolean }).__sinRecarga = true; });
  const anio = anioContractual(antes.period_end ?? new Date().toISOString()) + 2;
  // Negativos reales (el backend decide; nada cambia).
  for (const [opciones, codigo] of [[["--otra-instalacion"], "LICENSE_INSTALLATION_MISMATCH"], [["--firma-invalida"], "LICENSE_SIGNATURE_INVALID"],
                                    [["--kid", "kontrol-lic-2099-99"], "LICENSE_SIGNING_KID_UNKNOWN"]] as const) {
    const malo = licenciaFirmada(`LIC-E2E-PERFIL-NEG-${marca()}`, "--anio", String(anio), "--modulos", "gobierno", ...opciones);
    await cargar(page, malo, `negativo-${codigo}.json`);
    await page.getByRole("button", { name: "Validar y activar licencia" }).click();
    const dialogo = page.getByRole("dialog", { name: "Activar licencia" });
    await expect(dialogo).toBeVisible();
    const respuesta = page.waitForResponse((r) => new URL(r.url()).pathname.endsWith("/api/v1/license/activate") && r.request().method() === "POST");
    await dialogo.getByRole("button", { name: "Activar licencia" }).click();
    expect((await respuesta).status()).toBe(423);
    await expect(page.getByRole("alert").filter({ hasText: `(${codigo})` })).toBeVisible();
    await page.getByRole("button", { name: "Quitar archivo" }).click();
  }
  expect((await detalle(request, token)).license_id).toBe(antes.license_id);
  // Paquete legítimo solo-gobierno.
  const licenseId = `LIC-E2E-PERFIL-${marca()}`;
  const bueno = licenciaFirmada(licenseId, "--anio", String(anio), "--modulos", "gobierno");
  await cargar(page, bueno, "licencia-gobierno.json");
  await expect(page.getByText("KONTROL Gobierno", { exact: true })).toBeVisible();
  await expect(page.locator("body")).not.toContainText(bueno.signature_hex);
  // Responsive y Axe con la vista previa.
  for (const ancho of [1280, 390, 320]) {
    await page.setViewportSize({ width: ancho, height: 800 });
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth)).toBe(true);
    const axe = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"]).analyze();
    expect(axe.violations.filter((v) => v.impact === "serious" || v.impact === "critical")).toEqual([]);
  }
  await page.setViewportSize({ width: 1280, height: 800 });
  // REAUTH_REQUIRED: el login deja la reautenticación fresca, así que la PRIMERA respuesta se intercepta como la daría el backend;
  // la reautenticación y el reintento son reales.
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
  fingirPendiente = false;
  await confirmacion.getByRole("button", { name: "Activar licencia" }).click();
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
  await expect(page.getByRole("status").filter({ hasText: "Licencia activada" })).toBeVisible({ timeout: 15_000 });
  await expect(page.getByRole("heading", { level: 2, name: "Activar licencia" })).toHaveCount(0);
  // Perfil KONTROL Gobierno sin recargar.
  await expect(menu.getByRole("link", { name: "Empresas", exact: true })).toHaveCount(0, { timeout: 15_000 });
  await expect(menu.getByRole("link", { name: "Configuración del ente", exact: true })).toBeVisible();
  for (const enlace of await menu.getByRole("link").all()) {
    const href = (await enlace.getAttribute("href")) ?? "";
    expect(/^\/(organizacion|maestros|inventario|compras|ventas|tesoreria|fiscal|regulatorio|comercial|reportes)(\/|$)/.test(href)).toBe(false);
  }
  await expect(menu.getByRole("link", { name: "Mi licencia", exact: true })).toBeVisible();
  expect(await page.evaluate(() => (window as unknown as { __sinRecarga?: boolean }).__sinRecarga === true)).toBe(true);
  const despues = await detalle(request, token);
  expect(despues.license_id).toBe(licenseId);
  expect(despues.mode).toBe("FULL_ACCESS");
  expect(despues.entitlements).toEqual({ modules: ["gobierno"] });
  // Una pantalla de Gobierno responde; una ruta de Empresa directa queda bloqueada en la interfaz.
  // En una base nueva el ente aún no existe: el backend de Gobierno responde 404 GOV_ENTITY_NOT_FOUND, no 403 MODULE_NOT_ENTITLED.
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
