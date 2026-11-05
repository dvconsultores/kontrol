import { expect, test } from "./helpers/sesion";
import {
  ANIO, API, RESPONSABLE_ESTRUCTURA, adjuntarDocumentoApi, cargoVigenteApi, cerrarNotificaciones, crearTipoDocumental,
  enteActivo, entrarEnGobierno, es2xx, estructuraVigenteApi, prepararMundo,
} from "./helpers/gobierno";
import type { APIRequestContext, Locator, Page } from "@playwright/test";

const RESPONSABLE_TESORERIA = [
  ...RESPONSABLE_ESTRUCTURA,
  "gobierno_cargos:view", "gobierno_cargos:edit", "gobierno_cargos:publish",
  "gobierno_actos:view", "gobierno_actos:edit", "gobierno_actos:issue", "gobierno_actos:annul",
  "gobierno_cuentas:view", "gobierno_cuentas:manage", "gobierno_cuentas:activate",
  "gobierno_auditoria:view",
];

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

const TEXTOS_DE_HISTORIA = ["Acto vinculado", "Inactivada", "Reactivada"];

test.describe("Gobierno · Tesorería · Revocación del acto habilitante (OBS-TRE01-E2E-01)", () => {
  test("TRE-E2E-04 · acto revocado, bloqueo y restauración", async ({ page, request }) => {
    test.setTimeout(300_000);
    const codigoBanco = String(1000 + Math.floor(Math.random() * 8999));
    const numero = `${codigoBanco}${String(Date.now()).padStart(16, "0")}`;
    const { mundo, tipoId, cargoId, cargo2Id } = await mundoConCargo(request);
    const numeroA = `TRE-A-${ANIO}-${Date.now()}-A`;
    const numeroR = `TRE-R-${ANIO}-${Date.now()}-R`;
    const numeroC = `TRE-C-${ANIO}-${Date.now()}-C`;
    const A = await actoEmitidoApi(request, mundo, tipoId, cargoId, numeroA);
    await actoEmitidoApi(request, mundo, tipoId, cargoId, numeroR);
    const C = await actoEmitidoApi(request, mundo, tipoId, cargoId, numeroC);

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

    await page.getByLabel("Acto vigente").selectOption({ label: `RESOLUCION ${numeroA} · Asunto ${numeroA}` });
    await pulsarYEsperar(page, page.getByRole("button", { name: "Vincular acto" }), "POST", /\/api\/v1\/gobierno\/tesoreria\/cuentas\/[0-9a-f-]{36}\/acto$/);

    await page.getByRole("button", { name: "Autorizar un cargo" }).click();
    await page.getByRole("combobox", { name: /^Cargo/ }).selectOption({ value: cargoId });
    await page.getByLabel(/^Acto que lo autoriza/).selectOption({ label: `RESOLUCION ${numeroA} · Asunto ${numeroA}` });
    await pulsarYEsperar(page, page.getByRole("button", { name: "Registrar autorización" }), "POST", /\/api\/v1\/gobierno\/tesoreria\/cuentas\/[0-9a-f-]{36}\/autorizados$/);
    await expect(page.getByRole("region", { name: "Tabla de cargos autorizados" })).toContainText("DIR-ADM");

    await pulsarYEsperar(page, page.getByRole("button", { name: "Activar cuenta" }), "POST", /\/api\/v1\/gobierno\/tesoreria\/cuentas\/[0-9a-f-]{36}\/activar$/);
    await expect(page.locator("dd", { hasText: /^Vigente$/ })).toBeVisible();

    await page.getByRole("button", { name: "Inactivar cuenta" }).click();
    await page.getByLabel(/^Motivo/).fill("Inactivación temporal por revocación");
    await pulsarYEsperar(page, page.getByRole("button", { name: /^Confirmar/ }), "POST", /\/api\/v1\/gobierno\/tesoreria\/cuentas\/[0-9a-f-]{36}\/inactivar$/);
    await expect(page.locator("dd", { hasText: /^Inactiva$/ })).toBeVisible();

    await page.goto(`/gobierno/actos/${A.id}`);
    await page.getByRole("button", { name: "Registrar revocación" }).click();
    const formRevocacion = page.getByRole("form", { name: /^Registrar la revocación de / });
    const selectReferencia = formRevocacion.getByLabel(/^Acto de referencia/);
    const opcion = selectReferencia.locator("option", { hasText: numeroR });
    await expect(opcion).toHaveCount(1);
    await selectReferencia.selectOption((await opcion.getAttribute("value")) ?? "");
    await formRevocacion.getByLabel(/^Motivo/).fill("Revocación por acto de referencia");
    await pulsarYEsperar(page, formRevocacion.getByRole("button", { name: "Registrar revocación" }), "POST", /\/api\/v1\/gobierno\/actos\/[0-9a-f-]{36}\/revocar$/);

    await page.goto(`/gobierno/tesoreria/cuentas/${cuentaId}`);
    await expect(page.getByText("El acto habilitante fue revocado o anulado. Vincule un acto vigente: hasta entonces no se admiten nuevos autorizados ni la reactivación.")).toBeVisible();
    await expect(page.getByRole("button", { name: "Autorizar un cargo" })).toHaveCount(0);

    const cuentaResp = await request.get(`${API}/gobierno/tesoreria/cuentas/${cuentaId}`, { headers: mundo.headers });
    expect(cuentaResp.status()).toBe(200);
    const cuenta = await cuentaResp.json();
    const versionCuenta = cuenta.version as number;
    const autorizadosResp = await request.post(`${API}/gobierno/tesoreria/cuentas/${cuentaId}/autorizados`, {
      headers: { ...mundo.headers, "If-Match": String(versionCuenta) },
      data: {
        cargo_id: cargo2Id,
        acto_id: C.id,
        vigente_desde: hoyCaracas(),
      },
    });
    expect(autorizadosResp.status()).toBe(409);
    const autorizadosCuerpo = await autorizadosResp.json();
    expect(autorizadosCuerpo.code).toBe("GOV_BANK_ACCOUNT_ACT_WITHOUT_EFFECT");

    await page.getByRole("button", { name: "Reactivar cuenta" }).click();
    await page.getByLabel(/^Motivo/).fill("Reactivación no permitida sin acto vigente");
    const [respReact] = await Promise.all([
      page.waitForResponse((r) => r.request().method() === "POST" && /\/api\/v1\/gobierno\/tesoreria\/cuentas\/[0-9a-f-]{36}\/reactivar$/.test(new URL(r.url()).pathname), { timeout: 60_000 }),
      page.getByRole("button", { name: /^Confirmar/ }).click(),
    ]);
    expect(respReact.status()).toBe(409);
    const respReactCuerpo = await respReact.json();
    expect(respReactCuerpo.code).toBe("GOV_BANK_ACCOUNT_ACT_WITHOUT_EFFECT");
    await expect(page.getByRole("alert").filter({ hasText: "El acto habilitante fue revocado o anulado; vincule un acto vigente" })).toBeVisible();
    await expect(page.locator("dd", { hasText: /^Inactiva$/ })).toBeVisible();

    await page.getByLabel("Acto vigente").selectOption({ label: `RESOLUCION ${numeroC} · Asunto ${numeroC}` });
    await pulsarYEsperar(page, page.getByRole("button", { name: "Vincular acto" }), "POST", /\/api\/v1\/gobierno\/tesoreria\/cuentas\/[0-9a-f-]{36}\/acto$/);

    await page.reload();
    await expect(page.getByText("El acto habilitante fue revocado o anulado. Vincule un acto vigente: hasta entonces no se admiten nuevos autorizados ni la reactivación.")).toHaveCount(0);

    await page.getByRole("button", { name: "Reactivar cuenta" }).click();
    await page.getByLabel(/^Motivo/).fill("Reactivación con acto vigente");
    await pulsarYEsperar(page, page.getByRole("button", { name: /^Confirmar/ }), "POST", /\/api\/v1\/gobierno\/tesoreria\/cuentas\/[0-9a-f-]{36}\/reactivar$/);
    await expect(page.locator("dd", { hasText: /^Vigente$/ })).toBeVisible();

    await expect(page.getByRole("button", { name: "Autorizar un cargo" })).toBeVisible();

    const historia = page.getByRole("region", { name: "Historia de la cuenta" });
    for (const texto of TEXTOS_DE_HISTORIA) {
      await expect(historia).toContainText(texto);
    }

    const auditoriaResp = await request.get(`${API}/gobierno/auditoria/eventos?proceso=TRE-01&por_pagina=200`, { headers: mundo.headers });
    expect(auditoriaResp.status()).toBe(200);
    const auditoriaCuerpo = await auditoriaResp.json();
    const eventos = auditoriaCuerpo.items;
    const linked = eventos.filter((e: { accion: string; entidad_id: string }) => e.accion === "GOV_BANK_ACCOUNT_ACT_LINKED" && e.entidad_id === cuentaId);
    expect(linked.length).toBeGreaterThanOrEqual(2);
    const reactivated = eventos.some((e: { accion: string; entidad_id: string }) => e.accion === "GOV_BANK_ACCOUNT_REACTIVATED" && e.entidad_id === cuentaId);
    expect(reactivated).toBe(true);
  });
});
