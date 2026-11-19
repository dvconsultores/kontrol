import { expect, type APIRequestContext, type APIResponse } from "@playwright/test";
import {
  API,
  TENANT,

  adjuntarDocumentoApi,
  crearUsuario,
} from "./gobierno";
import { sesionApi } from "./sesion";
import {
  prepararMundoOrdenes,
  politicaOrdenPagoVigenteApi,
  borradorApi,
  emitirApi,
  hoyCaracas,
  type MundoOrdenes,
} from "./ordenes-pago";

export const PERMISOS_EXTRA_PAGOS: string[] = [
  "gobierno_actos:view",
  "gobierno_actos:edit",
  "gobierno_actos:issue",
  "gobierno_cuentas:view",
  "gobierno_cuentas:manage",
  "gobierno_cuentas:activate",
  "gobierno_pagos:view",
  "gobierno_pagos:manage",
  "gobierno_pagos:execute",
  "gobierno_pagos:cancel",
  "gobierno_pagos:policy",
];

export interface MundoPagos {
  m: MundoOrdenes;
  checker: { username: string; headers: Record<string, string> };
  checker2: { username: string; headers: Record<string, string> };
  cargoPagarId: string;
  cargoPagar2Id: string;
  cargoFirmarId: string;
  cuentaId: string;
  moneda: string;
}

export type BandaE2E = {
  monto_desde: string;
  monto_hasta: string | null;
  requisitos: { accion: string; materia: string; cantidad: number }[];
};

export function marca(): string {
  return `${Date.now().toString(36)}${Math.random().toString(36).slice(2, 6)}`.toUpperCase();
}

async function cargoApi(
  request: APIRequestContext,
  m: MundoOrdenes,
  codigo: string,
  accion: "PAGAR" | "FIRMAR" | "REGISTRAR",
): Promise<string> {
  const crearResp = await request.post(
    `${API}/gobierno/estructuras/${m.anio}/cargos`,
    {
      headers: m.mundo.headers,
      data: {
        codigo,
        denominacion: `Cargo ${codigo}`,
        unidad_id: m.despId,
        vigente_desde: `${m.anio}-01-01`,
      },
    },
  );
  expect(crearResp.status(), await crearResp.text()).toBe(201);
  const cargo = await crearResp.json();

  const competenciaResp = await request.post(
    `${API}/gobierno/estructuras/${m.anio}/cargos/${cargo.id}/competencias`,
    {
      headers: { ...m.mundo.headers, "If-Match": '"1"' },
      data: {
        accion,
        materia: "TESORERIA",
        tipo_limite: "SIN_LIMITE",
        monto: null,
        moneda: null,
      },
    },
  );
  expect(competenciaResp.status(), await competenciaResp.text()).toBe(201);

  await adjuntarDocumentoApi(
    request,
    m.mundo.headers,
    m.mundo.companyId,
    m.tipoId,
    "GovernmentPosition",
    cargo.id,
  );

  const activarResp = await request.post(
    `${API}/gobierno/estructuras/${m.anio}/cargos/${cargo.id}/activar`,
    {
      headers: { ...m.mundo.headers, "If-Match": '"2"' },
    },
  );
  expect(activarResp.status(), await activarResp.text()).toBe(200);

  return cargo.id;
}

