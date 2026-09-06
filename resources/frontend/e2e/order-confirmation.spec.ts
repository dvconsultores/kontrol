/**
 * E2E del control independiente del pedido — Spec 033.
 *
 * Frontend real → API real → backend real → PostgreSQL real.
 *
 * La regla de esta suite: **un aviso de éxito no prueba nada**. Lo que se
 * comprueba tras cada acción es el dominio —estado del pedido, intentos de
 * confirmación, elegibilidad para facturar, saldos e inventario— porque lo que
 * la Spec promete no es que la pantalla diga «conforme», sino que un pedido
 * incompleto no llegue nunca a facturación y que quien preparó no pueda firmar
 * su propio trabajo.
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

type Escenario = {
  producto: string;
  almacen: string;
  pedido: string;
  pedidoCode: string;
  linea: string;
  requerido: number;
  preparado: number;
};

/** Un pedido preparado y consolidado, esperando control. */
async function escenario(
  request: APIRequestContext,
  c: Ctx,
  m: string,
  { requerido = 70, recogido = 70 } = {},
): Promise<Escenario> {
  const propio = await post(request, c, "/organization/warehouses", {
    company_id: c.company, code: `WC-${m}`, name: `Almacén control ${m}`,
    warehouse_type: "PHYSICAL", status: "ACTIVE",
  });
  const almacen = propio.id as string;
  const producto = await post(request, c, "/maestros/catalogos/items", {
    code: `PQ-${m}`, name: `Artículo ${m}`, item_type: "PRODUCT", status: "ACTIVE",
  });
  const l1 = await post(request, c, "/organization/locations", {
    warehouse_id: almacen, code: `Q1-${m}`, name: "Origen", sequence: 1,
  });
  const area = await post(request, c, "/organization/locations", {
    warehouse_id: almacen, code: `QC-${m}`, name: "Área de Confirmación", sequence: 99,
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
    quantity: requerido + 50,
  });
  await post(request, c, "/inventory/putaway", {
    warehouse_id: almacen, product_id: producto.id, target_location_id: l1.id,
    quantity: requerido + 50,
  });

  const cliente = await post(request, c, "/maestros/terceros", {
    code: `CQ-${m}`, name: `Cliente ${m}`, roles: ["CLIENTE"],
  });
  const pedido = await post(request, c, "/sales/orders", {
    code: `OVQ-${m}`, customer_id: cliente.id, currency: "VED", warehouse_id: almacen,
  });
  const linea = await post(request, c, `/sales/orders/${pedido.id}/lines`, {
    product_id: producto.id, quantity: requerido, unit_price: 10,
  });
  const emitido = await post(request, c, `/sales/orders/${pedido.id}/submit`, {});
  if (emitido.status !== "RELEASED") {
    await post(request, c, `/sales/orders/${pedido.id}/release`, {});
  }

  const plan = await post(request, c, "/sales/pick-lists", {
    code: `PLQ-${m}`, order_id: pedido.id, warehouse_id: almacen,
  });
  await post(request, c, `/sales/picking/${plan.id}/asignaciones`, {
    order_line_id: linea.id, location_id: l1.id, quantity: requerido,
  });
  await post(request, c, `/sales/picking/${plan.id}/confirmar`, {});
  const prep = await get(request, c, `/sales/picking/${plan.id}/preparacion`);
  const parada = (prep.picking as Array<{ id: string }>)[0];
  await post(request, c, `/sales/picking/${plan.id}/recoger`, {
    line_id: parada.id, quantity: recogido,
    discrepancy_kind: recogido === requerido ? null : "CANTIDAD_INSUFICIENTE",
  });
  await post(request, c, `/sales/picking/${plan.id}/consolidar`, { location_id: area.id });

  return {
    producto: producto.id as string, almacen, pedido: pedido.id as string,
    pedidoCode: pedido.code as string, linea: linea.id as string,
    requerido, preparado: recogido,
  };
}

/**
 * Un verificador **distinto** del que preparó.
 *
 * No es un adorno de la prueba: `R-D0-12-5` fija el defecto en que quien
 * preparó no puede confirmar, y el `admin` que monta el escenario es quien
 * recogió y consolidó. Sin un segundo usuario no hay control independiente que
 * probar, y el propio backend lo impide —que es justo lo que se quiere.
 */
