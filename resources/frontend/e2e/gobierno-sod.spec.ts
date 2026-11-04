import AxeBuilder from "@axe-core/playwright";
import { expect, sesionApi, test } from "./helpers/sesion";
import {
  ANIO,
  API,
  RESPONSABLE_ESTRUCTURA,
  TENANT,
  cargoVigenteApi,
  cerrarNotificaciones,
  crearTipoDocumental,
  crearUsuario,
  enteActivo,
  entrarEnGobierno,
  es2xx,
  estructuraVigenteApi,
  prepararMundo,
} from "./helpers/gobierno";
import type { APIRequestContext, Locator, Page } from "@playwright/test";

const RESPONSABLE_SOD = [
  ...RESPONSABLE_ESTRUCTURA,
  "gobierno_cargos:view",
  "gobierno_cargos:edit",
  "gobierno_cargos:publish",
  "gobierno_actos:view",
  "gobierno_actos:edit",
  "gobierno_hallazgos:view",
  "gobierno_hallazgos:manage",
  "gobierno_sod:view",
  "gobierno_sod:manage",
  "gobierno_sod:activate",
];

const OTRO_ACTOR = [
  "organization:view",
  "gobierno_estructura:view",
  "gobierno_cargos:view",
  "gobierno_actos:view",
  "gobierno_actos:edit",
  "gobierno_hallazgos:view",
  "gobierno_hallazgos:manage",
  "documentos:view",
];

const CONSULTA_SOD = ["organization:view", "gobierno_sod:view"];

const WCAG = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"];

async function pulsarYEsperar(page: Page, boton: Locator, metodo: string, ruta: RegExp): Promise<void> {
  await cerrarNotificaciones(page);
  const [resp] = await Promise.all([
    page.waitForResponse((r) => r.request().method() === metodo && ruta.test(new URL(r.url()).pathname), { timeout: 60_000 }),
    boton.click(),
  ]);
  expect(es2xx(resp.status()), await resp.text()).toBe(true);
}

async function mundoConCargo(request: APIRequestContext) {
  const mundo = await prepararMundo(request, RESPONSABLE_SOD);
  const tipo = await crearTipoDocumental(request, mundo.headers, mundo.companyId);
  await enteActivo(request, mundo.headers, mundo.companyId, tipo.id);
  const { da01Id } = await estructuraVigenteApi(
    request,
    mundo.headers,
    mundo.companyId,
    tipo.id,
    ANIO,
  );
  const cargo = await cargoVigenteApi(
    request,
    mundo.headers,
    mundo.companyId,
    tipo.id,
    ANIO,
    da01Id,
    "DIR-ADM",
  );
  return { mundo, tipo, cargoId: cargo.id };
}

function hoyCaracas(): string {
  return new Intl.DateTimeFormat("en-CA", { timeZone: "America/Caracas" }).format(
    new Date(),
  );
}

