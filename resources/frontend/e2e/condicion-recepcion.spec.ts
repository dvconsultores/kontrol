/**
 * Spec 018 · §3 — condición del proceso de la recepción, de punta a punta.
 *
 * Recorre el ciclo completo sobre PostgreSQL real: pendiente al crear y al
 * contar, bloqueada por una incidencia abierta (con la confirmación impedida),
 * recalculada al resolverla y «Recibido» al confirmar el inventario. Comprueba
 * las dos superficies de la feature —la fila y la ficha de Recepciones— a 1280,
 * 390 y 320, y que la condición sobreviva a una recarga.
 */
import AxeBuilder from "@axe-core/playwright";
import { type Page } from "@playwright/test";

import { expect, test, entrar, sesionApi } from "./helpers/sesion";
import { verificadorDeEscenario } from "./helpers/usuario";

const WCAG = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"];

/** La condición es texto y un enlace: no puede introducir faltas graves. */
async function sinFaltasGraves(page: Page, etiqueta: string): Promise<void> {
  const resultado = await new AxeBuilder({ page }).withTags(WCAG).analyze();
  const graves = resultado.violations
    .filter((v) => v.impact === "critical" || v.impact === "serious")
    .map((v) => ({ id: v.id, impact: v.impact, nodes: v.nodes.length }));
  expect(graves, `${etiqueta}: ${JSON.stringify(graves)}`).toEqual([]);
}

const TENANT = process.env.KONTROL_E2E_TENANT ?? "DEMO";
const USER = process.env.KONTROL_E2E_USER ?? "admin";
const API = process.env.KONTROL_E2E_API ?? "http://127.0.0.1:8000/api/v1";

test.setTimeout(300000);

