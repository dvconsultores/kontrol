import AxeBuilder from "@axe-core/playwright";
import type { Page } from "@playwright/test";
import { expect, test } from "./helpers/sesion";
import {
  ANIO,
  API,
  RESPONSABLE_ESTRUCTURA,
  TENANT,
  adjuntarDocumentoApi,
  cerrarNotificaciones,
  crearTipoDocumental,
  crearUsuario,
  enteActivo,
  entrarEnGobierno,
  estructuraVigenteApi,
  prepararMundo,
} from "./helpers/gobierno";
import { sesionApi } from "./helpers/sesion";

test.setTimeout(300_000);

const CAPACIDADES = [
  ...RESPONSABLE_ESTRUCTURA,
  "gobierno_ocupacion:view",
  "gobierno_ocupacion:manage",
  "gobierno_expedientes:view",
  "gobierno_expedientes:manage",
  "gobierno_ofertas:view",
  "gobierno_ofertas:receive",
  "gobierno_sod:view",
  "gobierno_sod:manage",
  "gobierno_sod:activate",
  "gobierno_alertas:view",
  "gobierno_alertas:review",
  "documentos:view",
  "documentos:download",
  "documentos:link",
  "documentos:upload",
];

const WCAG = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"];

interface Alerta {
  clave: string;
  tipo: string;
  titulo: string;
  estado: "PENDIENTE" | "REVISADA";
  es_sujeto: boolean;
  detalle: string;
  revision: unknown;
}

interface RespuestaAlertas {
  aviso: string;
  tipos: unknown[];
  alertas: Alerta[];
}

interface Funcionario {
  id: string;
  nombre: string;
  tipo_documento: string;
  numero_documento: string;
}

interface Expediente {
  id: string;
  version: number;
  numero: string;
  objeto: string;
}

interface DocumentoVinculado {
  id: string;
}

async function sinViolacionesSerias(page: Page, contexto: string): Promise<void> {
  const resultados = await new AxeBuilder({ page }).include("main").withTags(WCAG).analyze();
  const serias = resultados.violations.filter((v) => ["critical", "serious"].includes(v.impact ?? ""));
  expect(
    serias.map((v) => ({ id: v.id, help: v.help })),
    contexto,
  ).toEqual([]);
}

function hoyCaracas(): string {
  return new Date().toLocaleDateString("en-CA", { timeZone: "America/Caracas" });
}

