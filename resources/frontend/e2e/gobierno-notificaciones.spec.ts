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
import type { APIRequestContext, Page } from "@playwright/test";

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

const RESPONSABLE_NOTIFICACIONES = [
  ...RESPONSABLE_ACTOS,
  "gobierno_notificaciones:view",
  "gobierno_notificaciones:edit",
  "gobierno_notificaciones:record",
];

const CONSULTA_NOTIFICACIONES = [
  "organization:view",
  "gobierno_actos:view",
  "gobierno_notificaciones:view",
  "documentos:view",
];

function ddmmaaaa(iso: string): string {
  const [year, month, day] = iso.split("-");
  return `${day}/${month}/${year}`;
}

function hoyCaracas(): string {
  return new Intl.DateTimeFormat("en-CA", { timeZone: "America/Caracas" }).format(
    new Date(),
  );
}

function fechaMasDias(iso: string, dias: number): string {
  const fecha = new Date(`${iso}T12:00:00Z`);
  fecha.setUTCDate(fecha.getUTCDate() + dias);
  return fecha.toISOString().slice(0, 10);
}

async function mundoConCargo(request: APIRequestContext) {
  const mundo = await prepararMundo(request, RESPONSABLE_NOTIFICACIONES);
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

async function actoParticularEmitidoApi(
  request: APIRequestContext,
  mundo: { headers: Record<string, string>; companyId: string; codigo: string },
  tipoId: string,
  cargoId: string,
  numero: string,
): Promise<{ id: string }> {
  const resp = await request.post(`${API}/gobierno/actos`, {
    headers: mundo.headers,
    data: {
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
    },
  });
  expect(resp.status(), await resp.text()).toBe(201);
  const id = (await resp.json()).id;

  await adjuntarDocumentoApi(
    request,
    mundo.headers,
    mundo.companyId,
    tipoId,
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

  return { id };
}

async function adjuntarDocumentoNotificacionApi(
  request: APIRequestContext,
  headers: Record<string, string>,
  companyId: string,
  tipoId: string,
  notificacionId: string,
): Promise<void> {
  await adjuntarDocumentoApi(
    request,
    headers,
    companyId,
    tipoId,
    "GovernmentNotification",
    notificacionId,
  );
}

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

test.describe("Gobierno · Notificaciones administrativas (DOC-04)", () => {
  test("DOC4-E2E-01: la dueña gestiona el ciclo completo de notificación desde un acto particular emitido", async ({
    page,
    request,
  }) => {
    test.setTimeout(240_000);

    const hoy = hoyCaracas();
    const hoyMas15 = fechaMasDias(hoy, 15);

    const { mundo, tipo, cargoId } = await mundoConCargo(request);
    const acto = await actoParticularEmitidoApi(
      request,
      mundo,
      tipo.id,
      cargoId,
      `DA-200-${ANIO}`,
    );

    await entrarEnGobierno(page, mundo.username, mundo.codigo, "/gobierno/notificaciones");

    await expect(
      page.getByRole("heading", { name: "Notificaciones administrativas", level: 1 }),
    ).toBeVisible();
    await expect(page.getByText(`Sin notificaciones en ${ANIO}`)).toBeVisible();

    await page.goto(`/gobierno/actos/${acto.id}`);
    await expect(
      page.getByRole("heading", { name: `Resolución Nº DA-200-${ANIO}`, level: 1 }),
    ).toBeVisible();

    const seccionNotificaciones = page.getByRole("heading", {
      name: "Notificaciones",
      level: 2,
    });
    await expect(seccionNotificaciones).toBeVisible();
    await expect(
      page.getByText("Agregue a cada interesado para notificarle el acto (LOPA art. 73)."),
    ).toBeVisible();

    await page.getByRole("button", { name: "Agregar destinatario" }).click();
    const formAgregar = page.getByRole("form", { name: "Agregar destinatario" });
    await expect(
      formAgregar.getByRole("heading", { name: "Agregar destinatario", level: 3 }),
    ).toBeVisible();

    await formAgregar.getByRole("radio", { name: "Persona natural" }).check();
    await formAgregar.getByLabel(/^Nombre o razón social/).fill("Pedro Pérez");
    await formAgregar.getByLabel(/^Cédula o RIF/).fill("V-12345678");
    await formAgregar.getByLabel(/^Domicilio o residencia/).fill("Avenida Siempreviva 742");
    await formAgregar.getByLabel(/^Recursos que proceden/).fill("Reconsideración");

    const [postPedroResp] = await Promise.all([
      page.waitForResponse(
        (r) =>
          new URL(r.url()).pathname.endsWith("/gobierno/notificaciones") &&
          r.request().method() === "POST",
        { timeout: 60_000 },
      ),
      formAgregar
        .getByRole("button", { name: "Agregar destinatario" })
        .click(),
    ]);
    expect(postPedroResp.status()).toBe(201);
    await expect(page.getByText("Destinatario agregado")).toBeVisible();
    await cerrarNotificaciones(page);

    await page.getByRole("button", { name: "Agregar destinatario" }).click();
    await formAgregar.getByRole("radio", { name: "Persona jurídica" }).check();
    await formAgregar.getByLabel(/^Nombre o razón social/).fill("Comercial Ejemplo C.A.");
    await formAgregar.getByLabel(/^Cédula o RIF/).fill("J-12345678-9");
    await formAgregar.getByLabel(/^Domicilio o residencia/).fill("Centro Empresarial, piso 4");
    await formAgregar.getByLabel(/^Apoderado \(opcional\)/).fill("Laura Rojas");
    await formAgregar.getByLabel(/^Cédula del apoderado/).fill("V-11222333");
    await formAgregar.getByLabel(/^Recursos que proceden/).fill("Reconsideración");

    const [postComercialResp] = await Promise.all([
      page.waitForResponse(
        (r) =>
          new URL(r.url()).pathname.endsWith("/gobierno/notificaciones") &&
          r.request().method() === "POST",
        { timeout: 60_000 },
      ),
      formAgregar
        .getByRole("button", { name: "Agregar destinatario" })
        .click(),
    ]);
    expect(postComercialResp.status()).toBe(201);
    await expect(page.getByText("Destinatario agregado")).toBeVisible();
    await cerrarNotificaciones(page);

    await expect(
      page.getByText("Faltan 2 por notificar de 2.", { exact: true }),
    ).toBeVisible();

    const linkPedro = page.getByRole("link", {
      name: "Pedro Pérez",
      exact: true,
    });
    await linkPedro.click();
    await page.waitForURL((u) => /\/gobierno\/notificaciones\/[^/]+$/.test(u.pathname));
    await expect(
      page.getByRole("heading", { name: "Notificación a Pedro Pérez", level: 1 }),
    ).toBeVisible();

    const pedroId = page.url().split("/").pop()!;
    await adjuntarDocumentoNotificacionApi(
      request,
      mundo.headers,
      mundo.companyId,
      tipo.id,
      pedroId,
    );
    await adjuntarDocumentoNotificacionApi(
      request,
      mundo.headers,
      mundo.companyId,
      tipo.id,
      pedroId,
    );

    await page.reload();
    await expect(
      page.getByRole("heading", { name: "Notificación a Pedro Pérez", level: 1 }),
    ).toBeVisible();
    await expect(page.getByText("Pendiente de notificar.", { exact: true })).toBeVisible();

    await page.getByRole("button", { name: "Registrar entrega" }).click();
    const formEntrega = page.getByRole("form", {
      name: "Registrar la entrega personal a Pedro Pérez",
    });
    await expect(
      formEntrega.getByRole("heading", {
        name: "Registrar la entrega personal a Pedro Pérez",
        level: 3,
      }),
    ).toBeVisible();

    await formEntrega.getByLabel(/^Fecha de la entrega/).fill(hoy);
    const selectOficio = formEntrega.getByLabel(/^Oficio de notificación/);
    await expect(selectOficio.locator("option")).toHaveCount(3);
    await selectOficio.selectOption({ index: 1 });
    const selectRecibo = formEntrega.getByLabel(/^Recibo firmado/);
    await expect(selectRecibo.locator("option")).toHaveCount(2);
    await selectRecibo.selectOption({ index: 1 });
    await formEntrega.getByLabel(/^Recibido por/).fill("María Gil");
    await formEntrega.getByLabel(/^Cédula de quien recibe/).fill("V-7654321");

    const [entregaResp] = await Promise.all([
      page.waitForResponse(
        (r) =>
          new URL(r.url()).pathname.endsWith(`/gobierno/notificaciones/${pedroId}/intentos`) &&
          r.request().method() === "POST",
        { timeout: 60_000 },
      ),
      formEntrega.getByRole("button", { name: "Registrar entrega" }).click(),
    ]);
    expect(entregaResp.status()).toBe(200);
    await expect(page.getByText("Entrega registrada")).toBeVisible();
    await cerrarNotificaciones(page);

    await expect(
      page.getByText(`Notificada el ${ddmmaaaa(hoy)}`, { exact: true }),
    ).toBeVisible();

    await page.goto(`/gobierno/actos/${acto.id}`);
    await expect(
      page.getByText("Faltan 1 por notificar de 2.", { exact: true }),
    ).toBeVisible();

    await page
      .getByRole("link", { name: "Comercial Ejemplo C.A.", exact: true })
      .click();
    await page.waitForURL((u) => /\/gobierno\/notificaciones\/[^/]+$/.test(u.pathname));
    const comercialId = page.url().split("/").pop()!;

    await adjuntarDocumentoNotificacionApi(
      request,
      mundo.headers,
      mundo.companyId,
      tipo.id,
      comercialId,
    );
    await adjuntarDocumentoNotificacionApi(
      request,
      mundo.headers,
      mundo.companyId,
      tipo.id,
      comercialId,
    );
    await adjuntarDocumentoNotificacionApi(
      request,
      mundo.headers,
      mundo.companyId,
      tipo.id,
      comercialId,
    );

    await page.reload();
    await expect(
      page.getByRole("heading", {
        name: "Notificación a Comercial Ejemplo C.A.",
        level: 1,
      }),
    ).toBeVisible();
    await expect(page.getByText("Pendiente de notificar.", { exact: true })).toBeVisible();

    await expect(
      page.getByRole("button", { name: "Publicar en prensa" }),
    ).toHaveCount(0);

    await page.getByRole("button", { name: "Registrar intento fallido" }).click();
    const formIntento = page.getByRole("form", {
      name: "Registrar un intento fallido a Comercial Ejemplo C.A.",
    });
    await expect(
      formIntento.getByRole("heading", {
        name: "Registrar un intento fallido a Comercial Ejemplo C.A.",
        level: 3,
      }),
    ).toBeVisible();

    await formIntento.getByLabel(/^Fecha del intento/).fill(hoy);
    await formIntento.getByLabel(/^Motivo del intento fallido/).fill("Domicilio cerrado");
    const selectOficioFallido = formIntento.getByLabel(/^Oficio de notificación/);
    await expect(selectOficioFallido.locator("option")).toHaveCount(4);
    await selectOficioFallido.selectOption({ index: 1 });
    const selectConstancia = formIntento.getByLabel(/^Constancia del intento/);
    await expect(selectConstancia.locator("option")).toHaveCount(3);
    await selectConstancia.selectOption({ index: 1 });

    const [intentoResp] = await Promise.all([
      page.waitForResponse(
        (r) =>
          new URL(r.url()).pathname.endsWith(
            `/gobierno/notificaciones/${comercialId}/intentos`,
          ) && r.request().method() === "POST",
        { timeout: 60_000 },
      ),
      formIntento.getByRole("button", { name: "Registrar intento fallido" }).click(),
    ]);
    expect(intentoResp.status()).toBe(200);
    await expect(page.getByText("Intento fallido registrado")).toBeVisible();
    await cerrarNotificaciones(page);

    await expect(
      page.getByRole("button", { name: "Publicar en prensa" }),
    ).toBeVisible();

    await page.getByRole("button", { name: "Publicar en prensa" }).click();
    const formPublicacion = page.getByRole("form", {
      name: "Registrar la publicación en prensa a Comercial Ejemplo C.A.",
    });
    await expect(
      formPublicacion.getByRole("heading", {
        name: "Registrar la publicación en prensa a Comercial Ejemplo C.A.",
        level: 3,
      }),
    ).toBeVisible();
    await formPublicacion.getByLabel(/^Fecha de la publicación/).fill(hoy);
    await formPublicacion.getByLabel(/^Diario/).fill("Diario de prueba");
    await formPublicacion.getByLabel(/^Edición o referencia/).fill("Ed. 123");

    await expect(
      page.getByText(`Se entenderá notificada el ${ddmmaaaa(hoyMas15)}.`, {
        exact: true,
      }),
    ).toBeVisible();

    await expect(formPublicacion.getByLabel(/^Oficio de notificación/)).toBeDisabled();
    const selectEjemplar = formPublicacion.getByLabel(/^Ejemplar del diario/);
    await expect(selectEjemplar.locator("option")).toHaveCount(2);
    await selectEjemplar.selectOption({ index: 1 });

    const [publicacionResp] = await Promise.all([
      page.waitForResponse(
        (r) =>
          new URL(r.url()).pathname.endsWith(
            `/gobierno/notificaciones/${comercialId}/intentos`,
          ) && r.request().method() === "POST",
        { timeout: 60_000 },
      ),
      formPublicacion
        .getByRole("button", { name: "Registrar publicación" })
        .click(),
    ]);
    expect(publicacionResp.status()).toBe(200);
    await expect(page.getByText("Publicación registrada")).toBeVisible();
    await cerrarNotificaciones(page);

    await expect(
      page.getByText(
        `Se entiende notificada el ${ddmmaaaa(hoyMas15)} (publicación en prensa más 15 días)`,
        { exact: true },
      ),
    ).toBeVisible();

    await page.goto(`/gobierno/actos/${acto.id}`);
    await expect(
      page.getByText("Todos los destinatarios están notificados.", { exact: true }),
    ).toBeVisible();
    await expect(
      page
        .locator("main")
        .getByRole("status")
        .filter({ hasText: `Eficaz a partir de ${ddmmaaaa(hoyMas15)}.` }),
    ).toBeVisible();

    await entrarEnGobierno(page, mundo.username, mundo.codigo, "/gobierno/notificaciones");
    await expect(
      page.getByRole("heading", { name: "Notificaciones administrativas", level: 1 }),
    ).toBeVisible();

    const tabla = page.getByRole("table");
    await expect(tabla).toBeVisible();
    await expect(
      tabla.getByRole("row").filter({ has: page.getByRole("cell") }),
    ).toHaveCount(2);
    await expect(
      tabla.getByRole("cell", { name: "Notificada", exact: true }),
    ).toHaveCount(2);

    const downloadPromise = page.waitForEvent("download");
    await page.getByRole("button", { name: "Exportar CSV" }).click();
    const download = await downloadPromise;
    expect(download.suggestedFilename()).toBe(`notificaciones-${ANIO}.csv`);
    const stream = await download.createReadStream();
    const chunks: Buffer[] = [];
    for await (const chunk of stream) {
      chunks.push(Buffer.from(chunk));
    }
    const csv = Buffer.concat(chunks).toString("utf8");
    expect(csv).toContain(`DA-200-${ANIO}`);
  });

  test("DOC4-E2E-02: consulta sin permisos de edición", async ({ page, request }) => {
    test.setTimeout(180_000);

    const { mundo, tipo, cargoId } = await mundoConCargo(request);
    const acto = await actoParticularEmitidoApi(
      request,
      mundo,
      tipo.id,
      cargoId,
      `DA-201-${ANIO}`,
    );

    const respNotif = await request.post(`${API}/gobierno/notificaciones`, {
      headers: mundo.headers,
      data: {
        acto_id: acto.id,
        tipo_persona: "NATURAL",
        nombre: "Destinatario Consulta",
        identificacion: "V-22222222",
        domicilio: "Calle de la consulta",
        recursos: "Reconsideración",
      },
    });
    expect(respNotif.status(), await respNotif.text()).toBe(201);
    const notificacionId = (await respNotif.json()).id;

    const admin = await sesionApi("admintenant", { tenant: TENANT });
    const consulta = await crearUsuario(
      request,
      admin.headers,
      CONSULTA_NOTIFICACIONES,
      mundo.companyId,
    );

    await entrarEnGobierno(
      page,
      consulta.username,
      mundo.codigo,
      "/gobierno/notificaciones",
    );

    await expect(
      page.getByRole("heading", { name: "Notificaciones administrativas", level: 1 }),
    ).toBeVisible();
    await expect(
      page.getByRole("link", {
        name: `Abrir el acto Resolución Nº DA-201-${ANIO}`,
      }),
    ).toBeVisible();
    await expect(
      page.getByRole("button", { name: "Exportar CSV" }),
    ).toBeVisible();

    await page.goto(`/gobierno/notificaciones/${notificacionId}`);
    await expect(
      page.getByRole("heading", {
        name: "Notificación a Destinatario Consulta",
        level: 1,
      }),
    ).toBeVisible();

    await expect(page.getByRole("button", { name: "Registrar entrega" })).toHaveCount(0);
    await expect(
      page.getByRole("button", { name: "Registrar intento fallido" }),
    ).toHaveCount(0);
    await expect(page.getByRole("button", { name: "Publicar en prensa" })).toHaveCount(0);
    await expect(page.getByRole("button", { name: "Corregir datos" })).toHaveCount(0);
    await expect(page.getByRole("button", { name: "Anular" })).toHaveCount(0);

    await page.goto(`/gobierno/actos/${acto.id}`);
    await expect(
      page.getByRole("button", { name: "Agregar destinatario" }),
    ).toHaveCount(0);

    const postResp = await request.post(`${API}/gobierno/notificaciones`, {
      headers: consulta.headers,
      data: {
        acto_id: acto.id,
        tipo_persona: "NATURAL",
        nombre: "Sin Permiso",
        identificacion: "V-33333333",
        domicilio: "Dirección sintética",
        recursos: "Reconsideración",
      },
    });
    expect(postResp.status(), await postResp.text()).toBe(403);
    const postBody = await postResp.json();
    expect(postBody.code).toBe("PERMISSION_DENIED");
  });

  test("DOC4-E2E-03: otro ente no puede ver la notificación", async ({
    page,
    request,
  }) => {
    test.setTimeout(180_000);

    const contextoA = await mundoConCargo(request);
    const actoA = await actoParticularEmitidoApi(
      request,
      contextoA.mundo,
      contextoA.tipo.id,
      contextoA.cargoId,
      `DA-202-${ANIO}`,
    );

    const respNotif = await request.post(`${API}/gobierno/notificaciones`, {
      headers: contextoA.mundo.headers,
      data: {
        acto_id: actoA.id,
        tipo_persona: "NATURAL",
        nombre: "Destinatario Ente A",
        identificacion: "V-44444444",
        domicilio: "Dirección ente A",
        recursos: "Reconsideración",
      },
    });
    expect(respNotif.status(), await respNotif.text()).toBe(201);
    const notificacionIdA = (await respNotif.json()).id;

    const contextoB = await mundoConCargo(request);
    const mundoB = contextoB.mundo;

    await entrarEnGobierno(
      page,
      mundoB.username,
      mundoB.codigo,
      "/gobierno/notificaciones",
    );
    await page.goto(`/gobierno/notificaciones/${notificacionIdA}`);

    await expect(
      page.getByText("Notificación no encontrada", { exact: true }),
    ).toBeVisible();
    await expect(
      page.getByRole("link", { name: "Volver a Notificaciones administrativas" }),
    ).toBeVisible();

    const getResp = await request.get(
      `${API}/gobierno/notificaciones/${notificacionIdA}`,
      { headers: mundoB.headers },
    );
    expect(getResp.status(), await getResp.text()).toBe(404);
    const getBody = await getResp.json();
    expect(getBody.code).toBe("GOV_NOTIFICATION_NOT_FOUND");
  });

  test("DOC4-E2E-04: validaciones de cédula duplicada, RIF inválido e If-Match", async ({
    page,
    request,
  }) => {
    test.setTimeout(180_000);

    const { mundo, tipo, cargoId } = await mundoConCargo(request);
    const acto = await actoParticularEmitidoApi(
      request,
      mundo,
      tipo.id,
      cargoId,
      `DA-203-${ANIO}`,
    );

    await entrarEnGobierno(page, mundo.username, mundo.codigo, "/gobierno/actos");
    const respCreacion = await request.post(`${API}/gobierno/notificaciones`, {
      headers: mundo.headers,
      data: {
        acto_id: acto.id,
        tipo_persona: "NATURAL",
        nombre: "Pedro Pérez",
        identificacion: "V-12345678",
        domicilio: "Calle 1, casa 2, Caracas",
        recursos: "Reconsideración ante el mismo órgano en 15 días hábiles (LOPA art. 94)",
      },
    });
    expect(respCreacion.status()).toBe(201);

    await page.goto(`/gobierno/actos/${acto.id}`);

    await page.getByRole("button", { name: "Agregar destinatario" }).click();
    const formAgregar = page.getByRole("form", { name: "Agregar destinatario" });
    await formAgregar.getByRole("radio", { name: "Persona natural" }).check();
    await formAgregar.getByLabel(/^Nombre o razón social/).fill("Cédula corta");
    await formAgregar.getByLabel(/^Cédula o RIF/).fill("123456");
    await formAgregar.getByLabel(/^Domicilio o residencia/).fill("Dirección sintética");
    await formAgregar.getByLabel(/^Recursos que proceden/).fill("Reconsideración");

    const [respInvalida] = await Promise.all([
      page.waitForResponse(
        (r) =>
          new URL(r.url()).pathname.endsWith("/gobierno/notificaciones") &&
          r.request().method() === "POST",
        { timeout: 60_000 },
      ),
      formAgregar
        .getByRole("button", { name: "Agregar destinatario" })
        .click(),
    ]);
    expect(respInvalida.status()).toBe(422);
    await expect(formAgregar.getByText(/Escriba la cédula con su letra/)).toBeVisible();
    await expect(page.getByText("Destinatario agregado")).toHaveCount(0);

    await formAgregar.getByLabel(/^Nombre o razón social/).fill("Duplicado");
    await formAgregar.getByLabel(/^Cédula o RIF/).fill("V-12345678");
    await formAgregar.getByLabel(/^Domicilio o residencia/).fill("Dirección sintética");

    const [respDuplicada] = await Promise.all([
      page.waitForResponse(
        (r) =>
          new URL(r.url()).pathname.endsWith("/gobierno/notificaciones") &&
          r.request().method() === "POST",
        { timeout: 60_000 },
      ),
      formAgregar
        .getByRole("button", { name: "Agregar destinatario" })
        .click(),
    ]);
    expect(respDuplicada.status()).toBe(409);
    const errorDuplicado = (await respDuplicada.json()) as { code: string; message: string };
    expect(errorDuplicado.code).toBe("GOV_NOTIFICATION_RECIPIENT_DUPLICATE");
    await expect(formAgregar.getByText(errorDuplicado.message)).toBeVisible();
    await expect(page.getByText("Destinatario agregado")).toHaveCount(0);

    const respNotif = await request.post(`${API}/gobierno/notificaciones`, {
      headers: mundo.headers,
      data: {
        acto_id: acto.id,
        tipo_persona: "NATURAL",
        nombre: "Destinatario If-Match",
        identificacion: "V-55555555",
        domicilio: "Dirección sintética",
        recursos: "Reconsideración",
      },
    });
    expect(respNotif.status(), await respNotif.text()).toBe(201);
    const notificacionId = (await respNotif.json()).id;

    const patchResp = await request.patch(
      `${API}/gobierno/notificaciones/${notificacionId}`,
      {
        headers: mundo.headers,
        data: { nombre: "Cambio sin If-Match" },
      },
    );
    expect(patchResp.status(), await patchResp.text()).toBe(428);
  });

  test("DOC4-E2E-05: accesibilidad", async ({ page, request }) => {
    test.setTimeout(180_000);

    const { mundo, tipo, cargoId } = await mundoConCargo(request);
    const acto = await actoParticularEmitidoApi(
      request,
      mundo,
      tipo.id,
      cargoId,
      `DA-204-${ANIO}`,
    );

    const respNotif = await request.post(`${API}/gobierno/notificaciones`, {
      headers: mundo.headers,
      data: {
        acto_id: acto.id,
        tipo_persona: "NATURAL",
        nombre: "Destinatario Accesible",
        identificacion: "V-66666666",
        domicilio: "Dirección accesible",
        recursos: "Reconsideración",
      },
    });
    expect(respNotif.status(), await respNotif.text()).toBe(201);
    const notificacionId = (await respNotif.json()).id;

    await entrarEnGobierno(page, mundo.username, mundo.codigo, "/gobierno/notificaciones");
    await expect(
      page.getByRole("heading", { name: "Notificaciones administrativas", level: 1 }),
    ).toBeVisible();

    for (const width of [1280, 768, 320]) {
      await page.setViewportSize({ width, height: 900 });
      await sinViolacionesSerias(page, `Lista de notificaciones a ${width}px`);
    }

    await page.goto(`/gobierno/notificaciones/${notificacionId}`);
    await expect(
      page.getByRole("heading", {
        name: "Notificación a Destinatario Accesible",
        level: 1,
      }),
    ).toBeVisible();
    for (const width of [1280, 768, 320]) {
      await page.setViewportSize({ width, height: 900 });
      await sinViolacionesSerias(page, `Detalle de notificación a ${width}px`);
    }

    await page.goto(`/gobierno/actos/${acto.id}`);
    await expect(
      page.getByRole("heading", { name: "Notificaciones", level: 2 }),
    ).toBeVisible();
    for (const width of [1280, 768, 320]) {
      await page.setViewportSize({ width, height: 900 });
      await sinViolacionesSerias(
        page,
        `Detalle del acto con Notificaciones a ${width}px`,
      );
    }
  });
});
