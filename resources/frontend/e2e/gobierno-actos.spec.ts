import AxeBuilder from "@axe-core/playwright";
import { expect, sesionApi, test } from "./helpers/sesion";
import {
  ANIO,
  API,
  PDF,
  RESPONSABLE_ESTRUCTURA,
  TENANT,
  adjuntarDocumentoApi,
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

const RESPONSABLE_ACTOS = [
  ...RESPONSABLE_ESTRUCTURA,
  "gobierno_cargos:view",
  "gobierno_cargos:edit",
  "gobierno_cargos:publish",
  "gobierno_actos:view",
  "gobierno_actos:edit",
  "gobierno_actos:issue",
  "gobierno_actos:annul",
];

async function mundoConCargo(request: APIRequestContext) {
  const mundo = await prepararMundo(request, RESPONSABLE_ACTOS);
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
  expect(es2xx(vinculoResp.status()), await vinculoResp.text()).toBe(true);
  await expect(page.getByText("Documento adjuntado")).toBeVisible({ timeout: 30_000 });
  await cerrarNotificaciones(page);
}

const WCAG = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"];

const CONSULTA_ACTOS = [
  "organization:view",
  "gobierno_estructura:view",
  "gobierno_cargos:view",
  "gobierno_actos:view",
  "documentos:view",
];

const REGISTRADOR_ACTOS = [
  ...CONSULTA_ACTOS,
  "gobierno_actos:edit",
  "documentos:create",
  "documentos:upload",
  "documentos:link",
];

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

test.describe("Gobierno · Actos administrativos (DOC-02)", () => {
  test("DOC2-E2E-01: el responsable registra un acto particular, adjunta el PDF firmado, lo emite (la notificación se registra en DOC-04) y exporta", async ({
    page,
    request,
  }) => {
    test.setTimeout(240_000);

    const { mundo, tipo } = await mundoConCargo(request);

    await entrarEnGobierno(page, mundo.username, mundo.codigo, "/gobierno/actos");

    const enlaceMenu = page.locator('nav a[href="/gobierno/actos"]').first();
    await expect(enlaceMenu).toBeVisible();
    await expect(
      enlaceMenu.getByText("Actos administrativos", { exact: true }),
    ).toBeVisible();
    await expect(page.getByRole("heading", { name: "Actos administrativos", level: 1 })).toBeVisible();

    await page.getByRole("button", { name: "Registrar acto" }).click();

    const formulario = page.getByRole("form", { name: "Registrar acto" });
    await formulario.getByLabel(/^Tipo de acto/).selectOption({ label: "Resolución" });
    await formulario.getByLabel(/^Número/).fill(`DA-001-${ANIO}`);
    await expect(formulario.getByLabel(/^Fecha del acto \*/)).toHaveValue(hoyCaracas());
    await formulario.getByLabel(/^Lugar/).fill("Caracas");
    await formulario
      .getByLabel(/^Cargo que lo dicta/)
      .selectOption({ label: "DA-01 · DIR-ADM — Cargo DIR-ADM" });
    await formulario
      .getByLabel(/^Competencia/)
      .selectOption({ label: "Aprobar · Contrataciones" });
    await formulario
      .getByLabel(/^Fundamento de la competencia/)
      .fill("Reglamento interno, art. 12");
    await formulario.getByLabel(/^Funcionario que suscribe/).fill("Funcionaria de prueba");
    await formulario.getByLabel(/^Titularidad/).selectOption({ label: "Titular" });
    await formulario.getByRole("radio", { name: "Particular (se notifica)" }).check();
    await formulario.getByLabel(/^Destinatario/).fill("Proveedor de prueba");
    await formulario.getByLabel(/^Asunto/).fill("Adjudicación de prueba");
    await formulario.getByLabel(/^Hechos/).fill("Hechos de prueba");
    await formulario.getByLabel(/^Fundamentos legales/).fill("Fundamentos legales de prueba");
    await formulario.getByLabel(/^Decisión/).fill("Decisión de prueba");

    const [actoResp] = await Promise.all([
      page.waitForResponse(
        (r) =>
          new URL(r.url()).pathname.endsWith("/api/v1/gobierno/actos") &&
          r.request().method() === "POST",
        { timeout: 30_000 },
      ),
      formulario.getByRole("button", { name: "Guardar" }).click(),
    ]);
    expect(actoResp.status()).toBe(201);
    const actoCreado = await actoResp.json();
    const id = actoCreado.id;

    await expect(page.getByText("Acto registrado")).toBeVisible();
    await cerrarNotificaciones(page);
    await page.waitForURL((u) => u.pathname === `/gobierno/actos/${id}`);
    await expect(
      page.getByRole("heading", { name: `Resolución Nº DA-001-${ANIO}`, level: 1 }),
    ).toBeVisible();

    const requisitos = page.getByRole("region", { name: "Requisitos para emitir" });
    await expect(requisitos.getByText("El PDF firmado del acto", { exact: true })).toBeVisible();

    const documentosActo = page
      .getByRole("region", { name: "Documentos del acto" })
      .first();
    await adjuntarPdfDesdeUi(page, documentosActo, tipo.name);

    await page.getByRole("button", { name: "Emitir" }).click();

    const formularioEmitir = page.getByRole("form", {
      name: `Emitir Resolución Nº DA-001-${ANIO}`,
    });
    await expect(formularioEmitir.getByLabel("PDF firmado del acto")).toBeVisible();
    const selectPdf = formularioEmitir.getByLabel("PDF firmado del acto");
    await expect(selectPdf.locator("option")).toHaveCount(2);
    await selectPdf.selectOption({ index: 1 });

    const [emitirResp] = await Promise.all([
      page.waitForResponse(
        (r) =>
          new URL(r.url()).pathname.endsWith(`/api/v1/gobierno/actos/${id}/emitir`) &&
          r.request().method() === "POST",
        { timeout: 30_000 },
      ),
      formularioEmitir.getByRole("button", { name: "Emitir" }).click(),
    ]);
    expect(emitirResp.status()).toBe(200);

    await expect(page.getByText("Acto emitido")).toBeVisible();
    await cerrarNotificaciones(page);
    await expect(
      page.locator("main").getByRole("status").filter({ hasText: "Emitido, pendiente de notificación." }),
    ).toBeVisible();

    await adjuntarPdfDesdeUi(page, documentosActo, tipo.name);

    await expect(page.getByRole("button", { name: "Registrar la notificación" })).toHaveCount(0);
    await expect(page.getByRole("heading", { name: "Notificaciones", level: 2 })).toBeVisible();

    const historial = page.getByRole("region", {
      name: `Historial del acto Resolución Nº DA-001-${ANIO}`,
    });
    await expect(historial.getByRole("row").filter({ has: page.getByRole("cell") })).toHaveCount(2);
    await expect(historial.getByRole("cell", { name: "Borrador", exact: true })).toBeVisible();
    await expect(historial.getByRole("cell", { name: "Emitido", exact: true })).toBeVisible();

    await page
      .getByRole("navigation", { name: "Ruta de navegación" })
      .getByRole("link", { name: "Actos administrativos", exact: true })
      .click();
    await page.waitForURL((u) => u.pathname === `/gobierno/actos`);

    const filaActo = page
      .getByRole("row")
      .filter({ has: page.getByRole("link", { name: `Abrir el acto Resolución Nº DA-001-${ANIO}` }) });
    await expect(filaActo.getByRole("cell", { name: "Emitido", exact: true })).toBeVisible();

    const downloadPromise = page.waitForEvent("download");
    await page.getByRole("button", { name: "Exportar CSV" }).click();
    const download = await downloadPromise;
    expect(download.suggestedFilename()).toBe(`actos-${ANIO}.csv`);
    const stream = await download.createReadStream();
    const chunks: Buffer[] = [];
    for await (const chunk of stream) {
      chunks.push(Buffer.isBuffer(chunk) ? chunk : Buffer.from(chunk));
    }
    const contenido = Buffer.concat(chunks).toString("utf8");
    expect(contenido).toContain(`DA-001-${ANIO}`);
  });

  test("DOC2-E2E-02: un acto eficaz se revoca indicando el acto que lo revoca", async ({
    page,
    request,
  }) => {
    test.setTimeout(240_000);

    const { mundo, tipo, cargoId } = await mundoConCargo(request);
    const fechaHoy = new Intl.DateTimeFormat("en-CA", { timeZone: "America/Caracas" }).format(
      new Date(),
    );

    const baseActo = {
      cargo_id: cargoId,
      fecha: fechaHoy,
      lugar: "Caracas",
      fundamento_competencia: "Reglamento interno, art. 12",
      funcionario: "Funcionaria de prueba",
      titularidad: "TITULAR",
      hechos: "Hechos de prueba",
      fundamentos: "Fundamentos legales de prueba",
      decision: "Decisión de prueba",
    };

    const crearActo = async (
      numero: string,
      caracter: "PARTICULAR" | "INTERNO",
      asunto: string,
      destinatario?: string,
    ) => {
      const data: Record<string, unknown> = {
        ...baseActo,
        tipo: "RESOLUCION",
        numero,
        caracter,
        asunto,
        simple_tramite: false,
        competencia: { accion: "APROBAR", materia: "CONTRATACIONES" },
      };
      if (destinatario !== undefined) {
        data.destinatario = destinatario;
      }

      const resp = await request.post(`${API}/gobierno/actos`, {
        headers: mundo.headers,
        data,
      });
      expect(resp.status(), await resp.text()).toBe(201);
      const body = await resp.json();
      const id = body.id;

      await adjuntarDocumentoApi(
        request,
        mundo.headers,
        mundo.companyId,
        tipo.id,
        "GovernmentAct",
        id,
      );

      const docsResp = await request.get(
        `${API}/documentos/por-recurso/GovernmentAct/${id}`,
        { headers: mundo.headers },
      );
      expect(docsResp.status(), await docsResp.text()).toBe(200);
      const docs = await docsResp.json();
      const documentoActoId = docs[0].id;

      const emitirResp = await request.post(`${API}/gobierno/actos/${id}/emitir`, {
        headers: { ...mundo.headers, "If-Match": '"1"' },
        data: { documento_acto_id: documentoActoId },
      });
      expect(emitirResp.status(), await emitirResp.text()).toBe(200);

      return { id, documentoActoId };
    };

    const actoA = await crearActo(
      `DA-010-${ANIO}`,
      "PARTICULAR",
      "Adjudicación de prueba",
      "Proveedor de prueba",
    );
    const actoB = await crearActo(`DA-011-${ANIO}`, "INTERNO", "Revocatoria de prueba");

    await entrarEnGobierno(page, mundo.username, mundo.codigo, "/gobierno/actos");
    await page.goto(`/gobierno/actos/${actoA.id}`);
    await expect(
      page.getByRole("heading", { name: `Resolución Nº DA-010-${ANIO}`, level: 1 }),
    ).toBeVisible();

    await page.getByRole("button", { name: "Registrar revocación" }).click();

    const formularioRevocacion = page.getByRole("form", {
      name: `Registrar la revocación de Resolución Nº DA-010-${ANIO}`,
    });
    const selectReferencia = formularioRevocacion.getByLabel(/^Acto de referencia/);
    const opcion = selectReferencia.locator("option", { hasText: `DA-011-${ANIO}` });
    await expect(opcion).toHaveCount(1);
    await selectReferencia.selectOption((await opcion.getAttribute("value")) ?? "");
    await formularioRevocacion.getByLabel(/^Motivo/).fill("Revocado por cambio de criterio");

    const [revocarResp] = await Promise.all([
      page.waitForResponse(
        (r) =>
          new URL(r.url()).pathname.endsWith("/revocar") &&
          r.request().method() === "POST",
        { timeout: 30_000 },
      ),
      formularioRevocacion.getByRole("button", { name: "Registrar revocación" }).click(),
    ]);
    expect(revocarResp.status()).toBe(200);

    await expect(
      page.locator("main").getByRole("status").filter({ hasText: /Revocado por/i }),
    ).toBeVisible();
    await expect(
      page.locator("main").getByRole("status").getByRole("link", {
        name: `Resolución Nº DA-011-${ANIO}`,
      }),
    ).toHaveAttribute("href", `/gobierno/actos/${actoB.id}`);
    await cerrarNotificaciones(page);
    await expect(page.getByRole("button", { name: "Corregir error material" })).toHaveCount(0);
    await expect(page.getByRole("button", { name: "Registrar revocación" })).toHaveCount(0);
  });

  test("DOC2-E2E-03: consulta", async ({ page, request }) => {
    test.setTimeout(180_000);

    const { mundo, cargoId } = await mundoConCargo(request);
    await actoBorradorApi(request, mundo.headers, cargoId, `DA-100-${ANIO}`);

    const admin = await sesionApi("admintenant", { tenant: TENANT });
    const consulta = await crearUsuario(
      request,
      admin.headers,
      CONSULTA_ACTOS,
      mundo.companyId,
    );

    await entrarEnGobierno(page, consulta.username, mundo.codigo, "/gobierno/actos");

    await expect(
      page.getByRole("link", { name: `Abrir el acto Resolución Nº DA-100-${ANIO}` }),
    ).toBeVisible();
    await expect(page.getByRole("button", { name: "Registrar acto" })).toHaveCount(0);
    await expect(page.getByRole("button", { name: "Exportar CSV" })).toBeVisible();

    await page
      .getByRole("link", { name: `Abrir el acto Resolución Nº DA-100-${ANIO}` })
      .click();
    await expect(
      page.getByRole("heading", { name: `Resolución Nº DA-100-${ANIO}`, level: 1 }),
    ).toBeVisible();
    await expect(page.getByRole("button", { name: "Editar" })).toHaveCount(0);
    await expect(page.getByRole("button", { name: "Eliminar" })).toHaveCount(0);
    await expect(page.getByRole("button", { name: "Emitir" })).toHaveCount(0);

    const postResp = await request.post(`${API}/gobierno/actos`, {
      headers: consulta.headers,
      data: {
        tipo: "RESOLUCION",
        numero: `DA-SIN-PERMISO-${ANIO}`,
        caracter: "INTERNO",
        asunto: "Sin permiso",
        simple_tramite: false,
        cargo_id: cargoId,
        fecha: hoyCaracas(),
        lugar: "Caracas",
        fundamento_competencia: "Reglamento interno, art. 12",
        funcionario: "Funcionaria de prueba",
        titularidad: "TITULAR",
        hechos: "Hechos de prueba",
        fundamentos: "Fundamentos legales de prueba",
        decision: "Decisión de prueba",
        competencia: { accion: "APROBAR", materia: "CONTRATACIONES" },
      },
    });
    expect(postResp.status(), await postResp.text()).toBe(403);
    const postBody = await postResp.json();
    expect(postBody.code).toBe("PERMISSION_DENIED");
  });

  test("DOC2-E2E-04: el registrador sin permiso de emisión no puede emitir", async ({
    page,
    request,
  }) => {
    test.setTimeout(180_000);

    const { mundo, cargoId } = await mundoConCargo(request);
    const acto = await actoBorradorApi(
      request,
      mundo.headers,
      cargoId,
      `DA-101-${ANIO}`,
    );

    const admin = await sesionApi("admintenant", { tenant: TENANT });
    const registrador = await crearUsuario(
      request,
      admin.headers,
      REGISTRADOR_ACTOS,
      mundo.companyId,
    );

    await entrarEnGobierno(
      page,
      registrador.username,
      mundo.codigo,
      "/gobierno/actos",
    );
    await page.goto(`/gobierno/actos/${acto.id}`);

    await expect(
      page.getByRole("heading", { name: `Resolución Nº DA-101-${ANIO}`, level: 1 }),
    ).toBeVisible();
    await expect(page.getByRole("button", { name: "Editar" })).toBeVisible();
    await expect(page.getByRole("button", { name: "Eliminar" })).toBeVisible();
    await expect(page.getByRole("button", { name: "Emitir" })).toHaveCount(0);

    const emitirResp = await request.post(`${API}/gobierno/actos/${acto.id}/emitir`, {
      headers: { ...registrador.headers, "If-Match": '"1"' },
      data: { documento_acto_id: "00000000-0000-0000-0000-000000000000" },
    });
    expect(emitirResp.status(), await emitirResp.text()).toBe(403);
    const emitirBody = await emitirResp.json();
    expect(emitirBody.code).toBe("PERMISSION_DENIED");
  });

  test("DOC2-E2E-05: otro ente", async ({ page, request }) => {
    test.setTimeout(180_000);

    const mundoAContext = await mundoConCargo(request);
    const actoA = await actoBorradorApi(
      request,
      mundoAContext.mundo.headers,
      mundoAContext.cargoId,
      `DA-102-${ANIO}`,
    );
    const idA = actoA.id;

    const mundoBContext = await mundoConCargo(request);
    const mundoB = mundoBContext.mundo;

    await entrarEnGobierno(page, mundoB.username, mundoB.codigo, "/gobierno/actos");
    await page.goto(`/gobierno/actos/${idA}`);

    await expect(
      page.getByText("El acto no existe o no pertenece a este ente", { exact: true }),
    ).toBeVisible();
    await expect(
      page.getByRole("link", { name: "Volver a Actos administrativos" }),
    ).toBeVisible();

    await expect(
      page.getByRole("link", { name: `Abrir el acto Resolución Nº DA-102-${ANIO}` }),
    ).toHaveCount(0);

    const getResp = await request.get(`${API}/gobierno/actos/${idA}`, {
      headers: mundoB.headers,
    });
    expect(getResp.status(), await getResp.text()).toBe(404);
    const getBody = await getResp.json();
    expect(getBody.code).toBe("GOV_ACT_NOT_FOUND");
  });

  test("DOC2-E2E-06: validaciones", async ({ page, request }) => {
    test.setTimeout(180_000);

    const { mundo, cargoId } = await mundoConCargo(request);
    await actoBorradorApi(request, mundo.headers, cargoId, `DA-103-${ANIO}`);

    await entrarEnGobierno(page, mundo.username, mundo.codigo, "/gobierno/actos");

    let peticionesPostActos = 0;
    page.on("request", (req) => {
      const url = new URL(req.url());
      if (
        url.pathname.endsWith("/api/v1/gobierno/actos") &&
        req.method() === "POST"
      ) {
        peticionesPostActos += 1;
      }
    });

    await page.getByRole("button", { name: "Registrar acto" }).click();

    const formulario = page.getByRole("form", { name: "Registrar acto" });
    await formulario.getByRole("button", { name: "Guardar" }).click();

    await expect(formulario.getByText("Seleccione el tipo de acto")).toBeVisible();
    await expect(
      formulario.getByText("El número debe tener entre 1 y 60 caracteres"),
    ).toBeVisible();
    await expect(formulario.getByText("Seleccione el cargo que dicta el acto")).toBeVisible();
    await expect(formulario.getByLabel(/^Número/)).toHaveAttribute("aria-invalid", "true");
    expect(peticionesPostActos).toBe(0);

    await formulario.getByLabel(/^Tipo de acto/).selectOption({ label: "Resolución" });
    await formulario.getByLabel(/^Número/).fill(`DA-103-${ANIO}`);
    await formulario
      .getByLabel(/^Cargo que lo dicta/)
      .selectOption({ label: "DA-01 · DIR-ADM — Cargo DIR-ADM" });
    await formulario
      .getByLabel(/^Competencia/)
      .selectOption({ label: "Aprobar · Contrataciones" });
    await formulario.getByLabel(/^Lugar/).fill("Caracas");
    await formulario
      .getByLabel(/^Fundamento de la competencia/)
      .fill("Reglamento interno, art. 12");
    await formulario.getByLabel(/^Funcionario que suscribe/).fill("Funcionaria de prueba");
    await formulario.getByLabel(/^Titularidad/).selectOption({ label: "Titular" });
    await formulario.getByRole("radio", { name: "Particular (se notifica)" }).check();
    await formulario.getByLabel(/^Destinatario/).fill("Proveedor de prueba");
    await formulario.getByLabel(/^Asunto/).fill(`Asunto DA-103-${ANIO}`);
    await formulario.getByLabel(/^Hechos/).fill("Hechos de prueba");
    await formulario.getByLabel(/^Fundamentos legales/).fill("Fundamentos legales de prueba");
    await formulario.getByLabel(/^Decisión/).fill("Decisión de prueba");

    const [duplicadoResp] = await Promise.all([
      page.waitForResponse(
        (r) =>
          new URL(r.url()).pathname.endsWith("/api/v1/gobierno/actos") &&
          r.request().method() === "POST",
        { timeout: 30_000 },
      ),
      formulario.getByRole("button", { name: "Guardar" }).click(),
    ]);
    expect(duplicadoResp.status()).toBe(409);
    await expect(
      formulario.getByText("Ya existe un acto con este cargo, tipo y número"),
    ).toBeVisible();

    const fechaHoy = hoyCaracas();
    const [year, month, day] = fechaHoy.split("-").map((v) => Number(v));
    const manana = new Date(Date.UTC(year, month - 1, day + 1));
    const mananaIso = [
      manana.getUTCFullYear(),
      String(manana.getUTCMonth() + 1).padStart(2, "0"),
      String(manana.getUTCDate()).padStart(2, "0"),
    ].join("-");

    await formulario.getByLabel(/^Fecha del acto/).fill(mananaIso);
    await formulario.getByRole("button", { name: "Guardar" }).click();

    await expect(
      formulario.getByText("La fecha del acto no puede ser posterior a hoy"),
    ).toBeVisible();
  });

  test("DOC2-E2E-07: accesibilidad", async ({ page, request }) => {
    test.setTimeout(180_000);

    const { mundo, cargoId } = await mundoConCargo(request);
    const acto = await actoBorradorApi(
      request,
      mundo.headers,
      cargoId,
      `DA-104-${ANIO}`,
    );

    await entrarEnGobierno(page, mundo.username, mundo.codigo, "/gobierno/actos");
    await expect(
      page.getByRole("heading", { name: "Actos administrativos", level: 1 }),
    ).toBeVisible();

    for (const width of [1280, 768, 320]) {
      await page.setViewportSize({ width, height: 900 });
      await sinViolacionesSerias(page, `Lista de actos a ${width}px`);
    }

    for (const width of [1280, 768, 320]) {
      await page.setViewportSize({ width, height: 900 });

      await page
        .getByRole("link", { name: `Abrir el acto Resolución Nº DA-104-${ANIO}` })
        .click();
      await page.waitForURL((u) => u.pathname === `/gobierno/actos/${acto.id}`);
      await expect(
        page.getByRole("heading", { name: `Resolución Nº DA-104-${ANIO}`, level: 1 }),
      ).toBeVisible();

      await sinViolacionesSerias(page, `Detalle del acto a ${width}px`);

      await cerrarNotificaciones(page);
      await page
        .getByRole("navigation", { name: "Ruta de navegación" })
        .getByRole("link", { name: "Actos administrativos", exact: true })
        .click();
      await page.waitForURL((u) => u.pathname === `/gobierno/actos`);
    }

    for (const width of [1280, 768, 320]) {
      await page.setViewportSize({ width, height: 900 });

      await cerrarNotificaciones(page);
      await page.getByRole("button", { name: "Registrar acto" }).click();
      await expect(
        page.getByRole("form", { name: "Registrar acto" }),
      ).toBeVisible();

      await sinViolacionesSerias(page, `Formulario de registro a ${width}px`);
    }
  });
});
