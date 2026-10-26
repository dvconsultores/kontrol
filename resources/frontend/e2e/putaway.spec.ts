/**
 * E2E del put-away — Spec 022.
 *
 * Frontend real → API real → backend real → PostgreSQL real.
 *
 * La regla de esta suite: **un aviso de éxito no prueba nada**. Cada acción de
 * interfaz se comprueba después contra el dominio —movimiento, saldos, reservas,
 * disponible— porque lo que la Spec promete no es que la pantalla diga que sí,
 * sino que la mercancía quede ubicada sin dejar de poder venderse.
 */
import { type APIRequestContext, type Page } from "@playwright/test";
import { expect, test, entrar, sesionApi } from "./helpers/sesion";

import { laReservaDe, reservasDeProducto } from "./helpers/reservas";

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

async function get(request: APIRequestContext, c: Ctx, ruta: string) {
  const r = await request.get(`${API}${ruta}`, { headers: c.headers });
  expect(r.ok(), `${ruta}: ${r.status()}`).toBeTruthy();
  return r.json();
}

/** Todas las listas de preparación de la empresa: el listado se pagina (`page_size` ≤ 100), así que se recorren las páginas hasta reunir `total`. */
async function todasLasListasDePreparacion(request: APIRequestContext, c: Ctx): Promise<unknown[]> {
  const todas: unknown[] = [];
  for (let page = 1; ; page += 1) {
    const pagina = (await get(request, c, `/sales/pick-lists?page=${page}&page_size=100`)) as { items: unknown[]; total: number };
    todas.push(...pagina.items);
    if (todas.length >= pagina.total || pagina.items.length === 0) return todas;
  }
}

/** Un identificador distinto por caso: los navegadores comparten base. */
const marca = (): string =>
  `${Date.now().toString(36)}${Math.random().toString(36).slice(2, 6)}`.toUpperCase();

type Escenario = {
  producto: string;
  almacen: string;
  almacenAjeno: string;
  activa: string;
  inactiva: string;
  otroAlmacen: string;
};

/**
 * Deja existencia disponible **sin ubicar** y cuatro ubicaciones: una válida,
 * una inactiva y una de otro almacén. La cuarta —de otra empresa— no se puede
 * montar aquí porque esta base tiene una sola; la certifica la suite
 * multiempresa del backend, que sí tiene dos tenants y tres empresas.
 */
async function escenario(
  request: APIRequestContext,
  c: Ctx,
  m: string,
  cantidad = 100,
): Promise<Escenario> {
  // Almacén propio por caso: la base es compartida entre navegadores y casos,
  // y la lista de pendientes acumula lo de corridas anteriores. Con un almacén
  // recién creado, lo que la pantalla muestra es exactamente lo de esta prueba.
  const propio = await post(request, c, "/organization/warehouses", {
    company_id: c.company, code: `W1-${m}`, name: `Almacén ${m}`,
    warehouse_type: "PHYSICAL", status: "ACTIVE",
  });
  const almacen = propio.id as string;
  // El «otro almacén» es el que ya existía: no hace falta crear un segundo por
  // caso, y crear de más ensucia la base que comparten los tres navegadores.
  const existentes = await get(request, c, "/organization/warehouses?limit=100");
  const segundo = (existentes.items as Array<{ id: string }>).find((w) => w.id !== almacen)!;
  const producto = await post(request, c, "/maestros/catalogos/items", {
    code: `PA-${m}`, name: `Artículo ${m}`, item_type: "PRODUCT", status: "ACTIVE",
  });
  const activa = await post(request, c, "/organization/locations", {
    warehouse_id: almacen, code: `OK-${m}`, name: "Rack válido", sequence: 1,
  });
  const inactiva = await post(request, c, "/organization/locations", {
    warehouse_id: almacen, code: `NO-${m}`, name: "Rack inactivo", sequence: 2,
  });
  await post(request, c, `/organization/locations/${inactiva.id}/deactivate`, {});
  const otroAlmacen = await post(request, c, "/organization/locations", {
    warehouse_id: segundo.id, code: `W2-${m}`, name: "Rack de otro almacén", sequence: 1,
  });

  // Existencia disponible sin ubicar, por el motor real. El tipo de entrada
  // puede no existir todavía en una base recién creada: se crea si falta, y así
  // la fixture no depende de qué haya sembrado otra corrida.
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
    warehouse_id: almacen, product_id: producto.id,
    movement_type_id: entrada.id, quantity: cantidad,
  });

  return {
    producto: producto.id as string,
    almacen,
    almacenAjeno: segundo.id as string,
    activa: activa.id as string,
    inactiva: inactiva.id as string,
    otroAlmacen: otroAlmacen.id as string,
  };
}