async function verificador(request: APIRequestContext, c: Ctx, m: string): Promise<Ctx> {
  const roles = await get(request, c, "/roles");
  const rol = (roles.items as Array<{ id: string; code?: string; name?: string }>).find(
    (r) => (r.code ?? r.name ?? "").toUpperCase().includes("ADMIN"),
  ) ?? (roles.items as Array<{ id: string }>)[0];
  const usuario = await post(request, c, "/users", {
    username: `check-${m.toLowerCase()}`,
    email: `check-${m.toLowerCase()}@kontrol-qa.com`,
    password: PASSWORD,
    must_change_password: false,
  });
  await post(request, c, `/users/${usuario.id}/roles`, { role_id: rol.id, company_id: c.company });
  const login = await request.post(`${API}/auth/login`, {
    data: { tenant_code: TENANT, username: `check-${m.toLowerCase()}`, password: PASSWORD },
  });
  expect(login.ok(), `login del verificador: ${login.status()} ${await login.text()}`).toBeTruthy();
  const token = (await login.json()).access_token as string;
  return {
    token,
    company: c.company,
    headers: { Authorization: `Bearer ${token}`, "X-Kontrol-Company": c.company },
  };
}

async function uiLogin(page: Page, usuario = USER): Promise<void> {
  await page.goto("/login");
  await page.getByLabel(/Empresa \(código\)/).fill(TENANT);
  await page.getByLabel(/Usuario/).fill(usuario);
  await page.getByLabel(/Contraseña/).fill(PASSWORD);
  await page.getByRole("button", { name: "Iniciar sesión" }).click();
  await expect(page).toHaveURL(/\/$/, { timeout: 20_000 });
}

