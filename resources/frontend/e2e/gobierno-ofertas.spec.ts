import { expect, test } from "./helpers/sesion";
import { AxeBuilder } from "@axe-core/playwright";
import {
  API,
  ANIO,
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

test("recibir oferta sella el documento y lo oculta de verdad", async ({ page, request }) => {
  const capacidades = [
    ...RESPONSABLE_ESTRUCTURA,
    "gobierno_ocupacion:view",
    "gobierno_ocupacion:manage",
    "gobierno_expedientes:view",
    "gobierno_expedientes:manage",
    "gobierno_ofertas:view",
    "gobierno_ofertas:receive",
    "documentos:view",
    "documentos:download",
    "documentos:link",
    "documentos:upload",
  ];

  const mundo = await prepararMundo(request, capacidades);
  const { companyId, codigo, username, headers } = mundo;

  const tipo = await crearTipoDocumental(request, headers, companyId);
  await enteActivo(request, headers, companyId, tipo.id);
  const estructura = await estructuraVigenteApi(request, headers, companyId, tipo.id, ANIO);

  const nombreFuncionario = "Funcionario Prueba";
  const numeroDoc = Date.now().toString().slice(-8);
  const funcionarioResp = await request.post(`${API}/gobierno/ocupacion/funcionarios`, {
    headers,
    data: {
      nombre: nombreFuncionario,
      tipo_documento: "V",
      numero_documento: numeroDoc,
    },
  });
  expect(funcionarioResp.status()).toBe(201);
  const funcionario = await funcionarioResp.json();

  const numeroExpediente = `EXP-${Date.now()}`;
  const hoyCaracas = new Date().toLocaleDateString("en-CA", { timeZone: "America/Caracas" });
  const expedienteResp = await request.post(`${API}/gobierno/contrataciones/expedientes`, {
    headers,
    data: {
      numero: numeroExpediente,
      fecha_inicio: hoyCaracas,
      objeto: "Objeto de prueba para ofertas",
      partes: null,
      tipo_contratacion: "BIENES",
      modalidad_declarada: "CONCURSO_ABIERTO",
      modalidad_fundamento: "Fundamento de prueba",
      modalidad_fuente: "Fuente de prueba",
      unidad_id: estructura.despId,
      responsable_id: funcionario.id,
    },
  });
  expect(expedienteResp.status()).toBe(201);
  const expediente = await expedienteResp.json();

  const comisionResp = await request.post(
    `${API}/gobierno/contrataciones/expedientes/${expediente.id}/comision`,
    {
      headers: { ...headers, "If-Match": String(expediente.version) },
      data: {
        comision_id: null,
        no_aplica_motivo: "No aplica por prueba",
        motivo: "Motivo de prueba",
      },
    },
  );
  expect(comisionResp.status()).toBe(200);

  await adjuntarDocumentoApi(
    request,
    headers,
    companyId,
    tipo.id,
    "GovernmentProcurementFile",
    expediente.id,
  );

  const porRecursoResp = await request.get(
    `${API}/documentos/por-recurso/GovernmentProcurementFile/${expediente.id}`,
    { headers },
  );
  expect(porRecursoResp.status()).toBe(200);
  const docsVinculados = await porRecursoResp.json();
  expect(docsVinculados.length).toBe(1);
  const docId = docsVinculados[0].id;

  const versionesResp = await request.get(`${API}/documentos/${docId}/versiones`, { headers });
  expect(versionesResp.status()).toBe(200);
  const versiones = await versionesResp.json();
  expect(versiones.length).toBeGreaterThan(0);
  const versionId = versiones[0].id;

  const descargaAntes = await request.get(`${API}/documentos/${docId}/descargar`, { headers });
  expect(descargaAntes.status()).toBe(200);
  const versionAntes = await request.get(
    `${API}/documentos/${docId}/versiones/${versionId}/descargar`,
    { headers },
  );
  expect(versionAntes.status()).toBe(200);

  await entrarEnGobierno(page, username, codigo, "/gobierno/contrataciones/expedientes");
  await cerrarNotificaciones(page);

  await page.getByRole("link", { name: numeroExpediente }).click();
  await expect(page.locator('[aria-labelledby="sec-ofertas"]')).toBeVisible();

  const seccionOfertas = page.locator('[aria-labelledby="sec-ofertas"]');
  await expect(seccionOfertas.getByText("Sin ofertas recibidas")).toBeVisible();

  const axeAntes = await new AxeBuilder({ page })
    .include('[aria-labelledby="sec-ofertas"]')
    .analyze();
  expect(axeAntes.violations).toEqual([]);

  await seccionOfertas.getByRole("button", { name: "Recibir oferta" }).click();
  await seccionOfertas.getByRole("button", { name: "Guardar" }).click();
  await expect(seccionOfertas.locator('[role="alert"]').first()).toBeVisible();
  await expect(seccionOfertas.getByRole("heading", { name: "Recibir oferta" })).toBeVisible();

  const axeForm = await new AxeBuilder({ page })
    .include('[aria-labelledby="sec-ofertas"]')
    .analyze();
  expect(axeForm.violations).toEqual([]);

  await seccionOfertas.getByLabel(/^Oferente/).fill("Constructora Andina");
  await seccionOfertas.getByLabel("Documento del oferente").fill("1-30-12345-6");
  await seccionOfertas.getByLabel("Representante").fill("María Pérez");
  await seccionOfertas.getByLabel("Tipo de sobre").selectOption({ label: "Sobre único" });
  await seccionOfertas.getByLabel("Canal").selectOption({ label: "Medio electrónico" });
  await seccionOfertas.getByLabel("Funcionario receptor").selectOption(funcionario.id);
  await seccionOfertas.getByRole("checkbox", { name: "Acto de prueba" }).check();
  await seccionOfertas.getByRole("button", { name: "Guardar" }).click();

  await expect(seccionOfertas.locator('[role="status"]')).toContainText("registrada");
  const itemOferta = seccionOfertas.locator('li', {
    hasText: "R-0001",
  });
  await expect(itemOferta.getByText("Constructora Andina")).toBeVisible();
  await expect(itemOferta.getByText("Medio electrónico")).toBeVisible();
  await expect(itemOferta.getByText("Integridad verificada")).toBeVisible();
  await expect(itemOferta.getByText("Sellada hasta la apertura")).toBeVisible();
  await expect(itemOferta.getByText("Pendiente de apertura")).toBeVisible();
  await expect(itemOferta.getByText(nombreFuncionario)).toBeVisible();

  await expect(seccionOfertas.getByText("VERIFICADA", { exact: true })).toHaveCount(0);
  await expect(seccionOfertas.getByText("Acto de prueba", { exact: true })).toHaveCount(0);

  await seccionOfertas.getByRole("button", { name: /Ver detalle de R-0001/ }).click();
  await expect(seccionOfertas.getByText("Contenido sellado hasta la apertura")).toBeVisible();

  const cronologia = page.locator('[aria-labelledby="sec-cronologia"]');
  await expect(cronologia.getByText("R-0001")).toBeVisible();
  await expect(cronologia.getByText("Constructora Andina")).toBeVisible();
  await expect(cronologia.getByText("Acto de prueba")).toHaveCount(0);

  const situacion = page.locator('[aria-labelledby="sec-situacion"]');
  await expect(situacion.getByText("Pendiente de apertura", { exact: true }).first()).toBeVisible();

  const detalleDoc = await request.get(`${API}/documentos/${docId}`, { headers });
  expect(detalleDoc.status()).toBe(404);
  const descargaDespues = await request.get(`${API}/documentos/${docId}/descargar`, { headers });
  expect(descargaDespues.status()).toBe(404);
  const versionDespues = await request.get(
    `${API}/documentos/${docId}/versiones/${versionId}/descargar`,
    { headers },
  );
  expect(versionDespues.status()).toBe(404);
  const porRecursoDespues = await request.get(
    `${API}/documentos/por-recurso/GovernmentProcurementFile/${expediente.id}`,
    { headers },
  );
  expect(porRecursoDespues.status()).toBe(200);
  const docsDespues = await porRecursoDespues.json();
  expect(docsDespues.some((d: { id: string }) => d.id === docId)).toBe(false);

  const axeResultado = await new AxeBuilder({ page })
    .include('[aria-labelledby="sec-ofertas"]')
    .include('[aria-labelledby="sec-cronologia"]')
    .include('[aria-labelledby="sec-situacion"]')
    .analyze();
  expect(axeResultado.violations).toEqual([]);

  for (const ancho of [1280, 390, 320]) {
    await page.setViewportSize({ width: ancho, height: 800 });
    await expect(seccionOfertas).toBeVisible();
    const desborde = await page.evaluate(
      () => document.documentElement.scrollWidth > document.documentElement.clientWidth,
    );
    expect(desborde).toBe(false);

    if (ancho !== 1280) {
      await expect(itemOferta).toBeVisible();
      const botonRecibir = seccionOfertas.getByRole("button", { name: /Recibir oferta/i });
      await expect(botonRecibir).toBeVisible();
      await botonRecibir.click();

      await seccionOfertas.getByLabel(/Oferente\s*\*/).fill("Oferente Responsive");
      await seccionOfertas.getByLabel(/Documento del oferente\s*\*/).fill("Doc123");
      await expect(seccionOfertas.getByRole("button", { name: /Guardar/i })).toBeVisible();
      await seccionOfertas.getByRole("button", { name: /Cancelar/i }).click();
      await expect(seccionOfertas.getByRole("heading", { name: /Recibir oferta/i })).toBeHidden();
    }
  }
});
