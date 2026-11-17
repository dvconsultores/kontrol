import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "./helpers/sesion";
import {
  ANIO,
  API,
  TENANT,
  adjuntarDocumentoApi,
  cerrarNotificaciones,
  crearTipoDocumental,
  crearUsuario,
  entrarEnGobierno,
  prepararMundo,
  enteActivo,
  estructuraVigenteApi,
  RESPONSABLE_ESTRUCTURA,
} from "./helpers/gobierno";
import { sesionApi } from "./helpers/sesion";
import type { Page } from "@playwright/test";

const WCAG = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"];

async function sinViolacionesSerias(page: Page, contexto: string): Promise<void> {
  const resultados = await new AxeBuilder({ page })
    .include("main")
    .withTags(WCAG)
    .analyze();

  const serias = resultados.violations.filter((v) =>
    ["critical", "serious"].includes(v.impact ?? ""),
  );

  expect(
    serias.map((v) => ({ id: v.id, help: v.help })),
    contexto,
  ).toEqual([]);

  if (page.viewportSize()?.width === 320) {
    const sinDesbordamiento = await page.evaluate(
      () => document.documentElement.scrollWidth <= document.documentElement.clientWidth,
    );
    expect(sinDesbordamiento, contexto).toBe(true);
  }
}

function hoyCaracas(): string {
  return new Intl.DateTimeFormat("en-CA", { timeZone: "America/Caracas" }).format(
    new Date(),
  );
}

