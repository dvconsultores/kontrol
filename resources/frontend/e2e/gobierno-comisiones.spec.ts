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

test.describe("Gobierno comisiones", () => {
  test("COM-E2E-01 · flujo completo por menú", async ({ request, browser, page }) => {
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
    ]);

    const tipo = await crearTipoDocumental(request, mundo.headers, mundo.companyId);
    await enteActivo(request, mundo.headers, mundo.companyId, tipo.id);
    const estructura = await estructuraVigenteApi(request, mundo.headers, mundo.companyId, tipo.id, ANIO);
    const emisor = await cargoVigenteApi(request, mundo.headers, mundo.companyId, tipo.id, ANIO, estructura.despId, `CE-${Date.now()}`);
    const acto = await actoEmitidoApi(request, mundo, tipo.id, emisor.id, `NUM-${Date.now()}`);

    const nombres = [
      "Persona Comision 1",
      "Persona Comision 2",
      "Persona Comision 3",
      "Persona Comision 4",
      "Persona Comision 5",
      "Persona Comision 6",
      "Persona Comision 7",
      "Persona Comision 8",
    ];

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
    await page.locator('nav[aria-label="Menú principal"] a[href="/gobierno/contrataciones/comisiones"]').click();
    await expect(page.getByRole("heading", { name: "Comisiones de contrataciones" })).toBeVisible();
    await page.getByRole("link", { name: "Nueva comisión" }).click();
    await page.locator("#comision-nombre").fill("Comisión permanente E2E");
    await page.locator("#comision-tipo-form").selectOption("PERMANENTE");
    await page.locator("#comision-desde").fill(hoyCaracas());
    await page.locator("#comision-acto").selectOption(acto.id);
    await page.getByRole("button", { name: "Guardar" }).click();
    await page.waitForURL(/\/comisiones\/[0-9a-f-]{36}$/);
    await expect(page.getByText("Para activar falta")).toBeVisible();
    await cerrarNotificaciones(page);
    await page.getByRole("link", { name: "Editar" }).click();
    await page.locator("#comision-nombre").fill("Comisión permanente E2E editada");
    await page.getByRole("button", { name: "Guardar" }).click();
    await page.waitForURL(/\/comisiones\/[0-9a-f-]{36}$/);
    await expect(page.getByRole("heading", { level: 1, name: "Comisión permanente E2E editada" })).toBeVisible();

    await cerrarNotificaciones(page);
    await page.getByRole("button", { name: "Añadir miembro" }).click();
    const opcionPrimero = page.locator("#miembro-funcionario option").filter({ hasText: "Persona Comision 1" });
    await page.locator("#miembro-funcionario").selectOption(await opcionPrimero.getAttribute("value"));
    await page.locator("#miembro-funcion").selectOption("MIEMBRO");
    await page.locator("#miembro-condicion").selectOption("PRINCIPAL");
    await page.locator("#miembro-area").selectOption("TECNICA");
    await cerrarNotificaciones(page);
    await page.getByRole("button", { name: "Guardar miembro" }).click();
    await expect(page.getByRole("cell", { name: /^Persona Comision 1\b/ }).first()).toBeVisible();

    await cerrarNotificaciones(page);
    await page.getByRole("button", { name: "Añadir miembro" }).click();
    const opcionSegundo = page.locator("#miembro-funcionario option").filter({ hasText: "Persona Comision 2" });
    await page.locator("#miembro-funcionario").selectOption(await opcionSegundo.getAttribute("value"));
    await page.locator("#miembro-funcion").selectOption("MIEMBRO");
    await page.locator("#miembro-condicion").selectOption("SUPLENTE");
    const opcionSuplenteDe = page.locator("#miembro-suplente-de option").filter({ hasText: "Persona Comision 1" });
    await page.locator("#miembro-suplente-de").selectOption(await opcionSuplenteDe.getAttribute("value"));
    await cerrarNotificaciones(page);
    await page.getByRole("button", { name: "Guardar miembro" }).click();
    await expect(page.getByRole("cell", { name: /^Persona Comision 2\b/ }).first()).toBeVisible();

    const comisionId = page.url().match(/\/comisiones\/([0-9a-f-]{36})$/)?.[1];
    expect(comisionId).toBeTruthy();

    const añadirPorApi = async (cuerpo: Record<string, unknown>) => {
      const detalleResp = await request.get(`${API}/gobierno/contrataciones/comisiones/${comisionId}`, {
        headers: mundo.headers,
      });
      expect(detalleResp.status()).toBe(200);
      const detalleData = await detalleResp.json();
      const resp = await request.post(`${API}/gobierno/contrataciones/comisiones/${comisionId}/miembros`, {
        headers: { ...mundo.headers, "If-Match": String(detalleData.version) },
        data: cuerpo,
      });
      expect(resp.status(), await resp.text()).toBe(200);
      return detalleData;
    };

    // Persona Comision 3 principal JURIDICA y 4 suplente
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
    const principal3 = detalle3Data.miembros.find((m: { funcionario: { id: string } }) => m.funcionario.id === funcionarios[2].id);
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

    // Persona Comision 5 principal ECONOMICO_FINANCIERA y 6 suplente
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
    const principal5 = detalle5Data.miembros.find((m: { funcionario: { id: string } }) => m.funcionario.id === funcionarios[4].id);
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

    // Persona Comision 7 SECRETARIO PRINCIPAL
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
    // Persona Comision 8 SECRETARIO SUPLENTE
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

    await page.reload();
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
    await expect(page.getByText("Para activar falta")).toHaveCount(0);
    await expect(page.getByRole("button", { name: "Activar" })).toHaveCount(0);

    const ctx = await browser.newContext();
    const p2 = await ctx.newPage();
    await entrarEnGobierno(p2, activador.username, mundo.codigo, "/gobierno/contrataciones/comisiones");
    const rutaDeFicha = `/gobierno/contrataciones/comisiones/${comisionId}`;
    await p2.goto(rutaDeFicha);
    await cerrarNotificaciones(p2);
    await p2.getByRole("button", { name: "Activar" }).click();
    await expect(p2.getByRole("heading", { level: 1 })).toBeVisible();
    await expect(p2.getByText(/Vigente/).first()).toBeVisible();
    await ctx.close();

    await page.reload();
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
    await cerrarNotificaciones(page);
    await page.getByRole("button", { name: "Declarar inhibición" }).click();
    await page.locator("#inhibicion-miembro").selectOption(
      await page.locator("#inhibicion-miembro option").filter({ hasText: "Persona Comision 1" }).getAttribute("value"),
    );
    await page.locator("#inhibicion-asunto").fill("Asunto de prueba");
    await page.locator("#inhibicion-causal").selectOption("INTERES");
    await page.locator("#inhibicion-descripcion").fill("Descripción de la inhibición");
    await page.locator("#inhibicion-fecha").fill(hoyCaracas());
    await cerrarNotificaciones(page);
    await page.getByRole("button", { name: "Declarar", exact: true }).click();
    await expect(page.getByRole("cell", { name: "Declarada" })).toBeVisible();
    await expect(page.getByRole("cell", { name: /Persona Comision 2/ }).first()).toBeVisible();

    await expect(page.getByText(/Activada con la regla/)).toBeVisible();
    await expect(page.getByRole("link", { name: "Abrir el acto" })).toHaveAttribute("href", `/gobierno/actos/${acto.id}`);

    // Consulta a una fecha anterior
    const fechaAnterior = new Date(Date.parse(`${hoyCaracas()}T12:00:00Z`) - 86_400_000).toISOString().slice(0, 10);
    await page.locator("#comision-fecha-consulta").fill(fechaAnterior);
    await expect(page.getByText(/No concede nada hoy/)).toBeVisible();
    await page.locator("#comision-fecha-consulta").fill("");
    const ctx2 = await browser.newContext();
    const p3 = await ctx2.newPage();
    await entrarEnGobierno(p3, activador.username, mundo.codigo, "/gobierno/contrataciones/comisiones");
    await p3.goto(rutaDeFicha);
    await cerrarNotificaciones(p3);
    await p3.getByRole("button", { name: "Resolver inhibición de Persona Comision 1" }).click();
    await p3.locator("#resolver-decision").selectOption("ACEPTADA");
    await p3.locator("#resolver-motivo").fill("Causal comprobada por la autoridad");
    await cerrarNotificaciones(p3);
    await p3.getByRole("button", { name: "Resolver", exact: true }).click();
    await expect(p3.getByRole("cell", { name: "Aceptada" })).toBeVisible();
    await ctx2.close();
    await page.reload();
    await cerrarNotificaciones(page);
    await page.getByRole("button", { name: "Registrar notificación al SNC" }).click();
    await page.locator("#snc-fecha").fill(hoyCaracas());
    await page.locator("#snc-referencia").fill("Oficio SNC 123");
    await cerrarNotificaciones(page);
    await page.getByRole("button", { name: "Registrar", exact: true }).click();
    await expect(page.getByText(/Oficio SNC 123/).first()).toBeVisible();
    await cerrarNotificaciones(page);
    await page.getByRole("button", { name: "Terminar a Persona Comision 3" }).click();
    await page.locator("#fin-fecha").fill(hoyCaracas());
    await page.locator("#fin-causa").selectOption("RETIRO_RENUNCIA_REMOCION");
    await page.locator("#fin-motivo").fill("Renuncia presentada por escrito");
    await cerrarNotificaciones(page);
    await page.getByRole("button", { name: "Terminar miembro" }).click();
    await expect(page.getByRole("heading", { name: "Miembros anteriores" })).toBeVisible();
    await cerrarNotificaciones(page);
    await page.getByRole("button", { name: "Cerrar comisión" }).click();
    await page.locator("#cierre-fecha").fill(hoyCaracas());
    await page.locator("#cierre-motivo").fill("Concluyó el período de la comisión");
    await cerrarNotificaciones(page);
    await page.getByRole("button", { name: "Cerrar comisión" }).last().click();
    await expect(page.getByText(/Cerrada/).first()).toBeVisible();
  });

  test("COM-E2E-02 · sin capacidad no entra", async ({ page, request }) => {
    const mundo = await prepararMundo(request, ["organization:view"]);
    await entrarEnGobierno(page, mundo.username, mundo.codigo, "/organizacion/empresas");
    await page.goto("/gobierno/contrataciones/comisiones/00000000-0000-0000-0000-000000000000");
    await expect(page.getByRole("heading", { name: "Acceso prohibido" })).toBeVisible();
  });
});
