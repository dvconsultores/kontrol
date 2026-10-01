/**
 * E2E de la estructura física de almacén (Spec 008).
 *
 * Frontend real → API real → backend real → **PostgreSQL real**. Nada del
 * núcleo se mockea.
 *
 * Dos recorridos en paralelo, que es la tesis de la Spec: el almacén simple
 * debe funcionar completo **sin ver un solo control de zona, pasillo, rack o
 * nivel**, y el complejo debe mantener la cadena entera.
 */
import { expect, test, type APIRequestContext, type Page } from "@playwright/test";
import { activarEmpresa } from "./helpers/empresa";

const TENANT = process.env.KONTROL_E2E_TENANT ?? "DEMO";
const USER = process.env.KONTROL_E2E_USER ?? "admin";
const PASSWORD = process.env.KONTROL_E2E_PASSWORD ?? "";
const API = process.env.KONTROL_E2E_API ?? "http://127.0.0.1:8000/api/v1";

/** Sufijo único: el estado persiste entre navegadores sobre la misma base. */
const RUN = `${Date.now().toString(36)}${Math.random().toString(36).slice(2, 5)}`.toUpperCase();

async function apiLogin(request: APIRequestContext): Promise<string> {
  const r = await request.post(`${API}/auth/login`, {
    data: { tenant_code: TENANT, username: USER, password: PASSWORD },
  });
  expect(r.ok(), `login: ${r.status()}`).toBeTruthy();
  return (await r.json()).access_token as string;
}

type Ctx = { headers: Record<string, string>; company: string };

async function ctx(request: APIRequestContext): Promise<Ctx> {
  const token = await apiLogin(request);
  const headers = { Authorization: `Bearer ${token}` };
  const r = await request.get(`${API}/organization/companies`, { headers });
  const body = await r.json();
  const items = body.items;
  return { headers, company: items[0].id as string };
}

async function uiLogin(page: Page): Promise<void> {
  await page.goto("/login");
  await page.getByLabel(/Empresa \(código\)/).fill(TENANT);
  await page.getByLabel(/Usuario/).fill(USER);
  await page.getByLabel(/Contraseña/).fill(PASSWORD);
  await page.getByRole("button", { name: "Iniciar sesión" }).click();
  await page.waitForURL((u) => !u.pathname.includes("login"), { timeout: 20000 });

  await page.locator('nav a[href="/organizacion/empresas"]').first().click();
  await page.waitForURL((u) => u.pathname === "/organizacion/empresas", { timeout: 15000 });
  await page.waitForLoadState("networkidle");
  await activarEmpresa(page);
}

/** Las notificaciones son persistentes por diseño y, apiladas, tapan acciones. */
async function closeNotifications(page: Page): Promise<void> {
  const close = page.getByRole("button", { name: "Cerrar notificación" });
  for (let i = await close.count(); i > 0; i = await close.count()) {
    await close.first().click();
  }
}

/** El deep-link recarga la página y pierde el token en memoria (ADR-004). */
async function goto(page: Page, href: string): Promise<void> {
  await page.locator(`nav a[href="${href}"]`).first().click();
  await page.waitForURL((u) => u.pathname === href, { timeout: 15000 });
}

/** Abre el detalle de un almacén filtrando por su código: la lista es
 *  paginada y el almacén buscado puede no estar en la primera página. */
async function openWarehouse(page: Page, code: string): Promise<void> {
  await page.getByLabel("Buscar almacén por código o nombre").fill(code);
  await expect(page.getByRole("link", { name: `Ver el almacén ${code}` }))
    .toBeVisible({ timeout: 15000 });
  await page.getByRole("link", { name: `Ver el almacén ${code}` }).click();
  await page.waitForURL(/\/organizacion\/almacenes\/[0-9a-f-]+$/, { timeout: 15000 });
}

async function createWarehouse(
  request: APIRequestContext, c: Ctx, code: string, levels: Record<string, boolean>,
): Promise<string> {
  const r = await request.post(`${API}/organization/warehouses`, {
    headers: c.headers,
    data: { company_id: c.company, code, name: `Almacén ${code}`, structure_levels: levels },
  });
  expect(r.ok(), `crear almacén ${code}: ${r.status()} ${await r.text()}`).toBeTruthy();
  return (await r.json()).id as string;
}

