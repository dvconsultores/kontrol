import AxeBuilder from "@axe-core/playwright";
import type { APIRequestContext, Page } from "@playwright/test";
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
  estructuraVigenteApi,
  prepararMundo,
} from "./helpers/gobierno";

test.setTimeout(420_000);

const WCAG = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"];

function hoyCaracas(): string {
  return new Intl.DateTimeFormat("en-CA", { timeZone: "America/Caracas" }).format(new Date());
}

async function sinViolacionesSerias(page: Page, contexto: string): Promise<void> {
  const resultados = await new AxeBuilder({ page })
    .include("main")
    .withTags(WCAG)
    .analyze();

  const serias = resultados.violations.filter((v) =>
    ["critical", "serious"].includes(v.impact ?? ""),
  );

  expect(
    serias.map((v) => ({ id: v.id, help: v.help })),
    contexto,
  ).toEqual([]);

  if (page.viewportSize()?.width === 320) {
    const sinDesbordamiento = await page.evaluate(
      () => document.documentElement.scrollWidth <= document.documentElement.clientWidth,
    );
    expect(sinDesbordamiento, contexto).toBe(true);
  }
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

test.describe("Gobierno política de comisión", () => {
  test("CP-E2E-01 · política de comisión de punta a punta", async ({ request, page }) => {
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
      "gobierno_comisiones:close",
      "gobierno_comisiones:configure",
      "gobierno_expedientes:view",
      "gobierno_expedientes:manage",
      "gobierno_evaluacion:view",
      "gobierno_decision:view",
    ]);

    const tipo = await crearTipoDocumental(request, mundo.headers, mundo.companyId);
    await enteActivo(request, mundo.headers, mundo.companyId, tipo.id);
    const estructura = await estructuraVigenteApi(request, mundo.headers, mundo.companyId, tipo.id, ANIO);
    const emisor = await cargoVigenteApi(request, mundo.headers, mundo.companyId, tipo.id, ANIO, estructura.despId, `CE-${Date.now()}`);
    const acto = await actoEmitidoApi(request, mundo, tipo.id, emisor.id, `NUM-${Date.now()}`);

    const nombres = Array.from({ length: 12 }, (_, i) => `Persona Política Comisión ${i + 1}`);
    const funcionarios: { id: string; nombre: string }[] = [];
    for (const nombre of nombres) {
      const resp = await request.post(`${API}/gobierno/ocupacion/funcionarios`, {
        headers: mundo.headers,
        data: {
          nombre,
          tipo_documento: "V",
          numero_documento: String(Math.floor(10000000 + Math.random() * 89999999)),
        },
      });
      expect(resp.status(), await resp.text()).toBe(201);
      const data = await resp.json();
      funcionarios.push({ id: data.id, nombre });
    }

    const admin = await sesionApi("admintenant", { tenant: TENANT });
    const activador = await crearUsuario(
      request,
      admin.headers,
      ["organization:view", "gobierno_comisiones:view", "gobierno_comisiones:activate"],
      mundo.companyId,
    );

    await entrarEnGobierno(page, mundo.username, mundo.codigo, "/gobierno/ente");
    await page.locator('nav[aria-label="Menú principal"] a[href="/gobierno/contrataciones/politicas-comision"]').click();
    await expect(page.getByRole("heading", { level: 1, name: "Políticas de comisión" })).toBeVisible();
    await page.getByRole("link", { name: "Nueva política" }).first().click();

    const codigo = `CP${Date.now().toString(36).toUpperCase()}`.slice(0, 20);
    await page.getByLabel(/^Código/).fill(codigo);
    await page.getByLabel(/^Nombre/).fill("Política comisión permanente E2E");
    await page.getByLabel(/^Tipo de comisión/).selectOption("PERMANENTE");
    await page.getByLabel(/^Base normativa/).selectOption("LCP_ART14");
    await page.getByLabel(/^Fundamento/).fill("Ley de Contrataciones Públicas, art. 14");
    await page.getByLabel(/^Desde/).fill(hoyCaracas());
    await page.getByLabel(/^Máximo de principales/).fill("3");
    await page.getByLabel(/^Tipo de quórum/).selectOption("SIMPLE_MAJORITY");
    await page.getByLabel(/^Tipo de mayoría/).selectOption("SIMPLE_MAJORITY");
    await page.getByLabel(/^Base de la decisión/).selectOption("MIEMBROS_CON_VOTO");
    await page.getByRole("button", { name: "Añadir requisito" }).click();
    await page.getByLabel(/^Etiqueta/).fill("Principal técnico");
    await page.getByLabel(/^Función/).selectOption("MIEMBRO");
    await page.getByLabel(/^Condición del miembro/).selectOption("PRINCIPAL");
    await page.getByLabel(/^Tipo de requisito/).selectOption("AREA");
    await page.getByLabel(/^Área/).selectOption("TECNICA");
    await page.getByLabel(/^Mínimo(?! de)/).fill("1");
    await sinViolacionesSerias(page, "formulario política");

    await page.getByRole("button", { name: "Guardar borrador" }).click();
    await page.waitForURL(/\/politicas-comision\/[0-9a-f-]{36}$/);
    await expect(page.getByRole("heading", { level: 2, name: "Requisitos de integración" })).toBeVisible();
    await expect(page.getByText("Principal técnico").first()).toBeVisible();
    await sinViolacionesSerias(page, "ficha política borrador");

    const politicaId = page.url().split("/").pop() as string;
    const detalleResp = await request.get(`${API}/gobierno/contrataciones/politicas-comision/${politicaId}`, {
      headers: mundo.headers,
    });
    expect(detalleResp.status(), await detalleResp.text()).toBe(200);
    const detalle = await detalleResp.json();
    const activarPoliticaResp = await request.post(
      `${API}/gobierno/contrataciones/politicas-comision/${politicaId}/activar`,
      {
        headers: { ...activador.headers, "If-Match": String(detalle.version) },
      },
    );
    expect(activarPoliticaResp.status(), await activarPoliticaResp.text()).toBe(200);

    await page.reload();
    await expect(page.getByText("Vigente").first()).toBeVisible();
    await expect(page.getByText("Historia").first()).toBeVisible();
    await expect(page.getByText("Creada").first()).toBeVisible();
    await expect(page.getByText("Activada").first()).toBeVisible();

    await page.locator('nav[aria-label="Menú principal"] a[href="/gobierno/contrataciones/comisiones"]').click();
    await expect(page.getByRole("heading", { level: 1, name: "Comisiones de contrataciones" })).toBeVisible();
    await page.getByRole("link", { name: "Nueva comisión" }).click();
    await page.locator("#comision-nombre").fill("Comisión con política E2E");
    await page.locator("#comision-tipo-form").selectOption("PERMANENTE");
    await page.locator("#comision-politica").selectOption(politicaId);
    await page.locator("#comision-desde").fill(hoyCaracas());
    await page.locator("#comision-acto").selectOption(acto.id);
    await page.getByRole("button", { name: "Guardar" }).click();
    await page.waitForURL(/\/comisiones\/[0-9a-f-]{36}$/);
    await expect(page.getByText("Regla aplicada").first()).toBeVisible();
    await expect(page.getByText(codigo).first()).toBeVisible();
    await expect(page.getByText("Se congelará al activar la comisión.").first()).toBeVisible();
    await cerrarNotificaciones(page);

    const comisionId = page.url().split("/").pop() as string;
    const comisionDetalleResp = await request.get(`${API}/gobierno/contrataciones/comisiones/${comisionId}`, {
      headers: mundo.headers,
    });
    expect(comisionDetalleResp.status(), await comisionDetalleResp.text()).toBe(200);
    let comisionDetalle = await comisionDetalleResp.json();

    type MiembroApi = { id: string; funcion: string; condicion: string; suplente_de_id: string | null; funcionario: { id: string } };
    const comisionUrl = `${API}/gobierno/contrataciones/comisiones/${comisionId}`;
    const anadirMiembro = async (datos: Record<string, unknown>) => {
      const resp = await request.post(`${comisionUrl}/miembros`, {
        headers: { ...mundo.headers, "If-Match": String(comisionDetalle.version) },
        data: { certificacion_snc: null, desde: null, acto_id: null, suplente_de_id: null, area: null, ...datos },
      });
      expect(resp.status(), await resp.text()).toBe(200);
      comisionDetalle = await resp.json();
    };
    const miembroDe = (funcionarioId: string): MiembroApi =>
      (comisionDetalle.miembros as MiembroApi[]).find((m) => m.funcionario.id === funcionarioId) as MiembroApi;

    const areas = ["TECNICA", "JURIDICA", "ECONOMICO_FINANCIERA", "TECNICA", "JURIDICA"];
    for (let i = 0; i < areas.length; i++) {
      await anadirMiembro({ funcionario_id: funcionarios[i].id, funcion: "MIEMBRO", condicion: "PRINCIPAL", area: areas[i] });
      await anadirMiembro({
        funcionario_id: funcionarios[i + 5].id,
        funcion: "MIEMBRO",
        condicion: "SUPLENTE",
        suplente_de_id: miembroDe(funcionarios[i].id).id,
      });
    }
    await anadirMiembro({ funcionario_id: funcionarios[10].id, funcion: "SECRETARIO", condicion: "PRINCIPAL" });
    await anadirMiembro({ funcionario_id: funcionarios[11].id, funcion: "SECRETARIO", condicion: "SUPLENTE" });

    await page.reload();
    await expect(page.getByText("Se admiten como máximo 3 miembros principales").first()).toBeVisible();

    // Corrige la composición: retira los dos principales sobrantes y sus suplentes (DELETE en borrador).
    for (const i of [3, 4]) {
      for (const funcionarioId of [funcionarios[i + 5].id, funcionarios[i].id]) {
        const resp = await request.delete(`${comisionUrl}/miembros/${miembroDe(funcionarioId).id}`, {
          headers: { ...mundo.headers, "If-Match": String(comisionDetalle.version) },
        });
        expect(resp.status(), await resp.text()).toBe(200);
        comisionDetalle = await resp.json();
      }
    }

    await page.reload();
    await expect(page.getByText("Se admiten como máximo 3 miembros principales")).toHaveCount(0);

    const activarComisionResp = await request.post(`${API}/gobierno/contrataciones/comisiones/${comisionId}/activar`, {
      headers: { ...activador.headers, "If-Match": String(comisionDetalle.version) },
    });
    expect(activarComisionResp.status(), await activarComisionResp.text()).toBe(200);

    await page.reload();
    await expect(page.getByText("Congelada al activarse").first()).toBeVisible();

    const expedienteResp = await request.post(`${API}/gobierno/contrataciones/expedientes`, {
      headers: mundo.headers,
      data: {
        numero: `EXP-${Date.now()}`,
        fecha_inicio: hoyCaracas(),
        objeto: "Adquisición de equipos con política",
        partes: null,
        tipo_contratacion: "BIENES",
        modalidad_declarada: "CONCURSO_ABIERTO",
        modalidad_fundamento: "LCP art. 78",
        modalidad_fuente: "LCP",
        unidad_id: estructura.despId,
        responsable_id: funcionarios[0].id,
      },
    });
    expect(expedienteResp.status(), await expedienteResp.text()).toBe(201);
    const expediente = await expedienteResp.json();
    const vincularResp = await request.post(
      `${API}/gobierno/contrataciones/expedientes/${expediente.id}/comision`,
      {
        headers: { ...mundo.headers, "If-Match": String(expediente.version) },
        data: { comision_id: comisionId, no_aplica_motivo: null, motivo: null },
      },
    );
    expect(vincularResp.status(), await vincularResp.text()).toBe(200);

    // PROC-07 y PROC-08 consumen la regla congelada de la comisión (estado real de la API).
    const evaluacionResp = await request.get(
      `${API}/gobierno/contrataciones/expedientes/${expediente.id}/evaluacion`,
      { headers: mundo.headers },
    );
    expect(evaluacionResp.status(), await evaluacionResp.text()).toBe(200);
    const evaluacion = await evaluacionResp.json();
    expect(evaluacion.modo).toBe("COMISION");
    expect(String(evaluacion.regla?.etiqueta)).toContain(codigo);
    expect(evaluacion.regla?.miembros_con_voto).toBe(3);
    expect(evaluacion.regla?.quorum_requerido).toBe(2);
    const decisionResp = await request.get(
      `${API}/gobierno/contrataciones/expedientes/${expediente.id}/decision`,
      { headers: mundo.headers },
    );
    expect(decisionResp.status(), await decisionResp.text()).toBe(200);
    const decision = await decisionResp.json();
    expect(decision.modo).toBe("COMISION");
    expect(String(decision.regla?.etiqueta)).toContain(codigo);
    await page.goto(`/gobierno/contrataciones/expedientes/${expediente.id}`);
    await expect(page.locator('[aria-labelledby="sec-evaluacion"]')).toBeVisible();

    const otroMundo = await prepararMundo(request, [...RESPONSABLE_ESTRUCTURA, "gobierno_comisiones:view"]);
    const aislamientoResp = await request.get(
      `${API}/gobierno/contrataciones/politicas-comision/${politicaId}`,
      { headers: otroMundo.headers },
    );
    expect(aislamientoResp.status(), await aislamientoResp.text()).toBe(404);

    for (const ancho of [1280, 390, 320]) {
      await page.setViewportSize({ width: ancho, height: 800 });
      await page.goto("/gobierno/contrataciones/politicas-comision");
      await expect(page.getByRole("heading", { level: 1, name: "Políticas de comisión" })).toBeVisible();
      await sinViolacionesSerias(page, `lista políticas ${ancho}`);

      await page.goto(`/gobierno/contrataciones/politicas-comision/${politicaId}`);
      await expect(page.getByText(codigo).first()).toBeVisible();
      await sinViolacionesSerias(page, `ficha política ${ancho}`);

      await page.goto(`/gobierno/contrataciones/comisiones/${comisionId}`);
      await expect(page.getByText("Regla aplicada").first()).toBeVisible();
      await sinViolacionesSerias(page, `ficha comisión ${ancho}`);
    }
  });
});
