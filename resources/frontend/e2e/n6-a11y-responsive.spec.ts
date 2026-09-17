/**
 * Selector de empresa: accesibilidad y adaptación (ARCH-MC-001, N6).
 *
 * El selector es un control nuevo en el shell, presente en todas las pantallas.
 * Si no se puede usar con teclado o rompe la cabecera en un móvil, el trabajo
 * multiempresa queda inaccesible por la puerta de entrada.
 */
import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page } from "@playwright/test";

import { mundoN6 } from "./helpers/n6-mundo";

const IDS = mundoN6();
const TENANT = "DEMO";
const PASS = "Kontrol2026Segura!";
const WCAG = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"];

/** Cierra las notificaciones: al ancho de un móvil tapan la cabecera. */
async function cerrarAvisos(page: Page): Promise<void> {
  for (const cerrar of await page.getByRole("button", { name: "Cerrar notificación" }).all()) {
    await cerrar.click().catch(() => undefined);
  }
}

async function entrar(page: Page, usuario: string): Promise<void> {
  await page.goto("/login");
  await page.getByLabel(/Empresa \(código\)/).fill(TENANT);
  await page.getByLabel(/Usuario/).fill(usuario);
  await page.getByLabel(/Contraseña/).fill(PASS);
  await page.getByRole("button", { name: "Iniciar sesión" }).click();
  await expect(page).toHaveURL(/\/$/, { timeout: 20_000 });
}

async function sinViolacionesSerias(page: Page, contexto: string): Promise<void> {
  const r = await new AxeBuilder({ page }).withTags(WCAG).analyze();
  const graves = r.violations.filter((v) => v.impact === "critical" || v.impact === "serious");
  expect(graves.map((v) => `${v.id}: ${v.help}`), `violaciones en ${contexto}`).toEqual([]);
}

test.describe("accesibilidad del contexto de empresa", () => {
  test("la pantalla de selección no tiene violaciones serias", async ({ page }) => {
    await entrar(page, "uab");
    await expect(page.getByRole("heading", { name: "Seleccione una empresa" })).toBeVisible();
    await sinViolacionesSerias(page, "pantalla de selección");
  });

  test("el selector abierto no tiene violaciones serias", async ({ page }) => {
    await entrar(page, "uab");
    await page.getByTestId("elegir-empresa-D1").click();
    await page.getByTestId("selector-empresa").click();
    await expect(page.getByRole("listbox")).toBeVisible();
    await sinViolacionesSerias(page, "selector abierto");
  });

  test("se opera con teclado de principio a fin", async ({ page }) => {
    await entrar(page, "uab");
    await page.getByTestId("elegir-empresa-D1").click();

    const boton = page.getByTestId("selector-empresa");
    await boton.focus();
    // Abrir, bajar a la segunda empresa y confirmar, sin tocar el ratón.
    await page.keyboard.press("ArrowDown");
    await expect(page.getByRole("listbox")).toBeVisible();
    await page.keyboard.press("ArrowDown");
    await page.keyboard.press("Enter");

    await expect(boton).toContainText(IDS.nombre_b);
    // El foco vuelve al botón: perderlo dejaría al usuario de teclado al
    // principio del documento después de cada cambio.
    await expect(boton).toBeFocused();
  });

  test("Escape cierra sin cambiar la empresa", async ({ page }) => {
    await entrar(page, "uab");
    await page.getByTestId("elegir-empresa-D1").click();
    const boton = page.getByTestId("selector-empresa");
    await boton.click();
    await expect(page.getByRole("listbox")).toBeVisible();
    await page.keyboard.press("Escape");
    await expect(page.getByRole("listbox")).toHaveCount(0);
    await expect(boton).toContainText(IDS.nombre_a);
    await expect(boton).toBeFocused();
  });

  test("el botón anuncia la empresa activa y su función", async ({ page }) => {
    await entrar(page, "uab");
    await page.getByTestId("elegir-empresa-D1").click();
    const boton = page.getByTestId("selector-empresa");
    const etiqueta = await boton.getAttribute("aria-label");
    expect(etiqueta).toContain(IDS.nombre_a);
    expect(etiqueta).toContain("Cambiar de empresa");
    expect(await boton.getAttribute("aria-haspopup")).toBe("listbox");
    expect(await boton.getAttribute("aria-expanded")).toBe("false");
  });

  test("la empresa activa se distingue sin depender del color", async ({ page }) => {
    await entrar(page, "uab");
    await page.getByTestId("elegir-empresa-D1").click();
    await page.getByTestId("selector-empresa").click();
    const opciones = page.getByRole("option");
    // `aria-selected` lo dice al lector de pantalla; el icono, a quien no
    // distingue el color.
    await expect(opciones.filter({ hasText: IDS.nombre_a })).toHaveAttribute("aria-selected", "true");
    await expect(opciones.filter({ hasText: IDS.nombre_b })).toHaveAttribute("aria-selected", "false");
  });
});

test.describe("el selector en cada tamaño", () => {
  const TAMANOS = [
    { ancho: 320, alto: 640, nombre: "móvil pequeño" },
    { ancho: 375, alto: 667, nombre: "móvil" },
    { ancho: 768, alto: 1024, nombre: "tableta" },
    { ancho: 1024, alto: 768, nombre: "portátil" },
    { ancho: 1280, alto: 800, nombre: "escritorio" },
    { ancho: 1440, alto: 900, nombre: "escritorio ancho" },
  ];

  for (const { ancho, alto, nombre } of TAMANOS) {
    test(`${nombre} (${ancho}px): usable y sin desbordar`, async ({ page }) => {
      await page.setViewportSize({ width: ancho, height: alto });
      await entrar(page, "uab");
      await page.getByTestId("elegir-empresa-D1").click();
      await cerrarAvisos(page);

      const boton = page.getByTestId("selector-empresa");
      await expect(boton).toBeVisible();

      // El nombre de la empresa B es largo a propósito en el arranque: si el
      // selector no lo recorta, empuja la cabecera y aparece scroll horizontal.
      const caja = await boton.boundingBox();
      expect(caja, "el selector no tiene caja").not.toBeNull();
      expect(caja!.width).toBeLessThanOrEqual(ancho);
      // Objetivo táctil suficiente en los tamaños pequeños.
      if (ancho <= 375) {
        expect(caja!.height).toBeGreaterThanOrEqual(24);
      }

      const desborda = await page.evaluate(() =>
        document.documentElement.scrollWidth > document.documentElement.clientWidth + 1);
      expect(desborda, "la página desborda en horizontal").toBe(false);

      // Y sigue pudiéndose cambiar de empresa.
      await boton.click();
      await expect(page.getByRole("listbox")).toBeVisible();
      await page.getByTestId("opcion-empresa-D2").click();
      await expect(boton).toContainText(IDS.nombre_b);
    });
  }
});
