import { resolve } from "node:path";
import AxeBuilder from "@axe-core/playwright";
import { expect, entrarComoUsuario, iniciarSesion, test } from "./helpers/sesion";
import { ejecutarPython } from "./helpers/python";

const API = process.env.KONTROL_E2E_API ?? "http://127.0.0.1:8000/api/v1";
const BACKEND = resolve(process.cwd(), "..", "backend");
const marca = () => Date.now().toString(36) + Math.random().toString(36).slice(2, 6);

async function crearUsuarioConPermisos(usuario: string, permisos: string[]): Promise<string> {
  const url = process.env.KONTROL_E2E_DB_URL;
  if (!url) throw new Error("KONTROL_E2E_DB_URL es obligatoria");
  const salida = await ejecutarPython(
    [resolve(BACKEND, "..", "..", "qa", "rol_con_permisos.py"), "DEMO", usuario, "D1", ...permisos],
    { cwd: BACKEND, env: { ...process.env, KONTROL_DB_URL: url, PYTHONPATH: BACKEND }, encoding: "utf8", timeout: 60_000 },
  );
  const lineas = salida.trim().split(/\r?\n/);
  return lineas[lineas.length - 1].trim();
}

test.describe("techo de delegación · Spec 003", () => {
  test("E2E-DEL-01 · UI: el rol ADMIN queda fuera de su autoridad; el propio rol es delegable", async ({ page }) => {
    const gestor = `del${marca()}`;
    await crearUsuarioConPermisos(gestor, ["roles:view", "roles:edit", "roles:create", "users:view", "inventario:view"]);
    await entrarComoUsuario(page, gestor, { tenant: "DEMO", ruta: "/seguridad/roles" });

    await expect(page.getByRole("heading", { name: "Roles y permisos", level: 1 })).toBeVisible();
    const rolSelect = page.getByLabel(/^Rol\b/);
    await expect(rolSelect).toBeEnabled();

    await expect
      .poll(async () => {
        const opciones = await rolSelect.locator("option").allTextContents();
        return opciones.some((t) => t.includes("(ADMIN)"));
      })
      .toBe(true);

    const opcionAdmin = rolSelect.locator("option", { hasText: "(ADMIN)" }).first();
    await expect(opcionAdmin).toBeDisabled();
    await expect(opcionAdmin).toHaveText(/— fuera de su autoridad$/);

    const codigoPropio = `QA-CON-${gestor.toUpperCase()}`;
    const opcionPropia = rolSelect.locator("option", { hasText: codigoPropio }).first();
    await expect(opcionPropia).toBeEnabled();
  });

  test("E2E-DEL-02 · UI: asignar el propio rol dentro del techo", async ({ page }) => {
    const gestor = `del${marca()}`;
    const destino = `del${marca()}`;
    await crearUsuarioConPermisos(gestor, ["roles:view", "roles:edit", "roles:create", "users:view", "inventario:view"]);
    const idDestino = await crearUsuarioConPermisos(destino, ["inventario:view"]);

    const { token } = await iniciarSesion(gestor, { tenant: "DEMO" });
    const rolesResp = await page.request.get(`${API}/roles`, { headers: { Authorization: `Bearer ${token}` } });
    expect(rolesResp.ok(), await rolesResp.text()).toBe(true);
    const rolesBody = await rolesResp.json();
    const rolPropio = rolesBody.items.find((r: { code: string }) => r.code === `QA-CON-${gestor.toUpperCase()}`);
    expect(rolPropio).toBeTruthy();

    await entrarComoUsuario(page, gestor, { tenant: "DEMO", ruta: "/seguridad/roles" });
    await expect(page.getByRole("heading", { name: "Roles y permisos", level: 1 })).toBeVisible();

    const usuarioSelect = page.getByLabel(/^Usuario/);
    await expect(usuarioSelect).toBeEnabled();
    await usuarioSelect.selectOption(idDestino);

    const rolSelect = page.getByLabel(/^Rol\b/);
    await expect(rolSelect).toBeEnabled();
    await rolSelect.selectOption(String(rolPropio.id));

    await page.getByRole("button", { name: "Asignar" }).click();
    await expect(page.getByText("Rol asignado")).toBeVisible();

    const { token: tokenFinal } = await iniciarSesion(gestor, { tenant: "DEMO" });
    const usersResp = await page.request.get(`${API}/users`, { headers: { Authorization: `Bearer ${tokenFinal}` } });
    expect(usersResp.ok(), await usersResp.text()).toBe(true);
    const usuarios = await usersResp.json();
    const usuarioDestino = usuarios.find((u: { id: string | number }) => String(u.id) === String(idDestino));
    expect(usuarioDestino).toBeTruthy();
    expect(usuarioDestino.roles.map((r: { code: string }) => r.code)).toContain(`QA-CON-${gestor.toUpperCase()}`);
  });

  test("E2E-DEL-03 · API: bypass de la interfaz", async ({ request }) => {
    const gestor = `del${marca()}`;
    const destino = `del${marca()}`;
    const idGestor = await crearUsuarioConPermisos(gestor, ["roles:view", "roles:edit", "roles:create", "users:view", "inventario:view"]);
    const idDestino = await crearUsuarioConPermisos(destino, ["inventario:view"]);

    const { token } = await iniciarSesion(gestor, { tenant: "DEMO" });
    const headers = { Authorization: `Bearer ${token}`, "Content-Type": "application/json" };

    const rolesResp = await request.get(`${API}/roles`, { headers });
    expect(rolesResp.ok(), await rolesResp.text()).toBe(true);
    const rolesBody = await rolesResp.json();
    const rolAdmin = rolesBody.items.find((r: { code: string }) => r.code === "ADMIN");
    expect(rolAdmin).toBeTruthy();

    const postSelf = await request.post(`${API}/users/${idGestor}/roles`, { headers, data: { role_id: rolAdmin.id } });
    expect(postSelf.status(), await postSelf.text()).toBe(403);
    expect(await postSelf.text()).toContain("SELF_ESCALATION_FORBIDDEN");

    const postDestino = await request.post(`${API}/users/${idDestino}/roles`, { headers, data: { role_id: rolAdmin.id } });
    expect(postDestino.status(), await postDestino.text()).toBe(403);
    expect(await postDestino.text()).toContain("AUTHORITY_CEILING_EXCEEDED");

    const postOculto = await request.post(`${API}/users/${idDestino}/roles`, { headers, data: { role_id: rolAdmin.id, protected: true } });
    expect(postOculto.status(), await postOculto.text()).toBe(422);

    const postRol = await request.post(`${API}/roles`, {
      headers,
      data: { code: `QA-EXCESO-${marca().toUpperCase()}`, name: "QA exceso", permissions: ["users:mfa_reset"] },
    });
    expect(postRol.status(), await postRol.text()).toBe(403);
    expect(await postRol.text()).toContain("AUTHORITY_CEILING_EXCEEDED");

    const postInvalid = await request.post(`${API}/roles`, {
      headers,
      data: { code: `QA-PROT-${marca().toUpperCase()}`, name: "QA protegido", permissions: ["inventario:view"], protected: true },
    });
    expect(postInvalid.status(), await postInvalid.text()).toBe(422);
  });

  test("E2E-DEL-04 · UI: denegación al intentar quitar un rol que excede el techo", async ({ page }) => {
    const gestor = `del${marca()}`;
    const destino = `del${marca()}`;
    await crearUsuarioConPermisos(gestor, ["roles:view", "roles:edit", "roles:create", "users:view", "inventario:view"]);
    await crearUsuarioConPermisos(destino, ["compras:approve"]);

    await entrarComoUsuario(page, gestor, { tenant: "DEMO", ruta: "/seguridad/roles" });
    await expect(page.getByRole("heading", { name: "Roles y permisos", level: 1 })).toBeVisible();

    const botonQuitar = page.getByRole("button", { name: `Quitar rol QA con permisos (${destino}) a ${destino}` });
    await expect(botonQuitar).toBeVisible();
    await botonQuitar.click();

    const dialogo = page.getByRole("dialog");
    await expect(dialogo).toBeVisible();
    await dialogo.getByRole("button", { name: "Quitar" }).click();

    await expect(page.getByText("No puede conceder ni gestionar una autoridad que usted no tiene.")).toBeVisible();
    await expect(botonQuitar).toBeVisible();
  });

  test("E2E-DEL-05 · UI: cancelar el diálogo de quitar", async ({ page }) => {
    const gestor = `del${marca()}`;
    const destino = `del${marca()}`;
    await crearUsuarioConPermisos(gestor, ["roles:view", "roles:edit", "roles:create", "users:view", "inventario:view"]);
    await crearUsuarioConPermisos(destino, ["inventario:view"]);

    await entrarComoUsuario(page, gestor, { tenant: "DEMO", ruta: "/seguridad/roles" });
    await expect(page.getByRole("heading", { name: "Roles y permisos", level: 1 })).toBeVisible();

    const botonQuitar = page.getByRole("button", { name: `Quitar rol QA con permisos (${destino}) a ${destino}` });
    await expect(botonQuitar).toBeVisible();
    await botonQuitar.click();

    const dialogo = page.getByRole("dialog");
    await expect(dialogo).toBeVisible();
    await dialogo.getByRole("button", { name: "Cancelar" }).click();
    await expect(dialogo).not.toBeVisible();
    await expect(botonQuitar).toBeVisible();
  });

  test("E2E-DEL-06 · Revocación efectiva: la sesión cae y la autoridad perdida no vuelve con una sesión nueva", async ({ request }) => {
    const gestor = `del${marca()}`;
    const destino = `del${marca()}`;
    const idGestor = await crearUsuarioConPermisos(gestor, ["roles:view", "roles:edit", "roles:create", "users:view", "inventario:view"]);
    const idDestino = await crearUsuarioConPermisos(destino, ["inventario:view"]);

    const { token } = await iniciarSesion(gestor, { tenant: "DEMO" });
    const headers = { Authorization: `Bearer ${token}`, "Content-Type": "application/json" };

    const rolesResp = await request.get(`${API}/roles`, { headers });
    expect(rolesResp.ok(), await rolesResp.text()).toBe(true);
    const rolesBody = await rolesResp.json();
    const rolPropio = rolesBody.items.find((r: { code: string }) => r.code === `QA-CON-${gestor.toUpperCase()}`);
    expect(rolPropio).toBeTruthy();

    const deleteResp = await request.delete(`${API}/users/${idGestor}/roles/${rolPropio.id}`, { headers });
    expect(deleteResp.status(), await deleteResp.text()).toBe(200);

    const postResp = await request.post(`${API}/users/${idDestino}/roles`, { headers, data: { role_id: rolPropio.id } });
    expect(postResp.status(), await postResp.text()).toBe(401);
    expect(await postResp.text()).toContain("SESSION_REVOKED");

    const nueva = await iniciarSesion(gestor, { tenant: "DEMO" });
    const postNueva = await request.post(`${API}/users/${idDestino}/roles`, {
      headers: { Authorization: `Bearer ${nueva.token}`, "Content-Type": "application/json" },
      data: { role_id: rolPropio.id },
    });
    expect(postNueva.status(), await postNueva.text()).toBe(403);
    expect(await postNueva.text()).toContain("PERMISSION_DENIED");
  });

  test("E2E-DEL-07 · Accesibilidad y viewport 320 px", async ({ page }) => {
    const gestor = `del${marca()}`;
    await crearUsuarioConPermisos(gestor, ["roles:view", "roles:edit", "roles:create", "users:view", "inventario:view"]);
    await entrarComoUsuario(page, gestor, { tenant: "DEMO", ruta: "/seguridad/roles" });
    await expect(page.getByRole("heading", { name: "Roles y permisos", level: 1 })).toBeVisible();

    const resultados = await new AxeBuilder({ page })
      .include("main")
      .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"])
      .analyze();
    const violacionesGraves = resultados.violations.filter((v) => v.impact === "serious" || v.impact === "critical");
    expect(violacionesGraves).toEqual([]);

    await page.setViewportSize({ width: 320, height: 800 });
    // El menú lateral no se pliega solo (deuda SHELL-SIDEBAR-NOT-RESPONSIVE); se mide la pantalla con el menú plegado, como la E2E MFA-14.
    await page.getByRole("button", { name: "Colapsar menú" }).click();
    await expect(page.getByRole("button", { name: "Expandir menú" })).toBeVisible();
    await expect
      .poll(() => page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth))
      .toBe(true);
  });
});
