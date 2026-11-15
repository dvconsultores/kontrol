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

test.describe("Tasas oficiales de tesorería", () => {
  test("TRE-09: registro, maker-checker, corrección, uso en compromiso, bloqueo sin tasa, historia, aislamiento y responsive", async ({ page, request }) => {
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
      "gobierno_tasas:view",
      "gobierno_tasas:manage",
    ];

    const mundo = await prepararMundo(request, PERMISOS);
    const admin = await sesionApi("admintenant", { tenant: TENANT });
    const certificador = await crearUsuario(
      request,
      admin.headers,
      ["organization:view", "gobierno_presupuesto:view", "gobierno_presupuesto:certify"],
      mundo.companyId,
    );
    const aprobador = await crearUsuario(
      request,
      admin.headers,
      ["organization:view", "gobierno_tasas:view", "gobierno_tasas:approve", "documentos:view"],
      mundo.companyId,
    );
    const tipo = await crearTipoDocumental(request, mundo.headers, mundo.companyId);
    const anio = ANIO;
    const fechaTasa = hoyCaracas();

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
          tipo_limite: "MONTO",
          monto: "500.00",
          moneda: "USD",
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
          monto: "1000000.00",
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
          monto: "1000000.00",
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
          monto: "600000.00",
          concepto: "Adquisición de material médico",
          expediente_referencia: "EXP-PRES-2026-001",
          firmante_cargo_id: cargoPres.id,
        },
      },
    );
    expect(cdpResp.status()).toBe(201);
    expect((await cdpResp.json()).estado).toBe("VIGENTE");

    const TASAS = `${API}/gobierno/tesoreria/tasas`;

    await entrarEnGobierno(page, mundo.username, mundo.codigo, "/");
    await cerrarNotificaciones(page);

    await page.locator('nav a[href="/gobierno/tesoreria/tasas"]').first().click();
    await expect(page.getByRole("heading", { name: "Tasas oficiales", exact: true })).toBeVisible();

    await page.getByRole("combobox", { name: "Moneda (obligatorio)", exact: true }).selectOption("USD");
    await page.getByLabel("Fecha efectiva").fill(fechaTasa);
    await page.getByRole("textbox", { name: "Valor en VES por unidad (obligatorio)", exact: true }).fill("900,5");
    await page.getByRole("textbox", { name: "Referencia oficial del BCV (obligatorio)", exact: true }).fill("BCV · tipo de cambio oficial de referencia");

    const crearTasaRespPromise = page.waitForResponse(
      (resp) =>
        resp.request().method() === "POST" &&
        new URL(resp.url()).pathname.endsWith("/gobierno/tesoreria/tasas"),
    );
    await page.getByRole("button", { name: "Registrar tasa", exact: true }).click();
    const crearTasaResp = await crearTasaRespPromise;
    expect(crearTasaResp.status()).toBe(201);
    const tasa = await crearTasaResp.json();
    expect(tasa.estado).toBe("BORRADOR");

    await adjuntarDocumentoApi(
      request,
      mundo.headers,
      mundo.companyId,
      tipo.id,
      "GovernmentOfficialExchangeRate",
      tasa.id,
    );

    const aprobarSponsorResp = await request.post(`${TASAS}/${tasa.id}/aprobar`, {
      headers: mundo.headers,
      data: {},
    });
    expect(aprobarSponsorResp.status()).toBe(403);

    const aprobarTasaResp = await request.post(`${TASAS}/${tasa.id}/aprobar`, {
      headers: aprobador.headers,
      data: {},
    });
    expect(aprobarTasaResp.status()).toBe(200);
    const tasaAprobada = await aprobarTasaResp.json();
    expect(tasaAprobada.estado).toBe("APROBADA");

    await page.reload();
    await cerrarNotificaciones(page);
    await expect(page.getByRole("heading", { name: "Tasas oficiales", exact: true })).toBeVisible();
    await expect(page.getByRole("region", { name: "Tabla de tasas oficiales", exact: true })).toContainText("1 USD = 900,50000000 VES");
    await expect(page.getByRole("region", { name: "Tabla de tasas oficiales", exact: true })).toContainText("Aprobada");

    const fechaTasaPartes = fechaTasa.split("-");
    const fechaTasaFormato = `${fechaTasaPartes[2]}/${fechaTasaPartes[1]}/${fechaTasaPartes[0]}`;
    await page.getByRole("button", { name: `Ver USD ${fechaTasaFormato} v1`, exact: true }).click();
    await expect(page.getByText("Historia de versiones", { exact: true })).toBeVisible();

    await page.getByRole("textbox", { name: "Nuevo valor en VES por unidad (obligatorio)", exact: true }).fill("1000");
    await page.getByRole("textbox", { name: "Referencia oficial del BCV de la corrección (obligatorio)", exact: true }).fill("BCV · corrección publicada");
    await page.getByRole("textbox", { name: "Motivo de la corrección (obligatorio)", exact: true }).fill("Corrección del valor publicado por el BCV");

    const correccionRespPromise = page.waitForResponse(
      (resp) =>
        resp.request().method() === "POST" &&
        new URL(resp.url()).pathname.endsWith(`/tasas/${tasa.id}/correccion`),
    );
    await page.getByRole("button", { name: "Registrar corrección", exact: true }).click();
    const correccionResp = await correccionRespPromise;
    expect(correccionResp.status()).toBe(201);
    const v2 = await correccionResp.json();
    expect(v2.version).toBe(2);

    await adjuntarDocumentoApi(
      request,
      mundo.headers,
      mundo.companyId,
      tipo.id,
      "GovernmentOfficialExchangeRate",
      v2.id,
    );

    const aprobarCorreccionResp = await request.post(`${TASAS}/${v2.id}/aprobar`, {
      headers: aprobador.headers,
      data: {},
    });
    expect(aprobarCorreccionResp.status()).toBe(200);

    const tasaSustituidaResp = await request.get(`${TASAS}/${tasa.id}`, {
      headers: mundo.headers,
    });
    expect(tasaSustituidaResp.status()).toBe(200);
    const tasaSustituida = await tasaSustituidaResp.json();
    expect(tasaSustituida.estado).toBe("SUSTITUIDA");

    await page.locator('nav a[href="/gobierno/presupuesto/ejercicios"]').first().click();
    await expect(page.getByRole("heading", { name: "Ejercicios presupuestarios", exact: true })).toBeVisible();
    await page.getByRole("link", { name: `Ejercicio ${anio}`, exact: true }).click();
    await expect(page.getByRole("heading", { name: `Ejercicio presupuestario ${anio}`, exact: true })).toBeVisible();

    const seccion = page.locator("section").filter({ has: page.getByRole("heading", { name: "Compromisos", exact: true }) });

    await seccion.getByRole("combobox", { name: "Certificación de la imputación 1 (obligatorio)", exact: true }).selectOption({ index: 1 });
    await seccion.getByRole("textbox", { name: "Monto de la imputación 1 (obligatorio)", exact: true }).fill("450000,00");
    await seccion.getByRole("textbox", { name: "Concepto (obligatorio)", exact: true }).fill("Orden de compra de material médico");
    await seccion.getByRole("combobox", { name: "Autoridad que compromete (cargo) (obligatorio)", exact: true }).selectOption({ value: cargoAdm.id });
    await seccion.getByRole("combobox", { name: "Soporte documental (obligatorio)", exact: true }).selectOption({ index: 1 });

    await expect(page.getByText("Tasa oficial utilizada: 1 USD = 1.000,00000000 VES", { exact: true })).toBeVisible();
    await expect(page.getByText(`Fecha de la tasa: ${fechaTasaFormato}`, { exact: true })).toBeVisible();
    await expect(page.getByText("dentro del límite", { exact: false })).toBeVisible();

    const compromisoRespPromise = page.waitForResponse(
      (resp) =>
        resp.request().method() === "POST" &&
        new URL(resp.url()).pathname.endsWith("/compromisos"),
    );
    await seccion.getByRole("button", { name: "Registrar compromiso", exact: true }).click();
    const compromisoResp = await compromisoRespPromise;
    expect(compromisoResp.status()).toBe(201);
    const k = await compromisoResp.json();
    expect(k.conversion.tasas[0].version).toBe(2);
    expect(k.conversion.tasas[0].fuente).toBe("BCV");

    await expect(page.getByRole("region", { name: "Tabla de compromisos", exact: true })).toContainText("Tasa BCV: 1 USD = 1.000,00000000 VES");

    const anularV2Resp = await request.post(`${TASAS}/${v2.id}/anular`, {
      headers: aprobador.headers,
      data: { motivo: "Retiro de la tasa para la prueba de bloqueo" },
    });
    expect(anularV2Resp.status()).toBe(200);

    await page.reload();
    await cerrarNotificaciones(page);
    await expect(page.getByRole("heading", { name: `Ejercicio presupuestario ${anio}`, exact: true })).toBeVisible();

    await seccion.getByRole("combobox", { name: "Certificación de la imputación 1 (obligatorio)", exact: true }).selectOption({ index: 1 });
    await seccion.getByRole("textbox", { name: "Monto de la imputación 1 (obligatorio)", exact: true }).fill("10,00");
    await seccion.getByRole("textbox", { name: "Concepto (obligatorio)", exact: true }).fill("Orden de compra de material médico");
    await seccion.getByRole("combobox", { name: "Autoridad que compromete (cargo) (obligatorio)", exact: true }).selectOption({ value: cargoAdm.id });
    await seccion.getByRole("combobox", { name: "Soporte documental (obligatorio)", exact: true }).selectOption({ index: 1 });

    await expect(page.getByRole("alert").filter({ hasText: "No hay tasa oficial BCV aprobada" })).toBeVisible();

    const sinTasaRespPromise = page.waitForResponse(
      (resp) =>
        resp.request().method() === "POST" &&
        new URL(resp.url()).pathname.endsWith("/compromisos"),
    );
    await seccion.getByRole("button", { name: "Registrar compromiso", exact: true }).click();
    const sinTasaResp = await sinTasaRespPromise;
    expect(sinTasaResp.status()).toBe(422);
    expect((await sinTasaResp.json()).code).toBe("GOV_OFFICIAL_RATE_REQUIRED");
    await cerrarNotificaciones(page);

    const historiaV2Resp = await request.get(`${TASAS}/${v2.id}`, {
      headers: mundo.headers,
    });
    expect(historiaV2Resp.status()).toBe(200);
    const historiaV2 = await historiaV2Resp.json();
    const versionesHistoria = (historiaV2.historia ?? []).map((h: { version: number }) => h.version);
    const estadosHistoria = (historiaV2.historia ?? []).map((h: { estado: string }) => h.estado);
    expect(versionesHistoria).toEqual(expect.arrayContaining([1, 2]));
    expect(estadosHistoria).toEqual(expect.arrayContaining(["SUSTITUIDA", "ANULADA"]));

    const otro = await prepararMundo(request, ["organization:view", "gobierno_tasas:view"]);
    const aislamientoResp = await request.get(`${TASAS}/${tasa.id}`, {
      headers: otro.headers,
    });
    expect(aislamientoResp.status()).toBe(404);

    await page.locator('nav a[href="/gobierno/tesoreria/tasas"]').first().click();
    await expect(page.getByRole("heading", { name: "Tasas oficiales", exact: true })).toBeVisible();

    for (const ancho of [1280, 390, 320]) {
      await page.setViewportSize({ width: ancho, height: 800 });
      await expect(page.getByRole("heading", { name: "Tasas oficiales", exact: true })).toBeVisible();
      await sinViolacionesSerias(page, `tasas ${ancho}`);
    }
  });
});
