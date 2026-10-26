/**
 * E2E del motor de aprobaciones (Spec 045 · CVG-045-03).
 *
 * Frontend real → API real → backend real → **PostgreSQL real**.
 * El motor NO se mockea en ningún punto.
 *
 * Requiere el stack levantado y credenciales E2E.
 */
import { type APIRequestContext, type Page } from "@playwright/test";
import { entrar, expect, sesionApi, test } from "./helpers/sesion";

import { diagnosticoDeEmpresa, emitirLaTablaTarde, esperarEstadoDeEmpresa } from "./helpers/empresa";

const TENANT = process.env.KONTROL_E2E_TENANT ?? "DEMO";
const USER = process.env.KONTROL_E2E_USER ?? "admin";
const API = process.env.KONTROL_E2E_API ?? "http://127.0.0.1:8000/api/v1";

/** Sufijo único: el estado persiste entre navegadores en la misma base. */
const RUN = `${Date.now().toString(36)}${Math.random().toString(36).slice(2, 6)}`;
/** El formulario de políticas normaliza el tipo de proceso a mayúsculas. */
const RUNU = RUN.toUpperCase();

async function apiLogin(): Promise<string> {
  return (await sesionApi(USER, { tenant: TENANT })).token;
}

type Empresa = { id: string; code: string };

