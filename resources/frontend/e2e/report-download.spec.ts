import { readFileSync } from "node:fs";
import { expect, entrarComoUsuario, iniciarSesion, sesionApi, test } from "./helpers/sesion";
import { mundoN6 } from "./helpers/n6-mundo";
import type { APIRequestContext } from "@playwright/test";

const API = process.env.KONTROL_E2E_API ?? "http://127.0.0.1:8000/api/v1";
const TENANT = process.env.KONTROL_E2E_TENANT ?? "DEMO";
const PASSWORD = process.env.KONTROL_E2E_PASSWORD ?? "";

const MUNDO = mundoN6();
const marca = (): string => `${Date.now().toString(36)}${Math.random().toString(36).slice(2, 6)}`.toLowerCase();

async function cabeceras(username: string, empresa?: string): Promise<Record<string, string>> {
  const sesion = await iniciarSesion(username, { tenant: TENANT });
  const headers: Record<string, string> = { Authorization: `Bearer ${sesion.token}` };
  if (empresa) {
    headers["X-Kontrol-Company"] = empresa;
  }
  return headers;
}

async function crearRol(request: APIRequestContext, permisos: string[]): Promise<string> {
  const code = `QA-DL-${marca().toUpperCase()}`;
  const response = await request.post(`${API}/roles`, {
    headers: (await sesionApi("admintenant", { tenant: TENANT })).headers,
    data: { code, name: code, permissions: permisos },
  });
  expect(response.status(), `crear rol ${code}: ${await response.text()}`).toBe(201);
  const body = await response.json();
  expect(body.id, "crear rol debe devolver id").toBeTruthy();
  return body.id as string;
}

async function crearUsuario(request: APIRequestContext): Promise<{ username: string; userId: string }> {
  const username = `dl${marca()}`;
  const response = await request.post(`${API}/users`, {
    headers: (await sesionApi("admintenant", { tenant: TENANT })).headers,
    data: {
      username,
      email: `${username}@example.com`,
      password: PASSWORD,
      must_change_password: false,
    },
  });
  expect(response.status(), `crear usuario ${username}: ${await response.text()}`).toBeGreaterThanOrEqual(200);
  expect(response.status()).toBeLessThan(300);
  const body = await response.json();
  expect(body.id, "crear usuario debe devolver id").toBeTruthy();
  return { username, userId: body.id as string };
}

async function asignar(
  request: APIRequestContext,
  userId: string,
  roleId: string,
  empresa: string | null,
): Promise<void> {
  const response = await request.post(`${API}/users/${userId}/roles`, {
    headers: (await sesionApi("admintenant", { tenant: TENANT })).headers,
    data: { role_id: roleId, company_id: empresa },
  });
  expect(response.status(), `asignar rol ${roleId} a ${userId}: ${await response.text()}`).toBeGreaterThanOrEqual(200);
  expect(response.status()).toBeLessThan(300);
}

async function entrarEn(
  page: import("@playwright/test").Page,
  username: string,
  codigoEmpresa: string,
): Promise<void> {
  await entrarComoUsuario(page, username, { tenant: TENANT, ruta: "/" });
  await expect(page.getByRole("heading", { name: "Seleccione una empresa" }), "debe pedir elegir empresa").toBeVisible();
  await page.getByTestId(`elegir-empresa-${codigoEmpresa}`).click();
  await expect(page.getByTestId("selector-empresa"), `selector debe mostrar empresa ${codigoEmpresa}`).toContainText(
    codigoEmpresa === "D1" ? MUNDO.nombre_a : MUNDO.nombre_b,
  );
}

async function crearExportacion(
  request: APIRequestContext,
  username: string,
  empresa: string,
): Promise<{ id: string; file_ref: string }> {
  const response = await request.post(`${API}/reporting/exports`, {
    headers: await cabeceras(username, empresa),
    data: { report_key: "executive_ventas", format: "PDF", filters: {} },
  });
  expect(response.status(), `crear exportación: ${await response.text()}`).toBe(200);
  const body = (await response.json()) as { id: string; file_ref: string };
  expect(body.id, "crear exportación debe devolver id").toBeTruthy();
  expect(body.file_ref, "crear exportación debe devolver file_ref").toBeTruthy();
  return { id: body.id, file_ref: body.file_ref };
}

