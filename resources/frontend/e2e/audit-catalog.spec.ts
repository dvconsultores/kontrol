/**
 * Auditoría con catálogo · ciclo 04 · SPEC 001 + 046.
 *
 * Certificación de extremo a extremo, contra la base efímera de la corrida canónica:
 *   (a) la bitácora `/auditoria` respeta el alcance tenant/empresa (OD-AUD-01),
 *       muestra fecha de Caracas y filtra; y
 *   (b) un archivo rechazado por el analizador deja un evento de auditoría persistente
 *       y seguro, y la persona ve un mensaje seguro.
 */
import { resolve } from "node:path";

import { type APIRequestContext, type Page } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

import {
  entrar,
  entrarComoUsuario,
  expect,
  sesionApi,
  sesionDeUsuario,
  test,
} from "./helpers/sesion";
import { mundoN6 } from "./helpers/n6-mundo";
import { ejecutarPython } from "./helpers/python";

const API = process.env.KONTROL_E2E_API ?? "http://127.0.0.1:8000/api/v1";
const TENANT = process.env.KONTROL_E2E_TENANT ?? "DEMO";
const USER = process.env.KONTROL_E2E_USER;
const PASSWORD = process.env.KONTROL_E2E_PASSWORD ?? "";

/** El runner dice si el backend de la corrida tiene `clamscan`; fuera del runner se asume que sí. */
const SCANNER = process.env.KONTROL_E2E_SCANNER_AVAILABLE !== "false";
const SIN_CLAMSCAN = "ENTORNO-SIN-CLAMSCAN: sin clamscan ninguna carga con análisis obligatorio crea versión " +
  "(SCAN_FAILED, falso seguro FR-046-072); dueña 046";

// Fixture estándar de prueba (EICAR), no malware real. Se obtiene en tiempo de
// ejecución desde los ayudantes Python de la certificación, una vez por fichero.
const MUESTRA = Buffer.from(
  ejecutarPython(
    ["-c", "import sys; sys.path.insert(0, 'qa'); import clamav_qa; sys.stdout.write(clamav_qa.EICAR)"],
    { cwd: resolve(process.cwd(), "..", ".."), encoding: "utf-8" },
  ),
  "ascii",
);

const MUNDO = mundoN6();
const marca = (): string => `${Date.now().toString(36)}${Math.random().toString(36).slice(2, 6)}`.toLowerCase();

type Ctx = { token: string; company: string; headers: Record<string, string> };

async function ctx(request: APIRequestContext): Promise<Ctx> {
  const token = (await sesionApi(USER as string, { tenant: TENANT })).token;
  const headers = { Authorization: `Bearer ${token}` };
  const body = await (await request.get(`${API}/organization/companies`, { headers })).json();
  const company = body.items[0].id as string;
  return { token, company, headers };
}

/** Sufijo único: el estado persiste entre navegadores sobre la misma base. */
const RUN = `${Date.now().toString(36)}${Math.random().toString(36).slice(2, 6)}`.toUpperCase();

async function createType(request: APIRequestContext, c: Ctx,
                          overrides: Record<string, unknown> = {}): Promise<string> {
  const suffix = Math.random().toString(36).slice(2, 6).toUpperCase();
  const r = await request.post(`${API}/documentos/tipos`, {
    headers: c.headers,
    data: {
      company_id: c.company, code: `E2EAUD${suffix}`.slice(0, 32),
      name: `Tipo E2E AUD ${suffix}`,
      allowed_mime_types: ["text/plain"], max_size_bytes: 1024 * 1024,
      scan_required: true, ...overrides,
    },
  });
  expect(r.ok(), await r.text()).toBeTruthy();
  return (await r.json()).id as string;
}

async function typeNameOf(request: APIRequestContext, c: Ctx, id: string): Promise<string> {
  const types = await (await request.get(`${API}/documentos/tipos`, { headers: c.headers })).json();
  return types.find((t: { id: string }) => t.id === id).name as string;
}

