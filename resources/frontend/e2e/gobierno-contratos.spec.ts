import { AxeBuilder } from "@axe-core/playwright";
import type { APIRequestContext } from "@playwright/test";
import { expect, test } from "./helpers/sesion";
import { sesionApi } from "./helpers/sesion";
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
  declararMontoApi,
  enteActivo,
  entrarEnGobierno,
  estructuraVigenteApi,
  prepararMundo,
} from "./helpers/gobierno";

test.setTimeout(720_000);

type ActoEmitido = {
  id: string;
  version: number;
  numero: string;
};

type DocumentoRecurso = {
  id: string;
  titulo: string;
};

type Funcionario = {
  id: string;
  nombre: string;
};

type MiembroComision = {
  id: string;
  funcionario: { id: string; nombre: string };
  funcion: string;
  condicion: string;
  suplente_de_id: string | null;
};

type Comision = {
  id: string;
  version: number;
  miembros: MiembroComision[];
};

type Expediente = {
  id: string;
  version: number;
  numero: string;
};

type MatrizEstado = {
  matriz: {
    version: number;
    criterios: Array<{ id: string; nombre: string; aspecto: string; escala: string }>;
  };
};

type Oferta = {
  id: string;
  version: number;
  codigo: string;
};

type EjercicioPresupuestario = {
  id: string;
  version: number;
};

type CargoPresupuesto = {
  id: string;
  version: number;
};

type DocumentoConTitulo = {
  id: string;
  titulo: string;
};

type GarantiaVersion = {
  version: number;
};

type CertificacionCreada = {
  id: string;
  codigo: string;
};

async function actoEmitidoApi(
  request: APIRequestContext,
  headers: Record<string, string>,
  companyId: string,
  tipoId: string,
  cargoId: string,
  hoy: string,
): Promise<ActoEmitido> {
  const actoResp = await request.post(`${API}/gobierno/actos`, {
    headers,
    data: {
      tipo: "RESOLUCION",
      numero: `NUM-${Date.now()}`,
      caracter: "GENERAL",
      asunto: "Designación de la Comisión",
      simple_tramite: false,
      cargo_id: cargoId,
      fecha: hoy,
      lugar: "Caracas",
      fundamento_competencia: "Reglamento interno, art. 12",
      funcionario: "Funcionaria de prueba",
      titularidad: "TITULAR",
      hechos: "Hechos de prueba",
      fundamentos: "Fundamentos de prueba",
      decision: "Decisión de prueba",
      competencia: { accion: "APROBAR", materia: "CONTRATACIONES" },
    },
  });
  expect(actoResp.status(), await actoResp.text()).toBe(201);
  const acto = (await actoResp.json()) as ActoEmitido;

  await adjuntarDocumentoApi(request, headers, companyId, tipoId, "GovernmentAct", acto.id);
  const docsAntes = (await (
    await request.get(`${API}/documentos/por-recurso/GovernmentAct/${acto.id}`, { headers })
  ).json()) as DocumentoRecurso[];

  const emitirResp = await request.post(`${API}/gobierno/actos/${acto.id}/emitir`, {
    headers: { ...headers, "If-Match": '"1"' },
    data: { documento_acto_id: docsAntes[0].id },
  });
  expect(emitirResp.status(), await emitirResp.text()).toBe(200);

  await adjuntarDocumentoApi(request, headers, companyId, tipoId, "GovernmentAct", acto.id);
  const docsDespues = (await (
    await request.get(`${API}/documentos/por-recurso/GovernmentAct/${acto.id}`, { headers })
  ).json()) as DocumentoRecurso[];
  const documentoEficacia = docsDespues.find((d) => !docsAntes.some((prev) => prev.id === d.id));
  expect(documentoEficacia).toBeTruthy();

  const eficaciaResp = await request.post(`${API}/gobierno/actos/${acto.id}/eficacia`, {
    headers: { ...headers, "If-Match": '"2"' },
    data: {
      medio: "GACETA",
      referencia: "Gaceta N.º 1",
      fecha: hoy,
      documento_eficacia_id: documentoEficacia!.id,
    },
  });
  expect(eficaciaResp.status(), await eficaciaResp.text()).toBe(200);

  return acto;
}

async function actoDecisionEmitidoApi(
  request: APIRequestContext,
  headers: Record<string, string>,
  companyId: string,
  tipoId: string,
  cargoId: string,
  hoy: string,
): Promise<ActoEmitido> {
  const actoResp = await request.post(`${API}/gobierno/actos`, {
    headers,
    data: {
      tipo: "RESOLUCION",
      numero: `DEC-${Date.now()}`,
      caracter: "PARTICULAR",
      asunto: "Adjudicación del concurso",
      destinatario: "Constructora Andina",
      simple_tramite: false,
      cargo_id: cargoId,
      fecha: hoy,
      lugar: "Caracas",
      fundamento_competencia: "Reglamento interno, art. 12",
      funcionario: "Funcionaria de prueba",
      titularidad: "TITULAR",
      hechos: "Hechos de prueba",
      fundamentos: "Fundamentos de prueba",
      decision: "Decisión de prueba",
      competencia: { accion: "APROBAR", materia: "CONTRATACIONES" },
    },
  });
  expect(actoResp.status(), await actoResp.text()).toBe(201);
  const acto = (await actoResp.json()) as ActoEmitido;

  await adjuntarDocumentoApi(request, headers, companyId, tipoId, "GovernmentAct", acto.id);
  const docsAntes = (await (
    await request.get(`${API}/documentos/por-recurso/GovernmentAct/${acto.id}`, { headers })
  ).json()) as DocumentoRecurso[];

  const emitirResp = await request.post(`${API}/gobierno/actos/${acto.id}/emitir`, {
    headers: { ...headers, "If-Match": '"1"' },
    data: { documento_acto_id: docsAntes[0].id },
  });
  expect(emitirResp.status(), await emitirResp.text()).toBe(200);

  return acto;
}

async function crearFuncionario(
  request: APIRequestContext,
  headers: Record<string, string>,
  nombre: string,
): Promise<Funcionario> {
  const resp = await request.post(`${API}/gobierno/ocupacion/funcionarios`, {
    headers,
    data: {
      nombre,
      tipo_documento: "V",
      numero_documento: String(Math.floor(10000000 + Math.random() * 89999999)),
    },
  });
  expect(resp.status(), await resp.text()).toBe(201);
  return (await resp.json()) as Funcionario;
}

async function agregarMiembro(
  request: APIRequestContext,
  headers: Record<string, string>,
  comisionId: string,
  version: number,
  funcionarioId: string,
  funcion: string,
  area: string | null,
  condicion: string,
  suplenteDeId: string | null,
): Promise<number> {
  const resp = await request.post(`${API}/gobierno/contrataciones/comisiones/${comisionId}/miembros`, {
    headers: { ...headers, "If-Match": String(version) },
    data: {
      funcionario_id: funcionarioId,
      funcion,
      area,
      condicion,
      suplente_de_id: suplenteDeId,
      certificacion_snc: null,
      desde: null,
      acto_id: null,
    },
  });
  expect(resp.status(), await resp.text()).toBe(200);
  const detalleResp = await request.get(`${API}/gobierno/contrataciones/comisiones/${comisionId}`, { headers });
  expect(detalleResp.status(), await detalleResp.text()).toBe(200);
  const detalle = (await detalleResp.json()) as Comision;
  return detalle.version;
}

async function crearCriterio(
  request: APIRequestContext,
  headers: Record<string, string>,
  expedienteId: string,
  versionMatriz: number,
  criterio: {
    aspecto: string;
    orden: number;
    nombre: string;
    descripcion: string | null;
    escala: string;
    puntaje_maximo: string | null;
    ponderacion: string | null;
  },
): Promise<{ id: string; version: number }> {
  const resp = await request.post(
    `${API}/gobierno/contrataciones/expedientes/${expedienteId}/evaluacion/matriz/criterios`,
    {
      headers: { ...headers, "If-Match": String(versionMatriz) },
      data: criterio,
    },
  );
  expect(resp.status(), await resp.text()).toBe(201);
  const estado = (await resp.json()) as MatrizEstado;
  const creado = estado.matriz.criterios.find((c) => c.nombre === criterio.nombre);
  expect(creado).toBeTruthy();
  return { id: creado!.id, version: estado.matriz.version };
}

