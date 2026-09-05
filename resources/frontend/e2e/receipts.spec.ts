/**
 * E2E de la recepción física — Spec 019.
 *
 * Frontend real → API real → backend real → PostgreSQL real. Lo que se
 * comprueba es lo que la Spec existe para cerrar: que dos cajas de doce entren
 * al inventario como veinticuatro unidades y no como dos, y que lo que se
 * observa en el muelle quede escrito.
 */
import { expect, test, type APIRequestContext, type Page } from "@playwright/test";

const TENANT = process.env.KONTROL_E2E_TENANT ?? "DEMO";
const USER = process.env.KONTROL_E2E_USER ?? "admin";
const PASSWORD = process.env.KONTROL_E2E_PASSWORD ?? "";
const API = process.env.KONTROL_E2E_API ?? "http://127.0.0.1:8000/api/v1";

const RUN = `${Date.now().toString(36)}${Math.random().toString(36).slice(2, 6)}`;

type Ctx = { token: string; company: string; headers: Record<string, string> };

async function ctx(request: APIRequestContext): Promise<Ctx> {
  const login = await request.post(`${API}/auth/login`, {
    data: { tenant_code: TENANT, username: USER, password: PASSWORD },
  });
  expect(login.ok(), `login: ${login.status()}`).toBeTruthy();
  const token = (await login.json()).access_token as string;
  const r = await request.get(`${API}/organization/companies`, { headers: { Authorization: `Bearer ${token}` } });
  expect(r.ok(), `companies: ${r.status()}`).toBeTruthy();
  const body = await r.json();
  const company = (Array.isArray(body) ? body : body.items)[0].id as string;
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

async function warehouse(request: APIRequestContext, c: Ctx): Promise<string> {
  const lista = await get(request, c, `/organization/warehouses?company_id=${c.company}`);
  const items = (lista.items as Array<{ id: string }>) ?? [];
  if (items.length > 0) return items[0].id;
  const ramas = await get(request, c, `/organization/branches?company_id=${c.company}`);
  const rama = ((ramas.items as Array<{ id: string }>) ?? [])[0];
  const branchId = rama?.id ?? ((await post(request, c, "/organization/branches",
    { company_id: c.company, code: `S-${RUN}`, name: "Sucursal E2E" })).id as string);
  const alm = await post(request, c, "/organization/warehouses",
    { company_id: c.company, branch_id: branchId, code: `W-${RUN}`, name: "Almacén E2E" });
  return alm.id as string;
}

/** Orden aprobada con una línea, producto con presentación de doce. */
async function mundo(request: APIRequestContext, c: Ctx, marca: string) {
  const alm = await warehouse(request, c);
  const unidad = await post(request, c, "/maestros/unidades",
    { code: `U-${marca}`, name: "Unidad", symbol: "u", decimals: 0 });
  const prod = await post(request, c, "/maestros/catalogos/items",
    { code: `P-${marca}`, name: `Producto ${marca}`, item_type: "PRODUCT", base_unit_id: unidad.id });
  const ayer = new Date(Date.now() - 86_400_000).toISOString();
  const caja = await post(request, c, `/maestros/productos/${prod.id}/presentaciones`,
    { code: `CAJA-${marca}`, name: "Caja de 12", factor_to_base: "12", valid_from: ayer });
  const prov = await post(request, c, "/maestros/terceros",
    { code: `PRV-${marca}`, name: "Proveedor E2E", roles: ["PROVEEDOR"] });
  const oc = await post(request, c, "/purchasing/orders",
    { code: `OC-${marca}`, supplier_id: prov.id, currency: "VED" });
  const linea = await post(request, c, `/purchasing/orders/${oc.id}/lines`,
    { product_id: prod.id, quantity_ordered: 100, unit_price: 5 });
  for (const target of ["SUBMITTED", "APPROVED"]) {
    await post(request, c, `/purchasing/orders/${oc.id}/transition`, { target });
  }
  return { alm, prod: prod.id as string, caja: caja.id as string, orden: oc.id as string, linea: linea.id as string };
}

async function uiLogin(page: Page): Promise<void> {
  await page.goto("/login");
  await page.getByLabel(/Empresa \(código\)/).fill(TENANT);
  await page.getByLabel(/Usuario/).fill(USER);
  await page.getByLabel(/Contraseña/).fill(PASSWORD);
  await page.getByRole("button", { name: "Iniciar sesión" }).click();
  await page.waitForURL((u) => !u.pathname.includes("login"), { timeout: 20000 });
}

async function irARecepciones(page: Page): Promise<void> {
  await page.locator('nav a[href="/compras/recepciones"]').first().click();
  await page.waitForURL((u) => u.pathname === "/compras/recepciones", { timeout: 15000 });
  await expect(page.getByRole("heading", { name: "Recepciones" })).toBeVisible();
  await page.waitForLoadState("networkidle");
}

test.describe("Spec 019 — recepción física", () => {
  test("dos cajas de doce entran al inventario como veinticuatro unidades", async ({ page, request }) => {
    const c = await ctx(request);
    const m = await mundo(request, c, `${RUN}A`);
    const rec = await post(request, c, "/purchasing/receipts", {
      code: `REC-${RUN}A`, order_id: m.orden, warehouse_id: m.alm,
      packing_list_ref: "PL-E2E", packages_declared: 2,
    });
    await post(request, c, `/purchasing/receipts/${rec.id}/lines`, {
      order_line_id: m.linea, product_id: m.prod, quantity_received: 2,
      quantity_accepted: 2, quantity_rejected: 0, presentation_id: m.caja,
      physical_condition: "BUENO", identification_ok: true, reference_ok: true,
    });

    await uiLogin(page);
    await irARecepciones(page);
    const fila = page.getByRole("row").filter({ hasText: `REC-${RUN}A` });
    await expect(fila).toContainText("Borrador");
    await expect(fila).toContainText("de 2");

    await fila.getByRole("button", { name: "confirmar arribo" }).click();
    await expect(fila).not.toContainText("sin confirmar", { timeout: 15000 });
    await fila.getByRole("button", { name: "confirmar", exact: true }).click();
    await expect(fila).toContainText("Confirmada", { timeout: 15000 });
    await fila.getByRole("button", { name: "conforme" }).click();
    await fila.getByRole("button", { name: "aceptar" }).click();
    await expect(fila).toContainText("Aceptada", { timeout: 15000 });

    const detalle = await get(request, c, `/purchasing/receipts/${rec.id}`);
    expect(detalle.record_issued_at).not.toBeNull();
    const lineas = detalle.lines as Array<{ base_quantity_received: string; conversion_factor_snapshot: string }>;
    expect(Number(lineas[0].base_quantity_received)).toBe(24);
    expect(Number(lineas[0].conversion_factor_snapshot)).toBe(12);

    const saldos = await get(request, c, `/inventory/balances?product_id=${m.prod}`);
    const saldo = (saldos.items as Array<{ product_id: string; qty_on_hand: string; location_id: string | null }>)
      .find((s) => s.product_id === m.prod);
    expect(Number(saldo?.qty_on_hand), "el inventario no recibió 24 unidades base").toBe(24);
    expect(saldo?.location_id, "recibir no es ubicar").toBeNull();
  });

  test("la pantalla registra la inspección y lo que se observó en el muelle", async ({ page, request }) => {
    const c = await ctx(request);
    const m = await mundo(request, c, `${RUN}B`);
    const rec = await post(request, c, "/purchasing/receipts", {
      code: `REC-${RUN}B`, order_id: m.orden, warehouse_id: m.alm,
      packing_list_ref: "PL-B", supplier_invoice_ref: "FAC-B", packages_declared: 5,
    });

    await uiLogin(page);
    await irARecepciones(page);
    const fila = page.getByRole("row").filter({ hasText: `REC-${RUN}B` });
    await fila.getByRole("button", { name: "detalle" }).click();
    await expect(page.getByRole("heading", { name: `Inspección de REC-${RUN}B` })).toBeVisible({ timeout: 15000 });

    await page.getByLabel(/Bultos contados/).fill("4");
    await page.getByLabel(/Observaciones/).fill("Una caja con el precinto forzado");
    await page.getByRole("button", { name: "Registrar diferencias" }).click();
    await expect(page.getByText(/no coincide/).first()).toBeVisible({ timeout: 15000 });

    const detalle = await get(request, c, `/purchasing/receipts/${rec.id}`);
    expect(detalle.packages_received).toBe(4);
    expect(detalle.packages_declared).toBe(5);
    expect(detalle.packing_list_match).toBe(false);
    expect(detalle.inspection_notes).toBe("Una caja con el precinto forzado");
    expect(detalle.inspected_at).not.toBeNull();
  });
});
