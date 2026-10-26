/**
 * ROLES · Alta de roles personalizados por `POST /roles` contra el backend real de la corrida
 * (ROLES-SIN-API-DE-ALTA; FR-001-040/043/072). Sesión + `roles:create` en el backend; el usuario sin ese
 * permiso lo fabrica `qa/rol_sin_permiso.py` en la base de la corrida. Proyecto `chromium`.
 */
import { resolve } from "node:path";

import { expect, test, type APIRequestContext } from "@playwright/test";
import { iniciarSesion, sesionApi } from "./helpers/sesion";

import { ejecutarPython } from "./helpers/python";

const API = process.env.KONTROL_E2E_API ?? "http://127.0.0.1:8000/api/v1";
const BACKEND = resolve(process.cwd(), "..", "backend");

const marca = (): string => Date.now().toString(36) + Math.random().toString(36).slice(2, 6);

function usuarioSinPermiso(): string {
  const url = process.env.KONTROL_E2E_DB_URL;
  if (!url) {
    throw new Error("KONTROL_E2E_DB_URL es obligatoria: el usuario sin permiso se escribe en la base de la corrida");
  }
  const usuario = `sinrol${marca()}`;
  ejecutarPython(
    [resolve(BACKEND, "..", "..", "qa", "rol_sin_permiso.py"), "DEMO", usuario, "D1", "roles:create"],
    { cwd: BACKEND, env: { ...process.env, KONTROL_DB_URL: url, PYTHONPATH: BACKEND }, encoding: "utf8", timeout: 60_000 },
  );
  return usuario;
}

async function bearer(_request: APIRequestContext, usuario: string): Promise<Record<string, string>> {
  const token = usuario === "admin"
    ? (await sesionApi("admin", { tenant: "DEMO" })).token
    : (await iniciarSesion(usuario, { tenant: "DEMO" })).token;
  return { Authorization: `Bearer ${token}` };
}

test.describe("roles · alta por API", () => {
  test("E2E-ROLE-01..05 · sin sesión 401, sin permiso 403, alta 201 con permisos, duplicado 409, el listado lo trae", async ({ request }) => {
    const code = `E2E-${marca()}`.toUpperCase();
    const anonimo = await request.post(`${API}/roles`, { data: { code, name: "Anónimo" } });
    expect(anonimo.status()).toBe(401);

    const sinPermiso = await bearer(request, usuarioSinPermiso());
    const denegado = await request.post(`${API}/roles`, { data: { code, name: "Denegado" }, headers: sinPermiso });
    expect(denegado.status()).toBe(403);
    expect(((await denegado.json()) as { code: string }).code).toBe("PERMISSION_DENIED");

    const admin = await bearer(request, "admin");
    const alta = await request.post(`${API}/roles`, { data: { code, name: "Rol E2E", permissions: ["roles:view", "users:view"] }, headers: admin });
    expect(alta.status(), await alta.text()).toBe(201);
    const creado = (await alta.json()) as { id: string; code: string; protected: boolean; status: string; company_id: string | null; permissions: string[] };
    expect(creado).toMatchObject({ code, protected: false, status: "ACTIVE", company_id: null, permissions: ["roles:view", "users:view"] });

    const duplicado = await request.post(`${API}/roles`, { data: { code, name: "Otra vez" }, headers: admin });
    expect(duplicado.status()).toBe(409);
    expect(((await duplicado.json()) as { code: string }).code).toBe("ROLE_DUPLICATE");

    const desconocido = await request.post(`${API}/roles`, { data: { code: `${code}-X`, name: "X", permissions: ["nave:despegar"] }, headers: admin });
    expect(desconocido.status()).toBe(422);
    expect(((await desconocido.json()) as { code: string }).code).toBe("PERMISSION_UNKNOWN");

    const listado = (await (await request.get(`${API}/roles`, { headers: admin })).json()) as { items: { id: string; permissions: string[] }[] };
    expect(listado.items.find((r) => r.id === creado.id)?.permissions).toEqual(["roles:view", "users:view"]);
  });
});
