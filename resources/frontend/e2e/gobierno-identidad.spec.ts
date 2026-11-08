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
const TITULAR = ["organization:view", "gobierno_actos:view"];

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

test.describe("Gobierno identidad", () => {
  test("IDE-E2E-01 · recorrido completo", async ({ request, browser, page }) => {
    test.setTimeout(300_000);
    const { mundo, tipoId, emisorId, objetivoId } = await mundoOcupacion(request);

    const acto = await actoEmitidoApi(request, mundo, tipoId, emisorId, `NUM-${Date.now()}`);
    const funcionario = await funcionarioApi(request, mundo.headers, "Persona Identidad Prueba");
    const asignacion = await asignacionApi(request, mundo.headers, {
      funcionario_id: funcionario.id,
      cargo_id: objetivoId,
      acto_id: acto.id,
      fundamento: "Fundamento de prueba para identidad",
    });

    const admin = await sesionApi("admintenant", { tenant: TENANT });
    const activadorOrg04 = await crearUsuario(request, admin.headers, [
      "organization:view",
      "gobierno_ocupacion:view",
      "gobierno_ocupacion:activate",
    ], mundo.companyId);
    const activarAsignacionResp = await activarApi(request, activadorOrg04.headers, asignacion);
    expect(activarAsignacionResp.status(), await activarAsignacionResp.text()).toBe(200);

    const titular = await crearUsuario(request, admin.headers, TITULAR, mundo.companyId);
    const activadorId = await crearUsuario(request, admin.headers, ACTIVADOR_ID, mundo.companyId);

    await entrarEnGobierno(page, mundo.username, mundo.codigo, "/gobierno/identidad");
    await expect(page.getByRole("heading", { level: 1, name: "Identidad institucional" })).toBeVisible();

    await page.locator('nav[aria-label="Menú principal"] a[href="/gobierno/identidad"]').click();
    await page.getByRole("link", { name: "Nuevo vínculo" }).click();
    await page.locator("#vinculo-cuenta").selectOption({ label: titular.username });
    const opciones = await obtenerOpciones(request, mundo.headers);
    const funcionarioOpcion = opciones.funcionarios.find((f: { id: string; nombre: string }) => f.id === funcionario.id);
    expect(funcionarioOpcion).toBeTruthy();
    const funcionarioValue = await page.locator("#vinculo-funcionario option").filter({ hasText: "Persona Identidad Prueba" }).first().getAttribute("value");
    expect(funcionarioValue).toBeTruthy();
    await page.locator("#vinculo-funcionario").selectOption({ value: funcionarioValue! });
    await page.locator("#vinculo-desde").fill(hoyCaracas());
    await page.locator("#vinculo-motivo").fill("Motivo de vínculo de prueba");
    await pulsarYEsperar(page, page.getByRole("button", { name: "Guardar borrador" }), "POST", /\/gobierno\/identidad\/vinculos$/);
    await page.waitForURL(/\/gobierno\/identidad\/vinculos\/[0-9a-f-]{36}$/);
    await expect(page.getByText("Borrador", { exact: true }).first()).toBeVisible();
    const url = page.url();
    const vinculoId = url.split("/").pop();
    expect(vinculoId).toBeTruthy();
    const codigoVinculo = ((await page.getByRole("heading", { level: 1 }).textContent()) ?? "").replace("Vínculo", "").trim();
    expect(codigoVinculo).toMatch(/^VIN-/);

    await page.getByRole("button", { name: "Activar" }).click();
    await expect(page.getByRole("alert").first()).toBeVisible();
    const alertaTexto = await page.getByRole("alert").first().textContent();
    expect(alertaTexto).toContain("registró");

    const contexto = await browser.newContext();
    const pagina2 = await contexto.newPage();
    await entrarEnGobierno(pagina2, activadorId.username, mundo.codigo, "/gobierno/identidad");
    await pagina2.locator('nav[aria-label="Menú principal"] a[href="/gobierno/identidad"]').click();
    await pagina2.locator(`a[href="/gobierno/identidad/vinculos/${vinculoId}"]`).click();
    await pulsarYEsperar(pagina2, pagina2.getByRole("button", { name: "Activar" }), "POST", /\/gobierno\/identidad\/vinculos\/.*\/activar$/);
    await expect(pagina2.getByText("Vigente", { exact: true }).first()).toBeVisible();
    await expect(pagina2.getByText("Cargo OBJETIVO-OCU").first()).toBeVisible();
    await expect(pagina2.getByRole("cell", { name: "Sí", exact: true }).first()).toBeVisible();

    const contextoTitular = await browser.newContext();
    const paginaTitular = await contextoTitular.newPage();
    await entrarEnGobierno(paginaTitular, titular.username, mundo.codigo, "/gobierno/identidad/mi-contexto");
    await expect(paginaTitular.getByText(codigoVinculo).first()).toBeVisible();
    await expect(paginaTitular.getByText("Cargo OBJETIVO-OCU").first()).toBeVisible();
    await contextoTitular.close();

    await pagina2.getByRole("button", { name: "Cerrar", exact: true }).first().click();
    await pagina2.getByLabel("Fecha", { exact: true }).fill(hoyCaracas());
    await pagina2.getByLabel("Motivo").fill("Motivo de cierre de prueba");
    const enviarCierre = pagina2.getByRole("button", { name: "Cerrar" }).last();
    await pulsarYEsperar(pagina2, enviarCierre, "POST", /\/gobierno\/identidad\/vinculos\/.*\/cerrar$/);
    await expect(pagina2.getByText("Cerrado", { exact: true }).first()).toBeVisible();
    await expect(pagina2.getByText("Vínculo registrado", { exact: true })).toBeVisible();
    await expect(pagina2.getByText("Vínculo activado", { exact: true })).toBeVisible();
    await expect(pagina2.getByText("Vínculo cerrado", { exact: true }).first()).toBeVisible();

    await pagina2.locator('nav[aria-label="Menú principal"] a[href="/gobierno/identidad"]').click();
    const descargaPromise = pagina2.waitForEvent("download");
    await pagina2.getByRole("button", { name: "Exportar CSV" }).click();
    const descarga = await descargaPromise;
    expect(descarga.suggestedFilename().endsWith(".csv")).toBe(true);

    await contexto.close();
  });

  test("IDE-E2E-02 · negativas", async ({ request, browser }) => {
    test.setTimeout(300_000);
    const { mundo, tipoId, emisorId, objetivoId, futuroId, revocadoId } = await mundoOcupacion(request);
    const admin = await sesionApi("admintenant", { tenant: TENANT });
    const activadorOrg04 = await crearUsuario(request, admin.headers, [
      "organization:view",
      "gobierno_ocupacion:view",
      "gobierno_ocupacion:activate",
    ], mundo.companyId);
    const activadorId = await crearUsuario(request, admin.headers, ACTIVADOR_ID, mundo.companyId);

    // (a) segunda cuenta para el mismo funcionario
    const actoA = await actoEmitidoApi(request, mundo, tipoId, emisorId, `NEG-A-${Date.now()}`);
    const funcionarioA = await funcionarioApi(request, mundo.headers, "Persona Solape Prueba");
    const asignacionA = await asignacionApi(request, mundo.headers, {
      funcionario_id: funcionarioA.id,
      cargo_id: objetivoId,
      acto_id: actoA.id,
      fundamento: "Fundamento de prueba para solape",
    });
    const activarAsignacionAResp = await activarApi(request, activadorOrg04.headers, asignacionA);
    expect(activarAsignacionAResp.status(), await activarAsignacionAResp.text()).toBe(200);

    const titularA = await crearUsuario(request, admin.headers, TITULAR, mundo.companyId);
    const opcionesA = await obtenerOpciones(request, mundo.headers);
    const userIdA = opcionesA.cuentas.find((c: { usuario: string; id: string }) => c.usuario === titularA.username)?.id;
    expect(userIdA).toBeTruthy();
    const vinculoA = await registrarVinculoApi(request, mundo.headers, {
      user_id: userIdA,
      official_id: funcionarioA.id,
      desde: hoyCaracas(),
      motivo: "Motivo de vínculo solape",
    });
    const activarVinculoAResp = await activarVinculoApi(request, activadorId.headers, vinculoA);
    expect(activarVinculoAResp.status(), await activarVinculoAResp.text()).toBe(200);

    const titularA2 = await crearUsuario(request, admin.headers, TITULAR, mundo.companyId);
    const contextoA = await browser.newContext();
    const paginaA = await contextoA.newPage();
    await entrarEnGobierno(paginaA, mundo.username, mundo.codigo, "/gobierno/identidad");
    await paginaA.locator('nav[aria-label="Menú principal"] a[href="/gobierno/identidad"]').click();
    await paginaA.getByRole("link", { name: "Nuevo vínculo" }).click();
    await paginaA.locator("#vinculo-cuenta").selectOption({ label: titularA2.username });
    const funcionarioValueA = await paginaA.locator("#vinculo-funcionario option").filter({ hasText: "Persona Solape Prueba" }).first().getAttribute("value");
    expect(funcionarioValueA).toBeTruthy();
    await paginaA.locator("#vinculo-funcionario").selectOption({ value: funcionarioValueA! });
    await paginaA.locator("#vinculo-desde").fill(hoyCaracas());
    await paginaA.locator("#vinculo-motivo").fill("Motivo de vínculo solape dos");
    await pulsarYEsperar(paginaA, paginaA.getByRole("button", { name: "Guardar borrador" }), "POST", /\/gobierno\/identidad\/vinculos$/);
    await paginaA.waitForURL(/\/gobierno\/identidad\/vinculos\/[0-9a-f-]{36}$/);
    const vinculoA2Id = paginaA.url().split("/").pop();
    expect(vinculoA2Id).toBeTruthy();
    await contextoA.close();

    const contextoA2 = await browser.newContext();
    const paginaA2 = await contextoA2.newPage();
    await entrarEnGobierno(paginaA2, activadorId.username, mundo.codigo, "/gobierno/identidad");
    await paginaA2.locator('nav[aria-label="Menú principal"] a[href="/gobierno/identidad"]').click();
    await paginaA2.locator(`a[href="/gobierno/identidad/vinculos/${vinculoA2Id}"]`).click();
    await paginaA2.getByRole("button", { name: "Activar" }).click();
    await expect(paginaA2.getByRole("alert").first()).toBeVisible();
    const alertaSolape = await paginaA2.getByRole("alert").first().textContent();
    expect(alertaSolape).toContain("Ya hay un vínculo activo");
    await contextoA2.close();

    // (b) ocupación futura
    const actoB = await actoEmitidoApi(request, mundo, tipoId, emisorId, `NEG-B-${Date.now()}`);
    const funcionarioB = await funcionarioApi(request, mundo.headers, "Persona Futura Prueba");
    const mananaB = new Date(Date.now() + 86_400_000).toISOString().slice(0, 10);
    const asignacionB = await asignacionApi(request, mundo.headers, {
      funcionario_id: funcionarioB.id,
      cargo_id: futuroId,
      acto_id: actoB.id,
      fundamento: "Fundamento de prueba para futura",
      desde: mananaB,
    });
    const activarAsignacionBResp = await activarApi(request, activadorOrg04.headers, asignacionB);
    expect(activarAsignacionBResp.status(), await activarAsignacionBResp.text()).toBe(200);

    const titularB = await crearUsuario(request, admin.headers, TITULAR, mundo.companyId);
    const opcionesB = await obtenerOpciones(request, mundo.headers);
    const userIdB = opcionesB.cuentas.find((c: { usuario: string; id: string }) => c.usuario === titularB.username)?.id;
    expect(userIdB).toBeTruthy();
    const vinculoB = await registrarVinculoApi(request, mundo.headers, {
      user_id: userIdB,
      official_id: funcionarioB.id,
      desde: hoyCaracas(),
      motivo: "Motivo de vínculo futura",
    });
    const activarVinculoBResp = await activarVinculoApi(request, activadorId.headers, vinculoB);
    expect(activarVinculoBResp.status()).toBe(200);

    const contextoB = await browser.newContext();
    const paginaB = await contextoB.newPage();
    await entrarEnGobierno(paginaB, titularB.username, mundo.codigo, "/gobierno/identidad/mi-contexto");
    await expect(paginaB.getByText("El funcionario no ejerce ningún cargo en esa fecha").first()).toBeVisible();
    await contextoB.close();

    // (c) ocupación revocada
    const actoC = await actoEmitidoApi(request, mundo, tipoId, emisorId, `NEG-C-${Date.now()}`);
    const actoCRev = await actoEmitidoApi(request, mundo, tipoId, emisorId, `NEG-C-REV-${Date.now()}`);
    const funcionarioC = await funcionarioApi(request, mundo.headers, "Persona Revocada Prueba");
    const asignacionC = await asignacionApi(request, mundo.headers, {
      funcionario_id: funcionarioC.id,
      cargo_id: revocadoId,
      acto_id: actoC.id,
      fundamento: "Fundamento de prueba para revocada",
    });
    const activarAsignacionCResp = await activarApi(request, activadorOrg04.headers, asignacionC);
    expect(activarAsignacionCResp.status()).toBe(200);
    const versionAsignacionC = (await activarAsignacionCResp.json()).version;

    const titularC = await crearUsuario(request, admin.headers, TITULAR, mundo.companyId);
    const opcionesC = await obtenerOpciones(request, mundo.headers);
    const userIdC = opcionesC.cuentas.find((c: { usuario: string; id: string }) => c.usuario === titularC.username)?.id;
    expect(userIdC).toBeTruthy();
    const vinculoC = await registrarVinculoApi(request, mundo.headers, {
      user_id: userIdC,
      official_id: funcionarioC.id,
      desde: hoyCaracas(),
      motivo: "Motivo de vínculo revocada",
    });
    const activarVinculoCResp = await activarVinculoApi(request, activadorId.headers, vinculoC);
    expect(activarVinculoCResp.status()).toBe(200);

    const revocarCResp = await request.post(`${API}/gobierno/ocupacion/asignaciones/${asignacionC.id}/revocar`, {
      headers: { ...mundo.headers, "If-Match": `"${versionAsignacionC}"` },
      data: { acto_id: actoCRev.id, fecha: hoyCaracas(), motivo: "Motivo de revocación de prueba" },
    });
    expect(revocarCResp.status(), await revocarCResp.text()).toBe(200);

    const contextoTC = await browser.newContext();
    const paginaTC = await contextoTC.newPage();
    await entrarEnGobierno(paginaTC, titularC.username, mundo.codigo, "/gobierno/identidad/mi-contexto");
    await expect(paginaTC.getByRole("heading", { level: 1, name: "Mi contexto institucional" })).toBeVisible();
    const mananaC = new Date(Date.parse(`${hoyCaracas()}T12:00:00Z`) + 86_400_000).toISOString().slice(0, 10);
    await paginaTC.locator("#fecha-consulta").fill(mananaC);
    await expect(paginaTC.getByText("El funcionario no ejerce ningún cargo en esa fecha").first()).toBeVisible();
    await contextoTC.close();

    // (d) administrador técnico sin vínculo
    const contextoTD = await browser.newContext();
    const paginaTD = await contextoTD.newPage();
    await entrarEnGobierno(paginaTD, mundo.username, mundo.codigo, "/gobierno/identidad/mi-contexto");
    await expect(paginaTD.getByText("Sin vínculo institucional vigente", { exact: true }).first()).toBeVisible();
    await contextoTD.close();

    // (e) otro ente
    const otro = await prepararMundo(request, ["organization:view", "gobierno_identidad:view"]);
    const respOtro = await request.get(`${API}/gobierno/identidad/vinculos/${vinculoA.id}`, {
      headers: otro.headers,
    });
    expect(respOtro.status()).toBe(404);
  });

  test("IDE-E2E-03 · accesibilidad", async ({ request, page }) => {
    test.setTimeout(240_000);
    const { mundo, tipoId, emisorId, objetivoId } = await mundoOcupacion(request);
    const admin = await sesionApi("admintenant", { tenant: TENANT });
    const activadorOrg04 = await crearUsuario(request, admin.headers, [
      "organization:view",
      "gobierno_ocupacion:view",
      "gobierno_ocupacion:activate",
    ], mundo.companyId);
    const activadorId = await crearUsuario(request, admin.headers, ACTIVADOR_ID, mundo.companyId);
    const todoUsuario = await crearUsuario(request, admin.headers, RESPONSABLE, mundo.companyId);

    const acto = await actoEmitidoApi(request, mundo, tipoId, emisorId, `ACC-${Date.now()}`);
    const funcionario = await funcionarioApi(request, mundo.headers, "Persona Accesible Identidad Prueba");
    const asignacion = await asignacionApi(request, mundo.headers, {
      funcionario_id: funcionario.id,
      cargo_id: objetivoId,
      acto_id: acto.id,
      fundamento: "Fundamento de prueba para accesibilidad",
    });
    const activarAsignacionResp = await activarApi(request, activadorOrg04.headers, asignacion);
    expect(activarAsignacionResp.status()).toBe(200);

    const titular = await crearUsuario(request, admin.headers, TITULAR, mundo.companyId);
    const opciones = await obtenerOpciones(request, mundo.headers);
    const userId = opciones.cuentas.find((c: { usuario: string; id: string }) => c.usuario === titular.username)?.id;
    expect(userId).toBeTruthy();
    const vinculo = await registrarVinculoApi(request, mundo.headers, {
      user_id: userId,
      official_id: funcionario.id,
      desde: hoyCaracas(),
      motivo: "Motivo de vínculo para accesibilidad",
    });
    const activarVinculoResp = await activarVinculoApi(request, activadorId.headers, vinculo);
    expect(activarVinculoResp.status()).toBe(200);

    await entrarEnGobierno(page, todoUsuario.username, mundo.codigo, "/gobierno/identidad");
    await expect(page.getByRole("heading", { level: 1, name: "Identidad institucional" })).toBeVisible();
    await contextoAccesible(page, page.getByRole("heading", { level: 1, name: "Identidad institucional" }), "Lista de identidad");

    await page.locator('nav[aria-label="Menú principal"] a[href="/gobierno/identidad"]').click();
    await page.getByRole("link", { name: "Nuevo vínculo" }).click();
    await contextoAccesible(page, page.locator("#vinculo-cuenta"), "Formulario nuevo vínculo");

    await page.locator('nav[aria-label="Menú principal"] a[href="/gobierno/identidad"]').click();
    await page.locator(`a[href="/gobierno/identidad/vinculos/${vinculo.id}"]`).click();
    await contextoAccesible(page, page.getByRole("heading", { level: 1 }), "Ficha de vínculo");

    await page.getByRole("button", { name: "Cerrar", exact: true }).first().click();
    await expect(page.getByRole("region", { name: "Cerrar vínculo" })).toBeVisible();
    await contextoAccesible(page, page.getByRole("heading", { level: 1 }), "Ficha de vínculo con panel Cerrar");

    await page.locator('nav[aria-label="Menú principal"] a[href="/gobierno/identidad"]').click();
    await page.getByRole("link", { name: "Categorías y separación" }).click();
    await contextoAccesible(page, page.getByRole("heading", { level: 1, name: "Categorías y separación" }), "Categorías");

    await page.locator('nav[aria-label="Menú principal"] a[href="/gobierno/identidad/mi-contexto"]').click();
    await contextoAccesible(page, page.getByRole("heading", { level: 1, name: "Mi contexto institucional" }), "Mi contexto");

    await page.goto("/gobierno/identidad/vinculos/00000000-0000-0000-0000-000000000000");
    await contextoAccesible(page, page.getByText("Vínculo no encontrado").first(), "Ficha de vínculo inexistente");
  });
});
