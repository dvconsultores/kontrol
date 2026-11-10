import { expect, test, entrar, sesionApi } from "./helpers/sesion";

const TENANT = process.env.KONTROL_E2E_TENANT ?? "DEMO";
const USER = process.env.KONTROL_E2E_USER ?? "admin";
const API = process.env.KONTROL_E2E_API ?? "http://127.0.0.1:8000/api/v1";

test.setTimeout(300000);
test("planificación de abastecimiento: política, requisición con sugerencia e instantánea", async ({ page }) => {
  const sufijo = Date.now().toString().slice(-8);
  const { token } = await sesionApi(USER, { tenant: TENANT });

  const authHeaders = (companyId: string) => ({
    Authorization: `Bearer ${token}`,
    "X-Kontrol-Company": companyId,
    "Content-Type": "application/json",
  });

  const getEmpresa = await fetch(`${API}/organization/companies`, {
    headers: {
      Authorization: `Bearer ${token}`,
      "X-Kontrol-Company": TENANT,
    },
  });
  expect(getEmpresa.ok).toBeTruthy();
  const empresas = (await getEmpresa.json()) as { items: Array<{ id: string }> };
  const companyId = empresas.items[0].id;

  const post = async <T>(
    ruta: string,
    datos: Record<string, unknown>,
  ): Promise<T> => {
    const res = await fetch(`${API}${ruta}`, {
      method: "POST",
      headers: authHeaders(companyId),
      body: JSON.stringify(datos),
    });
    expect([200, 201]).toContain(res.status);
    return (await res.json()) as T;
  };

  const branchesRes = await fetch(`${API}/organization/branches`, {
    headers: authHeaders(companyId),
  });
  const branchesData = await branchesRes.json();
  const branches = Array.isArray(branchesData) ? branchesData : (branchesData as { items?: Array<{ id: string }> }).items;
  let branchId = branches?.[0]?.id;
  if (!branchId) {
    branchId = await post<{ id: string }>("/organization/branches", {
      company_id: companyId,
      code: `BR-${sufijo}`,
      name: "Sucursal E2E",
    }).then((r) => r.id);
  }

  const almacen = await post<{ id: string }>("/organization/warehouses", {
    company_id: companyId,
    branch_id: branchId,
    code: `W-${sufijo}`,
    name: "Almacén E2E",
  }).then((r) => r.id);

  const niveles = await fetch(`${API}/organization/warehouses/${almacen}/structure-levels`, {
    method: "PATCH",
    headers: authHeaders(companyId),
    body: JSON.stringify({ structure_levels: { zone: true } }),
  });
  expect(niveles.ok).toBeTruthy();

  const zona = await post<{ id: string; code: string; name: string }>(`/organization/warehouses/${almacen}/zones`, {
    code: `ZP-${sufijo}`,
    name: `Zona Planificación ${sufijo}`,
    sequence: 1,
  });

  const articulo = await post<{ id: string }>("/maestros/catalogos/items", {
    code: `ART-${sufijo}`,
    name: `Artículo ${sufijo}`,
    item_type: "PRODUCT",
  });

  await post("/inventory/operations/receive", {
    warehouse_id: almacen,
    product_id: articulo.id,
    quantity: 12,
    unit_cost: 1,
  });
  await post("/inventory/operations/ship", {
    warehouse_id: almacen,
    product_id: articulo.id,
    quantity: 10,
  });

  const bandasRes = await fetch(`${API}/planning/rotation-bands`, {
    headers: authHeaders(companyId),
  });
  expect(bandasRes.ok).toBeTruthy();
  const bandasJson = (await bandasRes.json()) as { items?: Array<{ id: string; status: string; version: number }> } | Array<{ id: string; status: string; version: number }>;
  const bandasActivas = (Array.isArray(bandasJson) ? bandasJson : (bandasJson.items ?? [])).filter((b) => b.status === "ACTIVE");
  for (const banda of bandasActivas) {
    const patchRes = await fetch(`${API}/planning/rotation-bands/${banda.id}`, {
      method: "PATCH",
      headers: authHeaders(companyId),
      body: JSON.stringify({ expected_version: banda.version, status: "INACTIVE" }),
    });
    expect(patchRes.ok).toBeTruthy();
  }

  await entrar(page, USER, { tenant: TENANT });
  await page.goto("/");
  await page.waitForLoadState("networkidle");
  if (page.viewportSize() && page.viewportSize()!.width < 1024) {
    await page.addLocatorHandler(
      page.getByRole("button", { name: "Cerrar notificación" }).first(),
      async (boton) => {
        await boton.click();
      },
    );
    await page.getByRole("button", { name: /abrir menú|menú/i }).click();
  }

  await page.goto("/maestros/planificacion");
  await expect(page.getByRole("heading", { name: "Planificación de abastecimiento" })).toBeVisible();
  await expect.poll(() => page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth)).toBe(true);

  await page.getByLabel(/^Código de la política/).fill(`POL-${sufijo}`);
  await page.getByLabel(/^Nombre de la política/).fill(`Política ${sufijo}`);
  await page.getByLabel(/^Alcance/).selectOption(almacen);
  await page.getByLabel(/^Fuente de demanda/).selectOption("INVENTORY_ISSUES");
  await page.getByLabel(/^Días de histórico/).fill("10");
  await page.getByLabel(/^Días de horizonte/).fill("5");
  await page.getByLabel(/^Plazo de reposición/).fill("2");
  await page.getByLabel(/^Stock de seguridad/).selectOption("NONE");
  await page.getByLabel(/^Métrica de rotación/).selectOption("DEMAND_VELOCITY");
  await page.getByRole("button", { name: "Crear política" }).click();
  await expect(page.getByRole("cell", { name: `POL-${sufijo}`, exact: true })).toBeVisible();

  await page.getByLabel(/^Código de la banda/).fill(`RAP-${sufijo}`);
  await page.getByLabel(/^Nombre de la banda/).fill("Rápida");
  await page.getByLabel(/^Métrica de la banda/).selectOption("DEMAND_VELOCITY");
  await page.getByLabel(/^Desde \(incluido\)/).fill("0.5");
  await page.getByRole("button", { name: "Crear banda" }).click();
  await expect(page.getByRole("cell", { name: `RAP-${sufijo}`, exact: true })).toBeVisible();

  await page.goto("/compras/requisiciones");
  await expect(page.getByRole("heading", { name: "Requisiciones" })).toBeVisible();
  await page.getByRole("link", { name: "Nueva requisición" }).click();
  await page.getByLabel(/^Código/).fill(`REQ-${sufijo}`);
  await page.getByLabel(/^Almacén/).selectOption(almacen);
  await page.getByRole("button", { name: "Crear requisición" }).click();
  await expect(page.getByRole("heading", { name: `Requisición REQ-${sufijo}` })).toBeVisible();
  const urlDetalle = page.url();
  await expect.poll(() => page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth)).toBe(true);

  await page.getByLabel(/^Producto/).fill(`ART-${sufijo}`);
  await page.getByRole("listbox").getByRole("option", { name: new RegExp(`ART-${sufijo}`) }).click();
  await expect(page.getByText("Cantidad sugerida: 3.000000")).toBeVisible();
  await expect(page.getByText(`Rápida (RAP-${sufijo})`)).toBeVisible();
  await page.getByRole("button", { name: "Usar cantidad sugerida" }).click();
  await expect(page.getByText("Sugerencia aceptada")).toBeVisible();
  await expect(page.getByText(`POL-${sufijo} v1`)).toBeVisible();

  await page.goto("/maestros/planificacion");
  await expect(page.getByRole("heading", { name: "Planificación de abastecimiento" })).toBeVisible();
  await page.getByRole("button", { name: `Desactivar POL-${sufijo}` }).click();
  await expect(page.getByRole("button", { name: `Activar POL-${sufijo}` })).toBeVisible();
  await page.getByRole("button", { name: `Activar POL-${sufijo}` }).click();
  await expect(page.getByRole("button", { name: `Desactivar POL-${sufijo}` })).toBeVisible();

  await page.goto(urlDetalle);
  await expect(page.getByRole("heading", { name: `Requisición REQ-${sufijo}` })).toBeVisible();
  await expect(page.getByText(`POL-${sufijo} v1`)).toBeVisible();

  await page.getByLabel(/^Producto/).fill(`ART-${sufijo}`);
  await page.getByRole("listbox").getByRole("option", { name: new RegExp(`ART-${sufijo}`) }).click();
  await page.getByLabel(/^Cantidad en unidad base/).fill("7");
  await page.getByRole("button", { name: "Agregar con esta cantidad" }).click();
  await expect(page.getByText("Cantidad manual")).toBeVisible();
  await expect(page.getByText(`POL-${sufijo} v3`)).toBeVisible();

  await page.goto("/maestros/almacenamiento");
  await expect(page.getByRole("heading", { name: "Reglas de almacenamiento" })).toBeVisible();
  await expect.poll(() => page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth)).toBe(true);
  const reglas = page.getByRole("region", { name: "Reglas de almacenamiento" });

  await reglas.getByLabel(/^Código/).fill(`RR-${sufijo}`);
  await reglas.getByLabel(/^Nombre/).fill(`Regla rotación ${sufijo}`);
  await reglas.getByLabel(/^Prioridad/).fill("1");
  await reglas.getByLabel(/^Almacén/).selectOption(almacen);
  await reglas.getByLabel(/^Tipo de destino/).selectOption("ZONE");
  await reglas.getByLabel(/^Zona$/).selectOption(zona.id);
  await reglas.getByLabel(/^Banda de rotación/).selectOption({ label: `RAP-${sufijo} - Rápida` });
  await reglas.getByLabel(/^Etiquetado/).selectOption("NOT_REQUIRED");
  await reglas.getByRole("button", { name: "Crear regla" }).click();
  await expect(reglas.getByText(`Rotación: RAP-${sufijo}`)).toBeVisible();
});
