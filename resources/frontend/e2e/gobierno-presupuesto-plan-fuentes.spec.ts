import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "./helpers/sesion";
import {
  ANIO,
  API,
  RESPONSABLE_ESTRUCTURA,
  adjuntarDocumentoApi,
  cerrarNotificaciones,
  crearTipoDocumental,
  entrarEnGobierno,
  prepararMundo,
  enteActivo,
  estructuraVigenteApi,
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

test.describe("Plan y fuentes del ejercicio", () => {
  test("BUD-03/04: plan, objetivos, responsables, metas, fuentes, restricciones, historia, aislamiento y responsive", async ({ page, request }) => {
    test.setTimeout(300_000);

    const PERMISOS = [
      ...RESPONSABLE_ESTRUCTURA,
      "gobierno_presupuesto:view",
      "gobierno_presupuesto:manage",
      "gobierno_presupuesto:approve",
    ];

    const mundo = await prepararMundo(request, PERMISOS);
    const tipo = await crearTipoDocumental(request, mundo.headers, mundo.companyId);
    await enteActivo(request, mundo.headers, mundo.companyId, tipo.id);
    const anio = ANIO + 1;
    await estructuraVigenteApi(request, mundo.headers, mundo.companyId, tipo.id, anio);

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

    await adjuntarDocumentoApi(request, mundo.headers, mundo.companyId, tipo.id, "GovernmentBudgetYear", ejercicio.id);
    await adjuntarDocumentoApi(request, mundo.headers, mundo.companyId, tipo.id, "GovernmentBudgetYear", ejercicio.id);

    const clasificadorResp = await request.put(`${API}/gobierno/presupuesto/ejercicios/${ejercicio.id}/clasificador`, {
      headers: { ...mundo.headers, "If-Match": String(version) },
      data: {
        edicion: "Clasificador por sectores",
        procedencia: "Ordenanza de presupuesto",
        documento_id: null,
      },
    });
    expect(clasificadorResp.status()).toBe(200);
    version = (await clasificadorResp.json()).version;

    const partidaResp = await request.post(`${API}/gobierno/presupuesto/ejercicios/${ejercicio.id}/clasificador/partidas`, {
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
    expect(partidaResp.status()).toBe(201);
    version = (await partidaResp.json()).version;

    await entrarEnGobierno(page, mundo.username, mundo.codigo, "/gobierno/presupuesto/ejercicios");
    await cerrarNotificaciones(page);

    const enlaceEjercicio = page.getByRole("link", { name: `Ejercicio ${anio}` });
    await expect(enlaceEjercicio).toBeVisible();
    await enlaceEjercicio.click();

    await expect(page.getByRole("heading", { name: `Ejercicio presupuestario ${anio}` })).toBeVisible();

    const seccionPlan = page.locator("section").filter({ has: page.getByRole("heading", { name: "Plan operativo y metas" }) });
    await expect(seccionPlan).toBeVisible();

    const formPlan = seccionPlan.locator("form").filter({
      has: page.getByRole("button", { name: "Guardar plan" }),
    });

    const denominacionPlan = formPlan.getByRole("textbox", { name: "Denominación del plan (obligatorio)", exact: true });
    await denominacionPlan.fill("POA del ejercicio");
    await formPlan.getByRole("combobox", { name: "Documento del plan", exact: true }).selectOption({ index: 1 });

    const guardarPlanResp = page.waitForResponse(
      (resp) =>
        resp.request().method() === "PUT" &&
        new URL(resp.url()).pathname.endsWith(`/api/v1/gobierno/presupuesto/ejercicios/${ejercicio.id}/plan`),
    );
    await formPlan.getByRole("button", { name: "Guardar plan" }).click();
    expect((await guardarPlanResp).status()).toBe(200);

    const formObjetivo = seccionPlan.locator("form").filter({
      has: page.getByRole("button", { name: "Crear objetivo" }),
    });

    const objetivoCodigo = formObjetivo.getByRole("textbox", { name: "Código (obligatorio)", exact: true });
    const objetivoDescripcion = formObjetivo.getByRole("textbox", { name: "Descripción (obligatorio)", exact: true });
    await objetivoCodigo.fill("O1");
    await objetivoDescripcion.fill("Atención sanitaria universal");

    const crearObjetivoResp = page.waitForResponse(
      (resp) =>
        resp.request().method() === "POST" &&
        new URL(resp.url()).pathname.endsWith(`/api/v1/gobierno/presupuesto/ejercicios/${ejercicio.id}/plan/objetivos`),
    );
    await formObjetivo.getByRole("button", { name: "Crear objetivo" }).click();
    expect((await crearObjetivoResp).status()).toBe(201);

    const unidadSelect = seccionPlan.getByRole("combobox", { name: "Unidad responsable de 01", exact: true });
    const opcionDesp = (await unidadSelect.locator("option").allTextContents()).find((t) => t.startsWith("DESP · "));
    expect(opcionDesp).toBeDefined();
    await unidadSelect.selectOption({ label: opcionDesp! });

    const objetivoSelect = seccionPlan.getByRole("combobox", { name: "Objetivo de 01", exact: true });
    await objetivoSelect.selectOption({ index: 1 });

    const guardarVinculoResp = page.waitForResponse(
      (resp) =>
        resp.request().method() === "PUT" &&
        new URL(resp.url()).pathname.endsWith(`/api/v1/gobierno/presupuesto/ejercicios/${ejercicio.id}/categorias/${cat01.id}/vinculo`),
    );
    await seccionPlan.getByRole("button", { name: "Guardar vínculo de 01", exact: true }).click();
    expect((await guardarVinculoResp).status()).toBe(200);

    const formMeta = seccionPlan.locator("form").filter({
      has: page.getByRole("button", { name: "Crear meta" }),
    });

    const categoriaMeta = formMeta.getByRole("combobox", { name: "Categoría (obligatorio)", exact: true });
    await categoriaMeta.selectOption({ label: "01.02 · Atención primaria" });
    await formMeta.getByRole("textbox", { name: "Descripción (obligatorio)", exact: true }).fill("Consultas atendidas");
    await formMeta.getByRole("textbox", { name: "Unidad de medida (obligatorio)", exact: true }).fill("consulta");
    await formMeta.getByRole("textbox", { name: "Cantidad (obligatorio)", exact: true }).fill("1200.5");
    await formMeta.getByRole("textbox", { name: "Indicador (obligatorio)", exact: true }).fill("Consultas por mes");

    const crearMetaResp = page.waitForResponse(
      (resp) =>
        resp.request().method() === "POST" &&
        new URL(resp.url()).pathname.endsWith(`/api/v1/gobierno/presupuesto/ejercicios/${ejercicio.id}/plan/metas`),
    );
    await formMeta.getByRole("button", { name: "Crear meta" }).click();
    expect((await crearMetaResp).status()).toBe(201);

    await categoriaMeta.selectOption({ label: "01.02 · Atención primaria" });
    await formMeta.getByRole("textbox", { name: "Descripción (obligatorio)", exact: true }).fill("Meta sin cantidad");
    await formMeta.getByRole("textbox", { name: "Unidad de medida (obligatorio)", exact: true }).fill("consulta");
    await formMeta.getByRole("textbox", { name: "Cantidad (obligatorio)", exact: true }).fill("0");
    await formMeta.getByRole("textbox", { name: "Indicador (obligatorio)", exact: true }).fill("Consultas por mes");

    const metaInvalidaResp = page.waitForResponse(
      (resp) =>
        resp.request().method() === "POST" &&
        new URL(resp.url()).pathname.endsWith(`/api/v1/gobierno/presupuesto/ejercicios/${ejercicio.id}/plan/metas`),
    );
    await formMeta.getByRole("button", { name: "Crear meta" }).click();
    expect((await metaInvalidaResp).status()).toBe(422);
    await cerrarNotificaciones(page);

    const seccionFuentes = page.locator("section").filter({ has: page.getByRole("heading", { name: "Fuentes de financiamiento" }) });
    await expect(seccionFuentes).toBeVisible();

    const formFuente = seccionFuentes.locator("form").filter({
      has: page.getByRole("button", { name: "Crear fuente" }),
    });

    await formFuente.getByRole("textbox", { name: "Código (obligatorio)", exact: true }).fill("F01");
    await formFuente.getByRole("textbox", { name: "Denominación (obligatorio)", exact: true }).fill("Ingresos propios");
    await formFuente.getByRole("textbox", { name: "Procedencia (obligatorio)", exact: true }).fill("Ordenanza de ingresos del ente, copia de la Dirección de Hacienda");

    const crearFuenteResp = page.waitForResponse(
      (resp) =>
        resp.request().method() === "POST" &&
        new URL(resp.url()).pathname.endsWith(`/api/v1/gobierno/presupuesto/ejercicios/${ejercicio.id}/fuentes`),
    );
    await seccionFuentes.getByRole("button", { name: "Crear fuente" }).click();
    expect((await crearFuenteResp).status()).toBe(201);
    const crearFuenteDatos = await (await crearFuenteResp).json();
    const fuenteF01 = crearFuenteDatos.items.find((f: { codigo: string }) => f.codigo === "F01");

    await formFuente.getByRole("textbox", { name: "Código (obligatorio)", exact: true }).fill("F01");
    await formFuente.getByRole("textbox", { name: "Denominación (obligatorio)", exact: true }).fill("Ingresos propios");
    await formFuente.getByRole("textbox", { name: "Procedencia (obligatorio)", exact: true }).fill("Ordenanza de ingresos del ente, copia de la Dirección de Hacienda");

    const crearFuenteDuplicadaResp = page.waitForResponse(
      (resp) =>
        resp.request().method() === "POST" &&
        new URL(resp.url()).pathname.endsWith(`/api/v1/gobierno/presupuesto/ejercicios/${ejercicio.id}/fuentes`),
    );
    await seccionFuentes.getByRole("button", { name: "Crear fuente" }).click();
    expect((await crearFuenteDuplicadaResp).status()).toBe(422);
    await cerrarNotificaciones(page);

    await seccionFuentes.getByRole("textbox", { name: "Descripción de la restricción de F01 (obligatorio)", exact: true }).fill("Solo gasto corriente");
    await seccionFuentes.getByRole("textbox", { name: "Fundamento de la restricción de F01 (obligatorio)", exact: true }).fill("Afectación legal (LOPPM art. 246)");
    await seccionFuentes.getByRole("textbox", { name: "Partidas de egreso de F01", exact: true }).fill("401");

    const crearRestriccionResp = page.waitForResponse(
      (resp) =>
        resp.request().method() === "POST" &&
        new URL(resp.url()).pathname.endsWith(`/api/v1/gobierno/presupuesto/ejercicios/${ejercicio.id}/fuentes/${fuenteF01.id}/restricciones`),
    );
    await seccionFuentes.getByRole("button", { name: "Añadir restricción a F01" }).click();
    expect((await crearRestriccionResp).status()).toBe(201);

    await page.reload();
    await expect(page.getByRole("region", { name: "Objetivos del plan" })).toContainText("O1");
    await expect(page.getByRole("region", { name: "Metas físicas" })).toContainText("Consultas atendidas");
    await expect(seccionFuentes.getByRole("cell", { name: "F01", exact: true })).toBeVisible();
    await expect(seccionFuentes).toContainText("Solo gasto corriente");

    const ejercicioActualResp = await request.get(`${API}/gobierno/presupuesto/ejercicios/${ejercicio.id}`, {
      headers: mundo.headers,
    });
    expect(ejercicioActualResp.status()).toBe(200);
    const ejercicioActual = await ejercicioActualResp.json();
    const eventosHistoria = (ejercicioActual.historia ?? []).map((h: { tipo: string }) => h.tipo);
    expect(eventosHistoria).toContain("PLAN_REGISTRADO");
    expect(eventosHistoria).toContain("CATEGORIA_VINCULADA");
    expect(eventosHistoria).toContain("META_CREADA");
    expect(eventosHistoria).toContain("FUENTE_CREADA");
    expect(eventosHistoria).toContain("RESTRICCION_AGREGADA");

    const otro = await prepararMundo(request, ["organization:view", "gobierno_presupuesto:view"]);
    const planAisladoResp = await request.get(`${API}/gobierno/presupuesto/ejercicios/${ejercicio.id}/plan`, {
      headers: otro.headers,
    });
    expect(planAisladoResp.status()).toBe(404);
    const fuentesAisladoResp = await request.get(`${API}/gobierno/presupuesto/ejercicios/${ejercicio.id}/fuentes`, {
      headers: otro.headers,
    });
    expect(fuentesAisladoResp.status()).toBe(404);

    for (const ancho of [1280, 390, 320]) {
      await page.setViewportSize({ width: ancho, height: 800 });
      await expect(page.getByRole("heading", { name: `Ejercicio presupuestario ${anio}` })).toBeVisible();
      await sinViolacionesSerias(page, `plan y fuentes ${ancho}`);
    }
  });
});
