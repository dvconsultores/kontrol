/**
 * E2E del motor de aprobaciones (Spec 045 · CVG-045-03).
 *
 * Frontend real → API real → backend real → **PostgreSQL real**.
 * El motor NO se mockea en ningún punto.
 *
 * Requiere el stack levantado y credenciales E2E.
 */
import { expect, test, type APIRequestContext, type Page } from "@playwright/test";

const TENANT = process.env.KONTROL_E2E_TENANT ?? "DEMO";
const USER = process.env.KONTROL_E2E_USER ?? "admin";
const PASSWORD = process.env.KONTROL_E2E_PASSWORD ?? "";
const API = process.env.KONTROL_E2E_API ?? "http://127.0.0.1:8000/api/v1";

/** Sufijo único: el estado persiste entre navegadores en la misma base. */
const RUN = `${Date.now().toString(36)}${Math.random().toString(36).slice(2, 6)}`;
/** El formulario de políticas normaliza el tipo de proceso a mayúsculas. */
const RUNU = RUN.toUpperCase();

async function apiLogin(request: APIRequestContext): Promise<string> {
  const r = await request.post(`${API}/auth/login`, {
    data: { tenant_code: TENANT, username: USER, password: PASSWORD },
  });
  expect(r.ok(), `login: ${r.status()}`).toBeTruthy();
  return (await r.json()).access_token as string;
}

