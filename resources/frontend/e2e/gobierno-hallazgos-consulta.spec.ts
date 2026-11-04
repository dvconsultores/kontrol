import fs from "node:fs/promises";
import AxeBuilder from "@axe-core/playwright";
import { expect, sesionApi, test } from "./helpers/sesion";
import {
  ANIO,
  API,
  RESPONSABLE_ESTRUCTURA,
  TENANT,
  cargoVigenteApi,
  crearTipoDocumental,
  crearUsuario,
  enteActivo,
  entrarEnGobierno,
  estructuraVigenteApi,
  prepararMundo,
} from "./helpers/gobierno";
import { activarEmpresa } from "./helpers/empresa";
import { entrarComoUsuario } from "./helpers/sesion";
import type { APIRequestContext, Page } from "@playwright/test";

const RESPONSABLE_HALLAZGOS = [
  ...RESPONSABLE_ESTRUCTURA,
  "gobierno_cargos:view",
  "gobierno_cargos:edit",
  "gobierno_cargos:publish",
  "gobierno_auditoria:view",
  "gobierno_auditoria:sample",
  "gobierno_hallazgos:view",
  "gobierno_hallazgos:manage",
  "documentos:view",
  "documentos:create",
];

const CONSULTA = ["organization:view", "gobierno_hallazgos:view"];

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

async function mundoConActividad(request: APIRequestContext) {
  const mundo = await prepararMundo(request, RESPONSABLE_HALLAZGOS);
  const tipo = await crearTipoDocumental(request, mundo.headers, mundo.companyId);
  await enteActivo(request, mundo.headers, mundo.companyId, tipo.id);
  const { da01Id } = await estructuraVigenteApi(
    request,
    mundo.headers,
    mundo.companyId,
    tipo.id,
    ANIO,
  );
  const dir = await cargoVigenteApi(
    request,
    mundo.headers,
    mundo.companyId,
    tipo.id,
    ANIO,
    da01Id,
    "DIR-ADM",
  );

  return { mundo, dirId: dir.id };
}

async function crearHallazgoIndependiente(request: APIRequestContext, headers: Record<string, string>) {
  const respuesta = await request.post(`${API}/gobierno/hallazgos`, {
    headers,
    data: {
      titulo: "Hallazgo de prueba para consulta",
      condicion: "Condición de prueba del hallazgo",
      criterio: "Criterio de prueba del hallazgo",
      causa: "Causa de prueba del hallazgo",
      efecto: "Efecto de prueba del hallazgo con longitud suficiente",
      riesgo: "MEDIO",
      origen: "INDEPENDIENTE",
      origen_descripcion: "Actuación fiscal externa de prueba",
    },
  });

  expect(respuesta.status()).toBe(201);
  return respuesta.json();
}

test.describe("Gobierno · Hallazgos (CTL-06) · consulta", () => {
  test("CTL6-E2E-02 · menú y listado", async ({ page, request }) => {
    test.setTimeout(240_000);
    const { mundo } = await mundoConActividad(request);

    const hallazgo = await crearHallazgoIndependiente(request, mundo.headers);

    await entrarEnGobierno(page, mundo.username, mundo.codigo, "/gobierno/hallazgos");

    await expect(
      page.getByRole("heading", { level: 1, name: "Hallazgos y acciones correctivas" }),
    ).toBeVisible();

    const tabla = page.getByRole("region", { name: "Tabla de hallazgos" });
    await expect(tabla).toBeVisible();
    await expect(tabla.getByText(hallazgo.codigo)).toBeVisible();

    await expect(page.getByText("Abiertos")).toBeVisible();
    const resumenAbiertos = page.locator("text=Abiertos").locator("..");
    await expect(resumenAbiertos).toContainText(/[1-9]\d*/);

    const pendienteExportar = page.waitForEvent("download");
    await page.getByRole("button", { name: "Exportar plan (CSV)" }).click();
    const descarga = await pendienteExportar;
    expect(descarga.suggestedFilename().startsWith("plan-acciones-")).toBe(true);
    const contenido = await fs.readFile(await descarga.path(), "utf8");
    expect(contenido.startsWith("codigo,titulo,riesgo")).toBe(true);
  });

  test("CTL6-E2E-03 · permisos", async ({ browser, request }) => {
    test.setTimeout(180_000);
    const adminHeaders = (await sesionApi("admintenant", { tenant: TENANT })).headers;
    const mundo = await prepararMundo(request, RESPONSABLE_HALLAZGOS);
    const tipo = await crearTipoDocumental(request, mundo.headers, mundo.companyId);
    await enteActivo(request, mundo.headers, mundo.companyId, tipo.id);
    const { da01Id } = await estructuraVigenteApi(
      request,
      mundo.headers,
      mundo.companyId,
      tipo.id,
      ANIO,
    );
    await cargoVigenteApi(
      request,
      mundo.headers,
      mundo.companyId,
      tipo.id,
      ANIO,
      da01Id,
      "DIR-ADM",
    );

    const usuarioConsulta = await crearUsuario(
      request,
      adminHeaders,
      CONSULTA,
      mundo.companyId,
    );
    const ctxConsulta = await browser.newContext();
    const pConsulta = await ctxConsulta.newPage();
    await entrarComoUsuario(
      pConsulta,
      usuarioConsulta.username,
      { tenant: TENANT, ruta: "/" },
    );
    await activarEmpresa(pConsulta, mundo.codigo);
    await pConsulta.goto("/gobierno/hallazgos");

    await expect(
      pConsulta.getByRole("heading", { level: 1, name: "Hallazgos y acciones correctivas" }),
    ).toBeVisible();

    await expect(
      pConsulta.getByRole("button", { name: "Registrar hallazgo" }),
    ).toHaveCount(0);

    await ctxConsulta.close();

    const usuarioSoloOrg = await crearUsuario(
      request,
      adminHeaders,
      ["organization:view"],
      mundo.companyId,
    );
    const ctxSoloOrg = await browser.newContext();
    const pSoloOrg = await ctxSoloOrg.newPage();
    await entrarComoUsuario(
      pSoloOrg,
      usuarioSoloOrg.username,
      { tenant: TENANT, ruta: "/" },
    );
    await activarEmpresa(pSoloOrg, mundo.codigo);

    await expect(
      pSoloOrg.locator('nav a[href="/gobierno/hallazgos"]'),
    ).toHaveCount(0);

    await ctxSoloOrg.close();
  });

  test("CTL6-E2E-04 · accesibilidad", async ({ page, request }) => {
    test.setTimeout(240_000);
    const { mundo } = await mundoConActividad(request);

    const hallazgo = await crearHallazgoIndependiente(request, mundo.headers);

    const tamanos = [
      { width: 1280, height: 900 },
      { width: 768, height: 900 },
      { width: 320, height: 900 },
    ];

    for (const tamano of tamanos) {
      await page.setViewportSize(tamano);
      await entrarEnGobierno(page, mundo.username, mundo.codigo, "/gobierno/hallazgos");
      await expect(page.getByRole("heading", { level: 1, name: "Hallazgos y acciones correctivas" })).toBeVisible();
      await sinViolacionesSerias(page, "Listado de hallazgos");

      await page.goto(`/gobierno/hallazgos/${hallazgo.id}`);
      await expect(page.getByRole("heading", { level: 1, name: /^Hallazgo HA-/ })).toBeVisible();
      await sinViolacionesSerias(page, `Ficha del hallazgo ${hallazgo.codigo}`);
    }
  });
});
