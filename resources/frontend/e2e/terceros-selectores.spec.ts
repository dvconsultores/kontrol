/**
 * E2E de los selectores de terceros — TERCEROS-SELECTORES-PRIMERA-PAGINA.
 *
 * Frontend real → API real → backend real → PostgreSQL real. La base de datos llega al
 * resultado solo por la API y la interfaz: ningún estado final se escribe a mano.
 *
 * La operadora elige un cliente o proveedor fuera de la primera página (más de 20 activos)
 * en Órdenes de venta y Órdenes de compra, y se comprueba la integridad de roles
 * (multirol, rol requerido, inactivo) por UI y por API.
 */
import { type APIRequestContext, type Page } from "@playwright/test";
import { expect, test, entrar, sesionApi } from "./helpers/sesion";

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
async function uiLogin(page: Page): Promise<void> {
  await entrar(page, USER, { tenant: TENANT });
  await expect(page).toHaveURL(/\/$/, { timeout: 20_000 });
}

const marca = (): string => Math.random().toString(36).slice(2, 8).toUpperCase();

async function contarActivos(
  request: APIRequestContext,
  c: Ctx,
  role: "CLIENTE" | "PROVEEDOR",
): Promise<number> {
  const r = await request.get(
    `${API}/maestros/terceros?role=${role}&status=ACTIVE&page_size=1`,
    { headers: c.headers },
  );
  expect([200], `${role}: ${r.status()} ${await r.text()}`).toContain(r.status());
  const body = await r.json();
  return Number(body.total) || 0;
}

type Tercero = { id: string; code: string; name: string };

/**
 * Crea terceros de relleno hasta tener al menos 21 activos con el rol indicado y, después,
 * el tercero marcado. El orden del servidor es created_at, así que el último creado queda
 * fuera de la primera página de 20. Devuelve id, código y nombre del marcado.
 */
async function terceroFueraDeLaPrimeraPagina(
  request: APIRequestContext,
  c: Ctx,
  m: string,
  roles: ("CLIENTE" | "PROVEEDOR")[],
  prefijo: string,
): Promise<Tercero> {
  const role = roles[0];
  const objetivo = 21;
  let activos = await contarActivos(request, c, role);
  let i = 0;
  while (activos < objetivo - 1) {
    i += 1;
    const suffix = `${m}-${String(i).padStart(3, "0")}`;
    await post(request, c, "/maestros/terceros", {
      code: `${prefijo}-${suffix}`,
      name: `Relleno ${suffix}`,
      roles,
    });
    activos += 1;
  }
  const code = `${prefijo}-${m}`;
  const name = `Zeta ${m}`;
  const creado = await post(request, c, "/maestros/terceros", { code, name, roles });
  return { id: creado.id as string, code, name };
}

async function crearTercero(
  request: APIRequestContext,
  c: Ctx,
  code: string,
  name: string,
  roles: ("CLIENTE" | "PROVEEDOR")[],
): Promise<Tercero> {
  const creado = await post(request, c, "/maestros/terceros", { code, name, roles });
  return { id: creado.id as string, code, name };
}

async function desactivar(request: APIRequestContext, c: Ctx, id: string): Promise<void> {
  await post(request, c, `/maestros/terceros/${id}/deactivate`, {});
}

async function buscarYSeleccionar(
  page: Page,
  etiqueta: RegExp,
  tercero: Tercero,
): Promise<void> {
  const combo = page.getByRole("combobox", { name: etiqueta });
  await combo.click();
  await combo.pressSequentially(tercero.code);
  await page.getByRole("option", { name: new RegExp(tercero.code) }).click();
  await expect(combo).toHaveValue(`${tercero.code} · ${tercero.name}`);
}

async function crearOrdenVenta(page: Page, codigoOrden: string, tercero: Tercero): Promise<void> {
  await page.locator('nav a[href="/ventas/ordenes"]').first().click();
  await page.waitForURL(/\/ventas\/ordenes/);
  const codigo = page.getByLabel(/^Código/);
  await codigo.fill(codigoOrden);
  await buscarYSeleccionar(page, /^Cliente/, tercero);
  await codigo
    .locator("xpath=ancestor::form")
    .getByRole("button", { name: "Crear" })
    .click();
  await expect(page.getByRole("cell", { name: codigoOrden })).toBeVisible();
}

async function crearOrdenCompra(
  page: Page,
  codigoOrden: string,
  tercero: Tercero,
): Promise<void> {
  await page.locator('nav a[href="/compras/ordenes"]').first().click();
  await page.waitForURL(/\/compras\/ordenes/);
  const codigo = page.getByLabel(/^Código/);
  await codigo.fill(codigoOrden);
  await buscarYSeleccionar(page, /^Proveedor/, tercero);
  await codigo
    .locator("xpath=ancestor::form")
    .getByRole("button", { name: "Crear" })
    .click();
  await expect(page.getByRole("cell", { name: codigoOrden })).toBeVisible();
}

