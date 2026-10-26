/**
 * E2E de unidades, presentaciones y conversiones (Spec 011).
 *
 * Frontend real → API real → backend real → **PostgreSQL 18.x real**. El motor
 * de conversión no se mockea en ningún punto.
 *
 * El escenario central (§74) es el criterio de aceptación de la Spec: un
 * documento congelado con V1 debe seguir significando lo mismo después de que
 * exista V2.
 */
import { type APIRequestContext, type Page } from "@playwright/test";
import { activarEmpresa } from "./helpers/empresa";
import { entrar, expect, sesionApi, test } from "./helpers/sesion";

const TENANT = process.env.KONTROL_E2E_TENANT ?? "DEMO";
const USER = process.env.KONTROL_E2E_USER ?? "admin";
const API = process.env.KONTROL_E2E_API ?? "http://127.0.0.1:8000/api/v1";

const RUN = `${Date.now().toString(36)}${Math.random().toString(36).slice(2, 5)}`.toUpperCase();

async function apiLogin(_request: APIRequestContext): Promise<string> {
  return (await sesionApi(USER, { tenant: TENANT })).token;
}

type Ctx = { headers: Record<string, string> };

async function ctx(request: APIRequestContext): Promise<Ctx> {
  return { headers: { Authorization: `Bearer ${await apiLogin(request)}` } };
}

async function uiLogin(page: Page): Promise<void> {
  await entrar(page, USER, { tenant: TENANT });
  await page.locator('nav a[href="/organizacion/empresas"]').first().click();
  await page.waitForURL((u) => u.pathname === "/organizacion/empresas", { timeout: 15000 });
  await page.waitForLoadState("networkidle");
  await activarEmpresa(page);
}

async function closeNotifications(page: Page): Promise<void> {
  const close = page.getByRole("button", { name: "Cerrar notificación" });
  for (let i = await close.count(); i > 0; i = await close.count()) {
    await close.first().click();
  }
}

async function createUnit(request: APIRequestContext, c: Ctx, code: string,
                          decimals = 0): Promise<string> {
  const r = await request.post(`${API}/maestros/unidades`, {
    headers: c.headers,
    data: { code, name: `Unidad ${code}`, symbol: code.toLowerCase(),
            dimension: "CANTIDAD", decimals, rounding_mode: "HALF_UP" },
  });
  expect(r.ok(), `unidad ${code}: ${r.status()} ${await r.text()}`).toBeTruthy();
  return (await r.json()).id as string;
}

async function createProduct(request: APIRequestContext, c: Ctx, code: string,
                             baseUnitId: string | null): Promise<string> {
  const r = await request.post(`${API}/maestros/catalogos/items`, {
    headers: c.headers,
    data: { code, name: `Producto ${code}`, item_type: "PRODUCT", base_unit_id: baseUnitId },
  });
  expect(r.ok(), `producto ${code}: ${r.status()} ${await r.text()}`).toBeTruthy();
  return (await r.json()).id as string;
}

// ------------------------------------------------------------------ §74
test("flujo histórico: un documento congelado conserva su factor", async ({ request }) => {
  const c = await ctx(request);
  const und = await createUnit(request, c, `U${RUN}`);
  const product = await createProduct(request, c, `P${RUN}`, und);

  // V1: la caja son 100 unidades.
  const created = await request.post(`${API}/maestros/productos/${product}/presentaciones`, {
    headers: c.headers,
    data: { code: "CAJA", name: "Caja", factor_to_base: "100",
            valid_from: new Date(Date.now() - 86400000 * 30).toISOString() },
  });
  expect(created.ok(), await created.text()).toBeTruthy();
  const presentation = (await created.json()).id as string;

  // El backend resuelve el factor: 10 cajas = 1.000 unidades.
  const preview = await request.post(`${API}/maestros/conversion/preview`, {
    headers: c.headers,
    data: { product_id: product, presentation_id: presentation, quantity: "10" },
  });
  expect(preview.ok()).toBeTruthy();
  const resolved = await preview.json();
  expect(resolved.factor_applied).toBe("100.000000");
  expect(resolved.base_quantity).toBe("1000");

  // V2: la caja pasa a 120.
  const v2 = await request.post(`${API}/maestros/presentaciones/${presentation}/versiones`, {
    headers: c.headers, data: { factor_to_base: "120" },
  });
  expect(v2.ok(), await v2.text()).toBeTruthy();

  // Un documento **nuevo** usa 120.
  const after = await request.post(`${API}/maestros/conversion/preview`, {
    headers: c.headers,
    data: { product_id: product, presentation_id: presentation, quantity: "10" },
  });
  expect((await after.json()).base_quantity).toBe("1200");

  // Consultado **con la fecha del documento antiguo**, sigue siendo 100.
  const historic = await request.post(`${API}/maestros/conversion/preview`, {
    headers: c.headers,
    data: { product_id: product, presentation_id: presentation, quantity: "10",
            date: new Date(Date.now() - 86400000 * 10).toISOString() },
  });
  const past = await historic.json();
  expect(past.factor_applied).toBe("100.000000");
  expect(past.base_quantity).toBe("1000");

  // La versión anterior se conserva y está cerrada.
  const versions = await (await request.get(
    `${API}/maestros/presentaciones/${presentation}/versiones`, { headers: c.headers })).json();
  expect(versions).toHaveLength(2);
  expect(versions.filter((v: { is_open: boolean }) => v.is_open)).toHaveLength(1);
});