async function uiLogin(page: Page): Promise<void> {
  await entrar(page, USER as string, { tenant: TENANT });
  await page.waitForURL((u) => !u.pathname.includes("login"), { timeout: 20000 });

  await page.locator('nav a[href="/organizacion/empresas"]').first().click();
  await page.waitForURL((u) => u.pathname === "/organizacion/empresas", { timeout: 15000 });
  await page.waitForLoadState("networkidle");
  // Nombre exacto: sin `exact`, «Activar» casaba por subcadena con «Desactivar»,
  // y cuando la empresa ya estaba activa el helper la desactivaba (CONC-046).
  const activar = page.getByRole("button", { name: "Activar", exact: true }).first();
  if (await activar.count()) {
    await activar.click();
    await expect(page.getByRole("button", { name: "Desactivar", exact: true }).first())
      .toBeVisible({ timeout: 15000 });
  }
}

/** Navegación por menú: un `goto` recargaría y perdería el token en memoria. */
async function goto(page: Page, href: string): Promise<void> {
  await page.locator(`nav a[href="${href}"]`).first().click();
  await page.waitForURL((u) => u.pathname === href, { timeout: 15000 });
}

async function closeNotifications(page: Page): Promise<void> {
  const close = page.getByRole("button", { name: "Cerrar notificación" });
  for (let i = await close.count(); i > 0; i = await close.count()) {
    await close.first().click();
  }
}

/** Crea el documento por UI y entra en su detalle. */
async function createDocument(page: Page, title: string, typeName: string): Promise<void> {
  await goto(page, "/documentos");
  await page.waitForLoadState("networkidle");
  await page.getByLabel("Título del documento").fill(title);
  await page.getByLabel("Tipo documental del nuevo documento").selectOption({ label: typeName });
  await page.getByRole("button", { name: "Crear documento" }).click();
  await expect(page.getByText("Documento creado")).toBeVisible({ timeout: 15000 });
  await closeNotifications(page);
  await page.getByLabel("Buscar documento").fill(title);
  await page.waitForLoadState("networkidle");
  await page.getByRole("link", { name: title }).first().click();
  await page.waitForURL(/\/documentos\/[0-9a-f-]+$/, { timeout: 15000 });
}

async function crearRol(request: APIRequestContext, permisos: string[]): Promise<string> {
  const code = `QA-UIS-${marca().toUpperCase()}`;
  const response = await request.post(`${API}/roles`, {
    headers: (await sesionApi("admintenant", { tenant: TENANT })).headers,
    data: { code, name: code, permissions: permisos },
  });
  expect(response.status(), `crear rol ${code}: ${await response.text()}`).toBe(201);
  const body = await response.json();
  expect(body.id, "crear rol debe devolver id").toBeTruthy();
  return body.id as string;
}

async function crearUsuario(request: APIRequestContext): Promise<{ username: string; userId: string }> {
  const username = `aud${marca()}`;
  const response = await request.post(`${API}/users`, {
    headers: (await sesionApi("admintenant", { tenant: TENANT })).headers,
    data: {
      username,
      email: `${username}@example.com`,
      password: PASSWORD,
      must_change_password: false,
    },
  });
  expect(response.status(), `crear usuario ${username}: ${await response.text()}`).toBeGreaterThanOrEqual(200);
  expect(response.status()).toBeLessThan(300);
  const body = await response.json();
  expect(body.id, "crear usuario debe devolver id").toBeTruthy();
  return { username, userId: body.id as string };
}

async function asignar(
  request: APIRequestContext,
  userId: string,
  roleId: string,
  empresa: string | null,
): Promise<void> {
  const response = await request.post(`${API}/users/${userId}/roles`, {
    headers: (await sesionApi("admintenant", { tenant: TENANT })).headers,
    data: { role_id: roleId, company_id: empresa },
  });
  expect(response.status(), `asignar rol ${roleId} a ${userId}: ${await response.text()}`).toBeGreaterThanOrEqual(200);
  expect(response.status()).toBeLessThan(300);
}

async function entrarEn(
  page: Page,
  username: string,
  codigoEmpresa: string,
): Promise<void> {
  await entrarComoUsuario(page, username, { tenant: TENANT, ruta: "/" });
  await expect(page.getByRole("heading", { name: "Seleccione una empresa" }), "debe pedir elegir empresa").toBeVisible();
  await page.getByTestId(`elegir-empresa-${codigoEmpresa}`).click();
  await expect(page.getByTestId("selector-empresa"), `selector debe mostrar empresa ${codigoEmpresa}`).toContainText(
    codigoEmpresa === "D1" ? MUNDO.nombre_a : MUNDO.nombre_b,
  );
  await page.waitForLoadState("networkidle");
}