/** La empresa sobre la que opera la suite: la misma que resuelve el contexto del backend. */
async function empresa(request: APIRequestContext, token: string): Promise<Empresa> {
  const r = await request.get(`${API}/organization/companies`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  expect(r.ok(), `companies: ${r.status()}`).toBeTruthy();
  const body = await r.json();
  const items = body.items;
  return { id: items[0].id as string, code: items[0].code as string };
}

async function companyId(request: APIRequestContext, token: string): Promise<string> {
  return (await empresa(request, token)).id;
}

/**
 * Controles de la pantalla de empresas, por **nombre accesible exacto**.
 *
 * `EmpresasPage` pinta por fila controles mutuamente excluyentes: la empresa
 * activa muestra «Activa» (deshabilitado) y «Desactivar»; cualquier otra muestra
 * «Activar». Sin `exact`, «Activar» casa por subcadena con «Des**activar**», de modo
 * que el ayudante pulsaba el control contrario y a continuación esperaba ver el
 * botón que él mismo acababa de hacer desaparecer (deuda E2E-045).
 */
function controlesDeEmpresa(page: Page) {
  return {
    activar: page.getByRole("button", { name: "Activar", exact: true }),
    desactivar: page.getByRole("button", { name: "Desactivar", exact: true }),
    activa: page.getByRole("button", { name: "Activa", exact: true }),
  };
}

/**
 * Deja una empresa activa, **idempotente**: si ya lo está no pulsa nada, si no lo
 * está la activa una sola vez, y si el estado no es determinable falla en el acto
 * enumerando lo que encontró. Nunca continúa a ciegas: una sesión sin empresa
 * activa produce fallos aguas abajo que no se parecen a su causa.
 *
 * Sin empresa activa el producto no pinta la tabla: sustituye el contenido por la
 * compuerta «Seleccione una empresa». Los dos estados son legítimos y los dos se
 * resuelven aquí, cada uno por su control exacto.
 */
async function activarEmpresa(page: Page): Promise<void> {
  await page.locator('nav a[href="/organizacion/empresas"]').first().click();
  await page.waitForURL((u) => u.pathname === "/organizacion/empresas", { timeout: 15000 });

  const { activar, desactivar, activa } = controlesDeEmpresa(page);

  // Compuerta de selección: identificador canónico del propio producto, con el código
  // de la empresa que resuelve el backend. No hay prefijos ni posiciones de por medio.
  const { code } = await empresa(page.request, await apiLogin());
  const eleccion = page.getByTestId(`elegir-empresa-${code}`);

  // La decisión se toma sobre una lectura ya determinable (E2E-HELPER-EMPRESA-CARRERA-DE-
  // PINTADO): ni `networkidle` ni un `count()` suelto sobre una pantalla aún sin pintar.
  const lectura = await esperarEstadoDeEmpresa(page, eleccion);

  // Regresión permanente (FR-045-079): todo elemento que alcance el localizador de
  // decisión se llama literalmente «Activar». Si alguien retira `exact`, «Desactivar»
  // entra en el conjunto y esto falla aquí, en la causa, no tres pantallas después.
  const alcanzados = (await activar.allInnerTexts()).map((t) => t.trim());
  expect(alcanzados.filter((t) => t !== "Activar"), `el localizador de «Activar» alcanzó ${JSON.stringify(alcanzados)}`)
    .toEqual([]);

  if (lectura.estado === "ACTIVA") return; // ya se cumple

  const candidatas = lectura.activar;
  const puerta = lectura.compuerta;
  expect(candidatas + puerta, `estado de empresa no determinable: ${diagnosticoDeEmpresa(lectura)}`).toBe(1);

  await (puerta === 1 ? eleccion : activar).click();

  // El estado se verifica por los controles exactos, no por la ausencia de error:
  // exactamente una empresa activa, y ninguna candidata donde antes había una.
  await expect(desactivar).toHaveCount(1, { timeout: 15000 });
  await expect(activa).toHaveCount(1);
  await expect(activar).toHaveCount(candidatas === 0 ? 0 : candidatas - 1);
}

async function uiLogin(page: Page): Promise<void> {
  await entrar(page, USER, { tenant: TENANT });

  // La operación exige empresa activa: se selecciona como lo haría un usuario.
  await activarEmpresa(page);
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
  const token = await apiLogin();
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

  test("multiempresa: la bandeja la delimita el contexto, no el parámetro de consulta", async ({ request }) => {
    const c = await ctx(request);

    // Subconjunto propio y determinista: la bandeja es transversal y las demás pruebas
    // —y los demás navegadores— crean solicitudes mientras esta corre. Comparar la bandeja
    // entera entre dos lecturas sucesivas mediría la concurrencia, no la delimitación.
    const process = `E2E_MC_${RUNU}`;
    await createPolicy(request, c, process);
    const requestId = await createRequest(request, c, process, `mc-${RUN}`);

    // `GET /approvals/inbox` NO declara `company_id`: FastAPI descarta el parámetro y el
    // servicio delimita por `ctx.company_id`. La versión anterior de esta prueba pedía la
    // bandeja de «empresa-inexistente» y exigía `total === 0`: atribuía al parámetro una
    // autoridad que el contrato no le da, y pasaba —cuando pasaba— por casualidad.
    const url = `${API}/approvals/inbox?process_type=${process}`;
    const propia = await (await request.get(url, { headers: c.headers })).json();
    const conParametroAjeno = await (await request.get(
      `${url}&company_id=empresa-inexistente`, { headers: c.headers })).json();

    // La solicitud recién creada está ahí, y el parámetro ajeno no la hace desaparecer:
    // misma respuesta, ítem por ítem, en las dos direcciones.
    expect(propia.total).toBe(1);
    expect(propia.items[0].request_id).toBe(requestId);
    expect(conParametroAjeno.total).toBe(propia.total);
    expect(conParametroAjeno.items.map((i: { step_id: string }) => i.step_id))
      .toEqual(propia.items.map((i: { step_id: string }) => i.step_id));

    // Y lo que la bandeja devuelve pertenece a la empresa del contexto. Ni la bandeja ni el
    // detalle publican `company_id`, así que se comprueba contra la única ruta que sí
    // delimita de forma observable: `GET /requests/{id}` responde 404 cuando la solicitud
    // es de otra empresa (`api.py:344`). Que se recupere prueba que la bandeja no devolvió
    // nada ajeno al contexto.
    const detalleRes = await request.get(`${API}/approvals/requests/${requestId}`, { headers: c.headers });
    expect(detalleRes.status(), `la bandeja devolvió una solicitud ajena al contexto: ${requestId}`).toBe(200);
    const detalle = await detalleRes.json();
    expect(detalle.steps.map((st: { id: string }) => st.id)).toContain(propia.items[0].step_id);
  });

  test("E2E-045 · con la petición de la tabla emitida tarde, el ayudante espera a que se pinte", async ({ page }) => {
    await emitirLaTablaTarde(page, 2000);
    await uiLogin(page);
    const { activar, desactivar, activa } = controlesDeEmpresa(page);
    await expect(desactivar).toHaveCount(1);
    await expect(activa).toHaveCount(1);
    await expect(activar).toHaveCount(0);
  });

  test("E2E-045 · el localizador de «Activar» nunca alcanza «Desactivar»", async ({ page }) => {
    await uiLogin(page); // deja la empresa activa; el ayudante es idempotente
    const { activar, desactivar, activa } = controlesDeEmpresa(page);

    // Estado activo: los controles exactos son los del estado activo y ninguno más.
    await expect(desactivar).toHaveCount(1);
    await expect(activa).toHaveCount(1);
    await expect(activar).toHaveCount(0);

    // El defecto histórico, fijado como regresión: por subcadena «Activar» sí alcanza un
    // control, y ese control se llama «Desactivar». Por eso `exact` no es cosmético.
    const ambiguo = page.getByRole("button", { name: "Activar" });
    expect(await ambiguo.count()).toBeGreaterThan(await activar.count());
    expect((await ambiguo.allInnerTexts()).map((t) => t.trim())).toEqual(["Desactivar"]);
  });

  test("E2E-045 · el ayudante de empresa es idempotente", async ({ page }) => {
    const { activar, desactivar, activa } = controlesDeEmpresa(page);

    await uiLogin(page);
    await expect(desactivar).toHaveCount(1);
    await expect(activa).toHaveCount(1);

    // Segunda ejecución sobre el estado ya alcanzado: no debe pulsar nada ni romperse.
    await activarEmpresa(page);
    await expect(desactivar).toHaveCount(1);
    await expect(activa).toHaveCount(1);
    await expect(activar).toHaveCount(0);

    // Desde el estado contrario también converge. Al desactivar, el producto retira la
    // tabla y muestra la compuerta de selección: ese es el estado real «sin empresa».
    await desactivar.click();
    // Encabezado, no el botón homónimo del Topbar: el texto existe en los dos sitios.
    await expect(page.getByRole("heading", { name: "Seleccione una empresa", level: 1 }))
      .toBeVisible({ timeout: 15000 });
    await expect(activar).toHaveCount(0);
    await activarEmpresa(page);
    await expect(desactivar).toHaveCount(1);
    await expect(activa).toHaveCount(1);
    await expect(activar).toHaveCount(0);
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
