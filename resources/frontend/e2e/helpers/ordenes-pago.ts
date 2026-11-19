import AxeBuilder from "@axe-core/playwright";
import { expect, type APIRequestContext, type Page } from "@playwright/test";
import {
  ANIO,
  API,
  TENANT,
  adjuntarDocumentoApi,
  crearTipoDocumental,
  crearUsuario,
  enteActivo,
  estructuraVigenteApi,
  prepararMundo,
  RESPONSABLE_ESTRUCTURA,
} from "./gobierno";
import { sesionApi } from "./sesion";

export const PERMISOS_ORDENES: string[] = [
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
  "gobierno_ordenes_pago:view",
  "gobierno_ordenes_pago:manage",
  "gobierno_ordenes_pago:issue",
  "gobierno_ordenes_pago:cancel",
  "gobierno_ordenes_pago:policy",
  "gobierno_sod:view",
  "gobierno_sod:manage",
  "gobierno_sod:activate",
];

export function hoyCaracas(): string {
  return new Intl.DateTimeFormat("en-CA", { timeZone: "America/Caracas" }).format(
    new Date(),
  );
}

export async function sinViolacionesSerias(page: Page, contexto: string): Promise<void> {
  const resultados = await new AxeBuilder({ page })
    .include("main")
    .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"])
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

export interface CausadoListo {
  id: string;
  codigo: string;
  monto: string;
  version: number;
}

export interface MundoOrdenes {
  mundo: { companyId: string; codigo: string; username: string; headers: Record<string, string> };
  anio: number;
  ejercicioId: string;
  tipoId: string;
  cargoOrdenarId: string;
  cargoOrdenarNombre: string;
  causados: CausadoListo[];
  despId: string;
}

export async function prepararMundoOrdenes(
  request: APIRequestContext,
  montos: string[],
  permisosExtra: string[] = [],
): Promise<MundoOrdenes> {
  const mundo = await prepararMundo(request, [...PERMISOS_ORDENES, ...permisosExtra]);
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

  const montosEnCentavos = montos.map((m) => Math.round(Number(m) * 100));
  const totalCentavos = montosEnCentavos.reduce((acc, v) => acc + v, 0);
  const totalMonto = (totalCentavos / 100).toFixed(2);

  const cargoPresResp = await request.post(`${API}/gobierno/estructuras/${anio}/cargos`, {
    headers: mundo.headers,
    data: {
      codigo: "C-PRES",
      denominacion: "Director de Presupuesto",
      unidad_id: despId,
      vigente_desde: `${anio}-01-01`,
    },
  });
  expect(cargoPresResp.status(), await cargoPresResp.text()).toBe(201);
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
  expect(competenciaPresResp.status(), await competenciaPresResp.text()).toBe(201);
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
  expect(activarCargoPresResp.status(), await activarCargoPresResp.text()).toBe(200);

  const cargoAdmResp = await request.post(`${API}/gobierno/estructuras/${anio}/cargos`, {
    headers: mundo.headers,
    data: {
      codigo: "C-ADM",
      denominacion: "Director de Administración",
      unidad_id: despId,
      vigente_desde: `${anio}-01-01`,
    },
  });
  expect(cargoAdmResp.status(), await cargoAdmResp.text()).toBe(201);
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
  expect(competenciaAdmResp.status(), await competenciaAdmResp.text()).toBe(201);
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
  expect(activarCargoAdmResp.status(), await activarCargoAdmResp.text()).toBe(200);

  const cargoCausResp = await request.post(`${API}/gobierno/estructuras/${anio}/cargos`, {
    headers: mundo.headers,
    data: {
      codigo: "C-CAUS",
      denominacion: "Jefe de Causado",
      unidad_id: despId,
      vigente_desde: `${anio}-01-01`,
    },
  });
  expect(cargoCausResp.status(), await cargoCausResp.text()).toBe(201);
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
  expect(competenciaCausResp.status(), await competenciaCausResp.text()).toBe(201);
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
  expect(activarCargoCausResp.status(), await activarCargoCausResp.text()).toBe(200);

  const crearEjercicioResp = await request.post(`${API}/gobierno/presupuesto/ejercicios`, {
    headers: mundo.headers,
    data: { anio },
  });
  expect(crearEjercicioResp.status(), await crearEjercicioResp.text()).toBe(201);
  const ejercicio = await crearEjercicioResp.json();
  let version = ejercicio.version;

  const nivelesResp = await request.put(
    `${API}/gobierno/presupuesto/ejercicios/${ejercicio.id}/niveles`,
    {
      headers: { ...mundo.headers, "If-Match": String(version) },
      data: { niveles: [{ nombre: "Sector" }, { nombre: "Programa" }] },
    },
  );
  expect(nivelesResp.status(), await nivelesResp.text()).toBe(200);
  version = (await nivelesResp.json()).version;

  const cat01Resp = await request.post(
    `${API}/gobierno/presupuesto/ejercicios/${ejercicio.id}/categorias`,
    {
      headers: { ...mundo.headers, "If-Match": String(version) },
      data: {
        nivel_orden: 1,
        parent_id: null,
        codigo: "01",
        denominacion: "Sector salud",
      },
    },
  );
  expect(cat01Resp.status(), await cat01Resp.text()).toBe(201);
  const detalleCat01 = await cat01Resp.json();
  version = detalleCat01.version;
  const cat01 = detalleCat01.categorias.find(
    (c: { codigo_completo: string }) => c.codigo_completo === "01",
  );

  const cat02Resp = await request.post(
    `${API}/gobierno/presupuesto/ejercicios/${ejercicio.id}/categorias`,
    {
      headers: { ...mundo.headers, "If-Match": String(version) },
      data: {
        nivel_orden: 2,
        parent_id: cat01.id,
        codigo: "02",
        denominacion: "Atención primaria",
      },
    },
  );
  expect(cat02Resp.status(), await cat02Resp.text()).toBe(201);
  const detalleCat02 = await cat02Resp.json();
  version = detalleCat02.version;
  const cat02 = detalleCat02.categorias.find(
    (c: { codigo_completo: string }) => c.codigo_completo === "01.02",
  );

  await adjuntarDocumentoApi(request, mundo.headers, mundo.companyId, tipo.id, "GovernmentBudgetYear", ejercicio.id);
  await adjuntarDocumentoApi(request, mundo.headers, mundo.companyId, tipo.id, "GovernmentBudgetYear", ejercicio.id);
  await adjuntarDocumentoApi(request, mundo.headers, mundo.companyId, tipo.id, "GovernmentBudgetYear", ejercicio.id);
  const documentosResp = await request.get(
    `${API}/documentos/por-recurso/GovernmentBudgetYear/${ejercicio.id}`,
    { headers: mundo.headers },
  );
  expect(documentosResp.status(), await documentosResp.text()).toBe(200);
  const documentos = (await documentosResp.json()) as Array<{ id: string }>;
  expect(documentos.length).toBeGreaterThanOrEqual(3);

  const clasificadorResp = await request.put(
    `${API}/gobierno/presupuesto/ejercicios/${ejercicio.id}/clasificador`,
    {
      headers: { ...mundo.headers, "If-Match": String(version) },
      data: {
        edicion: "Clasificador del ente",
        procedencia: "Copia entregada por la Dirección de Presupuesto",
        documento_id: documentos[0].id,
      },
    },
  );
  expect(clasificadorResp.status(), await clasificadorResp.text()).toBe(200);
  version = (await clasificadorResp.json()).version;

  const partida301Resp = await request.post(
    `${API}/gobierno/presupuesto/ejercicios/${ejercicio.id}/clasificador/partidas`,
    {
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
    },
  );
  expect(partida301Resp.status(), await partida301Resp.text()).toBe(201);
  version = (await partida301Resp.json()).version;

  const partida401Resp = await request.post(
    `${API}/gobierno/presupuesto/ejercicios/${ejercicio.id}/clasificador/partidas`,
    {
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
    },
  );
  expect(partida401Resp.status(), await partida401Resp.text()).toBe(201);
  version = (await partida401Resp.json()).version;

  const partida40101Resp = await request.post(
    `${API}/gobierno/presupuesto/ejercicios/${ejercicio.id}/clasificador/partidas`,
    {
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
    },
  );
  expect(partida40101Resp.status(), await partida40101Resp.text()).toBe(201);
  version = (await partida40101Resp.json()).version;

  const fuentesResp = await request.post(
    `${API}/gobierno/presupuesto/ejercicios/${ejercicio.id}/fuentes`,
    {
      headers: { ...mundo.headers, "If-Match": String(version) },
      data: {
        codigo: "F01",
        denominacion: "Ingresos propios",
        procedencia: "Ordenanza municipal de ingresos del ente",
      },
    },
  );
  expect(fuentesResp.status(), await fuentesResp.text()).toBe(201);
  const fuentesDatos = await fuentesResp.json();
  version = fuentesDatos.version;
  const fuenteF01 = fuentesDatos.items.find((f: { codigo: string }) => f.codigo === "F01");

  const partidasResp = await request.get(
    `${API}/gobierno/presupuesto/ejercicios/${ejercicio.id}/clasificador/partidas`,
    { headers: mundo.headers },
  );
  expect(partidasResp.status(), await partidasResp.text()).toBe(200);
  const partidas = (await partidasResp.json()) as {
    items: Array<{ id: string; codigo: string }>;
  };
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
  expect(ingresoResp.status(), await ingresoResp.text()).toBe(201);
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
  expect(creditoResp.status(), await creditoResp.text()).toBe(201);
  const creditosDatos = await creditoResp.json();
  version = creditosDatos.version;
  const creditoId = (creditosDatos as { creditos: Array<{ id: string }> }).creditos[0].id;

  const ejercicioActualResp = await request.get(
    `${API}/gobierno/presupuesto/ejercicios/${ejercicio.id}`,
    { headers: mundo.headers },
  );
  expect(ejercicioActualResp.status(), await ejercicioActualResp.text()).toBe(200);
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
  expect(aprobarResp.status(), await aprobarResp.text()).toBe(200);

  const cdpResp = await request.post(
    `${API}/gobierno/presupuesto/ejercicios/${ejercicio.id}/certificaciones`,
    {
      headers: certificador.headers,
      data: {
        credito_id: creditoId,
        monto: totalMonto,
        concepto: "Adquisición de material médico",
        expediente_referencia: "EXP-PRES-2026-001",
        firmante_cargo_id: cargoPres.id,
      },
    },
  );
  expect(cdpResp.status(), await cdpResp.text()).toBe(201);
  const cdp = await cdpResp.json();

  const compromisoResp = await request.post(
    `${API}/gobierno/presupuesto/ejercicios/${ejercicio.id}/compromisos`,
    {
      headers: mundo.headers,
      data: {
        concepto: "Orden de servicio de mantenimiento",
        autoridad_cargo_id: cargoAdm.id,
        soporte_documento_id: documentos[2].id,
        lineas: [{ certificado_id: cdp.id, monto: totalMonto }],
      },
    },
  );
  expect(compromisoResp.status(), await compromisoResp.text()).toBe(201);
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
  expect(politicaResp.status(), await politicaResp.text()).toBe(201);
  const politica = await politicaResp.json();
  const activarPoliticaResp = await request.post(
    `${API}/gobierno/presupuesto/politicas-causado/${politica.id}/activar`,
    {
      headers: { ...mundo.headers, "If-Match": String(politica.version) },
      data: { fundamento: "Activación aprobada por la Dirección de Presupuesto del ente" },
    },
  );
  expect(activarPoliticaResp.status(), await activarPoliticaResp.text()).toBe(200);

  const cargoOrdenarResp = await request.post(`${API}/gobierno/estructuras/${anio}/cargos`, {
    headers: mundo.headers,
    data: {
      codigo: "C-ORD",
      denominacion: "Cargo ordenador de pagos",
      unidad_id: despId,
      vigente_desde: `${anio}-01-01`,
    },
  });
  expect(cargoOrdenarResp.status(), await cargoOrdenarResp.text()).toBe(201);
  const cargoOrdenar = await cargoOrdenarResp.json();
  const competenciaOrdenarResp = await request.post(
    `${API}/gobierno/estructuras/${anio}/cargos/${cargoOrdenar.id}/competencias`,
    {
      headers: { ...mundo.headers, "If-Match": '"1"' },
      data: {
        accion: "ORDENAR_PAGO",
        materia: "TESORERIA",
        tipo_limite: "SIN_LIMITE",
        monto: null,
        moneda: null,
      },
    },
  );
  expect(competenciaOrdenarResp.status(), await competenciaOrdenarResp.text()).toBe(201);
  await adjuntarDocumentoApi(
    request,
    mundo.headers,
    mundo.companyId,
    tipo.id,
    "GovernmentPosition",
    cargoOrdenar.id,
  );
  const activarCargoOrdenarResp = await request.post(
    `${API}/gobierno/estructuras/${anio}/cargos/${cargoOrdenar.id}/activar`,
    {
      headers: { ...mundo.headers, "If-Match": '"2"' },
    },
  );
  expect(activarCargoOrdenarResp.status(), await activarCargoOrdenarResp.text()).toBe(200);

  const causados: CausadoListo[] = [];
  for (let i = 0; i < montos.length; i += 1) {
    const monto = montos[i];
    const opcionesResp = await request.get(
      `${API}/gobierno/presupuesto/ejercicios/${ejercicio.id}/causados/opciones?compromiso_id=${compromiso.id}`,
      { headers: mundo.headers },
    );
    expect(opcionesResp.status(), await opcionesResp.text()).toBe(200);
    const opciones = await opcionesResp.json();
    const lineaCompromisoId = (opciones as { compromisos: Array<{ lineas: Array<{ id: string }> }> }).compromisos[0].lineas[0].id;

    const crearCausadoResp = await request.post(
      `${API}/gobierno/presupuesto/ejercicios/${ejercicio.id}/causados`,
      {
        headers: mundo.headers,
        data: {
          compromiso_id: compromiso.id,
          politica_id: politica.id,
          fecha_efectiva: hoyCaracas(),
          concepto: `Causado para orden de pago ${i + 1}`,
          beneficiario: "Proveedor Uno C.A.",
          autoridad_cargo_id: cargoCaus.id,
          lineas: [{ linea_compromiso_id: lineaCompromisoId, monto }],
          evidencias: [{ tipo: "DOCUMENT", id: documentos[0].id }],
        },
      },
    );
    expect(crearCausadoResp.status(), await crearCausadoResp.text()).toBe(201);
    const causadoCreado = await crearCausadoResp.json();
    const formalizarResp = await request.post(
      `${API}/gobierno/presupuesto/causados/${causadoCreado.id}/formalizar`,
      {
        headers: { ...mundo.headers, "If-Match": String(causadoCreado.version) },
      },
    );
    expect(formalizarResp.status(), await formalizarResp.text()).toBe(200);
    const causadoFormalizado = await formalizarResp.json();
    causados.push({
      id: causadoFormalizado.id,
      codigo: causadoFormalizado.codigo,
      monto,
      version: causadoFormalizado.version,
    });
  }

  return {
    mundo,
    anio,
    ejercicioId: ejercicio.id,
    tipoId: tipo.id,
    cargoOrdenarId: cargoOrdenar.id,
    cargoOrdenarNombre: cargoOrdenar.denominacion,
    causados,
    despId,
  };
}

export async function politicaOrdenPagoVigenteApi(
  request: APIRequestContext,
  m: MundoOrdenes,
  codigo: string,
  documentoObligatorio: boolean,
): Promise<{ id: string; version: number }> {
  const crearResp = await request.post(`${API}/gobierno/tesoreria/politicas-orden-pago`, {
    headers: m.mundo.headers,
    data: {
      codigo,
      nombre: `Política de órdenes ${codigo}`,
      vigente_desde: `${m.anio}-01-01`,
      tipo_regla: "INSTITUTIONAL_POLICY",
      competencia_accion: "ORDENAR_PAGO",
      competencia_materia: "TESORERIA",
      documentos: documentoObligatorio
        ? [{ document_type_id: m.tipoId, obligatorio: true, etapa: "EMISION" }]
        : [],
    },
  });
  expect(crearResp.status(), await crearResp.text()).toBe(201);
  const politica = await crearResp.json();
  const activarResp = await request.post(
    `${API}/gobierno/tesoreria/politicas-orden-pago/${politica.id}/activar`,
    {
      headers: { ...m.mundo.headers, "If-Match": String(politica.version) },
      data: { fundamento: "Activación de la política de órdenes de pago de la suite" },
    },
  );
  expect(activarResp.status(), await activarResp.text()).toBe(200);
  const activada = await activarResp.json();
  return { id: activada.id, version: activada.version };
}

export async function opcionDe(
  request: APIRequestContext,
  m: MundoOrdenes,
  causadoId: string,
): Promise<{ monto_ordenado: string; pendiente_de_ordenar: string }> {
  const resp = await request.get(
    `${API}/gobierno/tesoreria/ejercicios/${m.ejercicioId}/ordenes-pago/opciones`,
    { headers: m.mundo.headers },
  );
  expect(resp.status(), await resp.text()).toBe(200);
  const opciones = (await resp.json()) as {
    obligaciones: Array<{
      id: string;
      monto_ordenado: string;
      pendiente_de_ordenar: string;
    }>;
  };
  const obligacion = opciones.obligaciones.find((o) => o.id === causadoId);
  expect(obligacion, `Obligación ${causadoId} no disponible`).toBeTruthy();
  return {
    monto_ordenado: obligacion?.monto_ordenado ?? "0.00",
    pendiente_de_ordenar: obligacion?.pendiente_de_ordenar ?? "0.00",
  };
}

export async function numeracionApi(
  request: APIRequestContext,
  m: MundoOrdenes,
  patron: string,
): Promise<{ ejemplo: string }> {
  const getResp = await request.get(
    `${API}/gobierno/tesoreria/ordenes-pago/configuracion`,
    { headers: m.mundo.headers },
  );
  expect(getResp.status(), await getResp.text()).toBe(200);
  const configuracion = await getResp.json();
  const putResp = await request.put(
    `${API}/gobierno/tesoreria/ordenes-pago/configuracion`,
    {
      headers: { ...m.mundo.headers, "If-Match": String(configuracion.version) },
      data: { patron },
    },
  );
  expect(putResp.status(), await putResp.text()).toBe(200);
  const actualizada = await putResp.json();
  return { ejemplo: actualizada.ejemplo };
}

export async function documentoDelTipo(
  request: APIRequestContext,
  m: MundoOrdenes,
): Promise<string> {
  const resp = await request.get(
    `${API}/gobierno/tesoreria/ejercicios/${m.ejercicioId}/ordenes-pago/opciones`,
    { headers: m.mundo.headers },
  );
  expect(resp.status(), await resp.text()).toBe(200);
  const opciones = (await resp.json()) as {
    documentos: Array<{ id: string; document_type_id: string }>;
  };
  const documento = opciones.documentos.find((d) => d.document_type_id === m.tipoId);
  expect(documento, "Documento del tipo requerido no disponible").toBeTruthy();
  return documento?.id ?? "";
}

export async function reglaSodTre03Api(
  request: APIRequestContext,
  m: MundoOrdenes,
): Promise<void> {
  const crearResp = await request.post(`${API}/gobierno/sod/reglas`, {
    headers: m.mundo.headers,
    data: {
      nombre: "Causar y ordenar separados",
      descripcion: "Quien formaliza el causado no emite su orden de pago.",
      proceso: "TRE-03",
      accion_a: "TRE03_CAUSAR",
      accion_b: "TRE03_ORDENAR",
      bidireccional: false,
      vigente_desde: hoyCaracas(),
      vigente_hasta: null,
    },
  });
  expect(crearResp.status(), await crearResp.text()).toBe(201);
  const regla = await crearResp.json();
  const activarResp = await request.post(
    `${API}/gobierno/sod/reglas/${regla.id}/activar`,
    {
      headers: { ...m.mundo.headers, "If-Match": String(regla.version) },
      data: {},
    },
  );
  expect(activarResp.status(), await activarResp.text()).toBe(200);
}

export async function borradorApi(
  request: APIRequestContext,
  m: MundoOrdenes,
  politicaId: string,
  lineas: { cause_id: string; monto: string }[],
  documentos: string[],
): Promise<{ id: string; version: number }> {
  const resp = await request.post(
    `${API}/gobierno/tesoreria/ejercicios/${m.ejercicioId}/ordenes-pago`,
    {
      headers: m.mundo.headers,
      data: {
        policy_id: politicaId,
        fecha_orden: hoyCaracas(),
        concepto: "Orden preparada por la suite",
        lineas,
        documentos,
        autoridad_cargo_id: m.cargoOrdenarId,
      },
    },
  );
  expect(resp.status(), await resp.text()).toBe(201);
  const orden = await resp.json();
  return { id: orden.id, version: orden.version };
}

export async function emitirApi(
  request: APIRequestContext,
  m: MundoOrdenes,
  orden: { id: string; version: number },
): Promise<{ id: string; codigo: string; version: number }> {
  const resp = await request.post(
    `${API}/gobierno/tesoreria/ordenes-pago/${orden.id}/emitir`,
    {
      headers: { ...m.mundo.headers, "If-Match": String(orden.version) },
    },
  );
  expect(resp.status(), await resp.text()).toBe(200);
  const emitida = await resp.json();
  return { id: emitida.id, codigo: emitida.codigo, version: emitida.version };
}
