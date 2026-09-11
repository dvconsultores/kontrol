import { expect, test, type APIRequestContext, type Page } from "@playwright/test";

import {
  creditoAFavor,
  ctx,
  get,
  hoy,
  marca,
  post,
  postCrudo,
  type Ctx,
} from "./helpers/ventas";

const TENANT = process.env.KONTROL_E2E_TENANT ?? "DEMO";
/**
 * Un código de moneda que no choca con el de otra prueba.
 *
 * Se toma de la **cola** de la marca, que es la parte aleatoria: la cabeza es
 * `Date.now()` en base 36 y sus primeros caracteres son idénticos durante años,
 * de modo que `marca().slice(0, 2)` daba la misma moneda a todo el mundo.
 */
const codigoMoneda = (prefijo: string, m: string): string => `${prefijo}${m.slice(-3)}`;
const USER = process.env.KONTROL_E2E_USER ?? "admin";
const PASSWORD = process.env.KONTROL_E2E_PASSWORD ?? "";

/**
 * Una política permisiva y vigente.
 *
 * Todas las pruebas de esta suite crean una igual a propósito: activar
 * sustituye a la anterior, y una política restrictiva dejaría a las demás sin
 * poder operar. Lo restrictivo se prueba donde no estorba —en el backend—, no
 * pisando el estado compartido de los tres navegadores.
 */
async function politica(request: APIRequestContext, c: Ctx, m: string) {
  const p = await post(request, c, "/treasury/fx-policies", {
    policy_code: `FX-${m}`,
    functional_currency: "VED",
    effective_from: "2020-01-01",
    rate_source: "BCV",
    allow_cross_currency: true,
    allow_manual_rate: false,
    allow_refund: true,
    authority_reference: "Pendiente de validación legal (D0-07)",
  });
  expect(p.status, "la política nació activa sin que nadie la aprobara").toBe("DRAFT");
  return post(request, c, `/treasury/fx-policies/${p.id}/activate`, {});
}

async function cuenta(request: APIRequestContext, c: Ctx, m: string, moneda: string) {
  const bancos = await get(request, c, "/treasury/banks");
  const banco = (bancos.items as Array<{ id: string }>)[0]
    ?? (await post(request, c, "/treasury/banks", { code: `B-${m}`, name: `Banco ${m}` }));
  return post(request, c, "/treasury/accounts", {
    bank_id: banco.id, code: `CT-${m}-${moneda}`, name: `Cuenta ${moneda} ${m}`,
    currency: moneda,
  });
}

/** Mete fondos por la vía normal: un movimiento bancario de entrada. */
async function fondear(request: APIRequestContext, c: Ctx, cuentaId: string,
                       importe: number, moneda = "VED") {
  return post(request, c, "/treasury/bank-transactions", {
    account_id: cuentaId, direction: "IN", amount: importe, currency: moneda,
    txn_date: hoy(), reference: "Fondeo de prueba",
  });
}

async function saldo(request: APIRequestContext, c: Ctx, cuentaId: string): Promise<number> {
  return Number((await get(request, c, `/treasury/accounts/${cuentaId}/balance`)).balance);
}

async function irA(page: Page, ruta: string): Promise<void> {
  // `page.goto` justo después del login compite con la redirección del shell y
  // acaba en el inicio. Se navega como navega una persona: por el menú.
  await page.locator(`nav a[href="${ruta}"]`).first().click();
  await page.waitForURL((u) => u.pathname === ruta, { timeout: 20_000 });
}

async function uiLogin(page: Page): Promise<void> {
  await page.goto("/login");
  await page.getByLabel(/Empresa \(código\)/).fill(TENANT);
  await page.getByLabel(/Usuario/).fill(USER);
  await page.getByLabel(/Contraseña/).fill(PASSWORD);
  await page.getByRole("button", { name: "Iniciar sesión" }).click();
  await expect(page).toHaveURL(/\/$/, { timeout: 20_000 });
}

