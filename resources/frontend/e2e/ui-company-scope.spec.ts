import { expect, entrarComoUsuario, iniciarSesion, sesionApi, test } from "./helpers/sesion";
import { mundoN6 } from "./helpers/n6-mundo";
import AxeBuilder from "@axe-core/playwright";
import type { APIRequestContext } from "@playwright/test";

const API = process.env.KONTROL_E2E_API ?? "http://127.0.0.1:8000/api/v1";
const TENANT = process.env.KONTROL_E2E_TENANT ?? "DEMO";
const PASSWORD = process.env.KONTROL_E2E_PASSWORD ?? "";

const MUNDO = mundoN6();
const marca = (): string => `${Date.now().toString(36)}${Math.random().toString(36).slice(2, 6)}`.toLowerCase();

async function cabeceras(username: string, empresa?: string): Promise<Record<string, string>> {
  const sesion = await iniciarSesion(username, { tenant: TENANT });
  const headers: Record<string, string> = { Authorization: `Bearer ${sesion.token}` };
  if (empresa) {
    headers["X-Kontrol-Company"] = empresa;
  }
  return headers;
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

async function rolPorCodigo(request: APIRequestContext, code: string): Promise<string> {
  const response = await request.get(`${API}/roles`, {
    headers: (await sesionApi("admintenant", { tenant: TENANT })).headers,
  });
  expect(response.status(), `listar roles: ${await response.text()}`).toBe(200);
  const body = await response.json();
  const items = body.items as Array<{ id: string; code: string }>;
  const role = items.find((r) => r.code === code);
  expect(role, `debe existir el rol ${code}`).toBeTruthy();
  return role!.id;
}

async function crearUsuario(request: APIRequestContext): Promise<{ username: string; userId: string }> {
  const username = `uis${marca()}`;
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

async function quitarAsignacion(request: APIRequestContext, userId: string, roleId: string): Promise<void> {
  const response = await request.delete(`${API}/users/${userId}/roles/${roleId}`, {
    headers: (await sesionApi("admintenant", { tenant: TENANT })).headers,
  });
  expect(response.status(), `quitar rol ${roleId} de ${userId}: ${await response.text()}`).toBeGreaterThanOrEqual(200);
  expect(response.status()).toBeLessThan(300);
}

async function entrarEn(
  page: import("@playwright/test").Page,
  username: string,
  codigoEmpresa: string,
): Promise<void> {
  await entrarComoUsuario(page, username, { tenant: TENANT, ruta: "/" });
  await expect(page.getByRole("heading", { name: "Seleccione una empresa" }), "debe pedir elegir empresa").toBeVisible();
  await page.getByTestId(`elegir-empresa-${codigoEmpresa}`).click();
  await expect(page.getByTestId("selector-empresa"), `selector debe mostrar empresa ${codigoEmpresa}`).toContainText(
    codigoEmpresa === "D1" ? MUNDO.nombre_a : MUNDO.nombre_b,
  );
}

async function cambiarA(
  page: import("@playwright/test").Page,
  codigoEmpresa: string,
  nombre: string,
): Promise<void> {
  await page.getByTestId("selector-empresa").click();
  await page.getByTestId(`opcion-empresa-${codigoEmpresa}`).click();
  await expect(page.getByTestId("selector-empresa"), `selector debe mostrar ${nombre}`).toContainText(nombre);
}

test.describe("autoridad por empresa en la interfaz · Spec 003", () => {
  test("E2E-UI-SCOPE-01 · actor con maestros:view y maestros:create en D1 ve menú y alta en su empresa", async ({
    page,
    request,
  }) => {
    const roleId = await crearRol(request, ["maestros:view", "maestros:create"]);
    const { username, userId } = await crearUsuario(request);
    await asignar(request, userId, roleId, MUNDO.empresa_a);
    await entrarEn(page, username, "D1");

    await expect(
      page.locator('nav a[href="/maestros/unidades"]'),
      "menú debe mostrar /maestros/unidades en D1",
    ).toHaveCount(1);

    await page.goto("/maestros/unidades");
    await expect(
      page.getByRole("heading", { level: 2, name: "Nueva unidad" }),
      "la sección de alta debe existir con maestros:create en D1",
    ).toBeVisible();
  });

  test("E2E-UI-SCOPE-02 · el enlace a /maestros/unidades desaparece al cambiar a D2", async ({
    page,
    request,
  }) => {
    const roleId = await crearRol(request, ["maestros:view", "maestros:create"]);
    const { username, userId } = await crearUsuario(request);
    await asignar(request, userId, roleId, MUNDO.empresa_a);
    await entrarEn(page, username, "D1");

    await expect(page.locator('nav a[href="/maestros/unidades"]')).toHaveCount(1);
    await cambiarA(page, "D2", MUNDO.nombre_b);
    await expect(
      page.locator('nav a[href="/maestros/unidades"]'),
      "menú no debe mostrar /maestros/unidades en D2",
    ).toHaveCount(0);
  });

  test("E2E-UI-SCOPE-03 · URL directa sin autoridad en la empresa activa muestra mensaje de alcance y no monta la pantalla", async ({
    page,
    request,
  }) => {
    const roleId = await crearRol(request, ["maestros:view", "maestros:create"]);
    const { username, userId } = await crearUsuario(request);
    await asignar(request, userId, roleId, MUNDO.empresa_a);
    await entrarEn(page, username, "D2");

    await page.goto("/maestros/unidades");
    await expect(
      page.getByRole("heading", { level: 1, name: "Sin autoridad en esta empresa" }),
      "debe mostrar encabezado de alcance de empresa",
    ).toBeVisible();
    await expect(page.getByRole("alert"), "debe mencionar la empresa activa").toContainText(MUNDO.nombre_b);
    await expect(
      page.getByRole("heading", { level: 2, name: "Nueva unidad" }),
      "no debe montar la pantalla de unidades",
    ).toHaveCount(0);

    const axeResults = await new AxeBuilder({ page })
      .include("main")
      .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
      .analyze();
    const violations = axeResults.violations.filter((v) => v.impact === "serious" || v.impact === "critical");
    expect(
      violations,
      `violaciones axe serious/critical: ${JSON.stringify(violations)}`,
    ).toEqual([]);

    await page.setViewportSize({ width: 320, height: 800 });
    await page.getByRole("button", { name: "Colapsar menú" }).click();
    await expect
      .poll(
        () => page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth),
        "ancho de documento debe caber en viewport a 320 px",
      )
      .toBe(true);
  });

  test("E2E-UI-SCOPE-04 · la API rechaza lecturas de maestros sin autoridad en la empresa de la cabecera", async ({
    request,
  }) => {
    const roleId = await crearRol(request, ["maestros:view", "maestros:create"]);
    const { username, userId } = await crearUsuario(request);
    await asignar(request, userId, roleId, MUNDO.empresa_a);

    const headers = await cabeceras(username, MUNDO.empresa_b);
    const response = await request.get(`${API}/maestros/unidades`, { headers });
    expect(response.status(), `GET maestros/unidades en D2: ${await response.text()}`).toBe(403);
    const body = await response.json();
    expect(body.code, `código de error en D2: ${JSON.stringify(body)}`).toBe("COMPANY_SCOPE_FORBIDDEN");
  });

  test("E2E-UI-SCOPE-05 · FUNCIONAL_COMPLETO asignado en D1 no vale en D2", async ({ page, request }) => {
    const funcionalCompletoId = await rolPorCodigo(request, "FUNCIONAL_COMPLETO");
    const { username, userId } = await crearUsuario(request);
    await asignar(request, userId, funcionalCompletoId, MUNDO.empresa_a);
    await entrarEn(page, username, "D1");

    await expect(page.locator('nav a[href="/maestros/unidades"]'), "maestros en D1").toHaveCount(1);
    await expect(page.locator('nav a[href="/ventas/ordenes"]'), "ventas en D1").toHaveCount(1);

    await cambiarA(page, "D2", MUNDO.nombre_b);
    await expect(page.locator('nav a[href="/maestros/unidades"]'), "maestros no en D2").toHaveCount(0);
    await expect(page.locator('nav a[href="/ventas/ordenes"]'), "ventas no en D2").toHaveCount(0);
  });

  test("E2E-UI-SCOPE-06 · rol técnico ADMIN no ve pantallas de negocio y URL directa muestra Acceso prohibido", async ({
    page,
    request,
  }) => {
    const adminId = await rolPorCodigo(request, "ADMIN");
    const { username, userId } = await crearUsuario(request);
    await asignar(request, userId, adminId, null);
    await entrarEn(page, username, "D1");

    await expect(page.locator('nav a[href="/seguridad/usuarios"]'), "seguridad visible para ADMIN").toHaveCount(1);
    await expect(page.locator('nav a[href="/maestros/unidades"]'), "maestros oculto para ADMIN").toHaveCount(0);
    await expect(page.locator('nav a[href="/ventas/ordenes"]'), "ventas oculto para ADMIN").toHaveCount(0);

    await page.goto("/maestros/unidades");
    await expect(
      page.getByRole("heading", { level: 1, name: "Acceso prohibido" }),
      "ADMIN sin permiso de negocio debe ver Acceso prohibido",
    ).toBeVisible();
  });

  test("E2E-UI-SCOPE-07 · el botón Crear fuente solo aparece con fiscal:create en todas las empresas", async ({
    page,
    request,
  }) => {
    const roleAId = await crearRol(request, ["fiscal:view", "fiscal:create"]);
    const roleBId = await crearRol(request, ["fiscal:view", "fiscal:create"]);
    const usuarioA = await crearUsuario(request);
    const usuarioB = await crearUsuario(request);
    await asignar(request, usuarioA.userId, roleAId, null);
    await asignar(request, usuarioB.userId, roleBId, MUNDO.empresa_a);

    await entrarEn(page, usuarioA.username, "D1");
    await page.goto("/fiscal/configuracion");
    await expect(page.getByRole("heading", { level: 1 }), "pantalla fiscal A").toBeVisible();
    await expect(
      page.getByRole("button", { name: "Crear fuente" }),
      "actor A con fiscal:create en todas las empresas ve Crear fuente",
    ).toHaveCount(1);

    await entrarComoUsuario(page, usuarioB.username, { tenant: TENANT, ruta: "/" });
    await expect(page.getByRole("heading", { name: "Seleccione una empresa" })).toBeVisible();
    await page.getByTestId("elegir-empresa-D1").click();
    await expect(page.getByTestId("selector-empresa")).toContainText(MUNDO.nombre_a);
    await page.goto("/fiscal/configuracion");
    await expect(page.getByRole("heading", { level: 1 }), "pantalla fiscal B").toBeVisible();
    await expect(
      page.getByRole("button", { name: "Crear fuente" }),
      "actor B sin fiscal:create en todas las empresas no ve Crear fuente",
    ).toHaveCount(0);
  });

  test("E2E-UI-SCOPE-08 · permisos de distintos roles por empresa se reflejan en el menú", async ({
    page,
    request,
  }) => {
    const rolMaestrosId = await crearRol(request, ["maestros:view"]);
    const rolVentasId = await crearRol(request, ["ventas:view"]);
    const { username, userId } = await crearUsuario(request);
    await asignar(request, userId, rolMaestrosId, MUNDO.empresa_a);
    await asignar(request, userId, rolVentasId, MUNDO.empresa_b);
    await entrarEn(page, username, "D1");

    await expect(page.locator('nav a[href="/maestros/unidades"]'), "maestros en D1").toHaveCount(1);
    await expect(page.locator('nav a[href="/ventas/ordenes"]'), "ventas oculto en D1").toHaveCount(0);

    await cambiarA(page, "D2", MUNDO.nombre_b);
    await expect(page.locator('nav a[href="/ventas/ordenes"]'), "ventas en D2").toHaveCount(1);
    await expect(page.locator('nav a[href="/maestros/unidades"]'), "maestros oculto en D2").toHaveCount(0);
  });

  test("E2E-UI-SCOPE-09 · al cambiar la asignación del rol de empresa se pierde la autoridad en la empresa activa", async ({
    page,
    request,
  }) => {
    const roleIdA = await crearRol(request, ["maestros:view", "maestros:create"]);
    const roleIdB = await crearRol(request, ["maestros:view", "maestros:create"]);
    const { username, userId } = await crearUsuario(request);
    await asignar(request, userId, roleIdA, null);
    await entrarEn(page, username, "D1");

    await page.goto("/maestros/unidades");
    await expect(page.getByRole("heading", { level: 2, name: "Nueva unidad" })).toBeVisible();

    await asignar(request, userId, roleIdB, MUNDO.empresa_b);
    await quitarAsignacion(request, userId, roleIdA);

    await page.reload();
    await expect(
      page.getByRole("heading", { level: 1, name: "Sin autoridad en esta empresa" }),
      "tras reasignar a D2 la empresa activa D1 pierde maestros",
    ).toBeVisible();
  });
});
