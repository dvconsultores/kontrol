import AxeBuilder from "@axe-core/playwright";
import { expect, sesionApi, test } from "./helpers/sesion";
import {
  ANIO,
  API,
  RESPONSABLE_ESTRUCTURA,
  TENANT,
  adjuntarDocumentoApi,
  cargoVigenteApi,
  cerrarNotificaciones,
  crearTipoDocumental,
  crearUsuario,
  enteActivo,
  entrarEnGobierno,
  es2xx,
  estructuraVigenteApi,
  prepararMundo,
} from "./helpers/gobierno";
import type { APIRequestContext, Locator, Page } from "@playwright/test";

const RESPONSABLE_CIERRE = [
  ...RESPONSABLE_ESTRUCTURA,
  "gobierno_cargos:view",
  "gobierno_cargos:edit",
  "gobierno_cargos:publish",
  "gobierno_actos:view",
  "gobierno_actos:edit",
  "gobierno_actos:issue",
  "gobierno_hallazgos:view",
  "gobierno_hallazgos:manage",
  "gobierno_cuentas:view",
  "gobierno_cuentas:manage",
  "gobierno_cuentas:activate",
  "gobierno_caja:view",
  "gobierno_caja:manage",
  "gobierno_caja:activate",
  "gobierno_cierre:view",
  "gobierno_cierre:manage",
  "gobierno_cierre:activate",
];

const VERIFICADOR = [
  "organization:view",
  "gobierno_hallazgos:view",
  "gobierno_hallazgos:verify",
  "documentos:view",
];

const CONSULTA_CIERRE = ["organization:view", "gobierno_cierre:view"];

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
  const mundo = await prepararMundo(request, RESPONSABLE_CIERRE);
  const tipo = await crearTipoDocumental(request, mundo.headers, mundo.companyId);
  await enteActivo(request, mundo.headers, mundo.companyId, tipo.id);
  const estructura = await estructuraVigenteApi(request, mundo.headers, mundo.companyId, tipo.id, ANIO);
  const cargo = await cargoVigenteApi(request, mundo.headers, mundo.companyId, tipo.id, ANIO, estructura.da01Id, "DIR-ADM");
  return { mundo, tipoId: tipo.id, estructura, cargoId: cargo.id };
}

