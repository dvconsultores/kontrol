import { expect, test } from "./helpers/sesion";
import { API, TENANT, entrarEnGobierno, crearUsuario, cerrarNotificaciones } from "./helpers/gobierno";
import { sesionApi } from "./helpers/sesion";
import { hoyCaracas, sinViolacionesSerias } from "./helpers/ordenes-pago";
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
  marca,
} from "./helpers/pagos";

async function crearConceptoApi(request: import("@playwright/test").APIRequestContext, headers: Record<string, string>, codigo: string, nombre: string) {
  const resp = await request.post(`${API}/gobierno/tesoreria/retenciones/catalogo`, {
    headers,
    data: { tipo: "CONCEPTO", codigo, nombre, clase: "TRIBUTARIA" },
  });
  expect(resp.status()).toBe(201);
  return (await resp.json()) as { id: string; codigo: string; nombre: string };
}

async function crearCondicionApi(request: import("@playwright/test").APIRequestContext, headers: Record<string, string>, codigo: string, nombre: string) {
  const resp = await request.post(`${API}/gobierno/tesoreria/retenciones/catalogo`, {
    headers,
    data: { tipo: "CONDICION", codigo, nombre },
  });
  expect(resp.status()).toBe(201);
  return (await resp.json()) as { id: string; codigo: string; nombre: string };
}

async function crearPoliticaRetencionApi(
  request: import("@playwright/test").APIRequestContext,
  headers: Record<string, string>,
  mp: Awaited<ReturnType<typeof prepararMundoPagos>>,
  datos: {
    codigo: string;
    nombre: string;
    reglas: Array<{
      orden: number;
      concept_id: string;
      base_tipo?: string;
      tasa: string;
      umbral_tipo?: string;
      umbral_monto?: string;
      exclusiones?: string[];
      condiciones_exigidas?: string[];
      exige_comprobante?: boolean;
    }>;
  },
) {
  const resp = await request.post(`${API}/gobierno/tesoreria/retenciones/politicas`, {
    headers,
    data: {
      codigo: datos.codigo,
      nombre: datos.nombre,
      moneda: mp.moneda,
      fuente_descripcion: "Acto del ente de prueba E2E",
      fuente_referencia: "Art. 1",
      aprobador_competencia_accion: "PAGAR",
      aprobador_competencia_materia: "TESORERIA",
      vigente_desde: `${mp.m.anio}-01-01`,
      reglas: datos.reglas.map((r) => ({
        orden: r.orden,
        concept_id: r.concept_id,
        base_tipo: r.base_tipo ?? "MONTO_BRUTO",
        tasa: r.tasa,
        umbral_tipo: r.umbral_tipo ?? "NINGUNO",
        umbral_monto: r.umbral_monto ?? null,
        condiciones_exigidas: r.condiciones_exigidas ?? [],
        exclusiones: r.exclusiones ?? [],
        tipos_persona: null,
        exige_comprobante: r.exige_comprobante ?? false,
      })),
    },
  });
  expect(resp.status()).toBe(201);
  return (await resp.json()) as {
    id: string;
    version: number;
    numero_version: number;
    estado: string;
    reglas: Array<{ id: string; concept_id: string }>;
  };
}

async function activarPoliticaRetencionApi(
  request: import("@playwright/test").APIRequestContext,
  headers: Record<string, string>,
  politicaId: string,
  version: number,
) {
  const resp = await request.post(`${API}/gobierno/tesoreria/retenciones/politicas/${politicaId}/activar`, {
    headers: { ...headers, "If-Match": String(version) },
    data: { fundamento: "Fundamento de activación E2E de más de veinte caracteres." },
  });
  expect(resp.status()).toBe(200);
  return (await resp.json()) as { estado: string };
}

async function nuevaVersionPoliticaRetencionApi(
  request: import("@playwright/test").APIRequestContext,
  headers: Record<string, string>,
  politicaId: string,
) {
  const resp = await request.post(`${API}/gobierno/tesoreria/retenciones/politicas/${politicaId}/nueva-version`, {
    headers,
    data: {},
  });
  expect(resp.status()).toBe(201);
  return (await resp.json()) as {
    id: string;
    version: number;
    numero_version: number;
    estado: string;
    reglas: Array<{ id: string; concept_id: string }>;
  };
}