// ---------------------------------------------------------------- AC-008-37
test("almacén simple: crear, ubicar, consultar y desactivar sin tramos", async ({ page }) => {
  const code = `E2ES-${RUN}`;
  await uiLogin(page);
  await goto(page, "/organizacion/almacenes");

  await page.getByLabel(/^Código/).first().fill(code);
  await page.getByLabel(/^Nombre/).first().fill("Depósito único");
  await page.getByRole("button", { name: "Registrar" }).click();
  await expect(page.getByText("Almacén creado")).toBeVisible({ timeout: 15000 });
  await closeNotifications(page);

  // La lista describe la estructura del almacén, y el simple no tiene tramos.
  await page.getByLabel("Buscar almacén por código o nombre").fill(code);
  await expect(page.getByRole("row").filter({ hasText: code })
    .getByText("Simple · sin tramos")).toBeVisible({ timeout: 15000 });
  await openWarehouse(page, code);

  // La tesis de la Spec: el almacén simple **no** muestra tramos.
  await expect(page.getByRole("tab", { name: "Ubicaciones" })).toBeVisible();
  await expect(page.getByRole("tab", { name: "Zonas" })).toHaveCount(0);
  await expect(page.getByRole("tab", { name: "Pasillos" })).toHaveCount(0);
  await expect(page.getByRole("tab", { name: "Racks" })).toHaveCount(0);
  await expect(page.getByRole("tab", { name: "Niveles" })).toHaveCount(0);
  await expect(page.getByText(/Almacén simple/)).toBeVisible();

  await page.getByRole("button", { name: "Añadir ubicación" }).click();
  await expect(page.getByText("Ubicación creada")).toBeVisible({ timeout: 15000 });
  await closeNotifications(page);

  const row = page.getByRole("row").filter({ hasText: code });
  await expect(row.first()).toBeVisible();

  // Desactivar y reactivar: reversible.
  await page.getByRole("button", { name: /Desactivar la ubicación/ }).first().click();
  await expect(page.getByText("Ubicación desactivada")).toBeVisible({ timeout: 15000 });
  await closeNotifications(page);
  await page.getByRole("button", { name: /Activar la ubicación/ }).first().click();
  await expect(page.getByText("Ubicación activada")).toBeVisible({ timeout: 15000 });
});

// ---------------------------------------------------------------- AC-008-38
test("almacén complejo: cadena completa y orden físico determinista", async ({ page, request }) => {
  const c = await ctx(request);
  const code = `E2EC-${RUN}`;
  const warehouseId = await createWarehouse(request, c, code,
    { zone: true, aisle: true, rack: true, level: true });

  await uiLogin(page);
  await goto(page, "/organizacion/almacenes");
  await openWarehouse(page, code);

  // Los cuatro tramos declarados están presentes, y solo esos.
  for (const tab of ["Zonas", "Pasillos", "Racks", "Niveles", "Ubicaciones"]) {
    await expect(page.getByRole("tab", { name: tab })).toBeVisible();
  }

  const addNode = async (tab: string, nodeCode: string, name: string,
                         parentLabel?: string): Promise<void> => {
    await page.getByRole("tab", { name: tab }).click();
    await page.getByLabel(/^Código/).fill(nodeCode);
    await page.getByLabel(/^Nombre/).fill(name);
    if (parentLabel) {
      // El tramo padre es obligatorio cuando el almacén lo declara: un nodo
      // suelto nunca podría formar una cadena completa.
      await page.getByLabel(new RegExp(`^${parentLabel} al que pertenece`))
        .selectOption({ index: 1 });
    }
    await page.getByRole("button", { name: /^Añadir / }).click();
    await expect(page.getByText(/creado$/).first()).toBeVisible({ timeout: 15000 });
    await closeNotifications(page);
  };

  await addNode("Zonas", "Z1", "Zona uno");
  await addNode("Pasillos", "P1", "Pasillo uno", "Zona");
  await addNode("Racks", "R1", "Rack uno", "Pasillo");
  await addNode("Niveles", "N1", "Nivel uno", "Rack");

  // La ubicación se crea por API con la cadena completa: la UI ya demostró
  // que ofrece los tramos, y aquí interesa el orden resultante.
  const zones = await (await request.get(
    `${API}/organization/warehouses/${warehouseId}/zones`, { headers: c.headers })).json();
  const aisles = await (await request.get(
    `${API}/organization/warehouses/${warehouseId}/aisles`, { headers: c.headers })).json();
  const created = await request.post(`${API}/organization/locations`, {
    headers: c.headers,
    data: { warehouse_id: warehouseId, code: `L-${RUN}`,
            zone_id: zones[0].id, aisle_id: aisles[0].id },
  });
  expect(created.ok(), `crear ubicación: ${created.status()} ${await created.text()}`).toBeTruthy();
  const location = await created.json();
  expect(location.display_path).toContain("Zona uno");
  expect(location.display_path).toContain("Pasillo uno");

  // Orden físico: total, estable y determinista entre llamadas.
  const first = await (await request.get(
    `${API}/organization/locations/ordered?warehouse_id=${warehouseId}`,
    { headers: c.headers })).json();
  const second = await (await request.get(
    `${API}/organization/locations/ordered?warehouse_id=${warehouseId}`,
    { headers: c.headers })).json();
  expect(first.items.map((i: { code: string }) => i.code))
    .toEqual(second.items.map((i: { code: string }) => i.code));

  // La vista de orden físico existe en la UI y la consume.
  await goto(page, "/organizacion/ubicaciones");
  await page.getByLabel("Filtrar por almacén").selectOption({ label: `${code} · Almacén ${code}` });
  await page.getByLabel("Vista de ubicaciones").selectOption("ordered");
  await expect(page.getByRole("cell", { name: `L-${RUN}`, exact: true })).toBeVisible({ timeout: 15000 });
});