test("Alertas de operaciones atípicas: revisión, restricción por sujeto y hallazgo", async ({ page, request }) => {
  const mundo = await prepararMundo(request, CAPACIDADES);
  const { headers, companyId, codigo, username } = mundo;

  const tipo = await crearTipoDocumental(request, headers, companyId);
  await enteActivo(request, headers, companyId, tipo.id);
  const estructura = await estructuraVigenteApi(request, headers, companyId, tipo.id, ANIO);

  const documentoFuncionario = Date.now().toString().slice(-8);
  const funcionarioResp = await request.post(`${API}/gobierno/ocupacion/funcionarios`, {
    headers,
    data: {
      nombre: "Funcionaria Responsable",
      tipo_documento: "V",
      numero_documento: documentoFuncionario,
    },
  });
  expect(funcionarioResp.status(), await funcionarioResp.text()).toBe(201);
  const funcionario = (await funcionarioResp.json()) as Funcionario;

  const objeto = `Adquisición de papelería ${Date.now()}`;

  // Expediente A
  const numeroExpedienteA = `EXP-A-${Date.now()}`;
  const expedienteAResp = await request.post(`${API}/gobierno/contrataciones/expedientes`, {
    headers,
    data: {
      numero: numeroExpedienteA,
      fecha_inicio: hoyCaracas(),
      objeto,
      partes: null,
      tipo_contratacion: "BIENES",
      modalidad_declarada: "CONCURSO_ABIERTO",
      modalidad_fundamento: "Fundamento de prueba",
      modalidad_fuente: "Fuente de prueba",
      unidad_id: estructura.despId,
      responsable_id: funcionario.id,
    },
  });
  expect(expedienteAResp.status(), await expedienteAResp.text()).toBe(201);
  let expedienteA = (await expedienteAResp.json()) as Expediente;

  const comisionResp = await request.post(
    `${API}/gobierno/contrataciones/expedientes/${expedienteA.id}/comision`,
    {
      headers: { ...headers, "If-Match": String(expedienteA.version) },
      data: { comision_id: null, no_aplica_motivo: "No aplica por prueba", motivo: "Motivo de prueba" },
    },
  );
  expect(comisionResp.status(), await comisionResp.text()).toBe(200);
  expedienteA = (await comisionResp.json()) as Expediente;

  await adjuntarDocumentoApi(request, headers, companyId, tipo.id, "GovernmentProcurementFile", expedienteA.id);
  const vinculadosResp = await request.get(
    `${API}/documentos/por-recurso/GovernmentProcurementFile/${expedienteA.id}`,
    { headers },
  );
  const documentos = (await vinculadosResp.json()) as DocumentoVinculado[];
  expect(documentos.length).toBeGreaterThan(0);

  const ofertaRelacionadaResp = await request.post(
    `${API}/gobierno/contrataciones/expedientes/${expedienteA.id}/ofertas`,
    {
      headers: { ...headers, "If-Match": String(expedienteA.version) },
      data: {
        oferente_nombre: "Papelería Relacionada",
        oferente_documento: `V-${documentoFuncionario}`,
        representante: null,
        tipo_sobre: "UNICO",
        canal: "MEDIO_ELECTRONICO",
        recibida_en: new Date().toISOString(),
        funcionario_id: funcionario.id,
        confidencial: true,
        documento_ids: [documentos[0].id],
      },
    },
  );
  expect(ofertaRelacionadaResp.status(), await ofertaRelacionadaResp.text()).toBe(201);

  // Regla de funciones incompatibles por la pantalla
  await entrarEnGobierno(page, username, codigo, "/gobierno/sod/funciones");
  await cerrarNotificaciones(page);
  await expect(page.getByRole("heading", { level: 1, name: "Funciones incompatibles" })).toBeVisible();
  await page.getByLabel("Nombre de la regla").fill("Quien solicita no recibe ofertas");
  await page.getByLabel("Función A").selectOption("SOLICITANTE");
  await page.getByLabel("Función B").selectOption("RECEPTOR");
  await page
    .getByLabel("Riesgo que evita")
    .fill("Quien registra el expediente no debe recibir las ofertas para no controlar su propia compra.");
  await page.getByLabel("Fundamento").fill("N20 y N23: segregación de funciones y prevención del conflicto.");
  await page.getByRole("button", { name: "Registrar borrador" }).click();
  await expect(page.getByText(/registrada como borrador/)).toBeVisible();
  await page.getByRole("button", { name: "Activar desde hoy" }).click();
  await expect(page.getByText(/en vigor/).first()).toBeVisible();

  const expedienteAActualResp = await request.get(
    `${API}/gobierno/contrataciones/expedientes/${expedienteA.id}`,
    { headers },
  );
  const expedienteAActual = (await expedienteAActualResp.json()) as Expediente;
  const bloqueoResp = await request.post(
    `${API}/gobierno/contrataciones/expedientes/${expedienteA.id}/ofertas`,
    {
      headers: { ...headers, "If-Match": String(expedienteAActual.version) },
      data: {
        oferente_nombre: "Segundo Oferente",
        oferente_documento: "J-30999999-1",
        representante: null,
        tipo_sobre: "UNICO",
        canal: "MEDIO_ELECTRONICO",
        recibida_en: new Date().toISOString(),
        funcionario_id: funcionario.id,
        confidencial: true,
        documento_ids: [documentos[0].id],
      },
    },
  );
  expect(bloqueoResp.status(), await bloqueoResp.text()).toBe(409);
  expect((await bloqueoResp.json()).code, "la guarda debe bloquear, no otro conflicto").toBe(
    "GOV_SOD_ROLE_CONFLICT",
  );

  // Expediente B con el mismo objeto
  const numeroExpedienteB = `EXP-B-${Date.now()}`;
  const expedienteBResp = await request.post(`${API}/gobierno/contrataciones/expedientes`, {
    headers,
    data: {
      numero: numeroExpedienteB,
      fecha_inicio: hoyCaracas(),
      objeto,
      partes: null,
      tipo_contratacion: "BIENES",
      modalidad_declarada: "CONCURSO_ABIERTO",
      modalidad_fundamento: "Fundamento de prueba",
      modalidad_fuente: "Fuente de prueba",
      unidad_id: estructura.despId,
      responsable_id: funcionario.id,
    },
  });
  expect(expedienteBResp.status(), await expedienteBResp.text()).toBe(201);

  // Revisor
  const admin = await sesionApi("admintenant", { tenant: TENANT });
  const revisor = await crearUsuario(
    request,
    admin.headers,
    ["organization:view", "gobierno_alertas:view", "gobierno_alertas:review"],
    companyId,
  );

  // GET alertas con el usuario de prueba
  const alertasResp = await request.get(`${API}/gobierno/control/alertas`, { headers });
  expect(alertasResp.status(), await alertasResp.text()).toBe(200);
  const alertasData = (await alertasResp.json()) as RespuestaAlertas;

  const alertaDuplicidad = alertasData.alertas.find(
    (a) =>
      a.tipo === "DUPLICIDAD" &&
      a.titulo.includes(numeroExpedienteA) &&
      a.titulo.includes(numeroExpedienteB),
  );
  expect(alertaDuplicidad, "debe existir la alerta de duplicidad").toBeDefined();
  const alertaDuplicidadDef = alertaDuplicidad as Alerta;

  const alertaProveedor = alertasData.alertas.find(
    (a) => a.tipo === "PROVEEDOR_RELACIONADO" && a.titulo.includes("Papelería Relacionada"),
  );
  expect(alertaProveedor, "debe existir la alerta de proveedor relacionado").toBeDefined();

  const alertaAutoaprobacion = alertasData.alertas.find(
    (a) => a.tipo === "AUTOAPROBACION" && a.detalle.includes(numeroExpedienteA),
  );
  expect(alertaAutoaprobacion, "debe existir la alerta de autoaprobación").toBeDefined();
  const alertaAutoaprobacionDef = alertaAutoaprobacion as Alerta;
  expect(alertaAutoaprobacionDef.es_sujeto, "el usuario debe ser sujeto de la autoaprobación").toBe(true);

  // UI
  await entrarEnGobierno(page, username, codigo, "/gobierno/control/alertas");
  await cerrarNotificaciones(page);
  await expect(page.getByRole("heading", { level: 1, name: "Alertas de operaciones atípicas" })).toBeVisible();
  await expect(page.getByRole("note")).toContainText(
    "Una alerta es una señal para revisar; no es una acusación ni una conclusión.",
  );
  await expect(
    page
      .getByRole("table", { name: "Tipos de alerta" })
      .getByRole("row")
      .filter({ hasText: "Fraccionamiento" }),
  ).toContainText("No disponible");
  await sinViolacionesSerias(page, "inicio");

  const listaAlertas = page.getByRole("list", { name: "Alertas" });

  // Proveedor relacionado: documento enmascarado y sin número completo
  const liProveedor = listaAlertas.getByRole("listitem").filter({
    has: page.getByRole("heading", {
      level: 3,
      name: `Oferente Papelería Relacionada con el documento de un funcionario`,
    }),
  });
  await expect(liProveedor).toContainText(`V-******${documentoFuncionario.slice(-2)}`);
  await expect(page.locator("main")).not.toContainText(documentoFuncionario);

  // Autoaprobación: restricción por sujeto
  const liAutoaprobacion = listaAlertas.getByRole("listitem").filter({
    has: page.getByRole("heading", {
      level: 3,
      name: "Intento bloqueado por funciones incompatibles",
    }),
  });
  await expect(liAutoaprobacion).toContainText("No puede revisar esta alerta porque es sujeto de ella.");
  await expect(liAutoaprobacion.getByRole("button", { name: "Revisar" })).toHaveCount(0);

  // Por API, el usuario no puede revisarse a sí mismo
  const selfReviewResp = await request.post(`${API}/gobierno/control/alertas/revisiones`, {
    headers,
    data: {
      clave: alertaAutoaprobacionDef.clave,
      resultado: "SIN_OBSERVACION",
      observacion: "Intento de revisar la propia alerta en la prueba.",
    },
  });
  expect(selfReviewResp.status(), await selfReviewResp.text()).toBe(409);
  expect((await selfReviewResp.json()).code).toBe("GOV_ALERT_SELF_REVIEW");

  const alertasTrasSelfResp = await request.get(`${API}/gobierno/control/alertas`, { headers });
  const alertasTrasSelf = (await alertasTrasSelfResp.json()) as RespuestaAlertas;
  const alertaAutoTrasSelf = alertasTrasSelf.alertas.find((a) => a.clave === alertaAutoaprobacionDef.clave);
  expect(alertaAutoTrasSelf, "la alerta debe seguir existiendo tras el intento").toBeDefined();
  const alertaAutoTrasSelfDef = alertaAutoTrasSelf as Alerta;
  expect(alertaAutoTrasSelfDef.estado).toBe("PENDIENTE");

  // Revisar duplicidad por la pantalla
  const liDuplicidad = listaAlertas.getByRole("listitem").filter({
    has: page.getByRole("heading", {
      level: 3,
      name: `Expedientes ${numeroExpedienteA} y ${numeroExpedienteB} con el mismo objeto`,
    }),
  });
  await liDuplicidad.getByRole("button", { name: "Revisar" }).click();
  await page.getByRole("radio", { name: "Sin observación" }).check();
  await page
    .getByLabel("Observación", { exact: true })
    .fill("Expedientes del mismo objeto revisados con la unidad: son lotes distintos.");
  await page.getByRole("button", { name: "Registrar revisión" }).click();
  await expect(page.getByText("Revisión registrada")).toBeVisible();
  await expect(liDuplicidad).toContainText("Revisada por");
  await expect(liDuplicidad).toContainText("Expedientes del mismo objeto revisados con la unidad: son lotes distintos.");

  // Segunda revisión de duplicidad por el revisor → 409
  const segundaRevisionResp = await request.post(`${API}/gobierno/control/alertas/revisiones`, {
    headers: revisor.headers,
    data: {
      clave: alertaDuplicidadDef.clave,
      resultado: "REQUIERE_SEGUIMIENTO",
      observacion: "Revisión duplicada",
    },
  });
  expect(segundaRevisionResp.status(), await segundaRevisionResp.text()).toBe(409);
  expect((await segundaRevisionResp.json()).code).toBe("GOV_ALERT_ALREADY_REVIEWED");

  // El revisor revisa la autoaprobación por API
  const revisionAutoResp = await request.post(`${API}/gobierno/control/alertas/revisiones`, {
    headers: revisor.headers,
    data: {
      clave: alertaAutoaprobacionDef.clave,
      resultado: "REQUIERE_SEGUIMIENTO",
      observacion: "Intento de recibir ofertas del propio expediente: se abre seguimiento.",
    },
  });
  expect(revisionAutoResp.status(), await revisionAutoResp.text()).toBe(201);

  // Recargar y ver hallazgo
  await page.reload();
  await expect(page.getByRole("heading", { level: 1, name: "Alertas de operaciones atípicas" })).toBeVisible();
  const liAutoaprobacionRecargada = page
    .getByRole("list", { name: "Alertas" })
    .getByRole("listitem")
    .filter({
      has: page.getByRole("heading", {
        level: 3,
        name: "Intento bloqueado por funciones incompatibles",
      }),
    });
  await expect(liAutoaprobacionRecargada).toContainText("Requiere seguimiento");
  await expect(
    liAutoaprobacionRecargada.getByRole("link", { name: "Registrar hallazgo" }),
  ).toHaveAttribute("href", "/gobierno/hallazgos/nuevo");
  await sinViolacionesSerias(page, "revisadas");

  // Responsive
  for (const ancho of [1280, 390, 320]) {
    await page.setViewportSize({ width: ancho, height: 900 });
    await expect(
      page.getByRole("heading", { level: 1, name: "Alertas de operaciones atípicas" }),
    ).toBeVisible();
    const desborde = await page.evaluate(
      () => document.documentElement.scrollWidth > document.documentElement.clientWidth,
    );
    expect(desborde, `desborde a ${ancho}px`).toBe(false);
    await sinViolacionesSerias(page, `axe ${ancho}`);
  }
});
