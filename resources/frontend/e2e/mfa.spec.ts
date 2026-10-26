/**
 * Spec 002/003 · E2E-MFA — segundo factor por la interfaz real.
 *
 * Cubre de punta a punta el ciclo MFA tal como lo vive una persona: alta forzada
 * con QR y clave manual, login con TOTP, códigos de recuperación, errores,
 * bloqueo, antirrepetición, alta y baja voluntaria, reset administrativo y su
 * efecto en las sesiones, sin secretos en el almacenamiento ni en la URL,
 * accesibilidad y 320 px.
 *
 * OQ-MFA-3: cada prueba usa identidades propias (usuarios nuevos con nombre
 * único) y como mucho DOS códigos TOTP por usuario: el del paso actual y, si
 * procede, el del paso siguiente. Nunca se genera un tercero.
 *
 * La reautenticación dura 5 min desde el login: en E2E el diálogo «Confirme su
 * identidad» NO aparece sin esperar; no lo forzamos aquí (lo cubren las pruebas
 * unitarias).
 *
 * No hay atajos del MFA: ni claves fijas, ni códigos impresos, ni cookies
 * manipuladas para saltarse pasos.
 */
import AxeBuilder from "@axe-core/playwright";
import {
  type APIRequestContext,
  type Browser,
  type BrowserContext,
  type Page,
} from "@playwright/test";

import { codigoTotp, entrar, expect, sesionApi, test } from "./helpers/sesion";

async function elegirEmpresaSiHaceFalta(page: Page): Promise<void> {
  await page.waitForLoadState("networkidle");
  const compuerta = page.getByTestId(/^elegir-empresa-/);
  if (await compuerta.count()) {
    await compuerta.first().click();
    await page.waitForLoadState("networkidle");
  }
}

const API = process.env.KONTROL_E2E_API ?? "http://127.0.0.1:8000/api/v1";
const PASSWORD = process.env.KONTROL_E2E_PASSWORD ?? "";
const TENANT = "DEMO";
const marcas = new Set<string>();

function marcaUnica(): string {
  let marca = "";
  do {
    marca = `${Date.now().toString(36)}${Math.random().toString(36).slice(2, 6)}`;
  } while (marcas.has(marca));
  marcas.add(marca);
  return marca;
}

type UsuarioCreado = {
  username: string;
  password: string;
};

async function crearUsuario(
  request: APIRequestContext,
  caso: string,
  { privilegiado }: { privilegiado: boolean },
): Promise<UsuarioCreado> {
  // Crea usuarios privilegiados de todo el tenant: hace falta autoridad de todo el tenant (techo de delegación, Spec 003).
  const admin = await sesionApi("admintenant", { tenant: TENANT });
  const username = `mfa-${caso}-${marcaUnica()}`;

  const createResp = await request.post(`${API}/users`, {
    headers: admin.headers,
    data: {
      username,
      email: `${username}@example.com`,
      password: PASSWORD,
      must_change_password: false,
    },
  });
  expect(createResp.ok(), `crear usuario ${username}`).toBe(true);
  const user = (await createResp.json()) as { id: string };

  if (privilegiado) {
    const rolesResp = await request.get(`${API}/roles`, { headers: admin.headers });
    expect(rolesResp.ok(), "listar roles").toBe(true);
    const roles = (await rolesResp.json()) as { items: Array<{ id: string; code: string }> };
    const adminRole = roles.items.find((r) => r.code === "ADMIN");
    expect(adminRole, "rol ADMIN").toBeDefined();

    const assignResp = await request.post(`${API}/users/${user.id}/roles`, {
      headers: admin.headers,
      data: { role_id: adminRole?.id, company_id: null },
    });
    expect(assignResp.ok(), `asignar rol ADMIN a ${username}`).toBe(true);
  }

  return { username, password: PASSWORD };
}

