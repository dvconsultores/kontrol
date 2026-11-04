/**
 * AUDITORIA-SOBRE-VS-ARRAY · la pantalla de Auditoría pinta lo que el servidor devuelve.
 *
 * El servidor responde un sobre paginado; la pantalla lo trataba como un array y
 * no pintaba ninguna fila. Aquí se generan eventos controlados —el paso de
 * contraseña del login por API (`MFA_CHALLENGE_ISSUED`, o `LOGIN_SUCCESS` si el
 * usuario no exige segundo factor), cuyo `request_id` devuelve el propio servidor
 * en `X-Request-ID` y queda escrito en el evento— y se comprueba que aparecen como
 * filas al entrar por el menú. No consumen pasos TOTP. No se usa la columna «Fecha»
 * (deuda `AUDITORIA-CREATED-AT`) ni la caja de búsqueda (`UI-BUSQUEDA-MUERTA`,
 * decisión pendiente).
 */
import { type APIRequestContext, type Page } from "@playwright/test";

import { entrar as entrarConSesion, expect, identidad, sesionApi, test } from "./helpers/sesion";

const PASSWORD = process.env.KONTROL_E2E_PASSWORD ?? "";

const API = process.env.KONTROL_E2E_API ?? "http://127.0.0.1:8000/api/v1";

/** Hace el paso de contraseña del login por API y devuelve el `request_id` que el servidor
 * asignó a esa petición y la acción del evento registrado. No consume pasos TOTP: no verifica
 * el segundo factor, solo dispara el evento controlado con el `request_id` de `X-Request-ID`. */
async function eventoControlado(
  request: APIRequestContext,
  tenant: string,
  usuario: string,
): Promise<{ rastro: string; accion: string }> {
  const r = await request.post(`${API}/auth/login`, {
    data: { tenant_code: tenant, username: identidad(usuario), password: PASSWORD },
  });
  expect(r.ok(), `login de ${usuario}`).toBeTruthy();
  const rastro = r.headers()["x-request-id"];
  if (!rastro) throw new Error(`login de ${usuario}: sin cabecera X-Request-ID`);
  const { status } = (await r.json()) as { status: string };
  if (status === "MFA_REQUIRED" || status === "MFA_ENROLLMENT_REQUIRED") {
    return { rastro, accion: "MFA_CHALLENGE_ISSUED" };
  }
  if (status === "AUTHENTICATED") return { rastro, accion: "LOGIN_SUCCESS" };
  throw new Error(`login de ${usuario}: estado inesperado ${status}`);
}

/** ¿Está el rastro en la bitácora del tenant de `token`? Por API, con página amplia:
 * con muchas pruebas en paralelo la página 1 de 10 que pide la pantalla puede no bastar. */
async function rastroEnLaBitacora(
  request: APIRequestContext,
  token: string,
  rastro: string,
  accion: string,
): Promise<boolean> {
  const r = await request.get(`${API}/audit/events?page_size=100&action=${accion}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  expect(r.ok()).toBeTruthy();
  const cuerpo = (await r.json()) as { items: Array<{ request_id: string | null }> };
  return cuerpo.items.some((i) => i.request_id === rastro);
}

async function entrar(page: Page, tenant: string, usuario: string): Promise<void> {
  await entrarConSesion(page, usuario, { tenant });
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
    const a = await eventoControlado(request, "DEMO", "admin");
    const b = await eventoControlado(request, "DEMO", "uab");
    const rastroA = a.rastro;
    const rastroB = b.rastro;
    const { token } = await sesionApi("admintenant", { tenant: "DEMO" });

    let sobre: { items: Array<{ action: string; entity_type: string; request_id: string | null }>; total: number } | null = null;
    page.on("response", async (r) => {
      if (r.url().includes("/api/v1/audit/events")) sobre = await r.json();
    });

    await entrar(page, "DEMO", "admintenant");
    await irAAuditoria(page);

    // Los dos eventos existen en la bitácora del tenant (verdad del servidor), y lo
    // que la pantalla recibió es un sobre, no un array.
    expect(await rastroEnLaBitacora(request, token, rastroA, a.accion)).toBe(true);
    expect(await rastroEnLaBitacora(request, token, rastroB, b.accion)).toBe(true);
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
        await expect(page.getByRole("row", { name: new RegExp(rastro) }).first()).toBeVisible();
      }
    }
    await expect(page.getByText("Sin eventos")).toHaveCount(0);
  });

  test("ENV-04 · el rastro de otro tenant no está en el sobre ni en la tabla", async ({ page, request }) => {
    const ajenoEvento = await eventoControlado(request, "DEMO2", "uc");
    const propioEvento = await eventoControlado(request, "DEMO", "ub");
    const ajeno = ajenoEvento.rastro;
    const propio = propioEvento.rastro;
    const { token } = await sesionApi("admintenant", { tenant: "DEMO" });

    let sobre: { items: Array<{ request_id: string | null }> } | null = null;
    page.on("response", async (r) => {
      if (r.url().includes("/api/v1/audit/events")) sobre = await r.json();
    });
    await entrar(page, "DEMO", "admintenant");
    await irAAuditoria(page);
    await expect.poll(() => sobre !== null).toBeTruthy();

    expect(await rastroEnLaBitacora(request, token, propio, propioEvento.accion)).toBe(true);
    expect(await rastroEnLaBitacora(request, token, ajeno, ajenoEvento.accion)).toBe(false);
    expect(sobre!.items.map((i) => i.request_id)).not.toContain(ajeno);
    await expect(page.getByRole("row", { name: new RegExp(ajeno) })).toHaveCount(0);
    if (sobre!.items.some((i) => i.request_id === propio)) {
      await expect(page.getByRole("row", { name: new RegExp(propio) }).first()).toBeVisible();
    }
  });
});
