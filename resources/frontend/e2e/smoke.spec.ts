/**
 * Smoke test E2E (Playwright): la app carga y el login se muestra.
 * Requiere backend + frontend levantados (compose.dev).
 */
import { expect, test } from "@playwright/test";

test("la aplicación carga la pantalla de login", async ({ page }) => {
  await page.goto("/login");
  await expect(page).toHaveTitle(/KONTROL/);
  await expect(page.getByRole("heading", { name: /KONTROL/ })).toBeVisible();
  await expect(page.getByText("Inicie sesión para continuar")).toBeVisible();
  await expect(page.getByRole("button", { name: "Iniciar sesión" })).toBeVisible();
});

test("los campos del login son accesibles por label", async ({ page }) => {
  await page.goto("/login");
  await expect(page.getByLabel(/Empresa \(código\)/)).toBeVisible();
  await expect(page.getByLabel(/Usuario/)).toBeVisible();
  await expect(page.getByLabel(/Contraseña/)).toBeVisible();
});
