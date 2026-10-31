import AxeBuilder from "@axe-core/playwright";
import { type APIRequestContext } from "@playwright/test";
import { declararAlcance } from "./helpers/usuario";
import { entrarComoUsuario, expect, sesionApi, test } from "./helpers/sesion";
import {
  ANIO,
  API,
  CONSULTA_ESTRUCTURA,
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

async function abrirEstructuraApi(
  request: APIRequestContext,
  headers: Record<string, string>,
  ejercicio: number,
  copiarDe?: number,
): Promise<{ id: string; version: number }> {
  const resp = await request.post(`${API}/gobierno/estructuras`, {
    headers,
    data: { ejercicio, copiar_de: copiarDe ?? null },
  });
  expect(es2xx(resp.status()), await resp.text()).toBe(true);
  const body = await resp.json();
  return { id: body.id, version: body.version };
}

async function crearUnidadApi(
  request: APIRequestContext,
  headers: Record<string, string>,
  ejercicio: number,
  data: Record<string, unknown>,
): Promise<{ id: string; version: number }> {
  const resp = await request.post(`${API}/gobierno/estructuras/${ejercicio}/unidades`, {
    headers,
    data,
  });
  expect(es2xx(resp.status()), await resp.text()).toBe(true);
  const body = await resp.json();
  return { id: body.id, version: body.version };
}

async function publicarEstructuraApi(
  request: APIRequestContext,
  headers: Record<string, string>,
  ejercicio: number,
  version: number,
): Promise<void> {
  const resp = await request.post(`${API}/gobierno/estructuras/${ejercicio}/publicar`, {
    headers: { ...headers, "If-Match": `"${version}"` },
  });
  expect(resp.status(), await resp.text()).toBe(200);
}

async function cerrarEstructuraApi(
  request: APIRequestContext,
  headers: Record<string, string>,
  ejercicio: number,
  version: number,
): Promise<void> {
  const resp = await request.post(`${API}/gobierno/estructuras/${ejercicio}/cerrar`, {
    headers: { ...headers, "If-Match": `"${version}"` },
  });
  expect(resp.status(), await resp.text()).toBe(200);
}

async function prepararBorradorConUnidades(
  request: APIRequestContext,
  headers: Record<string, string>,
  ejercicio: number,
): Promise<{ estructuraId: string; despId: string; da01Id: string }> {
  const estructura = await abrirEstructuraApi(request, headers, ejercicio);
  const desp = await crearUnidadApi(request, headers, ejercicio, {
    codigo: "DESP",
    denominacion: "Despacho del Alcalde",
    tipo: "ORGANO",
    unidad_superior_id: null,
    vigente_desde: `${ejercicio}-01-01`,
  });
  const da01 = await crearUnidadApi(request, headers, ejercicio, {
    codigo: "DA-01",
    denominacion: "Dirección de Administración",
    tipo: "UNIDAD_ADMINISTRATIVA",
    unidad_superior_id: desp.id,
    vigente_desde: `${ejercicio}-01-01`,
  });
  return { estructuraId: estructura.id, despId: desp.id, da01Id: da01.id };
}

test.describe("Gobierno · Estructura organizativa (GOV-0-02)", () => {
  test("GOV2-E2E-01: el responsable abre el ejercicio, registra unidades, pone en vigor, modifica con motivo, desactiva y exporta", async ({
    page,
    request,
  }) => {
    test.setTimeout(240_000);

    const mundo = await prepararMundo(request, RESPONSABLE_ESTRUCTURA);
    const tipo = await crearTipoDocumental(request, mundo.headers, mundo.companyId);
    await enteActivo(request, mundo.headers, mundo.companyId, tipo.id);
    await entrarEnGobierno(page, mundo.username, mundo.codigo, "/gobierno/estructura");

    await expect(page.locator('nav[aria-label="Menú principal"]').getByText("Estructura organizativa", { exact: true })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Estructura organizativa", level: 1 })).toBeVisible();

    const formulario = page.getByRole("form", { name: "Abrir la estructura de un ejercicio" });
    await formulario.getByLabel(/^Ejercicio/).fill(String(ANIO));

    const [abrirResp] = await Promise.all([
      page.waitForResponse(
        (r) => new URL(r.url()).pathname.endsWith("/api/v1/gobierno/estructuras") && r.request().method() === "POST",
        { timeout: 30_000 },
      ),
      formulario.getByRole("button", { name: "Abrir estructura" }).click(),
    ]);
    expect(abrirResp.status()).toBe(201);

    await page.waitForURL((u) => u.pathname === `/gobierno/estructura/${ANIO}`);
    await expect(page.getByRole("heading", { name: `Estructura organizativa ${ANIO}`, level: 1 })).toBeVisible();
    await expect(page.locator("main header").first().getByText("Borrador", { exact: true })).toBeVisible();

    await page.getByRole("button", { name: "Agregar unidad" }).click();
    const formularioUnidad = page.getByRole("form", { name: "Nueva unidad" });
    await formularioUnidad.getByLabel(/^Código/).fill("DESP");
    await formularioUnidad.getByLabel(/^Denominación/).fill("Despacho del Alcalde");
    await formularioUnidad.getByLabel(/^Tipo de unidad/).selectOption({ label: "Órgano" });

    const [unidadResp] = await Promise.all([
      page.waitForResponse(
        (r) => new URL(r.url()).pathname.endsWith(`/api/v1/gobierno/estructuras/${ANIO}/unidades`) && r.request().method() === "POST",
        { timeout: 30_000 },
      ),
      formularioUnidad.getByRole("button", { name: "Guardar" }).click(),
    ]);
    expect(unidadResp.status()).toBe(201);

    await expect(page.getByText("Unidad registrada")).toBeVisible();
    await cerrarNotificaciones(page);

    await page.getByRole("button", { name: "Agregar subordinada a DESP" }).click();
    const formularioSub = page.getByRole("form", { name: "Nueva unidad" });
    await formularioSub.getByLabel(/^Código/).fill("DA-01");
    await formularioSub.getByLabel(/^Denominación/).fill("Dirección de Administración");
    await formularioSub.getByLabel(/^Tipo de unidad/).selectOption({ label: "Unidad administrativa" });

    const [subResp] = await Promise.all([
      page.waitForResponse(
        (r) => new URL(r.url()).pathname.endsWith(`/api/v1/gobierno/estructuras/${ANIO}/unidades`) && r.request().method() === "POST",
        { timeout: 30_000 },
      ),
      formularioSub.getByRole("button", { name: "Guardar" }).click(),
    ]);
    expect(subResp.status()).toBe(201);

    await expect(page.getByText("Unidad registrada")).toBeVisible();
    await cerrarNotificaciones(page);

    const filaDA01 = page.getByRole("row").filter({ hasText: "DA-01" });
    await expect(filaDA01.getByText("Nivel 2.", { exact: true })).toHaveCount(1);
    await expect(filaDA01.getByText("DESP", { exact: true })).toBeVisible();

    const requisitos = page.getByRole("region", { name: "Requisitos para poner en vigor" });
    await expect(requisitos.getByText("Acto que aprueba la estructura")).toBeVisible();
    await expect(page.getByRole("button", { name: "Poner en vigor" })).toBeDisabled();

    const acto = page.getByRole("region", { name: "Acto que aprueba la estructura" }).first();
    await acto.getByLabel("Tipo documental del archivo").selectOption({ label: tipo.name });
    await acto.getByLabel(/^Archivo/).setInputFiles({
      name: "acto.pdf",
      mimeType: "application/pdf",
      buffer: PDF,
    });

    const [vinculoResp] = await Promise.all([
      page.waitForResponse(
        (r) => /\/api\/v1\/documentos\/[^/]+\/vinculos$/.test(new URL(r.url()).pathname) && r.request().method() === "POST",
        { timeout: 60_000 },
      ),
      acto.getByRole("button", { name: "Adjuntar" }).click(),
    ]);
    expect(es2xx(vinculoResp.status()), await vinculoResp.text()).toBe(true);

    await expect(page.getByText("Documento adjuntado")).toBeVisible({ timeout: 30_000 });
    await cerrarNotificaciones(page);
    await expect(requisitos.getByText("La estructura está completa y puede ponerse en vigor.")).toBeVisible();
    await expect(page.getByRole("button", { name: "Poner en vigor" })).toBeEnabled();

    await page.getByRole("button", { name: "Poner en vigor" }).click();
    await expect(page.getByRole("dialog")).toBeVisible();
    await expect(page.getByRole("dialog").getByText(`¿Poner en vigor la estructura de ${ANIO}?`)).toBeVisible();

    const [publicarResp] = await Promise.all([
      page.waitForResponse(
        (r) => new URL(r.url()).pathname.endsWith(`/api/v1/gobierno/estructuras/${ANIO}/publicar`) && r.request().method() === "POST",
        { timeout: 30_000 },
      ),
      page.getByRole("dialog").getByRole("button", { name: "Poner en vigor" }).click(),
    ]);
    expect(publicarResp.status()).toBe(200);

    await expect(page.getByText("Estructura en vigor")).toBeVisible();
    await cerrarNotificaciones(page);
    await expect(page.locator("main header").first().getByText("Vigente", { exact: true })).toBeVisible();

    const patchRegex = new RegExp(`/api/v1/gobierno/estructuras/${ANIO}/unidades/[^/]+$`);
    let patchCount = 0;
    page.on("request", (req) => {
      if (patchRegex.test(new URL(req.url()).pathname) && req.method() === "PATCH") {
        patchCount += 1;
      }
    });

    await page.getByRole("button", { name: "Editar DA-01" }).click();
    const formularioEditar = page.getByRole("form", { name: "Editar la unidad DA-01" });
    await formularioEditar.getByLabel(/^Denominación/).fill("Dirección General de Administración");
    await formularioEditar.getByRole("button", { name: "Guardar" }).click();
    await expect(page.getByText("Indique el motivo (de 5 a 255 caracteres)")).toBeVisible();
    expect(patchCount).toBe(0);

    await formularioEditar.getByLabel(/^Motivo/).fill("Reorganización aprobada");

    const [editarResp] = await Promise.all([
      page.waitForResponse(
        (r) => patchRegex.test(new URL(r.url()).pathname) && r.request().method() === "PATCH",
        { timeout: 30_000 },
      ),
      formularioEditar.getByRole("button", { name: "Guardar" }).click(),
    ]);
    expect(editarResp.status()).toBe(200);

    await expect(page.getByText("Unidad actualizada")).toBeVisible();
    await cerrarNotificaciones(page);

    await page.getByRole("button", { name: "Historial de DA-01" }).click();
    const historial = page.getByRole("region", { name: "Historial de la unidad DA-01" });
    await expect(historial).toBeVisible();
    await expect(historial.getByRole("row")).toHaveCount(3);
    await expect(historial.getByRole("cell", { name: "Reorganización aprobada", exact: true })).toBeVisible();
    await historial.getByRole("button", { name: "Cerrar historial", exact: true }).click();

    await page.getByRole("button", { name: "Agregar subordinada a DA-01" }).click();
    const formularioCG = page.getByRole("form", { name: "Nueva unidad" });
    await formularioCG.getByLabel(/^Código/).fill("CG1");
    await formularioCG.getByLabel(/^Denominación/).fill("Centro de costos");
    await formularioCG.getByLabel(/^Tipo de unidad/).selectOption({ label: "Centro gestor" });
    await formularioCG.getByLabel(/^Motivo/).fill("Nuevo centro gestor");

    const [cgResp] = await Promise.all([
      page.waitForResponse(
        (r) => new URL(r.url()).pathname.endsWith(`/api/v1/gobierno/estructuras/${ANIO}/unidades`) && r.request().method() === "POST",
        { timeout: 30_000 },
      ),
      formularioCG.getByRole("button", { name: "Guardar" }).click(),
    ]);
    expect(cgResp.status()).toBe(201);

    await expect(page.getByText("Unidad registrada")).toBeVisible();
    await cerrarNotificaciones(page);

    await page.getByRole("button", { name: "Desactivar CG1" }).click();
    const formularioDesactivar = page.getByRole("form", { name: "Desactivar la unidad CG1" });
    await formularioDesactivar.getByLabel(/^Motivo/).fill("Supresión del centro");

    const desactivarRegex = new RegExp(`/api/v1/gobierno/estructuras/${ANIO}/unidades/[^/]+/desactivar$`);
    const [desactivarResp] = await Promise.all([
      page.waitForResponse(
        (r) => desactivarRegex.test(new URL(r.url()).pathname) && r.request().method() === "POST",
        { timeout: 30_000 },
      ),
      formularioDesactivar.getByRole("button", { name: "Desactivar unidad" }).click(),
    ]);
    expect(desactivarResp.status()).toBe(200);

    await expect(page.getByText("Unidad desactivada")).toBeVisible();
    await cerrarNotificaciones(page);

    const filaCG1 = page.getByRole("row").filter({ hasText: "CG1" });
    await expect(filaCG1.getByText("Inactiva", { exact: true })).toBeVisible();

    const downloadPromise = page.waitForEvent("download");
    await page.getByRole("button", { name: "Exportar CSV" }).click();
    const download = await downloadPromise;
    expect(download.suggestedFilename()).toBe(`estructura-${ANIO}.csv`);
    const stream = await download.createReadStream();
    const chunks: Buffer[] = [];
    for await (const chunk of stream) {
      chunks.push(Buffer.isBuffer(chunk) ? chunk : Buffer.from(chunk));
    }
    const contenido = Buffer.concat(chunks).toString("utf8");
    expect(contenido.startsWith("codigo,denominacion,tipo,codigo_superior,nivel,estado,vigente_desde,vigente_hasta")).toBe(true);

    const estructuraResp = await request.get(`${API}/gobierno/estructuras/${ANIO}`, { headers: mundo.headers });
    expect(estructuraResp.status(), await estructuraResp.text()).toBe(200);
    const estructura = await estructuraResp.json();

    const admin = await sesionApi("admintenant", { tenant: TENANT });
    const auditEstructuraResp = await request.get(
      `${API}/audit/events?entity_type=GovernmentStructure&entity_id=${estructura.id}&page_size=50`,
      { headers: admin.headers },
    );
    expect(auditEstructuraResp.status(), await auditEstructuraResp.text()).toBe(200);
    const auditEstructura = await auditEstructuraResp.json();
    const accionesEstructura = auditEstructura.items.map((e: { action: string }) => e.action);
    expect(accionesEstructura).toContain("GOV_STRUCTURE_CREATED");
    expect(accionesEstructura).toContain("GOV_STRUCTURE_PUBLISHED");
    expect(accionesEstructura).toContain("GOV_STRUCTURE_EXPORTED");

    const auditUnidadesResp = await request.get(
      `${API}/audit/events?entity_type=GovernmentUnit&page_size=100`,
      { headers: admin.headers },
    );
    expect(auditUnidadesResp.status(), await auditUnidadesResp.text()).toBe(200);
    const auditUnidades = await auditUnidadesResp.json();
    const eventosEmpresa = auditUnidades.items.filter(
      (e: { company_id?: string }) => e.company_id === mundo.companyId,
    );
    const actualizacionConMotivo = eventosEmpresa.find(
      (e: { action: string; reason?: string }) =>
        e.action === "GOV_UNIT_UPDATED" && e.reason === "Reorganización aprobada",
    );
    expect(actualizacionConMotivo).toBeTruthy();
    const desactivacion = eventosEmpresa.find(
      (e: { action: string; reason?: string }) =>
        e.action === "GOV_UNIT_DEACTIVATED" && e.reason === "Supresión del centro",
    );
    expect(desactivacion).toBeTruthy();
  });

  test("GOV2-E2E-02: copia y cierre", async ({ page, request }) => {
    test.setTimeout(120_000);

    const mundo = await prepararMundo(request, RESPONSABLE_ESTRUCTURA);
    const tipo = await crearTipoDocumental(request, mundo.headers, mundo.companyId);
    await enteActivo(request, mundo.headers, mundo.companyId, tipo.id);

    const ejercicioAnterior = ANIO - 1;
    const estructuraAnterior = await abrirEstructuraApi(request, mundo.headers, ejercicioAnterior);
    await crearUnidadApi(request, mundo.headers, ejercicioAnterior, {
      codigo: "DESP",
      denominacion: "Despacho del Alcalde",
      tipo: "ORGANO",
      unidad_superior_id: null,
      vigente_desde: `${ejercicioAnterior}-01-01`,
    });
    await adjuntarDocumentoApi(request, mundo.headers, mundo.companyId, tipo.id, "GovernmentStructure", estructuraAnterior.id);
    await publicarEstructuraApi(request, mundo.headers, ejercicioAnterior, estructuraAnterior.version);
    await cerrarEstructuraApi(request, mundo.headers, ejercicioAnterior, estructuraAnterior.version + 1);

    await entrarEnGobierno(page, mundo.username, mundo.codigo, "/gobierno/estructura");

    const lista = page.getByRole("region", { name: "Estructuras por ejercicio" });
    await expect(lista.getByText(`Estructura ${ejercicioAnterior}`, { exact: true })).toBeVisible();
    await expect(lista.getByRole("cell", { name: "Cerrada", exact: true })).toBeVisible();

    await lista.getByRole("link", { name: `Estructura ${ejercicioAnterior}` }).click();
    await page.waitForURL((u) => u.pathname === `/gobierno/estructura/${ejercicioAnterior}`);
    await expect(page.getByText("Estructura de un ejercicio cerrado: solo lectura.")).toBeVisible();
    await expect(page.getByRole("button", { name: "Agregar unidad" })).toHaveCount(0);

    await page
      .getByRole("navigation", { name: "Ruta de navegación" })
      .getByRole("link", { name: "Estructura organizativa", exact: true })
      .click();
    await page.waitForURL((u) => u.pathname === "/gobierno/estructura");

    const formulario = page.getByRole("form", { name: "Abrir la estructura de un ejercicio" });
    await formulario.getByLabel(/^Ejercicio/).fill(String(ANIO + 1));
    await formulario.getByLabel(/^Copiar del ejercicio/).selectOption({ label: `${ejercicioAnterior} · Cerrada` });

    const [copiarResp] = await Promise.all([
      page.waitForResponse(
        (r) => new URL(r.url()).pathname.endsWith("/api/v1/gobierno/estructuras") && r.request().method() === "POST",
        { timeout: 30_000 },
      ),
      formulario.getByRole("button", { name: "Abrir estructura" }).click(),
    ]);
    expect(copiarResp.status()).toBe(201);

    await page.waitForURL((u) => u.pathname === `/gobierno/estructura/${ANIO + 1}`);
    await expect(page.getByRole("heading", { name: `Estructura organizativa ${ANIO + 1}`, level: 1 })).toBeVisible();
    await expect(page.locator("main header").first().getByText("Borrador", { exact: true })).toBeVisible();

    const filaDESP = page.getByRole("row").filter({ hasText: "DESP" });
    await expect(filaDESP.getByText(`01/01/${ANIO + 1}`, { exact: false })).toBeVisible();
  });

  test("GOV2-E2E-03: consulta sin capacidad", async ({ page, request }) => {
    test.setTimeout(120_000);

    const mundo = await prepararMundo(request, RESPONSABLE_ESTRUCTURA);
    const tipo = await crearTipoDocumental(request, mundo.headers, mundo.companyId);
    await enteActivo(request, mundo.headers, mundo.companyId, tipo.id);
    await prepararBorradorConUnidades(request, mundo.headers, ANIO);

    const admin = await sesionApi("admintenant", { tenant: TENANT });
    const consulta = await crearUsuario(request, admin.headers, CONSULTA_ESTRUCTURA, mundo.companyId);

    await entrarEnGobierno(page, consulta.username, mundo.codigo, "/gobierno/estructura");
    await page.getByRole("link", { name: `Estructura ${ANIO}` }).click();
    await page.waitForURL((u) => u.pathname === `/gobierno/estructura/${ANIO}`);

    await expect(page.getByRole("heading", { name: `Estructura organizativa ${ANIO}`, level: 1 })).toBeVisible();
    await expect(page.getByRole("button", { name: "Exportar CSV" })).toBeVisible();
    await expect(page.getByRole("button", { name: "Agregar unidad" })).toHaveCount(0);
    await expect(page.getByRole("button", { name: "Editar DESP" })).toHaveCount(0);
    await expect(page.getByRole("button", { name: "Poner en vigor" })).toHaveCount(0);

    const postResp = await request.post(`${API}/gobierno/estructuras/${ANIO}/unidades`, {
      headers: consulta.headers,
      data: {
        codigo: "NO",
        denominacion: "No permitido",
        tipo: "ORGANO",
        unidad_superior_id: null,
      },
    });
    expect(postResp.status(), await postResp.text()).toBe(403);
    const postBody = await postResp.json();
    expect(postBody.code).toBe("PERMISSION_DENIED");
  });

  test("GOV2-E2E-04: otro ente", async ({ request }) => {
    test.setTimeout(120_000);

    const mundoA = await prepararMundo(request, RESPONSABLE_ESTRUCTURA);
    const mundoB = await prepararMundo(request, RESPONSABLE_ESTRUCTURA);

    const tipoA = await crearTipoDocumental(request, mundoA.headers, mundoA.companyId);
    await enteActivo(request, mundoA.headers, mundoA.companyId, tipoA.id);
    const tipoB = await crearTipoDocumental(request, mundoB.headers, mundoB.companyId);
    await enteActivo(request, mundoB.headers, mundoB.companyId, tipoB.id);

    await prepararBorradorConUnidades(request, mundoA.headers, ANIO);
    const estructuraB = await prepararBorradorConUnidades(request, mundoB.headers, ANIO);

    const headersAEnB = {
      ...mundoA.headers,
      "X-Kontrol-Company": mundoB.companyId,
    };

    const getResp = await request.get(`${API}/gobierno/estructuras`, { headers: headersAEnB });
    expect(getResp.status(), await getResp.text()).toBe(404);
    const getBody = await getResp.json();
    expect(getBody.code).toBe("COMPANY_NOT_FOUND");

    const patchResp = await request.patch(`${API}/gobierno/estructuras/${ANIO}/unidades/${estructuraB.despId}`, {
      headers: { ...mundoA.headers, "If-Match": '"1"' },
      data: { denominacion: "Intruso" },
    });
    expect(patchResp.status(), await patchResp.text()).toBe(404);
    const patchBody = await patchResp.json();
    expect(patchBody.code).toBe("GOV_UNIT_NOT_FOUND");
  });

  test("GOV2-E2E-05: jerarquía y versión", async ({ request }) => {
    test.setTimeout(120_000);

    const mundo = await prepararMundo(request, RESPONSABLE_ESTRUCTURA);
    const tipo = await crearTipoDocumental(request, mundo.headers, mundo.companyId);
    await enteActivo(request, mundo.headers, mundo.companyId, tipo.id);

    const unidades = await prepararBorradorConUnidades(request, mundo.headers, ANIO);

    const cicloResp = await request.patch(`${API}/gobierno/estructuras/${ANIO}/unidades/${unidades.despId}`, {
      headers: { ...mundo.headers, "If-Match": '"1"' },
      data: { unidad_superior_id: unidades.da01Id },
    });
    expect(cicloResp.status(), await cicloResp.text()).toBe(422);
    const cicloBody = await cicloResp.json();
    expect(cicloBody.code).toBe("GOV_UNIT_HIERARCHY_CYCLE");

    const patch1Resp = await request.patch(`${API}/gobierno/estructuras/${ANIO}/unidades/${unidades.da01Id}`, {
      headers: { ...mundo.headers, "If-Match": '"1"' },
      data: { denominacion: "Dirección de Administración A" },
    });
    expect(patch1Resp.status(), await patch1Resp.text()).toBe(200);

    const patch2Resp = await request.patch(`${API}/gobierno/estructuras/${ANIO}/unidades/${unidades.da01Id}`, {
      headers: { ...mundo.headers, "If-Match": '"1"' },
      data: { denominacion: "Dirección de Administración B" },
    });
    expect(patch2Resp.status(), await patch2Resp.text()).toBe(409);
    const patch2Body = await patch2Resp.json();
    expect(patch2Body.code).toBe("GOV_UNIT_STALE");

    const publicarSinIfMatchResp = await request.post(`${API}/gobierno/estructuras/${ANIO}/publicar`, {
      headers: mundo.headers,
    });
    expect(publicarSinIfMatchResp.status(), await publicarSinIfMatchResp.text()).toBe(428);
  });

  test("GOV2-E2E-06: compuerta en Gobierno dice ente (GOV0-UI-01)", async ({ page, request }) => {
    test.setTimeout(120_000);

    const mundoA = await prepararMundo(request, RESPONSABLE_ESTRUCTURA);
    const mundoB = await prepararMundo(request, RESPONSABLE_ESTRUCTURA);

    await declararAlcance(mundoA.username, [mundoA.companyId, mundoB.companyId], TENANT);

    await entrarComoUsuario(page, mundoA.username, { tenant: TENANT, ruta: "/gobierno/estructura" });

    await expect(page.getByRole("heading", { name: "Seleccione un ente" })).toBeVisible();
    await page.getByTestId(`elegir-empresa-${mundoA.codigo}`).click();

    const selector = page.locator("header").getByRole("button", { name: /^Ente activo/ });
    await expect(selector).toBeVisible();
  });

  test("GOV2-E2E-07: accesibilidad", async ({ page, request }) => {
    test.setTimeout(120_000);

    const mundo = await prepararMundo(request, RESPONSABLE_ESTRUCTURA);
    const tipo = await crearTipoDocumental(request, mundo.headers, mundo.companyId);
    await enteActivo(request, mundo.headers, mundo.companyId, tipo.id);
    await prepararBorradorConUnidades(request, mundo.headers, ANIO);

    await entrarEnGobierno(page, mundo.username, mundo.codigo, "/gobierno/estructura");
    await page.getByRole("link", { name: `Estructura ${ANIO}` }).click();
    await page.waitForURL((u) => u.pathname === `/gobierno/estructura/${ANIO}`);
    await expect(page.getByRole("heading", { name: `Estructura organizativa ${ANIO}`, level: 1 })).toBeVisible();

    for (const width of [1280, 768, 320]) {
      await page.setViewportSize({ width, height: 900 });

      const resultados = await new AxeBuilder({ page }).include("main").withTags(WCAG).analyze();
      const serias = resultados.violations.filter((v) => ["critical", "serious"].includes(v.impact ?? ""));
      expect(
        serias.map((v) => ({ id: v.id, help: v.help })),
        `Violaciones serias a ${width}px`,
      ).toEqual([]);

      if (width === 320) {
        const sinDesbordamiento = await page.evaluate(
          () => document.documentElement.scrollWidth <= document.documentElement.clientWidth,
        );
        expect(sinDesbordamiento).toBe(true);
      }
    }
  });
});
