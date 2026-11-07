/**
 * E2E de la confirmación de inventario — Spec 021.
 *
 * Frontend real → API real → backend real → PostgreSQL real. Comprueba lo que
 * da sentido a la Spec: que aceptar una recepción **no** ponga la mercancía a
 * la venta, y que solo la confirmación la libere. Y el límite: confirmar no
 * ubica nada.
 */
import { type APIRequestContext, type Page } from "@playwright/test";

import { entrar, expect, sesionApi, test } from "./helpers/sesion";

const TENANT = process.env.KONTROL_E2E_TENANT ?? "DEMO";
const USER = process.env.KONTROL_E2E_USER ?? "admin";
const API = process.env.KONTROL_E2E_API ?? "http://127.0.0.1:8000/api/v1";
const RUN = `${Date.now().toString(36)}${Math.random().toString(36).slice(2, 6)}`;

type Ctx = { token: string; company: string; headers: Record<string, string> };

async function ctx(request: APIRequestContext): Promise<Ctx> {
  const token = (await sesionApi(USER, { tenant: TENANT })).token;
  const r = await request.get(`${API}/organization/companies`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  const body = await r.json();
  const company = body.items[0].id as string;
  return { token, company, headers: { Authorization: `Bearer ${token}`, "X-Kontrol-Company": company } };
}

async function post(request: APIRequestContext, c: Ctx, ruta: string, data: unknown) {
  const r = await request.post(`${API}${ruta}`, { headers: c.headers, data });
  expect([200, 201], `${ruta}: ${r.status()} ${await r.text()}`).toContain(r.status());
  return r.json();
}

async function get(request: APIRequestContext, c: Ctx, ruta: string) {
  const r = await request.get(`${API}${ruta}`, { headers: c.headers });
  expect(r.ok(), `${ruta}: ${r.status()}`).toBeTruthy();
  return r.json();
}

/** Deja una recepción aceptada, con su mercancía en `RECIBIDO`. */
async function recepcionAceptada(request: APIRequestContext, c: Ctx, marca: string) {
  const almacenes = await get(request, c, "/organization/warehouses");
  const almacen = (almacenes.items ?? almacenes)[0].id as string;
  const prov = await post(request, c, "/maestros/terceros", {
    code: `PRV-${marca}`, name: "Proveedor E2E", person_type: "JURIDICA",
    roles: ["PROVEEDOR"], status: "ACTIVE",
  });
  const prod = await post(request, c, "/maestros/catalogos/items", {
    code: `ART-${marca}`, name: "Artículo E2E", item_type: "PRODUCT", status: "ACTIVE",
  });
  const orden = await post(request, c, "/purchasing/orders", {
    code: `OC-${marca}`, supplier_id: prov.id, currency: "VED",
  });
  const ol = await post(request, c, `/purchasing/orders/${orden.id}/lines`, {
    product_id: prod.id, quantity_ordered: 500, unit_price: 1,
  });
  for (const target of ["SUBMITTED", "APPROVED"]) {
    await post(request, c, `/purchasing/orders/${orden.id}/transition`, { target });
  }
  const rec = await post(request, c, "/purchasing/receipts", {
    code: `RC-${marca}`, order_id: orden.id, warehouse_id: almacen,
  });
  const rl = await post(request, c, `/purchasing/receipts/${rec.id}/lines`, {
    order_line_id: ol.id, product_id: prod.id,
    quantity_received: 100, quantity_accepted: 100, quantity_rejected: 0,
  });
  await post(request, c, `/purchasing/receipts/${rec.id}/confirm`, {});
  await post(request, c, `/purchasing/receipts/${rec.id}/quality`, {});
  await post(request, c, `/purchasing/receipts/${rec.id}/quality`, { quality_status: "APPROVED" });
  await post(request, c, `/purchasing/receipts/${rec.id}/accept`, {});
  return { receipt: rec.id as string, code: rec.code as string, line: rl.id as string,
           product: prod.id as string };
}

async function uiLogin(page: Page): Promise<void> {
  await entrar(page, USER, { tenant: TENANT });
  await expect(page).toHaveURL(/\/$/, { timeout: 20_000 });
}

async function irAConfirmacion(page: Page): Promise<void> {
  await page.locator('nav a[href="/inventario/confirmacion"]').first().click();
  await page.waitForURL((u) => u.pathname === "/inventario/confirmacion", { timeout: 15_000 });
  await expect(page.getByRole("heading", { name: "Confirmación de inventario" })).toBeVisible();
  await page.waitForLoadState("networkidle");
}

test.describe("Spec 021 — confirmación de inventario", () => {
  test("aceptar no libera; confirmar sí, y la pantalla lo hace de punta a punta", async ({ page, request }) => {
    const c = await ctx(request);
    const m = await recepcionAceptada(request, c, `${RUN}A`);

    // Antes de confirmar: nada disponible, todo recibido.
    const antes = await get(request, c, `/inventory/balances?product_id=${m.product}`);
    const estadosAntes = (antes.items as Array<{ state: string; qty_on_hand: string }>);
    expect(estadosAntes.map((b) => b.state)).toEqual(["RECIBIDO"]);
    expect(Number(estadosAntes[0].qty_on_hand)).toBe(100);

    await uiLogin(page);
    await irAConfirmacion(page);
    await page.getByLabel(/Recepción aceptada/).selectOption(m.receipt);
    // La confirmación arranca pendiente: es el estado que esta Spec introduce.
    await expect(page.getByRole("definition").filter({ hasText: "PENDIENTE" }).first())
      .toBeVisible({ timeout: 15_000 });
    await expect(page.getByText("Faltan líneas por contar.")).toBeVisible();

    await page.getByLabel(/Contado \(base\)/).fill("100");
    await page.getByRole("button", { name: "Registrar conteo" }).click();
    // Se comprueba el efecto, no el aviso: la tabla muestra lo contado y deja
    // de faltar por contar. Un toast puede desvanecerse; el estado, no.
    await expect(page.getByText("Faltan líneas por contar.")).toBeHidden({ timeout: 15_000 });

    await page.getByLabel(/Cantidad a confirmar/).fill("100");
    await page.getByRole("button", { name: "Confirmar inventario" }).click();
    await expect(page.getByRole("heading", { name: "Decisiones tomadas" }))
      .toBeVisible({ timeout: 15_000 });

    // Después: la mercancía se liberó y el físico no cambió.
    const despues = await get(request, c, `/inventory/balances?product_id=${m.product}`);
    const porEstado: Record<string, number> = {};
    for (const b of despues.items as Array<{ state: string; qty_on_hand: string }>) {
      porEstado[b.state] = Number(b.qty_on_hand);
    }
    expect(porEstado.DISPONIBLE).toBe(100);
    expect(porEstado.RECIBIDO ?? 0).toBe(0);
    expect(Object.values(porEstado).reduce((a, b) => a + b, 0)).toBe(100);
  });

  test("confirmar no ubica: el almacén se conoce y la ubicación sigue nula", async ({ request }) => {
    const c = await ctx(request);
    const m = await recepcionAceptada(request, c, `${RUN}B`);
    await post(request, c, `/purchasing/receipts/${m.receipt}/lines/${m.line}/conteo`,
               { counted_base_quantity: "100", difference_kinds: [] });
    await post(request, c, `/purchasing/receipts/${m.receipt}/confirmacion-inventario`, {
      decisions: [{ receipt_line_id: m.line, target_state: "DISPONIBLE", base_quantity: "100" }],
    });

    const saldos = await get(request, c, `/inventory/balances?product_id=${m.product}`);
    for (const b of saldos.items as Array<{ location_id: string | null }>) {
      expect(b.location_id, "la confirmación asignó ubicación: eso es de la Spec 022").toBeNull();
    }
  });

  test("el resultado mixto reparte y conserva el físico", async ({ request }) => {
    const c = await ctx(request);
    const m = await recepcionAceptada(request, c, `${RUN}C`);
    await post(request, c, `/purchasing/receipts/${m.receipt}/lines/${m.line}/conteo`,
               { counted_base_quantity: "100", difference_kinds: ["CANTIDAD"] });
    await post(request, c, `/purchasing/receipts/${m.receipt}/confirmacion-inventario`, {
      decisions: [
        { receipt_line_id: m.line, target_state: "DISPONIBLE", base_quantity: "90" },
        { receipt_line_id: m.line, target_state: "RECHAZADO", base_quantity: "10",
          reason: "Diez unidades no aptas" },
      ],
    });

    const saldos = await get(request, c, `/inventory/balances?product_id=${m.product}`);
    const porEstado: Record<string, number> = {};
    for (const b of saldos.items as Array<{ state: string; qty_on_hand: string }>) {
      porEstado[b.state] = Number(b.qty_on_hand);
    }
    expect(porEstado.DISPONIBLE).toBe(90);
    expect(porEstado.RECHAZADO).toBe(10);
    expect(Object.values(porEstado).reduce((a, b) => a + b, 0)).toBe(100);
  });
});
