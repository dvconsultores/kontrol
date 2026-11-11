import { expect, test, entrar, sesionApi } from "./helpers/sesion";
import { tick } from "./helpers/planificador";

const TENANT = process.env.KONTROL_E2E_TENANT ?? "DEMO";
const USER = process.env.KONTROL_E2E_USER ?? "admin";
const API = process.env.KONTROL_E2E_API ?? "http://127.0.0.1:8000/api/v1";

test.setTimeout(300000);
test("detección automática de reposición: alerta, necesidad, requisición, resolución y reaparición", async ({ page }) => {
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

  const almacen = await post<{ id: string; code: string }>("/organization/warehouses", {
    company_id: companyId,
    branch_id: branchId,
    code: `W-${sufijo}`,
    name: "Almacén E2E",
  }).then((r) => r as { id: string; code: string });

  const articulo = await post<{ id: string; code: string }>("/maestros/catalogos/items", {
    code: `ART-${sufijo}`,
    name: `Artículo ${sufijo}`,
    item_type: "PRODUCT",
  });

  const recibir = (n: number) =>
    post(`/inventory/operations/receive`, {
      warehouse_id: almacen.id,
      product_id: articulo.id,
      quantity: n,
      unit_cost: 1,
    });

  const despachar = (n: number) =>
    post(`/inventory/operations/ship`, {
      warehouse_id: almacen.id,
      product_id: articulo.id,
      quantity: n,
    });

  const necesidades = async () => {
    const res = await fetch(`${API}/planning/replenishment-needs?warehouse_id=${almacen.id}`, {
      headers: authHeaders(companyId),
    });
    expect(res.ok).toBeTruthy();
    const data = (await res.json()) as { items?: Array<{ id: string; status: string }> };
    return data.items ?? [];
  };

  const alertas = async (status: "ACTIVE" | "RESOLVED") => {
    const res = await fetch(`${API}/alerts?status=${status}&page_size=100`, {
      headers: authHeaders(companyId),
    });
    expect(res.ok).toBeTruthy();
    const data = (await res.json()) as {
      items?: Array<{
        id: string;
        status: string;
        message?: { text: string };
        link?: { source_type: string; source_id: string };
      }>;
    };
    const needIds = new Set((await necesidades()).map((n) => n.id));
    return (data.items ?? []).filter(
      (a) => a.link?.source_type === "ReplenishmentNeed" && needIds.has(a.link.source_id),
    );
  };

  await recibir(30);
  await despachar(10);

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

  await page.getByLabel(/^Código de la política/).fill(`POL-${sufijo}`);
  await page.getByLabel(/^Nombre de la política/).fill(`Política ${sufijo}`);
  await page.getByLabel(/^Alcance/).selectOption(almacen.id);
  await page.getByLabel(/^Fuente de demanda/).selectOption("INVENTORY_ISSUES");
  await page.getByLabel(/^Días de histórico/).fill("10");
  await page.getByLabel(/^Días de horizonte/).fill("5");
  await page.getByLabel(/^Plazo de reposición/).fill("3");
  await page.getByLabel(/^Stock de seguridad/).selectOption("NONE");
  await page.getByLabel(/^Métrica de rotación/).selectOption("DEMAND_VELOCITY");
  await page.getByLabel("Detección automática de reposición").check();
  await page.getByRole("button", { name: "Crear política" }).click();
  await expect(page.getByRole("cell", { name: `POL-${sufijo}`, exact: true })).toBeVisible();

  tick();
  expect((await necesidades()).length).toBe(0);

  await despachar(18);
  tick();
  let needs = await necesidades();
  expect(needs.length).toBe(1);
  expect(needs[0].status).toBe("ACTIVE");
  const needId = needs[0].id;
  let activas = await alertas("ACTIVE");
  expect(activas.length).toBe(1);

  tick();
  needs = await necesidades();
  expect(needs.length).toBe(1);
  expect(needs[0].status).toBe("ACTIVE");
  expect(needs[0].id).toBe(needId);
  activas = await alertas("ACTIVE");
  expect(activas.length).toBe(1);
  expect(activas[0].link?.source_id).toBe(needId);

  await page.goto("/alertas");
  await expect(page.getByRole("heading", { name: "Alertas" })).toBeVisible();
  await expect.poll(() => page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth)).toBe(true);

  const tarjeta = page.getByTestId("alerta").filter({ hasText: `ART-${sufijo}` });
  await expect(tarjeta.getByText(`requiere reposición en el almacén W-${sufijo}`)).toBeVisible();
  await tarjeta.getByRole("link", { name: "Abrir origen" }).click();

  await expect(page).toHaveURL(new RegExp(`/compras/planificacion/necesidades/${needId}`));
  await expect(page.getByText("Necesita reposición")).toBeVisible();
  await expect(
    page.getByText(
      `Se generó porque el disponible (2.000000) era menor o igual que el punto de reorden (8.400000), con la política POL-${sufijo} v1.`,
    ),
  ).toBeVisible();
  await expect(page.getByText("12.000000").first()).toBeVisible();
  await expect.poll(() => page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth)).toBe(true);

  await page.getByRole("link", { name: "Crear requisición" }).click();
  await expect(page).toHaveURL(/\/compras\/requisiciones\/nueva/);
  await expect(page.getByLabel(/^Almacén/)).toHaveValue(almacen.id);
  await expect(page.getByText(`Desde la necesidad de reposición de ART-${sufijo}`)).toBeVisible();
  await page.getByLabel(/^Código/).fill(`REQ-${sufijo}`);
  await page.getByRole("button", { name: "Crear requisición" }).click();

  await expect(page.getByRole("heading", { name: `Requisición REQ-${sufijo}` })).toBeVisible();
  await expect(page.getByText(`Línea para la necesidad de reposición de ART-${sufijo}`)).toBeVisible();
  await expect(page.getByLabel(/^Cantidad en unidad base/)).toHaveValue("12.000000");
  await expect(page.getByText("Cantidad sugerida: 12.000000")).toBeVisible();
  await page.getByRole("button", { name: "Agregar con esta cantidad" }).click();
  await expect(page.getByRole("link", { name: "Ver necesidad" })).toBeVisible();
  await expect(page.getByRole("cell", { name: `POL-${sufijo} v1`, exact: true })).toBeVisible();

  const urlRequisicion = page.url().split("?")[0];
  await page.goto(urlRequisicion);
  await expect(page.getByRole("heading", { name: `Requisición REQ-${sufijo}` })).toBeVisible();
  await expect(page.getByRole("link", { name: "Ver necesidad" })).toBeVisible();
  await expect(page.getByRole("cell", { name: `POL-${sufijo} v1`, exact: true })).toBeVisible();

  await page.goto(`/compras/planificacion/necesidades/${needId}`);
  await expect(page.getByText("Necesita reposición")).toBeVisible();
  await expect(page.getByText("Requisiciones creadas desde esta necesidad")).toBeVisible();
  await expect(page.getByText(`REQ-${sufijo}`)).toBeVisible();

  await recibir(50);
  tick();
  needs = await necesidades();
  const resuelta = needs.find((n) => n.id === needId);
  expect(resuelta?.status).toBe("RESOLVED");
  let resueltas = await alertas("RESOLVED");
  expect(resueltas.some((a) => a.link?.source_id === needId)).toBe(true);
  activas = await alertas("ACTIVE");
  expect(activas.length).toBe(0);

  await page.goto(`/compras/planificacion/necesidades/${needId}`);
  await expect(page.getByText(/^Resuelta: La condición dejó de cumplirse/)).toBeVisible();

  await despachar(50);
  tick();
  needs = await necesidades();
  expect(needs.length).toBe(2);
  const nuevaActiva = needs.find((n) => n.status === "ACTIVE");
  expect(nuevaActiva).toBeTruthy();
  expect(nuevaActiva!.id).not.toBe(needId);
  const viejaResuelta = needs.find((n) => n.id === needId);
  expect(viejaResuelta?.status).toBe("RESOLVED");
  activas = await alertas("ACTIVE");
  expect(activas.length).toBe(1);
  expect(activas[0].link?.source_id).toBe(nuevaActiva!.id);
  resueltas = await alertas("RESOLVED");
  expect(resueltas.some((a) => a.link?.source_id === needId)).toBe(true);

  await page.goto("/compras/planificacion/necesidades");
  await expect(page.getByRole("heading", { name: "Necesidades de reposición" })).toBeVisible();
  await expect(page.getByRole("cell", { name: new RegExp(`ART-${sufijo}`) }).first()).toBeVisible();
  await expect.poll(() => page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth)).toBe(true);
});
