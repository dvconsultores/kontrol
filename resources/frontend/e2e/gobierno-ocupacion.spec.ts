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
  cerrarNotificaciones,
  crearTipoDocumental,
  crearUsuario,
  enteActivo,
  entrarEnGobierno,
  es2xx,
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
];
const ACTIVADOR = [
  "organization:view",
  "gobierno_ocupacion:view",
  "gobierno_ocupacion:activate",
  "gobierno_ocupacion:revoke",
  "gobierno_actos:view",
];
const CONSULTA = ["organization:view", "gobierno_ocupacion:view"];

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
  },
): Promise<{ id: string; version: string }> {
  const resp = await request.post(`${API}/gobierno/ocupacion/asignaciones`, {
    headers,
    data: {
      funcionario_id: datos.funcionario_id,
      cargo_id: datos.cargo_id,
      figura: "TITULAR",
      acto_id: datos.acto_id,
      desde: hoyCaracas(),
      fundamento: datos.fundamento,
      cargo_origen_id: null,
      hasta: null,
      rendicion: null,
      maxima_autoridad: false,
      autorizacion_concejo: null,
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
  for (const ancho of [1280, 768, 320]) {
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
  return { mundo, tipoId: tipo.id, emisorId: emisor.id, objetivoId: objetivo.id };
}

test.describe("Gobierno ocupación", () => {
  test("OCU-E2E-01 · recorrido completo", async ({ request, browser, page }) => {
    test.setTimeout(240_000);
    const { mundo, tipoId, emisorId, objetivoId } = await mundoOcupacion(request);

    const acto = await actoEmitidoApi(request, mundo, tipoId, emisorId, `NUM-${Date.now()}`);
    const actoRevocacion = await actoEmitidoApi(request, mundo, tipoId, emisorId, `REV-${Date.now()}`);

    const admin = await sesionApi("admintenant", { tenant: TENANT });
    const activador = await crearUsuario(request, admin.headers, ACTIVADOR, mundo.companyId);

    await entrarEnGobierno(page, mundo.username, mundo.codigo, "/gobierno/ocupacion");
    await expect(page.getByRole("heading", { level: 1, name: "Ocupación de cargos" })).toBeVisible();

    await page.locator('nav[aria-label="Menú principal"] a[href="/gobierno/ocupacion"]').click();
    await page.getByRole("link", { name: "Funcionarios", exact: true }).click();
    const nombreFuncionario = "Persona Uno Prueba";
    const numeroDocumento = String(Math.floor(10000000 + Math.random() * 89999999));
    await page.getByLabel("Nombre completo").fill(nombreFuncionario);
    await page.getByLabel("Tipo de documento").selectOption("V");
    await page.getByLabel("Número de documento").fill(numeroDocumento);
    await pulsarYEsperar(page, page.getByRole("button", { name: "Registrar funcionario" }), "POST", /\/funcionarios$/);
    await expect(page.getByRole("cell", { name: nombreFuncionario, exact: true })).toBeVisible();
    await expect(page.getByText(numeroDocumento, { exact: true })).toHaveCount(0);

    await page.locator('nav[aria-label="Menú principal"] a[href="/gobierno/ocupacion"]').click();
    await page.getByRole("link", { name: "Nueva asignación" }).click();
    await page.locator("#asignacion-figura").selectOption("TITULAR");
    await page.locator("#asignacion-funcionario").selectOption({ index: 1 });
    await page.locator("#asignacion-cargo").selectOption({ value: objetivoId });
    await page.locator("#asignacion-acto").selectOption({ value: acto.id });
    await page.locator("#asignacion-desde").fill(hoyCaracas());
    await page.locator("#asignacion-fundamento").fill("Fundamento de prueba con más de diez caracteres");
    await pulsarYEsperar(page, page.getByRole("button", { name: "Guardar borrador" }), "POST", /\/asignaciones$/);
    await expect(page.getByText("Borrador", { exact: true }).first()).toBeVisible();
    const url = page.url();
    const asignacionId = url.split("/").pop();
    expect(asignacionId).toBeTruthy();
    await expect(page.getByRole("button", { name: "Activar" })).toHaveCount(0);

    const contexto = await browser.newContext();
    const pagina2 = await contexto.newPage();
    await entrarEnGobierno(pagina2, activador.username, mundo.codigo, "/gobierno/ocupacion");
    await pagina2.locator('nav[aria-label="Menú principal"] a[href="/gobierno/ocupacion"]').click();
    await pagina2.getByRole("link", { name: "Asignaciones", exact: true }).click();
    await pagina2.locator(`a[href="/gobierno/ocupacion/asignaciones/${asignacionId}"]`).click();
    await pulsarYEsperar(pagina2, pagina2.getByRole("button", { name: "Activar" }), "POST", /\/activar$/);
    await expect(pagina2.getByText("Vigente", { exact: true }).first()).toBeVisible();

    await pagina2.locator('nav[aria-label="Menú principal"] a[href="/gobierno/ocupacion"]').click();
    await expect(pagina2.getByRole("cell", { name: new RegExp(nombreFuncionario) }).first()).toBeVisible();
    await expect(pagina2.getByRole("cell", { name: "Cubierto", exact: true })).toBeVisible();
    await pagina2.locator(`a[href^="/gobierno/ocupacion/cargos/${objetivoId}"]`).first().click();
    await expect(pagina2.getByRole("link", { name: new RegExp(acto.numero) }).first()).toBeVisible();

    await pagina2.locator(`a[href="/gobierno/ocupacion/asignaciones/${asignacionId}"]`).first().click();
    await pagina2.getByRole("button", { name: "Revocar" }).click();
    await pagina2.getByLabel("Acto de revocación").selectOption({ value: actoRevocacion.id });
    await pagina2.getByLabel("Fecha").fill(hoyCaracas());
    await pagina2.getByLabel("Motivo").fill("Motivo de revocación de pruebas");
    const enviar = pagina2.getByRole("button", { name: "Revocar" }).last();
    await pulsarYEsperar(pagina2, enviar, "POST", /\/revocar$/);
    await expect(pagina2.getByRole("cell", { name: "Revocada", exact: true }).first()).toBeVisible();
    await expect(pagina2.getByRole("cell", { name: "Registrada", exact: true }).first()).toBeVisible();
    await expect(pagina2.getByRole("cell", { name: "Activada", exact: true }).first()).toBeVisible();
    await expect(pagina2.getByRole("cell", { name: "Revocada", exact: true }).first()).toBeVisible();

    await pagina2.locator('nav[aria-label="Menú principal"] a[href="/gobierno/ocupacion"]').click();
    await pagina2.locator(`a[href^="/gobierno/ocupacion/cargos/${objetivoId}"]`).first().click();
    await expect(pagina2.locator("#cargo-fecha")).toBeVisible();
    const manana = new Date(Date.now() + 86_400_000 * 2).toISOString().slice(0, 10);
    await pagina2.locator("#cargo-fecha").fill(manana);
    await expect(pagina2.getByRole("cell", { name: "Revocada", exact: true }).first()).toBeVisible();

    await pagina2.locator('nav[aria-label="Menú principal"] a[href="/gobierno/ocupacion"]').click();
    await pagina2.getByRole("link", { name: "Asignaciones", exact: true }).click();
    const descargaPromise = pagina2.waitForEvent("download");
    await pagina2.getByRole("button", { name: "Exportar CSV" }).click();
    const descarga = await descargaPromise;
    expect(descarga.suggestedFilename().endsWith(".csv")).toBe(true);

    await contexto.close();
  });

  test("OCU-E2E-02 · negativas", async ({ request, browser }) => {
    test.setTimeout(240_000);
    const { mundo, tipoId, emisorId, objetivoId } = await mundoOcupacion(request);
    const admin = await sesionApi("admintenant", { tenant: TENANT });
    const activador = await crearUsuario(request, admin.headers, ACTIVADOR, mundo.companyId);
    const consulta = await crearUsuario(request, admin.headers, CONSULTA, mundo.companyId);

    const acto = await actoEmitidoApi(request, mundo, tipoId, emisorId, `CON-${Date.now()}`);

    // (a) consulta
    const funcionarioConsulta = await funcionarioApi(request, mundo.headers, "Persona Consulta Prueba");
    const asignacionConsulta = await asignacionApi(request, mundo.headers, {
      funcionario_id: funcionarioConsulta.id,
      cargo_id: objetivoId,
      acto_id: acto.id,
      fundamento: "Fundamento de prueba para consulta",
    });
    const activarConsultaResp = await activarApi(request, activador.headers, asignacionConsulta);
    expect(activarConsultaResp.status(), await activarConsultaResp.text()).toBe(200);

    const contextoConsulta = await browser.newContext();
    const paginaConsulta = await contextoConsulta.newPage();
    await entrarEnGobierno(paginaConsulta, consulta.username, mundo.codigo, "/gobierno/ocupacion");
    await expect(paginaConsulta.getByRole("link", { name: "Nueva asignación" })).toHaveCount(0);
    await paginaConsulta.locator('nav[aria-label="Menú principal"] a[href="/gobierno/ocupacion"]').click();
    await paginaConsulta.getByRole("link", { name: "Asignaciones", exact: true }).click();
    await paginaConsulta.locator(`a[href="/gobierno/ocupacion/asignaciones/${asignacionConsulta.id}"]`).click();
    await expect(paginaConsulta.getByRole("button", { name: "Activar" })).toHaveCount(0);
    await expect(paginaConsulta.getByRole("button", { name: "Revocar" })).toHaveCount(0);
    await expect(paginaConsulta.getByRole("button", { name: "Finalizar" })).toHaveCount(0);
    await contextoConsulta.close();

    // (b) self activation
    const responsableSelf = await crearUsuario(request, admin.headers, [...RESPONSABLE, "gobierno_ocupacion:activate"], mundo.companyId);
    const funcionarioSelf = await funcionarioApi(request, mundo.headers, "Persona Self Prueba");
    const asignacionSelf = await asignacionApi(request, responsableSelf.headers, {
      funcionario_id: funcionarioSelf.id,
      cargo_id: objetivoId,
      acto_id: acto.id,
      fundamento: "Fundamento de prueba para self activation",
    });
    const activarSelfResp = await activarApi(request, responsableSelf.headers, asignacionSelf);
    expect(activarSelfResp.status()).toBe(403);
    const activarSelfData = await activarSelfResp.json();
    expect(activarSelfData.code).toBe("GOV_ASSIGNMENT_SELF_ACTIVATION");

    // (c) acto solo emitido
    const actoSoloEmitido = await request.post(`${API}/gobierno/actos`, {
      headers: mundo.headers,
      data: {
        tipo: "RESOLUCION",
        numero: `NOEFICAZ-${Date.now()}`,
        caracter: "GENERAL",
        asunto: "Acto sin eficacia",
        simple_tramite: false,
        cargo_id: emisorId,
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
    expect(actoSoloEmitido.status(), await actoSoloEmitido.text()).toBe(201);
    const actoSoloEmitidoId = (await actoSoloEmitido.json()).id as string;
    await adjuntarDocumentoApi(request, mundo.headers, mundo.companyId, tipoId, "GovernmentAct", actoSoloEmitidoId);
    const docsSoloEmitidoResp = await request.get(`${API}/documentos/por-recurso/GovernmentAct/${actoSoloEmitidoId}`, { headers: mundo.headers });
    expect(docsSoloEmitidoResp.status(), await docsSoloEmitidoResp.text()).toBe(200);
    const docsSoloEmitido = await docsSoloEmitidoResp.json();
    const emitirSoloEmitidoResp = await request.post(`${API}/gobierno/actos/${actoSoloEmitidoId}/emitir`, {
      headers: { ...mundo.headers, "If-Match": '"1"' },
      data: { documento_acto_id: docsSoloEmitido[0].id },
    });
    expect(emitirSoloEmitidoResp.status(), await emitirSoloEmitidoResp.text()).toBe(200);

    const funcionarioNoEficaz = await funcionarioApi(request, mundo.headers, "Persona No Eficaz Prueba");
    const respNoEficaz = await request.post(`${API}/gobierno/ocupacion/asignaciones`, {
      headers: mundo.headers,
      data: {
        funcionario_id: funcionarioNoEficaz.id,
        cargo_id: objetivoId,
        figura: "TITULAR",
        acto_id: actoSoloEmitidoId,
        desde: hoyCaracas(),
        fundamento: "Fundamento de prueba para no eficaz",
        cargo_origen_id: null,
        hasta: null,
        rendicion: null,
        maxima_autoridad: false,
        autorizacion_concejo: null,
        declara_delegable: false,
        competencias: [],
      },
    });
    if (respNoEficaz.status() === 201) {
      const asignacionNoEficaz = await respNoEficaz.json();
      const activarNoEficazResp = await activarApi(request, activador.headers, asignacionNoEficaz);
      expect(activarNoEficazResp.status()).toBe(422);
      const activarNoEficazData = await activarNoEficazResp.json();
      expect(activarNoEficazData.code).toBe("GOV_ASSIGNMENT_ACT_INVALID");
    } else {
      expect(respNoEficaz.status()).toBe(422);
      const respNoEficazData = await respNoEficaz.json();
      expect(respNoEficazData.code).toBe("GOV_ASSIGNMENT_ACT_INVALID");
    }

    // (d) otro ente
    const otro = await prepararMundo(request, ["organization:view", "gobierno_ocupacion:view"]);
    const respOtro = await request.get(`${API}/gobierno/ocupacion/asignaciones/${asignacionConsulta.id}`, {
      headers: otro.headers,
    });
    expect(respOtro.status()).toBe(404);

    // (e) doble titular
    const funcionarioDoble = await funcionarioApi(request, mundo.headers, "Persona Doble Prueba");
    const asignacionDoble = await asignacionApi(request, mundo.headers, {
      funcionario_id: funcionarioDoble.id,
      cargo_id: objetivoId,
      acto_id: acto.id,
      fundamento: "Fundamento de prueba para doble titular",
    });
    const activarDobleResp = await activarApi(request, activador.headers, asignacionDoble);
    expect(activarDobleResp.status()).toBe(409);
    const activarDobleData = await activarDobleResp.json();
    expect(activarDobleData.code).toBe("GOV_ASSIGNMENT_OVERLAP");
  });

  test("OCU-E2E-03 · accesibilidad", async ({ request, page }) => {
    test.setTimeout(240_000);
    const { mundo, tipoId, emisorId, objetivoId } = await mundoOcupacion(request);
    const admin = await sesionApi("admintenant", { tenant: TENANT });
    const activador = await crearUsuario(request, admin.headers, ACTIVADOR, mundo.companyId);
    const todoUsuario = await crearUsuario(request, admin.headers, [...RESPONSABLE, "gobierno_ocupacion:activate", "gobierno_ocupacion:revoke"], mundo.companyId);

    const acto = await actoEmitidoApi(request, mundo, tipoId, emisorId, `ACC-${Date.now()}`);

    const funcionario = await funcionarioApi(request, mundo.headers, "Persona Uno Prueba");
    const asignacion = await asignacionApi(request, mundo.headers, {
      funcionario_id: funcionario.id,
      cargo_id: objetivoId,
      acto_id: acto.id,
      fundamento: "Fundamento de prueba para accesibilidad",
    });
    const activarResp = await activarApi(request, activador.headers, asignacion);
    expect(activarResp.status(), await activarResp.text()).toBe(200);

    await entrarEnGobierno(page, todoUsuario.username, mundo.codigo, "/gobierno/ocupacion");
    await expect(page.getByRole("heading", { level: 1, name: "Ocupación de cargos" })).toBeVisible();

    await page.locator('nav[aria-label="Menú principal"] a[href="/gobierno/ocupacion"]').click();
    await page.locator(`a[href^="/gobierno/ocupacion/cargos/${objetivoId}"]`).first().click();
    await contextoAccesible(page, page.getByRole("heading", { level: 1 }), "Detalle de cargo");

    await page.locator('nav[aria-label="Menú principal"] a[href="/gobierno/ocupacion"]').click();
    await page.getByRole("link", { name: "Asignaciones", exact: true }).click();
    await contextoAccesible(page, page.getByRole("heading", { level: 1, name: "Asignaciones" }), "Asignaciones");

    await page.locator(`a[href="/gobierno/ocupacion/asignaciones/${asignacion.id}"]`).click();
    await page.getByRole("button", { name: "Revocar" }).click();
    await contextoAccesible(page, page.getByRole("heading", { level: 1 }), "Detalle de asignación con panel Revocar");

    await page.locator('nav[aria-label="Menú principal"] a[href="/gobierno/ocupacion"]').click();
    await page.getByRole("link", { name: "Nueva asignación" }).click();
    await contextoAccesible(page, page.getByRole("heading", { level: 1 }), "Formulario nueva asignación");

    await page.locator('nav[aria-label="Menú principal"] a[href="/gobierno/ocupacion"]').click();
    await page.getByRole("link", { name: "Funcionarios", exact: true }).click();
    await contextoAccesible(page, page.getByRole("heading", { level: 1, name: "Funcionarios" }), "Funcionarios");

    await page.locator(`a[href="/gobierno/ocupacion/funcionarios/${funcionario.id}"]`).click();
    await contextoAccesible(page, page.getByRole("heading", { level: 1 }), "Ficha de funcionario");

    await page.locator('nav[aria-label="Menú principal"] a[href="/gobierno/ocupacion"]').click();
    await page.getByRole("link", { name: "Nueva asignación" }).click();
    await page.getByRole("button", { name: "Guardar borrador" }).click();
    await expect(page.getByRole("alert").first()).toBeVisible();
    await contextoAccesible(page, page.getByRole("heading", { level: 1 }), "Formulario nueva asignación con error de validación");

    await page.route("**/api/v1/gobierno/ocupacion/cargos*", (route) => route.fulfill({ status: 500, body: "error" }));
    await page.locator('nav[aria-label="Menú principal"] a[href="/gobierno/ocupacion"]').click();
    await page.locator("#ocupacion-fecha").fill("2025-01-15");
    await expect(page.getByRole("button", { name: "Reintentar" })).toBeVisible();
    await contextoAccesible(page, page.getByRole("button", { name: "Reintentar" }), "Error de carga de ocupación");
    await page.unroute("**/api/v1/gobierno/ocupacion/cargos*");
  });
});
