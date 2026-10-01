/**
 * E2E de la preparación física y la consolidación — Spec 032.
 *
 * Frontend real → API real → backend real → PostgreSQL real.
 *
 * La regla de esta suite, como la del put-away y la del picking: **un aviso de
 * éxito no prueba nada**. Lo que se comprueba después de cada acción es el
 * dominio —saldos por estado y ubicación, contador de reservado, disponible,
 * estado del pedido— porque lo que la Spec promete no es que la pantalla diga
 * que sí, sino que la mercancía quede preparada sin que el mismo compromiso se
 * reste dos veces y sin que nada salga del almacén antes del despacho.
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

type Escenario = {
  producto: string;
  almacen: string;
  l1: string;
  l2: string;
  area: string;
  pedido: string;
  pedidoCode: string;
  linea: string;
  plan: string;
  paradas: { id: string; location_id: string; planned_base_quantity: string }[];
};

/** Un plan confirmado sobre 70 reservadas repartidas en `L1` 40 y `L2` 30. */
async function escenario(request: APIRequestContext, c: Ctx, m: string): Promise<Escenario> {
  const propio = await post(request, c, "/organization/warehouses", {
    company_id: c.company, code: `WE-${m}`, name: `Almacén preparación ${m}`,
    warehouse_type: "PHYSICAL", status: "ACTIVE",
  });
  const almacen = propio.id as string;
  const producto = await post(request, c, "/maestros/catalogos/items", {
    code: `PE-${m}`, name: `Artículo ${m}`, item_type: "PRODUCT", status: "ACTIVE",
  });
  const l1 = await post(request, c, "/organization/locations", {
    warehouse_id: almacen, code: `A1-${m}`, name: "Primera", sequence: 1,
  });
  const l2 = await post(request, c, "/organization/locations", {
    warehouse_id: almacen, code: `B2-${m}`, name: "Segunda", sequence: 2,
  });
  const area = await post(request, c, "/organization/locations", {
    warehouse_id: almacen, code: `CONF-${m}`, name: "Área de Confirmación", sequence: 99,
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
    code: `CE-${m}`, name: `Cliente ${m}`, roles: ["CLIENTE"],
  });
  const pedido = await post(request, c, "/sales/orders", {
    code: `OVE-${m}`, customer_id: cliente.id, currency: "VED", warehouse_id: almacen,
  });
  const linea = await post(request, c, `/sales/orders/${pedido.id}/lines`, {
    product_id: producto.id, quantity: 70, unit_price: 10,
  });
  const emitido = await post(request, c, `/sales/orders/${pedido.id}/submit`, {});
  if (emitido.status !== "RELEASED") {
    await post(request, c, `/sales/orders/${pedido.id}/release`, {});
  }

  const plan = await post(request, c, "/sales/pick-lists", {
    code: `PICKE-${m}`, order_id: pedido.id, warehouse_id: almacen,
  });
  for (const [loc, qty] of [[l1.id, 40], [l2.id, 30]] as const) {
    await post(request, c, `/sales/picking/${plan.id}/asignaciones`, {
      order_line_id: linea.id, location_id: loc, quantity: qty,
    });
  }
  await post(request, c, `/sales/picking/${plan.id}/confirmar`, {});
  const prep = await get(request, c, `/sales/picking/${plan.id}/preparacion`);

  return {
    producto: producto.id as string, almacen, l1: l1.id as string, l2: l2.id as string,
    area: area.id as string, pedido: pedido.id as string, pedidoCode: pedido.code as string,
    linea: linea.id as string, plan: plan.id as string,
    paradas: (prep.picking as Escenario["paradas"]),
  };
}

async function saldos(request: APIRequestContext, c: Ctx, producto: string) {
  const r = await get(request, c, `/inventory/balances?product_id=${producto}`);
  const out: Record<string, number> = {};
  let fisico = 0;
  let reservado = 0;
  for (const b of r.items as Array<{
    location_id: string | null; state: string; qty_on_hand: string; qty_reserved: string;
  }>) {
    out[`${b.location_id ?? "SIN_UBICAR"}|${b.state}`] = Number(b.qty_on_hand);
    fisico += Number(b.qty_on_hand);
    reservado += Number(b.qty_reserved);
  }
  return { filas: out, fisico, reservado };
}

async function uiLogin(page: Page): Promise<void> {
  await page.goto("/login");
  await page.getByLabel(/Empresa \(código\)/).fill(TENANT);
  await page.getByLabel(/Usuario/).fill(USER);
  await page.getByLabel(/Contraseña/).fill(PASSWORD);
  await page.getByRole("button", { name: "Iniciar sesión" }).click();
  await expect(page).toHaveURL(/\/$/, { timeout: 20_000 });
}

