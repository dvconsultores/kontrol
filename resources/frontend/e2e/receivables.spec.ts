/**
 * E2E de las cuentas por cobrar — Spec 037.
 *
 * Frontend real → API real → backend real → PostgreSQL real.
 *
 * El caso obligatorio de esta suite es el P0: el crédito de un cliente **no**
 * se aplica al documento de otro, aunque sean de la misma empresa. Y lo que se
 * comprueba después de cada acción es el dominio —saldo del documento, crédito
 * restante, filas de aplicación, cobros— porque un aviso en pantalla no prueba
 * que el dinero se haya movido donde debía.
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
    username: `cxc-${m.toLowerCase()}`,
    email: `cxc-${m.toLowerCase()}@kontrol-qa.com`,
    password: PASSWORD,
    must_change_password: false,
  });
  await post(request, c, `/users/${usuario.id}/roles`, { role_id: rol.id, company_id: c.company });
  const login = await request.post(`${API}/auth/login`, {
    data: { tenant_code: TENANT, username: `cxc-${m.toLowerCase()}`, password: PASSWORD },
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
    authority: "SENIAT", source_type: "LEY", number: `LC-${m}`, effective_from: "2020-01-01",
  });
  await post(request, c, `/fiscal/legal-sources/${fuente.id}/activate`, {});
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
    company_id: c.company, code: `WC-${m}`, name: `Almacén devoluciones ${m}`,
    warehouse_type: "PHYSICAL", status: "ACTIVE",
  });
  const almacen = propio.id as string;
  const producto = await post(request, c, "/maestros/catalogos/items", {
    code: `PC-${m}`, name: `Artículo ${m}`, item_type: "PRODUCT", status: "ACTIVE",
  });
  const l1 = await post(request, c, "/organization/locations", {
    warehouse_id: almacen, code: `C1-${m}`, name: "Origen", sequence: 1,
  });
  const area = await post(request, c, "/organization/locations", {
    warehouse_id: almacen, code: `CC-${m}`, name: "Área de Confirmación", sequence: 99,
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
    code: `CL-${m}`, name: `Cliente ${m}`, roles: ["CLIENTE"],
  });
  const pedido = await post(request, c, "/sales/orders", {
    code: `OVC-${m}`, customer_id: cliente.id, currency: "VED", warehouse_id: almacen,
  });
  const linea = await post(request, c, `/sales/orders/${pedido.id}/lines`, {
    product_id: producto.id, quantity: cantidad, unit_price: precio,
  });
  const emitido = await post(request, c, `/sales/orders/${pedido.id}/submit`, {});
  if (emitido.status !== "RELEASED") {
    await post(request, c, `/sales/orders/${pedido.id}/release`, {});
  }

  const plan = await post(request, c, "/sales/pick-lists", {
    code: `PLC-${m}`, order_id: pedido.id, warehouse_id: almacen,
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

/** El área a la que entra la mercancía devuelta. */
/** El documento por cobrar que la factura abre al emitirse (delta de la 034). */
async function documentoPorCobrar(request: APIRequestContext, c: Ctx, facturaId: string) {
  const items = await get(request, c, "/sales/open-items");
  const doc = (items.items as Array<{ id: string; source_document: string; balance: string }>)
    .find((x) => x.source_document === `SALES_INVOICE:${facturaId}`);
  expect(doc, "la factura emitida no abrió su cuenta por cobrar").toBeTruthy();
  return doc!;
}

/** Una nota de crédito emitida sobre la factura del escenario. */
async function creditoEmitido(request: APIRequestContext, c: Ctx, e: Despachado, cantidad: number) {
  const nota = await post(request, c, `/sales/notas/credito/${e.factura}/generar`, {
    cause: "Devolución de mercancía",
    lines: [{ invoice_line_id: e.invoiceLine, quantity: cantidad }],
  });
  return post(request, c, `/sales/notas/credito/${nota.id}/emitir`, {
    series_id: e.fiscal.series.CREDIT_NOTE, batch_id: e.fiscal.batch,
  });
}

