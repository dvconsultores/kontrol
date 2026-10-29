/**
 * ISOLATION-E2E del ciclo 07: la empresa A no ve datos de B (mismo tenant) ni
 * de C (otro tenant), ni por URL directa, ni por búsqueda, ni en ninguna
 * respuesta JSON de la API que la UI pide. Requiere la siembra de
 * `qa/n6_world.py`.
 */
import { type Page } from "@playwright/test";

import { mundoN6 } from "./helpers/n6-mundo";
import { entrar as entrarConSesion, expect, test } from "./helpers/sesion";

const IDS = mundoN6();

const TENANT = "DEMO";

type Captura = { url: string; texto: string };

async function entrar(page: Page, usuario: string, tenant = TENANT): Promise<void> {
  await entrarConSesion(page, usuario, { tenant });
  await expect(page).toHaveURL(/\/$/, { timeout: 20_000 });
}

async function registrarCaptura(page: Page, capturas: Captura[]): Promise<void> {
  await page.route("**/api/v1/**", async (route) => {
    const respuesta = await route.fetch();
    const tipo = respuesta.headers()["content-type"] ?? "";
    if (tipo.includes("application/json")) {
      capturas.push({ url: route.request().url(), texto: await respuesta.text() });
    }
    await route.fulfill({ response: respuesta });
  });
}

async function verificarSinFugas(capturas: Captura[]): Promise<void> {
  const ofensores = [
    IDS.doc_b,
    IDS.doc_c,
    IDS.prod_b,
    IDS.prod_c,
    IDS.tercero_b,
    IDS.tercero_c,
  ];
  expect(capturas.length, "ninguna respuesta de la API se capturó").toBeGreaterThan(0);
  for (const { url, texto } of capturas) {
    for (const ofensor of ofensores) {
      expect(texto, `URL ofensora: ${url}`).not.toContain(ofensor);
    }
  }
}

test.describe("ISOLATION-E2E: la empresa A no ve a B ni a C", () => {
  test.beforeEach(async ({ page }) => {
    await entrar(page, "ua");
  });

  test("URL directa al documento de B y de C", async ({ page }) => {
    const capturas: Captura[] = [];
    await registrarCaptura(page, capturas);

    await page.goto(`/documentos/${IDS.documento_b}`);
    await page.waitForLoadState("networkidle");
    await expect(
      page.getByRole("heading", { name: "No fue posible completar la operación" }),
    ).toBeVisible();
    await expect(page.getByText(IDS.doc_b)).toHaveCount(0);

    await page.goto(`/documentos/${IDS.documento_c}`);
    await page.waitForLoadState("networkidle");
    await expect(
      page.getByRole("heading", { name: "No fue posible completar la operación" }),
    ).toBeVisible();
    await expect(page.getByText(IDS.doc_c)).toHaveCount(0);

    await verificarSinFugas(capturas);
  });

  test("URL directa a las presentaciones del producto de B y de C", async ({ page }) => {
    const capturas: Captura[] = [];
    await registrarCaptura(page, capturas);

    await page.goto(`/maestros/productos/${IDS.producto_b}/presentaciones`);
    await page.waitForLoadState("networkidle");
    await expect(page.getByText(IDS.prod_b)).toHaveCount(0);
    const botonB = page.getByRole("button", { name: /nueva presentación/i });
    if (await botonB.count()) {
      await expect(botonB.first()).toBeDisabled();
    }

    await page.goto(`/maestros/productos/${IDS.producto_c}/presentaciones`);
    await page.waitForLoadState("networkidle");
    await expect(page.getByText(IDS.prod_c)).toHaveCount(0);
    const botonC = page.getByRole("button", { name: /nueva presentación/i });
    if (await botonC.count()) {
      await expect(botonC.first()).toBeDisabled();
    }

    await verificarSinFugas(capturas);
  });

  test("Búsqueda en terceros: B y C no aparecen, A sí", async ({ page }) => {
    const capturas: Captura[] = [];
    await registrarCaptura(page, capturas);

    await page.goto("/maestros/terceros");
    await page.waitForLoadState("networkidle");

    const campo = page.getByLabel("Buscar");

    await campo.fill("SOLO-DE-B");
    await page.waitForLoadState("networkidle");
    await expect(page.getByText(IDS.tercero_b)).toHaveCount(0);
    await expect(page.getByText(IDS.tercero_c)).toHaveCount(0);

    await campo.fill("SOLO-DE-C");
    await page.waitForLoadState("networkidle");
    await expect(page.getByText(IDS.tercero_b)).toHaveCount(0);
    await expect(page.getByText(IDS.tercero_c)).toHaveCount(0);

    await campo.fill("SOLO-DE-A");
    await page.waitForLoadState("networkidle");
    await expect(page.getByRole("cell", { name: IDS.tercero_a, exact: true })).toBeVisible();

    await verificarSinFugas(capturas);
  });
});
