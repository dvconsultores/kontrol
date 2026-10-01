/**
 * AUDITORIA-SOBRE-VS-ARRAY · la pantalla de Auditoría pinta lo que el servidor devuelve.
 *
 * El servidor responde un sobre paginado; la pantalla lo trataba como un array y
 * no pintaba ninguna fila. Aquí se generan eventos controlados —inicios de sesión
 * por API, cuyo `request_id` devuelve el propio servidor en `X-Request-ID` y queda
 * escrito en el evento `LOGIN_SUCCESS`— y se comprueba que aparecen como filas al
 * entrar por el menú. No se usa la columna «Fecha» (deuda `AUDITORIA-CREATED-AT`)
 * ni la caja de búsqueda (`UI-BUSQUEDA-MUERTA`, decisión pendiente).
 */
import { expect, test, type APIRequestContext, type Page } from "@playwright/test";

const API = process.env.KONTROL_E2E_API ?? "http://127.0.0.1:8000/api/v1";
const PASSWORD = process.env.KONTROL_E2E_PASSWORD ?? "";

/** Inicia sesión por API y devuelve el `request_id` que el servidor asignó a ese login. */
async function loginConRastro(request: APIRequestContext, tenant: string, usuario: string): Promise<{ rastro: string; token: string }> {
  const r = await request.post(`${API}/auth/login`, {
    data: { tenant_code: tenant, username: usuario, password: PASSWORD },
  });
  expect(r.ok(), `login ${usuario}/${tenant}: ${r.status()}`).toBeTruthy();
  const rastro = r.headers()["x-request-id"];
  expect(rastro, "el servidor devuelve X-Request-ID").toBeTruthy();
  return { rastro, token: (await r.json()).access_token as string };
}

/** ¿Está el rastro en la bitácora del tenant de `token`? Por API, con página amplia:
 * con muchas pruebas en paralelo la página 1 de 10 que pide la pantalla puede no bastar. */
async function rastroEnLaBitacora(request: APIRequestContext, token: string, rastro: string): Promise<boolean> {
  const r = await request.get(`${API}/audit/events?page_size=100&action=LOGIN_SUCCESS`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  expect(r.ok()).toBeTruthy();
  const cuerpo = (await r.json()) as { items: Array<{ request_id: string | null }> };
  return cuerpo.items.some((i) => i.request_id === rastro);
}

async function entrar(page: Page, tenant: string, usuario: string): Promise<void> {
  await page.goto("/login");
  await page.getByLabel(/Empresa \(código\)/).fill(tenant);
  await page.getByLabel(/Usuario/).fill(usuario);
  await page.getByLabel(/Contraseña/).fill(PASSWORD);
  await page.getByRole("button", { name: "Iniciar sesión" }).click();
  await page.waitForURL((u) => !u.pathname.includes("login"), { timeout: 20000 });
  await page.waitForLoadState("networkidle");
  const compuerta = page.getByTestId(/^elegir-empresa-/);
  if (await compuerta.count()) {
    await compuerta.first().click();
    await page.waitForLoadState("networkidle");
  }
}

async function irAAuditoria(page: Page): Promise<void> {
  await page.locator('nav a[href="/auditoria"]').first().click();
  await page.waitForURL((u) => u.pathname === "/auditoria", { timeout: 15000 });
  await page.waitForLoadState("networkidle");
}

test.describe("AUDITORIA-SOBRE-VS-ARRAY · las filas del sobre se pintan", () => {
  test("ENV-01/02 · dos eventos controlados del tenant aparecen como filas, y son los del sobre", async ({ page, request }) => {
    const { rastro: rastroA, token } = await loginConRastro(request, "DEMO", "admin");
    const { rastro: rastroB } = await loginConRastro(request, "DEMO", "uab");

    let sobre: { items: Array<{ action: string; entity_type: string; request_id: string | null }>; total: number } | null = null;
    page.on("response", async (r) => {
      if (r.url().includes("/api/v1/audit/events")) sobre = await r.json();
    });

    await entrar(page, "DEMO", "admin");
    await irAAuditoria(page);

    // Los dos eventos existen en la bitácora del tenant (verdad del servidor), y lo
    // que la pantalla recibió es un sobre, no un array.
    expect(await rastroEnLaBitacora(request, token, rastroA)).toBe(true);
    expect(await rastroEnLaBitacora(request, token, rastroB)).toBe(true);
    await expect.poll(() => sobre !== null).toBeTruthy();
    expect(Array.isArray(sobre)).toBe(false);
    expect(sobre!.items.length).toBeGreaterThan(0);
    expect(sobre!.total).toBeGreaterThanOrEqual(sobre!.items.length);

    // Y lo que la persona ve: la pantalla pide su página al servidor y la tabla la
    // pinta entera, así que las filas son exactamente los `items` recibidos, en su
    // orden. Con varias pruebas en paralelo, otros inicios de sesión se cuelan entre
    // los dos controlados: se mira la correspondencia entera, no la posición de uno.
    const esperadas = sobre!.items;
    const filas = page.locator("table tbody tr");
    await expect(filas).toHaveCount(esperadas.length);
    for (const [i, item] of esperadas.entries()) {
      const texto = await filas.nth(i).innerText();
      expect(texto, `fila ${i}`).toContain(item.action);
      expect(texto, `fila ${i}`).toContain(item.entity_type);
      if (item.request_id) expect(texto, `fila ${i}`).toContain(item.request_id);
    }
    for (const rastro of [rastroA, rastroB]) {
      if (esperadas.some((i) => i.request_id === rastro)) {
        await expect(page.getByRole("row", { name: new RegExp(rastro) })).toBeVisible();
      }
    }
    await expect(page.getByText("Sin eventos")).toHaveCount(0);
  });

  test("ENV-04 · el rastro de otro tenant no está en el sobre ni en la tabla", async ({ page, request }) => {
    const { rastro: ajeno } = await loginConRastro(request, "DEMO2", "uc");
    const { rastro: propio, token } = await loginConRastro(request, "DEMO", "admin");

    let sobre: { items: Array<{ request_id: string | null }> } | null = null;
    page.on("response", async (r) => {
      if (r.url().includes("/api/v1/audit/events")) sobre = await r.json();
    });
    await entrar(page, "DEMO", "admin");
    await irAAuditoria(page);
    await expect.poll(() => sobre !== null).toBeTruthy();

    expect(await rastroEnLaBitacora(request, token, propio)).toBe(true);
    expect(await rastroEnLaBitacora(request, token, ajeno)).toBe(false);
    expect(sobre!.items.map((i) => i.request_id)).not.toContain(ajeno);
    await expect(page.getByRole("row", { name: new RegExp(ajeno) })).toHaveCount(0);
    if (sobre!.items.some((i) => i.request_id === propio)) {
      await expect(page.getByRole("row", { name: new RegExp(propio) })).toBeVisible();
    }
  });
});
