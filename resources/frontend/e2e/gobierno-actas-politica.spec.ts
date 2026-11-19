import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "./helpers/sesion";
import type { APIRequestContext, Page } from "@playwright/test";
import {
  ANIO,
  API,
  RESPONSABLE_ESTRUCTURA,
  adjuntarDocumentoApi,
  cargoVigenteApi,
  cerrarNotificaciones,
  crearTipoDocumental,
  crearUsuario,
  enteActivo,
  entrarEnGobierno,
  estructuraVigenteApi,
  prepararMundo,
  TENANT,
} from "./helpers/gobierno";
import { sesionApi } from "./helpers/sesion";

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
  "gobierno_auditoria:view",
  "gobierno_actas:view",
  "gobierno_actas:manage",
  "gobierno_actas:verify",
  "gobierno_actas:configure",
  "gobierno_actas:activate",
  "documentos:view",
  "documentos:create",
];

function hoyCaracas(): string {
  return new Intl.DateTimeFormat("en-CA", { timeZone: "America/Caracas" }).format(new Date());
}

async function sinViolacionesSerias(page: Page, contexto: string): Promise<void> {
  const resultados = await new AxeBuilder({ page }).include("main").withTags(WCAG).analyze();
  const serias = resultados.violations.filter((v) => ["critical", "serious"].includes(v.impact ?? ""));
  expect(serias.map((v) => ({ id: v.id, help: v.help })), contexto).toEqual([]);
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
): Promise<{ id: string; version: number }> {
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

async function activarAsignacionApi(
  request: APIRequestContext,
  headers: Record<string, string>,
  asignacion: { id: string; version: number },
): Promise<{ status: () => number; text: () => Promise<string>; json: () => Promise<Record<string, unknown>> }> {
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

async function mundoOcupacion(request: APIRequestContext) {
  const mundo = await prepararMundo(request, RESPONSABLE);
  const tipo = await crearTipoDocumental(request, mundo.headers, mundo.companyId);
  await enteActivo(request, mundo.headers, mundo.companyId, tipo.id);
  const estructura = await estructuraVigenteApi(request, mundo.headers, mundo.companyId, tipo.id, ANIO);

  const codigoMaxA = `MAX-A-POL-${Date.now()}`;
  const codigoMaxB = `MAX-B-POL-${Date.now()}`;

  const emisor = await cargoVigenteApi(request, mundo.headers, mundo.companyId, tipo.id, ANIO, estructura.da01Id, "EMISOR-SEP");
  const maxA = await cargoVigenteApi(request, mundo.headers, mundo.companyId, tipo.id, ANIO, estructura.da01Id, codigoMaxA);
  const maxB = await cargoVigenteApi(request, mundo.headers, mundo.companyId, tipo.id, ANIO, estructura.da01Id, codigoMaxB);
  const salienteA = await funcionarioApi(request, mundo.headers, `Persona Saliente A Pol ${Date.now()}`);
  const salienteB = await funcionarioApi(request, mundo.headers, `Persona Saliente B Pol ${Date.now()}`);
  const receptorA = await funcionarioApi(request, mundo.headers, `Receptor A Pol ${Date.now()}`);
  const receptorB = await funcionarioApi(request, mundo.headers, `Receptor B Pol ${Date.now()}`);

  const actoA = await actoEmitidoApi(request, mundo, tipo.id, emisor.id, `POL-AA-${Date.now()}`);
  const actoB = await actoEmitidoApi(request, mundo, tipo.id, emisor.id, `POL-BB-${Date.now()}`);

  const asigA = await asignacionApi(request, mundo.headers, {
    funcionario_id: salienteA.id,
    cargo_id: maxA.id,
    acto_id: actoA.id,
    fundamento: "Fundamento de prueba para política A",
  });
  const asigB = await asignacionApi(request, mundo.headers, {
    funcionario_id: salienteB.id,
    cargo_id: maxB.id,
    acto_id: actoB.id,
    fundamento: "Fundamento de prueba para política B",
  });

  const admin = await sesionApi("admintenant", { tenant: TENANT });
  const activador = await crearUsuario(
    request,
    admin.headers,
    ["organization:view", "gobierno_ocupacion:view", "gobierno_ocupacion:activate"],
    mundo.companyId,
  );

  const respActivarA = await activarAsignacionApi(request, activador.headers, asigA);
  expect(respActivarA.status(), await respActivarA.text()).toBe(200);
  const respActivarB = await activarAsignacionApi(request, activador.headers, asigB);
  expect(respActivarB.status(), await respActivarB.text()).toBe(200);

  return {
    mundo,
    tipoId: tipo.id,
    emisorId: emisor.id,
    cargoMaxAId: maxA.id,
    cargoMaxBId: maxB.id,
    codigoMaxA,
    codigoMaxB,
    salienteA,
    salienteB,
    receptorA,
    receptorB,
    asignacionA: asigA,
    asignacionB: asigB,
  };
}

test.setTimeout(480_000);

test("CTL-09-DELIVERY-ACT-POLICY: política de actas P0, A17, congelación y ORG-04", async ({ page, request }) => {
  const marca = Date.now();
  const codigoPolitica = `PAE-${marca}`;

  const mundoData = await mundoOcupacion(request);
  const { mundo, codigoMaxA, codigoMaxB, receptorA, receptorB, asignacionA, asignacionB } = mundoData;

  await entrarEnGobierno(page, mundo.username, mundo.codigo, "/gobierno/actas-entrega");
  await cerrarNotificaciones(page);

  // OAE-E2E-01 política por UI
  await page.getByRole("link", { name: "Políticas de actas" }).click();
  await page.waitForURL(/\/gobierno\/actas-entrega\/politicas$/);
  await expect(page.getByRole("heading", { level: 1, name: "Políticas de actas" })).toBeVisible();
  await page.setViewportSize({ width: 1280, height: 800 });
  await sinViolacionesSerias(page, "listado políticas 1280");

  await page.getByRole("link", { name: "Nueva política" }).click();
  await page.waitForURL(/\/gobierno\/actas-entrega\/politicas\/nueva$/);
  await expect(page.getByRole("heading", { level: 1, name: "Nueva política de actas" })).toBeVisible();
  await sinViolacionesSerias(page, "formulario política");

  await page.getByLabel(/^Código(?! del)/).fill(codigoPolitica);
  await page.getByLabel("Nombre").fill(`Política de actas ${marca}`);
  await page.getByLabel("Fundamento").fill("N34 art. 17 y normativa aplicable");
  await page.getByLabel("Vigente desde").fill(`${ANIO}-01-01`);
  await page.getByLabel("Código del cargo de máxima autoridad").fill(codigoMaxA);

  const guardarBorradorRespPromise = page.waitForResponse(
    (resp) => resp.url().includes("/api/v1/gobierno/actas-entrega/politicas") && resp.request().method() === "POST",
  );
  await page.getByRole("button", { name: "Guardar borrador" }).click();
  const guardarBorradorResp = await guardarBorradorRespPromise;
  expect(guardarBorradorResp.status()).toBe(201);
  const politicaCreada = await guardarBorradorResp.json();
  const politicaId = politicaCreada.id as string;

  await page.waitForURL(new RegExp(`/gobierno/actas-entrega/politicas/${politicaId}`));
  await expect(page.getByRole("heading", { level: 1, name: `Política ${codigoPolitica} v1` })).toBeVisible();
  await sinViolacionesSerias(page, "ficha política borrador");

  const activarPoliticaRespPromise = page.waitForResponse(
    (resp) =>
      resp.url().includes(`/gobierno/actas-entrega/politicas/${politicaId}/activar`) &&
      resp.request().method() === "POST",
  );
  await page.getByRole("button", { name: "Activar" }).click();
  const activarPoliticaResp = await activarPoliticaRespPromise;
  expect(activarPoliticaResp.status()).toBe(200);
  const politicaVersionActiva = (await activarPoliticaResp.json()).version as number;
  await expect(page.getByText("Vigente", { exact: true })).toBeVisible();

  // OAE-E2E-02 (P0) nueva acta de S_A por UI
  await page.goto("/gobierno/actas-entrega");
  await cerrarNotificaciones(page);
  await page.getByRole("link", { name: "Nueva acta" }).click();
  await expect(page.getByRole("heading", { level: 1, name: "Nueva acta de entrega" })).toBeVisible();

  await page.getByLabel("Ocupación saliente").selectOption(asignacionA.id);
  await page.getByRole("combobox", { name: /^Receptor/ }).selectOption(receptorA.id);
  await page.getByRole("radio", { name: "Entrega por el saliente" }).check();
  await page.getByLabel("Motivo").fill("Motivo de prueba para acta de entrega P0");
  await page.getByLabel("Fundamento").fill("Fundamento de prueba para acta de entrega P0");
  await page.getByLabel("Lugar").fill("Caracas");

  const anexosExigidosA = page.getByRole("list", { name: "Anexos exigidos" });
  await expect(anexosExigidosA).toContainText("A11_1");
  await expect(anexosExigidosA).not.toContainText("A17_");
  await expect(
    page.getByRole("status").filter({ hasText: "Si el acta corresponde a una Alcaldía o Dirección de hacienda municipal" }),
  ).toBeVisible();
  await sinViolacionesSerias(page, "formulario acta P0");

  const crearActaARespPromise = page.waitForResponse(
    (resp) => resp.url().includes("/api/v1/gobierno/actas-entrega") && resp.request().method() === "POST",
  );
  await page.getByRole("button", { name: "Crear acta de entrega" }).click();
  const crearActaAResp = await crearActaARespPromise;
  expect(crearActaAResp.status()).toBe(201);
  const actaAId = (await crearActaAResp.json()).id as string;

  await page.waitForURL(new RegExp(`/gobierno/actas-entrega/${actaAId}`));
  await expect(page.getByRole("heading", { level: 1, name: /Acta AE-\d+-/ })).toBeVisible();
  await expect(page.getByText(`PAE-${marca} v1`, { exact: false })).toBeVisible();
  await expect(page.getByText("Se recalcula al editar el borrador.", { exact: false })).toBeVisible();
  await expect(page.getByText("Quien entrega", { exact: true })).toBeVisible();
  await expect(page.getByRole("table", { name: "Anexos del acta" })).toBeVisible();
  await expect(page.getByRole("table", { name: "Anexos del acta" })).not.toContainText("A17_");

  const avisoPendientesA = page.getByRole("status").filter({ hasText: "Anexos obligatorios pendientes" });
  await expect(avisoPendientesA).toContainText("A11_3");
  await expect(avisoPendientesA).toContainText("A11_4");
  await expect(page.getByRole("button", { name: "Suscribir acta" })).toBeDisabled();

  for (const codigoAnexo of ["A11_3", "A11_4"]) {
    const textareaConstancia = page.locator(`#constancia-${codigoAnexo}`);
    const celda = textareaConstancia.locator("xpath=ancestor::td[1]");
    await textareaConstancia.fill(`Constancia ${codigoAnexo} política ${marca}`);
    const guardarConstanciaRespPromise = page.waitForResponse(
      (resp) => resp.url().includes(`/anexos/${codigoAnexo}`) && resp.request().method() === "PUT",
    );
    await celda.getByRole("button", { name: "Guardar constancia" }).click();
    const guardarConstanciaResp = await guardarConstanciaRespPromise;
    expect(guardarConstanciaResp.status()).toBe(200);
  }

  await expect(avisoPendientesA).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Suscribir acta" })).toBeEnabled();

  const suscribirARespPromise = page.waitForResponse(
    (resp) => resp.url().includes("/api/v1/gobierno/actas-entrega") && resp.request().method() === "POST",
  );
  await page.getByRole("button", { name: "Suscribir acta" }).click();
  const suscribirAResp = await suscribirARespPromise;
  expect(suscribirAResp.status()).toBe(200);
  await expect(page.getByText("Suscrita", { exact: true })).toBeVisible();
  await expect(page.getByText("Congelada al suscribir: no cambia aunque cambie la política.", { exact: false })).toBeVisible();

  // OAE-E2E-03 (A17 positivo) por API: nueva-version v1 -> v2
  const nuevaVersionResp = await request.post(`${API}/gobierno/actas-entrega/politicas/${politicaId}/nueva-version`, {
    headers: { ...mundo.headers, "If-Match": `"${politicaVersionActiva}"` },
    data: {},
  });
  expect(nuevaVersionResp.status(), await nuevaVersionResp.text()).toBe(201);
  const politicaV2 = await nuevaVersionResp.json();
  const politicaV2Version = politicaV2.version as number;

  const entradaCompleta = {
    codigo: codigoPolitica,
    nombre: `Política de actas ${marca}`,
    fundamento: "N34 art. 17 y normativa aplicable",
    vigente_desde: `${ANIO}-01-01`,
    vigente_hasta: null,
    descripcion: null,
    act_id: null,
    numeracion_patron: null,
    testigos_en_entrega: 0,
    cargo_maxima_autoridad_codigo: codigoMaxB,
    vinculos: [{ supuesto: "N34_ART17", alcance: "ENTE", unit_id: null }],
    requisitos: [],
    plazos: [],
  };

  const putPoliticaResp = await request.put(`${API}/gobierno/actas-entrega/politicas/${politicaV2.id}`, {
    headers: { ...mundo.headers, "If-Match": `"${politicaV2Version}"` },
    data: entradaCompleta,
  });
  expect(putPoliticaResp.status(), await putPoliticaResp.text()).toBe(200);
  const putPoliticaJson = await putPoliticaResp.json();
  const politicaV2VersionTrasPut = putPoliticaJson.version as number;

  const activarPoliticaV2Resp = await request.post(`${API}/gobierno/actas-entrega/politicas/${politicaV2.id}/activar`, {
    headers: { ...mundo.headers, "If-Match": `"${politicaV2VersionTrasPut}"` },
    data: {},
  });
  expect(activarPoliticaV2Resp.status(), await activarPoliticaV2Resp.text()).toBe(200);
  expect(activarPoliticaV2Resp.status()).toBe(200);

  await page.goto("/gobierno/actas-entrega");
  await cerrarNotificaciones(page);
  await page.getByRole("link", { name: "Nueva acta" }).click();
  await expect(page.getByRole("heading", { level: 1, name: "Nueva acta de entrega" })).toBeVisible();

  await page.getByLabel("Ocupación saliente").selectOption(asignacionB.id);
  await page.getByRole("combobox", { name: /^Receptor/ }).selectOption(receptorB.id);
  await page.getByRole("radio", { name: "Entrega por el saliente" }).check();
  await page.getByLabel("Motivo").fill("Motivo de prueba para acta de entrega A17");
  await page.getByLabel("Fundamento").fill("Fundamento de prueba para acta de entrega A17");
  await page.getByLabel("Lugar").fill("Caracas");

  const anexosExigidosB = page.getByRole("list", { name: "Anexos exigidos" });
  await expect(anexosExigidosB).toContainText("A17_1");
  await expect(anexosExigidosB).toContainText("N34 art. 17");
  await expect(
    page.getByRole("status").filter({ hasText: "Si el acta corresponde a una Alcaldía o Dirección de hacienda municipal" }),
  ).toHaveCount(0);

  const crearActaBRespPromise = page.waitForResponse(
    (resp) => resp.url().includes("/api/v1/gobierno/actas-entrega") && resp.request().method() === "POST",
  );
  await page.getByRole("button", { name: "Crear acta de entrega" }).click();
  const crearActaBResp = await crearActaBRespPromise;
  expect(crearActaBResp.status()).toBe(201);
  const actaBId = (await crearActaBResp.json()).id as string;

  await page.waitForURL(new RegExp(`/gobierno/actas-entrega/${actaBId}`));
  await expect(page.getByRole("heading", { level: 1, name: /Acta AE-\d+-/ })).toBeVisible();
  await expect(page.getByText(`PAE-${marca} v2`, { exact: false })).toBeVisible();
  await expect(page.getByRole("table", { name: "Anexos del acta" })).toContainText("A17_1");
  await expect(page.getByRole("table", { name: "Anexos del acta" })).toContainText("A17_5");
  await expect(page.getByRole("button", { name: "Suscribir acta" })).toBeDisabled();

  const avisoPendientesB = page.getByRole("status").filter({ hasText: "Anexos obligatorios pendientes" });
  await expect(avisoPendientesB).toContainText("A17_1");
  await expect(avisoPendientesB).toContainText("A17_2");
  await expect(avisoPendientesB).toContainText("A17_3");
  await expect(avisoPendientesB).toContainText("A17_4");
  await expect(avisoPendientesB).toContainText("A17_5");

  for (const codigoAnexo of ["A11_3", "A11_4", "A17_1", "A17_2", "A17_3", "A17_4", "A17_5"]) {
    const textareaConstancia = page.locator(`#constancia-${codigoAnexo}`);
    const celda = textareaConstancia.locator("xpath=ancestor::td[1]");
    await textareaConstancia.fill(`Constancia ${codigoAnexo} política ${marca}`);
    const guardarConstanciaRespPromise = page.waitForResponse(
      (resp) => resp.url().includes(`/anexos/${codigoAnexo}`) && resp.request().method() === "PUT",
    );
    await celda.getByRole("button", { name: "Guardar constancia" }).click();
    const guardarConstanciaResp = await guardarConstanciaRespPromise;
    expect(guardarConstanciaResp.status()).toBe(200);
  }

  await expect(avisoPendientesB).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Suscribir acta" })).toBeEnabled();

  const suscribirBRespPromise = page.waitForResponse(
    (resp) => resp.url().includes("/api/v1/gobierno/actas-entrega") && resp.request().method() === "POST",
  );
  await page.getByRole("button", { name: "Suscribir acta" }).click();
  const suscribirBResp = await suscribirBRespPromise;
  expect(suscribirBResp.status()).toBe(200);
  await expect(page.getByText("Suscrita", { exact: true })).toBeVisible();
  await expect(page.getByText("Congelada al suscribir: no cambia aunque cambie la política.", { exact: false })).toBeVisible();

  // OAE-E2E-04 versión congelada y ORG-04
  await page.goto(`/gobierno/actas-entrega/${actaAId}`);
  await expect(page.getByText(`PAE-${marca} v1`, { exact: false })).toBeVisible();
  await expect(page.getByRole("table", { name: "Anexos del acta" })).not.toContainText("A17_");
  await expect(page.getByText("Quien entrega", { exact: true })).toBeVisible();
  await expect(page.getByText(`Persona Saliente A Pol`, { exact: false })).toBeVisible();

  await page.goto(`/gobierno/actas-entrega/${actaBId}`);
  await expect(page.getByText(`PAE-${marca} v2`, { exact: false })).toBeVisible();
  await expect(page.getByText("Quien entrega", { exact: true })).toBeVisible();
  await expect(page.getByText(`Persona Saliente B Pol`, { exact: false })).toBeVisible();

  // Responsive y Axe
  await page.setViewportSize({ width: 390, height: 800 });
  const overflow390 = await page.evaluate(() => document.documentElement.scrollWidth <= 390 + 1);
  expect(overflow390, "sin desbordamiento horizontal a 390px").toBe(true);
  await sinViolacionesSerias(page, "ficha acta B 390");

  await page.goto("/gobierno/actas-entrega/politicas");
  await page.waitForURL(/\/gobierno\/actas-entrega\/politicas$/);
  await page.setViewportSize({ width: 320, height: 800 });
  const overflow320 = await page.evaluate(() => document.documentElement.scrollWidth <= 320 + 1);
  expect(overflow320, "sin desbordamiento horizontal a 320px").toBe(true);
  await sinViolacionesSerias(page, "listado políticas 320");
});
