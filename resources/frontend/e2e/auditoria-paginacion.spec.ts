/**
 * AUDITORIA-PAGINACION-CLIENTE · la bitácora se pagina en el servidor.
 *
 * El defecto era que la tabla se paginaba en cliente de 10 en 10 sobre la primera
 * página recibida: «Página siguiente» no pedía nada al servidor y el selector de
 * tamaño tampoco. Como la bitácora CRECE mientras corre la suite (cada inicio de
 * sesión de otras pruebas añade un evento), ninguna aserción puede depender de un
 * total fijo ni de la posición de un evento concreto: todo se compara contra la
 * respuesta que la propia pantalla recibió, y entre páginas solo se afirma el orden.
 */
import { expect, test, type APIRequestContext, type Page, type Response } from "@playwright/test";

const API = process.env.KONTROL_E2E_API ?? "http://127.0.0.1:8000/api/v1";
const PASSWORD = process.env.KONTROL_E2E_PASSWORD ?? "";

interface Evento {
  id: string;
  action: string;
  entity_type: string;
  request_id: string | null;
  event_time: string;
}

interface Sobre {
  items: Evento[];
  total: number;
  page: number;
  page_size: number;
}

async function token(request: APIRequestContext, tenant: string, usuario: string): Promise<string> {
  const r = await request.post(`${API}/auth/login`, {
    data: { tenant_code: tenant, username: usuario, password: PASSWORD },
  });
  expect(r.ok(), `login ${usuario}/${tenant}: ${r.status()}`).toBeTruthy();
  return (await r.json()).access_token as string;
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

function respuestaDeAuditoria(page: Page, pagina: number, tamano: number): Promise<Response> {
  return page.waitForResponse((r) => {
    if (!r.url().includes("/api/v1/audit/events")) return false;
    const q = new URL(r.url()).searchParams;
    return q.get("page") === String(pagina) && q.get("page_size") === String(tamano);
  });
}

async function asegurarEventos(request: APIRequestContext, tok: string, minimo: number): Promise<void> {
  const leerTotal = async (): Promise<number> => {
    const r = await request.get(`${API}/audit/events?page=1&page_size=1`, {
      headers: { Authorization: `Bearer ${tok}` },
    });
    expect(r.ok(), `total de auditoría: ${r.status()}`).toBeTruthy();
    return ((await r.json()) as Sobre).total;
  };
  let total = await leerTotal();
  let intentos = 0;
  while (total < minimo && intentos < minimo + 5) {
    const r = await request.post(`${API}/auth/login`, {
      data: { tenant_code: "DEMO", username: "admin", password: PASSWORD },
    });
    expect(r.ok(), `login de relleno: ${r.status()}`).toBeTruthy();
    total = await leerTotal();
    intentos += 1;
  }
  expect(total).toBeGreaterThanOrEqual(minimo);
}

async function filasCoinciden(page: Page, items: Evento[]): Promise<void> {
  const filas = page.locator("table tbody tr");
  await expect(filas).toHaveCount(items.length);
  for (const [i, item] of items.entries()) {
    await expect(filas.nth(i)).toContainText(item.action);
    await expect(filas.nth(i)).toContainText(item.entity_type);
    if (item.request_id) await expect(filas.nth(i)).toContainText(item.request_id);
  }
}

async function abrirAuditoria(page: Page): Promise<Sobre> {
  const espera = respuestaDeAuditoria(page, 1, 10);
  await page.locator('nav a[href="/auditoria"]').first().click();
  await page.waitForURL((u) => u.pathname === "/auditoria", { timeout: 15000 });
  return (await (await espera).json()) as Sobre;
}

test.describe("AUDITORIA-PAGINACION-CLIENTE · la bitácora se pagina en el servidor", () => {
  test.beforeEach(async ({ request }) => {
    await asegurarEventos(request, await token(request, "DEMO", "admin"), 30);
  });

  test("PAG-E2E-01 · siguiente pide la página 2 al servidor, y la tabla pinta la página que recibe", async ({ page }) => {
    await entrar(page, "DEMO", "admin");
    const p1 = await abrirAuditoria(page);
    expect(p1.page).toBe(1);
    expect(p1.page_size).toBe(10);
    expect(p1.items).toHaveLength(10);
    expect(p1.total).toBeGreaterThan(10);

    await filasCoinciden(page, p1.items);
    await expect(page.getByRole("navigation", { name: "Paginación" })).toHaveCount(1);
    await expect(page.getByText(`Página 1 de ${Math.ceil(p1.total / 10)}`)).toBeVisible();
    await expect(page.getByText(/Mostrando/)).toHaveCount(0);

    const espera2 = respuestaDeAuditoria(page, 2, 10);
    await page.getByRole("button", { name: "Página siguiente" }).click();
    const p2 = (await (await espera2).json()) as Sobre;
    expect(p2.page).toBe(2);
    expect(p2.items).toHaveLength(10);
    await filasCoinciden(page, p2.items);

    // La bitácora crece mientras se pagina: entre una petición y la siguiente entran eventos
    // por arriba y la página 2 puede repetir los más antiguos de la 1. Lo que no cambia nunca
    // es el orden dentro de cada página: del más reciente al más antiguo.
    for (const recibida of [p1, p2]) {
      const tiempos = recibida.items.map((e) => Date.parse(e.event_time));
      expect(tiempos).toEqual([...tiempos].sort((a, b) => b - a));
    }
    await expect(page.getByText(`Página 2 de ${Math.ceil(p2.total / 10)}`)).toBeVisible();

    // Volver a la primera. Dentro de los 30 s de vigencia de la caché no hay petición nueva;
    // pasado ese tiempo la habría, y con ella podrían entrar eventos nuevos. Aquí solo se
    // afirma lo que vale en los dos casos; que vuelven las filas de la página 1 lo fija la
    // prueba de componente PAG-07.
    await page.getByRole("button", { name: "Página anterior" }).click();
    await expect(page.getByText(/Página 1 de \d+/)).toBeVisible();
    await expect(page.locator("table tbody tr")).toHaveCount(10);
    await expect(page.getByRole("button", { name: "Página anterior" })).toBeDisabled();
  });

  test("PAG-E2E-02 · con 25 por página se ven las 25 filas recibidas y un solo paginador", async ({ page }) => {
    await entrar(page, "DEMO", "admin");
    await abrirAuditoria(page);

    const espera = respuestaDeAuditoria(page, 1, 25);
    await page.getByLabel("Registros por página").selectOption("25");
    const p = (await (await espera).json()) as Sobre;
    expect(p.page_size).toBe(25);
    expect(p.items).toHaveLength(25);
    await filasCoinciden(page, p.items);
    await expect(page.getByRole("navigation", { name: "Paginación" })).toHaveCount(1);
    await expect(page.getByText(`Página 1 de ${Math.ceil(p.total / 25)}`)).toBeVisible();
  });

  test("PAG-E2E-03 · cambiar el tamaño desde otra página vuelve a la primera", async ({ page }) => {
    await entrar(page, "DEMO", "admin");
    await abrirAuditoria(page);

    const espera2 = respuestaDeAuditoria(page, 2, 10);
    await page.getByRole("button", { name: "Página siguiente" }).click();
    const p2 = (await (await espera2).json()) as Sobre;
    expect(p2.page).toBe(2);
    await filasCoinciden(page, p2.items);

    const espera = respuestaDeAuditoria(page, 1, 25);
    await page.getByLabel("Registros por página").selectOption("25");
    const p = (await (await espera).json()) as Sobre;
    expect(p.page).toBe(1);
    await filasCoinciden(page, p.items);
  });

  test("PAG-E2E-04 · por API: el final de la bitácora y los límites del contrato", async ({ request }) => {
    const tok = await token(request, "DEMO", "admin");

    async function auditoria(qs: string): Promise<{ status: number; body: Sobre }> {
      const r = await request.get(`${API}/audit/events${qs}`, { headers: { Authorization: `Bearer ${tok}` } });
      return { status: r.status(), body: (await r.json()) as Sobre };
    }

    const p1 = await auditoria("?page=1&page_size=10");
    expect(p1.status).toBe(200);
    expect(Object.keys(p1.body).sort()).toEqual(["items", "page", "page_size", "total"]);
    expect(p1.body.items).toHaveLength(10);

    const ultima = Math.ceil(p1.body.total / 10);
    const fin = await auditoria(`?page=${ultima}&page_size=10`);
    expect(fin.status).toBe(200);
    expect(fin.body.items.length).toBeGreaterThanOrEqual(1);
    expect(fin.body.items.length).toBeLessThanOrEqual(10);
    expect(fin.body.total).toBeGreaterThanOrEqual(p1.body.total);

    const fuera = await auditoria(`?page=${ultima + 50}&page_size=10`);
    expect(fuera.status).toBe(200);
    expect(fuera.body.items).toEqual([]);
    expect(fuera.body.total).toBeGreaterThanOrEqual(p1.body.total);

    const cero = await auditoria("?page=0");
    expect(cero.status).toBe(422);

    const excedido = await auditoria("?page_size=101");
    expect(excedido.status).toBe(422);
  });
});
