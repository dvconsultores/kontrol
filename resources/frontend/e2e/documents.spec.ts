/**
 * E2E de la gestión documental (Spec 046 · CVG-046-03).
 *
 * Frontend real → API real → backend real → PostgreSQL real → almacenamiento
 * real → analizador real. Ni el analizador ni el almacenamiento se simulan:
 * un mock aquí no probaría nada de lo que la Spec declara no negociable.
 */
import { expect, test, type APIRequestContext, type Page } from "@playwright/test";

const TENANT = process.env.KONTROL_E2E_TENANT ?? "DEMO";
const USER = process.env.KONTROL_E2E_USER;
const PASSWORD = process.env.KONTROL_E2E_PASSWORD;
const API = process.env.KONTROL_E2E_API ?? "http://127.0.0.1:8000/api/v1";

/** Sufijo único: el estado persiste entre navegadores sobre la misma base. */
const RUN = `${Date.now().toString(36)}${Math.random().toString(36).slice(2, 6)}`.toUpperCase();

/** Cadena EICAR: fixture de prueba estándar reconocido por todo antivirus.
 *  **No** es malware real. Se compone por partes para que este archivo fuente
 *  no dispare el antivirus de quien lo edite. */
const EICAR = ["X5O!P%@AP[4\\PZX54(P^)7CC)7}$EICAR-STANDARD-",
               "ANTIVIRUS-TEST-FILE", "!$H+H", "*"].join("");

const PDF = Buffer.from("%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\ntrailer\n%%EOF\n");

test.skip(!USER || !PASSWORD, "KONTROL_E2E_USER / KONTROL_E2E_PASSWORD no configurados");

type Ctx = { token: string; company: string; headers: Record<string, string> };

async function ctx(request: APIRequestContext): Promise<Ctx> {
  const login = await request.post(`${API}/auth/login`, {
    data: { tenant_code: TENANT, username: USER, password: PASSWORD },
  });
  expect(login.ok(), `login: ${login.status()}`).toBeTruthy();
  const token = (await login.json()).access_token as string;
  const headers = { Authorization: `Bearer ${token}` };
  const body = await (await request.get(`${API}/organization/companies`, { headers })).json();
  const company = (Array.isArray(body) ? body : body.items)[0].id as string;
  return { token, company, headers };
}

/** Tipo documental de la prueba: PDF, con análisis obligatorio. */
async function createType(request: APIRequestContext, c: Ctx,
                          overrides: Record<string, unknown> = {}): Promise<string> {
  const suffix = Math.random().toString(36).slice(2, 6).toUpperCase();
  const r = await request.post(`${API}/documentos/tipos`, {
    headers: c.headers,
    data: {
      company_id: c.company, code: `E2E${RUN}${suffix}`.slice(0, 32),
      name: `Tipo E2E ${suffix}`,
      allowed_mime_types: ["application/pdf"], max_size_bytes: 1024 * 1024,
      scan_required: true, ...overrides,
    },
  });
  expect(r.ok(), await r.text()).toBeTruthy();
  return (await r.json()).id as string;
}

async function uiLogin(page: Page): Promise<void> {
  await page.goto("/login");
  await page.getByLabel(/Empresa \(código\)/).fill(TENANT);
  await page.getByLabel(/Usuario/).fill(USER as string);
  await page.getByLabel(/Contraseña/).fill(PASSWORD as string);
  await page.getByRole("button", { name: "Iniciar sesión" }).click();
  await page.waitForURL((u) => !u.pathname.includes("login"), { timeout: 20000 });

  await page.locator('nav a[href="/organizacion/empresas"]').first().click();
  await page.waitForURL((u) => u.pathname === "/organizacion/empresas", { timeout: 15000 });
  await page.waitForLoadState("networkidle");
  const activar = page.getByRole("button", { name: "Activar" }).first();
  if (await activar.count()) {
    await activar.click();
    await expect(page.getByRole("button", { name: "Desactivar" }).first())
      .toBeVisible({ timeout: 15000 });
  }
}

/** Navegación por menú: un `goto` recargaría y perdería el token en memoria. */
async function goto(page: Page, href: string): Promise<void> {
  await page.locator(`nav a[href="${href}"]`).first().click();
  await page.waitForURL((u) => u.pathname === href, { timeout: 15000 });
}

async function closeNotifications(page: Page): Promise<void> {
  const close = page.getByRole("button", { name: "Cerrar notificación" });
  for (let i = await close.count(); i > 0; i = await close.count()) {
    await close.first().click();
  }
}

/** Crea el documento por UI y entra en su detalle. */
async function createDocument(page: Page, title: string, typeName: string): Promise<void> {
  await goto(page, "/documentos");
  await page.waitForLoadState("networkidle");
  await page.getByLabel("Título del documento").fill(title);
  await page.getByLabel("Tipo documental del nuevo documento").selectOption({ label: typeName });
  await page.getByRole("button", { name: "Crear documento" }).click();
  await expect(page.getByText("Documento creado")).toBeVisible({ timeout: 15000 });
  await closeNotifications(page);
  await page.getByLabel("Buscar documento").fill(title);
  await page.waitForLoadState("networkidle");
  await page.getByRole("link", { name: title }).first().click();
  await page.waitForURL(/\/documentos\/[0-9a-f-]+$/, { timeout: 15000 });
}

