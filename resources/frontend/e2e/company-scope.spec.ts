import { expect, entrarComoUsuario, iniciarSesion, sesionApi, test } from "./helpers/sesion";
import { mundoN6 } from "./helpers/n6-mundo";
import AxeBuilder from "@axe-core/playwright";
import type { APIRequestContext, APIResponse } from "@playwright/test";

const API = process.env.KONTROL_E2E_API ?? "http://127.0.0.1:8000/api/v1";
const TENANT = process.env.KONTROL_E2E_TENANT ?? "DEMO";
const PASSWORD = process.env.KONTROL_E2E_PASSWORD ?? "";

const marca = (): string => `${Date.now().toString(36)}${Math.random().toString(36).slice(2, 6)}`.toLowerCase();

async function crearActor(
  request: APIRequestContext,
  permisos: string[],
  empresa: string | null,
): Promise<{ username: string; userId: string; roleId: string }> {
  const admin = await sesionApi("admintenant", { tenant: TENANT });
  const roleCode = `QA-CSA-${marca().toUpperCase()}`;
  const roleRes = await request.post(`${API}/roles`, {
    headers: admin.headers,
    data: { code: roleCode, name: roleCode, permissions: permisos },
  });
  expect(roleRes.status()).toBe(201);
  const roleBody = await roleRes.json();
  const roleId: string = roleBody.id;

  const username = `csa${marca()}`;
  const userRes = await request.post(`${API}/users`, {
    headers: admin.headers,
    data: {
      username,
      email: `${username}@example.com`,
      password: PASSWORD,
      must_change_password: false,
    },
  });
  expect(userRes.status()).toBeGreaterThanOrEqual(200);
  expect(userRes.status()).toBeLessThan(300);
  const userBody = await userRes.json();
  const userId: string = userBody.id;

  const assignRes = await request.post(`${API}/users/${userId}/roles`, {
    headers: admin.headers,
    data: { role_id: roleId, company_id: empresa },
  });
  expect(assignRes.status()).toBeGreaterThanOrEqual(200);
  expect(assignRes.status()).toBeLessThan(300);

  return { username, userId, roleId };
}

async function cabeceras(username: string, empresa?: string): Promise<Record<string, string>> {
  const sesion = await iniciarSesion(username, { tenant: TENANT });
  const headers: Record<string, string> = { Authorization: `Bearer ${sesion.token}` };
  if (empresa) {
    headers["X-Kontrol-Company"] = empresa;
  }
  return headers;
}

async function codigo(r: APIResponse): Promise<string> {
  const body = await r.json();
  return body.code as string;
}

