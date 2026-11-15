import type { APIRequestContext } from "@playwright/test";
import { expect } from "@playwright/test";
import {
  ANIO,
  API,
  RESPONSABLE_ESTRUCTURA,
  TENANT,
  adjuntarDocumentoApi,
  cargoVigenteApi,
  crearTipoDocumental,
  crearUsuario,
  declararMontoApi,
  enteActivo,
  estructuraVigenteApi,
  prepararMundo,
} from "./gobierno";
import { sesionApi } from "./sesion";

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

type CertificacionCreada = {
  id: string;
  codigo: string;
};

type ContratoCreado = {
  id: string;
  codigo: string;
  version: number;
  huella: string;
};


export type ContratoFormalizadoE2E = {
  mundo: Awaited<ReturnType<typeof prepararMundo>>;
  tipoId: string;
  hoy: string;
  fechaFin: string;
  expediente: { id: string; numero: string };
  ejercicioId: string;
  creditoId: string;
  cargoPresupuestoId: string;
  firmanteSinLimiteId: string;
  despId: string;
  documentosPresupuesto: { id: string }[];
  cdp: { id: string; codigo: string };
  contrato: { id: string; codigo: string; huella: string };
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

export async function prepararContratoFormalizado(
  request: APIRequestContext,
): Promise<ContratoFormalizadoE2E> {
  const hoy = new Intl.DateTimeFormat("en-CA", { timeZone: "America/Caracas" }).format(new Date());
  const fechaFin = new Intl.DateTimeFormat("en-CA", { timeZone: "America/Caracas" }).format(
    new Date(Date.now() + 180 * 24 * 60 * 60 * 1000),
  );

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
    "gobierno_presupuesto:view",
    "gobierno_presupuesto:manage",
    "gobierno_presupuesto:approve",
    "gobierno_presupuesto:certify",
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

  const criterioTecnico = await crearCriterio(request, mundo.headers, expediente.id, 1, {
    aspecto: "TECNICO",
    orden: 1,
    nombre: "Calidad técnica",
    descripcion: null,
    escala: "PUNTAJE",
    puntaje_maximo: "50.00",
    ponderacion: null,
  });

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

  const contratoResp = await request.post(`${API}/gobierno/contratos`, {
    headers: mundo.headers,
    data: {
      expediente_id: expediente.id,
    },
  });
  expect(contratoResp.status(), await contratoResp.text()).toBe(201);
  const contratoCreado = (await contratoResp.json()) as ContratoCreado;

  await adjuntarDocumentoApi(
    request,
    mundo.headers,
    mundo.companyId,
    tipo.id,
    "GovernmentProcurementFile",
    expediente.id,
  );
  const documentosInstrumento = (await (
    await request.get(`${API}/documentos/por-recurso/GovernmentProcurementFile/${expediente.id}`, { headers: mundo.headers })
  ).json()) as DocumentoConTitulo[];
  const documentoInstrumento = documentosInstrumento[documentosInstrumento.length - 1];

  const patchContratoResp = await request.patch(`${API}/gobierno/contratos/${contratoCreado.id}`, {
    headers: { ...mundo.headers, "If-Match": String(contratoCreado.version) },
    data: {
      tipo: "CONTRATO",
      fecha_inicio: hoy,
      fecha_fin: fechaFin,
      referencia_instrumento: "CT-INSTR-001",
      documento_id: documentoInstrumento.id,
    },
  });
  expect(patchContratoResp.status(), await patchContratoResp.text()).toBe(200);

  const coberturaResp = await request.put(`${API}/gobierno/contratos/${contratoCreado.id}/cobertura`, {
    headers: { ...mundo.headers, "If-Match": String(((await patchContratoResp.json()) as { version: number }).version) },
    data: {
      asignaciones: [{ certificado_id: certificacion.id, monto: "50000.00" }],
    },
  });
  expect(coberturaResp.status(), await coberturaResp.text()).toBe(200);

  const formalizarResp = await request.post(`${API}/gobierno/contratos/${contratoCreado.id}/formalizar`, {
    headers: { ...mundo.headers, "If-Match": String(((await coberturaResp.json()) as { version: number }).version) },
    data: { firmante_cargo_id: firmanteSinLimite.id },
  });
  expect(formalizarResp.status(), await formalizarResp.text()).toBe(200);

  const contratoFinalResp = await request.get(`${API}/gobierno/contratos/${contratoCreado.id}`, {
    headers: mundo.headers,
  });
  expect(contratoFinalResp.status(), await contratoFinalResp.text()).toBe(200);
  const contratoFinal = (await contratoFinalResp.json()) as {
    id: string;
    codigo: string;
    huella: string;
  };

  return {
    mundo,
    tipoId: tipo.id,
    hoy,
    fechaFin,
    expediente: { id: expediente.id, numero: expediente.numero },
    ejercicioId: ejercicio.id,
    creditoId: credito.id,
    cargoPresupuestoId: cargoPresupuesto.id,
    firmanteSinLimiteId: firmanteSinLimite.id,
    despId: estructura.despId,
    documentosPresupuesto,
    cdp: { id: certificacion.id, codigo: certificacion.codigo },
    contrato: {
      id: contratoFinal.id,
      codigo: contratoFinal.codigo,
      huella: contratoFinal.huella,
    },
  };
}