test("CNT-01 · contrato u orden desde la adjudicación: recorrido, negativas, accesibilidad y responsive", async ({ page, request }) => {
  const hoy = new Intl.DateTimeFormat("en-CA", { timeZone: "America/Caracas" }).format(new Date());

  const PERMISOS = [
    ...RESPONSABLE_ESTRUCTURA,
    "gobierno_cargos:view",
    "gobierno_cargos:edit",
    "gobierno_cargos:publish",
    "gobierno_actos:view",
    "gobierno_actos:edit",
    "gobierno_actos:issue",
    "gobierno_ocupacion:view",
    "gobierno_ocupacion:manage",
    "gobierno_comisiones:view",
    "gobierno_comisiones:manage",
    "gobierno_expedientes:view",
    "gobierno_expedientes:manage",
    "gobierno_ofertas:view",
    "gobierno_ofertas:receive",
    "gobierno_ofertas:amount",
    "gobierno_evaluacion:view",
    "gobierno_evaluacion:criteria",
    "gobierno_evaluacion:open",
    "gobierno_evaluacion:evaluate",
    "gobierno_decision:view",
    "gobierno_decision:recommend",
    "gobierno_decision:decide",
    "gobierno_notificaciones:view",
    "gobierno_notificaciones:edit",
    "gobierno_notificaciones:record",
    "documentos:view",
    "documentos:download",
    "documentos:link",
    "documentos:upload",
    "gobierno_contratos:view",
    "gobierno_contratos:manage",
    "gobierno_contratos:formalize",
    "gobierno_contratos:assign_supervisor",
    "gobierno_ocupacion:activate",
    "gobierno_contratos:execute",
    "gobierno_identidad:view",
    "gobierno_identidad:manage",
    "gobierno_auditoria:view",
    "gobierno_presupuesto:view",
    "gobierno_presupuesto:manage",
    "gobierno_presupuesto:approve",
    "gobierno_presupuesto:certify",
    "gobierno_garantias:view",
    "gobierno_garantias:manage",
  ];

  const mundo = await prepararMundo(request, PERMISOS, "USD");

  const tipo = await crearTipoDocumental(request, mundo.headers, mundo.companyId);
  await enteActivo(request, mundo.headers, mundo.companyId, tipo.id);
  const estructura = await estructuraVigenteApi(request, mundo.headers, mundo.companyId, tipo.id, ANIO);
  const emisor = await cargoVigenteApi(
    request,
    mundo.headers,
    mundo.companyId,
    tipo.id,
    ANIO,
    estructura.despId,
    `CE-${Date.now()}`,
  );

  const acto = await actoEmitidoApi(request, mundo.headers, mundo.companyId, tipo.id, emisor.id, hoy);

  const nombres = [
    "Evaluadora Técnica",
    "Suplente Técnica",
    "Evaluador Jurídico",
    "Suplente Jurídico",
    "Evaluadora Financiera",
    "Suplente Financiera",
    "Secretaria de la Comisión",
    "Suplente de la Secretaría",
  ];
  const funcionarios: Record<string, Funcionario> = {};
  for (const nombre of nombres) {
    funcionarios[nombre] = await crearFuncionario(request, mundo.headers, nombre);
  }

  const comisionResp = await request.post(`${API}/gobierno/contrataciones/comisiones`, {
    headers: mundo.headers,
    data: {
      nombre: "Comisión de evaluación E2E",
      tipo: "PERMANENTE",
      objeto: null,
      desde: hoy,
      hasta: null,
      acto_id: acto.id,
    },
  });
  expect(comisionResp.status(), await comisionResp.text()).toBe(201);
  const comisionInicial = (await comisionResp.json()) as Comision;
  let versionComision = comisionInicial.version;

  const principales: Array<{ nombre: string; area: string }> = [
    { nombre: "Evaluadora Técnica", area: "TECNICA" },
    { nombre: "Evaluador Jurídico", area: "JURIDICA" },
    { nombre: "Evaluadora Financiera", area: "ECONOMICO_FINANCIERA" },
  ];
  const suplentes: Record<string, string> = {
    "Evaluadora Técnica": "Suplente Técnica",
    "Evaluador Jurídico": "Suplente Jurídico",
    "Evaluadora Financiera": "Suplente Financiera",
  };

  for (const principal of principales) {
    versionComision = await agregarMiembro(
      request,
      mundo.headers,
      comisionInicial.id,
      versionComision,
      funcionarios[principal.nombre].id,
      "MIEMBRO",
      principal.area,
      "PRINCIPAL",
      null,
    );
    const detalleResp = await request.get(`${API}/gobierno/contrataciones/comisiones/${comisionInicial.id}`, {
      headers: mundo.headers,
    });
    const detalle = (await detalleResp.json()) as Comision;
    const miembroPrincipal = detalle.miembros.find((m) => m.funcionario.id === funcionarios[principal.nombre].id);
    expect(miembroPrincipal).toBeTruthy();
    versionComision = await agregarMiembro(
      request,
      mundo.headers,
      comisionInicial.id,
      versionComision,
      funcionarios[suplentes[principal.nombre]].id,
      "MIEMBRO",
      null,
      "SUPLENTE",
      miembroPrincipal!.id,
    );
  }

  versionComision = await agregarMiembro(
    request,
    mundo.headers,
    comisionInicial.id,
    versionComision,
    funcionarios["Secretaria de la Comisión"].id,
    "SECRETARIO",
    null,
    "PRINCIPAL",
    null,
  );

  versionComision = await agregarMiembro(
    request,
    mundo.headers,
    comisionInicial.id,
    versionComision,
    funcionarios["Suplente de la Secretaría"].id,
    "SECRETARIO",
    null,
    "SUPLENTE",
    null,
  );

  const admin = await sesionApi("admintenant", { tenant: TENANT });
  const activador = await crearUsuario(request, admin.headers, [
    "organization:view",
    "gobierno_comisiones:view",
    "gobierno_comisiones:activate",
  ], mundo.companyId);

  const detalleComisionResp = await request.get(`${API}/gobierno/contrataciones/comisiones/${comisionInicial.id}`, {
    headers: activador.headers,
  });
  expect(detalleComisionResp.status(), await detalleComisionResp.text()).toBe(200);
  const detalleComision = (await detalleComisionResp.json()) as Comision;
  const activarResp = await request.post(`${API}/gobierno/contrataciones/comisiones/${comisionInicial.id}/activar`, {
    headers: { ...activador.headers, "If-Match": String(detalleComision.version) },
  });
  expect(activarResp.status(), await activarResp.text()).toBe(200);

  const comisionActivadaResp = await request.get(
    `${API}/gobierno/contrataciones/comisiones/${comisionInicial.id}`,
    { headers: mundo.headers },
  );
  expect(comisionActivadaResp.status(), await comisionActivadaResp.text()).toBe(200);
  const comisionActivada = (await comisionActivadaResp.json()) as Comision;
  const miembroIds: Record<string, string> = {};
  for (const nombre of nombres) {
    const miembro = comisionActivada.miembros.find((m) => m.funcionario.id === funcionarios[nombre].id);
    expect(miembro, `Miembro de comisión para ${nombre}`).toBeTruthy();
    miembroIds[nombre] = miembro!.id;
  }

  const expedienteResp = await request.post(`${API}/gobierno/contrataciones/expedientes`, {
    headers: mundo.headers,
    data: {
      numero: `EXP-${Date.now()}`,
      fecha_inicio: hoy,
      objeto: "Adquisición de equipos de prueba",
      partes: null,
      tipo_contratacion: "BIENES",
      modalidad_declarada: "CONCURSO_ABIERTO",
      modalidad_fundamento: "LCP art. 78",
      modalidad_fuente: "LCP",
      unidad_id: estructura.despId,
      responsable_id: funcionarios["Secretaria de la Comisión"].id,
    },
  });
  expect(expedienteResp.status(), await expedienteResp.text()).toBe(201);
  let expediente = (await expedienteResp.json()) as Expediente;

  const comisionExpResp = await request.post(
    `${API}/gobierno/contrataciones/expedientes/${expediente.id}/comision`,
    {
      headers: { ...mundo.headers, "If-Match": String(expediente.version) },
      data: { comision_id: comisionInicial.id, no_aplica_motivo: null, motivo: null },
    },
  );
  expect(comisionExpResp.status(), await comisionExpResp.text()).toBe(200);
  const expedienteReload1 = await request.get(`${API}/gobierno/contrataciones/expedientes/${expediente.id}`, {
    headers: mundo.headers,
  });
  expect(expedienteReload1.status(), await expedienteReload1.text()).toBe(200);
  expediente = (await expedienteReload1.json()) as Expediente;

  await adjuntarDocumentoApi(request, mundo.headers, mundo.companyId, tipo.id, "GovernmentProcurementFile", expediente.id);
  const docsPliegoAntes = (await (
    await request.get(`${API}/documentos/por-recurso/GovernmentProcurementFile/${expediente.id}`, {
      headers: mundo.headers,
    })
  ).json()) as DocumentoRecurso[];
  const pliegoId = docsPliegoAntes[docsPliegoAntes.length - 1].id;

  const matrizResp = await request.post(
    `${API}/gobierno/contrataciones/expedientes/${expediente.id}/evaluacion/matriz`,
    {
      headers: { ...mundo.headers, "If-Match": String(expediente.version) },
      data: { pliego_documento_id: pliegoId },
    },
  );
  expect(matrizResp.status(), await matrizResp.text()).toBe(201);
  let estadoMatriz = (await matrizResp.json()) as MatrizEstado;

  const criterioTecnico = await crearCriterio(request, mundo.headers, expediente.id, estadoMatriz.matriz.version, {
    aspecto: "TECNICO",
    orden: 1,
    nombre: "Calidad técnica",
    descripcion: null,
    escala: "PUNTAJE",
    puntaje_maximo: "50.00",
    ponderacion: null,
  });
  estadoMatriz = { matriz: { version: criterioTecnico.version, criterios: estadoMatriz.matriz.criterios } } as MatrizEstado;

  const criterioEconomico = await crearCriterio(request, mundo.headers, expediente.id, criterioTecnico.version, {
    aspecto: "ECONOMICO",
    orden: 1,
    nombre: "Precio ofertado",
    descripcion: null,
    escala: "PUNTAJE",
    puntaje_maximo: "50.00",
    ponderacion: null,
  });

  const criterioLegal = await crearCriterio(request, mundo.headers, expediente.id, criterioEconomico.version, {
    aspecto: "LEGAL",
    orden: 1,
    nombre: "Capacidad legal",
    descripcion: null,
    escala: "CUMPLE",
    puntaje_maximo: null,
    ponderacion: null,
  });

  const bloqueoResp = await request.post(
    `${API}/gobierno/contrataciones/expedientes/${expediente.id}/evaluacion/matriz/bloquear`,
    {
      headers: { ...mundo.headers, "If-Match": String(criterioLegal.version) },
      data: {},
    },
  );
  expect(bloqueoResp.status(), await bloqueoResp.text()).toBe(200);

  await adjuntarDocumentoApi(request, mundo.headers, mundo.companyId, tipo.id, "GovernmentProcurementFile", expediente.id);
  const docsOfertaAntes = (await (
    await request.get(`${API}/documentos/por-recurso/GovernmentProcurementFile/${expediente.id}`, {
      headers: mundo.headers,
    })
  ).json()) as DocumentoRecurso[];
  const ofertaDocId = docsOfertaAntes[docsOfertaAntes.length - 1].id;

  const ofertaResp = await request.post(`${API}/gobierno/contrataciones/expedientes/${expediente.id}/ofertas`, {
    headers: { ...mundo.headers, "If-Match": String(expediente.version) },
    data: {
      oferente_nombre: "Constructora Andina",
      oferente_documento: "J-12345678-9",
      representante: null,
      tipo_sobre: "UNICO",
      canal: "MEDIO_ELECTRONICO",
      recibida_en: new Date().toISOString(),
      funcionario_id: funcionarios["Secretaria de la Comisión"].id,
      condicion_sobre: null,
      confidencial: true,
      motivo_sin_sello: null,
      documento_ids: [ofertaDocId],
    },
  });
  expect(ofertaResp.status(), await ofertaResp.text()).toBe(201);
  const oferta = (await ofertaResp.json()) as Oferta;

  const expedienteReloadOferta = await request.get(
    `${API}/gobierno/contrataciones/expedientes/${expediente.id}`,
    { headers: mundo.headers },
  );
  expect(expedienteReloadOferta.status(), await expedienteReloadOferta.text()).toBe(200);
  expediente = (await expedienteReloadOferta.json()) as Expediente;

  await adjuntarDocumentoApi(request, mundo.headers, mundo.companyId, tipo.id, "GovernmentProcurementFile", expediente.id);
  const docsOferta2Antes = (await (
    await request.get(`${API}/documentos/por-recurso/GovernmentProcurementFile/${expediente.id}`, {
      headers: mundo.headers,
    })
  ).json()) as DocumentoRecurso[];
  const oferta2DocId = docsOferta2Antes[docsOferta2Antes.length - 1].id;

  const oferta2Resp = await request.post(`${API}/gobierno/contrataciones/expedientes/${expediente.id}/ofertas`, {
    headers: { ...mundo.headers, "If-Match": String(expediente.version) },
    data: {
      oferente_nombre: "Servicios Orinoco",
      oferente_documento: "J-87654321-0",
      representante: null,
      tipo_sobre: "UNICO",
      canal: "MEDIO_ELECTRONICO",
      recibida_en: new Date().toISOString(),
      funcionario_id: funcionarios["Secretaria de la Comisión"].id,
      condicion_sobre: null,
      confidencial: true,
      motivo_sin_sello: null,
      documento_ids: [oferta2DocId],
    },
  });
  expect(oferta2Resp.status(), await oferta2Resp.text()).toBe(201);
  const oferta2 = (await oferta2Resp.json()) as Oferta;

  const expedienteReloadOferta2 = await request.get(
    `${API}/gobierno/contrataciones/expedientes/${expediente.id}`,
    { headers: mundo.headers },
  );
  expect(expedienteReloadOferta2.status(), await expedienteReloadOferta2.text()).toBe(200);
  expediente = (await expedienteReloadOferta2.json()) as Expediente;

  const concluirResp = await request.post(
    `${API}/gobierno/contrataciones/expedientes/${expediente.id}/ofertas/concluir`,
    {
      headers: { ...mundo.headers, "If-Match": String(expediente.version) },
      data: { motivo: null },
    },
  );
  expect(concluirResp.status(), await concluirResp.text()).toBe(200);

  const expedienteReloadConcluir = await request.get(
    `${API}/gobierno/contrataciones/expedientes/${expediente.id}`,
    { headers: mundo.headers },
  );
  expect(expedienteReloadConcluir.status(), await expedienteReloadConcluir.text()).toBe(200);
  expediente = (await expedienteReloadConcluir.json()) as Expediente;

  await adjuntarDocumentoApi(request, mundo.headers, mundo.companyId, tipo.id, "GovernmentProcurementFile", expediente.id);
  const docsActaAntes = (await (
    await request.get(`${API}/documentos/por-recurso/GovernmentProcurementFile/${expediente.id}`, {
      headers: mundo.headers,
    })
  ).json()) as DocumentoRecurso[];
  const actaDocumentoId = docsActaAntes[docsActaAntes.length - 1].id;

  const aperturaResp = await request.post(
    `${API}/gobierno/contrataciones/expedientes/${expediente.id}/evaluacion/aperturas`,
    {
      headers: { ...mundo.headers, "If-Match": String(expediente.version) },
      data: {
        abierta_en: new Date().toISOString(),
        oferta_ids: [oferta.id, oferta2.id],
        miembro_ids: Object.values(miembroIds),
        acta_documento_id: actaDocumentoId,
        observaciones: null,
      },
    },
  );
  expect(aperturaResp.status(), await aperturaResp.text()).toBe(201);

  const expedienteReloadApertura = await request.get(
    `${API}/gobierno/contrataciones/expedientes/${expediente.id}`,
    { headers: mundo.headers },
  );
  expect(expedienteReloadApertura.status(), await expedienteReloadApertura.text()).toBe(200);
  expediente = (await expedienteReloadApertura.json()) as Expediente;

  const evaluacionResp = await request.get(
    `${API}/gobierno/contrataciones/expedientes/${expediente.id}/evaluacion`,
    { headers: mundo.headers },
  );
  expect(evaluacionResp.status(), await evaluacionResp.text()).toBe(200);
  const evaluacionEstado = (await evaluacionResp.json()) as MatrizEstado;
  const matrizVersion = evaluacionEstado.matriz.version;

  const criterios = [
    { id: criterioTecnico.id, escala: "PUNTAJE" },
    { id: criterioEconomico.id, escala: "PUNTAJE" },
    { id: criterioLegal.id, escala: "CUMPLE" },
  ];

  for (const ofertaId of [oferta.id, oferta2.id]) {
    for (const criterio of criterios) {
      const resultadoData =
        criterio.escala === "PUNTAJE"
          ? {
              oferta_id: ofertaId,
              criterio_id: criterio.id,
              miembro_id: miembroIds["Secretaria de la Comisión"],
              matriz_version: matrizVersion,
              observacion: "Comisión",
              evidencia_documento_id: null,
              puntaje: "40.00",
            }
          : {
              oferta_id: ofertaId,
              criterio_id: criterio.id,
              miembro_id: miembroIds["Secretaria de la Comisión"],
              matriz_version: matrizVersion,
              observacion: "Comisión",
              evidencia_documento_id: null,
              cumple: true,
            };
      const resultadoResp = await request.post(
        `${API}/gobierno/contrataciones/expedientes/${expediente.id}/evaluacion/resultados`,
        {
          headers: { ...mundo.headers, "If-Match": String(expediente.version) },
          data: resultadoData,
        },
      );
      expect(resultadoResp.status(), await resultadoResp.text()).toBe(201);
      const expedienteReloadResultado = await request.get(
        `${API}/gobierno/contrataciones/expedientes/${expediente.id}`,
        { headers: mundo.headers },
      );
      expect(expedienteReloadResultado.status(), await expedienteReloadResultado.text()).toBe(200);
      expediente = (await expedienteReloadResultado.json()) as Expediente;
    }
  }

  await declararMontoApi(request, mundo.headers, expediente.id, oferta.id, expediente.version, {
    moneda: "USD",
    monto_sin_iva: "43103.45",
    tributos: "6896.55",
    total_con_tributos: "50000.00",
  });
  const expedienteReloadMonto = await request.get(
    `${API}/gobierno/contrataciones/expedientes/${expediente.id}`,
    { headers: mundo.headers },
  );
  expect(expedienteReloadMonto.status(), await expedienteReloadMonto.text()).toBe(200);
  expediente = (await expedienteReloadMonto.json()) as Expediente;

  const concluirEvaluacionResp = await request.post(
    `${API}/gobierno/contrataciones/expedientes/${expediente.id}/evaluacion/concluir`,
    {
      headers: { ...mundo.headers, "If-Match": String(expediente.version) },
      data: {},
    },
  );
  expect(concluirEvaluacionResp.status(), await concluirEvaluacionResp.text()).toBe(200);

  const expedienteReloadEvaluacion = await request.get(
    `${API}/gobierno/contrataciones/expedientes/${expediente.id}`,
    { headers: mundo.headers },
  );
  expect(expedienteReloadEvaluacion.status(), await expedienteReloadEvaluacion.text()).toBe(200);
  expediente = (await expedienteReloadEvaluacion.json()) as Expediente;

  const recomendacionResp = await request.post(
    `${API}/gobierno/contrataciones/expedientes/${expediente.id}/decision/recomendaciones`,
    {
      headers: { ...mundo.headers, "If-Match": String(expediente.version) },
      data: {
        resultado_recomendado: "ADJUDICAR",
        motivacion: "Motivación de la recomendación",
        examen_legal: "Examen legal favorable",
        examen_financiero: "Examen financiero favorable",
        examen_tecnico: "Examen técnico favorable",
        resultado_matriz: "Resultado de la matriz favorable",
        medidas_promocion: "Medidas de promoción",
        firmante_ids: Object.values(miembroIds),
        opciones: [
          { posicion: 1, offer_id: oferta.id },
          { posicion: 2, offer_id: oferta2.id },
        ],
        rechazos: [],
        causal_desierta: null,
      },
    },
  );
  expect(recomendacionResp.status(), await recomendacionResp.text()).toBe(201);
  const recomendacion = (await recomendacionResp.json()) as { recomendacion_vigente: { id: string } };
  const recomendacionId = recomendacion.recomendacion_vigente.id;

  const expedienteReloadRecomendacion = await request.get(
    `${API}/gobierno/contrataciones/expedientes/${expediente.id}`,
    { headers: mundo.headers },
  );
  expect(expedienteReloadRecomendacion.status(), await expedienteReloadRecomendacion.text()).toBe(200);
  expediente = (await expedienteReloadRecomendacion.json()) as Expediente;

  const cargoSinLimite = await cargoVigenteApi(
    request,
    mundo.headers,
    mundo.companyId,
    tipo.id,
    ANIO,
    estructura.despId,
    `CA-${Date.now()}`,
    { tipo_limite: "SIN_LIMITE" },
  );

  const actoDecision = await actoDecisionEmitidoApi(
    request,
    mundo.headers,
    mundo.companyId,
    tipo.id,
    cargoSinLimite.id,
    hoy,
  );

  const decisionResp = await request.post(
    `${API}/gobierno/contrataciones/expedientes/${expediente.id}/decision/decisiones`,
    {
      headers: { ...mundo.headers, "If-Match": String(expediente.version) },
      data: {
        resultado: "ADJUDICADA",
        recomendacion_id: recomendacionId,
        acto_id: actoDecision.id,
        oferta_id: oferta.id,
        motivacion: "Adjudicación a la mejor oferta",
      },
    },
  );
  expect(decisionResp.status(), await decisionResp.text()).toBe(201);

  const firmanteSinLimite = await cargoVigenteApi(
    request,
    mundo.headers,
    mundo.companyId,
    tipo.id,
    ANIO,
    estructura.despId,
    `CF-${Date.now()}`,
    { tipo_limite: "SIN_LIMITE" },
    "FIRMAR",
  );

  const firmanteCorto = await cargoVigenteApi(
    request,
    mundo.headers,
    mundo.companyId,
    tipo.id,
    ANIO,
    estructura.despId,
    `CL-${Date.now()}`,
    { tipo_limite: "MONTO", monto: "40000.00", moneda: "USD" },
    "FIRMAR",
  );

  const cargoPresupuestoResp = await request.post(`${API}/gobierno/estructuras/${ANIO}/cargos`, {
    headers: mundo.headers,
    data: {
      codigo: "C-PRES",
      denominacion: "Director de Presupuesto",
      unidad_id: estructura.despId,
      vigente_desde: `${ANIO}-01-01`,
    },
  });
  expect(cargoPresupuestoResp.status(), await cargoPresupuestoResp.text()).toBe(201);
  const cargoPresupuesto = (await cargoPresupuestoResp.json()) as CargoPresupuesto;

  const competenciaPresupuestoResp = await request.post(
    `${API}/gobierno/estructuras/${ANIO}/cargos/${cargoPresupuesto.id}/competencias`,
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
  expect(competenciaPresupuestoResp.status(), await competenciaPresupuestoResp.text()).toBe(201);

  await adjuntarDocumentoApi(
    request,
    mundo.headers,
    mundo.companyId,
    tipo.id,
    "GovernmentPosition",
    cargoPresupuesto.id,
  );

  const activarCargoPresupuestoResp = await request.post(
    `${API}/gobierno/estructuras/${ANIO}/cargos/${cargoPresupuesto.id}/activar`,
    {
      headers: { ...mundo.headers, "If-Match": '"2"' },
    },
  );
  expect(activarCargoPresupuestoResp.status(), await activarCargoPresupuestoResp.text()).toBe(200);

  const crearEjercicioResp = await request.post(`${API}/gobierno/presupuesto/ejercicios`, {
    headers: mundo.headers,
    data: { anio: ANIO },
  });
  expect(crearEjercicioResp.status(), await crearEjercicioResp.text()).toBe(201);
  const ejercicio = (await crearEjercicioResp.json()) as EjercicioPresupuestario;
  let versionPresupuesto = ejercicio.version;

  const nivelesResp = await request.put(`${API}/gobierno/presupuesto/ejercicios/${ejercicio.id}/niveles`, {
    headers: { ...mundo.headers, "If-Match": String(versionPresupuesto) },
    data: { niveles: [{ nombre: "Sector" }, { nombre: "Programa" }] },
  });
  expect(nivelesResp.status(), await nivelesResp.text()).toBe(200);
  versionPresupuesto = (await nivelesResp.json()).version;

  const cat01Resp = await request.post(`${API}/gobierno/presupuesto/ejercicios/${ejercicio.id}/categorias`, {
    headers: { ...mundo.headers, "If-Match": String(versionPresupuesto) },
    data: {
      nivel_orden: 1,
      parent_id: null,
      codigo: "01",
      denominacion: "Sector salud",
    },
  });
  expect(cat01Resp.status(), await cat01Resp.text()).toBe(201);
  const detalleCat01 = await cat01Resp.json();
  versionPresupuesto = detalleCat01.version;
  const cat01 = detalleCat01.categorias.find((c: { codigo_completo: string }) => c.codigo_completo === "01");

  const cat02Resp = await request.post(`${API}/gobierno/presupuesto/ejercicios/${ejercicio.id}/categorias`, {
    headers: { ...mundo.headers, "If-Match": String(versionPresupuesto) },
    data: {
      nivel_orden: 2,
      parent_id: cat01.id,
      codigo: "02",
      denominacion: "Atención primaria",
    },
  });
  expect(cat02Resp.status(), await cat02Resp.text()).toBe(201);
  const detalleCat02 = await cat02Resp.json();
  versionPresupuesto = detalleCat02.version;
  const cat02 = detalleCat02.categorias.find(
    (c: { codigo_completo: string }) => c.codigo_completo === "01.02",
  );

  await adjuntarDocumentoApi(request, mundo.headers, mundo.companyId, tipo.id, "GovernmentBudgetYear", ejercicio.id);
  await adjuntarDocumentoApi(request, mundo.headers, mundo.companyId, tipo.id, "GovernmentBudgetYear", ejercicio.id);
  await adjuntarDocumentoApi(request, mundo.headers, mundo.companyId, tipo.id, "GovernmentBudgetYear", ejercicio.id);

  const documentosPresupuestoResp = await request.get(`${API}/documentos/por-recurso/GovernmentBudgetYear/${ejercicio.id}`, { headers: mundo.headers });
  expect(documentosPresupuestoResp.status(), await documentosPresupuestoResp.text()).toBe(200);
  const documentosPresupuesto = (await documentosPresupuestoResp.json()) as Array<{ id: string }>;
  expect(documentosPresupuesto.length).toBeGreaterThanOrEqual(3);

  const clasificadorResp = await request.put(`${API}/gobierno/presupuesto/ejercicios/${ejercicio.id}/clasificador`, {
    headers: { ...mundo.headers, "If-Match": String(versionPresupuesto) },
    data: {
      edicion: "Clasificador del ente",
      procedencia: "Copia entregada por la Dirección de Presupuesto",
      documento_id: documentosPresupuesto[0].id,
    },
  });
  expect(clasificadorResp.status(), await clasificadorResp.text()).toBe(200);
  versionPresupuesto = (await clasificadorResp.json()).version;

  const partida301Resp = await request.post(`${API}/gobierno/presupuesto/ejercicios/${ejercicio.id}/clasificador/partidas`, {
    headers: { ...mundo.headers, "If-Match": String(versionPresupuesto) },
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
  expect(partida301Resp.status(), await partida301Resp.text()).toBe(201);
  versionPresupuesto = (await partida301Resp.json()).version;

  const partida401Resp = await request.post(`${API}/gobierno/presupuesto/ejercicios/${ejercicio.id}/clasificador/partidas`, {
    headers: { ...mundo.headers, "If-Match": String(versionPresupuesto) },
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
  expect(partida401Resp.status(), await partida401Resp.text()).toBe(201);
  versionPresupuesto = (await partida401Resp.json()).version;

  const partida40101Resp = await request.post(`${API}/gobierno/presupuesto/ejercicios/${ejercicio.id}/clasificador/partidas`, {
    headers: { ...mundo.headers, "If-Match": String(versionPresupuesto) },
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
  expect(partida40101Resp.status(), await partida40101Resp.text()).toBe(201);
  versionPresupuesto = (await partida40101Resp.json()).version;

  const fuentesResp = await request.post(`${API}/gobierno/presupuesto/ejercicios/${ejercicio.id}/fuentes`, {
    headers: { ...mundo.headers, "If-Match": String(versionPresupuesto) },
    data: {
      codigo: "F01",
      denominacion: "Ingresos propios",
      procedencia: "Ordenanza municipal de ingresos del ente",
    },
  });
  expect(fuentesResp.status(), await fuentesResp.text()).toBe(201);
  const fuentesDatos = await fuentesResp.json();
  versionPresupuesto = fuentesDatos.version;
  const fuenteF01 = fuentesDatos.items.find((f: { codigo: string }) => f.codigo === "F01");

  const partidasResp = await request.get(`${API}/gobierno/presupuesto/ejercicios/${ejercicio.id}/clasificador/partidas`, {
    headers: mundo.headers,
  });
  expect(partidasResp.status(), await partidasResp.text()).toBe(200);
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
      headers: { ...mundo.headers, "If-Match": String(versionPresupuesto) },
      data: {
        partida_id: partida301?.id,
        monto: "60000.00",
      },
    },
  );
  expect(ingresoResp.status(), await ingresoResp.text()).toBe(201);
  versionPresupuesto = (await ingresoResp.json()).version;

  const creditoResp = await request.post(
    `${API}/gobierno/presupuesto/ejercicios/${ejercicio.id}/presupuesto-aprobado/creditos`,
    {
      headers: { ...mundo.headers, "If-Match": String(versionPresupuesto) },
      data: {
        categoria_id: cat02.id,
        partida_id: partida40101?.id,
        fuente_id: fuenteF01.id,
        monto: "60000.00",
      },
    },
  );
  expect(creditoResp.status(), await creditoResp.text()).toBe(201);
  versionPresupuesto = (await creditoResp.json()).version;
  const credito = ((await creditoResp.json()) as { creditos: Array<{ id: string; partida: { codigo: string } }> }).creditos.find(
    (c) => c.partida.codigo === "401.01",
  ) as { id: string };

  const ejercicioActualResp = await request.get(`${API}/gobierno/presupuesto/ejercicios/${ejercicio.id}`, {
    headers: mundo.headers,
  });
  expect(ejercicioActualResp.status(), await ejercicioActualResp.text()).toBe(200);
  const ejercicioActual = await ejercicioActualResp.json();

  const aprobarPresupuestoResp = await request.post(
    `${API}/gobierno/presupuesto/ejercicios/${ejercicio.id}/aprobar`,
    {
      headers: { ...mundo.headers, "If-Match": String(ejercicioActual.version) },
      data: {
        referencia: "Gaceta Municipal Extraordinaria N.º 9",
        fecha: hoy,
        documento_id: documentosPresupuesto[1].id,
      },
    },
  );
  expect(aprobarPresupuestoResp.status(), await aprobarPresupuestoResp.text()).toBe(200);

  const certificacionResp = await request.post(
    `${API}/gobierno/presupuesto/ejercicios/${ejercicio.id}/certificaciones`,
    {
      headers: mundo.headers,
      data: {
        credito_id: credito.id,
        monto: "50000.00",
        concepto: "Adquisición contratada",
        expediente_id: expediente.id,
        firmante_cargo_id: cargoPresupuesto.id,
      },
    },
  );
  expect(certificacionResp.status(), await certificacionResp.text()).toBe(201);
  const certificacion = (await certificacionResp.json()) as CertificacionCreada;
  const codigoCdp = certificacion.codigo;

  await adjuntarDocumentoApi(request, mundo.headers, mundo.companyId, tipo.id, "GovernmentProcurementFile", expediente.id);
  const documentosInstrumento = (await (
    await request.get(`${API}/documentos/por-recurso/GovernmentProcurementFile/${expediente.id}`, { headers: mundo.headers })
  ).json()) as DocumentoConTitulo[];
  const documentoInstrumento = documentosInstrumento[documentosInstrumento.length - 1];

  const garantiaVersionResp = await request.get(
    `${API}/gobierno/contrataciones/expedientes/${expediente.id}/garantias`,
    { headers: mundo.headers },
  );
  expect(garantiaVersionResp.status(), await garantiaVersionResp.text()).toBe(200);
  const garantiaVersion = (await garantiaVersionResp.json()) as GarantiaVersion;

  const emisorGarantiaResp = await request.post(`${API}/gobierno/contrataciones/garantias/emisores`, {
    headers: { ...mundo.headers, "If-Match": String(garantiaVersion.version) },
    data: {
      tipo: "ASEGURADORA",
      nombre: "Aseguradora Caribe",
      rif: `J-${Date.now().toString().slice(-8)}-1`,
    },
  });
  expect(emisorGarantiaResp.status(), await emisorGarantiaResp.text()).toBe(201);
  const emisorGarantia = (await emisorGarantiaResp.json()) as { id: string };

  await adjuntarDocumentoApi(request, mundo.headers, mundo.companyId, tipo.id, "GovernmentProcurementFile", expediente.id);
  const documentosRequisito = (await (
    await request.get(`${API}/documentos/por-recurso/GovernmentProcurementFile/${expediente.id}`, { headers: mundo.headers })
  ).json()) as DocumentoConTitulo[];
  const documentoRequisitoId = documentosRequisito[documentosRequisito.length - 1].id;

  const requisitoResp = await request.post(`${API}/gobierno/contrataciones/expedientes/${expediente.id}/garantias/requisitos`, {
    headers: { ...mundo.headers, "If-Match": String(garantiaVersion.version) },
    data: {
      regla_codigo: "FIEL-1",
      porcentaje: "20",
      fundamento: "Pliego, cláusula 20",
      documento_id: documentoRequisitoId,
    },
  });
  expect(requisitoResp.status(), await requisitoResp.text()).toBe(201);
  const estadoRequisito = (await requisitoResp.json()) as { version: number; requisitos: Array<{ id: string }> };
  const requisito = estadoRequisito.requisitos[0];

  await adjuntarDocumentoApi(request, mundo.headers, mundo.companyId, tipo.id, "GovernmentProcurementFile", expediente.id);
  const documentosGarantia = (await (
    await request.get(`${API}/documentos/por-recurso/GovernmentProcurementFile/${expediente.id}`, { headers: mundo.headers })
  ).json()) as DocumentoConTitulo[];
  const documentoGarantiaId = documentosGarantia[documentosGarantia.length - 1].id;

  const fechaVigenteHasta = new Intl.DateTimeFormat("en-CA", { timeZone: "America/Caracas" }).format(
    new Date(Date.now() + 365 * 24 * 60 * 60 * 1000),
  );

  const garantiaResp = await request.post(`${API}/gobierno/contrataciones/expedientes/${expediente.id}/garantias`, {
    headers: { ...mundo.headers, "If-Match": String(estadoRequisito.version) },
    data: {
      requisito_id: requisito.id,
      oferta_id: oferta.id,
      emisor_id: emisorGarantia.id,
      referencia_emisor: "FC-0001",
      monto: "10000.00",
      moneda: "USD",
      fecha_emision: hoy,
      vigente_desde: hoy,
      vigente_hasta: fechaVigenteHasta,
      documento_id: documentoGarantiaId,
    },
  });
  expect(garantiaResp.status(), await garantiaResp.text()).toBe(201);

  await entrarEnGobierno(page, mundo.username, mundo.codigo, "/gobierno/contrataciones/expedientes");
  await cerrarNotificaciones(page);
  await page.getByRole("link", { name: new RegExp(expediente.numero) }).click();

  const seccionDecision = page.locator('[aria-labelledby="sec-decision"]');
  await expect(seccionDecision.getByRole("heading", { name: "Contrato u orden" })).toBeVisible();
  await expect(seccionDecision.getByRole("button", { name: "Crear contrato u orden" })).toBeVisible();
  await seccionDecision.getByRole("button", { name: "Crear contrato u orden" }).click();
  await page.waitForURL(/\/gobierno\/contratos\/[^/]+$/);

  await expect(page.getByText("Constructora Andina").first()).toBeVisible();
  await expect(page.getByText("Adquisición de equipos de prueba").first()).toBeVisible();
  await expect(page.getByText("50000.00 USD").first()).toBeVisible();
  await expect(page.getByRole("heading", { level: 1 }).filter({ hasText: "Borrador · " })).toBeVisible();

  const fechaFin = new Intl.DateTimeFormat("en-CA", { timeZone: "America/Caracas" }).format(
    new Date(Date.now() + 180 * 24 * 60 * 60 * 1000),
  );

  await page.selectOption("#contrato-tipo", "CONTRATO");
  await page.fill("#contrato-inicio", hoy);
  await page.fill("#contrato-fin", fechaFin);
  await page.fill("#contrato-referencia", "CT-INSTR-001");
  await page.selectOption("#contrato-documento", documentoInstrumento.id);
  await Promise.all([page.waitForResponse((r) => r.url().includes("/gobierno/contratos/") && r.request().method() === "PATCH"), page.getByRole("button", { name: "Guardar datos" }).click()]);
  await expect(page.getByRole("status").filter({ hasText: "Cambios guardados." })).toBeVisible();

  await page.fill(`#asignar-${codigoCdp}`, "40000.00");
  await Promise.all([page.waitForResponse((r) => r.url().includes("/cobertura") && r.request().method() === "PUT"), page.getByRole("button", { name: "Guardar cobertura" }).click()]);
  await expect(page.getByText("Falta: 10000.00 USD", { exact: false })).toBeVisible();

  await page.getByRole("checkbox", { name: /^GAR-01/ }).check();
  await Promise.all([page.waitForResponse((r) => r.url().includes("/garantias") && r.request().method() === "PUT"), page.getByRole("button", { name: "Guardar garantías" }).click()]);

  await page.selectOption("#contrato-firmante", firmanteSinLimite.id);
  await page.getByRole("button", { name: "Formalizar" }).click();
  const dialogoInsuficiente = page.getByRole("dialog");
  await dialogoInsuficiente.getByRole("button", { name: "Formalizar" }).click();
  await expect(page.getByRole("alert").filter({ hasText: "no es igual al monto del contrato" })).toBeVisible();

  await page.fill(`#asignar-${codigoCdp}`, "50000.00");
  await Promise.all([page.waitForResponse((r) => r.url().includes("/cobertura") && r.request().method() === "PUT"), page.getByRole("button", { name: "Guardar cobertura" }).click()]);
  await expect(page.getByText("Cobertura completa")).toBeVisible();

  await page.selectOption("#contrato-firmante", firmanteCorto.id);
  await expect(page.getByRole("region", { name: "Control del límite del firmante" }).getByText("Excede el límite", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Formalizar" }).click();
  const dialogoLimite = page.getByRole("dialog");
  await dialogoLimite.getByRole("button", { name: "Formalizar" }).click();
  await expect(page.getByRole("alert").filter({ hasText: "excede el límite de firma" })).toBeVisible();
  await expect(page.getByRole("heading", { level: 1 }).filter({ hasText: "Borrador · " })).toBeVisible();

  const axeBorrador = new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"]).analyze();
  const resultadoAxeBorrador = await axeBorrador;
  expect(
    resultadoAxeBorrador.violations.filter(
      (v) => v.impact === "serious" || v.impact === "critical",
    ),
  ).toEqual([]);

  await page.selectOption("#contrato-firmante", firmanteSinLimite.id);
  await page.getByRole("button", { name: "Formalizar" }).click();
  const dialogoFormalizar = page.getByRole("dialog");
  await dialogoFormalizar.getByRole("button", { name: "Formalizar" }).click();
  await expect(page.getByRole("status").filter({ hasText: /^Formalizado: CT-/ })).toBeVisible();
  const headingFormalizado = page.getByRole("heading", { level: 1 });
  const textoHeading = await headingFormalizado.textContent();
  const codigoContrato = textoHeading?.match(/CT-\d{4}-\d{4}/)?.[0];
  expect(codigoContrato).toBeTruthy();

  await expect(page.getByText("Instrumento formalizado")).toBeVisible();
  await expect(page.getByText(codigoContrato!).first()).toBeVisible();
  await expect(page.getByText(`Cargo CF-`).first()).toBeVisible();
  await expect(page.getByText("Cobertura").first()).toBeVisible();
  await expect(page.getByText(codigoCdp).first()).toBeVisible();
  await expect(page.getByText("GAR-01").first()).toBeVisible();
  await expect(page.getByRole("button", { name: "Formalizar" })).toHaveCount(0);

  const contratoId = page.url().split("/").pop();
  expect(contratoId).toBeTruthy();

  const dobleFormalizacionResp = await request.post(
    `${API}/gobierno/contratos/${contratoId}/formalizar`,
    {
      headers: { ...mundo.headers, "If-Match": "1" },
      data: { firmante_cargo_id: firmanteSinLimite.id },
    },
  );
  expect(dobleFormalizacionResp.status(), await dobleFormalizacionResp.text()).toBe(409);

  await page.getByRole("link", { name: new RegExp(expediente.numero) }).first().click();
  await expect(page.getByText("Ver contrato u orden")).toBeVisible();
  await expect(page.getByText(codigoContrato!).first()).toBeVisible();

  await page.goto("/gobierno/contratos");
  const filaContrato = page.locator("tr", { hasText: codigoContrato! });
  await expect(filaContrato).toBeVisible();
  await expect(filaContrato.getByRole("link")).toBeVisible();
  await filaContrato.getByRole("link").click();
  await page.waitForURL(/\/gobierno\/contratos\/[^/]+$/);
  await expect(page.getByText("Instrumento formalizado")).toBeVisible();

  const contratoApiResp = await request.get(`${API}/gobierno/contratos/${contratoId}`, {
    headers: mundo.headers,
  });
  expect(contratoApiResp.status(), await contratoApiResp.text()).toBe(200);
  const contratoApi = (await contratoApiResp.json()) as { estado: string; huella: string };
  expect(contratoApi.estado).toBe("FORMALIZADO");
  expect(contratoApi.huella).toMatch(/^[a-f0-9]{64}$/);

  const activadorOcupacion = await crearUsuario(
    request,
    admin.headers,
    ["organization:view", "gobierno_ocupacion:view", "gobierno_ocupacion:activate"],
    mundo.companyId,
  );
  const cargoSupA = await cargoVigenteApi(
    request,
    mundo.headers,
    mundo.companyId,
    tipo.id,
    ANIO,
    estructura.despId,
    `CSA-${Date.now()}`,
  );
  const cargoSupB = await cargoVigenteApi(
    request,
    mundo.headers,
    mundo.companyId,
    tipo.id,
    ANIO,
    estructura.despId,
    `CSB-${Date.now()}`,
  );
  const anaSup = await crearFuncionario(request, mundo.headers, "Ana Supervisora");
  const brunoSup = await crearFuncionario(request, mundo.headers, "Bruno Inspector");

  async function asignarTitular(funcionarioId: string, cargoId: string): Promise<string> {
    const resp = await request.post(`${API}/gobierno/ocupacion/asignaciones`, {
      headers: mundo.headers,
      data: {
        funcionario_id: funcionarioId,
        cargo_id: cargoId,
        figura: "TITULAR",
        acto_id: acto.id,
        desde: hoy,
        fundamento: "Designación de prueba CNT-04",
        cargo_origen_id: null,
        hasta: null,
        rendicion: null,
        maxima_autoridad: false,
        autorizacion_concejo: null,
        declara_delegable: false,
        competencias: [],
      },
    });
    expect(resp.status(), await resp.text()).toBe(201);
    const json: { id: string; version: number } = await resp.json();
    const actResp = await request.post(`${API}/gobierno/ocupacion/asignaciones/${json.id}/activar`, {
      headers: { ...activadorOcupacion.headers, "If-Match": `"${json.version}"` },
      data: {},
    });
    expect(actResp.status(), await actResp.text()).toBe(200);
    return json.id;
  }

  const asignacionAna = await asignarTitular(anaSup.id, cargoSupA.id);
  await asignarTitular(brunoSup.id, cargoSupB.id);
  const actoSupA = await actoEmitidoApi(request, mundo.headers, mundo.companyId, tipo.id, cargoSinLimite.id, hoy);
  const actoSupB = await actoEmitidoApi(request, mundo.headers, mundo.companyId, tipo.id, cargoSinLimite.id, hoy);
  const actoSupC = await actoEmitidoApi(request, mundo.headers, mundo.companyId, tipo.id, cargoSinLimite.id, hoy);

  await page.reload();
  const seccionSup = page.locator("section").filter({
    has: page.getByRole("heading", { name: "Supervisor / responsable del contrato", exact: true }),
  });
  await expect(seccionSup.getByText("Sin supervisor designado")).toBeVisible();

  await seccionSup.getByRole("button", { name: "Nueva designación", exact: true }).click();
  await page.waitForResponse((r) => r.request().method() === "GET" && new URL(r.url()).pathname.endsWith("/supervision/opciones"));
  await seccionSup.getByRole("combobox", { name: "Funcionario (obligatorio)", exact: true }).selectOption(anaSup.id);
  await expect(seccionSup.getByText(/^Cargo: Cargo CSA-/)).toBeVisible();
  await seccionSup.getByRole("combobox", { name: "Acto de designación (obligatorio)", exact: true }).selectOption(actoSupA.id);
  await seccionSup.getByRole("button", { name: "Formalizar designación", exact: true }).click();
  const dialogoSup = page.getByRole("dialog");
  await Promise.all([
    page.waitForResponse((r) => r.request().method() === "POST" && new URL(r.url()).pathname.endsWith("/supervision/designaciones")),
    dialogoSup.getByRole("button", { name: "Formalizar", exact: true }).click(),
  ]);
  await expect(seccionSup.getByRole("status")).toContainText("Designación SUP-01 registrada.");
  await expect(seccionSup).toContainText("Ana Supervisora");
  await expect(page.getByRole("region", { name: "Historial de supervisores" })).toContainText("SUP-01");

  const fechaProgramada = new Intl.DateTimeFormat("en-CA", { timeZone: "America/Caracas" }).format(
    new Date(Date.now() + 7 * 24 * 60 * 60 * 1000),
  );
  await seccionSup.getByRole("button", { name: "Sustituir supervisor", exact: true }).click();
  await page.fill("#supervision-desde", fechaProgramada);
  await page.waitForResponse(
    (r) => r.request().method() === "GET" && new URL(r.url()).pathname.endsWith("/supervision/opciones") && r.url().includes(`fecha=${fechaProgramada}`),
  );
  await page.getByRole("combobox", { name: "Funcionario (obligatorio)", exact: true }).selectOption(brunoSup.id);
  await page.getByRole("combobox", { name: "Acto de designación (obligatorio)", exact: true }).selectOption(actoSupB.id);
  await page.getByRole("textbox", { name: "Motivo del cambio (obligatorio)", exact: true }).fill("Traslado de la supervisora");
  await seccionSup.getByRole("button", { name: "Formalizar designación", exact: true }).click();
  await Promise.all([
    page.waitForResponse((r) => r.request().method() === "POST" && new URL(r.url()).pathname.endsWith("/supervision/designaciones")),
    dialogoSup.getByRole("button", { name: "Formalizar", exact: true }).click(),
  ]);
  await expect(seccionSup.getByRole("status")).toContainText("Designación SUP-02 registrada.");
  await expect(seccionSup.getByRole("heading", { name: "Designación programada", exact: true })).toBeVisible();
  await expect(seccionSup).toContainText("Bruno Inspector");
  await expect(page.getByRole("region", { name: "Historial de supervisores" })).toContainText("En ejercicio · Sustituida");
  await expect(page.getByRole("region", { name: "Historial de supervisores" })).toContainText("Programada · Vigente");

  const supHoyResp = await request.get(`${API}/gobierno/contratos/${contratoId}/supervision/en?fecha=${hoy}`, { headers: mundo.headers });
  expect(supHoyResp.status()).toBe(200);
  expect((await supHoyResp.json()).supervisor.referencia).toBe("SUP-01");
  const supFutResp = await request.get(`${API}/gobierno/contratos/${contratoId}/supervision/en?fecha=${fechaProgramada}`, { headers: mundo.headers });
  expect(supFutResp.status()).toBe(200);
  expect((await supFutResp.json()).supervisor.referencia).toBe("SUP-02");
  const supResp = await request.get(`${API}/gobierno/contratos/${contratoId}/supervision`, { headers: mundo.headers });
  expect(supResp.status()).toBe(200);
  const supervision = (await supResp.json()) as { ultima_id: string | null; programada: { id: string } | null };
  expect(supervision.ultima_id).toBe(supervision.programada?.id);

  const fechaConcurrente = new Intl.DateTimeFormat("en-CA", { timeZone: "America/Caracas" }).format(
    new Date(Date.now() + 10 * 24 * 60 * 60 * 1000),
  );
  const cuerpoConcurrente = {
    funcionario_id: anaSup.id,
    asignacion_id: asignacionAna,
    acto_id: actoSupC.id,
    desde: fechaConcurrente,
    motivo: "Prueba de concurrencia",
    sustituye_id: supervision.ultima_id,
  };
  const urlDesignacion = `${API}/gobierno/contratos/${contratoId}/supervision/designaciones`;
  const [r1, r2] = await Promise.all([
    request.post(urlDesignacion, { headers: mundo.headers, data: cuerpoConcurrente }),
    request.post(urlDesignacion, { headers: mundo.headers, data: cuerpoConcurrente }),
  ]);
  expect([r1.status(), r2.status()].sort()).toEqual([201, 409]);

  const auditoriaAsignada = await request.get(`${API}/gobierno/bitacora?accion=GOV_CONTRACT_SUPERVISOR_ASSIGNED`, { headers: mundo.headers });
  expect(auditoriaAsignada.status()).toBe(200);
  const asignadaTotal = ((await auditoriaAsignada.json()) as { total: number }).total;
  expect(asignadaTotal).toBeGreaterThanOrEqual(1);
  const auditoriaSustituida = await request.get(`${API}/gobierno/bitacora?accion=GOV_CONTRACT_SUPERVISOR_REPLACED`, { headers: mundo.headers });
  expect(auditoriaSustituida.status()).toBe(200);
  const sustituidaTotal = ((await auditoriaSustituida.json()) as { total: number }).total;
  expect(sustituidaTotal).toBeGreaterThanOrEqual(1);

  await page.reload();
  await expect(seccionSup.getByRole("heading", { name: "Designación programada", exact: true })).toBeVisible();
  const accesibilidadSup = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"]).analyze();
  const violacionesGravesSup = accesibilidadSup.violations.filter((v) => v.impact === "serious" || v.impact === "critical");
  expect(violacionesGravesSup).toEqual([]);

  // ===== CNT-03 · Ejecución del contrato (E2E del sponsor) =====
  type EjecucionE2E = {
    hitos: { id: string; descripcion: string }[];
    recepciones: { id: string; referencia: string }[];
  };

  const supervisorAna = await crearUsuario(
    request,
    admin.headers,
    ["organization:view", "gobierno_contratos:view", "gobierno_contratos:execute"],
    mundo.companyId
  );
  const activadorIdentidad = await crearUsuario(
    request,
    admin.headers,
    ["organization:view", "gobierno_identidad:view", "gobierno_identidad:activate"],
    mundo.companyId
  );

  const meResp = await request.get(`${API}/auth/me`, { headers: supervisorAna.headers });
  const supervisorUserId = ((await meResp.json()) as { user: { id: string } }).user.id;

  const vinculoResp = await request.post(`${API}/gobierno/identidad/vinculos`, {
    headers: mundo.headers,
    data: {
      user_id: supervisorUserId,
      official_id: anaSup.id,
      desde: hoy,
      hasta: null,
      motivo: "Cuenta institucional de la supervisora (CNT-03)",
      soporte: null
    }
  });
  expect(vinculoResp.status()).toBe(201);
  const vinculo = (await vinculoResp.json()) as { id: string; version: number };
  const activaResp = await request.post(`${API}/gobierno/identidad/vinculos/${vinculo.id}/activar`, {
    headers: { ...activadorIdentidad.headers, "If-Match": `"${vinculo.version}"` },
    data: {}
  });
  expect(activaResp.status()).toBe(200);

  for (let i = 0; i < 10; i++) {
    await adjuntarDocumentoApi(
      request,
      mundo.headers,
      mundo.companyId,
      tipo.id,
      "GovernmentProcurementFile",
      expediente.id
    );
  }

  const docsResp = await request.get(`${API}/documentos/por-recurso/GovernmentProcurementFile/${expediente.id}`, {
    headers: mundo.headers
  });
  const docsLista = (await docsResp.json()) as { id: string; titulo: string }[];
  const docs = docsLista.slice(-10).map((d) => d.id);

  await entrarEnGobierno(page, supervisorAna.username, mundo.codigo, "/gobierno/contratos");
  await cerrarNotificaciones(page);
  await page.getByRole("link", { name: new RegExp(codigoContrato!) }).click();
  await page.waitForURL(/\/gobierno\/contratos\/[^/]+$/);
  await page.getByRole("link", { name: "Ejecución del contrato" }).click();
  await page.waitForURL(/\/ejecucion$/);

  await expect(page.getByRole("heading", { name: "Resumen de la ejecución" })).toBeVisible();
  const seccionResumen = page.locator('section[aria-labelledby="resumen"]');
  await expect(seccionResumen).toContainText("Ana Supervisora");
  await expect(seccionResumen).toContainText("50000.00");

  const confirmarDialogo = async (sufijo: string, statusTexto: string, callback: () => Promise<void>): Promise<void> => {
    await callback();
    await Promise.all([
      page.waitForResponse(
        (r) => r.request().method() === "POST" && new URL(r.url()).pathname.endsWith(sufijo)
      ),
      page.getByRole("dialog").getByRole("button", { name: "Confirmar", exact: true }).click()
    ]);
    await expect(page.getByRole("status").filter({ hasText: statusTexto })).toBeVisible();
  };

  // 3 · Inicio
  await confirmarDialogo("/ejecucion/inicio", "Inicio de la ejecución registrado.", async () => {
    await page.fill("#inicio-fecha", hoy);
    await page.selectOption("#inicio-documento", docs[0]);
    await page.getByRole("button", { name: "Registrar inicio" }).click();
  });

  // 4 · Hito
  await confirmarDialogo("/ejecucion/hitos", "Hito registrado.", async () => {
    await page.fill("#hito-descripcion", "Entrega del lote 1");
    await page.fill("#hito-fecha", hoy);
    await page.fill("#hito-monto", "20000.00");
    await page.getByRole("button", { name: "Registrar hito" }).click();
  });
  await expect(page.locator('section[aria-labelledby="hitos"]')).toContainText("HIT-01");

  // 5 · Entregable
  let ejecucionResp = await request.get(`${API}/gobierno/contratos/${contratoId}/ejecucion`, {
    headers: mundo.headers
  });
  let ejecucion = (await ejecucionResp.json()) as EjecucionE2E;
  const hitoId = ejecucion.hitos[0].id;

  await confirmarDialogo("/ejecucion/entregables", "Entregable registrado.", async () => {
    await page.fill("#entregable-descripcion", "Informe del lote 1");
    await page.fill("#entregable-vencimiento", hoy);
    await page.selectOption("#entregable-hito", hitoId);
    await page.getByRole("button", { name: "Registrar entregable" }).click();
  });

  // 6 · Entrega y conformidad
  const seccionEntregables = page.locator('section[aria-labelledby="entregables"]');
  await seccionEntregables.getByRole("button", { name: "Registrar entrega", exact: true }).first().click();
  await confirmarDialogo("/entregas", "Entrega registrada.", async () => {
    await page.fill("#entrega-fecha", hoy);
    await page.selectOption("#entrega-evidencia", docs[1]);
    await seccionEntregables.getByRole("button", { name: "Registrar entrega", exact: true }).last().click();
  });
  await confirmarDialogo("/revision", "Entrega conformada.", async () => {
    await seccionEntregables.getByRole("button", { name: "Conformar", exact: true }).click();
    await seccionEntregables.getByRole("button", { name: "Confirmar revisión" }).click();
  });

  // 7 · Valuación
  await confirmarDialogo("/ejecucion/valuaciones", "Valuación presentada.", async () => {
    await page.selectOption("#valuacion-hito", hitoId);
    await page.fill("#valuacion-desde", hoy);
    await page.fill("#valuacion-hasta", hoy);
    await page.fill("#valuacion-fecha", hoy);
    await page.fill("#valuacion-monto", "15000.00");
    await page.selectOption("#valuacion-soporte", docs[2]);
    await page.getByRole("button", { name: "Presentar valuación" }).click();
  });
  await confirmarDialogo("/resolucion", "Valuación conformada.", async () => {
    await page.locator('section[aria-labelledby="valuaciones"]').getByRole("button", { name: "Conformar", exact: true }).click();
    await page.locator('section[aria-labelledby="valuaciones"]').getByRole("button", { name: "Confirmar resolución" }).click();
  });

  // 8 · Saldo
  await expect(seccionResumen).toContainText("35000.00");
  await expect(seccionResumen).toContainText("15000.00");

  // 9 · Recepción parcial
  await confirmarDialogo("/ejecucion/recepciones", "Recepción registrada.", async () => {
    await page.selectOption("#recepcion-tipo", "PARCIAL");
    await page.fill("#recepcion-fecha", hoy);
    await page.selectOption("#recepcion-documento", docs[3]);
    await page.getByRole("checkbox", { name: /HIT-01/ }).check();
    await page.getByRole("button", { name: "Registrar recepción" }).click();
  });
  await expect(page.locator('section[aria-labelledby="recepciones"]')).toContainText("REC-01");

  // 10 · Factura
  ejecucionResp = await request.get(`${API}/gobierno/contratos/${contratoId}/ejecucion`, {
    headers: mundo.headers
  });
  ejecucion = (await ejecucionResp.json()) as EjecucionE2E;
  const recepcionId = ejecucion.recepciones[0].id;

  await confirmarDialogo("/ejecucion/facturas", "Factura vinculada.", async () => {
    await page.fill("#factura-numero", "F-0001");
    await page.fill("#factura-fecha", hoy);
    await page.fill("#factura-monto", "15000.00");
    await page.selectOption("#factura-hito", hitoId);
    await page.selectOption("#factura-recepcion", recepcionId);
    await page.fill("#factura-conformidad", hoy);
    await page.selectOption("#factura-soporte", docs[4]);
    await page.getByRole("button", { name: "Vincular factura" }).click();
  });
  await expect(page.locator('section[aria-labelledby="facturas"]')).toContainText("FAC-01");

  // 11 · Negativa por API (sin conformidad de recepción)
  const hitoNuevoResp = await request.post(`${API}/gobierno/contratos/${contratoId}/ejecucion/hitos`, {
    headers: supervisorAna.headers,
    data: {
      descripcion: "Hito sin recepción",
      fecha_prevista: hoy,
      monto_previsto: null,
      porcentaje_previsto: null,
      obligatorio: false
    }
  });
  const hitoNuevoJson = (await hitoNuevoResp.json()) as EjecucionE2E;
  expect(hitoNuevoResp.status(), await hitoNuevoResp.text()).toBe(201);
  const hitoNuevoId = hitoNuevoJson.hitos.find((h) => h.descripcion === "Hito sin recepción")?.id ?? "";
  const facturaInvalidaResp = await request.post(
    `${API}/gobierno/contratos/${contratoId}/ejecucion/facturas`,
    {
      headers: supervisorAna.headers,
      data: {
        numero_documento: "F-SIN-RECEPCION",
        fecha: hoy,
        monto: "1.00",
        hito_id: hitoNuevoId,
        recepcion_id: recepcionId,
        documento_id: docs[5],
        fecha_conformidad: hoy
      }
    }
  );
  expect(facturaInvalidaResp.status()).toBe(422);
  expect(((await facturaInvalidaResp.json()) as { code: string }).code).toBe(
    "GOV_CONTRACT_EXEC_RECEIPT_INVALID"
  );
  await page.reload();
  await expect(page.getByRole("heading", { name: "Resumen de la ejecución" })).toBeVisible();

  // 12-13 · Recepción definitiva
  const seccionRecepciones = page.locator('section[aria-labelledby="recepciones"]');
  await confirmarDialogo("/ejecucion/recepciones", "Recepción registrada.", async () => {
    await page.selectOption("#recepcion-tipo", "DEFINITIVA");
    await page.fill("#recepcion-fecha", hoy);
    await page.selectOption("#recepcion-documento", docs[6]);
    await page.getByRole("button", { name: "Registrar recepción" }).click();
  });
  await expect(seccionRecepciones).toContainText(/definitiva/i);

  // 14 · Cierre
  await confirmarDialogo("/ejecucion/cierre", "Ejecución cerrada.", async () => {
    await page.fill("#cierre-fecha", hoy);
    await page.selectOption("#cierre-documento", docs[7]);
    await page.selectOption("#cierre-evaluacion", docs[8]);
    await page.getByRole("button", { name: "Cerrar ejecución" }).click();
  });
  await expect(seccionResumen).toContainText("Cerrada");

  // 15 · Historia
  await expect(page.locator('section[aria-labelledby="cronologia"]')).toContainText("HIT-01");
  await expect(page.locator('section[aria-labelledby="cronologia"]')).toContainText("VAL-01");
  await expect(page.locator('section[aria-labelledby="cronologia"]')).toContainText("REC-01");
  await expect(page.locator('section[aria-labelledby="cronologia"]')).toContainText("FAC-01");

  // 16 · Auditoría por API
  for (const accion of ["GOV_CONTRACT_EXEC_CLOSED", "GOV_CONTRACT_EXEC_INVOICE_LINKED"]) {
    const bitacoraResp = await request.get(`${API}/gobierno/bitacora?accion=${accion}`, {
      headers: mundo.headers
    });
    expect(bitacoraResp.status()).toBe(200);
    const bitacora = (await bitacoraResp.json()) as { total: number };
    expect(bitacora.total).toBeGreaterThanOrEqual(1);
  }

  // CSV
  const csvResp = await request.get(`${API}/gobierno/contratos/${contratoId}/ejecucion/reporte.csv`, {
    headers: mundo.headers
  });
  expect(csvResp.status()).toBe(200);
  expect(await csvResp.text()).toMatch(/^fecha,tipo,referencia,titulo,monto,moneda,estado/);

  // Axe en ejecución a 1280
  const axeResults = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
    .analyze();
  const violationsSeriousCritical = axeResults.violations.filter(
    (v) => v.impact === "serious" || v.impact === "critical"
  );
  expect(violationsSeriousCritical).toEqual([]);

  for (const ancho of [1280, 390, 320]) {
    await page.setViewportSize({ width: ancho, height: 800 });
    const sinDesbordamiento = await page.evaluate(
      () => document.documentElement.scrollWidth <= document.documentElement.clientWidth,
    );
    expect(sinDesbordamiento).toBe(true);

    if (ancho === 390 || ancho === 320) {
      const axeResponsive = new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"]).analyze();
      const resultadoAxeResponsive = await axeResponsive;
      expect(
        resultadoAxeResponsive.violations.filter(
          (v) => v.impact === "serious" || v.impact === "critical",
        ),
      ).toEqual([]);
    }
  }
});