async function actualizarPoliticaRetencionApi(
  request: import("@playwright/test").APIRequestContext,
  headers: Record<string, string>,
  politicaId: string,
  version: number,
  reglas: Array<{
    orden: number;
    concept_id: string;
    base_tipo?: string;
    tasa: string;
    umbral_tipo?: string;
    umbral_monto?: string;
    exclusiones?: string[];
    condiciones_exigidas?: string[];
    exige_comprobante?: boolean;
  }>,
) {
  const resp = await request.put(`${API}/gobierno/tesoreria/retenciones/politicas/${politicaId}`, {
    headers: { ...headers, "If-Match": String(version) },
    data: {
      vigente_desde: hoyCaracas(),
      reglas: reglas.map((r) => ({
        orden: r.orden,
        concept_id: r.concept_id,
        base_tipo: r.base_tipo ?? "MONTO_BRUTO",
        tasa: r.tasa,
        umbral_tipo: r.umbral_tipo ?? "NINGUNO",
        umbral_monto: r.umbral_monto ?? null,
        condiciones_exigidas: r.condiciones_exigidas ?? [],
        exclusiones: r.exclusiones ?? [],
        tipos_persona: null,
        exige_comprobante: r.exige_comprobante ?? false,
      })),
    },
  });
  expect(resp.status()).toBe(200);
  return (await resp.json()) as { id: string; version: number; estado: string };
}

async function calcularLiquidacionApi(
  request: import("@playwright/test").APIRequestContext,
  headers: Record<string, string>,
  pagoId: string,
  policyId: string,
  conceptoCodigos: string[],
  beneficiario: {
    nombre: string;
    identificacion_fiscal: string;
    tipo_persona: string;
    condiciones?: string[];
  },
) {
  const resp = await request.post(`${API}/gobierno/tesoreria/retenciones/pagos/${pagoId}/liquidacion`, {
    headers,
    data: {
      policy_id: policyId,
      conceptos: conceptoCodigos,
      beneficiario: {
        nombre: beneficiario.nombre,
        identificacion_fiscal: beneficiario.identificacion_fiscal,
        tipo_persona: beneficiario.tipo_persona,
        condiciones: beneficiario.condiciones ?? [],
      },
    },
  });
  expect(resp.status()).toBe(201);
  return (await resp.json()) as {
    id: string;
    version: number;
    estado: string;
    policy_numero_version: number;
    total_retenido: string;
    neto: string;
    lineas: Array<{
      concepto_codigo: string;
      aplica: boolean;
      motivo_no_aplica: string | null;
      monto_aprobado: string;
    }>;
  };
}

async function getLiquidacionApi(
  request: import("@playwright/test").APIRequestContext,
  headers: Record<string, string>,
  pagoId: string,
) {
  const resp = await request.get(`${API}/gobierno/tesoreria/retenciones/pagos/${pagoId}/liquidacion`, {
    headers,
  });
  expect(resp.status()).toBe(200);
  return (await resp.json()) as {
    montos: { bruto: string; total_retenido: string; neto: string; definitivo: boolean };
    liquidacion: {
      id: string;
      version: number;
      estado: string;
      policy_numero_version: number;
      total_retenido: string;
      neto: string;
      lineas: Array<{
        concepto_codigo: string;
        aplica: boolean;
        motivo_no_aplica: string | null;
        monto_aprobado: string;
      }>;
    };
  };
}

async function aprobarLiquidacionApi(
  request: import("@playwright/test").APIRequestContext,
  headers: Record<string, string>,
  liquidacionId: string,
  version: number,
  cargoId: string,
) {
  const resp = await request.post(`${API}/gobierno/tesoreria/retenciones/liquidaciones/${liquidacionId}/aprobar`, {
    headers: { ...headers, "If-Match": String(version) },
    data: { cargo_id: cargoId },
  });
  expect(resp.status()).toBe(200);
  return (await resp.json()) as { estado: string };
}

async function getPoliticaRetencionApi(
  request: import("@playwright/test").APIRequestContext,
  headers: Record<string, string>,
  politicaId: string,
) {
  const resp = await request.get(`${API}/gobierno/tesoreria/retenciones/politicas/${politicaId}`, {
    headers,
  });
  expect(resp.status()).toBe(200);
  return (await resp.json()) as { id: string; estado: string; numero_version: number };
}

async function getComprobantesApi(
  request: import("@playwright/test").APIRequestContext,
  headers: Record<string, string>,
  paymentId: string,
) {
  const resp = await request.get(`${API}/gobierno/tesoreria/retenciones/comprobantes?payment_id=${paymentId}`, {
    headers,
  });
  expect(resp.status()).toBe(200);
  return (await resp.json()) as Array<{
    id: string;
    codigo: string;
    concepto_codigo: string;
    estado: string;
    beneficiario_nombre: string;
    monto: string;
  }>;
}

async function anularComprobanteApi(
  request: import("@playwright/test").APIRequestContext,
  headers: Record<string, string>,
  comprobanteId: string,
  motivo: string,
  beneficiario: { nombre: string; identificacion_fiscal: string },
) {
  const resp = await request.post(`${API}/gobierno/tesoreria/retenciones/comprobantes/${comprobanteId}/anular`, {
    headers,
    data: { motivo, sustituir: true, beneficiario },
  });
  expect(resp.status()).toBe(200);
  return (await resp.json()) as { id: string; estado: string };
}

