import { AxeBuilder } from "@axe-core/playwright";
import type { APIRequestContext } from "@playwright/test";
import { expect, sesionApi, test } from "./helpers/sesion";
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

test("PROC-07 · abrir y evaluar ofertas desde la ficha del expediente", async ({ page, request }) => {
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
  const actaId = docsActaAntes[docsActaAntes.length - 1].id;

  const docSelladoResp = await request.get(`${API}/documentos/${ofertaDocId}`, { headers: mundo.headers });
  expect(docSelladoResp.status(), await docSelladoResp.text()).toBe(404);

  await entrarEnGobierno(page, mundo.username, mundo.codigo, "/gobierno/contrataciones/expedientes");
  await cerrarNotificaciones(page);
  await page.getByRole("link", { name: expediente.numero }).click();
  const sec = page.locator('[aria-labelledby="sec-evaluacion"]');
  await expect(sec.getByRole("heading", { level: 2, name: "Apertura y evaluación" })).toBeVisible();

  await expect(sec.getByText(/^Concluida ·/)).toBeVisible();
  await expect(sec.getByRole("heading", { level: 3, name: "Matriz de evaluación", exact: true })).toBeVisible();
  await expect(sec.getByRole("heading", { level: 4, name: "Técnico", exact: true })).toBeVisible();
  await expect(sec.getByRole("heading", { level: 4, name: "Económico", exact: true })).toBeVisible();
  await expect(sec.getByRole("heading", { level: 4, name: "Legal", exact: true })).toBeVisible();
  await expect(sec.getByRole("heading", { level: 4, name: "Calidad técnica", exact: true })).toBeVisible();
  await expect(sec.getByRole("heading", { level: 4, name: "Precio ofertado", exact: true })).toBeVisible();
  await expect(sec.getByRole("heading", { level: 4, name: "Capacidad legal", exact: true })).toBeVisible();

  const axe1 = await new AxeBuilder({ page }).include('[aria-labelledby="sec-evaluacion"]').analyze();
  expect(axe1.violations).toEqual([]);

  await sec.getByRole("button", { name: "Bloquear matriz" }).click();
  await expect(sec.getByText("Al bloquear, los criterios quedan fijos")).toBeVisible();
  await sec.getByRole("button", { name: "Confirmar bloqueo" }).click();
  await expect(sec.getByText("Matriz bloqueada: criterios fijos para la evaluación")).toBeVisible();
  await cerrarNotificaciones(page);

  const estadoBloqueoResp = await request.get(
    `${API}/gobierno/contrataciones/expedientes/${expediente.id}/evaluacion`,
    { headers: mundo.headers },
  );
  expect(estadoBloqueoResp.status(), await estadoBloqueoResp.text()).toBe(200);
  const estadoBloqueo = (await estadoBloqueoResp.json()) as MatrizEstado;
  const criterioPostBloqueoResp = await request.post(
    `${API}/gobierno/contrataciones/expedientes/${expediente.id}/evaluacion/matriz/criterios`,
    {
      headers: { ...mundo.headers, "If-Match": String(estadoBloqueo.matriz.version) },
      data: {
        aspecto: "TECNICO",
        orden: 2,
        nombre: "Criterio post bloqueo",
        descripcion: null,
        escala: "PUNTAJE",
        puntaje_maximo: "10.00",
        ponderacion: null,
      },
    },
  );
  expect(criterioPostBloqueoResp.status(), await criterioPostBloqueoResp.text()).toBe(409);
  expect(((await criterioPostBloqueoResp.json()) as { code?: string }).code).toBe("GOV_EVAL_MATRIX_LOCKED");

  const tarjetaOferta = sec
    .getByRole("listitem")
    .filter({ has: page.getByRole("heading", { level: 4, name: "O-01", exact: true }) });
  await expect(
    tarjetaOferta.getByRole("definition").filter({ hasText: /^Sellada hasta la apertura$/ }),
  ).toBeVisible();
  await expect(tarjetaOferta.getByText("Constructora Andina")).toBeVisible();

  for (const width of [390, 320]) {
    await page.setViewportSize({ width, height: 800 });
    const sinDesborde = await page.evaluate(
      () => document.documentElement.scrollWidth <= document.documentElement.clientWidth,
    );
    expect(sinDesborde).toBe(true);
    await expect(sec.getByRole("button", { name: "Registrar apertura" })).toBeVisible();
    await sec.getByRole("button", { name: "Registrar apertura" }).click();
    await expect(sec.getByRole("group", { name: "Ofertas a abrir" })).toBeVisible();
    await expect(sec.getByRole("group", { name: "Asistentes" })).toBeVisible();
    await expect(sec.getByRole("button", { name: "Abrir ofertas" })).toBeVisible();
    await sec.getByRole("button", { name: "Cancelar", exact: true }).click();
  }
  await page.setViewportSize({ width: 1280, height: 800 });

  await sec.getByRole("button", { name: "Registrar apertura" }).click();
  const axe2 = await new AxeBuilder({ page }).include('[aria-labelledby="sec-evaluacion"]').analyze();
  expect(axe2.violations).toEqual([]);

  const checkboxOferta = sec.getByRole("checkbox", { name: /O-01/ });
  await expect(checkboxOferta).not.toBeChecked();
  await checkboxOferta.check();

  await sec.getByRole("checkbox", { name: /^Evaluadora Técnica/ }).check();
  await sec.getByRole("checkbox", { name: /^Secretaria de la Comisión/ }).check();
  await expect(sec.getByRole("status").filter({ hasText: "Sin quórum" })).toBeVisible();
  await sec.locator("#apertura-acta").selectOption(actaId);
  await sec.getByRole("button", { name: "Abrir ofertas" }).click();
  await sec.getByRole("button", { name: "Confirmar apertura" }).click();
  await expect(sec.getByRole("alert").filter({ hasText: "Sin quórum: se requieren" })).toBeVisible();
  await expect(
    tarjetaOferta.getByRole("definition").filter({ hasText: /^Sellada hasta la apertura$/ }),
  ).toBeVisible();

  await sec.getByRole("checkbox", { name: /^Evaluador Jurídico/ }).check();
  await sec.getByRole("checkbox", { name: /^Evaluadora Financiera/ }).check();
  await expect(sec.getByRole("status").filter({ hasText: "Hay quórum" })).toBeVisible();
  await expect(sec.getByText("Esta acción abrirá las ofertas seleccionadas y liberará su contenido")).toBeVisible();
  await sec.getByRole("button", { name: "Confirmar apertura" }).click();
  await expect(sec.getByRole("status").filter({ hasText: "Ofertas abiertas" })).toBeVisible();
  await expect(tarjetaOferta.getByText("Abierta", { exact: true })).toBeVisible();
  await expect(tarjetaOferta.getByText("Sellada hasta la apertura", { exact: true })).toHaveCount(0);
  await expect(
    tarjetaOferta.getByRole("definition").filter({ hasText: /^Sello levantado en la apertura$/ }),
  ).toBeVisible();

  const tarjetaApertura = sec
    .locator("li")
    .filter({ has: page.getByRole("heading", { level: 4, name: "A-01", exact: true }) });
  await expect(tarjetaApertura.getByText("Registrada por", { exact: true })).toBeVisible();
  await expect(tarjetaApertura.getByRole("definition").filter({ hasText: mundo.username })).toBeVisible();
  await expect(
    tarjetaApertura.getByRole("definition").filter({ hasText: /^3 de 3 miembros con voto \(requerido 2\)$/ }),
  ).toBeVisible();
  await expect(tarjetaApertura.getByRole("link", { name: "Acto de prueba", exact: true })).toHaveAttribute(
    "href",
    `/documentos/${actaId}`,
  );
  await cerrarNotificaciones(page);

  const expedienteReload2 = await request.get(`${API}/gobierno/contrataciones/expedientes/${expediente.id}`, {
    headers: mundo.headers,
  });
  expect(expedienteReload2.status(), await expedienteReload2.text()).toBe(200);
  const expedienteActual = (await expedienteReload2.json()) as Expediente;

  const dobleAperturaResp = await request.post(
    `${API}/gobierno/contrataciones/expedientes/${expediente.id}/evaluacion/aperturas`,
    {
      headers: { ...mundo.headers, "If-Match": String(expedienteActual.version) },
      data: {
        abierta_en: new Date().toISOString(),
        oferta_ids: [oferta.id],
        miembro_ids: [
          miembroIds["Evaluadora Técnica"],
          miembroIds["Evaluador Jurídico"],
          miembroIds["Evaluadora Financiera"],
          miembroIds["Secretaria de la Comisión"],
        ],
        acta_documento_id: actaId,
        observaciones: null,
      },
    },
  );
  expect(dobleAperturaResp.status(), await dobleAperturaResp.text()).toBe(409);
  expect(((await dobleAperturaResp.json()) as { code?: string }).code).toBe("GOV_OFFER_ALREADY_OPENED");

  const estadoAntesResp = await request.get(
    `${API}/gobierno/contrataciones/expedientes/${expediente.id}/evaluacion`,
    { headers: mundo.headers },
  );
  expect(estadoAntesResp.status(), await estadoAntesResp.text()).toBe(200);
  const estadoAntes = (await estadoAntesResp.json()) as {
    resultados_por_oferta: Array<{ aportes: unknown[] }>;
  };
  const totalAportesAntes = estadoAntes.resultados_por_oferta.reduce(
    (total, ofertaEstado) => total + ofertaEstado.aportes.length,
    0,
  );

  const expedienteAntesResp = await request.get(
    `${API}/gobierno/contrataciones/expedientes/${expediente.id}`,
    { headers: mundo.headers },
  );
  expect(expedienteAntesResp.status(), await expedienteAntesResp.text()).toBe(200);
  const expedienteAntes = (await expedienteAntesResp.json()) as Expediente;

  const aporteViejoResp = await request.post(
    `${API}/gobierno/contrataciones/expedientes/${expediente.id}/evaluacion/aportes`,
    {
      headers: mundo.headers,
      data: {
        oferta_id: oferta.id,
        criterio_id: criterioTecnico.id,
        miembro_id: miembroIds["Evaluadora Técnica"],
        matriz_version: estadoBloqueo.matriz.version - 1,
        puntaje: "45.00",
        observacion: "Aporte de prueba",
        evidencia_documento_id: null,
      },
    },
  );
  expect(aporteViejoResp.status(), await aporteViejoResp.text()).toBe(409);
  expect(((await aporteViejoResp.json()) as { code?: string }).code).toBe("GOV_EVAL_MATRIX_STALE");

  const estadoDespuesResp = await request.get(
    `${API}/gobierno/contrataciones/expedientes/${expediente.id}/evaluacion`,
    { headers: mundo.headers },
  );
  expect(estadoDespuesResp.status(), await estadoDespuesResp.text()).toBe(200);
  const estadoDespues = (await estadoDespuesResp.json()) as {
    resultados_por_oferta: Array<{ aportes: unknown[] }>;
  };
  const totalAportesDespues = estadoDespues.resultados_por_oferta.reduce(
    (total, ofertaEstado) => total + ofertaEstado.aportes.length,
    0,
  );
  expect(totalAportesDespues).toBe(totalAportesAntes);

  const expedienteDespuesResp = await request.get(
    `${API}/gobierno/contrataciones/expedientes/${expediente.id}`,
    { headers: mundo.headers },
  );
  expect(expedienteDespuesResp.status(), await expedienteDespuesResp.text()).toBe(200);
  const expedienteDespues = (await expedienteDespuesResp.json()) as Expediente;
  expect(expedienteDespues.version).toBe(expedienteAntes.version);

  const docLiberadoResp = await request.get(`${API}/documentos/${ofertaDocId}`, { headers: mundo.headers });
  expect(docLiberadoResp.status(), await docLiberadoResp.text()).toBe(200);

  await sec.getByRole("button", { name: "Ver documentos de O-01" }).click();
  const enlaceDocumento = tarjetaOferta.getByRole("link", { name: "Acto de prueba", exact: true });
  await expect(enlaceDocumento).toBeVisible();
  await expect(enlaceDocumento).toHaveAttribute("href", `/documentos/${ofertaDocId}`);
  await enlaceDocumento.click();
  await page.waitForURL(`**/documentos/${ofertaDocId}`);
  await expect(page.getByRole("heading", { level: 1, name: "Acto de prueba" })).toBeVisible();
  await page.goBack();
  await expect(sec.getByRole("heading", { level: 2, name: "Apertura y evaluación" })).toBeVisible();

  const aportes: Array<{
    criterio: string;
    criterioId: string;
    evaluador: string;
    puntaje?: string;
    cumple?: boolean;
  }> = [
    { criterio: "Calidad técnica", criterioId: criterioTecnico.id, evaluador: "Evaluadora Técnica", puntaje: "45.00" },
    { criterio: "Precio ofertado", criterioId: criterioEconomico.id, evaluador: "Evaluador Jurídico", puntaje: "40.00" },
    { criterio: "Capacidad legal", criterioId: criterioLegal.id, evaluador: "Evaluadora Financiera", cumple: true },
  ];

  const tarjetaCriterio = (criterio: string) =>
    sec
      .locator("div.rounded-lg")
      .filter({ has: page.getByRole("heading", { level: 4, name: criterio, exact: true }) })
      .filter({ hasText: "Aportes" });

  for (const aporte of aportes) {
    await sec.getByRole("button", { name: `Registrar aporte de ${aporte.criterio} para O-01` }).click();
    await sec.locator(`#aporte-O-01-${aporte.criterioId}-miembro`).selectOption(miembroIds[aporte.evaluador]);
    if (aporte.puntaje !== undefined) {
      await sec.locator(`#aporte-O-01-${aporte.criterioId}-puntaje`).fill(aporte.puntaje);
    } else if (aporte.cumple) {
      await sec.getByRole("radio", { name: "Cumple", exact: true }).check();
    }
    await sec.getByRole("button", { name: "Guardar aporte" }).click();
    await expect(sec.getByRole("button", { name: "Guardar aporte" })).toHaveCount(0);

    const tarjeta = tarjetaCriterio(aporte.criterio);
    const liAporte = tarjeta.getByRole("listitem").filter({ hasText: aporte.evaluador });
    await expect(liAporte.getByText(aporte.puntaje ?? "Cumple", { exact: true })).toBeVisible();
    await expect(liAporte.getByText("Vigente", { exact: true })).toBeVisible();
    await cerrarNotificaciones(page);
  }

  await sec.getByRole("button", { name: "Registrar aporte de Calidad técnica para O-01" }).click();
  await sec.locator(`#aporte-O-01-${criterioTecnico.id}-miembro`).selectOption(miembroIds["Evaluadora Técnica"]);
  await sec.locator(`#aporte-O-01-${criterioTecnico.id}-puntaje`).fill("44.50");
  await sec.getByRole("button", { name: "Guardar aporte" }).click();
  await expect(sec.getByRole("button", { name: "Guardar aporte" })).toHaveCount(0);
  await cerrarNotificaciones(page);

  const tarjetaCalidad = tarjetaCriterio("Calidad técnica");
  const liAporteCalidad = tarjetaCalidad.getByRole("listitem").filter({ hasText: "Evaluadora Técnica" });
  await expect(liAporteCalidad.getByText("44.50", { exact: true })).toBeVisible();
  await expect(liAporteCalidad.getByText("Vigente", { exact: true })).toBeVisible();
  await expect(liAporteCalidad.getByText("Historial (1)", { exact: true })).toBeVisible();
  await liAporteCalidad.locator("summary").click();
  await expect(liAporteCalidad.getByRole("listitem").filter({ hasText: /^45\.00 · / })).toBeVisible();

  const axe3 = await new AxeBuilder({ page }).include('[aria-labelledby="sec-evaluacion"]').analyze();
  expect(axe3.violations).toEqual([]);

  for (const width of [390, 320]) {
    await page.setViewportSize({ width, height: 800 });
    const sinDesborde = await page.evaluate(
      () => document.documentElement.scrollWidth <= document.documentElement.clientWidth,
    );
    expect(sinDesborde).toBe(true);
    await expect(
      sec.getByRole("button", { name: "Registrar resultado de la Comisión de Calidad técnica para O-01" }),
    ).toBeVisible();
  }
  await page.setViewportSize({ width: 1280, height: 800 });

  const resultados: Array<{
    criterio: string;
    criterioId: string;
    puntaje?: string;
    cumple?: boolean;
  }> = [
    { criterio: "Calidad técnica", criterioId: criterioTecnico.id, puntaje: "44.00" },
    { criterio: "Precio ofertado", criterioId: criterioEconomico.id, puntaje: "41.00" },
    { criterio: "Capacidad legal", criterioId: criterioLegal.id, cumple: true },
  ];

  for (const resultado of resultados) {
    await sec
      .getByRole("button", { name: `Registrar resultado de la Comisión de ${resultado.criterio} para O-01` })
      .click();
    await sec
      .locator(`#resultado-O-01-${resultado.criterioId}-miembro`)
      .selectOption(miembroIds["Secretaria de la Comisión"]);
    if (resultado.puntaje !== undefined) {
      await sec.locator(`#resultado-O-01-${resultado.criterioId}-puntaje`).fill(resultado.puntaje);
    } else if (resultado.cumple) {
      await sec.getByRole("radio", { name: "Cumple", exact: true }).check();
    }
    await sec.getByRole("button", { name: "Guardar resultado" }).click();
    await expect(sec.getByRole("button", { name: "Guardar resultado" })).toHaveCount(0);

    const tarjeta = tarjetaCriterio(resultado.criterio);
    const bloqueResultado = tarjeta.locator("div.rounded-md.border-brand-600");
    await expect(bloqueResultado.getByText("Resultado de la Comisión", { exact: true })).toBeVisible();
    await expect(bloqueResultado.getByText(resultado.puntaje ?? "Cumple", { exact: true })).toBeVisible();
    await expect(
      bloqueResultado.getByText(/^Registrado por Secretaria de la Comisión · /),
    ).toBeVisible();
    await cerrarNotificaciones(page);
  }

  await expect(tarjetaCalidad.getByText("Resultado de la Comisión", { exact: true })).toBeVisible();
  await expect(tarjetaCalidad.getByText("44.00", { exact: true })).toBeVisible();
  await expect(tarjetaCalidad.getByText("44.50", { exact: true })).toBeVisible();
  await expect(sec.getByText("3 de 3 resultados de la Comisión registrados", { exact: true })).toBeVisible();

  await sec.getByRole("button", { name: "Concluir evaluación" }).click();
  await sec.getByRole("button", { name: "Confirmar conclusión" }).click();
  await expect(sec.getByText(/^Evaluación concluida ·/)).toBeVisible();
  await expect(
    sec.getByRole("definition").filter({ hasText: /^Preparar recomendación$/ }),
  ).toBeVisible();
  await expect(sec.getByRole("button", { name: /^Registrar aporte de / })).toHaveCount(0);
  await expect(sec.getByRole("button", { name: /^Registrar resultado de la Comisión de / })).toHaveCount(0);
  await cerrarNotificaciones(page);

  const axe4 = await new AxeBuilder({ page }).include('[aria-labelledby="sec-evaluacion"]').analyze();
  expect(axe4.violations).toEqual([]);

  for (const width of [390, 320]) {
    await page.setViewportSize({ width, height: 800 });
    const sinDesborde = await page.evaluate(
      () => document.documentElement.scrollWidth <= document.documentElement.clientWidth,
    );
    expect(sinDesborde).toBe(true);
    await expect(sec.getByText(/^Evaluación concluida ·/)).toBeVisible();
    await expect(tarjetaCalidad.getByText("Resultado de la Comisión", { exact: true })).toBeVisible();
  }
  await page.setViewportSize({ width: 1280, height: 800 });

  const cronologia = page.locator('[aria-labelledby="sec-cronologia"]');
  await expect(cronologia).toContainText("Matriz de evaluación bloqueada");
  await expect(cronologia).toContainText("Apertura A-01: 1 oferta(s)");
  await expect(cronologia).toContainText("Evaluación concluida: 1 oferta(s)");

  await expect(page.getByRole("button", { name: /Adjudicar|Declarar desierta/ })).toHaveCount(0);
});