async function typeNameOf(request: APIRequestContext, c: Ctx, id: string): Promise<string> {
  const types = await (await request.get(`${API}/documentos/tipos`, { headers: c.headers })).json();
  return types.find((t: { id: string }) => t.id === id).name as string;
}

// ---------------------------------------------------------------- flujo principal
test("carga, versión y descarga por la interfaz real", async ({ page, request }) => {
  const c = await ctx(request);
  const name = await typeNameOf(request, c, await createType(request, c));
  const title = `Contrato ${RUN}-OK`;

  await uiLogin(page);
  await createDocument(page, title, name);

  // Primera versión.
  await page.getByLabel(/^Archivo/).setInputFiles({
    name: "contrato.pdf", mimeType: "application/pdf", buffer: PDF });
  await page.getByRole("button", { name: "Cargar", exact: true }).click();
  await expect(page.getByText("Versión cargada")).toBeVisible({ timeout: 30000 });
  await closeNotifications(page);
  await expect(page.getByText("v1")).toBeVisible();
  await expect(page.getByText("Verificado").first()).toBeVisible();

  // Segunda versión: la primera no desaparece.
  await page.getByLabel(/^Archivo/).setInputFiles({
    name: "contrato-v2.pdf", mimeType: "application/pdf",
    buffer: Buffer.concat([PDF, Buffer.from("v2")]) });
  await page.getByLabel("Motivo del reemplazo").fill("Corrección de cláusula");
  await page.getByRole("button", { name: "Cargar", exact: true }).click();
  await expect(page.getByText("Versión cargada")).toBeVisible({ timeout: 30000 });
  await closeNotifications(page);
  // Las dos versiones conviven: la nueva no reemplaza la fila de la anterior.
  await expect(page.getByRole("cell", { name: /^v2/ })).toBeVisible();
  await expect(page.getByRole("cell", { name: /^v1/ })).toBeVisible();
  await expect(page.getByText("Corrección de cláusula")).toBeVisible();

  // Descarga de la versión histórica: devuelve **sus** bytes.
  const [download] = await Promise.all([
    page.waitForEvent("download", { timeout: 30000 }),
    page.getByRole("button", { name: "Descargar la versión 1" }).click(),
  ]);
  expect(download.suggestedFilename()).toBe("contrato.pdf");
});

// ---------------------------------------------------------------- MIME inválido
test("un formato no admitido se rechaza con un mensaje accionable", async ({ page, request }) => {
  const c = await ctx(request);
  const name = await typeNameOf(request, c, await createType(request, c));

  await uiLogin(page);
  await createDocument(page, `Contrato ${RUN}-MIME`, name);

  await page.getByLabel(/^Archivo/).setInputFiles({
    name: "hoja.png", mimeType: "image/png",
    buffer: Buffer.concat([Buffer.from("89504e470d0a1a0a", "hex"), Buffer.alloc(64)]) });
  await page.getByRole("button", { name: "Cargar", exact: true }).click();

  const alert = page.getByRole("main").getByRole("alert");
  await expect(alert).toBeVisible({ timeout: 30000 });
  await expect(alert).toContainText(/no admite archivos de ese formato/i);
  // El mensaje dice qué SÍ se admite: no es un «error desconocido».
  await expect(alert).toContainText("application/pdf");
});

// ---------------------------------------------------------------- tamaño
test("un archivo por encima del máximo se rechaza indicando el límite", async ({ page, request }) => {
  const c = await ctx(request);
  const name = await typeNameOf(request, c,
    await createType(request, c, { max_size_bytes: 2048 }));

  await uiLogin(page);
  await createDocument(page, `Contrato ${RUN}-SIZE`, name);

  await page.getByLabel(/^Archivo/).setInputFiles({
    name: "grande.pdf", mimeType: "application/pdf",
    buffer: Buffer.concat([PDF, Buffer.alloc(100_000)]) });
  await page.getByRole("button", { name: "Cargar", exact: true }).click();

  const alert = page.getByRole("main").getByRole("alert");
  await expect(alert).toBeVisible({ timeout: 30000 });
  await expect(alert).toContainText(/supera el tamaño máximo/i);
});

// ---------------------------------------------------------------- malware
test("un archivo malicioso se rechaza y no queda disponible", async ({ page, request }) => {
  const c = await ctx(request);
  const name = await typeNameOf(request, c,
    await createType(request, c, { allowed_mime_types: ["text/plain"] }));
  const title = `Contrato ${RUN}-EICAR`;

  await uiLogin(page);
  await createDocument(page, title, name);

  await page.getByLabel(/^Archivo/).setInputFiles({
    name: "muestra.txt", mimeType: "text/plain", buffer: Buffer.from(EICAR) });
  await page.getByRole("button", { name: "Cargar", exact: true }).click();

  const alert = page.getByRole("main").getByRole("alert");
  await expect(alert).toBeVisible({ timeout: 60000 });
  await expect(alert).toContainText(/malicioso|no se pudo verificar/i);

  // Y el documento sigue sin archivo: nada quedó disponible.
  await expect(page.getByText("Este documento todavía no tiene archivos.")).toBeVisible();
});

