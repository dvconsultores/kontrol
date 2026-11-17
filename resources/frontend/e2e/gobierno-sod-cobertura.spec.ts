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

test.describe("Cobertura de segregación de funciones", () => {
  test("T004: bloqueo SoD de BUD-08 se refleja en alertas y reporte de control interno", async ({ page, request }) => {
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
      "gobierno_presupuesto:certify",
      "gobierno_alertas:view",
      "gobierno_auditoria:view",
    ];

    const mundo = await prepararMundo(request, PERMISOS);
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
        headers: mundo.headers,
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

    const compromisoRespPromise = page.waitForResponse(
      (resp) =>
        resp.request().method() === "POST" &&
        new URL(resp.url()).pathname.endsWith("/compromisos"),
    );
    await seccion.getByRole("button", { name: "Registrar compromiso", exact: true }).click();
    const compromisoResp = await compromisoRespPromise;
    expect(compromisoResp.status()).toBe(409);
    const errorBody = (await compromisoResp.json()) as unknown;
    expect(JSON.stringify(errorBody)).toContain("GOV_SOD_CONFLICT");

    await expect(disp).toContainText("700,00");
    await expect(page.getByText(/quien certifica no compromete/i).first()).toBeVisible();

    await cerrarNotificaciones(page);
    await page.getByRole("link", { name: "Alertas de operaciones atípicas" }).click();
    await expect(page.getByRole("heading", { level: 1, name: "Alertas de operaciones atípicas" })).toBeVisible();

    const listaAlertas = page.getByRole("list", { name: "Alertas" });
    const liSod = listaAlertas.getByRole("listitem").filter({
      has: page.getByRole("heading", {
        level: 3,
        name: "Intento bloqueado por segregación de funciones",
      }),
    });
    await expect(liSod).toContainText("Segregación de funciones");
    await expect(liSod).toContainText("intentó registrar un compromiso");
    await expect(liSod).toContainText(cdp.codigo);
    await expect(liSod).toContainText("Quien certifica no compromete");
    await expect(page.getByRole("note")).toContainText(
      "Una alerta es una señal para revisar; no es una acusación ni una conclusión.",
    );

    await page.getByRole("link", { name: "Reporte de control interno" }).click();
    await expect(page.getByRole("heading", { level: 1, name: "Reporte de control interno" })).toBeVisible();

    const resumen = page.getByRole("region", { name: "Resumen" });
    await expect(resumen).toContainText("Conflictos de segregación");
    await expect(resumen).toContainText("1");

    const porRegla = page.getByRole("table", { name: "Conflictos por regla" });
    const filaRegla = porRegla.getByRole("row").filter({ hasText: "Quien certifica no compromete" });
    await expect(filaRegla).toContainText("Compromiso presupuestario");
    await expect(filaRegla).toContainText("Segregación de funciones");
    await expect(filaRegla).toContainText("1");
    await expect(porRegla).not.toContainText("null");
    await expect(porRegla.getByRole("columnheader", { name: "Tipo de conflicto" })).toBeVisible();

    const recientes = page.getByRole("table", { name: "Conflictos recientes" });
    await expect(recientes).toContainText("Registrar un compromiso");
    await expect(recientes).toContainText(cdp.codigo);

    for (const ancho of [1280, 390, 320]) {
      await page.setViewportSize({ width: ancho, height: 800 });
      await page.goto("/gobierno/control-interno");
      await expect(page.getByRole("heading", { level: 1, name: "Reporte de control interno" })).toBeVisible();
      await expect(page.getByRole("heading", { level: 2, name: "Conflictos de segregación de funciones" })).toBeVisible();
      const sinDesbordamiento = await page.evaluate(
        () => document.documentElement.scrollWidth <= document.documentElement.clientWidth,
      );
      expect(sinDesbordamiento).toBe(true);
      await sinViolacionesSerias(page, `reporte ${ancho}`);
    }

    for (const ancho of [1280, 390, 320]) {
      await page.setViewportSize({ width: ancho, height: 800 });
      await page.goto("/gobierno/control/alertas");
      await expect(page.getByRole("heading", { level: 1, name: "Alertas de operaciones atípicas" })).toBeVisible();
      const sinDesbordamiento = await page.evaluate(
        () => document.documentElement.scrollWidth <= document.documentElement.clientWidth,
      );
      expect(sinDesbordamiento).toBe(true);
      await sinViolacionesSerias(page, `alertas ${ancho}`);
    }
  });
});
