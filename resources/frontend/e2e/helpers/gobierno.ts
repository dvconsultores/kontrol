import { type APIRequestContext, type Page } from "@playwright/test";
import { activarEmpresa } from "./empresa";
import { declararAlcance } from "./usuario";
import { entrarComoUsuario, expect, iniciarSesion, sesionApi } from "./sesion";
import { marca } from "./ventas";

export const TENANT = process.env.KONTROL_E2E_TENANT ?? "DEMO";
export const API = process.env.KONTROL_E2E_API ?? "http://127.0.0.1:8000/api/v1";
const PASSWORD = process.env.KONTROL_E2E_PASSWORD ?? "";
export const PDF = Buffer.from("%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\ntrailer\n%%EOF\n");

export const RESPONSABLE_ESTRUCTURA = [
  "organization:view",
  "gobierno_ente:view",
  "gobierno_ente:create",
  "gobierno_ente:edit",
  "gobierno_ente:activate",
  "gobierno_estructura:view",
  "gobierno_estructura:edit",
  "gobierno_estructura:publish",
  "gobierno_estructura:close",
  "documentos:view",
  "documentos:create",
  "documentos:upload",
  "documentos:link",
  "documentos:download",
  "documentos:manage_types",
];

export const CONSULTA_ESTRUCTURA = ["organization:view", "gobierno_estructura:view", "documentos:view"];

export const ANIO = new Date().getFullYear();

export function es2xx(status: number): boolean {
  return status >= 200 && status < 300;
}

export async function crearUsuario(
  request: APIRequestContext,
  adminHeaders: Record<string, string>,
  capacidades: string[],
  companyId: string,
): Promise<{ username: string; headers: Record<string, string> }> {
  const sufijo = marca();
  const username = `gov${sufijo}`;
  const rolCode = `QA-GOV-${sufijo}`.toUpperCase();

  const rolResp = await request.post(`${API}/roles`, {
    headers: adminHeaders,
    data: { code: rolCode, name: "QA Gobierno", permissions: capacidades },
  });
  expect(rolResp.status(), await rolResp.text()).toBe(201);
  const rol = await rolResp.json();

  const userResp = await request.post(`${API}/users`, {
    headers: adminHeaders,
    data: {
      username,
      email: `${username}@example.com`,
      password: PASSWORD,
      must_change_password: false,
    },
  });
  expect(es2xx(userResp.status()), await userResp.text()).toBe(true);
  const user = await userResp.json();

  const asignResp = await request.post(`${API}/users/${user.id}/roles`, {
    headers: adminHeaders,
    data: { role_id: rol.id, company_id: companyId },
  });
  expect(es2xx(asignResp.status()), await asignResp.text()).toBe(true);

  await declararAlcance(username, [companyId], TENANT);

  const sesion = await iniciarSesion(username, { tenant: TENANT });
  const headers = {
    Authorization: `Bearer ${sesion.token}`,
    "X-Kontrol-Company": companyId,
  };

  return { username, headers };
}

export async function prepararMundo(
  request: APIRequestContext,
  capacidades: string[],
): Promise<{ companyId: string; codigo: string; username: string; headers: Record<string, string> }> {
  const admin = await sesionApi("admintenant", { tenant: TENANT });

  const companyResp = await request.post(`${API}/organization/companies`, {
    headers: admin.headers,
    data: {
      code: `GOV${marca()}`.toUpperCase().slice(0, 20),
      legal_name: `Ente de prueba ${marca()}`,
      rif: "G-20000000-0",
    },
  });
  expect(es2xx(companyResp.status()), await companyResp.text()).toBe(true);
  const company = await companyResp.json();
  const companyId = company.id;
  const codigo = company.code;

  const usuario = await crearUsuario(request, admin.headers, capacidades, companyId);

  return { companyId, codigo, username: usuario.username, headers: usuario.headers };
}

