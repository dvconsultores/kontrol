/**
 * E2E de las incidencias de recepción — Spec 020.
 *
 * Frontend real → API real → backend real → PostgreSQL real. Se comprueban las
 * tres etapas del proceso: registrar la diferencia, escalarla a Compras y
 * registrar el tratamiento; y el límite que da sentido a la Spec: registrar el
 * tratamiento no mueve inventario.
 */
import { type APIRequestContext, type Page } from "@playwright/test";

import { entrar, expect, sesionApi, test } from "./helpers/sesion";

const TENANT = process.env.KONTROL_E2E_TENANT ?? "DEMO";
const USER = process.env.KONTROL_E2E_USER ?? "admin";
const API = process.env.KONTROL_E2E_API ?? "http://127.0.0.1:8000/api/v1";
const RUN = `${Date.now().toString(36)}${Math.random().toString(36).slice(2, 6)}`;

type Ctx = { token: string; company: string; headers: Record<string, string> };

async function ctx(request: APIRequestContext): Promise<Ctx> {
  const sesion = await sesionApi(USER, { tenant: TENANT });
  const token = sesion.token;
  const r = await request.get(`${API}/organization/companies`, { headers: { Authorization: `Bearer ${token}` } });
  expect(r.ok()).toBeTruthy();
  const body = await r.json();
  const company = body.items[0].id as string;
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
  const ramas = await get(request, c, `/organization/branches`);
  const rama = ((ramas.items as Array<{ id: string }>) ?? [])[0];
  const branchId = rama?.id ?? ((await post(request, c, "/organization/branches",
    { company_id: c.company, code: `S-${RUN}`, name: "Sucursal E2E" })).id as string);
  return (await post(request, c, "/organization/warehouses",
    { company_id: c.company, branch_id: branchId, code: `W-${RUN}`, name: "Almacén E2E" })).id as string;
}

/** Recepción aceptada con una línea de 20 unidades, tres de ellas dañadas. */
async function recepcionConDano(request: APIRequestContext, c: Ctx, marca: string) {
  const alm = await warehouse(request, c);
  const prod = await post(request, c, "/maestros/catalogos/items",
    { code: `P-${marca}`, name: `Producto ${marca}`, item_type: "PRODUCT" });
  const prov = await post(request, c, "/maestros/terceros",
    { code: `PRV-${marca}`, name: "Proveedor E2E", roles: ["PROVEEDOR"] });
  const oc = await post(request, c, "/purchasing/orders",
    { code: `OC-${marca}`, supplier_id: prov.id, currency: "VED" });
  const linea = await post(request, c, `/purchasing/orders/${oc.id}/lines`,
    { product_id: prod.id, quantity_ordered: 100, unit_price: 5 });
  for (const target of ["SUBMITTED", "APPROVED"]) {
    await post(request, c, `/purchasing/orders/${oc.id}/transition`, { target });
  }
  const rec = await post(request, c, "/purchasing/receipts",
    { code: `REC-${marca}`, order_id: oc.id, warehouse_id: alm });
  await post(request, c, `/purchasing/receipts/${rec.id}/lines`, {
    order_line_id: linea.id, product_id: prod.id, quantity_received: 20,
    quantity_accepted: 17, quantity_rejected: 3, physical_condition: "DAÑADO",
    damaged_quantity: 3, damage_notes: "Tres cajas aplastadas",
  });
  return { rec: rec.id as string, codigo: `REC-${marca}`, prod: prod.id as string, alm };
}

async function uiLogin(page: Page): Promise<void> {
  await entrar(page, USER, { tenant: TENANT });
}

async function irAIncidencias(page: Page): Promise<void> {
  await page.locator('nav a[href="/compras/incidencias"]').first().click();
  await page.waitForURL((u) => u.pathname === "/compras/incidencias", { timeout: 15000 });
  await expect(page.getByRole("heading", { name: "Incidencias de recepción" })).toBeVisible();
  await page.waitForLoadState("networkidle");
}

