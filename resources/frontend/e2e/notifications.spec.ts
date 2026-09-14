/**
 * E2E de notificaciones, tareas y alertas (Spec 047).
 *
 * Frontend real → API real → PostgreSQL real → planificador real. Los hechos
 * salen del motor de aprobaciones de la 045; nada se inserta por la puerta de atrás.
 *
 * Cada ejecución crea su propio usuario y lo hace el único aprobador de su
 * política: así sus notificaciones y sus totales no dependen de lo que hagan a la
 * vez los otros navegadores contra la misma base.
 *
 * Requiere `KONTROL_E2E_DB_URL` (la base del E2E) y el arranque
 * `qa/n6-multicompany-bootstrap.py` para la prueba de aislamiento entre empresas.
 */
import { expect, test, type APIRequestContext, type Page } from "@playwright/test";

import { hastaQue, tick } from "./helpers/planificador";

const TENANT = process.env.KONTROL_E2E_TENANT ?? "DEMO";
const ADMIN = process.env.KONTROL_E2E_USER ?? "admin";
const ADMIN_PASSWORD = process.env.KONTROL_E2E_PASSWORD ?? "";
const API = process.env.KONTROL_E2E_API ?? "http://127.0.0.1:8000/api/v1";

const RUN = `${Date.now().toString(36)}${Math.random().toString(36).slice(2, 6)}`;
const PROCESO = `E2E047${RUN.toUpperCase()}`;
const USUARIO = `n047${RUN}`;
const PASSWORD = "Kontrol2026Segura!047";

type Cabeceras = Record<string, string>;
type Notificacion = { id: string; link: { source_id: string }; read_at: string | null };
type Tarea = { id: string; status: string; assignee_user_id: string | null; link: { source_id: string } };

const estado: {
  admin: Cabeceras; usuario: Cabeceras; usuarioD2: Cabeceras | null;
  adminId: string; usuarioId: string; solicitudes: string[];
} = { admin: {}, usuario: {}, usuarioD2: null, adminId: "", usuarioId: "", solicitudes: [] };

async function token(request: APIRequestContext, username: string, password: string): Promise<string> {
  const r = await request.post(`${API}/auth/login`, { data: { tenant_code: TENANT, username, password } });
  expect(r.ok(), `login ${username}: ${r.status()}`).toBeTruthy();
  return (await r.json()).access_token as string;
}

async function pedir<T>(request: APIRequestContext, h: Cabeceras, metodo: "get" | "post", ruta: string, data?: unknown): Promise<T> {
  const r = await request[metodo](`${API}${ruta}`, { headers: h, data });
  expect(r.ok(), `${metodo.toUpperCase()} ${ruta}: ${r.status()} ${await r.text()}`).toBeTruthy();
  return (await r.json()) as T;
}

async function notificacionesDe(request: APIRequestContext, h: Cabeceras, solicitud: string): Promise<Notificacion[]> {
  const pagina = await pedir<{ items: Notificacion[] }>(request, h, "get", "/notifications?state=all&page_size=100");
  return pagina.items.filter((n) => n.link.source_id === solicitud);
}

async function tareasDe(request: APIRequestContext, h: Cabeceras, solicitud: string): Promise<Tarea[]> {
  const pagina = await pedir<{ items: Tarea[] }>(request, h, "get", "/tasks?scope=involved&status=OPEN&page_size=100");
  return pagina.items.filter((t) => t.link.source_id === solicitud);
}

async function crearSolicitud(request: APIRequestContext, indice: number): Promise<string> {
  const r = await pedir<{ request_id: string; requires_approval: boolean }>(request, estado.admin, "post", "/approvals/requests", {
    process_type: PROCESO, document_type: "Doc", document_id: `${RUN}-${indice}`,
    context: { amount: 5000, currency: "VED" },
  });
  expect(r.requires_approval).toBe(true);
  return r.request_id;
}

async function entrar(page: Page): Promise<void> {
  await page.goto("/login");
  await page.getByLabel(/Empresa \(código\)/).fill(TENANT);
  await page.getByLabel(/Usuario/).fill(USUARIO);
  await page.getByLabel(/Contraseña/).fill(PASSWORD);
  await page.getByRole("button", { name: "Iniciar sesión" }).click();
  await page.waitForURL((u) => !u.pathname.includes("login"), { timeout: 20_000 });
  const elegir = page.getByTestId("elegir-empresa-D1");
  await expect(elegir.or(page.getByTestId("campana"))).toBeVisible({ timeout: 20_000 });
  if (await elegir.isVisible()) {
    await elegir.click();
  }
  await expect(page.getByTestId("campana")).toBeVisible({ timeout: 20_000 });
}

