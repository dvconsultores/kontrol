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
import { politicaHistoricaE2E } from "./helpers/politicaComision";

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

test("PROC-08 · emitir recomendación y registrar decisión desde la ficha del expediente", async ({ page, request }) => {
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
    "gobierno_tasas:view",
    "gobierno_tasas:manage",
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

  const politicaId = await politicaHistoricaE2E(request, mundo.companyId);
  const comisionResp = await request.post(`${API}/gobierno/contrataciones/comisiones`, {
    headers: mundo.headers,
    data: {
      nombre: "Comisión de evaluación E2E",
      tipo: "PERMANENTE",
      objeto: null,
      desde: hoy,
      hasta: null,
      acto_id: acto.id,
      politica_id: politicaId,
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
    monto_sin_iva: "43103.46",
    tributos: "6896.55",
    total_con_tributos: "50000.01",
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

  const actoInsuficiente = await actoDecisionEmitidoApi(
    request,
    mundo.headers,
    mundo.companyId,
    tipo.id,
    emisor.id,
    hoy,
  );
  const cargoSinLimite = await cargoVigenteApi(
    request,
    mundo.headers,
    mundo.companyId,
    tipo.id,
    ANIO,
    estructura.despId,
    `CS-${Date.now()}`,
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

  const aprobadorTasas = await crearUsuario(request, admin.headers, ["organization:view", "gobierno_tasas:view", "gobierno_tasas:approve", "documentos:view"], mundo.companyId);

  const tasaResp = await request.post(`${API}/gobierno/tesoreria/tasas`, {
    headers: mundo.headers,
    data: {
      moneda: "USD",
      fecha_efectiva: hoy,
      valor: "900.50",
      fuente_referencia: "BCV · tipo de cambio oficial de referencia",
    },
  });
  expect(tasaResp.status()).toBe(201);
  const tasa = (await tasaResp.json()) as { id: string; estado: string };
  await adjuntarDocumentoApi(request, mundo.headers, mundo.companyId, tipo.id, "GovernmentOfficialExchangeRate", tasa.id);
  const aprobarTasaResp = await request.post(`${API}/gobierno/tesoreria/tasas/${tasa.id}/aprobar`, {
    headers: aprobadorTasas.headers,
    data: {},
  });
  expect(aprobarTasaResp.status()).toBe(200);
  const tasaAprobada = (await aprobarTasaResp.json()) as { estado: string };
  expect(tasaAprobada.estado).toBe("APROBADA");

  const cargoVesBajo = await cargoVigenteApi(request, mundo.headers, mundo.companyId, tipo.id, ANIO, estructura.despId, `CVB-${Date.now()}`, {
    tipo_limite: "MONTO",
    monto: "45000000.00",
    moneda: "VES",
  });
  const cargoVesAlto = await cargoVigenteApi(request, mundo.headers, mundo.companyId, tipo.id, ANIO, estructura.despId, `CVA-${Date.now()}`, {
    tipo_limite: "MONTO",
    monto: "45100000.00",
    moneda: "VES",
  });
  const cargoEur = await cargoVigenteApi(request, mundo.headers, mundo.companyId, tipo.id, ANIO, estructura.despId, `CEU-${Date.now()}`, {
    tipo_limite: "MONTO",
    monto: "60000.00",
    moneda: "EUR",
  });
  const actoVesBajo = await actoDecisionEmitidoApi(request, mundo.headers, mundo.companyId, tipo.id, cargoVesBajo.id, hoy);
  const actoVesAlto = await actoDecisionEmitidoApi(request, mundo.headers, mundo.companyId, tipo.id, cargoVesAlto.id, hoy);
  const actoEur = await actoDecisionEmitidoApi(request, mundo.headers, mundo.companyId, tipo.id, cargoEur.id, hoy);

  await entrarEnGobierno(page, mundo.username, mundo.codigo, "/gobierno/contrataciones/expedientes");
  await cerrarNotificaciones(page);

  await page.getByRole("link", { name: expediente.numero, exact: true }).click();

  const sec = page.locator('[aria-labelledby="sec-decision"]');
  await expect(sec.getByRole("heading", { level: 2, name: "Recomendación y decisión" })).toBeVisible();
  await expect(sec.getByText("Concluida", { exact: false })).toBeVisible();
  await expect(sec.getByText("Preparar recomendación", { exact: false })).toBeVisible();
  await expect(sec.getByText("O-01", { exact: true })).toBeVisible();
  await expect(sec.getByText("O-02", { exact: true })).toBeVisible();
  await expect(sec.getByText("Constructora Andina", { exact: true })).toBeVisible();
  await expect(sec.getByText("Servicios Orinoco", { exact: true })).toBeVisible();

  const axeSec = new AxeBuilder({ page }).include('[aria-labelledby="sec-decision"]');
  const axeResultSec = await axeSec.analyze();
  expect(axeResultSec.violations).toEqual([]);

  const formularioRecomendacion = sec.locator("div").filter({ hasText: "Resultado recomendado" }).first();
  await formularioRecomendacion.locator("#resultado-recomendado").selectOption("ADJUDICAR");
  await formularioRecomendacion.locator("#motivacion-recomendacion").fill("Motivación de la recomendación");
  await formularioRecomendacion.locator("#examen-legal").fill("Examen legal favorable");
  await formularioRecomendacion.locator("#examen-financiero").fill("Examen financiero favorable");
  await formularioRecomendacion.locator("#examen-tecnico").fill("Examen técnico favorable");
  await formularioRecomendacion.locator("#resultado-matriz").fill("Resultado de la matriz favorable");
  await formularioRecomendacion.locator("#opcion-0").selectOption(oferta.id);
  await formularioRecomendacion.locator("#opcion-1").selectOption(oferta2.id);

  const firmantesGroup = sec.getByRole("group", { name: "Firmantes" });
  const checkboxes = firmantesGroup.getByRole("checkbox");
  const count = await checkboxes.count();
  for (let i = 0; i < count; i++) {
    await checkboxes.nth(i).check();
  }
  // El quórum lo fija la regla de la comisión (backend), no el navegador.
  await expect(sec.getByText("(requerido 2 de 3)", { exact: false })).toBeVisible();

  await sec.getByRole("button", { name: "Emitir recomendación", exact: true }).click();

  const axeConfirmacionRecomendacion = new AxeBuilder({ page }).include('[aria-labelledby="sec-decision"]');
  const axeResultConfirmacionRecomendacion = await axeConfirmacionRecomendacion.analyze();
  expect(axeResultConfirmacionRecomendacion.violations).toEqual([]);

  await page.setViewportSize({ width: 390, height: 844 });
  const overflow390 = await page.evaluate(
    () => document.documentElement.scrollWidth <= document.documentElement.clientWidth,
  );
  expect(overflow390).toBe(true);
  await page.setViewportSize({ width: 320, height: 568 });
  const overflow320 = await page.evaluate(
    () => document.documentElement.scrollWidth <= document.documentElement.clientWidth,
  );
  expect(overflow320).toBe(true);
  await page.setViewportSize({ width: 1280, height: 720 });

  const postRecomendacionPromise = page.waitForResponse(
    (r) => r.request().method() === "POST" && new URL(r.url()).pathname.endsWith("/decision/recomendaciones"),
  );
  await sec.getByRole("button", { name: "Confirmar emisión", exact: true }).click();
  const postRecomendacion = await postRecomendacionPromise;
  expect(postRecomendacion.status()).toBe(201);

  await expect(sec.getByText("REC-01", { exact: true })).toBeVisible();
  await expect(sec.getByText("Emitida: no se puede editar.", { exact: true })).toBeVisible();
  await expect(sec.getByText("Opción 1: O-01", { exact: false })).toBeVisible();
  await expect(sec.getByText("Opción 2: O-02", { exact: false })).toBeVisible();
  await expect(sec.getByRole("button", { name: "Emitir recomendación", exact: true })).toHaveCount(0);
  await expect(sec.locator("#motivo-sustitucion")).toBeVisible();

  const downloadPromise = page.waitForEvent("download");
  await sec.getByRole("button", { name: "Descargar informe (PDF)", exact: true }).click();
  const download = await downloadPromise;
  expect(download.suggestedFilename().endsWith(".pdf")).toBe(true);

  // 1. Autoridad insuficiente: el panel lo anticipa y el backend bloquea.
  await sec.locator("#acto-decision").selectOption(actoInsuficiente.id);
  await sec.getByRole("radio", { name: "Adjudicada", exact: true }).check();
  await expect(sec.locator("#oferta-decision")).toHaveValue(oferta.id);
  const panelLimite = sec.getByRole("region", { name: "Control del límite de autoridad" });
  await expect(panelLimite).toBeVisible();
  await expect(panelLimite.getByText("50000.01", { exact: true })).toBeVisible();
  await expect(panelLimite.getByText("USD", { exact: true })).toBeVisible();
  await expect(panelLimite.getByText("50000.00 USD", { exact: true })).toBeVisible();
  await expect(panelLimite.getByText("Excede el límite", { exact: true })).toBeVisible();
  const axePanelLimite = await new AxeBuilder({ page }).include('[aria-labelledby="control-limite-titulo"]').analyze();
  expect(axePanelLimite.violations).toEqual([]);
  await sec.locator("#motivacion-decision").fill("Motivación de la decisión de adjudicación");
  await sec.getByRole("button", { name: "Registrar decisión", exact: true }).click();
  const postBloqueadaPromise = page.waitForResponse(
    (r) => r.request().method() === "POST" && new URL(r.url()).pathname.endsWith("/decision/decisiones"),
  );
  await sec.getByRole("button", { name: "Confirmar decisión", exact: true }).click();
  const postBloqueada = await postBloqueadaPromise;
  expect(postBloqueada.status()).toBe(409);
  expect(((await postBloqueada.json()) as { code: string }).code).toBe("GOV_DECISION_AUTHORITY_AMOUNT_EXCEEDED");
  await expect(sec.getByRole("alert")).toContainText("excede el límite de aprobación");
  await expect(sec.getByText("DEC-01", { exact: true })).toHaveCount(0);
  await sec
    .getByRole("button", { name: "Confirmar decisión", exact: true })
    .locator("..")
    .getByRole("button", { name: "Cancelar", exact: true })
    .click();

  // 1b. Límite en EUR sin tasa oficial EUR: el panel lo anticipa y el backend bloquea.
  await sec.locator("#acto-decision").selectOption(actoEur.id);
  await expect(panelLimite.getByText("Sin tasa oficial aprobada", { exact: true })).toBeVisible();
  await expect(panelLimite.getByRole("heading", { name: "Tasa oficial BCV utilizada" })).toHaveCount(0);
  await sec.getByRole("button", { name: "Registrar decisión", exact: true }).click();
  const postSinTasaPromise = page.waitForResponse((r) => r.request().method() === "POST" && new URL(r.url()).pathname.endsWith("/decision/decisiones"));
  await sec.getByRole("button", { name: "Confirmar decisión", exact: true }).click();
  const postSinTasa = await postSinTasaPromise;
  expect(postSinTasa.status()).toBe(422);
  const postSinTasaBody = (await postSinTasa.json()) as { code: string };
  expect(postSinTasaBody.code).toBe("GOV_OFFICIAL_RATE_REQUIRED");
  await expect(sec.getByRole("alert")).toContainText("Tasas oficiales");
  await expect(sec.getByText("DEC-01", { exact: true })).toHaveCount(0);
  await sec.getByRole("button", { name: "Confirmar decisión", exact: true }).locator("..").getByRole("button", { name: "Cancelar", exact: true }).click();

  // 1c. Límite en VES con tasa oficial: equivalente insuficiente.
  await sec.locator("#acto-decision").selectOption(actoVesBajo.id);
  await expect(panelLimite.getByRole("heading", { name: "Tasa oficial BCV utilizada", exact: true })).toBeVisible();
  await expect(panelLimite).toContainText("1 USD = ");
  await expect(panelLimite).toContainText("BCV · tipo de cambio oficial de referencia");
  await expect(panelLimite.getByText("Excede el límite", { exact: true })).toBeVisible();
  const axePanelVes = await new AxeBuilder({ page }).include('[aria-labelledby="control-limite-titulo"]').analyze();
  expect(axePanelVes.violations).toEqual([]);
  await sec.getByRole("button", { name: "Registrar decisión", exact: true }).click();
  const postVesBajoPromise = page.waitForResponse((r) => r.request().method() === "POST" && new URL(r.url()).pathname.endsWith("/decision/decisiones"));
  await sec.getByRole("button", { name: "Confirmar decisión", exact: true }).click();
  const postVesBajo = await postVesBajoPromise;
  expect(postVesBajo.status()).toBe(409);
  const postVesBajoBody = (await postVesBajo.json()) as { code: string };
  expect(postVesBajoBody.code).toBe("GOV_DECISION_AUTHORITY_AMOUNT_EXCEEDED");
  await sec.getByRole("button", { name: "Confirmar decisión", exact: true }).locator("..").getByRole("button", { name: "Cancelar", exact: true }).click();

  // 2. Autoridad sin límite y autoridad con límite en VES y tasa suficiente: se adjudica con la segunda.
  await sec.locator("#acto-decision").selectOption(actoDecision.id);
  await expect(panelLimite.getByText("Sin límite", { exact: true })).toHaveCount(2);
  await sec.locator("#acto-decision").selectOption(actoVesAlto.id);
  await expect(panelLimite.getByText("Dentro del límite", { exact: true })).toBeVisible();
  await expect(panelLimite.getByRole("heading", { name: "Tasa oficial BCV utilizada", exact: true })).toBeVisible();
  await sec.getByRole("button", { name: "Registrar decisión", exact: true }).click();

  const axeConfirmacionDecision = new AxeBuilder({ page }).include('[aria-labelledby="sec-decision"]');
  const axeResultConfirmacionDecision = await axeConfirmacionDecision.analyze();
  expect(axeResultConfirmacionDecision.violations).toEqual([]);

  await page.setViewportSize({ width: 390, height: 844 });
  const overflow390Decision = await page.evaluate(
    () => document.documentElement.scrollWidth <= document.documentElement.clientWidth,
  );
  expect(overflow390Decision).toBe(true);
  await page.setViewportSize({ width: 320, height: 568 });
  const overflow320Decision = await page.evaluate(
    () => document.documentElement.scrollWidth <= document.documentElement.clientWidth,
  );
  expect(overflow320Decision).toBe(true);
  await page.setViewportSize({ width: 1280, height: 720 });

  const postDecisionPromise = page.waitForResponse(
    (r) => r.request().method() === "POST" && new URL(r.url()).pathname.endsWith("/decision/decisiones"),
  );
  await sec.getByRole("button", { name: "Confirmar decisión", exact: true }).click();
  const postDecision = await postDecisionPromise;
  expect(postDecision.status()).toBe(201);

  await expect(sec.getByText("DEC-01", { exact: true }).first()).toBeVisible();
  await expect(sec.getByText("Adjudicada", { exact: true }).first()).toBeVisible();
  await expect(sec.getByRole("link", { name: new RegExp(actoVesAlto.numero) })).toBeVisible();
  await expect(sec.getByRole("heading", { name: "Conversión de autoridad de DEC-01", exact: true })).toBeVisible();
  const estadoDecisionResp = await request.get(`${API}/gobierno/contrataciones/expedientes/${expediente.id}/decision`, { headers: mundo.headers });
  expect(estadoDecisionResp.status()).toBe(200);
  const estadoDecision = (await estadoDecisionResp.json()) as { decisiones: Array<{ conversion: { tasas: Array<{ tasa_id: string }> } | null }> };
  expect(estadoDecision.decisiones[0].conversion?.tasas[0].tasa_id).toBe(tasa.id);
  await expect(sec.getByText("Sin notificación", { exact: true })).toHaveCount(2);
  await expect(
    sec.getByText("El registro de notificaciones se hace en el acto administrativo (DOC-04).", { exact: false }),
  ).toBeVisible();

  const notificacionResp = await request.post(`${API}/gobierno/notificaciones`, {
    headers: mundo.headers,
    data: {
      acto_id: actoVesAlto.id,
      tipo_persona: "JURIDICA",
      nombre: "Constructora Andina",
      identificacion: "J-12345678-9",
      domicilio: "Calle 1, Caracas",
      recursos: "Recurso de reconsideración (LOPA art. 94)",
    },
  });
  expect(notificacionResp.status(), await notificacionResp.text()).toBe(201);

  await page.reload();
  await cerrarNotificaciones(page);
  const secReload = page.locator('[aria-labelledby="sec-decision"]');
  await expect(secReload.getByText("Pendiente", { exact: true }).first()).toBeVisible();

  await expect(secReload.getByText("REC-01", { exact: true }).first()).toBeVisible();
  await expect(secReload.getByText("DEC-01", { exact: true })).toBeVisible();
  await expect(secReload.getByRole("heading", { name: "Conversión de autoridad de DEC-01", exact: true })).toBeVisible();

  const axeFinal = new AxeBuilder({ page }).include('[aria-labelledby="sec-decision"]');
  const axeResultFinal = await axeFinal.analyze();
  expect(axeResultFinal.violations).toEqual([]);

  await page.setViewportSize({ width: 390, height: 844 });
  const overflow390Final = await page.evaluate(
    () => document.documentElement.scrollWidth <= document.documentElement.clientWidth,
  );
  expect(overflow390Final).toBe(true);
  await page.setViewportSize({ width: 320, height: 568 });
  const overflow320Final = await page.evaluate(
    () => document.documentElement.scrollWidth <= document.documentElement.clientWidth,
  );
  expect(overflow320Final).toBe(true);
  await page.setViewportSize({ width: 1280, height: 720 });

  await expect(secReload.getByRole("heading", { name: "Contrato u orden", exact: true })).toBeVisible();
});
