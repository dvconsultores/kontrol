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
  "gobierno_caja:view", "gobierno_caja:manage", "gobierno_caja:activate",
];
const CONSULTA_CAJA = ["organization:view", "gobierno_caja:view"];

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
  await cargoVigenteApi(request, mundo.headers, mundo.companyId, tipo.id, ANIO, da01Id, "DIR-TES");
  return { mundo, tipoId: tipo.id, cargoId: cargo.id };
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

async function cuentaVigenteUi(page: Page, request: APIRequestContext) {
  const { mundo, tipoId, cargoId } = await mundoConCargo(request);
  const codigoBanco = String(2000 + Math.floor(Math.random() * 7999));
  const numero = `${codigoBanco}${String(Date.now()).padStart(16, "0").slice(-16)}`;
  const numeroA = `TRE-C-${ANIO}-${Date.now()}`;
  const numeroB = `TRE-D-${ANIO}-${Date.now()}`;
  await actoEmitidoApi(request, mundo, tipoId, cargoId, numeroA);
  await actoEmitidoApi(request, mundo, tipoId, cargoId, numeroB);

  await entrarEnGobierno(page, mundo.username, mundo.codigo, "/gobierno/tesoreria/bancos");
  await expect(page.getByRole("heading", { level: 1, name: "Bancos" })).toBeVisible();
  await page.getByLabel(/^Código/).fill(codigoBanco);
  await page.getByLabel(/^Nombre/).fill(`Banco ${codigoBanco}`);
  await pulsarYEsperar(page, page.getByRole("button", { name: "Registrar banco" }), "POST", /\/api\/v1\/gobierno\/tesoreria\/bancos$/);

  await page.locator('nav[aria-label="Menú principal"] a[href="/gobierno/tesoreria/cuentas"]').click();
  await expect(page.getByRole("heading", { level: 1, name: "Cuentas bancarias" })).toBeVisible();
  await page.getByRole("link", { name: "Nueva cuenta" }).first().click();
  await page.getByLabel(/^Denominación/).fill(`Cuenta PF-${codigoBanco}-${numero.slice(-4)}`);
  await page.getByLabel(/^Banco/).selectOption({ label: `${codigoBanco} · Banco ${codigoBanco}` });
  await page.getByLabel(/^Tipo de cuenta/).selectOption({ label: "Corriente" });
  await page.getByLabel(/^Número de cuenta/).fill(numero);
  await page.getByLabel(/^Moneda/).selectOption("VES");
  await page.getByLabel(/^Vigente desde/).fill(hoyCaracas());
  await pulsarYEsperar(page, page.getByRole("button", { name: "Registrar cuenta" }), "POST", /\/api\/v1\/gobierno\/tesoreria\/cuentas$/);
  await expect(page.getByRole("heading", { level: 1, name: /^Cuenta CB-\d{4}-\d{4}$/ })).toBeVisible();
  const cuentaId = page.url().split("/").pop() as string;

  await page.getByLabel("Acto vigente").selectOption({ label: `RESOLUCION ${numeroA} · Asunto ${numeroA}` });
  await pulsarYEsperar(page, page.getByRole("button", { name: "Vincular acto" }), "POST", /\/api\/v1\/gobierno\/tesoreria\/cuentas\/[0-9a-f-]{36}\/acto$/);

  await page.getByRole("button", { name: "Autorizar un cargo" }).click();
  await page.getByRole("combobox", { name: /^Cargo/ }).selectOption({ value: cargoId });
  await page.getByLabel(/^Acto que lo autoriza/).selectOption({ label: `RESOLUCION ${numeroA} · Asunto ${numeroA}` });
  await pulsarYEsperar(page, page.getByRole("button", { name: "Registrar autorización" }), "POST", /\/api\/v1\/gobierno\/tesoreria\/cuentas\/[0-9a-f-]{36}\/autorizados$/);

  await pulsarYEsperar(page, page.getByRole("button", { name: "Activar cuenta" }), "POST", /\/api\/v1\/gobierno\/tesoreria\/cuentas\/[0-9a-f-]{36}\/activar$/);
  await expect(page.locator("dd", { hasText: /^Vigente$/ })).toBeVisible();

  return { cuentaId, mundo };
}

