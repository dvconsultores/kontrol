import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "./helpers/sesion";
import type { APIRequestContext, Page } from "@playwright/test";
import {
  ANIO,
  API,
  RESPONSABLE_ESTRUCTURA,
  TENANT,
  adjuntarDocumentoApi,
  cargoVigenteApi,
  crearTipoDocumental,
  crearUsuario,
  enteActivo,
  entrarEnGobierno,
  es2xx,
  estructuraVigenteApi,
  prepararMundo,
} from "./helpers/gobierno";
import { declararAlcance } from "./helpers/usuario";
import { entrarComoUsuario, iniciarSesion, sesionApi } from "./helpers/sesion";

const PASSWORD = process.env.KONTROL_E2E_PASSWORD ?? "";

const WCAG = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"];

const RESPONSABLE = [
  ...RESPONSABLE_ESTRUCTURA,
  "gobierno_cargos:view",
  "gobierno_cargos:edit",
  "gobierno_cargos:publish",
  "gobierno_actos:view",
  "gobierno_actos:edit",
  "gobierno_actos:issue",
  "gobierno_ocupacion:view",
  "gobierno_ocupacion:manage",
  "gobierno_ocupacion:activate",
  "gobierno_ocupacion:revoke",
  "gobierno_identidad:view",
  "gobierno_identidad:manage",
  "gobierno_identidad:activate",
  "gobierno_identidad:revoke",
  "gobierno_auditoria:view",
];

const ACTIVADOR_ID = [
  "organization:view",
  "gobierno_identidad:view",
  "gobierno_identidad:activate",
  "gobierno_identidad:revoke",
];

const TITULAR = ["organization:view", "gobierno_actos:view", "gobierno_actos:issue"];

function hoyCaracas(): string {
  return new Intl.DateTimeFormat("en-CA", { timeZone: "America/Caracas" }).format(new Date());
}

async function sinViolacionesSerias(page: Page, contexto: string): Promise<void> {
  const resultados = await new AxeBuilder({ page }).include("main").withTags(WCAG).analyze();
  const serias = resultados.violations.filter((v) => ["critical", "serious"].includes(v.impact ?? ""));
  expect(serias.map((v) => ({ id: v.id, help: v.help })), contexto).toEqual([]);
}

async function funcionarioApi(
  request: APIRequestContext,
  headers: Record<string, string>,
  nombre: string,
): Promise<{ id: string }> {
  const resp = await request.post(`${API}/gobierno/ocupacion/funcionarios`, {
    headers,
    data: {
      nombre,
      tipo_documento: "V",
      numero_documento: String(Math.floor(10000000 + Math.random() * 89999999)),
    },
  });
  expect(resp.status(), await resp.text()).toBe(201);
  return resp.json();
}

async function asignacionApi(
  request: APIRequestContext,
  headers: Record<string, string>,
  datos: {
    funcionario_id: string;
    cargo_id: string;
    acto_id: string;
    fundamento: string;
    desde?: string;
  },
): Promise<{ id: string; version: string }> {
  const resp = await request.post(`${API}/gobierno/ocupacion/asignaciones`, {
    headers,
    data: {
      funcionario_id: datos.funcionario_id,
      cargo_id: datos.cargo_id,
      figura: "TITULAR",
      acto_id: datos.acto_id,
      desde: datos.desde ?? hoyCaracas(),
      fundamento: datos.fundamento,
      cargo_origen_id: null,
      hasta: null,
      rendicion: null,
      maxima_autoridad: false,
      autorizacion_concejo: null,
      declara_delegable: false,
      competencias: [],
    },
  });
  expect(resp.status(), await resp.text()).toBe(201);
  return resp.json();
}

function activarApi(
  request: APIRequestContext,
  headers: Record<string, string>,
  asignacion: { id: string; version: string },
) {
  return request.post(`${API}/gobierno/ocupacion/asignaciones/${asignacion.id}/activar`, {
    headers: { ...headers, "If-Match": `"${asignacion.version}"` },
    data: {},
  });
}

