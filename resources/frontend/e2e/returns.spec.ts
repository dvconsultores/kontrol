/**
 * E2E de las devoluciones y las notas — Spec 036.
 *
 * Frontend real → API real → backend real → PostgreSQL real.
 *
 * Lo que defiende es el orden que la norma escribe: cuatro actos antes de tocar
 * el inventario. No comprueba que la pantalla diga «devuelto»: comprueba que
 * solicitar no mueve nada, que recibir devuelve la custodia sin hacer vendible
 * la mercancía, que solo la entrada de inventario crea existencia, y que
 * aceptar una devolución **no** emite ninguna nota.
 */
import { type APIRequestContext, type Page } from "@playwright/test";

import { entrar as entrarConSesion, expect, sesionApi, test } from "./helpers/sesion";
import { verificadorDeEscenario } from "./helpers/usuario";

const API = process.env.KONTROL_E2E_API ?? "http://127.0.0.1:8000/api/v1";

type Ctx = { token: string; company: string; headers: Record<string, string> };

async function ctx(request: APIRequestContext): Promise<Ctx> {
  const token = (await sesionApi("admin", { tenant: "DEMO" })).token;
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
    usuario: `dev-${m.toLowerCase()}`,
    empresas: [c.company],
  });
}

async function fiscalListo(request: APIRequestContext, c: Ctx, m: string) {
  // Los catálogos fiscales valen en todas las empresas: los prepara el administrador de QA de todo el tenant (ADR-017, C4).
  const admin = await sesionApi("admintenant", { tenant: "DEMO" });
  const tenantCtx: Ctx = { ...c, token: admin.token, headers: { ...c.headers, Authorization: `Bearer ${admin.token}` } };
  const fuente = await post(request, tenantCtx, "/fiscal/legal-sources", {
    authority: "SENIAT", source_type: "LEY", number: `LR-${m}`, effective_from: "2020-01-01",
  });
  await post(request, tenantCtx, `/fiscal/legal-sources/${fuente.id}/activate`, {});
  const series: Record<string, string> = {};
  for (const [tipo, prefijo] of [["INVOICE", "F"], ["CREDIT_NOTE", "NC"], ["DEBIT_NOTE", "ND"]]) {
    const s = await post(request, c, "/fiscal/number-series", {
      document_type: tipo, prefix: prefijo,
    });
    series[tipo] = s.id as string;
  }
  const desde = 100000 + Math.floor(Math.random() * 800000);
  const lote = await post(request, c, "/fiscal/control-batches", {
    range_from: String(desde), range_to: String(desde + 99),
  });
  return { series, batch: lote.id as string };
}

type Escenario = {
  producto: string;
  almacen: string;
  area: string;
  pedido: string;
  pedidoCode: string;
  linea: string;
  cantidad: number;
  v: Ctx;
};

type Despachado = Escenario & {
  factura: string;
  fiscal: { series: Record<string, string>; batch: string };
  shipment: string;
  invoiceLine: string;
};

