import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "./helpers/sesion";
import {
  ANIO,
  API,
  RESPONSABLE_ESTRUCTURA,
  adjuntarDocumentoApi,
  cerrarNotificaciones,
  crearTipoDocumental,
  enteActivo,
  entrarEnGobierno,
  estructuraVigenteApi,
  prepararMundo,
} from "./helpers/gobierno";

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
  "documentos:view",
  "documentos:download",
  "documentos:link",
  "documentos:upload",
];

function hoyCaracas(): string {
  return new Date().toLocaleDateString("en-CA", { timeZone: "America/Caracas" });
}

test("PROC-11 · funciones incompatibles: matriz, conflicto previo y bloqueo", async ({ page, request }) => {
  const mundo = await prepararMundo(request, CAPACIDADES);
  const { headers, companyId, codigo, username } = mundo;

  const tipo = await crearTipoDocumental(request, headers, companyId);
  await enteActivo(request, headers, companyId, tipo.id);
  const estructura = await estructuraVigenteApi(request, headers, companyId, tipo.id, ANIO);

  const funcionarioResp = await request.post(`${API}/gobierno/ocupacion/funcionarios`, {
    headers,
    data: {
      nombre: "Funcionario Responsable",
      tipo_documento: "V",
      numero_documento: Date.now().toString().slice(-8),
    },
  });
  expect(funcionarioResp.status(), await funcionarioResp.text()).toBe(201);
  const funcionario = await funcionarioResp.json();

  const numeroExpediente = `EXP-P11-${Date.now()}`;
  const expedienteResp = await request.post(`${API}/gobierno/contrataciones/expedientes`, {
    headers,
    data: {
      numero: numeroExpediente,
      fecha_inicio: hoyCaracas(),
      objeto: "Objeto de prueba de funciones incompatibles",
      partes: null,
      tipo_contratacion: "BIENES",
      modalidad_declarada: "CONCURSO_ABIERTO",
      modalidad_fundamento: "Fundamento de prueba",
      modalidad_fuente: "Fuente de prueba",
      unidad_id: estructura.despId,
      responsable_id: funcionario.id,
    },
  });
  expect(expedienteResp.status(), await expedienteResp.text()).toBe(201);
  let expediente = await expedienteResp.json();

  const comisionResp = await request.post(
    `${API}/gobierno/contrataciones/expedientes/${expediente.id}/comision`,
    {
      headers: { ...headers, "If-Match": String(expediente.version) },
      data: { comision_id: null, no_aplica_motivo: "No aplica por prueba", motivo: "Motivo de prueba" },
    },
  );
  expect(comisionResp.status(), await comisionResp.text()).toBe(200);
  expediente = await comisionResp.json();

  await adjuntarDocumentoApi(
    request,
    headers,
    companyId,
    tipo.id,
    "GovernmentProcurementFile",
    expediente.id,
  );
  const vinculados = await request.get(
    `${API}/documentos/por-recurso/GovernmentProcurementFile/${expediente.id}`,
    { headers },
  );
  const documentos = await vinculados.json();
  expect(documentos.length).toBeGreaterThan(0);

  const ofertaResp = await request.post(
    `${API}/gobierno/contrataciones/expedientes/${expediente.id}/ofertas`,
    {
      headers: { ...headers, "If-Match": String(expediente.version) },
      data: {
        oferente_nombre: "Constructora Andina",
        oferente_documento: "J-30123456-7",
        representante: "María Pérez",
        tipo_sobre: "UNICO",
        canal: "MEDIO_ELECTRONICO",
        recibida_en: new Date().toISOString(),
        funcionario_id: funcionario.id,
        confidencial: true,
        documento_ids: [documentos[0].id],
      },
    },
  );
  expect(ofertaResp.status(), await ofertaResp.text()).toBe(201);

  await entrarEnGobierno(page, username, codigo, "/gobierno/sod/funciones");
  await cerrarNotificaciones(page);
  await expect(page.getByRole("heading", { level: 1, name: "Funciones incompatibles" })).toBeVisible();
  await expect(page.getByText(/GOV-TRE-004/)).toBeVisible();

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

  const expedienteActual = await request.get(
    `${API}/gobierno/contrataciones/expedientes/${expediente.id}`,
    { headers },
  );
  const versionActual = (await expedienteActual.json()).version as number;
  const bloqueo = await request.post(
    `${API}/gobierno/contrataciones/expedientes/${expediente.id}/ofertas`,
    {
      headers: { ...headers, "If-Match": String(versionActual) },
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
  expect(bloqueo.status(), await bloqueo.text()).toBe(409);
  expect((await bloqueo.json()).code, "la guarda debe bloquear, no otro conflicto").toBe(
    "GOV_SOD_ROLE_CONFLICT",
  );

  const conflictos = page.locator('[aria-labelledby="conflictos-titulo"]');
  await expect(conflictos.getByRole("link", { name: numeroExpediente })).toBeVisible();
  await expect(conflictos.getByText(/Solicitante .* ≠ Receptor de ofertas/)).toBeVisible();
  await expect(conflictos.getByText(/Recepción de la oferta R-0001/)).toBeVisible();

  const axe = await new AxeBuilder({ page }).analyze();
  expect(axe.violations.filter((v) => v.impact === "serious" || v.impact === "critical")).toEqual([]);

  for (const ancho of [1280, 390, 320]) {
    await page.setViewportSize({ width: ancho, height: 900 });
    await expect(page.getByRole("heading", { level: 1, name: "Funciones incompatibles" })).toBeVisible();
    const desborde = await page.evaluate(
      () => document.documentElement.scrollWidth > document.documentElement.clientWidth,
    );
    expect(desborde, `desborde a ${ancho}px`).toBe(false);
  }

  await page.setViewportSize({ width: 1280, height: 900 });
  await page.getByRole("link", { name: numeroExpediente }).click();
  const seccion = page.locator('[aria-labelledby="funciones-incompatibles-titulo"]');
  await expect(seccion).toBeVisible();
  await expect(seccion.getByText(/Solicitante .* ≠ Receptor de ofertas/)).toBeVisible();
  await expect(seccion.getByText(/Recepción de la oferta R-0001/)).toBeVisible();
});