async function actoEmitidoApi(
  request: APIRequestContext,
  mundo: { headers: Record<string, string>; companyId: string },
  tipoId: string,
  cargoId: string,
  numero: string,
): Promise<{ id: string; numero: string }> {
  const resp = await request.post(`${API}/gobierno/actos`, {
    headers: mundo.headers,
    data: {
      tipo: "RESOLUCION",
      numero,
      caracter: "GENERAL",
      asunto: `Asunto ${numero}`,
      simple_tramite: false,
      cargo_id: cargoId,
      fecha: hoyCaracas(),
      lugar: "Caracas",
      fundamento_competencia: "Reglamento interno, art. 12",
      funcionario: "Funcionaria de prueba",
      titularidad: "TITULAR",
      hechos: "Hechos de prueba",
      fundamentos: "Fundamentos legales de prueba",
      decision: "Decisión de prueba",
      competencia: { accion: "APROBAR", materia: "CONTRATACIONES" },
    },
  });
  expect(resp.status(), await resp.text()).toBe(201);
  const id = (await resp.json()).id as string;
  await adjuntarDocumentoApi(request, mundo.headers, mundo.companyId, tipoId, "GovernmentAct", id);
  const docsResp = await request.get(`${API}/documentos/por-recurso/GovernmentAct/${id}`, { headers: mundo.headers });
  expect(docsResp.status(), await docsResp.text()).toBe(200);
  const docs = await docsResp.json();
  const emitirResp = await request.post(`${API}/gobierno/actos/${id}/emitir`, {
    headers: { ...mundo.headers, "If-Match": '"1"' },
    data: { documento_acto_id: docs[0].id },
  });
  expect(emitirResp.status(), await emitirResp.text()).toBe(200);
  await adjuntarDocumentoApi(request, mundo.headers, mundo.companyId, tipoId, "GovernmentAct", id);
  const docsDespues = await request.get(`${API}/documentos/por-recurso/GovernmentAct/${id}`, { headers: mundo.headers });
  expect(docsDespues.status(), await docsDespues.text()).toBe(200);
  const docsList = await docsDespues.json();
  const documentoEficacia = docsList.find((d: { id: string }) => d.id !== docs[0].id);
  expect(documentoEficacia, "Debe existir un segundo documento para la eficacia").toBeTruthy();
  const eficaciaResp = await request.post(`${API}/gobierno/actos/${id}/eficacia`, {
    headers: { ...mundo.headers, "If-Match": '"2"' },
    data: {
      medio: "GACETA",
      referencia: "Gaceta N.º 1",
      fecha: hoyCaracas(),
      documento_eficacia_id: documentoEficacia.id,
    },
  });
  expect(eficaciaResp.status(), await eficaciaResp.text()).toBe(200);
  return { id, numero };
}

async function mundoOcupacion(request: APIRequestContext) {
  const mundo = await prepararMundo(request, RESPONSABLE);
  const tipo = await crearTipoDocumental(request, mundo.headers, mundo.companyId);
  await enteActivo(request, mundo.headers, mundo.companyId, tipo.id);
  const estructura = await estructuraVigenteApi(request, mundo.headers, mundo.companyId, tipo.id, ANIO);
  const emisor = await cargoVigenteApi(request, mundo.headers, mundo.companyId, tipo.id, ANIO, estructura.da01Id, "EMISOR-SEP");
  const objetivo = await cargoVigenteApi(request, mundo.headers, mundo.companyId, tipo.id, ANIO, estructura.da01Id, "OBJETIVO-SEP");
  return { mundo, tipoId: tipo.id, emisorId: emisor.id, objetivoId: objetivo.id };
}

