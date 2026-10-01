/**
 * E2E de los maestros financieros — Spec 013.
 *
 * Frontend real → API real → backend real → PostgreSQL real.
 *
 * El caso obligatorio es el mismo que la 038 dejó sellado y esta Spec hereda:
 * **falta de tasa no es tasa uno**. Lo demás protege lo que se descubrió al
 * mirar lo que ya existía: que el par no estaba escrito en ninguna parte, que
 * dos monedas con el mismo código convivían, y que la resolución derivaba
 * cotizaciones —invertía y triangulaba— sin permiso y sin decirlo.
 */
import { expect, test, type APIRequestContext, type Page } from "@playwright/test";

import { ctx, get, hoy, marca, post, postCrudo, type Ctx } from "./helpers/ventas";

const TENANT = process.env.KONTROL_E2E_TENANT ?? "DEMO";
const USER = process.env.KONTROL_E2E_USER ?? "admin";
const PASSWORD = process.env.KONTROL_E2E_PASSWORD ?? "";

/** Una moneda que no choca con la de otra prueba. */
const codigoMoneda = (m: string): string => `X${m.slice(-3)}`;

async function moneda(request: APIRequestContext, c: Ctx, code: string) {
  const ya = await get(request, c, "/treasury/currencies");
  const encontrada = (ya.items as Array<{ id: string; code: string }>).find((x) => x.code === code);
  if (encontrada) return encontrada;
  return post(request, c, "/treasury/currencies", { code, name: code });
}

async function funcional(request: APIRequestContext, c: Ctx): Promise<string> {
  const empresas = await get(request, c, "/organization/companies");
  const lista = empresas.items as Array<{
    id: string;
    functional_currency: string;
  }>;
  const propia = lista.find((x) => x.id === c.company) ?? lista[0];
  return propia.functional_currency;
}

async function fuente(request: APIRequestContext, c: Ctx, m: string, prioridad = 100) {
  return post(request, c, "/treasury/rate-sources", {
    code: `F${m.slice(-5)}`,
    name: `Fuente ${m}`,
    source_type: "OFFICIAL",
    authority_reference: "Pendiente de validación legal (D0-07)",
    priority: prioridad,
  });
}

/**
 * Una política de resolución permisiva y vigente.
 *
 * Activar sustituye a la anterior, así que todas las pruebas que la necesitan
 * crean una equivalente: una restrictiva dejaría a las demás sin poder operar.
 * Lo restrictivo se prueba en el backend, no pisando el estado compartido.
 */
async function politica(request: APIRequestContext, c: Ctx, m: string,
                        opciones: Record<string, unknown> = {}) {
  const p = await post(request, c, "/treasury/rate-policies", {
    policy_code: `RES-${m}`,
    effective_from: "2020-01-01",
    allow_inversion: false,
    allow_triangulation: false,
    require_rate_approval: false,
    ...opciones,
  });
  expect(p.status, "la política nació activa sin que nadie la aprobara").toBe("DRAFT");
  return post(request, c, `/treasury/rate-policies/${p.id}/activate`, {});
}

async function registrar(request: APIRequestContext, c: Ctx, datos: Record<string, unknown>) {
  return post(request, c, "/treasury/exchange-rates/observations", datos);
}

async function resolver(request: APIRequestContext, c: Ctx, base: string, quote: string,
                        cuando?: string) {
  const q = cuando ? `&effective_at=${encodeURIComponent(cuando)}` : "";
  return request.get(
    `${process.env.KONTROL_E2E_API ?? "http://127.0.0.1:8000/api/v1"}` +
      `/treasury/exchange-rates/resolve?base_currency=${base}&quote_currency=${quote}${q}`,
    { headers: c.headers },
  );
}

async function uiLogin(page: Page): Promise<void> {
  await page.goto("/login");
  await page.getByLabel(/Empresa \(código\)/).fill(TENANT);
  await page.getByLabel(/Usuario/).fill(USER);
  await page.getByLabel(/Contraseña/).fill(PASSWORD);
  await page.getByRole("button", { name: "Iniciar sesión" }).click();
  await expect(page).toHaveURL(/\/$/, { timeout: 20_000 });
}

