/**
 * E2E de la cola y la ruta de picking — Spec 031.
 *
 * Frontend real → API real → backend real → PostgreSQL real.
 *
 * La regla de esta suite es la misma que la del put-away: **un aviso de éxito
 * no prueba nada**. Cada acción de interfaz se comprueba después contra el
 * dominio —cola, plan, recorrido, estado del pedido, reserva, saldos— porque lo
 * que la Spec promete no es que la pantalla diga que sí, sino que el plan diga
 * de dónde se recoge sin mover una sola unidad.
 */
import { expect, test, type APIRequestContext, type Page } from "@playwright/test";

import { reservasDePedido } from "./helpers/reservas";

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

type Escenario = {
  producto: string;
  almacen: string;
  l1: string;
  l2: string;
  otroAlmacen: string;
  pedido: string;
  pedidoCode: string;
  linea: string;
  plan: string;
};

/**
 * Un pedido liberado con 70 reservadas y existencia repartida entre dos
 * ubicaciones: `L1` con 40 y `L2` con 60. Ninguna tiene las 70, que es
 * exactamente el caso que obliga a dividir.
 */
async function escenario(request: APIRequestContext, c: Ctx, m: string): Promise<Escenario> {
  const propio = await post(request, c, "/organization/warehouses", {
    company_id: c.company, code: `WP-${m}`, name: `Almacén picking ${m}`,
    warehouse_type: "PHYSICAL", status: "ACTIVE",
  });
  const almacen = propio.id as string;
  const existentes = await get(request, c, "/organization/warehouses?limit=500");
  const segundo = (existentes.items as Array<{ id: string }>).find((w) => w.id !== almacen)!;

  const producto = await post(request, c, "/maestros/catalogos/items", {
    code: `PP-${m}`, name: `Artículo ${m}`, item_type: "PRODUCT", status: "ACTIVE",
  });
  const l1 = await post(request, c, "/organization/locations", {
    warehouse_id: almacen, code: `A1-${m}`, name: "Primera del recorrido", sequence: 1,
  });
  const l2 = await post(request, c, "/organization/locations", {
    warehouse_id: almacen, code: `B2-${m}`, name: "Segunda del recorrido", sequence: 2,
  });
  const otroAlmacen = await post(request, c, "/organization/locations", {
    warehouse_id: segundo.id, code: `WX-${m}`, name: "Rack de otro almacén", sequence: 1,
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
    warehouse_id: almacen, product_id: producto.id, movement_type_id: entrada.id, quantity: 100,
  });
  await post(request, c, "/inventory/putaway", {
    warehouse_id: almacen, product_id: producto.id, target_location_id: l1.id, quantity: 40,
  });
  await post(request, c, "/inventory/putaway", {
    warehouse_id: almacen, product_id: producto.id, target_location_id: l2.id, quantity: 60,
  });

  const cliente = await post(request, c, "/maestros/terceros", {
    code: `CL-${m}`, name: `Cliente ${m}`, roles: ["CLIENTE"],
  });
  const pedido = await post(request, c, "/sales/orders", {
    code: `OVP-${m}`, customer_id: cliente.id, currency: "VED", warehouse_id: almacen,
  });
  const linea = await post(request, c, `/sales/orders/${pedido.id}/lines`, {
    product_id: producto.id, quantity: 70, unit_price: 10,
  });
  const emitido = await post(request, c, `/sales/orders/${pedido.id}/submit`, {});
  if (emitido.status !== "RELEASED") {
    await post(request, c, `/sales/orders/${pedido.id}/release`, {});
  }

  const plan = await post(request, c, "/sales/pick-lists", {
    code: `PICK-${m}`, order_id: pedido.id, warehouse_id: almacen,
  });

  return {
    producto: producto.id as string, almacen, l1: l1.id as string, l2: l2.id as string,
    otroAlmacen: otroAlmacen.id as string, pedido: pedido.id as string,
    pedidoCode: pedido.code as string, linea: linea.id as string, plan: plan.id as string,
  };
}

async function saldos(request: APIRequestContext, c: Ctx, producto: string) {
  const r = await get(request, c, `/inventory/balances?product_id=${producto}`);
  const out: Record<string, number> = {};
  for (const b of r.items as Array<{
    location_id: string | null; state: string; qty_on_hand: string; qty_reserved: string;
  }>) {
    out[`${b.location_id ?? "SIN_UBICAR"}|${b.state}`] = Number(b.qty_on_hand);
    out[`RES|${b.location_id ?? "SIN_UBICAR"}`] = Number(b.qty_reserved);
  }
  return out;
}

async function uiLogin(page: Page): Promise<void> {
  await page.goto("/login");
  await page.getByLabel(/Empresa \(código\)/).fill(TENANT);
  await page.getByLabel(/Usuario/).fill(USER);
  await page.getByLabel(/Contraseña/).fill(PASSWORD);
  await page.getByRole("button", { name: "Iniciar sesión" }).click();
  await expect(page).toHaveURL(/\/$/, { timeout: 20_000 });
}