test.describe("Gobierno · Tesorería · Programación financiera (TRE-02)", () => {
  test("PF-E2E-01 · proceso completo por el menú", async ({ page, request }) => {
    test.setTimeout(300_000);
    const { cuentaId, mundo } = await cuentaVigenteUi(page, request);
    const fechaHoy = hoyCaracas();
    const fundamento = "Fundamento legal de programación";
    const mesLineaIngreso = "Enero";
    const mesLineaDesembolso = "Febrero";

    await entrarEnGobierno(page, mundo.username, mundo.codigo, "/gobierno/tesoreria/programacion");
    await expect(page.getByRole("heading", { level: 1, name: "Programación financiera" })).toBeVisible();

    await page.locator('nav[aria-label="Menú principal"] a[href="/gobierno/tesoreria/rubros"]').click();
    await expect(page.getByRole("heading", { level: 1, name: "Rubros de caja" })).toBeVisible();
    await page.getByLabel(/^Código/).fill("PF-ING");
    await page.getByLabel(/^Nombre/).fill("Ingreso PF");
    await page.getByLabel(/^Tipo/).selectOption("INGRESO");
    await pulsarYEsperar(page, page.getByRole("button", { name: "Registrar rubro" }), "POST", /\/api\/v1\/gobierno\/tesoreria\/rubros$/);
    await expect(page.getByRole("region", { name: "Tabla de rubros" })).toContainText("Ingreso PF");

    await page.getByLabel(/^Código/).fill("PF-DES");
    await page.getByLabel(/^Nombre/).fill("Desembolso PF");
    await page.getByLabel(/^Tipo/).selectOption("DESEMBOLSO");
    await pulsarYEsperar(page, page.getByRole("button", { name: "Registrar rubro" }), "POST", /\/api\/v1\/gobierno\/tesoreria\/rubros$/);
    await expect(page.getByRole("region", { name: "Tabla de rubros" })).toContainText("Desembolso PF");

    await page.locator('nav[aria-label="Menú principal"] a[href="/gobierno/tesoreria/programacion"]').click();
    await expect(page.getByRole("heading", { level: 1, name: "Programación financiera" })).toBeVisible();
    await page.getByRole("link", { name: "Nuevo programa" }).first().click();
    await expect(page.getByRole("heading", { level: 1, name: "Nuevo programa" })).toBeVisible();
    await page.getByLabel("Ejercicio").fill(String(ANIO + 1));
    await page.getByLabel("Moneda").selectOption("VES");
    await page.getByLabel("Mes inicial").selectOption({ label: "Enero" });
    await pulsarYEsperar(page, page.getByRole("button", { name: "Registrar programa" }), "POST", /\/api\/v1\/gobierno\/tesoreria\/programas$/);
    await expect(page.getByRole("heading", { level: 1, name: `Programa PF-${ANIO + 1}-VES` })).toBeVisible();

    const programaUrl = page.url();
    const programaId = programaUrl.split("/").pop() as string;
    expect(programaId).toMatch(/^[0-9a-f-]{36}$/);

    await page.getByRole("button", { name: "Declarar" }).click();
    await page.getByLabel(/^Cuenta/).selectOption({ value: cuentaId });
    await page.getByLabel(/^Monto/).fill("1000.00");
    await page.getByLabel(/^Fecha de corte/).fill(fechaHoy);
    await page.getByLabel(/^Fundamento/).fill(fundamento);
    await pulsarYEsperar(page, page.getByRole("button", { name: "Registrar declaración" }), "POST", /\/api\/v1\/gobierno\/tesoreria\/programas\/[0-9a-f-]{36}\/declaraciones$/);
    await expect(page.getByRole("region", { name: "Tabla de declaraciones" })).toContainText("1.000,00");

    await page.getByRole("button", { name: "Añadir línea" }).first().click();
    await page.getByLabel(/^Mes\b/).selectOption({ label: mesLineaIngreso });
    await page.getByLabel(/^Rubro/).selectOption({ label: "PF-ING · Ingreso PF" });
    await page.getByLabel(/^Monto/).fill("500.00");
    await pulsarYEsperar(page, page.getByRole("button", { name: "Añadir línea" }).last(), "POST", /\/api\/v1\/gobierno\/tesoreria\/programas\/[0-9a-f-]{36}\/lineas$/);
    await expect(page.getByRole("region", { name: "Tabla de líneas" })).toContainText("Ingreso PF");

    await page.getByRole("button", { name: "Añadir línea" }).first().click();
    await page.getByLabel(/^Mes\b/).selectOption({ label: mesLineaIngreso });
    await page.getByLabel(/^Rubro/).selectOption({ label: "PF-DES · Desembolso PF" });
    await page.getByLabel(/^Monto/).fill("300.00");
    await pulsarYEsperar(page, page.getByRole("button", { name: "Añadir línea" }).last(), "POST", /\/api\/v1\/gobierno\/tesoreria\/programas\/[0-9a-f-]{36}\/lineas$/);

    await expect(page.getByRole("region", { name: "Tabla de disponibilidad mensual del programa" })).toContainText("Enero");
    await expect(page.getByRole("region", { name: "Tabla de disponibilidad mensual del programa" })).toContainText("1.200,00");
    await expect(page.getByRole("region", { name: "Tabla de disponibilidad mensual del programa" })).toContainText("Febrero");
    await expect(page.getByRole("region", { name: "Tabla de disponibilidad mensual del programa" })).toContainText("1.200,00");

    await pulsarYEsperar(page, page.getByRole("button", { name: "Activar versión" }), "POST", /\/api\/v1\/gobierno\/tesoreria\/programas\/[0-9a-f-]{36}\/activar$/);
    await expect(page.getByRole("main").locator("p", { hasText: /^Vigente/ })).toBeVisible();

    await page.getByRole("button", { name: "Reprogramar" }).click();
    await page.getByLabel(/^Motivo/).fill("Reprogramación autorizada");
    await pulsarYEsperar(page, page.getByRole("button", { name: "Confirmar reprogramación" }), "POST", /\/api\/v1\/gobierno\/tesoreria\/programas\/[0-9a-f-]{36}\/reprogramar$/);
    await expect(page.getByRole("button", { name: "Activar versión" })).toBeVisible();

    await page.getByRole("button", { name: "Añadir línea" }).first().click();
    await page.getByLabel(/^Mes\b/).selectOption({ label: mesLineaDesembolso });
    await page.getByLabel(/^Rubro/).selectOption({ label: "PF-DES · Desembolso PF" });
    await page.getByLabel(/^Monto/).fill("100.00");
    await pulsarYEsperar(page, page.getByRole("button", { name: "Añadir línea" }).last(), "POST", /\/api\/v1\/gobierno\/tesoreria\/programas\/[0-9a-f-]{36}\/lineas$/);

    await pulsarYEsperar(page, page.getByRole("button", { name: "Activar versión" }), "POST", /\/api\/v1\/gobierno\/tesoreria\/programas\/[0-9a-f-]{36}\/activar$/);
    await expect(page.getByRole("main").locator("p", { hasText: /^Vigente/ })).toBeVisible();
    await expect(page.locator("dt", { hasText: /^Versión vigente$/ }).locator("..").locator("dd")).toHaveText("2");
    await expect(page.getByRole("region", { name: "Tabla de versiones del programa" })).toContainText("Superada");

    await page.getByRole("button", { name: "Ver versión 1" }).click();
    await expect(page.getByRole("region", { name: "Tabla de disponibilidad mensual del programa" })).toContainText("1.200,00");
    await expect(page.getByRole("region", { name: "Tabla de disponibilidad mensual del programa" })).not.toContainText("1.300,00");

    await page.getByRole("button", { name: "Cerrar programa" }).click();
    await page.getByLabel(/^Motivo/).fill("Cierre autorizado del programa");
    await pulsarYEsperar(page, page.getByRole("button", { name: "Confirmar cierre" }), "POST", /\/api\/v1\/gobierno\/tesoreria\/programas\/[0-9a-f-]{36}\/cerrar$/);
    await expect(page.getByRole("main").locator("p", { hasText: /^Cerrado/ })).toBeVisible();
    await expect(page.getByRole("button", { name: "Activar versión" })).toHaveCount(0);
    await expect(page.getByRole("button", { name: "Reprogramar" })).toHaveCount(0);
    await expect(page.getByRole("button", { name: "Cerrar programa" })).toHaveCount(0);

    await expect(page.getByRole("region", { name: "Tabla de historia del programa" })).toContainText("Programa registrado");
    await expect(page.getByRole("region", { name: "Tabla de historia del programa" })).toContainText("Versión activada");
    await expect(page.getByRole("region", { name: "Tabla de historia del programa" })).toContainText("Reprogramación abierta");
    await expect(page.getByRole("region", { name: "Tabla de historia del programa" })).toContainText("Programa cerrado");

    const auditoriaResp = await request.get(`${API}/gobierno/auditoria/eventos?proceso=TRE-02&por_pagina=200`, { headers: mundo.headers });
    expect(auditoriaResp.status()).toBe(200);
    const auditoria = await auditoriaResp.json();
    expect(auditoria.items.some((ev: { accion: string; entidad_id: string }) => ev.accion === "GOV_CASH_PROGRAM_CREATED" && ev.entidad_id === programaId)).toBe(true);
  });

  test("PF-E2E-02 · negativas", async ({ page, request }) => {
    test.setTimeout(300_000);
    const { cuentaId, mundo } = await cuentaVigenteUi(page, request);
    const ejercicio = ANIO + 2;

    await entrarEnGobierno(page, mundo.username, mundo.codigo, "/gobierno/tesoreria/programacion");
    await page.getByRole("link", { name: "Nuevo programa" }).first().click();
    await expect(page.getByRole("heading", { level: 1, name: "Nuevo programa" })).toBeVisible();
    await page.getByLabel("Ejercicio").fill(String(ejercicio));
    await page.getByLabel("Moneda").selectOption("VES");
    await page.getByLabel("Mes inicial").selectOption({ label: "Enero" });
    await expect(page.getByLabel("Ejercicio")).toHaveValue(String(ejercicio));
    await expect(page.getByLabel("Moneda")).toHaveValue("VES");
    await pulsarYEsperar(page, page.getByRole("button", { name: "Registrar programa" }), "POST", /\/api\/v1\/gobierno\/tesoreria\/programas$/);
    await expect(page.getByRole("heading", { level: 1, name: `Programa PF-${ejercicio}-VES` })).toBeVisible();
    const primerProgramaUrl = page.url();
    const primerProgramaId = primerProgramaUrl.split("/").pop() as string;

    await page.getByRole("button", { name: "Activar versión" }).click();
    await expect(page.getByText(/al menos una declaración de disponibilidad/i)).toBeVisible();
    await expect(page.getByText(/al menos una línea de programación/i)).toBeVisible();
    await expect(page.getByRole("main").locator("p", { hasText: /^Borrador$/ })).toBeVisible();

    await page.locator('nav[aria-label="Menú principal"] a[href="/gobierno/tesoreria/programacion"]').click();
    await page.getByRole("link", { name: "Nuevo programa" }).first().click();
    await expect(page.getByRole("heading", { level: 1, name: "Nuevo programa" })).toBeVisible();
    await page.getByLabel("Ejercicio").fill(String(ejercicio));
    await page.getByLabel("Moneda").selectOption("VES");
    await page.getByLabel("Mes inicial").selectOption({ label: "Enero" });
    await expect(page.getByLabel("Ejercicio")).toHaveValue(String(ejercicio));
    await expect(page.getByLabel("Moneda")).toHaveValue("VES");
    await page.getByRole("button", { name: "Registrar programa" }).click();
    await expect(page.getByText("Ya hay un programa de ese ejercicio y moneda.")).toBeVisible();

    await page.locator('nav[aria-label="Menú principal"] a[href="/gobierno/tesoreria/programacion"]').click();
    await expect(page.getByText(`PF-${ejercicio}-VES`)).toHaveCount(1);

    await page.goto(primerProgramaUrl);
    await page.getByRole("button", { name: "Activar versión" }).click();
    await expect(page.getByText(/al menos una declaración de disponibilidad/i)).toBeVisible();

    const opcionesResp = await request.get(`${API}/gobierno/tesoreria/programas/${primerProgramaId}/opciones`, { headers: mundo.headers });
    expect(opcionesResp.status()).toBe(200);
    const opciones = await opcionesResp.json();
    expect(opciones.cuentas.find((op: { id: string }) => op.id === cuentaId)).toBeTruthy();
    const cuentaResp = await request.get(`${API}/gobierno/tesoreria/cuentas/${cuentaId}`, {
      headers: mundo.headers,
    });
    expect(cuentaResp.status()).toBe(200);
    const versionCuenta = (await cuentaResp.json()).version as number;
    const respCierreCuenta = await request.post(`${API}/gobierno/tesoreria/cuentas/${cuentaId}/cerrar`, {
      headers: { ...mundo.headers, "If-Match": `"${versionCuenta}"` },
      data: { motivo: "Cierre para prueba negativa", fecha_cierre: hoyCaracas() },
    });
    expect(respCierreCuenta.status()).toBe(200);

    const opcionesCerradaResp = await request.get(`${API}/gobierno/tesoreria/programas/${primerProgramaId}/opciones`, { headers: mundo.headers });
    expect(opcionesCerradaResp.status()).toBe(200);
    const opcionesCerradas = await opcionesCerradaResp.json();
    expect(opcionesCerradas.cuentas.find((op: { id: string }) => op.id === cuentaId)).toBeUndefined();

    const actResp = await request.post(`${API}/gobierno/tesoreria/programas`, {
      headers: mundo.headers,
      data: { ejercicio, moneda: "USD", mes_inicial: 1 },
    });
    expect(actResp.status()).toBe(201);
    const otroProgramaId = (await actResp.json()).id as string;
    const versionResp = await request.get(`${API}/gobierno/tesoreria/programas/${otroProgramaId}`, { headers: mundo.headers });
    expect(versionResp.status()).toBe(200);
    const programaActual = await versionResp.json();
    const versionAnterior = (programaActual.version as number) - 1;
    const staleResp = await request.post(`${API}/gobierno/tesoreria/programas/${otroProgramaId}/activar`, {
      headers: { ...mundo.headers, "If-Match": `"${versionAnterior}"` },
    });
    expect(staleResp.status()).toBe(409);
    expect((await staleResp.json()).code).toBe("GOV_CASH_PROGRAM_STALE");

    const admin = await sesionApi("admintenant", { tenant: TENANT });
    const consulta = await crearUsuario(request, admin.headers, CONSULTA_CAJA, mundo.companyId);
    await entrarEnGobierno(page, consulta.username, mundo.codigo, "/gobierno/tesoreria/programacion");
    await expect(page.getByRole("heading", { level: 1, name: "Programación financiera" })).toBeVisible();
    await expect(page.getByRole("link", { name: "Nuevo programa" })).toHaveCount(0);
    await page.goto(`/gobierno/tesoreria/programacion/${primerProgramaId}`);
    await expect(page.getByRole("button", { name: "Activar versión" })).toHaveCount(0);
  });

  test("PF-E2E-03 · accesibilidad y responsive", async ({ page, request }) => {
    test.setTimeout(300_000);
    const { mundo } = await cuentaVigenteUi(page, request);
    await entrarEnGobierno(page, mundo.username, mundo.codigo, "/gobierno/tesoreria/rubros");
    await expect(page.getByRole("heading", { level: 1, name: "Rubros de caja" })).toBeVisible();

    for (const width of [1280, 768, 320]) {
      await page.setViewportSize({ width, height: 800 });
      await sinViolacionesSerias(page, `Rubros ${width}px`);
    }

    await page.locator('nav[aria-label="Menú principal"] a[href="/gobierno/tesoreria/programacion"]').click();
    await expect(page.getByRole("heading", { level: 1, name: "Programación financiera" })).toBeVisible();
    for (const width of [1280, 768, 320]) {
      await page.setViewportSize({ width, height: 800 });
      await sinViolacionesSerias(page, `Programación ${width}px`);
    }

    await page.getByRole("link", { name: "Nuevo programa" }).first().click();
    await expect(page.getByRole("heading", { level: 1, name: "Nuevo programa" })).toBeVisible();
    for (const width of [1280, 768, 320]) {
      await page.setViewportSize({ width, height: 800 });
      await sinViolacionesSerias(page, `Nuevo programa ${width}px`);
    }

    const actResp = await request.post(`${API}/gobierno/tesoreria/programas`, {
      headers: mundo.headers,
      data: { ejercicio: ANIO + 3, moneda: "VES", mes_inicial: 1 },
    });
    expect(actResp.status()).toBe(201);
    const programaId = (await actResp.json()).id as string;
    await page.goto(`/gobierno/tesoreria/programacion/${programaId}`);
    await expect(page.getByRole("heading", { level: 1, name: /^Programa PF-/ })).toBeVisible();
    for (const width of [1280, 768, 320]) {
      await page.setViewportSize({ width, height: 800 });
      await sinViolacionesSerias(page, `Programa detalle ${width}px`);
    }
  });
});
