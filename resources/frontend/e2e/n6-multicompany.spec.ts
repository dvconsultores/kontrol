/**
 * Multiempresa en el frontend (ARCH-MC-001, N6).
 *
 * Lo que se prueba aquí no es que el selector cambie el nombre en pantalla:
 * es que dos empresas del mismo tenant no se contaminen. Los datos, las
 * peticiones, la caché y los formularios de una no pueden aparecer bajo la
 * otra, y manipular el navegador no puede conceder lo que el servidor niega.
 *
 * Requiere el arranque `qa/n6-multicompany-bootstrap.py`: dos empresas en el
 * tenant DEMO y los usuarios ua / ub / uab.
 */
import { readFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

import { expect, test, type APIRequestContext, type Page } from "@playwright/test";

/**
 * Identificadores del mundo sembrado.
 *
 * Se leen del arranque en vez de codificarlos: sembrar de nuevo genera otros, y
 * una prueba con ids fijos empezaría a pasar por el motivo equivocado —el id ya
 * no existe, así que claro que se rechaza—.
 */
const IDS = JSON.parse(
  readFileSync(process.env.KONTROL_QA_IDS_FILE ?? join(tmpdir(), "kontrol-n6-ids.json"), "utf8"),
) as { empresa_a: string; empresa_b: string; empresa_c: string; tenant_1: string };

const TENANT = "DEMO";
const PASS = "Kontrol2026Segura!";
const CABECERA = "x-kontrol-company";

async function entrar(page: Page, usuario: string, tenant = TENANT): Promise<void> {
  await page.goto("/login");
  await page.getByLabel(/Empresa \(código\)/).fill(tenant);
  await page.getByLabel(/Usuario/).fill(usuario);
  await page.getByLabel(/Contraseña/).fill(PASS);
  await page.getByRole("button", { name: "Iniciar sesión" }).click();
  await expect(page).toHaveURL(/\/$/, { timeout: 20_000 });
}

/** Cabeceras de empresa observadas en la red desde ahora. */
/**
 * Navega por la interfaz, no con `goto`.
 *
 * `page.goto` recarga la aplicación entera: el token vive en memoria, así que
 * cada recarga pasa por restaurar sesión y resolver empresa antes de pedir
 * nada. Para observar qué cabecera lleva una petición hace falta que la
 * petición ocurra dentro de la sesión que ya está viva.
 */
async function irA(page: Page, enlace: RegExp): Promise<void> {
  await page.getByRole("link", { name: enlace }).first().click();
  await page.waitForLoadState("networkidle");
  await page.waitForTimeout(800);
}

function observarEmpresas(page: Page): string[] {
  const vistas: string[] = [];
  page.on("request", (req) => {
    const valor = req.headers()[CABECERA];
    if (valor) vistas.push(valor);
  });
  return vistas;
}

/**
 * Empresas autorizadas, tomadas de la respuesta que pide la propia aplicación.
 *
 * No se piden con un `fetch` desde la página: el token de acceso vive en
 * memoria del módulo, no en una cookie, así que esa petición saldría sin
 * autenticar y devolvería un 401 que no prueba nada.
 */
async function capturarEmpresas(page: Page): Promise<Promise<Empresa[]>> {
  const espera = page.waitForResponse(
    (r) => r.url().includes("/api/v1/organization/companies") && r.status() === 200,
    { timeout: 20_000 });
  return espera.then((r) => r.json() as Promise<Empresa[]>);
}

interface Empresa { id: string; code: string; legal_name: string }

// ==================================================================== flujo 1
test.describe("una sola empresa", () => {
  test("se resuelve sola y opera sin pedir selección", async ({ page }) => {
    const empresas = observarEmpresas(page);
    await entrar(page, "ua");

    // No hay nada que elegir: se muestra el contexto, no un control inútil.
    await expect(page.getByTestId("empresa-activa")).toBeVisible();
    await expect(page.getByTestId("selector-empresa")).toHaveCount(0);
    await expect(page.getByText("Seleccione una empresa")).toHaveCount(0);

    await irA(page, /Terceros/);

    expect(empresas.length, "no salió ninguna petición con empresa").toBeGreaterThan(0);
    const distintas = new Set(empresas);
    expect(distintas.size, `se usaron varias empresas: ${[...distintas]}`).toBe(1);
  });
});

// ==================================================================== flujo 2
test.describe("dos empresas", () => {
  test("exige elegir y no decide por el usuario", async ({ page }) => {
    await entrar(page, "uab");
    // Con dos empresas y sin preferencia previa, elegir la primera por su
    // cuenta sería decidir en qué empresa opera alguien.
    await expect(page.getByRole("heading", { name: "Seleccione una empresa" })).toBeVisible();
    await expect(page.getByTestId("elegir-empresa-D1")).toBeVisible();
    await expect(page.getByTestId("elegir-empresa-D2")).toBeVisible();
  });

  test("cambiar de empresa cambia la cabecera de las peticiones", async ({ page }) => {
    const empresas = capturarEmpresas(page);
    await entrar(page, "uab");
    const [a, b] = await (await empresas);

    await page.getByTestId("elegir-empresa-D1").click();
    const enA = observarEmpresas(page);
    await irA(page, /Terceros/);
    expect(enA.length).toBeGreaterThan(0);
    expect(new Set(enA)).toEqual(new Set([a.id]));

    // Al cambiar de empresa, la pantalla se vuelve a pedir: es el momento donde
    // se vería si alguna petición sale todavía con la empresa anterior.
    const enB = observarEmpresas(page);
    await page.getByTestId("selector-empresa").click();
    await page.getByTestId("opcion-empresa-D2").click();
    await page.waitForLoadState("networkidle");
    await page.waitForTimeout(1200);
    expect(enB.length, "el cambio no provocó ninguna petición").toBeGreaterThan(0);
    expect(new Set(enB), "quedaron peticiones con la empresa anterior").toEqual(new Set([b.id]));
  });

  test("la cabecera nunca lleva el tenant", async ({ page }) => {
    const meCapturado = page.waitForResponse(
      (r) => r.url().includes("/api/v1/auth/me") && r.status() === 200, { timeout: 20_000 },
    ).then((r) => r.json() as Promise<{ user?: { tenant_id?: string } }>);
    const empresas = observarEmpresas(page);
    await entrar(page, "uab");
    await page.getByTestId("elegir-empresa-D1").click();
    await irA(page, /Terceros/);

    // El tenant se toma de la respuesta que la propia aplicación ya recibió.
    const me = await meCapturado;
    const tenant = me?.user?.tenant_id ?? null;
    expect(empresas.length).toBeGreaterThan(0);
    expect(tenant, "no se pudo leer el tenant").toBeTruthy();
    expect(empresas).not.toContain(tenant);
  });

  test("la empresa elegida se recuerda al recargar", async ({ page }) => {
    const empresas = capturarEmpresas(page);
    await entrar(page, "uab");
    const [, b] = await (await empresas);
    await page.getByTestId("elegir-empresa-D2").click();
    await expect(page.getByTestId("selector-empresa")).toContainText("SEGUNDA");

    await page.reload();
    await expect(page.getByTestId("selector-empresa")).toContainText("SEGUNDA");
    const guardada = await page.evaluate(() =>
      window.sessionStorage.getItem("kontrol.company-tab.v1"));
    expect(guardada, "la pestaña no recordó su empresa").toContain(b.id);
  });
});

// ==================================================================== flujo 3
test.describe("aislamiento entre pestañas", () => {
  test("cada pestaña conserva su empresa", async ({ context }) => {
    const tab1 = await context.newPage();
    await entrar(tab1, "uab");
    await tab1.getByTestId("elegir-empresa-D1").click();
    await expect(tab1.getByTestId("selector-empresa")).toContainText("GLOBAL DV");

    // La segunda pestaña arranca con la preferencia, y cambiar aquí no puede
    // arrastrar a la primera: es el caso que `localStorage` rompía.
    const tab2 = await context.newPage();
    await tab2.goto("/");
    await tab2.waitForLoadState("networkidle");
    const selector2 = tab2.getByTestId("selector-empresa");
    if (await selector2.count()) {
      await selector2.click();
      await tab2.getByTestId("opcion-empresa-D2").click();
    } else {
      await tab2.getByTestId("elegir-empresa-D2").click();
    }
    await expect(tab2.getByTestId("selector-empresa")).toContainText("SEGUNDA");

    // La primera sigue donde estaba, incluso después de recargar.
    await expect(tab1.getByTestId("selector-empresa")).toContainText("GLOBAL DV");
    await tab1.reload();
    await expect(tab1.getByTestId("selector-empresa")).toContainText("GLOBAL DV");

    // Y las peticiones de cada una llevan su propia empresa.
    const deTab1 = observarEmpresas(tab1);
    const deTab2 = observarEmpresas(tab2);
    await irA(tab1, /Terceros/);
    await irA(tab2, /Terceros/);
    expect(new Set(deTab1).size).toBe(1);
    expect(new Set(deTab2).size).toBe(1);
    expect([...new Set(deTab1)][0]).not.toBe([...new Set(deTab2)][0]);

    await tab1.close();
    await tab2.close();
  });
});

// ==================================================================== flujo 4
test.describe("aislamiento de la caché", () => {
  test("los datos de una empresa no aparecen bajo la otra", async ({ page }) => {
    const empresas = capturarEmpresas(page);
    await entrar(page, "uab");
    const [a] = await (await empresas);

    await page.getByTestId("elegir-empresa-D1").click();
    await irA(page, /Terceros/);

    // Cada empresa tiene un tercero propio sembrado en el arranque. Sin datos
    // distintos, dos listas vacías tampoco se contaminan y el aislamiento
    // quedaría "demostrado" por no haber nada que mezclar.
    expect(a.id).toBe(IDS.empresa_a);
    await expect(page.getByText("SOLO-DE-A").first()).toBeVisible({ timeout: 20_000 });
    await expect(page.getByText("SOLO-DE-B")).toHaveCount(0);

    // Al cambiar de empresa, el tercero de A no puede seguir en pantalla.
    await page.getByTestId("selector-empresa").click();
    await page.getByTestId("opcion-empresa-D2").click();
    await page.waitForLoadState("networkidle");
    await expect(page.getByText("SOLO-DE-B").first()).toBeVisible({ timeout: 20_000 });
    await expect(page.getByText("SOLO-DE-A"),
      "el tercero de la empresa A siguió visible bajo la B").toHaveCount(0);
  });
});

// ==================================================================== flujo 5
test.describe("manipulación del cliente", () => {
  test("una empresa inventada en el almacenamiento no concede nada", async ({ page }) => {
    const autorizadas = capturarEmpresas(page);
    await entrar(page, "ua");
    const [a] = await (await autorizadas);

    await page.evaluate(() => {
      window.sessionStorage.setItem("kontrol.company-tab.v1", "u|00000000-0000-0000-0000-000000000000");
      window.localStorage.setItem("kontrol.company-preference.v2:falso", "00000000-0000-0000-0000-000000000000");
    });
    const empresas = observarEmpresas(page);
    await page.reload();
    await page.waitForLoadState("networkidle");

    // El id inventado no está en la lista autorizada: no se adopta.
    expect(empresas).not.toContain("00000000-0000-0000-0000-000000000000");
    expect(new Set(empresas)).toEqual(new Set([a.id]));
  });

  /**
   * Sesión con token real, para forzar la cabecera saltándose la interfaz.
   *
   * No se usa `page.evaluate` con `fetch`: el token de acceso vive en memoria
   * del módulo, no en una cookie, así que esa petición saldría sin autenticar y
   * su 401 no diría nada sobre el control de empresa. Aquí se pide un token por
   * el mismo endpoint que usa la aplicación y se manda la cabecera a mano, que
   * es exactamente lo que haría alguien con las herramientas del navegador.
   */
  async function sesionCruda(request: APIRequestContext, usuario: string, tenant = TENANT) {
    const r = await request.post("/api/v1/auth/login", {
      data: { tenant_code: tenant, username: usuario, password: PASS },
    });
    expect(r.status(), "no se pudo iniciar sesión").toBe(200);
    return (await r.json()).access_token as string;
  }

  test("la empresa de otro tenant se rechaza en el servidor", async ({ request }) => {
    const token = await sesionCruda(request, "ua");
    const r = await request.get("/api/v1/maestros/terceros", {
      headers: { Authorization: `Bearer ${token}`, "X-Kontrol-Company": IDS.empresa_c },
    });
    expect(r.status(), "la empresa de otro tenant fue aceptada").toBe(404);
  });

  test("una empresa a la que no se tiene acceso se rechaza", async ({ request }) => {
    // `ua` opera solo en A; B pertenece a su mismo tenant y aun así se niega.
    const token = await sesionCruda(request, "ua");
    const r = await request.get("/api/v1/maestros/terceros", {
      headers: { Authorization: `Bearer ${token}`, "X-Kontrol-Company": IDS.empresa_b },
    });
    expect(r.status(), "una empresa ajena del mismo tenant fue aceptada").toBe(404);
  });

  test("el contexto propio sí funciona", async ({ request }) => {
    // Sin esto, los dos bloqueos anteriores podrían deberse a que la ruta
    // rechaza cualquier cosa.
    const token = await sesionCruda(request, "ua");
    const r = await request.get("/api/v1/maestros/terceros", {
      headers: { Authorization: `Bearer ${token}`, "X-Kontrol-Company": IDS.empresa_a },
    });
    expect(r.status()).toBe(200);
    expect(JSON.stringify(await r.json())).toContain("SOLO-DE-A");
  });

  test("la escritura tampoco cruza: el cuerpo no impone la empresa", async ({ request }) => {
    // Regresión de la vulnerabilidad de la Spec 045, desde el cliente.
    const token = await sesionCruda(request, "ua");
    const r = await request.post("/api/v1/approvals/policies", {
      headers: { Authorization: `Bearer ${token}`, "X-Kontrol-Company": IDS.empresa_a },
      data: {
        company_id: IDS.empresa_b, process_type: "PURCHASE_ORDER",
        code: `N6-CRUZADA-${Date.now()}`, name: "Cruzada", requires_segregation: false,
      },
    });
    expect([404, 400].includes(r.status()),
      `el cuerpo impuso la empresa ajena: ${r.status()}`).toBe(true);
  });

});

// ==================================================================== flujo 6
test.describe("usuarios distintos en el mismo navegador", () => {
  test("quien entra después no hereda la empresa del anterior", async ({ page }) => {
    await entrar(page, "uab");
    await page.getByTestId("elegir-empresa-D2").click();
    await expect(page.getByTestId("selector-empresa")).toContainText("SEGUNDA");

    await page.keyboard.press("Escape");
    // Las notificaciones pueden quedar encima del botón: se espera a que se
    // vayan en vez de forzar el clic, que dispararía el evento sin que el botón
    // estuviera realmente accesible.
    for (const cerrar of await page.getByRole("button", { name: "Cerrar notificación" }).all()) {
      await cerrar.click().catch(() => undefined);
    }
    await page.getByRole("button", { name: "Salir" }).click({ timeout: 15_000 });
    await expect(page).toHaveURL(/\/login/, { timeout: 20_000 });

    const empresas = observarEmpresas(page);
    await entrar(page, "ua");
    await irA(page, /Terceros/);

    // `ua` solo opera en A: la preferencia de `uab` no puede arrastrarlo.
    expect(empresas).not.toContain(IDS.empresa_b);
    await expect(page.getByTestId("empresa-activa")).toContainText("GLOBAL DV");
  });
});