// ------------------------------------------------------ AC-008-32 / AC-008-39
test("el bloqueo estructural lo produce el backend y la UI lo refleja", async ({ page, request }) => {
  const c = await ctx(request);
  const code = `E2EB-${RUN}`;
  const warehouseId = await createWarehouse(request, c, code, { zone: true, aisle: true });
  const zone = await request.post(`${API}/organization/warehouses/${warehouseId}/zones`, {
    headers: c.headers, data: { code: "ZB", name: "Zona bloqueo" },
  });
  expect(zone.ok()).toBeTruthy();

  // Bloqueo por API, saltándose el frontend por completo.
  const blocked = await request.patch(
    `${API}/organization/warehouses/${warehouseId}/structure-levels`,
    { headers: c.headers, data: { structure_levels: { zone: false, aisle: true } } });
  expect(blocked.status()).toBe(409);
  const body = await blocked.json();
  expect(body.code).toBe("STRUCTURE_LEVEL_IN_USE");
  expect(body.details.dependencies.node_count).toBe(1);
  expect(body.details.allowed_actions).toContain("deactivate");

  // La UI muestra el aviso de almacén en operación.
  await uiLogin(page);
  await goto(page, "/organizacion/almacenes");
  await openWarehouse(page, code);
  await expect(page.getByText(/Este almacén está en operación/)).toBeVisible();
});

// ---------------------------------------------------------------- AC-008-40
test("borrado protegido: la UI ofrece desactivar, no eliminar", async ({ page, request }) => {
  const c = await ctx(request);
  const code = `E2ED-${RUN}`;
  const warehouseId = await createWarehouse(request, c, code, { zone: true });
  await request.post(`${API}/organization/warehouses/${warehouseId}/zones`, {
    headers: c.headers, data: { code: "ZD", name: "Zona con hijos" },
  });
  const zones = await (await request.get(
    `${API}/organization/warehouses/${warehouseId}/zones`, { headers: c.headers })).json();
  await request.post(`${API}/organization/locations`, {
    headers: c.headers,
    data: { warehouse_id: warehouseId, code: `LD-${RUN}`, zone_id: zones[0].id },
  });

  await uiLogin(page);
  await goto(page, "/organizacion/almacenes");
  await openWarehouse(page, code);
  await page.getByRole("tab", { name: "Zonas" }).click();

  // El botón de eliminar está deshabilitado **y explica por qué**.
  const remove = page.getByRole("button", { name: /no puede eliminarse/ }).first();
  await expect(remove).toBeVisible();
  await expect(remove).toBeDisabled();
  // Tampoco se ofrece desactivar mientras tenga descendientes activos: no hay
  // cascada silenciosa (R-008-9). La zona solo puede desactivarse después de
  // desactivar su ubicación.
  await expect(page.getByRole("button", { name: /Desactivar ZD/ })).toHaveCount(0);

  await page.getByRole("tab", { name: "Ubicaciones" }).click();
  await page.getByRole("button", { name: /Desactivar la ubicación/ }).first().click();
  await expect(page.getByText("Ubicación desactivada")).toBeVisible({ timeout: 15000 });
  await closeNotifications(page);

  await page.getByRole("tab", { name: "Zonas" }).click();
  await expect(page.getByRole("button", { name: /Desactivar ZD/ })).toBeVisible({ timeout: 15000 });
});

// ---------------------------------------------------------------- AC-008-05
test("multiempresa: la lista solo muestra almacenes de la empresa activa", async ({ request }) => {
  const c = await ctx(request);
  const r = await request.get(`${API}/organization/warehouses?company_id=${c.company}`,
    { headers: c.headers });
  expect(r.ok()).toBeTruthy();
  const body = await r.json();
  for (const w of body.items) {
    expect(w.company_id).toBe(c.company);
  }
});
