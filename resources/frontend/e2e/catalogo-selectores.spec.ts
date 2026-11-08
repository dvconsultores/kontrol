/**
 * E2E de los selectores de artículo — CATALOGO-SELECTORES-PRIMERA-PAGINA, Spec 002.
 *
 * Frontend real → API real → backend real → PostgreSQL real. La base de datos llega al
 * resultado solo por la API y la interfaz: ningún estado final se escribe a mano.
 *
 * La operadora elige un artículo fuera de la primera página (más de 20 activos) en
 * Órdenes de compra, Órdenes de venta y Movimientos de inventario.
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

/**
 * Crea artículos de relleno hasta tener al menos 21 activos y, después, un artículo
 * marcado cuyo nombre ordena al final ("Zeta ${m}") para que quede fuera de la primera
 * página de 20. Devuelve el código y el nombre del marcado.
 */
async function articuloFueraDeLaPrimeraPagina(
  request: APIRequestContext,
  c: Ctx,
  m: string,
): Promise<{ code: string; name: string }> {
  const r = await request.get(`${API}/maestros/catalogos/items/search?page_size=1`, {
    headers: c.headers,
  });
  const { total } = (await r.json()) as { total: number };
  for (let i = total; i < 21; i += 1) {
    await post(request, c, "/maestros/catalogos/items", {
      code: `RELL-${m}-${i}`,
      name: `Relleno ${i}`,
      item_type: "PRODUCT",
      status: "ACTIVE",
    });
  }
  const code = `CAT-${m}`;
  const name = `Zeta ${m}`;
  await post(request, c, "/maestros/catalogos/items", {
    code,
    name,
    item_type: "PRODUCT",
    status: "ACTIVE",
  });
  return { code, name };
}

async function crearServicio(
  request: APIRequestContext,
  c: Ctx,
  m: string,
): Promise<{ code: string; name: string }> {
  const code = `SRV-${m}`;
  const name = `Zeta servicio ${m}`;
  await post(request, c, "/maestros/catalogos/items", {
    code,
    name,
    item_type: "SERVICE",
    status: "ACTIVE",
  });
  return { code, name };
}

async function irA(page: Page, ruta: string): Promise<void> {
  await page.locator(`nav a[href="${ruta}"]`).first().click();
  await page.waitForURL((u) => u.pathname === ruta, { timeout: 15_000 });
}

async function elegirProducto(page: Page, code: string, name: string): Promise<void> {
  const selector = page.getByRole("combobox", { name: /^Producto/ });
  await selector.click();
  await selector.pressSequentially(code);
  await page.getByRole("option", { name: new RegExp(code) }).click();
  await expect(selector).toHaveValue(`${code} · ${name}`);
}

async function comprobarServicioElegible(page: Page, code: string, name: string): Promise<void> {
  const selector = page.getByRole("combobox", { name: /^Producto/ });
  await selector.click();
  await selector.fill(code);
  await page.getByRole("option", { name: new RegExp(code) }).click();
  await expect(selector).toHaveValue(`${code} · ${name}`);
}

test.describe("Selectores de artículo", () => {
  test("la operadora elige un producto más allá de la primera página en Órdenes de compra", async ({
    page,
    request,
  }) => {
    const c = await ctx(request);
    const m = marca();
    const articulo = await articuloFueraDeLaPrimeraPagina(request, c, m);
    const servicio = await crearServicio(request, c, m);

    await uiLogin(page);
    await irA(page, "/compras/ordenes");
    await elegirProducto(page, articulo.code, articulo.name);
    await comprobarServicioElegible(page, servicio.code, servicio.name);
  });

  test("la operadora elige un producto más allá de la primera página en Órdenes de venta", async ({
    page,
    request,
  }) => {
    const c = await ctx(request);
    const m = marca();
    const articulo = await articuloFueraDeLaPrimeraPagina(request, c, m);
    const servicio = await crearServicio(request, c, m);

    await uiLogin(page);
    await irA(page, "/ventas/ordenes");
    await elegirProducto(page, articulo.code, articulo.name);
    await comprobarServicioElegible(page, servicio.code, servicio.name);
  });

  test("la operadora elige un producto más allá de la primera página en Movimientos de inventario", async ({
    page,
    request,
  }) => {
    const c = await ctx(request);
    const m = marca();
    const articulo = await articuloFueraDeLaPrimeraPagina(request, c, m);
    const servicio = await crearServicio(request, c, m);

    const rServicio = await request.get(
      `${API}/maestros/catalogos/items/search?q=${servicio.code}`,
      { headers: c.headers },
    );
    expect(rServicio.status(), `servicio search: ${await rServicio.text()}`).toBe(200);
    const { total } = (await rServicio.json()) as { total: number };
    expect(total, "el servicio debe existir y ser buscable por API").toBe(1);

    await uiLogin(page);
    await irA(page, "/inventario/movimientos");
    await elegirProducto(page, articulo.code, articulo.name);

    const selector = page.getByRole("combobox", { name: /^Producto/ });
    await selector.click();
    await selector.fill(servicio.code);
    await expect(page.getByText("Sin resultados")).toBeVisible();
    await expect(page.getByRole("option", { name: new RegExp(servicio.code) })).toHaveCount(0);
  });
});
