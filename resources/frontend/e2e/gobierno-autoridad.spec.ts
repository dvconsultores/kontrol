import fs from "node:fs/promises";
import AxeBuilder from "@axe-core/playwright";
import { expect, sesionApi, test } from "./helpers/sesion";
import {
  ANIO,
  API,
  RESPONSABLE_ESTRUCTURA,
  TENANT,
  adjuntarDocumentoApi,
  cargoVigenteApi,
  cerrarNotificaciones,
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

const RESPONSABLE_AUTORIDAD = [
  ...RESPONSABLE_ESTRUCTURA,
  "gobierno_cargos:view",
  "gobierno_cargos:edit",
  "gobierno_cargos:publish",
  "gobierno_autoridad:view",
];

const CONSULTA_AUTORIDAD = ["organization:view", "gobierno_autoridad:view"];

const WCAG = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"];

function ddmmaaaa(iso: string): string {
  const [year, month, day] = iso.split("-");
  return `${day}/${month}/${year}`;
}

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

async function mundoConMatriz(request: APIRequestContext) {
  const mundo = await prepararMundo(request, RESPONSABLE_AUTORIDAD);
  const tipo = await crearTipoDocumental(request, mundo.headers, mundo.companyId);
  await enteActivo(request, mundo.headers, mundo.companyId, tipo.id);
  const { estructuraId, despId, da01Id } = await estructuraVigenteApi(
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

  const altaJef = await request.post(
    `${API}/gobierno/estructuras/${ANIO}/cargos`,
    {
      headers: mundo.headers,
      data: {
        codigo: "JEF-TES",
        denominacion: "Jefe de Tesorería",
        unidad_id: despId,
        vigente_desde: `${ANIO}-01-01`,
      },
    },
  );
  expect(altaJef.status()).toBe(201);
  const jef = await altaJef.json();

  const competenciaJef = await request.post(
    `${API}/gobierno/estructuras/${ANIO}/cargos/${jef.id}/competencias`,
    {
      headers: { ...mundo.headers, "If-Match": '"1"' },
      data: {
        accion: "PAGAR",
        materia: "TESORERIA",
        tipo_limite: "SIN_LIMITE",
      },
    },
  );
  expect(competenciaJef.status()).toBe(201);

  await adjuntarDocumentoApi(
    request,
    mundo.headers,
    mundo.companyId,
    tipo.id,
    "GovernmentPosition",
    jef.id,
  );

  const activacionJef = await request.post(
    `${API}/gobierno/estructuras/${ANIO}/cargos/${jef.id}/activar`,
    {
      headers: { ...mundo.headers, "If-Match": '"2"' },
    },
  );
  expect(activacionJef.status()).toBe(200);

  return { mundo, dirId: dir.id, jefId: jef.id, estructuraId, despId, da01Id };
}

test.describe("Gobierno · Matriz de autoridad (ORG-07)", () => {
  test("ORG7-E2E-01 · ciclo de consulta", async ({ page, request }) => {
    test.setTimeout(180_000);
    const { mundo, dirId } = await mundoConMatriz(request);
    const hoy = hoyCaracas();
    const resumenDos = `2 autorizaciones de 2 cargos al ${ddmmaaaa(hoy)}`;
    const resumenUno = `1 autorización de 1 cargo al ${ddmmaaaa(hoy)}`;

    await entrarEnGobierno(page, mundo.username, mundo.codigo, "/gobierno/autoridad");

    await expect(page.getByRole("heading", { level: 1, name: "Matriz de autoridad" })).toBeVisible();
    await expect(page.getByText(resumenDos)).toBeVisible();

    const filaDir = page.getByRole("row", { name: /DIR-ADM/ });
    await expect(filaDir).toContainText("Hasta 50.000,00 USD por operación");
    await expect(filaDir).toContainText("Acto de prueba");

    await page.getByLabel(/^Acción/).selectOption("PAGAR");
    await expect(page.getByText(resumenUno)).toBeVisible();
    await expect(page.getByRole("row", { name: /DIR-ADM/ })).toHaveCount(0);
    await expect(page.getByRole("row", { name: /JEF-TES/ })).toBeVisible();

    await page.getByRole("button", { name: "Limpiar filtros" }).click();
    await expect(page.getByText(resumenDos)).toBeVisible();

    await page.getByLabel(/^Unidad/).selectOption({ label: "DESP · Despacho del Alcalde" });
    await expect(page.getByText(resumenDos)).toBeVisible();
    await expect(page.getByRole("row", { name: /DIR-ADM/ })).toBeVisible();
    await expect(page.getByRole("row", { name: /JEF-TES/ })).toBeVisible();

    await cerrarNotificaciones(page);
    await page.getByRole("button", { name: `Ver el detalle de ${"DIR-ADM"}` }).click();
    await expect(page.getByRole("heading", { name: `Detalle de DIR-ADM · Cargo DIR-ADM` })).toBeVisible();
    await expect(page.getByText("Usada para esta fecha")).toBeVisible();
    await expect(page.getByRole("link", { name: "Abrir el cargo" })).toHaveAttribute(
      "href",
      `/gobierno/cargos/${ANIO}/${dirId}`,
    );
    await page.getByRole("button", { name: "Cerrar el detalle" }).click();
    await expect(page.getByRole("heading", { name: `Detalle de DIR-ADM · Cargo DIR-ADM` })).toHaveCount(0);

    await cerrarNotificaciones(page);
    const pendienteExportar = page.waitForEvent("download");
    await page.getByRole("button", { name: "Exportar CSV" }).click();
    const descarga = await pendienteExportar;
    expect(descarga.suggestedFilename()).toBe(`autoridad-${ANIO}-${hoy}.csv`);
    const contenido = await fs.readFile(await descarga.path(), "utf8");
    expect(contenido.startsWith("fecha_corte,codigo_unidad,unidad,ruta_unidad,codigo_cargo")).toBe(true);
  });

  test("ORG7-E2E-02 · a la fecha", async ({ page, request }) => {
    test.setTimeout(180_000);
    const { mundo, jefId } = await mundoConMatriz(request);
    const hoy = hoyCaracas();
    const esPrimeroDeEnero = hoy === `${ANIO}-01-01`;
    if (esPrimeroDeEnero) {
      test.info().annotations.push({
        type: "issue",
        description: "Hoy es 1 de enero; se comprueba solo la vista a la fecha.",
      });
    }

    const desactivacion = await request.post(
      `${API}/gobierno/estructuras/${ANIO}/cargos/${jefId}/desactivar`,
      {
        headers: { ...mundo.headers, "If-Match": '"3"' },
        data: { fecha: `${ANIO}-01-01`, motivo: "Cargo suprimido" },
      },
    );
    expect(desactivacion.status()).toBe(200);

    await entrarEnGobierno(page, mundo.username, mundo.codigo, "/gobierno/autoridad");

    if (!esPrimeroDeEnero) {
      await expect(page.getByText(`1 autorización de 1 cargo al ${ddmmaaaa(hoy)}`)).toBeVisible();
      await expect(page.getByRole("row", { name: /DIR-ADM/ })).toBeVisible();
      await expect(page.getByRole("row", { name: /JEF-TES/ })).toHaveCount(0);
    }

    await page.getByLabel(/^A la fecha/).fill(`${ANIO}-01-01`);
    await expect(page.getByText(`2 autorizaciones de 2 cargos al 01/01/${ANIO}`)).toBeVisible();
    await expect(page.getByRole("row", { name: /JEF-TES/ })).toContainText("Inactivo");
    await expect(page.getByRole("row", { name: /JEF-TES/ })).toContainText(`01/01/${ANIO} – 01/01/${ANIO}`);
  });

  test("ORG7-E2E-03 · permisos", async ({ page, request }) => {
    test.setTimeout(180_000);
    const { mundo } = await mundoConMatriz(request);
    const adminTenant = (await sesionApi("admintenant", { tenant: TENANT })).headers;
    const soloConsulta = await crearUsuario(
      request,
      adminTenant,
      ["organization:view", "gobierno_autoridad:view"],
      mundo.companyId,
    );
    await entrarEnGobierno(page, soloConsulta.username, mundo.codigo, "/gobierno/autoridad");
    await expect(page.getByRole("heading", { level: 1, name: "Matriz de autoridad" })).toBeVisible();
    await cerrarNotificaciones(page);
    await page.getByRole("button", { name: `Ver el detalle de ${"DIR-ADM"}` }).click();
    await expect(page.getByText("Usada para esta fecha")).toBeVisible();
    await expect(page.getByRole("link", { name: "Abrir el cargo" })).toHaveCount(0);
    await expect(page.locator('nav a[href="/gobierno/cargos"]')).toHaveCount(0);

    const otroUsuario = await crearUsuario(
      request,
      adminTenant,
      ["organization:view", "gobierno_estructura:view"],
      mundo.companyId,
    );
    await page.context().clearCookies();
    await entrarComoUsuario(page, otroUsuario.username, {
      tenant: TENANT,
      ruta: "/",
    });
    await activarEmpresa(page, mundo.codigo);
    await expect(page.locator('nav a[href="/gobierno/autoridad"]')).toHaveCount(0);
    await expect(page.locator('nav a[href="/gobierno/estructura"]')).toBeVisible();
  });

  test("ORG7-E2E-04 · otro ente", async ({ request }) => {
    test.setTimeout(180_000);
    const { dirId } = await mundoConMatriz(request);
    const mundoB = await prepararMundo(request, CONSULTA_AUTORIDAD);

    const respuestaCargo = await request.get(
      `${API}/gobierno/autoridad/${ANIO}/cargos/${dirId}`,
      { headers: mundoB.headers },
    );
    expect(respuestaCargo.status()).toBe(404);
    await expect(respuestaCargo.json()).resolves.toMatchObject({
      code: "GOV_STRUCTURE_NOT_FOUND",
    });
    expect(JSON.stringify(await respuestaCargo.json())).not.toContain("DIR-ADM");

    const respuestaMatriz = await request.get(`${API}/gobierno/autoridad/${ANIO}`, {
      headers: mundoB.headers,
    });
    expect(respuestaMatriz.status()).toBe(404);
    await expect(respuestaMatriz.json()).resolves.toMatchObject({
      code: "GOV_STRUCTURE_NOT_FOUND",
    });
  });

  test("ORG7-E2E-05 · accesibilidad", async ({ page, request }) => {
    test.setTimeout(180_000);
    const { mundo } = await mundoConMatriz(request);
    await entrarEnGobierno(page, mundo.username, mundo.codigo, "/gobierno/autoridad");
    await cerrarNotificaciones(page);
    await page.getByRole("button", { name: `Ver el detalle de ${"DIR-ADM"}` }).click();
    await expect(page.getByText("Usada para esta fecha")).toBeVisible();

    for (const viewport of [
      { width: 1280, height: 768 },
      { width: 768, height: 900 },
      { width: 320, height: 568 },
    ]) {
      await page.setViewportSize(viewport);
      await sinViolacionesSerias(page, `Matriz de autoridad ${viewport.width}px`);
    }
  });
});