async function cerrarAvisos(page: Page): Promise<void> {
  const cerrar = page.getByRole("button", { name: "Cerrar notificación" });
  for (let i = await cerrar.count(); i > 0; i = await cerrar.count()) {
    await cerrar.first().click();
  }
}

const sinLeer = (n: number): string => `Notificaciones sin leer: ${n}`;

test.describe.configure({ mode: "serial" });

test.beforeAll(async ({ request }) => {
  const adminToken = await token(request, ADMIN, ADMIN_PASSWORD);
  const base = { Authorization: `Bearer ${adminToken}` };
  const empresas = await pedir<{ id: string; code: string }[] | { items: { id: string; code: string }[] }>(
    request, base, "get", "/organization/companies");
  const lista = Array.isArray(empresas) ? empresas : empresas.items;
  const d1 = lista.find((e) => e.code === "D1");
  expect(d1, "la base del E2E no tiene la empresa D1").toBeTruthy();
  estado.admin = { ...base, "X-Kontrol-Company": d1!.id };

  const roles = await pedir<{ items: { id: string; code: string }[] }>(request, base, "get", "/roles");
  const adminRol = roles.items.find((r) => r.code === "ADMIN")!;
  const usuarios = await pedir<{ id: string; username: string }[]>(request, base, "get", "/users");
  estado.adminId = usuarios.find((u) => u.username === ADMIN)!.id;
  const creado = await pedir<{ id: string }>(request, base, "post", "/users", {
    username: USUARIO, password: PASSWORD, must_change_password: false,
  });
  estado.usuarioId = creado.id;
  await pedir(request, base, "post", `/users/${creado.id}/roles`, { role_id: adminRol.id, company_id: null });

  const usuarioToken = await token(request, USUARIO, PASSWORD);
  estado.usuario = { Authorization: `Bearer ${usuarioToken}`, "X-Kontrol-Company": d1!.id };
  // La segunda empresa se busca con el usuario de esta ejecución: la siembra de la
  // 047 limita al administrador a D1 para no alterar el resto de la cadena.
  const suyas = await pedir<{ id: string; code: string }[] | { items: { id: string; code: string }[] }>(
    request, { Authorization: `Bearer ${usuarioToken}` }, "get", "/organization/companies");
  const d2 = (Array.isArray(suyas) ? suyas : suyas.items).find((e) => e.code === "D2");
  estado.usuarioD2 = d2 ? { Authorization: `Bearer ${usuarioToken}`, "X-Kontrol-Company": d2.id } : null;

  for (const effect of ["NOTIFICATION", "TASK"]) {
    await pedir(request, estado.admin, "post", "/notifications/rules", {
      code: `${effect.slice(0, 1)}${RUN}`, source: "APPROVAL", event_type: "approval.step_opened",
      effect, auto_close: effect === "TASK",
    });
  }
  const politica = await pedir<{ id: string }>(request, estado.admin, "post", "/approvals/policies", {
    process_type: PROCESO, code: `P${RUN}`, name: `Política ${RUN}`, requires_segregation: false,
  });
  const regla = await pedir<{ id: string }>(request, estado.admin, "post", `/approvals/policies/${politica.id}/rules`, {
    name: "Siempre", conditions: [{ field: "amount_base", operator: "gt", value: 0 }],
    condition_fields: ["amount_base", "amount", "currency"],
  });
  await pedir(request, estado.admin, "post", `/approvals/policies/${politica.id}/rules/${regla.id}/levels`, {
    level_order: 1, resolver_type: "USER", resolver_ref: estado.usuarioId, quorum_type: "ANY",
  });
  await pedir(request, estado.admin, "post", `/approvals/policies/${politica.id}/activate`, {});
});

