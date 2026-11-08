import { expect, test, entrar, sesionApi } from "./helpers/sesion";

const TENANT = process.env.KONTROL_E2E_TENANT ?? "DEMO";
const USER = process.env.KONTROL_E2E_USER ?? "admin";
const API = process.env.KONTROL_E2E_API ?? "http://127.0.0.1:8000/api/v1";

test("crear, editar, aprobar y pagar a un proveedor", async ({ page, request }) => {
  const sufijo = Date.now().toString().slice(-8);
  const codigo = `E2E-TER-${sufijo}`;
  const rif = `J-${sufijo}-1`;
  const nombre = `Proveedor E2E ${sufijo}`;

  const token = (await sesionApi(USER, { tenant: TENANT })).token;
  const authHeaders = {
    Authorization: `Bearer ${token}`,
  };
  const companiesResp = await request.get(`${API}/organization/companies`, {
    headers: authHeaders,
  });
  expect(companiesResp.ok()).toBeTruthy();
  const companiesBody = (await companiesResp.json()) as {
    items: Array<{ id: string }>;
  };
  const company = companiesBody.items[0].id;
  const headers = {
    ...authHeaders,
    "X-Kontrol-Company": company,
  };

  await entrar(page, USER, { tenant: TENANT });

  await page.goto("/maestros/terceros");
  await page.getByRole("link", { name: /Nuevo tercero/i }).click();

  await page.getByLabel(/^Código/).fill(codigo);
  await page.getByLabel(/^Nombre \*/).fill(nombre);
  await page.getByLabel(/^RIF/).fill(rif);
  await page.getByLabel("Proveedor").check();
  await page.getByRole("button", { name: "Guardar tercero" }).click();

  await expect(page).toHaveURL(/\/maestros\/terceros\/[0-9a-f-]{36}$/);
  await expect(
    page.getByRole("heading", { name: nombre }),
  ).toBeVisible();
  await expect(
    page.getByRole("dialog", { name: /¿Descartar los cambios sin guardar\?/ }),
  ).toHaveCount(0);

  const match = page.url().match(/\/maestros\/terceros\/([0-9a-f-]{36})$/);
  expect(match).not.toBeNull();
  const partyId = match![1];

  await page.getByLabel(/^Razón social/).fill(`Razón ${sufijo}`);
  await page.getByRole("button", { name: "Guardar cambios" }).click();
  await expect(
    page.getByRole("button", { name: "Guardar cambios" }),
  ).toBeDisabled();

  await page.getByLabel("Rol a agregar").selectOption("CLIENTE");
  await page.getByRole("button", { name: "Agregar rol" }).click();
  await expect(
    page.getByRole("button", { name: "Quitar rol Cliente" }),
  ).toBeVisible();

  const earlyPayment = await request.post(`${API}/purchasing/payments`, {
    headers,
    data: { party_id: partyId, amount: 100 },
  });
  expect(earlyPayment.status()).toBe(409);
  const earlyBody = (await earlyPayment.json()) as { code: string };
  expect(earlyBody.code).toBe("SUPPLIER_NOT_APPROVED");

  await page.getByRole("button", { name: "Agregar en Cuentas bancarias" }).click();
  await page.getByLabel(/^Banco/).fill("Banco E2E");
  await page.getByLabel(/^Número de cuenta/).fill("01020000000000000001");
  await page.getByRole("button", { name: "Guardar", exact: true }).click();
  await expect(page.getByText("Banco E2E 01020000000000000001")).toBeVisible();

  await page
    .getByLabel("Evidencia de Banco E2E 01020000000000000001")
    .fill("constancia E2E");
  await page.getByRole("button", { name: "Verificar Banco E2E" }).click();
  await expect(
    page.getByText("Banco E2E 01020000000000000001 · Verificada"),
  ).toBeVisible();

  await page.getByRole("button", { name: "Aprobar proveedor" }).click();
  await expect(
    page.getByText("Estado de aprobación: Aprobado"),
  ).toBeVisible();

  const approvedPayment = await request.post(`${API}/purchasing/payments`, {
    headers,
    data: { party_id: partyId, amount: 100 },
  });
  expect(approvedPayment.status()).toBe(200);
  const approvedBody = (await approvedPayment.json()) as { status: string };
  expect(approvedBody.status).toBe("DRAFT");

  await expect(
    page.getByText("Aprobación de proveedor cambiada"),
  ).toBeVisible();
});