test.describe("autoridad por empresa · Spec 003", () => {
  test("E2E-SCOPE-01 · API: actor [maestros:view, maestros:create] en D1 → GET unidades D1 200; D2 403 COMPANY_SCOPE_FORBIDDEN", async ({ request }) => {
    const MUNDO = mundoN6();
    const actor = await crearActor(request, ["maestros:view", "maestros:create"], MUNDO.empresa_a);
    const headersD1 = await cabeceras(actor.username, MUNDO.empresa_a);
    const headersD2 = await cabeceras(actor.username, MUNDO.empresa_b);

    const rD1 = await request.get(`${API}/maestros/unidades`, { headers: headersD1 });
    expect(rD1.status()).toBe(200);

    const rD2 = await request.get(`${API}/maestros/unidades`, { headers: headersD2 });
    expect(rD2.status()).toBe(403);
    expect(await codigo(rD2)).toBe("COMPANY_SCOPE_FORBIDDEN");
  });

  test("E2E-SCOPE-02 · API: POST unidad en D2 → 403 sin efecto; en D1 el mismo POST → 200", async ({ request }) => {
    const MUNDO = mundoN6();
    const actor = await crearActor(request, ["maestros:view", "maestros:create"], MUNDO.empresa_a);
    const headersD1 = await cabeceras(actor.username, MUNDO.empresa_a);
    const headersD2 = await cabeceras(actor.username, MUNDO.empresa_b);
    const code = `CSA${marca().toUpperCase()}`;
    const symbol = `S${marca().toUpperCase()}`.slice(0, 6);

    const rD2 = await request.post(`${API}/maestros/unidades`, {
      headers: headersD2,
      data: { code, name: code, symbol },
    });
    expect(rD2.status()).toBe(403);
    expect(await codigo(rD2)).toBe("COMPANY_SCOPE_FORBIDDEN");

    const admin = await sesionApi("admintenant", { tenant: TENANT });
    const adminHeaders = { ...admin.headers, "X-Kontrol-Company": MUNDO.empresa_b };
    const chequeo = await request.get(`${API}/maestros/unidades?q=${encodeURIComponent(code)}`, {
      headers: adminHeaders,
    });
    expect(chequeo.status()).toBe(200);
    const chequeoBody = await chequeo.json();
    const items: Array<{ code: string }> = chequeoBody.items;
    expect(items.some((item) => item.code === code)).toBe(false);

    const rD1 = await request.post(`${API}/maestros/unidades`, {
      headers: headersD1,
      data: { code, name: code, symbol },
    });
    expect(rD1.status()).toBe(200);
  });

  test("E2E-SCOPE-03 · API: actor [ventas:view, tesoreria:view] en D1 → rutas en D2 403; en D1 200", async ({ request }) => {
    const MUNDO = mundoN6();
    const actor = await crearActor(request, ["ventas:view", "tesoreria:view"], MUNDO.empresa_a);
    const headersD1 = await cabeceras(actor.username, MUNDO.empresa_a);
    const headersD2 = await cabeceras(actor.username, MUNDO.empresa_b);

    const rutas = ["/sales/picking/cola", "/treasury/fx-policies"];
    for (const ruta of rutas) {
      const rD2 = await request.get(`${API}${ruta}`, { headers: headersD2 });
      expect(rD2.status()).toBe(403);
      expect(await codigo(rD2)).toBe("COMPANY_SCOPE_FORBIDDEN");

      const rD1 = await request.get(`${API}${ruta}`, { headers: headersD1 });
      expect(rD1.status()).toBe(200);
    }
  });

  test("E2E-SCOPE-04 · API: actor [reportes:export] en D1 → export en D1 404 REPORT_NOT_FOUND; en D2 403 COMPANY_SCOPE_FORBIDDEN", async ({ request }) => {
    const MUNDO = mundoN6();
    const actor = await crearActor(request, ["reportes:export"], MUNDO.empresa_a);
    const headersD1 = await cabeceras(actor.username, MUNDO.empresa_a);
    const headersD2 = await cabeceras(actor.username, MUNDO.empresa_b);
    const body = { report_key: "no-existe", format: "CSV" };

    const rD1 = await request.post(`${API}/reporting/exports`, { headers: headersD1, data: body });
    expect(rD1.status()).toBe(404);
    expect(await codigo(rD1)).toBe("REPORT_NOT_FOUND");

    const rD2 = await request.post(`${API}/reporting/exports`, { headers: headersD2, data: body });
    expect(rD2.status()).toBe(403);
    expect(await codigo(rD2)).toBe("COMPANY_SCOPE_FORBIDDEN");
  });

  test("E2E-SCOPE-05 · API: actor [tareas:view] en D1 → GET tasks?scope=all en D1 200; en D2 403 PERMISSION_DENIED", async ({ request }) => {
    const MUNDO = mundoN6();
    const actor = await crearActor(request, ["tareas:view"], MUNDO.empresa_a);
    const headersD1 = await cabeceras(actor.username, MUNDO.empresa_a);
    const headersD2 = await cabeceras(actor.username, MUNDO.empresa_b);

    const rD1 = await request.get(`${API}/tasks?scope=all`, { headers: headersD1 });
    expect(rD1.status()).toBe(200);

    const rD2 = await request.get(`${API}/tasks?scope=all`, { headers: headersD2 });
    expect(rD2.status()).toBe(403);
    expect(await codigo(rD2)).toBe("PERMISSION_DENIED");
  });

  test("E2E-SCOPE-06 · API (auditoría de la denegación y bitácora acotada)", async ({ request }) => {
    const MUNDO = mundoN6();
    const actor = await crearActor(request, ["maestros:view"], MUNDO.empresa_a);
    const headersD2 = await cabeceras(actor.username, MUNDO.empresa_b);

    const denied = await request.get(`${API}/maestros/unidades`, { headers: headersD2 });
    expect(denied.status()).toBe(403);
    expect(await codigo(denied)).toBe("COMPANY_SCOPE_FORBIDDEN");

    const admin = await sesionApi("admintenant", { tenant: TENANT });
    const auditUrl = `${API}/audit/events?action=COMPANY_SCOPE_DENIED&entity_id=${encodeURIComponent(MUNDO.empresa_b)}&page_size=100`;
    const rAdmin = await request.get(auditUrl, { headers: admin.headers });
    expect(rAdmin.status()).toBe(200);
    const adminBody = await rAdmin.json();
    const adminItems: Array<{ action: string }> = adminBody.items;
    expect(
      adminItems.some((item) => item.action === "COMPANY_SCOPE_DENIED"),
      `La auditoría debe incluir COMPANY_SCOPE_DENIED. Respuesta: ${JSON.stringify(adminBody)}`,
    ).toBe(true);

    const auditor = await crearActor(request, ["audit:view"], MUNDO.empresa_a);
    const auditorHeaders = await cabeceras(auditor.username);
    const rAuditor = await request.get(auditUrl, { headers: auditorHeaders });
    expect(rAuditor.status()).toBe(200);
    const auditorBody = await rAuditor.json();
    expect(auditorBody.total).toBe(0);
  });

  test("E2E-SCOPE-07 · API: actor [fiscal:create, organization:create] en D1 → catálogos de todo el tenant exigen todas las empresas", async ({ request }) => {
    const MUNDO = mundoN6();
    const actor = await crearActor(request, ["fiscal:create", "organization:create"], MUNDO.empresa_a);
    const headersD1 = await cabeceras(actor.username, MUNDO.empresa_a);

    const rLegal = await request.post(`${API}/fiscal/legal-sources`, {
      headers: headersD1,
      data: { authority: "SENIAT", source_type: "PROVIDENCIA" },
    });
    expect(rLegal.status()).toBe(403);
    expect(await codigo(rLegal)).toBe("COMPANY_SCOPE_FORBIDDEN");

    const empresaCode = `EC${marca().toUpperCase()}`.slice(0, 20);
    const rCompany = await request.post(`${API}/organization/companies`, {
      headers: headersD1,
      data: { code: empresaCode, legal_name: empresaCode, rif: "J-22222222-2" },
    });
    expect(rCompany.status()).toBe(403);
    expect(await codigo(rCompany)).toBe("COMPANY_SCOPE_FORBIDDEN");
  });

  test("E2E-SCOPE-08 · API (revocación con el mismo token)", async ({ request }) => {
    const MUNDO = mundoN6();
    const actor = await crearActor(request, ["maestros:view"], null);
    const headers = await cabeceras(actor.username, MUNDO.empresa_b);

    const antes = await request.get(`${API}/maestros/unidades`, { headers });
    expect(antes.status()).toBe(200);

    const admin = await sesionApi("admintenant", { tenant: TENANT });
    const deleteRes = await request.delete(`${API}/users/${actor.userId}/roles/${actor.roleId}`, {
      headers: admin.headers,
    });
    expect(deleteRes.status()).toBeGreaterThanOrEqual(200);
    expect(deleteRes.status()).toBeLessThan(300);

    const reassignRes = await request.post(`${API}/users/${actor.userId}/roles`, {
      headers: admin.headers,
      data: { role_id: actor.roleId, company_id: MUNDO.empresa_a },
    });
    expect(reassignRes.status()).toBeGreaterThanOrEqual(200);
    expect(reassignRes.status()).toBeLessThan(300);

    const rD2 = await request.get(`${API}/maestros/unidades`, { headers });
    expect(rD2.status()).toBe(403);
    expect(await codigo(rD2)).toBe("COMPANY_SCOPE_FORBIDDEN");

    const headersD1 = { ...headers, "X-Kontrol-Company": MUNDO.empresa_a };
    const rD1 = await request.get(`${API}/maestros/unidades`, { headers: headersD1 });
    expect(rD1.status()).toBe(200);
  });

  test("E2E-SCOPE-09 · API (cabecera manipulada)", async ({ request }) => {
    const MUNDO = mundoN6();
    const actor = await crearActor(request, ["maestros:view"], MUNDO.empresa_a);

    const headersOtroTenant = await cabeceras(actor.username, MUNDO.empresa_c);
    const rOtroTenant = await request.get(`${API}/maestros/unidades`, { headers: headersOtroTenant });
    expect(rOtroTenant.status()).toBe(404);
    expect(await codigo(rOtroTenant)).toBe("COMPANY_NOT_FOUND");

    const headersInexistente = await cabeceras(actor.username, "00000000-0000-0000-0000-000000000000");
    const rInexistente = await request.get(`${API}/maestros/unidades`, { headers: headersInexistente });
    expect(rInexistente.status()).toBe(404);
    expect(await codigo(rInexistente)).toBe("COMPANY_NOT_FOUND");
  });

  test("E2E-SCOPE-10 · UI: actor [maestros:view, organization:view] en D1 ve error acotado en D2 y contenido en D1", async ({ page }) => {
    const MUNDO = mundoN6();
    const actor = await crearActor(page.request, ["maestros:view", "organization:view"], MUNDO.empresa_a);

    await entrarComoUsuario(page, actor.username, { tenant: TENANT, ruta: "/maestros/unidades" });
    await expect(page.getByRole("heading", { name: "Seleccione una empresa" })).toBeVisible();
    await page.getByTestId("elegir-empresa-D2").click();
    await expect(page.getByTestId("selector-empresa")).toContainText(MUNDO.nombre_b);

    const responseD2Promise = page.waitForResponse(
      (response) =>
        response.url().includes("/maestros/unidades") &&
        response.request().method() === "GET" &&
        response.status() === 403,
    );
    await page.goto("/maestros/unidades");
    const responseD2 = await responseD2Promise;
    const bodyD2 = await responseD2.json();
    expect(bodyD2.code, `Respuesta inesperada: ${JSON.stringify(bodyD2)}`).toBe("COMPANY_SCOPE_FORBIDDEN");

    await expect(page.getByText("No fue posible cargar las unidades.")).toBeVisible();
    await expect(page.getByRole("heading", { level: 1, name: "Unidades de medida" })).toBeVisible();

    const axeResults = await new AxeBuilder({ page })
      .include("main")
      .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"])
      .analyze();
    const violacionesGraves = axeResults.violations.filter(
      (violation) => violation.impact === "serious" || violation.impact === "critical",
    );
    expect(
      violacionesGraves,
      `Violaciones de accesibilidad graves/críticas: ${JSON.stringify(violacionesGraves)}`,
    ).toEqual([]);

    await page.getByTestId("selector-empresa").click();
    await page.getByTestId("opcion-empresa-D1").click();
    await expect(page.getByTestId("selector-empresa")).toContainText(MUNDO.nombre_a);
    const responseD1Promise = page.waitForResponse(
      (response) =>
        response.url().includes("/maestros/unidades") &&
        response.request().method() === "GET" &&
        response.status() === 200,
    );
    await page.goto("/maestros/unidades");
    const responseD1 = await responseD1Promise;
    expect(responseD1.status(), `Respuesta inesperada: ${JSON.stringify(await responseD1.text())}`).toBe(200);

    await expect(page.getByText("No fue posible cargar las unidades.")).not.toBeVisible();
  });
});