test("la campana cuenta en el servidor y leer una notificación la actualiza sin recargar", async ({ page, request }) => {
  const solicitud = await crearSolicitud(request, 1);
  estado.solicitudes.push(solicitud);
  await hastaQue(async () => (await notificacionesDe(request, estado.usuario, solicitud)).length > 0);
  const antes = await pedir<{ unread_notifications: number }>(request, estado.usuario, "get", "/notifications/counts");

  // Lo que el navegador pidió y recibió: si la campana no coincide con el servidor,
  // el fallo tiene que decir por qué, no solo que no coincide.
  const vistas: string[] = [];
  const esContador = (url: string): boolean => url.includes("/api/v1/notifications/counts");
  page.on("request", (q) => {
    if (esContador(q.url())) vistas.push(`petición empresa=${q.headers()["x-kontrol-company"] ?? "sin-cabecera"}`);
  });
  page.on("requestfailed", (q) => {
    if (esContador(q.url())) vistas.push(`fallida ${q.failure()?.errorText ?? ""}`);
  });
  page.on("response", (r) => {
    if (!esContador(r.url())) return;
    vistas.push(`respuesta ${r.status()}`);
    void r.text().then((cuerpo) => vistas.push(`cuerpo ${cuerpo}`)).catch(() => undefined);
  });

  await entrar(page);
  try {
    await expect(page.getByTestId("campana")).toHaveAttribute("aria-label", sinLeer(antes.unread_notifications));
  } catch (error) {
    // El registro se lee ahora, cuando la espera ya terminó: antes estaría vacío.
    throw new Error(`${String(error)}\ncontadores vistos por el navegador: ${JSON.stringify(vistas)}`);
  }
  await page.getByTestId("campana").click();
  await page.waitForURL((u) => u.pathname === "/notificaciones");

  const tarjeta = page.getByTestId("notificacion").filter({ hasText: PROCESO }).first();
  await expect(tarjeta).toContainText("Sin leer");
  await tarjeta.getByRole("button", { name: "Marcar como leída" }).click();
  await expect(page.getByTestId("campana")).toHaveAttribute("aria-label", sinLeer(antes.unread_notifications - 1));
});

test("completar la tarea no aprueba el documento de origen", async ({ page, request }) => {
  const [solicitud] = estado.solicitudes;
  await hastaQue(async () => (await tareasDe(request, estado.usuario, solicitud)).length > 0);

  await entrar(page);
  await page.locator('nav a[href="/tareas"]').first().click();
  await page.waitForURL((u) => u.pathname === "/tareas");
  await page.getByTestId("tarea").filter({ hasText: PROCESO }).first().getByRole("link", { name: "Ver detalle" }).click();
  await expect(page.getByRole("heading", { name: "Detalle de la tarea" })).toBeVisible();

  await page.getByRole("button", { name: "Iniciar" }).click();
  await expect(page.getByTestId("tarea-estado")).toHaveText("En curso");
  await cerrarAvisos(page);
  await page.getByRole("button", { name: "Completar", exact: true }).click();
  await expect(page.getByTestId("tarea-estado")).toHaveText("Completada");
  await expect(page.getByTestId("tarea-historial")).toContainText("Iniciada");
  await expect(page.getByTestId("tarea-historial")).toContainText("Completada");

  const documento = await pedir<{ is_approved: boolean }>(request, estado.admin, "get",
    `/approvals/requests/by-document?document_type=Doc&document_id=${RUN}-1`);
  expect(documento.is_approved, "completar la tarea aprobó el documento").toBe(false);
});

test("reasignar deja la asignación anterior en el historial", async ({ page, request }) => {
  const solicitud = await crearSolicitud(request, 2);
  estado.solicitudes.push(solicitud);
  await hastaQue(async () => (await tareasDe(request, estado.usuario, solicitud)).length > 0);
  const [tarea] = await tareasDe(request, estado.usuario, solicitud);

  await entrar(page);
  await page.locator('nav a[href="/tareas"]').first().click();
  await page.waitForURL((u) => u.pathname === "/tareas");
  await page.locator(`a[href="/tareas/${tarea.id}"]`).click();
  await page.getByLabel("Reasignar a").selectOption({ label: ADMIN });
  await page.getByRole("button", { name: "Reasignar" }).click();
  await expect(page.getByTestId("tarea-asignada")).toHaveText(ADMIN);
  await expect(page.getByTestId("tarea-historial")).toContainText("Reasignada");

  const detalle = await pedir<Tarea>(request, estado.admin, "get", `/tasks/${tarea.id}`);
  expect(detalle.assignee_user_id).toBe(estado.adminId);
});

