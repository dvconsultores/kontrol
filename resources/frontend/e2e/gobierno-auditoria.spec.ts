import fs from "node:fs/promises";
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
import { activarEmpresa } from "./helpers/empresa";
import { entrarComoUsuario } from "./helpers/sesion";
import type { APIRequestContext, Page } from "@playwright/test";

const RESPONSABLE_AUDITORIA = [
  ...RESPONSABLE_ESTRUCTURA,
  "gobierno_cargos:view",
  "gobierno_cargos:edit",
  "gobierno_cargos:publish",
  "gobierno_auditoria:view",
  "gobierno_auditoria:sample",
];

const CONSULTA_AUDITORIA = ["organization:view", "gobierno_auditoria:view"];

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
  const mundo = await prepararMundo(request, RESPONSABLE_AUDITORIA);
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

test.describe("Gobierno · Auditoría institucional (CTL-04)", () => {
  test("CTL4-E2E-01 · ciclo", async ({ page, request }) => {
    test.setTimeout(180_000);
    const { mundo } = await mundoConActividad(request);

    await entrarEnGobierno(page, mundo.username, mundo.codigo, "/gobierno/auditoria");

    await expect(page.getByRole("heading", { level: 1, name: "Auditoría institucional" })).toBeVisible();
    await expect(page.getByRole("note")).toContainText("Vista de solo lectura");

    await page.getByLabel(/^Proceso/).selectOption("ORG-03 · Cargos y competencias");
    await expect(page.getByRole("region", { name: "Población de eventos de Gobierno" })
      .getByRole("row")).not.toHaveCount(0);

    await page.getByRole("button", { name: /Ver evidencia del evento/ }).first().click();
    await expect(page.getByRole("heading", { level: 2, name: "Evidencia del evento" })).toBeVisible();
    await expect(page.getByRole("link", { name: "Ir al objeto" })).toHaveAttribute(
      "href",
      new RegExp(`^/gobierno/cargos/${ANIO}/`),
    );
    await page.getByRole("button", { name: "Cerrar la evidencia" }).click();
    await expect(page.getByRole("heading", { level: 2, name: "Evidencia del evento" })).toHaveCount(0);

    await cerrarNotificaciones(page);
    await page.getByRole("button", { name: "Registrar muestra" }).click();
    const regionRegistro = page.getByRole("region", { name: "Registrar muestra" });
    await expect(regionRegistro.getByRole("heading", { level: 2, name: "Registrar muestra" })).toBeVisible();
    await regionRegistro.getByLabel("Título").fill("Muestra aleatoria de prueba");
    await regionRegistro.getByLabel("Criterio de selección").fill("Eventos de cargos del ente");
    await regionRegistro.getByLabel("Justificación").fill("Verificar la integridad de la bitácora");
    await expect(regionRegistro.getByRole("radio", { name: "Selección aleatoria" })).toBeChecked();
    await regionRegistro.getByLabel("Tamaño de la muestra").fill("2");
    await regionRegistro.getByLabel("Semilla").fill("12345");
    await regionRegistro.getByRole("button", { name: "Registrar muestra" }).click();

    await expect(page).toHaveURL(/\/gobierno\/auditoria\/muestras\/.+/);
    const h1 = page.getByRole("heading", { level: 1, name: /^Muestra MU-\d{4}-\d{4}$/ });
    await expect(h1).toBeVisible();
    const codigoMuestra = ((await h1.textContent()) ?? "").replace("Muestra ", "");
    await expect(page.getByText("12345")).toBeVisible();

    const regionPartidas = page.getByRole("region", { name: `Partidas de la muestra ${codigoMuestra}` });
    const enlacesPartida = regionPartidas.getByRole("link", { name: /Ver evidencia de la partida/ });
    await expect(enlacesPartida).toHaveCount(2);
    const hrefsPrimera = await enlacesPartida.evaluateAll((enlaces) =>
      enlaces.map((e) => (e as HTMLAnchorElement).href),
    );

    await page.goto("/gobierno/auditoria?proceso=ORG-03");
    await cerrarNotificaciones(page);
    await page.getByRole("button", { name: "Registrar muestra" }).click();
    await regionRegistro.getByLabel("Título").fill("Muestra aleatoria de prueba");
    await regionRegistro.getByLabel("Criterio de selección").fill("Eventos de cargos del ente");
    await regionRegistro.getByLabel("Justificación").fill("Verificar la integridad de la bitácora");
    await regionRegistro.getByLabel("Tamaño de la muestra").fill("2");
    await regionRegistro.getByLabel("Semilla").fill("12345");
    await regionRegistro.getByRole("button", { name: "Registrar muestra" }).click();

    await expect(page).toHaveURL(/\/gobierno\/auditoria\/muestras\/.+/);
    const h1Segunda = page.getByRole("heading", { level: 1, name: /^Muestra MU-\d{4}-\d{4}$/ });
    await expect(h1Segunda).toBeVisible();
    const codigoMuestra2 = ((await h1Segunda.textContent()) ?? "").replace("Muestra ", "");
    const regionPartidas2 = page.getByRole("region", { name: `Partidas de la muestra ${codigoMuestra2}` });
    const enlacesPartida2 = regionPartidas2.getByRole("link", { name: /Ver evidencia de la partida/ });
    const hrefsSegunda = await enlacesPartida2.evaluateAll((enlaces) =>
      enlaces.map((e) => (e as HTMLAnchorElement).href),
    );
    expect(hrefsSegunda).toEqual(hrefsPrimera);

    const pendienteExportar = page.waitForEvent("download");
    await page.getByRole("button", { name: "Exportar CSV" }).click();
    const descarga = await pendienteExportar;
    expect(descarga.suggestedFilename()).toBe(`muestra-${codigoMuestra2}.csv`);
    const contenido = await fs.readFile(await descarga.path(), "utf8");
    expect(contenido.startsWith("# titulo: ")).toBe(true);
  });

  test("CTL4-E2E-02 · específica", async ({ page, request }) => {
    test.setTimeout(180_000);
    const { mundo } = await mundoConActividad(request);

    await entrarEnGobierno(page, mundo.username, mundo.codigo, "/gobierno/auditoria");
    await page.getByLabel(/^Proceso/).selectOption("ORG-03 · Cargos y competencias");
    await expect(page.getByRole("region", { name: "Población de eventos de Gobierno" })
      .getByRole("row")).not.toHaveCount(0);

    await page.getByRole("checkbox", { name: /Marcar el evento/ }).nth(0).check();
    await page.getByRole("checkbox", { name: /Marcar el evento/ }).nth(1).check();
    await expect(page.getByText("2 partidas marcadas")).toBeVisible();

    await cerrarNotificaciones(page);
    await page.getByRole("button", { name: "Registrar muestra" }).click();
    const regionRegistro = page.getByRole("region", { name: "Registrar muestra" });
    await expect(regionRegistro.getByRole("heading", { level: 2, name: "Registrar muestra" })).toBeVisible();
    await regionRegistro.getByLabel("Título").fill("Muestra específica de prueba");
    await regionRegistro.getByLabel("Criterio de selección").fill("Eventos elegidos a mano");
    await regionRegistro.getByLabel("Justificación").fill("Comprobar las partidas seleccionadas");
    await regionRegistro.getByRole("radio", { name: "Partidas específicas" }).check();
    await regionRegistro.getByRole("button", { name: "Registrar muestra" }).click();

    await expect(page).toHaveURL(/\/gobierno\/auditoria\/muestras\/.+/);
    const h1 = page.getByRole("heading", { level: 1, name: /^Muestra MU-\d{4}-\d{4}$/ });
    await expect(h1).toBeVisible();
    const codigoMuestra = ((await h1.textContent()) ?? "").replace("Muestra ", "");

    const regionPartidas = page.getByRole("region", { name: `Partidas de la muestra ${codigoMuestra}` });
    const enlacesPartida = regionPartidas.getByRole("link", { name: /Ver evidencia de la partida/ });
    await expect(enlacesPartida).toHaveCount(2);
  });

  test("CTL4-E2E-03 · permisos", async ({ page, request }) => {
    test.setTimeout(180_000);
    const { mundo } = await mundoConActividad(request);
    const adminTenant = (await sesionApi("admintenant", { tenant: TENANT })).headers;
    const soloConsulta = await crearUsuario(
      request,
      adminTenant,
      CONSULTA_AUDITORIA,
      mundo.companyId,
    );
    await entrarEnGobierno(page, soloConsulta.username, mundo.codigo, "/gobierno/auditoria");
    await expect(page.getByRole("heading", { level: 1, name: "Auditoría institucional" })).toBeVisible();
    await expect(page.getByRole("region", { name: "Población de eventos de Gobierno" })).toBeVisible();
    await expect(page.getByRole("button", { name: "Registrar muestra" })).toHaveCount(0);
    await expect(page.getByRole("checkbox", { name: /Marcar el evento/ })).toHaveCount(0);

    const otroUsuario = await crearUsuario(
      request,
      adminTenant,
      ["organization:view", "audit:view"],
      mundo.companyId,
    );
    await page.context().clearCookies();
    await entrarComoUsuario(page, otroUsuario.username, {
      tenant: TENANT,
      ruta: "/",
    });
    await activarEmpresa(page, mundo.codigo);
    await expect(page.locator('nav a[href="/gobierno/auditoria"]')).toHaveCount(0);

    const respuestaEventos = await request.get(`${API}/gobierno/auditoria/eventos`, {
      headers: otroUsuario.headers,
    });
    expect(respuestaEventos.status()).toBe(403);
  });

  test("CTL4-E2E-04 · otro ente", async ({ request }) => {
    test.setTimeout(180_000);
    const { mundo } = await mundoConActividad(request);

    const eventosA = await request.get(
      `${API}/gobierno/auditoria/eventos?proceso=ORG-03`,
      { headers: mundo.headers },
    );
    expect(eventosA.status()).toBe(200);
    const listaEventos = (await eventosA.json()) as { items: { id: string }[] };
    const eventoId = listaEventos.items[0].id;
    expect(eventoId).toBeTruthy();

    const muestraResp = await request.post(`${API}/gobierno/auditoria/muestras`, {
      headers: mundo.headers,
      data: {
        titulo: "Muestra para prueba de aislamiento",
        criterio: "Eventos del proceso ORG-03",
        justificacion: "Verificar que otro ente no accede",
        metodo: "TODAS",
        filtros: { proceso: "ORG-03" },
      },
    });
    expect(muestraResp.status()).toBe(201);
    const muestra = await muestraResp.json();
    const muestraId = muestra.id;
    expect(muestraId).toBeTruthy();

    const mundoB = await prepararMundo(request, CONSULTA_AUDITORIA);

    const respuestaEvento = await request.get(
      `${API}/gobierno/auditoria/eventos/${eventoId}`,
      { headers: mundoB.headers },
    );
    expect(respuestaEvento.status()).toBe(404);
    await expect(respuestaEvento.json()).resolves.toMatchObject({
      code: "GOV_AUDIT_EVENT_NOT_FOUND",
    });

    const respuestaMuestra = await request.get(
      `${API}/gobierno/auditoria/muestras/${muestraId}`,
      { headers: mundoB.headers },
    );
    expect(respuestaMuestra.status()).toBe(404);
    await expect(respuestaMuestra.json()).resolves.toMatchObject({
      code: "GOV_AUDIT_SAMPLE_NOT_FOUND",
    });

    const respuestaListaB = await request.get(
      `${API}/gobierno/auditoria/eventos?proceso=ORG-03`,
      { headers: mundoB.headers },
    );
    expect(respuestaListaB.status()).toBe(200);
    const listaB = (await respuestaListaB.json()) as { items: { id: string }[] };
    const idsB = listaB.items.map((e: { id: string }) => e.id);
    expect(idsB).not.toContain(eventoId);
  });

  test("CTL4-E2E-05 · inmutabilidad", async ({ request }) => {
    test.setTimeout(180_000);
    const { mundo } = await mundoConActividad(request);

    const muestraResp = await request.post(`${API}/gobierno/auditoria/muestras`, {
      headers: mundo.headers,
      data: {
        titulo: "Muestra inmutable",
        criterio: "Eventos del proceso ORG-03",
        justificacion: "Comprobar que no se puede modificar",
        metodo: "TODAS",
        filtros: { proceso: "ORG-03" },
      },
    });
    expect(muestraResp.status()).toBe(201);
    const muestra = await muestraResp.json();
    const url = `${API}/gobierno/auditoria/muestras/${muestra.id}`;

    for (const method of ["PATCH", "PUT", "DELETE"]) {
      const respuesta = await request.fetch(url, {
        method,
        headers: mundo.headers,
        data: { titulo: "Intento de modificación" },
      });
      expect(respuesta.status()).toBe(405);
    }

    const respuestaGet = await request.get(url, { headers: mundo.headers });
    expect(respuestaGet.status()).toBe(200);
    const cuerpo = await respuestaGet.json();
    expect(cuerpo.codigo).toBe(muestra.codigo);
  });

  test("CTL4-E2E-06 · accesibilidad", async ({ page, request }) => {
    test.setTimeout(180_000);
    const { mundo } = await mundoConActividad(request);

    await entrarEnGobierno(page, mundo.username, mundo.codigo, "/gobierno/auditoria");
    await cerrarNotificaciones(page);
    await page.getByRole("button", { name: /Ver evidencia del evento/ }).first().click();
    await expect(page.getByRole("heading", { level: 2, name: "Evidencia del evento" })).toBeVisible();

    for (const viewport of [
      { width: 1280, height: 768 },
      { width: 768, height: 900 },
      { width: 320, height: 568 },
    ]) {
      await page.setViewportSize(viewport);
      await sinViolacionesSerias(page, `Auditoría institucional ${viewport.width}px`);
    }

    await page.getByRole("button", { name: "Cerrar la evidencia" }).click();
    await page.getByRole("button", { name: "Registrar muestra" }).click();
    const regionRegistro = page.getByRole("region", { name: "Registrar muestra" });
    await regionRegistro.getByLabel("Título").fill("Muestra accesible");
    await regionRegistro.getByLabel("Criterio de selección").fill("Eventos de cargos del ente");
    await regionRegistro.getByLabel("Justificación").fill("Comprobar accesibilidad de la muestra");
    await regionRegistro.getByLabel("Tamaño de la muestra").fill("2");
    await regionRegistro.getByLabel("Semilla").fill("12345");
    await regionRegistro.getByRole("button", { name: "Registrar muestra" }).click();

    await expect(page).toHaveURL(/\/gobierno\/auditoria\/muestras\/.+/);
    const h1 = page.getByRole("heading", { level: 1, name: /^Muestra MU-\d{4}-\d{4}$/ });
    await expect(h1).toBeVisible();
    for (const viewport of [
      { width: 1280, height: 768 },
      { width: 768, height: 900 },
      { width: 320, height: 568 },
    ]) {
      await page.setViewportSize(viewport);
      await sinViolacionesSerias(page, `Muestra de auditoría ${viewport.width}px`);
    }
  });
});
