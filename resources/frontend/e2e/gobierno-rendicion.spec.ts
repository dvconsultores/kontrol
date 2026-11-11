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
  "gobierno_rendicion:view",
  "gobierno_rendicion:form",
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

test("CTL-05: expedientes de cuenta recorre ciclo completo, negativas, accesibilidad y responsive", async ({ page, request, browser }) => {
  const marca = Date.now();

  // ───────────────────────────────────────────────────────────── R1: mundo real por API
  const { mundo, tipoId, emisorId, objetivoId } = await mundoOcupacion(request);
  const admin = await sesionApi("admintenant", { tenant: TENANT });

  const activador = await crearUsuario(
    request,
    admin.headers,
    ["organization:view", "gobierno_ocupacion:view", "gobierno_ocupacion:activate"],
    mundo.companyId,
  );

  const actoLegitimo = await actoEmitidoApi(request, mundo, tipoId, emisorId, `LEG-${marca}`);
  const nombreFuncionario = `Persona Rendición Prueba ${marca}`;
  const funcionario = await funcionarioApi(request, mundo.headers, nombreFuncionario);
  const asignacion = await asignacionApi(request, mundo.headers, {
    funcionario_id: funcionario.id,
    cargo_id: objetivoId,
    acto_id: actoLegitimo.id,
    fundamento: "Fundamento de prueba para expediente de cuenta",
  });
  const activarAsignacionResp = await activarApi(request, activador.headers, asignacion);
  expect(activarAsignacionResp.status()).toBe(200);

  const calificador = await crearUsuario(
    request,
    admin.headers,
    ["organization:view", "gobierno_rendicion:view", "gobierno_rendicion:qualify"],
    mundo.companyId,
  );

  // ───────────────────────────────────────────────────────────── R2: alta por UI
  await entrarEnGobierno(page, mundo.username, mundo.codigo, "/gobierno/rendicion");
  await cerrarNotificaciones(page);
  await expect(page.getByRole("heading", { level: 1, name: "Expedientes de cuenta" })).toBeVisible();
  await sinViolacionesSerias(page, "listado expedientes");

  await page.getByRole("link", { name: "Nuevo expediente" }).click();
  await expect(page).toHaveURL(/\/gobierno\/rendicion\/nuevo/);

  const denominacion = `Cuenta E2E ${marca}`;
  const periodoDesde = `${hoyCaracas().slice(0, 4)}-01-01`;
  const periodoHasta = hoyCaracas();

  await page.getByLabel(/Denominación/).fill(denominacion);
  await page.getByLabel(/Ejercicio/).fill(String(new Date().getFullYear()));
  await page.getByLabel("Periodo desde").fill(periodoDesde);
  await page.getByLabel("Periodo hasta").fill(periodoHasta);
  await page.getByLabel(/Fecha de corte/).fill(hoyCaracas());
  const opcion = page.getByLabel(/Responsable/).locator("option", { hasText: nombreFuncionario });
  await page.getByLabel(/Responsable/).selectOption(await opcion.getAttribute("value") ?? "");
  await page.getByLabel(/Observaciones/).fill("Observaciones E2E");

  const crearRespPromise = page.waitForResponse(
    (resp) => resp.url().includes("/gobierno/rendicion/expedientes") && resp.request().method() === "POST",
  );
  await page.getByRole("button", { name: "Crear expediente" }).click();
  const crearResp = await crearRespPromise;
  expect(crearResp.status()).toBe(201);
  const expedienteCreado = await crearResp.json();
  const expedienteId = expedienteCreado.id as string;

  await expect(page).toHaveURL(new RegExp(`/gobierno/rendicion/${expedienteId}`));
  await expect(page.getByRole("region", { name: "Cuenta" }).getByText("En formación", { exact: true })).toBeVisible();

  // ───────────────────────────────────────────────────────────── R3: incorporar dos hechos
  const seccionHechos = page.getByRole("region", { name: "Hechos disponibles del período" });

  for (let i = 0; i < 2; i++) {
    const boton = seccionHechos.getByRole("button", { name: "Incorporar", exact: true }).first();
    const incorporarRespPromise = page.waitForResponse(
      (resp) => resp.url().includes(`/gobierno/rendicion/expedientes/${expedienteId}/piezas`) && resp.request().method() === "POST",
    );
    await boton.click();
    const incorporarResp = await incorporarRespPromise;
    expect(incorporarResp.status()).toBe(201);
    await expect(seccionHechos.getByRole("button", { name: "Incorporada", exact: true })).toHaveCount(i + 1);
  }

  const seccionIndice = page.getByRole("region", { name: "Índice de piezas" });
  await expect(seccionIndice.getByRole("link", { name: "Ver en la bitácora" })).toHaveCount(2);

  const seccionReporte = page.getByRole("region", { name: "Reporte de rendición" });
  await expect(seccionReporte.getByText("Reporte provisional")).toBeVisible();

  const seccionCuenta = page.getByRole("region", { name: "Cuenta" });
  await expect(seccionCuenta.getByText("En formación", { exact: true })).toBeVisible();

  // ───────────────────────────────────────────────────────────── R4: formar la cuenta
  const formarRespPromise = page.waitForResponse(
    (resp) => resp.url().includes(`/gobierno/rendicion/expedientes/${expedienteId}/formar`) && resp.request().method() === "POST",
  );
  await page.getByRole("button", { name: "Formar la cuenta" }).click();
  const formarResp = await formarRespPromise;
  expect(formarResp.status()).toBe(200);

  await expect(page.getByRole("region", { name: "Cuenta" }).getByText("Formada", { exact: true })).toBeVisible();
  await expect(page.getByText("Corte congelado")).toBeVisible();

  const regionReporte = page.getByRole("region", { name: "Reporte de rendición" });
  const textoHuella = await regionReporte.getByText(/Corte congelado/).textContent();
  const huellaOriginal = (textoHuella ?? "").match(/([a-f0-9]{64})/)?.[1];
  expect(huellaOriginal, "Debe existir una huella de 64 hex en el texto de corte congelado").toBeTruthy();

  await expect(page.getByRole("heading", { name: "Hechos disponibles del período" })).toHaveCount(0);

  await sinViolacionesSerias(page, "ficha formada");

  // accesibilidad teclado: foco en Verificar integridad
  const verificarBoton = page.getByRole("button", { name: "Verificar integridad" });
  await verificarBoton.focus();
  await expect(verificarBoton).toBeFocused();

  // ───────────────────────────────────────────────────────────── R5: descarga PDF
  const downloadPromise = page.waitForEvent("download");
  await page.getByRole("button", { name: "Descargar PDF" }).click();
  const download = await downloadPromise;
  expect(download.suggestedFilename()).toMatch(/\.pdf$/);

  // ───────────────────────────────────────────────────────────── R6: snapshot inmutable ante nuevo hecho
  const funcionarioNuevo = await funcionarioApi(request, mundo.headers, `Persona Hecho Nuevo ${marca}`);
  const actoNuevo = await actoEmitidoApi(request, mundo, tipoId, emisorId, `NUEVO-${marca}`);
  expect(funcionarioNuevo.id).toBeTruthy();
  expect(actoNuevo.id).toBeTruthy();

  await page.reload();
  await cerrarNotificaciones(page);
  await expect(page.getByRole("heading", { name: "Índice de piezas" })).toBeVisible();
  await expect(page.getByRole("region", { name: "Índice de piezas" }).getByRole("link", { name: "Ver en la bitácora" })).toHaveCount(2);
  const textoHuellaRecargado = await page.getByRole("region", { name: "Reporte de rendición" }).getByText(/Corte congelado/).textContent();
  const huellaRecargada = (textoHuellaRecargado ?? "").match(/([a-f0-9]{64})/)?.[1];
  expect(huellaRecargada).toBe(huellaOriginal);

  const getExpedienteResp = await request.get(`${API}/gobierno/rendicion/expedientes/${expedienteId}`, {
    headers: mundo.headers,
  });
  expect(getExpedienteResp.status()).toBe(200);
  const expedienteActual = await getExpedienteResp.json();
  expect(expedienteActual.piezas).toHaveLength(2);

  // ───────────────────────────────────────────────────────────── R7: verificar integridad
  const integridadRespPromise = page.waitForResponse(
    (resp) => resp.url().includes(`/gobierno/rendicion/expedientes/${expedienteId}/integridad`) && resp.request().method() === "GET",
  );
  await page.getByRole("button", { name: "Verificar integridad" }).click();
  const integridadResp = await integridadRespPromise;
  expect(integridadResp.status()).toBe(200);
  const integridad = await integridadResp.json();
  expect(integridad.estado, JSON.stringify(integridad)).toBe("VALIDO");
  expect(integridad.snapshot_ok, JSON.stringify(integridad)).toBe(true);
  expect(integridad.informe_ok, JSON.stringify(integridad)).toBe(true);
  await expect(page.getByRole("region", { name: "Integridad" }).getByText(/^Válido · snapshot: OK · informe: OK$/)).toBeVisible();

  // ───────────────────────────────────────────────────────────── R8: participación
  const seccionAcciones = page.getByRole("region", { name: "Acciones" });
  const formParticipacion = seccionAcciones.locator("form").filter({ hasText: "Registrar participación" });
  await formParticipacion.getByLabel(/Fecha/).fill(hoyCaracas());
  await formParticipacion.getByLabel(/Oficio/).fill("OF-E2E-1");

  const participacionRespPromise = page.waitForResponse(
    (resp) => resp.url().includes(`/gobierno/rendicion/expedientes/${expedienteId}/participacion`) && resp.request().method() === "POST",
  );
  await formParticipacion.getByRole("button", { name: /Registrar participación/ }).click();
  const participacionResp = await participacionRespPromise;
  expect(participacionResp.status()).toBe(200);

  await expect(page.getByRole("region", { name: "Cuenta" }).getByText("Participada", { exact: true })).toBeVisible();

  // ───────────────────────────────────────────────────────────── R9: calificación por otro usuario
  const ctxCal = await browser.newContext();
  const pagCal = await ctxCal.newPage();
  await entrarEnGobierno(pagCal, calificador.username, mundo.codigo, "/gobierno/rendicion");
  await cerrarNotificaciones(pagCal);
  await expect(pagCal.getByRole("heading", { level: 1, name: "Expedientes de cuenta" })).toBeVisible();

  const enlaceFicha = pagCal.getByRole("listitem").filter({ hasText: denominacion }).getByRole("link");
  await enlaceFicha.click();
  await expect(pagCal).toHaveURL(new RegExp(`/gobierno/rendicion/${expedienteId}`));

  const pagCalSeccionAcciones = pagCal.getByRole("region", { name: "Acciones" });
  const formCalificacion = pagCalSeccionAcciones.locator("form").filter({ hasText: "Registrar calificación del órgano de control" });
  await expect(formCalificacion.getByText("no la calcula")).toBeVisible();

  await formCalificacion.getByRole("radio", { name: "Conforme" }).check();
  await formCalificacion.getByLabel(/Órgano/).fill("Contraloría Municipal (E2E)");
  await formCalificacion.getByLabel(/Número de informe definitivo/).fill("INF-E2E-1");
  await formCalificacion.getByLabel(/Fecha del informe/).fill(hoyCaracas());
  await formCalificacion.getByLabel(/Fundamento/).fill("Informe definitivo del examen de la cuenta.");

  const calificacionRespPromise = pagCal.waitForResponse(
    (resp) => resp.url().includes(`/gobierno/rendicion/expedientes/${expedienteId}/calificacion`) && resp.request().method() === "POST",
  );
  await formCalificacion.getByRole("button", { name: /Registrar calificación/ }).click();
  const calificacionResp = await calificacionRespPromise;
  expect(calificacionResp.status()).toBe(200);

  await expect(pagCal.getByRole("region", { name: "Cuenta" }).getByText("Calificada", { exact: true })).toBeVisible();

  // ───────────────────────────────────────────────────────────── R10: historial
  const seccionHistorial = pagCal.getByRole("region", { name: "Historial" });
  await expect(seccionHistorial.getByText("Expediente de cuenta formado")).toBeVisible();
  await expect(seccionHistorial.getByText("Expediente de cuenta calificado")).toBeVisible();

  await ctxCal.close();

  // ───────────────────────────────────────────────────────────── N1: aislamiento entre entes
  const otroMundo = await prepararMundo(request, ["organization:view", "gobierno_rendicion:view"]);
  const aislamientoResp = await request.get(`${API}/gobierno/rendicion/expedientes/${expedienteId}`, {
    headers: otroMundo.headers,
  });
  expect(aislamientoResp.status()).toBe(404);

  // ───────────────────────────────────────────────────────────── N2: cuenta formada inmutable
  const eventoValido = expedienteActual.piezas[0].evento_id;
  const inmutableResp = await request.post(`${API}/gobierno/rendicion/expedientes/${expedienteId}/piezas`, {
    headers: mundo.headers,
    data: { evento_id: eventoValido },
  });
  expect(inmutableResp.status()).toBe(409);
  const inmutableBody = await inmutableResp.json();
  expect(inmutableBody.code).toBe("GOV_RENDITION_STATE");

  // ───────────────────────────────────────────────────────────── N3: pieza inexistente
  const otroExpedienteResp = await request.post(`${API}/gobierno/rendicion/expedientes`, {
    headers: mundo.headers,
    data: {
      denominacion: `Negativa ${marca}`,
      ejercicio: Number(hoyCaracas().slice(0, 4)),
      periodo_desde: periodoDesde,
      periodo_hasta: periodoHasta,
      fecha_corte: hoyCaracas(),
      assignment_id: asignacion.id,
      observaciones: "",
    },
  });
  expect(otroExpedienteResp.status()).toBe(201);
  const otroExpediente = await otroExpedienteResp.json();

  const piezaInexistenteResp = await request.post(`${API}/gobierno/rendicion/expedientes/${otroExpediente.id}/piezas`, {
    headers: mundo.headers,
    data: { evento_id: crypto.randomUUID() },
  });
  expect(piezaInexistenteResp.status()).toBe(404);
  const piezaInexistenteBody = await piezaInexistenteResp.json();
  expect(piezaInexistenteBody.code).toBe("GOV_RENDITION_EVENT_NOT_FOUND");

  // ───────────────────────────────────────────────────────────── RESPONSIVE
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto(`/gobierno/rendicion`);
  await expect(page.getByRole("heading", { level: 1, name: "Expedientes de cuenta" })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1)).toBe(true);

  await page.goto(`/gobierno/rendicion/${expedienteId}`);
  for (const titulo of ["Cuenta", "Índice de piezas", "Reporte de rendición", "Acciones", "Rendición", "Integridad", "Historial"]) {
    await expect(page.getByRole("heading", { level: 2, name: titulo, exact: true })).toBeVisible();
  }
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1)).toBe(true);

  await page.setViewportSize({ width: 320, height: 568 });
  await page.goto(`/gobierno/rendicion`);
  await expect(page.getByRole("heading", { level: 1, name: "Expedientes de cuenta" })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1)).toBe(true);

  await page.goto(`/gobierno/rendicion/${expedienteId}`);
  for (const titulo of ["Cuenta", "Índice de piezas", "Reporte de rendición", "Acciones", "Rendición", "Integridad", "Historial"]) {
    await expect(page.getByRole("heading", { level: 2, name: titulo, exact: true })).toBeVisible();
  }
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1)).toBe(true);

  await page.setViewportSize({ width: 1280, height: 720 });
});
