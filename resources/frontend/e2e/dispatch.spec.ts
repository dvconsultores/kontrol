/**
 * E2E del despacho — Spec 035.
 *
 * Frontend real → API real → backend real → PostgreSQL real.
 *
 * Lo que esta suite defiende es la compuerta del ¶103 y la salida física. No
 * comprueba que la pantalla diga «despachado»: comprueba que la mercancía dejó
 * de estar preparada, que salió en unidad **base** y que la reserva quedó
 * consumida. Hasta este ciclo `validate_shipment` aprobaba siempre, así que
 * cada negativa de aquí es una que antes no existía.
 */
import { expect, test, type APIRequestContext, type Page } from "@playwright/test";

const TENANT = process.env.KONTROL_E2E_TENANT ?? "DEMO";
const USER = process.env.KONTROL_E2E_USER ?? "admin";
const PASSWORD = process.env.KONTROL_E2E_PASSWORD ?? "";
const API = process.env.KONTROL_E2E_API ?? "http://127.0.0.1:8000/api/v1";

type Ctx = { token: string; company: string; headers: Record<string, string> };

async function ctx(request: APIRequestContext): Promise<Ctx> {
  const login = await request.post(`${API}/auth/login`, {
    data: { tenant_code: TENANT, username: USER, password: PASSWORD },
  });
  expect(login.ok(), `login: ${login.status()}`).toBeTruthy();
  const token = (await login.json()).access_token as string;
  const r = await request.get(`${API}/organization/companies`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  const body = await r.json();
  const company = (Array.isArray(body) ? body : body.items)[0].id as string;
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
  const roles = await get(request, c, "/roles");
  const rol = (roles.items as Array<{ id: string; code?: string; name?: string }>).find(
    (r) => (r.code ?? r.name ?? "").toUpperCase().includes("ADMIN"),
  ) ?? (roles.items as Array<{ id: string }>)[0];
  const usuario = await post(request, c, "/users", {
    username: `disp-${m.toLowerCase()}`,
    email: `disp-${m.toLowerCase()}@kontrol-qa.com`,
    password: PASSWORD,
    must_change_password: false,
  });
  await post(request, c, `/users/${usuario.id}/roles`, { role_id: rol.id, company_id: c.company });
  const login = await request.post(`${API}/auth/login`, {
    data: { tenant_code: TENANT, username: `disp-${m.toLowerCase()}`, password: PASSWORD },
  });
  expect(login.ok(), `login del verificador: ${login.status()}`).toBeTruthy();
  const token = (await login.json()).access_token as string;
  return {
    token,
    company: c.company,
    headers: { Authorization: `Bearer ${token}`, "X-Kontrol-Company": c.company },
  };
}

async function fiscalListo(request: APIRequestContext, c: Ctx, m: string) {
  const fuente = await post(request, c, "/fiscal/legal-sources", {
    authority: "SENIAT", source_type: "LEY", number: `LD-${m}`, effective_from: "2020-01-01",
  });
  await post(request, c, `/fiscal/legal-sources/${fuente.id}/activate`, {});
  const serie = await post(request, c, "/fiscal/number-series", {
    document_type: "INVOICE", prefix: "D",
  });
  const desde = 100000 + Math.floor(Math.random() * 800000);
  const lote = await post(request, c, "/fiscal/control-batches", {
    range_from: String(desde), range_to: String(desde + 49),
  });
  return { series: serie.id as string, batch: lote.id as string };
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

/** Un pedido confirmado, listo para facturar. */
async function escenario(
  request: APIRequestContext,
  c: Ctx,
  m: string,
  { cantidad = 10, precio = 25 } = {},
): Promise<Escenario> {
  const propio = await post(request, c, "/organization/warehouses", {
    company_id: c.company, code: `WD-${m}`, name: `Almacén despacho ${m}`,
    warehouse_type: "PHYSICAL", status: "ACTIVE",
  });
  const almacen = propio.id as string;
  const producto = await post(request, c, "/maestros/catalogos/items", {
    code: `PD-${m}`, name: `Artículo ${m}`, item_type: "PRODUCT", status: "ACTIVE",
  });
  const l1 = await post(request, c, "/organization/locations", {
    warehouse_id: almacen, code: `D1-${m}`, name: "Origen", sequence: 1,
  });
  const area = await post(request, c, "/organization/locations", {
    warehouse_id: almacen, code: `DC-${m}`, name: "Área de Confirmación", sequence: 99,
  });

  const tipos = await get(request, c, "/inventory/movement-types");
  let entrada = (tipos.items ?? tipos).find(
    (x: { code: string }) => x.code === "ENTRADA_RECEPCION",
  ) as { id: string } | undefined;
  if (!entrada) {
    entrada = (await post(request, c, "/inventory/movement-types", {
      code: "ENTRADA_RECEPCION", name: "Entrada por recepción", direction: "IN",
    })) as { id: string };
  }
  await post(request, c, "/inventory/movements", {
    warehouse_id: almacen, product_id: producto.id, movement_type_id: entrada.id,
    quantity: cantidad + 20,
  });
  await post(request, c, "/inventory/putaway", {
    warehouse_id: almacen, product_id: producto.id, target_location_id: l1.id,
    quantity: cantidad + 20,
  });

  const cliente = await post(request, c, "/maestros/terceros", {
    code: `CD-${m}`, name: `Cliente ${m}`, roles: ["CLIENTE"],
  });
  const pedido = await post(request, c, "/sales/orders", {
    code: `OVD-${m}`, customer_id: cliente.id, currency: "VED", warehouse_id: almacen,
  });
  const linea = await post(request, c, `/sales/orders/${pedido.id}/lines`, {
    product_id: producto.id, quantity: cantidad, unit_price: precio,
  });
  const emitido = await post(request, c, `/sales/orders/${pedido.id}/submit`, {});
  if (emitido.status !== "RELEASED") {
    await post(request, c, `/sales/orders/${pedido.id}/release`, {});
  }

  const plan = await post(request, c, "/sales/pick-lists", {
    code: `PLD-${m}`, order_id: pedido.id, warehouse_id: almacen,
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
async function facturado(request: APIRequestContext, c: Ctx, m: string, opciones = {}) {
  const f = await fiscalListo(request, c, m);
  const e = await escenario(request, c, m, opciones);
  await post(request, e.v, `/sales/facturacion/${e.pedido}/solicitar`, {});
  const factura = await post(request, c, `/sales/facturacion/${e.pedido}/generar`, {});
  const emitida = await post(request, c, `/sales/facturacion/${factura.id}/emitir`, {
    series_id: f.series, batch_id: f.batch,
  });
  expect(emitida.status).toBe("EMITTED");
  return { ...e, factura: factura.id as string };
}

async function saldos(request: APIRequestContext, c: Ctx, producto: string) {
  const r = await get(request, c, `/inventory/balances?product_id=${producto}`);
  const mapa: Record<string, number> = {};
  for (const b of r.items as Array<{ state: string; qty_on_hand: string }>) {
    mapa[b.state] = (mapa[b.state] ?? 0) + Number(b.qty_on_hand);
  }
  return mapa;
}

async function uiLogin(page: Page): Promise<void> {
  await page.goto("/login");
  await page.getByLabel(/Empresa \(código\)/).fill(TENANT);
  await page.getByLabel(/Usuario/).fill(USER);
  await page.getByLabel(/Contraseña/).fill(PASSWORD);
  await page.getByRole("button", { name: "Iniciar sesión" }).click();
  await expect(page).toHaveURL(/\/$/, { timeout: 20_000 });
}

test.describe("Spec 035 — despacho, transporte y regulación", () => {
  test("el pedido facturado sale del almacén y la reserva se consume", async ({ request }) => {
    const c = await ctx(request);
    const m = marca();
    const e = await facturado(request, c, m, { cantidad: 10, precio: 25 });

    const antes = await saldos(request, c, e.producto);
    expect(antes.PREPARADO, "la 032 no dejó la mercancía preparada").toBe(10);

    const sh = await post(request, c, "/sales/shipments", {
      code: `DESP-${m}`, order_id: e.pedido,
      destination: "Caracas", transport: "Transportista X",
    });
    expect(sh.lines.length, "el despacho no tomó las líneas consolidadas").toBe(1);
    expect(Number(sh.lines[0].base_quantity)).toBe(10);
    expect(sh.origin_warehouse_id, "no heredó el almacén del pedido").toBe(e.almacen);

    const validado = await post(request, c, `/sales/shipments/${sh.id}/validate`, {});
    expect(validado.status).toBe("READY");
    expect(validado.regulatory_status).toBe("CLEARED");
    expect(validado.invoice_id, "no guardó con qué factura sale").toBeTruthy();

    const salido = await post(request, c, `/sales/shipments/${sh.id}/confirm`, {});
    expect(salido.status).toBe("SHIPPED");
    expect(salido.dispatched_at).toBeTruthy();

    expect((await get(request, c, `/sales/orders/${e.pedido}`)).status).toBe("SHIPPED");
    const despues = await saldos(request, c, e.producto);
    expect(despues.PREPARADO ?? 0, "la mercancía sigue preparada tras salir").toBe(0);
    expect(despues.DESPACHADO).toBe(10);

    const reservas = await get(request, c, `/inventory/reservations?product_id=${e.producto}`);
    const activas = (reservas.items as Array<{ status: string }>).filter((x) => x.status === "ACTIVE");
    expect(activas.length, "quedó reserva viva tras la salida").toBe(0);
  });

  test("no se despacha un pedido sin factura emitida", async ({ request }) => {
    const c = await ctx(request);
    const m = marca();
    const e = await escenario(request, c, m, { cantidad: 5 });
    const r = await postCrudo(request, c, "/sales/shipments", {
      code: `DESP-${m}`, order_id: e.pedido, destination: "Valencia", transport: "Cliente",
    });
    expect(r.status()).toBe(409);
    expect((await r.json()).code).toBe("ORDER_NOT_SHIPPABLE");
  });

  test("no se autoriza la salida sin decir a dónde va ni con quién", async ({ request }) => {
    const c = await ctx(request);
    const m = marca();
    const e = await facturado(request, c, m, { cantidad: 4 });
    const sh = await post(request, c, "/sales/shipments", {
      code: `DESP-${m}`, order_id: e.pedido,
    });
    const r = await postCrudo(request, c, `/sales/shipments/${sh.id}/validate`, {});
    expect(r.status()).toBe(422);
    expect((await r.json()).code).toBe("DISPATCH_TRANSPORT_REQUIRED");
  });

  test("no se confirma una salida sin validar", async ({ request }) => {
    const c = await ctx(request);
    const m = marca();
    const e = await facturado(request, c, m, { cantidad: 3 });
    const sh = await post(request, c, "/sales/shipments", {
      code: `DESP-${m}`, order_id: e.pedido, destination: "Barquisimeto", transport: "Cliente",
    });
    const r = await postCrudo(request, c, `/sales/shipments/${sh.id}/confirm`, {});
    expect(r.status()).toBe(409);
    expect((await r.json()).code).toBe("SHIPMENT_NOT_VALIDATED");
  });

  test("un pedido no se despacha dos veces", async ({ request }) => {
    const c = await ctx(request);
    const m = marca();
    const e = await facturado(request, c, m, { cantidad: 6 });
    await post(request, c, "/sales/shipments", {
      code: `DESP-${m}`, order_id: e.pedido, destination: "Maracaibo", transport: "Cliente",
    });
    const r = await postCrudo(request, c, "/sales/shipments", {
      code: `DESP2-${m}`, order_id: e.pedido, destination: "Maracaibo", transport: "Cliente",
    });
    expect(r.status()).toBe(409);
    expect((await r.json()).code).toBe("ORDER_ALREADY_SHIPPED");
  });

  test("confirmar dos veces no saca la mercancía dos veces", async ({ request }) => {
    const c = await ctx(request);
    const m = marca();
    const e = await facturado(request, c, m, { cantidad: 7 });
    const sh = await post(request, c, "/sales/shipments", {
      code: `DESP-${m}`, order_id: e.pedido, destination: "Mérida", transport: "Cliente",
    });
    await post(request, c, `/sales/shipments/${sh.id}/validate`, {});
    await post(request, c, `/sales/shipments/${sh.id}/confirm`, {});
    await post(request, c, `/sales/shipments/${sh.id}/confirm`, {});
    expect((await saldos(request, c, e.producto)).DESPACHADO).toBe(7);
  });

  test("la cola solo trae pedidos facturados y los suelta al salir", async ({ request }) => {
    const c = await ctx(request);
    const m = marca();
    const sinFactura = await escenario(request, c, m, { cantidad: 2 });
    const listo = await facturado(request, c, marca(), { cantidad: 5 });

    const cola = await get(request, c, "/sales/despacho/pendientes");
    const codigos = (cola.items as Array<{ code: string }>).map((x) => x.code);
    expect(codigos).toContain(listo.pedidoCode);
    expect(codigos, "un pedido sin factura emitida entró en la cola")
      .not.toContain(sinFactura.pedidoCode);

    const sh = await post(request, c, "/sales/shipments", {
      code: `DESP-${m}`, order_id: listo.pedido, destination: "Cumaná", transport: "Cliente",
    });
    await post(request, c, `/sales/shipments/${sh.id}/validate`, {});
    await post(request, c, `/sales/shipments/${sh.id}/confirm`, {});

    const despues = await get(request, c, "/sales/despacho/pendientes");
    expect((despues.items as Array<{ code: string }>).map((x) => x.code))
      .not.toContain(listo.pedidoCode);
  });

  test("la interfaz despacha y el dominio lo confirma", async ({ page, request }) => {
    const c = await ctx(request);
    const m = marca();
    const e = await facturado(request, c, m, { cantidad: 8, precio: 10 });

    await uiLogin(page);
    await page.locator('nav a[href="/ventas/despacho"]').first().click();
    await page.waitForURL((u) => u.pathname === "/ventas/despacho", { timeout: 15_000 });
    await expect(page.getByRole("heading", { name: "Despacho" })).toBeVisible();

    // Hay que esperar a que la cola cargue antes de mirar el paginador: con la
    // tabla todavía vacía no existe, se salía del bucle en la primera vuelta y
    // la fila se quedaba en la página tres. Este pedido está facturado, así que
    // la tabla tiene al menos una fila.
    await expect(page.getByRole("region", { name: /Resultados:/ })).toBeVisible({
      timeout: 15_000,
    });

    // La cola cabe en una página cuando la base está recién sembrada y en
    // varias cuando lleva corridas encima: se pagina solo si hay paginador.
    const fila = page.getByRole("row", { name: new RegExp(e.pedidoCode) });
    const siguiente = page.getByRole("button", { name: "Página siguiente" });
    for (let i = 0; i < 20 && (await fila.count()) === 0; i += 1) {
      if ((await siguiente.count()) === 0 || (await siguiente.isDisabled())) break;
      await siguiente.click();
      await page.waitForLoadState("networkidle");
    }
    await expect(fila).toHaveCount(1);
    await fila.getByRole("button", { name: "Preparar salida" }).click();
    await page.waitForLoadState("networkidle");

    await page.getByLabel("Código").fill(`DESP-${m}`);
    await page.getByLabel("Destino").fill("Puerto Cabello");
    await page.getByLabel("Se entrega a").fill("Transportista UI");
    await page.getByRole("button", { name: "Registrar despacho" }).click();

    await page.getByRole("button", { name: "Validar salida" }).click();
    await expect(page.getByRole("button", { name: "Confirmar salida física" }))
      .toBeVisible({ timeout: 15_000 });

    // La pantalla no tiene campo de cantidad: lo que sale es lo consolidado.
    const estadoMedio = await get(request, c, `/sales/despacho/${e.pedido}/despacho`);
    expect(Number(estadoMedio.shipment.lines[0].base_quantity)).toBe(8);
    expect(estadoMedio.shipment.status, "validar sacó la mercancía").toBe("READY");
    expect((await saldos(request, c, e.producto)).PREPARADO).toBe(8);

    await page.getByRole("button", { name: "Confirmar salida física" }).click();
    await expect(page.getByText(/Mercancía despachada/)).toBeVisible({ timeout: 15_000 });

    const estado = await get(request, c, `/sales/despacho/${e.pedido}/despacho`);
    expect(estado.order_status).toBe("SHIPPED");
    expect((await saldos(request, c, e.producto)).DESPACHADO).toBe(8);
  });
});
