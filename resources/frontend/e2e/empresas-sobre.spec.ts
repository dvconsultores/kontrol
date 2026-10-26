/**
 * EMPRESAS-SIN-SOBRE · el listado de Empresas responde el sobre del contrato y la
 * pantalla lo consume, en una pila real.
 *
 * El endpoint devolvía un array plano sin `total` ni `page`. Aquí se comprueba
 * por API la forma del sobre, la paginación y el `total` acotado al alcance del
 * usuario, y en el navegador que la pantalla pinta los items y que el selector de
 * contexto sigue ofreciendo todas las empresas del usuario.
 */
import { type APIRequestContext, type Page } from "@playwright/test";

import { mundoN6 } from "./helpers/n6-mundo";
import { entrar as entrarConSesion, expect, sesionApi, test } from "./helpers/sesion";

const API = process.env.KONTROL_E2E_API ?? "http://127.0.0.1:8000/api/v1";

interface Sobre { items: Array<{ id: string; code: string; legal_name: string }>; total: number; page: number; page_size: number }

async function token(tenant: string, usuario: string): Promise<string> {
  return (await sesionApi(usuario, { tenant })).token;
}

async function empresas(request: APIRequestContext, tok: string, qs = ""): Promise<{ status: number; body: Sobre }> {
  const r = await request.get(`${API}/organization/companies${qs}`, { headers: { Authorization: `Bearer ${tok}` } });
  return { status: r.status(), body: (await r.json()) as Sobre };
}

async function entrar(page: Page, tenant: string, usuario: string): Promise<void> {
  await entrarConSesion(page, usuario, { tenant });
  await page.waitForLoadState("networkidle");
}

test.describe("EMPRESAS-SIN-SOBRE · sobre paginado del listado de Empresas", () => {
  const mundo = mundoN6();

  test("LIST-E2E-01 · la API responde el sobre del contrato, con total acotado al usuario", async ({ request }) => {
    const uab = await token("DEMO", "uab");
    const { status, body } = await empresas(request, uab);
    expect(status).toBe(200);
    expect(Array.isArray(body)).toBe(false);
    expect(Object.keys(body).sort()).toEqual(["items", "page", "page_size", "total"]);
    expect(body.page).toBe(1);
    expect(body.page_size).toBe(20);
    expect(body.total).toBe(2);
    expect(body.items.map((c) => c.id).sort()).toEqual([mundo.empresa_a, mundo.empresa_b].sort());

    // `ua` solo opera en A: total 1, no 2.
    const ua = await token("DEMO", "ua");
    const deUa = (await empresas(request, ua)).body;
    expect(deUa.total).toBe(1);
    expect(deUa.items.map((c) => c.id)).toEqual([mundo.empresa_a]);
  });

  test("LIST-E2E-02 · la paginación corta el conjunto y una página más allá del final viene vacía", async ({ request }) => {
    const uab = await token("DEMO", "uab");
    const p1 = (await empresas(request, uab, "?page=1&page_size=1")).body;
    const p2 = (await empresas(request, uab, "?page=2&page_size=1")).body;
    const p3 = (await empresas(request, uab, "?page=3&page_size=1")).body;
    expect([p1.total, p2.total, p3.total]).toEqual([2, 2, 2]);
    expect(p1.items).toHaveLength(1);
    expect(p2.items).toHaveLength(1);
    expect(p1.items[0].id).not.toBe(p2.items[0].id);
    expect(p3.items).toEqual([]);
    expect((await empresas(request, uab, "?page=0")).status).toBe(422);
    expect((await empresas(request, uab, "?page_size=101")).status).toBe(422);
  });

  test("LIST-E2E-03 · q sigue buscando y el total es el del conjunto filtrado", async ({ request }) => {
    const uab = await token("DEMO", "uab");
    const con = (await empresas(request, uab, `?q=${encodeURIComponent(mundo.nombre_b)}`)).body;
    expect(con.total).toBe(1);
    expect(con.items.map((c) => c.id)).toEqual([mundo.empresa_b]);
    const sin = (await empresas(request, uab, "?q=ZZZ-NO-EXISTE-EMPRESA-Q")).body;
    expect(sin.total).toBe(0);
    expect(sin.items).toEqual([]);
  });

  test("LIST-E2E-04 · la pantalla pinta los items del sobre y el selector ofrece todas las empresas", async ({ page }) => {
    await entrar(page, "DEMO", "uab");
    // Con dos empresas el producto pide elegir: las dos están en la compuerta.
    await expect(page.getByTestId(`elegir-empresa-D1`)).toBeVisible({ timeout: 15000 });
    await expect(page.getByTestId(`elegir-empresa-D2`)).toBeVisible();
    await page.getByTestId("elegir-empresa-D1").click();
    await page.waitForLoadState("networkidle");

    await page.locator('nav a[href="/organizacion/empresas"]').first().click();
    await page.waitForURL((u) => u.pathname === "/organizacion/empresas", { timeout: 15000 });
    await page.waitForLoadState("networkidle");
    await expect(page.getByRole("row", { name: new RegExp(mundo.nombre_a.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")) })).toBeVisible();
    await expect(page.getByRole("row", { name: new RegExp(mundo.nombre_b.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")) })).toBeVisible();
    await expect(page.getByText("Sin empresas")).toHaveCount(0);
  });
});
