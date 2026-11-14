import AxeBuilder from "@axe-core/playwright";
import { type APIRequestContext, type Page } from "@playwright/test";

import { entrar, expect, sesionApi, test } from "./helpers/sesion";
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

async function get(request: APIRequestContext, c: Ctx, ruta: string) {
  const r = await request.get(`${API}${ruta}`, { headers: c.headers });
  expect(r.ok(), `${ruta}: ${r.status()}`).toBeTruthy();
  return r.json();
}

async function postCruda(request: APIRequestContext, c: Ctx, ruta: string, data: unknown) {
  return request.post(`${API}${ruta}`, { headers: c.headers, data });
}

async function recepcionAceptada(request: APIRequestContext, c: Ctx, marca: string) {
  // Crear sucursal y almacén propios para no depender de los sembrados.
  const sucursal = await post(request, c, "/organization/branches", {
    company_id: c.company,
    code: `S-${marca}`,
    name: "Sucursal E2E",
  });
  const almacen = await post(request, c, "/organization/warehouses", {
    company_id: c.company,
    branch_id: sucursal.id,
    code: `W-${marca}`,
    name: "Almacén E2E",
  });
  const prov = await post(request, c, "/maestros/terceros", {
    code: `PRV-${marca}`,
    name: "Proveedor E2E",
    person_type: "JURIDICA",
    roles: ["PROVEEDOR"],
    status: "ACTIVE",
  });
  const prod = await post(request, c, "/maestros/catalogos/items", {
    code: `ART-${marca}`,
    name: "Artículo confirmación",
    item_type: "PRODUCT",
    status: "ACTIVE",
  });
  const orden = await post(request, c, "/purchasing/orders", {
    code: `OC-${marca}`,
    supplier_id: prov.id,
    currency: "VED",
  });
  const ol = await post(request, c, `/purchasing/orders/${orden.id}/lines`, {
    product_id: prod.id,
    quantity_ordered: 500,
    unit_price: 1,
  });
  for (const target of ["SUBMITTED", "APPROVED"]) {
    await post(request, c, `/purchasing/orders/${orden.id}/transition`, { target });
  }
  const rec = await post(request, c, "/purchasing/receipts", {
    code: `RC-${marca}`,
    order_id: orden.id,
    warehouse_id: almacen.id,
  });
  const rl = await post(request, c, `/purchasing/receipts/${rec.id}/lines`, {
    order_line_id: ol.id,
    product_id: prod.id,
    quantity_received: 100,
    quantity_accepted: 80,
    quantity_rejected: 20,
  });
  await post(request, c, `/purchasing/receipts/${rec.id}/confirm`, {});
  await post(request, c, `/purchasing/receipts/${rec.id}/quality`, {});
  await post(request, c, `/purchasing/receipts/${rec.id}/quality`, { quality_status: "APPROVED" });
  await post(request, c, `/purchasing/receipts/${rec.id}/accept`, {});
  return {
    receipt: rec.id as string,
    code: rec.code as string,
    line: rl.id as string,
    product: prod.id as string,
    almacen: almacen.id as string,
  };
}

