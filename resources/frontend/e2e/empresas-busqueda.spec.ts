/**
 * EMP-Q · la búsqueda de Empresas, en un navegador real (FR-001-065).
 *
 * La caja existía y enviaba `q`; el servidor lo ignoraba y la tabla enseñaba la
 * lista entera con 200. Aquí se entra por el menú, se escribe y se mira lo que
 * queda en la tabla, que es lo único que una persona ve.
 *
 * El mundo es el que siembra `qa/e2e-seed.sh`: `uab` opera en las dos empresas
 * de DEMO; `uc`, en la única de DEMO2. Los nombres se leen del mundo sembrado,
 * no se escriben a mano.
 */
import { expect, test, type Page } from "@playwright/test";

import { mundoN6 } from "./helpers/n6-mundo";

const PASSWORD = process.env.KONTROL_E2E_PASSWORD ?? "";

async function entrar(page: Page, tenant: string, usuario: string): Promise<void> {
  await page.goto("/login");
  await page.getByLabel(/Empresa \(código\)/).fill(tenant);
  await page.getByLabel(/Usuario/).fill(usuario);
  await page.getByLabel(/Contraseña/).fill(PASSWORD);
  await page.getByRole("button", { name: "Iniciar sesión" }).click();
  await page.waitForURL((u) => !u.pathname.includes("login"), { timeout: 20000 });
  await page.waitForLoadState("networkidle");
  // Con varias empresas el producto pide elegir una antes de operar.
  const compuerta = page.getByTestId(/^elegir-empresa-/);
  if (await compuerta.count()) {
    await compuerta.first().click();
    await page.waitForLoadState("networkidle");
  }
}

async function irAEmpresas(page: Page): Promise<void> {
  await page.locator('nav a[href="/organizacion/empresas"]').first().click();
  await page.waitForURL((u) => u.pathname === "/organizacion/empresas", { timeout: 15000 });
  await page.waitForLoadState("networkidle");
}

function fila(page: Page, nombre: string) {
  return page.getByRole("row", { name: new RegExp(nombre.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")) });
}

test.describe("EMP-Q · búsqueda general de Empresas", () => {
  const mundo = mundoN6();

  test("EMP-Q-01 · buscar la razón social de una empresa deja solo esa fila", async ({ page }) => {
    await entrar(page, "DEMO", "uab");
    await irAEmpresas(page);
    await expect(fila(page, mundo.nombre_a)).toBeVisible();
    await expect(fila(page, mundo.nombre_b)).toBeVisible();

    await page.getByLabel("Buscar").fill(mundo.nombre_b);
    await expect(fila(page, mundo.nombre_b)).toBeVisible();
    await expect(fila(page, mundo.nombre_a)).toHaveCount(0);
  });

  test("EMP-Q-02 · un término inexistente deja la tabla vacía, y limpiar la devuelve", async ({ page }) => {
    await entrar(page, "DEMO", "uab");
    await irAEmpresas(page);
    await expect(fila(page, mundo.nombre_a)).toBeVisible();

    await page.getByLabel("Buscar").fill("ZZZ-NO-EXISTE-EMPRESA-Q");
    await expect(page.getByText("Sin empresas")).toBeVisible();
    await expect(fila(page, mundo.nombre_a)).toHaveCount(0);
    await expect(fila(page, mundo.nombre_b)).toHaveCount(0);

    await page.getByRole("button", { name: "Limpiar búsqueda" }).click();
    await expect(fila(page, mundo.nombre_a)).toBeVisible();
    await expect(fila(page, mundo.nombre_b)).toBeVisible();
  });

  test("EMP-Q-03 · la búsqueda no cruza tenants: cada sesión encuentra solo lo suyo", async ({ page }) => {
    await entrar(page, "DEMO", "uab");
    await irAEmpresas(page);
    await page.getByLabel("Buscar").fill(mundo.nombre_c);
    await expect(page.getByText("Sin empresas")).toBeVisible();
    await expect(fila(page, mundo.nombre_c)).toHaveCount(0);
  });

  test("EMP-Q-04 · el otro tenant sí encuentra su empresa con el mismo término", async ({ page }) => {
    await entrar(page, "DEMO2", "uc");
    await irAEmpresas(page);
    await page.getByLabel("Buscar").fill(mundo.nombre_c);
    await expect(fila(page, mundo.nombre_c)).toBeVisible();
    await expect(fila(page, mundo.nombre_b)).toHaveCount(0);
  });

  test("EMP-Q-05 · la búsqueda no distingue mayúsculas, como en terceros", async ({ page }) => {
    await entrar(page, "DEMO", "uab");
    await irAEmpresas(page);
    await page.getByLabel("Buscar").fill(mundo.nombre_b.toLowerCase());
    await expect(fila(page, mundo.nombre_b)).toBeVisible();
    await expect(fila(page, mundo.nombre_a)).toHaveCount(0);
  });
});