async function actoBorradorApi(
  request: APIRequestContext,
  headers: Record<string, string>,
  cargoId: string,
  numero: string,
): Promise<{ id: string }> {
  const data = {
    tipo: "RESOLUCION",
    numero,
    caracter: "PARTICULAR",
    asunto: `Asunto ${numero}`,
    simple_tramite: false,
    cargo_id: cargoId,
    fecha: hoyCaracas(),
    lugar: "Caracas",
    fundamento_competencia: "Reglamento interno, art. 12",
    funcionario: "Funcionaria de prueba",
    titularidad: "TITULAR",
    destinatario: "Proveedor de prueba",
    hechos: "Hechos de prueba",
    fundamentos: "Fundamentos legales de prueba",
    decision: "Decisión de prueba",
    competencia: { accion: "APROBAR", materia: "CONTRATACIONES" },
  };

  const resp = await request.post(`${API}/gobierno/actos`, {
    headers,
    data,
  });
  expect(resp.status(), await resp.text()).toBe(201);
  const body = await resp.json();
  return { id: body.id };
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

test.describe("Gobierno · Segregación de funciones (CTL-01)", () => {
  test("SOD-E2E-01 · CTL-06 por la interfaz", async ({ page, browser, request }) => {
    test.setTimeout(240_000);
    const { mundo } = await mundoConCargo(request);

    await entrarEnGobierno(page, mundo.username, mundo.codigo, "/gobierno/sod");
    await expect(page.getByRole("heading", { level: 1, name: "Segregación de funciones" })).toBeVisible();

    await page.getByRole("link", { name: "Nueva regla" }).click();
    await expect(page.getByRole("heading", { level: 1, name: "Nueva regla de segregación de funciones" })).toBeVisible();

    await page.getByLabel("Proceso").selectOption({ label: "Hallazgos y acciones correctivas" });
    await page.getByLabel("Acción A").selectOption({ label: "Registrar el hallazgo" });
    await page.getByLabel("Acción B").selectOption({ label: "Añadir una recomendación" });
    await page.getByLabel("Nombre").fill("Quien registra no recomienda");
    await page.getByLabel("Razón").fill("Quien registra el hallazgo no debe formular su recomendación.");

    await pulsarYEsperar(
      page,
      page.getByRole("button", { name: "Registrar regla" }),
      "POST",
      /\/api\/v1\/gobierno\/sod\/reglas$/,
    );

    await expect(page).toHaveURL(/\/gobierno\/sod\/[0-9a-f-]{36}$/);
    const titulo = page.getByRole("heading", { level: 1 });
    await expect(titulo).toHaveText(/^Regla SOD-\d{4}-\d{4}$/);
    const codigo = ((await titulo.textContent()) ?? "").trim().replace(/^Regla /, "");
    const reglaId = page.url().split("/").pop() ?? "";

    await pulsarYEsperar(
      page,
      page.getByRole("button", { name: "Activar regla" }),
      "POST",
      /\/api\/v1\/gobierno\/sod\/reglas\/[\w-]+\/activar$/,
    );
    await expect(page.getByText("Vigente · en vigor")).toBeVisible();

    const hallazgoResp = await request.post(`${API}/gobierno/hallazgos`, {
      headers: mundo.headers,
      data: {
        titulo: "Hallazgo para prueba de SOD",
        condicion: "Condición observada en la prueba",
        criterio: "Criterio normativo aplicable",
        causa: "Causa raíz identificada",
        efecto: "Efecto material del hallazgo",
        riesgo: "MEDIO",
        origen: "INDEPENDIENTE",
        origen_descripcion: "Prueba de segregación de funciones",
      },
    });
    expect(hallazgoResp.status(), await hallazgoResp.text()).toBe(201);
    const hallazgo = await hallazgoResp.json();
    const hallazgoId = hallazgo.id as string;

    await page.goto(`/gobierno/hallazgos/${hallazgoId}`);
    await page.getByLabel("Recomendación").fill("Recomendación que debe quedar bloqueada");

    await cerrarNotificaciones(page);
    const [recomendacionResp] = await Promise.all([
      page.waitForResponse(
        (r) =>
          r.request().method() === "POST" &&
          new URL(r.url()).pathname === `/api/v1/gobierno/hallazgos/${hallazgoId}/recomendaciones`,
        { timeout: 60_000 },
      ),
      page.getByRole("button", { name: "Añadir recomendación" }).click(),
    ]);
    expect(recomendacionResp.status()).toBe(409);

    const alerta = page.getByRole("alert");
    await expect(alerta).toContainText("Operación bloqueada por segregación de funciones");
    await expect(alerta).toContainText("Registrar el hallazgo");
    await expect(alerta).toContainText("Pida a otro usuario autorizado");

    const hallazgoGetResp = await request.get(`${API}/gobierno/hallazgos/${hallazgoId}`, {
      headers: mundo.headers,
    });
    expect(hallazgoGetResp.status(), await hallazgoGetResp.text()).toBe(200);
    const hallazgoGet = await hallazgoGetResp.json();
    expect(hallazgoGet.recomendaciones.length).toBe(0);

    const sessionAdmin = await sesionApi("admintenant", { tenant: TENANT });
    const otro = await crearUsuario(request, sessionAdmin.headers, OTRO_ACTOR, mundo.companyId);

    const contextoOtro = await browser.newContext();
    const page2 = await contextoOtro.newPage();
    await entrarEnGobierno(page2, otro.username, mundo.codigo, "/gobierno/hallazgos");
    await page2.goto(`/gobierno/hallazgos/${hallazgoId}`);
    await page2.getByLabel("Recomendación").fill("Recomendación formulada por otro usuario");

    await cerrarNotificaciones(page2);
    const [recomendacionOtroResp] = await Promise.all([
      page2.waitForResponse(
        (r) =>
          r.request().method() === "POST" &&
          new URL(r.url()).pathname === `/api/v1/gobierno/hallazgos/${hallazgoId}/recomendaciones`,
        { timeout: 60_000 },
      ),
      page2.getByRole("button", { name: "Añadir recomendación" }).click(),
    ]);
    expect(es2xx(recomendacionOtroResp.status()), await recomendacionOtroResp.text()).toBe(true);
    await contextoOtro.close();

    await page.goto("/gobierno/sod/conflictos");
    const tablaConflictos = page.getByRole("region", { name: "Tabla de conflictos de segregación de funciones" });
    await expect(tablaConflictos).toContainText(mundo.username);
    await expect(tablaConflictos).toContainText(codigo);
    await expect(tablaConflictos).toContainText("Añadir una recomendación");
    await expect(tablaConflictos).toContainText("Registrar el hallazgo");
    await expect(
      page.getByRole("link", { name: "Abrir hallazgo" }),
    ).toHaveAttribute("href", `/gobierno/hallazgos/${hallazgoId}`);

    const reglaGetResp = await request.get(`${API}/gobierno/sod/reglas/${reglaId}`, {
      headers: mundo.headers,
    });
    expect(reglaGetResp.status(), await reglaGetResp.text()).toBe(200);
    const reglaGet = await reglaGetResp.json();
    expect(reglaGet.conflictos).toBe(1);
  });

  test("SOD-E2E-02 · DOC-02", async ({ page, request }) => {
    test.setTimeout(240_000);
    const { mundo, cargoId } = await mundoConCargo(request);

    const reglaResp = await request.post(`${API}/gobierno/sod/reglas`, {
      headers: mundo.headers,
      data: {
        nombre: "Quien registra no edita",
        descripcion: "Quien registra el acto no debe editar su borrador.",
        proceso: "DOC-02",
        accion_a: "DOC02_REGISTRAR",
        accion_b: "DOC02_EDITAR",
        bidireccional: false,
        vigente_desde: hoyCaracas(),
        vigente_hasta: null,
      },
    });
    expect(reglaResp.status(), await reglaResp.text()).toBe(201);
    const regla = await reglaResp.json();
    const reglaId = regla.id as string;

    const activarResp = await request.post(`${API}/gobierno/sod/reglas/${reglaId}/activar`, {
      headers: { ...mundo.headers, "If-Match": String(regla.version) },
      data: {},
    });
    expect(activarResp.status(), await activarResp.text()).toBe(200);

    const acto = await actoBorradorApi(request, mundo.headers, cargoId, `SOD-DA-01-${ANIO}`);

    await entrarEnGobierno(page, mundo.username, mundo.codigo, "/gobierno/actos");
    await page.goto(`/gobierno/actos/${acto.id}`);
    await page.getByRole("button", { name: "Editar" }).click();
    await page.getByLabel("Asunto").fill("Asunto cambiado por el autor");

    await cerrarNotificaciones(page);
    const [patchResp] = await Promise.all([
      page.waitForResponse(
        (r) =>
          r.request().method() === "PATCH" &&
          new URL(r.url()).pathname === `/api/v1/gobierno/actos/${acto.id}`,
        { timeout: 60_000 },
      ),
      page.getByRole("button", { name: "Guardar" }).click(),
    ]);
    expect(patchResp.status()).toBe(409);

    const alerta = page.getByRole("alert");
    await expect(alerta).toContainText("Operación bloqueada por segregación de funciones");
    await expect(alerta).toContainText("Registrar el acto");

    const actoGetResp = await request.get(`${API}/gobierno/actos/${acto.id}`, {
      headers: mundo.headers,
    });
    expect(actoGetResp.status(), await actoGetResp.text()).toBe(200);
    const actoGet = await actoGetResp.json();
    expect(actoGet.asunto).toBe(`Asunto SOD-DA-01-${ANIO}`);

    const sessionAdmin = await sesionApi("admintenant", { tenant: TENANT });
    const otro = await crearUsuario(request, sessionAdmin.headers, OTRO_ACTOR, mundo.companyId);
    const actoOtroResp = await request.get(`${API}/gobierno/actos/${acto.id}`, {
      headers: otro.headers,
    });
    expect(actoOtroResp.status(), await actoOtroResp.text()).toBe(200);
    const actoOtro = await actoOtroResp.json();

    const patchOtroResp = await request.patch(`${API}/gobierno/actos/${acto.id}`, {
      headers: { ...otro.headers, "If-Match": String(actoOtro.version) },
      data: { asunto: "Asunto cambiado por otro usuario" },
    });
    expect(patchOtroResp.status(), await patchOtroResp.text()).toBe(200);

    await page.goto("/gobierno/sod/conflictos");
    const tablaConflictos = page.getByRole("region", { name: "Tabla de conflictos de segregación de funciones" });
    await expect(tablaConflictos).toContainText("Editar el borrador del acto");
    await expect(
      page.getByRole("link", { name: "Abrir acto" }),
    ).toHaveAttribute("href", `/gobierno/actos/${acto.id}`);
  });

  test("SOD-E2E-03 · consulta, permisos y accesibilidad", async ({ page, request, browser }) => {
    test.setTimeout(180_000);
    const mundo = await prepararMundo(request, RESPONSABLE_SOD);

    const reglaResp = await request.post(`${API}/gobierno/sod/reglas`, {
      headers: mundo.headers,
      data: {
        nombre: "Regla de consulta",
        descripcion: "Regla creada para comprobar permisos de consulta.",
        proceso: "CTL-06",
        accion_a: "CTL06_REGISTRAR",
        accion_b: "CTL06_RECOMENDAR",
        bidireccional: false,
        vigente_desde: hoyCaracas(),
        vigente_hasta: null,
      },
    });
    expect(reglaResp.status(), await reglaResp.text()).toBe(201);
    const regla = await reglaResp.json();
    const reglaId = regla.id as string;
    const codigo = regla.codigo as string;

    const sessionAdmin = await sesionApi("admintenant", { tenant: TENANT });
    const consulta = await crearUsuario(request, sessionAdmin.headers, CONSULTA_SOD, mundo.companyId);

    const contextoConsulta = await browser.newContext();
    const pageConsulta = await contextoConsulta.newPage();
    await entrarEnGobierno(pageConsulta, consulta.username, mundo.codigo, "/gobierno/sod");
    await expect(pageConsulta.getByRole("region", { name: "Tabla de reglas de segregación de funciones" })).toContainText(codigo);
    await expect(pageConsulta.getByRole("link", { name: "Nueva regla" })).toHaveCount(0);

    await pageConsulta.getByRole("link", { name: `Abrir la regla ${codigo}` }).click();
    await expect(pageConsulta.getByRole("heading", { level: 1 })).toHaveText(`Regla ${codigo}`);
    await expect(pageConsulta.getByRole("button", { name: "Activar regla" })).toHaveCount(0);
    await contextoConsulta.close();

    await entrarEnGobierno(page, mundo.username, mundo.codigo, "/gobierno/sod");
    const pantallas: ReadonlyArray<readonly [ruta: string, titulo: string | RegExp, nombre: string]> = [
      ["/gobierno/sod", "Segregación de funciones", "S1"],
      ["/gobierno/sod/nueva", "Nueva regla de segregación de funciones", "S2"],
      [`/gobierno/sod/${reglaId}`, `Regla ${codigo}`, "S3"],
      ["/gobierno/sod/conflictos", "Conflictos de segregación de funciones", "S4"],
    ];
    for (const [ruta, titulo, nombre] of pantallas) {
      await page.setViewportSize({ width: 1280, height: 768 });
      await page.goto(ruta);
      await expect(page.getByRole("heading", { level: 1, name: titulo })).toBeVisible();
      for (const ancho of [1280, 768, 320]) {
        await page.setViewportSize({ width: ancho, height: 768 });
        await expect(page.getByRole("heading", { level: 1, name: titulo })).toBeVisible();
        await sinViolacionesSerias(page, `${nombre} ${ancho}x768`);
      }
    }
  });
});