test.describe("Causado presupuestario", () => {
  test("BUD-09: causado parcial con evidencia, formalización, historia, exceso bloqueado, aislamiento y responsive", async ({ page, request }) => {
    test.setTimeout(300_000);

    const PERMISOS = [
      ...RESPONSABLE_ESTRUCTURA,
      "gobierno_cargos:view",
      "gobierno_cargos:edit",
      "gobierno_cargos:publish",
      "documentos:view",
      "documentos:create",
      "documentos:upload",
      "documentos:link",
      "documentos:download",
      "documentos:manage_types",
      "gobierno_presupuesto:view",
      "gobierno_presupuesto:manage",
      "gobierno_presupuesto:approve",
      "gobierno_presupuesto:commit",
      "gobierno_presupuesto:cause",
      "gobierno_presupuesto:cause_policy",
    ];

    const mundo = await prepararMundo(request, PERMISOS);
    const admin = await sesionApi("admintenant", { tenant: TENANT });
    const certificador = await crearUsuario(
      request,
      admin.headers,
      ["organization:view", "gobierno_presupuesto:view", "gobierno_presupuesto:certify"],
      mundo.companyId,
    );
    const tipo = await crearTipoDocumental(request, mundo.headers, mundo.companyId);
    const anio = ANIO;

    await enteActivo(request, mundo.headers, mundo.companyId, tipo.id);
    const { despId } = await estructuraVigenteApi(request, mundo.headers, mundo.companyId, tipo.id, anio);

    const cargoPresResp = await request.post(`${API}/gobierno/estructuras/${anio}/cargos`, {
      headers: mundo.headers,
      data: {
        codigo: "C-PRES",
        denominacion: "Director de Presupuesto",
        unidad_id: despId,
        vigente_desde: `${anio}-01-01`,
      },
    });
    expect(cargoPresResp.status()).toBe(201);
    const cargoPres = await cargoPresResp.json();

    const competenciaPresResp = await request.post(
      `${API}/gobierno/estructuras/${anio}/cargos/${cargoPres.id}/competencias`,
      {
        headers: { ...mundo.headers, "If-Match": '"1"' },
        data: {
          accion: "FIRMAR",
          materia: "PRESUPUESTO",
          tipo_limite: "SIN_LIMITE",
          monto: null,
          moneda: null,
        },
      },
    );
    expect(competenciaPresResp.status()).toBe(201);

    await adjuntarDocumentoApi(
      request,
      mundo.headers,
      mundo.companyId,
      tipo.id,
      "GovernmentPosition",
      cargoPres.id,
    );

    const activarCargoPresResp = await request.post(
      `${API}/gobierno/estructuras/${anio}/cargos/${cargoPres.id}/activar`,
      {
        headers: { ...mundo.headers, "If-Match": '"2"' },
      },
    );
    expect(activarCargoPresResp.status()).toBe(200);

    const cargoAdmResp = await request.post(`${API}/gobierno/estructuras/${anio}/cargos`, {
      headers: mundo.headers,
      data: {
        codigo: "C-ADM",
        denominacion: "Director de Administración",
        unidad_id: despId,
        vigente_desde: `${anio}-01-01`,
      },
    });
    expect(cargoAdmResp.status()).toBe(201);
    const cargoAdm = await cargoAdmResp.json();

    const competenciaAdmResp = await request.post(
      `${API}/gobierno/estructuras/${anio}/cargos/${cargoAdm.id}/competencias`,
      {
        headers: { ...mundo.headers, "If-Match": '"1"' },
        data: {
          accion: "COMPROMETER",
          materia: "PRESUPUESTO",
          tipo_limite: "SIN_LIMITE",
          monto: null,
          moneda: null,
        },
      },
    );
    expect(competenciaAdmResp.status()).toBe(201);

    await adjuntarDocumentoApi(
      request,
      mundo.headers,
      mundo.companyId,
      tipo.id,
      "GovernmentPosition",
      cargoAdm.id,
    );

    const activarCargoAdmResp = await request.post(
      `${API}/gobierno/estructuras/${anio}/cargos/${cargoAdm.id}/activar`,
      {
        headers: { ...mundo.headers, "If-Match": '"2"' },
      },
    );
    expect(activarCargoAdmResp.status()).toBe(200);

    const cargoCausResp = await request.post(`${API}/gobierno/estructuras/${anio}/cargos`, {
      headers: mundo.headers,
      data: {
        codigo: "C-CAUS",
        denominacion: "Jefe de Causado",
        unidad_id: despId,
        vigente_desde: `${anio}-01-01`,
      },
    });
    expect(cargoCausResp.status()).toBe(201);
    const cargoCaus = await cargoCausResp.json();

    const competenciaCausResp = await request.post(
      `${API}/gobierno/estructuras/${anio}/cargos/${cargoCaus.id}/competencias`,
      {
        headers: { ...mundo.headers, "If-Match": '"1"' },
        data: {
          accion: "CAUSAR",
          materia: "PRESUPUESTO",
          tipo_limite: "SIN_LIMITE",
          monto: null,
          moneda: null,
        },
      },
    );
    expect(competenciaCausResp.status()).toBe(201);

    await adjuntarDocumentoApi(
      request,
      mundo.headers,
      mundo.companyId,
      tipo.id,
      "GovernmentPosition",
      cargoCaus.id,
    );

    const activarCargoCausResp = await request.post(
      `${API}/gobierno/estructuras/${anio}/cargos/${cargoCaus.id}/activar`,
      {
        headers: { ...mundo.headers, "If-Match": '"2"' },
      },
    );
    expect(activarCargoCausResp.status()).toBe(200);

    const crearEjercicioResp = await request.post(`${API}/gobierno/presupuesto/ejercicios`, {
      headers: mundo.headers,
      data: { anio },
    });
    expect(crearEjercicioResp.status()).toBe(201);
    const ejercicio = await crearEjercicioResp.json();
    let version = ejercicio.version;

    const nivelesResp = await request.put(`${API}/gobierno/presupuesto/ejercicios/${ejercicio.id}/niveles`, {
      headers: { ...mundo.headers, "If-Match": String(version) },
      data: { niveles: [{ nombre: "Sector" }, { nombre: "Programa" }] },
    });
    expect(nivelesResp.status()).toBe(200);
    version = (await nivelesResp.json()).version;

    const cat01Resp = await request.post(`${API}/gobierno/presupuesto/ejercicios/${ejercicio.id}/categorias`, {
      headers: { ...mundo.headers, "If-Match": String(version) },
      data: {
        nivel_orden: 1,
        parent_id: null,
        codigo: "01",
        denominacion: "Sector salud",
      },
    });
    expect(cat01Resp.status()).toBe(201);
    const detalleCat01 = await cat01Resp.json();
    version = detalleCat01.version;
    const cat01 = detalleCat01.categorias.find((c: { codigo_completo: string }) => c.codigo_completo === "01");

    const cat02Resp = await request.post(`${API}/gobierno/presupuesto/ejercicios/${ejercicio.id}/categorias`, {
      headers: { ...mundo.headers, "If-Match": String(version) },
      data: {
        nivel_orden: 2,
        parent_id: cat01.id,
        codigo: "02",
        denominacion: "Atención primaria",
      },
    });
    expect(cat02Resp.status()).toBe(201);
    const detalleCat02 = await cat02Resp.json();
    version = detalleCat02.version;
    const cat02 = detalleCat02.categorias.find(
      (c: { codigo_completo: string }) => c.codigo_completo === "01.02",
    );

    await adjuntarDocumentoApi(request, mundo.headers, mundo.companyId, tipo.id, "GovernmentBudgetYear", ejercicio.id);
    await adjuntarDocumentoApi(request, mundo.headers, mundo.companyId, tipo.id, "GovernmentBudgetYear", ejercicio.id);
    await adjuntarDocumentoApi(request, mundo.headers, mundo.companyId, tipo.id, "GovernmentBudgetYear", ejercicio.id);

    const documentosResp = await request.get(`${API}/documentos/por-recurso/GovernmentBudgetYear/${ejercicio.id}`, { headers: mundo.headers });
    expect(documentosResp.status()).toBe(200);
    const documentos = (await documentosResp.json()) as Array<{ id: string }>;
    expect(documentos.length).toBeGreaterThanOrEqual(3);

    const clasificadorResp = await request.put(`${API}/gobierno/presupuesto/ejercicios/${ejercicio.id}/clasificador`, {
      headers: { ...mundo.headers, "If-Match": String(version) },
      data: {
        edicion: "Clasificador del ente",
        procedencia: "Copia entregada por la Dirección de Presupuesto",
        documento_id: documentos[0].id,
      },
    });
    expect(clasificadorResp.status()).toBe(200);
    version = (await clasificadorResp.json()).version;

    const partida301Resp = await request.post(`${API}/gobierno/presupuesto/ejercicios/${ejercicio.id}/clasificador/partidas`, {
      headers: { ...mundo.headers, "If-Match": String(version) },
      data: {
        tipo: "RECURSO",
        codigo: "301",
        denominacion: "Ingresos propios",
        nivel: 1,
        codigo_padre: null,
        vigente_desde: null,
        vigente_hasta: null,
      },
    });
    expect(partida301Resp.status()).toBe(201);
    version = (await partida301Resp.json()).version;

    const partida401Resp = await request.post(`${API}/gobierno/presupuesto/ejercicios/${ejercicio.id}/clasificador/partidas`, {
      headers: { ...mundo.headers, "If-Match": String(version) },
      data: {
        tipo: "EGRESO",
        codigo: "401",
        denominacion: "Gasto corriente",
        nivel: 1,
        codigo_padre: null,
        vigente_desde: null,
        vigente_hasta: null,
      },
    });
    expect(partida401Resp.status()).toBe(201);
    version = (await partida401Resp.json()).version;

    const partida40101Resp = await request.post(`${API}/gobierno/presupuesto/ejercicios/${ejercicio.id}/clasificador/partidas`, {
      headers: { ...mundo.headers, "If-Match": String(version) },
      data: {
        tipo: "EGRESO",
        codigo: "401.01",
        denominacion: "Servicios personales",
        nivel: 2,
        codigo_padre: "401",
        vigente_desde: null,
        vigente_hasta: null,
      },
    });
    expect(partida40101Resp.status()).toBe(201);
    version = (await partida40101Resp.json()).version;

    const fuentesResp = await request.post(`${API}/gobierno/presupuesto/ejercicios/${ejercicio.id}/fuentes`, {
      headers: { ...mundo.headers, "If-Match": String(version) },
      data: {
        codigo: "F01",
        denominacion: "Ingresos propios",
        procedencia: "Ordenanza municipal de ingresos del ente",
      },
    });
    expect(fuentesResp.status()).toBe(201);
    const fuentesDatos = await fuentesResp.json();
    version = fuentesDatos.version;
    const fuenteF01 = fuentesDatos.items.find((f: { codigo: string }) => f.codigo === "F01");

    const partidasResp = await request.get(`${API}/gobierno/presupuesto/ejercicios/${ejercicio.id}/clasificador/partidas`, {
      headers: mundo.headers,
    });
    expect(partidasResp.status()).toBe(200);
    const partidas = (await partidasResp.json()) as { items: Array<{ id: string; codigo: string }> };
    const partida301 = partidas.items.find((p) => p.codigo === "301");
    const partida401 = partidas.items.find((p) => p.codigo === "401");
    const partida40101 = partidas.items.find((p) => p.codigo === "401.01");
    expect(partida301).toBeTruthy();
    expect(partida401).toBeTruthy();
    expect(partida40101).toBeTruthy();

    const ingresoResp = await request.post(
      `${API}/gobierno/presupuesto/ejercicios/${ejercicio.id}/presupuesto-aprobado/ingresos`,
      {
        headers: { ...mundo.headers, "If-Match": String(version) },
        data: {
          partida_id: partida301?.id,
          monto: "5000.00",
        },
      },
    );
    expect(ingresoResp.status()).toBe(201);
    version = (await ingresoResp.json()).version;

    const creditoResp = await request.post(
      `${API}/gobierno/presupuesto/ejercicios/${ejercicio.id}/presupuesto-aprobado/creditos`,
      {
        headers: { ...mundo.headers, "If-Match": String(version) },
        data: {
          categoria_id: cat02.id,
          partida_id: partida40101?.id,
          fuente_id: fuenteF01.id,
          monto: "1000.00",
        },
      },
    );
    expect(creditoResp.status()).toBe(201);
    const creditosDatos = await creditoResp.json();
    version = creditosDatos.version;
    const creditoId = (creditosDatos as { creditos: Array<{ id: string }> }).creditos[0].id;

    const ejercicioActualResp = await request.get(`${API}/gobierno/presupuesto/ejercicios/${ejercicio.id}`, {
      headers: mundo.headers,
    });
    expect(ejercicioActualResp.status()).toBe(200);
    const ejercicioActual = await ejercicioActualResp.json();

    const aprobarResp = await request.post(
      `${API}/gobierno/presupuesto/ejercicios/${ejercicio.id}/aprobar`,
      {
        headers: { ...mundo.headers, "If-Match": String(ejercicioActual.version) },
        data: {
          referencia: "Gaceta Municipal Extraordinaria N.º 9",
          fecha: hoyCaracas(),
          documento_id: documentos[1].id,
        },
      },
    );
    expect(aprobarResp.status()).toBe(200);

    const cdpResp = await request.post(
      `${API}/gobierno/presupuesto/ejercicios/${ejercicio.id}/certificaciones`,
      {
        headers: certificador.headers,
        data: {
          credito_id: creditoId,
          monto: "300.00",
          concepto: "Adquisición de material médico",
          expediente_referencia: "EXP-PRES-2026-001",
          firmante_cargo_id: cargoPres.id,
        },
      },
    );
    expect(cdpResp.status()).toBe(201);
    const cdp = await cdpResp.json();

    const compromisoResp = await request.post(
      `${API}/gobierno/presupuesto/ejercicios/${ejercicio.id}/compromisos`,
      {
        headers: mundo.headers,
        data: {
          concepto: "Orden de servicio de mantenimiento",
          autoridad_cargo_id: cargoAdm.id,
          soporte_documento_id: documentos[2].id,
          lineas: [{ certificado_id: cdp.id, monto: "200.00" }],
        },
      },
    );
    expect(compromisoResp.status()).toBe(201);
    const compromiso = await compromisoResp.json();

    const politicaResp = await request.post(
      `${API}/gobierno/presupuesto/politicas-causado`,
      {
        headers: mundo.headers,
        data: {
          codigo: "POL-SERV",
          tipo_gasto: "SERVICIOS",
          nombre: "Servicios contratados",
          disparador: "DOCUMENTARY",
          vigente_desde: `${anio}-01-01`,
          fundamento: "Política institucional de causado de servicios",
          documentos: [{ document_type_id: tipo.id, obligatorio: true, etapa: "FORMALIZACION" }],
        },
      },
    );
    expect(politicaResp.status()).toBe(201);
    const politica = await politicaResp.json();

    const activarPoliticaResp = await request.post(
      `${API}/gobierno/presupuesto/politicas-causado/${politica.id}/activar`,
      {
        headers: { ...mundo.headers, "If-Match": String(politica.version) },
        data: { fundamento: "Activación aprobada por la Dirección de Presupuesto del ente" },
      },
    );
    expect(activarPoliticaResp.status()).toBe(200);

    await entrarEnGobierno(page, mundo.username, mundo.codigo, "/gobierno/presupuesto/causados");
    await cerrarNotificaciones(page);

    await expect(page.getByRole("heading", { name: "Causados", exact: true })).toBeVisible();
    await expect(page.getByText("Aún no hay causados en este ejercicio")).toBeVisible();

    await page.getByRole("link", { name: "Nuevo causado" }).click();
    await expect(page.getByRole("heading", { name: "Nuevo causado", exact: true })).toBeVisible();

    await page.getByRole("combobox", { name: "Compromiso", exact: true }).selectOption(compromiso.id);
    await expect(page.getByLabel("Monto a causar Servicios personales")).toBeVisible();

    await page.getByLabel("Monto a causar Servicios personales").fill("250.00");
    await expect(page.getByText("Supera el pendiente de la línea")).toBeVisible();
    await expect(page.getByRole("button", { name: "Guardar borrador" })).toBeDisabled();

    await page.getByLabel("Monto a causar Servicios personales").fill("120.00");
    await expect(page.getByRole("cell", { name: "80.00", exact: true })).toBeVisible();

    await page.getByRole("combobox", { name: "Política", exact: true }).selectOption(politica.id);
    await expect(page.getByText("Se exige", { exact: true })).toBeVisible();
    await expect(page.getByRole("listitem").filter({ hasText: "Solo documentos exigidos" })).toBeVisible();

    const evidencias = page.getByRole("region", { name: "Evidencias" });
    await evidencias.getByRole("checkbox").first().check();

    await page.getByRole("textbox", { name: "Concepto (obligatorio)" }).fill("Mantenimiento preventivo del mes");
    await page.getByRole("combobox", { name: "Autoridad que formalizará" }).selectOption({ label: "Jefe de Causado" });

    const guardarRespPromise = page.waitForResponse(
      (resp) =>
        resp.request().method() === "POST" &&
        new URL(resp.url()).pathname.endsWith(`/ejercicios/${ejercicio.id}/causados`),
    );
    await page.getByRole("button", { name: "Guardar borrador" }).click();
    const guardarResp = await guardarRespPromise;
    expect(guardarResp.status()).toBe(201);

    await expect(page.getByRole("heading", { name: "Borrador de causado" })).toBeVisible();
    await expect(page.getByText(/✗ Pendiente/)).toHaveCount(0);

    await page.getByRole("button", { name: "Formalizar" }).click();
    const dialog = page.getByRole("dialog");
    await expect(dialog).toBeVisible();
    await expect(dialog.getByText("Esta acción no se puede deshacer")).toBeVisible();

    const formalizarRespPromise = page.waitForResponse(
      (resp) =>
        resp.request().method() === "POST" &&
        new URL(resp.url()).pathname.endsWith("/formalizar"),
    );
    await dialog.getByRole("button", { name: "Formalizar" }).click();
    const formalizarResp = await formalizarRespPromise;
    expect(formalizarResp.status()).toBe(200);
    const formalizado = await formalizarResp.json();

    await expect(page.getByRole("heading", { name: formalizado.codigo })).toBeVisible();
    await expect(page.getByText("Formalizado", { exact: true })).toBeVisible();
    await expect(page.getByText(/Pendiente de orden de pago: 120\.00/)).toBeVisible();
    await expect(page.getByRole("region", { name: "Historia" }).getByText("Sin eventos")).toHaveCount(0);

    await page.goto("/gobierno/presupuesto/causados");
    await expect(page.getByRole("link", { name: formalizado.codigo, exact: true })).toBeVisible();
    await expect(page.getByRole("cell", { name: "Formalizado", exact: true })).toBeVisible();

    const opcionesResp = await request.get(
      `${API}/gobierno/presupuesto/ejercicios/${ejercicio.id}/causados/opciones?compromiso_id=${compromiso.id}`,
      { headers: mundo.headers },
    );
    expect(opcionesResp.status()).toBe(200);
    const opciones = await opcionesResp.json();
    const lineaCompromisoId = opciones.compromisos[0].lineas[0].id;

    const excesoServidorResp = await request.post(
      `${API}/gobierno/presupuesto/ejercicios/${ejercicio.id}/causados`,
      {
        headers: mundo.headers,
        data: {
          compromiso_id: compromiso.id,
          politica_id: politica.id,
          fecha_efectiva: hoyCaracas(),
          concepto: "Segundo causado que excede el saldo",
          beneficiario: null,
          autoridad_cargo_id: cargoCaus.id,
          lineas: [{ linea_compromiso_id: lineaCompromisoId, monto: "100.00" }],
          evidencias: [],
        },
      },
    );
    expect(excesoServidorResp.status()).toBe(422);
    const excesoServidor = await excesoServidorResp.json();
    expect(excesoServidor.code).toBe("GOV_BUDGET_CAUSE_OVER_COMMITMENT");

    const otro = await prepararMundo(request, ["organization:view", "gobierno_presupuesto:view"]);
    const aislamientoResp = await request.get(
      `${API}/gobierno/presupuesto/causados/${formalizado.id}`,
      { headers: otro.headers },
    );
    expect(aislamientoResp.status()).toBe(404);

    for (const width of [1280, 390, 320]) {
      await page.setViewportSize({ width, height: 800 });
      await page.goto(`/gobierno/presupuesto/causados/${formalizado.id}`);
      await sinViolacionesSerias(page, `causado detalle ${width}`);
      await page.goto("/gobierno/presupuesto/causados");
      await sinViolacionesSerias(page, `causado listado ${width}`);
    }
  });
});