test("repetir el planificador no duplica notificaciones ni tareas", async ({ request }) => {
  const [solicitud] = estado.solicitudes;
  const notas = (await notificacionesDe(request, estado.usuario, solicitud)).length;
  const tareas = (await pedir<{ items: Tarea[] }>(request, estado.usuario, "get", "/tasks?scope=involved&page_size=100"))
    .items.filter((t) => t.link.source_id === solicitud).length;
  for (let i = 0; i < 3; i++) tick();
  expect((await notificacionesDe(request, estado.usuario, solicitud)).length).toBe(notas);
  expect((await pedir<{ items: Tarea[] }>(request, estado.usuario, "get", "/tasks?scope=involved&page_size=100"))
    .items.filter((t) => t.link.source_id === solicitud).length).toBe(tareas);
});

test("el enlace lleva al origen cuando el usuario puede verlo", async ({ page }) => {
  await entrar(page);
  await page.getByTestId("campana").click();
  await page.waitForURL((u) => u.pathname === "/notificaciones");
  await page.getByLabel("Estado").selectOption("all");
  await page.getByTestId("notificacion").filter({ hasText: PROCESO }).first()
    .getByRole("link", { name: "Abrir origen" }).click();
  await page.waitForURL((u) => u.pathname === "/aprobaciones/bandeja");
});

test("lo de una empresa no se ve ni se cuenta en otra", async ({ page, request }) => {
  expect(estado.usuarioD2, "la base del E2E no tiene la segunda empresa (qa/spec047-e2e-seed.py)").toBeTruthy();
  const [solicitud] = estado.solicitudes;
  const [nota] = await notificacionesDe(request, estado.usuario, solicitud);
  const ajena = await request.get(`${API}/notifications/${nota.id}`, { headers: estado.usuarioD2! });
  expect(ajena.status()).toBe(404);
  const enD2 = await pedir<{ unread_notifications: number }>(request, estado.usuarioD2!, "get", "/notifications/counts");

  await entrar(page);
  await page.getByTestId("selector-empresa").click();
  await page.getByTestId("opcion-empresa-D2").click();
  await expect(page.getByTestId("campana")).toHaveAttribute("aria-label", sinLeer(enD2.unread_notifications));
  await page.getByTestId("campana").click();
  await page.waitForURL((u) => u.pathname === "/notificaciones");
  await page.getByLabel("Estado").selectOption("all");
  await expect(page.getByTestId("notificacion").filter({ hasText: PROCESO })).toHaveCount(0);
});

test("la página 3 muestra lo que el servidor pone en la página 3", async ({ page, request }) => {
  test.setTimeout(240_000);
  const nuevas: string[] = [];
  for (let i = 10; i < 31; i++) nuevas.push(await crearSolicitud(request, i));
  // Las reglas son de la empresa y cada ejecución deja las suyas: una solicitud
  // produce varias notificaciones, así que una sola página no basta para verlas.
  await hastaQue(async () => {
    const vistas = new Set<string>();
    for (let pagina = 1; ; pagina++) {
      const p = await pedir<{ items: Notificacion[]; total: number }>(request, estado.usuario, "get",
        `/notifications?state=all&page=${pagina}&page_size=100`);
      p.items.forEach((n) => vistas.add(n.link.source_id));
      if (p.items.length === 0 || pagina * 100 >= p.total) break;
    }
    return nuevas.every((s) => vistas.has(s));
  }, 40);
  const pagina3 = await pedir<{ items: Notificacion[]; total: number }>(request, estado.usuario, "get",
    "/notifications?state=active&page=3&page_size=10");
  expect(pagina3.total).toBeGreaterThan(20);

  await entrar(page);
  await page.getByTestId("campana").click();
  await page.waitForURL((u) => u.pathname === "/notificaciones");
  await page.getByRole("button", { name: "Página siguiente" }).click();
  await page.getByRole("button", { name: "Página siguiente" }).click();
  await expect(page.getByText(/Página 3 de/)).toBeVisible();
  await expect(page.getByTestId("notificacion").first()).toHaveAttribute("data-id", pagina3.items[0].id);
});
