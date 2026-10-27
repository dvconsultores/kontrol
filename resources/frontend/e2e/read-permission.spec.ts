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
  const code = `QA-RPE-${marca().toUpperCase()}`;
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
  const username = `rpe${marca()}`;
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

// SHELL-MAIN-SCROLL-REGION-NOT-FOCUSABLE (deuda registrada): a 320 px el <main> del shell tiene scroll y no es enfocable;
// se excluye SOLO esa violación cuando su único nodo es el propio <main> del shell. Cualquier otra, o esa misma regla
// sobre contenido de la pantalla, sigue fallando.
function sinDeudaDelShell<T extends { id: string; nodes: { html: string }[] }>(violaciones: T[]): T[] {
  return violaciones.filter((v) => !(v.id === "scrollable-region-focusable" && v.nodes.length === 1 && v.nodes[0].html.startsWith("<main ")));
}
test.describe("lecturas con capacidad declarada · Spec 003 (02D)", () => {
  test("READ-E2E-01 · actor con inventario:view en D1 lee existencias por UI y API", async ({
    page,
    request,
  }) => {
    const roleId = await crearRol(request, ["inventario:view"]);
    const { username, userId } = await crearUsuario(request);
    await asignar(request, userId, roleId, MUNDO.empresa_a);

    await entrarEn(page, username, "D1");
    await page.goto("/inventario/existencias");
    await expect(
      page.getByRole("heading", { level: 1, name: "Existencias" }),
      "debe mostrar el encabezado de existencias",
    ).toBeVisible();

    const response = await request.get(`${API}/inventory/balances`, {
      headers: await cabeceras(username, MUNDO.empresa_a),
    });
    expect(response.status(), `balances con inventario:view en D1: ${await response.text()}`).toBe(200);
  });

  test("READ-E2E-02 · actor sin inventario:view no ve el menú ni monta la pantalla", async ({
    page,
    request,
  }) => {
    const roleId = await crearRol(request, ["organization:view"]);
    const { username, userId } = await crearUsuario(request);
    await asignar(request, userId, roleId, MUNDO.empresa_a);

    await entrarEn(page, username, "D1");
    await expect(
      page.locator('nav a[href="/inventario/existencias"]'),
      "el menú no debe mostrar el enlace a existencias",
    ).toHaveCount(0);

    const pedidas: string[] = [];
    page.on("request", (r) => {
      if (r.url().includes("/api/v1/inventory/") && r.method() === "GET") {
        pedidas.push(r.url());
      }
    });

    await page.goto("/inventario/existencias");
    await expect(
      page.getByRole("heading", { level: 1, name: "Acceso prohibido" }),
      "debe mostrar el encabezado de acceso prohibido",
    ).toBeVisible();
    expect(pedidas, `no debe pedir rutas de inventory: ${JSON.stringify(pedidas)}`).toEqual([]);

    const axeResults = await new AxeBuilder({ page })
      .include("main")
      .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
      .analyze();
    const violations = axeResults.violations.filter((v) => v.impact === "serious" || v.impact === "critical");
    expect(
      violations,
      `violaciones axe serious/critical: ${JSON.stringify(violations)}`,
    ).toEqual([]);
  });

  test("READ-E2E-03 · la API directa tampoco se salta la capacidad en D1", async ({
    request,
  }) => {
    const roleId = await crearRol(request, ["organization:view"]);
    const { username, userId } = await crearUsuario(request);
    await asignar(request, userId, roleId, MUNDO.empresa_a);
    const headers = await cabeceras(username, MUNDO.empresa_a);

    const rutas = [
      `${API}/inventory/balances`,
      `${API}/maestros/terceros`,
      `${API}/sales/orders`,
    ];

    for (const ruta of rutas) {
      const response = await request.get(ruta, { headers });
      expect(response.status(), `${ruta} sin permiso: ${await response.text()}`).toBe(403);
      const body = await response.json();
      expect(body.code, `${ruta} debe devolver PERMISSION_DENIED`).toBe("PERMISSION_DENIED");
    }
  });

  test("READ-E2E-04 · capacidad solo en D2 no vale en D1 por UI ni API", async ({
    page,
    request,
  }) => {
    const roleId = await crearRol(request, ["inventario:view"]);
    const { username, userId } = await crearUsuario(request);
    await asignar(request, userId, roleId, MUNDO.empresa_b);

    await entrarEn(page, username, "D1");
    await page.goto("/inventario/existencias");
    await expect(
      page.getByRole("heading", { level: 1, name: "Sin autoridad en esta empresa" }),
      "debe mostrar el encabezado de alcance de empresa",
    ).toBeVisible();

    const response = await request.get(`${API}/inventory/balances`, {
      headers: await cabeceras(username, MUNDO.empresa_a),
    });
    expect(response.status(), `balances con inventario:view solo en D2, cabecera D1: ${await response.text()}`).toBe(403);
    const body = await response.json();
    expect(body.code, "debe devolver COMPANY_SCOPE_FORBIDDEN").toBe("COMPANY_SCOPE_FORBIDDEN");
  });

  test("READ-E2E-05 · ADMIN técnico no lee negocio y no ve indicadores", async ({
    page,
    request,
  }) => {
    const roleId = await rolPorCodigo(request, "ADMIN");
    const { username, userId } = await crearUsuario(request);
    await asignar(request, userId, roleId, null);

    const ordersResponse = await request.get(`${API}/sales/orders`, {
      headers: await cabeceras(username, MUNDO.empresa_a),
    });
    expect(ordersResponse.status(), `ADMIN no debe leer ventas: ${await ordersResponse.text()}`).toBe(403);
    const ordersBody = await ordersResponse.json();
    expect(ordersBody.code, "ADMIN en ventas debe devolver PERMISSION_DENIED").toBe("PERMISSION_DENIED");

    const dashboardResponse = await request.get(`${API}/reporting/dashboard`, {
      headers: await cabeceras(username, MUNDO.empresa_a),
    });
    expect(dashboardResponse.status(), `dashboard técnico: ${await dashboardResponse.text()}`).toBe(200);
    const dashboardBody = await dashboardResponse.json();
    expect(dashboardBody.indicators, "ADMIN no debe ver indicadores de negocio").toEqual({});
    expect(dashboardBody.vencimientos, "ADMIN no debe ver vencimientos de negocio").toEqual({});

    const respuestaTablero = page.waitForResponse(
      (r) => r.url().includes("/api/v1/reporting/dashboard") && r.request().method() === "GET",
    );
    await entrarEn(page, username, "D1");
    await expect(
      page.getByRole("heading", { level: 1, name: "Inicio" }),
      "debe mostrar el encabezado de inicio",
    ).toBeVisible();
    expect((await respuestaTablero).status()).toBe(200);
    await expect(
      page.getByRole("heading", { name: "Indicadores" }),
      "ADMIN no debe ver indicadores",
    ).toHaveCount(0);
  });

  test("READ-E2E-06 · FUNCIONAL_COMPLETO en D1 no lee D2", async ({ request }) => {
    const roleId = await rolPorCodigo(request, "FUNCIONAL_COMPLETO");
    const { username, userId } = await crearUsuario(request);
    await asignar(request, userId, roleId, MUNDO.empresa_a);

    const forbiddenResponse = await request.get(`${API}/sales/orders`, {
      headers: await cabeceras(username, MUNDO.empresa_b),
    });
    expect(forbiddenResponse.status(), `FUNCIONAL_COMPLETO en D1 no debe leer D2: ${await forbiddenResponse.text()}`).toBe(403);
    const forbiddenBody = await forbiddenResponse.json();
    expect(forbiddenBody.code, "cabecera D2 debe devolver COMPANY_SCOPE_FORBIDDEN").toBe("COMPANY_SCOPE_FORBIDDEN");

    const allowedResponse = await request.get(`${API}/sales/orders`, {
      headers: await cabeceras(username, MUNDO.empresa_a),
    });
    expect(allowedResponse.status(), `FUNCIONAL_COMPLETO en D1 debe leer D1: ${await allowedResponse.text()}`).toBe(200);
  });

  test("READ-E2E-07 · búsqueda, listas y conteos no filtran datos sin permiso", async ({
    request,
  }) => {
    const roleId = await crearRol(request, ["organization:view"]);
    const { username, userId } = await crearUsuario(request);
    await asignar(request, userId, roleId, MUNDO.empresa_a);
    const headers = await cabeceras(username, MUNDO.empresa_a);

    const rutas = [
      `${API}/maestros/catalogos/items/search?q=a`,
      `${API}/purchasing/aging`,
      `${API}/sales/open-items`,
      `${API}/reporting/reports/executive_ventas`,
    ];

    for (const ruta of rutas) {
      const response = await request.get(ruta, { headers });
      expect(response.status(), `${ruta} sin permiso: ${await response.text()}`).toBe(403);
      const body = await response.json();
      expect(body, `${ruta} no debe incluir items`).not.toHaveProperty("items");
      expect(body, `${ruta} no debe incluir rows`).not.toHaveProperty("rows");
    }
  });

  test("READ-E2E-08 · la UI autorizada sigue funcionando", async ({ page, request }) => {
    const roleId = await crearRol(request, ["ventas:view", "maestros:view", "reportes:view"]);
    const { username, userId } = await crearUsuario(request);
    await asignar(request, userId, roleId, MUNDO.empresa_a);

    await entrarEn(page, username, "D1");
    await page.goto("/ventas/ordenes");
    await expect(
      page.getByRole("heading", { level: 1, name: "Órdenes de venta" }),
      "debe mostrar el encabezado de órdenes de venta",
    ).toBeVisible();
    await expect(
      page.getByRole("heading", { name: "Acceso prohibido" }),
      "no debe mostrar acceso prohibido con ventas:view",
    ).toHaveCount(0);

    await page.goto("/reportes/centro");
    await expect(
      page.getByRole("button", { name: "Ejecutivos" }),
      "debe mostrar el botón de ejecutivos",
    ).toBeVisible();
    await expect(
      page.getByRole("button", { name: "Operativos" }),
      "no debe mostrar operativos sin inventario:view",
    ).toHaveCount(0);
  });

  test("READ-E2E-09 · Inicio y Centro de reportes a 320 px sin desbordamiento y sin violaciones axe graves", async ({ page, request }) => {
    const roleId = await crearRol(request, ["dashboard:view", "ventas:view", "reportes:view"]);
    const { username, userId } = await crearUsuario(request);
    await asignar(request, userId, roleId, MUNDO.empresa_a);

    await entrarEn(page, username, "D1");

    await page.setViewportSize({ width: 320, height: 800 });

    await page.goto("/");
    await expect(page.getByRole("heading", { name: "Indicadores" })).toBeVisible();
    const anchoInicio = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
    expect(anchoInicio).toBeLessThanOrEqual(0);
    const axeInicio = await new AxeBuilder({ page }).include("main").withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"]).analyze();
    const gravesInicio = sinDeudaDelShell(axeInicio.violations.filter((violation) => ["serious", "critical"].includes(violation.impact ?? "")));
    expect(gravesInicio).toEqual([]);

    await page.goto("/reportes/centro");
    await expect(page.getByRole("button", { name: "Ejecutivos" })).toBeVisible();
    const anchoCentro = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
    expect(anchoCentro).toBeLessThanOrEqual(0);
    const axeCentro = await new AxeBuilder({ page }).include("main").withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"]).analyze();
    const gravesCentro = sinDeudaDelShell(axeCentro.violations.filter((violation) => ["serious", "critical"].includes(violation.impact ?? "")));
    expect(gravesCentro).toEqual([]);
  });
});
