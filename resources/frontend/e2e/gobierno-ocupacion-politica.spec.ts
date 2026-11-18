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
  "gobierno_ocupacion:configure",
];
const ACTIVADOR = [
  "organization:view",
  "gobierno_ocupacion:view",
  "gobierno_ocupacion:activate",
  "gobierno_ocupacion:revoke",
  "gobierno_actos:view",
];
const CONFIGURADOR = [
  "organization:view",
  "gobierno_ocupacion:view",
  "gobierno_ocupacion:manage",
  "gobierno_ocupacion:configure",
];

function hoyCaracas(): string {
  return new Intl.DateTimeFormat("en-CA", { timeZone: "America/Caracas" }).format(new Date());
}

function sumarDias(fechaISO: string, dias: number): string {
  const [anio, mes, dia] = fechaISO.split("-").map(Number);
  const fecha = new Date(Date.UTC(anio, mes - 1, dia + dias));
  return fecha.toISOString().slice(0, 10);
}

function enElAnio(dias: number): string {
  const f = sumarDias(hoyCaracas(), dias);
  const fin = `${ANIO}-12-31`;
  return f > fin ? fin : f;
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

async function asignacionApi(
  request: APIRequestContext,
  headers: Record<string, string>,
  datos: {
    funcionario_id: string;
    cargo_id: string;
    acto_id: string;
    fundamento: string;
    figura?: "TITULAR" | "SUPLENCIA";
    cargo_origen_id?: string | null;
    hasta?: string | null;
    maxima_autoridad?: boolean;
    autorizacion_especial?: string | null;
  },
): Promise<{ id: string; version: string }> {
  const resp = await request.post(`${API}/gobierno/ocupacion/asignaciones`, {
    headers,
    data: {
      funcionario_id: datos.funcionario_id,
      cargo_id: datos.cargo_id,
      figura: datos.figura ?? "TITULAR",
      acto_id: datos.acto_id,
      desde: hoyCaracas(),
      fundamento: datos.fundamento,
      cargo_origen_id: datos.cargo_origen_id ?? null,
      hasta: datos.hasta ?? null,
      rendicion: null,
      maxima_autoridad: datos.maxima_autoridad ?? false,
      autorizacion_especial: datos.autorizacion_especial ?? null,
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

async function politicaApi(
  request: APIRequestContext,
  headers: Record<string, string>,
  datos: {
    codigo: string;
    nombre: string;
    descripcion: string;
    figura: string;
    fundamento: string;
    vigente_desde: string;
    vigente_hasta?: string | null;
    max_dias?: number;
    autorizacion_requerida?: boolean;
    autorizacion_etiqueta?: string;
    autorizacion_ambito?: string;
    autorizacion_mas_de_dias?: number;
  },
): Promise<{ id: string; version: string }> {
  const resp = await request.post(`${API}/gobierno/ocupacion/politicas`, {
    headers,
    data: {
      codigo: datos.codigo,
      nombre: datos.nombre,
      descripcion: datos.descripcion,
      figura: datos.figura,
      fundamento: datos.fundamento,
      act_id: null,
      vigente_desde: datos.vigente_desde,
      vigente_hasta: datos.vigente_hasta ?? null,
      exige_fin: false,
      max_dias: datos.max_dias ?? 365,
      acto_medio: null,
      emisor_tipo: "CUALQUIERA",
      emisor_position_id: null,
      emisor_competencia_accion: null,
      emisor_competencia_materia: null,
      autorizacion_requerida: datos.autorizacion_requerida ?? false,
      autorizacion_etiqueta: datos.autorizacion_etiqueta ?? null,
      autorizacion_ambito: datos.autorizacion_ambito ?? null,
      autorizacion_mas_de_dias: datos.autorizacion_mas_de_dias ?? null,
      prohibe_avocacion: false,
      competencias: [],
      documentos: [],
    },
  });
  expect(resp.status(), await resp.text()).toBe(201);
  return resp.json();
}

async function activarPoliticaApi(
  request: APIRequestContext,
  headers: Record<string, string>,
  politica: { id: string; version: string },
): Promise<void> {
  const resp = await request.post(`${API}/gobierno/ocupacion/politicas/${politica.id}/activar`, {
    headers: { ...headers, "If-Match": `"${politica.version}"` },
    data: {},
  });
  expect(resp.status(), await resp.text()).toBe(200);
}

async function nuevaVersionPoliticaApi(
  request: APIRequestContext,
  headers: Record<string, string>,
  politica: { id: string; version: string },
): Promise<{ id: string; version: string }> {
  const resp = await request.post(`${API}/gobierno/ocupacion/politicas/${politica.id}/nueva-version`, {
    headers: { ...headers, "If-Match": `"${politica.version}"` },
    data: {},
  });
  expect(resp.status(), await resp.text()).toBe(201);
  return resp.json();
}

async function actualizarPoliticaApi(
  request: APIRequestContext,
  headers: Record<string, string>,
  politica: { id: string; version: string },
  datos: { max_dias: number },
): Promise<{ id: string; version: string }> {
  // El PUT reemplaza la política entera: se parte del detalle actual y se cambia solo lo pedido.
  const actual = await request.get(`${API}/gobierno/ocupacion/politicas/${politica.id}`, { headers });
  expect(actual.status(), await actual.text()).toBe(200);
  const d = await actual.json();
  const claves = [
    "codigo", "nombre", "descripcion", "figura", "fundamento", "act_id", "vigente_desde", "vigente_hasta",
    "exige_fin", "max_dias", "acto_medio", "emisor_tipo", "emisor_position_id", "emisor_competencia_accion",
    "emisor_competencia_materia", "autorizacion_requerida", "autorizacion_etiqueta", "autorizacion_ambito",
    "autorizacion_mas_de_dias", "prohibe_avocacion",
  ];
  const entrada: Record<string, unknown> = Object.fromEntries(claves.map((k) => [k, d[k]]));
  entrada.competencias = (d.competencias ?? []).map((c: { accion: string; materia: string }) => ({ accion: c.accion, materia: c.materia }));
  entrada.documentos = (d.documentos ?? []).map((x: { document_type_id: string; etapa: string; obligatorio: boolean }) => ({
    document_type_id: x.document_type_id, etapa: x.etapa, obligatorio: x.obligatorio,
  }));
  entrada.max_dias = datos.max_dias;
  const resp = await request.put(`${API}/gobierno/ocupacion/politicas/${politica.id}`, {
    headers: { ...headers, "If-Match": `"${d.version}"` },
    data: entrada,
  });
  expect(resp.status(), await resp.text()).toBe(200);
  return resp.json();
}


test.describe("Gobierno ocupación · políticas de asignación", () => {
  test("OAP-E2E-01 · ente no municipal: la suplencia de máxima autoridad no exige la autorización del Concejo (P0)", async ({ request, browser, page }) => {
    test.setTimeout(240_000);
    const mundo = await prepararMundo(request, RESPONSABLE);
    const tipo = await crearTipoDocumental(request, mundo.headers, mundo.companyId);
    await enteActivo(request, mundo.headers, mundo.companyId, tipo.id, "ESTADAL");
    const estructura = await estructuraVigenteApi(request, mundo.headers, mundo.companyId, tipo.id, ANIO);
    const emisor = await cargoVigenteApi(request, mundo.headers, mundo.companyId, tipo.id, ANIO, estructura.da01Id, "EMISOR-POL01");
    const suplido = await cargoVigenteApi(request, mundo.headers, mundo.companyId, tipo.id, ANIO, estructura.da01Id, "SUPLIDO-POL01");
    const origen = await cargoVigenteApi(request, mundo.headers, mundo.companyId, tipo.id, ANIO, estructura.da01Id, "ORIGEN-POL01");

    const admin = await sesionApi("admintenant", { tenant: TENANT });
    const activador = await crearUsuario(request, admin.headers, ACTIVADOR, mundo.companyId);

    const actoTitularSuplido = await actoEmitidoApi(request, mundo, tipo.id, emisor.id, `TSUP-${Date.now()}`);
    const actoSuplencia = await actoEmitidoApi(request, mundo, tipo.id, suplido.id, `SUPL-${Date.now()}`);

    const titularSuplido = await funcionarioApi(request, mundo.headers, "Persona Titular Suplido");
    const suplente = await funcionarioApi(request, mundo.headers, "Persona Suplente Pol01");

    const asignTitularSuplido = await asignacionApi(request, mundo.headers, {
      funcionario_id: titularSuplido.id,
      cargo_id: suplido.id,
      acto_id: actoTitularSuplido.id,
      fundamento: "Asignación titular del cargo suplido",
    });
    expect((await activarApi(request, activador.headers, asignTitularSuplido)).status()).toBe(200);

    const asignSuplenteOrigen = await asignacionApi(request, mundo.headers, {
      funcionario_id: suplente.id,
      cargo_id: origen.id,
      acto_id: actoSuplencia.id,
      fundamento: "Suplente también es titular activo en origen",
    });
    expect((await activarApi(request, activador.headers, asignSuplenteOrigen)).status()).toBe(200);

    await entrarEnGobierno(page, mundo.username, mundo.codigo, "/gobierno/ocupacion");
    await page.locator('nav[aria-label="Menú principal"] a[href="/gobierno/ocupacion"]').click();
    await page.getByRole("link", { name: "Nueva asignación" }).click();

    await page.locator("#asignacion-figura").selectOption("SUPLENCIA");
    await page.locator("#asignacion-funcionario").selectOption({ value: suplente.id });
    await page.locator("#asignacion-cargo").selectOption({ value: suplido.id });
    await page.locator("#asignacion-cargo-origen").selectOption({ value: origen.id });
    await page.locator("#asignacion-acto").selectOption({ value: actoSuplencia.id });
    await page.locator("#asignacion-desde").fill(hoyCaracas());
    await page.locator("#asignacion-hasta").fill(enElAnio(19));
    await page.locator("#asignacion-fundamento").fill("Suplencia de máxima autoridad en ente estadal");
    await page.locator("#asignacion-maxima-autoridad").check();
    await page.locator("#asignacion-maxima-autoridad").uncheck();
    await page.locator("#asignacion-maxima-autoridad").check();

    await expect(page.locator("h2", { hasText: "Regla aplicada" })).toBeVisible();
    await expect(page.locator("h2", { hasText: "Regla aplicada" }).locator("..").getByText("Regla legal base, sin política institucional")).toBeVisible();
    expect(await page.getByText("Concejo", { exact: false }).count()).toBe(0);
    await expect(page.locator("h2", { hasText: "Regla aplicada" }).locator("..")).not.toContainText("Concejo");

    await pulsarYEsperar(page, page.getByRole("button", { name: "Guardar borrador" }), "POST", /\/asignaciones$/);
    await page.waitForURL(/\/gobierno\/ocupacion\/(asignaciones|politicas)\/[0-9a-f-]{36}$/);
    const url = page.url();
    const asignacionId = url.split("/").pop();
    expect(asignacionId).toBeTruthy();

    const contexto = await browser.newContext();
    const pagina2 = await contexto.newPage();
    await entrarEnGobierno(pagina2, activador.username, mundo.codigo, "/gobierno/ocupacion");
    const getResp = await request.get(`${API}/gobierno/ocupacion/asignaciones/${asignacionId}`, { headers: activador.headers });
    expect(getResp.status(), await getResp.text()).toBe(200);
    const asignacionDatos = await getResp.json();
    const activarResp = await activarApi(request, activador.headers, { id: asignacionId!, version: asignacionDatos.version });
    expect(activarResp.status(), await activarResp.text()).toBe(200);

    await pagina2.locator('nav[aria-label="Menú principal"] a[href="/gobierno/ocupacion"]').click();
    await pagina2.locator(`a[href^="/gobierno/ocupacion/cargos/${suplido.id}"]`).first().click();
    await expect(pagina2.getByRole("cell", { name: new RegExp("Persona Suplente Pol01") }).first()).toBeVisible();

    await contexto.close();
  });

  test("OAP-E2E-02 · política con autorización especial: se pide, se exige y se congela", async ({ request, page }) => {
    test.setTimeout(300_000);
    const mundo = await prepararMundo(request, RESPONSABLE);
    const tipo = await crearTipoDocumental(request, mundo.headers, mundo.companyId);
    await enteActivo(request, mundo.headers, mundo.companyId, tipo.id, "ESTADAL");
    const estructura = await estructuraVigenteApi(request, mundo.headers, mundo.companyId, tipo.id, ANIO);
    const emisor = await cargoVigenteApi(request, mundo.headers, mundo.companyId, tipo.id, ANIO, estructura.da01Id, "EMISOR-POL02");
    const suplidoA = await cargoVigenteApi(request, mundo.headers, mundo.companyId, tipo.id, ANIO, estructura.da01Id, "SUPLIDO-POL02A");
    const origenA = await cargoVigenteApi(request, mundo.headers, mundo.companyId, tipo.id, ANIO, estructura.da01Id, "ORIGEN-POL02A");

    const admin = await sesionApi("admintenant", { tenant: TENANT });
    const activador = await crearUsuario(request, admin.headers, ACTIVADOR, mundo.companyId);
    const configurador = await crearUsuario(request, admin.headers, CONFIGURADOR, mundo.companyId);

    const codigoPolitica = `POL${Date.now().toString(36).toUpperCase()}`.slice(0, 20);
    await entrarEnGobierno(page, configurador.username, mundo.codigo, "/gobierno/ocupacion/politicas");
    await expect(page.getByRole("heading", { level: 1, name: "Políticas de asignación" })).toBeVisible();
    await page.getByRole("link", { name: "Nueva política" }).first().click();

    const anioInicio = `${ANIO}-01-01`;
    await page.getByLabel("Código").fill(codigoPolitica);
    await page.getByLabel("Nombre").fill("Política de autorización especial E2E");
    await page.getByLabel("Figura").selectOption("SUPLENCIA");
    await page.getByLabel("Fundamento").fill("Reglamento interno del instituto autónomo, art. 12");
    await page.getByLabel("Vigente desde").fill(anioInicio);
    await page.getByLabel("Exige autorización especial").check();
    await page.getByLabel("Nombre de la autorización").fill("Autorización del Consejo Directivo");
    await page.getByLabel("Ámbito de la autorización").selectOption("TODAS");
    await page.getByLabel("Exigir con más de (días)").fill("10");
    await pulsarYEsperar(page, page.getByRole("button", { name: "Guardar borrador" }), "POST", /\/politicas$/);
    await expect(page.getByRole("heading", { level: 1, name: new RegExp(codigoPolitica) })).toBeVisible();

    await page.waitForURL(/\/gobierno\/ocupacion\/(asignaciones|politicas)\/[0-9a-f-]{36}$/);
    const politicaUrl = page.url();
    const politicaId = politicaUrl.split("/").pop();
    expect(politicaId).toBeTruthy();

    const politicaGetResp = await request.get(`${API}/gobierno/ocupacion/politicas/${politicaId}`, { headers: configurador.headers });
    expect(politicaGetResp.status(), await politicaGetResp.text()).toBe(200);
    const politicaDatos = await politicaGetResp.json();
    await activarPoliticaApi(request, activador.headers, { id: politicaId!, version: politicaDatos.version });

    const actoTitularSuplidoA = await actoEmitidoApi(request, mundo, tipo.id, emisor.id, `TSUP2A-${Date.now()}`);
    const actoSuplenciaA = await actoEmitidoApi(request, mundo, tipo.id, suplidoA.id, `SUPL2A-${Date.now()}`);

    const titularSuplidoA = await funcionarioApi(request, mundo.headers, "Persona Titular Suplido A");
    const suplenteA = await funcionarioApi(request, mundo.headers, "Persona Suplente Pol02A");

    const asignTitularSuplidoA = await asignacionApi(request, mundo.headers, {
      funcionario_id: titularSuplidoA.id,
      cargo_id: suplidoA.id,
      acto_id: actoTitularSuplidoA.id,
      fundamento: "Asignación titular del cargo suplido A",
    });
    expect((await activarApi(request, activador.headers, asignTitularSuplidoA)).status()).toBe(200);

    const asignSuplenteOrigenA = await asignacionApi(request, mundo.headers, {
      funcionario_id: suplenteA.id,
      cargo_id: origenA.id,
      acto_id: actoSuplenciaA.id,
      fundamento: "Suplente A es titular activo en origen",
    });
    expect((await activarApi(request, activador.headers, asignSuplenteOrigenA)).status()).toBe(200);

    await page.locator('nav[aria-label="Menú principal"] a[href="/gobierno/ocupacion"]').click();
    await page.getByRole("link", { name: "Nueva asignación" }).click();

    await page.locator("#asignacion-figura").selectOption("SUPLENCIA");
    await page.locator("#asignacion-funcionario").selectOption({ value: suplenteA.id });
    await page.locator("#asignacion-cargo").selectOption({ value: suplidoA.id });
    await page.locator("#asignacion-cargo-origen").selectOption({ value: origenA.id });
    await page.locator("#asignacion-acto").selectOption({ value: actoSuplenciaA.id });
    await page.locator("#asignacion-desde").fill(hoyCaracas());
    await page.locator("#asignacion-hasta").fill(enElAnio(20));
    await page.locator("#asignacion-fundamento").fill("Suplencia con autorización especial requerida");

    await expect(page.locator("h2", { hasText: "Regla aplicada" })).toBeVisible();
    await expect(page.locator("h2", { hasText: "Regla aplicada" }).locator("..").getByText(`Política ${codigoPolitica} v1`).first()).toBeVisible();
    await expect(page.getByLabel("Autorización del Consejo Directivo")).toBeVisible();

    await page.getByRole("button", { name: "Guardar borrador" }).click();
    await expect(page.getByText("La autorización debe tener entre 5 y 200 caracteres.")).toBeVisible();
    await expect(page.url()).toContain("/asignaciones/nueva");

    await page.getByLabel("Autorización del Consejo Directivo").fill("Acta N.º 7 del Consejo Directivo");
    await pulsarYEsperar(page, page.getByRole("button", { name: "Guardar borrador" }), "POST", /\/asignaciones$/);
    await page.waitForURL(/\/gobierno\/ocupacion\/(asignaciones|politicas)\/[0-9a-f-]{36}$/);
    const urlAsignacionA = page.url();
    const asignacionAId = urlAsignacionA.split("/").pop();
    expect(asignacionAId).toBeTruthy();

    const getAsignacionAResp = await request.get(`${API}/gobierno/ocupacion/asignaciones/${asignacionAId}`, { headers: configurador.headers });
    expect(getAsignacionAResp.status(), await getAsignacionAResp.text()).toBe(200);
    const asignacionADatos = await getAsignacionAResp.json();
    const activarAsignacionAResp = await activarApi(request, activador.headers, { id: asignacionAId!, version: asignacionADatos.version });
    expect(activarAsignacionAResp.status(), await activarAsignacionAResp.text()).toBe(200);

    await page.locator('nav[aria-label="Menú principal"] a[href="/gobierno/ocupacion"]').click();
    await page.getByRole("link", { name: "Asignaciones", exact: true }).click();
    await page.locator(`a[href="/gobierno/ocupacion/asignaciones/${asignacionAId}"]`).click();
    // La activación fue por API, fuera de esta pestaña: se recarga para no leer la ficha en caché.
    await page.reload();

    await expect(page.locator("h2", { hasText: "Regla aplicada" })).toBeVisible();
    await expect(page.locator("h2", { hasText: "Regla aplicada" }).locator("..").getByText(`Política ${codigoPolitica} v1`).first()).toBeVisible();
    await expect(page.locator("h2", { hasText: "Regla aplicada" }).locator("..").getByText("Congelada al activarse: no cambia aunque cambie la política.")).toBeVisible();

    // Nueva versión de la política
    const politicaGetResp2 = await request.get(`${API}/gobierno/ocupacion/politicas/${politicaId}`, { headers: configurador.headers });
    expect(politicaGetResp2.status(), await politicaGetResp2.text()).toBe(200);
    const politicaDatos2 = await politicaGetResp2.json();
    const nuevaVersion = await nuevaVersionPoliticaApi(request, configurador.headers, { id: politicaId!, version: politicaDatos2.version });
    const actualizada = await actualizarPoliticaApi(request, configurador.headers, { id: nuevaVersion.id, version: nuevaVersion.version }, { max_dias: 15 });
    await activarPoliticaApi(request, activador.headers, { id: nuevaVersion.id, version: actualizada.version });

    // Recargar ficha de asignación A: sigue mostrando v1
    await page.reload();
    await expect(page.locator("h2", { hasText: "Regla aplicada" }).locator("..").getByText(`Política ${codigoPolitica} v1`).first()).toBeVisible();
    await expect(page.locator("h2", { hasText: "Regla aplicada" }).locator("..").getByText(`Política ${codigoPolitica} v2`)).toHaveCount(0);

    // Crear suplencia B con la nueva política v2
    const suplidoB = await cargoVigenteApi(request, mundo.headers, mundo.companyId, tipo.id, ANIO, estructura.da01Id, "SUPLIDO-POL02B");
    const origenB = await cargoVigenteApi(request, mundo.headers, mundo.companyId, tipo.id, ANIO, estructura.da01Id, "ORIGEN-POL02B");

    const actoTitularSuplidoB = await actoEmitidoApi(request, mundo, tipo.id, emisor.id, `TSUP2B-${Date.now()}`);
    const actoSuplenciaB = await actoEmitidoApi(request, mundo, tipo.id, suplidoB.id, `SUPL2B-${Date.now()}`);

    const titularSuplidoB = await funcionarioApi(request, mundo.headers, "Persona Titular Suplido B");
    const suplenteB = await funcionarioApi(request, mundo.headers, "Persona Suplente Pol02B");

    const asignTitularSuplidoB = await asignacionApi(request, mundo.headers, {
      funcionario_id: titularSuplidoB.id,
      cargo_id: suplidoB.id,
      acto_id: actoTitularSuplidoB.id,
      fundamento: "Asignación titular del cargo suplido B",
    });
    expect((await activarApi(request, activador.headers, asignTitularSuplidoB)).status()).toBe(200);

    const asignSuplenteOrigenB = await asignacionApi(request, mundo.headers, {
      funcionario_id: suplenteB.id,
      cargo_id: origenB.id,
      acto_id: actoSuplenciaB.id,
      fundamento: "Suplente B es titular activo en origen",
    });
    expect((await activarApi(request, activador.headers, asignSuplenteOrigenB)).status()).toBe(200);

    const asignacionB = await asignacionApi(request, mundo.headers, {
      funcionario_id: suplenteB.id,
      cargo_id: suplidoB.id,
      figura: "SUPLENCIA",
      acto_id: actoSuplenciaB.id,
      fundamento: "Suplencia B con autorización especial",
      cargo_origen_id: origenB.id,
      hasta: enElAnio(13),
      maxima_autoridad: false,
      autorizacion_especial: "Resolución N.º 15 del Consejo Directivo",
    });
    const activarBResp = await activarApi(request, activador.headers, asignacionB);
    expect(activarBResp.status(), await activarBResp.text()).toBe(200);

    const getBResp = await request.get(`${API}/gobierno/ocupacion/asignaciones/${asignacionB.id}`, { headers: configurador.headers });
    expect(getBResp.status(), await getBResp.text()).toBe(200);
    const datosB = await getBResp.json();
    expect(datosB.regla.politica.codigo).toBe(codigoPolitica);
    expect(datosB.regla.politica.numero_version).toBe(2);
  });

  test("OAP-E2E-03 · accesibilidad 1280/390/320", async ({ request, page }) => {
    test.setTimeout(300_000);
    const mundo = await prepararMundo(request, RESPONSABLE);
    const tipo = await crearTipoDocumental(request, mundo.headers, mundo.companyId);
    await enteActivo(request, mundo.headers, mundo.companyId, tipo.id, "ESTADAL");
    const estructura = await estructuraVigenteApi(request, mundo.headers, mundo.companyId, tipo.id, ANIO);
    const emisor = await cargoVigenteApi(request, mundo.headers, mundo.companyId, tipo.id, ANIO, estructura.da01Id, "EMISOR-POLACC");
    const suplido = await cargoVigenteApi(request, mundo.headers, mundo.companyId, tipo.id, ANIO, estructura.da01Id, "SUPLIDO-POLACC");
    const origen = await cargoVigenteApi(request, mundo.headers, mundo.companyId, tipo.id, ANIO, estructura.da01Id, "ORIGEN-POLACC");

    const admin = await sesionApi("admintenant", { tenant: TENANT });
    const activador = await crearUsuario(request, admin.headers, ACTIVADOR, mundo.companyId);
    const configurador = await crearUsuario(request, admin.headers, CONFIGURADOR, mundo.companyId);

    const codigoPolitica = `POLACC${Date.now().toString(36).toUpperCase()}`.slice(0, 20);
    await entrarEnGobierno(page, configurador.username, mundo.codigo, "/gobierno/ocupacion/politicas");
    await expect(page.getByRole("heading", { level: 1, name: "Políticas de asignación" })).toBeVisible();

    // Crear política por API
    const politica = await politicaApi(request, configurador.headers, {
      codigo: codigoPolitica,
      nombre: "Política de accesibilidad E2E",
      descripcion: "Política para pruebas de accesibilidad",
      figura: "SUPLENCIA",
      fundamento: "Ley de accesibilidad, art. 3",
      vigente_desde: `${ANIO}-01-01`,
      max_dias: 30,
      autorizacion_requerida: true,
      autorizacion_etiqueta: "Autorización de Accesibilidad",
      autorizacion_ambito: "TODAS",
      autorizacion_mas_de_dias: 10,
    });
    await activarPoliticaApi(request, activador.headers, politica);

    const actoTitularSuplido = await actoEmitidoApi(request, mundo, tipo.id, emisor.id, `TSUPACC-${Date.now()}`);
    const actoSuplencia = await actoEmitidoApi(request, mundo, tipo.id, suplido.id, `SUPLACC-${Date.now()}`);

    const titularSuplido = await funcionarioApi(request, mundo.headers, "Persona Titular Suplido ACC");
    const suplente = await funcionarioApi(request, mundo.headers, "Persona Suplente ACC");

    const asignTitularSuplido = await asignacionApi(request, mundo.headers, {
      funcionario_id: titularSuplido.id,
      cargo_id: suplido.id,
      acto_id: actoTitularSuplido.id,
      fundamento: "Asignación titular del cargo suplido ACC",
    });
    expect((await activarApi(request, activador.headers, asignTitularSuplido)).status()).toBe(200);

    const asignSuplenteOrigen = await asignacionApi(request, mundo.headers, {
      funcionario_id: suplente.id,
      cargo_id: origen.id,
      acto_id: actoSuplencia.id,
      fundamento: "Suplente ACC es titular activo en origen",
    });
    expect((await activarApi(request, activador.headers, asignSuplenteOrigen)).status()).toBe(200);

    const asignacion = await asignacionApi(request, mundo.headers, {
      funcionario_id: suplente.id,
      cargo_id: suplido.id,
      figura: "SUPLENCIA",
      acto_id: actoSuplencia.id,
      fundamento: "Suplencia ACC con autorización especial",
      cargo_origen_id: origen.id,
      hasta: enElAnio(25),
      maxima_autoridad: false,
      autorizacion_especial: "Acta de accesibilidad N.º 1",
    });
    const activarAsignacionResp = await activarApi(request, activador.headers, asignacion);
    expect(activarAsignacionResp.status(), await activarAsignacionResp.text()).toBe(200);

    // Lista de políticas
    async function recorrerAnchos(ruta: string, nombre: string): Promise<void> {
      await page.goto(`${page.url().split("/gobierno")[0]}/gobierno${ruta}`);
      for (const ancho of [1280, 390, 320]) {
        await page.setViewportSize({ width: ancho, height: 800 });
        await expect(page.locator("main")).toBeVisible();
        await sinViolacionesSerias(page, `${nombre} ${ancho}x800`);
      }
      await page.setViewportSize({ width: 1280, height: 800 });
    }

    await recorrerAnchos("/ocupacion/politicas", "Lista de políticas");

    // Formulario de política
    await page.locator('nav[aria-label="Menú principal"] a[href="/gobierno/ocupacion/politicas"]').click();
    await page.getByRole("link", { name: "Nueva política" }).first().click();
    await expect(page.getByLabel("Código")).toBeVisible();
    for (const ancho of [1280, 390, 320]) {
      await page.setViewportSize({ width: ancho, height: 800 });
      await expect(page.locator("main")).toBeVisible();
      await sinViolacionesSerias(page, `Formulario de política ${ancho}x800`);
    }
    await page.setViewportSize({ width: 1280, height: 800 });

    // Formulario de asignación con figura Suplencia
    await page.locator('nav[aria-label="Menú principal"] a[href="/gobierno/ocupacion"]').click();
    await page.getByRole("link", { name: "Nueva asignación" }).click();
    await page.locator("#asignacion-figura").selectOption("SUPLENCIA");
    await page.locator("#asignacion-funcionario").selectOption({ value: suplente.id });
    await page.locator("#asignacion-cargo").selectOption({ value: suplido.id });
    await page.locator("#asignacion-cargo-origen").selectOption({ value: origen.id });
    await page.locator("#asignacion-acto").selectOption({ value: actoSuplencia.id });
    await page.locator("#asignacion-desde").fill(hoyCaracas());
    await page.locator("#asignacion-hasta").fill(enElAnio(20));
    await page.locator("#asignacion-fundamento").fill("Suplencia de accesibilidad");
    await expect(page.locator("h2", { hasText: "Regla aplicada" })).toBeVisible();
    await expect(page.getByLabel("Autorización de Accesibilidad")).toBeVisible();
    for (const ancho of [1280, 390, 320]) {
      await page.setViewportSize({ width: ancho, height: 800 });
      await expect(page.locator("main")).toBeVisible();
      await sinViolacionesSerias(page, `Formulario de asignación ${ancho}x800`);
    }
    await page.setViewportSize({ width: 1280, height: 800 });

    // Ficha de asignación
    await page.locator('nav[aria-label="Menú principal"] a[href="/gobierno/ocupacion"]').click();
    await page.getByRole("link", { name: "Asignaciones", exact: true }).click();
    await page.locator(`a[href="/gobierno/ocupacion/asignaciones/${asignacion.id}"]`).click();
    await expect(page.locator("h2", { hasText: "Regla aplicada" })).toBeVisible();
    for (const ancho of [1280, 390, 320]) {
      await page.setViewportSize({ width: ancho, height: 800 });
      await expect(page.locator("main")).toBeVisible();
      await sinViolacionesSerias(page, `Ficha de asignación ${ancho}x800`);
    }
    await page.setViewportSize({ width: 1280, height: 800 });
  });
});