/** Igual que `entrarEn` pero para una identidad BASE del worker (no creada por la prueba). */
async function entrarBaseEn(
  page: Page,
  base: string,
  codigoEmpresa: string,
): Promise<void> {
  await entrar(page, base, { tenant: TENANT, ruta: "/" });
  await expect(page.getByRole("heading", { name: "Seleccione una empresa" }), "debe pedir elegir empresa").toBeVisible();
  await page.getByTestId(`elegir-empresa-${codigoEmpresa}`).click();
  await expect(page.getByTestId("selector-empresa"), `selector debe mostrar empresa ${codigoEmpresa}`).toContainText(
    codigoEmpresa === "D1" ? MUNDO.nombre_a : MUNDO.nombre_b,
  );
  await page.waitForLoadState("networkidle");
}

type EventoAuditoria = {
  request_id: string | null;
  event_time: string;
  action: string;
  entity_type: string;
  entity_id: string | null;
  scope: "TENANT" | "COMPANY";
  company_id: string | null;
  company_name: string | null;
  action_label: string;
  username: string | null;
  reason: string | null;
  details: Record<string, unknown>;
};

async function eventos(
  request: APIRequestContext,
  headers: Record<string, string>,
  query: string,
): Promise<{ total: number; items: EventoAuditoria[] }> {
  const r = await request.get(`${API}/audit/events?${query}`, { headers });
  expect(r.status(), `GET audit/events ${query}: ${await r.text()}`).toBe(200);
  return (await r.json()) as { total: number; items: EventoAuditoria[] };
}

function fechaCaracasHoy(): string {
  return new Intl.DateTimeFormat("en-CA", { timeZone: "America/Caracas" }).format(new Date());
}

function fechaCaracasAyer(): string {
  const ayer = new Date(Date.now() - 24 * 60 * 60 * 1000);
  return new Intl.DateTimeFormat("en-CA", { timeZone: "America/Caracas" }).format(ayer);
}

