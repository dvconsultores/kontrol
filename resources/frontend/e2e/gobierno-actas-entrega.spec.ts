import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "./helpers/sesion";
import type { APIRequestContext, Page } from "@playwright/test";
import {
  ANIO,
  API,
  RESPONSABLE_ESTRUCTURA,
  adjuntarDocumentoApi,
  cerrarNotificaciones,
  cargoVigenteApi,
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

async function mundoOcupacion(request: APIRequestContext) {
  const mundo = await prepararMundo(request, RESPONSABLE);
  const tipo = await crearTipoDocumental(request, mundo.headers, mundo.companyId);
  await enteActivo(request, mundo.headers, mundo.companyId, tipo.id);
  const estructura = await estructuraVigenteApi(request, mundo.headers, mundo.companyId, tipo.id, ANIO);
  const emisor = await cargoVigenteApi(request, mundo.headers, mundo.companyId, tipo.id, ANIO, estructura.da01Id, "EMISOR-SEP");
  const objetivo = await cargoVigenteApi(request, mundo.headers, mundo.companyId, tipo.id, ANIO, estructura.da01Id, "OBJETIVO-SEP");
  return { mundo, tipoId: tipo.id, emisorId: emisor.id, objetivoId: objetivo.id };
}

test.setTimeout(420_000);

test("CTL-09: actas de entrega recorre el ciclo, negativas, accesibilidad y responsive", async ({ page, request, browser }) => {
  const marca = Date.now();

  const { mundo, tipoId, emisorId, objetivoId } = await mundoOcupacion(request);
  const admin = await sesionApi("admintenant", { tenant: TENANT });

  const activador = await crearUsuario(
    request,
    admin.headers,
    ["organization:view", "gobierno_ocupacion:view", "gobierno_ocupacion:activate"],
    mundo.companyId,
  );

  const actoLegitimo = await actoEmitidoApi(request, mundo, tipoId, emisorId, `LEG-${marca}`);
  const nombreSaliente = `Persona Saliente Acta ${marca}`;
  const saliente = await funcionarioApi(request, mundo.headers, nombreSaliente);
  const asignacion = await asignacionApi(request, mundo.headers, {
    funcionario_id: saliente.id,
    cargo_id: objetivoId,
    acto_id: actoLegitimo.id,
    fundamento: "Fundamento de prueba para acta de entrega",
  });
  const activarAsignacionResp = await activarApi(request, activador.headers, asignacion);
  expect(activarAsignacionResp.status()).toBe(200);

  const nombreReceptor = `Persona Receptora Acta ${marca}`;
  const receptor = await funcionarioApi(request, mundo.headers, nombreReceptor);

  await entrarEnGobierno(page, mundo.username, mundo.codigo, "/gobierno/actas-entrega");
  await cerrarNotificaciones(page);

  await expect(page.getByRole("link", { name: "Actas de entrega" })).toBeVisible();
  await expect(page.getByRole("heading", { level: 1, name: "Actas de entrega" })).toBeVisible();
  await sinViolacionesSerias(page, "listado actas");

  await page.getByRole("link", { name: "Nueva acta" }).click();
  await expect(page.getByRole("heading", { level: 1, name: "Nueva acta de entrega" })).toBeVisible();

  await page.getByLabel("Ocupación saliente").selectOption(asignacion.id);
  await page.getByRole("combobox", { name: /^Receptor/ }).selectOption(receptor.id);
  await page.getByRole("radio", { name: "Entrega por el saliente" }).check();
  await page.getByLabel("Motivo").fill("Motivo de prueba para acta de entrega");
  await page.getByLabel("Fundamento").fill("Fundamento de prueba para acta de entrega");
  await page.getByLabel("Lugar").fill("Caracas");

  const crearActaRespPromise = page.waitForResponse(
    (resp) => resp.url().includes("/api/v1/gobierno/actas-entrega") && resp.request().method() === "POST",
  );
  await page.getByRole("button", { name: "Crear acta de entrega" }).click();
  const crearActaResp = await crearActaRespPromise;
  expect(crearActaResp.status()).toBe(201);

  await expect(page.getByRole("heading", { level: 1, name: /Acta AE-\d+-/ })).toBeVisible();
  await expect(page.getByText("Borrador", { exact: true })).toBeVisible();
  await sinViolacionesSerias(page, "ficha borrador");

  const avisoPendientes = page.getByRole("status").filter({ hasText: "Anexos obligatorios pendientes" });
  await expect(avisoPendientes).toContainText("A11_3");
  await expect(avisoPendientes).toContainText("A11_4");
  await expect(page.getByRole("button", { name: "Suscribir acta" })).toBeDisabled();



  for (const codigoAnexo of ["A11_3", "A11_4"]) {
    const textareaConstancia = page.locator(`#constancia-${codigoAnexo}`);
    const celda = textareaConstancia.locator("xpath=ancestor::td[1]");
    await textareaConstancia.fill(`Constancia art. 19 para ${codigoAnexo}`);
    const guardarConstanciaRespPromise = page.waitForResponse(
      (resp) => resp.url().includes(`/anexos/${codigoAnexo}`) && resp.request().method() === "PUT",
    );
    await celda.getByRole("button", { name: "Guardar constancia" }).click();
    const guardarConstanciaResp = await guardarConstanciaRespPromise;
    expect(guardarConstanciaResp.status()).toBe(200);
  }

  await expect(avisoPendientes).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Suscribir acta" })).toBeEnabled();

  const suscribirRespPromise = page.waitForResponse(
    (resp) => resp.url().includes("/api/v1/gobierno/actas-entrega") && resp.request().method() === "POST",
  );
  await page.getByRole("button", { name: "Suscribir acta" }).click();
  const suscribirResp = await suscribirRespPromise;
  expect(suscribirResp.status()).toBe(200);

  await expect(page.getByText("Suscrita", { exact: true })).toBeVisible();
  await expect(page.getByText("Huella del acta")).toBeVisible();

  const downloadPromise = page.waitForEvent("download");
  await page.getByRole("button", { name: "Descargar acta (PDF)" }).click();
  const download = await downloadPromise;
  expect(download.suggestedFilename()).toMatch(/\.pdf$/);

  const remisionRespPromise = page.waitForResponse(
    (resp) => resp.url().includes("/api/v1/gobierno/actas-entrega") && resp.request().method() === "POST",
  );
  await page.getByRole("button", { name: "Registrar remisión" }).click();
  const remisionResp = await remisionRespPromise;
  expect(remisionResp.status()).toBe(200);

  const observacionTexto = "Observación de prueba con más de diez caracteres";
  await page.locator("#o-texto").fill(observacionTexto);
  const observacionRespPromise = page.waitForResponse(
    (resp) => resp.url().includes("/api/v1/gobierno/actas-entrega") && resp.request().method() === "POST",
  );
  await page.getByRole("button", { name: /Registrar observación/ }).click();
  const observacionResp = await observacionRespPromise;
  expect(observacionResp.status()).toBe(201);
  await expect(page.getByText(observacionTexto)).toBeVisible();

  await page.getByLabel("Número del informe").fill("VERIF-NEG-1");
  await page.getByRole("radio", { name: "Conforme" }).check();
  await page.getByLabel("Fundamento de la verificación").fill("Fundamento de verificación de prueba");
  const verificacionNegRespPromise = page.waitForResponse(
    (resp) => resp.url().includes("/api/v1/gobierno/actas-entrega") && resp.request().method() === "POST",
  );
  await page.getByRole("button", { name: /Registrar verificación/ }).click();
  const verificacionNegResp = await verificacionNegRespPromise;
  expect(verificacionNegResp.status()).toBe(403);
  await expect(page.getByText("La verificación no puede registrarla quien suscribió, el saliente o el receptor.")).toBeVisible();
  await expect(page.getByText("Suscrita", { exact: true })).toBeVisible();

  const verificador = await crearUsuario(
    request,
    admin.headers,
    ["organization:view", "gobierno_actas:view", "gobierno_actas:verify"],
    mundo.companyId,
  );

  const contextVerificador = await browser.newContext();
  const pageVerificador = await contextVerificador.newPage();
  await entrarEnGobierno(pageVerificador, verificador.username, mundo.codigo, "/gobierno/actas-entrega");
  await cerrarNotificaciones(pageVerificador);
  await expect(pageVerificador.getByRole("heading", { level: 1, name: "Actas de entrega" })).toBeVisible();

  const codigoActa = await page.getByRole("heading", { level: 1 }).innerText();
  const codigoFicha = codigoActa.replace(/^Acta\s+/, "");
  const enlaceFicha = pageVerificador.getByRole("link", { name: codigoFicha });
  await enlaceFicha.click();
  await expect(pageVerificador).toHaveURL(new RegExp(`/gobierno/actas-entrega/`));

  await pageVerificador.getByLabel("Número del informe").fill("VERIF-OK-1");
  await pageVerificador.getByRole("radio", { name: "Conforme" }).check();
  await pageVerificador.getByLabel("Fundamento de la verificación").fill("Fundamento de verificación conforme");
  const verificacionOkRespPromise = pageVerificador.waitForResponse(
    (resp) => resp.url().includes("/api/v1/gobierno/actas-entrega") && resp.request().method() === "POST",
  );
  await pageVerificador.getByRole("button", { name: /Registrar verificación/ }).click();
  const verificacionOkResp = await verificacionOkRespPromise;
  expect(verificacionOkResp.status()).toBe(200);
  await expect(pageVerificador.getByText("Verificada", { exact: true })).toBeVisible();

  await contextVerificador.close();

  const otroMundo = await prepararMundo(request, ["organization:view", "gobierno_actas:view"]);
  const actaId = page.url().match(/\/actas-entrega\/([^/?]+)/)?.[1] ?? "";
  const aislamientoResp = await request.get(`${API}/gobierno/actas-entrega/actas/${actaId}`, {
    headers: otroMundo.headers,
  });
  expect(aislamientoResp.status()).toBe(404);

  const listadoResp = await request.get(`${API}/gobierno/actas-entrega/actas`, {
    headers: otroMundo.headers,
  });
  expect(listadoResp.status()).toBe(200);
  const listadoBody = await listadoResp.json();
  expect(listadoBody.items).not.toContainEqual(expect.objectContaining({ id: actaId }));

  await page.setViewportSize({ width: 320, height: 800 });
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth <= 320 + 1);
  expect(overflow, "sin desbordamiento horizontal a 320px").toBe(true);
  await sinViolacionesSerias(page, "ficha 320");

  const botonIntegridad = page.getByRole("button", { name: "Verificar integridad" });
  await botonIntegridad.focus();
  await expect(botonIntegridad).toBeFocused();
  await botonIntegridad.click();
  await expect(page.getByRole("region", { name: /Integridad/ })).toContainText("Resultado: Íntegra");
});
