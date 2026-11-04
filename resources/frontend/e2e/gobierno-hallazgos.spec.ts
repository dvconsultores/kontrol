import { expect, sesionApi, test } from "./helpers/sesion";
import {
  ANIO,
  API,
  PDF,
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

const RESPONSABLE_HALLAZGOS = [
  ...RESPONSABLE_ESTRUCTURA,
  "gobierno_cargos:view",
  "gobierno_cargos:edit",
  "gobierno_cargos:publish",
  "gobierno_auditoria:view",
  "gobierno_auditoria:sample",
  "gobierno_hallazgos:view",
  "gobierno_hallazgos:manage",
  "gobierno_hallazgos:verify",
  "documentos:view",
  "documentos:create",
];

const VERIFICADOR = [
  "organization:view",
  "gobierno_hallazgos:view",
  "gobierno_hallazgos:verify",
  "documentos:view",
];

async function pulsarYEsperar(page: Page, boton: Locator, metodo: string, ruta: RegExp): Promise<void> {
  await cerrarNotificaciones(page);
  const [resp] = await Promise.all([
    page.waitForResponse((r) => r.request().method() === metodo && ruta.test(new URL(r.url()).pathname), { timeout: 60_000 }),
    boton.click(),
  ]);
  expect(es2xx(resp.status()), await resp.text()).toBe(true);
}

async function adjuntarPdfDesdeUi(
  page: Page,
  region: Locator,
  tipoNombre: string,
) {
  await region.getByLabel("Tipo documental del archivo").selectOption({ label: tipoNombre });
  await region.getByLabel(/^Archivo/).setInputFiles({
    name: "documento.pdf",
    mimeType: "application/pdf",
    buffer: PDF,
  });

  const [vinculoResp] = await Promise.all([
    page.waitForResponse(
      (r) =>
        /\/api\/v1\/documentos\/[^/]+\/vinculos$/.test(new URL(r.url()).pathname) &&
        r.request().method() === "POST",
      { timeout: 60_000 },
    ),
    region.getByRole("button", { name: "Adjuntar" }).click(),
  ]);
  expect(es2xx(vinculoResp.status())).toBe(true);
  await expect(page.getByText("Documento adjuntado")).toBeVisible({ timeout: 30_000 });
  await cerrarNotificaciones(page);
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

  return { mundo, tipo, dirId: dir.id };
}

test.describe("Gobierno · Hallazgos y acciones correctivas (CTL-06)", () => {
  test("CTL6-E2E-01 · ciclo", async ({ page, request, browser }) => {
    test.setTimeout(240_000);

    // 1. Mundo base y muestra por API
    const { mundo, tipo } = await mundoConActividad(request);

    const muestraResp = await request.post(`${API}/gobierno/auditoria/muestras`, {
      headers: mundo.headers,
      data: {
        titulo: "Muestra para hallazgo",
        criterio: "Eventos de cargos del ente",
        justificacion: "Base del hallazgo de prueba",
        metodo: "TODAS",
        filtros: { proceso: "ORG-03" },
      },
    });
    expect(muestraResp.status()).toBe(201);
    const muestra = await muestraResp.json();
    const muestraId = muestra.id;

    await entrarEnGobierno(page, mundo.username, mundo.codigo, "/gobierno/auditoria");
    await page.goto(`/gobierno/auditoria/muestras/${muestraId}`);

    await page.getByRole("button", { name: "Registrar hallazgo" }).click();
    await expect(page).toHaveURL(
      new RegExp(`/gobierno/hallazgos/nuevo\\?muestra=${muestraId}$`),
    );

    // 2. Formulario de registro
    await expect(
      page.getByRole("radio", { name: "Muestra de auditoría" }),
    ).toBeChecked();

    await page
      .getByRole("checkbox", { name: /^Partida .+/ })
      .first()
      .check();

    await page.getByLabel("Título").fill("Hallazgo de prueba de ciclo completo");
    await page.getByLabel("Condición").fill("Condición detectada en la muestra");
    await page.getByLabel("Criterio").fill("Criterio normativo aplicable");
    await page.getByLabel("Causa").fill("Causa raíz identificada en la revisión");
    await page.getByLabel("Efecto").fill("Efecto material sobre el proceso evaluado");
    await page.getByLabel("Riesgo").selectOption({ label: "Alto" });

    await page.getByRole("button", { name: "Registrar hallazgo" }).click();
    await expect(page).toHaveURL(/\/gobierno\/hallazgos\/[^/]+$/);
    const h1 = page.getByRole("heading", {
      level: 1,
      name: /^Hallazgo HA-\d{4}-\d{4}$/,
    });
    await expect(h1).toBeVisible();
    const codigoHallazgo = ((await h1.textContent()) ?? "").replace("Hallazgo ", "");

    // 3. Recomendación y acción correctiva
    await page
      .getByLabel("Recomendación")
      .fill("Implementar controles preventivos y correctivos");
    await pulsarYEsperar(
      page,
      page.getByRole("button", { name: "Añadir recomendación" }),
      "POST",
      /\/api\/v1\/gobierno\/hallazgos\/[^/]+\/recomendaciones$/,
    );

    await page
      .getByLabel("Acción para la recomendación 1")
      .fill("Aplicar controles de revisión periódica");

    const selectCargo = page.getByLabel("Cargo responsable de la recomendación 1");
    await expect(selectCargo.locator("option", { hasText: "DIR-ADM" })).toHaveCount(1);
    const valor = await selectCargo.locator("option", { hasText: "DIR-ADM" }).getAttribute("value");
    await selectCargo.selectOption(valor ?? "");

    await page
      .getByLabel("Fecha objetivo de la recomendación 1")
      .fill(
        new Date(Date.now() + 30 * 24 * 60 * 60 * 1000)
          .toISOString()
          .slice(0, 10),
      );
    await pulsarYEsperar(
      page,
      page.getByRole("button", { name: "Añadir acción correctiva" }),
      "POST",
      /\/api\/v1\/gobierno\/hallazgos\/[^/]+\/acciones$/,
    );

    // 4. Registrar plan e iniciar ejecución
    await pulsarYEsperar(
      page,
      page.getByRole("button", { name: "Registrar plan" }),
      "POST",
      /\/api\/v1\/gobierno\/hallazgos\/[^/]+\/plan$/,
    );
    await pulsarYEsperar(
      page,
      page.getByRole("button", { name: "Iniciar ejecución" }),
      "POST",
      /\/api\/v1\/gobierno\/hallazgos\/[^/]+\/ejecucion$/,
    );

    // 5. Evidencia y avance
    const regionEvidencia = page.locator("section").filter({
      has: page.getByRole("heading", { name: "Evidencia de la acción 1" }),
    });
    await adjuntarPdfDesdeUi(page, regionEvidencia, tipo.name);

    await page.getByLabel("Nota del avance de la acción 1").fill("Avance completado al 100%");
    await page
      .getByLabel("Porcentaje de avance de la acción 1")
      .fill("100");
    await page
      .getByLabel("Documento de evidencia de la acción 1")
      .selectOption({ index: 1 });
    await pulsarYEsperar(
      page,
      page.getByRole("button", { name: "Registrar avance" }),
      "POST",
      /\/api\/v1\/gobierno\/hallazgos\/[^/]+\/acciones\/[^/]+\/avances$/,
    );

    // 6. Presentar a verificación y error con el mismo usuario
    await pulsarYEsperar(
      page,
      page.getByRole("button", { name: "Presentar a verificación" }),
      "POST",
      /\/api\/v1\/gobierno\/hallazgos\/[^/]+\/presentar$/,
    );

    await page.getByRole("button", { name: "Verificar y cerrar" }).click();
    await page.getByLabel("Nota de verificación").fill("Intento de verificación inválida");
    await page.getByRole("button", { name: "Confirmar verificación" }).click();

    await expect(page.getByRole("alert")).toContainText("no puede verificarlo");

    // 7. Segundo usuario verificador
    const sessionAdmin = await sesionApi("admintenant", { tenant: TENANT });
    const verificador = await crearUsuario(
      request,
      sessionAdmin.headers,
      VERIFICADOR,
      mundo.companyId,
    );

    const context2 = await browser.newContext();
    const page2 = await context2.newPage();

    await entrarEnGobierno(
      page2,
      verificador.username,
      mundo.codigo,
      "/gobierno/hallazgos",
    );

    await page2
      .getByRole("link", { name: `Abrir el hallazgo ${codigoHallazgo}` })
      .click();

    await page2.getByRole("button", { name: "Verificar y cerrar" }).click();
    await page2.getByLabel("Nota de verificación").fill("Verificación satisfactoria");
    await pulsarYEsperar(
      page2,
      page2.getByRole("button", { name: "Confirmar verificación" }),
      "POST",
      /\/api\/v1\/gobierno\/hallazgos\/[^/]+\/verificar$/,
    );

    await expect(page2.locator('[aria-current="step"]')).toHaveText("Cerrado");
    await expect(
      page2.getByRole("region", { name: `Historia del hallazgo ${codigoHallazgo}` }),
    ).toContainText("Verificado y cerrado");

    await context2.close();
  });
});
