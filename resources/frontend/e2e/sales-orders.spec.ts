/**
 * E2E del ciclo del pedido — Spec 030 (`RESERVATION TRIGGER = ORDER_CONFIRMATION`).
 *
 * Frontend real → API real → backend real → PostgreSQL real. Los datos los crea
 * la propia prueba por API (cliente, producto, stock, pedido); la pantalla
 * confirma, cancela con motivo y muestra lo que el backend dicta.
 *
 * Requiere el stack levantado y credenciales E2E.
 */
import { expect, test, type APIRequestContext, type Page } from "@playwright/test";

const TENANT = process.env.KONTROL_E2E_TENANT ?? "DEMO";
const USER = process.env.KONTROL_E2E_USER ?? "admin";
const PASSWORD = process.env.KONTROL_E2E_PASSWORD ?? "";
const API = process.env.KONTROL_E2E_API ?? "http://127.0.0.1:8000/api/v1";

/** Sufijo único: el estado persiste entre navegadores en la misma base. */
const RUN = `${Date.now().toString(36)}${Math.random().toString(36).slice(2, 6)}`;

type Ctx = { token: string; company: string; headers: Record<string, string> };

async function apiLogin(request: APIRequestContext): Promise<string> {
  const r = await request.post(`${API}/auth/login`, {
    data: { tenant_code: TENANT, username: USER, password: PASSWORD },
  });
  expect(r.ok(), `login: ${r.status()}`).toBeTruthy();
  return (await r.json()).access_token as string;
}

async function ctx(request: APIRequestContext): Promise<Ctx> {
  const token = await apiLogin(request);
  const r = await request.get(`${API}/organization/companies`, { headers: { Authorization: `Bearer ${token}` } });
  expect(r.ok(), `companies: ${r.status()}`).toBeTruthy();
  const body = await r.json();
  const items = Array.isArray(body) ? body : body.items;
  const company = items[0].id as string;
  return { token, company, headers: { Authorization: `Bearer ${token}`, "X-Kontrol-Company": company } };
}

async function post(request: APIRequestContext, c: Ctx, ruta: string, data: unknown): Promise<Record<string, unknown>> {
  const r = await request.post(`${API}${ruta}`, { headers: c.headers, data });
  expect([200, 201], `${ruta}: ${r.status()} ${await r.text()}`).toContain(r.status());
  return (await r.json()) as Record<string, unknown>;
}

async function get(request: APIRequestContext, c: Ctx, ruta: string): Promise<Record<string, unknown>> {
  const r = await request.get(`${API}${ruta}`, { headers: c.headers });
  expect(r.ok(), `${ruta}: ${r.status()}`).toBeTruthy();
  return (await r.json()) as Record<string, unknown>;
}

/** Un almacén de la empresa activa (crea uno si no hay). */
async function warehouse(request: APIRequestContext, c: Ctx): Promise<string> {
  const lista = await get(request, c, `/organization/warehouses?company_id=${c.company}`);
  const items = (lista.items as Array<{ id: string }>) ?? [];
  if (items.length > 0) return items[0].id;
  const ramas = await get(request, c, `/organization/branches?company_id=${c.company}`);
  const rama = ((ramas.items as Array<{ id: string }>) ?? [])[0];
  let branchId = rama?.id;
  if (!branchId) {
    const nueva = await post(request, c, "/organization/branches", { company_id: c.company, code: `S-${RUN}`, name: "Sucursal E2E" });
    branchId = nueva.id as string;
  }
  const alm = await post(request, c, "/organization/warehouses", {
    company_id: c.company, branch_id: branchId, code: `W-${RUN}`, name: "Almacén E2E",
  });
  return alm.id as string;
}

/** Cliente, producto con stock y pedido en borrador con una línea. */
async function pedidoListo(request: APIRequestContext, c: Ctx, marca: string, stock: number, cantidad: number) {
  const alm = await warehouse(request, c);
  const cli = await post(request, c, "/maestros/terceros", { code: `C-${marca}`, name: `Cliente ${marca}`, roles: ["CLIENTE"] });
  const prod = await post(request, c, "/maestros/catalogos/items", { code: `P-${marca}`, name: `Producto ${marca}`, item_type: "PRODUCT" });
  const tipo = await post(request, c, "/inventory/movement-types", { code: `ENT-${marca}`, name: "Entrada E2E", direction: "IN" });
  await post(request, c, "/inventory/movements", {
    warehouse_id: alm, product_id: prod.id, movement_type_id: tipo.id, quantity: stock, unit_cost: 1, currency: "VED",
  });
  const ped = await post(request, c, "/sales/orders", { code: `OV-${marca}`, customer_id: cli.id, currency: "VED", warehouse_id: alm });
  await post(request, c, `/sales/orders/${ped.id}/lines`, { product_id: prod.id, quantity: cantidad, unit_price: 10 });
  return { pedido: ped.id as string, codigo: `OV-${marca}`, producto: prod.id as string, almacen: alm };
}

async function uiLogin(page: Page): Promise<void> {
  await page.goto("/login");
  await page.getByLabel(/Empresa \(código\)/).fill(TENANT);
  await page.getByLabel(/Usuario/).fill(USER);
  await page.getByLabel(/Contraseña/).fill(PASSWORD);
  await page.getByRole("button", { name: "Iniciar sesión" }).click();
  await page.waitForURL((u) => !u.pathname.includes("login"), { timeout: 20000 });
}

