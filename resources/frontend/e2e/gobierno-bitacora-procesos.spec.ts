import AxeBuilder from "@axe-core/playwright";
import { expect, sesionApi, test } from "./helpers/sesion";
import type { APIRequestContext, Locator, Page } from "@playwright/test";
import {
  ANIO,
  API,
  RESPONSABLE_ESTRUCTURA,
  TENANT,
  adjuntarDocumentoApi,
  cargoVigenteApi,
  crearTipoDocumental,
  crearUsuario,
  enteActivo,
  entrarEnGobierno,
  estructuraVigenteApi,
  prepararMundo,
} from "./helpers/gobierno";

const WCAG = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"];

const RESPONSABLE = [
  ...RESPONSABLE_ESTRUCTURA,
  "gobierno_cargos:view",
  "gobierno_cargos:edit",
  "gobierno_cargos:publish",
  "gobierno_actos:view",
  "gobierno_actos:edit",
  "gobierno_actos:issue",
  "gobierno_ocupacion:view",
  "gobierno_ocupacion:manage",
  "gobierno_ocupacion:activate",
  "gobierno_ocupacion:revoke",
  "gobierno_identidad:view",
  "gobierno_identidad:manage",
  "gobierno_identidad:activate",
  "gobierno_identidad:revoke",
];
const ACTIVADOR_ID = [
  "organization:view",
  "gobierno_identidad:view",
  "gobierno_identidad:activate",
  "gobierno_identidad:revoke",
];

function hoyCaracas(): string {
  return new Intl.DateTimeFormat("en-CA", { timeZone: "America/Caracas" }).format(new Date());
}

async function funcionarioApi(
  request: APIRequestContext,
  headers: Record<string, string>,
  nombre: string,
): Promise<{ id: string }> {
  const resp = await request.post(`${API}/gobierno/ocupacion/funcionarios`, {
    headers,
    data: {
      nombre,
      tipo_documento: "V",
      numero_documento: String(Math.floor(10000000 + Math.random() * 89999999)),
    },
  });
  expect(resp.status(), await resp.text()).toBe(201);
  return resp.json();
}

async function asignacionApi(
  request: APIRequestContext,
  headers: Record<string, string>,
  datos: {
    funcionario_id: string;
    cargo_id: string;
    acto_id: string;
    fundamento: string;
    desde?: string;
  },
): Promise<{ id: string; version: string }> {
  const resp = await request.post(`${API}/gobierno/ocupacion/asignaciones`, {
    headers,
    data: {
      funcionario_id: datos.funcionario_id,
      cargo_id: datos.cargo_id,
      figura: "TITULAR",
      acto_id: datos.acto_id,
      desde: datos.desde ?? hoyCaracas(),
      fundamento: datos.fundamento,
      cargo_origen_id: null,
      hasta: null,
      rendicion: null,
      maxima_autoridad: false,
      autorizacion_especial: null,
      declara_delegable: false,
      competencias: [],
    },
  });
  expect(resp.status(), await resp.text()).toBe(201);
  return resp.json();
}

function activarApi(
  request: APIRequestContext,
  headers: Record<string, string>,
  asignacion: { id: string; version: string },
) {
  return request.post(`${API}/gobierno/ocupacion/asignaciones/${asignacion.id}/activar`, {
    headers: { ...headers, "If-Match": `"${asignacion.version}"` },
    data: {},
  });
}