test.describe("auditoría con catálogo · ciclo 04", () => {
  test("AUDIT-E2E-01 · evento de tenant visible solo con autoridad de tenant", async ({ page, request }) => {
    const roleId = await crearRol(request, ["audit:view"]);
    const { userId } = await crearUsuario(request);
    await asignar(request, userId, roleId, MUNDO.empresa_a);

    const adminHeaders = (await sesionApi("admintenant", { tenant: TENANT })).headers;
    const createdResponse = await request.post(`${API}/users`, {
      headers: adminHeaders,
      data: {
        username: `tenant${marca()}`,
        email: `tenant${marca()}@example.com`,
        password: PASSWORD,
        must_change_password: false,
      },
    });
    expect(createdResponse.status(), await createdResponse.text()).toBeGreaterThanOrEqual(200);
    expect(createdResponse.status()).toBeLessThan(300);
    const rid = createdResponse.headers()["x-request-id"];
    expect(rid, "respuesta de creación debe llevar x-request-id").toBeTruthy();

    const apiResult = await eventos(request, adminHeaders, `request_id=${encodeURIComponent(rid)}`);
    expect(apiResult.total).toBeGreaterThanOrEqual(1);
    const evento = apiResult.items.find((i) => i.action === "USER_CREATED");
    expect(evento, "debe existir evento USER_CREATED").toBeTruthy();
    expect(evento!.scope).toBe("TENANT");
    expect(evento!.company_id).toBeNull();

    await entrarBaseEn(page, "admintenant", "D1");
    await goto(page, "/auditoria");
    await page.waitForLoadState("networkidle");
    await page.getByLabel("Correlación").fill(rid);
    await page.getByRole("button", { name: "Aplicar filtros" }).click();

    const fila = page.getByRole("row", { name: new RegExp(rid) });
    await expect(fila, "la fila del evento debe existir").toBeVisible();
    await expect(fila).toContainText("USER_CREATED");
    await expect(fila).toContainText("Tenant");
  });

  test("AUDIT-E2E-02 · el auditor de D1 NO ve el evento de tenant", async ({ page, request }) => {
    const roleId = await crearRol(request, ["audit:view"]);
    const { username, userId } = await crearUsuario(request);
    await asignar(request, userId, roleId, MUNDO.empresa_a);

    const adminHeaders = (await sesionApi("admintenant", { tenant: TENANT })).headers;
    const createdResponse = await request.post(`${API}/users`, {
      headers: adminHeaders,
      data: {
        username: `tenant${marca()}`,
        email: `tenant${marca()}@example.com`,
        password: PASSWORD,
        must_change_password: false,
      },
    });
    expect(createdResponse.status()).toBeGreaterThanOrEqual(200);
    expect(createdResponse.status()).toBeLessThan(300);
    const rid = createdResponse.headers()["x-request-id"];
    expect(rid).toBeTruthy();

    const { headers: auditorHeaders } = await sesionDeUsuario(username, {
      tenant: TENANT,
      empresa: MUNDO.empresa_a,
    });

    const result = await eventos(request, auditorHeaders, `request_id=${encodeURIComponent(rid)}`);
    expect(result.total).toBe(0);

    const filtersResponse = await request.get(`${API}/audit/filters`, { headers: auditorHeaders });
    expect(filtersResponse.status()).toBe(200);
    const filters = await filtersResponse.json();
    expect(filters.tenant_wide).toBe(false);

    await entrarEn(page, username, "D1");
    await goto(page, "/auditoria");
    await page.waitForLoadState("networkidle");
    await expect(page.getByText("Solo eventos del tenant")).toHaveCount(0);
    await page.getByLabel("Correlación").fill(rid);
    await page.getByRole("button", { name: "Aplicar filtros" }).click();
    await expect(page.getByText("No hay eventos de auditoría registrados con los filtros actuales.")).toBeVisible();
  });

  test("AUDIT-E2E-03 · D1 sí, D2 no", async ({ page, request }) => {
    const roleId = await crearRol(request, ["audit:view"]);
    const { username, userId } = await crearUsuario(request);
    await asignar(request, userId, roleId, MUNDO.empresa_a);

    const adminHeaders = (await sesionApi("admintenant", { tenant: TENANT })).headers;
    const cD1 = { ...adminHeaders, "X-Kontrol-Company": MUNDO.empresa_a };
    const cD2 = { ...adminHeaders, "X-Kontrol-Company": MUNDO.empresa_b };

    const r1 = await request.post(`${API}/documentos/tipos`, {
      headers: cD1,
      data: {
        company_id: MUNDO.empresa_a,
        code: `E2EAUD${marca().toUpperCase()}`.slice(0, 32),
        name: `Tipo AUD ${marca().toUpperCase()}`,
        allowed_mime_types: ["text/plain"],
        max_size_bytes: 1024 * 1024,
      },
    });
    expect(r1.status(), await r1.text()).toBeGreaterThanOrEqual(200);
    expect(r1.status()).toBeLessThan(300);
    const ridD1 = r1.headers()["x-request-id"];
    expect(ridD1).toBeTruthy();

    const r2 = await request.post(`${API}/documentos/tipos`, {
      headers: cD2,
      data: {
        company_id: MUNDO.empresa_b,
        code: `E2EAUD${marca().toUpperCase()}`.slice(0, 32),
        name: `Tipo AUD ${marca().toUpperCase()}`,
        allowed_mime_types: ["text/plain"],
        max_size_bytes: 1024 * 1024,
      },
    });
    expect(r2.status(), await r2.text()).toBeGreaterThanOrEqual(200);
    expect(r2.status()).toBeLessThan(300);
    const ridD2 = r2.headers()["x-request-id"];
    expect(ridD2).toBeTruthy();

    const { headers: auditorHeaders } = await sesionDeUsuario(username, {
      tenant: TENANT,
      empresa: MUNDO.empresa_a,
    });

    const resultD1 = await eventos(request, auditorHeaders, `request_id=${encodeURIComponent(ridD1)}`);
    expect(resultD1.total).toBeGreaterThanOrEqual(1);
    const eventD1 = resultD1.items.find((i) => i.action === "DOCUMENT_TYPE_CREATED");
    expect(eventD1, "debe existir evento DOCUMENT_TYPE_CREATED de D1").toBeTruthy();
    expect(eventD1!.entity_type).toBe("DocumentType");
    expect(eventD1!.company_id).toBe(MUNDO.empresa_a);
    expect(eventD1!.company_name).toBeTruthy();

    const resultD2 = await eventos(request, auditorHeaders, `request_id=${encodeURIComponent(ridD2)}`);
    expect(resultD2.total).toBe(0);

    await entrarEn(page, username, "D1");
    await goto(page, "/auditoria");
    await page.waitForLoadState("networkidle");
    await page.getByLabel("Correlación").fill(ridD1);
    await page.getByRole("button", { name: "Aplicar filtros" }).click();

    const fila = page.getByRole("row", { name: new RegExp(ridD1) });
    await expect(fila, "la fila del evento de D1 debe existir").toBeVisible();
    await expect(fila).toContainText("DOCUMENT_TYPE_CREATED");
    await expect(fila).toContainText(MUNDO.nombre_a);
  });

  test("AUDIT-E2E-04 · fecha de Caracas y filtro de fecha", async ({ request }) => {
    const roleId = await crearRol(request, ["audit:view"]);
    const { username, userId } = await crearUsuario(request);
    await asignar(request, userId, roleId, MUNDO.empresa_a);

    const adminHeaders = (await sesionApi("admintenant", { tenant: TENANT })).headers;
    const cD1 = { ...adminHeaders, "X-Kontrol-Company": MUNDO.empresa_a };
    const r = await request.post(`${API}/documentos/tipos`, {
      headers: cD1,
      data: {
        company_id: MUNDO.empresa_a,
        code: `E2EAUD${marca().toUpperCase()}`.slice(0, 32),
        name: `Tipo AUD ${marca().toUpperCase()}`,
        allowed_mime_types: ["text/plain"],
        max_size_bytes: 1024 * 1024,
      },
    });
    expect(r.status()).toBeGreaterThanOrEqual(200);
    expect(r.status()).toBeLessThan(300);
    const rid = r.headers()["x-request-id"];
    expect(rid).toBeTruthy();

    const { headers: auditorHeaders } = await sesionDeUsuario(username, {
      tenant: TENANT,
      empresa: MUNDO.empresa_a,
    });

    const result = await eventos(request, auditorHeaders, `request_id=${encodeURIComponent(rid)}`);
    const event = result.items.find((i) => i.action === "DOCUMENT_TYPE_CREATED");
    expect(event, "debe existir el evento para la prueba de fecha").toBeTruthy();

    const hoy = fechaCaracasHoy();
    const incluye = await eventos(
      request,
      auditorHeaders,
      `request_id=${encodeURIComponent(rid)}&desde=${hoy}&hasta=${hoy}`,
    );
    expect(incluye.items.some((i) => i.request_id === rid)).toBe(true);

    const ayer = fechaCaracasAyer();
    const excluye = await eventos(
      request,
      auditorHeaders,
      `request_id=${encodeURIComponent(rid)}&hasta=${ayer}`,
    );
    expect(excluye.items.some((i) => i.request_id === rid)).toBe(false);
  });

  test("AUDIT-E2E-05 · detalle seguro", async ({ page, request }) => {
    const roleId = await crearRol(request, ["audit:view"]);
    const { username, userId } = await crearUsuario(request);
    await asignar(request, userId, roleId, MUNDO.empresa_a);

    const adminHeaders = (await sesionApi("admintenant", { tenant: TENANT })).headers;
    const cD1 = { ...adminHeaders, "X-Kontrol-Company": MUNDO.empresa_a };
    const r = await request.post(`${API}/documentos/tipos`, {
      headers: cD1,
      data: {
        company_id: MUNDO.empresa_a,
        code: `E2EAUD${marca().toUpperCase()}`.slice(0, 32),
        name: `Tipo AUD ${marca().toUpperCase()}`,
        allowed_mime_types: ["text/plain"],
        max_size_bytes: 1024 * 1024,
      },
    });
    expect(r.status()).toBeGreaterThanOrEqual(200);
    expect(r.status()).toBeLessThan(300);
    const rid = r.headers()["x-request-id"];
    expect(rid).toBeTruthy();

    const { headers: auditorHeaders } = await sesionDeUsuario(username, {
      tenant: TENANT,
      empresa: MUNDO.empresa_a,
    });
    const apiResult = await eventos(request, auditorHeaders, `request_id=${encodeURIComponent(rid)}`);
    const event = apiResult.items.find((i) => i.action === "DOCUMENT_TYPE_CREATED");
    expect(event, "debe existir el evento para la prueba de detalle").toBeTruthy();
    const expectedDate = new Date(event!.event_time).toLocaleString("es-VE", { timeZone: "America/Caracas" });

    await entrarEn(page, username, "D1");
    await goto(page, "/auditoria");
    await page.waitForLoadState("networkidle");
    await page.getByLabel("Correlación").fill(rid);
    await page.getByRole("button", { name: "Aplicar filtros" }).click();

    const fila = page.getByRole("row", { name: new RegExp(rid) });
    await expect(fila, "la fila del evento debe existir").toBeVisible();
    await expect(fila).toContainText(expectedDate);

    await fila.getByRole("button", { name: "Ver detalle" }).click();
    const detalle = page.getByRole("region", { name: "Detalle del evento" });
    await expect(detalle).toBeVisible();
    await expect(detalle.getByText("Después", { exact: true })).toBeVisible();
    await expect(detalle.getByText("code", { exact: true })).toBeVisible();
    await expect(detalle.getByText("Antes", { exact: true })).toHaveCount(0);
    await expect(detalle.getByText("Evidencia", { exact: true })).toHaveCount(0);

    const axeResults = await new AxeBuilder({ page })
      .include("main")
      .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
      .analyze();
    const violations = axeResults.violations.filter((v) => v.impact === "serious" || v.impact === "critical");
    expect(violations, `violaciones axe serious/critical: ${JSON.stringify(violations)}`).toEqual([]);

    await page.setViewportSize({ width: 320, height: 800 });
    await page.getByRole("button", { name: "Colapsar menú" }).click();
    await expect
      .poll(
        () => page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth),
        "ancho de documento debe caber en viewport a 320 px",
      )
      .toBe(true);
  });

  test("SCAN-E2E-01 · rechazo por analizador deja evento persistente y mensaje seguro", async ({ page, request }) => {
    test.skip(!SCANNER, SIN_CLAMSCAN);
    test.skip(!USER || !PASSWORD, "KONTROL_E2E_USER / KONTROL_E2E_PASSWORD no configurados");
    test.setTimeout(120_000);

    await uiLogin(page);
    const c = await ctx(request);

    const tipoId = await createType(request, c);
    const typeName = await typeNameOf(request, c, tipoId);

    const titulo = `Rechazo AUD ${RUN}`;
    await createDocument(page, titulo, typeName);
    const docId = new URL(page.url()).pathname.split("/").pop();
    expect(docId, "URL de detalle debe contener id").toBeTruthy();

    await page.getByLabel(/^Archivo/).setInputFiles({
      name: "muestra.txt",
      mimeType: "text/plain",
      buffer: MUESTRA,
    });
    await page.getByRole("button", { name: "Cargar", exact: true }).click();

    const alerta = page.getByRole("main").getByRole("alert");
    await expect(alerta).toBeVisible({ timeout: 60000 });
    await expect(alerta).toContainText("rechazado por seguridad");
    await expect(alerta).toContainText(
      "El archivo fue rechazado por seguridad: el análisis lo identificó como malicioso. No se guardó.",
    );
    await expect(page.locator("body")).not.toContainText(/Eicar/i);
    await expect(page.locator("body")).not.toContainText(/signature/i);

    await expect(page.getByText("Este documento todavía no tiene archivos.")).toBeVisible();

    const adminHeaders = (await sesionApi("admintenant", { tenant: TENANT })).headers;
    const rechazo = await eventos(
      request,
      adminHeaders,
      `action=DOCUMENT_SCAN_REJECTED&entity_id=${encodeURIComponent(docId!)}`,
    );
    expect(rechazo.total).toBe(1);
    const item = rechazo.items[0];
    expect(item.scope).toBe("COMPANY");
    expect(item.company_id).toBe(c.company);
    expect(item.reason).toBe("MALWARE_DETECTED");
    const evidence = item.details.evidence as Record<string, unknown>;
    expect(Object.keys(evidence).sort()).toEqual([
      "category",
      "detected_mime",
      "document_type_id",
      "engine",
      "engine_version",
      "reason_code",
      "sha256",
      "size_bytes",
    ]);
    expect(evidence.sha256).toMatch(/^[0-9a-f]{64}$/i);
    expect(["clamav", "clamd"]).toContain(evidence.engine);
    expect(String(evidence.engine_version)).toBeTruthy();
    expect(JSON.stringify(item)).not.toContain("muestra.txt");
    expect(JSON.stringify(item)).not.toMatch(/Eicar/i);
  });
});
