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
  enteActivo,
  entrarEnGobierno,
  estructuraVigenteApi,
  prepararMundo,
} from "./helpers/gobierno";

test.setTimeout(420_000);

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

test("PROC-10 · registrar, renovar y liberar garantías desde la ficha del expediente", async ({ page, request }) => {
  const hoy = new Intl.DateTimeFormat("en-CA", { timeZone: "America/Caracas" }).format(new Date());

  const mundo = await prepararMundo(request, [
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
    "gobierno_evaluacion:view",
    "gobierno_evaluacion:criteria",
    "gobierno_evaluacion:open",
    "gobierno_evaluacion:evaluate",
    "gobierno_decision:view",
    "gobierno_decision:recommend",
    "gobierno_decision:decide",
    "gobierno_garantias:view",
    "gobierno_garantias:manage",
    "gobierno_garantias:release",
    "gobierno_garantias:execute",
    "gobierno_notificaciones:view",
    "gobierno_notificaciones:edit",
    "gobierno_notificaciones:record",
    "documentos:view",
    "documentos:download",
    "documentos:link",
    "documentos:upload",
  ]);

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

  const actoDecision = await actoDecisionEmitidoApi(
    request,
    mundo.headers,
    mundo.companyId,
    tipo.id,
    emisor.id,
    hoy,
  );

  // B1 Adjudicación por API
  const expedienteReloadB1 = await request.get(`${API}/gobierno/contrataciones/expedientes/${expediente.id}`, {
    headers: mundo.headers,
  });
  expect(expedienteReloadB1.status(), await expedienteReloadB1.text()).toBe(200);
  expediente = (await expedienteReloadB1.json()) as Expediente;

  const recomendacionResp = await request.post(
    `${API}/gobierno/contrataciones/expedientes/${expediente.id}/decision/recomendaciones`,
    {
      headers: { ...mundo.headers, "If-Match": String(expediente.version) },
      data: {
        resultado_recomendado: "ADJUDICAR",
        causal_desierta: null,
        motivacion: "Motivación E2E",
        examen_legal: "Examen legal E2E",
        examen_financiero: "Examen financiero E2E",
        examen_tecnico: "Examen técnico E2E",
        resultado_matriz: "Resultado de la matriz E2E",
        medidas_promocion: null,
        firmante_ids: Object.values(miembroIds),
        opciones: [{ posicion: 1, offer_id: oferta.id }, { posicion: 2, offer_id: oferta2.id }],
        rechazos: [],
      },
    },
  );
  expect(recomendacionResp.status(), await recomendacionResp.text()).toBe(201);
  const recomendacionJson = (await recomendacionResp.json()) as { recomendacion_vigente: { id: string } };
  const recomendacionId = recomendacionJson.recomendacion_vigente.id;

  const expedienteReloadB1b = await request.get(`${API}/gobierno/contrataciones/expedientes/${expediente.id}`, {
    headers: mundo.headers,
  });
  expect(expedienteReloadB1b.status(), await expedienteReloadB1b.text()).toBe(200);
  expediente = (await expedienteReloadB1b.json()) as Expediente;

  const decisionResp = await request.post(
    `${API}/gobierno/contrataciones/expedientes/${expediente.id}/decision/decisiones`,
    {
      headers: { ...mundo.headers, "If-Match": String(expediente.version) },
      data: {
        resultado: "ADJUDICADA",
        recomendacion_id: recomendacionId,
        acto_id: actoDecision.id,
        oferta_id: oferta.id,
        motivacion: "Adjudicación E2E",
      },
    },
  );
  expect(decisionResp.status(), await decisionResp.text()).toBe(201);

  // B2 Documentos para garantías
  const PDF = Buffer.from("%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n");

  async function documentoExpedienteApi(
    request: APIRequestContext,
    headers: Record<string, string>,
    companyId: string,
    tipoId: string,
    expedienteId: string,
    titulo: string,
  ): Promise<string> {
    const docResp = await request.post(`${API}/documentos`, {
      headers,
      data: {
        company_id: companyId,
        document_type_id: tipoId,
        title: titulo,
      },
    });
    expect(docResp.ok(), await docResp.text()).toBe(true);
    const doc = (await docResp.json()) as { id: string };

    const versionResp = await request.post(`${API}/documentos/${doc.id}/versiones`, {
      headers,
      multipart: {
        file: {
          name: `${titulo}.pdf`,
          mimeType: "application/pdf",
          buffer: PDF,
        },
      },
    });
    expect(versionResp.ok(), await versionResp.text()).toBe(true);

    const vinculoResp = await request.post(`${API}/documentos/${doc.id}/vinculos`, {
      headers,
      data: { resource_type: "GovernmentProcurementFile", resource_id: expedienteId },
    });
    expect(vinculoResp.ok(), await vinculoResp.text()).toBe(true);

    return doc.id;
  }

  const docPliego = await documentoExpedienteApi(request, mundo.headers, mundo.companyId, tipo.id, expediente.id, "Pliego garantías E2E");
  const docFianza = await documentoExpedienteApi(request, mundo.headers, mundo.companyId, tipo.id, expediente.id, "Fianza mantenimiento E2E");
  const docProrroga = await documentoExpedienteApi(request, mundo.headers, mundo.companyId, tipo.id, expediente.id, "Endoso de prórroga E2E");
  const docFiel = await documentoExpedienteApi(request, mundo.headers, mundo.companyId, tipo.id, expediente.id, "Fianza de fiel cumplimiento E2E");

  // B3 Fechas
  function masDias(fecha: string, dias: number): string {
    const [anio, mes, dia] = fecha.split("-").map(Number);
    const d = new Date(Date.UTC(anio, mes - 1, dia + dias));
    return d.toISOString().slice(0, 10);
  }

  // B4 Garantía de fiel cumplimiento por API
  const emisorFielResp = await request.post(`${API}/gobierno/contrataciones/garantias/emisores`, {
    headers: mundo.headers,
    data: {
      tipo: "ASEGURADORA",
      nombre: "Aseguradora Fiel E2E",
      rif: "J-40000001-0",
    },
  });
  expect(emisorFielResp.status(), await emisorFielResp.text()).toBe(201);
  const emisorFiel = (await emisorFielResp.json()) as { id: string };

  const estadoGarantiasResp = await request.get(
    `${API}/gobierno/contrataciones/expedientes/${expediente.id}/garantias`,
    { headers: mundo.headers },
  );
  expect(estadoGarantiasResp.status(), await estadoGarantiasResp.text()).toBe(200);
  let estadoGarantias = (await estadoGarantiasResp.json()) as {
    version: number;
    requisitos: Array<{ id: string; referencia: string; regla: { codigo: string } }>;
    garantias: Array<{ id: string; referencia: string; estado: string; requisito_id: string }>;
    emisores: Array<{ id: string; nombre: string }>;
  };

  const requisitoFielResp = await request.post(
    `${API}/gobierno/contrataciones/expedientes/${expediente.id}/garantias/requisitos`,
    {
      headers: { ...mundo.headers, "If-Match": String(estadoGarantias.version) },
      data: {
        regla_codigo: "FIEL-1",
        porcentaje: "20",
        fundamento: "Pliego, cláusula 20",
        documento_id: docPliego,
      },
    },
  );
  expect(requisitoFielResp.status(), await requisitoFielResp.text()).toBe(201);
  estadoGarantias = (await requisitoFielResp.json()) as typeof estadoGarantias;
  const requisitoFiel = estadoGarantias.requisitos.find((r) => r.regla.codigo === "FIEL-1");
  expect(requisitoFiel).toBeTruthy();

  const garantiaFielResp = await request.post(
    `${API}/gobierno/contrataciones/expedientes/${expediente.id}/garantias`,
    {
      headers: { ...mundo.headers, "If-Match": String(estadoGarantias.version) },
      data: {
        requisito_id: requisitoFiel!.id,
        oferta_id: oferta.id,
        emisor_id: emisorFiel.id,
        referencia_emisor: "FC-0001",
        monto: "5000.00",
        moneda: "USD",
        fecha_emision: hoy,
        vigente_desde: hoy,
        vigente_hasta: masDias(hoy, 365),
        documento_id: docFiel,
      },
    },
  );
  expect(garantiaFielResp.status(), await garantiaFielResp.text()).toBe(201);
  estadoGarantias = (await garantiaFielResp.json()) as typeof estadoGarantias;

  // B5 Interfaz
  await entrarEnGobierno(page, mundo.username, mundo.codigo, "/gobierno/contrataciones/expedientes");
  await cerrarNotificaciones(page);
  await page.getByRole("link", { name: new RegExp(expediente.numero) }).click();

  const sec = page.locator('section[aria-labelledby="sec-garantias"]');
  await expect(sec.getByRole("heading", { level: 2, name: "Garantías y cauciones" })).toBeVisible();
  await expect(sec.getByLabel("Resumen de garantías")).toBeVisible();
  await expect(sec.getByText("Adjudicación vigente: DEC-01 · O-01 (Constructora Andina)")).toBeVisible();

  const estadoGarantiasB5Resp = await request.get(
    `${API}/gobierno/contrataciones/expedientes/${expediente.id}/garantias`,
    { headers: mundo.headers },
  );
  expect(estadoGarantiasB5Resp.status(), await estadoGarantiasB5Resp.text()).toBe(200);
  const estadoGarantiasB5 = (await estadoGarantiasB5Resp.json()) as typeof estadoGarantias;
  const garantiaFielId = estadoGarantiasB5.garantias.find((g) => g.referencia === "GAR-01")!.id;
  const tarjetaFiel = sec.locator(`article[aria-labelledby="gar-${garantiaFielId}"]`);
  await expect(tarjetaFiel.getByText("Suficiencia: No evaluable")).toBeVisible();
  await expect(tarjetaFiel.getByText("BASE_MONETARIA_NO_DISPONIBLE")).toBeVisible();

  const axeB5 = await new AxeBuilder({ page }).include('[aria-labelledby="sec-garantias"]').analyze();
  expect(axeB5.violations).toEqual([]);

  // B6 Emisor por la interfaz
  await sec.getByRole("button", { name: "Nuevo emisor" }).click();
  await sec.locator("#emi-tipo").selectOption("ASEGURADORA");
  await sec.locator("#emi-nombre").fill("Seguros Sintéticos E2E");
  await sec.locator("#emi-rif").fill("J-40000002-0");
  const emisorUiRespPromise = page.waitForResponse(
    (r) => r.request().method() === "POST" && new URL(r.url()).pathname.endsWith("/garantias/emisores"),
  );
  await sec.getByRole("button", { name: "Registrar emisor" }).click();
  const emisorUiResp = await emisorUiRespPromise;
  expect(emisorUiResp.status()).toBe(201);
  await expect(sec.getByText("Seguros Sintéticos E2E", { exact: false })).toBeVisible();

  // B7 Requisito por la interfaz
  await sec.getByRole("button", { name: "Nuevo requisito" }).click();
  await sec.locator("#req-regla").selectOption("MANT-FIJO-1");
  await sec.locator("#req-monto").fill("1000");
  await sec.locator("#req-moneda").selectOption("VES");
  await sec.locator("#req-vigencia").fill(masDias(hoy, 60));
  await sec.locator("#req-fundamento").fill("Pliego, cláusula 12");
  await sec.locator("#req-documento").selectOption(docPliego);

  const axeB7 = await new AxeBuilder({ page }).include('[aria-labelledby="sec-garantias"]').analyze();
  expect(axeB7.violations).toEqual([]);

  const requisitoUiRespPromise = page.waitForResponse(
    (r) => r.request().method() === "POST" && new URL(r.url()).pathname.endsWith("/garantias/requisitos"),
  );
  await sec.getByRole("button", { name: "Registrar requisito" }).click();
  const requisitoUiResp = await requisitoUiRespPromise;
  expect(requisitoUiResp.status()).toBe(201);
  await expect(sec.getByText("REQ-02 · Mantenimiento de oferta")).toBeVisible();

  // B8 Garantía por la interfaz
  const estadoGarantiasB8Resp = await request.get(
    `${API}/gobierno/contrataciones/expedientes/${expediente.id}/garantias`,
    { headers: mundo.headers },
  );
  expect(estadoGarantiasB8Resp.status(), await estadoGarantiasB8Resp.text()).toBe(200);
  const estadoGarantiasB8 = (await estadoGarantiasB8Resp.json()) as typeof estadoGarantias;
  const requisitoMant = estadoGarantiasB8.requisitos.find((r) => r.referencia === "REQ-02")!;
  const emisorSintetico = estadoGarantiasB8.emisores.find((e) => e.nombre === "Seguros Sintéticos E2E")!;

  await sec.getByRole("button", { name: "Registrar garantía" }).click();
  await sec.locator("#gar-requisito").selectOption(requisitoMant.id);
  await sec.locator("#gar-oferta").selectOption(oferta2.id);
  await sec.locator("#gar-emisor").selectOption(emisorSintetico.id);
  await sec.locator("#gar-referencia").fill("FZ-0001");
  await sec.locator("#gar-monto").fill("1000");
  await sec.locator("#gar-moneda").selectOption("VES");
  await sec.locator("#gar-emision").fill(hoy);
  await sec.locator("#gar-desde").fill(hoy);
  await sec.locator("#gar-hasta").fill(masDias(hoy, 30));
  await sec.locator("#gar-documento").selectOption(docFianza);

  const garantiaUiRespPromise = page.waitForResponse(
    (r) =>
      r.request().method() === "POST" &&
      new URL(r.url()).pathname.endsWith(`/expedientes/${expediente.id}/garantias`),
  );
  await sec.getByRole("button", { name: "Registrar", exact: true }).click();
  const garantiaUiResp = await garantiaUiRespPromise;
  expect(garantiaUiResp.status()).toBe(201);

  const estadoGarantiasB8bResp = await request.get(
    `${API}/gobierno/contrataciones/expedientes/${expediente.id}/garantias`,
    { headers: mundo.headers },
  );
  expect(estadoGarantiasB8bResp.status(), await estadoGarantiasB8bResp.text()).toBe(200);
  const estadoGarantiasB8b = (await estadoGarantiasB8bResp.json()) as typeof estadoGarantias;
  const garantiaMant = estadoGarantiasB8b.garantias.find((g) => g.referencia === "GAR-02")!;
  const tarjetaMant = sec.locator(`article[aria-labelledby="gar-${garantiaMant.id}"]`);
  await expect(tarjetaMant.getByText("Suficiencia: Insuficiente")).toBeVisible();
  await expect(tarjetaMant.getByText("Vigencia mínima: No cumple", { exact: false })).toBeVisible();
  await expect(tarjetaMant.locator('dd').filter({ hasText: /^Vigente$/ })).toBeVisible();

  // B9 Renovación
  await tarjetaMant.getByRole("button", { name: "Renovar" }).click();
  await sec.locator(`#ren-hasta-${garantiaMant.id}`).fill(masDias(hoy, 90));
  await sec.locator(`#ren-documento-${garantiaMant.id}`).selectOption(docProrroga);
  await sec.locator(`#ren-motivo-${garantiaMant.id}`).fill("Prórroga de la oferta (LCP art. 71)");

  const renovarRespPromise = page.waitForResponse(
    (r) => r.request().method() === "POST" && new URL(r.url()).pathname.endsWith(`/${garantiaMant.id}/renovar`),
  );
  await sec.getByRole("button", { name: "Renovar garantía" }).click();
  const renovarResp = await renovarRespPromise;
  expect(renovarResp.status()).toBe(201);

  const estadoGarantiasB9Resp = await request.get(
    `${API}/gobierno/contrataciones/expedientes/${expediente.id}/garantias`,
    { headers: mundo.headers },
  );
  expect(estadoGarantiasB9Resp.status(), await estadoGarantiasB9Resp.text()).toBe(200);
  const estadoGarantiasB9 = (await estadoGarantiasB9Resp.json()) as typeof estadoGarantias;
  const garantiaRenovada = estadoGarantiasB9.garantias.find((g) => g.referencia === "GAR-03")!;
  expect(garantiaRenovada.estado).toBe("REGISTRADA");

  await expect(tarjetaMant.getByText("Renovada")).toBeVisible();
  const tarjetaRenovada = sec.locator(`article[aria-labelledby="gar-${garantiaRenovada.id}"]`);
  await expect(tarjetaRenovada.getByText("Suficiencia: Suficiente")).toBeVisible();

  const abrirHistorial = async (tarjeta: ReturnType<typeof sec.locator>, recuento: number) => {
    const details = tarjeta.locator("details");
    const summary = details.locator("summary", { hasText: `Historial (${recuento})` });
    const estaAbierto = await details.evaluate((el) => el.hasAttribute("open"));
    if (!estaAbierto) {
      await summary.click();
    }
    await expect(details).toHaveAttribute("open", "");
    await expect(summary).toHaveText(`Historial (${recuento})`);
  };

  await abrirHistorial(tarjetaRenovada, 2);
  const historialRenovada = tarjetaRenovada.locator('details ol');
  await expect(historialRenovada.getByText("Registro", { exact: false })).toBeVisible();
  await expect(historialRenovada.getByText("Renovación", { exact: false })).toBeVisible();

  const axeB9 = await new AxeBuilder({ page }).include('[aria-labelledby="sec-garantias"]').analyze();
  expect(axeB9.violations).toEqual([]);

  // B10 Liberación con confirmación
  await tarjetaRenovada.getByRole("button", { name: "Liberar" }).click();
  await sec.locator(`#lib-acto-${garantiaRenovada.id}`).selectOption(actoDecision.id);
  await sec.locator(`#lib-motivo-${garantiaRenovada.id}`).fill("Oferente no adjudicado");
  await sec.getByRole("button", { name: "Liberar garantía" }).click();
  await expect(sec.getByText("La liberación no se puede deshacer.")).toBeVisible();

  const axeB10 = await new AxeBuilder({ page }).include('[aria-labelledby="sec-garantias"]').analyze();
  expect(axeB10.violations).toEqual([]);

  for (const viewport of [{ width: 390, height: 844 }, { width: 320, height: 568 }]) {
    await page.setViewportSize(viewport);
    const overflow = await page.evaluate(() => {
      const el = document.querySelector('section[aria-labelledby="sec-garantias"]');
      return el ? el.scrollWidth <= el.clientWidth : true;
    });
    expect(overflow).toBe(true);
  }
  await page.setViewportSize({ width: 1280, height: 720 });

  const liberarRespPromise = page.waitForResponse(
    (r) => r.request().method() === "POST" && new URL(r.url()).pathname.endsWith(`/${garantiaRenovada.id}/liberar`),
  );
  await sec.getByRole("button", { name: "Confirmar liberación" }).click();
  const liberarResp = await liberarRespPromise;
  expect(liberarResp.status()).toBe(201);

  await expect(tarjetaRenovada.getByText("Liberada")).toBeVisible();
  await abrirHistorial(tarjetaRenovada, 3);
  const historialLiberada = tarjetaRenovada.locator('details ol');
  await expect(historialLiberada.getByText("Precondición: Verificada", { exact: false })).toBeVisible();
  await expect(historialLiberada.getByText("DEC-01", { exact: false })).toBeVisible();

  // B10b Sustitución de la garantía de fiel cumplimiento por la interfaz
  const estadoGarantiasB10bResp = await request.get(
    `${API}/gobierno/contrataciones/expedientes/${expediente.id}/garantias`,
    { headers: mundo.headers },
  );
  expect(estadoGarantiasB10bResp.status(), await estadoGarantiasB10bResp.text()).toBe(200);
  const estadoGarantiasB10b = (await estadoGarantiasB10bResp.json()) as typeof estadoGarantias;
  const garantiaFielB10b = estadoGarantiasB10b.garantias.find((g) => g.referencia === "GAR-01")!;
  const tarjetaFielB10b = sec.locator(`article[aria-labelledby="gar-${garantiaFielB10b.id}"]`);

  await tarjetaFielB10b.getByRole("button", { name: "Sustituir" }).click();
  await sec.locator(`#sus-emisor-${garantiaFielB10b.id}`).selectOption(emisorFiel.id);
  await sec.locator(`#sus-referencia-${garantiaFielB10b.id}`).fill("FC-0002");
  await sec.locator(`#sus-monto-${garantiaFielB10b.id}`).fill("5000.00");
  await sec.locator(`#sus-moneda-${garantiaFielB10b.id}`).selectOption("USD");
  await sec.locator(`#sus-emision-${garantiaFielB10b.id}`).fill(hoy);
  await sec.locator(`#sus-desde-${garantiaFielB10b.id}`).fill(hoy);
  await sec.locator(`#sus-hasta-${garantiaFielB10b.id}`).fill(masDias(hoy, 365));
  await sec.locator(`#sus-documento-${garantiaFielB10b.id}`).selectOption(docFiel);
  await sec.locator(`#sus-motivo-${garantiaFielB10b.id}`).fill("Sustitución por cambio de póliza");

  const sustituirRespPromise = page.waitForResponse(
    (r) => r.request().method() === "POST" && new URL(r.url()).pathname.endsWith(`/${garantiaFielB10b.id}/sustituir`),
  );
  await sec.getByRole("button", { name: "Sustituir garantía" }).click();
  const sustituirResp = await sustituirRespPromise;
  expect(sustituirResp.status()).toBe(201);

  const estadoGarantiasB10cResp = await request.get(
    `${API}/gobierno/contrataciones/expedientes/${expediente.id}/garantias`,
    { headers: mundo.headers },
  );
  expect(estadoGarantiasB10cResp.status(), await estadoGarantiasB10cResp.text()).toBe(200);
  const estadoGarantiasB10c = (await estadoGarantiasB10cResp.json()) as typeof estadoGarantias;
  const garantiaSustituida = estadoGarantiasB10c.garantias.find((g) => g.referencia === "GAR-04")!;
  expect(garantiaSustituida.estado).toBe("REGISTRADA");

  await expect(tarjetaFielB10b.getByText("Sustituida")).toBeVisible();
  const tarjetaSustituida = sec.locator(`article[aria-labelledby="gar-${garantiaSustituida.id}"]`);
  await expect(tarjetaSustituida.getByRole('heading', { name: /GAR-04/ })).toBeVisible();
  await expect(tarjetaSustituida.locator('dd').filter({ hasText: /^GAR-01$/ })).toBeVisible();

  await abrirHistorial(tarjetaSustituida, 2);
  const historialSustituida = tarjetaSustituida.locator('details ol');
  await expect(historialSustituida.getByText("Registro", { exact: false })).toBeVisible();
  await expect(historialSustituida.getByText("Sustitución", { exact: false })).toBeVisible();
  await expect(historialSustituida.getByText("GAR-01 → GAR-04", { exact: false })).toBeVisible();

  // B10c Ejecución de la garantía sustituida por la interfaz
  await tarjetaSustituida.getByRole("button", { name: "Ejecutar" }).click();
  await sec.locator(`#eje-acto-${garantiaSustituida.id}`).selectOption(actoDecision.id);
  await sec.locator(`#eje-motivo-${garantiaSustituida.id}`).fill("Incumplimiento de contrato");
  await sec.locator(`#eje-monto-${garantiaSustituida.id}`).fill("1000.00");
  await sec.getByRole("button", { name: "Ejecutar garantía" }).click();
  await expect(sec.getByText("La ejecución no se puede deshacer.")).toBeVisible();

  const axeB10c = await new AxeBuilder({ page }).include('[aria-labelledby="sec-garantias"]').analyze();
  expect(axeB10c.violations).toEqual([]);

  const ejecutarRespPromise = page.waitForResponse(
    (r) => r.request().method() === "POST" && new URL(r.url()).pathname.endsWith(`/${garantiaSustituida.id}/ejecutar`),
  );
  await sec.getByRole("button", { name: "Confirmar ejecución" }).click();
  const ejecutarResp = await ejecutarRespPromise;
  expect(ejecutarResp.status()).toBe(201);

  await expect(tarjetaSustituida.getByText("Ejecutada")).toBeVisible();
  await abrirHistorial(tarjetaSustituida, 3);
  const historialEjecutada = tarjetaSustituida.locator('details ol');
  await expect(historialEjecutada.getByText("Ejecución", { exact: false })).toBeVisible();
  await expect(historialEjecutada.getByText("1.000,00 USD", { exact: false })).toBeVisible();

  // B11 Cronología del expediente
  await page.reload();
  await expect(sec.getByRole("heading", { level: 2, name: "Garantías y cauciones" })).toBeVisible();
  const cronologiaSec = page.locator('section[aria-labelledby="sec-cronologia"]');
  await expect(cronologiaSec.getByText("Garantía GAR-03 liberada", { exact: false })).toBeVisible();
  await expect(cronologiaSec.getByText("Garantía GAR-01 sustituida por GAR-04", { exact: false })).toBeVisible();
  await expect(cronologiaSec.getByText("Garantía GAR-04 ejecutada por 1000.00 USD", { exact: false })).toBeVisible();

  // B12 Estado final
  const estadoGarantiasB12Resp = await request.get(
    `${API}/gobierno/contrataciones/expedientes/${expediente.id}/garantias`,
    { headers: mundo.headers },
  );
  expect(estadoGarantiasB12Resp.status(), await estadoGarantiasB12Resp.text()).toBe(200);
  const estadoGarantiasB12 = (await estadoGarantiasB12Resp.json()) as typeof estadoGarantias;
  const garantiaEjecutadaB12 = estadoGarantiasB12.garantias.find((g) => g.referencia === "GAR-04")!;
  const tarjetaEjecutadaB12 = sec.locator(`article[aria-labelledby="gar-${garantiaEjecutadaB12.id}"]`);
  await abrirHistorial(tarjetaEjecutadaB12, 3);

  const axeB12 = await new AxeBuilder({ page }).include('[aria-labelledby="sec-garantias"]').analyze();
  expect(axeB12.violations).toEqual([]);

  for (const viewport of [{ width: 390, height: 844 }, { width: 320, height: 568 }]) {
    await page.setViewportSize(viewport);
    const overflowGarantias = await page.evaluate(() => {
      const el = document.querySelector('section[aria-labelledby="sec-garantias"]');
      return el ? el.scrollWidth <= el.clientWidth : true;
    });
    expect(overflowGarantias).toBe(true);
    const overflowCronologia = await page.evaluate(() => {
      const el = document.querySelector('section[aria-labelledby="sec-cronologia"]');
      return el ? el.scrollWidth <= el.clientWidth : true;
    });
    expect(overflowCronologia).toBe(true);
  }
  await page.setViewportSize({ width: 1280, height: 720 });
});
