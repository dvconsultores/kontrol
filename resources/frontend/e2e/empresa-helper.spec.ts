/**
 * Spec 054 · E2E-HELPER-EMPRESA-AMBIGUO — el ayudante de empresa, bajo prueba.
 *
 * La infraestructura de pruebas también se prueba. Doce fallos repartidos en cuatro
 * ficheros venían de un selector que buscaba «Activar» por subcadena y encontraba
 * «Desactivar»: el ayudante apagaba la empresa que necesitaba encendida.
 *
 * Lo que aquí se fija es que eso no pueda volver sin que alguien se entere.
 */
import { expect, test, type Locator, type Page } from "@playwright/test";

import {
  activarEmpresa,
  controlesDeEmpresa,
  emitirLaTablaTarde,
  esperarEstadoDeEmpresa,
  leerEstadoDeEmpresa,
} from "./helpers/empresa";

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
  /**
   * La carrera de pintado (E2E-HELPER-EMPRESA-CARRERA-DE-PINTADO), reproducida a voluntad
   * con `emitirLaTablaTarde`: la petición de la tabla sale 2 s después de que la página
   * la pida, mucho más que la ventana de 500 ms de `networkidle`. Con el ayudante antiguo
   * esta prueba fallaba en el acto con «estado de empresa no determinable: activar=0
   * compuerta=0 activa=0 desactivar=0» (corrida `r20261013t183318…`).
   */
  test("HE-02 · con la petición de la tabla emitida tarde, el ayudante espera a que se pinte y acierta", async ({ page }) => {
    await emitirLaTablaTarde(page, 2000);
    await entrar(page);
    const { activar, desactivar, activa } = controlesDeEmpresa(page);
    await activarEmpresa(page);
    await expect(desactivar).toHaveCount(1);
    await expect(activa).toHaveCount(1);
    await expect(activar).toHaveCount(0);
  });

  test("HE-06 · mientras no hay nada pintado la lectura es NO_LISTA, no un fallo, y la espera acaba en ACTIVA", async ({ page }) => {
    await emitirLaTablaTarde(page, 2000);
    await entrar(page);
    await page.locator('nav a[href="/organizacion/empresas"]').first().click();
    await page.waitForURL((u) => u.pathname === "/organizacion/empresas", { timeout: 15000 });
    const compuerta = page.getByTestId(/^elegir-empresa-/);
    const transitoria = await leerEstadoDeEmpresa(page, compuerta);
    expect(transitoria.estado, JSON.stringify(transitoria)).toBe("NO_LISTA");
    const lectura = await esperarEstadoDeEmpresa(page, compuerta);
    expect(lectura.estado).toBe("ACTIVA");
    expect([lectura.desactivar, lectura.activa, lectura.compuerta]).toEqual([1, 1, 0]);
  });

  test("HE-05 · la pareja «Activa» + «Desactivar» es UN estado: ACTIVA, nunca ambiguo", async ({ page }) => {
    await entrar(page);
    await activarEmpresa(page);
    const lectura = await esperarEstadoDeEmpresa(page, page.getByTestId(/^elegir-empresa-/));
    expect(lectura.estado).toBe("ACTIVA");
    expect(lectura.desactivar).toBe(1);
    expect(lectura.activa).toBe(1);
  });

  /** Un control impostor inyectado solo en el DOM de la prueba: el producto no cambia. */
  async function inyectarBoton(page: Page, texto: string): Promise<void> {
    await page.evaluate((t) => {
      const boton = document.createElement("button");
      boton.type = "button";
      boton.textContent = t;
      document.body.appendChild(boton);
    }, texto);
  }

  test("HE-07 · una lectura contradictoria es AMBIGUO y, si persiste, la espera falla con el diagnóstico", async ({ page }) => {
    await entrar(page);
    await activarEmpresa(page);
    const compuerta: Locator = page.getByTestId(/^elegir-empresa-/);
    await inyectarBoton(page, "Desactivar");
    const lectura = await leerEstadoDeEmpresa(page, compuerta);
    expect(lectura.estado, JSON.stringify(lectura)).toBe("AMBIGUO");
    expect(lectura.desactivar).toBe(2);
    // Lo contradictorio no se resuelve esperando: al agotar el tiempo, el diagnóstico dice lo que hay.
    await expect(esperarEstadoDeEmpresa(page, compuerta, 1500)).rejects.toThrow(/AMBIGUO: activar=0 compuerta=0 activa=1 desactivar=2/);
  });

  test("HE-10 · más de una empresa activa no es una postcondición válida", async ({ page }) => {
    await entrar(page);
    await activarEmpresa(page);
    await inyectarBoton(page, "Activa");
    await inyectarBoton(page, "Desactivar");
    await expect(activarEmpresa(page)).rejects.toThrow(/no determinable[\s\S]*AMBIGUO: activar=0 compuerta=0 activa=2 desactivar=2/);
  });

  test("HE-08 · si la tabla no llega nunca, el ayudante falla en su tiempo de siempre, con el diagnóstico", async ({ page }) => {
    await emitirLaTablaTarde(page, null);
    await entrar(page);
    const inicio = Date.now();
    await expect(activarEmpresa(page)).rejects.toThrow(/no determinable[\s\S]*NO_LISTA: activar=0 compuerta=0 activa=0 desactivar=0/);
    expect(Date.now() - inicio).toBeLessThan(25000);
  });

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
