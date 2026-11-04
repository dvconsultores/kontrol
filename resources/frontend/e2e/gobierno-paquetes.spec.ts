import { createHash } from "node:crypto";
import fs from "node:fs/promises";
import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "./helpers/sesion";
import {
  API,
  RESPONSABLE_ESTRUCTURA,
  cerrarNotificaciones,
  crearTipoDocumental,
  entrarEnGobierno,
  enteActivo,
  es2xx,
  prepararMundo,
  crearUsuario,
  TENANT,
} from "./helpers/gobierno";
import { sesionApi } from "./helpers/sesion";
import type { Locator, Page } from "@playwright/test";

const PERMISOS_PAQUETES = [
  ...RESPONSABLE_ESTRUCTURA,
  "gobierno_auditoria:view",
  "gobierno_auditoria:sample",
  "gobierno_paquetes:view",
  "gobierno_paquetes:generate",
  "documentos:download",
];
const SOLO_CONSULTA = ["organization:view", "gobierno_auditoria:view", "gobierno_paquetes:view"];
const SIN_PAQUETES = ["organization:view", "gobierno_auditoria:view"];
const WCAG = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"];

async function pulsarYEsperar(
  page: Page,
  boton: Locator,
  metodo: string,
  ruta: RegExp,
): Promise<void> {
  await cerrarNotificaciones(page);
  const [resp] = await Promise.all([
    page.waitForResponse(
      (r) => r.request().method() === metodo && ruta.test(new URL(r.url()).pathname),
      { timeout: 60_000 },
    ),
    boton.click(),
  ]);
  expect(es2xx(resp.status()), await resp.text()).toBe(true);
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

async function mundoConMuestra(request: import("@playwright/test").APIRequestContext) {
  const mundo = await prepararMundo(request, PERMISOS_PAQUETES);
  const tipo = await crearTipoDocumental(request, mundo.headers, mundo.companyId);
  await enteActivo(request, mundo.headers, mundo.companyId, tipo.id);
  const r = await request.post(`${API}/gobierno/auditoria/muestras`, {
    headers: mundo.headers,
    data: {
      titulo: "Muestra para paquete",
      criterio: "Eventos del ente",
      justificacion: "Paquete para control fiscal externo",
      metodo: "TODAS",
      filtros: { proceso: "ORG-01" },
    },
  });
  expect(r.status(), await r.text()).toBe(201);
  const muestra = await r.json();
  return { mundo, muestraId: muestra.id, muestraCodigo: muestra.codigo };
}

async function generarDesdeUi(page: Page, muestraId: string): Promise<string> {
  await page.goto(`/gobierno/auditoria/muestras/${muestraId}`);
  await cerrarNotificaciones(page);
  await page.getByRole("button", { name: "Generar paquete de auditoría" }).click();
  await expect(
    page.getByRole("heading", { level: 2, name: "Contenido del paquete" }),
  ).toBeVisible({ timeout: 30_000 });
  await expect(
    page.getByRole("region", { name: "Tabla de documentos del paquete" }),
  ).toContainText("Incluido");
  await page.getByLabel(/^Propósito/).fill("Revisión de control fiscal externo del ejercicio");
  await pulsarYEsperar(
    page,
    page.getByRole("button", { name: "Generar paquete" }),
    "POST",
    /\/api\/v1\/gobierno\/auditoria\/muestras\/[^/]+\/paquetes$/,
  );
  const h1 = page.getByRole("heading", {
    level: 1,
    name: /^Paquete PA-\d{4}-\d{4}$/,
  });
  await expect(h1).toBeVisible({ timeout: 30_000 });
  return ((await h1.textContent()) ?? "").replace("Paquete ", "");
}

test.describe("Gobierno · Paquete de auditoría exportable (DOC-08)", () => {
  test("DOC8-E2E-01 · flujo completo de generación, descarga, verificación e historia", async ({
    page,
    request,
  }) => {
    test.setTimeout(240_000);

    const { mundo, muestraId } = await mundoConMuestra(request);
    await entrarEnGobierno(page, mundo.username, mundo.codigo, "/gobierno/auditoria");

    const codigo = await generarDesdeUi(page, muestraId);
    await expect(page.getByText("Huella del paquete (SHA-256)")).toBeVisible();

    await cerrarNotificaciones(page);
    const [descarga] = await Promise.all([
      page.waitForEvent("download"),
      page.getByRole("button", { name: "Descargar paquete" }).click(),
    ]);
    expect(descarga.suggestedFilename()).toBe(`paquete-${codigo}.zip`);
    const ruta = await descarga.path();
    expect(ruta).not.toBeNull();
    const zip = await fs.readFile(ruta as string);
    const huella = createHash("sha256").update(zip).digest("hex");
    await expect(page.getByText(huella)).toBeVisible();

    await cerrarNotificaciones(page);
    const [descargaManifiesto] = await Promise.all([
      page.waitForEvent("download"),
      page.getByRole("button", { name: "Descargar manifiesto" }).click(),
    ]);
    expect(descargaManifiesto.suggestedFilename()).toBe(`manifiesto-${codigo}.json`);
    const rutaManifiesto = await descargaManifiesto.path();
    expect(rutaManifiesto).not.toBeNull();
    const manifiesto = JSON.parse(await fs.readFile(rutaManifiesto as string, "utf8")) as {
      formato: string;
      paquete: { codigo: string };
    };
    expect(manifiesto.formato).toBe("kontrol-gobierno-paquete-auditoria");
    expect(manifiesto.paquete.codigo).toBe(codigo);

    await cerrarNotificaciones(page);
    await page.locator('nav a[href="/gobierno/paquetes"]').first().click();
    await page.waitForURL((u) => u.pathname === "/gobierno/paquetes");
    await expect(
      page.getByRole("link", { name: `Abrir el paquete ${codigo}` }),
    ).toBeVisible();

    await page
      .getByLabel(/^Archivo del paquete/)
      .setInputFiles({ name: "paquete.zip", mimeType: "application/zip", buffer: zip });
    await pulsarYEsperar(
      page,
      page.getByRole("button", { name: "Verificar" }),
      "POST",
      /\/api\/v1\/gobierno\/paquetes\/verificar$/,
    );
    const estado = page.getByRole("status");
    await expect(estado).toContainText("Resultado: Válido");
    await expect(estado).toContainText("idéntica byte a byte");

    const marca = Buffer.from("%PDF-1.4");
    const pos = zip.indexOf(marca);
    expect(pos).toBeGreaterThan(0);
    const alterado = Buffer.from(zip);
    alterado[pos + 1] = alterado[pos + 1] ^ 0x01;
    await page
      .getByLabel(/^Archivo del paquete/)
      .setInputFiles({ name: "paquete.zip", mimeType: "application/zip", buffer: alterado });
    await pulsarYEsperar(
      page,
      page.getByRole("button", { name: "Verificar" }),
      "POST",
      /\/api\/v1\/gobierno\/paquetes\/verificar$/,
    );
    await expect(estado).toContainText("Resultado: Inválido");
    await expect(estado).toContainText("Archivo alterado");

    await page.getByRole("link", { name: `Abrir el paquete ${codigo}` }).click();
    await expect(
      page.getByRole("heading", { level: 1, name: `Paquete ${codigo}` }),
    ).toBeVisible();
    await expect(
      page
        .locator("section")
        .filter({ has: page.getByRole("heading", { name: "Verificaciones" }) }),
    ).toContainText("copia idéntica");
  });

  test("DOC8-E2E-02 · roles y permisos", async ({ page, browser, request }) => {
    test.setTimeout(180_000);

    const { mundo, muestraId } = await mundoConMuestra(request);
    const adminHeaders = (await sesionApi("admintenant", { tenant: TENANT })).headers;

    const consulta = await crearUsuario(
      request,
      adminHeaders,
      SOLO_CONSULTA,
      mundo.companyId,
    );
    await entrarEnGobierno(page, consulta.username, mundo.codigo, "/gobierno/paquetes");
    await expect(
      page.getByRole("heading", { name: "Verificar un paquete" }),
    ).toBeVisible();
    await page.goto(`/gobierno/auditoria/muestras/${muestraId}`);
    await expect(page.getByRole("heading", { level: 1, name: /^Muestra/ })).toBeVisible();
    await expect(
      page.getByRole("button", { name: "Generar paquete de auditoría" }),
    ).toHaveCount(0);

    const sinPaquetes = await crearUsuario(
      request,
      adminHeaders,
      SIN_PAQUETES,
      mundo.companyId,
    );
    const contexto = await browser.newContext();
    const page2 = await contexto.newPage();
    await entrarEnGobierno(page2, sinPaquetes.username, mundo.codigo, "/gobierno/auditoria");
    await expect(page2.locator('nav a[href="/gobierno/paquetes"]')).toHaveCount(0);
    await page2.goto("/gobierno/paquetes");
    await expect(page2.getByRole("heading", { name: "Verificar un paquete" })).toHaveCount(0);
    await contexto.close();
  });

  test("DOC8-E2E-03 · accesibilidad y responsive", async ({ page, request }) => {
    test.setTimeout(240_000);

    const { mundo, muestraId } = await mundoConMuestra(request);
    await entrarEnGobierno(page, mundo.username, mundo.codigo, "/gobierno/auditoria");
    const codigo = await generarDesdeUi(page, muestraId);
    const urlPaquete = page.url();

    for (const viewport of [
      { width: 1280, height: 900 },
      { width: 768, height: 900 },
      { width: 320, height: 900 },
    ]) {
      await page.setViewportSize(viewport);

      await page.goto(urlPaquete);
      await expect(
        page.getByRole("heading", { level: 1, name: `Paquete ${codigo}` }),
      ).toBeVisible();
      await sinViolacionesSerias(page, "Ficha del paquete");

      await page.goto("/gobierno/paquetes");
      await expect(
        page.getByRole("heading", { level: 1, name: "Paquetes de auditoría" }),
      ).toBeVisible();
      await sinViolacionesSerias(page, "Paquetes de auditoría");

      await page.goto(`/gobierno/auditoria/muestras/${muestraId}/paquete`);
      await expect(
        page.getByRole("heading", { level: 2, name: "Contenido del paquete" }),
      ).toBeVisible();
      await sinViolacionesSerias(page, "Generar paquete");
    }
  });
});