async function actoEmitidoApi(
  request: APIRequestContext,
  mundo: { headers: Record<string, string>; companyId: string },
  tipoId: string,
  cargoId: string,
  numero: string,
): Promise<{ id: string; numero: string }> {
  const resp = await request.post(`${API}/gobierno/actos`, {
    headers: mundo.headers,
    data: {
      tipo: "RESOLUCION",
      numero,
      caracter: "GENERAL",
      asunto: `Asunto ${numero}`,
      simple_tramite: false,
      cargo_id: cargoId,
      fecha: hoyCaracas(),
      lugar: "Caracas",
      fundamento_competencia: "Reglamento interno, art. 12",
      funcionario: "Funcionaria de prueba",
      titularidad: "TITULAR",
      hechos: "Hechos de prueba",
      fundamentos: "Fundamentos legales de prueba",
      decision: "Decisión de prueba",
      competencia: { accion: "APROBAR", materia: "CONTRATACIONES" },
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
  await adjuntarDocumentoApi(request, mundo.headers, mundo.companyId, tipoId, "GovernmentAct", id);
  const docsDespues = await request.get(`${API}/documentos/por-recurso/GovernmentAct/${id}`, { headers: mundo.headers });
  expect(docsDespues.status(), await docsDespues.text()).toBe(200);
  const docsList = await docsDespues.json();
  const documentoEficacia = docsList.find((d: { id: string }) => d.id !== docs[0].id);
  expect(documentoEficacia, "Debe existir un segundo documento para la eficacia").toBeTruthy();
  const eficaciaResp = await request.post(`${API}/gobierno/actos/${id}/eficacia`, {
    headers: { ...mundo.headers, "If-Match": '"2"' },
    data: {
      medio: "GACETA",
      referencia: "Gaceta N.º 1",
      fecha: hoyCaracas(),
      documento_eficacia_id: documentoEficacia.id,
    },
  });
  expect(eficaciaResp.status(), await eficaciaResp.text()).toBe(200);
  return { id, numero };
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

async function contextoAccesible(page: Page, indicador: Locator, nombre: string): Promise<void> {
  for (const ancho of [1280, 390, 320]) {
    await page.setViewportSize({ width: ancho, height: 768 });
    await expect(indicador).toBeVisible();
    await sinViolacionesSerias(page, `${nombre} ${ancho}x768`);
    const sinDesbordamiento = await page.evaluate(
      () => document.documentElement.scrollWidth <= document.documentElement.clientWidth,
    );
    expect(sinDesbordamiento, `${nombre} ${ancho}`).toBe(true);
  }
  await page.setViewportSize({ width: 1280, height: 768 });
}

async function mundoOcupacion(request: APIRequestContext) {
  const mundo = await prepararMundo(request, RESPONSABLE);
  const tipo = await crearTipoDocumental(request, mundo.headers, mundo.companyId);
  await enteActivo(request, mundo.headers, mundo.companyId, tipo.id);
  const estructura = await estructuraVigenteApi(request, mundo.headers, mundo.companyId, tipo.id, ANIO);
  const emisor = await cargoVigenteApi(request, mundo.headers, mundo.companyId, tipo.id, ANIO, estructura.da01Id, "EMISOR-OCU");
  const objetivo = await cargoVigenteApi(request, mundo.headers, mundo.companyId, tipo.id, ANIO, estructura.da01Id, "OBJETIVO-OCU");
  const futuro = await cargoVigenteApi(request, mundo.headers, mundo.companyId, tipo.id, ANIO, estructura.da01Id, "FUTURO-OCU");
  const revocado = await cargoVigenteApi(request, mundo.headers, mundo.companyId, tipo.id, ANIO, estructura.da01Id, "REVOCADO-OCU");
  return { mundo, tipoId: tipo.id, emisorId: emisor.id, objetivoId: objetivo.id, futuroId: futuro.id, revocadoId: revocado.id };
}

async function registrarVinculoApi(
  request: APIRequestContext,
  headers: Record<string, string>,
  datos: { user_id: string; official_id: string; desde: string; motivo: string },
): Promise<{ id: string; version: string }> {
  const resp = await request.post(`${API}/gobierno/identidad/vinculos`, {
    headers,
    data: {
      user_id: datos.user_id,
      official_id: datos.official_id,
      desde: datos.desde,
      hasta: null,
      motivo: datos.motivo,
      soporte: null,
    },
  });
  expect(resp.status(), await resp.text()).toBe(201);
  return resp.json();
}

async function activarVinculoApi(
  request: APIRequestContext,
  headers: Record<string, string>,
  vinculo: { id: string; version: string },
) {
  return request.post(`${API}/gobierno/identidad/vinculos/${vinculo.id}/activar`, {
    headers: { ...headers, "If-Match": `"${vinculo.version}"` },
    data: {},
  });
}

async function obtenerOpciones(request: APIRequestContext, headers: Record<string, string>) {
  const resp = await request.get(`${API}/gobierno/identidad/opciones`, { headers });
  expect(resp.status(), await resp.text()).toBe(200);
  return resp.json();
}

function constantes() {
  return { moneda: "USD", fuenteReferencia: "Publicación oficial de prueba E2E" };
}

test.describe("Gobierno bitácora de procesos", () => {
  test("BIT-E2E-03 · resolución de procesos en la bitácora y auditoría", async ({ request, page }) => {
    test.setTimeout(300_000);
    const { mundo, tipoId, emisorId, objetivoId } = await mundoOcupacion(request);
    const acto = await actoEmitidoApi(request, mundo, tipoId, emisorId, `NUM-PROCESOS-${Date.now()}`);
    const funcionario = await funcionarioApi(request, mundo.headers, "Persona Procesos Bitácora");
    const asignacion = await asignacionApi(request, mundo.headers, {
      funcionario_id: funcionario.id,
      cargo_id: objetivoId,
      acto_id: acto.id,
      fundamento: "Fundamento de prueba para bitácora de procesos",
    });
    const admin = await sesionApi("admintenant", { tenant: TENANT });
    const operador = await crearUsuario(
      request,
      admin.headers,
      [
        "organization:view",
        "gobierno_ocupacion:view",
        "gobierno_ocupacion:manage",
        "gobierno_tasas:view",
        "gobierno_tasas:manage",
        "gobierno_expedientes:view",
      ],
      mundo.companyId,
    );
    const activadorOrg04 = await crearUsuario(request, admin.headers, ["organization:view", "gobierno_ocupacion:view", "gobierno_ocupacion:activate"], mundo.companyId);
    expect((await activarApi(request, activadorOrg04.headers, asignacion)).status()).toBe(200);
    const activadorId = await crearUsuario(request, admin.headers, ACTIVADOR_ID, mundo.companyId);
    const opciones = await obtenerOpciones(request, mundo.headers);
    const cuentaOperador = opciones.cuentas.find((c: { usuario: string; id: string }) => c.usuario === operador.username);
    expect(cuentaOperador).toBeTruthy();
    const vinculo = await registrarVinculoApi(request, mundo.headers, {
      user_id: cuentaOperador.id,
      official_id: funcionario.id,
      desde: hoyCaracas(),
      motivo: "Motivo de vínculo para bitácora de procesos",
    });
    expect((await activarVinculoApi(request, activadorId.headers, vinculo)).status()).toBe(200);

    const { moneda, fuenteReferencia } = constantes();
    const tasaResp = await request.post(`${API}/gobierno/tesoreria/tasas`, {
      headers: operador.headers,
      data: {
        moneda,
        fecha_efectiva: hoyCaracas(),
        valor: "36.5",
        fuente_referencia: fuenteReferencia,
      },
    });
    expect(tasaResp.status(), await tasaResp.text()).toBe(201);
    const reporteResp = await request.get(`${API}/gobierno/contrataciones/reporte.csv`, { headers: operador.headers });
    expect(reporteResp.status(), await reporteResp.text()).toBe(200);

    const auditor = await crearUsuario(request, admin.headers, ["organization:view", "gobierno_auditoria:view"], mundo.companyId);
    await entrarEnGobierno(page, auditor.username, mundo.codigo, "/gobierno/auditoria");
    await page.locator('nav[aria-label="Menú principal"] a[href="/gobierno/bitacora"]').click();
    await expect(page.getByRole("heading", { level: 1, name: "Bitácora institucional" })).toBeVisible();
    await page.locator("#bitacora-accion").selectOption("GOV_OFFICIAL_RATE_CREATED");
    await page.getByRole("button", { name: "Filtrar" }).click();
    const filaTasa = page.getByRole("row").filter({ hasText: operador.username });
    await expect(filaTasa).toHaveCount(1);
    await expect(filaTasa.getByText("Tesorería · Tasas oficiales")).toBeVisible();
    await contextoAccesible(page, page.getByRole("heading", { level: 1, name: "Bitácora institucional" }), "Bitácora TRE-09");
    await filaTasa.getByRole("link").click();
    await page.waitForURL(/\/gobierno\/bitacora\/[0-9a-f-]{36}$/);
    await expect(page.getByText("Proceso", { exact: true })).toBeVisible();
    await expect(page.getByText("Tasas oficiales", { exact: true }).first()).toBeVisible();
    await expect(page.getByText("Módulo", { exact: true })).toBeVisible();
    await expect(page.getByText("Tesorería", { exact: true }).first()).toBeVisible();
    await expect(page.getByText("Actor efectivo", { exact: true })).toBeVisible();
    await expect(page.getByText("Correlación", { exact: true })).toBeVisible();
    await expect(page.getByText("Unidad", { exact: true }).first()).toBeVisible();
    await contextoAccesible(page, page.getByRole("heading", { level: 1 }), "Evento TRE-09");

    await page.goto("/gobierno/bitacora");
    await expect(page.getByRole("heading", { level: 1, name: "Bitácora institucional" })).toBeVisible();
    await page.locator("#bitacora-accion").selectOption("GOV_PROCUREMENT_REPORT_EXPORTED");
    await page.getByRole("button", { name: "Filtrar" }).click();
    const filaReporte = page.getByRole("row").filter({ hasText: operador.username });
    await expect(filaReporte).toHaveCount(1);
    await expect(filaReporte.getByText("Reportes · Reporte de contrataciones")).toBeVisible();

    await page.goto("/gobierno/auditoria");
    await page.locator("#filtro-proceso").selectOption("TRE-09");
    const filaAuditoria = page.getByRole("row").filter({ hasText: "TRE-09 · Tasas oficiales" });
    await expect(filaAuditoria).toHaveCount(1);
    await expect(filaAuditoria.getByText("TRE-09 · Tasas oficiales")).toBeVisible();
    await contextoAccesible(page, page.getByRole("heading", { level: 1 }), "Auditoría filtrada por TRE-09");
  });
});