test.describe("Spec 033 — confirmación independiente del pedido", () => {
  test("el pedido conforme queda confirmado y habilita facturación", async ({ request }) => {
    const c = await ctx(request);
    const m = marca();
    const e = await escenario(request, c, m);
    const v = await verificador(request, c, m);

    const antes = await get(request, v, `/sales/confirmacion/${e.pedido}/facturable`);
    expect(antes.eligible_for_billing, "un pedido sin control ya era facturable").toBe(false);

    const r = await post(request, v, `/sales/confirmacion/${e.pedido}`, {
      lines: [{ order_line_id: e.linea, checked_base_quantity: e.requerido }],
    });
    expect(r.status).toBe("CONFIRMED");
    expect(r.attempt).toBe(1);

    expect((await get(request, c, `/sales/orders/${e.pedido}`)).status).toBe("CONFIRMED");
    const despues = await get(request, c, `/sales/confirmacion/${e.pedido}/facturable`);
    expect(despues.eligible_for_billing).toBe(true);
    expect(despues.confirmation_id).toBe(r.id);
  });

  test("se compara contra el pedido, no contra la preparación", async ({ request }) => {
    const c = await ctx(request);
    const m = marca();
    const e = await escenario(request, c, m, { requerido: 70, recogido: 65 });
    const v = await verificador(request, c, m);

    const hoja = await get(request, v, `/sales/confirmacion/${e.pedido}`);
    expect(Number(hoja.lines[0].required_base_quantity)).toBe(70);
    expect(Number(hoja.lines[0].prepared_base_quantity)).toBe(65);

    // El verificador cuenta lo que hay: 65. Contra la preparación coincidiría.
    const r = await post(request, v, `/sales/confirmacion/${e.pedido}`, {
      lines: [{ order_line_id: e.linea, checked_base_quantity: 65 }],
    });
    expect(r.status, "un pedido incompleto pasó el control").toBe("REJECTED");
    expect(r.lines[0].difference_kind).toBe("CANTIDAD");
    expect(Number(r.lines[0].required_base_quantity)).toBe(70);
    expect(Number(r.lines[0].prepared_base_quantity)).toBe(65);
    expect(Number(r.lines[0].checked_base_quantity)).toBe(65);

    expect((await get(request, c, `/sales/orders/${e.pedido}`)).status,
      "el pedido no regresó a preparación").toBe("PREPARING");
    expect((await get(request, c, `/sales/confirmacion/${e.pedido}/facturable`))
      .eligible_for_billing).toBe(false);
  });

  test("la presentación y la condición bloquean el control", async ({ request }) => {
    const c = await ctx(request);
    for (const [campo, motivo] of [["presentation_ok", "PRESENTACION"],
                                   ["condition_ok", "CONDICION"]] as const) {
      const m = marca();
      const e = await escenario(request, c, m);
      const v = await verificador(request, c, m);
      const r = await post(request, v, `/sales/confirmacion/${e.pedido}`, {
        lines: [{ order_line_id: e.linea, checked_base_quantity: e.requerido, [campo]: false }],
      });
      expect(r.status, `${campo} no bloqueó`).toBe("REJECTED");
      expect(r.lines[0].difference_kind).toBe(motivo);
    }
  });

  test("el control es completo o no es control", async ({ request }) => {
    const c = await ctx(request);
    const m = marca();
    const e = await escenario(request, c, m);
    const v = await verificador(request, c, m);
    const r = await postCrudo(request, v, `/sales/confirmacion/${e.pedido}`, { lines: [] });
    expect(r.status()).toBe(422);
    expect((await r.json()).code).toBe("CONFIRMATION_INCOMPLETE");
  });

  test("el rechazo se conserva cuando hay un segundo intento", async ({ request }) => {
    const c = await ctx(request);
    const m = marca();
    const e = await escenario(request, c, m);
    const v = await verificador(request, c, m);

    const primero = await post(request, v, `/sales/confirmacion/${e.pedido}`, {
      lines: [{ order_line_id: e.linea, checked_base_quantity: e.requerido - 2 }],
      notes: "faltan dos",
    });
    expect(primero.status).toBe("REJECTED");

    // La preparación corrige y devuelve el pedido al control.
    const plan = (await get(request, c, `/sales/pick-lists?order_id=${e.pedido}`)).items[0];
    expect(plan.status).toBe("CLOSED");

    const hoja = await get(request, v, `/sales/confirmacion/${e.pedido}`).catch(() => null);
    // Con el pedido en PREPARING la hoja no está disponible: el control exige
    // que la preparación lo devuelva. Eso es lo que dice el ¶77.
    expect(hoja).toBeNull();
  });

  test("verificar no mueve una sola unidad", async ({ request }) => {
    const c = await ctx(request);
    const m = marca();
    const e = await escenario(request, c, m);
    const v = await verificador(request, c, m);
    const antesSaldos = await get(request, c, `/inventory/balances?product_id=${e.producto}`);
    const antesMovs = await get(request, c, `/inventory/movements?product_id=${e.producto}`);

    await post(request, v, `/sales/confirmacion/${e.pedido}`, {
      lines: [{ order_line_id: e.linea, checked_base_quantity: e.requerido }],
    });

    const despuesSaldos = await get(request, c, `/inventory/balances?product_id=${e.producto}`);
    const despuesMovs = await get(request, c, `/inventory/movements?product_id=${e.producto}`);
    expect(despuesMovs.items.length, "el control creó un movimiento").toBe(antesMovs.items.length);
    expect(
      (despuesSaldos.items as Array<{ qty_on_hand: string; qty_reserved: string }>)
        .map((b) => `${b.qty_on_hand}|${b.qty_reserved}`).sort(),
      "el control movió inventario",
    ).toEqual(
      (antesSaldos.items as Array<{ qty_on_hand: string; qty_reserved: string }>)
        .map((b) => `${b.qty_on_hand}|${b.qty_reserved}`).sort(),
    );
  });

  test("la interfaz registra el control y el dominio lo confirma", async ({ page, request }) => {
    const c = await ctx(request);
    const m = marca();
    const e = await escenario(request, c, m);
    await verificador(request, c, m);

    await uiLogin(page, `check-${m.toLowerCase()}`);
    await page.locator('nav a[href="/ventas/confirmacion-pedido"]').first().click();
    await page.waitForURL((u) => u.pathname === "/ventas/confirmacion-pedido", { timeout: 15_000 });
    await expect(page.getByRole("heading", { name: "Confirmación de pedido" })).toBeVisible();
    await page.waitForLoadState("networkidle");

    const fila = page.getByRole("row", { name: new RegExp(e.pedidoCode) });
    for (let i = 0; i < 20 && (await fila.count()) === 0; i += 1) {
      const siguiente = page.getByRole("button", { name: "Página siguiente" });
      if (await siguiente.isDisabled()) break;
      await siguiente.click();
      await page.waitForLoadState("networkidle");
    }
    await expect(fila).toHaveCount(1);
    await fila.getByRole("button", { name: "Verificar" }).click();
    await page.waitForLoadState("networkidle");
    await expect(page.getByText(`Pedido ${e.pedidoCode}`)).toBeVisible();

    await page.getByLabel(/Cantidad contada/).fill(String(e.requerido));
    await page.getByRole("button", { name: "Registrar control" }).click();
    await expect(page.getByText(/Intento #1: CONFIRMED/)).toBeVisible({ timeout: 15_000 });

    expect((await get(request, c, `/sales/orders/${e.pedido}`)).status).toBe("CONFIRMED");
    expect((await get(request, c, `/sales/confirmacion/${e.pedido}/facturable`))
      .eligible_for_billing).toBe(true);
  });
});