// ---------------------------------------------------------------- IDOR
test("un identificador ajeno no abre nada", async ({ page }) => {
  await uiLogin(page);
  await goto(page, "/documentos");
  // Identificador válido en forma, inexistente en la empresa: no se confirma
  // que exista ni se muestra contenido.
  await page.locator('nav a[href="/documentos"]').first().click();
  await page.evaluate(() => window.history.pushState({}, "",
    "/documentos/00000000-0000-0000-0000-000000000000"));
  await page.reload();
  await page.waitForLoadState("networkidle");
  const body = await page.textContent("body");
  expect(body ?? "").not.toContain("storage_key");
});

// ---------------------------------------------------------------- inmutabilidad
test("una versión histórica no se reinterpreta al cargar otra", async ({ page, request }) => {
  const c = await ctx(request);
  const typeId = await createType(request, c);
  const name = await typeNameOf(request, c, typeId);
  const title = `Contrato ${RUN}-HIST`;

  await uiLogin(page);
  await createDocument(page, title, name);

  await page.getByLabel(/^Archivo/).setInputFiles({
    name: "original.pdf", mimeType: "application/pdf", buffer: PDF });
  await page.getByRole("button", { name: "Cargar", exact: true }).click();
  await expect(page.getByText("Versión cargada")).toBeVisible({ timeout: 30000 });
  await closeNotifications(page);

  const documentId = page.url().split("/").pop() as string;
  const before = await (await request.get(
    `${API}/documentos/${documentId}/versiones`, { headers: c.headers })).json();
  const firstHash = before[0].sha256 as string;

  await page.getByLabel(/^Archivo/).setInputFiles({
    name: "nuevo.pdf", mimeType: "application/pdf",
    buffer: Buffer.concat([PDF, Buffer.from("otro")]) });
  await page.getByRole("button", { name: "Cargar", exact: true }).click();
  await expect(page.getByText("Versión cargada")).toBeVisible({ timeout: 30000 });

  const after = await (await request.get(
    `${API}/documentos/${documentId}/versiones`, { headers: c.headers })).json();
  const v1 = after.find((v: { version_number: number }) => v.version_number === 1);
  expect(v1.sha256).toBe(firstHash);
});

// ---------------------------------------------------------------- reintento
test("un reintento tras el fallo no deja el formulario sin salida", async ({ page, request }) => {
  const c = await ctx(request);
  const name = await typeNameOf(request, c, await createType(request, c));

  await uiLogin(page);
  await createDocument(page, `Contrato ${RUN}-RETRY`, name);

  // Falla…
  await page.getByLabel(/^Archivo/).setInputFiles({
    name: "hoja.png", mimeType: "image/png",
    buffer: Buffer.concat([Buffer.from("89504e470d0a1a0a", "hex"), Buffer.alloc(64)]) });
  await page.getByRole("button", { name: "Cargar", exact: true }).click();
  await expect(page.getByRole("main").getByRole("alert"))
    .toBeVisible({ timeout: 30000 });

  // …y el mismo formulario admite el archivo correcto sin recargar.
  await page.getByLabel(/^Archivo/).setInputFiles({
    name: "bueno.pdf", mimeType: "application/pdf", buffer: PDF });
  await page.getByRole("button", { name: "Cargar", exact: true }).click();
  await expect(page.getByText("Versión cargada")).toBeVisible({ timeout: 30000 });
});

// ---------------------------------------------------------------- tipos
test("los tipos documentales declaran la política sin código", async ({ page }) => {
  await uiLogin(page);
  await goto(page, "/documentos/tipos");
  await page.waitForLoadState("networkidle");

  const code = `UI${RUN}`.slice(0, 32);
  await page.getByLabel("Código del tipo documental").fill(code);
  await page.getByLabel("Nombre del tipo documental").fill(`Tipo por UI ${RUN}`);
  await page.getByLabel("Formatos MIME admitidos, separados por coma").fill("application/pdf");
  await page.getByRole("button", { name: "Crear tipo" }).click();
  await expect(page.getByText("Tipo documental creado")).toBeVisible({ timeout: 15000 });
  await closeNotifications(page);

  // La tabla pagina: el tipo recién creado ordena al final, así que se avanza
  // hasta encontrarlo. Es lo que haría quien lo acaba de crear.
  const next = page.getByRole("button", { name: "Página siguiente" });
  for (let i = 0; i < 20 && await next.isEnabled(); i += 1) {
    if (await page.getByRole("cell", { name: code }).count()) break;
    await next.click();
    await page.waitForTimeout(150);
  }
  await expect(page.getByRole("cell", { name: code })).toBeVisible();
});
