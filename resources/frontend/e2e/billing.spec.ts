/**
 * E2E de la liberación y la facturación — Spec 034.
 *
 * Frontend real → API real → backend real → PostgreSQL real.
 *
 * La regla de esta suite es la misma de todo el tramo: **un aviso de éxito no
 * prueba nada**. Lo que se comprueba tras cada acción es el dominio —estado del
 * pedido, factura, correlativo, número de control, saldos— porque lo que la
 * Spec promete no es que la pantalla diga «facturado», sino que no se pueda
 * facturar un pedido sin confirmar, ni dos veces, ni gastando dos números.
 */
import { expect, type APIRequestContext, type Page } from "@playwright/test";

import { entrar, sesionApi, test } from "./helpers/sesion";
import { verificadorDeEscenario } from "./helpers/usuario";

const TENANT = process.env.KONTROL_E2E_TENANT ?? "DEMO";
const USER = process.env.KONTROL_E2E_USER ?? "admin";
const API = process.env.KONTROL_E2E_API ?? "http://127.0.0.1:8000/api/v1";

type Ctx = { token: string; company: string; headers: Record<string, string> };

async function ctx(request: APIRequestContext): Promise<Ctx> {
  const token = (await sesionApi(USER, { tenant: TENANT })).token;
  const r = await request.get(`${API}/organization/companies`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  const body = await r.json();
  const company = body.items[0].id as string;
  return {
    token,
    company,
    headers: { Authorization: `Bearer ${token}`, "X-Kontrol-Company": company },
  };
}

async function post(request: APIRequestContext, c: Ctx, ruta: string, data: unknown) {
  const r = await request.post(`${API}${ruta}`, { headers: c.headers, data });
  expect([200, 201], `${ruta}: ${r.status()} ${await r.text()}`).toContain(r.status());
  return r.json();
}

async function postCrudo(request: APIRequestContext, c: Ctx, ruta: string, data: unknown) {
  return request.post(`${API}${ruta}`, { headers: c.headers, data });
}

async function get(request: APIRequestContext, c: Ctx, ruta: string) {
  const r = await request.get(`${API}${ruta}`, { headers: c.headers });
  expect(r.ok(), `${ruta}: ${r.status()}`).toBeTruthy();
  return r.json();
}

const marca = (): string =>
  `${Date.now().toString(36)}${Math.random().toString(36).slice(2, 6)}`.toUpperCase();

/** Un verificador distinto del preparador: `R-D0-12-5` lo exige por defecto. */
async function verificador(request: APIRequestContext, c: Ctx, m: string): Promise<Ctx> {
  return verificadorDeEscenario(request, c, {
    usuario: `bill-${m.toLowerCase()}`,
    empresas: [c.company],
  });
}

/** Regla de impuesto vigente, serie de numeración y lote de control. */
async function fiscalListo(request: APIRequestContext, c: Ctx, m: string) {
  const fuente = await post(request, c, "/fiscal/legal-sources", {
    authority: "SENIAT", source_type: "LEY", number: `L-${m}`, effective_from: "2020-01-01",
  });
  await post(request, c, `/fiscal/legal-sources/${fuente.id}/activate`, {});
  const taxCode = `IVA_${m}`;
  const regla = await post(request, c, "/fiscal/tax-rule-versions", {
    tax_code: taxCode, legal_source_id: fuente.id, effective_from: "2020-01-01", rate: 16.0,
  });
  await post(request, c, `/fiscal/tax-rule-versions/${regla.id}/approve`, {});
  const serie = await post(request, c, "/fiscal/number-series", {
    document_type: "INVOICE", prefix: "A",
  });
  const desde = 100000 + Math.floor(Math.random() * 800000);
  const lote = await post(request, c, "/fiscal/control-batches", {
    range_from: String(desde), range_to: String(desde + 49),
  });
  return { taxCode, series: serie.id as string, batch: lote.id as string };
}

type Escenario = {
  producto: string;
  pedido: string;
  pedidoCode: string;
  linea: string;
  cantidad: number;
  v: Ctx;
};

/** Un pedido confirmado de punta a punta. */
async function escenario(
  request: APIRequestContext,
  c: Ctx,
  m: string,
  { cantidad = 10, precio = 25, taxCode = null as string | null } = {},
): Promise<Escenario> {
  const propio = await post(request, c, "/organization/warehouses", {
    company_id: c.company, code: `WB-${m}`, name: `Almacén facturación ${m}`,
    warehouse_type: "PHYSICAL", status: "ACTIVE",
  });
  const almacen = propio.id as string;
  const producto = await post(request, c, "/maestros/catalogos/items", {
    code: `PB-${m}`, name: `Artículo ${m}`, item_type: "PRODUCT", status: "ACTIVE",
  });
  const l1 = await post(request, c, "/organization/locations", {
    warehouse_id: almacen, code: `B1-${m}`, name: "Origen", sequence: 1,
  });
  const area = await post(request, c, "/organization/locations", {
    warehouse_id: almacen, code: `BC-${m}`, name: "Área de Confirmación", sequence: 99,
  });

  // Buscar y, si falta, crear. En una base recién instalada varias pruebas
  // llegan a la vez, todas ven que el tipo no existe y solo la primera consigue
  // crearlo: las demás reciben un 409 legítimo del índice único. Ese 409 no es
  // un fallo del escenario sino la señal de que otra prueba ya lo creó, así que
  // se vuelve a leer. Cualquier otro error sí rompe la prueba.
  const buscarEntrada = async () => {
    const tipos = await get(request, c, "/inventory/movement-types");
    return (tipos.items ?? tipos).find(
      (x: { code: string }) => x.code === "ENTRADA_RECEPCION",
    ) as { id: string } | undefined;
  };
  let entrada = await buscarEntrada();
  if (!entrada) {
    const creado = await request.post(`${API}/inventory/movement-types`, {
      headers: c.headers,
      data: { code: "ENTRADA_RECEPCION", name: "Entrada por recepción", direction: "IN" },
    });
    if (creado.ok()) {
      entrada = (await creado.json()) as { id: string };
    } else {
      expect((await creado.json()).code, `movement-types: ${creado.status()}`)
        .toBe("MOVEMENT_TYPE_DUPLICATE");
      entrada = await buscarEntrada();
    }
  }
  if (!entrada) throw new Error("No existe el tipo de movimiento ENTRADA_RECEPCION");
  await post(request, c, "/inventory/movements", {
    warehouse_id: almacen, product_id: producto.id, movement_type_id: entrada.id,
    quantity: cantidad + 20,
  });
  await post(request, c, "/inventory/putaway", {
    warehouse_id: almacen, product_id: producto.id, target_location_id: l1.id,
    quantity: cantidad + 20,
  });

  const cliente = await post(request, c, "/maestros/terceros", {
    code: `CB-${m}`, name: `Cliente ${m}`, roles: ["CLIENTE"],
  });
  const pedido = await post(request, c, "/sales/orders", {
    code: `OVB-${m}`, customer_id: cliente.id, currency: "VED", warehouse_id: almacen,
  });
  const linea = await post(request, c, `/sales/orders/${pedido.id}/lines`, {
    product_id: producto.id, quantity: cantidad, unit_price: precio,
    ...(taxCode ? { tax_ref: taxCode } : {}),
  });
  const emitido = await post(request, c, `/sales/orders/${pedido.id}/submit`, {});
  if (emitido.status !== "RELEASED") {
    await post(request, c, `/sales/orders/${pedido.id}/release`, {});
  }

  const plan = await post(request, c, "/sales/pick-lists", {
    code: `PLB-${m}`, order_id: pedido.id, warehouse_id: almacen,
  });
  await post(request, c, `/sales/picking/${plan.id}/asignaciones`, {
    order_line_id: linea.id, location_id: l1.id, quantity: cantidad,
  });
  await post(request, c, `/sales/picking/${plan.id}/confirmar`, {});
  const prep = await get(request, c, `/sales/picking/${plan.id}/preparacion`);
  await post(request, c, `/sales/picking/${plan.id}/recoger`, {
    line_id: (prep.picking as Array<{ id: string }>)[0].id, quantity: cantidad,
  });
  await post(request, c, `/sales/picking/${plan.id}/consolidar`, { location_id: area.id });

  const v = await verificador(request, c, m);
  await post(request, v, `/sales/confirmacion/${pedido.id}`, {
    lines: [{ order_line_id: linea.id, checked_base_quantity: cantidad }],
  });

  return {
    producto: producto.id as string, pedido: pedido.id as string,
    pedidoCode: pedido.code as string, linea: linea.id as string, cantidad, v,
  };
}

async function uiLogin(page: Page): Promise<void> {
  await entrar(page, USER, { tenant: TENANT });
  await expect(page).toHaveURL(/\/$/, { timeout: 20_000 });
}

test.describe("Spec 034 — liberación y facturación", () => {
  test("el pedido confirmado se libera, se factura y se emite", async ({ request }) => {
    const c = await ctx(request);
    const m = marca();
    const f = await fiscalListo(request, c, m);
    const e = await escenario(request, c, m, { cantidad: 10, precio: 25, taxCode: f.taxCode });

    await post(request, e.v, `/sales/facturacion/${e.pedido}/solicitar`, {});
    expect((await get(request, c, `/sales/orders/${e.pedido}`)).status).toBe("READY_FOR_BILLING");

    const factura = await post(request, c, `/sales/facturacion/${e.pedido}/generar`, {});
    expect(factura.order_id).toBe(e.pedido);
    expect(factura.confirmation_id, "la factura no dice sobre qué control se emitió").toBeTruthy();
    expect(Number(factura.base_fiscal)).toBe(250);
    expect(Number(factura.tax_total), "el impuesto no salió de la regla").toBe(40);
    expect(Number(factura.total)).toBe(290);

    const emitida = await post(request, c, `/sales/facturacion/${factura.id}/emitir`, {
      series_id: f.series, batch_id: f.batch,
    });
    expect(emitida.status).toBe("EMITTED");
    expect(emitida.invoice_number, "no se asignó correlativo").toBeTruthy();
    expect(emitida.control_number, "no se asignó número de control").toBeTruthy();
    expect((await get(request, c, `/sales/orders/${e.pedido}`)).status).toBe("INVOICED");
  });

  test("no se factura un pedido sin confirmación independiente", async ({ request }) => {
    const c = await ctx(request);
    const m = marca();
    const cliente = await post(request, c, "/maestros/terceros", {
      code: `CN-${m}`, name: `Cliente ${m}`, roles: ["CLIENTE"],
    });
    const pedido = await post(request, c, "/sales/orders", {
      code: `OVN-${m}`, customer_id: cliente.id, currency: "VED",
    });
    const r = await postCrudo(request, c, `/sales/facturacion/${pedido.id}/solicitar`, {});
    expect(r.status()).toBe(409);
    expect((await r.json()).code).toBe("BILLING_ORDER_NOT_CONFIRMED");
  });

  test("no se genera factura sin solicitud", async ({ request }) => {
    const c = await ctx(request);
    const m = marca();
    const e = await escenario(request, c, m);
    const r = await postCrudo(request, c, `/sales/facturacion/${e.pedido}/generar`, {});
    expect(r.status()).toBe(409);
    expect((await r.json()).code).toBe("BILLING_NOT_REQUESTED");
  });

  test("un pedido no se factura dos veces", async ({ request }) => {
    const c = await ctx(request);
    const m = marca();
    const e = await escenario(request, c, m);
    await post(request, e.v, `/sales/facturacion/${e.pedido}/solicitar`, {});
    await post(request, c, `/sales/facturacion/${e.pedido}/generar`, {});
    const r = await postCrudo(request, c, `/sales/facturacion/${e.pedido}/generar`, {});
    expect(r.status()).toBe(409);
    expect((await r.json()).code).toBe("ORDER_ALREADY_INVOICED");
  });

  test("emitir dos veces no gasta dos números", async ({ request }) => {
    const c = await ctx(request);
    const m = marca();
    const f = await fiscalListo(request, c, m);
    const e = await escenario(request, c, m, { cantidad: 4, precio: 10 });
    await post(request, e.v, `/sales/facturacion/${e.pedido}/solicitar`, {});
    const factura = await post(request, c, `/sales/facturacion/${e.pedido}/generar`, {});
    const uno = await post(request, c, `/sales/facturacion/${factura.id}/emitir`, {
      series_id: f.series, batch_id: f.batch,
    });
    const dos = await post(request, c, `/sales/facturacion/${factura.id}/emitir`, {
      series_id: f.series, batch_id: f.batch,
    });
    expect(dos.invoice_number).toBe(uno.invoice_number);
    expect(dos.control_number).toBe(uno.control_number);
  });

  test("facturar no mueve una sola unidad", async ({ request }) => {
    const c = await ctx(request);
    const m = marca();
    const f = await fiscalListo(request, c, m);
    const e = await escenario(request, c, m, { cantidad: 6, precio: 10 });
    const antes = await get(request, c, `/inventory/balances?product_id=${e.producto}`);
    const movsAntes = await get(request, c, `/inventory/movements?product_id=${e.producto}`);

    await post(request, e.v, `/sales/facturacion/${e.pedido}/solicitar`, {});
    const factura = await post(request, c, `/sales/facturacion/${e.pedido}/generar`, {});
    await post(request, c, `/sales/facturacion/${factura.id}/emitir`, {
      series_id: f.series, batch_id: f.batch,
    });

    const despues = await get(request, c, `/inventory/balances?product_id=${e.producto}`);
    expect(
      (despues.items as Array<{ qty_on_hand: string; qty_reserved: string }>)
        .map((b) => `${b.qty_on_hand}|${b.qty_reserved}`).sort(),
      "facturar movió inventario o tocó la reserva",
    ).toEqual(
      (antes.items as Array<{ qty_on_hand: string; qty_reserved: string }>)
        .map((b) => `${b.qty_on_hand}|${b.qty_reserved}`).sort(),
    );
    expect((await get(request, c, `/inventory/movements?product_id=${e.producto}`)).items.length)
      .toBe(movsAntes.items.length);
  });

  test("el despacho puede consultar si el pedido está facturado", async ({ request }) => {
    const c = await ctx(request);
    const m = marca();
    const f = await fiscalListo(request, c, m);
    const e = await escenario(request, c, m, { cantidad: 2, precio: 10 });
    const antes = await get(request, c, `/sales/facturacion/${e.pedido}/factura`);
    expect(antes.invoiced).toBe(false);

    await post(request, e.v, `/sales/facturacion/${e.pedido}/solicitar`, {});
    const factura = await post(request, c, `/sales/facturacion/${e.pedido}/generar`, {});
    await post(request, c, `/sales/facturacion/${factura.id}/emitir`, {
      series_id: f.series, batch_id: f.batch,
    });

    const despues = await get(request, c, `/sales/facturacion/${e.pedido}/factura`);
    expect(despues.invoiced).toBe(true);
    expect(despues.invoice.control_number).toBeTruthy();
  });

  test("la interfaz factura y el dominio lo confirma", async ({ page, request }) => {
    const c = await ctx(request);
    const m = marca();
    const e = await escenario(request, c, m, { cantidad: 3, precio: 20 });
    await post(request, e.v, `/sales/facturacion/${e.pedido}/solicitar`, {});

    await uiLogin(page);
    await page.locator('nav a[href="/ventas/facturacion"]').first().click();
    await page.waitForURL((u) => u.pathname === "/ventas/facturacion", { timeout: 15_000 });
    await expect(page.getByRole("heading", { name: "Facturación" })).toBeVisible();

    // Hay que esperar a que la cola cargue antes de mirar el paginador, y
    // comprobar que existe: con la tabla vacía no hay paginador, y con la base
    // recién sembrada la cola cabe en una página. `isDisabled()` sobre un botón
    // que no existe espera hasta agotar el tiempo de la prueba.
    await expect(page.getByRole("region", { name: /Resultados:/ })).toBeVisible({
      timeout: 15_000,
    });
    const fila = page.getByRole("row", { name: new RegExp(e.pedidoCode) });
    const siguiente = page.getByRole("button", { name: "Página siguiente" });
    for (let i = 0; i < 20 && (await fila.count()) === 0; i += 1) {
      if ((await siguiente.count()) === 0 || (await siguiente.isDisabled())) break;
      await siguiente.click();
      await page.waitForLoadState("networkidle");
    }
    await expect(fila).toHaveCount(1);
    await fila.getByRole("button", { name: "Facturar" }).click();
    await page.waitForLoadState("networkidle");
    await page.getByRole("button", { name: "Generar factura" }).click();
    await expect(page.getByRole("button", { name: "Emitir documento fiscal" }))
      .toBeVisible({ timeout: 15_000 });

    const estado = await get(request, c, `/sales/facturacion/${e.pedido}/factura`);
    expect(estado.invoice, "la interfaz no creó la factura").not.toBeNull();
    expect(Number(estado.invoice.total)).toBe(60);
    expect(estado.invoiced, "generar no puede emitir por su cuenta").toBe(false);
  });
});