async function verFila(page: import("@playwright/test").Page, texto: string): Promise<void> {
  for (let intento = 0; intento < 20; intento += 1) {
    if ((await page.getByText(texto, { exact: true }).count()) > 0) {
      await expect(page.getByText(texto, { exact: true })).toBeVisible();
      return;
    }

    const siguiente = page
      .getByRole("navigation", { name: "Paginación" })
      .last()
      .getByRole("button", { name: "Página siguiente" });
    if ((await siguiente.count()) === 0 || (await siguiente.isDisabled())) {
      break;
    }

    await siguiente.click();
  }

  await expect(
    page.getByText(texto, { exact: true }),
    `la fila ${texto} debe existir en alguna página`,
  ).toBeVisible();
}

test.describe("descarga autenticada de exportaciones · Spec 009 (02E)", () => {
  test("DOWNLOAD-E2E-01 · el usuario autorizado recibe el nombre sugerido y el aviso de éxito", async ({
    page,
    request,
  }) => {
    const rol = await crearRol(request, ["reportes:view", "reportes:export", "ventas:view"]);
    const usuario = await crearUsuario(request);
    await asignar(request, usuario.userId, rol, MUNDO.empresa_a);
    const { file_ref } = await crearExportacion(request, usuario.username, MUNDO.empresa_a);

    await entrarEn(page, usuario.username, "D1");
    await page.goto("/reportes/exportaciones");
    await verFila(page, file_ref);

    const espera = page.waitForEvent("download");
    await page.getByRole("button", { name: `Descargar ${file_ref}` }).click();
    const descarga = await espera;

    expect(descarga.suggestedFilename()).toBe(file_ref);
    await expect(page.getByRole("status").filter({ hasText: "Archivo descargado" })).toBeVisible();
  });

  test("DOWNLOAD-E2E-02 · la descarga devuelve PDF, usa blob y no expone el token", async ({
    page,
    request,
  }) => {
    const rol = await crearRol(request, ["reportes:view", "reportes:export", "ventas:view"]);
    const usuario = await crearUsuario(request);
    await asignar(request, usuario.userId, rol, MUNDO.empresa_a);
    const { id, file_ref } = await crearExportacion(request, usuario.username, MUNDO.empresa_a);

    await entrarEn(page, usuario.username, "D1");
    const pedidas: string[] = [];
    page.on("request", (r) => pedidas.push(r.url()));
    const respuesta = page.waitForResponse((r) => r.url().includes(`/api/v1/reporting/exports/${id}/download`));

    await page.goto("/reportes/exportaciones");
    await verFila(page, file_ref);

    const espera = page.waitForEvent("download");
    await page.getByRole("button", { name: `Descargar ${file_ref}` }).click();
    const descarga = await espera;

    expect((await respuesta).status()).toBe(200);
    expect((await respuesta).headers()["content-type"]).toContain("application/pdf");
    const contenido = readFileSync(await descarga.path());
    expect(contenido.subarray(0, 4).toString()).toBe("%PDF");
    expect(descarga.url().startsWith("blob:")).toBe(true);
    expect(pedidas.some((url) => /Bearer|access_token|token=|Authorization/.test(url))).toBe(false);
  });

  test("DOWNLOAD-E2E-03 · sin reportes:export no aparece el botón y la API devuelve 403", async ({
    page,
    request,
  }) => {
    const exportadorRol = await crearRol(request, ["reportes:view", "reportes:export", "ventas:view"]);
    const exportador = await crearUsuario(request);
    await asignar(request, exportador.userId, exportadorRol, MUNDO.empresa_a);
    const { id, file_ref } = await crearExportacion(request, exportador.username, MUNDO.empresa_a);

    const rol = await crearRol(request, ["reportes:view", "ventas:view"]);
    const usuario = await crearUsuario(request);
    await asignar(request, usuario.userId, rol, MUNDO.empresa_a);

    await entrarEn(page, usuario.username, "D1");
    await page.goto("/reportes/exportaciones");
    await verFila(page, file_ref);
    await expect(page.getByRole("button", { name: `Descargar ${file_ref}` })).toHaveCount(0);

    const respuesta = await request.get(`${API}/reporting/exports/${id}/download`, {
      headers: await cabeceras(usuario.username, MUNDO.empresa_a),
    });
    expect(respuesta.status()).toBe(403);
    expect(((await respuesta.json()) as { code?: string }).code).toBe("PERMISSION_DENIED");
  });

  test("DOWNLOAD-E2E-04 · otra empresa devuelve COMPANY_SCOPE_FORBIDDEN o EXPORT_NOT_FOUND", async ({
    request,
  }) => {
    const rolA = await crearRol(request, ["reportes:view", "reportes:export", "ventas:view"]);
    const usuarioA = await crearUsuario(request);
    await asignar(request, usuarioA.userId, rolA, MUNDO.empresa_a);

    const rolB = await crearRol(request, ["reportes:view", "reportes:export", "ventas:view"]);
    const usuarioB = await crearUsuario(request);
    await asignar(request, usuarioB.userId, rolB, MUNDO.empresa_b);

    const { id } = await crearExportacion(request, usuarioB.username, MUNDO.empresa_b);

    const pedidaOtraEmpresa = await request.get(`${API}/reporting/exports/${id}/download`, {
      headers: await cabeceras(usuarioA.username, MUNDO.empresa_b),
    });
    expect(pedidaOtraEmpresa.status()).toBe(403);
    expect(((await pedidaOtraEmpresa.json()) as { code?: string }).code).toBe("COMPANY_SCOPE_FORBIDDEN");

    const pedidaPropiaEmpresa = await request.get(`${API}/reporting/exports/${id}/download`, {
      headers: await cabeceras(usuarioA.username, MUNDO.empresa_a),
    });
    expect(pedidaPropiaEmpresa.status()).toBe(404);
    expect(((await pedidaPropiaEmpresa.json()) as { code?: string }).code).toBe("EXPORT_NOT_FOUND");
  });

  test("DOWNLOAD-E2E-05 · URL directa sin autenticar devuelve 401 AUTH_REQUIRED", async ({ request }) => {
    const rol = await crearRol(request, ["reportes:view", "reportes:export", "ventas:view"]);
    const usuario = await crearUsuario(request);
    await asignar(request, usuario.userId, rol, MUNDO.empresa_a);
    const { id } = await crearExportacion(request, usuario.username, MUNDO.empresa_a);

    const respuesta = await request.get(`${API}/reporting/exports/${id}/download`);
    expect(respuesta.status()).toBe(401);
    expect(((await respuesta.json()) as { code?: string }).code).toBe("AUTH_REQUIRED");
  });

  test("DOWNLOAD-E2E-06 · sin capacidad de origen muestra permiso denegado y no descarga", async ({
    page,
    request,
  }) => {
    const exportadorRol = await crearRol(request, ["reportes:view", "reportes:export", "ventas:view"]);
    const exportador = await crearUsuario(request);
    await asignar(request, exportador.userId, exportadorRol, MUNDO.empresa_a);
    const { file_ref } = await crearExportacion(request, exportador.username, MUNDO.empresa_a);

    const rol = await crearRol(request, ["reportes:view", "reportes:export"]);
    const usuario = await crearUsuario(request);
    await asignar(request, usuario.userId, rol, MUNDO.empresa_a);

    await entrarEn(page, usuario.username, "D1");
    await page.goto("/reportes/exportaciones");
    await verFila(page, file_ref);
    await expect(page.getByRole("button", { name: `Descargar ${file_ref}` })).toBeVisible();

    let descargas = 0;
    page.on("download", () => {
      descargas += 1;
    });

    await page.getByRole("button", { name: `Descargar ${file_ref}` }).click();
    await expect(
      page.getByRole("alert").filter({ hasText: "No tiene permiso para descargar este archivo." }),
    ).toBeVisible();
    expect(descargas).toBe(0);
  });

  test("DOWNLOAD-E2E-07 · fallo de generación y de red muestran alertas y no descargan", async ({
    page,
    request,
  }) => {
    const rol = await crearRol(request, ["reportes:view", "reportes:export", "ventas:view"]);
    const usuario = await crearUsuario(request);
    await asignar(request, usuario.userId, rol, MUNDO.empresa_a);
    const { id, file_ref } = await crearExportacion(request, usuario.username, MUNDO.empresa_a);

    await entrarEn(page, usuario.username, "D1");
    await page.goto("/reportes/exportaciones");
    await verFila(page, file_ref);

    let descargas = 0;
    page.on("download", () => {
      descargas += 1;
    });

    await page.route(`**/api/v1/reporting/exports/${id}/download`, (ruta) =>
      ruta.fulfill({
        status: 404,
        contentType: "application/json",
        body: JSON.stringify({ code: "EXPORT_FILE_MISSING", message: "El archivo de la exportación no existe" }),
      }),
    );
    await page.getByRole("button", { name: `Descargar ${file_ref}` }).click();
    await expect(
      page.getByRole("alert").filter({ hasText: "El archivo ya no existe o no está disponible." }),
    ).toBeVisible();
    expect(descargas).toBe(0);

    await page.unroute(`**/api/v1/reporting/exports/${id}/download`);
    await page.route(`**/api/v1/reporting/exports/${id}/download`, (ruta) => ruta.abort());
    await page.getByRole("button", { name: `Descargar ${file_ref}` }).click();
    await expect(
      page.getByRole("alert").filter({ hasText: "No hay conexión con el servidor. Inténtelo de nuevo." }),
    ).toBeVisible();
    expect(descargas).toBe(0);
  });

  test("DOWNLOAD-E2E-08 · dos descargas sucesivas conservan el nombre y mantienen el botón habilitado", async ({
    page,
    request,
  }) => {
    const rol = await crearRol(request, ["reportes:view", "reportes:export", "ventas:view"]);
    const usuario = await crearUsuario(request);
    await asignar(request, usuario.userId, rol, MUNDO.empresa_a);
    const { file_ref } = await crearExportacion(request, usuario.username, MUNDO.empresa_a);

    await entrarEn(page, usuario.username, "D1");
    await page.goto("/reportes/exportaciones");
    await verFila(page, file_ref);

    const boton = page.getByRole("button", { name: `Descargar ${file_ref}` });
    await expect(boton).toBeVisible();

    const primeraEspera = page.waitForEvent("download");
    await boton.click();
    const primeraDescarga = await primeraEspera;
    expect(primeraDescarga.suggestedFilename()).toBe(file_ref);

    const segundaEspera = page.waitForEvent("download");
    await boton.click();
    const segundaDescarga = await segundaEspera;
    expect(segundaDescarga.suggestedFilename()).toBe(file_ref);

    await expect(boton).toBeEnabled();
  });

  test("DOWNLOAD-E2E-09 · el Centro completa el proceso con el nombre del CSV auditado", async ({
    page,
    request,
  }) => {
    const rol = await crearRol(request, ["reportes:view", "reportes:export", "ventas:view"]);
    const usuario = await crearUsuario(request);
    await asignar(request, usuario.userId, rol, MUNDO.empresa_a);

    await entrarEn(page, usuario.username, "D1");
    await page.goto("/reportes/centro");

    const espera = page.waitForEvent("download");
    await page.getByRole("button", { name: "Exportar CSV (auditado)" }).click();
    const descarga = await espera;
    expect(descarga.suggestedFilename()).toMatch(/^report-executive_ventas-\d{14}-[0-9a-f]{12}\.csv$/);
  });
});