export async function crearTipoDocumental(
  request: APIRequestContext,
  headers: Record<string, string>,
  companyId: string,
): Promise<{ id: string; name: string }> {
  const resp = await request.post(`${API}/documentos/tipos`, {
    headers,
    data: {
      company_id: companyId,
      code: `ACTO${marca()}`.toUpperCase().slice(0, 32),
      name: "Acto de creación",
      allowed_mime_types: ["application/pdf"],
      max_size_bytes: 1048576,
      scan_required: true,
    },
  });
  expect(es2xx(resp.status()), await resp.text()).toBe(true);
  const body = await resp.json();
  return { id: body.id, name: body.name };
}

export async function adjuntarDocumentoApi(
  request: APIRequestContext,
  headers: Record<string, string>,
  companyId: string,
  tipoId: string,
  resourceType: string,
  resourceId: string,
): Promise<void> {
  const docResp = await request.post(`${API}/documentos`, {
    headers,
    data: {
      company_id: companyId,
      document_type_id: tipoId,
      title: "Acto de prueba",
    },
  });
  expect(es2xx(docResp.status()), await docResp.text()).toBe(true);
  const doc = await docResp.json();

  const versionResp = await request.post(`${API}/documentos/${doc.id}/versiones`, {
    headers,
    multipart: {
      file: {
        name: "acto.pdf",
        mimeType: "application/pdf",
        buffer: PDF,
      },
    },
  });
  expect(es2xx(versionResp.status()), await versionResp.text()).toBe(true);

  const vinculoResp = await request.post(`${API}/documentos/${doc.id}/vinculos`, {
    headers,
    data: { resource_type: resourceType, resource_id: resourceId },
  });
  expect(es2xx(vinculoResp.status()), await vinculoResp.text()).toBe(true);
}

export async function enteActivo(
  request: APIRequestContext,
  headers: Record<string, string>,
  companyId: string,
  tipoId: string,
): Promise<string> {
  const crearResp = await request.post(`${API}/gobierno/ente`, {
    headers,
    data: { denominacion: "Alcaldía del Municipio Demo" },
  });
  expect(crearResp.status(), await crearResp.text()).toBe(201);
  const ente = await crearResp.json();

  const patchResp = await request.patch(`${API}/gobierno/ente`, {
    headers: { ...headers, "If-Match": '"1"' },
    data: {
      nivel_territorial: "MUNICIPAL",
      forma_organizativa: "ADMINISTRACION_CENTRAL",
      entidad_federal: "Lara",
      municipio: "Iribarren",
      acto_tipo: "ORDENANZA",
      acto_numero: "1",
      acto_fecha: "2020-01-15",
      acto_publicacion: "Gaceta Municipal N.º 1 del 15/01/2020",
    },
  });
  expect(patchResp.status(), await patchResp.text()).toBe(200);

  await adjuntarDocumentoApi(request, headers, companyId, tipoId, "GovernmentEntity", ente.id);

  const activarResp = await request.post(`${API}/gobierno/ente/activar`, {
    headers: { ...headers, "If-Match": '"2"' },
  });
  expect(activarResp.status(), await activarResp.text()).toBe(200);

  return ente.id;
}

export async function cerrarNotificaciones(page: Page): Promise<void> {
  const cerrar = page.getByRole("button", { name: "Cerrar notificación" });
  for (let i = await cerrar.count(); i > 0; i = await cerrar.count()) {
    await cerrar.first().click();
  }
}

export async function entrarEnGobierno(
  page: Page,
  username: string,
  codigo: string,
  enlace: string,
  ruta?: string,
): Promise<void> {
  await entrarComoUsuario(page, username, { tenant: TENANT, ruta: "/" });
  await activarEmpresa(page, codigo);
  await page.locator(`nav a[href="${enlace}"]`).first().click();
  await page.waitForURL((u) => u.pathname === (ruta ?? enlace));
}
