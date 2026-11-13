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
} from "./helpers/gobierno";
import type { Page } from "@playwright/test";

const RESPONSABLE_PRESUPUESTO = [
  "organization:view",
  "documentos:view",
  "documentos:create",
  "documentos:upload",
  "documentos:link",
  "documentos:download",
  "documentos:manage_types",
  "gobierno_presupuesto:view",
  "gobierno_presupuesto:manage",
  "gobierno_presupuesto:approve",
  "gobierno_presupuesto:close",
];

const WCAG = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"];

function hoyCaracas(): string {
  return new Intl.DateTimeFormat("en-CA", { timeZone: "America/Caracas" }).format(
    new Date(),
  );
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

test.describe("Ejercicio presupuestario", () => {
  test("BUD-01/02: ejercicio, estructura, clasificador, fijación, congelado, historia, aislamiento y responsive", async ({ page, request }) => {
    test.setTimeout(300_000);
    const mundo = await prepararMundo(request, RESPONSABLE_PRESUPUESTO);
    const tipo = await crearTipoDocumental(request, mundo.headers, mundo.companyId);
    const anio = ANIO + 1;

    await entrarEnGobierno(page, mundo.username, mundo.codigo, "/gobierno/presupuesto/ejercicios");
    await cerrarNotificaciones(page);

    await expect(page.getByRole("heading", { level: 1, name: "Ejercicios presupuestarios" })).toBeVisible();

    await page.getByLabel("Año").fill(String(anio));
    const [crearResp] = await Promise.all([
      page.waitForResponse(
        (r) =>
          r.request().method() === "POST" &&
          new URL(r.url()).pathname.endsWith("/api/v1/gobierno/presupuesto/ejercicios"),
        { timeout: 60_000 },
      ),
      page.getByRole("button", { name: "Crear ejercicio" }).click(),
    ]);
    expect(crearResp.status(), await crearResp.text()).toBe(201);

    await page.waitForURL((u) => /\/gobierno\/presupuesto\/ejercicios\/[^/]+$/.test(u.pathname));
    const id = page.url().split("/").pop() ?? "";
    await expect(page.getByRole("heading", { level: 1, name: `Ejercicio presupuestario ${anio}` })).toBeVisible();

    await page.getByLabel("Nivel 1").fill("Sector");
    await page.getByRole("button", { name: "Añadir nivel" }).click();
    await page.getByLabel("Nivel 2").fill("Programa");
    const [nivelesResp] = await Promise.all([
      page.waitForResponse(
        (r) =>
          r.request().method() === "PUT" &&
          new URL(r.url()).pathname.endsWith(`/gobierno/presupuesto/ejercicios/${id}/niveles`),
        { timeout: 60_000 },
      ),
      page.getByRole("button", { name: "Guardar niveles" }).click(),
    ]);
    expect(nivelesResp.status(), await nivelesResp.text()).toBe(200);

    const seccionEstructura = page.locator("section").filter({
      has: page.getByRole("heading", { name: "Estructura programática" }),
    });

    await seccionEstructura.getByRole("combobox", { name: "Nivel" }).selectOption("1");
    await seccionEstructura.getByLabel("Código", { exact: true }).fill("01");
    await seccionEstructura.getByLabel("Denominación", { exact: true }).fill("Sector salud");
    const [cat1Resp] = await Promise.all([
      page.waitForResponse(
        (r) =>
          r.request().method() === "POST" &&
          new URL(r.url()).pathname.endsWith(`/gobierno/presupuesto/ejercicios/${id}/categorias`),
        { timeout: 60_000 },
      ),
      seccionEstructura.getByRole("button", { name: "Agregar categoría" }).click(),
    ]);
    expect(cat1Resp.status(), await cat1Resp.text()).toBe(201);

    await seccionEstructura.getByRole("combobox", { name: "Nivel" }).selectOption("2");
    await seccionEstructura.getByRole("combobox", { name: "Categoría superior" }).selectOption({ index: 1 });
    await seccionEstructura.getByLabel("Código", { exact: true }).fill("02");
    await seccionEstructura.getByLabel("Denominación", { exact: true }).fill("Atención primaria");
    const [cat2Resp] = await Promise.all([
      page.waitForResponse(
        (r) =>
          r.request().method() === "POST" &&
          new URL(r.url()).pathname.endsWith(`/gobierno/presupuesto/ejercicios/${id}/categorias`),
        { timeout: 60_000 },
      ),
      seccionEstructura.getByRole("button", { name: "Agregar categoría" }).click(),
    ]);
    expect(cat2Resp.status(), await cat2Resp.text()).toBe(201);

    await expect(page.getByRole("region", { name: "Categorías programáticas" })).toContainText("01.02");

    await seccionEstructura.getByRole("combobox", { name: "Nivel" }).selectOption("1");
    await seccionEstructura.getByLabel("Código", { exact: true }).fill("a b");
    await seccionEstructura.getByLabel("Denominación", { exact: true }).fill("Inválida");
    const [invalidCatResp] = await Promise.all([
      page.waitForResponse(
        (r) =>
          r.request().method() === "POST" &&
          new URL(r.url()).pathname.endsWith(`/gobierno/presupuesto/ejercicios/${id}/categorias`),
        { timeout: 60_000 },
      ),
      seccionEstructura.getByRole("button", { name: "Agregar categoría" }).click(),
    ]);
    expect(invalidCatResp.status(), await invalidCatResp.text()).toBe(422);
    await expect(page.getByRole("alert").first()).toBeVisible();

    await adjuntarDocumentoApi(request, mundo.headers, mundo.companyId, tipo.id, "GovernmentBudgetYear", id);
    await adjuntarDocumentoApi(request, mundo.headers, mundo.companyId, tipo.id, "GovernmentBudgetYear", id);
    await page.reload();
    await expect(page.getByRole("heading", { level: 1, name: `Ejercicio presupuestario ${anio}` })).toBeVisible();

    const seccionClasificador = page.locator("section").filter({
      has: page.getByRole("heading", { name: "Clasificador registrado por el ente" }),
    });
    await seccionClasificador.getByLabel("Edición", { exact: true }).fill(`Clasificador del ente ${anio}`);
    await seccionClasificador.getByLabel("Procedencia", { exact: true }).fill("Copia entregada por la Dirección de Presupuesto del ente");
    await seccionClasificador.getByLabel("Documento de procedencia").selectOption({ index: 1 });
    const [clasificadorResp] = await Promise.all([
      page.waitForResponse(
        (r) =>
          r.request().method() === "PUT" &&
          new URL(r.url()).pathname.endsWith(`/gobierno/presupuesto/ejercicios/${id}/clasificador`),
        { timeout: 60_000 },
      ),
      seccionClasificador.getByRole("button", { name: "Guardar clasificador" }).click(),
    ]);
    expect(clasificadorResp.status(), await clasificadorResp.text()).toBe(200);

    const csv = [
      "tipo,codigo,denominacion,nivel,codigo_padre,vigente_desde,vigente_hasta",
      "RECURSO,301,Ingresos propios,1,,,",
      "EGRESO,401,Gasto corriente,1,,,",
      "EGRESO,401.01,Servicios personales,2,401,,",
    ].join("\n");
    await seccionClasificador.getByLabel("Archivo CSV de partidas").setInputFiles({
      name: "partidas.csv",
      mimeType: "text/csv",
      buffer: Buffer.from(csv),
    });
    const [importarResp] = await Promise.all([
      page.waitForResponse(
        (r) =>
          r.request().method() === "POST" &&
          new URL(r.url()).pathname.endsWith(`/gobierno/presupuesto/ejercicios/${id}/clasificador/importar`),
        { timeout: 60_000 },
      ),
      seccionClasificador.getByRole("button", { name: "Importar partidas" }).click(),
    ]);
    expect(importarResp.status(), await importarResp.text()).toBe(200);
    await expect(page.getByRole("region", { name: "Partidas del clasificador" })).toContainText("401.01");

    const seccionFijacion = page.locator("section").filter({
      has: page.getByRole("heading", { name: "Fijación, precompromiso y cierre" }),
    });
    await expect(seccionFijacion.getByRole("radio", { name: "Ordenanza de presupuesto sancionada" })).toBeChecked();
    await seccionFijacion.getByLabel("Referencia").fill("Gaceta Municipal Extraordinaria N.º 1");
    await seccionFijacion.getByLabel("Fecha de sanción").fill(hoyCaracas());
    await seccionFijacion.getByLabel("Documento", { exact: true }).selectOption({ index: 2 });
    const [aprobarResp] = await Promise.all([
      page.waitForResponse(
        (r) =>
          r.request().method() === "POST" &&
          new URL(r.url()).pathname.endsWith(`/gobierno/presupuesto/ejercicios/${id}/aprobar`),
        { timeout: 60_000 },
      ),
      seccionFijacion.getByRole("button", { name: "Aprobar ejercicio" }).click(),
    ]);
    expect(aprobarResp.status(), await aprobarResp.text()).toBe(200);

    await expect(page.getByText(/El ejercicio está fijado/)).toBeVisible();
    await expect(page.getByRole("button", { name: "Agregar categoría" })).toHaveCount(0);

    const detalleResp = await request.get(`${API}/gobierno/presupuesto/ejercicios/${id}`, {
      headers: mundo.headers,
    });
    expect(detalleResp.status(), await detalleResp.text()).toBe(200);
    const detalle = await detalleResp.json();

    const congeladoResp = await request.post(`${API}/gobierno/presupuesto/ejercicios/${id}/categorias`, {
      headers: { ...mundo.headers, "If-Match": String(detalle.version) },
      data: {
        nivel_orden: 1,
        parent_id: null,
        codigo: "09",
        denominacion: "No",
      },
    });
    expect(congeladoResp.status(), await congeladoResp.text()).toBe(409);

    await expect(page.getByRole("region", { name: "Tabla de historia del ejercicio" })).toContainText("Aprobado por ordenanza");

    const otroMundo = await prepararMundo(request, ["organization:view", "gobierno_presupuesto:view"]);
    const otroDetalleResp = await request.get(`${API}/gobierno/presupuesto/ejercicios/${id}`, {
      headers: otroMundo.headers,
    });
    expect(otroDetalleResp.status(), await otroDetalleResp.text()).toBe(404);

    for (const ancho of [1280, 390, 320]) {
      await page.setViewportSize({ width: ancho, height: 800 });
      await expect(page.getByRole("heading", { level: 1, name: `Ejercicio presupuestario ${anio}` })).toBeVisible();
      await sinViolacionesSerias(page, `ejercicio ${ancho}`);
    }

    await page.setViewportSize({ width: 1280, height: 800 });
    await page.locator(`nav a[href="/gobierno/presupuesto/ejercicios"]`).first().click();
    await page.waitForURL((u) => u.pathname === "/gobierno/presupuesto/ejercicios");
    await expect(page.getByRole("heading", { level: 1, name: "Ejercicios presupuestarios" })).toBeVisible();
    await sinViolacionesSerias(page, "lista ejercicios 1280");
  });
});
