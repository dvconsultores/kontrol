import fs from "node:fs/promises";
import AxeBuilder from "@axe-core/playwright";
import { expect, sesionApi, test } from "./helpers/sesion";
import type { APIRequestContext, Page } from "@playwright/test";
import {
  ANIO,
  API,
  RESPONSABLE_ESTRUCTURA,
  TENANT,
  adjuntarDocumentoApi,
  cargoVigenteApi,
  cerrarNotificaciones,
  crearTipoDocumental,
  crearUsuario,
  enteActivo,
  entrarEnGobierno,
  estructuraVigenteApi,
  prepararMundo,
} from "./helpers/gobierno";

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
  "documentos:view",
  "documentos:create",
  "gobierno_autoridad:view",
];

const WCAG = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"];

function hoyCaracas(): string {
  return new Intl.DateTimeFormat("en-CA", { timeZone: "America/Caracas" }).format(new Date());
}

function ddmmaaaa(iso: string): string {
  const [year, month, day] = iso.split("-");
  return `${day}/${month}/${year}`;
}

function sumarDias(fechaISO: string, dias: number): string {
  const [anio, mes, dia] = fechaISO.split("-").map(Number);
  const fecha = new Date(Date.UTC(anio, mes - 1, dia + dias));
  return fecha.toISOString().slice(0, 10);
}

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

  if (page.viewportSize()?.width === 320 || page.viewportSize()?.width === 390) {
    const sinDesbordamiento = await page.evaluate(
      () => document.documentElement.scrollWidth <= document.documentElement.clientWidth,
    );
    expect(sinDesbordamiento, contexto).toBe(true);
  }
}

async function funcionarioApi(
  request: APIRequestContext,
  headers: Record<string, string>,
  nombre: string,
): Promise<{ id: string; nombre: string }> {
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
    hasta?: string;
    cargo_origen_id?: string;
    figura?: string;
    rendicion?: string;
    declara_delegable?: boolean;
    competencias?: Array<{ accion: string; materia: string }>;
  },
): Promise<{ id: string; version: number; codigo?: string }> {
  const resp = await request.post(`${API}/gobierno/ocupacion/asignaciones`, {
    headers,
    data: {
      funcionario_id: datos.funcionario_id,
      cargo_id: datos.cargo_id,
      figura: datos.figura ?? "TITULAR",
      acto_id: datos.acto_id,
      desde: datos.desde ?? hoyCaracas(),
      fundamento: datos.fundamento,
      cargo_origen_id: datos.cargo_origen_id ?? null,
      hasta: datos.hasta ?? null,
      rendicion: datos.rendicion ?? null,
      maxima_autoridad: false,
      autorizacion_especial: null,
      declara_delegable: datos.declara_delegable ?? false,
      competencias: datos.competencias ?? [],
    },
  });
  expect(resp.status(), await resp.text()).toBe(201);
  return resp.json();
}