test("la confirmación exige repartir el 100 % de lo aceptado y ejecuta el reparto", async ({
  page,
  request,
}) => {
  test.setTimeout(300000);
  const marca = `${Date.now().toString(36)}${Math.random().toString(36).slice(2, 6)}`;
  const c = await ctx(request);
  const m = await recepcionAceptada(request, c, marca);

  // Conteo por un contador independiente.
  const contador = await verificadorDeEscenario(request, c, {
    usuario: `invc-${marca}`,
    empresas: [c.company],
  });
  await post(request, contador, `/purchasing/receipts/${m.receipt}/lines/${m.line}/conteo`, {
    counted_base_quantity: "100",
    difference_kinds: [],
  });

  // Plan antes: 80 recibido sin confirmar y nada disponible.
  const planAntes = await get(
    request,
    c,
    `/planning/plan?warehouse_id=${m.almacen}&product_id=${m.product}`,
  );
  expect(planAntes.received_unconfirmed).toBe("80.000000");
  expect(planAntes.available).toBe("0.000000");

  await entrar(page, USER, {
    tenant: TENANT,
    ruta: `/inventario/confirmacion?recepcion=${m.receipt}`,
  });
  await expect(page.getByRole("heading", { name: "Confirmación de inventario" })).toBeVisible();
  await expect(page.getByText(`ART-${marca}`)).toBeVisible();
  expect(await page.locator("body").innerText()).not.toContain(m.product);
  await sinFaltasGraves(page, "inicio");
  const sinDesplazamiento = await page.evaluate(
    () => document.documentElement.scrollWidth <= window.innerWidth,
  );
  expect(sinDesplazamiento).toBe(true);

  // Residuo de 20 sin decidir.
  await page.getByLabel(/A disponible/).fill("50");
  await page.getByLabel(/^Rechazada/).fill("10");
  await page.getByLabel(/Motivo del rechazo/).fill("No apto");
  await expect(page.getByText("Pendiente por decidir: 20")).toBeVisible();
  await expect(page.getByRole("button", { name: "Confirmar inventario" })).toBeDisabled();
  await sinFaltasGraves(page, "residuo");

  // El backend rechaza el residuo por la API.
  const intento = await postCruda(request, c, `/purchasing/receipts/${m.receipt}/confirmacion-inventario`, {
    decisions: [
      { receipt_line_id: m.line, target_state: "DISPONIBLE", base_quantity: "50" },
      { receipt_line_id: m.line, target_state: "RECHAZADO", base_quantity: "10", reason: "No apto" },
    ],
  });
  expect(intento.status()).toBe(422);
  const cuerpo = await intento.json();
  expect(cuerpo.code).toBe("RECEIPT_CONFIRMATION_INCOMPLETE");
  expect(cuerpo.details.lines[0].base_pending).toBe("20.000000");

  // Cero mutación tras el residuo.
  const balances = await get(request, c, `/inventory/balances?product_id=${m.product}`);
  expect((balances.items as Array<{ state: string; qty_on_hand: string }>).length).toBe(1);
  expect((balances.items as Array<{ state: string; qty_on_hand: string }>)[0].state).toBe("RECIBIDO");
  expect(Number((balances.items as Array<{ state: string; qty_on_hand: string }>)[0].qty_on_hand)).toBe(80);
  const hechas = await get(request, c, `/purchasing/receipts/${m.receipt}/confirmacion-inventario`);
  expect(hechas.items.length).toBe(0);
  const planTrasIntento = await get(
    request,
    c,
    `/planning/plan?warehouse_id=${m.almacen}&product_id=${m.product}`,
  );
  expect(planTrasIntento.received_unconfirmed).toBe("80.000000");

  // Exceso.
  await page.getByLabel(/A disponible/).fill("70");
  await page.getByLabel(/^Rechazada/).fill("20");
  await expect(page.getByText("Excede lo aceptado en 10.")).toBeVisible();
  await expect(page.getByRole("button", { name: "Confirmar inventario" })).toBeDisabled();

  // Reparto completo.
  await page.getByLabel(/A disponible/).fill("60");
  await page.getByLabel(/^Rechazada/).fill("20");
  await expect(page.getByText("Pendiente por decidir: 0")).toBeVisible();
  await expect(page.getByRole("button", { name: "Confirmar inventario" })).toBeEnabled();
  await page.getByRole("button", { name: "Confirmar inventario" }).click();
  await expect(page.getByRole("heading", { name: "Decisiones tomadas" })).toBeVisible();
  await sinFaltasGraves(page, "confirmada");

  // Saldos finales.
  const finales = await get(request, c, `/inventory/balances?product_id=${m.product}`);
  const porEstado: Record<string, number> = {};
  for (const b of finales.items as Array<{ state: string; qty_on_hand: string }>) {
    porEstado[b.state] = Number(b.qty_on_hand);
  }
  expect(porEstado.DISPONIBLE).toBe(60);
  expect(porEstado.RECHAZADO).toBe(20);
  expect(porEstado.RECIBIDO ?? 0).toBe(0);
  expect(Object.values(porEstado).reduce((a, b) => a + b, 0)).toBe(80);
  const confirmadas = await get(request, c, `/purchasing/receipts/${m.receipt}/confirmacion-inventario`);
  expect(confirmadas.items.length).toBe(2);

  // Plan final coherente.
  const planFinal = await get(
    request,
    c,
    `/planning/plan?warehouse_id=${m.almacen}&product_id=${m.product}`,
  );
  expect(planFinal.received_unconfirmed).toBe("0.000000");
  expect(planFinal.available).toBe("60.000000");
  expect(Number(planFinal.projected_available)).toBe(
    Number(planFinal.available) + Number(planFinal.open_supply) + Number(planFinal.received_unconfirmed),
  );

  // Segunda confirmación impedida.
  const segunda = await postCruda(request, c, `/purchasing/receipts/${m.receipt}/confirmacion-inventario`, {
    decisions: [
      { receipt_line_id: m.line, target_state: "DISPONIBLE", base_quantity: "60" },
      { receipt_line_id: m.line, target_state: "RECHAZADO", base_quantity: "20", reason: "No apto" },
    ],
  });
  expect(segunda.status()).toBe(409);
  expect((await segunda.json()).code).toBe("ALREADY_CONFIRMED");
  const confirmadasFinal = await get(request, c, `/purchasing/receipts/${m.receipt}/confirmacion-inventario`);
  expect(confirmadasFinal.items.length).toBe(2);
});