async function irAPreparacion(page: Page, almacen?: string): Promise<void> {
  await page.locator('nav a[href="/ventas/preparacion"]').first().click();
  await page.waitForURL((u) => u.pathname === "/ventas/preparacion", { timeout: 15_000 });
  await expect(page.getByRole("heading", { name: "Preparación de pedidos" })).toBeVisible();
  if (almacen) {
    await page.getByLabel("Almacén").selectOption(almacen);
  }
  await page.waitForLoadState("networkidle");
}

test.describe("Spec 031 — cola y ruta de picking", () => {
  test("el pedido liberado aparece en la cola con su puesto", async ({ page, request }) => {
    const c = await ctx(request);
    const e = await escenario(request, c, marca());

    const cola = await get(request, c, "/sales/picking/cola");
    expect(cola.order_by, "el contrato no declara su orden").toBe("released_at ASC, id ASC");
    const fila = (cola.items as Array<{ order_id: string; position: number }>).find(
      (x) => x.order_id === e.pedido,
    );
    expect(fila, "el pedido liberado no entró en la cola").toBeTruthy();

    await uiLogin(page);
    await irAPreparacion(page, e.almacen);
    await expect(page.getByRole("cell", { name: e.pedidoCode })).toBeVisible();
  });

  test("la interfaz reparte entre dos ubicaciones y el recorrido sale en orden", async ({
    page,
    request,
  }) => {
    const c = await ctx(request);
    const e = await escenario(request, c, marca());

    await post(request, c, `/sales/picking/${e.plan}/asignaciones`, {
      order_line_id: e.linea, location_id: e.l2, quantity: 30,
    });
    await post(request, c, `/sales/picking/${e.plan}/asignaciones`, {
      order_line_id: e.linea, location_id: e.l1, quantity: 40,
    });

    const plan = await get(request, c, `/sales/picking/${e.plan}`);
    expect(Number(plan.remaining_base_quantity)).toBe(0);
    expect(plan.confirmable).toBe(true);
    // El recorrido va por orden físico: `L1` tiene secuencia 1 y se asignó la
    // segunda, así que si saliera por orden de asignación empezaría por `L2`.
    expect((plan.route as Array<{ location_id: string }>).map((r) => r.location_id)).toEqual([
      e.l1,
      e.l2,
    ]);

    await uiLogin(page);
    await irAPreparacion(page, e.almacen);
    await page.getByRole("row", { name: new RegExp(e.pedidoCode) })
      .getByRole("button", { name: "Planificar" }).click();
    await page.waitForLoadState("networkidle");
    await expect(page.getByText("1. Ubicación", { exact: false }).first()).toBeVisible();
  });

  test("no se confirma con remanente, y el dominio lo impide", async ({ page, request }) => {
    const c = await ctx(request);
    const e = await escenario(request, c, marca());

    await post(request, c, `/sales/picking/${e.plan}/asignaciones`, {
      order_line_id: e.linea, location_id: e.l1, quantity: 40,
    });
    const plan = await get(request, c, `/sales/picking/${e.plan}`);
    expect(Number(plan.remaining_base_quantity)).toBe(30);
    expect(plan.confirmable).toBe(false);

    const r = await postCrudo(request, c, `/sales/picking/${e.plan}/confirmar`, {});
    expect(r.status(), "un plan incompleto se pudo confirmar").toBe(409);
    expect((await r.json()).code).toBe("PICKING_PLAN_INCOMPLETE");

    const pedido = await get(request, c, `/sales/orders/${e.pedido}`);
    expect(pedido.status, "el pedido salió de la cola sin plan ejecutable").toBe("RELEASED");

    await uiLogin(page);
    await irAPreparacion(page, e.almacen);
    await page.getByRole("row", { name: new RegExp(e.pedidoCode) })
      .getByRole("button", { name: "Planificar" }).click();
    await page.waitForLoadState("networkidle");
    await expect(page.getByRole("button", { name: "Confirmar plan" })).toBeDisabled();
  });

  test("confirmar completo mueve el pedido a preparación y lo saca de la cola", async ({
    request,
  }) => {
    const c = await ctx(request);
    const e = await escenario(request, c, marca());

    for (const [loc, qty] of [[e.l1, 40], [e.l2, 30]] as const) {
      await post(request, c, `/sales/picking/${e.plan}/asignaciones`, {
        order_line_id: e.linea, location_id: loc, quantity: qty,
      });
    }
    const plan = await post(request, c, `/sales/picking/${e.plan}/confirmar`, {});
    expect(plan.status).toBe("CONFIRMED");
    expect(plan.confirmed_at).toBeTruthy();

    const pedido = await get(request, c, `/sales/orders/${e.pedido}`);
    expect(pedido.status).toBe("PREPARING");
    const cola = await get(request, c, "/sales/picking/cola");
    expect(
      (cola.items as Array<{ order_id: string }>).some((x) => x.order_id === e.pedido),
      "un pedido ya planificado sigue en la cola",
    ).toBe(false);
  });

  test("cancelar un plan confirmado devuelve el pedido a la cola sin tocar la reserva", async ({
    request,
  }) => {
    const c = await ctx(request);
    const e = await escenario(request, c, marca());

    for (const [loc, qty] of [[e.l1, 40], [e.l2, 30]] as const) {
      await post(request, c, `/sales/picking/${e.plan}/asignaciones`, {
        order_line_id: e.linea, location_id: loc, quantity: qty,
      });
    }
    await post(request, c, `/sales/picking/${e.plan}/confirmar`, {});
    // Se pedía `?source_order_id=`, que el servidor no declara y por tanto
    // ignora en silencio: la respuesta traía las reservas de toda la empresa y
    // lo que se contaba eran las ajenas. El pedido se identifica por el campo
    // que el servidor sí publica.
    const activasAntes = (await reservasDePedido(request, c.headers, e.pedido))
      .filter((r) => r.status === "ACTIVE").length;

    const plan = await post(request, c, `/sales/picking/${e.plan}/cancelar`, {
      reason: "el cliente cambió la fecha de entrega",
    });
    expect(plan.status).toBe("CANCELLED");
    expect(plan.status_reason).toContain("cliente");

    const pedido = await get(request, c, `/sales/orders/${e.pedido}`);
    expect(pedido.status, "el pedido quedó varado en preparación").toBe("RELEASED");

    const activas = (await reservasDePedido(request, c.headers, e.pedido))
      .filter((r) => r.status === "ACTIVE").length;
    expect(activas, "cancelar el plan liberó la reserva comercial").toBe(activasAntes);
    expect(activasAntes, "el escenario no dejó ninguna reserva viva que comprobar")
      .toBeGreaterThan(0);

    const cola = await get(request, c, "/sales/picking/cola");
    expect(
      (cola.items as Array<{ order_id: string }>).some((x) => x.order_id === e.pedido),
      "el pedido no volvió a la cola",
    ).toBe(true);
  });

  test("planificar no mueve una sola unidad", async ({ request }) => {
    const c = await ctx(request);
    const e = await escenario(request, c, marca());
    const antes = await saldos(request, c, e.producto);
    const movsAntes = (await get(request, c, `/inventory/movements?product_id=${e.producto}`))
      .items.length;

    for (const [loc, qty] of [[e.l1, 40], [e.l2, 30]] as const) {
      await post(request, c, `/sales/picking/${e.plan}/asignaciones`, {
        order_line_id: e.linea, location_id: loc, quantity: qty,
      });
    }
    await post(request, c, `/sales/picking/${e.plan}/confirmar`, {});
    await post(request, c, `/sales/picking/${e.plan}/cancelar`, { reason: "prueba de deriva" });

    expect(await saldos(request, c, e.producto), "planificar movió inventario").toEqual(antes);
    expect(
      (await get(request, c, `/inventory/movements?product_id=${e.producto}`)).items.length,
      "planificar generó un movimiento",
    ).toBe(movsAntes);
  });

  test("no se asigna más de lo reservado ni desde otro almacén", async ({ request }) => {
    const c = await ctx(request);
    const e = await escenario(request, c, marca());

    const exceso = await postCrudo(request, c, `/sales/picking/${e.plan}/asignaciones`, {
      order_line_id: e.linea, location_id: e.l2, quantity: 71,
    });
    expect(exceso.status()).toBe(409);
    expect((await exceso.json()).code).toBe("PICKING_OVER_RESERVATION");

    const ajena = await postCrudo(request, c, `/sales/picking/${e.plan}/asignaciones`, {
      order_line_id: e.linea, location_id: e.otroAlmacen, quantity: 10,
    });
    expect(ajena.status(), "se asignó una ubicación de otro almacén").toBe(409);
    expect((await ajena.json()).code).toBe("LOCATION_OTHER_WAREHOUSE");

    expect(Number((await get(request, c, `/sales/picking/${e.plan}`)).remaining_base_quantity))
      .toBe(70);
  });

  test("invalidar exige que la precondición esté perdida", async ({ request }) => {
    const c = await ctx(request);
    const e = await escenario(request, c, marca());

    const sano = await postCrudo(request, c, `/sales/picking/${e.plan}/invalidar`, {
      reason: "sin causa aguas arriba",
    });
    expect(sano.status(), "se invalidó un plan válido").toBe(409);
    expect((await sano.json()).code).toBe("PICKING_PLAN_STILL_VALID");
  });
});