async function activarAsignacionApi(
  request: APIRequestContext,
  headers: Record<string, string>,
  asignacion: { id: string; version: number },
): Promise<{ status: () => number; text: () => Promise<string>; json: () => Promise<Record<string, unknown>> }> {
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

async function prepararMundoAutoridadEfectiva(request: APIRequestContext) {
  const mundo = await prepararMundo(request, RESPONSABLE);
  const tipo = await crearTipoDocumental(request, mundo.headers, mundo.companyId);
  await enteActivo(request, mundo.headers, mundo.companyId, tipo.id);
  const estructura = await estructuraVigenteApi(request, mundo.headers, mundo.companyId, tipo.id, ANIO);

  const sello = Date.now();
  const codigoEmi = `EMI-EF`;
  const codigoDir = `DIR-EF`;
  const codigoJef = `JEF-EF`;
  const codigoSup = `SUP-EF`;
  const codigoAux = `AUX-EF`;

  const emi = await cargoVigenteApi(request, mundo.headers, mundo.companyId, tipo.id, ANIO, estructura.despId, codigoEmi);
  const dir = await cargoVigenteApi(request, mundo.headers, mundo.companyId, tipo.id, ANIO, estructura.despId, codigoDir);
  const jef = await cargoVigenteApi(request, mundo.headers, mundo.companyId, tipo.id, ANIO, estructura.da01Id, codigoJef);
  const sup = await cargoVigenteApi(request, mundo.headers, mundo.companyId, tipo.id, ANIO, estructura.despId, codigoSup);
  const aux = await cargoVigenteApi(request, mundo.headers, mundo.companyId, tipo.id, ANIO, estructura.da01Id, codigoAux);

  const luis = await funcionarioApi(request, mundo.headers, `Luis Efectivo ${sello}`);
  const ana = await funcionarioApi(request, mundo.headers, `Ana Efectiva ${sello}`);
  const rosa = await funcionarioApi(request, mundo.headers, `Rosa Suplente ${sello}`);

  const actoLuisTitular = await actoEmitidoApi(request, mundo, tipo.id, emi.id, `EF-LUIS-${sello}`);
  const actoAnaTitular = await actoEmitidoApi(request, mundo, tipo.id, emi.id, `EF-ANA-${sello}`);

  const asignacionLuis = await asignacionApi(request, mundo.headers, {
    funcionario_id: luis.id,
    cargo_id: jef.id,
    acto_id: actoLuisTitular.id,
    fundamento: "Titularidad de Luis en cargo delegado",
  });
  const asignacionAna = await asignacionApi(request, mundo.headers, {
    funcionario_id: ana.id,
    cargo_id: sup.id,
    acto_id: actoAnaTitular.id,
    fundamento: "Titularidad de Ana en cargo suplido",
  });

  const admin = await sesionApi("admintenant", { tenant: TENANT });
  const activador = await crearUsuario(
    request,
    admin.headers,
    ["organization:view", "gobierno_ocupacion:view", "gobierno_ocupacion:activate"],
    mundo.companyId,
  );

  const respLuis = await activarAsignacionApi(request, activador.headers, asignacionLuis);
  expect(respLuis.status(), await respLuis.text()).toBe(200);
  const respAna = await activarAsignacionApi(request, activador.headers, asignacionAna);
  expect(respAna.status(), await respAna.text()).toBe(200);

  return {
    mundo,
    tipoId: tipo.id,
    activador,
    emisorId: emi.id,
    dirId: dir.id,
    jefId: jef.id,
    supId: sup.id,
    auxId: aux.id,
    codigoDir,
    codigoJef,
    codigoSup,
    luis,
    ana,
    rosa,
  };
}

test.describe("Gobierno · Matriz de autoridad efectiva (ORG-07)", () => {
  test("ORG7-E2E-02 · autoridad efectiva, histórico y exportación", async ({ page, request }) => {
    test.setTimeout(480_000);

    const preparado = await prepararMundoAutoridadEfectiva(request);
    const { mundo, tipoId, activador, emisorId, dirId, jefId, supId, auxId, codigoDir, codigoJef, codigoSup, luis, ana, rosa } = preparado;

    const hoy = hoyCaracas();
    const manana = sumarDias(hoy, 1);
    const pasadoManana = sumarDias(hoy, 3);
    const finSuplencia = sumarDias(hoy, 2);
    const hoyFormateado = ddmmaaaa(hoy);

    let codigoAsignacionDelegacion = "";
    let numeroActoDelegacion = "";

    await test.step("1 Autoridad efectiva", async () => {
      await entrarEnGobierno(page, mundo.username, mundo.codigo, "/gobierno/autoridad");
      await cerrarNotificaciones(page);

      const filaDir = page
        .getByRole("row")
        .filter({ hasText: codigoDir });

      await expect(filaDir.filter({ hasText: "Sin ocupante" })).toBeVisible();
      await expect(filaDir.filter({ hasText: "Delegación de atribuciones" })).toHaveCount(0);

      const actoDelegacion = await actoEmitidoApi(
        request,
        mundo,
        tipoId,
        dirId,
        `EF-DELEG-${Date.now()}`,
      );

      numeroActoDelegacion = actoDelegacion.numero;

      const asignacionDelegacion = await asignacionApi(request, mundo.headers, {
        funcionario_id: luis.id,
        cargo_id: dirId,
        acto_id: actoDelegacion.id,
        fundamento: "Delegación de atribuciones de contrataciones",
        cargo_origen_id: jefId,
        figura: "DELEGACION_ATRIBUCIONES",
        rendicion: "Rinde cuentas de la gestión delegada",
        declara_delegable: true,
        competencias: [{ accion: "APROBAR", materia: "CONTRATACIONES" }],
      });

      codigoAsignacionDelegacion = asignacionDelegacion.codigo ?? "";

      const respDelegacion = await activarAsignacionApi(request, activador.headers, asignacionDelegacion);
      expect(respDelegacion.status(), await respDelegacion.text()).toBe(200);

      await page.reload();
      await cerrarNotificaciones(page);

      const filaDelegada = filaDir.filter({ hasText: "Delegación de atribuciones" });
      await expect(filaDelegada).toContainText(luis.nombre);
      await expect(filaDelegada).toContainText(`Desde ${hoyFormateado}`);
      await expect(filaDelegada).toContainText("Hasta 50.000,00 USD por operación");
      await expect(filaDir.filter({ hasText: "Sin ocupante" })).toBeVisible();

      await page
        .getByRole("button", { name: `Ver el detalle de ${codigoDir}` })
        .first()
        .click();

      await expect(
        page.getByRole("heading", { name: `Autoridad efectiva al ${hoyFormateado}` }),
      ).toBeVisible();

      const regionCargo = page.getByRole("region", {
        name: `Autoridad efectiva del cargo ${codigoDir}`,
      });
      await expect(regionCargo).toContainText("Delegación de atribuciones");
      await expect(regionCargo).toContainText(luis.nombre);
      await expect(regionCargo).toContainText(`Desde el cargo ${codigoJef} · Cargo ${codigoJef}`);
      await expect(regionCargo).toContainText(`Resolución ${numeroActoDelegacion}`);
      await expect(regionCargo).toContainText(codigoAsignacionDelegacion);
    });

    await test.step("2 Histórico", async () => {
      const actoSuplencia = await actoEmitidoApi(
        request,
        mundo,
        tipoId,
        emisorId,
        `EF-SUPLE-${Date.now()}`,
      );

      const asignacionSuplencia = await asignacionApi(request, mundo.headers, {
        funcionario_id: rosa.id,
        cargo_id: supId,
        acto_id: actoSuplencia.id,
        fundamento: "Suplencia temporal de la titularidad de Ana",
        desde: manana,
        hasta: finSuplencia,
        cargo_origen_id: auxId,
        figura: "SUPLENCIA",
      });

      const respSuplencia = await activarAsignacionApi(request, activador.headers, asignacionSuplencia);
      expect(respSuplencia.status(), await respSuplencia.text()).toBe(200);

      await page.reload();
      await cerrarNotificaciones(page);

      const filaSup = page
        .getByRole("row")
        .filter({ hasText: codigoSup });

      await page.getByLabel(/^A la fecha/).fill(hoy);
      await expect(filaSup.filter({ hasText: ana.nombre })).toBeVisible();
      await expect(filaSup.filter({ hasText: ana.nombre })).not.toContainText("Suplente");
      await expect(filaSup.filter({ hasText: rosa.nombre })).toHaveCount(0);

      await page.getByLabel(/^A la fecha/).fill(manana);
      const filaSupManana = filaSup.filter({ hasText: rosa.nombre });
      await expect(filaSupManana).toContainText("Suplente");
      await expect(filaSupManana).toContainText(`Sustituye a ${ana.nombre}`);
      await expect(page.getByRole("row").filter({ hasText: codigoSup })).toHaveCount(1);

      await page.getByLabel(/^A la fecha/).fill(pasadoManana);
      await expect(filaSup.filter({ hasText: ana.nombre })).toBeVisible();
      await expect(filaSup.filter({ hasText: rosa.nombre })).toHaveCount(0);
    });

    await test.step("3 Exportar CSV", async () => {
      await page.getByLabel(/^A la fecha/).fill(hoy);

      const pendienteExportar = page.waitForEvent("download");
      await page.getByRole("button", { name: "Exportar CSV" }).click();
      const descarga = await pendienteExportar;
      expect(descarga.suggestedFilename()).toBe(`autoridad-${ANIO}-${hoy}.csv`);

      const contenido = await fs.readFile(await descarga.path(), "utf8");
      expect(
        contenido.startsWith(
          "fecha_corte,codigo_unidad,unidad,ruta_unidad,codigo_cargo,denominacion_cargo,estado_cargo,vigente_desde,vigente_hasta,accion,materia,tipo_limite,monto,moneda,fundamento,acto_soporte,version_cargo,origen,figura,persona_codigo,persona,sustituye_a,asignacion,asignacion_desde,asignacion_hasta,acto,cargo_origen",
        ),
      ).toBe(true);

      const lineas = contenido.trim().split("\n");
      const cabecera = lineas[0].split(",");
      const datos = lineas.slice(1);

      const filaDelegada = datos.find((linea) => {
        const columnas = linea.split(",");
        const indiceOrigen = cabecera.indexOf("origen");
        const indicePersona = cabecera.indexOf("persona");
        const indiceFigura = cabecera.indexOf("figura");
        const indiceAsignacion = cabecera.indexOf("asignacion");
        const indiceAsignacionDesde = cabecera.indexOf("asignacion_desde");
        return (
          columnas[indiceOrigen] === "DELEGACION_ATRIBUCIONES" &&
          columnas[indicePersona] === luis.nombre &&
          columnas[indiceFigura] === "Delegación de atribuciones" &&
          columnas[indiceAsignacion] === codigoAsignacionDelegacion &&
          columnas[indiceAsignacionDesde] === hoy
        );
      });
      expect(filaDelegada, "La fila delegada debe aparecer en el CSV").toBeTruthy();

      const indiceCargo = cabecera.indexOf("codigo_cargo");
      const filasDirCsv = datos.filter((linea) => linea.split(",")[indiceCargo] === codigoDir);
      expect(filasDirCsv).toHaveLength(2);

      const filasDirPantalla = page
        .getByRole("row")
        .filter({ hasText: codigoDir });
      await expect(filasDirPantalla).toHaveCount(2);
    });

    await test.step("4 Accesibilidad", async () => {
      await page.getByLabel(/^A la fecha/).fill(hoy);

      const botonDetalle = page
        .getByRole("button", { name: `Ver el detalle de ${codigoDir}` })
        .first();

      const detalleAbierto = page.getByRole("heading", {
        name: `Autoridad efectiva al ${hoyFormateado}`,
      });
      if ((await detalleAbierto.count()) === 0) {
        await botonDetalle.click();
      }
      await expect(detalleAbierto).toBeVisible();

      for (const viewport of [
        { width: 1280, height: 800 },
        { width: 390, height: 844 },
        { width: 320, height: 568 },
      ]) {
        await page.setViewportSize(viewport);
        await sinViolacionesSerias(page, `Accesibilidad en ${viewport.width}x${viewport.height}`);
      }
    });
  });
});