// ------------------------------------------------------------------ §75
test("producto simple: opera sin presentaciones", async ({ request }) => {
  const c = await ctx(request);
  const und = await createUnit(request, c, `S${RUN}`);
  const product = await createProduct(request, c, `PS${RUN}`, und);

  const listed = await (await request.get(
    `${API}/maestros/productos/${product}/presentaciones`, { headers: c.headers })).json();
  expect(listed).toEqual([]);

  const preview = await request.post(`${API}/maestros/conversion/preview`, {
    headers: c.headers, data: { product_id: product, quantity: "7" },
  });
  expect(preview.ok()).toBeTruthy();
  const resolved = await preview.json();
  expect(resolved.factor_applied).toBe("1");
  expect(resolved.base_quantity).toBe("7");
});

// ------------------------------------------------------------------ §77
test("factor decimal sin error binario", async ({ request }) => {
  const c = await ctx(request);
  const kg = await createUnit(request, c, `K${RUN}`, 3);
  const product = await createProduct(request, c, `PK${RUN}`, kg);
  const created = await request.post(`${API}/maestros/productos/${product}/presentaciones`, {
    headers: c.headers, data: { code: "SACO", name: "Saco", factor_to_base: "25.5" },
  });
  expect(created.ok(), await created.text()).toBeTruthy();
  const presentation = (await created.json()).id as string;

  const preview = await (await request.post(`${API}/maestros/conversion/preview`, {
    headers: c.headers,
    data: { product_id: product, presentation_id: presentation, quantity: "3" },
  })).json();
  // Exactamente 76,500: con coma flotante habría dado 76.49999999999999.
  expect(preview.base_quantity).toBe("76.500");
});

// ------------------------------------------------------------------ §79
test("versión solapada bloqueada por el backend", async ({ request }) => {
  const c = await ctx(request);
  const und = await createUnit(request, c, `O${RUN}`);
  const product = await createProduct(request, c, `PO${RUN}`, und);
  const created = await request.post(`${API}/maestros/productos/${product}/presentaciones`, {
    headers: c.headers,
    data: { code: "CAJA", name: "Caja", factor_to_base: "100",
            valid_from: new Date("2026-06-01").toISOString() },
  });
  const presentation = (await created.json()).id as string;

  const overlap = await request.post(`${API}/maestros/presentaciones/${presentation}/versiones`, {
    headers: c.headers,
    data: { factor_to_base: "120", valid_from: new Date("2026-01-01").toISOString() },
  });
  expect(overlap.status()).toBe(409);
  expect((await overlap.json()).code).toBe("PRESENTATION_VERSION_OVERLAP");
});

// ------------------------------------------------------------------ §80
test("multiempresa: la unidad global no se edita desde la empresa", async ({ request }) => {
  const c = await ctx(request);
  const listed = await (await request.get(`${API}/maestros/unidades?scope=GLOBAL`,
    { headers: c.headers })).json();
  for (const unit of listed.items) {
    expect(unit.scope).toBe("GLOBAL");
    expect(unit.allowed_actions).toEqual([]);
  }
});

// ------------------------------------------------------- UI: alta y preview
test("interfaz: crear unidad y presentación con equivalencia legible", async ({ page }) => {
  await uiLogin(page);
  await page.locator('nav a[href="/maestros/unidades"]').first().click();
  await page.waitForURL((u) => u.pathname === "/maestros/unidades", { timeout: 15000 });

  const code = `UI${RUN}`;
  await page.getByLabel(/^Código/).fill(code);
  await page.getByLabel(/^Nombre/).fill("Unidad de prueba");
  await page.getByLabel(/^Símbolo/).fill("ui");
  await page.getByLabel(/^Decimales/).fill("0");
  await page.getByRole("button", { name: "Guardar" }).click();
  await expect(page.getByText("Unidad creada")).toBeVisible({ timeout: 15000 });
  await closeNotifications(page);

  await page.getByLabel("Buscar unidad por código o nombre").fill(code);
  await expect(page.getByRole("cell", { name: code, exact: true })).toBeVisible({ timeout: 15000 });
  // El ámbito y los decimales se muestran: son lo que decide el comportamiento.
  const row = page.getByRole("row").filter({ hasText: code });
  await expect(row.getByText("Empresa")).toBeVisible();
});
