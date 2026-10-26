/**
 * El alcance empresarial de un usuario de prueba (SPEC054 · SPEC003).
 *
 * Estas pruebas no comprueban el producto: comprueban que el **fixture** crea
 * el usuario que dice crear. Seis suites daban un rol acotado a una empresa y
 * daban por hecho que eso limitaba al usuario a esa empresa; no lo limita, y el
 * error solo se veía cuando la base tenía más de una empresa activa, es decir
 * cuando dejaba de ser un accidente afortunado.
 *
 * Por eso todo aquí se mide con **D1 y D2 activas**: es el único escenario donde
 * la diferencia entre «declaré una empresa» y «alcanzo una empresa» se nota.
 */
import { expect, test, type APIRequestContext } from "@playwright/test";

import { iniciarSesion, sesionApi } from "./helpers/sesion";
import { mundoN6 } from "./helpers/n6-mundo";
import { declararAlcance, verificadorDeEscenario, type Contexto } from "./helpers/usuario";

const API = process.env.KONTROL_E2E_API ?? "http://127.0.0.1:8000/api/v1";
const TENANT = process.env.KONTROL_E2E_TENANT ?? "DEMO";
const PASSWORD = process.env.KONTROL_E2E_PASSWORD ?? "";

const MUNDO = mundoN6();
const D1 = MUNDO.empresa_a;
const D2 = MUNDO.empresa_b;

const marca = (): string =>
  `${Date.now().toString(36)}${Math.random().toString(36).slice(2, 6)}`.toLowerCase();

async function admin(): Promise<Contexto> {
  // Prepara verificadores en D1, D2 o ambas: hace falta autoridad de todo el tenant (techo de delegación, Spec 003).
  const { token, headers } = await sesionApi("admintenant", { tenant: TENANT, empresa: D1 });
  return { token, company: D1, headers };
}

/** Las empresas que el servidor reconoce a este usuario. Es la autoridad. */
async function suyas(request: APIRequestContext, c: Contexto): Promise<string[]> {
  const r = await request.get(`${API}/organization/companies`, {
    headers: { Authorization: `Bearer ${c.token}` },
  });
  expect(r.ok(), `empresas: ${r.status()}`).toBeTruthy();
  const cuerpo = await r.json();
  return cuerpo.items.map((e: { id: string }) => e.id).sort();
}

test.beforeAll(async ({ request }) => {
  // Si la base no tiene las dos empresas activas, estas pruebas no probarían
  // nada: pasarían por no haber ambigüedad que resolver.
  const c = await admin();
  const r = await request.get(`${API}/organization/companies`, { headers: c.headers });
  expect(r.ok()).toBeTruthy();
  void r;
  expect(D1, "el mundo sembrado no trae la primera empresa").toBeTruthy();
  expect(D2, "el mundo sembrado no trae la segunda empresa").toBeTruthy();
  expect(D1).not.toBe(D2);
});

// ------------------------------------------------------------------------ U1
test("U1 · quien se declara de una empresa alcanza solo esa", async ({ request }) => {
  const a = await admin();
  const v = await verificadorDeEscenario(request, a, { usuario: `u1-${marca()}`, empresas: [D1] });
  expect(await suyas(request, v)).toEqual([D1]);
});

test("U1b · y opera sin que nadie le pregunte en cuál", async ({ request }) => {
  const a = await admin();
  const v = await verificadorDeEscenario(request, a, { usuario: `u1b-${marca()}`, empresas: [D1] });
  // Sin cabecera de empresa: con una sola alcanzable el servidor la resuelve, y
  // es justo lo que hace que la interfaz no plante la compuerta de selección.
  const r = await request.get(`${API}/maestros/terceros`, {
    headers: { Authorization: `Bearer ${v.token}` },
  });
  expect(r.status(), "sin cabecera, el servidor debería resolver la única empresa").toBe(200);
});

// ------------------------------------------------------------------------ U2
test("U2 · la empresa es la que pide el escenario, no la primera", async ({ request }) => {
  const a = await admin();
  const v = await verificadorDeEscenario(request, a, { usuario: `u2-${marca()}`, empresas: [D2] });
  expect(await suyas(request, v)).toEqual([D2]);
});

// ------------------------------------------------------------------------ U3
test("U3 · quien se declara de dos alcanza las dos", async ({ request }) => {
  const a = await admin();
  const v = await verificadorDeEscenario(request, a, { usuario: `u3-${marca()}`, empresas: [D1, D2] });
  expect(await suyas(request, v)).toEqual([D1, D2].sort());
});

// ------------------------------------------------------------------------ U4
test("U4 · sin alcance declarado se sigue alcanzando todo el tenant", async ({ request }) => {
  // El contrato del producto: sin ninguna fila en `user_scopes` se admiten todas
  // las empresas del tenant (`app/core/company_context.py:82`). Es deliberado y
  // hay una suite que lo necesita —`notifications`—, así que se comprueba aquí
  // que esta delta no lo ha cambiado por el camino.
  const a = await admin();
  const usuario = `u4-${marca()}`;
  const creado = await request.post(`${API}/users`, {
    headers: a.headers,
    data: { username: usuario, email: `${usuario}@kontrol-qa.com`, password: PASSWORD,
            must_change_password: false },
  });
  expect(creado.ok(), `alta: ${creado.status()}`).toBeTruthy();
  const { token } = await iniciarSesion(usuario, { tenant: TENANT });
  const vistas = await suyas(request, { token, company: D1, headers: {} });
  expect(vistas, "sin alcance declarado debería alcanzar las dos").toContain(D1);
  expect(vistas, "sin alcance declarado debería alcanzar las dos").toContain(D2);
});

// ----------------------------------------------------------------- contrato
test("declarar dos veces lo mismo no acumula alcance", async ({ request }) => {
  const a = await admin();
  const usuario = `idem-${marca()}`;
  await verificadorDeEscenario(request, a, { usuario, empresas: [D1] });
  expect(declararAlcance(usuario, [D1])).toEqual([D1]);
  expect(declararAlcance(usuario, [D1])).toEqual([D1]);
});

test("pedir un usuario sin decir su empresa falla al instante", async ({ request }) => {
  const a = await admin();
  await expect(
    verificadorDeEscenario(request, a, { usuario: `vacio-${marca()}`, empresas: [] }),
  ).rejects.toThrow(/falta declarar su empresa/);
  expect(() => declararAlcance(`vacio-${marca()}`, [])).toThrow(/en qué empresas opera/);
});

test("pedir un alcance que contradice el ya declarado falla, no se acumula", async ({ request }) => {
  const a = await admin();
  const usuario = `choque-${marca()}`;
  await verificadorDeEscenario(request, a, { usuario, empresas: [D1] });
  // Un fixture que pide una empresa para alguien que ya opera en otra está
  // pidiendo dos cosas incompatibles; se entera aquí y no en una pantalla.
  expect(() => declararAlcance(usuario, [D2])).toThrow();
  expect(declararAlcance(usuario, [D1])).toEqual([D1]);
});
