/**
 * El verificador de escenario: un usuario distinto del preparador
 * (`R-D0-12-5`), con **el alcance empresarial que su escenario declara**.
 *
 * Seis suites tenían esta misma función copiada literalmente, y las seis
 * cometían el mismo error: creaban el usuario, le daban un rol acotado a la
 * empresa del escenario —`company_id: c.company`— y daban por hecho que eso lo
 * limitaba a esa empresa. No lo limita. La autoridad de acceso del producto es
 * `user_scopes`, no `user_roles`, y lo dice el propio producto
 * (`app/core/company_context.py:62`): un rol con empresa es el alcance del
 * **permiso**, no la lista de empresas en las que se opera.
 *
 * El efecto era invisible mientras la base del E2E tuvo una sola empresa. Con
 * dos activas, el usuario alcanzaba las dos, la interfaz le pedía elegir —con
 * razón— y la prueba se quedaba en la compuerta sin llegar a su pantalla.
 *
 * `user_scopes` no tiene API ni interfaz: solo se escribe desde `qa/`. Así que
 * el alcance se declara invocando la orden canónica contra la misma base del
 * E2E, que es el patrón que ya usa `helpers/planificador.ts` para el
 * planificador. No hay una segunda manera de conceder acceso a una empresa.
 *
 * Este módulo no contiene pruebas; Playwright solo recoge `*.spec.ts`.
 */
import { resolve } from "node:path";

import { expect, type APIRequestContext } from "@playwright/test";

import { ejecutarPython } from "./python";
import { iniciarSesion } from "./sesion";

const BACKEND = resolve(process.cwd(), "..", "backend");
const API = process.env.KONTROL_E2E_API ?? "http://127.0.0.1:8000/api/v1";
const TENANT = process.env.KONTROL_E2E_TENANT ?? "DEMO";
const PASSWORD = process.env.KONTROL_E2E_PASSWORD ?? "";

export interface Contexto {
  token: string;
  company: string;
  headers: Record<string, string>;
}

/**
 * Deja escrito en qué empresas opera `usuario`. Devuelve su alcance real.
 *
 * Falla si no se pide ninguna: un usuario sin alcance declarado alcanza todas
 * las empresas del tenant, y eso es una decisión —legítima, la usa
 * `notifications.spec.ts`— que debe tomarse a la vista, no por omisión.
 */
export function declararAlcance(usuario: string, empresas: string[], tenant = TENANT): string[] {
  if (empresas.length === 0) {
    throw new Error(
      `alcance de ${usuario}: hay que decir en qué empresas opera. Sin alcance declarado ` +
      "alcanza todas las del tenant, y entonces la prueba depende de cuántas haya sembradas",
    );
  }
  const url = process.env.KONTROL_E2E_DB_URL;
  if (!url) {
    throw new Error(
      "KONTROL_E2E_DB_URL es obligatoria para declarar alcance: `user_scopes` no tiene API " +
      "ni interfaz, así que se escribe con la orden canónica contra la base del E2E",
    );
  }
  const salida = ejecutarPython(
    [resolve(BACKEND, "..", "..", "qa", "alcance_de_usuario.py"), tenant, usuario, ...empresas],
    { cwd: BACKEND, env: { ...process.env, KONTROL_DB_URL: url, PYTHONPATH: BACKEND },
      encoding: "utf8", timeout: 60_000 },
  );
  return salida.trim().split(/\s+/).filter(Boolean);
}

/**
 * Crea el verificador del escenario y devuelve su contexto.
 *
 * `empresas` es obligatorio y es el punto de todo esto: el usuario que sale de
 * aquí opera exactamente donde el escenario dice, y no donde la base del E2E
 * haya quedado.
 */
export async function verificadorDeEscenario(
  request: APIRequestContext,
  admin: { headers: Record<string, string> },
  opciones: { usuario: string; empresas: string[] },
): Promise<Contexto> {
  const { usuario, empresas } = opciones;
  if (empresas.length === 0) {
    throw new Error(`verificador ${usuario}: falta declarar su empresa`);
  }

  const roles = await request.get(`${API}/roles`, { headers: admin.headers });
  expect(roles.ok(), `roles: ${roles.status()}`).toBeTruthy();
  const items = (await roles.json()).items as Array<{ id: string; code?: string; name?: string }>;
  const rol = items.find((r) => (r.code ?? r.name ?? "").toUpperCase().includes("ADMIN")) ?? items[0];

  const creado = await request.post(`${API}/users`, {
    headers: admin.headers,
    data: { username: usuario, email: `${usuario}@kontrol-qa.com`, password: PASSWORD,
            must_change_password: false },
  });
  expect(creado.ok(), `alta de ${usuario}: ${creado.status()} ${await creado.text()}`).toBeTruthy();
  const id = (await creado.json()).id as string;

  // El rol lleva la empresa cuando hay una sola: es el alcance del permiso, y
  // con varias no hay una a la que atarlo.
  const asignado = await request.post(`${API}/users/${id}/roles`, {
    headers: admin.headers,
    data: { role_id: rol.id, company_id: empresas.length === 1 ? empresas[0] : null },
  });
  expect(asignado.ok(), `rol de ${usuario}: ${asignado.status()}`).toBeTruthy();

  // Y el acceso, que es lo que decide qué empresas ve.
  const alcance = declararAlcance(usuario, empresas);
  expect([...alcance].sort(), `alcance de ${usuario}`).toEqual([...new Set(empresas)].sort());

  const token = (await iniciarSesion(usuario, { tenant: TENANT })).token;
  return {
    token,
    company: empresas[0],
    headers: { Authorization: `Bearer ${token}`, "X-Kontrol-Company": empresas[0] },
  };
}
