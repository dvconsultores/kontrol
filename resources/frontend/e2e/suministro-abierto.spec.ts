import AxeBuilder from "@axe-core/playwright";
import { type Page } from "@playwright/test";

import { expect, test, entrar, sesionApi } from "./helpers/sesion";
import { tick } from "./helpers/planificador";

const TENANT = process.env.KONTROL_E2E_TENANT ?? "DEMO";
const USER = process.env.KONTROL_E2E_USER ?? "admin";
const API = process.env.KONTROL_E2E_API ?? "http://127.0.0.1:8000/api/v1";

const WCAG = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"];

async function sinFaltasGraves(page: Page, etiqueta: string): Promise<void> {
  const resultado = await new AxeBuilder({ page }).withTags(WCAG).analyze();
  const graves = resultado.violations
    .filter((v) => v.impact === "critical" || v.impact === "serious")
    .map((v) => ({ id: v.id, impact: v.impact, nodes: v.nodes.length }));
  expect(graves, `${etiqueta}: ${JSON.stringify(graves)}`).toEqual([]);
}

test.setTimeout(300000);
test("suministro abierto por almacén: la orden en camino evita reponer otra vez", async ({ page }) => {
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

  const postCrudo = async (
    ruta: string,
    datos: Record<string, unknown>,
  ): Promise<Response> => {
    return fetch(`${API}${ruta}`, {
      method: "POST",
      headers: authHeaders(companyId),
      body: JSON.stringify(datos),
    });
  };

  // 1. Datos base: empresa, sucursal, almacenes W y W2, artículo, inventario y proveedor.
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

  const almacen2 = await post<{ id: string; code: string }>("/organization/warehouses", {
    company_id: companyId,
    branch_id: branchId,
    code: `W2-${sufijo}`,
    name: "Almacén Secundario E2E",
  }).then((r) => r as { id: string; code: string });

  const articulo = await post<{ id: string; code: string }>("/maestros/catalogos/items", {
    code: `ART-${sufijo}`,
    name: `Artículo ${sufijo}`,
    item_type: "PRODUCT",
  }).then((r) => r as { id: string; code: string });

  const proveedor = await post<{ id: string }>("/maestros/terceros", {
    code: `PRV-${sufijo}`,
    name: `Proveedor ${sufijo}`,
    person_type: "JURIDICA",
    roles: ["PROVEEDOR"],
    status: "ACTIVE",
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

  // 2. Política de reposición.
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

  // 3. Sin necesidad; tras despachar 18 aparece la necesidad ACTIVE.
  tick();
  expect((await necesidades()).length).toBe(0);
  await despachar(18);
  tick();
  let needs = await necesidades();
  expect(needs.length).toBe(1);
  expect(needs[0].status).toBe("ACTIVE");
  const needId = needs[0].id;

  // 4. Detalle con proyección.
  await page.goto(`/compras/planificacion/necesidades/${needId}`);
  await expect(page.getByText(/Necesita reposición|Resuelta/).first()).toBeVisible();
  const seccionPorQue = page.locator("section", { hasText: "Por qué se generó" });
  await expect(
    seccionPorQue.locator("div", { has: page.getByText("Suministro abierto", { exact: true }) }),
  ).toContainText("0.000000");
  await expect(
    seccionPorQue.locator("div", { has: page.getByText("Disponible proyectado", { exact: true }) }),
  ).toContainText("2.000000");
  await sinFaltasGraves(page, "detalle inicial de necesidad");

  // 5. Requisición desde la necesidad.
  await page.getByRole("link", { name: "Crear requisición" }).click();
  await expect(page).toHaveURL(/\/compras\/requisiciones\/nueva/);
  await page.getByLabel(/^Código/).fill(`REQ-${sufijo}`);
  await page.getByRole("button", { name: "Crear requisición" }).click();
  await expect(page.getByRole("heading", { name: `Requisición REQ-${sufijo}` })).toBeVisible();
  await page.getByRole("button", { name: "Agregar con esta cantidad" }).click();

  // 6. Orden de compra desde cotización por API.
  const quote = await post<{ id: string }>("/purchasing/quotes", {
    code: `COT-${sufijo}`,
    supplier_id: proveedor.id,
    currency: "VED",
  });
  await post(`/purchasing/quotes/${quote.id}/lines`, {
    product_id: articulo.id,
    quantity: 12,
    unit_price: 1,
    discount: 0,
    delivery_days: 5,
    tax_ref: null,
  });
  await post(`/purchasing/quotes/${quote.id}/award`, { reason: "Reposición" });
  const responseOrden = await post<{ order: { id: string; code: string; lines: Array<{ id: string }> } }>(
    `/purchasing/quotes/${quote.id}/order`,
    { code: `OC-${sufijo}` },
  );
  const orden = responseOrden.order;

  // 7. Fijar destino en UI.
  await page.goto("/compras/ordenes");
  await expect(page.getByRole("heading", { name: "Órdenes de compra" })).toBeVisible();
  await page.getByRole("button", { name: `Ver líneas de OC-${sufijo}` }).click();
  await expect(page.getByText("Sin almacén destino: no cuenta en la planificación")).toBeVisible();
  const selectDestino = page.getByLabel(`Almacén destino de ART-${sufijo} · Artículo ${sufijo}`);
  await selectDestino.selectOption({ label: `W-${sufijo} · Almacén E2E` });
  await page.getByRole("button", { name: `Fijar destino de ART-${sufijo} · Artículo ${sufijo}` }).click();
  await expect(page.getByRole("cell", { name: `W-${sufijo} · Almacén E2E`, exact: true })).toBeVisible();
  await expect.poll(() => page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth)).toBe(true);
  await sinFaltasGraves(page, "panel de líneas con destino fijado");

  // 8. Transiciones y verificación de pendiente.
  for (const target of ["SUBMITTED", "APPROVED"]) {
    await post(`/purchasing/orders/${orden.id}/transition`, { target });
  }
  await page.goto("/compras/ordenes");
  await expect(page.getByRole("heading", { name: "Órdenes de compra" })).toBeVisible();
  await page.getByRole("button", { name: `Ver líneas de OC-${sufijo}` }).click();
  await expect(page.getByRole("cell", { name: "12.000000", exact: true })).toBeVisible();

  // 9. La necesidad se resuelve con el suministro abierto.
  tick();
  needs = await necesidades();
  expect(needs.find((n) => n.id === needId)?.status).toBe("RESOLVED");
  await page.goto(`/compras/planificacion/necesidades/${needId}`);
  const seccionActual = page.locator("section", { hasText: "Situación actual" });
  await expect(
    seccionActual.locator("div", { has: page.getByText("Suministro abierto", { exact: true }) }),
  ).toContainText("12.000000");
  await expect(
    seccionActual.locator("div", { has: page.getByText("Disponible proyectado", { exact: true }) }),
  ).toContainText("14.000000");
  tick();
  expect((await necesidades()).length).toBe(1);

  // 10. Recepción en el almacén equivocado bloqueada.
  const rec2 = await post<{ id: string }>("/purchasing/receipts", {
    code: `REC2-${sufijo}`,
    order_id: orden.id,
    warehouse_id: almacen2.id,
  });
  const r = await postCrudo(`/purchasing/receipts/${rec2.id}/lines`, {
    order_line_id: orden.lines[0].id,
    product_id: articulo.id,
    quantity_received: 5,
    quantity_accepted: 5,
    quantity_rejected: 0,
  });
  expect(r.status).toBe(409);
  expect(((await r.json()) as { code: string }).code).toBe("RECEIPT_LINE_OTHER_WAREHOUSE");
  await post(`/purchasing/receipts/${rec2.id}/cancel`, { reason: "Almacén equivocado" });

  // 11. Recepción parcial en el almacén correcto.
  const rec = await post<{ id: string }>("/purchasing/receipts", {
    code: `REC-${sufijo}`,
    order_id: orden.id,
    warehouse_id: almacen.id,
  });
  await post(`/purchasing/receipts/${rec.id}/lines`, {
    order_line_id: orden.lines[0].id,
    product_id: articulo.id,
    quantity_received: 5,
    quantity_accepted: 5,
    quantity_rejected: 0,
  });
  await post(`/purchasing/receipts/${rec.id}/confirm`, {});
  await post(`/purchasing/receipts/${rec.id}/quality`, {});
  await post(`/purchasing/receipts/${rec.id}/quality`, { quality_status: "APPROVED" });
  await post(`/purchasing/receipts/${rec.id}/accept`, {});

  const getOrden = await fetch(`${API}/purchasing/orders/${orden.id}`, {
    headers: authHeaders(companyId),
  });
  expect(getOrden.ok).toBeTruthy();
  const ordenActualizada = (await getOrden.json()) as {
    lines: Array<{ open_quantity: string }>;
  };
  expect(ordenActualizada.lines[0].open_quantity).toBe("7.000000");

  await page.goto("/compras/ordenes");
  await page.getByRole("button", { name: `Ver líneas de OC-${sufijo}` }).click();
  await expect(page.getByRole("cell", { name: "7.000000", exact: true })).toBeVisible();

  // 12. Cierre y reaparición de la necesidad.
  await post(`/purchasing/orders/${orden.id}/transition`, { target: "CLOSED" });
  const getOrdenCerrada = await fetch(`${API}/purchasing/orders/${orden.id}`, {
    headers: authHeaders(companyId),
  });
  expect(getOrdenCerrada.ok).toBeTruthy();
  const ordenCerrada = (await getOrdenCerrada.json()) as {
    lines: Array<{ open_quantity: string }>;
  };
  expect(ordenCerrada.lines[0].open_quantity).toBe("0.000000");

  tick();
  needs = await necesidades();
  expect(needs.length).toBe(2);
  const vieja = needs.find((n) => n.id === needId);
  expect(vieja?.status).toBe("RESOLVED");
  const nueva = needs.find((n) => n.id !== needId);
  expect(nueva?.status).toBe("ACTIVE");

  await page.goto(`/compras/planificacion/necesidades/${nueva!.id}`);
  const seccionPorQueNueva = page.locator("section", { hasText: "Por qué se generó" });
  await expect(
    seccionPorQueNueva.locator("div", { has: page.getByText("Suministro abierto", { exact: true }) }),
  ).toContainText("0.000000");
});