async function sinResultados(page: Page, etiqueta: RegExp, consulta: string): Promise<void> {
  const combo = page.getByRole("combobox", { name: etiqueta });
  await combo.click();
  await combo.pressSequentially(consulta);
  await expect(page.getByText("Sin resultados")).toBeVisible();
}

test.describe("Terceros — selectores fuera de la primera página e integridad de roles", () => {
  test("E-01 venta: cliente fuera de la primera página aparece en la tabla", async ({
    page,
    request,
  }) => {
    const c = await ctx(request);
    const m = marca();
    const tercero = await terceroFueraDeLaPrimeraPagina(
      request,
      c,
      m,
      ["CLIENTE"],
      `TCL-E01${m}`,
    );
    await uiLogin(page);
    await crearOrdenVenta(page, `OV-${m}`, tercero);
  });

  test("E-02 compra: proveedor fuera de la primera página aparece en la tabla", async ({
    page,
    request,
  }) => {
    const c = await ctx(request);
    const m = marca();
    const tercero = await terceroFueraDeLaPrimeraPagina(
      request,
      c,
      m,
      ["PROVEEDOR"],
      `TPR-E02${m}`,
    );
    await uiLogin(page);
    await crearOrdenCompra(page, `OC-${m}`, tercero);
  });

  test("E-03 multirol: TMU se ofrece como cliente y como proveedor", async ({
    page,
    request,
  }) => {
    const c = await ctx(request);
    const m = marca();
    const tercero = await terceroFueraDeLaPrimeraPagina(
      request,
      c,
      m,
      ["CLIENTE", "PROVEEDOR"],
      `TMU-E03${m}`,
    );
    await uiLogin(page);

    await page.locator('nav a[href="/ventas/ordenes"]').first().click();
    await page.waitForURL(/\/ventas\/ordenes/);
    await buscarYSeleccionar(page, /^Cliente/, tercero);

    await page.locator('nav a[href="/compras/ordenes"]').first().click();
    await page.waitForURL(/\/compras\/ordenes/);
    await buscarYSeleccionar(page, /^Proveedor/, tercero);
  });

  test("E-04 PROVEEDOR-only no se ofrece como cliente", async ({ page, request }) => {
    const c = await ctx(request);
    const m = marca();
    const tercero = await crearTercero(
      request,
      c,
      `TPR-E04${m}`,
      `Zeta ${m}`,
      ["PROVEEDOR"],
    );
    await uiLogin(page);

    await page.locator('nav a[href="/ventas/ordenes"]').first().click();
    await page.waitForURL(/\/ventas\/ordenes/);
    await sinResultados(page, /^Cliente/, tercero.code);

    const r = await request.post(`${API}/sales/quotes`, {
      headers: c.headers,
      data: { code: `COT-E04-${m}`, customer_id: tercero.id, currency: "VED" },
    });
    expect(r.status()).toBe(409);
    const body = await r.json();
    expect(body.code).toBe("PARTY_ROLE_REQUIRED");
  });

  test("E-05 CLIENTE-only no se ofrece como proveedor", async ({ page, request }) => {
    const c = await ctx(request);
    const m = marca();
    const tercero = await crearTercero(
      request,
      c,
      `TCL-E05${m}`,
      `Zeta ${m}`,
      ["CLIENTE"],
    );
    await uiLogin(page);

    await page.locator('nav a[href="/compras/ordenes"]').first().click();
    await page.waitForURL(/\/compras\/ordenes/);
    await sinResultados(page, /^Proveedor/, tercero.code);

    const r = await request.post(`${API}/purchasing/orders`, {
      headers: c.headers,
      data: { code: `OC-E05-${m}`, supplier_id: tercero.id, currency: "VED" },
    });
    expect(r.status()).toBe(409);
    const body = await r.json();
    expect(body.code).toBe("PARTY_ROLE_REQUIRED");
  });

  test("E-06 inactivo: un cliente desactivado no se ofrece ni se acepta", async ({
    page,
    request,
  }) => {
    const c = await ctx(request);
    const m = marca();
    const tercero = await crearTercero(
      request,
      c,
      `TCL-E06${m}`,
      `Zeta ${m}`,
      ["CLIENTE"],
    );
    await desactivar(request, c, tercero.id);
    await uiLogin(page);

    await page.locator('nav a[href="/ventas/ordenes"]').first().click();
    await page.waitForURL(/\/ventas\/ordenes/);
    await sinResultados(page, /^Cliente/, tercero.code);

    const r = await request.post(`${API}/sales/quotes`, {
      headers: c.headers,
      data: { code: `COT-E06-${m}`, customer_id: tercero.id, currency: "VED" },
    });
    expect(r.status()).toBe(409);
    const body = await r.json();
    expect(body.code).toBe("PARTY_INACTIVE");
  });
});
