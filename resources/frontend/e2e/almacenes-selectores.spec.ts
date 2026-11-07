/**
 * E2E de los selectores de almacén — ALMACENES-DESPLEGABLES-TRUNCADOS, Spec 008.
 *
 * Frontend real → API real → backend real → PostgreSQL real. La base de datos llega al
 * resultado solo por la API y la interfaz: ningún estado final se escribe a mano.
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

/** Crea almacenes hasta dejar el marcado más allá de la primera página. */
async function almacenFueraDeLaPrimeraPagina(request: APIRequestContext, c: Ctx, m: string): Promise<string> {
  const r = await request.get(`${API}/organization/warehouses?limit=1`, { headers: c.headers });
  const { total } = (await r.json()) as { total: number };
  for (let i = total; i < 51; i += 1) {
    await post(request, c, "/organization/warehouses", {
      company_id: c.company, code: `SEL-${m}-${i}`, name: `Relleno ${i}`,
      warehouse_type: "PHYSICAL", status: "ACTIVE",
    });
  }
  const ultimo = await post(request, c, "/organization/warehouses", {
    company_id: c.company, code: `ZZZ-${m}`, name: `Último ${m}`,
    warehouse_type: "PHYSICAL", status: "ACTIVE",
  });
  return ultimo.id as string;
}

test.describe("Selectores de almacén", () => {
  test("la operadora elige un almacén más allá del 50 en Ajustes", async ({ page, request }) => {
    const c = await ctx(request);
    const m = marca();
    const almacen = await almacenFueraDeLaPrimeraPagina(request, c, m);

    await uiLogin(page);
    await page.locator('nav a[href="/inventario/ajustes"]').first().click();
    await page.waitForURL((u) => u.pathname === "/inventario/ajustes", { timeout: 15_000 });
    const selector = page.getByLabel(/^Almacén/);
    await expect(selector.locator(`option[value="${almacen}"]`)).toHaveCount(1, { timeout: 15_000 });
    await selector.selectOption(almacen);
    await expect(selector).toHaveValue(almacen);
  });
});
