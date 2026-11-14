import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "./helpers/sesion";
import {
  ANIO,
  API,
  TENANT,
  adjuntarDocumentoApi,
  cerrarNotificaciones,
  crearTipoDocumental,
  crearUsuario,
  entrarEnGobierno,
  prepararMundo,
  enteActivo,
  estructuraVigenteApi,
  RESPONSABLE_ESTRUCTURA,
} from "./helpers/gobierno";
import { sesionApi } from "./helpers/sesion";
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

test.describe("Compromiso presupuestario", () => {
  test("BUD-08: compromiso parcial y total, sin doble descuento, exceso bloqueado, CDP en uso, anulación, historia, aislamiento y responsive", async ({ page, request }) => {
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
      "gobierno_presupuesto:commit",
    ];

    const mundo = await prepararMundo(request, PERMISOS);
    const admin = await sesionApi("admintenant", { tenant: TENANT });
    const certificador = await crearUsuario(
      request,
      admin.headers,
      ["organization:view", "gobierno_presupuesto:view", "gobierno_presupuesto:certify"],
      mundo.companyId,
    );
    const tipo = await crearTipoDocumental(request, mundo.headers, mundo.companyId);
    const anio = ANIO;

    await enteActivo(request, mundo.headers, mundo.companyId, tipo.id);
    const { despId } = await estructuraVigenteApi(request, mundo.headers, mundo.companyId, tipo.id, anio);

    const cargoPresResp = await request.post(`${API}/gobierno/estructuras/${anio}/cargos`, {
      headers: mundo.headers,
      data: {
        codigo: "C-PRES",
        denominacion: "Director de Presupuesto",
        unidad_id: despId,
        vigente_desde: `${anio}-01-01`,
      },
    });
    expect(cargoPresResp.status()).toBe(201);
    const cargoPres = await cargoPresResp.json();

    const competenciaPresResp = await request.post(
      `${API}/gobierno/estructuras/${anio}/cargos/${cargoPres.id}/competencias`,
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
    expect(competenciaPresResp.status()).toBe(201);

    await adjuntarDocumentoApi(
      request,
      mundo.headers,
      mundo.companyId,
      tipo.id,
      "GovernmentPosition",
      cargoPres.id,
    );

    const activarCargoPresResp = await request.post(
      `${API}/gobierno/estructuras/${anio}/cargos/${cargoPres.id}/activar`,
      {
        headers: { ...mundo.headers, "If-Match": '"2"' },
      },
    );
    expect(activarCargoPresResp.status()).toBe(200);

    const cargoAdmResp = await request.post(`${API}/gobierno/estructuras/${anio}/cargos`, {
      headers: mundo.headers,
      data: {
        codigo: "C-ADM",
        denominacion: "Director de Administración",
        unidad_id: despId,
        vigente_desde: `${anio}-01-01`,
      },
    });
    expect(cargoAdmResp.status()).toBe(201);
    const cargoAdm = await cargoAdmResp.json();

    const competenciaAdmResp = await request.post(
      `${API}/gobierno/estructuras/${anio}/cargos/${cargoAdm.id}/competencias`,
      {
        headers: { ...mundo.headers, "If-Match": '"1"' },
        data: {
          accion: "COMPROMETER",
          materia: "PRESUPUESTO",
          tipo_limite: "SIN_LIMITE",
          monto: null,
          moneda: null,
        },
      },
    );
    expect(competenciaAdmResp.status()).toBe(201);

    await adjuntarDocumentoApi(
      request,
      mundo.headers,
      mundo.companyId,
      tipo.id,
      "GovernmentPosition",
      cargoAdm.id,
    );

    const activarCargoAdmResp = await request.post(
      `${API}/gobierno/estructuras/${anio}/cargos/${cargoAdm.id}/activar`,
      {
        headers: { ...mundo.headers, "If-Match": '"2"' },
      },
    );
    expect(activarCargoAdmResp.status()).toBe(200);

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
    const creditosDatos = await creditoResp.json();
    version = creditosDatos.version;
    const creditoId = (creditosDatos as { creditos: Array<{ id: string }> }).creditos[0].id;

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

    const cdpResp = await request.post(
      `${API}/gobierno/presupuesto/ejercicios/${ejercicio.id}/certificaciones`,
      {
        headers: certificador.headers,
        data: {
          credito_id: creditoId,
          monto: "300.00",
          concepto: "Adquisición de material médico",
          expediente_referencia: "EXP-PRES-2026-001",
          firmante_cargo_id: cargoPres.id,
        },
      },
    );
    expect(cdpResp.status()).toBe(201);
    const cdp = await cdpResp.json();

    await entrarEnGobierno(page, mundo.username, mundo.codigo, "/gobierno/presupuesto/ejercicios");
    await cerrarNotificaciones(page);

    await page.getByRole("link", { name: `Ejercicio ${anio}`, exact: true }).click();
    await expect(page.getByRole("heading", { name: `Ejercicio presupuestario ${anio}`, exact: true })).toBeVisible();

    const disp = page.getByRole("region", { name: "Tabla de disponibilidad", exact: true });
    await expect(disp).toContainText("700,00");

    const seccion = page.locator("section").filter({ has: page.getByRole("heading", { name: "Compromisos", exact: true }) });

    await seccion.getByRole("combobox", { name: "Certificación de la imputación 1 (obligatorio)", exact: true }).selectOption({ index: 1 });
    await expect(seccion).toContainText("remanente 300,00");
    await seccion.getByRole("textbox", { name: "Monto de la imputación 1 (obligatorio)", exact: true }).fill("200,00");
    await seccion.getByRole("textbox", { name: "Concepto (obligatorio)", exact: true }).fill("Orden de compra de material médico");
    await seccion.getByRole("combobox", { name: "Autoridad que compromete (cargo) (obligatorio)", exact: true }).selectOption({ index: 1 });
    await seccion.getByRole("combobox", { name: "Soporte documental (obligatorio)", exact: true }).selectOption({ index: 1 });
    await expect(seccion).toContainText("Total del compromiso: 200,00");

    const compromiso1RespPromise = page.waitForResponse(
      (resp) =>
        resp.request().method() === "POST" &&
        new URL(resp.url()).pathname.endsWith("/compromisos"),
    );
    await seccion.getByRole("button", { name: "Registrar compromiso", exact: true }).click();
    const compromiso1Resp = await compromiso1RespPromise;
    expect(compromiso1Resp.status()).toBe(201);
    const k1 = await compromiso1Resp.json();

    await expect(seccion).toContainText(`Compromiso ${k1.codigo} registrado por 200,00`);
    await expect(disp).toContainText("700,00");
    await expect(disp).toContainText("200,00");
    await expect(page.getByRole("region", { name: "Tabla de certificaciones", exact: true })).toContainText("Parcialmente consumida");
    await expect(page.getByRole("region", { name: "Tabla de certificaciones", exact: true })).toContainText("Con compromisos vigentes");

    await seccion.getByRole("combobox", { name: "Certificación de la imputación 1 (obligatorio)", exact: true }).selectOption({ index: 1 });
    await seccion.getByRole("textbox", { name: "Monto de la imputación 1 (obligatorio)", exact: true }).fill("60,00");
    await seccion.getByRole("textbox", { name: "Concepto (obligatorio)", exact: true }).fill("Orden de compra de material médico");
    await seccion.getByRole("combobox", { name: "Autoridad que compromete (cargo) (obligatorio)", exact: true }).selectOption({ index: 1 });
    await seccion.getByRole("combobox", { name: "Soporte documental (obligatorio)", exact: true }).selectOption({ index: 1 });

    const compromiso2RespPromise = page.waitForResponse(
      (resp) =>
        resp.request().method() === "POST" &&
        new URL(resp.url()).pathname.endsWith("/compromisos"),
    );
    await seccion.getByRole("button", { name: "Registrar compromiso", exact: true }).click();
    const compromiso2Resp = await compromiso2RespPromise;
    expect(compromiso2Resp.status()).toBe(201);
    const k2 = await compromiso2Resp.json();

    await seccion.getByRole("combobox", { name: "Certificación de la imputación 1 (obligatorio)", exact: true }).selectOption({ index: 1 });
    await seccion.getByRole("textbox", { name: "Monto de la imputación 1 (obligatorio)", exact: true }).fill("50,00");
    await seccion.getByRole("textbox", { name: "Concepto (obligatorio)", exact: true }).fill("Orden de compra de material médico");
    await seccion.getByRole("combobox", { name: "Autoridad que compromete (cargo) (obligatorio)", exact: true }).selectOption({ index: 1 });
    await seccion.getByRole("combobox", { name: "Soporte documental (obligatorio)", exact: true }).selectOption({ index: 1 });

    const excesoRespPromise = page.waitForResponse(
      (resp) =>
        resp.request().method() === "POST" &&
        new URL(resp.url()).pathname.endsWith("/compromisos"),
    );
    await seccion.getByRole("button", { name: "Registrar compromiso", exact: true }).click();
    const excesoResp = await excesoRespPromise;
    expect(excesoResp.status()).toBe(422);
    expect((await excesoResp.json()).code).toBe("GOV_BUDGET_CERTIFICATE_INSUFFICIENT_REMAINING");
    await cerrarNotificaciones(page);
    await expect(disp).toContainText("700,00");

    const tablaCompromisos = page.getByRole("region", { name: "Tabla de compromisos", exact: true });
    await expect(tablaCompromisos).toContainText(k1.codigo);
    await expect(tablaCompromisos).toContainText(k2.codigo);
    await expect(tablaCompromisos).toContainText("C-ADM · Director de Administración");
    await expect(tablaCompromisos).toContainText("EXP-PRES-2026-001");

    const [descarga] = await Promise.all([
      page.waitForEvent("download"),
      seccion.getByRole("button", { name: `Descargar ${k1.codigo}`, exact: true }).click(),
    ]);
    expect(descarga.suggestedFilename()).toBe(`compromiso-${k1.codigo}.pdf`);

    const anularCdpResp = await request.post(
      `${API}/gobierno/presupuesto/ejercicios/${ejercicio.id}/certificaciones/${cdp.id}/anular`,
      {
        headers: certificador.headers,
        data: { motivo: "Error en el expediente de origen" },
      },
    );
    expect(anularCdpResp.status()).toBe(409);
    expect((await anularCdpResp.json()).code).toBe("GOV_BUDGET_CERTIFICATE_IN_USE");

    await seccion.getByRole("textbox", { name: `Motivo de anulación de ${k1.codigo}`, exact: true }).fill("Error en la orden de compra");

    const anularCompromisoRespPromise = page.waitForResponse(
      (resp) =>
        resp.request().method() === "POST" &&
        new URL(resp.url()).pathname.endsWith(`/compromisos/${k1.id}/anular`),
    );
    await seccion.getByRole("button", { name: `Anular ${k1.codigo}`, exact: true }).click();
    const anularCompromisoResp = await anularCompromisoRespPromise;
    expect(anularCompromisoResp.status()).toBe(200);

    await expect(tablaCompromisos).toContainText("Anulado");
    await expect(page.getByRole("region", { name: "Tabla de certificaciones", exact: true })).toContainText("240,00");
    await expect(disp).toContainText("700,00");

    const ejercicioHistoriaResp = await request.get(`${API}/gobierno/presupuesto/ejercicios/${ejercicio.id}`, {
      headers: mundo.headers,
    });
    expect(ejercicioHistoriaResp.status()).toBe(200);
    const ejercicioHistoria = await ejercicioHistoriaResp.json();
    const tiposHistoria = (ejercicioHistoria.historia ?? []).map((h: { tipo: string }) => h.tipo);
    expect(tiposHistoria).toContain("COMPROMISO_REGISTRADO");
    expect(tiposHistoria).toContain("COMPROMISO_ANULADO");

    const otro = await prepararMundo(request, ["organization:view", "gobierno_presupuesto:view"]);
    const aislamientoResp = await request.get(
      `${API}/gobierno/presupuesto/ejercicios/${ejercicio.id}/compromisos`,
      {
        headers: otro.headers,
      },
    );
    expect(aislamientoResp.status()).toBe(404);

    for (const ancho of [1280, 390, 320]) {
      await page.setViewportSize({ width: ancho, height: 800 });
      await expect(page.getByRole("heading", { name: `Ejercicio presupuestario ${anio}`, exact: true })).toBeVisible();
      await sinViolacionesSerias(page, `compromiso ${ancho}`);
    }
  });
});
