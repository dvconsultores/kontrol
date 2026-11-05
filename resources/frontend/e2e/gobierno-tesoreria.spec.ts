import AxeBuilder from "@axe-core/playwright";
import { expect, sesionApi, test } from "./helpers/sesion";
import {
  ANIO, API, RESPONSABLE_ESTRUCTURA, TENANT, adjuntarDocumentoApi, cargoVigenteApi, cerrarNotificaciones, crearTipoDocumental,
  crearUsuario, enteActivo, entrarEnGobierno, es2xx, estructuraVigenteApi, prepararMundo,
} from "./helpers/gobierno";
import type { APIRequestContext, Locator, Page } from "@playwright/test";

const RESPONSABLE_TESORERIA = [
  ...RESPONSABLE_ESTRUCTURA,
  "gobierno_cargos:view", "gobierno_cargos:edit", "gobierno_cargos:publish",
  "gobierno_actos:view", "gobierno_actos:edit", "gobierno_actos:issue", "gobierno_actos:annul",
  "gobierno_cuentas:view", "gobierno_cuentas:manage", "gobierno_cuentas:activate",
  "gobierno_auditoria:view",
];
const CONSULTA_CUENTAS = ["organization:view", "gobierno_cuentas:view"];

const WCAG = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"];

function hoyCaracas(): string {
  return new Intl.DateTimeFormat("en-CA", { timeZone: "America/Caracas" }).format(new Date());
}

async function pulsarYEsperar(page: Page, boton: Locator, metodo: string, ruta: RegExp): Promise<void> {
  await cerrarNotificaciones(page);
  const [resp] = await Promise.all([
    page.waitForResponse((r) => r.request().method() === metodo && ruta.test(new URL(r.url()).pathname), { timeout: 60_000 }),
    boton.click(),
  ]);
  expect(es2xx(resp.status()), await resp.text()).toBe(true);
}

async function sinViolacionesSerias(page: Page, contexto: string): Promise<void> {
  const resultados = await new AxeBuilder({ page }).include("main").withTags(WCAG).analyze();
  const serias = resultados.violations.filter((v) => ["critical", "serious"].includes(v.impact ?? ""));
  expect(serias.map((v) => ({ id: v.id, help: v.help })), contexto).toEqual([]);
  if (page.viewportSize()?.width === 320) {
    const sinDesbordamiento = await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth);
    expect(sinDesbordamiento, contexto).toBe(true);
  }
}

async function mundoConCargo(request: APIRequestContext) {
  const mundo = await prepararMundo(request, RESPONSABLE_TESORERIA);
  const tipo = await crearTipoDocumental(request, mundo.headers, mundo.companyId);
  await enteActivo(request, mundo.headers, mundo.companyId, tipo.id);
  const { da01Id } = await estructuraVigenteApi(request, mundo.headers, mundo.companyId, tipo.id, ANIO);
  const cargo = await cargoVigenteApi(request, mundo.headers, mundo.companyId, tipo.id, ANIO, da01Id, "DIR-ADM");
  const cargo2 = await cargoVigenteApi(request, mundo.headers, mundo.companyId, tipo.id, ANIO, da01Id, "DIR-TES");
  return { mundo, tipoId: tipo.id, cargoId: cargo.id, cargo2Id: cargo2.id };
}

async function actoEmitidoApi(
  request: APIRequestContext,
  mundo: { headers: Record<string, string>; companyId: string },
  tipoId: string,
  cargoId: string,
  numero: string,
): Promise<{ id: string; version: number }> {
  const resp = await request.post(`${API}/gobierno/actos`, {
    headers: mundo.headers,
    data: {
      tipo: "RESOLUCION", numero, caracter: "PARTICULAR", asunto: `Asunto ${numero}`, simple_tramite: false, cargo_id: cargoId,
      fecha: hoyCaracas(), lugar: "Caracas", fundamento_competencia: "Reglamento interno, art. 12", funcionario: "Funcionaria de prueba",
      titularidad: "TITULAR", destinatario: "Proveedor de prueba", hechos: "Hechos de prueba", fundamentos: "Fundamentos legales de prueba",
      decision: "Decisión de prueba", competencia: { accion: "APROBAR", materia: "CONTRATACIONES" },
    },
  });
  expect(resp.status(), await resp.text()).toBe(201);
  const id = (await resp.json()).id as string;
  await adjuntarDocumentoApi(request, mundo.headers, mundo.companyId, tipoId, "GovernmentAct", id);
  const docsResp = await request.get(`${API}/documentos/por-recurso/GovernmentAct/${id}`, { headers: mundo.headers });
  expect(docsResp.status(), await docsResp.text()).toBe(200);
  const docs = await docsResp.json();
  const emitirResp = await request.post(`${API}/gobierno/actos/${id}/emitir`, {
    headers: { ...mundo.headers, "If-Match": '"1"' },
    data: { documento_acto_id: docs[0].id },
  });
  expect(emitirResp.status(), await emitirResp.text()).toBe(200);
  return { id, version: (await emitirResp.json()).version as number };
}