test("la condición del proceso acompañara la recepción hasta «Recibido»", async ({ page, request }) => {
  const sufijo = Date.now().toString().slice(-8);
  const { token } = await sesionApi(USER, { tenant: TENANT });

  const empresas = await request.get(`${API}/organization/companies`, {
    headers: { Authorization: `Bearer ${token}`, "X-Kontrol-Company": TENANT },
  });
  expect(empresas.ok()).toBeTruthy();
  const companyId = ((await empresas.json()) as { items: Array<{ id: string }> }).items[0].id;
  const authHeaders = {
    Authorization: `Bearer ${token}`,
    "X-Kontrol-Company": companyId,
    "Content-Type": "application/json",
  };
  const post = async <T>(ruta: string, datos: Record<string, unknown>): Promise<T> => {
    const res = await request.post(`${API}${ruta}`, { headers: authHeaders, data: datos });
    expect(res.ok(), `${ruta}: ${res.status()} ${await res.text()}`).toBeTruthy();
    return (await res.json()) as T;
  };
  const proveedor = await post<{ id: string }>("/maestros/terceros", {
    code: `PC-PRV-${sufijo}`,
    name: `Proveedor Condición ${sufijo}`,
    person_type: "JURIDICA",
    roles: ["PROVEEDOR"],
    status: "ACTIVE",
  });
  const articulo = await post<{ id: string }>("/maestros/catalogos/items", {
    code: `PC-ART-${sufijo}`,
    name: `Artículo Condición ${sufijo}`,
    item_type: "PRODUCT",
    status: "ACTIVE",
  });
  const almacen = await post<{ id: string }>("/organization/warehouses", {
    company_id: companyId,
    code: `PC-ALM-${sufijo.slice(-5)}`,
    name: `Almacén Condición ${sufijo}`,
  });
  const orden = await post<{ id: string }>("/purchasing/orders", {
    code: `PC-OC-${sufijo}`,
    supplier_id: proveedor.id,
    currency: "VED",
  });
  const lineaOrden = await post<{ id: string }>(`/purchasing/orders/${orden.id}/lines`, {
    product_id: articulo.id,
    quantity_ordered: 100,
    unit_price: 1,
  });
  for (const target of ["SUBMITTED", "APPROVED"]) {
    await post(`/purchasing/orders/${orden.id}/transition`, { target });
  }
  const recepcion = await post<{ id: string }>("/purchasing/receipts", {
    code: `PC-REC-${sufijo}`,
    order_id: orden.id,
    warehouse_id: almacen.id,
  });
  const linea = await post<{ id: string }>(`/purchasing/receipts/${recepcion.id}/lines`, {
    order_line_id: lineaOrden.id,
    product_id: articulo.id,
    quantity_received: 100,
    quantity_accepted: 100,
    quantity_rejected: 0,
  });

  await entrar(page, USER, { tenant: TENANT });
  await page.goto("/compras/recepciones");

  const fila = page.locator("tr", { hasText: `PC-REC-${sufijo}` });
  // 1. Recepción creada: pendiente de validación, en la fila y en la ficha.
  await expect(fila).toContainText("Pendiente de validación");
  await fila.getByRole("button", { name: "detalle" }).click();
  const ficha = page.getByRole("heading", { name: `Inspección de PC-REC-${sufijo}` }).locator("..");
  await expect(ficha).toContainText("Condición del proceso");
  await expect(ficha).toContainText("Pendiente de validación");

  // 2. Aceptada y contada, todavía sin confirmar: sigue pendiente.
  await post(`/purchasing/receipts/${recepcion.id}/confirm`, {});
  await post(`/purchasing/receipts/${recepcion.id}/quality`, {});
  await post(`/purchasing/receipts/${recepcion.id}/quality`, { quality_status: "APPROVED" });
  await post(`/purchasing/receipts/${recepcion.id}/accept`, {});
  const contador = await verificadorDeEscenario(request, { headers: authHeaders }, {
    usuario: `pcc-${sufijo.toLowerCase()}`,
    empresas: [companyId],
  });
  const conteo = await request.post(
    `${API}/purchasing/receipts/${recepcion.id}/lines/${linea.id}/conteo`,
    { headers: { ...contador.headers, "Content-Type": "application/json" },
      data: { counted_base_quantity: "100", difference_kinds: [] } },
  );
  expect(conteo.ok(), await conteo.text()).toBeTruthy();
  await page.reload();
  await expect(page.locator("tr", { hasText: `PC-REC-${sufijo}` })).toContainText("Pendiente de validación");

  // 3. Incidencia abierta: bloqueo visible, motivo y enlace a la incidencia.
  const incidencia = await post<{ id: string }>(`/purchasing/receipts/${recepcion.id}/incidencias`, {
    code: `PC-INC-${sufijo}`,
    incident_type: "DANO",
    receipt_line_id: linea.id,
    affected_base_quantity: 3,
  });
  const impedida = await request.post(
    `${API}/purchasing/receipts/${recepcion.id}/confirmacion-inventario`,
    { headers: authHeaders,
      data: { decisions: [{ receipt_line_id: linea.id, target_state: "DISPONIBLE",
                            base_quantity: "100", source_state: "RECIBIDO" }] } },
  );
  expect(impedida.status(), await impedida.text()).toBe(409);
  expect(((await impedida.json()) as { code: string }).code).toBe("INCIDENTS_UNRESOLVED");

  await page.reload();
  const filaBloqueada = page.locator("tr", { hasText: `PC-REC-${sufijo}` });
  await expect(filaBloqueada).toContainText("Bloqueado por incidencia");
  await filaBloqueada.getByRole("button", { name: "detalle" }).click();
  const fichaBloqueada = page.getByRole("heading", { name: `Inspección de PC-REC-${sufijo}` }).locator("..");
  await expect(fichaBloqueada).toContainText("Bloqueado por incidencia");
  await expect(fichaBloqueada).toContainText("incidencias sin resolver");
  const enlace = fichaBloqueada.getByRole("link", { name: "Ver la incidencia" });
  await expect(enlace).toBeVisible();
  await expect(enlace).toHaveAttribute("href", new RegExp(`recepcion=${recepcion.id}`));
  await expect(fichaBloqueada).not.toContainText(/INCIDENTS_UNRESOLVED|[0-9a-f]{8}-[0-9a-f]{4}-/);
  await sinFaltasGraves(page, "recepciones bloqueadas a 1280");

  // 4. Resuelta: la condición se recalcula sola.
  await post(`/purchasing/receipts/${recepcion.id}/incidencias/${incidencia.id}/resolve`, {
    resolution: "RECLAMO_PROVEEDOR",
    reason: "Reclamo registrado al proveedor.",
  });
  await page.reload();
  await expect(page.locator("tr", { hasText: `PC-REC-${sufijo}` })).toContainText("Pendiente de validación");
  await expect(page.locator("tr", { hasText: `PC-REC-${sufijo}` })).not.toContainText("Bloqueado por incidencia");

  // 5. Confirmación del inventario: el proceso termina en «Recibido».
  const confirmacion = await request.post(
    `${API}/purchasing/receipts/${recepcion.id}/confirmacion-inventario`,
    { headers: authHeaders,
      data: { decisions: [{ receipt_line_id: linea.id, target_state: "DISPONIBLE",
                            base_quantity: "100", source_state: "RECIBIDO" }] } },
  );
  expect(confirmacion.ok(), await confirmacion.text()).toBeTruthy();
  await page.reload();
  await expect(page.locator("tr", { hasText: `PC-REC-${sufijo}` })).toContainText("Recibido");

  // 6. Responsive: la condición se lee sin desplazamiento lateral a 390 y 320.
  for (const ancho of [390, 320]) {
    await page.setViewportSize({ width: ancho, height: 800 });
    await page.goto("/compras/recepciones");
    const filaEstrecha = page.locator("tr", { hasText: `PC-REC-${sufijo}` });
    await expect(filaEstrecha).toContainText("Recibido");
    await expect
      .poll(() => page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth))
      .toBe(true);
  }
});
