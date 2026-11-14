import AxeBuilder from "@axe-core/playwright";
import { expect, sesionApi, test } from "./helpers/sesion";
import {
  ANIO,
  API,
  RESPONSABLE_ESTRUCTURA,
  TENANT,
  cerrarNotificaciones,
  crearTipoDocumental,
  crearUsuario,
  enteActivo,
  entrarEnGobierno,
  estructuraVigenteApi,
  prepararMundo,
} from "./helpers/gobierno";
import type { Page } from "@playwright/test";

const RESPONSABLE_REPORTE = [
  ...RESPONSABLE_ESTRUCTURA,
  "gobierno_cargos:view",
  "gobierno_cargos:edit",
  "gobierno_cargos:publish",
  "gobierno_actos:view",
  "gobierno_ocupacion:view",
  "gobierno_ocupacion:manage",
  "gobierno_expedientes:view",
  "gobierno_expedientes:manage",
  "documentos:view",
  "documentos:create",
];

const WCAG = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"];

function hoyCaracas(): string {
  return new Intl.DateTimeFormat("en-CA", { timeZone: "America/Caracas" }).format(
    new Date(),
  );
}

function ayerCaracas(): string {
  const ayer = new Date();
  ayer.setDate(ayer.getDate() - 1);
  return new Intl.DateTimeFormat("en-CA", { timeZone: "America/Caracas" }).format(
    ayer,
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

test.describe("Reporte de contrataciones", () => {
  test("REP-03: reporte de contrataciones con expediente real, desviación, exportación, permisos, aislamiento y responsive", async ({ page, request }) => {
    test.setTimeout(300_000);
    const mundo = await prepararMundo(request, RESPONSABLE_REPORTE);
    const tipo = await crearTipoDocumental(request, mundo.headers, mundo.companyId);
    await enteActivo(request, mundo.headers, mundo.companyId, tipo.id);
    const estructura = await estructuraVigenteApi(
      request,
      mundo.headers,
      mundo.companyId,
      tipo.id,
      ANIO,
    );

    const funcionarioResp = await request.post(`${API}/gobierno/ocupacion/funcionarios`, {
      headers: mundo.headers,
      data: {
        nombre: "Persona Reporte REP-03",
        tipo_documento: "V",
        numero_documento: String(Math.floor(10000000 + Math.random() * 89999999)),
      },
    });
    expect(funcionarioResp.status(), await funcionarioResp.text()).toBe(201);
    const funcionario = await funcionarioResp.json();

    const expedienteResp = await request.post(`${API}/gobierno/contrataciones/expedientes`, {
      headers: mundo.headers,
      data: {
        numero: `REP03-${Date.now()}`,
        fecha_inicio: hoyCaracas(),
        objeto: "Adquisición de prueba REP-03",
        tipo_contratacion: "BIENES",
        modalidad_declarada: "CONSULTA_PRECIOS",
        modalidad_fundamento: "Fundamento de prueba",
        unidad_id: estructura.da01Id,
        responsable_id: funcionario.id,
      },
    });
    expect(expedienteResp.status(), await expedienteResp.text()).toBe(201);
    const exp = await expedienteResp.json();

    const hitoResp = await request.post(
      `${API}/gobierno/contrataciones/expedientes/${exp.id}/hitos`,
      {
        headers: { ...mundo.headers, "If-Match": String(exp.version) },
        data: {
          nombre: "Publicación del llamado",
          fecha_prevista: ayerCaracas(),
        },
      },
    );
    expect(hitoResp.status(), await hitoResp.text()).toBe(200);

    await entrarEnGobierno(page, mundo.username, mundo.codigo, "/gobierno/contrataciones/reporte");
    await cerrarNotificaciones(page);

    await expect(page.getByRole("heading", { level: 1, name: "Reporte de contrataciones" })).toBeVisible();
    await expect(page.getByRole("heading", { level: 2, name: "Distribución" })).toBeVisible();
    await sinViolacionesSerias(page, "reporte contrataciones 1280");

    const tablaModalidad = page.getByRole("table", { name: "Por modalidad", exact: true });
    await expect(tablaModalidad).toContainText("Consulta de precios");

    const tablaDesviacion = page.getByRole("table", { name: "Hitos con desviación", exact: true });
    await expect(tablaDesviacion).toContainText("Publicación del llamado");
    await expect(tablaDesviacion).toContainText("Vencido");

    const enlaceExpediente = tablaDesviacion.getByRole("link", { name: new RegExp(exp.numero) });
    await expect(enlaceExpediente).toHaveAttribute(
      "href",
      `/gobierno/contrataciones/expedientes/${exp.id}`,
    );

    await expect(page.getByRole("heading", { level: 2, name: "Monto" })).toBeVisible();
    await expect(
      page.getByText("No declarado: ninguna oferta adjudicada del periodo tiene monto declarado."),
    ).toBeVisible();

    const [download] = await Promise.all([
      page.waitForEvent("download"),
      page.getByRole("button", { name: "Exportar CSV" }).click(),
    ]);
    expect(download.suggestedFilename().endsWith(".csv")).toBe(true);

    const manana = new Date();
    manana.setDate(manana.getDate() + 1);
    const mananaCaracas = new Intl.DateTimeFormat("en-CA", { timeZone: "America/Caracas" }).format(manana);
    await page.locator("#rp-desde").fill(mananaCaracas);
    await page.locator("#rp-hasta").fill(hoyCaracas());
    const [invalidResp] = await Promise.all([
      page.waitForResponse(
        (r) =>
          r.request().method() === "GET" &&
          new URL(r.url()).pathname.includes("/api/v1/gobierno/contrataciones/reporte"),
        { timeout: 60_000 },
      ),
      page.getByRole("button", { name: "Aplicar" }).click(),
    ]);
    expect(invalidResp.status()).toBe(422);
    await expect(page.getByText("La fecha inicial no puede ser posterior a la fecha final")).toBeVisible();
    await expect(page.locator("#rp-desde")).toBeVisible();

    const sessionAdmin = await sesionApi("admintenant", { tenant: TENANT });
    const usuarioSoloOrg = await crearUsuario(
      request,
      sessionAdmin.headers,
      ["organization:view"],
      mundo.companyId,
    );
    const soloOrgResp = await request.get(`${API}/gobierno/contrataciones/reporte`, {
      headers: usuarioSoloOrg.headers,
    });
    expect(soloOrgResp.status()).toBe(403);

    const otroMundo = await prepararMundo(request, ["organization:view", "gobierno_expedientes:view"]);
    const otroReporteResp = await request.get(`${API}/gobierno/contrataciones/reporte`, {
      headers: otroMundo.headers,
    });
    expect(otroReporteResp.status(), await otroReporteResp.text()).toBe(200);
    const otroReporte = await otroReporteResp.json();
    expect(
      otroReporte.desviaciones.hitos.some(
        (h: { expediente_id?: string }) => h.expediente_id === exp.id,
      ),
    ).toBe(false);

    for (const ancho of [390, 320]) {
      await page.setViewportSize({ width: ancho, height: 800 });
      await page.goto("/gobierno/contrataciones/reporte");
      await expect(page.getByRole("heading", { level: 1, name: "Reporte de contrataciones" })).toBeVisible();
      await expect(page.getByRole("heading", { level: 2, name: "Distribución" })).toBeVisible();
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