async function irAOrdenes(page: Page): Promise<void> {
  await page.locator('nav a[href="/ventas/ordenes"]').first().click();
  await page.waitForURL((u) => u.pathname === "/ventas/ordenes", { timeout: 15000 });
  await expect(page.getByRole("heading", { name: "Órdenes de venta" })).toBeVisible();
  await page.waitForLoadState("networkidle");
}

function fila(page: Page, codigo: string) {
  return page.getByRole("row").filter({ hasText: codigo });
}

test.describe("Spec 030 — confirmar reserva y liberar", () => {
  test("confirmar un pedido de contado lo deja liberado a preparación con la reserva hecha", async ({ page, request }) => {
    const c = await ctx(request);
    const m = await pedidoListo(request, c, `${RUN}A`, 10, 4);
    await uiLogin(page);
    await irAOrdenes(page);

    const row = fila(page, m.codigo);
    await expect(row).toContainText("Borrador");
    await row.getByRole("button", { name: "Confirmar" }).click();
    await expect(row).toContainText("Liberado a preparación", { timeout: 15000 });
    await expect(row).toContainText("4 en base");

    // La pantalla no decide: lo que muestra coincide con lo que el backend dice.
    const pedido = await get(request, c, `/sales/orders/${m.pedido}`);
    expect(pedido.status).toBe("RELEASED");
    expect(pedido.eligible_for_picking).toBe(true);
    const lineas = pedido.lines as Array<{ reservations: Array<{ status: string; base_quantity: string; trigger: string }> }>;
    expect(lineas[0].reservations[0].status).toBe("ACTIVE");
    expect(lineas[0].reservations[0].trigger).toBe("ORDER_CONFIRMATION");
    expect(Number(lineas[0].reservations[0].base_quantity)).toBe(4);
    // Ya no es editable: los botones de borrador desaparecen
    await expect(row.getByRole("button", { name: "Confirmar" })).toHaveCount(0);
  });

  test("sin disponible el pedido sigue en borrador y la pantalla dice cuánto falta", async ({ page, request }) => {
    const c = await ctx(request);
    const m = await pedidoListo(request, c, `${RUN}B`, 3, 8);
    await uiLogin(page);
    await irAOrdenes(page);
    const row = fila(page, m.codigo);
    await row.getByRole("button", { name: "Confirmar" }).click();
    await expect(page.getByText("No hay disponible suficiente")).toBeVisible({ timeout: 15000 });
    await expect(page.getByText(/pedido 8\.000000, disponible 3\.000000/)).toBeVisible();
    await expect(row).toContainText("Borrador");
    const pedido = await get(request, c, `/sales/orders/${m.pedido}`);
    expect(pedido.status).toBe("DRAFT");
  });

  test("cancelar exige motivo y libera la reserva", async ({ page, request }) => {
    const c = await ctx(request);
    const m = await pedidoListo(request, c, `${RUN}C`, 10, 5);
    await post(request, c, `/sales/orders/${m.pedido}/submit`, {});
    await uiLogin(page);
    await irAOrdenes(page);
    const row = fila(page, m.codigo);
    await expect(row).toContainText("Liberado a preparación");
    await row.getByRole("button", { name: "Cancelar" }).click();
    const dialogo = page.getByRole("dialog");
    await expect(dialogo).toBeVisible();
    await dialogo.getByLabel(/Motivo/).fill("Cliente desistió (E2E)");
    await dialogo.getByRole("button", { name: "Confirmar" }).click();
    await expect(row).toContainText("Cancelado", { timeout: 15000 });
    await expect(row).toContainText("Cliente desistió (E2E)");

    const reservas = await get(request, c, "/inventory/reservations");
    const propias = (reservas.items as Array<{ source_order_id: string | null; status: string; release_reason: string | null }>)
      .filter((r) => r.source_order_id === m.pedido);
    expect(propias).toHaveLength(1);
    expect(propias[0].status).toBe("RELEASED");
    expect(propias[0].release_reason).toBe("ORDER_CANCELLED");
  });

  test("la política de reserva muestra el disparador fijo y admite vigencia", async ({ page, request }) => {
    const c = await ctx(request);
    await uiLogin(page);
    await irAOrdenes(page);
    await expect(page.getByText(/Disparador: ORDER_CONFIRMATION \(fijo\)/)).toBeVisible();
    await page.getByLabel(/Vigencia \(días\)/).fill("3");
    await page.getByRole("button", { name: "Guardar" }).click();
    await expect(page.getByText(/Vigencia 3 días/)).toBeVisible({ timeout: 15000 });
    const politica = await get(request, c, "/sales/settings/reservation");
    expect(politica.reservation_ttl_days).toBe(3);
    expect(politica.trigger_configurable).toBe(false);
    // Se deja como estaba para no condicionar a los demás navegadores
    const r = await request.put(`${API}/sales/settings/reservation`, { headers: c.headers, data: { reservation_ttl_days: null } });
    expect(r.ok()).toBeTruthy();
  });
});
