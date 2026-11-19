import { expect, test } from "./helpers/sesion";
import { API, TENANT, entrarEnGobierno, crearUsuario, cerrarNotificaciones } from "./helpers/gobierno";
import { sesionApi } from "./helpers/sesion";
import { sinViolacionesSerias, hoyCaracas } from "./helpers/ordenes-pago";
import {
  prepararMundoPagos,
  ordenEmitidaApi,
  medioApi,
  politicaPagoApi,
  pagoApi,
  enviarApi,
  aprobarApi,
  registrarApi,
  detallePagoApi,
  detalleOrdenApi,
  marca,
} from "./helpers/pagos";

test.describe("Gobierno · Tesorería · Pagos (TRE-04)", () => {
  test("TRE04-E2E-01 · recorrido principal por la interfaz", async ({ page, request, browser }) => {
    test.setTimeout(600_000);

    const mp = await prepararMundoPagos(request, ["100.00"]);
    const orden = await ordenEmitidaApi(request, mp.m, 0, "100.00");

    let medioId = "";
    let politicaId = "";
    let pagoId = "";


    await test.step("Preparar medio y política de pago por la interfaz", async () => {
      await entrarEnGobierno(page, mp.m.mundo.username, mp.m.mundo.codigo, "/gobierno/tesoreria/politicas-pago");
      await expect(page.getByRole("heading", { level: 1, name: "Políticas de pago" })).toBeVisible();
      await sinViolacionesSerias(page, "políticas de pago");

      const codigo = `MEDIO-${marca()}`;
      const crearResp = page.waitForResponse(
        (resp) =>
          resp.request().method() === "POST" &&
          new URL(resp.url()).pathname.endsWith("/medios-pago") &&
          resp.status() === 201,
      );


      await page.getByLabel(/^Código/).fill(codigo);
      await page.getByLabel(/^Nombre/).fill(`Medio ${marca()}`);
      await page.getByLabel(/^Vigente desde/).fill(`${mp.m.anio}-01-01`);
      await page.getByLabel(/^Fundamento/).fill("Fundamento del medio de pago E2E");
      await page.getByRole("button", { name: "Crear medio de pago" }).click();
      const crearRespJson = (await (await crearResp).json()) as { id: string };
      medioId = crearRespJson.id;

      await cerrarNotificaciones(page);

      const politica = await politicaPagoApi(request, mp, [medioId]);
      politicaId = politica.id;
    });

    await test.step("Crear pago por la interfaz", async () => {
      await page.locator('nav a[href="/gobierno/tesoreria/pagos"]').first().click();
      await expect(page.getByRole("heading", { level: 1, name: "Pagos" })).toBeVisible();

      await page.getByRole("link", { name: "Nuevo pago" }).click();

      await page.getByLabel(/^Orden de pago/).selectOption(orden.id);
      await page.getByLabel(/^Política/).selectOption(politicaId);
      await page.getByLabel(/^Cuenta/).selectOption(mp.cuentaId);
      await page.getByLabel(/^Medio de pago/).selectOption(medioId);
      await page.getByLabel(/^Monto/).fill("40.00");
      await page.getByLabel(/^Fecha de pago/).fill(hoyCaracas());
      await page.getByLabel(/^Concepto/).fill("Pago E2E principal");

      const crearPagoResp = page.waitForResponse(
        (resp) =>
          resp.request().method() === "POST" &&
          new URL(resp.url()).pathname.endsWith("/pagos") &&
          resp.status() === 201,
      );

      await page.getByRole("button", { name: /^Guardar/ }).click();
      const crearPagoJson = (await (await crearPagoResp).json()) as { id: string };
      pagoId = crearPagoJson.id;

      await page.waitForURL(`**/gobierno/tesoreria/pagos/${pagoId}`);
      await expect(page.getByRole("heading", { level: 1, name: /Pago/ })).toBeVisible();

      await cerrarNotificaciones(page);

      const detalleOrden = await detalleOrdenApi(request, mp.m.mundo.headers, orden.id);
      expect(detalleOrden.monto_pagado).toBe("0.00");
      expect(detalleOrden.monto_en_tramite).toBe("0.00");
    });

    await test.step("Enviar a autorización", async () => {
      await page.getByRole("button", { name: "Enviar a autorización" }).click();
      const dialog = page.getByRole("dialog");
      await expect(dialog.getByRole("heading", { name: "Enviar a autorización" })).toBeVisible();

      const enviarResp = page.waitForResponse(
        (resp) =>
          resp.request().method() === "POST" &&
          new URL(resp.url()).pathname.endsWith(`/pagos/${pagoId}/enviar`) &&
          resp.status() === 200,
      );

      await dialog.getByRole("button", { name: "Enviar" }).click();
      await enviarResp;

      await expect(page.getByText("Pendiente de autorización", { exact: true })).toBeVisible();

      await cerrarNotificaciones(page);

      const detalleOrden = await detalleOrdenApi(request, mp.m.mundo.headers, orden.id);
      expect(detalleOrden.monto_en_tramite).toBe("40.00");
    });

    await test.step("El checker aprueba el pago", async () => {
      const context2 = await browser.newContext();
      const page2 = await context2.newPage();

      await entrarEnGobierno(
        page2,
        mp.checker.username,
        mp.m.mundo.codigo,
        "/gobierno/tesoreria/pagos",
      );

      await cerrarNotificaciones(page2);

      await page2.locator(`a[href="/gobierno/tesoreria/pagos/${pagoId}"]`).first().click();
      await page2.waitForURL(`**/gobierno/tesoreria/pagos/${pagoId}`);

      await page2.getByRole("button", { name: "Aprobar" }).click();
      const dialog = page2.getByRole("dialog");
      await expect(dialog.getByRole("heading", { name: "Aprobar pago" })).toBeVisible();

      const aprobarResp = page2.waitForResponse(
        (resp) =>
          resp.request().method() === "POST" &&
          new URL(resp.url()).pathname.endsWith(`/pagos/${pagoId}/aprobar`) &&
          resp.status() === 200,
      );

      await dialog.getByLabel(/^Cargo que autoriza/).selectOption(mp.cargoPagarId);
      await dialog.getByLabel(/^Requisito/).selectOption("0");
      await dialog.getByRole("button", { name: "Aprobar" }).click();
      await aprobarResp;

      await expect(page2.getByText("Autorizado", { exact: true })).toBeVisible();
      await cerrarNotificaciones(page2);
      await context2.close();
    });

    await test.step("El maker registra el pago ejecutado", async () => {
      await page.reload();
      await expect(page.getByRole("heading", { level: 1, name: /Pago/ })).toBeVisible();

      await page.getByRole("button", { name: "Registrar pago ejecutado" }).click();
      const dialog = page.getByRole("dialog");
      await expect(dialog.getByRole("heading", { name: "Registrar pago ejecutado" })).toBeVisible();

      const registrarResp = page.waitForResponse(
        (resp) =>
          resp.request().method() === "POST" &&
          new URL(resp.url()).pathname.endsWith(`/pagos/${pagoId}/registrar`) &&
          resp.status() === 200,
      );

      const referencia = `REF-${marca()}`;
      await dialog.getByLabel(/^Referencia externa/).fill(referencia);
      await dialog.getByRole("button", { name: "Registrar" }).click();
      await registrarResp;

      await expect(page.getByText("Pago registrado", { exact: true })).toBeVisible();

      await cerrarNotificaciones(page);

      const detalleOrden = await detalleOrdenApi(request, mp.m.mundo.headers, orden.id);
      expect(detalleOrden.monto_pagado).toBe("40.00");
      expect(detalleOrden.pendiente_de_pagar).toBe("60.00");

      const tablaEventos = page.getByRole("region", { name: "Tabla de eventos del pago" });
      await expect(tablaEventos).toContainText("CREADO");
      await expect(tablaEventos).toContainText("ENVIADO");
      await expect(tablaEventos).toContainText("AUTORIZADO");
      await expect(tablaEventos).toContainText("REGISTRADO");
    });

    await test.step("Auditoría de accesibilidad y responsive", async () => {
      for (const ancho of [1280, 390, 320]) {
        await page.setViewportSize({ width: ancho, height: 900 });

        await page.goto("/gobierno/tesoreria/pagos");
        await expect(page.getByRole("heading", { level: 1, name: "Pagos" })).toBeVisible();
        await sinViolacionesSerias(page, `lista de pagos a ${ancho}px`);
        await page.goto(`/gobierno/tesoreria/pagos/${pagoId}`);
        await expect(page.getByRole("heading", { level: 1, name: /Pago/ })).toBeVisible();
        await sinViolacionesSerias(page, `detalle de pago a ${ancho}px`);
        await page.goto("/gobierno/tesoreria/pagos/nuevo");
        await expect(page.getByRole("heading", { level: 1, name: "Nuevo pago" })).toBeVisible();
        await sinViolacionesSerias(page, `nuevo pago a ${ancho}px`);
        await page.goto("/gobierno/tesoreria/politicas-pago");
        await expect(page.getByRole("heading", { level: 1, name: "Políticas de pago" })).toBeVisible();
        await sinViolacionesSerias(page, `políticas de pago a ${ancho}px`);
      }
    });
  });

  test("TRE04-E2E-02 · el maker no autoriza su propio pago", async ({ request }) => {
    test.setTimeout(600_000);

    const mp = await prepararMundoPagos(request, ["100.00"]);
    const admin = await sesionApi("admintenant", { tenant: TENANT });

    const mkck = await crearUsuario(
      request,
      admin.headers,
      [
        "organization:view",
        "gobierno_pagos:view",
        "gobierno_pagos:manage",
        "gobierno_pagos:authorize",
      ],
      mp.m.mundo.companyId,
    );

    const medio = await medioApi(request, mp);
    const politica = await politicaPagoApi(request, mp, [medio.id]);
    const orden = await ordenEmitidaApi(request, mp.m, 0, "100.00");

    const pagoCreado = await request.post(`${API}/gobierno/tesoreria/pagos`, {
      headers: mkck.headers,
      data: {
        order_id: orden.id,
        policy_id: politica.id,
        account_id: mp.cuentaId,
        method_id: medio.id,
        fecha_pago: hoyCaracas(),
        monto: "40.00",
        concepto: "Pago del maker sin permiso para autoaprobar",
      },
    });
    expect(pagoCreado.status(), await pagoCreado.text()).toBe(201);
    const pago = (await pagoCreado.json()) as { id: string; version: number };

    const enviado = await enviarApi(request, mkck.headers, pago, {});
    expect(enviado.status(), await enviado.text()).toBe(200);

    const aprobado = await aprobarApi(request, mkck.headers, pago, mp.cargoPagarId, 0);
    expect(aprobado.status(), await aprobado.text()).toBe(409);
    const errorBody = (await aprobado.json()) as { code?: string };
    expect(errorBody.code).toBe("GOV_PAYMENT_MAKER_CHECKER");

    const detalle = await detallePagoApi(request, mp.m.mundo.headers, pago.id);
    expect(detalle.estado).toBe("PENDIENTE_AUTORIZACION");
  });

  test("TRE04-E2E-03 · pagos múltiples hasta completar", async ({ request }) => {
    test.setTimeout(600_000);

    const mp = await prepararMundoPagos(request, ["100.00"]);
    const medio = await medioApi(request, mp);
    const politica = await politicaPagoApi(request, mp, [medio.id], {
      controlDuplicado: "ADVERTIR",
    });
    const orden = await ordenEmitidaApi(request, mp.m, 0, "100.00");

    const importes = ["40.00", "30.00", "30.00"];
    const pagos: { id: string; version: number }[] = [];

    for (let i = 0; i < importes.length; i++) {
      const pago = await pagoApi(request, mp, orden.id, politica.id, medio.id, importes[i]);
      pagos.push(pago);

      if (i === 2) {
        const enviadoConflicto = await enviarApi(request, mp.m.mundo.headers, pago, {});
        expect(enviadoConflicto.status(), await enviadoConflicto.text()).toBe(409);
        const conflicto = (await enviadoConflicto.json()) as { code?: string };
        expect(conflicto.code).toBe("GOV_PAYMENT_DUPLICATE_CONFIRMATION_REQUIRED");

        const enviado = await enviarApi(request, mp.m.mundo.headers, pago, {
          confirmar_duplicado: true,
          motivo_duplicado: "Segunda cuota del mismo importe",
        });
        expect(enviado.status(), await enviado.text()).toBe(200);
      } else {
        const enviado = await enviarApi(request, mp.m.mundo.headers, pago, {});
        expect(enviado.status(), await enviado.text()).toBe(200);
      }

      const aprobado = await aprobarApi(request, mp.checker.headers, pago, mp.cargoPagarId, 0);
      expect(aprobado.status(), await aprobado.text()).toBe(200);

      const referencia = `PAGO-${marca()}-${i + 1}`;
      const registrado = await registrarApi(request, mp.m.mundo.headers, pago, referencia);
      expect(registrado.status(), await registrado.text()).toBe(200);
    }

    const detalle = await detalleOrdenApi(request, mp.m.mundo.headers, orden.id);
    expect(detalle.monto_pagado).toBe("100.00");
    expect(detalle.pendiente_de_pagar).toBe("0.00");
  });

  test("TRE04-E2E-04 · sobrepago bloqueado", async ({ request }) => {
    test.setTimeout(600_000);

    const mp = await prepararMundoPagos(request, ["100.00"]);
    const medio = await medioApi(request, mp);
    const politica = await politicaPagoApi(request, mp, [medio.id]);
    const orden = await ordenEmitidaApi(request, mp.m, 0, "100.00");

    const pago70 = await pagoApi(request, mp, orden.id, politica.id, medio.id, "70.00");
    const enviado70 = await enviarApi(request, mp.m.mundo.headers, pago70, {});
    expect(enviado70.status(), await enviado70.text()).toBe(200);
    const aprobado70 = await aprobarApi(request, mp.checker.headers, pago70, mp.cargoPagarId, 0);
    expect(aprobado70.status(), await aprobado70.text()).toBe(200);
    const registrado70 = await registrarApi(request, mp.m.mundo.headers, pago70, `SOBRE-${marca()}`);
    expect(registrado70.status(), await registrado70.text()).toBe(200);

    const pago31 = await pagoApi(request, mp, orden.id, politica.id, medio.id, "31.00");
    const enviado31 = await enviarApi(request, mp.m.mundo.headers, pago31, {});
    expect(enviado31.status(), await enviado31.text()).toBe(409);
    const errorBody = (await enviado31.json()) as { code?: string };
    expect(errorBody.code).toBe("GOV_PAYMENT_OVERPAYMENT");

    const pago30 = await pagoApi(request, mp, orden.id, politica.id, medio.id, "30.00");
    const enviado30 = await enviarApi(request, mp.m.mundo.headers, pago30, {});
    expect(enviado30.status(), await enviado30.text()).toBe(200);
  });

  test("TRE04-E2E-05 · referencia duplicada", async ({ request }) => {
    test.setTimeout(600_000);

    const mp = await prepararMundoPagos(request, ["100.00", "100.00"]);
    const medio = await medioApi(request, mp, { referenciaUnica: true });
    const politica = await politicaPagoApi(request, mp, [medio.id]);
    const ordenA = await ordenEmitidaApi(request, mp.m, 0, "100.00");
    const ordenB = await ordenEmitidaApi(request, mp.m, 1, "100.00");

    const referencia = `DUP-${marca()}`;

    const pagoA = await pagoApi(request, mp, ordenA.id, politica.id, medio.id, "40.00");
    const enviadoA = await enviarApi(request, mp.m.mundo.headers, pagoA, {});
    expect(enviadoA.status(), await enviadoA.text()).toBe(200);
    const aprobadoA = await aprobarApi(request, mp.checker.headers, pagoA, mp.cargoPagarId, 0);
    expect(aprobadoA.status(), await aprobadoA.text()).toBe(200);
    const registradoA = await registrarApi(request, mp.m.mundo.headers, pagoA, referencia);
    expect(registradoA.status(), await registradoA.text()).toBe(200);

    const pagoB = await pagoApi(request, mp, ordenB.id, politica.id, medio.id, "40.00");
    const enviadoB = await enviarApi(request, mp.m.mundo.headers, pagoB, {});
    expect(enviadoB.status(), await enviadoB.text()).toBe(200);
    const aprobadoB = await aprobarApi(request, mp.checker.headers, pagoB, mp.cargoPagarId, 0);
    expect(aprobadoB.status(), await aprobadoB.text()).toBe(200);

    const registradoB = await registrarApi(
      request,
      mp.m.mundo.headers,
      pagoB,
      referencia.toLowerCase(),
    );
    expect(registradoB.status(), await registradoB.text()).toBe(409);
    const errorBody = (await registradoB.json()) as { code?: string };
    expect(errorBody.code).toBe("GOV_PAYMENT_DUPLICATE_REFERENCE");
  });

  test("TRE04-E2E-06 · la banda depende del monto", async ({ request }) => {
    test.setTimeout(600_000);

    const mp = await prepararMundoPagos(request, ["300.00"]);
    const medio = await medioApi(request, mp);
    const politica = await politicaPagoApi(request, mp, [medio.id], {
      bandas: [
        {
          monto_desde: "0",
          monto_hasta: "100.00",
          requisitos: [{ accion: "PAGAR", materia: "TESORERIA", cantidad: 1 }],
        },
        {
          monto_desde: "100.00",
          monto_hasta: null,
          requisitos: [
            { accion: "PAGAR", materia: "TESORERIA", cantidad: 1 },
            { accion: "FIRMAR", materia: "TESORERIA", cantidad: 1 },
          ],
        },
      ],
    });
    const orden = await ordenEmitidaApi(request, mp.m, 0, "300.00");

    const pago50 = await pagoApi(request, mp, orden.id, politica.id, medio.id, "50.00");
    const enviado50 = await enviarApi(request, mp.m.mundo.headers, pago50, {});
    expect(enviado50.status(), await enviado50.text()).toBe(200);
    const detalle50 = await detallePagoApi(request, mp.m.mundo.headers, pago50.id);
    expect(detalle50.aprobaciones_requeridas).toBe(1);
    expect((detalle50.regla as { banda: { orden: number } }).banda.orden).toBe(1);

    const pago150 = await pagoApi(request, mp, orden.id, politica.id, medio.id, "150.00");
    const enviado150 = await enviarApi(request, mp.m.mundo.headers, pago150, {});
    expect(enviado150.status(), await enviado150.text()).toBe(200);
    const detalle150 = await detallePagoApi(request, mp.m.mundo.headers, pago150.id);
    expect(detalle150.aprobaciones_requeridas).toBe(2);
    expect((detalle150.regla as { banda: { orden: number } }).banda.orden).toBe(2);

    const aprobadoChecker = await aprobarApi(
      request,
      mp.checker.headers,
      pago150,
      mp.cargoPagarId,
      0,
    );
    expect(aprobadoChecker.status(), await aprobadoChecker.text()).toBe(200);

    const aprobadoFirmante = await aprobarApi(
      request,
      mp.checker2.headers,
      pago150,
      mp.cargoFirmarId,
      1,
    );
    expect(aprobadoFirmante.status(), await aprobadoFirmante.text()).toBe(200);

    const detalleFinal = await detallePagoApi(request, mp.m.mundo.headers, pago150.id);
    expect(detalleFinal.estado).toBe("AUTORIZADO");
  });

  test("TRE04-E2E-07 · la versión de la política queda congelada", async ({ request }) => {
    test.setTimeout(600_000);

    const mp = await prepararMundoPagos(request, ["100.00", "100.00"]);
    const medio = await medioApi(request, mp);
    const politicaV1 = await politicaPagoApi(request, mp, [medio.id], {
      activar: true,
      vigenteDesde: `${mp.m.anio - 1}-12-31`,
    });

    const ordenA = await ordenEmitidaApi(request, mp.m, 0, "100.00");
    const pagoA = await pagoApi(request, mp, ordenA.id, politicaV1.id, medio.id, "40.00");
    const enviadoA = await enviarApi(request, mp.m.mundo.headers, pagoA, {});
    expect(enviadoA.status(), await enviadoA.text()).toBe(200);
    const detalleA1 = await detallePagoApi(request, mp.m.mundo.headers, pagoA.id);
    expect((detalleA1.regla as { numero_version: number }).numero_version).toBe(1);

    const nuevaVersionResp = await request.post(
      `${API}/gobierno/tesoreria/politicas-pago/${politicaV1.id}/nueva-version`,
      { headers: mp.m.mundo.headers },
    );
    expect(nuevaVersionResp.status(), await nuevaVersionResp.text()).toBe(201);
    const v2 = (await nuevaVersionResp.json()) as { id: string; version: number };

    const actualizarV2 = await request.put(
      `${API}/gobierno/tesoreria/politicas-pago/${v2.id}`,
      {
        headers: { ...mp.m.mundo.headers, "If-Match": String(v2.version) },
        data: { vigente_desde: hoyCaracas() },
      },
    );
    expect(actualizarV2.status(), await actualizarV2.text()).toBe(200);
    const v2Actualizado = (await actualizarV2.json()) as { id: string; version: number };

    const activarV2 = await request.post(
      `${API}/gobierno/tesoreria/politicas-pago/${v2Actualizado.id}/activar`,
      {
        headers: { ...mp.m.mundo.headers, "If-Match": String(v2Actualizado.version) },
        data: { fundamento: "Activación de la versión 2 para congelar reglas de pagos" },
      },
    );
    expect(activarV2.status(), await activarV2.text()).toBe(200);

    const ordenB = await ordenEmitidaApi(request, mp.m, 1, "100.00");
    const pagoB = await pagoApi(request, mp, ordenB.id, v2Actualizado.id, medio.id, "40.00");
    const enviadoB = await enviarApi(request, mp.m.mundo.headers, pagoB, {});
    expect(enviadoB.status(), await enviadoB.text()).toBe(200);
    const detalleB = await detallePagoApi(request, mp.m.mundo.headers, pagoB.id);
    expect((detalleB.regla as { numero_version: number }).numero_version).toBe(2);

    const detalleA2 = await detallePagoApi(request, mp.m.mundo.headers, pagoA.id);
    expect((detalleA2.regla as { numero_version: number }).numero_version).toBe(1);

    const aprobadoA = await aprobarApi(request, mp.checker.headers, pagoA, mp.cargoPagarId, 0);
    expect(aprobadoA.status(), await aprobadoA.text()).toBe(200);
    const registradoA = await registrarApi(request, mp.m.mundo.headers, pagoA, `VER-${marca()}`);
    expect(registradoA.status(), await registradoA.text()).toBe(200);
  });
});
