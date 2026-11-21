/**
 * E2E V4 · transferencia con valor, recepción por línea y reversión (P3 Enterprise).
 *
 * Frontend real → API real → PostgreSQL real. El estado final solo se alcanza por la
 * interfaz; la API se usa para sembrar existencia valorada y para leer la valoración.
 *
 * Recorrido de la dueña: stock valorizado en A → transferir 4 → recibir 3 y luego 1 →
 * A pierde exactamente el valor que gana B y el total no cambia → revertir con motivo →
 * cantidades y valor vuelven a A.
 */
import AxeBuilder from "@axe-core/playwright";
import { type APIRequestContext, type Page } from "@playwright/test";

import { activarEmpresa } from "./helpers/empresa";
import { entrar, expect, test } from "./helpers/sesion";
import { ctx, get, marca, post, type Ctx } from "./helpers/ventas";

const TENANT = process.env.KONTROL_E2E_TENANT ?? "DEMO";
const USER = process.env.KONTROL_E2E_USER ?? "admin";
const API = process.env.KONTROL_E2E_API ?? "http://127.0.0.1:8000/api/v1";
const WCAG_TAGS = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"];

type Escenario = { origen: string; destino: string; producto: { id: string; code: string; name: string }; m: string };

async function tipoEntrada(request: APIRequestContext, c: Ctx): Promise<string> {
  const buscar = async (): Promise<{ id: string } | undefined> => {
    const tipos = await get(request, c, "/inventory/movement-types");
    return (tipos.items ?? tipos).find((x: { code: string }) => x.code === "ENTRADA_RECEPCION");
  };
  let tipo = await buscar();
  if (!tipo) {
    const creado = await request.post(`${API}/inventory/movement-types`, {
      headers: c.headers,
      data: { code: "ENTRADA_RECEPCION", name: "Entrada por recepción", direction: "IN" },
    });
    if (creado.ok()) {
      tipo = (await creado.json()) as { id: string };
    } else {
      expect((await creado.json()).code).toBe("MOVEMENT_TYPE_DUPLICATE");
      tipo = await buscar();
    }
  }
  if (!tipo) throw new Error("No existe el tipo de movimiento ENTRADA_RECEPCION");
  return tipo.id;
}

async function sembrar(request: APIRequestContext, c: Ctx): Promise<Escenario> {
  const m = marca();
  const almacen = async (sufijo: string): Promise<string> =>
    (await post(request, c, "/organization/warehouses", {
      company_id: c.company, code: `V4${sufijo}-${m}`, name: `Almacén V4 ${sufijo} ${m}`,
      warehouse_type: "PHYSICAL", status: "ACTIVE",
    })).id as string;
  const origen = await almacen("A");
  const destino = await almacen("B");
  const producto = await post(request, c, "/maestros/catalogos/items", {
    code: `V4P-${m}`, name: `Artículo V4 ${m}`, item_type: "PRODUCT", status: "ACTIVE",
  });
  await post(request, c, "/inventory/movements", {
    warehouse_id: origen, product_id: producto.id, movement_type_id: await tipoEntrada(request, c),
    quantity: 10, unit_cost: 10, currency: "VED", fiscal_rate: null, document_ref: `REC-V4-${m}`, location_id: null,
  });
  return { origen, destino, producto: { id: producto.id, code: producto.code, name: producto.name }, m };
}

async function valor(request: APIRequestContext, c: Ctx, productId: string, warehouseId?: string): Promise<number> {
  const q = warehouseId ? `&warehouse_id=${warehouseId}` : "";
  const r = await get(request, c, `/inventory/valuation?product_id=${productId}${q}`);
  return Number(r.valuation);
}

async function irATransferencias(page: Page): Promise<void> {
  await entrar(page, USER, { tenant: TENANT });
  await activarEmpresa(page);
  await page.locator('nav a[href="/inventario/transferencias"]').first().click();
  await page.waitForURL((u) => u.pathname === "/inventario/transferencias", { timeout: 15000 });
  await expect(page.getByRole("heading", { name: "Transferencias" })).toBeVisible();
}

async function accionDeFila(page: Page, codigo: string, boton: string): Promise<void> {
  const fila = page.locator("tr", { hasText: codigo });
  const [r] = await Promise.all([
    page.waitForResponse((x) => x.url().includes("/inventory/transfers/") && x.url().endsWith("/transition")
      && x.request().method() === "POST", { timeout: 15000 }),
    fila.getByRole("button", { name: boton }).click(),
  ]);
  expect(r.status(), await r.text()).toBe(200);
}

async function axe(page: Page, ancho: number, alto: number): Promise<void> {
  await page.setViewportSize({ width: ancho, height: alto });
  await page.waitForLoadState("networkidle");
  const resultado = await new AxeBuilder({ page }).withTags(WCAG_TAGS).analyze();
  const graves = resultado.violations.filter((v) => v.impact === "serious" || v.impact === "critical");
  expect(graves.map((v) => `${v.id}: ${v.nodes.map((n) => n.target.join(" ")).join(", ")}`),
    `Axe a ${ancho}px`).toEqual([]);
  const desborde = await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth + 1);
  expect(desborde, `desbordamiento horizontal a ${ancho}px`).toBe(false);
}

