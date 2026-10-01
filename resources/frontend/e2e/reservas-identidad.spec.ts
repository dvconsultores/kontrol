/**
 * Identificar la reserva propia en una base compartida (SPEC054 · SPEC023).
 *
 * La base del E2E es compartida a propósito y las reservas son historia: no se
 * borran. Por eso `GET /inventory/reservations` devuelve un conjunto que crece
 * mientras la suite corre —en un mismo ciclo pasó de 330 a 369— y por eso dos
 * suites que afirmaban sobre su tamaño fallaban cuando otra prueba reservaba
 * en el momento equivocado.
 *
 * Estas pruebas fijan la diferencia entre las dos afirmaciones: «hay las mismas
 * reservas que antes», que depende de lo que hagan los demás, y «mi reserva
 * sigue siendo la que era», que es lo que un escenario quiere comprobar.
 */
import { expect, test, type APIRequestContext } from "@playwright/test";

import { laReservaDe, reservasDePedido, reservasDeProducto } from "./helpers/reservas";

const API = process.env.KONTROL_E2E_API ?? "http://127.0.0.1:8000/api/v1";
const TENANT = process.env.KONTROL_E2E_TENANT ?? "DEMO";
const USER = process.env.KONTROL_E2E_USER ?? "admin";
const PASSWORD = process.env.KONTROL_E2E_PASSWORD ?? "";

async function post(request: APIRequestContext, c: Ctx, ruta: string, data: unknown) {
  const r = await request.post(`${API}${ruta}`, { headers: c.headers, data });
  expect(r.ok(), `${ruta}: ${r.status()} ${await r.text()}`).toBeTruthy();
  return r.json();
}

async function get(request: APIRequestContext, c: Ctx, ruta: string) {
  const r = await request.get(`${API}${ruta}`, { headers: c.headers });
  expect(r.ok(), `${ruta}: ${r.status()}`).toBeTruthy();
  return r.json();
}

const marca = (): string =>
  `${Date.now().toString(36)}${Math.random().toString(36).slice(2, 6)}`.toUpperCase();

interface Ctx { company: string; headers: Record<string, string> }

