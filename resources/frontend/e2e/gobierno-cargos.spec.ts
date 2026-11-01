import AxeBuilder from "@axe-core/playwright";
import { type APIRequestContext } from "@playwright/test";
import { expect, sesionApi, test } from "./helpers/sesion";
import {
  ANIO,
  API,
  PDF,
  RESPONSABLE_ESTRUCTURA,
  TENANT,
  adjuntarDocumentoApi,
  cerrarNotificaciones,
  crearTipoDocumental,
  crearUsuario,
  enteActivo,
  entrarEnGobierno,
  es2xx,
  prepararMundo,
} from "./helpers/gobierno";

const WCAG = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"];

const RESPONSABLE_CARGOS = [
  ...RESPONSABLE_ESTRUCTURA,
  "gobierno_cargos:view",
  "gobierno_cargos:edit",
  "gobierno_cargos:publish",
];
const PREPARADOR_CARGOS = [
  "organization:view",
  "gobierno_estructura:view",
  "gobierno_cargos:view",
  "gobierno_cargos:edit",
  "documentos:view",
];
const CONSULTA_CARGOS = [
  "organization:view",
  "gobierno_estructura:view",
  "gobierno_cargos:view",
  "documentos:view",
];

async function estructuraVigenteApi(
  request: APIRequestContext,
  headers: Record<string, string>,
  companyId: string,
  tipoId: string,
  ejercicio: number,
): Promise<{ estructuraId: string; despId: string; da01Id: string }> {
  const estructuraResp = await request.post(`${API}/gobierno/estructuras`, {
    headers,
    data: { ejercicio },
  });
  expect(es2xx(estructuraResp.status()), await estructuraResp.text()).toBe(true);
  const estructura = await estructuraResp.json();

  const crearUnidad = async (
    data: Record<string, unknown>,
  ): Promise<{ id: string; version: number }> => {
    const resp = await request.post(`${API}/gobierno/estructuras/${ejercicio}/unidades`, {
      headers,
      data,
    });
    expect(es2xx(resp.status()), await resp.text()).toBe(true);
    const body = await resp.json();
    return { id: body.id, version: body.version };
  };

  const desp = await crearUnidad({
    codigo: "DESP",
    denominacion: "Despacho del Alcalde",
    tipo: "ORGANO",
    unidad_superior_id: null,
    vigente_desde: `${ejercicio}-01-01`,
  });
  const da01 = await crearUnidad({
    codigo: "DA-01",
    denominacion: "Dirección de Administración",
    tipo: "UNIDAD_ADMINISTRATIVA",
    unidad_superior_id: desp.id,
    vigente_desde: `${ejercicio}-01-01`,
  });

  await adjuntarDocumentoApi(
    request,
    headers,
    companyId,
    tipoId,
    "GovernmentStructure",
    estructura.id,
  );

  const publicarResp = await request.post(`${API}/gobierno/estructuras/${ejercicio}/publicar`, {
    headers: { ...headers, "If-Match": '"1"' },
  });
  expect(publicarResp.status(), await publicarResp.text()).toBe(200);

  return { estructuraId: estructura.id, despId: desp.id, da01Id: da01.id };
}

async function cargoVigenteApi(
  request: APIRequestContext,
  headers: Record<string, string>,
  companyId: string,
  tipoId: string,
  ejercicio: number,
  unidadId: string,
  codigo: string,
): Promise<{ id: string; version: number }> {
  const cargoResp = await request.post(`${API}/gobierno/estructuras/${ejercicio}/cargos`, {
    headers,
    data: {
      codigo,
      denominacion: `Cargo ${codigo}`,
      unidad_id: unidadId,
      vigente_desde: `${ejercicio}-01-01`,
    },
  });
  expect(cargoResp.status(), await cargoResp.text()).toBe(201);
  const cargo = await cargoResp.json();

  const competenciaResp = await request.post(
    `${API}/gobierno/estructuras/${ejercicio}/cargos/${cargo.id}/competencias`,
    {
      headers: { ...headers, "If-Match": '"1"' },
      data: {
        accion: "APROBAR",
        materia: "CONTRATACIONES",
        tipo_limite: "MONTO",
        monto: "50000.00",
        moneda: "USD",
      },
    },
  );
  expect(competenciaResp.status(), await competenciaResp.text()).toBe(201);

  await adjuntarDocumentoApi(
    request,
    headers,
    companyId,
    tipoId,
    "GovernmentPosition",
    cargo.id,
  );

  const activarResp = await request.post(
    `${API}/gobierno/estructuras/${ejercicio}/cargos/${cargo.id}/activar`,
    {
      headers: { ...headers, "If-Match": '"2"' },
    },
  );
  expect(activarResp.status(), await activarResp.text()).toBe(200);

  return { id: cargo.id, version: 3 };
}