async function registrarVinculoApi(
  request: APIRequestContext,
  headers: Record<string, string>,
  datos: { user_id: string; official_id: string; desde: string; motivo: string },
): Promise<{ id: string; version: string }> {
  const resp = await request.post(`${API}/gobierno/identidad/vinculos`, {
    headers,
    data: {
      user_id: datos.user_id,
      official_id: datos.official_id,
      desde: datos.desde,
      hasta: null,
      motivo: datos.motivo,
      soporte: null,
    },
  });
  expect(resp.status(), await resp.text()).toBe(201);
  return resp.json();
}

async function activarVinculoApi(
  request: APIRequestContext,
  headers: Record<string, string>,
  vinculo: { id: string; version: string },
) {
  return request.post(`${API}/gobierno/identidad/vinculos/${vinculo.id}/activar`, {
    headers: { ...headers, "If-Match": `"${vinculo.version}"` },
    data: {},
  });
}

async function obtenerOpciones(request: APIRequestContext, headers: Record<string, string>) {
  const resp = await request.get(`${API}/gobierno/identidad/opciones`, { headers });
  expect(resp.status(), await resp.text()).toBe(200);
  return resp.json();
}

async function crearUsuarioSinRol(
  request: APIRequestContext,
  adminHeaders: Record<string, string>,
): Promise<{ username: string; id: string }> {
  const sufijo = Date.now().toString(36) + Math.random().toString(36).slice(2, 6);
  const username = `sep${sufijo}`;
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
  return { username, id: user.id };
}

async function asignarRolProtegido(
  request: APIRequestContext,
  adminHeaders: Record<string, string>,
  userId: string,
  roleCode: string,
): Promise<void> {
  const rolesResp = await request.get(`${API}/roles`, { headers: adminHeaders });
  expect(rolesResp.status(), await rolesResp.text()).toBe(200);
  const roles = (await rolesResp.json()).items;
  const rol = roles.find((r: { code: string; protected: boolean }) => r.code === roleCode && r.protected === true);
  expect(rol, `Rol protegido ${roleCode} no encontrado`).toBeTruthy();
  const asignResp = await request.post(`${API}/users/${userId}/roles`, {
    headers: adminHeaders,
    data: { role_id: rol.id },
  });
  expect(es2xx(asignResp.status()), await asignResp.text()).toBe(true);
}