async function actoEmitidoApi(
  request: APIRequestContext,
  m: MundoOrdenes,
  cargoId: string,
  numero: string,
): Promise<{ id: string; version: number }> {
  const resp = await request.post(`${API}/gobierno/actos`, {
    headers: m.mundo.headers,
    data: {
      tipo: "RESOLUCION",
      numero,
      caracter: "PARTICULAR",
      asunto: `Asunto ${numero}`,
      simple_tramite: false,
      cargo_id: cargoId,
      fecha: hoyCaracas(),
      lugar: "Caracas",
      fundamento_competencia: "Reglamento interno, art. 12",
      funcionario: "Funcionaria de prueba",
      titularidad: "TITULAR",
      destinatario: "Proveedor de prueba",
      hechos: "Hechos de prueba",
      fundamentos: "Fundamentos legales de prueba",
      decision: "Decisión de prueba",
      competencia: { accion: "FIRMAR", materia: "TESORERIA" },
    },
  });
  expect(resp.status(), await resp.text()).toBe(201);
  const id = (await resp.json()).id as string;
  await adjuntarDocumentoApi(request, m.mundo.headers, m.mundo.companyId, m.tipoId, "GovernmentAct", id);
  const docsResp = await request.get(`${API}/documentos/por-recurso/GovernmentAct/${id}`, { headers: m.mundo.headers });
  expect(docsResp.status(), await docsResp.text()).toBe(200);
  const docs = await docsResp.json();
  const emitirResp = await request.post(`${API}/gobierno/actos/${id}/emitir`, {
    headers: { ...m.mundo.headers, "If-Match": '"1"' },
    data: { documento_acto_id: docs[0].id },
  });
  expect(emitirResp.status(), await emitirResp.text()).toBe(200);
  return { id, version: (await emitirResp.json()).version as number };
}

async function cuentaVigenteApi(
  request: APIRequestContext,
  m: MundoOrdenes,
  moneda: string,
  cargoFirmanteId: string,
): Promise<string> {
  const codigoBanco = String(1000 + Math.floor(Math.random() * 8999));
  const bancoResp = await request.post(`${API}/gobierno/tesoreria/bancos`, {
    headers: m.mundo.headers,
    data: { codigo: codigoBanco, nombre: `Banco ${codigoBanco}` },
  });
  expect(bancoResp.status(), await bancoResp.text()).toBe(201);
  const banco = await bancoResp.json();

  const numero = codigoBanco + String(Date.now()).padStart(16, "0");
  const cuentaResp = await request.post(`${API}/gobierno/tesoreria/cuentas`, {
    headers: m.mundo.headers,
    data: {
      denominacion: `Cuenta ${codigoBanco}`,
      banco_id: banco.id,
      tipo: "CORRIENTE",
      numero,
      moneda,
      vigente_desde: `${m.anio}-01-01`,
    },
  });
  expect(cuentaResp.status(), await cuentaResp.text()).toBe(201);
  let cuenta = await cuentaResp.json();

  const acto = await actoEmitidoApi(request, m, cargoFirmanteId, `AC-${marca()}`);
  const actoResp = await request.post(
    `${API}/gobierno/tesoreria/cuentas/${cuenta.id}/acto`,
    {
      headers: { ...m.mundo.headers, "If-Match": String(cuenta.version) },
      data: { acto_id: acto.id },
    },
  );
  expect(actoResp.status(), await actoResp.text()).toBe(200);
  cuenta = await actoResp.json();

  const autorizadoResp = await request.post(
    `${API}/gobierno/tesoreria/cuentas/${cuenta.id}/autorizados`,
    {
      headers: { ...m.mundo.headers, "If-Match": String(cuenta.version) },
      data: {
        cargo_id: cargoFirmanteId,
        acto_id: acto.id,
        vigente_desde: `${m.anio}-01-01`,
      },
    },
  );
  expect(autorizadoResp.status(), await autorizadoResp.text()).toBe(201);
  cuenta = await autorizadoResp.json();

  const activarResp = await request.post(
    `${API}/gobierno/tesoreria/cuentas/${cuenta.id}/activar`,
    {
      headers: { ...m.mundo.headers, "If-Match": String(cuenta.version) },
    },
  );
  expect(activarResp.status(), await activarResp.text()).toBe(200);

  return cuenta.id;
}

