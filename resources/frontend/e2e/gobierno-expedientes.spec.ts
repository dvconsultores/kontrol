import { expect, sesionApi, test } from "./helpers/sesion";
import type { APIRequestContext } from "@playwright/test";
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
  estructuraVigenteApi,
  prepararMundo,
} from "./helpers/gobierno";

function hoyCaracas(): string {
  return new Intl.DateTimeFormat("en-CA", { timeZone: "America/Caracas" }).format(new Date());
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
  const docsResp = await request.get(`${API}/documentos/por-recurso/GovernmentAct/${id}`, {
    headers: mundo.headers,
  });
  expect(docsResp.status(), await docsResp.text()).toBe(200);
  const docs = await docsResp.json();
  const emitirResp = await request.post(`${API}/gobierno/actos/${id}/emitir`, {
    headers: { ...mundo.headers, "If-Match": '"1"' },
    data: { documento_acto_id: docs[0].id },
  });
  expect(emitirResp.status(), await emitirResp.text()).toBe(200);
  await adjuntarDocumentoApi(request, mundo.headers, mundo.companyId, tipoId, "GovernmentAct", id);
  const docsDespues = await request.get(`${API}/documentos/por-recurso/GovernmentAct/${id}`, {
    headers: mundo.headers,
  });
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

test.describe("Gobierno expedientes", () => {
  test("EXP-E2E-01 · expediente de contratación por menú", async ({ page, request, browser }) => {
    test.setTimeout(300_000);
    const mundo = await prepararMundo(request, [
      ...RESPONSABLE_ESTRUCTURA,
      "gobierno_cargos:view",
      "gobierno_cargos:edit",
      "gobierno_cargos:publish",
      "gobierno_actos:view",
      "gobierno_actos:edit",
      "gobierno_actos:issue",
      "gobierno_ocupacion:view",
      "gobierno_ocupacion:manage",
      "gobierno_comisiones:view",
      "gobierno_comisiones:manage",
      "gobierno_expedientes:view",
      "gobierno_expedientes:manage",
      "gobierno_expedientes:close",
      "documentos:view",
      "documentos:create",
      "documentos:link",
    ]);
    const tipo = await crearTipoDocumental(request, mundo.headers, mundo.companyId);
    await enteActivo(request, mundo.headers, mundo.companyId, tipo.id);
    const estructura = await estructuraVigenteApi(request, mundo.headers, mundo.companyId, tipo.id, ANIO);
    const emisor = await cargoVigenteApi(
      request,
      mundo.headers,
      mundo.companyId,
      tipo.id,
      ANIO,
      estructura.despId,
      `CE-${Date.now()}`,
    );
    const acto = await actoEmitidoApi(request, mundo, tipo.id, emisor.id, `RES-EXP1-${Date.now()}`);
    const acto2 = await actoEmitidoApi(request, mundo, tipo.id, emisor.id, `RES-EXP2-${Date.now()}`);

    const funcionarios: { id: string }[] = [];
    for (let i = 0; i < 8; i++) {
      const resp = await request.post(`${API}/gobierno/ocupacion/funcionarios`, {
        headers: mundo.headers,
        data: {
          nombre: `Persona Expediente ${i + 1}`,
          tipo_documento: "V",
          numero_documento: String(Math.floor(10000000 + Math.random() * 89999999)),
        },
      });
      expect(resp.status(), await resp.text()).toBe(201);
      funcionarios.push(await resp.json());
    }

    const comisionResp = await request.post(`${API}/gobierno/contrataciones/comisiones`, {
      headers: mundo.headers,
      data: {
        nombre: "Comisión del expediente E2E",
        tipo: "PERMANENTE",
        desde: hoyCaracas(),
        hasta: null,
        objeto: null,
        acto_id: acto.id,
      },
    });
    expect(comisionResp.status(), await comisionResp.text()).toBe(201);
    const comision = await comisionResp.json();
    const comisionId = comision.id as string;
    const comisionCodigo = comision.codigo as string;

    const añadirPorApi = async (cuerpo: Record<string, unknown>) => {
      const detalleResp = await request.get(`${API}/gobierno/contrataciones/comisiones/${comisionId}`, {
        headers: mundo.headers,
      });
      expect(detalleResp.status(), await detalleResp.text()).toBe(200);
      const detalleData = await detalleResp.json();
      const resp = await request.post(
        `${API}/gobierno/contrataciones/comisiones/${comisionId}/miembros`,
        {
          headers: { ...mundo.headers, "If-Match": String(detalleData.version) },
          data: cuerpo,
        },
      );
      expect(resp.status(), await resp.text()).toBe(200);
      return detalleData;
    };

    await añadirPorApi({
      funcionario_id: funcionarios[0].id,
      funcion: "MIEMBRO",
      area: "TECNICA",
      condicion: "PRINCIPAL",
      suplente_de_id: null,
      certificacion_snc: null,
      desde: null,
      acto_id: null,
    });
    const detalle1 = await request.get(`${API}/gobierno/contrataciones/comisiones/${comisionId}`, {
      headers: mundo.headers,
    });
    const detalle1Data = await detalle1.json();
    const principal1 = detalle1Data.miembros.find(
      (m: { funcionario: { id: string } }) => m.funcionario.id === funcionarios[0].id,
    );
    expect(principal1).toBeTruthy();
    await añadirPorApi({
      funcionario_id: funcionarios[1].id,
      funcion: "MIEMBRO",
      area: null,
      condicion: "SUPLENTE",
      suplente_de_id: principal1.id,
      certificacion_snc: null,
      desde: null,
      acto_id: null,
    });

    await añadirPorApi({
      funcionario_id: funcionarios[2].id,
      funcion: "MIEMBRO",
      area: "JURIDICA",
      condicion: "PRINCIPAL",
      suplente_de_id: null,
      certificacion_snc: null,
      desde: null,
      acto_id: null,
    });
    const detalle3 = await request.get(`${API}/gobierno/contrataciones/comisiones/${comisionId}`, {
      headers: mundo.headers,
    });
    const detalle3Data = await detalle3.json();
    const principal3 = detalle3Data.miembros.find(
      (m: { funcionario: { id: string } }) => m.funcionario.id === funcionarios[2].id,
    );
    expect(principal3).toBeTruthy();
    await añadirPorApi({
      funcionario_id: funcionarios[3].id,
      funcion: "MIEMBRO",
      area: null,
      condicion: "SUPLENTE",
      suplente_de_id: principal3.id,
      certificacion_snc: null,
      desde: null,
      acto_id: null,
    });

    await añadirPorApi({
      funcionario_id: funcionarios[4].id,
      funcion: "MIEMBRO",
      area: "ECONOMICO_FINANCIERA",
      condicion: "PRINCIPAL",
      suplente_de_id: null,
      certificacion_snc: null,
      desde: null,
      acto_id: null,
    });
    const detalle5 = await request.get(`${API}/gobierno/contrataciones/comisiones/${comisionId}`, {
      headers: mundo.headers,
    });
    const detalle5Data = await detalle5.json();
    const principal5 = detalle5Data.miembros.find(
      (m: { funcionario: { id: string } }) => m.funcionario.id === funcionarios[4].id,
    );
    expect(principal5).toBeTruthy();
    await añadirPorApi({
      funcionario_id: funcionarios[5].id,
      funcion: "MIEMBRO",
      area: null,
      condicion: "SUPLENTE",
      suplente_de_id: principal5.id,
      certificacion_snc: null,
      desde: null,
      acto_id: null,
    });

    await añadirPorApi({
      funcionario_id: funcionarios[6].id,
      funcion: "SECRETARIO",
      area: null,
      condicion: "PRINCIPAL",
      suplente_de_id: null,
      certificacion_snc: null,
      desde: null,
      acto_id: null,
    });
    await añadirPorApi({
      funcionario_id: funcionarios[7].id,
      funcion: "SECRETARIO",
      area: null,
      condicion: "SUPLENTE",
      suplente_de_id: null,
      certificacion_snc: null,
      desde: null,
      acto_id: null,
    });

    const admin = await sesionApi("admintenant", { tenant: TENANT });
    const activador = await crearUsuario(
      request,
      admin.headers,
      ["organization:view", "gobierno_comisiones:view", "gobierno_comisiones:activate"],
      mundo.companyId,
    );

    const ctx = await browser.newContext();
    const p2 = await ctx.newPage();
    await entrarEnGobierno(p2, activador.username, mundo.codigo, "/gobierno/contrataciones/comisiones");
    await p2.goto(`/gobierno/contrataciones/comisiones/${comisionId}`);
    await cerrarNotificaciones(p2);
    await p2.getByRole("button", { name: "Activar" }).click();
    await expect(p2.getByText(/Vigente/).first()).toBeVisible();
    await ctx.close();
    await entrarEnGobierno(page, mundo.username, mundo.codigo, "/gobierno/ente");
    await cerrarNotificaciones(page);
    await page.locator('nav[aria-label="Menú principal"] a[href="/gobierno/contrataciones/expedientes"]').click();
    await expect(page.getByRole("heading", { name: "Expedientes de contratación" })).toBeVisible();
    await expect(page.getByText("Sin expedientes")).toBeVisible();
    await cerrarNotificaciones(page);
    await page.getByRole("link", { name: "Nuevo expediente" }).click();

    const numeroExpediente = `EXP-${Date.now()}`;
    await cerrarNotificaciones(page);
    await page.locator("#expediente-numero").fill(numeroExpediente);
    await page.locator("#expediente-fecha").fill(hoyCaracas());
    await page.locator("#expediente-objeto").fill("Adquisición de equipos E2E");
    await page.locator("#expediente-tipo").selectOption("BIENES");
    await page.locator("#expediente-unidad").selectOption(estructura.despId);
    await page.locator("#expediente-responsable").selectOption(funcionarios[0].id);
    await page.locator("#expediente-modalidad").selectOption("CONCURSO_ABIERTO");
    await page.locator("#expediente-fundamento").fill("Declarada por la unidad");
    await page.getByRole("button", { name: "Guardar" }).click();
    await page.waitForURL(/\/expedientes\/[0-9a-f-]{36}$/);
    const expedienteId = page.url().split("/").pop() as string;
    await expect(page.getByRole("heading", { level: 1 })).toContainText(numeroExpediente);
    await expect(page.getByRole("heading", { name: "Situación" })).toBeVisible();
    await expect(page.getByText("En curso").first()).toBeVisible();
    await expect(page.getByRole("listitem").filter({ hasText: "Identifique las partes (LCP art. 19)" })).toBeVisible();

    await cerrarNotificaciones(page);
    await page.getByRole("link", { name: "Editar" }).click();
    await page.locator("#expediente-partes").fill("Ente contratante y oferentes por identificar");
    await page.locator("#expediente-motivo").fill("Identificar las partes");
    await page.getByRole("button", { name: "Guardar" }).click();
    await page.waitForURL(/\/expedientes\/[0-9a-f-]{36}$/);
    await expect(page.getByText("Identifique las partes (LCP art. 19)")).toHaveCount(0);

    await cerrarNotificaciones(page);
    await page.getByRole("button", { name: "Vincular comisión" }).click();
    await page.locator("#com-comision").selectOption(comisionId);
    await page.getByRole("button", { name: "Guardar" }).click();
    await expect(page.getByRole("link", { name: "Abrir comisión" })).toBeVisible();
    await expect(page.getByText(comisionCodigo).first()).toBeVisible();

    await cerrarNotificaciones(page);
    await page.getByRole("button", { name: "Asignar responsable" }).click();
    await page.locator("#resp-funcionario").selectOption(funcionarios[1].id);
    await page.locator("#resp-rol").selectOption("CUSTODIA");
    await page.getByRole("button", { name: "Guardar" }).click();
    await expect(page.getByRole("cell", { name: "Custodia" })).toBeVisible();

    await cerrarNotificaciones(page);
    await page.getByRole("button", { name: "Registrar hito" }).click();
    await page.locator("#hito-nombre").fill("Apertura de sobres");
    await page.locator("#hito-fuente").fill("Pliego");
    await page.locator("#hito-prevista").fill(hoyCaracas());
    await page.getByRole("button", { name: "Guardar" }).click();
    await expect(page.getByRole("cell", { name: "Apertura de sobres", exact: true })).toBeVisible();

    await adjuntarDocumentoApi(
      request,
      mundo.headers,
      mundo.companyId,
      tipo.id,
      "GovernmentProcurementFile",
      expedienteId,
    );
    await page.reload();
    await cerrarNotificaciones(page);
    await page.getByRole("button", { name: "Incorporar al expediente" }).click();
    await page.locator("#fol-clase").selectOption("SOLICITUD");
    await page.getByRole("radio", { name: "Documento" }).check();
    const opcionesDocumento = page.locator("#fol-documento option:not([value=''])");
    await expect(opcionesDocumento.first()).toBeAttached();
    const primerDocValor = await opcionesDocumento.first().getAttribute("value");
    await page.locator("#fol-documento").selectOption(primerDocValor as string);
    const opcionesHito = page.locator("#fol-hito option:not([value=''])");
    await expect(opcionesHito.first()).toBeAttached();
    const primerHitoValor = await opcionesHito.first().getAttribute("value");
    await page.locator("#fol-hito").selectOption(primerHitoValor as string);
    await page.getByRole("button", { name: "Guardar" }).click();
    const folios = page.getByRole("region", { name: "Folios del expediente" });
    await expect(folios.getByText("Solicitud de la unidad usuaria")).toBeVisible();
    await expect(folios.getByRole("cell", { name: "1", exact: true }).first()).toBeVisible();

    await cerrarNotificaciones(page);
    await page.getByRole("button", { name: "Incorporar al expediente" }).click();
    await page.locator("#fol-clase").selectOption("ACTOS_MOTIVADOS");
    await page.getByRole("radio", { name: "Acto" }).check();
    await page.locator("#fol-acto").selectOption(acto2.id);
    await page.getByRole("button", { name: "Guardar" }).click();
    await expect(folios.getByRole("cell", { name: "2", exact: true }).first()).toBeVisible();

    await cerrarNotificaciones(page);
    await page.getByRole("button", { name: "Registrar actuación" }).click();
    await page.locator("#act-fecha").fill(hoyCaracas());
    await page.locator("#act-titulo").fill("Revisión de la solicitud");
    await page.locator("#act-detalle").fill("Revisada sin observaciones");
    await page.locator("#act-funcionario").selectOption(funcionarios[0].id);
    const opcionesFolio = page.locator("#act-folio option:not([value=''])");
    await expect(opcionesFolio.first()).toBeAttached();
    const primerFolioValor = await opcionesFolio.first().getAttribute("value");
    await page.locator("#act-folio").selectOption(primerFolioValor as string);
    await page.getByRole("button", { name: "Guardar" }).click();
    await expect(page.getByText("Revisión de la solicitud").first()).toBeVisible();

    await cerrarNotificaciones(page);
    await page.getByRole("button", { name: "Registrar decisión" }).click();
    await page.locator("#act-fecha").fill(hoyCaracas());
    await page.locator("#act-titulo").fill("Continuar el procedimiento");
    await page.locator("#act-resultado").fill("Se continúa");
    await page.locator("#act-funcionario").selectOption(funcionarios[0].id);
    await page.locator("#act-acto").selectOption(acto.id);
    await page.getByRole("button", { name: "Guardar" }).click();
    await expect(page.getByText("Resultado: Se continúa").first()).toBeVisible();

    await cerrarNotificaciones(page);
    await page.getByRole("button", { name: "Actualizar Apertura de sobres" }).click();
    await page.locator("#upd-real").fill(hoyCaracas());
    await page.getByRole("button", { name: "Guardar" }).click();
    const hitosRegion = page.getByRole("region", { name: "Hitos del expediente" });
    await expect(hitosRegion.getByText("Cumplido")).toBeVisible();
    await expect(hitosRegion.getByRole("cell", { name: "Pliego", exact: true })).toBeVisible();

    const crono = page.locator('section[aria-labelledby="sec-cronologia"]');
    await expect(crono).toBeVisible();
    await expect(crono).toContainText("Hito cumplido");
    const cronoTexto = await crono.innerText();
    const indiceAbierto = cronoTexto.indexOf("abierto");
    const indiceRevision = cronoTexto.indexOf("Revisión de la solicitud");
    expect(indiceAbierto).toBeGreaterThanOrEqual(0);
    expect(indiceRevision).toBeGreaterThan(indiceAbierto);
    expect(cronoTexto).toContain("Registro 1");
    expect(cronoTexto).toContain(mundo.username);
    expect(cronoTexto).toContain("Folio 1");

    await expect(page.getByText("Orientación: no decide ni bloquea")).toBeVisible();
    await expect(page.getByText("En curso").first()).toBeVisible();

    const actuaciones = page.locator('section[aria-labelledby="sec-actuaciones"]');
    await cerrarNotificaciones(page);
    await actuaciones.getByRole("button", { name: "Rectificar" }).first().click();
    await page.locator("#act-motivo").fill("Corrección");
    await page.locator("#act-titulo").fill("Revisión corregida de la solicitud");
    await page.locator("#act-funcionario").selectOption(funcionarios[0].id);
    await page.getByRole("button", { name: "Guardar" }).click();
    await expect(crono).toContainText("Revisión corregida de la solicitud");
    await expect(crono).toContainText("Revisión de la solicitud");
    await expect(crono).toContainText("Rectifica el registro");
    await expect(crono).toContainText("Folio 1 ·");

    await cerrarNotificaciones(page);
    await page.locator('nav[aria-label="Menú principal"] a[href="/gobierno/contrataciones/expedientes"]').click();
    await cerrarNotificaciones(page);
    await page.locator("#expediente-buscar").fill(numeroExpediente);
    await expect(page.getByRole("link", { name: numeroExpediente })).toBeVisible();
    await expect(page.getByRole("cell", { name: "Concurso abierto" })).toBeVisible();
    await page.screenshot({ path: test.info().outputPath("exp-lista.png"), fullPage: true });
    await cerrarNotificaciones(page);
    await page.getByRole("link", { name: numeroExpediente }).click();
    await page.waitForURL(/\/expedientes\/[0-9a-f-]{36}$/);
    await page.screenshot({ path: test.info().outputPath("exp-ficha.png"), fullPage: true });

    await cerrarNotificaciones(page);
    await page.getByRole("button", { name: "Cerrar expediente" }).first().click();
    await page.locator("#cie-fecha").fill(hoyCaracas());
    await page.locator("#cie-motivo").fill("Fin de la prueba");
    await page.locator('section[aria-labelledby]').getByRole("button", { name: "Cerrar expediente" }).last().click();
    await expect(page.getByText("Solo consulta")).toBeVisible();
    await expect(page.getByRole("button", { name: "Registrar actuación" })).toHaveCount(0);
  });

  test("EXP-E2E-02 · sin permiso de gestión", async ({ page, request }) => {
    const mundo = await prepararMundo(request, [...RESPONSABLE_ESTRUCTURA]);
    const admin = await sesionApi("admintenant", { tenant: TENANT });
    const usuario = await crearUsuario(
      request,
      admin.headers,
      ["organization:view", "gobierno_expedientes:view"],
      mundo.companyId,
    );
    await entrarEnGobierno(
      page,
      usuario.username,
      mundo.codigo,
      "/gobierno/contrataciones/expedientes",
    );
    await expect(page.getByRole("heading", { name: "Expedientes de contratación" })).toBeVisible();
    await expect(page.getByRole("link", { name: "Nuevo expediente" })).toHaveCount(0);
  });
});
