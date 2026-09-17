/**
 * Spec 054 · E2E-HELPER-EMPRESA-AMBIGUO — el ayudante de empresa, bajo prueba.
 *
 * La infraestructura de pruebas también se prueba. Doce fallos repartidos en cuatro
 * ficheros venían de un selector que buscaba «Activar» por subcadena y encontraba
 * «Desactivar»: el ayudante apagaba la empresa que necesitaba encendida.
 *
 * Lo que aquí se fija es que eso no pueda volver sin que alguien se entere.
 */
import { expect, test, type Page } from "@playwright/test";

import { activarEmpresa, controlesDeEmpresa } from "./helpers/empresa";

const TENANT = process.env.KONTROL_E2E_TENANT ?? "DEMO";
const USER = process.env.KONTROL_E2E_USER ?? "admin";
const PASSWORD = process.env.KONTROL_E2E_PASSWORD ?? "";

async function entrar(page: Page): Promise<void> {
  await page.goto("/login");
  await page.getByLabel(/Empresa \(código\)/).fill(TENANT);
  await page.getByLabel(/Usuario/).fill(USER);
  await page.getByLabel(/Contraseña/).fill(PASSWORD);
  await page.getByRole("button", { name: "Iniciar sesión" }).click();
  await page.waitForURL((u) => !u.pathname.includes("login"), { timeout: 20000 });
}

test.describe("Spec 054 · el ayudante de empresa", () => {
  test("el localizador de «Activar» nunca alcanza «Desactivar»", async ({ page }) => {
    await entrar(page);
    await activarEmpresa(page);
    const { activar, desactivar, activa } = controlesDeEmpresa(page);

    // Estado activo: los controles exactos son los del estado activo y ninguno más.
    await expect(desactivar).toHaveCount(1);
    await expect(activa).toHaveCount(1);
    await expect(activar).toHaveCount(0);

    // El defecto histórico, fijado como regresión: por subcadena «Activar» sí alcanza
    // un control, y ese control se llama «Desactivar». Por eso `exact` no es cosmético.
    const ambiguo = page.getByRole("button", { name: "Activar" });
    expect(await ambiguo.count()).toBeGreaterThan(await activar.count());
    expect((await ambiguo.allInnerTexts()).map((t) => t.trim())).toEqual(["Desactivar"]);
  });

  test("es idempotente: pedir la empresa que ya está activa no la apaga", async ({ page }) => {
    await entrar(page);
    const { activar, desactivar, activa } = controlesDeEmpresa(page);

    await activarEmpresa(page);
    await expect(desactivar).toHaveCount(1);

    // Segunda llamada sobre el estado ya alcanzado: exactamente el caso que rompía.
    await activarEmpresa(page);
    await expect(desactivar).toHaveCount(1);
    await expect(activa).toHaveCount(1);
    await expect(activar).toHaveCount(0);

    // Y una tercera, por si el daño fuera acumulativo.
    await activarEmpresa(page);
    await expect(desactivar).toHaveCount(1);
  });

  test("desde el estado contrario converge y verifica la postcondición", async ({ page }) => {
    await entrar(page);
    await activarEmpresa(page);
    const { activar, desactivar, activa } = controlesDeEmpresa(page);

    // Al desactivar, el producto retira la tabla y muestra la compuerta de selección:
    // ese es el estado real «sin empresa», y el ayudante tiene que saber resolverlo.
    await desactivar.click();
    await expect(page.getByRole("heading", { name: "Seleccione una empresa", level: 1 }))
      .toBeVisible({ timeout: 15000 });
    await expect(activar).toHaveCount(0);

    await activarEmpresa(page);
    await expect(desactivar).toHaveCount(1);
    await expect(activa).toHaveCount(1);
  });

  test("la empresa activa es la que el contexto usa de verdad", async ({ page }) => {
    await entrar(page);
    await activarEmpresa(page);

    // La postcondición no se queda en la pantalla de empresas: el Topbar nombra la
    // empresa activa, que es lo que el resto de la aplicación consume. Con una sola
    // empresa el producto muestra el contexto sin control de cambio —no hay nada que
    // elegir—, así que se comprueba el indicador, que es lo que existe de verdad.
    const indicador = page.getByTestId("empresa-activa");
    await expect(indicador).toBeVisible({ timeout: 15000 });
    await expect(indicador).not.toHaveText("Seleccione una empresa");
  });
});