export async function prepararMundoPagos(
  request: APIRequestContext,
  montos: string[],
): Promise<MundoPagos> {
  const m = await prepararMundoOrdenes(request, montos, PERMISOS_EXTRA_PAGOS);

  const admin = await sesionApi("admintenant", { tenant: TENANT });

  const checker = await crearUsuario(
    request,
    admin.headers,
    ["organization:view", "gobierno_pagos:view", "gobierno_pagos:authorize"],
    m.mundo.companyId,
  );
  const checker2 = await crearUsuario(
    request,
    admin.headers,
    ["organization:view", "gobierno_pagos:view", "gobierno_pagos:authorize"],
    m.mundo.companyId,
  );

  const cargoPagarId = await cargoApi(request, m, "C-PAG1", "PAGAR");
  const cargoPagar2Id = await cargoApi(request, m, "C-PAG2", "PAGAR");
  const cargoFirmarId = await cargoApi(request, m, "C-FIR", "FIRMAR");

  const ejercicioResp = await request.get(
    `${API}/gobierno/presupuesto/ejercicios/${m.ejercicioId}`,
    { headers: m.mundo.headers },
  );
  expect(ejercicioResp.status(), await ejercicioResp.text()).toBe(200);
  const ejercicio = await ejercicioResp.json();
  const moneda = ejercicio.moneda_funcional as string;

  const cuentaId = await cuentaVigenteApi(request, m, moneda, cargoFirmarId);

  return { m, checker, checker2, cargoPagarId, cargoPagar2Id, cargoFirmarId, cuentaId, moneda };
}

export async function ordenEmitidaApi(
  request: APIRequestContext,
  m: MundoOrdenes,
  indiceCausado: number,
  monto: string,
): Promise<{ id: string; codigo: string; version: number }> {
  const politica = await politicaOrdenPagoVigenteApi(
    request,
    m,
    `OP${marca()}`,
    false,
  );
  const borrador = await borradorApi(
    request,
    m,
    politica.id,
    [{ cause_id: m.causados[indiceCausado].id, monto }],
    [],
  );
  return emitirApi(request, m, borrador);
}

export async function medioApi(
  request: APIRequestContext,
  mp: MundoPagos,
  opciones: { exigeReferencia?: boolean; referenciaUnica?: boolean } = {},
): Promise<{ id: string }> {
  const resp = await request.post(`${API}/gobierno/tesoreria/medios-pago`, {
    headers: mp.m.mundo.headers,
    data: {
      codigo: `M${marca()}`,
      nombre: `Medio de pago ${marca()}`,
      vigente_desde: `${mp.m.anio}-01-01`,
      exige_referencia: opciones.exigeReferencia ?? true,
      referencia_unica: opciones.referenciaUnica ?? true,
      fundamento: "Fundamento de prueba para el medio de pago E2E TRE-04",
    },
  });
  expect(resp.status(), await resp.text()).toBe(201);
  return { id: (await resp.json()).id as string };
}

export async function politicaPagoApi(
  request: APIRequestContext,
  mp: MundoPagos,
  medios: string[],
  opciones: {
    bandas?: BandaE2E[];
    permiteParcial?: boolean;
    controlDuplicado?: "BLOQUEAR" | "ADVERTIR";
    activar?: boolean;
    vigenteDesde?: string;
  } = {},
): Promise<{ id: string; version: number; numero_version: number; codigo: string }> {
  const codigo = `PP${marca()}`;
  const crearResp = await request.post(`${API}/gobierno/tesoreria/politicas-pago`, {
    headers: mp.m.mundo.headers,
    data: {
      codigo,
      nombre: `Política de pagos ${codigo}`,
      moneda: mp.moneda,
      tipo_regla: "INSTITUTIONAL_POLICY",
      vigente_desde: opciones.vigenteDesde ?? `${mp.m.anio}-01-01`,
      fundamento: "Fundamento de prueba de la política de pagos E2E TRE-04.",
      medios,
      bandas: opciones.bandas ?? [
        {
          monto_desde: "0",
          monto_hasta: null,
          requisitos: [{ accion: "PAGAR", materia: "TESORERIA", cantidad: 1 }],
        },
      ],
      documentos: [],
      permite_pago_parcial: opciones.permiteParcial ?? true,
      control_duplicado: opciones.controlDuplicado ?? "BLOQUEAR",
    },
  });
  expect(crearResp.status(), await crearResp.text()).toBe(201);
  let politica = await crearResp.json();

  if (opciones.activar ?? true) {
    const activarResp = await request.post(
      `${API}/gobierno/tesoreria/politicas-pago/${politica.id}/activar`,
      {
        headers: { ...mp.m.mundo.headers, "If-Match": String(politica.version) },
        data: { fundamento: "Fundamento de activación de la política de pagos E2E TRE-04." },
      },
    );
    expect(activarResp.status(), await activarResp.text()).toBe(200);
    politica = await activarResp.json();
  }

  return {
    id: politica.id,
    version: politica.version,
    numero_version: politica.numero_version,
    codigo: politica.codigo,
  };
}