async function uiLogin(page: Page): Promise<void> {
  await page.goto("/login");
  await page.getByLabel(/Empresa \(código\)/).fill(TENANT);
  await page.getByLabel(/Usuario/).fill(USER);
  await page.getByLabel(/Contraseña/).fill(PASSWORD);
  await page.getByRole("button", { name: "Iniciar sesión" }).click();
  await expect(page).toHaveURL(/\/$/, { timeout: 20_000 });
}

test.describe("Spec 037 — cuentas por cobrar", () => {
  test("la factura emitida abre su cuenta por cobrar", async ({ request }) => {
    const c = await ctx(request);
    const e = await despachado(request, c, marca(), { cantidad: 4, precio: 25 });
    const doc = await documentoPorCobrar(request, c, e.factura);
    expect(Number(doc.balance)).toBe(100);
  });

  test("P0 · el crédito de un cliente no se aplica al documento de otro", async ({ request }) => {
    const c = await ctx(request);
    // Dos escenarios completos: cada uno con su cliente y su factura.
    const x = await despachado(request, c, marca(), { cantidad: 4, precio: 25 });
    const y = await despachado(request, c, marca(), { cantidad: 4, precio: 25 });
    const credito = await creditoEmitido(request, c, x, 2);
    const ajeno = await documentoPorCobrar(request, c, y.factura);

    const r = await postCrudo(request, c, `/sales/cxc/creditos/${credito.id}/aplicar`, {
      target_open_item_id: ajeno.id, amount: "10.00",
    });
    expect(r.status(), "se aplicó un crédito entre clientes").toBe(409);
    expect((await r.json()).code).toBe("CREDIT_CUSTOMER_MISMATCH");

    // Y nada se movió.
    const despues = await documentoPorCobrar(request, c, y.factura);
    expect(Number(despues.balance)).toBe(Number(ajeno.balance));
    const apps = await get(request, c, `/sales/cxc/documentos/${ajeno.id}/aplicaciones`);
    expect(apps.items.length).toBe(0);
  });

  test("el crédito se aplica al documento de su propio cliente", async ({ request }) => {
    const c = await ctx(request);
    const e = await despachado(request, c, marca(), { cantidad: 4, precio: 25 });
    const credito = await creditoEmitido(request, c, e, 2);
    const doc = await documentoPorCobrar(request, c, e.factura);

    // La emisión de la nota ya redujo el documento; queda lo demás por aplicar.
    const saldo = await get(request, c, `/sales/cxc/clientes/${credito.customer_id}/saldo`);
    expect(Number(saldo.documents)).toBe(100);

    const apps = await get(request, c, `/sales/cxc/documentos/${doc.id}/aplicaciones`);
    expect(apps.items.length, "la emisión no dejó su aplicación").toBe(1);
    expect(apps.items[0].source_type).toBe("CREDIT");
    expect(apps.items[0].status).toBe("APPLIED");
  });

  test("revertir una aplicación no la borra y reabre el documento", async ({ request }) => {
    const c = await ctx(request);
    const e = await despachado(request, c, marca(), { cantidad: 4, precio: 25 });
    const credito = await creditoEmitido(request, c, e, 2);
    const doc = await documentoPorCobrar(request, c, e.factura);
    const apps = await get(request, c, `/sales/cxc/documentos/${doc.id}/aplicaciones`);
    const original = apps.items[0];

    const rev = await post(request, c, `/sales/cxc/aplicaciones/${original.id}/revertir`, {
      reason: "El cliente reclamó que no correspondía",
    });
    expect(Number(rev.amount)).toBe(-Number(original.amount));

    const despues = await get(request, c, `/sales/cxc/documentos/${doc.id}/aplicaciones`);
    const estados = (despues.items as Array<{ status: string }>).map((x) => x.status).sort();
    expect(estados, "el reverso borró la original").toEqual(["REVERSAL", "REVERSED"]);

    const doc2 = await documentoPorCobrar(request, c, e.factura);
    expect(Number(doc2.balance)).toBe(100);
    expect(Number((await get(request, c,
      `/sales/cxc/clientes/${credito.customer_id}/creditos`)).items[0].available))
      .toBe(Number(original.amount));
  });

  test("una aplicación no se revierte dos veces", async ({ request }) => {
    const c = await ctx(request);
    const e = await despachado(request, c, marca(), { cantidad: 4, precio: 25 });
    await creditoEmitido(request, c, e, 1);
    const doc = await documentoPorCobrar(request, c, e.factura);
    const apps = await get(request, c, `/sales/cxc/documentos/${doc.id}/aplicaciones`);
    const original = apps.items[0];
    await post(request, c, `/sales/cxc/aplicaciones/${original.id}/revertir`, { reason: "Primera" });
    const otra = await postCrudo(request, c, `/sales/cxc/aplicaciones/${original.id}/revertir`,
                                 { reason: "Segunda" });
    expect(otra.status()).toBe(409);
    expect((await otra.json()).code).toBe("APPLICATION_ALREADY_REVERSED");
  });

  test("aplicar un crédito no crea cobros", async ({ request }) => {
    const c = await ctx(request);
    const antes = (await get(request, c, "/sales/collections")).items.length;
    const e = await despachado(request, c, marca(), { cantidad: 4, precio: 25 });
    await creditoEmitido(request, c, e, 2);
    const despues = (await get(request, c, "/sales/collections")).items.length;
    expect(despues, "aplicar un crédito registró un cobro").toBe(antes);
  });

  test("el saldo del cliente resta el crédito una sola vez", async ({ request }) => {
    const c = await ctx(request);
    const e = await despachado(request, c, marca(), { cantidad: 4, precio: 25 });
    const credito = await creditoEmitido(request, c, e, 1);
    const saldo = await get(request, c, `/sales/cxc/clientes/${credito.customer_id}/saldo`);
    // Documentos 100, crédito 25 aplicado entero al emitirse: quedan 75.
    expect(Number(saldo.documents)).toBe(100);
    expect(Number(saldo.credits)).toBe(25);
    expect(Number(saldo.credit_available)).toBe(0);
    expect(Number(saldo.balance), "el crédito se restó dos veces").toBe(75);
  });

  test("el estado de cuenta reconstruye la cronología", async ({ request }) => {
    const c = await ctx(request);
    const e = await despachado(request, c, marca(), { cantidad: 4, precio: 25 });
    const credito = await creditoEmitido(request, c, e, 2);
    const estado = await get(request, c,
      `/sales/cxc/clientes/${credito.customer_id}/estado-de-cuenta`);
    const tipos = (estado.entries as Array<{ type: string }>).map((x) => x.type);
    expect(tipos).toContain("DOCUMENT");
    expect(tipos).toContain("CREDIT_NOTE");
    expect(tipos).toContain("APPLICATION");
  });

  test("la interfaz muestra el estado de cuenta y el dominio lo confirma", async ({ page, request }) => {
    const c = await ctx(request);
    const e = await despachado(request, c, marca(), { cantidad: 4, precio: 25 });
    const credito = await creditoEmitido(request, c, e, 1);

    await uiLogin(page);
    await page.locator('nav a[href="/ventas/estado-de-cuenta"]').first().click();
    await page.waitForURL((u) => u.pathname === "/ventas/estado-de-cuenta", { timeout: 15_000 });
    await expect(page.getByRole("heading", { name: "Estado de cuenta", level: 1 })).toBeVisible();

    await page.getByLabel("Cliente").selectOption(credito.customer_id as string);
    await expect(page.getByRole("heading", { name: "Saldo" })).toBeVisible({ timeout: 15_000 });
    await expect(page.getByText("Cronología")).toBeVisible();

    // El dominio dice lo mismo que la pantalla, y la pantalla no lo calculó.
    const saldo = await get(request, c, `/sales/cxc/clientes/${credito.customer_id}/saldo`);
    expect(Number(saldo.balance)).toBe(75);

    // Y no hay reembolso en ninguna parte de la interfaz.
    expect(await page.getByRole("button", { name: /reembols/i }).count()).toBe(0);
  });
});
