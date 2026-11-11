import { API, TENANT, cerrarNotificaciones, crearUsuario, es2xx } from "./helpers/gobierno";
import { activarEmpresa } from "./helpers/empresa";
import { entrarComoUsuario, expect, sesionApi, test } from "./helpers/sesion";

/**
 * Humo autenticado de solo lectura del módulo Gobierno (DOC02-T000 / HUMO-UAT-01).
 *
 * Existe para demostrar que un usuario sintético de consulta puede iniciar sesión, ver el menú
 * Gobierno y abrir por el menú las pantallas del módulo (Configuración del ente, Estructura
 * organizativa, Cargos y competencias, Ocupación de cargos, Identidad institucional, Actos administrativos, Notificaciones administrativas,
 * Matriz de autoridad, Auditoría institucional, Hallazgos y acciones correctivas, Paquetes de
 * auditoría, Segregación de funciones, Cuentas bancarias, Bancos, Programación financiera y Rubros
 * de caja) sin tropezar con los estados de
 * falta de acceso o de módulo deshabilitado. Al
 * terminar se le retira su rol en un
 * `finally` para dejarlo sin permisos.
 *
 * No crea ni modifica datos de negocio: únicamente usa las APIs de organización y de usuarios.
 */

const CAPACIDADES = [
  "organization:view",
  "gobierno_ente:view",
  "gobierno_estructura:view",
  "gobierno_cargos:view",
  "gobierno_ocupacion:view",
  "gobierno_identidad:view",
  "gobierno_comisiones:view",
  "gobierno_actos:view",
  "gobierno_notificaciones:view",
  "gobierno_autoridad:view",
  "gobierno_auditoria:view",
  "gobierno_hallazgos:view",
  "gobierno_paquetes:view",
  "gobierno_sod:view",
  "gobierno_cierre:view",
  "gobierno_cuentas:view",
  "gobierno_caja:view",
  "gobierno_expedientes:view",
  "documentos:view",
];

const PANTALLAS: ReadonlyArray<readonly [href: string, titulo: string]> = [
  ["/gobierno/ente", "Configuración del ente"],
  ["/gobierno/estructura", "Estructura organizativa"],
  ["/gobierno/cargos", "Cargos y competencias"],
  ["/gobierno/ocupacion", "Ocupación de cargos"],
  ["/gobierno/identidad", "Identidad institucional"],
  ["/gobierno/actos", "Actos administrativos"],
  ["/gobierno/notificaciones", "Notificaciones administrativas"],
  ["/gobierno/autoridad", "Matriz de autoridad"],
  ["/gobierno/auditoria", "Auditoría institucional"],
  ["/gobierno/bitacora", "Bitácora institucional"],
  ["/gobierno/control/separacion", "Separación técnica y funcional"],
  ["/gobierno/hallazgos", "Hallazgos y acciones correctivas"],
  ["/gobierno/paquetes", "Paquetes de auditoría"],
  ["/gobierno/sod", "Segregación de funciones"],
  ["/gobierno/cierres", "Controles de cierre"],
  ["/gobierno/contrataciones/comisiones", "Comisiones de contrataciones"],
  ["/gobierno/contrataciones/expedientes", "Expedientes de contratación"],
  ["/gobierno/tesoreria/cuentas", "Cuentas bancarias"],
  ["/gobierno/tesoreria/bancos", "Bancos"],
  ["/gobierno/tesoreria/programacion", "Programación financiera"],
  ["/gobierno/tesoreria/rubros", "Rubros de caja"],
];

interface EmpresaApi {
  id: string;
  code: string;
}

interface EmpresasApi {
  items: EmpresaApi[];
}

interface RolApi {
  id: string;
  code: string;
  name: string;
  company_id: string | null;
}

interface UsuarioApi {
  id: string;
  username: string;
  roles: RolApi[];
}

test.describe("Humo UAT · Gobierno (HUMO-UAT-01)", () => {
  test("HUMO-UAT-01 · el usuario de consulta abre las catorce pantallas por el menú y se le retira el rol", async ({
    page,
    request,
  }) => {
    test.setTimeout(120_000);

    const admin = await sesionApi("admintenant", { tenant: TENANT });

    const respEmpresas = await request.get(`${API}/organization/companies`, {
      headers: admin.headers,
    });
    expect(respEmpresas.status(), "GET /organization/companies debe responder 200").toBe(200);
    const empresas = (await respEmpresas.json()) as EmpresasApi;
    const d1 = empresas.items.find((empresa) => empresa.code === "D1");
    expect(d1, "la siembra debe haber creado la empresa de código D1").toBeTruthy();

    const usuario = await crearUsuario(request, admin.headers, CAPACIDADES, d1!.id);

    try {
      await entrarComoUsuario(page, usuario.username, { tenant: TENANT, ruta: "/" });
      await activarEmpresa(page, "D1");

      for (const [href, titulo] of PANTALLAS) {
        await cerrarNotificaciones(page);
        await page.locator(`nav a[href="${href}"]`).first().click();
        await page.waitForURL((u) => u.pathname === href);
        await expect(
          page.getByRole("heading", { level: 1, name: titulo, exact: true }),
        ).toBeVisible();
        await expect(page.getByText("Sin acceso", { exact: true })).toHaveCount(0);
        await expect(
          page.getByText("El módulo de Gobierno no está habilitado", { exact: true }),
        ).toHaveCount(0);
      }
    } finally {
      const respUsuarios = await request.get(`${API}/users`, { headers: admin.headers });
      expect(respUsuarios.status(), "GET /users debe responder 200").toBe(200);
      const usuarios = (await respUsuarios.json()) as UsuarioApi[];
      const encontrado = usuarios.find((item) => item.username === usuario.username);
      expect(
        encontrado,
        `el usuario sintético ${usuario.username} debe existir para retirarle el rol`,
      ).toBeTruthy();

      for (const rol of encontrado!.roles) {
        const respBorrado = await request.delete(
          `${API}/users/${encontrado!.id}/roles/${rol.id}`,
          { headers: admin.headers },
        );
        expect(
          es2xx(respBorrado.status()),
          `DELETE /users/${encontrado!.id}/roles/${rol.id} debe responder 2xx`,
        ).toBe(true);
      }
    }
  });
});