test.describe("Gobierno separación", () => {
  test("CTL-03-E2E · recorrido completo", async ({ request, page }) => {
    test.setTimeout(420_000);
    const { mundo, tipoId, emisorId, objetivoId } = await mundoOcupacion(request);
    const admin = await sesionApi("admintenant", { tenant: TENANT });

    // Actores
    const adminPuro = await crearUsuarioSinRol(request, admin.headers);
    await asignarRolProtegido(request, admin.headers, adminPuro.id, "ADMIN");
    await declararAlcance(adminPuro.username, [mundo.companyId], TENANT);

    const dual = await crearUsuarioSinRol(request, admin.headers);
    await asignarRolProtegido(request, admin.headers, dual.id, "ADMIN");
    await asignarRolProtegido(request, admin.headers, dual.id, "FUNCIONAL_COMPLETO");
    await declararAlcance(dual.username, [mundo.companyId], TENANT);

    const activadorOrg04 = await crearUsuario(request, admin.headers, [
      "organization:view",
      "gobierno_ocupacion:view",
      "gobierno_ocupacion:activate",
    ], mundo.companyId);
    const activadorId = await crearUsuario(request, admin.headers, ACTIVADOR_ID, mundo.companyId);
    const legitimo = await crearUsuario(request, admin.headers, TITULAR, mundo.companyId);

    // P1: ADMIN puro por API
    const adminPuroSesion = await iniciarSesion(adminPuro.username, { tenant: TENANT });
    const adminPuroHeaders = {
      Authorization: `Bearer ${adminPuroSesion.token}`,
      "X-Kontrol-Company": mundo.companyId,
    };

    const funcionalRolResp = await request.get(`${API}/roles`, { headers: admin.headers });
    const funcionalRol = (await funcionalRolResp.json()).items.find(
      (r: { code: string; protected: boolean }) => r.code === "FUNCIONAL_COMPLETO" && r.protected === true,
    );
    expect(funcionalRol).toBeTruthy();

    const selfEscResp = await request.post(`${API}/users/${adminPuro.id}/roles`, {
      headers: adminPuroHeaders,
      data: { role_id: funcionalRol.id },
    });
    expect(selfEscResp.status()).toBe(403);
    expect((await selfEscResp.json()).code).toBe("SELF_ESCALATION_FORBIDDEN");

    const ceilingResp = await request.post(`${API}/users/${dual.id}/roles`, {
      headers: adminPuroHeaders,
      data: { role_id: funcionalRol.id },
    });
    expect(ceilingResp.status()).toBe(403);
    expect((await ceilingResp.json()).code).toBe("AUTHORITY_CEILING_EXCEEDED");

    const sufijo = Date.now().toString(36);
    const rootRoleResp = await request.post(`${API}/roles`, {
      headers: adminPuroHeaders,
      data: {
        code: `ROOT${sufijo}`,
        name: "Root intento",
        company_id: mundo.companyId,
        permissions: ["gobierno_decision:decide"],
      },
    });
    expect(rootRoleResp.status()).toBe(403);
    const rolesDespues = await request.get(`${API}/roles`, { headers: admin.headers });
    const rolesLista = (await rolesDespues.json()).items;
    expect(rolesLista.some((r: { code: string }) => r.code === `ROOT${sufijo}`)).toBe(false);

    const admin2Resp = await request.post(`${API}/roles`, {
      headers: adminPuroHeaders,
      data: {
        code: `ADMIN2${sufijo}`,
        name: "Admin técnico",
        company_id: mundo.companyId,
        permissions: ["users:view", "roles:view"],
      },
    });
    expect(admin2Resp.status()).toBe(201);

    // P2: ADMIN puro en navegador
    await entrarComoUsuario(page, adminPuro.username, { tenant: TENANT, ruta: "/seguridad/usuarios" });
    await expect(page.getByRole("heading", { level: 1, name: "Usuarios" })).toBeVisible();
    await page.goto("/gobierno/control/separacion");
    await expect(page.getByRole("heading", { level: 1, name: "Separación técnica y funcional" })).toHaveCount(0);

    // P3: Preparación previa del legítimo (antes de activar exigencia de identidad)
    const actoLegitimo = await actoEmitidoApi(request, mundo, tipoId, emisorId, `LEG-${Date.now()}`);
    const funcionario = await funcionarioApi(request, mundo.headers, "Persona Separación Prueba");
    const asignacion = await asignacionApi(request, mundo.headers, {
      funcionario_id: funcionario.id,
      cargo_id: objetivoId,
      acto_id: actoLegitimo.id,
      fundamento: "Fundamento de prueba para separación",
    });
    const activarAsignacionResp = await activarApi(request, activadorOrg04.headers, asignacion);
    expect(activarAsignacionResp.status()).toBe(200);

    const opciones = await obtenerOpciones(request, mundo.headers);
    const legitimoUserId = opciones.cuentas.find((c: { usuario: string; id: string }) => c.usuario === legitimo.username)?.id;
    expect(legitimoUserId).toBeTruthy();
    const vinculo = await registrarVinculoApi(request, mundo.headers, {
      user_id: legitimoUserId,
      official_id: funcionario.id,
      desde: hoyCaracas(),
      motivo: "Motivo de vínculo para separación",
    });
    const activarVinculoResp = await activarVinculoApi(request, activadorId.headers, vinculo);
    expect(activarVinculoResp.status()).toBe(200);

    const legitimoSesionPrevia = await iniciarSesion(legitimo.username, { tenant: TENANT });
    const legitimoHeaders = {
      Authorization: `Bearer ${legitimoSesionPrevia.token}`,
      "X-Kontrol-Company": mundo.companyId,
    };

    // P3: Exigencia de identidad
    const politicaResp = await request.get(`${API}/gobierno/identidad/politica`, { headers: mundo.headers });
    expect(politicaResp.status()).toBe(200);
    const politica = await politicaResp.json();
    const activarPoliticaResp = await request.post(`${API}/gobierno/identidad/politica`, {
      headers: { ...mundo.headers, "If-Match": String(politica.version) },
      data: { exige_identidad: true, motivo: "Activación para la prueba CTL-03." },
    });
    expect(activarPoliticaResp.status()).toBe(200);

    // P4: Dual intenta emitir acto sin vínculo
    const actoDual = await request.post(`${API}/gobierno/actos`, {
      headers: mundo.headers,
      data: {
        tipo: "RESOLUCION",
        numero: `DUAL-${Date.now()}`,
        caracter: "GENERAL",
        asunto: "Asunto dual",
        simple_tramite: false,
        cargo_id: emisorId,
        fecha: hoyCaracas(),
        lugar: "Caracas",
        fundamento_competencia: "Reglamento interno, art. 12",
        funcionario: "Funcionaria de prueba",
        titularidad: "TITULAR",
        hechos: "Hechos de prueba",
        fundamentos: "Fundamentos legales de prueba",
        decision: "Decisión de prueba",
        competencia: { accion: "APROBAR", materia: "CONTRATACIONES" },
      },
    });
    expect(actoDual.status()).toBe(201);
    const actoDualId = (await actoDual.json()).id as string;
    await adjuntarDocumentoApi(request, mundo.headers, mundo.companyId, tipoId, "GovernmentAct", actoDualId);
    const docsDualResp = await request.get(`${API}/documentos/por-recurso/GovernmentAct/${actoDualId}`, { headers: mundo.headers });
    const docsDual = await docsDualResp.json();
    const dualSesion = await iniciarSesion(dual.username, { tenant: TENANT });
    const dualHeaders = {
      Authorization: `Bearer ${dualSesion.token}`,
      "X-Kontrol-Company": mundo.companyId,
    };
    const emitirDualResp = await request.post(`${API}/gobierno/actos/${actoDualId}/emitir`, {
      headers: { ...dualHeaders, "If-Match": '"1"' },
      data: { documento_acto_id: docsDual[0].id },
    });
    expect(emitirDualResp.status()).toBe(403);
    expect((await emitirDualResp.json()).code).toBe("GOV_IDENTITY_LINK_REQUIRED");

    // Legitimo emite acto LEG2 con vínculo ya activo
    const actoLegitimoEmitido = await request.post(`${API}/gobierno/actos`, {
      headers: mundo.headers,
      data: {
        tipo: "RESOLUCION",
        numero: `LEG2-${Date.now()}`,
        caracter: "GENERAL",
        asunto: "Asunto legítimo",
        simple_tramite: false,
        cargo_id: objetivoId,
        fecha: hoyCaracas(),
        lugar: "Caracas",
        fundamento_competencia: "Reglamento interno, art. 12",
        funcionario: "Funcionaria de prueba",
        titularidad: "TITULAR",
        hechos: "Hechos de prueba",
        fundamentos: "Fundamentos legales de prueba",
        decision: "Decisión de prueba",
        competencia: { accion: "APROBAR", materia: "CONTRATACIONES" },
      },
    });
    expect(actoLegitimoEmitido.status()).toBe(201);
    const actoLegitimoId = (await actoLegitimoEmitido.json()).id as string;
    await adjuntarDocumentoApi(request, mundo.headers, mundo.companyId, tipoId, "GovernmentAct", actoLegitimoId);
    const docsLegResp = await request.get(`${API}/documentos/por-recurso/GovernmentAct/${actoLegitimoId}`, { headers: mundo.headers });
    const docsLeg = await docsLegResp.json();
    const emitirLegResp = await request.post(`${API}/gobierno/actos/${actoLegitimoId}/emitir`, {
      headers: { ...legitimoHeaders, "If-Match": '"1"' },
      data: { documento_acto_id: docsLeg[0].id },
    });
    expect(es2xx(emitirLegResp.status()), await emitirLegResp.text()).toBe(true);

    // P5: Control Interno en navegador
    await page.context().clearCookies();
    await entrarEnGobierno(page, mundo.username, mundo.codigo, "/gobierno/control/separacion");
    await expect(page.getByRole("heading", { level: 1, name: "Separación técnica y funcional" })).toBeVisible();

    const regionIntegridad = page.locator('section[aria-labelledby="sec-integridad"]');
    await expect(regionIntegridad.getByText("Separación íntegra")).toBeVisible();
    await expect(regionIntegridad.getByText("Exigencia de identidad institucional:")).toBeVisible();
    await expect(regionIntegridad.getByText("Activa")).toBeVisible();

    const regionAdministradores = page.locator('section[aria-labelledby="sec-administradores"]');
    const articleAdminPuro = regionAdministradores.getByRole("article", { name: new RegExp(adminPuro.username) });
    await expect(articleAdminPuro).toBeVisible();
    await expect(articleAdminPuro.getByText("Solo técnico")).toBeVisible();
    await expect(articleAdminPuro.getByText(`Concedido por admintenant`)).toBeVisible();

    const articleDual = regionAdministradores.getByRole("article", { name: new RegExp(dual.username) });
    await expect(articleDual).toBeVisible();
    await expect(articleDual.getByText("Técnico y funcional, sin autoridad institucional", { exact: true })).toBeVisible();
    await expect(articleDual.getByText("Sin vínculo institucional vigente", { exact: true })).toBeVisible();

    await expect(regionAdministradores.getByRole("article", { name: new RegExp(legitimo.username) })).toHaveCount(0);

    const regionDenegaciones = page.locator('section[aria-labelledby="sec-denegaciones"]');
    const contenedorDenegaciones = regionDenegaciones.getByRole("region", { name: "Tabla de intentos denegados" });
    const tablaDenegaciones = contenedorDenegaciones.getByRole("table");
    await expect(tablaDenegaciones.getByText("No puede ampliar su propia autoridad.", { exact: true })).toBeVisible();
    const enlaceBitacora = tablaDenegaciones.getByRole("link", { name: /Ver en la bitácora el intento de/ });
    await expect(enlaceBitacora).toBeVisible();
    await expect(tablaDenegaciones.getByText("Su cuenta no tiene un vínculo institucional vigente en este ente", { exact: true })).toBeVisible();

    // P6: Accesibilidad
    await sinViolacionesSerias(page, "Separación inicial");
    await regionDenegaciones.scrollIntoViewIfNeeded();
    await sinViolacionesSerias(page, "Separación tras desplazarse a Intentos denegados");

    await enlaceBitacora.focus();
    await expect(enlaceBitacora).toBeFocused();

    // P7: Responsive
    for (const ancho of [390, 320]) {
      await page.setViewportSize({ width: ancho, height: 768 });
      const sinDesbordamiento = await page.evaluate(
        () => document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1,
      );
      expect(sinDesbordamiento, `Sin desbordamiento a ${ancho}px`).toBe(true);
      await expect(page.getByRole("heading", { level: 2, name: "Integridad de la separación", exact: true })).toBeVisible();
      await expect(page.getByRole("heading", { level: 2, name: "Administradores técnicos", exact: true })).toBeVisible();
      await expect(page.getByRole("heading", { level: 2, name: "Intentos denegados", exact: true })).toBeVisible();
    }
    await page.setViewportSize({ width: 390, height: 768 });
    await expect(page.locator('section[aria-labelledby="sec-denegaciones"] ul')).toBeVisible();
    await page.setViewportSize({ width: 1280, height: 768 });
  });
});