test.describe("Gobierno · Cargos y competencias (GOV-0-03)", () => {
  test("GOV3-E2E-01: el responsable registra un cargo, le da competencias con límite, adjunta el acto, lo pone en vigor, cambia el límite con motivo y exporta", async ({
    page,
    request,
  }) => {
    test.setTimeout(240_000);

    const mundo = await prepararMundo(request, RESPONSABLE_CARGOS);
    const tipo = await crearTipoDocumental(request, mundo.headers, mundo.companyId);
    await enteActivo(request, mundo.headers, mundo.companyId, tipo.id);
    await estructuraVigenteApi(
      request,
      mundo.headers,
      mundo.companyId,
      tipo.id,
      ANIO,
    );

    await entrarEnGobierno(page, mundo.username, mundo.codigo, "/gobierno/cargos");

    const enlaceMenu = page.locator('nav a[href="/gobierno/cargos"]').first();
    await expect(enlaceMenu).toBeVisible();
    await expect(enlaceMenu.getByText("Cargos y competencias", { exact: true })).toBeVisible();

    await page.getByRole("link", { name: `Cargos ${ANIO}` }).click();
    await page.waitForURL((u) => u.pathname === `/gobierno/cargos/${ANIO}`);
    await expect(
      page.getByRole("heading", { name: `Cargos y competencias ${ANIO}`, level: 1 }),
    ).toBeVisible();

    await page.getByRole("button", { name: "Agregar cargo" }).click();

    const formulario = page.getByRole("form", { name: "Registrar cargo" });
    const codigo = "DIR-ADM";
    const denominacion = "Director de Administración";
    await formulario.getByLabel(/^Código/).fill(codigo);
    await formulario.getByLabel(/^Denominación/).fill(denominacion);
    await formulario
      .getByLabel(/^Unidad/)
      .selectOption({ label: "DA-01 — Dirección de Administración" });
    await formulario.getByLabel(/^Vigente desde/).fill(`${ANIO}-01-01`);

    const [cargoResp] = await Promise.all([
      page.waitForResponse(
        (r) =>
          new URL(r.url()).pathname.endsWith(`/api/v1/gobierno/estructuras/${ANIO}/cargos`) &&
          r.request().method() === "POST",
        { timeout: 30_000 },
      ),
      formulario.getByRole("button", { name: "Guardar" }).click(),
    ]);
    expect(cargoResp.status()).toBe(201);
    const cargoCreado = await cargoResp.json();
    const cargoId = cargoCreado.id;

    await expect(page.getByText("Cargo registrado")).toBeVisible();
    await cerrarNotificaciones(page);
    await page.waitForURL((u) => u.pathname === `/gobierno/cargos/${ANIO}/${cargoId}`);
    await expect(
      page.getByRole("heading", { name: `${codigo} — ${denominacion}`, level: 1 }),
    ).toBeVisible();

    const requisitos = page.getByRole("region", { name: "Requisitos para poner en vigor" });
    await expect(requisitos.getByText("Al menos una competencia", { exact: true })).toBeVisible();
    await expect(requisitos.getByText("Acto del cargo", { exact: true })).toBeVisible();
    await expect(page.getByRole("button", { name: "Poner en vigor" })).toBeDisabled();

    await page.getByRole("button", { name: "Agregar competencia" }).click();
    const formularioCompetencia = page.getByRole("form", {
      name: `Agregar competencia al cargo ${codigo}`,
    });
    await formularioCompetencia.getByLabel(/^Acción/).selectOption({ label: "Aprobar" });
    await formularioCompetencia.getByLabel(/^Materia/).selectOption({ label: "Contrataciones" });
    await formularioCompetencia
      .getByRole("radio", { name: "Hasta un monto por operación" })
      .check();
    await formularioCompetencia.getByLabel(/^Monto máximo por operación/).fill("50000");
    await formularioCompetencia.getByLabel(/^Moneda/).selectOption({ label: "Dólares (USD)" });
    await formularioCompetencia.getByLabel(/^Fundamento/).fill("Reglamento interno, art. 12");

    const competenciaRegex = new RegExp(
      `/api/v1/gobierno/estructuras/${ANIO}/cargos/[^/]+/competencias$`,
    );
    const [competenciaResp] = await Promise.all([
      page.waitForResponse(
        (r) => competenciaRegex.test(new URL(r.url()).pathname) && r.request().method() === "POST",
        { timeout: 30_000 },
      ),
      formularioCompetencia.getByRole("button", { name: "Guardar" }).click(),
    ]);
    expect(competenciaResp.status()).toBe(201);

    await expect(page.getByText("Competencia agregada")).toBeVisible();
    await cerrarNotificaciones(page);

    const filaAprobar = page
      .getByRole("row")
      .filter({ has: page.getByRole("cell", { name: "Aprobar", exact: true }) })
      .filter({ has: page.getByRole("cell", { name: "Contrataciones", exact: true }) });
    await expect(
      filaAprobar.getByText("Hasta 50.000,00 USD por operación", { exact: true }),
    ).toBeVisible();

    await page.getByRole("button", { name: "Agregar competencia" }).click();
    const formularioFirmar = page.getByRole("form", {
      name: `Agregar competencia al cargo ${codigo}`,
    });
    await formularioFirmar.getByLabel(/^Acción/).selectOption({ label: "Firmar" });
    await formularioFirmar.getByLabel(/^Materia/).selectOption({ label: "Tesorería" });
    await formularioFirmar.getByRole("radio", { name: "Sin límite" }).check();
    await formularioFirmar.getByLabel(/^Fundamento/).fill("Reglamento interno, art. 15");

    const [firmarResp] = await Promise.all([
      page.waitForResponse(
        (r) => competenciaRegex.test(new URL(r.url()).pathname) && r.request().method() === "POST",
        { timeout: 30_000 },
      ),
      formularioFirmar.getByRole("button", { name: "Guardar" }).click(),
    ]);
    expect(firmarResp.status()).toBe(201);

    await expect(page.getByText("Competencia agregada")).toBeVisible();
    await cerrarNotificaciones(page);

    const filaFirmar = page
      .getByRole("row")
      .filter({ has: page.getByRole("cell", { name: "Firmar", exact: true }) })
      .filter({ has: page.getByRole("cell", { name: "Tesorería", exact: true }) });
    await expect(filaFirmar.getByText("Sin límite", { exact: true })).toBeVisible();

    const acto = page.getByRole("region", { name: "Acto del cargo" }).first();
    await acto.getByLabel("Tipo documental del archivo").selectOption({ label: tipo.name });
    await acto.getByLabel(/^Archivo/).setInputFiles({
      name: "acto.pdf",
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
      acto.getByRole("button", { name: "Adjuntar" }).click(),
    ]);
    expect(es2xx(vinculoResp.status()), await vinculoResp.text()).toBe(true);

    await expect(page.getByText("Documento adjuntado")).toBeVisible({ timeout: 30_000 });
    await cerrarNotificaciones(page);
    await expect(
      requisitos.getByText("El cargo está completo y puede ponerse en vigor.", { exact: true }),
    ).toBeVisible();
    await expect(page.getByRole("button", { name: "Poner en vigor" })).toBeEnabled();

    await page.getByRole("button", { name: "Poner en vigor" }).click();
    await expect(page.getByRole("dialog")).toBeVisible();
    await expect(
      page.getByRole("dialog").getByText(`Poner en vigor el cargo ${codigo}`, { exact: false }),
    ).toBeVisible();

    const activarRegex = new RegExp(
      `/api/v1/gobierno/estructuras/${ANIO}/cargos/[^/]+/activar$`,
    );
    const [publicarResp] = await Promise.all([
      page.waitForResponse(
        (r) => activarRegex.test(new URL(r.url()).pathname) && r.request().method() === "POST",
        { timeout: 30_000 },
      ),
      page.getByRole("dialog").getByRole("button", { name: "Poner en vigor" }).click(),
    ]);
    expect(publicarResp.status()).toBe(200);

    await expect(page.getByText("Cargo en vigor")).toBeVisible();
    await cerrarNotificaciones(page);
    await expect(
      page.locator("main header").first().getByText("Vigente", { exact: true }),
    ).toBeVisible();

    await page
      .getByRole("button", { name: "Cambiar el límite de Aprobar · Contrataciones" })
      .click();
    const formularioCambio = page.getByRole("form", {
      name: "Cambiar el límite de Aprobar · Contrataciones",
    });
    await formularioCambio.getByLabel(/^Monto máximo por operación/).fill("75000");
    await formularioCambio.getByLabel(/^Motivo del cambio/).fill("Ajuste del límite aprobado");

    const [cambioResp] = await Promise.all([
      page.waitForResponse(
        (r) =>
          new RegExp(`/api/v1/gobierno/estructuras/${ANIO}/cargos/[^/]+/competencias/[^/]+$`).test(
            new URL(r.url()).pathname,
          ) && r.request().method() === "PATCH",
        { timeout: 30_000 },
      ),
      formularioCambio.getByRole("button", { name: "Guardar" }).click(),
    ]);
    expect(cambioResp.status()).toBe(200);

    await expect(page.getByText("Límite actualizado")).toBeVisible();
    await cerrarNotificaciones(page);
    await expect(
      filaAprobar.getByText("Hasta 75.000,00 USD por operación", { exact: true }),
    ).toBeVisible();

    await page
      .getByRole("navigation", { name: "Ruta de navegación" })
      .getByRole("link", { name: `${ANIO}`, exact: true })
      .click();
    await page.waitForURL((u) => u.pathname === `/gobierno/cargos/${ANIO}`);

    const downloadPromise = page.waitForEvent("download");
    await page.getByRole("button", { name: "Exportar CSV" }).click();
    const download = await downloadPromise;
    expect(download.suggestedFilename()).toBe(`cargos-${ANIO}.csv`);
    const stream = await download.createReadStream();
    const chunks: Buffer[] = [];
    for await (const chunk of stream) {
      chunks.push(Buffer.isBuffer(chunk) ? chunk : Buffer.from(chunk));
    }
    const contenido = Buffer.concat(chunks).toString("utf8");
    expect(contenido.startsWith("codigo_cargo,denominacion,codigo_unidad,estado")).toBe(true);

    const admin = await sesionApi("admintenant", { tenant: TENANT });
    const auditResp = await request.get(
      `${API}/audit/events?entity_type=GovernmentPosition&entity_id=${cargoId}&page_size=50`,
      { headers: admin.headers },
    );
    expect(auditResp.status(), await auditResp.text()).toBe(200);
    const auditBody = await auditResp.json();
    const acciones = auditBody.items.map((e: { action: string }) => e.action);
    expect(acciones).toContain("GOV_POSITION_CREATED");
    expect(acciones).toContain("GOV_COMPETENCY_GRANTED");
    expect(acciones).toContain("GOV_POSITION_ACTIVATED");
    expect(acciones).toContain("GOV_COMPETENCY_CHANGED");
  });

  test("GOV3-E2E-02: el preparador no cambia la autoridad de un cargo vigente", async ({
    page,
    request,
  }) => {
    test.setTimeout(180_000);

    const mundo = await prepararMundo(request, RESPONSABLE_CARGOS);
    const tipo = await crearTipoDocumental(request, mundo.headers, mundo.companyId);
    await enteActivo(request, mundo.headers, mundo.companyId, tipo.id);
    const estructura = await estructuraVigenteApi(
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
      estructura.da01Id,
      "DIR-ADM",
    );

    const admin = await sesionApi("admintenant", { tenant: TENANT });
    const preparador = await crearUsuario(
      request,
      admin.headers,
      PREPARADOR_CARGOS,
      mundo.companyId,
    );

    await entrarEnGobierno(page, preparador.username, mundo.codigo, "/gobierno/cargos");
    await page.getByRole("link", { name: `Cargos ${ANIO}` }).click();
    await page.waitForURL((u) => u.pathname === `/gobierno/cargos/${ANIO}`);
    await expect(
      page.getByRole("heading", { name: `Cargos y competencias ${ANIO}`, level: 1 }),
    ).toBeVisible();
    await expect(page.getByRole("button", { name: "Agregar cargo" })).toBeVisible();
    await page.getByRole("link", { name: `Abrir el cargo DIR-ADM` }).click();
    await page.waitForURL((u) => u.pathname === `/gobierno/cargos/${ANIO}/${cargo.id}`);

    await expect(
      page.getByRole("heading", { name: "DIR-ADM — Cargo DIR-ADM", level: 1 }),
    ).toBeVisible();
    await expect(page.getByRole("button", { name: "Editar" })).toBeVisible();
    await expect(
      page.getByText("Solo quien puede poner cargos en vigor cambia sus competencias.", {
        exact: true,
      }),
    ).toBeVisible();
    await expect(page.getByRole("button", { name: "Agregar competencia" })).toHaveCount(0);
    await expect(
      page.getByRole("button", { name: "Cambiar el límite de Aprobar · Contrataciones" }),
    ).toHaveCount(0);
    await expect(page.getByRole("button", { name: "Poner en vigor" })).toHaveCount(0);
    await expect(page.getByRole("button", { name: "Desactivar" })).toHaveCount(0);

    const detalleResp = await request.get(
      `${API}/gobierno/estructuras/${ANIO}/cargos/${cargo.id}`,
      { headers: mundo.headers },
    );
    expect(detalleResp.status(), await detalleResp.text()).toBe(200);
    const detalle = await detalleResp.json();
    const competenciaId = detalle.competencias[0].id;

    const patchResp = await request.patch(
      `${API}/gobierno/estructuras/${ANIO}/cargos/${cargo.id}/competencias/${competenciaId}`,
      {
        headers: { ...preparador.headers, "If-Match": '"3"' },
        data: {
          tipo_limite: "MONTO",
          monto: "100000.00",
          moneda: "USD",
          motivo: "Subir el límite",
        },
      },
    );
    expect(patchResp.status(), await patchResp.text()).toBe(403);
    const patchBody = await patchResp.json();
    expect(patchBody.code).toBe("GOV_POSITION_AUTHORITY_REQUIRED");
  });

  test("GOV3-E2E-03: consulta", async ({ page, request }) => {
    test.setTimeout(180_000);

    const mundo = await prepararMundo(request, RESPONSABLE_CARGOS);
    const tipo = await crearTipoDocumental(request, mundo.headers, mundo.companyId);
    await enteActivo(request, mundo.headers, mundo.companyId, tipo.id);
    const estructura = await estructuraVigenteApi(
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
      estructura.da01Id,
      "DIR-ADM",
    );

    const admin = await sesionApi("admintenant", { tenant: TENANT });
    const consulta = await crearUsuario(
      request,
      admin.headers,
      CONSULTA_CARGOS,
      mundo.companyId,
    );

    await entrarEnGobierno(page, consulta.username, mundo.codigo, "/gobierno/cargos");
    await expect(page.getByRole("link", { name: `Cargos ${ANIO}` })).toBeVisible();
    await page.getByRole("link", { name: `Cargos ${ANIO}` }).click();
    await page.waitForURL((u) => u.pathname === `/gobierno/cargos/${ANIO}`);
    await expect(
      page.getByRole("heading", { name: `Cargos y competencias ${ANIO}`, level: 1 }),
    ).toBeVisible();
    await expect(page.getByRole("button", { name: "Agregar cargo" })).toHaveCount(0);

    await page.getByRole("link", { name: `Abrir el cargo DIR-ADM` }).click();
    await page.waitForURL((u) => u.pathname === `/gobierno/cargos/${ANIO}/${cargo.id}`);
    await expect(
      page.getByRole("heading", { name: "DIR-ADM — Cargo DIR-ADM", level: 1 }),
    ).toBeVisible();
    await expect(page.getByRole("button", { name: "Editar" })).toHaveCount(0);
    await expect(page.getByRole("button", { name: "Agregar competencia" })).toHaveCount(0);

    const postResp = await request.post(`${API}/gobierno/estructuras/${ANIO}/cargos`, {
      headers: consulta.headers,
      data: {
        codigo: "NO-ADM",
        denominacion: "No permitido",
        unidad_id: estructura.da01Id,
        vigente_desde: `${ANIO}-01-01`,
      },
    });
    expect(postResp.status(), await postResp.text()).toBe(403);
    const postBody = await postResp.json();
    expect(postBody.code).toBe("PERMISSION_DENIED");
  });

  test("GOV3-E2E-04: otro ente", async ({ page, request }) => {
    test.setTimeout(180_000);

    const mundoA = await prepararMundo(request, RESPONSABLE_CARGOS);
    const tipoA = await crearTipoDocumental(request, mundoA.headers, mundoA.companyId);
    await enteActivo(request, mundoA.headers, mundoA.companyId, tipoA.id);
    const estructuraA = await estructuraVigenteApi(
      request,
      mundoA.headers,
      mundoA.companyId,
      tipoA.id,
      ANIO,
    );
    const cargoA = await cargoVigenteApi(
      request,
      mundoA.headers,
      mundoA.companyId,
      tipoA.id,
      ANIO,
      estructuraA.da01Id,
      "DIR-ADM",
    );

    const mundoB = await prepararMundo(request, RESPONSABLE_CARGOS);
    const tipoB = await crearTipoDocumental(request, mundoB.headers, mundoB.companyId);
    await enteActivo(request, mundoB.headers, mundoB.companyId, tipoB.id);
    await estructuraVigenteApi(
      request,
      mundoB.headers,
      mundoB.companyId,
      tipoB.id,
      ANIO,
    );

    await entrarEnGobierno(page, mundoB.username, mundoB.codigo, "/gobierno/cargos");
    await page.goto(`/gobierno/cargos/${ANIO}/${cargoA.id}`);
    await expect(
      page.getByText("El cargo no existe en este ejercicio", { exact: true }),
    ).toBeVisible();

    const getResp = await request.get(
      `${API}/gobierno/estructuras/${ANIO}/cargos/${cargoA.id}`,
      { headers: mundoB.headers },
    );
    expect(getResp.status(), await getResp.text()).toBe(404);
    const getBody = await getResp.json();
    expect(getBody.code).toBe("GOV_POSITION_NOT_FOUND");
  });

  test("GOV3-E2E-05: validaciones", async ({ page, request }) => {
    test.setTimeout(180_000);

    const mundo = await prepararMundo(request, RESPONSABLE_CARGOS);
    const tipo = await crearTipoDocumental(request, mundo.headers, mundo.companyId);
    await enteActivo(request, mundo.headers, mundo.companyId, tipo.id);
    await estructuraVigenteApi(
      request,
      mundo.headers,
      mundo.companyId,
      tipo.id,
      ANIO,
    );

    await entrarEnGobierno(page, mundo.username, mundo.codigo, "/gobierno/cargos");
    await page.getByRole("link", { name: `Cargos ${ANIO}` }).click();
    await page.waitForURL((u) => u.pathname === `/gobierno/cargos/${ANIO}`);
    await expect(
      page.getByRole("heading", { name: `Cargos y competencias ${ANIO}`, level: 1 }),
    ).toBeVisible();

    await page.getByRole("button", { name: "Agregar cargo" }).click();

    const formulario = page.getByRole("form", { name: "Registrar cargo" });
    await formulario.getByLabel(/^Código/).fill("DIR-ADM");
    await formulario.getByLabel(/^Denominación/).fill("Director de Administración");
    await formulario
      .getByLabel(/^Unidad/)
      .selectOption({ label: "DA-01 — Dirección de Administración" });
    await formulario.getByLabel(/^Vigente desde/).fill(`${ANIO}-01-01`);

    const [cargoResp] = await Promise.all([
      page.waitForResponse(
        (r) =>
          new URL(r.url()).pathname.endsWith(`/api/v1/gobierno/estructuras/${ANIO}/cargos`) &&
          r.request().method() === "POST",
        { timeout: 30_000 },
      ),
      formulario.getByRole("button", { name: "Guardar" }).click(),
    ]);
    expect(cargoResp.status()).toBe(201);
    const cargoCreado = await cargoResp.json();

    await expect(page.getByText("Cargo registrado")).toBeVisible();
    await cerrarNotificaciones(page);
    await page.waitForURL((u) => u.pathname === `/gobierno/cargos/${ANIO}/${cargoCreado.id}`);

    const competenciaRegex = new RegExp(
      `/api/v1/gobierno/estructuras/${ANIO}/cargos/[^/]+/competencias$`,
    );
    let postCount = 0;
    page.on("request", (req) => {
      if (competenciaRegex.test(new URL(req.url()).pathname) && req.method() === "POST") {
        postCount += 1;
      }
    });

    await page.getByRole("button", { name: "Agregar competencia" }).click();
    const formularioCompetencia = page.getByRole("form", {
      name: "Agregar competencia al cargo DIR-ADM",
    });
    await formularioCompetencia.getByLabel(/^Acción/).selectOption({ label: "Aprobar" });
    await formularioCompetencia.getByLabel(/^Materia/).selectOption({ label: "Contrataciones" });
    await formularioCompetencia
      .getByRole("radio", { name: "Hasta un monto por operación" })
      .check();
    await formularioCompetencia.getByLabel(/^Monto máximo por operación/).fill("0");
    await formularioCompetencia.getByLabel(/^Moneda/).selectOption({ label: "Dólares (USD)" });
    await formularioCompetencia.getByLabel(/^Fundamento/).fill("Fundamento inicial");

    const postCountAntesCero = postCount;
    await formularioCompetencia.getByRole("button", { name: "Guardar" }).click();
    await expect(
      formularioCompetencia.getByText("El monto debe ser mayor que cero", { exact: true }),
    ).toBeVisible();
    expect(postCount).toBe(postCountAntesCero);

    await formularioCompetencia.getByLabel(/^Monto máximo por operación/).fill("50000");
    const postCountAntesValida = postCount;
    const [competenciaResp] = await Promise.all([
      page.waitForResponse(
        (r) => competenciaRegex.test(new URL(r.url()).pathname) && r.request().method() === "POST",
        { timeout: 30_000 },
      ),
      formularioCompetencia.getByRole("button", { name: "Guardar" }).click(),
    ]);
    expect(competenciaResp.status()).toBe(201);
    expect(postCount).toBe(postCountAntesValida + 1);

    await expect(page.getByText("Competencia agregada")).toBeVisible();
    await cerrarNotificaciones(page);

    const postCountAntesRepetida = postCount;
    await page.getByRole("button", { name: "Agregar competencia" }).click();
    const formularioRepetida = page.getByRole("form", {
      name: "Agregar competencia al cargo DIR-ADM",
    });
    await formularioRepetida.getByLabel(/^Acción/).selectOption({ label: "Aprobar" });
    await formularioRepetida.getByLabel(/^Materia/).selectOption({ label: "Contrataciones" });
    await formularioRepetida.getByRole("radio", { name: "Sin límite" }).check();
    await formularioRepetida.getByLabel(/^Fundamento/).fill("Otra competencia");

    await formularioRepetida.getByRole("button", { name: "Guardar" }).click();
    await expect(
      formularioRepetida.getByText("El cargo ya tiene esa competencia", { exact: true }),
    ).toBeVisible();
    expect(postCount).toBe(postCountAntesRepetida);

    await page
      .getByRole("navigation", { name: "Ruta de navegación" })
      .getByRole("link", { name: `${ANIO}`, exact: true })
      .click();
    await page.waitForURL((u) => u.pathname === `/gobierno/cargos/${ANIO}`);

    await page.getByRole("button", { name: "Agregar cargo" }).click();
    const formularioRepetido = page.getByRole("form", { name: "Registrar cargo" });
    await formularioRepetido.getByLabel(/^Código/).fill("DIR-ADM");
    await formularioRepetido.getByLabel(/^Denominación/).fill("Otro director");
    await formularioRepetido
      .getByLabel(/^Unidad/)
      .selectOption({ label: "DA-01 — Dirección de Administración" });
    await formularioRepetido.getByLabel(/^Vigente desde/).fill(`${ANIO}-01-01`);

    const [repetidoCargoResp] = await Promise.all([
      page.waitForResponse(
        (r) =>
          new URL(r.url()).pathname.endsWith(`/api/v1/gobierno/estructuras/${ANIO}/cargos`) &&
          r.request().method() === "POST",
        { timeout: 30_000 },
      ),
      formularioRepetido.getByRole("button", { name: "Guardar" }).click(),
    ]);
    expect(repetidoCargoResp.status()).toBe(409);
    await expect(
      formularioRepetido.getByText("Ya existe un cargo con ese código en esta estructura", {
        exact: true,
      }),
    ).toBeVisible();
  });

  test("GOV3-E2E-06: desactivar", async ({ page, request }) => {
    test.setTimeout(180_000);

    const mundo = await prepararMundo(request, RESPONSABLE_CARGOS);
    const tipo = await crearTipoDocumental(request, mundo.headers, mundo.companyId);
    await enteActivo(request, mundo.headers, mundo.companyId, tipo.id);
    const estructura = await estructuraVigenteApi(
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
      estructura.da01Id,
      "DIR-ADM",
    );

    await entrarEnGobierno(page, mundo.username, mundo.codigo, "/gobierno/cargos");
    await page.getByRole("link", { name: `Cargos ${ANIO}` }).click();
    await page.waitForURL((u) => u.pathname === `/gobierno/cargos/${ANIO}`);
    await page.getByRole("link", { name: `Abrir el cargo DIR-ADM` }).click();
    await page.waitForURL((u) => u.pathname === `/gobierno/cargos/${ANIO}/${cargo.id}`);

    await expect(
      page.locator("main header").first().getByText("Vigente", { exact: true }),
    ).toBeVisible();

    await page.getByRole("button", { name: "Desactivar" }).click();
    const formularioDesactivar = page.getByRole("form", {
      name: "Desactivar el cargo DIR-ADM",
    });
    await expect(formularioDesactivar.getByLabel(/^Fecha de fin de vigencia/)).toHaveValue(
      `${ANIO}-12-31`,
    );
    await formularioDesactivar.getByLabel(/^Motivo/).fill("Supresión del cargo");

    const desactivarRegex = new RegExp(
      `/api/v1/gobierno/estructuras/${ANIO}/cargos/[^/]+/desactivar$`,
    );
    const [desactivarResp] = await Promise.all([
      page.waitForResponse(
        (r) => desactivarRegex.test(new URL(r.url()).pathname) && r.request().method() === "POST",
        { timeout: 30_000 },
      ),
      formularioDesactivar.getByRole("button", { name: "Desactivar cargo" }).click(),
    ]);
    expect(desactivarResp.status()).toBe(200);

    await expect(page.getByText("Cargo desactivado")).toBeVisible();
    await cerrarNotificaciones(page);
    await expect(
      page.locator("main header").first().getByText("Inactivo", { exact: true }),
    ).toBeVisible();
    await expect(
      page.getByText(
        `Cargo inactivo: su vigencia terminó el 31/12/${ANIO}; no tiene autoridad.`,
        { exact: true },
      ),
    ).toBeVisible();

    await page
      .getByRole("navigation", { name: "Ruta de navegación" })
      .getByRole("link", { name: `${ANIO}`, exact: true })
      .click();
    await page.waitForURL((u) => u.pathname === `/gobierno/cargos/${ANIO}`);
    const filaCargo = page.getByRole("row").filter({ hasText: "DIR-ADM" });
    await expect(filaCargo.getByText("Inactivo", { exact: true })).toBeVisible();
  });

  test("GOV3-E2E-07: la copia de la estructura trae los cargos vigentes (regresión de ORG-02)", async ({
    request,
  }) => {
    test.setTimeout(180_000);

    const mundo = await prepararMundo(request, RESPONSABLE_CARGOS);
    const tipo = await crearTipoDocumental(request, mundo.headers, mundo.companyId);
    await enteActivo(request, mundo.headers, mundo.companyId, tipo.id);
    const estructura = await estructuraVigenteApi(
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
      estructura.da01Id,
      "DIR-ADM",
    );

    const copiarResp = await request.post(`${API}/gobierno/estructuras`, {
      headers: mundo.headers,
      data: { ejercicio: ANIO + 1, copiar_de: ANIO },
    });
    expect(copiarResp.status(), await copiarResp.text()).toBe(201);

    const getResp = await request.get(`${API}/gobierno/estructuras/${ANIO + 1}/cargos`, {
      headers: mundo.headers,
    });
    expect(getResp.status(), await getResp.text()).toBe(200);
    const cargos = await getResp.json();
    const cargoCopiado = cargos.items?.find((c: { codigo: string }) => c.codigo === "DIR-ADM");
    expect(cargoCopiado).toBeTruthy();
    expect(cargoCopiado.estado).toBe("BORRADOR");
    expect(cargoCopiado.version).toBe(1);
  });

  test("GOV3-E2E-08: accesibilidad", async ({ page, request }) => {
    test.setTimeout(180_000);

    const mundo = await prepararMundo(request, RESPONSABLE_CARGOS);
    const tipo = await crearTipoDocumental(request, mundo.headers, mundo.companyId);
    await enteActivo(request, mundo.headers, mundo.companyId, tipo.id);
    const estructura = await estructuraVigenteApi(
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
      estructura.da01Id,
      "DIR-ADM",
    );

    await entrarEnGobierno(page, mundo.username, mundo.codigo, "/gobierno/cargos");
    await page.getByRole("link", { name: `Cargos ${ANIO}` }).click();
    await page.waitForURL((u) => u.pathname === `/gobierno/cargos/${ANIO}`);
    await expect(
      page.getByRole("heading", { name: `Cargos y competencias ${ANIO}`, level: 1 }),
    ).toBeVisible();

    for (const width of [1280, 768, 320]) {
      await page.setViewportSize({ width, height: 900 });

      const resultadosEjercicio = await new AxeBuilder({ page }).include("main").withTags(WCAG).analyze();
      const seriasEjercicio = resultadosEjercicio.violations.filter((v) =>
        ["critical", "serious"].includes(v.impact ?? ""),
      );
      expect(
        seriasEjercicio.map((v) => ({ id: v.id, help: v.help })),
        `Violaciones serias en el ejercicio a ${width}px`,
      ).toEqual([]);

      if (width === 320) {
        const sinDesbordamientoEjercicio = await page.evaluate(
          () => document.documentElement.scrollWidth <= document.documentElement.clientWidth,
        );
        expect(sinDesbordamientoEjercicio).toBe(true);
      }
    }

    await page.setViewportSize({ width: 1280, height: 900 });
    await page.getByRole("link", { name: `Abrir el cargo DIR-ADM` }).click();
    await page.waitForURL((u) => u.pathname === `/gobierno/cargos/${ANIO}/${cargo.id}`);
    await expect(
      page.getByRole("heading", { name: "DIR-ADM — Cargo DIR-ADM", level: 1 }),
    ).toBeVisible();

    for (const width of [1280, 768, 320]) {
      await page.setViewportSize({ width, height: 900 });

      const resultadosCargo = await new AxeBuilder({ page }).include("main").withTags(WCAG).analyze();
      const seriasCargo = resultadosCargo.violations.filter((v) =>
        ["critical", "serious"].includes(v.impact ?? ""),
      );
      expect(
        seriasCargo.map((v) => ({ id: v.id, help: v.help })),
        `Violaciones serias en el cargo a ${width}px`,
      ).toEqual([]);

      if (width === 320) {
        const sinDesbordamientoCargo = await page.evaluate(
          () => document.documentElement.scrollWidth <= document.documentElement.clientWidth,
        );
        expect(sinDesbordamientoCargo).toBe(true);
      }
    }
  });
});