test.describe("Gobierno · Tesorería · Retenciones (TRE-05)", () => {
  test("TRE05-E2E-01 · recorrido principal por la interfaz", async ({ page, request, browser }) => {
    test.setTimeout(600_000);

    const admin = await sesionApi("admintenant", { tenant: TENANT });
    const mp = await prepararMundoPagos(request, ["100.00"]);
    const rtMk = await crearUsuario(request, admin.headers, [
      "organization:view",
      "gobierno_pagos:view",
      "gobierno_ordenes_pago:view",
      "gobierno_retenciones:view",
      "gobierno_retenciones:manage",
      "gobierno_retenciones:calculate",
      "gobierno_retenciones:policy",
    ], mp.m.mundo.companyId as never);
    const rtCk = await crearUsuario(request, admin.headers, [
      "organization:view",
      "gobierno_pagos:view",
      "gobierno_ordenes_pago:view",
      "gobierno_retenciones:view",
      "gobierno_retenciones:approve",
      "gobierno_retenciones:cancel",
    ], mp.m.mundo.companyId as never);
    const orden = await ordenEmitidaApi(request, mp.m, 0, "100.00");
    const medio = await medioApi(request, mp);
    const politicaPago = await politicaPagoApi(request, mp, [medio.id]);
    const pago = await pagoApi(request, mp, orden.id, politicaPago.id, medio.id, "100.00");
    const pagoId = pago.id;

    let conceptoCodigo = "";
    let nombreConcepto = "";
    let conceptoId = "";
    let politicaRetencionId = "";
    let politicaRetencionVersion = 0;

    await test.step("Crear concepto por la interfaz", async () => {
      await entrarEnGobierno(page, rtMk.username, mp.m.mundo.codigo, "/gobierno/tesoreria/politicas-retencion");
      await expect(page.getByRole("heading", { level: 1, name: "Políticas de retención" })).toBeVisible();
      await sinViolacionesSerias(page, "políticas de retención");

      conceptoCodigo = `C${marca()}`.slice(0, 20);
      nombreConcepto = `Concepto ${marca()}`;
      await page.locator("#concepto-codigo").fill(conceptoCodigo);
      await page.locator("#concepto-nombre").fill(nombreConcepto);
      await page.locator("#concepto-clase").selectOption("TRIBUTARIA");

      const crearConceptoResp = page.waitForResponse(
        (resp) =>
          resp.request().method() === "POST" &&
          new URL(resp.url()).pathname.endsWith("/retenciones/catalogo") &&
          resp.status() === 201,
      );

      await page.getByRole("button", { name: "Añadir concepto" }).click();
      const crearConceptoJson = (await (await crearConceptoResp).json()) as { id: string };
      conceptoId = crearConceptoJson.id;

      await cerrarNotificaciones(page);
    });

    await test.step("Crear y activar política de retención por API", async () => {
      const politica = await crearPoliticaRetencionApi(request, rtMk.headers, mp, {
        codigo: `P${marca()}`.slice(0, 20),
        nombre: `Política retención ${marca()}`,
        reglas: [
          {
            orden: 1,
            concept_id: conceptoId,
            tasa: "5",
            exige_comprobante: true,
          },
        ],
      });
      politicaRetencionId = politica.id;
      politicaRetencionVersion = politica.version;
      expect(politica.estado).toBe("BORRADOR");
      expect(politica.reglas).toHaveLength(1);

      await activarPoliticaRetencionApi(request, rtMk.headers, politicaRetencionId, politicaRetencionVersion);
    });

    await test.step("Calcular retenciones por la interfaz", async () => {
      await page.goto(`/gobierno/tesoreria/pagos/${pagoId}`);
      await expect(page.getByRole("heading", { level: 1, name: /Pago/ })).toBeVisible();

      const seccionRetenciones = page.locator("section", {
        has: page.getByRole("heading", { level: 2, name: "Retenciones" }),
      });
      await expect(seccionRetenciones).toBeVisible();

      await seccionRetenciones.getByRole("button", { name: "Calcular retenciones" }).click();
      await expect(seccionRetenciones.locator("#politica-retencion")).toBeVisible();

      await seccionRetenciones.locator("#politica-retencion").selectOption(politicaRetencionId);
      await seccionRetenciones
        .getByRole("checkbox", { name: `${conceptoCodigo} · ${nombreConcepto}` })
        .check();
      await seccionRetenciones.locator("#beneficiario-nombre").fill("Proveedor E2E S.A.");
      await seccionRetenciones.locator("#beneficiario-identificacion").fill("J-12345678-9");
      await seccionRetenciones.locator("#beneficiario-tipo-persona").selectOption("JURIDICA");

      const calcularResp = page.waitForResponse(
        (resp) =>
          resp.request().method() === "POST" &&
          new URL(resp.url()).pathname.endsWith(`/retenciones/pagos/${pagoId}/liquidacion`) &&
          resp.status() === 201,
      );

      await seccionRetenciones.getByRole("button", { name: "Calcular", exact: true }).click();
      await calcularResp;

      await expect(seccionRetenciones.getByText(`95.00 ${mp.moneda}`, { exact: true })).toBeVisible();
      await expect(seccionRetenciones.getByRole("table", { name: "Retenciones calculadas" })).toContainText(conceptoCodigo);
      await expect(seccionRetenciones.getByText("Calculada", { exact: true })).toBeVisible();

      await cerrarNotificaciones(page);
    });

    let liquidacionId = "";

    await test.step("El aprobador aprueba retenciones por la interfaz", async () => {
      const g = await getLiquidacionApi(request, rtMk.headers, pagoId);
      liquidacionId = g.liquidacion.id;

      const context2 = await browser.newContext();
      const page2 = await context2.newPage();

      await entrarEnGobierno(page2, rtCk.username, mp.m.mundo.codigo, "/gobierno/tesoreria/pagos");
      await page2.goto(`/gobierno/tesoreria/pagos/${pagoId}`);
      await expect(page2.getByRole("heading", { level: 1, name: /Pago/ })).toBeVisible();

      const seccionRetenciones2 = page2.locator("section", {
        has: page2.getByRole("heading", { level: 2, name: "Retenciones" }),
      });
      await expect(seccionRetenciones2).toBeVisible();

      await seccionRetenciones2.getByRole("button", { name: "Aprobar retenciones" }).click();
      const dialog = page2.getByRole("dialog");
      await expect(dialog.getByRole("heading", { name: "Aprobar retenciones" })).toBeVisible();

      const aprobarResp = page2.waitForResponse(
        (resp) =>
          resp.request().method() === "POST" &&
          new URL(resp.url()).pathname.endsWith(`/retenciones/liquidaciones/${liquidacionId}/aprobar`) &&
          resp.status() === 200,
      );

      await dialog.getByLabel(/^Cargo que aprueba/).selectOption(mp.cargoPagarId);
      await dialog.getByRole("button", { name: "Aprobar" }).click();
      await aprobarResp;

      await expect(seccionRetenciones2.getByText("Aprobada", { exact: true })).toBeVisible();
      await cerrarNotificaciones(page2);
      await context2.close();
    });

    await test.step("Ejecutar el pago y ver comprobante", async () => {
      const actual = (await detallePagoApi(request, mp.m.mundo.headers, pagoId)) as { version: number };
      const envio = await enviarApi(request, mp.m.mundo.headers, { id: pagoId, version: actual.version });
      expect(envio.status()).toBe(200);

      const auto = await aprobarApi(request, mp.checker.headers, { id: pagoId, version: 0 }, mp.cargoPagarId);
      expect(auto.status(), await auto.text()).toBe(200);

      const registro = await registrarApi(request, mp.m.mundo.headers, { id: pagoId, version: 0 }, `REF-${marca()}`);
      expect(registro.status()).toBe(200);

      await page.reload();
      await expect(page.getByRole("heading", { level: 1, name: /Pago/ })).toBeVisible();

      const seccionRetenciones = page.locator("section", {
        has: page.getByRole("heading", { level: 2, name: "Retenciones" }),
      });
      await expect(seccionRetenciones.getByText("Aplicada", { exact: true })).toBeVisible();
      await expect(seccionRetenciones.getByRole("heading", { level: 3, name: "Comprobantes" })).toBeVisible();
      await expect(seccionRetenciones.getByRole("button", { name: "Descargar PDF" })).toBeVisible();

      await cerrarNotificaciones(page);
    });

    await test.step("Verificar detalle del pago y listado de comprobantes", async () => {
      const detalle = (await detallePagoApi(request, rtMk.headers, pagoId)) as {
        retenciones: { total_retenido: string; neto: string; definitivo: boolean };
      };
      expect(detalle.retenciones.total_retenido).toBe("5.00");
      expect(detalle.retenciones.neto).toBe("95.00");
      expect(detalle.retenciones.definitivo).toBe(true);

      const comprobantes = await getComprobantesApi(request, rtMk.headers, pagoId);
      expect(comprobantes).toHaveLength(1);
      expect(comprobantes[0].estado).toBe("EMITIDO");
      expect(comprobantes[0].concepto_codigo).toBe(conceptoCodigo);

      await page.goto("/gobierno/tesoreria/retenciones");
      await expect(page.getByRole("heading", { level: 1, name: "Retenciones" })).toBeVisible();
      await page.getByRole("tab", { name: "Comprobantes" }).click();
      const tablaComprobantes = page.getByRole("table", { name: "Comprobantes de retención" });
      await expect(tablaComprobantes).toContainText(conceptoCodigo);
    });

    await test.step("Auditoría de accesibilidad y responsive", async () => {
      const rutas: Array<[string, string]> = [
        ["/gobierno/tesoreria/retenciones", "Retenciones"],
        ["/gobierno/tesoreria/politicas-retencion", "Políticas de retención"],
        [`/gobierno/tesoreria/politicas-retencion/${politicaRetencionId}`, "Política retención"],
        [`/gobierno/tesoreria/pagos/${pagoId}`, "Pago"],
      ];

      for (const ancho of [1280, 390, 320]) {
        await page.setViewportSize({ width: ancho, height: 900 });

        for (const [ruta, nombre] of rutas) {
          await page.goto(ruta);
          await expect(page.getByRole("heading", { level: 1, name: new RegExp(nombre) })).toBeVisible();
          await sinViolacionesSerias(page, `${nombre} a ${ancho}px`);
        }
      }
    });
  });

  test("TRE05-E2E-02 · varias reglas", async ({ request }) => {
    test.setTimeout(600_000);

    const admin = await sesionApi("admintenant", { tenant: TENANT });
    const mp = await prepararMundoPagos(request, ["100.00"]);
    const rtMk = await crearUsuario(request, admin.headers, [
      "organization:view",
      "gobierno_pagos:view",
      "gobierno_ordenes_pago:view",
      "gobierno_retenciones:view",
      "gobierno_retenciones:manage",
      "gobierno_retenciones:calculate",
      "gobierno_retenciones:policy",
    ], mp.m.mundo.companyId);
    const orden = await ordenEmitidaApi(request, mp.m, 0, "100.00");
    const medio = await medioApi(request, mp);
    const politicaPago = await politicaPagoApi(request, mp, [medio.id]);
    const pago = await pagoApi(request, mp, orden.id, politicaPago.id, medio.id, "100.00");

    const marcaLocal = marca();
    const c1 = await crearConceptoApi(request, rtMk.headers, `C1${marcaLocal}`.slice(0, 20), `Concepto 1 ${marcaLocal}`);
    const c2 = await crearConceptoApi(request, rtMk.headers, `C2${marcaLocal}`.slice(0, 20), `Concepto 2 ${marcaLocal}`);
    const c3 = await crearConceptoApi(request, rtMk.headers, `C3${marcaLocal}`.slice(0, 20), `Concepto 3 ${marcaLocal}`);

    const politica = await crearPoliticaRetencionApi(request, rtMk.headers, mp, {
      codigo: `P${marca()}`.slice(0, 20),
      nombre: `Política multi-regla ${marca()}`,
      reglas: [
        { orden: 1, concept_id: c1.id, tasa: "5" },
        { orden: 2, concept_id: c2.id, tasa: "2" },
        { orden: 3, concept_id: c3.id, tasa: "1" },
      ],
    });
    await activarPoliticaRetencionApi(request, rtMk.headers, politica.id, politica.version);

    const liquidacion = await calcularLiquidacionApi(
      request,
      rtMk.headers,
      pago.id,
      politica.id,
      [c1.codigo, c2.codigo, c3.codigo],
      { nombre: "Proveedor E2E S.A.", identificacion_fiscal: "J-12345678-9", tipo_persona: "JURIDICA" },
    );

    expect(liquidacion.total_retenido).toBe("8.00");
    expect(liquidacion.neto).toBe("92.00");
    expect(liquidacion.lineas).toHaveLength(3);
    for (const linea of liquidacion.lineas) {
      expect(linea.aplica).toBe(true);
    }

    const detalle = (await detallePagoApi(request, rtMk.headers, pago.id)) as {
      retenciones: { total_retenido: string; neto: string; definitivo: boolean };
    };
    expect(detalle.retenciones.total_retenido).toBe("8.00");
    expect(detalle.retenciones.neto).toBe("92.00");
    expect(detalle.retenciones.definitivo).toBe(false);
  });

  test("TRE05-E2E-03 · umbral", async ({ request }) => {
    test.setTimeout(600_000);

    const admin = await sesionApi("admintenant", { tenant: TENANT });
    const mp = await prepararMundoPagos(request, ["100.00", "200.00"]);
    const rtMk = await crearUsuario(request, admin.headers, [
      "organization:view",
      "gobierno_pagos:view",
      "gobierno_ordenes_pago:view",
      "gobierno_retenciones:view",
      "gobierno_retenciones:manage",
      "gobierno_retenciones:calculate",
      "gobierno_retenciones:policy",
    ], mp.m.mundo.companyId);
    const orden1 = await ordenEmitidaApi(request, mp.m, 0, "100.00");
    const orden2 = await ordenEmitidaApi(request, mp.m, 1, "200.00");
    const medio = await medioApi(request, mp);
    const politicaPago = await politicaPagoApi(request, mp, [medio.id]);
    const pago1 = await pagoApi(request, mp, orden1.id, politicaPago.id, medio.id, "100.00");
    const pago2 = await pagoApi(request, mp, orden2.id, politicaPago.id, medio.id, "200.00");

    const marcaLocal = marca();
    const concepto = await crearConceptoApi(request, rtMk.headers, `CU${marcaLocal}`.slice(0, 20), `Concepto umbral ${marcaLocal}`);

    const politica = await crearPoliticaRetencionApi(request, rtMk.headers, mp, {
      codigo: `P${marca()}`.slice(0, 20),
      nombre: `Política umbral ${marca()}`,
      reglas: [
        {
          orden: 1,
          concept_id: concepto.id,
          tasa: "5",
          umbral_tipo: "MONTO",
          umbral_monto: "150",
        },
      ],
    });
    await activarPoliticaRetencionApi(request, rtMk.headers, politica.id, politica.version);

    const liquidacion1 = await calcularLiquidacionApi(
      request,
      rtMk.headers,
      pago1.id,
      politica.id,
      [concepto.codigo],
      { nombre: "Proveedor E2E S.A.", identificacion_fiscal: "J-12345678-9", tipo_persona: "JURIDICA" },
    );

    expect(liquidacion1.total_retenido).toBe("0.00");
    expect(liquidacion1.neto).toBe("100.00");
    expect(liquidacion1.lineas[0].aplica).toBe(false);
    expect(liquidacion1.lineas[0].motivo_no_aplica).toBe("UMBRAL");

    const liquidacion2 = await calcularLiquidacionApi(
      request,
      rtMk.headers,
      pago2.id,
      politica.id,
      [concepto.codigo],
      { nombre: "Proveedor E2E S.A.", identificacion_fiscal: "J-12345678-9", tipo_persona: "JURIDICA" },
    );

    expect(liquidacion2.total_retenido).toBe("10.00");
    expect(liquidacion2.neto).toBe("190.00");
    expect(liquidacion2.lineas[0].aplica).toBe(true);
  });

  test("TRE05-E2E-04 · exclusión", async ({ request }) => {
    test.setTimeout(600_000);

    const admin = await sesionApi("admintenant", { tenant: TENANT });
    const mp = await prepararMundoPagos(request, ["100.00"]);
    const rtMk = await crearUsuario(request, admin.headers, [
      "organization:view",
      "gobierno_pagos:view",
      "gobierno_ordenes_pago:view",
      "gobierno_retenciones:view",
      "gobierno_retenciones:manage",
      "gobierno_retenciones:calculate",
      "gobierno_retenciones:policy",
    ], mp.m.mundo.companyId);
    const orden = await ordenEmitidaApi(request, mp.m, 0, "100.00");
    const medio = await medioApi(request, mp);
    const politicaPago = await politicaPagoApi(request, mp, [medio.id]);
    const pago = await pagoApi(request, mp, orden.id, politicaPago.id, medio.id, "100.00");

    const marcaLocal = marca();
    const condicion = await crearCondicionApi(request, rtMk.headers, `X${marcaLocal}`.slice(0, 20), `Condición ${marcaLocal}`);
    const conceptoA = await crearConceptoApi(request, rtMk.headers, `CA${marcaLocal}`.slice(0, 20), `Concepto A ${marcaLocal}`);
    const conceptoB = await crearConceptoApi(request, rtMk.headers, `CB${marcaLocal}`.slice(0, 20), `Concepto B ${marcaLocal}`);

    const politica = await crearPoliticaRetencionApi(request, rtMk.headers, mp, {
      codigo: `P${marca()}`.slice(0, 20),
      nombre: `Política exclusión ${marca()}`,
      reglas: [
        { orden: 1, concept_id: conceptoA.id, tasa: "5", exclusiones: [condicion.codigo] },
        { orden: 2, concept_id: conceptoB.id, tasa: "2" },
      ],
    });
    await activarPoliticaRetencionApi(request, rtMk.headers, politica.id, politica.version);

    const liquidacion = await calcularLiquidacionApi(
      request,
      rtMk.headers,
      pago.id,
      politica.id,
      [conceptoA.codigo, conceptoB.codigo],
      {
        nombre: "Proveedor E2E S.A.",
        identificacion_fiscal: "J-12345678-9",
        tipo_persona: "JURIDICA",
        condiciones: [condicion.codigo],
      },
    );

    expect(liquidacion.total_retenido).toBe("2.00");
    expect(liquidacion.neto).toBe("98.00");

    const lineaA = liquidacion.lineas.find((l) => l.concepto_codigo === conceptoA.codigo);
    const lineaB = liquidacion.lineas.find((l) => l.concepto_codigo === conceptoB.codigo);

    expect(lineaA?.aplica).toBe(false);
    expect(lineaA?.motivo_no_aplica).toBe("EXCLUSION");
    expect(lineaB?.aplica).toBe(true);
    expect(lineaB?.monto_aprobado).toBe("2.00");
  });

  test("TRE05-E2E-05 · versión congelada", async ({ request }) => {
    test.setTimeout(600_000);

    const admin = await sesionApi("admintenant", { tenant: TENANT });
    const mp = await prepararMundoPagos(request, ["100.00", "100.00"]);
    const rtMk = await crearUsuario(request, admin.headers, [
      "organization:view",
      "gobierno_pagos:view",
      "gobierno_ordenes_pago:view",
      "gobierno_retenciones:view",
      "gobierno_retenciones:manage",
      "gobierno_retenciones:calculate",
      "gobierno_retenciones:policy",
    ], mp.m.mundo.companyId);
    const orden1 = await ordenEmitidaApi(request, mp.m, 0, "100.00");
    const orden2 = await ordenEmitidaApi(request, mp.m, 1, "100.00");
    const medio = await medioApi(request, mp);
    const politicaPago = await politicaPagoApi(request, mp, [medio.id]);
    const pago1 = await pagoApi(request, mp, orden1.id, politicaPago.id, medio.id, "100.00");
    const pago2 = await pagoApi(request, mp, orden2.id, politicaPago.id, medio.id, "100.00");

    const marcaLocal = marca();
    const concepto = await crearConceptoApi(request, rtMk.headers, `CV${marcaLocal}`.slice(0, 20), `Concepto versión ${marcaLocal}`);

    const politicaV1 = await crearPoliticaRetencionApi(request, rtMk.headers, mp, {
      codigo: `P${marca()}`.slice(0, 20),
      nombre: `Política versión ${marca()}`,
      reglas: [{ orden: 1, concept_id: concepto.id, tasa: "5" }],
    });
    await activarPoliticaRetencionApi(request, rtMk.headers, politicaV1.id, politicaV1.version);

    const liquidacion1 = await calcularLiquidacionApi(
      request,
      rtMk.headers,
      pago1.id,
      politicaV1.id,
      [concepto.codigo],
      { nombre: "Proveedor E2E S.A.", identificacion_fiscal: "J-12345678-9", tipo_persona: "JURIDICA" },
    );

    expect(liquidacion1.total_retenido).toBe("5.00");
    expect(liquidacion1.policy_numero_version).toBe(1);

    const politicaV2 = await nuevaVersionPoliticaRetencionApi(request, rtMk.headers, politicaV1.id);
    expect(politicaV2.numero_version).toBe(2);
    expect(politicaV2.estado).toBe("BORRADOR");
    expect(politicaV2.reglas).toHaveLength(1);

    const politicaV2Actualizada = await actualizarPoliticaRetencionApi(request, rtMk.headers, politicaV2.id, politicaV2.version, [
      { orden: 1, concept_id: concepto.id, tasa: "10" },
    ]);
    await activarPoliticaRetencionApi(request, rtMk.headers, politicaV2.id, politicaV2Actualizada.version);

    const get1 = await getLiquidacionApi(request, rtMk.headers, pago1.id);
    expect(get1.liquidacion.total_retenido).toBe("5.00");
    expect(get1.liquidacion.policy_numero_version).toBe(1);

    const liquidacion2 = await calcularLiquidacionApi(
      request,
      rtMk.headers,
      pago2.id,
      politicaV2.id,
      [concepto.codigo],
      { nombre: "Proveedor E2E S.A.", identificacion_fiscal: "J-12345678-9", tipo_persona: "JURIDICA" },
    );

    expect(liquidacion2.total_retenido).toBe("10.00");
    expect(liquidacion2.policy_numero_version).toBe(2);

    const politicaV1Get = await getPoliticaRetencionApi(request, rtMk.headers, politicaV1.id);
    expect(politicaV1Get.estado).toBe("CERRADA");
  });

  test("TRE05-E2E-06 · comprobante", async ({ request }) => {
    test.setTimeout(600_000);

    const admin = await sesionApi("admintenant", { tenant: TENANT });
    const mp = await prepararMundoPagos(request, ["100.00"]);
    const rtMk = await crearUsuario(request, admin.headers, [
      "organization:view",
      "gobierno_pagos:view",
      "gobierno_ordenes_pago:view",
      "gobierno_retenciones:view",
      "gobierno_retenciones:manage",
      "gobierno_retenciones:calculate",
      "gobierno_retenciones:policy",
    ], mp.m.mundo.companyId);
    const rtCk = await crearUsuario(request, admin.headers, [
      "organization:view",
      "gobierno_pagos:view",
      "gobierno_ordenes_pago:view",
      "gobierno_retenciones:view",
      "gobierno_retenciones:approve",
      "gobierno_retenciones:cancel",
    ], mp.m.mundo.companyId);
    const orden = await ordenEmitidaApi(request, mp.m, 0, "100.00");
    const medio = await medioApi(request, mp);
    const politicaPago = await politicaPagoApi(request, mp, [medio.id]);
    const pago = await pagoApi(request, mp, orden.id, politicaPago.id, medio.id, "100.00");

    const marcaLocal = marca();
    const concepto = await crearConceptoApi(request, rtMk.headers, `CC${marcaLocal}`.slice(0, 20), `Concepto comprobante ${marcaLocal}`);

    const politica = await crearPoliticaRetencionApi(request, rtMk.headers, mp, {
      codigo: `P${marca()}`.slice(0, 20),
      nombre: `Política comprobante ${marca()}`,
      reglas: [
        {
          orden: 1,
          concept_id: concepto.id,
          tasa: "5",
          exige_comprobante: true,
        },
      ],
    });
    await activarPoliticaRetencionApi(request, rtMk.headers, politica.id, politica.version);

    const liquidacion = await calcularLiquidacionApi(
      request,
      rtMk.headers,
      pago.id,
      politica.id,
      [concepto.codigo],
      { nombre: "Proveedor E2E S.A.", identificacion_fiscal: "J-12345678-9", tipo_persona: "JURIDICA" },
    );

    expect(liquidacion.total_retenido).toBe("5.00");
    expect(liquidacion.estado).toBe("CALCULADA");

    const actualPago = (await detallePagoApi(request, mp.m.mundo.headers, pago.id)) as { version: number };

    const envio = await enviarApi(request, mp.m.mundo.headers, { id: pago.id, version: actualPago.version });
    expect(envio.status(), await envio.text()).toBe(200);

    const auto = await aprobarApi(request, mp.checker.headers, { id: pago.id, version: 0 }, mp.cargoPagarId);
    expect(auto.status()).toBe(200);

    const registro409 = await registrarApi(request, mp.m.mundo.headers, { id: pago.id, version: pago.version + 1 }, `REF-${marca()}`);
    expect(registro409.status()).toBe(409);
    expect(((await registro409.json()) as { code: string }).code).toBe("GOV_WITHHOLDING_PENDING_APPROVAL");

    const liqActual = await getLiquidacionApi(request, rtMk.headers, pago.id);
    const aprobada = await aprobarLiquidacionApi(request, rtCk.headers, liqActual.liquidacion.id, liqActual.liquidacion.version, mp.cargoPagarId);
    expect(aprobada.estado).toBe("APROBADA");

    const registroOk = await registrarApi(request, mp.m.mundo.headers, { id: pago.id, version: pago.version + 2 }, `REF-${marca()}`);
    expect(registroOk.status(), await registroOk.text()).toBe(200);

    const comprobantes1 = await getComprobantesApi(request, rtMk.headers, pago.id);
    expect(comprobantes1).toHaveLength(1);
    expect(comprobantes1[0].estado).toBe("EMITIDO");
    expect(comprobantes1[0].concepto_codigo).toBe(concepto.codigo);

    const pdfResp = await request.get(`${API}/gobierno/tesoreria/retenciones/comprobantes/${comprobantes1[0].id}/pdf`, {
      headers: rtMk.headers,
    });
    expect(pdfResp.status()).toBe(200);
    expect(pdfResp.headers()["content-type"]).toContain("application/pdf");

    await anularComprobanteApi(request, rtCk.headers, comprobantes1[0].id, "Motivo de anulación E2E", {
      nombre: "Proveedor Corregido S.A.",
      identificacion_fiscal: "J-12345678-9",
    });

    const comprobantes2 = await getComprobantesApi(request, rtMk.headers, pago.id);
    expect(comprobantes2).toHaveLength(2);

    const anulado = comprobantes2.find((c) => c.estado === "ANULADO");
    const emitido = comprobantes2.find((c) => c.estado === "EMITIDO");

    expect(anulado).toBeDefined();
    expect(anulado?.id).toBe(comprobantes1[0].id);
    expect(emitido).toBeDefined();
    expect(emitido?.beneficiario_nombre).toBe("Proveedor Corregido S.A.");
  });
});