test.describe("Gobierno · Tesorería · Cuentas bancarias (TRE-01)", () => {
  test("TRE-E2E-01 · proceso completo por la interfaz", async ({ page, request }) => {
    test.setTimeout(300_000);
    const codigoBanco = String(1000 + Math.floor(Math.random() * 8999));
    const numero = `${codigoBanco}${String(Date.now()).padStart(16, "0")}`;
    const { mundo, tipoId, cargoId, cargo2Id } = await mundoConCargo(request);
    const numeroA = `TRE-A-${ANIO}-${Date.now()}`;
    const numeroB = `TRE-B-${ANIO}-${Date.now()}`;
    await actoEmitidoApi(request, mundo, tipoId, cargoId, numeroA);
    await actoEmitidoApi(request, mundo, tipoId, cargoId, numeroB);

    await entrarEnGobierno(page, mundo.username, mundo.codigo, "/gobierno/tesoreria/bancos");
    await expect(page.getByRole("heading", { level: 1, name: "Bancos" })).toBeVisible();
    await page.getByLabel("Código").fill(codigoBanco);
    await page.getByLabel("Nombre").fill(`Banco ${codigoBanco}`);
    await pulsarYEsperar(page, page.getByRole("button", { name: "Registrar banco" }), "POST", /\/api\/v1\/gobierno\/tesoreria\/bancos$/);
    await expect(page.getByRole("region", { name: "Tabla de bancos" })).toContainText(codigoBanco);

    await page.locator('nav a[href="/gobierno/tesoreria/cuentas"]').click();
    await expect(page.getByRole("heading", { level: 1, name: "Cuentas bancarias" })).toBeVisible();
    await page.getByRole("link", { name: "Nueva cuenta" }).first().click();
    await expect(page.getByRole("heading", { level: 1, name: "Nueva cuenta bancaria" })).toBeVisible();
    await page.getByLabel(/^Denominación/).fill(`Cuenta CB-${codigoBanco}-${numero.slice(-4)}`);
    await page.getByLabel(/^Banco/).selectOption({ label: `${codigoBanco} · Banco ${codigoBanco}` });
    await page.getByLabel(/^Tipo de cuenta/).selectOption({ label: "Corriente" });
    await page.getByLabel(/^Número de cuenta/).fill(numero);
    await page.getByLabel(/^Moneda/).selectOption("VES");
    await page.getByLabel(/^Vigente desde/).fill(hoyCaracas());
    await pulsarYEsperar(page, page.getByRole("button", { name: "Registrar cuenta" }), "POST", /\/api\/v1\/gobierno\/tesoreria\/cuentas$/);
    await expect(page.getByRole("heading", { level: 1, name: /^Cuenta CB-\d{4}-\d{4}$/ })).toBeVisible();
    const cuentaId = page.url().split("/").pop() as string;
    expect(cuentaId).toMatch(/^[0-9a-f-]{36}$/);
    await expect(page.getByText(numero)).toHaveCount(0);
    await expect(page.getByText(`••••${numero.slice(-4)}`)).toBeVisible();

    await page.getByLabel("Acto vigente").selectOption({ label: `RESOLUCION ${numeroA} · Asunto ${numeroA}` });
    await pulsarYEsperar(page, page.getByRole("button", { name: "Vincular acto" }), "POST", /\/api\/v1\/gobierno\/tesoreria\/cuentas\/[0-9a-f-]{36}\/acto$/);

    await page.getByRole("button", { name: "Autorizar un cargo" }).click();
    await page.getByRole("combobox", { name: /^Cargo/ }).selectOption({ value: cargoId });
    await page.getByLabel(/^Acto que lo autoriza/).selectOption({ label: `RESOLUCION ${numeroA} · Asunto ${numeroA}` });
    await pulsarYEsperar(page, page.getByRole("button", { name: "Registrar autorización" }), "POST", /\/api\/v1\/gobierno\/tesoreria\/cuentas\/[0-9a-f-]{36}\/autorizados$/);
    await expect(page.getByRole("region", { name: "Tabla de cargos autorizados" })).toContainText("DIR-ADM");

    await pulsarYEsperar(page, page.getByRole("button", { name: "Activar cuenta" }), "POST", /\/api\/v1\/gobierno\/tesoreria\/cuentas\/[0-9a-f-]{36}\/activar$/);
    await expect(page.locator("dd", { hasText: /^Vigente$/ })).toBeVisible();

    await page.getByRole("button", { name: "Ver número completo" }).click();
    await expect(page.getByText(numero)).toBeVisible();
    await page.getByRole("button", { name: "Ocultar número" }).click();
    await expect(page.getByText(numero)).toHaveCount(0);
    await expect(page.getByText(`••••${numero.slice(-4)}`)).toBeVisible();

    await page.getByRole("button", { name: "Autorizar un cargo" }).click();
    await page.getByRole("combobox", { name: /^Cargo/ }).selectOption({ value: cargo2Id });
    await page.getByLabel(/^Acto que lo autoriza/).selectOption({ label: `RESOLUCION ${numeroB} · Asunto ${numeroB}` });
    await pulsarYEsperar(page, page.getByRole("button", { name: "Registrar autorización" }), "POST", /\/api\/v1\/gobierno\/tesoreria\/cuentas\/[0-9a-f-]{36}\/autorizados$/);
    await expect(page.getByRole("region", { name: "Tabla de cargos autorizados" })).toContainText("DIR-TES");

    await page.getByRole("button", { name: "Terminar la autorización de DIR-ADM" }).click();
    await page.getByLabel(/^Acto de fin/).selectOption({ label: `RESOLUCION ${numeroB} · Asunto ${numeroB}` });
    await page.getByLabel(/^Motivo/).fill("Rotación de autorizados del ejercicio");
    await pulsarYEsperar(page, page.getByRole("button", { name: "Confirmar fin" }), "POST", /\/api\/v1\/gobierno\/tesoreria\/cuentas\/[0-9a-f-]{36}\/autorizados\/[0-9a-f-]{36}\/fin$/);
    await expect(page.getByRole("region", { name: "Tabla de cargos autorizados" })).toContainText("DIR-ADM");
    await expect(page.getByRole("region", { name: "Tabla de cargos autorizados" })).toContainText("DIR-TES");
    await expect(page.getByRole("region", { name: "Historia de la cuenta" })).toContainText("Cargo autorizado");
    await expect(page.getByRole("region", { name: "Historia de la cuenta" })).toContainText("Autorización terminada");

    await page.getByRole("button", { name: "Inactivar cuenta" }).click();
    await page.getByLabel(/^Motivo/).fill("Inactivación temporal");
    await pulsarYEsperar(page, page.getByRole("button", { name: /^Confirmar/ }), "POST", /\/api\/v1\/gobierno\/tesoreria\/cuentas\/[0-9a-f-]{36}\/inactivar$/);
    await expect(page.locator("dd", { hasText: /^Inactiva$/ })).toBeVisible();
    await expect(page.getByRole("button", { name: "Activar cuenta", exact: true })).toHaveCount(0);

    await page.getByRole("button", { name: "Reactivar cuenta" }).click();
    await page.getByLabel(/^Motivo/).fill("Reactivación");
    await pulsarYEsperar(page, page.getByRole("button", { name: /^Confirmar/ }), "POST", /\/api\/v1\/gobierno\/tesoreria\/cuentas\/[0-9a-f-]{36}\/reactivar$/);
    await expect(page.locator("dd", { hasText: /^Vigente$/ })).toBeVisible();
    await expect(page.getByRole("button", { name: "Reactivar cuenta", exact: true })).toHaveCount(0);

    await page.getByRole("button", { name: "Cerrar cuenta" }).click();
    await page.getByLabel(/^Motivo/).fill("Cierre definitivo");
    await pulsarYEsperar(page, page.getByRole("button", { name: /^Confirmar/ }), "POST", /\/api\/v1\/gobierno\/tesoreria\/cuentas\/[0-9a-f-]{36}\/cerrar$/);
    await expect(page.getByText("Una cuenta cerrada no se reabre.")).toBeVisible();
    await expect(page.getByRole("button", { name: "Activar cuenta", exact: true })).toHaveCount(0);
    await expect(page.getByRole("button", { name: "Inactivar cuenta", exact: true })).toHaveCount(0);
    await expect(page.getByRole("button", { name: "Reactivar cuenta" })).toHaveCount(0);

    const auditoriaResp = await request.get(`${API}/gobierno/auditoria/eventos?proceso=TRE-01&por_pagina=200`, { headers: mundo.headers });
    expect(auditoriaResp.status()).toBe(200);
    const auditoriaCuerpo = await auditoriaResp.text();
    expect(JSON.stringify(auditoriaCuerpo)).not.toContain(numero);

    await page.locator('nav a[href="/gobierno/tesoreria/cuentas"]').click();
    await expect(page.getByRole("heading", { level: 1, name: "Cuentas bancarias" })).toBeVisible();
    await expect(page.getByRole("region", { name: "Tabla de cuentas bancarias" })).toContainText(`CB-${codigoBanco}-${numero.slice(-4)}`);
    await expect(page.getByRole("region", { name: "Tabla de cuentas bancarias" })).toContainText("Cerrada");
  });

  test("TRE-E2E-02 · negativas por la interfaz", async ({ page, request }) => {
    test.setTimeout(240_000);
    const codigoBanco = String(1000 + Math.floor(Math.random() * 8999));
    const numero = `${codigoBanco}${String(Date.now()).padStart(16, "0")}`;
    const { mundo, tipoId, cargoId } = await mundoConCargo(request);
    const numeroA = `TRE-A-${ANIO}-${Date.now()}`;
    await actoEmitidoApi(request, mundo, tipoId, cargoId, numeroA);

    const bancoResp = await request.post(`${API}/gobierno/tesoreria/bancos`, {
      headers: mundo.headers,
      data: { codigo: codigoBanco, nombre: `Banco ${codigoBanco}` },
    });
    expect(bancoResp.status()).toBe(201);
    const bancoId = (await bancoResp.json()).id as string;

    await entrarEnGobierno(page, mundo.username, mundo.codigo, "/gobierno/tesoreria/cuentas");
    await page.getByRole("link", { name: "Nueva cuenta" }).first().click();
    await expect(page.getByRole("heading", { level: 1, name: "Nueva cuenta bancaria" })).toBeVisible();
    await page.getByLabel(/^Denominación/).fill("Cuenta inválida");
    await page.getByLabel(/^Banco/).selectOption({ label: `${codigoBanco} · Banco ${codigoBanco}` });
    await page.getByLabel(/^Tipo de cuenta/).selectOption({ label: "Corriente" });
    await page.getByLabel(/^Número de cuenta/).fill(`9999${numero.slice(4)}`);
    await page.getByLabel(/^Moneda/).selectOption("VES");
    await page.getByLabel(/^Vigente desde/).fill(hoyCaracas());
    await page.getByRole("button", { name: "Registrar cuenta" }).click();
    await expect(page.getByText("El número debe empezar por el código del banco")).toBeVisible();
    await expect(page).toHaveURL(/\/gobierno\/tesoreria\/cuentas\/nueva$/);

    const cuentaResp = await request.post(`${API}/gobierno/tesoreria/cuentas`, {
      headers: mundo.headers,
      data: {
        denominacion: `Cuenta CB-${codigoBanco}-${numero.slice(-4)}`,
        banco_id: bancoId,
        tipo: "CORRIENTE",
        numero,
        moneda: "VES",
        vigente_desde: hoyCaracas(),
      },
    });
    expect(cuentaResp.status()).toBe(201);
    const cuentaCreada = await cuentaResp.json();
    const cuentaId = cuentaCreada.id as string;
    const codigoCuenta = cuentaCreada.codigo as string;

    await page.goto(`/gobierno/tesoreria/cuentas/${cuentaId}`);
    await expect(page.getByRole("heading", { level: 1, name: `Cuenta ${codigoCuenta}` })).toBeVisible();
    await page.getByRole("button", { name: "Autorizar un cargo" }).click();
    await expect(page.getByRole("combobox", { name: /^Cargo/ })).toHaveJSProperty("tagName", "SELECT");
    await page.getByRole("button", { name: "Cancelar" }).click();

    await page.getByRole("button", { name: "Activar cuenta" }).click();
    const alerta = page.locator('[role="alert"]');
    await expect(alerta).toContainText("Para continuar la cuenta necesita");

    const otroMundo = await prepararMundo(request, RESPONSABLE_TESORERIA);
    const crossResp = await request.get(`${API}/gobierno/tesoreria/cuentas/${cuentaId}`, { headers: otroMundo.headers });
    expect(crossResp.status()).toBe(404);
    const crossPostResp = await request.post(`${API}/gobierno/tesoreria/cuentas`, {
      headers: otroMundo.headers,
      data: {
        denominacion: "Cuenta ajena",
        banco_id: bancoId,
        tipo: "CORRIENTE",
        numero,
        moneda: "VES",
        vigente_desde: hoyCaracas(),
      },
    });
    expect(crossPostResp.status()).toBe(422);

    const admin = await sesionApi("admintenant", { tenant: TENANT });
    const consulta = await crearUsuario(request, admin.headers, CONSULTA_CUENTAS, mundo.companyId);
    await entrarEnGobierno(page, consulta.username, mundo.codigo, "/gobierno/tesoreria/cuentas");
    await page.getByRole("link", { name: `Abrir la cuenta ${codigoCuenta}` }).click();
    await expect(page.getByRole("heading", { level: 1, name: `Cuenta ${codigoCuenta}` })).toBeVisible();
    await expect(page.getByRole("link", { name: "Nueva cuenta" })).toHaveCount(0);
    await expect(page.getByRole("button", { name: "Ver número completo" })).toHaveCount(0);
    await expect(page.getByRole("button", { name: "Activar cuenta" })).toHaveCount(0);
    await expect(page.getByRole("button", { name: "Autorizar un cargo" })).toHaveCount(0);
    const numeroResp = await request.get(`${API}/gobierno/tesoreria/cuentas/${cuentaId}/numero`, { headers: consulta.headers });
    expect(numeroResp.status()).toBe(403);
  });

  test("TRE-E2E-03 · accesibilidad y responsive", async ({ page, request }) => {
    test.setTimeout(180_000);
    const codigoBanco = String(1000 + Math.floor(Math.random() * 8999));
    const numero = `${codigoBanco}${String(Date.now()).padStart(16, "0")}`;
    const { mundo } = await mundoConCargo(request);

    const bancoResp = await request.post(`${API}/gobierno/tesoreria/bancos`, {
      headers: mundo.headers,
      data: { codigo: codigoBanco, nombre: `Banco ${codigoBanco}` },
    });
    expect(bancoResp.status()).toBe(201);
    const bancoId = (await bancoResp.json()).id as string;

    const cuentaResp = await request.post(`${API}/gobierno/tesoreria/cuentas`, {
      headers: mundo.headers,
      data: {
        denominacion: `Cuenta CB-${codigoBanco}-${numero.slice(-4)}`,
        banco_id: bancoId,
        tipo: "CORRIENTE",
        numero,
        moneda: "VES",
        vigente_desde: hoyCaracas(),
      },
    });
    expect(cuentaResp.status()).toBe(201);
    const cuentaCreada = await cuentaResp.json();
    const cuentaId = cuentaCreada.id as string;
    const codigoCuenta = cuentaCreada.codigo as string;

    await entrarEnGobierno(page, mundo.username, mundo.codigo, "/gobierno/tesoreria/cuentas");
    const pantallas: Array<[string, RegExp | string, string]> = [
      ["/gobierno/tesoreria/cuentas", /^Cuentas bancarias$/, "listado"],
      ["/gobierno/tesoreria/cuentas/nueva", /^Nueva cuenta bancaria$/, "nueva"],
      [`/gobierno/tesoreria/cuentas/${cuentaId}`, `Cuenta ${codigoCuenta}`, "ficha"],
      ["/gobierno/tesoreria/bancos", /^Bancos$/, "bancos"],
    ];

    for (const [ruta, titulo, nombre] of pantallas) {
      await page.setViewportSize({ width: 1280, height: 768 });
      await page.goto(ruta);
      await expect(page.getByRole("heading", { level: 1, name: titulo })).toBeVisible();
      for (const ancho of [1280, 768, 320]) {
        await page.setViewportSize({ width: ancho, height: 768 });
        await expect(page.getByRole("heading", { level: 1, name: titulo })).toBeVisible();
        await sinViolacionesSerias(page, `${nombre} ${ancho}x768`);
      }
    }
  });
});