/** Un pedido confirmado, listo para facturar. */
async function escenario(
  request: APIRequestContext,
  c: Ctx,
  m: string,
  { cantidad = 10, precio = 25 } = {},
): Promise<Escenario> {
  const propio = await post(request, c, "/organization/warehouses", {
    company_id: c.company, code: `WV-${m}`, name: `Almacén devoluciones ${m}`,
    warehouse_type: "PHYSICAL", status: "ACTIVE",
  });
  const almacen = propio.id as string;
  const producto = await post(request, c, "/maestros/catalogos/items", {
    code: `PV-${m}`, name: `Artículo ${m}`, item_type: "PRODUCT", status: "ACTIVE",
  });
  const l1 = await post(request, c, "/organization/locations", {
    warehouse_id: almacen, code: `V1-${m}`, name: "Origen", sequence: 1,
  });
  const area = await post(request, c, "/organization/locations", {
    warehouse_id: almacen, code: `VC-${m}`, name: "Área de Confirmación", sequence: 99,
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
    code: `CV-${m}`, name: `Cliente ${m}`, roles: ["CLIENTE"],
  });
  const pedido = await post(request, c, "/sales/orders", {
    code: `OVV-${m}`, customer_id: cliente.id, currency: "VED", warehouse_id: almacen,
  });
  const linea = await post(request, c, `/sales/orders/${pedido.id}/lines`, {
    product_id: producto.id, quantity: cantidad, unit_price: precio,
  });
  const emitido = await post(request, c, `/sales/orders/${pedido.id}/submit`, {});
  if (emitido.status !== "RELEASED") {
    await post(request, c, `/sales/orders/${pedido.id}/release`, {});
  }

  const plan = await post(request, c, "/sales/pick-lists", {
    code: `PLV-${m}`, order_id: pedido.id, warehouse_id: almacen,
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
    producto: producto.id as string, almacen, area: area.id as string,
    pedido: pedido.id as string, pedidoCode: pedido.code as string,
    linea: linea.id as string, cantidad, v,
  };
}

/** Hasta la factura **emitida**: lo que el ¶101 exige para pasar a despacho. */
async function despachado(request: APIRequestContext, c: Ctx, m: string,
                          opciones = {}): Promise<Despachado> {
  const f = await fiscalListo(request, c, m);
  const e = await escenario(request, c, m, opciones);
  await post(request, e.v, `/sales/facturacion/${e.pedido}/solicitar`, {});
  const factura = await post(request, c, `/sales/facturacion/${e.pedido}/generar`, {});
  const emitida = await post(request, c, `/sales/facturacion/${factura.id}/emitir`, {
    series_id: f.series.INVOICE, batch_id: f.batch,
  });
  expect(emitida.status).toBe("EMITTED");

  const sh = await post(request, c, "/sales/shipments", {
    code: `DESP-${m}`, order_id: e.pedido, destination: "Caracas", transport: "Transportista",
  });
  await post(request, c, `/sales/shipments/${sh.id}/validate`, {});
  await post(request, c, `/sales/shipments/${sh.id}/confirm`, {});

  const elegible = await get(request, c, `/sales/devoluciones/elegibles/${factura.id}`);
  expect(elegible.dispatched, "el escenario no llegó a despachar").toBe(true);
  return {
    ...e, factura: factura.id as string, fiscal: f, shipment: sh.id as string,
    invoiceLine: elegible.lines[0].invoice_line_id as string,
  };
}

async function saldos(request: APIRequestContext, c: Ctx, producto: string) {
  const r = await get(request, c, `/inventory/balances?product_id=${producto}`);
  const mapa: Record<string, number> = {};
  for (const b of r.items as Array<{ state: string; qty_on_hand: string }>) {
    mapa[b.state] = (mapa[b.state] ?? 0) + Number(b.qty_on_hand);
  }
  return mapa;
}

/** El área a la que entra la mercancía devuelta. */
async function areaDeDevoluciones(request: APIRequestContext, c: Ctx, almacen: string, m: string) {
  const loc = await post(request, c, "/organization/locations", {
    warehouse_id: almacen, code: `VD-${m}`, name: "Área de devoluciones", sequence: 90,
  });
  return loc.id as string;
}


async function uiLogin(page: Page): Promise<void> {
  await entrarConSesion(page, "admin", { tenant: "DEMO" });
  await expect(page).toHaveURL(/\/$/, { timeout: 20_000 });
}

test.describe("Spec 036 — devoluciones, notas de crédito y notas de débito", () => {
  test("los cuatro actos, y solo el último crea existencia", async ({ request }) => {
    const c = await ctx(request);
    const m = marca();
    const e = await despachado(request, c, m, { cantidad: 10, precio: 25 });
    const area = await areaDeDevoluciones(request, c, e.almacen, m);

    const antes = await saldos(request, c, e.producto);
    expect(antes.DESPACHADO).toBe(10);

    // 1 · Solicitud. No mueve una sola unidad.
    const dev = await post(request, c, "/sales/devoluciones", {
      code: `DEV-${m}`, invoice_id: e.factura, reason: "Mercancía dañada en tránsito",
      lines: [{ invoice_line_id: e.invoiceLine, base_quantity: 6, quantity: 6 }],
    });
    expect(dev.status).toBe("REQUESTED");
    expect(await saldos(request, c, e.producto), "la solicitud movió inventario").toEqual(antes);

    // 2 · Recepción. La custodia vuelve; la disponibilidad no.
    await post(request, c, `/sales/devoluciones/${dev.id}/recibir`, { location_id: area });
    const trasRecibir = await saldos(request, c, e.producto);
    expect(trasRecibir.DEVUELTO).toBe(6);
    expect(trasRecibir.DESPACHADO).toBe(4);
    expect(trasRecibir.DISPONIBLE ?? 0, "recibir la hizo vendible sin verificarla")
      .toBe(antes.DISPONIBLE ?? 0);

    // 3 · Verificación y aprobación.
    const detalle = await get(request, c, `/sales/devoluciones/${dev.id}`);
    await post(request, c, `/sales/devoluciones/${dev.id}/verificar`, {
      lines: [{ return_line_id: detalle.lines[0].id, disposition: "DISPONIBLE",
                accepted_base_quantity: 4 }],
    });
    await post(request, c, `/sales/devoluciones/${dev.id}/decidir`, { approved: true });

    // 4 · Entrada de inventario. Ahora sí.
    const cerrada = await post(request, c, `/sales/devoluciones/${dev.id}/reingresar`, {});
    expect(cerrada.status).toBe("CLOSED");
    const final = await saldos(request, c, e.producto);
    expect(final.DISPONIBLE).toBe((antes.DISPONIBLE ?? 0) + 4);
    expect(final.DEVUELTO, "lo no aceptado salió de custodia").toBe(2);
  });

  test("no se reingresa sin pasar por la aprobación", async ({ request }) => {
    const c = await ctx(request);
    const m = marca();
    const e = await despachado(request, c, m, { cantidad: 5 });
    const area = await areaDeDevoluciones(request, c, e.almacen, m);
    const dev = await post(request, c, "/sales/devoluciones", {
      code: `DEV-${m}`, invoice_id: e.factura, reason: "Producto equivocado",
      lines: [{ invoice_line_id: e.invoiceLine, base_quantity: 5, quantity: 5 }],
    });
    await post(request, c, `/sales/devoluciones/${dev.id}/recibir`, { location_id: area });
    const detalle = await get(request, c, `/sales/devoluciones/${dev.id}`);
    await post(request, c, `/sales/devoluciones/${dev.id}/verificar`, {
      lines: [{ return_line_id: detalle.lines[0].id, disposition: "DISPONIBLE" }],
    });
    const r = await postCrudo(request, c, `/sales/devoluciones/${dev.id}/reingresar`, {});
    expect(r.status()).toBe(409);
  });

  test("no se devuelve más de lo despachado", async ({ request }) => {
    const c = await ctx(request);
    const m = marca();
    const e = await despachado(request, c, m, { cantidad: 10 });
    const r = await postCrudo(request, c, "/sales/devoluciones", {
      code: `DEV-${m}`, invoice_id: e.factura, reason: "Excede",
      lines: [{ invoice_line_id: e.invoiceLine, base_quantity: 11, quantity: 11 }],
    });
    expect(r.status()).toBe(409);
    expect((await r.json()).code).toBe("RETURN_EXCEEDS_DISPATCHED");
  });

  test("el destino de la mercancía devuelta no se inventa", async ({ request }) => {
    const c = await ctx(request);
    const m = marca();
    const e = await despachado(request, c, m, { cantidad: 4 });
    const area = await areaDeDevoluciones(request, c, e.almacen, m);
    const dev = await post(request, c, "/sales/devoluciones", {
      code: `DEV-${m}`, invoice_id: e.factura, reason: "Dañada",
      lines: [{ invoice_line_id: e.invoiceLine, base_quantity: 4, quantity: 4 }],
    });
    await post(request, c, `/sales/devoluciones/${dev.id}/recibir`, { location_id: area });
    const detalle = await get(request, c, `/sales/devoluciones/${dev.id}`);
    const r = await postCrudo(request, c, `/sales/devoluciones/${dev.id}/verificar`, {
      lines: [{ return_line_id: detalle.lines[0].id, disposition: "CUARENTENA" }],
    });
    expect(r.status()).toBe(422);
    expect((await r.json()).code).toBe("RETURN_DISPOSITION_INVALID");
  });

  test("aceptar la devolución no emite ninguna nota", async ({ request }) => {
    const c = await ctx(request);
    const m = marca();
    const e = await despachado(request, c, m, { cantidad: 6, precio: 10 });
    const area = await areaDeDevoluciones(request, c, e.almacen, m);
    const dev = await post(request, c, "/sales/devoluciones", {
      code: `DEV-${m}`, invoice_id: e.factura, reason: "Devolución completa",
      lines: [{ invoice_line_id: e.invoiceLine, base_quantity: 6, quantity: 6 }],
    });
    await post(request, c, `/sales/devoluciones/${dev.id}/recibir`, { location_id: area });
    const detalle = await get(request, c, `/sales/devoluciones/${dev.id}`);
    await post(request, c, `/sales/devoluciones/${dev.id}/verificar`, {
      lines: [{ return_line_id: detalle.lines[0].id, disposition: "DISPONIBLE" }],
    });
    await post(request, c, `/sales/devoluciones/${dev.id}/decidir`, { approved: true });
    await post(request, c, `/sales/devoluciones/${dev.id}/reingresar`, {});

    const acreditable = await get(request, c, `/sales/notas/acreditable/${e.factura}`);
    expect(Number(acreditable.lines[0].credited_quantity),
           "la devolución acreditó por su cuenta").toBe(0);
    expect((await get(request, c, `/sales/invoices`)).items.length).toBeGreaterThan(0);
  });

  test("la nota reparte el impuesto de la factura y lleva su propio número", async ({ request }) => {
    const c = await ctx(request);
    const m = marca();
    const e = await despachado(request, c, m, { cantidad: 10, precio: 100 });

    const nota = await post(request, c, `/sales/notas/credito/${e.factura}/generar`, {
      cause: "Devolución de mercancía",
      lines: [{ invoice_line_id: e.invoiceLine, quantity: 2 }],
    });
    expect(Number(nota.base_fiscal), "no repartió en proporción").toBe(200);
    expect(nota.invoice_number, "la nota nació numerada sin emitirse").toBeNull();

    const emitida = await post(request, c, `/sales/notas/credito/${nota.id}/emitir`, {
      series_id: e.fiscal.series.CREDIT_NOTE, batch_id: e.fiscal.batch,
    });
    expect(emitida.invoice_number, "no recibió consecutivo propio").toBeTruthy();
    expect(emitida.control_number, "no recibió número de control").toBeTruthy();
  });

  test("la nota no se emite con la serie de las facturas", async ({ request }) => {
    const c = await ctx(request);
    const m = marca();
    const e = await despachado(request, c, m, { cantidad: 4, precio: 10 });
    const nota = await post(request, c, `/sales/notas/credito/${e.factura}/generar`, {
      cause: "Descuento posterior",
      lines: [{ invoice_line_id: e.invoiceLine, quantity: 1 }],
    });
    const r = await postCrudo(request, c, `/sales/notas/credito/${nota.id}/emitir`, {
      series_id: e.fiscal.series.INVOICE, batch_id: e.fiscal.batch,
    });
    expect(r.status()).toBe(422);
    expect((await r.json()).code).toBe("SERIES_DOCUMENT_TYPE_MISMATCH");
  });

  test("no se acredita por encima de lo pendiente", async ({ request }) => {
    const c = await ctx(request);
    const m = marca();
    const e = await despachado(request, c, m, { cantidad: 10, precio: 10 });
    await post(request, c, `/sales/notas/credito/${e.factura}/generar`, {
      cause: "Disminución de cantidad",
      lines: [{ invoice_line_id: e.invoiceLine, quantity: 8 }],
    });
    const r = await postCrudo(request, c, `/sales/notas/credito/${e.factura}/generar`, {
      cause: "Otra más", lines: [{ invoice_line_id: e.invoiceLine, quantity: 3 }],
    });
    expect(r.status()).toBe(409);
    expect((await r.json()).code).toBe("CREDIT_EXCEEDS_INVOICE");
  });

  test("la nota de crédito sin devolución no mueve inventario", async ({ request }) => {
    const c = await ctx(request);
    const m = marca();
    const e = await despachado(request, c, m, { cantidad: 5, precio: 20 });
    const antes = await saldos(request, c, e.producto);
    const nota = await post(request, c, `/sales/notas/credito/${e.factura}/generar`, {
      cause: "Corrección de un precio facturado en exceso",
      lines: [{ invoice_line_id: e.invoiceLine, quantity: 1 }],
    });
    await post(request, c, `/sales/notas/credito/${nota.id}/emitir`, {
      series_id: e.fiscal.series.CREDIT_NOTE, batch_id: e.fiscal.batch,
    });
    expect(await saldos(request, c, e.producto)).toEqual(antes);
  });

  test("la nota de débito aumenta y no toca inventario", async ({ request }) => {
    const c = await ctx(request);
    const m = marca();
    const e = await despachado(request, c, m, { cantidad: 5, precio: 20 });
    const antes = await saldos(request, c, e.producto);
    const nota = await post(request, c, `/sales/notas/debito/${e.factura}/generar`, {
      cause: "Flete posterior gravado",
      lines: [{ concept: "Flete al domicilio del cliente", base_fiscal: 40 }],
    });
    expect(Number(nota.total)).toBe(40);
    const emitida = await post(request, c, `/sales/notas/debito/${nota.id}/emitir`, {
      series_id: e.fiscal.series.DEBIT_NOTE, batch_id: e.fiscal.batch,
    });
    expect(emitida.invoice_number).toBeTruthy();
    expect(await saldos(request, c, e.producto)).toEqual(antes);
  });

  test("emitir dos veces no gasta dos números", async ({ request }) => {
    const c = await ctx(request);
    const m = marca();
    const e = await despachado(request, c, m, { cantidad: 4, precio: 10 });
    const nota = await post(request, c, `/sales/notas/credito/${e.factura}/generar`, {
      cause: "Bonificación posterior",
      lines: [{ invoice_line_id: e.invoiceLine, quantity: 1 }],
    });
    const uno = await post(request, c, `/sales/notas/credito/${nota.id}/emitir`, {
      series_id: e.fiscal.series.CREDIT_NOTE, batch_id: e.fiscal.batch,
    });
    const dos = await post(request, c, `/sales/notas/credito/${nota.id}/emitir`, {
      series_id: e.fiscal.series.CREDIT_NOTE, batch_id: e.fiscal.batch,
    });
    expect(dos.invoice_number).toBe(uno.invoice_number);
    expect(dos.control_number).toBe(uno.control_number);
  });

  test("la interfaz solicita la devolución y el dominio lo confirma", async ({ page, request }) => {
    const c = await ctx(request);
    const m = marca();
    const e = await despachado(request, c, m, { cantidad: 8, precio: 10 });
    const antes = await saldos(request, c, e.producto);

    await uiLogin(page);
    await page.locator('nav a[href="/ventas/devoluciones"]').first().click();
    await page.waitForURL((u) => u.pathname === "/ventas/devoluciones", { timeout: 15_000 });
    await expect(page.getByRole("heading", { name: "Devoluciones", level: 1 })).toBeVisible();

    await page.getByLabel("Factura").fill(e.factura);
    await expect(page.getByText("Se puede devolver")).toBeVisible({ timeout: 15_000 });
    await page.getByLabel("Código").fill(`DEV-${m}`);
    await page.getByLabel("Motivo").fill("El cliente recibió una unidad rota");
    await page.getByLabel(/^Devolver de/).fill("3");
    await page.getByRole("button", { name: "Solicitar devolución" }).click();

    await expect(page.getByText(/Ubicación de entrada/)).toBeVisible({ timeout: 15_000 });
    // Solicitar no mueve inventario, y el dominio lo confirma.
    expect(await saldos(request, c, e.producto),
           "la interfaz movió inventario al solicitar").toEqual(antes);

    const lista = await get(request, c, "/sales/devoluciones");
    const creada = (lista.items as Array<{ code: string; status: string }>)
      .find((x) => x.code === `DEV-${m}`);
    expect(creada, "la interfaz no creó la devolución").toBeTruthy();
    expect(creada?.status).toBe("REQUESTED");
  });
});