async function irA(page: Page, ruta: string): Promise<void> {
  await page.locator(`nav a[href="${ruta}"]`).first().click();
  await page.waitForURL((u) => u.pathname === ruta, { timeout: 20_000 });
}

/**
 * En serie a propósito.
 *
 * La política de resolución es **una por empresa**, y el mundo de e2e tiene una
 * sola. Dos pruebas en paralelo —una que necesita la inversión denegada y otra
 * que la necesita permitida— se pisarían la política y el resultado dependería
 * de cuál llegó última. Una prueba que gana o pierde por la carrera no prueba
 * nada; en serie, cada una fija su política justo antes de mirar.
 */
test.describe.configure({ mode: "serial" });

test.describe("Spec 013 — maestros financieros", () => {
  test("P0 · un par sin tasa no se resuelve, y no vale uno", async ({ request }) => {
    const c = await ctx(request);
    const m = marca();
    await politica(request, c, m);
    const a = await moneda(request, c, codigoMoneda(m));
    const b = await moneda(request, c, `Y${m.slice(-3)}`);

    const r = await resolver(request, c, a.code, b.code);
    expect(r.status(), "resolvió un par que nadie ha cotizado").toBe(409);
    expect((await r.json()).code).toBe("MISSING_RATE");
  });

  test("la misma moneda es identidad y no inventa una fila de mercado", async ({ request }) => {
    const c = await ctx(request);
    const a = await moneda(request, c, codigoMoneda(marca()));
    const r = await resolver(request, c, a.code, a.code);
    expect(r.ok(), await r.text()).toBeTruthy();
    const cuerpo = await r.json();
    expect(Number(cuerpo.rate)).toBe(1);
    expect(cuerpo.identity).toBe(true);
    expect(cuerpo.observation_id, "creó una observación falsa para la identidad").toBeNull();
  });

  test("la tasa manual se registra con su par y se resuelve exacta", async ({ request }) => {
    const c = await ctx(request);
    const m = marca();
    await politica(request, c, m);
    const ved = await funcional(request, c);
    await moneda(request, c, ved);
    const div = await moneda(request, c, codigoMoneda(m));
    const f = await fuente(request, c, m);

    await registrar(request, c, {
      base_currency: div.code, quote_currency: ved, rate: "36.123456",
      effective_at: new Date().toISOString(), source_id: f.id,
    });

    const r = await resolver(request, c, div.code, ved);
    const cuerpo = await r.json();
    expect(cuerpo.rate).toBe("36.123456");
    expect(cuerpo.meaning).toBe(`1 ${div.code} = 36.123456 ${ved}`);
    expect(cuerpo.source_code).toBe(f.code);
    expect(cuerpo.derived, "derivó una tasa que estaba registrada directa").toBeNull();
  });

  test("una tasa no positiva se rechaza", async ({ request }) => {
    const c = await ctx(request);
    const m = marca();
    const ved = await funcional(request, c);
    await moneda(request, c, ved);
    const div = await moneda(request, c, codigoMoneda(m));
    for (const valor of ["0", "-1"]) {
      const r = await postCrudo(request, c, "/treasury/exchange-rates/observations", {
        base_currency: div.code, quote_currency: ved, rate: valor,
        effective_at: new Date().toISOString(),
      });
      expect([409, 422], `aceptó la tasa ${valor}`).toContain(r.status());
    }
  });

  test("P0 · sin política no se invierte el par", async ({ request }) => {
    const c = await ctx(request);
    const m = marca();
    await politica(request, c, m, { allow_inversion: false });
    const ved = await funcional(request, c);
    await moneda(request, c, ved);
    const div = await moneda(request, c, codigoMoneda(m));
    const f = await fuente(request, c, m);
    await registrar(request, c, {
      base_currency: div.code, quote_currency: ved, rate: "100.00",
      effective_at: new Date().toISOString(), source_id: f.id,
    });

    const r = await resolver(request, c, ved, div.code);
    expect(r.status(), "invirtió la cotización sin permiso").toBe(409);
    expect((await r.json()).code).toBe("INVERSION_NOT_ALLOWED");
  });

  test("con política se invierte y la respuesta dice que es derivada", async ({ request }) => {
    const c = await ctx(request);
    const m = marca();
    await politica(request, c, m, { allow_inversion: true });
    const ved = await funcional(request, c);
    await moneda(request, c, ved);
    const div = await moneda(request, c, codigoMoneda(m));
    const f = await fuente(request, c, m);
    const obs = await registrar(request, c, {
      base_currency: div.code, quote_currency: ved, rate: "100.00",
      effective_at: new Date().toISOString(), source_id: f.id,
    });

    const cuerpo = await (await resolver(request, c, ved, div.code)).json();
    expect(Number(cuerpo.rate)).toBeCloseTo(0.01, 6);
    expect(cuerpo.derived, "derivó sin dejar constancia").toBe("INVERSE");
    expect(cuerpo.derived_from).toContain(obs.id);
  });

  test("una tasa futura no valora una fecha anterior", async ({ request }) => {
    const c = await ctx(request);
    const m = marca();
    await politica(request, c, m);
    const ved = await funcional(request, c);
    await moneda(request, c, ved);
    const div = await moneda(request, c, codigoMoneda(m));
    const f = await fuente(request, c, m);
    const ayer = new Date(Date.now() - 86_400_000).toISOString();
    const manana = new Date(Date.now() + 86_400_000).toISOString();
    await registrar(request, c, {
      base_currency: div.code, quote_currency: ved, rate: "100.00",
      effective_at: ayer, source_id: f.id,
    });
    await registrar(request, c, {
      base_currency: div.code, quote_currency: ved, rate: "999.00",
      effective_at: manana, source_id: f.id,
    });

    const cuerpo = await (await resolver(request, c, div.code, ved, ayer)).json();
    expect(cuerpo.rate).toBe("100.000000");
  });

  test("corregir una tasa no reescribe la anterior", async ({ request }) => {
    const c = await ctx(request);
    const m = marca();
    await politica(request, c, m);
    const ved = await funcional(request, c);
    await moneda(request, c, ved);
    const div = await moneda(request, c, codigoMoneda(m));
    const f = await fuente(request, c, m);
    const obs = await registrar(request, c, {
      base_currency: div.code, quote_currency: ved, rate: "100.00",
      effective_at: new Date().toISOString(), source_id: f.id,
    });

    const nueva = await post(request, c,
      `/treasury/exchange-rates/observations/${obs.id}/correct`,
      { rate: "120.00", reason: "La fuente publicó una corrección" });
    expect(nueva.supersedes_id).toBe(obs.id);
    expect(nueva.version).toBe(obs.version + 1);

    const historico = await get(request, c,
      `/treasury/exchange-rates/observations?source_id=${f.id}&page=1&page_size=100`);
    const anterior = (historico.items as Array<{ id: string; rate: string; status: string }>)
      .find((x) => x.id === obs.id);
    expect(anterior, "la corrección borró la original").toBeTruthy();
    expect(anterior!.rate, "la corrección reescribió el importe histórico").toBe("100.000000");
    expect(anterior!.status).toBe("SUPERSEDED");

    expect((await (await resolver(request, c, div.code, ved)).json()).rate).toBe("120.000000");
  });

  test("una fuente desactivada deja de resolver y conserva su historia", async ({ request }) => {
    const c = await ctx(request);
    const m = marca();
    await politica(request, c, m);
    const ved = await funcional(request, c);
    await moneda(request, c, ved);
    const div = await moneda(request, c, codigoMoneda(m));
    const f = await fuente(request, c, m);
    const obs = await registrar(request, c, {
      base_currency: div.code, quote_currency: ved, rate: "100.00",
      effective_at: new Date().toISOString(), source_id: f.id,
    });
    await post(request, c, `/treasury/rate-sources/${f.id}/status`, { status: "DISABLED" });

    expect((await resolver(request, c, div.code, ved)).status()).toBe(409);
    const historico = await get(request, c,
      `/treasury/exchange-rates/observations?source_id=${f.id}&page=1&page_size=100`);
    expect((historico.items as Array<{ id: string }>).some((x) => x.id === obs.id),
           "desactivar la fuente borró su historia").toBe(true);
  });

  test("importar crea las tasas, reimportar no duplica y lo inválido se detalla",
       async ({ request }) => {
    const c = await ctx(request);
    const m = marca();
    await politica(request, c, m);
    const ved = await funcional(request, c);
    await moneda(request, c, ved);
    const div = await moneda(request, c, codigoMoneda(m));
    const f = await fuente(request, c, m);
    const contenido =
      "base_currency,quote_currency,rate,effective_at\n" +
      `${div.code},${ved},100.00,${hoy()}\n` +
      `${div.code},${ved},0,${hoy()}\n` +
      `NOEXISTE,${ved},10,${hoy()}\n`;

    const r = await post(request, c, "/treasury/exchange-rates/import",
                         { source_id: f.id, content: contenido, filename: `t-${m}.csv` });
    expect(r.imported).toBe(1);
    expect(r.rejected, "alguna fila inválida desapareció sin decirlo").toBe(2);
    expect(r.errors.map((e: { row: number }) => e.row).sort()).toEqual([3, 4]);

    const otra = await postCrudo(request, c, "/treasury/exchange-rates/import",
                                 { source_id: f.id, content: contenido, filename: `t-${m}.csv` });
    expect(otra.status(), "reimportar el mismo fichero duplicó tasas").toBe(409);
    expect((await otra.json()).code).toBe("IMPORT_DUPLICATE");
  });

  test("P0 · la tesorería se bloquea sin tasa y funciona en cuanto se registra",
       async ({ request }) => {
    const c = await ctx(request);
    const m = marca();
    await politica(request, c, m);
    const ved = await funcional(request, c);
    await moneda(request, c, ved);
    const div = await moneda(request, c, codigoMoneda(m));

    // Política cambiaria de la 038, que es la que autoriza convertir.
    const fx = await post(request, c, "/treasury/fx-policies", {
      policy_code: `FX-${m}`, functional_currency: ved, effective_from: "2020-01-01",
      allow_cross_currency: true, allow_refund: true,
      authority_reference: "Pendiente de validación legal (D0-07)",
    });
    await post(request, c, `/treasury/fx-policies/${fx.id}/activate`, {});

    const bancos = await get(request, c, "/treasury/banks");
    const banco = (bancos.items as Array<{ id: string }>)[0]
      ?? (await post(request, c, "/treasury/banks", { code: `B-${m}`, name: `Banco ${m}` }));
    const origen = await post(request, c, "/treasury/accounts", {
      bank_id: banco.id, code: `CD-${m}`, name: `Cuenta ${div.code}`, currency: div.code,
    });
    const destino = await post(request, c, "/treasury/accounts", {
      bank_id: banco.id, code: `CV-${m}`, name: `Cuenta ${ved}`, currency: ved,
    });
    await post(request, c, "/treasury/bank-transactions", {
      account_id: origen.id, direction: "IN", amount: "100.00", currency: div.code,
      txn_date: hoy(), reference: "Fondeo",
    });

    const sinTasa = await postCrudo(request, c, "/treasury/fx-conversions", {
      source_account_id: origen.id, target_account_id: destino.id, source_amount: "10.00",
    });
    expect(sinTasa.status(), "convirtió sin tasa registrada").toBe(409);
    expect((await sinTasa.json()).code).toBe("RATE_NOT_AVAILABLE");

    const f = await fuente(request, c, m);
    await registrar(request, c, {
      base_currency: div.code, quote_currency: ved, rate: "40.00",
      effective_at: new Date().toISOString(), source_id: f.id,
    });

    const conv = await post(request, c, "/treasury/fx-conversions", {
      source_account_id: origen.id, target_account_id: destino.id, source_amount: "10.00",
    });
    expect(Number(conv.target_amount)).toBe(400);
    expect(conv.rate_origin).toBe("REGISTERED");
    expect(conv.rate_source, "la instantánea no dice de qué fuente salió").toBe(f.code);

    // Y corregir la tasa después no revalúa la operación ya hecha.
    const historico = await get(request, c,
      `/treasury/exchange-rates/observations?source_id=${f.id}&page=1&page_size=100`);
    const usada = (historico.items as Array<{ id: string; status: string }>)
      .find((x) => x.status === "ACTIVE");
    await post(request, c, `/treasury/exchange-rates/observations/${usada!.id}/correct`,
               { rate: "80.00", reason: "Corrección posterior" });
    const conversiones = await get(request, c, "/treasury/fx-conversions");
    const misma = (conversiones.items as Array<{ id: string; target_amount: string }>)
      .find((x) => x.id === conv.id);
    expect(Number(misma!.target_amount), "una corrección posterior revaluó lo ya hecho").toBe(400);
  });

  test("la interfaz registra una tasa, dice lo que significa y el dominio lo confirma",
       async ({ page, request }) => {
    const c = await ctx(request);
    const m = marca();
    await politica(request, c, m);
    const ved = await funcional(request, c);
    await moneda(request, c, ved);
    const div = await moneda(request, c, codigoMoneda(m));

    await uiLogin(page);
    await irA(page, "/tesoreria/tasas");
    await expect(page.getByRole("heading", { name: "Tasas de cambio", level: 1 })).toBeVisible({
      timeout: 20_000,
    });

    await page.getByLabel("Moneda base").selectOption(div.code);
    await page.getByLabel("Moneda cotizada").selectOption(ved);
    await page.getByLabel(/^Tasa\s*\*/).fill("55.500000");
    await expect(page.getByText(`Significa: 1 ${div.code} = 55.500000 ${ved}.`)).toBeVisible();
    await page.getByRole("button", { name: "Registrar" }).click();

    // Se comprueba con la propia consulta de la pantalla y no buscando la fila
    // en el histórico: esa tabla crece con cada prueba y la fila puede caer
    // fuera de la primera página, que haría fallar la prueba por el motivo
    // equivocado.
    await page.getByLabel("Convertir de").selectOption(div.code);
    await page.getByLabel("Convertir a").selectOption(ved);
    await page.getByRole("button", { name: "Resolver" }).click();
    await expect(page.getByText(`1 ${div.code} = 55.500000 ${ved}`).first())
      .toBeVisible({ timeout: 20_000 });

    const cuerpo = await (await resolver(request, c, div.code, ved)).json();
    expect(cuerpo.rate).toBe("55.500000");
    expect(cuerpo.meaning).toBe(`1 ${div.code} = 55.500000 ${ved}`);
  });

  test("la interfaz de fuentes crea, desactiva y muestra la política", async ({ page, request }) => {
    const c = await ctx(request);
    const m = marca();
    await politica(request, c, m);

    await uiLogin(page);
    await irA(page, "/tesoreria/fuentes");
    await expect(page.getByRole("heading", { name: "Fuentes de tasa", level: 1 })).toBeVisible({
      timeout: 20_000,
    });

    const codigo = `UI${m.slice(-4)}`;
    await page.getByLabel(/^Código\s*\*/).first().fill(codigo);
    await page.getByLabel(/^Nombre\s*\*/).fill(`Fuente ${m}`);
    await page.getByRole("button", { name: "Crear fuente" }).click();

    const fila = page.getByRole("row").filter({ hasText: codigo }).first();
    await expect(fila).toBeVisible({ timeout: 20_000 });
    await expect(fila).toContainText("Activa");
    await fila.getByRole("button", { name: "Desactivar" }).click();
    await expect(fila).toContainText("Desactivada", { timeout: 20_000 });

    // Y el dominio dice lo mismo.
    const fuentes = await get(request, c, "/treasury/rate-sources");
    const suya = (fuentes.items as Array<{ code: string; status: string }>)
      .find((x) => x.code === codigo);
    expect(suya?.status).toBe("DISABLED");
  });
});
