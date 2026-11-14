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

test.describe("Presupuesto aprobado del ejercicio", () => {
  test("BUD-05: ingresos, créditos, existencias, aprobación, congelado, historia, aislamiento y responsive", async ({ page, request }) => {
    test.setTimeout(300_000);

    const PERMISOS = [
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
    ];

    const mundo = await prepararMundo(request, PERMISOS);
    const tipo = await crearTipoDocumental(request, mundo.headers, mundo.companyId);
    const anio = ANIO + 1;

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

    const documentosResp = await request.get(`${API}/documentos/por-recurso/GovernmentBudgetYear/${ejercicio.id}`, { headers: mundo.headers });
    expect(documentosResp.status()).toBe(200);
    const documentos = (await documentosResp.json()) as Array<{ id: string }>;
    expect(documentos.length).toBeGreaterThanOrEqual(2);

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

    const partida402Resp = await request.post(`${API}/gobierno/presupuesto/ejercicios/${ejercicio.id}/clasificador/partidas`, {
      headers: { ...mundo.headers, "If-Match": String(version) },
      data: {
        tipo: "EGRESO",
        codigo: "402",
        denominacion: "Materiales",
        nivel: 1,
        codigo_padre: null,
        vigente_desde: null,
        vigente_hasta: null,
      },
    });
    expect(partida402Resp.status()).toBe(201);
    version = (await partida402Resp.json()).version;

    const fuentesResp = await request.post(`${API}/gobierno/presupuesto/ejercicios/${ejercicio.id}/fuentes`, {
      headers: { ...mundo.headers, "If-Match": String(version) },
      data: {
        codigo: "F01",
        denominacion: "Ingresos propios",
        procedencia: "Ordenanza municipal de ingresos del ente",
      },
    });
    expect(fuentesResp.status()).toBe(201);
    let fuentesDatos = await fuentesResp.json();
    version = fuentesDatos.version;
    const fuenteF01 = fuentesDatos.items.find((f: { codigo: string }) => f.codigo === "F01");

    const fuenteF02Resp = await request.post(`${API}/gobierno/presupuesto/ejercicios/${ejercicio.id}/fuentes`, {
      headers: { ...mundo.headers, "If-Match": String(version) },
      data: {
        codigo: "F02",
        denominacion: "Aportes nacionales",
        procedencia: "Ordenanza municipal de ingresos del ente",
      },
    });
    expect(fuenteF02Resp.status()).toBe(201);
    fuentesDatos = await fuenteF02Resp.json();
    version = fuentesDatos.version;

    const restriccionResp = await request.post(
      `${API}/gobierno/presupuesto/ejercicios/${ejercicio.id}/fuentes/${fuenteF01.id}/restricciones`,
      {
        headers: { ...mundo.headers, "If-Match": String(version) },
        data: {
          descripcion: "Solo gasto corriente",
          fundamento: "Afectación legal (LOPPM art. 246)",
          partidas: ["401"],
        },
      },
    );
    expect(restriccionResp.status()).toBe(201);
    version = (await restriccionResp.json()).version;

    await entrarEnGobierno(page, mundo.username, mundo.codigo, "/gobierno/presupuesto/ejercicios");
    await cerrarNotificaciones(page);

    await page.getByRole("link", { name: `Ejercicio ${anio}`, exact: true }).click();
    await expect(page.getByRole("heading", { name: `Ejercicio presupuestario ${anio}`, exact: true })).toBeVisible();

    const seccion = page.locator("section").filter({
      has: page.getByRole("heading", { name: "Presupuesto aprobado", exact: true }),
    });

    // 3. Registrar ingreso
    await seccion
      .getByRole("combobox", { name: "Partida de recursos (obligatorio)", exact: true })
      .selectOption({ label: "301 · Ingresos propios" });
    await seccion.getByRole("textbox", { name: "Monto del ingreso (obligatorio)", exact: true }).fill("1.000.000,00");

    const [ingresoResp] = await Promise.all([
      page.waitForResponse(
        (resp) =>
          resp.request().method() === "POST" &&
          new URL(resp.url()).pathname.endsWith(`/gobierno/presupuesto/ejercicios/${ejercicio.id}/presupuesto-aprobado/ingresos`),
      ),
      seccion.getByRole("button", { name: "Registrar ingreso", exact: true }).click(),
    ]);
    expect(ingresoResp.status()).toBe(201);

    // 4. Registrar crédito compatible con restricción
    await seccion
      .getByRole("combobox", { name: "Categoría programática (obligatorio)", exact: true })
      .selectOption({ label: "01.02 · Atención primaria" });
    await seccion
      .getByRole("combobox", { name: "Fuente de financiamiento (obligatorio)", exact: true })
      .selectOption({ label: "F01 · Ingresos propios" });

    await expect(seccion).toContainText("La fuente F01 solo financia las partidas 401");

    const comboEgresos = seccion.getByRole("combobox", {
      name: "Partida de egresos (obligatorio)",
      exact: true,
    });
    await expect(comboEgresos.locator("option", { hasText: "402 · Materiales" })).toHaveCount(0);
    await comboEgresos.selectOption({ label: "401.01 · Servicios personales" });
    await seccion.getByRole("textbox", { name: "Monto del crédito (obligatorio)", exact: true }).fill("1.200.000,00");

    const [creditoResp] = await Promise.all([
      page.waitForResponse(
        (resp) =>
          resp.request().method() === "POST" &&
          new URL(resp.url()).pathname.endsWith(`/gobierno/presupuesto/ejercicios/${ejercicio.id}/presupuesto-aprobado/creditos`),
      ),
      seccion.getByRole("button", { name: "Registrar crédito", exact: true }).click(),
    ]);
    expect(creditoResp.status()).toBe(201);
    const creditoDatos = await creditoResp.json();
    const creditoId = creditoDatos.creditos[0].id;

    await expect(seccion).toContainText("No cuadra");

    // 5. Fuente incompatible en backend
    const ejercicioActualResp = await request.get(`${API}/gobierno/presupuesto/ejercicios/${ejercicio.id}`, {
      headers: mundo.headers,
    });
    expect(ejercicioActualResp.status()).toBe(200);
    const ejercicioActual = await ejercicioActualResp.json();
    const versionActual = ejercicioActual.version;

    const partidasResp = await request.get(
      `${API}/gobierno/presupuesto/ejercicios/${ejercicio.id}/clasificador/partidas`,
      { headers: mundo.headers },
    );
    expect(partidasResp.status()).toBe(200);
    const partidas = (await partidasResp.json()).items as Array<{ id: string; codigo: string }>;
    const partida402 = partidas.find((p) => p.codigo === "402");
    const partida301 = partidas.find((p) => p.codigo === "301");
    expect(partida402).toBeDefined();
    expect(partida301).toBeDefined();

    const creditoInvalidoResp = await request.post(
      `${API}/gobierno/presupuesto/ejercicios/${ejercicio.id}/presupuesto-aprobado/creditos`,
      {
        headers: { ...mundo.headers, "If-Match": String(versionActual) },
        data: {
          categoria_id: cat02.id,
          fuente_id: fuenteF01.id,
          partida_id: partida402!.id,
          monto: "800000.00",
        },
      },
    );
    expect(creditoInvalidoResp.status()).toBe(422);
    expect(await creditoInvalidoResp.json()).toMatchObject({ code: "GOV_BUDGET_CREDIT_SOURCE_RESTRICTED" });

    // 6. Editar crédito
    await seccion
      .getByRole("textbox", { name: "Nuevo monto del crédito 01.02 · 401.01 · F01", exact: true })
      .fill("900.000,00");

    const [editarCreditoResp] = await Promise.all([
      page.waitForResponse(
        (resp) =>
          resp.request().method() === "PATCH" &&
          new URL(resp.url()).pathname.endsWith(`/gobierno/presupuesto/ejercicios/${ejercicio.id}/presupuesto-aprobado/creditos/${creditoId}`),
      ),
      seccion.getByRole("button", { name: "Guardar crédito 01.02 · 401.01 · F01", exact: true }).click(),
    ]);
    expect(editarCreditoResp.status()).toBe(200);
    await expect(seccion).toContainText("El presupuesto cuadra");

    // 7. Declarar existencias
    await seccion.getByRole("textbox", { name: "Monto de las existencias (obligatorio)", exact: true }).fill("100.000,00");
    await seccion.getByLabel("Fecha de corte").fill(hoyCaracas());
    await seccion
      .getByRole("combobox", { name: "Certificación del Tesorero (obligatorio)", exact: true })
      .selectOption({ index: 1 });

    const [existenciasResp] = await Promise.all([
      page.waitForResponse(
        (resp) =>
          resp.request().method() === "PUT" &&
          new URL(resp.url()).pathname.endsWith(`/gobierno/presupuesto/ejercicios/${ejercicio.id}/presupuesto-aprobado/existencias-tesoro`),
      ),
      seccion.getByRole("button", { name: "Declarar existencias", exact: true }).click(),
    ]);
    expect(existenciasResp.status()).toBe(200);

    // 8. Persistencia tras recarga
    await page.reload();
    await expect(page.getByRole("heading", { name: `Ejercicio presupuestario ${anio}`, exact: true })).toBeVisible();
    await expect(
      page.getByRole("region", { name: "Tabla de créditos presupuestarios", exact: true }),
    ).toContainText("900.000,00");
    await expect(
      page.getByRole("region", { name: "Tabla de ingresos estimados", exact: true }),
    ).toContainText("1.000.000,00");

    // 9. Aislamiento entre empresas
    const otro = await prepararMundo(request, [
      "organization:view",
      "gobierno_presupuesto:view",
      "gobierno_presupuesto:manage",
    ]);

    const getActualResp = await request.get(`${API}/gobierno/presupuesto/ejercicios/${ejercicio.id}`, {
      headers: mundo.headers,
    });
    expect(getActualResp.status()).toBe(200);
    const getActual = await getActualResp.json();

    const aisladoGetResp = await request.get(
      `${API}/gobierno/presupuesto/ejercicios/${ejercicio.id}/presupuesto-aprobado`,
      { headers: otro.headers },
    );
    expect(aisladoGetResp.status()).toBe(404);

    const aisladoPostResp = await request.post(
      `${API}/gobierno/presupuesto/ejercicios/${ejercicio.id}/presupuesto-aprobado/ingresos`,
      {
        headers: { ...otro.headers, "If-Match": String(getActual.version) },
        data: {
          partida_id: partida301!.id,
          monto: "1.00",
        },
      },
    );
    expect(aisladoPostResp.status()).toBe(404);

    // 10. Aprobación por pantalla
    const seccionFijacion = page.locator("section").filter({
      has: page.getByRole("heading", { name: "Fijación, precompromiso y cierre", exact: true }),
    });
    await expect(
      seccionFijacion.getByRole("radio", { name: "Ordenanza de presupuesto sancionada", exact: true }),
    ).toBeChecked();
    await seccionFijacion.getByLabel("Referencia").fill("Gaceta Municipal Extraordinaria N.º 7");
    await seccionFijacion.getByLabel("Fecha de sanción").fill(hoyCaracas());
    await seccionFijacion.getByLabel("Documento", { exact: true }).selectOption({ index: 2 });

    const [aprobarResp] = await Promise.all([
      page.waitForResponse(
        (r) =>
          r.request().method() === "POST" &&
          new URL(r.url()).pathname.endsWith(`/gobierno/presupuesto/ejercicios/${ejercicio.id}/aprobar`),
        { timeout: 60_000 },
      ),
      seccionFijacion.getByRole("button", { name: "Aprobar ejercicio", exact: true }).click(),
    ]);
    expect(aprobarResp.status(), await aprobarResp.text()).toBe(200);

    // 11. Congelado
    await expect(seccion.getByRole("button", { name: "Registrar crédito", exact: true })).toHaveCount(0);
    await expect(seccion).toContainText("El presupuesto aprobado está fijado y ya no se modifica.");

    const congeladoResp = await request.get(`${API}/gobierno/presupuesto/ejercicios/${ejercicio.id}`, {
      headers: mundo.headers,
    });
    expect(congeladoResp.status()).toBe(200);
    const congeladoDatos = await congeladoResp.json();

    const patchCongeladoResp = await request.patch(
      `${API}/gobierno/presupuesto/ejercicios/${ejercicio.id}/presupuesto-aprobado/creditos/${creditoId}`,
      {
        headers: { ...mundo.headers, "If-Match": String(congeladoDatos.version) },
        data: { monto: "800000.00" },
      },
    );
    expect(patchCongeladoResp.status()).toBe(409);
    expect(await patchCongeladoResp.json()).toMatchObject({ code: "GOV_BUDGET_YEAR_FROZEN" });

    // 12. Fundamento e historia por API
    const fundamento = congeladoDatos.fundamentos?.[0];
    expect(fundamento).toBeTruthy();
    expect(fundamento.huella).toMatch(/^[0-9a-f]{64}$/);

    const tiposHistoria = congeladoDatos.historia.map((h: { tipo: string }) => h.tipo);
    for (const tipoHistoria of [
      "INGRESO_REGISTRADO",
      "CREDITO_REGISTRADO",
      "CREDITO_MODIFICADO",
      "EXISTENCIAS_REGISTRADAS",
      "APROBADO",
    ]) {
      expect(tiposHistoria).toContain(tipoHistoria);
    }

    // 13. Responsive y accesibilidad
    for (const ancho of [1280, 390, 320]) {
      await page.setViewportSize({ width: ancho, height: 800 });
      await expect(page.getByRole("heading", { name: `Ejercicio presupuestario ${anio}`, exact: true })).toBeVisible();
      await sinViolacionesSerias(page, `presupuesto aprobado ${ancho}`);
    }
  });
});