async function formularioLogin(page: Page, usuario: string): Promise<void> {
  await page.goto("/login");
  await page.getByLabel("Empresa (código)").fill(TENANT);
  await page.getByLabel("Usuario").fill(usuario);
  await page.getByLabel("Contraseña").fill(PASSWORD);
  await page.getByRole("button", { name: "Iniciar sesión" }).click();
}

async function altaPorInterfaz(
  page: Page,
  opciones?: { yaComenzado?: boolean },
): Promise<{ clave: string; codigos: string[]; paso: number }> {
  if (!opciones?.yaComenzado) {
    await page.getByRole("button", { name: "Comenzar" }).click();
  }
  await expect(page.getByText("Configure su aplicación")).toBeVisible();

  const qr = page.locator("img[src^='data:image/svg+xml']");
  await expect(qr).toBeVisible();

  const claveConEspacios =
    (await page.locator("code[aria-label^='Clave manual']").textContent()) ?? "";
  const clave = claveConEspacios.replace(/\s+/g, "");

  await page.getByRole("button", { name: "Siguiente" }).click();
  await expect(page.getByLabel("Código de verificación")).toBeVisible();

  const paso = Math.floor(Date.now() / 30000);
  const codigo = codigoTotp(clave, paso * 30000);
  await page.getByLabel("Código de verificación").fill(codigo);
  await page.getByRole("button", { name: "Verificar", exact: true }).click();

  const listaCodigos = page.locator("ol li.font-mono");
  await expect(listaCodigos).toHaveCount(10);
  const codigos = await listaCodigos.allTextContents();

  const continuar = page.getByRole("button", { name: "Continuar", exact: true });
  await expect(continuar).toBeDisabled();
  await page.getByLabel("He guardado mis códigos en un lugar seguro").check();
  await expect(continuar).toBeEnabled();
  await continuar.click();

  return { clave, codigos, paso };
}

async function contextoLimpio(browser: Browser): Promise<{ page: Page; context: BrowserContext }> {
  const context = await browser.newContext();
  const page = await context.newPage();
  return { page, context };
}

