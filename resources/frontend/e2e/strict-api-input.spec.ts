import { type APIRequestContext, type Page } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

import { entrar, expect, sesionApi, test } from "./helpers/sesion";
import { activarEmpresa } from "./helpers/empresa";

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
  return { token, company, headers: { Authorization: `Bearer ${token}`, "X-Kontrol-Company": company } };
}

async function post(request: APIRequestContext, c: Ctx, ruta: string, data: unknown) {
  const r = await request.post(`${API}${ruta}`, { headers: c.headers, data });
  expect([200, 201], `${ruta}: ${r.status()} ${await r.text()}`).toContain(r.status());
  return r.json();
}

const marca = (): string =>
  `${Date.now().toString(36)}${Math.random().toString(36).slice(2, 6)}`.toUpperCase();

async function irA(page: Page, href: string): Promise<void> {
  await page.locator(`nav a[href="${href}"]`).first().click();
  await page.waitForURL((u) => u.pathname === href, { timeout: 15000 });
  await page.waitForLoadState("networkidle");
}

test.describe("Contrato estricto de entrada · SHARED-CORE-P0-HARDENING-05", () => {
  test("QUERY-422-E2E-01", async ({ request }) => {
    const c = await ctx(request);
    const r = await request.get(`${API}/maestros/terceros?zz_b=1&zz_a=VALOR-E2E-SENSIBLE`, {
      headers: c.headers,
    });
    expect(r.status()).toBe(422);

    const text = await r.text();
    const body = JSON.parse(text);
    expect(body.code).toBe("UNKNOWN_QUERY_PARAMETER");
    expect(body.message).toBe("La consulta incluye parámetros que esta operación no admite.");
    expect(body.details.unknown_query_parameters).toEqual(["zz_a", "zz_b"]);
    expect(Object.keys(body.field_errors).sort()).toEqual(["query.zz_a", "query.zz_b"]);
    expect(body.request_id).toBeTruthy();
    expect(text).not.toContain("VALOR-E2E-SENSIBLE");
  });

  test("QUERY-422-E2E-02", async ({ request }) => {
    const c = await ctx(request);
    const rPost = await request.post(`${API}/maestros/terceros?zz=1`, {
      headers: c.headers,
      data: {},
    });
    expect(rPost.status()).toBe(422);
    const bodyPost = await rPost.json();
    expect(bodyPost.code).toBe("UNKNOWN_QUERY_PARAMETER");

    const rGet = await request.get(`${API}/maestros/terceros?zz=1`);
    expect(rGet.status()).toBe(401);
  });

  test("QUERY-422-E2E-03", async ({ request }) => {
    const c = await ctx(request);
    const naive = await request.get(`${API}/notifications`, {
      headers: c.headers,
      params: { created_from: "2026-03-10T12:00:00" },
    });
    expect(naive.status()).toBe(422);
    const naiveText = await naive.text();
    const naiveBody = JSON.parse(naiveText);
    expect(naiveBody.code).toBe("NAIVE_DATETIME");
    expect(naiveBody.field_errors["query.created_from"]).toEqual([
      "Indique la zona horaria (Z o ±HH:MM).",
    ]);
    expect(naiveText).not.toContain("12:00:00");

    const utc = await request.get(`${API}/notifications`, {
      headers: c.headers,
      params: { created_from: "2026-03-10T12:00:00Z" },
    });
    expect(utc.status()).toBe(200);

    const offset = await request.get(`${API}/notifications`, {
      headers: c.headers,
      params: { created_from: "2026-03-10T08:00:00-04:00" },
    });
    expect(offset.status()).toBe(200);
  });

  test("QUERY-422-E2E-04", async ({ page }) => {
    const codigos: string[] = [];
    const urlsConCompanyId: string[] = [];

    page.on("response", async (res) => {
      if (res.url().includes("/api/v1/") && res.status() === 422) {
        try {
          const body = await res.json();
          if (typeof body.code === "string") codigos.push(body.code);
        } catch {
          codigos.push("SIN_JSON");
        }
      }
    });

    page.on("request", (req) => {
      const url = req.url();
      if (
        url.includes("/api/v1/") &&
        url.includes("company_id=") &&
        (url.includes("/organization/branches") || url.includes("/approvals/"))
      ) {
        urlsConCompanyId.push(url);
      }
    });

    await entrar(page, USER, { tenant: TENANT });
    await page.waitForURL((u) => !u.pathname.includes("login"), { timeout: 20000 });
    await page.waitForLoadState("networkidle");
    await activarEmpresa(page);

    const rutas = [
      "/inventario/existencias",
      "/organizacion/sucursales",
      "/organizacion/almacenes",
      "/organizacion/establecimientos",
      "/aprobaciones/bandeja",
      "/aprobaciones/politicas",
      "/aprobaciones/delegaciones",
      "/auditoria",
    ];

    for (const ruta of rutas) {
      await irA(page, ruta);
      await expect(page.locator("main h1").first()).toBeVisible();
    }

    expect(codigos.filter((x) => x === "UNKNOWN_QUERY_PARAMETER")).toEqual([]);
    expect(urlsConCompanyId).toEqual([]);
  });

  test("EXISTENCIAS-E2E-01", async ({ page, request }) => {
    const c = await ctx(request);
    const m = marca();
    const warehouseCode = `ALM-${m}`;
    const productCode = `EXS-${m}`;
    const productName = `Tornillo E2E ${m}`;

    const warehouse = await post(request, c, "/organization/warehouses", {
      company_id: c.company,
      code: warehouseCode,
      name: `Almacén ${m}`,
      warehouse_type: "PHYSICAL",
      status: "ACTIVE",
    });

    const product = await post(request, c, "/maestros/catalogos/items", {
      code: productCode,
      name: productName,
      item_type: "PRODUCT",
      status: "ACTIVE",
    });

    let movementTypeId: string | undefined;
    const existingTypes = await request.get(`${API}/inventory/movement-types`, {
      headers: c.headers,
    });
    const typesBody = await existingTypes.json();
    const types = typesBody.items ?? typesBody;
    movementTypeId = types.find((t: { code: string; id?: string }) => t.code === "ENTRADA_RECEPCION")?.id;

    if (!movementTypeId) {
      const createType = await request.post(`${API}/inventory/movement-types`, {
        headers: c.headers,
        data: {
          code: "ENTRADA_RECEPCION",
          name: "Entrada por recepción",
          direction: "IN",
        },
      });
      if (createType.status() === 409) {
        const duplicateBody = await createType.json();
        if (duplicateBody.code !== "MOVEMENT_TYPE_DUPLICATE") {
          throw new Error(`409 inesperado: ${await createType.text()}`);
        }
      } else {
        expect([200, 201], `movement-types: ${createType.status()} ${await createType.text()}`).toContain(
          createType.status(),
        );
      }
      const reread = await request.get(`${API}/inventory/movement-types`, {
        headers: c.headers,
      });
      const rereadBody = await reread.json();
      const rereadTypes = rereadBody.items ?? rereadBody;
      movementTypeId = rereadTypes.find(
        (t: { code: string; id?: string }) => t.code === "ENTRADA_RECEPCION",
      )?.id;
      if (!movementTypeId) {
        throw new Error("Tipo de entrada no encontrado tras reintentar creación");
      }
    }

    await post(request, c, "/inventory/movements", {
      warehouse_id: warehouse.id,
      product_id: product.id,
      movement_type_id: movementTypeId,
      quantity: 5,
    });

    await entrar(page, USER, { tenant: TENANT });
    await page.waitForURL((u) => !u.pathname.includes("login"), { timeout: 20000 });
    await page.waitForLoadState("networkidle");
    await activarEmpresa(page);

    await irA(page, "/inventario/existencias");

    const searchBox = page.getByLabel("Buscar por producto");
    await expect(searchBox).toBeVisible();

    const waitForSearch = page.waitForResponse(
      (r) =>
        r.url().includes("/api/v1/inventory/balances") &&
        r.url().includes(`q=${productCode}`),
    );
    await searchBox.fill(productCode);
    const searchResponse = await waitForSearch;
    expect(searchResponse.status()).toBe(200);

    await expect(page.getByText(`${productCode} — ${productName}`)).toBeVisible();
    await expect(page.locator("tbody tr")).toHaveCount(1);

    await page.getByRole("button", { name: "Limpiar búsqueda" }).click();
    // Sin `q` la lista vuelve al conjunto completo; puede servirse de la caché de TanStack Query (staleTime 30 s),
    // así que se comprueba en la pantalla y no esperando una petición.
    await expect(searchBox).toHaveValue("");
    await expect(page.getByRole("button", { name: "Limpiar búsqueda" })).toHaveCount(0);
    await expect.poll(() => page.locator("tbody tr").count()).toBeGreaterThan(0);

    const axeResults = await new AxeBuilder({ page })
      .include("main")
      .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
      .analyze();
    expect(axeResults.violations.filter((v) => v.impact === "serious" || v.impact === "critical")).toEqual([]);

    await page.setViewportSize({ width: 320, height: 800 });
    await page.getByRole("button", { name: "Colapsar menú" }).click();
    await expect
      .poll(() => page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth))
      .toBe(true);
    await expect(page.getByLabel("Buscar por producto")).toBeVisible();
  });

  test("RUBRO-E2E-01", async ({ page, request }) => {
    const c = await ctx(request);
    const m = marca();
    const code = `RUB-${m}`;
    const name = `Rubro E2E ${m}`;

    await post(request, c, "/maestros/catalogos/taxonomia", {
      code,
      name,
      level: "RUBRO",
      applies_to: ["PRODUCT"],
    });

    await entrar(page, USER, { tenant: TENANT });
    await page.waitForURL((u) => !u.pathname.includes("login"), { timeout: 20000 });
    await page.waitForLoadState("networkidle");
    await activarEmpresa(page);

    await irA(page, "/maestros/productos");
    await page.getByRole("link", { name: /nuevo producto/i }).click();
    await page.waitForURL((u) => u.pathname === "/maestros/productos/nuevo", { timeout: 15000 });
    await page.waitForLoadState("networkidle");

    const combo = page.getByRole("combobox", { name: "Buscar rubro" });
    await expect(combo).toBeVisible();

    const waitForSearch = page.waitForResponse(
      (r) => r.url().includes("/api/v1/maestros/catalogos/taxonomia/search"),
    );
    await combo.fill(name);
    const searchResponse = await waitForSearch;
    expect(searchResponse.status()).toBe(200);

    await expect(page.getByRole("option", { name: new RegExp(name) })).toBeVisible();
  });
});