/** Saldos por ubicación y estado, leídos del dominio. */
async function saldos(
  request: APIRequestContext,
  c: Ctx,
  producto: string,
): Promise<Record<string, number>> {
  const r = await get(request, c, `/inventory/balances?product_id=${producto}`);
  const out: Record<string, number> = {};
  for (const b of r.items as Array<{ location_id: string | null; state: string; qty_on_hand: string }>) {
    out[`${b.location_id ?? "SIN_UBICAR"}|${b.state}`] = Number(b.qty_on_hand);
  }
  return out;
}

async function movimientos(request: APIRequestContext, c: Ctx, producto: string) {
  const r = await get(request, c, `/inventory/movements?product_id=${producto}`);
  return r.items as Array<{
    id: string; source_location_id: string | null; target_location_id: string | null;
    base_quantity: string; source_state: string | null; target_state: string | null;
  }>;
}

async function uiLogin(page: Page): Promise<void> {
  await entrar(page, USER, { tenant: TENANT });
  await expect(page).toHaveURL(/\/$/, { timeout: 20_000 });
}

async function irAPutAway(page: Page): Promise<void> {
  await page.locator('nav a[href="/inventario/putaway"]').first().click();
  await page.waitForURL((u) => u.pathname === "/inventario/putaway", { timeout: 15_000 });
  await expect(page.getByRole("heading", { name: "Put-away" })).toBeVisible();
  await page.waitForLoadState("networkidle");
}