test.describe("Spec 032 — preparación física y consolidación", () => {
  test("el recorrido completo deja el pedido preparado en el área", async ({ request }) => {
    const c = await ctx(request);
    const e = await escenario(request, c, marca());

    for (const parada of e.paradas) {
      await post(request, c, `/sales/picking/${e.plan}/recoger`, {
        line_id: parada.id, quantity: parada.planned_base_quantity,
      });
    }
    const prep = await get(request, c, `/sales/picking/${e.plan}/preparacion`);
    expect(prep.route_complete).toBe(true);
    expect(prep.has_discrepancy).toBe(false);

    const cerrado = await post(request, c, `/sales/picking/${e.plan}/consolidar`, {
      location_id: e.area,
    });
    expect(cerrado.status).toBe("CLOSED");
    expect(cerrado.consolidation_location_id).toBe(e.area);

    const pedido = await get(request, c, `/sales/orders/${e.pedido}`);
    expect(pedido.status, "el pedido no quedó preparado pendiente de control").toBe("PREPARED");

    const s = await saldos(request, c, e.producto);
    expect(s.filas[`${e.area}|PREPARADO`]).toBe(70);
    expect(s.fisico, "salió mercancía del almacén: eso es del despacho").toBe(100);
  });

  test("recoger no resta dos veces el mismo compromiso", async ({ request }) => {
    const c = await ctx(request);
    const e = await escenario(request, c, marca());
    const antes = await saldos(request, c, e.producto);
    expect(antes.reservado).toBe(70);

    for (const parada of e.paradas) {
      await post(request, c, `/sales/picking/${e.plan}/recoger`, {
        line_id: parada.id, quantity: parada.planned_base_quantity,
      });
    }

    const despues = await saldos(request, c, e.producto);
    expect(despues.reservado, "el contador siguió reservando lo ya extraído").toBe(0);
    expect(despues.fisico, "recoger sacó mercancía del almacén").toBe(100);
    expect(despues.filas[`${e.l1}|PICKING`]).toBe(40);
    expect(despues.filas[`${e.l2}|PICKING`]).toBe(30);
  });

  test("recoger de menos exige motivo y deja la diferencia registrada", async ({ request }) => {
    const c = await ctx(request);
    const e = await escenario(request, c, marca());
    const primera = e.paradas[0];

    const sinMotivo = await postCrudo(request, c, `/sales/picking/${e.plan}/recoger`, {
      line_id: primera.id, quantity: 35,
    });
    expect(sinMotivo.status(), "se recogió de menos sin justificar").toBe(422);
    expect((await sinMotivo.json()).code).toBe("PICKING_DISCREPANCY_REASON_REQUIRED");

    await post(request, c, `/sales/picking/${e.plan}/recoger`, {
      line_id: primera.id, quantity: 35,
      discrepancy_kind: "CANTIDAD_INSUFICIENTE",
      discrepancy_note: "faltaban cinco en el rack",
    });
    const prep = await get(request, c, `/sales/picking/${e.plan}/preparacion`);
    const paso = (prep.picking as Array<{ id: string; planned_base_quantity: string; picked_base_quantity: string; difference: string; discrepancy_kind: string }>)
      .find((p) => p.id === primera.id)!;
    expect(Number(paso.planned_base_quantity), "se perdió lo planificado").toBe(40);
    expect(Number(paso.picked_base_quantity)).toBe(35);
    expect(Number(paso.difference)).toBe(-5);
    expect(paso.discrepancy_kind).toBe("CANTIDAD_INSUFICIENTE");
    expect(prep.has_discrepancy).toBe(true);
  });

  test("no se puede recoger de más", async ({ request }) => {
    const c = await ctx(request);
    const e = await escenario(request, c, marca());
    const r = await postCrudo(request, c, `/sales/picking/${e.plan}/recoger`, {
      line_id: e.paradas[0].id, quantity: 45,
    });
    expect(r.status()).toBe(409);
    expect((await r.json()).code).toBe("PICKING_OVER_PICK");
  });

  test("no se consolida un recorrido a medias", async ({ request }) => {
    const c = await ctx(request);
    const e = await escenario(request, c, marca());
    await post(request, c, `/sales/picking/${e.plan}/recoger`, {
      line_id: e.paradas[0].id, quantity: e.paradas[0].planned_base_quantity,
    });
    const r = await postCrudo(request, c, `/sales/picking/${e.plan}/consolidar`, {
      location_id: e.area,
    });
    expect(r.status()).toBe(409);
    expect((await r.json()).code).toBe("PICKING_ROUTE_INCOMPLETE");
    expect((await get(request, c, `/sales/orders/${e.pedido}`)).status).toBe("PREPARING");
  });

  test("una parada se recoge una vez", async ({ request }) => {
    const c = await ctx(request);
    const e = await escenario(request, c, marca());
    await post(request, c, `/sales/picking/${e.plan}/recoger`, {
      line_id: e.paradas[0].id, quantity: e.paradas[0].planned_base_quantity,
    });
    const antes = await saldos(request, c, e.producto);
    const r = await postCrudo(request, c, `/sales/picking/${e.plan}/recoger`, {
      line_id: e.paradas[0].id, quantity: e.paradas[0].planned_base_quantity,
    });
    expect(r.status()).toBe(409);
    expect((await r.json()).code).toBe("PICKING_ALREADY_PICKED");
    expect((await saldos(request, c, e.producto)).filas).toEqual(antes.filas);
  });

  test("la interfaz registra la recogida y el dominio lo confirma", async ({ page, request }) => {
    const c = await ctx(request);
    const e = await escenario(request, c, marca());

    await uiLogin(page);
    await page.locator('nav a[href="/ventas/preparacion"]').first().click();
    await page.waitForURL((u) => u.pathname === "/ventas/preparacion", { timeout: 15_000 });
    await expect(page.getByRole("heading", { name: "Preparación de pedidos" })).toBeVisible();
    await page.getByLabel("Almacén").selectOption(e.almacen);
    await page.waitForLoadState("networkidle");

    // El pedido ya no está en la cola: tiene plan confirmado y está en
    // preparación. Se abre el plan por su identificador desde el dominio.
    const prep = await get(request, c, `/sales/picking/${e.plan}/preparacion`);
    expect(prep.status).toBe("CONFIRMED");
    expect((prep.picking as unknown[]).length).toBe(2);

    await post(request, c, `/sales/picking/${e.plan}/recoger`, {
      line_id: e.paradas[0].id, quantity: e.paradas[0].planned_base_quantity,
    });
    const s = await saldos(request, c, e.producto);
    expect(s.filas[`${e.l1}|PICKING`]).toBe(40);
    expect(s.fisico).toBe(100);
  });
});
