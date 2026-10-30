import AxeBuilder from "@axe-core/playwright";
import { type APIRequestContext, type Page } from "@playwright/test";
import { activarEmpresa } from "./helpers/empresa";
import { declararAlcance } from "./helpers/usuario";
import { entrarComoUsuario, expect, iniciarSesion, sesionApi, test } from "./helpers/sesion";
import { marca } from "./helpers/ventas";

const TENANT = process.env.KONTROL_E2E_TENANT ?? "DEMO";
const API = process.env.KONTROL_E2E_API ?? "http://127.0.0.1:8000/api/v1";
const PASSWORD = process.env.KONTROL_E2E_PASSWORD ?? "";
const WCAG = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"];
const PDF = Buffer.from("%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\ntrailer\n%%EOF\n");

const RESPONSABLE = [
  "organization:view",
  "gobierno_ente:view",
  "gobierno_ente:create",
  "gobierno_ente:edit",
  "gobierno_ente:activate",
  "documentos:view",
  "documentos:create",
  "documentos:upload",
  "documentos:link",
  "documentos:download",
  "documentos:manage_types",
];

const CONSULTA = ["organization:view", "gobierno_ente:view", "documentos:view"];

function es2xx(status: number): boolean {
  return status >= 200 && status < 300;
}

async function crearUsuario(
  request: APIRequestContext,
  adminHeaders: Record<string, string>,
  capacidades: string[],
  companyId: string,
): Promise<{ username: string; headers: Record<string, string> }> {
  const sufijo = marca();
  const username = `gov${sufijo}`;
  const rolCode = `QA-GOV-${sufijo}`.toUpperCase();

  const rolResp = await request.post(`${API}/roles`, {
    headers: adminHeaders,
    data: { code: rolCode, name: "QA Gobierno", permissions: capacidades },
  });
  expect(rolResp.status(), await rolResp.text()).toBe(201);
  const rol = await rolResp.json();

  const userResp = await request.post(`${API}/users`, {
    headers: adminHeaders,
    data: {
      username,
      email: `${username}@example.com`,
      password: PASSWORD,
      must_change_password: false,
    },
  });
  expect(es2xx(userResp.status()), await userResp.text()).toBe(true);
  const user = await userResp.json();

  const asignResp = await request.post(`${API}/users/${user.id}/roles`, {
    headers: adminHeaders,
    data: { role_id: rol.id, company_id: companyId },
  });
  expect(es2xx(asignResp.status()), await asignResp.text()).toBe(true);

  await declararAlcance(username, [companyId], TENANT);

  const sesion = await iniciarSesion(username, { tenant: TENANT });
  const headers = {
    Authorization: `Bearer ${sesion.token}`,
    "X-Kontrol-Company": companyId,
  };

  return { username, headers };
}

async function prepararMundo(
  request: APIRequestContext,
  capacidades: string[],
): Promise<{ companyId: string; codigo: string; username: string; headers: Record<string, string> }> {
  const admin = await sesionApi("admintenant", { tenant: TENANT });

  const companyResp = await request.post(`${API}/organization/companies`, {
    headers: admin.headers,
    data: {
      code: `GOV${marca()}`.toUpperCase().slice(0, 20),
      legal_name: `Ente de prueba ${marca()}`,
      rif: "G-20000000-0",
    },
  });
  expect(es2xx(companyResp.status()), await companyResp.text()).toBe(true);
  const company = await companyResp.json();
  const companyId = company.id;
  const codigo = company.code;

  const usuario = await crearUsuario(request, admin.headers, capacidades, companyId);

  return { companyId, codigo, username: usuario.username, headers: usuario.headers };
}

async function crearTipoDocumental(
  request: APIRequestContext,
  headers: Record<string, string>,
  companyId: string,
): Promise<string> {
  const resp = await request.post(`${API}/documentos/tipos`, {
    headers,
    data: {
      company_id: companyId,
      code: `ACTO${marca()}`.toUpperCase().slice(0, 32),
      name: "Acto de creación",
      allowed_mime_types: ["application/pdf"],
      max_size_bytes: 1048576,
      scan_required: true,
    },
  });
  expect(es2xx(resp.status()), await resp.text()).toBe(true);
  const body = await resp.json();
  return body.name;
}

/** Cierra las notificaciones visibles: quedan sobre las acciones de la cabecera (patrón de approvals.spec.ts). */
async function cerrarNotificaciones(page: Page): Promise<void> {
  const cerrar = page.getByRole("button", { name: "Cerrar notificación" });
  for (let i = await cerrar.count(); i > 0; i = await cerrar.count()) {
    await cerrar.first().click();
  }
}

