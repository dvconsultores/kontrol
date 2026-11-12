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

  estructuraVigenteApi,
  prepararMundo,
} from "./helpers/gobierno";
import type { APIRequestContext, Page } from "@playwright/test";

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
  "gobierno_auditoria:view",
];

const WCAG = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"];

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

test.describe("Reporte de control interno", () => {
  test("REP-10: reporte de control interno con conflicto real, exportación, permisos, aislamiento y responsive", async ({ page, request, browser }) => {
    test.setTimeout(300_000);
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
    const reglaCodigo = regla.codigo as string;

    const activarResp = await request.post(`${API}/gobierno/sod/reglas/${reglaId}/activar`, {
      headers: { ...mundo.headers, "If-Match": String(regla.version) },
      data: {},
    });
    expect(activarResp.status(), await activarResp.text()).toBe(200);

    const acto = await actoBorradorApi(request, mundo.headers, cargoId, `REP10-DA-01-${ANIO}`);

    const actoCompleto = await request.get(`${API}/gobierno/actos/${acto.id}`, { headers: mundo.headers });
    expect(actoCompleto.ok()).toBeTruthy();
    const actoConVersion = await actoCompleto.json();

    const patchResp = await request.patch(`${API}/gobierno/actos/${acto.id}`, {
      headers: { ...mundo.headers, "If-Match": String(actoConVersion.version) },
      data: { asunto: "Cambio del autor" },
    });
    expect(patchResp.status(), await patchResp.text()).toBe(409);

    await entrarEnGobierno(page, mundo.username, mundo.codigo, "/gobierno/control-interno");
    await cerrarNotificaciones(page);

    await expect(page.getByRole("link", { name: "Reporte de control interno" })).toBeVisible();
    await expect(page.getByRole("heading", { level: 1, name: "Reporte de control interno" })).toBeVisible();
    await sinViolacionesSerias(page, "reporte 1280");

    const tablaConflictos = page.getByRole("table", { name: "Conflictos recientes" });
    await expect(tablaConflictos).toContainText(reglaCodigo);
    await expect(tablaConflictos).toContainText("Editar el borrador del acto");
    const fila = tablaConflictos.getByRole("row", { name: new RegExp(reglaCodigo) });
    const enlaceBitacora = fila.getByRole("link", { name: "Ver en la bitácora" });
    await expect(enlaceBitacora).toHaveAttribute("href", /^\/gobierno\/bitacora\//);

    await expect(page.getByRole("heading", { level: 2, name: "Excepciones a los controles (overrides)" })).toBeVisible();
    await expect(page.getByRole("heading", { level: 2, name: "Operaciones duplicadas" })).toBeVisible();
    await expect(page.getByText("No aplica: en Gobierno los controles de segregación de funciones solo bloquean")).toBeVisible();

    const [download] = await Promise.all([
      page.waitForEvent("download"),
      page.getByRole("button", { name: "Exportar CSV" }).click(),
    ]);
    expect(download.suggestedFilename().endsWith(".csv")).toBe(true);

    const manana = new Date();
    manana.setDate(manana.getDate() + 1);
    const mananaCaracas = new Intl.DateTimeFormat("en-CA", { timeZone: "America/Caracas" }).format(manana);
    await page.locator("#rc-desde").fill(mananaCaracas);
    await page.locator("#rc-hasta").fill(hoyCaracas());
    const [invalidResp] = await Promise.all([
      page.waitForResponse(
        (r) =>
          r.request().method() === "GET" &&
          new URL(r.url()).pathname.includes("/api/v1/gobierno/control-interno/"),
        { timeout: 60_000 },
      ),
      page.getByRole("button", { name: "Aplicar" }).click(),
    ]);
    expect(invalidResp.status()).toBe(422);
    await expect(page.getByText("La fecha inicial no puede ser posterior a la fecha final")).toBeVisible();

    const sessionAdmin = await sesionApi("admintenant", { tenant: TENANT });
    const usuarioSinHallazgos = await crearUsuario(
      request,
      sessionAdmin.headers,
      ["organization:view", "gobierno_auditoria:view"],
      mundo.companyId,
    );
    const contextoLimite = await browser.newContext();
    const paginaLimite = await contextoLimite.newPage();
    await entrarEnGobierno(paginaLimite, usuarioSinHallazgos.username, mundo.codigo, "/gobierno/control-interno");
    await expect(paginaLimite.getByText("Sin permiso para ver hallazgos (gobierno_hallazgos:view)")).toBeVisible();
    await contextoLimite.close();

    const usuarioSoloOrg = await crearUsuario(
      request,
      sessionAdmin.headers,
      ["organization:view"],
      mundo.companyId,
    );
    const soloOrgResp = await request.get(`${API}/gobierno/control-interno/reporte`, {
      headers: usuarioSoloOrg.headers,
    });
    expect(soloOrgResp.status()).toBe(403);

    const otroMundo = await prepararMundo(request, ["organization:view", "gobierno_auditoria:view"]);
    const otroReporteResp = await request.get(`${API}/gobierno/control-interno/reporte`, {
      headers: otroMundo.headers,
    });
    expect(otroReporteResp.status(), await otroReporteResp.text()).toBe(200);
    const otroReporte = await otroReporteResp.json();
    expect(otroReporte.conflictos_sod.eventos.some((e: { regla_codigo?: string }) => e.regla_codigo === reglaCodigo)).toBe(false);

    for (const ancho of [390, 320]) {
      await page.setViewportSize({ width: ancho, height: 800 });
      await page.goto("/gobierno/control-interno");
      await expect(page.getByRole("heading", { level: 1, name: "Reporte de control interno" })).toBeVisible();
      await expect(page.getByRole("heading", { level: 2, name: "Conflictos de segregación de funciones" })).toBeVisible();
      const sinDesbordamiento = await page.evaluate(
        (w) => document.documentElement.scrollWidth <= w + 1,
        ancho,
      );
      expect(sinDesbordamiento, `desbordamiento ${ancho}`).toBe(true);
      await sinViolacionesSerias(page, `reporte ${ancho}`);
    }

    const botonExportar = page.getByRole("button", { name: "Exportar CSV" });
    await botonExportar.focus();
    await expect(botonExportar).toBeFocused();
  });
});