async function ctx(request: APIRequestContext): Promise<Ctx> {
  const login = await request.post(`${API}/auth/login`, {
    data: { tenant_code: TENANT, username: USER, password: PASSWORD },
  });
  expect(login.ok(), `login: ${login.status()}`).toBeTruthy();
  const token = (await login.json()).access_token as string;
  const empresas = await request.get(`${API}/organization/companies`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  const lista = await empresas.json();
  const empresa = lista.items[0].id as string;
  return { company: empresa,
           headers: { Authorization: `Bearer ${token}`, "X-Kontrol-Company": empresa } };
}

/**
 * Un producto propio, con existencias, en un almacén propio.
 *
 * Cada caso monta el suyo por la misma razón que `putaway`: la base es
 * compartida entre casos y navegadores, y un producto que ya arrastra reservas
 * de otra suite no sirve para comprobar «la mía es la única de este producto».
 * Con producto propio, lo que se mide es exactamente lo de esta prueba.
 */
async function productoConSaldo(request: APIRequestContext, c: Ctx, m: string, cantidad = 10) {
  const almacen = await post(request, c, "/organization/warehouses", {
    company_id: c.company, code: `WR-${m}`, name: `Almacén ${m}`,
    warehouse_type: "PHYSICAL", status: "ACTIVE",
  });
  const producto = await post(request, c, "/maestros/catalogos/items", {
    code: `RI-${m}`, name: `Artículo ${m}`, item_type: "PRODUCT", status: "ACTIVE",
  });
  const tipos = await get(request, c, "/inventory/movement-types");
  const entrada = ((tipos.items ?? tipos) as Array<{ id: string; code: string }>).find(
    (x) => x.code === "ENTRADA_RECEPCION",
  );
  expect(entrada, "la base del E2E no tiene el tipo de movimiento ENTRADA_RECEPCION").toBeTruthy();
  await post(request, c, "/inventory/movements", {
    warehouse_id: almacen.id, product_id: producto.id,
    movement_type_id: entrada!.id, quantity: cantidad,
  });
  return { product_id: producto.id as string, warehouse_id: almacen.id as string };
}

async function reservar(request: APIRequestContext, c: Ctx,
                        p: { product_id: string; warehouse_id: string }, doc: string) {
  const r = await request.post(`${API}/inventory/reservations`, {
    headers: c.headers,
    data: { product_id: p.product_id, warehouse_id: p.warehouse_id, quantity: 1,
            source_document: doc },
  });
  expect(r.ok(), `reservar: ${r.status()} ${await r.text()}`).toBeTruthy();
  return (await r.json()) as { id: string };
}

/** El tamaño del conjunto compartido. Se mide aquí para demostrar que se mueve. */
async function cuantasHayEnLaEmpresa(request: APIRequestContext, c: Ctx): Promise<number> {
  const r = await request.get(`${API}/inventory/reservations`, { headers: c.headers });
  expect(r.ok()).toBeTruthy();
  return ((await r.json()).items as unknown[]).length;
}

test("el escenario identifica su reserva aunque aparezcan otras a la vez", async ({ request }) => {
  const c = await ctx(request);
  const m = marca();
  const mio = await productoConSaldo(request, c, `A${m}`);
  const ajeno = await productoConSaldo(request, c, `B${m}`);

  const mia = await reservar(request, c, mio, `IDENT-MIA-${m}`);
  const antes = await cuantasHayEnLaEmpresa(request, c);

  // Lo que ocurre en la suite completa: otro escenario reserva mientras tanto.
  await reservar(request, c, ajeno, `IDENT-AJENA-${m}`);

  const despues = await cuantasHayEnLaEmpresa(request, c);
  expect(despues,
    "el conjunto de reservas de la empresa es compartido: contarlo no puede ser una invariante",
  ).toBeGreaterThan(antes);

  // Y aun así lo propio sigue siendo identificable, exactamente.
  const encontrada = await laReservaDe(request, c.headers, mio.product_id);
  expect(encontrada.id).toBe(mia.id);
  expect(encontrada.source_document).toBe(`IDENT-MIA-${m}`);
  expect(encontrada.warehouse_id).toBe(mio.warehouse_id);
  expect(encontrada.status).toBe("ACTIVE");
});

test("una reserva manual no se confunde con la de ningún pedido", async ({ request }) => {
  const c = await ctx(request);
  const m = marca();
  const mio = await productoConSaldo(request, c, `M${m}`);
  await reservar(request, c, mio, `IDENT-MANUAL-${m}`);

  const suya = await laReservaDe(request, c.headers, mio.product_id);
  expect(suya.source_type, "una reserva creada a mano no nace atada a un pedido").toBe("MANUAL");
  expect(suya.source_order_id).toBeNull();

  // Y buscar por un pedido inexistente no devuelve nada: el filtro del cliente
  // mira el campo publicado, no el tamaño de la lista.
  expect(await reservasDePedido(request, c.headers,
    "00000000-0000-0000-0000-000000000000")).toHaveLength(0);
});

test("el filtro por producto lo aplica el servidor, no la prueba", async ({ request }) => {
  const c = await ctx(request);
  const m = marca();
  const mio = await productoConSaldo(request, c, `S${m}`);
  const ajeno = await productoConSaldo(request, c, `T${m}`);
  await reservar(request, c, mio, `IDENT-SRV-${m}`);
  await reservar(request, c, ajeno, `IDENT-SRV-AJENA-${m}`);

  const suyas = await reservasDeProducto(request, c.headers, mio.product_id);
  expect(suyas.length).toBeGreaterThan(0);
  expect(suyas.every((r) => r.product_id === mio.product_id),
    "el servidor devolvió reservas de otro producto").toBe(true);
  expect(suyas.some((r) => r.product_id === ajeno.product_id)).toBe(false);
});

test("con dos reservas del mismo producto el ayudante se niega a elegir", async ({ request }) => {
  // Elegir por posición dentro de un conjunto que no se controla es la misma
  // clase de error que contar el total: parece que funciona hasta que el orden
  // cambia. Si un escenario acaba con dos reservas del mismo producto, lo que
  // hay es una prueba mal planteada, y debe verse ahí y no tres aserciones
  // después.
  const c = await ctx(request);
  const m = marca();
  const mio = await productoConSaldo(request, c, `D${m}`);
  await reservar(request, c, mio, `IDENT-DOBLE-1-${m}`);
  await reservar(request, c, mio, `IDENT-DOBLE-2-${m}`);

  expect(await reservasDeProducto(request, c.headers, mio.product_id)).toHaveLength(2);
  await expect(laReservaDe(request, c.headers, mio.product_id))
    .rejects.toThrow(/se esperaba una sola reserva/);
});
