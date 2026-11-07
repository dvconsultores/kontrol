/**
 * E2E de la recepción física — Spec 019.
 *
 * Frontend real → API real → backend real → PostgreSQL real. Lo que se
 * comprueba es lo que la Spec existe para cerrar: que dos cajas de doce entren
 * al inventario como veinticuatro unidades y no como dos, y que lo que se
 * observa en el muelle quede escrito.
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
  const r = await request.get(`${API}/organization/companies`, { headers: { Authorization: `Bearer ${token}` } });
  expect(r.ok(), `companies: ${r.status()}`).toBeTruthy();
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
  await entrar(page, USER, { tenant: TENANT });
  await page.waitForURL((u) => !u.pathname.includes("login"), { timeout: 20000 });
}

async function irARecepciones(page: Page): Promise<void> {
  await page.locator('nav a[href="/compras/recepciones"]').first().click();
  await page.waitForURL((u) => u.pathname === "/compras/recepciones", { timeout: 15000 });
  await expect(page.getByRole("heading", { name: "Recepciones" })).toBeVisible();
  await page.waitForLoadState("networkidle");
}

test.describe("Spec 019 — recepción física", () => {
  test("la operadora elige el almacén al crear la recepción", async ({ page, request }) => {
    const c = await ctx(request);
    const m = await mundo(request, c, `${RUN}S`);
    const ultimo = await post(request, c, "/organization/warehouses", {
      company_id: c.company, code: `ZZZ-${RUN}`, name: "Último E2E",
      warehouse_type: "PHYSICAL", status: "ACTIVE",
    });

    await uiLogin(page);
    await irARecepciones(page);
    await page.getByLabel(/^Código/).first().fill(`REC-${RUN}S`);
    await page.getByLabel(/^Orden de compra/).selectOption(m.orden);
    await page.getByLabel(/^Almacén/).selectOption(ultimo.id as string);
    await page.getByRole("button", { name: "Crear" }).first().click();

    await expect.poll(async () => {
      const lista = await get(request, c, "/purchasing/receipts");
      const recepcion = (lista.items as Array<{ code: string; warehouse_id: string }>)
        .find((r) => r.code === `REC-${RUN}S`);
      return recepcion?.warehouse_id;
    }).toBe(ultimo.id);
  });

  test("la operadora elige la línea y el producto sale de ella", async ({ page, request }) => {
    const c = await ctx(request);
    const m = await mundo(request, c, `${RUN}L`);

    const segundo = await post(request, c, "/maestros/catalogos/items", {
      code: `P2-${RUN}L`,
      name: `Segundo ${RUN}L`,
      item_type: "PRODUCT",
    });
    const proveedor = await post(request, c, "/maestros/terceros", {
      code: `PRV2-${RUN}L`,
      name: "Proveedor E2E",
      roles: ["PROVEEDOR"],
    });
    const orden = await post(request, c, "/purchasing/orders", {
      code: `OC2-${RUN}L`,
      supplier_id: proveedor.id,
      currency: "VED",
    });
    const lineaA = await post(request, c, `/purchasing/orders/${orden.id}/lines`, {
      product_id: m.prod,
      quantity_ordered: 100,
      unit_price: 5,
    });
    const lineaB = await post(request, c, `/purchasing/orders/${orden.id}/lines`, {
      product_id: segundo.id,
      quantity_ordered: 40,
      unit_price: 7,
    });
    for (const target of ["SUBMITTED", "APPROVED"]) {
      await post(request, c, `/purchasing/orders/${orden.id}/transition`, { target });
    }
    const recepcion = await post(request, c, "/purchasing/receipts", {
      code: `REC-${RUN}L`,
      order_id: orden.id,
      warehouse_id: m.alm,
    });

    await uiLogin(page);
    await irARecepciones(page);
    const fila = page.getByRole("row").filter({ hasText: `REC-${RUN}L` });
    await fila.getByRole("button", { name: "detalle" }).click();
    await expect(page.getByRole("heading", { name: `Inspección de REC-${RUN}L` })).toBeVisible({ timeout: 15000 });

    const linea = page.getByLabel(/^Línea de la orden/);
    await expect(linea.locator("option", { hasText: `P-${RUN}L` })).toHaveCount(1, { timeout: 15000 });
    await expect(linea.locator("option", { hasText: `P2-${RUN}L` })).toHaveCount(1);
    await linea.selectOption(lineaA.id as string);
    await expect(page.getByLabel(/^Producto/)).toHaveValue(new RegExp(`^P-${RUN}L`));
    await page.getByLabel(/^Presentación/).selectOption(m.caja);
    await page.getByLabel(/^Recibido/).fill("2");
    await page.getByRole("button", { name: "Registrar", exact: true }).click();
    await expect
      .poll(async () => {
        const detalle = await get(request, c, `/purchasing/receipts/${recepcion.id}`);
        return (detalle.lines as Array<unknown>).length;
      })
      .toBe(1);

    await linea.selectOption(lineaB.id as string);
    await expect(page.getByLabel(/^Producto/)).toHaveValue(new RegExp(`^P2-${RUN}L`));
    await expect(page.getByLabel(/^Presentación/).locator(`option[value="${m.caja}"]`)).toHaveCount(0);
    await page.getByLabel(/^Recibido/).fill("3");
    await page.getByRole("button", { name: "Registrar", exact: true }).click();
    await expect
      .poll(async () => {
        const detalle = await get(request, c, `/purchasing/receipts/${recepcion.id}`);
        return (detalle.lines as Array<unknown>).length;
      })
      .toBe(2);

    const detalle = await get(request, c, `/purchasing/receipts/${recepcion.id}`);
    const lines = detalle.lines as Array<{
      order_line_id: string;
      product_id: string;
      presentation_id: string | null;
    }>;
    const registradaA = lines.find((l) => l.order_line_id === lineaA.id);
    const registradaB = lines.find((l) => l.order_line_id === lineaB.id);
    expect(registradaA?.product_id).toBe(m.prod);
    expect(registradaA?.presentation_id).toBe(m.caja);
    expect(registradaB?.product_id).toBe(segundo.id);
    expect(registradaB?.presentation_id).toBeNull();
  });

  test("la recepción recorre el proceso completo desde el menú", async ({ page, request }) => {
    test.setTimeout(120000);
    const c = await ctx(request);
    const m = await mundo(request, c, `${RUN}Z`);
    const segundo = await post(request, c, "/maestros/catalogos/items", {
      code: `P2-${RUN}Z`,
      name: `Segundo ${RUN}Z`,
      item_type: "PRODUCT",
    });
    const proveedor = await post(request, c, "/maestros/terceros", {
      code: `PRV3-${RUN}Z`,
      name: "Proveedor E2E",
      roles: ["PROVEEDOR"],
    });
    const aprobar = async (
      codigo: string,
      lineas: Array<{ product_id: unknown; quantity_ordered: number; unit_price: number }>,
    ) => {
      const orden = await post(request, c, "/purchasing/orders", {
        code: codigo,
        supplier_id: proveedor.id,
        currency: "VED",
      });
      const creadas: Array<Record<string, unknown>> = [];
      for (const linea of lineas) {
        creadas.push(
          await post(request, c, `/purchasing/orders/${orden.id}/lines`, linea),
        );
      }
      for (const target of ["SUBMITTED", "APPROVED"]) {
        await post(request, c, `/purchasing/orders/${orden.id}/transition`, { target });
      }
      return { orden, creadas };
    };
    const buscada = await aprobar(`OC3-${RUN}Z`, [
      { product_id: m.prod, quantity_ordered: 100, unit_price: 5 },
      { product_id: segundo.id, quantity_ordered: 40, unit_price: 7 },
    ]);
    for (let i = 0; i < 51; i += 1) {
      await aprobar(`OCX-${RUN}${i}`, [
        { product_id: m.prod, quantity_ordered: 1, unit_price: 1 },
      ]);
    }
    await uiLogin(page);
    await irARecepciones(page);
    await page.getByLabel(/^Buscar orden/).fill(`OC3-${RUN}Z`);
    const selectorOrden = page.getByLabel(/^Orden de compra/);
    await expect(selectorOrden.locator("option", { hasText: `OC3-${RUN}Z` })).toHaveCount(1, {
      timeout: 15000,
    });
    await selectorOrden.selectOption(buscada.orden.id as string);
    await page.getByLabel(/^Almacén/).selectOption(m.alm as string);
    await page.getByLabel(/^Código/).first().fill(`REC-${RUN}Z`);
    await page.getByRole("button", { name: "Crear" }).first().click();
    await expect(
      page.getByRole("heading", { name: `Inspección de REC-${RUN}Z` }),
    ).toBeVisible({ timeout: 15000 });
    const fila = page.getByRole("row").filter({ hasText: `REC-${RUN}Z` });
    await expect(fila).toContainText(`OC3-${RUN}Z`);
    await fila.getByRole("button", { name: "confirmar arribo" }).click();
    await expect(fila).not.toContainText("sin confirmar", { timeout: 15000 });
    await page.getByLabel(/^Packing list comparado/).selectOption("true");
    await page.getByRole("button", { name: "Registrar inspección", exact: true }).click();
    await expect(page.getByText(/inspeccionada el/)).toBeVisible({ timeout: 15000 });
    const lista = await get(request, c, "/purchasing/receipts");
    const recId = (
      lista.items as Array<{ id: string; code: string }>
    ).find((r) => r.code === `REC-${RUN}Z`)?.id as string;
    const linea = page.getByLabel(/^Línea de la orden/);
    await linea.selectOption(buscada.creadas[0].id as string);
    await expect(page.getByLabel(/^Producto/)).toHaveValue(new RegExp(`^P-${RUN}Z`));
    await page.getByLabel(/^Presentación/).selectOption(m.caja);
    await page.getByLabel(/^Identificación/).selectOption("true");
    await page.getByLabel(/^Referencia/).selectOption("false");
    await page.getByLabel(/^Recibido/).fill("2");
    await page.getByRole("button", { name: "Registrar", exact: true }).click();
    await expect
      .poll(
        async () => {
          const detalle = await get(request, c, `/purchasing/receipts/${recId}`);
          return (detalle.lines as Array<unknown>).length;
        },
        { timeout: 15000 },
      )
      .toBe(1);
    await linea.selectOption(buscada.creadas[1].id as string);
    await expect(page.getByLabel(/^Producto/)).toHaveValue(new RegExp(`^P2-${RUN}Z`));
    await page.getByLabel(/^Recibido/).fill("3");
    await page.getByRole("button", { name: "Registrar", exact: true }).click();
    await expect
      .poll(
        async () => {
          const detalle = await get(request, c, `/purchasing/receipts/${recId}`);
          return (detalle.lines as Array<unknown>).length;
        },
        { timeout: 15000 },
      )
      .toBe(2);
    await fila.getByRole("button", { name: "confirmar", exact: true }).click();
    await expect(fila).toContainText("Confirmada", { timeout: 15000 });
    await fila.getByRole("button", { name: "enviar a calidad", exact: true }).click();
    await expect(fila).toContainText("Pendiente de calidad", { timeout: 15000 });
    await fila.getByRole("button", { name: "conforme", exact: true }).click();
    await fila.getByRole("button", { name: "aceptar" }).click();
    await expect(fila).toContainText("Aceptada", { timeout: 15000 });
    const detalle = await get(request, c, `/purchasing/receipts/${recId}`);
    const lineas = detalle.lines as Array<{
      order_line_id: string;
      product_id: string;
      identification_ok: boolean | null;
      reference_ok: boolean | null;
    }>;
    expect(lineas).toHaveLength(2);
    expect(lineas[0].product_id).toBe(m.prod);
    expect(lineas[0].identification_ok).toBe(true);
    expect(lineas[0].reference_ok).toBe(false);
    expect(lineas[1].product_id).toBe(segundo.id);
    expect(lineas[1].identification_ok).toBeNull();
    expect(lineas[1].reference_ok).toBeNull();
    const saldosProd = await get(request, c, `/inventory/balances?product_id=${m.prod}`);
    const itemsProd = saldosProd.items as Array<{ warehouse_id: string; qty_on_hand: string }>;
    const sumaProd = itemsProd
      .filter((b) => b.warehouse_id === m.alm)
      .reduce((acc, b) => acc + Number(b.qty_on_hand), 0);
    expect(sumaProd).toBe(24);
    const saldosSeg = await get(request, c, `/inventory/balances?product_id=${segundo.id}`);
    const itemsSeg = saldosSeg.items as Array<{ warehouse_id: string; qty_on_hand: string }>;
    const sumaSeg = itemsSeg
      .filter((b) => b.warehouse_id === m.alm)
      .reduce((acc, b) => acc + Number(b.qty_on_hand), 0);
    expect(sumaSeg).toBe(3);
  });

  const recepcionEnBorrador = async (request: APIRequestContext, c: Ctx, marca: string, recibido: number, aceptado: number) => {
    const m = await mundo(request, c, marca);
    const rec = await post(request, c, "/purchasing/receipts", { code: `REC-${marca}`, order_id: m.orden, warehouse_id: m.alm });
    const linea = await post(request, c, `/purchasing/receipts/${rec.id}/lines`, { order_line_id: m.linea, product_id: m.prod, quantity_received: recibido, quantity_accepted: aceptado, quantity_rejected: recibido - aceptado });
    return { m, rec, linea };
  };

  const recorrerHastaAceptar = async (page: Page, marca: string, etiquetaFinal: string) => {
    const fila = page.getByRole("row").filter({ hasText: `REC-${marca}` });
    await fila.getByRole("button", { name: "confirmar", exact: true }).click();
    await expect(fila).toContainText("Confirmada", { timeout: 15000 });
    await fila.getByRole("button", { name: "enviar a calidad", exact: true }).click();
    await expect(fila).toContainText("Pendiente de calidad", { timeout: 15000 });
    await fila.getByRole("button", { name: "conforme", exact: true }).click();
    await fila.getByRole("button", { name: "aceptar", exact: true }).click();
    await expect(fila).toContainText(etiquetaFinal, { timeout: 15000 });
    return fila;
  };

  const confirmarInventario = async (request: APIRequestContext, c: Ctx, recId: string, lineaId: string, recibido: string, aceptado: string) => {
    await post(request, c, `/purchasing/receipts/${recId}/lines/${lineaId}/conteo`, { counted_base_quantity: recibido, difference_kinds: [] });
    await post(request, c, `/purchasing/receipts/${recId}/confirmacion-inventario`, { decisions: [{ receipt_line_id: lineaId, target_state: "DISPONIBLE", base_quantity: aceptado }] });
  };

  test("la recepción aceptada del todo se cierra tras confirmar el inventario", async ({ page, request }) => {
    const c = await ctx(request);
    const { m, rec, linea } = await recepcionEnBorrador(request, c, `${RUN}E1`, 10, 10);
    await uiLogin(page);
    await irARecepciones(page);
    await recorrerHastaAceptar(page, `${RUN}E1`, "Aceptada");
    await confirmarInventario(request, c, String(rec.id), String(linea.id), "10", "10");
    const saldosAntes = await get(request, c, `/inventory/balances?product_id=${m.prod}`);
    await page.reload();
    await irARecepciones(page);
    const fila = page.getByRole("row").filter({ hasText: `REC-${RUN}E1` });
    await expect(fila).toContainText("Aceptada", { timeout: 15000 });
    await fila.getByRole("button", { name: "cerrar", exact: true }).click();
    await expect(fila).toContainText("Cerrada", { timeout: 15000 });
    const detalle = await get(request, c, `/purchasing/receipts/${rec.id}`);
    expect(detalle.status).toBe("CLOSED");
    const saldosDespues = await get(request, c, `/inventory/balances?product_id=${m.prod}`);
    expect(saldosDespues.items).toEqual(saldosAntes.items);
  });

  test("la recepción parcial queda aceptada parcialmente y se cierra", async ({ page, request }) => {
    const c = await ctx(request);
    const { m, rec, linea } = await recepcionEnBorrador(request, c, `${RUN}E2`, 10, 7);
    await uiLogin(page);
    await irARecepciones(page);
    await recorrerHastaAceptar(page, `${RUN}E2`, "Aceptada parcialmente");
    await confirmarInventario(request, c, String(rec.id), String(linea.id), "10", "7");
    await page.reload();
    await irARecepciones(page);
    const fila = page.getByRole("row").filter({ hasText: `REC-${RUN}E2` });
    await expect(fila).toContainText("Aceptada parcialmente", { timeout: 15000 });
    await fila.getByRole("button", { name: "cerrar", exact: true }).click();
    await expect(fila).toContainText("Cerrada", { timeout: 15000 });
    const detalle = await get(request, c, `/purchasing/receipts/${rec.id}`);
    expect(detalle.status).toBe("CLOSED");
    const saldos = await get(request, c, `/inventory/balances?product_id=${m.prod}`);
    const items = saldos.items as Array<{ warehouse_id: string; qty_on_hand: string }>;
    const total = items.filter((i) => i.warehouse_id === m.alm).reduce((acc, i) => acc + Number(i.qty_on_hand), 0);
    expect(total).toBe(7);
  });

  test("la recepción rechazada se cierra sin inventario", async ({ page, request }) => {
    const c = await ctx(request);
    const { m, rec } = await recepcionEnBorrador(request, c, `${RUN}E3`, 10, 10);
    await uiLogin(page);
    await irARecepciones(page);
    const fila = page.getByRole("row").filter({ hasText: `REC-${RUN}E3` });
    await fila.getByRole("button", { name: "confirmar", exact: true }).click();
    await expect(fila).toContainText("Confirmada", { timeout: 15000 });
    await fila.getByRole("button", { name: "enviar a calidad", exact: true }).click();
    await expect(fila).toContainText("Pendiente de calidad", { timeout: 15000 });
    await fila.getByRole("button", { name: "no conforme", exact: true }).click();
    await expect(fila).toContainText("Rechazada", { timeout: 15000 });
    await fila.getByRole("button", { name: "cerrar", exact: true }).click();
    await expect(fila).toContainText("Cerrada", { timeout: 15000 });
    const detalle = await get(request, c, `/purchasing/receipts/${rec.id}`);
    expect(detalle.status).toBe("CLOSED");
    const saldos = await get(request, c, `/inventory/balances?product_id=${m.prod}`);
    const items = saldos.items as Array<{ warehouse_id: string; qty_on_hand: string }>;
    const total = items.filter((i) => i.warehouse_id === m.alm).reduce((acc, i) => acc + Number(i.qty_on_hand), 0);
    expect(total).toBe(0);
  });

  test("un borrador se anula con su motivo", async ({ page, request }) => {
    const c = await ctx(request);
    const { rec } = await recepcionEnBorrador(request, c, `${RUN}E4`, 5, 5);
    await uiLogin(page);
    await irARecepciones(page);
    const fila = page.getByRole("row").filter({ hasText: `REC-${RUN}E4` });
    await fila.getByRole("button", { name: "detalle", exact: true }).click();
    await page.getByLabel(/^Motivo de anulación/).fill("Creada por error");
    await page.getByRole("button", { name: "Anular recepción", exact: true }).click();
    await expect(fila).toContainText("Anulada", { timeout: 15000 });
    const detalle = await get(request, c, `/purchasing/receipts/${rec.id}`);
    expect(detalle.status).toBe("CANCELLED");
  });

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
    await fila.getByRole("button", { name: "enviar a calidad", exact: true }).click();
    await expect(fila).toContainText("Pendiente de calidad", { timeout: 15000 });
    await fila.getByRole("button", { name: "conforme", exact: true }).click();
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
    await page.getByLabel(/^Packing list comparado/).selectOption("false");
    await page.getByLabel(/^Factura comparada/).selectOption("true");
    await page.getByRole("button", { name: "Registrar inspección", exact: true }).click();
    await expect(page.getByText(/no coincide/).first()).toBeVisible({ timeout: 15000 });

    const detalle = await get(request, c, `/purchasing/receipts/${rec.id}`);
    expect(detalle.packages_received).toBe(4);
    expect(detalle.packages_declared).toBe(5);
    expect(detalle.packing_list_match).toBe(false);
    expect(detalle.supplier_invoice_match).toBe(true);
    expect(detalle.order_match).toBeNull();
    expect(detalle.inspection_notes).toBe("Una caja con el precinto forzado");
    expect(detalle.inspected_at).not.toBeNull();
  });
});