test.describe("E2E-MFA · segundo factor por la interfaz", () => {
  test("01 alta forzada completa", async ({ page }) => {
    const usuario = await crearUsuario(page.request, "alta", { privilegiado: true });

    await formularioLogin(page, usuario.username);
    await expect(page).toHaveURL(/\/acceso\/mfa\/alta$/);
    await expect(
      page.getByRole("heading", { name: "Verificación en dos pasos" }).first(),
    ).toBeVisible();

    const alta = await altaPorInterfaz(page);
    await expect(page).toHaveURL(/\/$/);

    expect(alta.clave.length, "clave manual visible").toBeGreaterThan(0);
    expect(alta.codigos.length, "10 códigos de recuperación").toBe(10);
  });

  test("02 login con TOTP", async ({ browser, page }) => {
    const usuario = await crearUsuario(page.request, "totp", { privilegiado: true });

    await formularioLogin(page, usuario.username);
    await expect(page).toHaveURL(/\/acceso\/mfa\/alta$/);
    const alta = await altaPorInterfaz(page);

    const { page: page2 } = await contextoLimpio(browser);
    await formularioLogin(page2, usuario.username);
    await expect(page2.getByText("Código de verificación")).toBeVisible();
    await expect(page2.locator("#mfa-code")).toBeVisible();

    const codigoSiguiente = codigoTotp(alta.clave, (alta.paso + 1) * 30000);
    await page2.locator("#mfa-code").fill(codigoSiguiente);
    await page2.getByRole("button", { name: "Verificar", exact: true }).click();
    await expect(page2).toHaveURL(/\/$/);
  });

  test("03 login con código de recuperación", async ({ browser, page }) => {
    const usuario = await crearUsuario(page.request, "recuperacion", { privilegiado: true });

    await formularioLogin(page, usuario.username);
    const alta = await altaPorInterfaz(page);

    const { page: page2 } = await contextoLimpio(browser);
    await formularioLogin(page2, usuario.username);
    await page2
      .getByRole("button", { name: "Usar un código de recuperación", exact: true })
      .click();
    await expect(page2.locator("#recovery-code")).toBeVisible();

    await page2.locator("#recovery-code").fill(alta.codigos[0]);
    await page2.getByRole("button", { name: "Verificar", exact: true }).click();
    await expect(page2).toHaveURL(/\/$/);

    await page2.goto("/seguridad/mfa");
    await elegirEmpresaSiHaceFalta(page2);
    await expect(
      page2.locator("p", { hasText: /Códigos de recuperación disponibles:\s*9/ }),
    ).toBeVisible();
  });

  test("04 código incorrecto", async ({ browser, page }) => {
    const usuario = await crearUsuario(page.request, "incorrecto", { privilegiado: true });

    await formularioLogin(page, usuario.username);
    const alta = await altaPorInterfaz(page);

    const codigoValido = codigoTotp(alta.clave, (alta.paso + 1) * 30000);
    const codigoInvalido = codigoValido === "000000" ? "111111" : "000000";

    const { page: page2 } = await contextoLimpio(browser);
    await formularioLogin(page2, usuario.username);
    await page2.locator("#mfa-code").fill(codigoInvalido);
    await page2.getByRole("button", { name: "Verificar", exact: true }).click();

    await expect(page2.getByText("Código incorrecto. Le quedan 4 intentos.")).toBeVisible();
  });

  test("05 bloqueo", async ({ browser, page }) => {
    const usuario = await crearUsuario(page.request, "bloqueo", { privilegiado: true });

    await formularioLogin(page, usuario.username);
    const alta = await altaPorInterfaz(page);
    const codigoValido = codigoTotp(alta.clave, (alta.paso + 1) * 30000);

    const { page: page2 } = await contextoLimpio(browser);
    await formularioLogin(page2, usuario.username);

    const candidatos = ["000000", "111111", "222222", "333333", "444444", "555555"];
    const invalidos = candidatos.filter(
      (c) => c !== codigoValido && c !== codigoTotp(alta.clave, (alta.paso + 2) * 30000),
    );
    for (let i = 0; i < 5; i += 1) {
      const codigo = invalidos[i];
      await page2.locator("#mfa-code").fill(codigo);
      await page2.getByRole("button", { name: "Verificar", exact: true }).click();
      if (i < 4) {
        await expect(page2.getByText(/Código incorrecto/)).toBeVisible();
      }
    }

    await expect(page2.getByText("Código incorrecto. Le quedan 0 intentos.")).toBeVisible();
    await page2.getByRole("button", { name: "Volver", exact: true }).click();
    await page2.getByLabel("Contraseña").fill(PASSWORD);
    await page2.getByRole("button", { name: "Iniciar sesión" }).click();
    await expect(page2.locator("#password-error")).toContainText(/bloqueada/i);
    await expect(page2.getByLabel("Contraseña")).toBeVisible();
    await expect(page2).toHaveURL(/\/login/);
  });

  test("06 regenerar códigos", async ({ page }) => {
    const usuario = await crearUsuario(page.request, "regenerar", { privilegiado: true });

    await formularioLogin(page, usuario.username);
    const alta = await altaPorInterfaz(page);

    await page.goto("/seguridad/mfa");
    await elegirEmpresaSiHaceFalta(page);
    await expect(
      page.locator("p", { hasText: /Códigos de recuperación disponibles:\s*10/ }),
    ).toBeVisible();

    await page
      .getByRole("button", { name: "Generar códigos nuevos", exact: true })
      .click();
    await expect(page.locator("ol li.font-mono")).toHaveCount(10);

    const nuevos = await page.locator("ol li.font-mono").allTextContents();
    expect(nuevos.length, "10 códigos nuevos").toBe(10);
    const coinciden = nuevos.filter((codigo) => alta.codigos.includes(codigo));
    expect(coinciden.length, "los códigos nuevos difieren de los del alta").toBe(0);

    const ocultar = page.getByRole("button", { name: "Ocultar códigos", exact: true });
    await expect(ocultar).toBeDisabled();
    await page.getByLabel("He guardado mis códigos").check();
    await expect(ocultar).toBeEnabled();
    await ocultar.click();
    await expect(
      page.locator("p", { hasText: /Códigos de recuperación disponibles:\s*10/ }),
    ).toBeVisible();
  });

  test("07 nada en almacenamiento ni URL", async ({ page }) => {
    const usuario = await crearUsuario(page.request, "secreto", { privilegiado: true });
    const urls: string[] = [];
    page.on("framenavigated", (frame) => {
      if (frame === page.mainFrame()) {
        urls.push(frame.url());
      }
    });

    await formularioLogin(page, usuario.username);
    await expect(page).toHaveURL(/\/acceso\/mfa\/alta$/);

    const alta = await altaPorInterfaz(page);
    const clave = alta.clave;
    const codigos = alta.codigos;

    const storage = await page.evaluate(() => ({
      local: { ...localStorage },
      session: { ...sessionStorage },
    }));

    const localTexto = JSON.stringify(storage.local);
    const sessionTexto = JSON.stringify(storage.session);
    expect(localTexto.includes(clave), "localStorage no contiene la clave").toBe(false);
    expect(sessionTexto.includes(clave), "sessionStorage no contiene la clave").toBe(false);
    for (const codigo of codigos) {
      expect(localTexto.includes(codigo), "localStorage no contiene códigos").toBe(false);
      expect(sessionTexto.includes(codigo), "sessionStorage no contiene códigos").toBe(false);
    }
    expect(localTexto.toLowerCase().includes("token"), "localStorage sin token").toBe(false);
    expect(sessionTexto.toLowerCase().includes("token"), "sessionStorage sin token").toBe(false);

    for (const url of urls) {
      expect(url.includes("challenge"), `URL sin challenge: ${url}`).toBe(false);
      expect(url.includes(clave), `URL sin clave: ${url}`).toBe(false);
    }
  });

  test("08 reset administrativo", async ({ browser, page }) => {
    const usuario = await crearUsuario(page.request, "reset", { privilegiado: true });

    const contextoUsuario = await browser.newContext();
    const pageUsuario = await contextoUsuario.newPage();
    await formularioLogin(pageUsuario, usuario.username);
    await altaPorInterfaz(pageUsuario);
    await expect(pageUsuario).toHaveURL(/\/$/);

    await entrar(page, "admin", { tenant: TENANT });
    await page.goto("/seguridad/usuarios");
    const fila = page
      .locator("div")
      .filter({ hasText: usuario.username })
      .filter({ has: page.getByRole("button", { name: "Restablecer verificación", exact: true }) })
      .last();
    await expect(fila).toBeVisible();
    await expect(fila).toContainText("Verificación en dos pasos: activa");
    await fila.getByRole("button", { name: "Restablecer verificación", exact: true }).click();
    await expect(page.getByText("Restablecer la verificación en dos pasos")).toBeVisible();
    await page.getByRole("button", { name: "Restablecer", exact: true }).click();
    await expect(page.getByText("Verificación restablecida")).toBeVisible();
    await expect(page.locator("div").filter({ hasText: usuario.username }).filter({ hasText: "Verificación en dos pasos: no configurada" }).last()).toBeVisible();

    const { page: page2 } = await contextoLimpio(browser);
    await formularioLogin(page2, usuario.username);
    await expect(page2).toHaveURL(/\/acceso\/mfa\/alta$/);
    await contextoUsuario.close();
  });

  test("09 revocación por el reset", async ({ browser, page }) => {
    const usuario = await crearUsuario(page.request, "revocacion", { privilegiado: true });

    const contextoUsuario = await browser.newContext();
    const pageUsuario = await contextoUsuario.newPage();
    await formularioLogin(pageUsuario, usuario.username);
    await altaPorInterfaz(pageUsuario);
    await expect(pageUsuario).toHaveURL(/\/$/);

    await entrar(page, "admin", { tenant: TENANT });
    await page.goto("/seguridad/usuarios");
    const fila = page
      .locator("div")
      .filter({ hasText: usuario.username })
      .filter({ has: page.getByRole("button", { name: "Restablecer verificación", exact: true }) })
      .last();
    await expect(fila).toBeVisible();
    await fila.getByRole("button", { name: "Restablecer verificación", exact: true }).click();
    await page.getByRole("button", { name: "Restablecer", exact: true }).click();
    await expect(page.getByText("Verificación restablecida")).toBeVisible();

    await pageUsuario.reload();
    await elegirEmpresaSiHaceFalta(pageUsuario);
    await expect(pageUsuario).toHaveURL(/\/login/);
    await contextoUsuario.close();
  });

  test("10 antirrepetición", async ({ browser, page }) => {
    const usuario = await crearUsuario(page.request, "antirrepeticion", { privilegiado: true });

    await formularioLogin(page, usuario.username);
    const alta = await altaPorInterfaz(page);

    const { page: page2 } = await contextoLimpio(browser);
    await formularioLogin(page2, usuario.username);
    const codigo = codigoTotp(alta.clave, alta.paso * 30000);
    await page2.locator("#mfa-code").fill(codigo);
    await page2.getByRole("button", { name: "Verificar", exact: true }).click();

    await expect(
      page2.getByText("Ese código ya se usó. Espere al siguiente código de su aplicación."),
    ).toBeVisible();
  });

  test("11 STANDARD voluntario", async ({ page }) => {
    const usuario = await crearUsuario(page.request, "voluntario", { privilegiado: false });

    await formularioLogin(page, usuario.username);
    await expect(page).toHaveURL(/\/$/);

    await page.goto("/seguridad/mfa");
    await elegirEmpresaSiHaceFalta(page);
    await expect(page.getByText("Desactivada")).toBeVisible();

    await page.getByRole("button", { name: "Configurar" }).click();
    await expect(page).toHaveURL(/\/seguridad\/mfa\/alta$/);
    await altaPorInterfaz(page);
    await expect(page).toHaveURL(/\/seguridad\/mfa$/);
    await expect(page.getByText("Activa desde")).toBeVisible();
    await elegirEmpresaSiHaceFalta(page);

    await page
      .getByRole("button", { name: "Quitar la verificación", exact: true })
      .click();
    await expect(page.getByText("Quitar la verificación en dos pasos")).toBeVisible();
    await page.getByRole("button", { name: "Quitar", exact: true }).click();
    await expect(page.getByText("Desactivada")).toBeVisible();
  });

  test("12 PRIVILEGED no puede quitarla", async ({ page }) => {
    const usuario = await crearUsuario(page.request, "privilegiado", { privilegiado: true });

    await formularioLogin(page, usuario.username);
    await altaPorInterfaz(page);

    await page.goto("/seguridad/mfa");
    await elegirEmpresaSiHaceFalta(page);
    await expect(page.getByText("Su política no permite quitarla")).toBeVisible();
    await expect(
      page.getByRole("button", { name: "Quitar la verificación", exact: true }),
    ).toHaveCount(0);
  });

  test("13 la sesión MFA sobrevive a la recarga", async ({ page }) => {
    const usuario = await crearUsuario(page.request, "recarga", { privilegiado: true });

    await formularioLogin(page, usuario.username);
    await altaPorInterfaz(page);
    await expect(page).toHaveURL(/\/$/);

    await page.reload();
    await elegirEmpresaSiHaceFalta(page);
    await expect(page).toHaveURL(/\/$/);
  });

  test("14 accesibilidad y 320 px", async ({ browser, page }) => {
    const WCAG = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"];

    const usuarioA = await crearUsuario(page.request, "a11y-a", { privilegiado: true });
    await formularioLogin(page, usuarioA.username);
    await expect(
      page.getByRole("heading", { name: "Verificación en dos pasos" }).first(),
    ).toBeVisible();
    await page.setViewportSize({ width: 320, height: 800 });
    let results = await new AxeBuilder({ page }).withTags(WCAG).analyze();
    let serious = results.violations.filter(
      (v) => v.impact === "critical" || v.impact === "serious",
    );
    expect(
      serious,
      JSON.stringify(
        serious.map((v) => ({ id: v.id, nodes: v.nodes.length })),
        null,
        2,
      ),
    ).toEqual([]);
    const horizontalLogin = await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    );
    expect(horizontalLogin, "login sin scroll horizontal a 320 px").toBe(true);

    const { page: pageAlta } = await contextoLimpio(browser);
    const usuarioB = await crearUsuario(page.request, "a11y-b", { privilegiado: true });
    await formularioLogin(pageAlta, usuarioB.username);
    await pageAlta.getByRole("button", { name: "Comenzar", exact: true }).click();
    await expect(pageAlta.getByText("Configure su aplicación")).toBeVisible();
    await pageAlta.setViewportSize({ width: 320, height: 800 });
    results = await new AxeBuilder({ page: pageAlta }).withTags(WCAG).analyze();
    serious = results.violations.filter(
      (v) => v.impact === "critical" || v.impact === "serious",
    );
    expect(
      serious,
      JSON.stringify(
        serious.map((v) => ({ id: v.id, nodes: v.nodes.length })),
        null,
        2,
      ),
    ).toEqual([]);
    const horizontalAlta = await pageAlta.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    );
    expect(horizontalAlta, "alta sin scroll horizontal a 320 px").toBe(true);

    await altaPorInterfaz(pageAlta, { yaComenzado: true });
    await pageAlta.setViewportSize({ width: 1280, height: 800 });
    await pageAlta.goto("/seguridad/mfa");
    await elegirEmpresaSiHaceFalta(pageAlta);
    await expect(pageAlta.getByText("Activa desde")).toBeVisible();
    results = await new AxeBuilder({ page: pageAlta }).withTags(WCAG).analyze();
    serious = results.violations.filter(
      (v) => v.impact === "critical" || v.impact === "serious",
    );
    expect(
      serious,
      JSON.stringify(
        serious.map((v) => ({ id: v.id, nodes: v.nodes.length })),
        null,
        2,
      ),
    ).toEqual([]);
    await pageAlta.setViewportSize({ width: 320, height: 800 });
    // La cabecera del shell a 320 px es la deuda SHELL-SIDEBAR-NOT-RESPONSIVE; aquí se mide el contenido MFA.
    results = await new AxeBuilder({ page: pageAlta }).include("main").withTags(WCAG).analyze();
    serious = results.violations.filter(
      (v) => v.impact === "critical" || v.impact === "serious",
    );
    expect(
      serious,
      JSON.stringify(
        serious.map((v) => ({ id: v.id, nodes: v.nodes.length })),
        null,
        2,
      ),
    ).toEqual([]);
    const horizontalMfa = await pageAlta.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    );
    expect(horizontalMfa, "/seguridad/mfa sin scroll horizontal a 320 px").toBe(true);

    const { page: pageLogin2 } = await contextoLimpio(browser);
    await formularioLogin(pageLogin2, usuarioB.username);
    await expect(
      pageLogin2.getByRole("heading", { name: "Verificación en dos pasos" }).first(),
    ).toBeVisible();
    await pageLogin2.setViewportSize({ width: 320, height: 800 });
    results = await new AxeBuilder({ page: pageLogin2 }).withTags(WCAG).analyze();
    serious = results.violations.filter(
      (v) => v.impact === "critical" || v.impact === "serious",
    );
    expect(
      serious,
      JSON.stringify(
        serious.map((v) => ({ id: v.id, nodes: v.nodes.length })),
        null,
        2,
      ),
    ).toEqual([]);
    const horizontalLogin2 = await pageLogin2.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    );
    expect(horizontalLogin2, "paso 2 del login sin scroll horizontal a 320 px").toBe(true);
  });
});
