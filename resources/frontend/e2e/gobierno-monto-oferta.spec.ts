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

type OfertaItem = {
  id: string;
  monto_estado: string;
  monto: unknown;
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

test("OMA · declarar y corregir el monto de la oferta, y verlo en la decisión", async ({ page, request }) => {
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

  const ofertasAntesResp = await request.get(
    `${API}/gobierno/contrataciones/expedientes/${expediente.id}/ofertas`,
    { headers: mundo.headers },
  );
  expect(ofertasAntesResp.status(), await ofertasAntesResp.text()).toBe(200);
  const ofertasAntes = (await ofertasAntesResp.json()) as { items: OfertaItem[] };
  const ofertaAntesItem = ofertasAntes.items.find((o) => o.id === oferta.id);
  expect(ofertaAntesItem).toBeTruthy();
  expect(ofertaAntesItem!.monto_estado).toBe("SELLADO");
  expect(ofertaAntesItem!.monto).toBeNull();

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

  await entrarEnGobierno(page, mundo.username, mundo.codigo, "/gobierno/contrataciones/expedientes");
  await cerrarNotificaciones(page);
  await page.getByRole("link", { name: new RegExp(expediente.numero) }).click();

  const secOfertas = page.locator('section[aria-labelledby="sec-ofertas"]');
  const tarjetaOferta = secOfertas.locator("li").filter({ hasText: "R-0001" }).first();
  await tarjetaOferta.getByRole("button", { name: "Ver detalle de R-0001" }).click();

  await page.getByRole("button", { name: "Declarar monto de R-0001" }).click();
  await page.getByLabel("Moneda", { exact: true }).selectOption("VES");
  await page.getByLabel("Monto del objeto sin IVA", { exact: true }).fill("1000.00");
  await page.getByLabel("Tributos", { exact: true }).fill("160.00");
  await page.getByLabel("Total con tributos", { exact: true }).fill("1160.00");
  await page.getByLabel("Documento soporte", { exact: true }).selectOption({ index: 1 });
  await page.getByRole("button", { name: "Registrar monto" }).click();

  await expect(tarjetaOferta.getByText("1160.00 VES (total con tributos)")).toBeVisible();

  const axeDeclarado = await new AxeBuilder({ page }).include('[aria-labelledby="sec-ofertas"]').analyze();
  expect(axeDeclarado.violations).toEqual([]);

  await page.getByRole("button", { name: "Corregir monto de R-0001" }).click();
  await page.getByLabel("Total con tributos", { exact: true }).fill("1170.00");
  await page.getByLabel("Documento soporte", { exact: true }).selectOption({ index: 2 });
  const botonRegistrarCorreccion = page.getByRole("button", { name: "Registrar monto" });
  await expect(botonRegistrarCorreccion).toBeDisabled();
  await page.getByLabel("Motivo de la corrección", { exact: true }).fill("Error de transcripción del total");
  await expect(botonRegistrarCorreccion).toBeEnabled();
  await botonRegistrarCorreccion.click();

  await expect(tarjetaOferta.getByText("1170.00 VES (total con tributos)")).toBeVisible();
  await expect(tarjetaOferta.getByText("La suma declarada no coincide con el total (diferencia 10.00 VES).")).toBeVisible();
  await expect(tarjetaOferta.getByRole("heading", { name: "Historial del monto" })).toBeVisible();
  await expect(tarjetaOferta.getByText("Motivo: Error de transcripción del total")).toBeVisible();

  const axeCorregido = await new AxeBuilder({ page }).include('[aria-labelledby="sec-ofertas"]').analyze();
  expect(axeCorregido.violations).toEqual([]);

  for (const viewport of [{ width: 390, height: 844 }, { width: 320, height: 568 }]) {
    await page.setViewportSize(viewport);
    const overflow = await page.evaluate(() => {
      const el = document.querySelector('section[aria-labelledby="sec-ofertas"]');
      return el ? el.scrollWidth <= el.clientWidth : true;
    });
    expect(overflow).toBe(true);
    const axeResponsive = await new AxeBuilder({ page }).include('[aria-labelledby="sec-ofertas"]').analyze();
    expect(axeResponsive.violations).toEqual([]);
  }
  await page.setViewportSize({ width: 1280, height: 720 });

  expediente = (await (
    await request.get(`${API}/gobierno/contrataciones/expedientes/${expediente.id}`, {
      headers: mundo.headers,
    })
  ).json()) as Expediente;

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

  await page.reload();
  const secOfertasFinal = page.locator('section[aria-labelledby="sec-ofertas"]');
  const tarjetaOfertaFinal = secOfertasFinal.locator("li").filter({ hasText: "R-0001" }).first();
  await tarjetaOfertaFinal.getByRole("button", { name: "Ver detalle de R-0001" }).click();
  await expect(tarjetaOfertaFinal.getByText("La evaluación está concluida: el monto ya no se registra ni se corrige")).toBeVisible();
  await expect(page.getByRole("button", { name: "Corregir monto de R-0001" })).toHaveCount(0);

  const secDecision = page.locator('section[aria-labelledby="sec-decision"]');
  await expect(secDecision.getByRole("columnheader", { name: "Monto declarado" })).toBeVisible();
  await expect(secDecision.getByRole("cell", { name: "1170.00 VES" })).toBeVisible();
  await expect(secDecision.getByRole("cell", { name: "No declarado" })).toBeVisible();
});

