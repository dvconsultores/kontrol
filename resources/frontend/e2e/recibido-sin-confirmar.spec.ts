import AxeBuilder from "@axe-core/playwright";
import { type APIRequestContext, type Page } from "@playwright/test";

import { expect, test, entrar, sesionApi } from "./helpers/sesion";
import { tick, hastaQue } from "./helpers/planificador";
import { verificadorDeEscenario } from "./helpers/usuario";

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

interface Necesidad {
  id: string;
  status: string;
}

test.setTimeout(300000);
test("recibido sin confirmar: la recepción pendiente cuenta en la proyección sin tocar el stock real", async ({
  page,
  request,
}: {
  page: Page;
  request: APIRequestContext;
}) => {
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
    const data = (await res.json()) as { items?: Necesidad[] };
    return data.items ?? [];
  };

  const detalleNecesidad = async (id: string) => {
    const res = await fetch(`${API}/planning/replenishment-needs/${id}`, {
      headers: authHeaders(companyId),
    });
    expect(res.ok).toBeTruthy();
    return (await res.json()) as {
      current: {
        available: string;
        open_supply: string;
        received_unconfirmed: string | null;
        projected_available: string;
        recommended_quantity: string;
      };
    };
  };

  const plan = async (warehouseId: string) => {
    const res = await fetch(
      `${API}/planning/plan?warehouse_id=${warehouseId}&product_id=${articulo.id}`,
      { headers: authHeaders(companyId) },
    );
    expect(res.ok).toBeTruthy();
    return (await res.json()) as {
      available: string;
      open_supply: string;
      received_unconfirmed: string;
      projected_available: string;
    };
  };

  // 1) Inventario y política.
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

  // 2) Generar primera necesidad.
  tick();
  expect((await necesidades()).length).toBe(0);
  await despachar(18);
  await hastaQue(async () => (await necesidades()).length === 1);
  let needs = await necesidades();
  expect(needs[0].status).toBe("ACTIVE");
  const needId = needs[0].id;

  // 3) Orden pequeña que no resuelve.
  const orden = await post<{ id: string }>("/purchasing/orders", {
    code: `OC-${sufijo}`,
    supplier_id: proveedor.id,
    currency: "VED",
  });
  const lineaOrden = await post<{ id: string }>(`/purchasing/orders/${orden.id}/lines`, {
    product_id: articulo.id,
    quantity_ordered: 4,
    unit_price: 1,
    destination_warehouse_id: almacen.id,
  });
  for (const target of ["SUBMITTED", "APPROVED"]) {
    await post(`/purchasing/orders/${orden.id}/transition`, { target });
  }

  // 4) Suministro abierto no basta.
  await hastaQue(async () => {
    const detalle = await detalleNecesidad(needId);
    return detalle.current.open_supply === "4.000000";
  });
  needs = await necesidades();
  expect(needs.length).toBe(1);
  expect(needs.find((n) => n.id === needId)?.status).toBe("ACTIVE");
  const detalleAntes = await detalleNecesidad(needId);
  const sugeridaAntes = detalleAntes.current.recommended_quantity;

  await page.goto(`/compras/planificacion/necesidades/${needId}`);
  await expect(page.getByText(/Necesita reposición|Resuelta/).first()).toBeVisible();
  const seccionActual4 = page.locator("section", { hasText: "Situación actual" });
  await expect(
    seccionActual4.locator("div", { has: page.getByText("Disponible", { exact: true }) }),
  ).toContainText("2.000000");
  await expect(
    seccionActual4.locator("div", { has: page.getByText("Suministro abierto", { exact: true }) }),
  ).toContainText("4.000000");
  await expect(
    seccionActual4.locator("div", { has: page.getByText("En recepción (pendiente de confirmar)", { exact: true }) }),
  ).toContainText("0.000000");
  await expect(
    seccionActual4.locator("div", { has: page.getByText("Disponible proyectado", { exact: true }) }),
  ).toContainText("6.000000");
  await sinFaltasGraves(page, "detalle de necesidad con suministro abierto");

  // 5) Recepción aceptada pendiente de confirmar.
  const rec = await post<{ id: string }>("/purchasing/receipts", {
    code: `REC-${sufijo}`,
    order_id: orden.id,
    warehouse_id: almacen.id,
  });
  const lineaRecepcion = await post<{ id: string }>(`/purchasing/receipts/${rec.id}/lines`, {
    order_line_id: lineaOrden.id,
    product_id: articulo.id,
    quantity_received: 3,
    quantity_accepted: 3,
    quantity_rejected: 0,
  });
  await post(`/purchasing/receipts/${rec.id}/confirm`, {});
  await post(`/purchasing/receipts/${rec.id}/quality`, {});
  await post(`/purchasing/receipts/${rec.id}/quality`, { quality_status: "APPROVED" });
  await post(`/purchasing/receipts/${rec.id}/accept`, {});

  // 6) Proyección suma lo recibido, el disponible real no sube.
  await hastaQue(async () => {
    const detalle = await detalleNecesidad(needId);
    return detalle.current.received_unconfirmed === "3.000000";
  });
  needs = await necesidades();
  expect(needs.length).toBe(1);
  expect(needs.find((n) => n.id === needId)?.status).toBe("ACTIVE");
  const detalleRecibido = await detalleNecesidad(needId);
  expect(detalleRecibido.current.recommended_quantity).toBe(sugeridaAntes);

  const planAntesConfirmar = await plan(almacen.id);
  expect(planAntesConfirmar.available).toBe("2.000000");
  expect(planAntesConfirmar.open_supply).toBe("1.000000");
  expect(planAntesConfirmar.received_unconfirmed).toBe("3.000000");
  expect(planAntesConfirmar.projected_available).toBe("6.000000");
  await page.goto(`/compras/planificacion/necesidades/${needId}`);
  await expect(page.getByText(/Necesita reposición|Resuelta/).first()).toBeVisible();

  const seccionActual6 = page.locator("section", { hasText: "Situación actual" });
  await expect(
    seccionActual6.locator("div", { has: page.getByText("Disponible", { exact: true }) }),
  ).toContainText("2.000000");
  await expect(
    seccionActual6.locator("div", { has: page.getByText("Suministro abierto", { exact: true }) }),
  ).toContainText("1.000000");
  await expect(
    seccionActual6.locator("div", { has: page.getByText("En recepción (pendiente de confirmar)", { exact: true }) }),
  ).toContainText("3.000000");
  await expect(
    seccionActual6.locator("div", { has: page.getByText("Disponible proyectado", { exact: true }) }),
  ).toContainText("6.000000");
  await sinFaltasGraves(page, "detalle con recepción pendiente de confirmar");
  await expect.poll(() => page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth)).toBe(true);

  // 7) Aislamiento por almacén.
  const planAislado = await plan(almacen2.id);
  expect(planAislado.received_unconfirmed).toBe("0.000000");
  expect(planAislado.open_supply).toBe("0.000000");

  // 8) Conteo por otra persona.
  const contador = await verificadorDeEscenario(
    request,
    { headers: authHeaders(companyId) },
    { usuario: `rup-${sufijo}`, empresas: [companyId] },
  );
  const conteoRes = await request.post(`${API}/purchasing/receipts/${rec.id}/lines/${lineaRecepcion.id}/conteo`, {
    headers: contador.headers,
    data: { counted_base_quantity: "3", difference_kinds: [] },
  });
  expect([200, 201]).toContain(conteoRes.status());

  // 9) Confirmar en la UI.
  await page.goto("/inventario/confirmacion");
  await expect(page.getByRole("heading", { name: "Confirmación de inventario" })).toBeVisible();
  await page.getByLabel(/Recepción aceptada/).selectOption(rec.id);
  await expect(page.getByText("Faltan líneas por contar.")).toBeHidden({ timeout: 15_000 });
  await page.getByLabel(/A disponible/).fill("3");
  await page.getByRole("button", { name: "Confirmar inventario" }).click();
  await expect(page.getByRole("heading", { name: "Decisiones tomadas" })).toBeVisible({ timeout: 15_000 });

  // 10) Confirmación pasa a disponible.
  await hastaQue(async () => {
    const detalle = await detalleNecesidad(needId);
    return detalle.current.received_unconfirmed === "0.000000" && detalle.current.available === "5.000000";
  });
  needs = await necesidades();
  expect(needs.length).toBe(1);
  const detalleConfirmado = await detalleNecesidad(needId);
  expect(detalleConfirmado.current.recommended_quantity).toBe(sugeridaAntes);

  const planConfirmado = await plan(almacen.id);
  expect(planConfirmado.available).toBe("5.000000");
  expect(planConfirmado.received_unconfirmed).toBe("0.000000");
  expect(planConfirmado.projected_available).toBe("6.000000");

  await page.goto(`/compras/planificacion/necesidades/${needId}`);
  await expect(page.getByText(/Necesita reposición|Resuelta/).first()).toBeVisible();

  const seccionActual10 = page.locator("section", { hasText: "Situación actual" });
  await expect(
    seccionActual10.locator("div", { has: page.getByText("Disponible", { exact: true }) }),
  ).toContainText("5.000000");
  await expect(
    seccionActual10.locator("div", { has: page.getByText("En recepción (pendiente de confirmar)", { exact: true }) }),
  ).toContainText("0.000000");
  await expect(
    seccionActual10.locator("div", { has: page.getByText("Disponible proyectado", { exact: true }) }),
  ).toContainText("6.000000");
  await sinFaltasGraves(page, "detalle tras confirmar recepción");
});