async function actoEmitidoApi(
  request: APIRequestContext,
  mundo: { headers: Record<string, string>; companyId: string },
  tipoId: string,
  cargoId: string,
  numero: string,
): Promise<{ id: string }> {
  const resp = await request.post(`${API}/gobierno/actos`, {
    headers: mundo.headers,
    data: {
      tipo: "RESOLUCION",
      numero,
      caracter: "PARTICULAR",
      asunto: `Asunto ${numero}`,
      simple_tramite: false,
      cargo_id: cargoId,
      fecha: hoyCaracas(),
      lugar: "Caracas",
      fundamento_competencia: "Reglamento interno, art. 12",
      funcionario: "Funcionaria de prueba",
      titularidad: "TITULAR",
      destinatario: "Proveedor de prueba",
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
  return { id };
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

  return { cuentaId, mundo, tipoId, cargoId };
}

async function crearPoliticaCierreApi(
  request: APIRequestContext,
  headers: Record<string, string>,
  nombre: string,
  accionCierre: string,
): Promise<{ id: string; codigo: string; version: number }> {
  const resp = await request.post(`${API}/gobierno/cierres/politicas`, {
    headers,
    data: {
      nombre,
      accion_cierre: accionCierre,
      fundamento: "Fundamento de prueba",
      vigente_desde: hoyCaracas(),
      vigente_hasta: null,
    },
  });
  expect(resp.status(), await resp.text()).toBe(201);
  const body = await resp.json();
  return { id: body.id as string, codigo: body.codigo as string, version: body.version as number };
}

async function crearPoliticaCierreUi(
  page: Page,
  nombre: string,
  accionCierre: string,
  fundamento: string,
): Promise<{ id: string; codigo: string }> {
  await expect(page.getByRole("heading", { level: 1, name: "Controles de cierre" })).toBeVisible();
  await page.getByRole("link", { name: "Nueva política" }).first().click();
  await expect(page.getByRole("heading", { level: 1, name: "Nueva política de cierre" })).toBeVisible();
  await page.getByLabel("Nombre de la política").fill(nombre);
  await page.getByLabel("Acción de cierre").selectOption({ label: accionCierre });
  await page.getByLabel("Fundamento").fill(fundamento);
  await pulsarYEsperar(page, page.getByRole("button", { name: "Crear política" }), "POST", /\/api\/v1\/gobierno\/cierres\/politicas$/);
  const h1 = page.getByRole("heading", { level: 1, name: /^Política PC-\d+$/ });
  await expect(h1).toBeVisible();
  const texto = (await h1.textContent()) as string;
  const codigo = texto.replace("Política ", "");
  return { id: page.url().split("/").pop() as string, codigo };
}

async function anadirControlUi(
  page: Page,
  tipo: string,
  riesgo: string | null,
  materialidad: string,
): Promise<void> {
  await page.getByRole("button", { name: "Añadir control" }).click();
  await page.getByLabel("Tipo").selectOption({ label: tipo });
  if (riesgo) {
    await page.getByLabel("Riesgo mínimo").selectOption({ label: riesgo });
  }
  await page.getByLabel("Materialidad").fill(materialidad);
  await pulsarYEsperar(page, page.getByRole("button", { name: "Guardar" }), "POST", /\/api\/v1\/gobierno\/cierres\/politicas\/[0-9a-f-]{36}\/controles$/);
}

async function activarPoliticaUi(page: Page): Promise<void> {
  await pulsarYEsperar(page, page.getByRole("button", { name: "Activar" }), "POST", /\/api\/v1\/gobierno\/cierres\/politicas\/[0-9a-f-]{36}\/activar$/);
  await expect(page.getByRole("main").locator("p", { hasText: /^Vigente/ })).toBeVisible();
}

async function crearHallazgoApi(
  request: APIRequestContext,
  headers: Record<string, string>,
  titulo: string,
): Promise<{ id: string; version: number }> {
  const resp = await request.post(`${API}/gobierno/hallazgos`, {
    headers,
    data: {
      titulo,
      condicion: "Condición observada en la prueba",
      criterio: "Criterio normativo aplicable",
      causa: "Causa raíz identificada",
      efecto: "Efecto material del hallazgo",
      riesgo: "ALTO",
      origen: "INDEPENDIENTE",
      origen_descripcion: "Prueba de controles de cierre",
    },
  });
  expect(resp.status(), await resp.text()).toBe(201);
  const body = await resp.json();
  return { id: body.id as string, version: body.version as number };
}

async function recomendacionApi(
  request: APIRequestContext,
  headers: Record<string, string>,
  hallazgoId: string,
  version: number,
): Promise<{ id: string; version: number }> {
  const resp = await request.post(`${API}/gobierno/hallazgos/${hallazgoId}/recomendaciones`, {
    headers: { ...headers, "If-Match": `"${version}"` },
    data: { texto: "Recomendación de prueba" },
  });
  expect(resp.status(), await resp.text()).toBe(201);
  const body = await resp.json();
  return { id: body.recomendaciones[0].id as string, version: body.version as number };
}

async function accionApi(
  request: APIRequestContext,
  headers: Record<string, string>,
  hallazgoId: string,
  version: number,
  recomendacionId: string,
  cargoId: string,
): Promise<{ id: string; version: number }> {
  const resp = await request.post(`${API}/gobierno/hallazgos/${hallazgoId}/acciones`, {
    headers: { ...headers, "If-Match": `"${version}"` },
    data: {
      recomendacion_id: recomendacionId,
      descripcion: "Acción de prueba",
      cargo_id: cargoId,
      fecha_objetivo: hoyCaracas(),
    },
  });
  expect(resp.status(), await resp.text()).toBe(201);
  const body = await resp.json();
  return { id: body.acciones[0].id as string, version: body.version as number };
}

async function planApi(
  request: APIRequestContext,
  headers: Record<string, string>,
  hallazgoId: string,
  version: number,
): Promise<{ version: number }> {
  const resp = await request.post(`${API}/gobierno/hallazgos/${hallazgoId}/plan`, {
    headers: { ...headers, "If-Match": `"${version}"` },
    data: {},
  });
  expect(resp.status(), await resp.text()).toBe(200);
  return { version: (await resp.json()).version as number };
}

async function ejecucionApi(
  request: APIRequestContext,
  headers: Record<string, string>,
  hallazgoId: string,
  version: number,
): Promise<{ version: number }> {
  const resp = await request.post(`${API}/gobierno/hallazgos/${hallazgoId}/ejecucion`, {
    headers: { ...headers, "If-Match": `"${version}"` },
    data: {},
  });
  expect(resp.status(), await resp.text()).toBe(200);
  return { version: (await resp.json()).version as number };
}

async function avanceApi(
  request: APIRequestContext,
  headers: Record<string, string>,
  hallazgoId: string,
  version: number,
  accionId: string,
  documentoId: string,
): Promise<{ version: number }> {
  const resp = await request.post(`${API}/gobierno/hallazgos/${hallazgoId}/acciones/${accionId}/avances`, {
    headers: { ...headers, "If-Match": `"${version}"` },
    data: { nota: "Avance de prueba", porcentaje: 100, documento_id: documentoId },
  });
  expect(resp.status(), await resp.text()).toBe(201);
  return { version: (await resp.json()).version as number };
}

async function presentarApi(
  request: APIRequestContext,
  headers: Record<string, string>,
  hallazgoId: string,
  version: number,
): Promise<{ version: number }> {
  const resp = await request.post(`${API}/gobierno/hallazgos/${hallazgoId}/presentar`, {
    headers: { ...headers, "If-Match": `"${version}"` },
    data: {},
  });
  expect(resp.status(), await resp.text()).toBe(200);
  return { version: (await resp.json()).version as number };
}

async function verificarApi(
  request: APIRequestContext,
  headers: Record<string, string>,
  hallazgoId: string,
  version: number,
): Promise<void> {
  const resp = await request.post(`${API}/gobierno/hallazgos/${hallazgoId}/verificar`, {
    headers: { ...headers, "If-Match": `"${version}"` },
    data: { nota: "Verificación de prueba" },
  });
  expect(resp.status(), await resp.text()).toBe(200);
}

async function politicaVigenteApi(
  request: APIRequestContext,
  headers: Record<string, string>,
  nombre: string,
  accionApi: string,
  control: { tipo: string; riesgo_minimo: string | null; materialidad: string },
): Promise<{ id: string; codigo: string }> {
  const politica = await crearPoliticaCierreApi(request, headers, nombre, accionApi);
  const controlesResp = await request.post(`${API}/gobierno/cierres/politicas/${politica.id}/controles`, {
    headers: { ...headers, "If-Match": `"${politica.version}"` },
    data: control,
  });
  expect(controlesResp.status(), await controlesResp.text()).toBe(201);
  const controlVersion = (await controlesResp.json()).version as number;
  const activarResp = await request.post(`${API}/gobierno/cierres/politicas/${politica.id}/activar`, {
    headers: { ...headers, "If-Match": `"${controlVersion}"` },
    data: {},
  });
  expect(activarResp.status(), await activarResp.text()).toBe(200);
  return { id: politica.id, codigo: politica.codigo };
}

test.describe("Gobierno · Controles de cierre (CTL-10)", () => {
  test("CIE-E2E-01 · estructura bloqueada y resuelta por verificación real", async ({ page, request }) => {
    test.setTimeout(300_000);
    const { mundo, tipoId, cargoId } = await mundoConCargo(request);
    await estructuraVigenteApi(request, mundo.headers, mundo.companyId, tipoId, ANIO - 1);

    await entrarEnGobierno(page, mundo.username, mundo.codigo, "/gobierno/cierres");
    await crearPoliticaCierreUi(
      page,
      "Cierre de estructura con hallazgos",
      "Cerrar estructura del ejercicio",
      "Fundamento de prueba",
    );
    await anadirControlUi(page, "Hallazgos abiertos", "Medio o superior", "El control evidencia el riesgo material pendiente.");
    await activarPoliticaUi(page);

    const hallazgo = await crearHallazgoApi(request, mundo.headers, "Hallazgo CTL-10");
    const hallazgoId = hallazgo.id;

    await page.goto(`/gobierno/estructura/${ANIO - 1}`);
    await expect(page.getByRole("heading", { level: 1, name: `Estructura organizativa ${ANIO - 1}` })).toBeVisible();
    await page.getByRole("button", { name: "Cerrar ejercicio" }).click();
    await expect(page.getByRole("dialog")).toBeVisible();
    const [resp409] = await Promise.all([
      page.waitForResponse((r) => r.request().method() === "POST" && new RegExp(`/api/v1/gobierno/estructuras/${ANIO - 1}/cerrar$`).test(new URL(r.url()).pathname), { timeout: 60_000 }),
      page.getByRole("dialog").getByRole("button", { name: "Cerrar ejercicio" }).click(),
    ]);
    expect(resp409.status()).toBe(409);
    const alert = page.getByRole("alert");
    await expect(alert).toContainText("Cierre bloqueado por control material");
    await expect(alert).toContainText("Hallazgo CTL-10");
    await expect(alert).toContainText("Control Interno");
    await expect(page.getByRole("link", { name: /Hallazgo CTL-10/ })).toHaveAttribute("href", `/gobierno/hallazgos/${hallazgoId}`);

    await page.goto("/gobierno/cierres/bloqueos");
    await expect(page.getByRole("heading", { level: 1, name: "Cierres bloqueados" })).toBeVisible();
    await expect(page.getByRole("region", { name: /Tabla/ })).toContainText(`EST-${ANIO - 1}`);

    let version = hallazgo.version;
    const recomendacion = await recomendacionApi(request, mundo.headers, hallazgoId, version);
    version = recomendacion.version;
    const accion = await accionApi(request, mundo.headers, hallazgoId, version, recomendacion.id, cargoId);
    version = accion.version;
    const plan = await planApi(request, mundo.headers, hallazgoId, version);
    version = plan.version;
    const ejecucion = await ejecucionApi(request, mundo.headers, hallazgoId, version);
    version = ejecucion.version;
    await adjuntarDocumentoApi(request, mundo.headers, mundo.companyId, tipoId, "GovernmentCorrectiveAction", accion.id);
    const docsResp = await request.get(`${API}/documentos/por-recurso/GovernmentCorrectiveAction/${accion.id}`, { headers: mundo.headers });
    expect(docsResp.status(), await docsResp.text()).toBe(200);
    const docs = await docsResp.json();
    const avance = await avanceApi(request, mundo.headers, hallazgoId, version, accion.id, docs[0].id);
    version = avance.version;
    const presentado = await presentarApi(request, mundo.headers, hallazgoId, version);
    version = presentado.version;

    const admin = await sesionApi("admintenant", { tenant: TENANT });
    const verificador = await crearUsuario(request, admin.headers, VERIFICADOR, mundo.companyId);
    await verificarApi(request, verificador.headers, hallazgoId, version);

    await page.goto(`/gobierno/estructura/${ANIO - 1}`);
    await expect(page.getByRole("heading", { level: 1, name: `Estructura organizativa ${ANIO - 1}` })).toBeVisible();
    await page.getByRole("button", { name: "Cerrar ejercicio" }).click();
    await expect(page.getByRole("dialog")).toBeVisible();
    const [resp200] = await Promise.all([
      page.waitForResponse((r) => r.request().method() === "POST" && new RegExp(`/api/v1/gobierno/estructuras/${ANIO - 1}/cerrar$`).test(new URL(r.url()).pathname), { timeout: 60_000 }),
      page.getByRole("dialog").getByRole("button", { name: "Cerrar ejercicio" }).click(),
    ]);
    expect(resp200.status()).toBe(200);
    await expect(page.getByRole("heading", { level: 1, name: `Estructura organizativa ${ANIO - 1}` })).toBeVisible();
    await expect(page.getByRole("button", { name: "Cerrar ejercicio" })).toHaveCount(0);
  });

  test("CIE-E2E-02 · programa bloqueado por actos sin eficacia, retiro de política y cierre", async ({ page, request }) => {
    test.setTimeout(300_000);
    const { cuentaId, mundo, tipoId, cargoId } = await cuentaVigenteUi(page, request);

    await page.locator('nav[aria-label="Menú principal"] a[href="/gobierno/tesoreria/rubros"]').click();
    await expect(page.getByRole("heading", { level: 1, name: "Rubros de caja" })).toBeVisible();
    await page.getByLabel(/^Código/).fill("PF-ING");
    await page.getByLabel(/^Nombre/).fill("Ingreso PF");
    await page.getByLabel(/^Tipo/).selectOption("INGRESO");
    await pulsarYEsperar(page, page.getByRole("button", { name: "Registrar rubro" }), "POST", /\/api\/v1\/gobierno\/tesoreria\/rubros$/);

    await page.locator('nav[aria-label="Menú principal"] a[href="/gobierno/tesoreria/programacion"]').click();
    await expect(page.getByRole("heading", { level: 1, name: "Programación financiera" })).toBeVisible();
    await page.getByRole("link", { name: "Nuevo programa" }).first().click();
    await expect(page.getByRole("heading", { level: 1, name: "Nuevo programa" })).toBeVisible();
    await page.getByLabel(/^Ejercicio/).fill(String(ANIO));
    await page.getByLabel(/^Moneda/).selectOption("VES");
    await page.getByLabel("Mes inicial").selectOption({ label: "Enero" });
    await pulsarYEsperar(page, page.getByRole("button", { name: "Registrar programa" }), "POST", /\/api\/v1\/gobierno\/tesoreria\/programas$/);
    await expect(page.getByRole("heading", { level: 1, name: `Programa PF-${ANIO}-VES` })).toBeVisible();
    const programaId = page.url().split("/").pop() as string;

    await page.getByRole("button", { name: "Declarar" }).click();
    await page.getByLabel(/^Cuenta/).selectOption({ value: cuentaId });
    await page.getByLabel(/^Monto/).fill("1000.00");
    await page.getByLabel(/^Fecha de corte/).fill(hoyCaracas());
    await page.getByLabel(/^Fundamento/).fill("Fundamento legal de programación");
    await pulsarYEsperar(page, page.getByRole("button", { name: "Registrar declaración" }), "POST", new RegExp(`/api/v1/gobierno/tesoreria/programas/${programaId}/declaraciones$`));

    await page.getByRole("button", { name: "Añadir línea" }).first().click();
    await page.getByLabel(/^Mes\b/).selectOption({ label: "Enero" });
    await page.getByLabel(/^Rubro/).selectOption({ label: "PF-ING · Ingreso PF" });
    await page.getByLabel(/^Monto/).fill("500.00");
    await pulsarYEsperar(page, page.getByRole("button", { name: "Añadir línea" }).last(), "POST", new RegExp(`/api/v1/gobierno/tesoreria/programas/${programaId}/lineas$`));

    await pulsarYEsperar(page, page.getByRole("button", { name: "Activar versión" }), "POST", new RegExp(`/api/v1/gobierno/tesoreria/programas/${programaId}/activar$`));
    await expect(page.getByRole("main").locator("p", { hasText: /^Vigente/ })).toBeVisible();

    const politica = await politicaVigenteApi(request, mundo.headers, "Cierre de programa con actos sin eficacia", "TRE02_CERRAR_PROGRAMA", {
      tipo: "ACTOS_SIN_EFICACIA",
      riesgo_minimo: null,
      materialidad: "El control evidencia el riesgo material pendiente.",
    });

    await actoEmitidoApi(request, mundo, tipoId, cargoId, `TRE-ACT-${Date.now()}`);

    await page.goto(`/gobierno/tesoreria/programacion/${programaId}`);
    await page.getByRole("button", { name: "Cerrar programa" }).click();
    await page.getByLabel(/^Motivo/).fill("Motivo de prueba válido");
    const [resp409] = await Promise.all([
      page.waitForResponse((r) => r.request().method() === "POST" && new RegExp(`/api/v1/gobierno/tesoreria/programas/${programaId}/cerrar$`).test(new URL(r.url()).pathname), { timeout: 60_000 }),
      page.getByRole("button", { name: "Confirmar cierre" }).click(),
    ]);
    expect(resp409.status()).toBe(409);
    const alert = page.getByRole("alert");
    await expect(alert).toContainText("Actos sin eficacia");

    await page.goto(`/gobierno/cierres/${politica.id}`);
    await expect(page.getByRole("heading", { level: 1, name: /^Política PC-\d+$/ })).toBeVisible();
    await page.getByRole("button", { name: "Retirar" }).click();
    await page.getByLabel(/^Motivo/).fill("Motivo de retiro");
    await pulsarYEsperar(page, page.getByRole("button", { name: "Confirmar retiro" }), "POST", /\/api\/v1\/gobierno\/cierres\/politicas\/[0-9a-f-]{36}\/retirar$/);
    await expect(page.getByRole("main").locator("p", { hasText: /^Retirada/ })).toBeVisible();

    await page.goto(`/gobierno/tesoreria/programacion/${programaId}`);
    await page.getByRole("button", { name: "Cerrar programa" }).click();
    await page.getByLabel(/^Motivo/).fill("Motivo de cierre válido");
    const [resp200] = await Promise.all([
      page.waitForResponse((r) => r.request().method() === "POST" && new RegExp(`/api/v1/gobierno/tesoreria/programas/${programaId}/cerrar$`).test(new URL(r.url()).pathname), { timeout: 60_000 }),
      page.getByRole("button", { name: "Confirmar cierre" }).click(),
    ]);
    expect(resp200.status()).toBe(200);
    await expect(page.getByRole("main").locator("p", { hasText: /^Cerrado/ })).toBeVisible();
  });

  test("CIE-E2E-03 · negativas y accesibilidad", async ({ page, request, browser }) => {
    test.setTimeout(240_000);
    const { mundo } = await mundoConCargo(request);

    const vigente = await politicaVigenteApi(
      request,
      mundo.headers,
      "Cierre de estructura vigente",
      "ORG02_CERRAR_ESTRUCTURA",
      {
        tipo: "HALLAZGOS_ABIERTOS",
        riesgo_minimo: "MEDIO",
        materialidad: "El control evidencia el riesgo material pendiente.",
      },
    );

    const borrador = await crearPoliticaCierreApi(
      request,
      mundo.headers,
      "Cierre de estructura borrador",
      "ORG02_CERRAR_ESTRUCTURA",
    );

    const controlResponse = await request.post(
      `${API}/gobierno/cierres/politicas/${borrador.id}/controles`,
      {
        headers: {
          ...mundo.headers,
          "If-Match": `"${borrador.version}"`,
        },
        data: {
          tipo: "HALLAZGOS_ABIERTOS",
          riesgo_minimo: "MEDIO",
          materialidad: "El control evidencia el riesgo material pendiente.",
        },
      },
    );
    expect(controlResponse.status()).toBe(201);

    await entrarEnGobierno(page, mundo.username, mundo.codigo, "/gobierno/cierres");
    await page.goto(`/gobierno/cierres/${borrador.id}`);
    await expect(page.getByRole("heading", { level: 1, name: `Política ${borrador.codigo}` })).toBeVisible();

    await page.getByRole("button", { name: "Activar", exact: true }).click();

    await expect(page.getByRole("alert")).toContainText(
      "Ya hay una política vigente para esa acción de cierre.",
    );

    // Usuario de consulta
    const admin = await sesionApi("admintenant", { tenant: TENANT });
    const consulta = await crearUsuario(request, admin.headers, CONSULTA_CIERRE, mundo.companyId);

    const context2 = await browser.newContext();
    const page2 = await context2.newPage();
    await entrarEnGobierno(page2, consulta.username, mundo.codigo, "/gobierno/cierres");
    await expect(page2.getByRole("heading", { level: 1, name: "Controles de cierre" })).toBeVisible();
    await expect(page2.getByRole("link", { name: "Nueva política" })).toHaveCount(0);
    await page2.getByRole("link", { name: `Abrir la política ${vigente.codigo}` }).click();
    await expect(page2.getByRole("heading", { level: 1, name: `Política ${vigente.codigo}` })).toBeVisible();
    await expect(page2.getByRole("button", { name: "Activar" })).toHaveCount(0);
    await expect(page2.getByRole("button", { name: "Retirar" })).toHaveCount(0);
    await context2.close();

    // Accesibilidad
    const pantallas: Array<[string, string]> = [
      ["/gobierno/cierres", "Controles de cierre"],
      ["/gobierno/cierres/nueva", "Nueva política de cierre"],
      [`/gobierno/cierres/${borrador.id}`, `Política ${borrador.codigo}`],
      ["/gobierno/cierres/bloqueos", "Cierres bloqueados"],
    ];

    for (const [ruta, titulo] of pantallas) {
      await page.setViewportSize({ width: 1280, height: 768 });
      await page.goto(ruta);
      await expect(page.getByRole("heading", { level: 1, name: titulo })).toBeVisible();

      for (const ancho of [1280, 768, 320]) {
        await page.setViewportSize({ width: ancho, height: 768 });
        await expect(page.getByRole("heading", { level: 1, name: titulo })).toBeVisible();
        await sinViolacionesSerias(page, `${titulo} ${ancho}x768`);
      }
    }
  });
});
