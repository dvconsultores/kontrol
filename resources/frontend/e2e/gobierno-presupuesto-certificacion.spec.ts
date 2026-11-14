import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "./helpers/sesion";
import {
  ANIO,
  API,
  adjuntarDocumentoApi,
  cerrarNotificaciones,
  crearTipoDocumental,
  entrarEnGobierno,
  prepararMundo,
  enteActivo,
  estructuraVigenteApi,
  RESPONSABLE_ESTRUCTURA,
} from "./helpers/gobierno";
import type { Page } from "@playwright/test";

const WCAG = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"];

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

function hoyCaracas(): string {
  return new Intl.DateTimeFormat("en-CA", { timeZone: "America/Caracas" }).format(
    new Date(),
  );
}

test.describe("Certificación presupuestaria", () => {
  test("BUD-06: disponibilidad, certificación, descarga, anulación, historia, aislamiento y responsive", async ({ page, request }) => {
    test.setTimeout(300_000);

    const PERMISOS = [
      ...RESPONSABLE_ESTRUCTURA,
      "gobierno_cargos:view",
      "gobierno_cargos:edit",
      "gobierno_cargos:publish",
      "documentos:view",
      "documentos:create",
      "documentos:upload",
      "documentos:link",
      "documentos:download",
      "documentos:manage_types",
      "gobierno_presupuesto:view",
      "gobierno_presupuesto:manage",
      "gobierno_presupuesto:approve",
      "gobierno_presupuesto:certify",
    ];

    const mundo = await prepararMundo(request, PERMISOS);
    const tipo = await crearTipoDocumental(request, mundo.headers, mundo.companyId);
    const anio = ANIO;

    await enteActivo(request, mundo.headers, mundo.companyId, tipo.id);
    const { despId } = await estructuraVigenteApi(request, mundo.headers, mundo.companyId, tipo.id, anio);

    const cargoResp = await request.post(`${API}/gobierno/estructuras/${anio}/cargos`, {
      headers: mundo.headers,
      data: {
        codigo: "C-PRES",
        denominacion: "Director de Presupuesto",
        unidad_id: despId,
        vigente_desde: `${anio}-01-01`,
      },
    });
    expect(cargoResp.status()).toBe(201);
    const cargo = await cargoResp.json();

    const competenciaResp = await request.post(
      `${API}/gobierno/estructuras/${anio}/cargos/${cargo.id}/competencias`,
      {
        headers: { ...mundo.headers, "If-Match": '"1"' },
        data: {
          accion: "FIRMAR",
          materia: "PRESUPUESTO",
          tipo_limite: "SIN_LIMITE",
          monto: null,
          moneda: null,
        },
      },
    );
    expect(competenciaResp.status()).toBe(201);

    await adjuntarDocumentoApi(
      request,
      mundo.headers,
      mundo.companyId,
      tipo.id,
      "GovernmentPosition",
      cargo.id,
    );

    const activarCargoResp = await request.post(
      `${API}/gobierno/estructuras/${anio}/cargos/${cargo.id}/activar`,
      {
        headers: { ...mundo.headers, "If-Match": '"2"' },
      },
    );
    expect(activarCargoResp.status()).toBe(200);

    const crearEjercicioResp = await request.post(`${API}/gobierno/presupuesto/ejercicios`, {
      headers: mundo.headers,
      data: { anio },
    });
    expect(crearEjercicioResp.status()).toBe(201);
    const ejercicio = await crearEjercicioResp.json();
    let version = ejercicio.version;

    const nivelesResp = await request.put(`${API}/gobierno/presupuesto/ejercicios/${ejercicio.id}/niveles`, {
      headers: { ...mundo.headers, "If-Match": String(version) },
      data: { niveles: [{ nombre: "Sector" }, { nombre: "Programa" }] },
    });
    expect(nivelesResp.status()).toBe(200);
    version = (await nivelesResp.json()).version;

    const cat01Resp = await request.post(`${API}/gobierno/presupuesto/ejercicios/${ejercicio.id}/categorias`, {
      headers: { ...mundo.headers, "If-Match": String(version) },
      data: {
        nivel_orden: 1,
        parent_id: null,
        codigo: "01",
        denominacion: "Sector salud",
      },
    });
    expect(cat01Resp.status()).toBe(201);
    const detalleCat01 = await cat01Resp.json();
    version = detalleCat01.version;
    const cat01 = detalleCat01.categorias.find((c: { codigo_completo: string }) => c.codigo_completo === "01");

    const cat02Resp = await request.post(`${API}/gobierno/presupuesto/ejercicios/${ejercicio.id}/categorias`, {
      headers: { ...mundo.headers, "If-Match": String(version) },
      data: {
        nivel_orden: 2,
        parent_id: cat01.id,
        codigo: "02",
        denominacion: "Atención primaria",
      },
    });
    expect(cat02Resp.status()).toBe(201);
    const detalleCat02 = await cat02Resp.json();
    version = detalleCat02.version;
    const cat02 = detalleCat02.categorias.find(
      (c: { codigo_completo: string }) => c.codigo_completo === "01.02",
    );

    await adjuntarDocumentoApi(request, mundo.headers, mundo.companyId, tipo.id, "GovernmentBudgetYear", ejercicio.id);
    await adjuntarDocumentoApi(request, mundo.headers, mundo.companyId, tipo.id, "GovernmentBudgetYear", ejercicio.id);
    await adjuntarDocumentoApi(request, mundo.headers, mundo.companyId, tipo.id, "GovernmentBudgetYear", ejercicio.id);

    const documentosResp = await request.get(`${API}/documentos/por-recurso/GovernmentBudgetYear/${ejercicio.id}`, { headers: mundo.headers });
    expect(documentosResp.status()).toBe(200);
    const documentos = (await documentosResp.json()) as Array<{ id: string }>;
    expect(documentos.length).toBeGreaterThanOrEqual(3);

    const clasificadorResp = await request.put(`${API}/gobierno/presupuesto/ejercicios/${ejercicio.id}/clasificador`, {
      headers: { ...mundo.headers, "If-Match": String(version) },
      data: {
        edicion: "Clasificador del ente",
        procedencia: "Copia entregada por la Dirección de Presupuesto",
        documento_id: documentos[0].id,
      },
    });
    expect(clasificadorResp.status()).toBe(200);
    version = (await clasificadorResp.json()).version;

    const partida301Resp = await request.post(`${API}/gobierno/presupuesto/ejercicios/${ejercicio.id}/clasificador/partidas`, {
      headers: { ...mundo.headers, "If-Match": String(version) },
      data: {
        tipo: "RECURSO",
        codigo: "301",
        denominacion: "Ingresos propios",
        nivel: 1,
        codigo_padre: null,
        vigente_desde: null,
        vigente_hasta: null,
      },
    });
    expect(partida301Resp.status()).toBe(201);
    version = (await partida301Resp.json()).version;

    const partida401Resp = await request.post(`${API}/gobierno/presupuesto/ejercicios/${ejercicio.id}/clasificador/partidas`, {
      headers: { ...mundo.headers, "If-Match": String(version) },
      data: {
        tipo: "EGRESO",
        codigo: "401",
        denominacion: "Gasto corriente",
        nivel: 1,
        codigo_padre: null,
        vigente_desde: null,
        vigente_hasta: null,
      },
    });
    expect(partida401Resp.status()).toBe(201);
    version = (await partida401Resp.json()).version;

    const partida40101Resp = await request.post(`${API}/gobierno/presupuesto/ejercicios/${ejercicio.id}/clasificador/partidas`, {
      headers: { ...mundo.headers, "If-Match": String(version) },
      data: {
        tipo: "EGRESO",
        codigo: "401.01",
        denominacion: "Servicios personales",
        nivel: 2,
        codigo_padre: "401",
        vigente_desde: null,
        vigente_hasta: null,
      },
    });
    expect(partida40101Resp.status()).toBe(201);
    version = (await partida40101Resp.json()).version;

    const fuentesResp = await request.post(`${API}/gobierno/presupuesto/ejercicios/${ejercicio.id}/fuentes`, {
      headers: { ...mundo.headers, "If-Match": String(version) },
      data: {
        codigo: "F01",
        denominacion: "Ingresos propios",
        procedencia: "Ordenanza municipal de ingresos del ente",
      },
    });
    expect(fuentesResp.status()).toBe(201);
    const fuentesDatos = await fuentesResp.json();
    version = fuentesDatos.version;
    const fuenteF01 = fuentesDatos.items.find((f: { codigo: string }) => f.codigo === "F01");

    const partidasResp = await request.get(`${API}/gobierno/presupuesto/ejercicios/${ejercicio.id}/clasificador/partidas`, {
      headers: mundo.headers,
    });
    expect(partidasResp.status()).toBe(200);
    const partidas = (await partidasResp.json()) as { items: Array<{ id: string; codigo: string }> };
    const partida301 = partidas.items.find((p) => p.codigo === "301");
    const partida401 = partidas.items.find((p) => p.codigo === "401");
    const partida40101 = partidas.items.find((p) => p.codigo === "401.01");
    expect(partida301).toBeTruthy();
    expect(partida401).toBeTruthy();
    expect(partida40101).toBeTruthy();

    const ingresoResp = await request.post(
      `${API}/gobierno/presupuesto/ejercicios/${ejercicio.id}/presupuesto-aprobado/ingresos`,
      {
        headers: { ...mundo.headers, "If-Match": String(version) },
        data: {
          partida_id: partida301?.id,
          monto: "5000.00",
        },
      },
    );
    expect(ingresoResp.status()).toBe(201);
    version = (await ingresoResp.json()).version;

    const creditoResp = await request.post(
      `${API}/gobierno/presupuesto/ejercicios/${ejercicio.id}/presupuesto-aprobado/creditos`,
      {
        headers: { ...mundo.headers, "If-Match": String(version) },
        data: {
          categoria_id: cat02.id,
          partida_id: partida40101?.id,
          fuente_id: fuenteF01.id,
          monto: "1000.00",
        },
      },
    );
    expect(creditoResp.status()).toBe(201);
    version = (await creditoResp.json()).version;

    const ejercicioActualResp = await request.get(`${API}/gobierno/presupuesto/ejercicios/${ejercicio.id}`, {
      headers: mundo.headers,
    });
    expect(ejercicioActualResp.status()).toBe(200);
    const ejercicioActual = await ejercicioActualResp.json();

    const aprobarResp = await request.post(
      `${API}/gobierno/presupuesto/ejercicios/${ejercicio.id}/aprobar`,
      {
        headers: { ...mundo.headers, "If-Match": String(ejercicioActual.version) },
        data: {
          referencia: "Gaceta Municipal Extraordinaria N.º 9",
          fecha: hoyCaracas(),
          documento_id: documentos[1].id,
        },
      },
    );
    expect(aprobarResp.status()).toBe(200);

    await entrarEnGobierno(page, mundo.username, mundo.codigo, "/gobierno/presupuesto/ejercicios");
    await cerrarNotificaciones(page);

    await page.getByRole("link", { name: `Ejercicio ${anio}`, exact: true }).click();
    await expect(page.getByRole("heading", { name: `Ejercicio presupuestario ${anio}`, exact: true })).toBeVisible();

    const seccion = page.locator("section").filter({ has: page.getByRole("heading", { name: "Disponibilidad y certificaciones", exact: true }) });
    await expect(page.getByRole("region", { name: "Tabla de disponibilidad", exact: true })).toContainText("1.000,00");

    const emitirRespPromise = page.waitForResponse(
      (resp) =>
        resp.request().method() === "POST" &&
        new URL(resp.url()).pathname.endsWith("/certificaciones"),
    );
    await seccion.getByRole("combobox", { name: "Crédito presupuestario (obligatorio)", exact: true }).selectOption({ index: 1 });
    await seccion.getByRole("textbox", { name: "Monto (obligatorio)", exact: true }).fill("300,00");
    await seccion.getByRole("textbox", { name: "Concepto (obligatorio)", exact: true }).fill("Adquisición de material médico");
    await seccion.getByRole("textbox", { name: "Referencia del expediente (obligatorio)", exact: true }).fill("EXP-PRES-2026-001");
    await seccion.getByRole("combobox", { name: "Firmante (cargo) (obligatorio)", exact: true }).selectOption({ index: 1 });
    await seccion.getByRole("button", { name: "Emitir certificación", exact: true }).click();
    const emitirResp = await emitirRespPromise;
    expect(emitirResp.status()).toBe(201);
    const cert = await emitirResp.json();

    await expect(seccion).toContainText(`Certificación ${cert.codigo} emitida`);
    await expect(seccion).toContainText("saldo antes 1.000,00");
    await expect(seccion).toContainText("saldo después 700,00");

    const tablaCertificaciones = page.getByRole("region", { name: "Tabla de certificaciones", exact: true });
    await expect(tablaCertificaciones).toContainText(cert.codigo);
    await expect(tablaCertificaciones).toContainText("EXP-PRES-2026-001");
    await expect(tablaCertificaciones).toContainText("C-PRES · Director de Presupuesto");
    await expect(page.getByRole("region", { name: "Tabla de disponibilidad", exact: true })).toContainText("700,00");

    const [descarga] = await Promise.all([
      page.waitForEvent("download"),
      seccion.getByRole("button", { name: `Descargar ${cert.codigo}`, exact: true }).click(),
    ]);
    expect(descarga.suggestedFilename()).toBe(`certificacion-${cert.codigo}.pdf`);

    await seccion.getByRole("combobox", { name: "Crédito presupuestario (obligatorio)", exact: true }).selectOption({ index: 1 });
    await seccion.getByRole("textbox", { name: "Monto (obligatorio)", exact: true }).fill("800,00");
    await seccion.getByRole("textbox", { name: "Concepto (obligatorio)", exact: true }).fill("Adquisición de material médico");
    await seccion.getByRole("textbox", { name: "Referencia del expediente (obligatorio)", exact: true }).fill("EXP-PRES-2026-001");
    await seccion.getByRole("combobox", { name: "Firmante (cargo) (obligatorio)", exact: true }).selectOption({ index: 1 });

    const excesoRespPromise = page.waitForResponse(
      (resp) =>
        resp.request().method() === "POST" &&
        new URL(resp.url()).pathname.endsWith("/certificaciones"),
    );
    await seccion.getByRole("button", { name: "Emitir certificación", exact: true }).click();
    const excesoResp = await excesoRespPromise;
    expect(excesoResp.status()).toBe(422);
    expect((await excesoResp.json()).code).toBe("GOV_BUDGET_INSUFFICIENT_AVAILABILITY");
    await cerrarNotificaciones(page);
    await expect(page.getByRole("region", { name: "Tabla de disponibilidad", exact: true })).toContainText("700,00");

    await seccion.getByRole("textbox", { name: `Motivo de anulación de ${cert.codigo}`, exact: true }).fill("Error en el expediente de origen");

    const anularRespPromise = page.waitForResponse(
      (resp) =>
        resp.request().method() === "POST" &&
        new URL(resp.url()).pathname.endsWith(`/certificaciones/${cert.id}/anular`),
    );
    await seccion.getByRole("button", { name: `Anular ${cert.codigo}`, exact: true }).click();
    const anularResp = await anularRespPromise;
    expect(anularResp.status()).toBe(200);

    await expect(page.getByRole("region", { name: "Tabla de disponibilidad", exact: true })).toContainText("1.000,00");
    await expect(page.getByRole("region", { name: "Tabla de certificaciones", exact: true })).toContainText("Anulada");

    const ejercicioHistoriaResp = await request.get(`${API}/gobierno/presupuesto/ejercicios/${ejercicio.id}`, {
      headers: mundo.headers,
    });
    expect(ejercicioHistoriaResp.status()).toBe(200);
    const ejercicioHistoria = await ejercicioHistoriaResp.json();
    const tiposHistoria = (ejercicioHistoria.historia ?? []).map((h: { tipo: string }) => h.tipo);
    expect(tiposHistoria).toContain("CERTIFICACION_EMITIDA");
    expect(tiposHistoria).toContain("CERTIFICACION_ANULADA");

    const otro = await prepararMundo(request, ["organization:view", "gobierno_presupuesto:view"]);
    const aislamientoResp = await request.get(
      `${API}/gobierno/presupuesto/ejercicios/${ejercicio.id}/disponibilidad`,
      {
        headers: otro.headers,
      },
    );
    expect(aislamientoResp.status()).toBe(404);

    for (const ancho of [1280, 390, 320]) {
      await page.setViewportSize({ width: ancho, height: 800 });
      await expect(page.getByRole("heading", { name: `Ejercicio presupuestario ${anio}`, exact: true })).toBeVisible();
      await sinViolacionesSerias(page, `certificación ${ancho}`);
    }
  });
});