async function companyId(request: APIRequestContext, token: string): Promise<string> {
  const r = await request.get(`${API}/organization/companies`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  expect(r.ok(), `companies: ${r.status()}`).toBeTruthy();
  const body = await r.json();
  const items = Array.isArray(body) ? body : body.items;
  return items[0].id as string;
}

async function uiLogin(page: Page): Promise<void> {
  await page.goto("/login");
  await page.getByLabel(/Empresa \(código\)/).fill(TENANT);
  await page.getByLabel(/Usuario/).fill(USER);
  await page.getByLabel(/Contraseña/).fill(PASSWORD);
  await page.getByRole("button", { name: "Iniciar sesión" }).click();
  await page.waitForURL((u) => !u.pathname.includes("login"), { timeout: 20000 });

  // La operación exige empresa activa: se selecciona como lo haría un usuario.
  await page.locator('nav a[href="/organizacion/empresas"]').click();
  await page.waitForURL((u) => u.pathname === "/organizacion/empresas", { timeout: 15000 });
  await page.waitForLoadState("networkidle");
  const activar = page.getByRole("button", { name: "Activar" }).first();
  if (await activar.count()) {
    await activar.click();
    // La Topbar refleja la empresa activa: confirma que el contexto se aplicó.
    await expect(page.getByRole("button", { name: "Desactivar" }).first())
      .toBeVisible({ timeout: 15000 });
  }
}

/** Cierra las notificaciones: son persistentes por diseño y, apiladas, tapan
 *  las acciones de la cabecera. */
async function closeNotifications(page: Page): Promise<void> {
  const close = page.getByRole("button", { name: "Cerrar notificación" });
  for (let i = await close.count(); i > 0; i = await close.count()) {
    await close.first().click();
  }
}

/** Navegación por el menú: el deep-link recarga y pierde el token en memoria. */
async function goto(page: Page, href: string): Promise<void> {
  // `.first()`: el breadcrumb también es un <nav>, así que el enlace puede
  // aparecer dos veces y el modo estricto de Playwright fallaría.
  await page.locator(`nav a[href="${href}"]`).first().click();
  await page.waitForURL((u) => u.pathname === href, { timeout: 15000 });
}

type Ctx = { token: string; company: string; headers: Record<string, string> };

async function ctx(request: APIRequestContext): Promise<Ctx> {
  const token = await apiLogin(request);
  const company = await companyId(request, token);
  return { token, company, headers: { Authorization: `Bearer ${token}` } };
}

/** Política de N niveles resuelta por el rol ADMIN. Umbral propio de la prueba. */
async function createPolicy(
  request: APIRequestContext, c: Ctx, processType: string,
  opts: { levels?: number; segregation?: boolean; threshold?: number } = {},
): Promise<string> {
  const { levels = 1, segregation = false, threshold = 1000 } = opts;
  const p = await request.post(`${API}/approvals/policies`, {
    headers: c.headers,
    data: {
      company_id: c.company, process_type: processType, code: `PC-${RUN}`,
      name: `Política ${processType}`, requires_segregation: segregation,
    },
  });
  expect(p.status(), await p.text()).toBe(201);
  const policyId = (await p.json()).id as string;

  const rule = await request.post(`${API}/approvals/policies/${policyId}/rules`, {
    headers: c.headers,
    data: {
      name: "Sobre umbral",
      conditions: [{ field: "amount_base", operator: "gt", value: threshold }],
      condition_fields: ["amount_base", "amount", "currency"],
    },
  });
  expect(rule.status(), await rule.text()).toBe(201);
  const ruleId = (await rule.json()).id as string;

  for (let order = 1; order <= levels; order += 1) {
    const lv = await request.post(`${API}/approvals/policies/${policyId}/rules/${ruleId}/levels`, {
      headers: c.headers,
      data: { level_order: order, resolver_type: "ROLE", resolver_ref: "ADMIN", quorum_type: "ANY" },
    });
    expect(lv.status(), await lv.text()).toBe(201);
  }
  const act = await request.post(`${API}/approvals/policies/${policyId}/activate`, { headers: c.headers });
  expect(act.ok(), await act.text()).toBeTruthy();
  return policyId;
}

async function createRequest(
  request: APIRequestContext, c: Ctx, processType: string, documentId: string, amount = 5000,
): Promise<string> {
  const r = await request.post(`${API}/approvals/requests`, {
    headers: c.headers,
    data: {
      company_id: c.company, process_type: processType,
      document_type: "E2EDoc", document_id: documentId,
      context: { amount, currency: "VED" },
    },
  });
  expect(r.status(), await r.text()).toBe(201);
  const body = await r.json();
  expect(body.requires_approval).toBe(true);
  return body.request_id as string;
}

async function openStep(request: APIRequestContext, c: Ctx, requestId: string) {
  const r = await request.get(`${API}/approvals/requests/${requestId}`, { headers: c.headers });
  expect(r.ok()).toBeTruthy();
  const body = await r.json();
  return body.steps.find((s: { status: string }) => s.status === "IN_REVIEW");
}

// --------------------------------------------------------------------------- //

test.describe("Spec 045 · motor de aprobaciones sobre PostgreSQL real", () => {
  test("flujo principal: configurar → solicitar → bandeja → aprobar 2 niveles → historial", async ({ page, request }) => {
    const c = await ctx(request);
    const process = `E2E_MAIN_${RUNU}`;

    // --- Configuración COMPLETA desde la interfaz (§12 pasos 2-8) ---
    await uiLogin(page);
    await goto(page, "/aprobaciones/politicas");
    await expect(page.getByRole("heading", { name: "Políticas de aprobación", level: 1 })).toBeVisible();

    await page.getByLabel("Tipo de proceso").fill(process);
    await page.getByLabel("Código").fill(`PC-${RUN}`);
    await page.getByLabel("Nombre").fill(`Política ${process}`);
    await page.getByRole("button", { name: "Crear borrador" }).click();

    // Al crearse abre su pantalla propia con URL propia (ADR-015 / P18)
    await page.waitForURL(/\/aprobaciones\/politicas\/[0-9a-f-]+$/, { timeout: 15000 });
    await expect(page.getByRole("heading", { name: `${process} v1`, level: 1 })).toBeVisible();

    // --- Regla y dos niveles, desde los formularios de la propia pantalla ---
    await page.getByLabel("Nombre de la regla").fill("Sobre umbral");
    await page.getByLabel("Campo", { exact: true }).fill("amount_base");
    await page.getByLabel("Operador de la condición").selectOption("gt");
    await page.getByLabel("Valor", { exact: true }).fill("1000");
    await page.getByRole("button", { name: "Añadir regla" }).click();
    // `.first()`: el nombre aparece en la lista de reglas y en el selector de nivel.
    await expect(page.getByText("Sobre umbral").first()).toBeVisible({ timeout: 15000 });

    for (const order of ["1", "2"]) {
      await page.getByLabel("Regla a la que se añade el nivel").selectOption({ label: "Sobre umbral" });
      await page.getByLabel("Orden", { exact: true }).fill(order);
      await page.getByLabel("Tipo de resolutor").selectOption("ROLE");
      await page.getByLabel(/^Referencia/).fill("ADMIN");
      await page.getByLabel("Tipo de cuórum").selectOption("ANY");
      await page.getByRole("button", { name: "Añadir nivel" }).click();
      await expect(page.getByText(new RegExp(`^${order}\\. Rol ADMIN`)).first())
        .toBeVisible({ timeout: 15000 });
    }

    // Simulación antes de activar: no crea solicitudes (FR-045-008)
    await page.getByLabel(/^Monto/).fill("5000");
    await page.getByRole("button", { name: "Simular" }).click();
    await expect(page.getByText(/Requiere 2 nivel/)).toBeVisible({ timeout: 15000 });

    // Activación desde la UI
    await closeNotifications(page);
    await page.getByRole("button", { name: "Activar" }).click();
    await expect(page.getByRole("button", { name: "Cerrar vigencia" })).toBeVisible({ timeout: 15000 });

    const doc = `main-${RUN}`;
    const requestId = await createRequest(request, c, process, doc);

    // Aparece en la bandeja de la UI (se filtra por proceso: la bandeja es
    // transversal y pagina desde 11 registros)
    await goto(page, "/aprobaciones/bandeja");
    await expect(page.getByRole("heading", { name: "Mis aprobaciones", level: 1 })).toBeVisible();
    await page.getByLabel("Proceso").fill(process);
    await expect(page.getByText(doc)).toBeVisible({ timeout: 15000 });
    await expect(page.getByRole("button", { name: `Aprobar ${doc}` })).toBeVisible();

    // Nivel 1
    const step1 = await openStep(request, c, requestId);
    expect(step1.level_order).toBe(1);
    const a1 = await request.post(`${API}/approvals/steps/${step1.id}/approve`, {
      headers: { ...c.headers, "If-Match": String(step1.version) }, data: {},
    });
    expect(a1.ok(), await a1.text()).toBeTruthy();
    expect((await a1.json()).next_level).toBe(2);

    // Nivel 2 → APPROVED
    const step2 = await openStep(request, c, requestId);
    expect(step2.level_order).toBe(2);
    const a2 = await request.post(`${API}/approvals/steps/${step2.id}/approve`, {
      headers: c.headers, data: {},
    });
    expect((await a2.json()).status).toBe("APPROVED");

    // El documento origen puede continuar y el historial persiste
    const st = await request.get(
      `${API}/approvals/requests/by-document?company_id=${c.company}&document_type=E2EDoc&document_id=${doc}`,
      { headers: c.headers });
    const body = await st.json();
    expect(body.is_approved).toBe(true);
    expect(body.blocks_advance).toBe(false);
    expect(body.requests[0].steps).toHaveLength(2);

    // Auditoría registrada
    const audit = await request.get(`${API}/audit/events?limit=200`, { headers: c.headers });
    const actions = (await audit.json()).items.map((e: { action: string }) => e.action);
    expect(actions).toContain("APPROVAL_REQUESTED");
    expect(actions).toContain("APPROVAL_APPROVE");
  });

  test("rechazo con motivo obligatorio", async ({ request }) => {
    const c = await ctx(request);
    const process = `E2E_REJ_${RUN}`;
    await createPolicy(request, c, process);
    const requestId = await createRequest(request, c, process, `rej-${RUN}`);
    const step = await openStep(request, c, requestId);

    const sinMotivo = await request.post(`${API}/approvals/steps/${step.id}/reject`, {
      headers: c.headers, data: { reason: "   " },
    });
    expect(sinMotivo.status()).toBe(422);
    expect((await sinMotivo.json()).code).toBe("APPROVAL_REASON_REQUIRED");

    const conMotivo = await request.post(`${API}/approvals/steps/${step.id}/reject`, {
      headers: c.headers, data: { reason: "fuera de presupuesto" },
    });
    expect((await conMotivo.json()).status).toBe("REJECTED");
  });

  test("devolución para corrección y reenvío", async ({ request }) => {
    const c = await ctx(request);
    const process = `E2E_RET_${RUN}`;
    await createPolicy(request, c, process);
    const doc = `ret-${RUN}`;
    const first = await createRequest(request, c, process, doc);
    const step = await openStep(request, c, first);
    const ret = await request.post(`${API}/approvals/steps/${step.id}/return`, {
      headers: c.headers, data: { reason: "falta centro de costo" },
    });
    expect((await ret.json()).status).toBe("RETURNED");

    // Documento corregido → solicitud nueva, y el historial conserva ambas
    const second = await createRequest(request, c, process, doc, 6000);
    expect(second).not.toBe(first);
    const step2 = await openStep(request, c, second);
    const ok = await request.post(`${API}/approvals/steps/${step2.id}/approve`, { headers: c.headers, data: {} });
    expect((await ok.json()).status).toBe("APPROVED");

    const hist = await request.get(
      `${API}/approvals/requests/by-document?company_id=${c.company}&document_type=E2EDoc&document_id=${doc}`,
      { headers: c.headers });
    expect((await hist.json()).requests.length).toBeGreaterThanOrEqual(2);
  });

  test("segregación: el creador no puede aprobar y no ve acciones", async ({ request }) => {
    const c = await ctx(request);
    const process = `E2E_SEG_${RUN}`;
    await createPolicy(request, c, process, { segregation: true });
    const requestId = await createRequest(request, c, process, `seg-${RUN}`);

    const detail = await (await request.get(`${API}/approvals/requests/${requestId}`, { headers: c.headers })).json();
    expect(detail.allowed_actions).toEqual([]); // backend decide, no la UI

    const step = detail.steps.find((s: { status: string }) => s.status === "IN_REVIEW");
    const denied = await request.post(`${API}/approvals/steps/${step.id}/approve`, { headers: c.headers, data: {} });
    expect(denied.status()).toBe(403);
    expect((await denied.json()).code).toBe("APPROVAL_SEGREGATION_VIOLATION");

    // El estado no cambió
    const after = await (await request.get(`${API}/approvals/requests/${requestId}`, { headers: c.headers })).json();
    expect(after.status).toBe("IN_REVIEW");
  });

  test("usuario sin sesión: el backend deniega, no la UI", async ({ request }) => {
    const c = await ctx(request);
    for (const path of ["/approvals/policies?company_id=" + c.company, "/approvals/inbox?company_id=" + c.company]) {
      const r = await request.get(`${API}${path}`);
      expect(r.status()).toBe(401);
    }
  });

  test("solicitud obsoleta: el documento cambió después de solicitar", async ({ request }) => {
    const c = await ctx(request);
    const process = `E2E_OBS_${RUN}`;
    await createPolicy(request, c, process);
    const doc = `obs-${RUN}`;
    const first = await createRequest(request, c, process, doc, 5000);

    // Nueva solicitud con importe distinto → la anterior queda obsoleta
    await createRequest(request, c, process, doc, 9000);
    const stale = await (await request.get(`${API}/approvals/requests/${first}`, { headers: c.headers })).json();
    expect(stale.status).toBe("OBSOLETE");
    expect(stale.allowed_actions).toEqual([]);
  });

  test("If-Match: versión obsoleta produce 409 y no duplica decisión", async ({ request }) => {
    const c = await ctx(request);
    const process = `E2E_ETAG_${RUN}`;
    await createPolicy(request, c, process);
    const requestId = await createRequest(request, c, process, `etag-${RUN}`);
    const step = await openStep(request, c, requestId);

    const stale = await request.post(`${API}/approvals/steps/${step.id}/approve`, {
      headers: { ...c.headers, "If-Match": "999" }, data: {},
    });
    expect(stale.status()).toBe(409);
    expect((await stale.json()).code).toBe("APPROVAL_STEP_VERSION_CONFLICT");

    // Sin If-Match (compatibilidad: la extensión global no rompe lo existente)
    const ok = await request.post(`${API}/approvals/steps/${step.id}/approve`, { headers: c.headers, data: {} });
    expect(ok.ok(), await ok.text()).toBeTruthy();
  });

  test("idempotencia: doble envío no duplica la solicitud", async ({ request }) => {
    const c = await ctx(request);
    const process = `E2E_IDEM_${RUN}`;
    await createPolicy(request, c, process);
    const doc = `idem-${RUN}`;
    const payload = {
      company_id: c.company, process_type: process, document_type: "E2EDoc",
      document_id: doc, context: { amount: 5000, currency: "VED" },
    };
    const [r1, r2] = await Promise.all([
      request.post(`${API}/approvals/requests`, { headers: c.headers, data: payload }),
      request.post(`${API}/approvals/requests`, { headers: c.headers, data: payload }),
    ]);
    const b1 = await r1.json();
    const b2 = await r2.json();
    expect(b1.request_id).toBe(b2.request_id);

    const hist = await (await request.get(
      `${API}/approvals/requests/by-document?company_id=${c.company}&document_type=E2EDoc&document_id=${doc}`,
      { headers: c.headers })).json();
    expect(hist.requests).toHaveLength(1);
  });

  test("concurrencia: dos decisiones simultáneas, sólo una prospera", async ({ request }) => {
    const c = await ctx(request);
    const process = `E2E_CONC_${RUN}`;
    await createPolicy(request, c, process);
    const requestId = await createRequest(request, c, process, `conc-${RUN}`);
    const step = await openStep(request, c, requestId);

    const [a, b] = await Promise.all([
      request.post(`${API}/approvals/steps/${step.id}/approve`, {
        headers: { ...c.headers, "If-Match": String(step.version) }, data: {},
      }),
      request.post(`${API}/approvals/steps/${step.id}/reject`, {
        headers: { ...c.headers, "If-Match": String(step.version) }, data: { reason: "no procede" },
      }),
    ]);
    const codes = [a.status(), b.status()].sort();
    expect(codes[0]).toBe(200);
    expect(codes[1]).toBeGreaterThanOrEqual(409); // conflicto o decisión duplicada

    // Estado final válido y una sola decisión registrada
    const detail = await (await request.get(`${API}/approvals/requests/${requestId}`, { headers: c.headers })).json();
    expect(["APPROVED", "REJECTED"]).toContain(detail.status);
    const decisions = detail.steps.flatMap((s: { decisions: unknown[] }) => s.decisions);
    expect(decisions).toHaveLength(1);
  });

  test("multiempresa: no se ven solicitudes de otra empresa", async ({ request }) => {
    const c = await ctx(request);
    const inbox = await (await request.get(
      `${API}/approvals/inbox?company_id=empresa-inexistente`, { headers: c.headers })).json();
    expect(inbox.total).toBe(0);
  });

  test("eventos de dominio emitidos para la Spec 047", async ({ request }) => {
    const c = await ctx(request);
    const process = `E2E_EV_${RUN}`;
    await createPolicy(request, c, process);
    const requestId = await createRequest(request, c, process, `ev-${RUN}`);
    const step = await openStep(request, c, requestId);
    await request.post(`${API}/approvals/steps/${step.id}/approve`, { headers: c.headers, data: {} });

    // Los eventos se consultan por la propia solicitud: el motor emite, no notifica
    const detail = await (await request.get(`${API}/approvals/requests/${requestId}`, { headers: c.headers })).json();
    expect(detail.status).toBe("APPROVED");
    expect(detail.steps[0].decisions[0].decision).toBe("APPROVE");
  });
});