async function entrarEnElEnte(page: Page, username: string, codigo: string): Promise<void> {
  await entrarComoUsuario(page, username, { tenant: TENANT, ruta: "/" });
  await activarEmpresa(page, codigo);
  await page.locator('nav a[href="/gobierno/ente"]').first().click();
  await page.waitForURL((u) => u.pathname === "/gobierno/ente");
}

test.describe("Gobierno · Configurar el ente (GOV-0-01)", () => {
  test("GOV-E2E-01: el responsable configura, documenta, activa y modifica el ente desde el menú", async ({ page, request }) => {
    test.setTimeout(180_000);

    const mundo = await prepararMundo(request, RESPONSABLE);
    const tipo = await crearTipoDocumental(request, mundo.headers, mundo.companyId);
    await entrarEnElEnte(page, mundo.username, mundo.codigo);

    await expect(page.locator('nav[aria-label="Menú principal"]').getByText("Gobierno", { exact: true })).toBeVisible();
    await expect(page.locator('nav[aria-label="Menú principal"]').getByText("Configuración del ente", { exact: true })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Configuración del ente", level: 1 })).toBeVisible();
    await expect(page.getByText("El ente aún no está configurado")).toBeVisible();

    await page.getByRole("button", { name: "Configurar el ente" }).click();
    await page.getByLabel(/^Denominación oficial/).fill("Alcaldía del Municipio Demo");

    const [altaResp] = await Promise.all([
      page.waitForResponse(
        (r) => new URL(r.url()).pathname.endsWith("/api/v1/gobierno/ente") && r.request().method() === "POST",
        { timeout: 30_000 },
      ),
      page.getByRole("button", { name: "Guardar" }).click(),
    ]);
    expect(altaResp.status()).toBe(201);

    await expect(page.getByText("Ente registrado en borrador")).toBeVisible();
    await cerrarNotificaciones(page);
    const cabecera = page.locator("main header").first();
    await expect(cabecera.getByText("Borrador", { exact: true })).toBeVisible();
    const requisitos = page.getByRole("region", { name: "Requisitos para activar" });
    await expect(requisitos.getByRole("listitem").filter({ hasText: "Nivel político-territorial" })).toBeVisible();
    await expect(requisitos.getByRole("listitem").filter({ hasText: "Documento del acto de creación" })).toBeVisible();
    await expect(page.getByRole("button", { name: "Activar el ente" })).toBeDisabled();

    await page.getByRole("button", { name: "Editar" }).click();
    await page.getByLabel("Nivel político-territorial").selectOption({ label: "Municipal" });
    await page.getByLabel("Forma organizativa").selectOption({ label: "Administración central" });
    await page.getByLabel("Entidad federal").fill("Lara");
    await page.getByLabel("Municipio").fill("Iribarren");
    await page.getByLabel("Tipo de acto de creación").selectOption({ label: "Ordenanza" });
    await page.getByLabel("Número del acto").fill("1");
    await page.getByLabel("Fecha del acto").fill("2020-01-15");
    await page.getByLabel("Publicación oficial").fill("Gaceta Municipal N.º 1 del 15/01/2020");

    const [editResp] = await Promise.all([
      page.waitForResponse(
        (r) => new URL(r.url()).pathname.endsWith("/api/v1/gobierno/ente") && r.request().method() === "PATCH",
        { timeout: 30_000 },
      ),
      page.getByRole("button", { name: "Guardar" }).click(),
    ]);
    expect(editResp.status()).toBe(200);

    await expect(page.getByText("Cambios guardados")).toBeVisible();
    await cerrarNotificaciones(page);
    await expect(requisitos.getByRole("listitem")).toHaveCount(1);
    await expect(requisitos.getByRole("listitem").filter({ hasText: "Documento del acto de creación" })).toBeVisible();

    const documento = page.getByRole("region", { name: "Documento del acto de creación" }).first();
    await documento.getByLabel("Tipo documental del archivo").selectOption({ label: tipo });
    await documento.getByLabel(/^Archivo/).setInputFiles({
      name: "acto.pdf",
      mimeType: "application/pdf",
      buffer: PDF,
    });

    const [vinculoResp] = await Promise.all([
      page.waitForResponse(
        (r) => /\/api\/v1\/documentos\/[^/]+\/vinculos$/.test(new URL(r.url()).pathname) && r.request().method() === "POST",
        { timeout: 60_000 },
      ),
      documento.getByRole("button", { name: "Adjuntar" }).click(),
    ]);
    expect(es2xx(vinculoResp.status()), await vinculoResp.text()).toBe(true);

    await expect(page.getByText("Documento adjuntado")).toBeVisible({ timeout: 30_000 });
    await cerrarNotificaciones(page);
    await expect(requisitos.getByText("El ente está completo y puede activarse.")).toBeVisible();
    await expect(page.getByRole("button", { name: "Activar el ente" })).toBeEnabled();

    await page.getByRole("button", { name: "Activar el ente" }).click();
    await expect(page.getByRole("dialog")).toBeVisible();
    await expect(page.getByRole("dialog").getByText("¿Activar el ente?")).toBeVisible();

    const [activarResp] = await Promise.all([
      page.waitForResponse(
        (r) => new URL(r.url()).pathname.endsWith("/api/v1/gobierno/ente/activar") && r.request().method() === "POST",
        { timeout: 30_000 },
      ),
      page.getByRole("dialog").getByRole("button", { name: "Activar", exact: true }).click(),
    ]);
    expect(activarResp.status()).toBe(200);

    await expect(page.getByText("Ente activado")).toBeVisible();
    await cerrarNotificaciones(page);
    await expect(cabecera.getByText("Activo", { exact: true })).toBeVisible();
    await expect(page.getByRole("button", { name: "Activar el ente" })).toHaveCount(0);
    await expect(page.getByRole("button", { name: "Modificar" })).toBeVisible();

    let patchCount = 0;
    page.on("request", (req) => {
      if (new URL(req.url()).pathname.endsWith("/api/v1/gobierno/ente") && req.method() === "PATCH") {
        patchCount += 1;
      }
    });

    await page.getByRole("button", { name: "Modificar" }).click();
    await page.getByLabel("Siglas").fill("AMD");
    await page.getByRole("button", { name: "Guardar" }).click();
    await expect(page.getByText("Indique el motivo (de 5 a 255 caracteres)")).toBeVisible();
    expect(patchCount).toBe(0);

    await page.getByLabel("Motivo de la modificación").fill("Corrección de las siglas institucionales");

    const [modificarResp] = await Promise.all([
      page.waitForResponse(
        (r) => new URL(r.url()).pathname.endsWith("/api/v1/gobierno/ente") && r.request().method() === "PATCH",
        { timeout: 30_000 },
      ),
      page.getByRole("button", { name: "Guardar" }).click(),
    ]);
    expect(modificarResp.status()).toBe(200);

    await expect(page.getByText("Modificación registrada")).toBeVisible();
    await cerrarNotificaciones(page);

    await expect(page.getByRole("cell", { name: "4", exact: true })).toBeVisible();
    await expect(page.getByRole("cell", { name: "Corrección de las siglas institucionales", exact: true })).toBeVisible();

    const enteResp = await request.get(`${API}/gobierno/ente`, { headers: mundo.headers });
    expect(enteResp.status(), await enteResp.text()).toBe(200);
    const ente = await enteResp.json();

    const admin = await sesionApi("admintenant", { tenant: TENANT });
    const auditResp = await request.get(
      `${API}/audit/events?entity_type=GovernmentEntity&entity_id=${ente.id}&page_size=50`,
      { headers: admin.headers },
    );
    expect(auditResp.status(), await auditResp.text()).toBe(200);
    const audit = await auditResp.json();
    const acciones = audit.items.map((e: { action: string }) => e.action);
    expect(acciones).toContain("GOV_ENTITY_CREATED");
    expect(acciones.filter((a: string) => a === "GOV_ENTITY_UPDATED").length).toBeGreaterThanOrEqual(2);
    expect(acciones).toContain("GOV_ENTITY_ACTIVATED");
    const actualizacionConMotivo = audit.items.find(
      (e: { action: string; reason?: string }) =>
        e.action === "GOV_ENTITY_UPDATED" && e.reason === "Corrección de las siglas institucionales",
    );
    expect(actualizacionConMotivo).toBeTruthy();
  });

  test("GOV-E2E-02: consulta sin capacidad de escritura: ve, pero no puede editar ni activar", async ({ page, request }) => {
    const mundo = await prepararMundo(request, RESPONSABLE);

    const crearResp = await request.post(`${API}/gobierno/ente`, {
      headers: mundo.headers,
      data: { denominacion: "Ente de consulta" },
    });
    expect(crearResp.status(), await crearResp.text()).toBe(201);

    const admin = await sesionApi("admintenant", { tenant: TENANT });
    const consulta = await crearUsuario(request, admin.headers, CONSULTA, mundo.companyId);

    await entrarEnElEnte(page, consulta.username, mundo.codigo);

    await expect(page.getByRole("heading", { name: "Ente de consulta", level: 1 })).toBeVisible();
    const cabecera = page.locator("main header").first();
    await expect(cabecera.getByText("Borrador", { exact: true })).toBeVisible();
    await expect(page.getByRole("button", { name: "Editar" })).toHaveCount(0);
    await expect(page.getByRole("button", { name: "Activar el ente" })).toHaveCount(0);
    await expect(page.getByRole("button", { name: "Configurar el ente" })).toHaveCount(0);

    const patchResp = await request.patch(`${API}/gobierno/ente`, {
      headers: { ...consulta.headers, "If-Match": '"1"' },
      data: { siglas: "NO" },
    });
    expect(patchResp.status(), await patchResp.text()).toBe(403);
    const patchBody = await patchResp.json();
    expect(patchBody.code).toBe("PERMISSION_DENIED");

    const activarResp = await request.post(`${API}/gobierno/ente/activar`, {
      headers: { ...consulta.headers, "If-Match": '"1"' },
    });
    expect(activarResp.status(), await activarResp.text()).toBe(403);
    const activarBody = await activarResp.json();
    expect(activarBody.code).toBe("PERMISSION_DENIED");
  });

  test("GOV-E2E-03: otro ente: la empresa ajena no existe para este usuario", async ({ request }) => {
    const mundoA = await prepararMundo(request, RESPONSABLE);
    const mundoB = await prepararMundo(request, RESPONSABLE);

    const crearResp = await request.post(`${API}/gobierno/ente`, {
      headers: mundoB.headers,
      data: { denominacion: "Ente de B" },
    });
    expect(crearResp.status(), await crearResp.text()).toBe(201);

    const headersAEnB = {
      ...mundoA.headers,
      "X-Kontrol-Company": mundoB.companyId,
    };

    const getResp = await request.get(`${API}/gobierno/ente`, { headers: headersAEnB });
    expect(getResp.status(), await getResp.text()).toBe(404);
    const getBody = await getResp.json();
    expect(getBody.code).toBe("COMPANY_NOT_FOUND");

    const postResp = await request.post(`${API}/gobierno/ente`, {
      headers: headersAEnB,
      data: { denominacion: "Intruso" },
    });
    expect(postResp.status(), await postResp.text()).toBe(404);
    const postBody = await postResp.json();
    expect(postBody.code).toBe("COMPANY_NOT_FOUND");

    const getBResp = await request.get(`${API}/gobierno/ente`, { headers: mundoB.headers });
    expect(getBResp.status(), await getBResp.text()).toBe(200);
    const enteB = await getBResp.json();
    expect(enteB.denominacion).toBe("Ente de B");
  });

  test("GOV-E2E-04: versión vieja: el segundo cambio con la misma versión se rechaza", async ({ request }) => {
    const mundo = await prepararMundo(request, RESPONSABLE);

    const crearResp = await request.post(`${API}/gobierno/ente`, {
      headers: mundo.headers,
      data: { denominacion: "Ente de versiones" },
    });
    expect(crearResp.status(), await crearResp.text()).toBe(201);

    const patch1Resp = await request.patch(`${API}/gobierno/ente`, {
      headers: { ...mundo.headers, "If-Match": '"1"' },
      data: { siglas: "A1" },
    });
    expect(patch1Resp.status(), await patch1Resp.text()).toBe(200);

    const patch2Resp = await request.patch(`${API}/gobierno/ente`, {
      headers: { ...mundo.headers, "If-Match": '"1"' },
      data: { siglas: "A2" },
    });
    expect(patch2Resp.status(), await patch2Resp.text()).toBe(409);
    const patch2Body = await patch2Resp.json();
    expect(patch2Body.code).toBe("GOV_ENTITY_STALE");

    const patchSinIfMatchResp = await request.patch(`${API}/gobierno/ente`, {
      headers: mundo.headers,
      data: { siglas: "A3" },
    });
    expect(patchSinIfMatchResp.status(), await patchSinIfMatchResp.text()).toBe(428);
    const patchSinIfMatchBody = await patchSinIfMatchResp.json();
    expect(patchSinIfMatchBody.code).toBe("GOV_ENTITY_IF_MATCH_REQUIRED");
  });

  test("GOV-E2E-05: la pantalla no tiene violaciones serias de accesibilidad a 1280 y 320 px", async ({ page, request }) => {
    const mundo = await prepararMundo(request, RESPONSABLE);

    const crearResp = await request.post(`${API}/gobierno/ente`, {
      headers: mundo.headers,
      data: { denominacion: "Ente accesible" },
    });
    expect(crearResp.status(), await crearResp.text()).toBe(201);

    await entrarEnElEnte(page, mundo.username, mundo.codigo);
    await expect(page.getByRole("heading", { name: "Ente accesible", level: 1 })).toBeVisible();

    for (const width of [1280, 320]) {
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