test.describe("Spec 038 — tesorería", () => {
  test("P0 · sin tasa registrada la conversión se niega", async ({ request }) => {
    const c = await ctx(request);
    const m = marca();
    await politica(request, c, m);
    // Una moneda recién creada que nadie ha cotizado. El caso hostil exacto.
    const codigo = codigoMoneda("Q", m);
    await post(request, c, "/treasury/currencies", { code: codigo, name: `Moneda ${m}` });
    const origen = await cuenta(request, c, m, codigo);
    const destino = await cuenta(request, c, m, "VED");
    await fondear(request, c, origen.id, 100);

    const r = await postCrudo(request, c, "/treasury/fx-conversions", {
      source_account_id: origen.id, target_account_id: destino.id, source_amount: "10.00",
    });
    expect(r.status(), "convirtió sin tasa: se inventó un cambio").toBe(409);
    expect((await r.json()).code).toBe("RATE_NOT_AVAILABLE");

    // Y no se movió nada en ninguna de las dos cuentas.
    expect(await saldo(request, c, origen.id)).toBe(100);
    expect(await saldo(request, c, destino.id)).toBe(0);
  });

  test("la conversión mueve las dos cuentas y guarda de dónde salió la tasa", async ({ request }) => {
    const c = await ctx(request);
    const m = marca();
    const p = await politica(request, c, m);
    const codigo = codigoMoneda("R", m);
    const moneda = await post(request, c, "/treasury/currencies", { code: codigo, name: `Moneda ${m}` });
    await post(request, c, "/treasury/exchange-rates", {
      currency_id: moneda.id, rate_date: hoy(), rate: "40.00", source: "BCV",
    });
    const origen = await cuenta(request, c, m, codigo);
    const destino = await cuenta(request, c, m, "VED");
    await fondear(request, c, origen.id, 100);

    const conv = await post(request, c, "/treasury/fx-conversions", {
      source_account_id: origen.id, target_account_id: destino.id, source_amount: "10.00",
    });
    expect(Number(conv.target_amount)).toBe(400);
    expect(conv.rate_origin, "no dice de dónde salió la tasa").toBe("REGISTERED");
    expect(conv.rate_source).toBe("BCV");
    expect(conv.policy_version).toBe(p.version);

    expect(await saldo(request, c, origen.id)).toBe(90);
    expect(await saldo(request, c, destino.id)).toBe(400);
  });

  test("P0 · el crédito reservado para devolver no se imputa además a una factura", async ({ request }) => {
    const c = await ctx(request);
    const m = marca();
    await politica(request, c, m);
    const { cliente, nota } = await creditoAFavor(request, c, m);
    const banco = await cuenta(request, c, m, "VED");
    await fondear(request, c, banco.id, 500);

    await post(request, c, "/treasury/refunds", {
      credit_note_id: nota.id, amount: "60.00", reason: "El cliente pidió su dinero",
      account_id: banco.id,
    });

    // Lo imputable bajó: son el mismo dinero.
    const creditos = await get(request, c, `/sales/cxc/clientes/${cliente}/creditos`);
    const fila = (creditos.items as Array<{ id: string; available: string; refund_reserved: string }>)
      .find((x) => x.id === nota.id);
    expect(Number(fila?.available), "ofrece crédito ya reservado").toBe(40);
    expect(Number(fila?.refund_reserved)).toBe(60);

    // Y un segundo reembolso por lo reservado tampoco cabe.
    const otro = await postCrudo(request, c, "/treasury/refunds", {
      credit_note_id: nota.id, amount: "60.00", reason: "Otra vez lo mismo",
      account_id: banco.id,
    });
    expect(otro.status(), "reservó dos veces el mismo dinero").toBe(409);
  });

  test("denegar libera la reserva y el crédito vuelve", async ({ request }) => {
    const c = await ctx(request);
    const m = marca();
    await politica(request, c, m);
    const { cliente, nota } = await creditoAFavor(request, c, m);
    const r = await post(request, c, "/treasury/refunds", {
      credit_note_id: nota.id, amount: "60.00", reason: "Solicitud del cliente",
    });
    await post(request, c, `/treasury/refunds/${r.id}/decide`, {
      approved: false, reason: "No procede",
    });

    const creditos = await get(request, c, `/sales/cxc/clientes/${cliente}/creditos`);
    const fila = (creditos.items as Array<{ id: string; available: string }>)
      .find((x) => x.id === nota.id);
    expect(Number(fila?.available), "denegar dejó el dinero secuestrado").toBe(100);
  });

  test("aprobar no paga; ejecutar saca el dinero del banco", async ({ request }) => {
    const c = await ctx(request);
    const m = marca();
    await politica(request, c, m);
    const { cliente, nota } = await creditoAFavor(request, c, m);
    const banco = await cuenta(request, c, m, "VED");
    await fondear(request, c, banco.id, 500);

    const r = await post(request, c, "/treasury/refunds", {
      credit_note_id: nota.id, amount: "60.00", reason: "Solicitud del cliente",
      account_id: banco.id,
    });
    await post(request, c, `/treasury/refunds/${r.id}/decide`, { approved: true });
    expect(await saldo(request, c, banco.id), "aprobar movió dinero").toBe(500);

    const hecho = await post(request, c, `/treasury/refunds/${r.id}/settle`, {});
    expect(hecho.status).toBe("SETTLED");
    expect(hecho.movement_id, "ejecutó sin dejar movimiento").toBeTruthy();
    expect(await saldo(request, c, banco.id)).toBe(440);

    const saldoCliente = await get(request, c, `/sales/cxc/clientes/${cliente}/saldo`);
    expect(Number(saldoCliente.credit_refunded)).toBe(60);
    expect(Number(saldoCliente.credit_available)).toBe(40);
  });

  test("P0 · ejecutar dos veces no paga dos veces", async ({ request }) => {
    // Ejecutar es idempotente **a propósito**: un reintento por corte de red no
    // puede convertirse en un segundo pago, y devolver un error al que reintenta
    // le invita a insistir de otra forma. Así que lo que se exige no es un
    // código de rechazo, sino que el dinero no se mueva: mismo saldo, mismo
    // movimiento, mismo importe devuelto.
    const c = await ctx(request);
    const m = marca();
    await politica(request, c, m);
    const { cliente, nota } = await creditoAFavor(request, c, m);
    const banco = await cuenta(request, c, m, "VED");
    await fondear(request, c, banco.id, 500);
    const r = await post(request, c, "/treasury/refunds", {
      credit_note_id: nota.id, amount: "60.00", reason: "Solicitud del cliente",
      account_id: banco.id,
    });
    await post(request, c, `/treasury/refunds/${r.id}/decide`, { approved: true });
    const primera = await post(request, c, `/treasury/refunds/${r.id}/settle`, {});
    expect(await saldo(request, c, banco.id)).toBe(440);

    const segunda = await post(request, c, `/treasury/refunds/${r.id}/settle`, {});
    expect(segunda.movement_id, "el segundo pago creó otro movimiento")
      .toBe(primera.movement_id);
    expect(await saldo(request, c, banco.id), "pagó dos veces el mismo reembolso").toBe(440);
    const saldoCliente = await get(request, c, `/sales/cxc/clientes/${cliente}/saldo`);
    expect(Number(saldoCliente.credit_refunded), "descontó el crédito dos veces").toBe(60);
  });

  /*
   * El aislamiento entre empresas se comprueba en `tests/test_spec038_treasury.py`
   * (`test_la_api_no_devuelve_un_credito_de_otra_empresa`), con dos empresas
   * reales del mundo de pruebas del backend.
   *
   * Aquí no: crear una segunda empresa en la base de e2e hace que el shell pida
   * «Seleccione una empresa» al entrar, y eso cambia el arranque de **todas**
   * las demás suites. Una prueba no puede dejar el mundo distinto de como lo
   * encontró.
   */

  test("la posición de caja no suma monedas distintas", async ({ request }) => {
    const c = await ctx(request);
    const m = marca();
    const codigo = codigoMoneda("S", m);
    await post(request, c, "/treasury/currencies", { code: codigo, name: `Moneda ${m}` });
    const antes = await get(request, c, "/treasury/cash-position");
    const uno = await cuenta(request, c, m, "VED");
    const dos = await cuenta(request, c, m, codigo);
    await fondear(request, c, uno.id, 100);
    await fondear(request, c, dos.id, 50);

    const pos = await get(request, c, "/treasury/cash-position");
    expect(pos.total, "sumó monedas distintas en un solo número").toBeUndefined();
    const saldoDe = (p: { by_currency: Array<{ currency: string; balance: string }> },
                     cod: string): number =>
      Number(p.by_currency.find((x) => x.currency === cod)?.balance ?? 0);
    // Se mide la diferencia, no el absoluto: la base es compartida y otras
    // pruebas también mueven bolívares.
    expect(saldoDe(pos, codigo) - saldoDe(antes, codigo)).toBe(50);
    expect(saldoDe(pos, "VED") - saldoDe(antes, "VED")).toBe(100);
  });

  test("la interfaz recorre el reembolso y el dominio lo confirma", async ({ page, request }) => {
    const c = await ctx(request);
    const m = marca();
    await politica(request, c, m);
    const { cliente, nota } = await creditoAFavor(request, c, m);
    const banco = await cuenta(request, c, m, "VED");
    await fondear(request, c, banco.id, 500);

    await uiLogin(page);
    await irA(page, "/tesoreria/reembolsos");
    await expect(page.getByRole("heading", { name: "Reembolsos", level: 1 })).toBeVisible({
      timeout: 20_000,
    });

    await page.getByLabel("Cliente").selectOption(cliente);
    await expect(page.getByLabel("Crédito").locator(`option[value="${nota.id}"]`))
      .toHaveCount(1, { timeout: 20_000 });
    await page.getByLabel("Crédito").selectOption(nota.id as string);
    await page.getByLabel("Importe").fill("60.00");
    await page.getByLabel("Cuenta pagadora").selectOption(banco.id as string);
    // `getByLabel` casa el **texto** de la etiqueta, no el nombre accesible: ahí
    // sigue el asterisco de obligatorio, que la accesibilidad sí oculta. De modo
    // que se ancla al principio —«Motivo» suelto chocaría con «Motivo de la
    // decisión»— y se deja pasar el asterisco.
    await page.getByLabel(/^Motivo\s*\*/).fill("El cliente pidió su dinero");
    await page.getByRole("button", { name: "Solicitar reembolso" }).click();

    // La tabla lista los reembolsos de toda la empresa, así que la fila se
    // identifica por **su** nota: quedarse con la primera «Solicitado» sería
    // operar sobre el reembolso de otra prueba que corre a la vez.
    const fila = page.getByRole("row").filter({ hasText: (nota.id as string).slice(0, 8) });
    await expect(fila).toBeVisible({ timeout: 20_000 });
    await expect(fila).toContainText("Solicitado");
    await fila.getByRole("button", { name: "Aprobar" }).click();

    await expect(fila).toContainText("Aprobado", { timeout: 20_000 });
    // Aprobar no paga: el banco sigue igual.
    expect(await saldo(request, c, banco.id)).toBe(500);

    await fila.getByRole("button", { name: "Ejecutar pago" }).click();
    await expect(fila).toContainText("Ejecutado", { timeout: 20_000 });

    // Y el dominio: salió el dinero y el crédito quedó devuelto.
    expect(await saldo(request, c, banco.id)).toBe(440);
    const saldoCliente = await get(request, c, `/sales/cxc/clientes/${cliente}/saldo`);
    expect(Number(saldoCliente.credit_refunded)).toBe(60);
  });

  test("la interfaz de cambio muestra la política vigente y la procedencia de la tasa", async ({ page, request }) => {
    const c = await ctx(request);
    const m = marca();
    await politica(request, c, m);
    const codigo = codigoMoneda("T", m);
    const moneda = await post(request, c, "/treasury/currencies", { code: codigo, name: `Moneda ${m}` });
    await post(request, c, "/treasury/exchange-rates", {
      currency_id: moneda.id, rate_date: hoy(), rate: "40.00", source: "BCV",
    });
    const origen = await cuenta(request, c, m, codigo);
    const destino = await cuenta(request, c, m, "VED");
    await fondear(request, c, origen.id, 100);
    await post(request, c, "/treasury/fx-conversions", {
      source_account_id: origen.id, target_account_id: destino.id, source_amount: "10.00",
    });

    await uiLogin(page);
    await irA(page, "/tesoreria/cambio");
    await expect(page.getByRole("heading", { name: "Cambio de moneda", level: 1 })).toBeVisible({
      timeout: 20_000,
    });
    await expect(page.getByRole("heading", { name: "Política vigente" })).toBeVisible();
    await expect(page.getByText("Tasa registrada").first()).toBeVisible({ timeout: 20_000 });
  });

  test("la posición de caja se ve por moneda y sin total", async ({ page, request }) => {
    const c = await ctx(request);
    const m = marca();
    const uno = await cuenta(request, c, m, "VED");
    await fondear(request, c, uno.id, 100);

    await uiLogin(page);
    await irA(page, "/tesoreria/posicion");
    await expect(page.getByRole("heading", { name: "Posición de caja", level: 1 })).toBeVisible({
      timeout: 20_000,
    });
    await expect(page.getByRole("heading", { name: "Por moneda" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Por cuenta" })).toBeVisible();
    expect(await page.getByText(/^Total general/i).count()).toBe(0);
  });
});
