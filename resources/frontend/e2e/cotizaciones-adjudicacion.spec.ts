import { ctx, get, marca, post, postCrudo } from "./helpers/ventas";
import { entrar, expect, test } from "./helpers/sesion";

const USER = process.env.KONTROL_E2E_USER ?? "admin";
const TENANT = process.env.KONTROL_E2E_TENANT ?? "DEMO";

test("adjudicar cotización y emitir orden de compra", async ({ page, request }) => {
  const c = await ctx(request);
  const m = marca();

  // Setup: producto y dos proveedores
  const product = await post(request, c, "/maestros/catalogos/items", {
    code: `PQ-${m}`,
    name: `Producto ${m}`,
    item_type: "PRODUCT",
  });
  const supplierCaro = await post(request, c, "/maestros/terceros", {
    code: `PA-${m}`,
    name: `Proveedor Caro ${m}`,
    roles: ["PROVEEDOR"],
  });
  const supplierBarato = await post(request, c, "/maestros/terceros", {
    code: `PB-${m}`,
    name: `Proveedor Barato ${m}`,
    roles: ["PROVEEDOR"],
  });

  // Setup: dos cotizaciones con líneas
  const quoteCaro = await post(request, c, "/purchasing/quotes", {
    code: `CA-${m}`,
    supplier_id: supplierCaro.id,
    currency: "VED",
  });
  const quoteBarato = await post(request, c, "/purchasing/quotes", {
    code: `CB-${m}`,
    supplier_id: supplierBarato.id,
    currency: "VED",
  });
  await post(request, c, `/purchasing/quotes/${quoteCaro.id}/lines`, {
    product_id: product.id,
    quantity: 10,
    unit_price: 12,
    discount: 0,
    delivery_days: 5,
    tax_ref: null,
  });
  await post(request, c, `/purchasing/quotes/${quoteBarato.id}/lines`, {
    product_id: product.id,
    quantity: 10,
    unit_price: 9.5,
    discount: 0,
    delivery_days: 8,
    tax_ref: null,
  });

  // UI: login y navegación
  await entrar(page, USER, { tenant: TENANT });
  await page.goto("/compras/cotizaciones");
  await expect(page.getByRole("heading", { name: "Cotizaciones de compra" })).toBeVisible();
  await page.waitForLoadState("networkidle");

  // Elegir producto en el comparador
  const combobox = page.getByRole("combobox", { name: "Artículo a comparar" });
  await combobox.click();
  await combobox.pressSequentially(`PQ-${m}`);
  await page.getByRole("option", { name: new RegExp(`PQ-${m}`) }).click();
  await expect(combobox).toHaveValue(new RegExp(`PQ-${m}`));

  // Verificar comparación: orden del backend, sin reordenar
  const comparacionSection = page.locator("section", { has: page.getByRole("heading", { name: "Comparar ofertas" }) });
  const comparacionRows = comparacionSection.locator("tbody tr");
  await expect(comparacionRows).toHaveCount(2);

  await expect(comparacionRows.nth(0)).toContainText(`CB-${m}`);
  await expect(comparacionRows.nth(0)).toContainText(`Proveedor Barato ${m}`);
  await expect(comparacionRows.nth(0)).toContainText("95.00");

  await expect(comparacionRows.nth(1)).toContainText(`CA-${m}`);
  await expect(comparacionRows.nth(1)).toContainText(`Proveedor Caro ${m}`);
  await expect(comparacionRows.nth(1)).toContainText("120.00");

  // Adjudicar la oferta barata
  await comparacionRows.nth(0).getByRole("button", { name: `Adjudicar CB-${m}` }).click();
  const dialog = page.getByRole("dialog");
  await dialog.getByLabel("Motivo de la adjudicación").fill("Mejor precio para la importación");
  await dialog.getByRole("button", { name: "Adjudicar" }).click();

  // Verificar adjudicación en tabla principal
  const mainTable = page.locator("table").last();
  const rowCb = mainTable.locator("tbody tr", { hasText: `CB-${m}` });
  await expect(rowCb).toContainText("Adjudicada");

  // El botón de adjudicar desaparece en comparación
  await expect(comparacionRows.nth(0).getByRole("button", { name: `Adjudicar CB-${m}` })).toHaveCount(0);

  // Emitir orden
  await rowCb.getByRole("button", { name: `Emitir orden CB-${m}` }).click();
  const orderDialog = page.getByRole("dialog");
  const orderCodeInput = orderDialog.getByLabel("Código de la orden");
  await expect(orderCodeInput).toHaveValue(`OC-CB-${m}`);
  await orderDialog.getByRole("button", { name: "Emitir orden" }).click();

  // Verificar "Orden emitida" en tabla principal
  await expect(rowCb).toContainText("Orden emitida");

  // Verificaciones API
  const orders = await get(request, c, `/purchasing/orders?q=OC-CB-${m}`);
  expect(orders.items).toHaveLength(1);
  const order = orders.items[0];
  expect(order.status).toBe("DRAFT");
  expect(order.supplier_id).toBe(supplierBarato.id);
  expect(order.quote_id).toBe(quoteBarato.id);
  expect(Number(order.lines[0].unit_price)).toBeCloseTo(9.5);
  expect(Number(order.lines[0].quantity_ordered)).toBe(10);

  const quotes = await get(request, c, "/purchasing/quotes");
  const quoteBaratoFinal = quotes.items.find((q: { id: string }) => q.id === quoteBarato.id);
  expect(quoteBaratoFinal).toBeTruthy();
  expect(quoteBaratoFinal.status).toBe("CONVERTED");
  expect(quoteBaratoFinal.award_reason).toBe("Mejor precio para la importación");

  // Negativo: cotización no adjudicada no puede emitir orden
  const negative = await postCrudo(request, c, `/purchasing/quotes/${quoteCaro.id}/order`, {
    code: `OC-CA-${m}`,
  });
  expect(negative.status()).toBe(409);
  const negativeBody = await negative.json();
  expect(negativeBody.code).toBe("QUOTE_NOT_AWARDED");

  // Responsive
  await page.setViewportSize({ width: 390, height: 844 });
  await page.reload();
  await expect(page.getByRole("heading", { name: "Cotizaciones de compra" })).toBeVisible();
  await expect
    .poll(async () =>
      page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth),
    )
    .toBeTruthy();
});