test.describe("Spec 022 — put-away", () => {
  // ------------------------------------------------------------- camino feliz
  test("el operario ubica la mercancía y el dominio lo confirma", async ({ page, request }) => {
    const c = await ctx(request);
    const m = marca();
    const e = await escenario(request, c, m);

    const antes = await saldos(request, c, e.producto);
    expect(antes[`SIN_UBICAR|DISPONIBLE`]).toBe(100);

    await uiLogin(page);
    await irAPutAway(page);
    await page.getByLabel(/Almacén/).selectOption(e.almacen);
    // La fila **de este producto**: la base es compartida y la tabla muestra
    // pendientes de otros casos.
    const fila = page.getByRole("row").filter({ hasText: e.producto.slice(0, 8) });
    await expect(fila).toHaveCount(1, { timeout: 15_000 });
    await fila.getByRole("button", { name: "Elegir ubicación" }).click();

    // La ubicación la elige la persona: no viene preseleccionada.
    const selector = page.getByLabel(/Ubicación de destino/);
    await expect(selector).toHaveValue("", { timeout: 15_000 });
    // Solo la válida es candidata: ni la inactiva ni la de otro almacén.
    await expect(selector.locator(`option[value="${e.activa}"]`)).toHaveCount(1);
    await expect(selector.locator(`option[value="${e.inactiva}"]`)).toHaveCount(0);
    await expect(selector.locator(`option[value="${e.otroAlmacen}"]`)).toHaveCount(0);

    await selector.selectOption(e.activa);
    await page.getByLabel(/Cantidad/).fill("100");
    await page.getByRole("button", { name: "Confirmar ubicación" }).click();

    // La prueba no es el aviso: es que **esta** mercancía deje de estar
    // pendiente. La tabla puede seguir mostrando otras: la base es compartida.
    await expect(page.getByRole("row").filter({ hasText: e.producto.slice(0, 8) }))
      .toHaveCount(0, { timeout: 20_000 });

    const despues = await saldos(request, c, e.producto);
    expect(despues[`SIN_UBICAR|DISPONIBLE`] ?? 0).toBe(0);
    expect(despues[`${e.activa}|DISPONIBLE`]).toBe(100);
    expect(Object.values(despues).reduce((a, b) => a + b, 0)).toBe(100);

    const movs = await movimientos(request, c, e.producto);
    const traslado = movs.find((x) => x.target_location_id === e.activa);
    expect(traslado, "no se registró el movimiento de traslado").toBeTruthy();
    expect(traslado!.source_location_id).toBeNull();
    expect(Number(traslado!.base_quantity)).toBe(100);
    expect(traslado!.source_state).toBe("DISPONIBLE");
    expect(traslado!.target_state).toBe("DISPONIBLE");
  });

  // --------------------------------------------- el backend es la autoridad
  test("una ubicación inactiva se rechaza aunque se fuerce por API", async ({ request }) => {
    const c = await ctx(request);
    const e = await escenario(request, c, marca());
    const r = await request.post(`${API}/inventory/putaway`, {
      headers: c.headers,
      data: {
        product_id: e.producto, warehouse_id: e.almacen,
        target_location_id: e.inactiva, quantity: "10",
      },
    });
    expect(r.status(), await r.text()).toBe(409);
    expect((await r.json()).code).toBe("LOCATION_NOT_ELIGIBLE");
    const s = await saldos(request, c, e.producto);
    expect(s[`SIN_UBICAR|DISPONIBLE`]).toBe(100);
  });

  test("una ubicación de otro almacén se rechaza aunque se fuerce por API", async ({ request }) => {
    const c = await ctx(request);
    const e = await escenario(request, c, marca());
    const r = await request.post(`${API}/inventory/putaway`, {
      headers: c.headers,
      data: {
        product_id: e.producto, warehouse_id: e.almacen,
        target_location_id: e.otroAlmacen, quantity: "10",
      },
    });
    expect(r.status(), await r.text()).toBe(409);
    expect((await r.json()).code).toBe("LOCATION_OTHER_WAREHOUSE");
    const s = await saldos(request, c, e.producto);
    expect(s[`SIN_UBICAR|DISPONIBLE`]).toBe(100);
  });

  // --------------------------------------------------------------- TOCTOU
  test("una ubicación desactivada después de listarla ya no sirve", async ({ request }) => {
    const c = await ctx(request);
    const e = await escenario(request, c, marca());

    // El operario la ve como candidata…
    const candidatas = await get(request, c, `/inventory/putaway/ubicaciones?warehouse_id=${e.almacen}`);
    expect((candidatas.items as Array<{ id: string }>).map((x) => x.id)).toContain(e.activa);

    // …y entre que la ve y confirma, alguien la desactiva.
    await post(request, c, `/organization/locations/${e.activa}/deactivate`, {});

    const r = await request.post(`${API}/inventory/putaway`, {
      headers: c.headers,
      data: {
        product_id: e.producto, warehouse_id: e.almacen,
        target_location_id: e.activa, quantity: "100",
      },
    });
    expect(r.status(), "se aceptó una ubicación desactivada tras listarla").toBe(409);
    expect((await r.json()).code).toBe("LOCATION_NOT_ELIGIBLE");

    const s = await saldos(request, c, e.producto);
    expect(s[`SIN_UBICAR|DISPONIBLE`]).toBe(100);
    expect(s[`${e.activa}|DISPONIBLE`] ?? 0).toBe(0);
  });

  // -------------------------------------------------------- doble envío
  test("dos envíos del mismo put-away no duplican el traslado", async ({ request }) => {
    const c = await ctx(request);
    const e = await escenario(request, c, marca());
    const cuerpo = {
      product_id: e.producto, warehouse_id: e.almacen,
      target_location_id: e.activa, quantity: "100",
    };
    const [a, b] = await Promise.all([
      request.post(`${API}/inventory/putaway`, { headers: c.headers, data: cuerpo }),
      request.post(`${API}/inventory/putaway`, { headers: c.headers, data: cuerpo }),
    ]);
    const exitos = [a, b].filter((r) => r.ok()).length;
    expect(exitos, "las dos peticiones movieron existencia").toBe(1);

    const s = await saldos(request, c, e.producto);
    expect(s[`${e.activa}|DISPONIBLE`]).toBe(100);
    expect(s[`SIN_UBICAR|DISPONIBLE`] ?? 0).toBe(0);
    expect(Object.values(s).reduce((x, y) => x + y, 0)).toBe(100);
  });

  // ------------------------------------------- la invariante 100 / 30 / 70
  test("ubicar no cambia lo reservado ni lo disponible del almacén", async ({ request }) => {
    const c = await ctx(request);
    const e = await escenario(request, c, marca());

    await post(request, c, "/inventory/reservations", {
      product_id: e.producto, warehouse_id: e.almacen, quantity: 30,
      source_document: `E2E-${e.producto.slice(0, 8)}`,
    });
    const reservaAntes = await laReservaDe(request, c.headers, e.producto);

    await post(request, c, "/inventory/putaway", {
      product_id: e.producto, warehouse_id: e.almacen,
      target_location_id: e.activa, quantity: "100",
    });

    const s = await saldos(request, c, e.producto);
    expect(s[`${e.activa}|DISPONIBLE`]).toBe(100);
    expect(s[`SIN_UBICAR|DISPONIBLE`] ?? 0).toBe(0);

    // El compromiso sigue en el ancla, y el disponible del almacén no se movió.
    const r = await get(request, c, `/inventory/balances?product_id=${e.producto}`);
    const reservado = (r.items as Array<{ qty_reserved: string }>)
      .reduce((acc, b) => acc + Number(b.qty_reserved), 0);
    expect(reservado, "el compromiso se perdió al ubicar").toBe(30);

    // Se comprueba la reserva del escenario, no cuántas hay en la empresa: el
    // conjunto es compartido y crece mientras la suite corre, así que contarlo
    // afirmaba «nadie más reservó mientras yo ubicaba», que no es lo que esta
    // prueba quiere decir ni depende del código que prueba.
    const reservaDespues = await laReservaDe(request, c.headers, e.producto);
    expect(reservaDespues.id, "ubicar cambió la reserva por otra").toBe(reservaAntes.id);
    expect(reservaDespues.status, "ubicar cambió el estado de la reserva").toBe(reservaAntes.status);
    expect(Number(reservaDespues.quantity), "ubicar cambió la cantidad reservada")
      .toBe(Number(reservaAntes.quantity));
    expect(reservaDespues.warehouse_id, "ubicar movió la reserva de almacén")
      .toBe(reservaAntes.warehouse_id);
  });

  test("la mercancía ubicada sigue pudiéndose reservar", async ({ request }) => {
    const c = await ctx(request);
    const e = await escenario(request, c, marca());
    await post(request, c, "/inventory/putaway", {
      product_id: e.producto, warehouse_id: e.almacen,
      target_location_id: e.activa, quantity: "100",
    });

    // Es la frase que bloqueó la Spec un ciclo entero: ubicar no puede volver
    // invendible la mercancía.
    const r = await request.post(`${API}/inventory/reservations`, {
      headers: c.headers,
      data: {
        product_id: e.producto, warehouse_id: e.almacen, quantity: 30,
        source_document: `E2E-POST-${e.producto.slice(0, 8)}`,
      },
    });
    expect([200, 201], `reservar tras ubicar: ${r.status()} ${await r.text()}`)
      .toContain(r.status());

    const saldo = await get(request, c, `/inventory/balances?product_id=${e.producto}`);
    const reservado = (saldo.items as Array<{ qty_reserved: string }>)
      .reduce((acc, b) => acc + Number(b.qty_reserved), 0);
    expect(reservado).toBe(30);
  });

  // ------------------------------------------------------------ la capacidad
  test("una capacidad menor que la cantidad no impide ubicar", async ({ request }) => {
    const c = await ctx(request);
    const m = marca();
    const e = await escenario(request, c, m);
    const pequena = await post(request, c, "/organization/locations", {
      warehouse_id: e.almacen, code: `CAP-${m}`, name: "Rack pequeño", sequence: 3,
      capacity_units: 5, capacity_uom: "CAJAS",
    });

    const candidatas = await get(request, c, `/inventory/putaway/ubicaciones?warehouse_id=${e.almacen}`);
    const fila = (candidatas.items as Array<{ id: string; capacity: { enforced: boolean } }>)
      .find((x) => x.id === pequena.id);
    expect(fila!.capacity.enforced, "la capacidad se declaró aplicable").toBe(false);

    await post(request, c, "/inventory/putaway", {
      product_id: e.producto, warehouse_id: e.almacen,
      target_location_id: pequena.id, quantity: "100",
    });
    const s = await saldos(request, c, e.producto);
    expect(s[`${pequena.id}|DISPONIBLE`]).toBe(100);
  });

  // ------------------------------------------------------------ la frontera
  test("ubicar no crea nada de picking", async ({ request }) => {
    const c = await ctx(request);
    const e = await escenario(request, c, marca());
    // La ruta de listas de preparación ya existe de antes; lo que no puede
    // existir es un artefacto **nuevo** creado por ubicar mercancía. Se miran las
    // listas del almacén de este escenario y no las de toda la empresa: otras
    // suites crean las suyas a la vez, y contarlas es medir lo ajeno.
    const delAlmacen = async (): Promise<unknown[]> =>
      ((await todasLasListasDePreparacion(request, c)) as { warehouse_id: string }[])
        .filter((x) => x.warehouse_id === e.almacen);
    expect(await delAlmacen(), "el almacén del escenario ya tenía listas de preparación").toEqual([]);

    await post(request, c, "/inventory/putaway", {
      product_id: e.producto, warehouse_id: e.almacen,
      target_location_id: e.activa, quantity: "100",
    });

    expect(
      await delAlmacen(),
      "ubicar creó una lista de preparación: eso es de la Spec 031",
    ).toEqual([]);
    // Y la reserva de este escenario no quedó atada a una ubicación. Se mira la
    // propia y no el conjunto de la empresa: lo que se comprueba es la forma de
    // la reserva que esta prueba creó.
    for (const x of await reservasDeProducto(request, c.headers, e.producto)) {
      expect(Object.keys(x)).not.toContain("location_id");
    }
  });
});