export async function pagoApi(
  request: APIRequestContext,
  mp: MundoPagos,
  orderId: string,
  politicaId: string,
  medioId: string,
  monto: string,
): Promise<{ id: string; version: number }> {
  const resp = await request.post(`${API}/gobierno/tesoreria/pagos`, {
    headers: mp.m.mundo.headers,
    data: {
      order_id: orderId,
      policy_id: politicaId,
      method_id: medioId,
      account_id: mp.cuentaId,
      fecha_pago: hoyCaracas(),
      concepto: "Pago E2E TRE-04",
      monto,
    },
  });
  expect(resp.status(), await resp.text()).toBe(201);
  const pago = await resp.json();
  return { id: pago.id, version: pago.version };
}

export async function enviarApi(
  request: APIRequestContext,
  headers: Record<string, string>,
  pago: { id: string; version: number },
  cuerpo: Record<string, unknown> = {},
): Promise<APIResponse> {
  return request.post(`${API}/gobierno/tesoreria/pagos/${pago.id}/enviar`, {
    headers: { ...headers, "If-Match": String(pago.version) },
    data: cuerpo,
  });
}

export async function aprobarApi(
  request: APIRequestContext,
  headers: Record<string, string>,
  pago: { id: string; version: number },
  cargoId: string,
  requisitoIndice: number = 0,
): Promise<APIResponse> {
  const actual = (await detallePagoApi(request, headers, pago.id)) as { version: number };
  return request.post(`${API}/gobierno/tesoreria/pagos/${pago.id}/aprobar`, {
    headers: { ...headers, "If-Match": String(actual.version) },
    data: { cargo_id: cargoId, requisito_indice: requisitoIndice },
  });
}

export async function registrarApi(
  request: APIRequestContext,
  headers: Record<string, string>,
  pago: { id: string; version: number },
  referencia: string,
): Promise<APIResponse> {
  const actual = (await detallePagoApi(request, headers, pago.id)) as { version: number };
  return request.post(`${API}/gobierno/tesoreria/pagos/${pago.id}/registrar`, {
    headers: { ...headers, "If-Match": String(actual.version) },
    data: { referencia_externa: referencia, fecha_valor: hoyCaracas() },
  });
}

export async function detallePagoApi(
  request: APIRequestContext,
  headers: Record<string, string>,
  id: string,
): Promise<Record<string, unknown>> {
  const resp = await request.get(`${API}/gobierno/tesoreria/pagos/${id}`, {
    headers,
  });
  expect(resp.status(), await resp.text()).toBe(200);
  return resp.json();
}

export async function detalleOrdenApi(
  request: APIRequestContext,
  headers: Record<string, string>,
  orderId: string,
): Promise<Record<string, unknown>> {
  const resp = await request.get(`${API}/gobierno/tesoreria/ordenes-pago/${orderId}`, {
    headers,
  });
  expect(resp.status(), await resp.text()).toBe(200);
  return resp.json();
}