test.describe("Spec 020 — incidencias de recepción", () => {
  test("registrar el daño, escalarlo y tratarlo, sin tocar el inventario", async ({ page, request }) => {
    const c = await ctx(request);
    const m = await recepcionConDano(request, c, `${RUN}A`);
    // Acotado al producto: el listado pagina y compararlo entero haría que
    // cualquier escritura ajena en paralelo pareciera obra de la incidencia.
    const saldosAntes = await get(request, c, `/inventory/balances?product_id=${m.prod}`);

    await uiLogin(page);
    await irAIncidencias(page);

    await page.getByLabel(/Recepción/).selectOption(m.rec);
    await page.getByLabel(/Código/).fill(`INC-${RUN}A`);
    await page.getByLabel(/Tipo/).selectOption("DANO");
    const lineas = page.getByLabel(/Línea recibida/);
    await expect(lineas).toBeEnabled();
    await lineas.selectOption({ index: 1 });
    await page.getByLabel(/Cantidad afectada/).fill("3");
    await page.getByLabel(/Descripción/).fill("Se reclama al transportista");
    await page.getByRole("button", { name: "Registrar" }).click();

    const fila = page.getByRole("row").filter({ hasText: `INC-${RUN}A` });
    await expect(fila).toContainText("Registrada", { timeout: 15000 });
    await expect(fila).toContainText("Daño");

    await fila.getByRole("button", { name: "escalar" }).click();
    await expect(fila).toContainText("Escalada a Compras", { timeout: 15000 });

    await fila.getByRole("button", { name: "tratar" }).click();
    const dialogo = page.getByRole("dialog");
    await expect(dialogo).toBeVisible();
    await dialogo.getByLabel(/Tratamiento/).selectOption("RECLAMO_PROVEEDOR");
    await dialogo.getByLabel(/Motivo/).fill("Se reclama al proveedor por el daño");
    await dialogo.getByRole("button", { name: "Registrar tratamiento" }).click();
    await expect(fila).toContainText("Resuelta", { timeout: 15000 });
    await expect(fila).toContainText("Reclamo al proveedor");

    const resultado = await get(request, c, `/purchasing/receipts/${m.rec}/incidencias/resultado`);
    expect(resultado.ready_for_confirmation).toBe(true);
    expect(resultado.unresolved).toBe(0);
    const items = resultado.items as Array<{ incident_type: string; resolution: string; affected_base_quantity: string }>;
    expect(items[0].incident_type).toBe("DANO");
    expect(items[0].resolution).toBe("RECLAMO_PROVEEDOR");
    expect(Number(items[0].affected_base_quantity)).toBe(3);

    const saldosDespues = await get(request, c, `/inventory/balances?product_id=${m.prod}`);
    expect(saldosDespues, "la incidencia movió inventario").toEqual(saldosAntes);
  });

  test("la diferencia documental no pide línea ni cantidad", async ({ page, request }) => {
    const c = await ctx(request);
    const m = await recepcionConDano(request, c, `${RUN}B`);

    await uiLogin(page);
    await irAIncidencias(page);
    await page.getByLabel(/Recepción/).selectOption(m.rec);
    await page.getByLabel(/Código/).fill(`INC-${RUN}B`);
    await page.getByLabel(/Tipo/).selectOption("DIFERENCIA_DOCUMENTAL");
    await expect(page.getByLabel(/Línea recibida/)).toHaveCount(0);
    await expect(page.getByLabel(/Cantidad afectada/)).toHaveCount(0);
    await page.getByLabel(/Descripción/).fill("Falta el certificado de origen");
    await page.getByRole("button", { name: "Registrar" }).click();

    const fila = page.getByRole("row").filter({ hasText: `INC-${RUN}B` });
    await expect(fila).toContainText("Diferencia documental", { timeout: 15000 });

    const lista = await get(request, c, `/purchasing/receipts/${m.rec}/incidencias`);
    const inc = (lista.items as Array<{ code: string; receipt_line_id: string | null; affected_base_quantity: string | null }>)
      .find((x) => x.code === `INC-${RUN}B`);
    expect(inc?.receipt_line_id).toBeNull();
    expect(inc?.affected_base_quantity).toBeNull();
  });
});