test.describe("V4 · transferencia con valor y reversión", () => {
  test("E2E-V4-01: transferir, recibir por partes, conservar el valor y revertir", async ({ page, request }) => {
    const c = await ctx(request);
    const e = await sembrar(request, c);
    expect(await valor(request, c, e.producto.id)).toBeCloseTo(100, 2);

    await irATransferencias(page);
    const codigo = `TR-${e.m}`;
    await page.getByLabel("Código").fill(codigo);
    await page.getByLabel("Almacén origen").selectOption(e.origen);
    await page.getByLabel("Almacén destino").selectOption(e.destino);
    const selector = page.getByRole("combobox", { name: /^Producto/ });
    await selector.click();
    await selector.pressSequentially(e.producto.code);
    await page.getByRole("option", { name: new RegExp(e.producto.code) }).click();
    await page.getByLabel("Cantidad").fill("4");
    await page.getByRole("button", { name: "Crear" }).click();
    const fila = page.locator("tr", { hasText: codigo });
    await expect(fila).toContainText("Borrador");
    await expect(fila).toContainText(`V4A-${e.m}`);
    await expect(fila).toContainText(`V4B-${e.m}`);

    const lista = await get(request, c, "/inventory/transfers?page_size=100");
    const idTransferencia = (lista.items as Array<{ id: string; code: string }>).find((x) => x.code === codigo)?.id ?? "";
    expect(idTransferencia).not.toBe("");

    await accionDeFila(page, codigo, "Enviar a aprobación");
    await accionDeFila(page, codigo, "Aprobar");
    await accionDeFila(page, codigo, "Confirmar envío");
    await expect(fila).toContainText("En tránsito");
    await expect(fila).toContainText("40.00");
    expect(await valor(request, c, e.producto.id, e.origen)).toBeCloseTo(60, 2);

    // Recepción parcial: llegan 3 de 4.
    await page.getByLabel("Transferencia que llega").selectOption(idTransferencia);
    const recibir = page.getByLabel(/^Recibir ahora · /);
    await expect(recibir).toHaveValue("4");
    await recibir.fill("3");
    await page.getByRole("button", { name: "Registrar recepción" }).click();
    await expect(fila).toContainText("Recibida parcialmente");
    await expect(fila).toContainText("10.00");

    // Llega el resto.
    await page.getByLabel("Transferencia que llega").selectOption(idTransferencia);
    await expect(page.getByLabel(/^Recibir ahora · /)).toHaveValue("1");
    await page.getByRole("button", { name: "Registrar recepción" }).click();
    await expect(fila).toContainText("Recibida");
    await expect(fila).not.toContainText("Recibida parcialmente");

    expect(await valor(request, c, e.producto.id, e.origen)).toBeCloseTo(60, 2);
    expect(await valor(request, c, e.producto.id, e.destino)).toBeCloseTo(40, 2);
    expect(await valor(request, c, e.producto.id)).toBeCloseTo(100, 2);

    // Trazabilidad: el historial del producto muestra la salida y las entradas.
    const movimientos = await get(request, c, `/inventory/movements?product_id=${e.producto.id}&page_size=50`);
    const refs = (movimientos.items as Array<{ document_ref: string | null; quantity: number }>)
      .filter((x) => (x.document_ref ?? "").startsWith("TRANSFER:"));
    expect(refs.reduce((s, x) => s + Number(x.quantity), 0)).toBeCloseTo(0, 6);

    await axe(page, 1280, 900);
    await axe(page, 390, 844);
    await axe(page, 320, 720);
    await page.setViewportSize({ width: 1280, height: 900 });

    // Reversión con motivo: todo vuelve a A.
    await page.getByLabel("Transferencia recibida").selectOption(idTransferencia);
    await page.getByRole("button", { name: "Revertir" }).click();
    await expect(page.getByText("Falta el motivo")).toBeVisible();
    await page.getByLabel("Motivo").fill("Destino equivocado");
    const [rev] = await Promise.all([
      page.waitForResponse((x) => x.url().endsWith("/reverse") && x.request().method() === "POST", { timeout: 15000 }),
      page.getByRole("button", { name: "Revertir" }).click(),
    ]);
    expect(rev.status(), await rev.text()).toBe(200);
    await expect(fila).toContainText("Revertida");
    expect(await valor(request, c, e.producto.id, e.origen)).toBeCloseTo(100, 2);
    expect(await valor(request, c, e.producto.id, e.destino)).toBeCloseTo(0, 2);
    expect(await valor(request, c, e.producto.id)).toBeCloseTo(100, 2);
    await expect(page.getByLabel("Transferencia recibida").locator("option", { hasText: codigo })).toHaveCount(0);
  });
});
