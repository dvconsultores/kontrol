import { AxeBuilder } from "@axe-core/playwright";
import type { APIRequestContext } from "@playwright/test";
import { expect, test, sesionApi } from "./helpers/sesion";
import {
  API,
  TENANT,
  crearUsuario,
  adjuntarDocumentoApi,
  entrarEnGobierno,
  cerrarNotificaciones,
} from "./helpers/gobierno";
import { prepararContratoFormalizado } from "./helpers/contratos";

test.setTimeout(480_000);

type DocumentoRespuesta = {
  id: string;
};

async function ultimoDocumentoExpediente(
  request: APIRequestContext,
  headers: Record<string, string>,
  expedienteId: string,
): Promise<DocumentoRespuesta> {
  const resp = await request.get(`${API}/documentos/por-recurso/GovernmentProcurementFile/${expedienteId}`, {
    headers,
  });
  expect(resp.status(), await resp.text()).toBe(200);
  const docs = (await resp.json()) as DocumentoRespuesta[];
  return docs[docs.length - 1];
}

async function adjuntarDocumentoExpediente(
  request: APIRequestContext,
  headers: Record<string, string>,
  companyId: string,
  tipoId: string,
  expedienteId: string,
): Promise<string> {
  await adjuntarDocumentoApi(request, headers, companyId, tipoId, "GovernmentProcurementFile", expedienteId);
  const doc = await ultimoDocumentoExpediente(request, headers, expedienteId);
  return doc.id;
}

function sumarDias(fecha: string, dias: number): string {
  const [anio, mes, dia] = fecha.split("-").map(Number);
  const d = new Date(Date.UTC(anio, mes - 1, dia + dias));
  return d.toISOString().slice(0, 10);
}

test("T007 · recorrido del sponsor por el expediente contractual: secciones, garantías, supervisión, ejecución, documentos, integridad, cronología, auditoría, exportaciones, aislamiento, responsive y Axe", async ({
  page,
  request,
}) => {
  const s = await prepararContratoFormalizado(request);

  const docId = await adjuntarDocumentoExpediente(
    request,
    s.mundo.headers,
    s.mundo.companyId,
    s.tipoId,
    s.expediente.id,
  );

  const nuevaFechaFin = sumarDias(s.fechaFin, 30);

  const crearModificacionResp = await request.post(
    `${API}/gobierno/contratos/${s.contrato.id}/modificaciones`,
    {
      headers: s.mundo.headers,
      data: { tipo: "PRORROGA" },
    },
  );
  expect(crearModificacionResp.status(), await crearModificacionResp.text()).toBe(201);
  const modificacionCreada = (await crearModificacionResp.json()) as { id: string; version: number };

  const actualizarModificacionResp = await request.patch(
    `${API}/gobierno/contratos/${s.contrato.id}/modificaciones/${modificacionCreada.id}`,
    {
      headers: {
        ...s.mundo.headers,
        "If-Match": String(modificacionCreada.version),
      },
      data: {
        fecha_instrumento: s.hoy,
        vigente_desde: s.hoy,
        motivo: "Prórroga del expediente contractual (E2E)",
        referencia_instrumento: "INSTR-E2E-08",
        documento_id: docId,
        nueva_fecha_fin: nuevaFechaFin,
      },
    },
  );
  expect(actualizarModificacionResp.status(), await actualizarModificacionResp.text()).toBe(200);
  const modificacionActualizada = (await actualizarModificacionResp.json()) as { version: number };

  const formalizarModificacionResp = await request.post(
    `${API}/gobierno/contratos/${s.contrato.id}/modificaciones/${modificacionCreada.id}/formalizar`,
    {
      headers: {
        ...s.mundo.headers,
        "If-Match": String(modificacionActualizada.version),
      },
      data: { firmante_cargo_id: s.firmanteSinLimiteId },
    },
  );
  expect(formalizarModificacionResp.status(), await formalizarModificacionResp.text()).toBe(200);
  const prorrogaFormalizada = (await formalizarModificacionResp.json()) as { codigo: string };

  const admin = await sesionApi("admintenant", { tenant: TENANT });
  const fiscal = await crearUsuario(
    request,
    admin.headers,
    [
      "organization:view",
      "gobierno_contratos:view",
      "gobierno_auditoria:view",
      "gobierno_paquetes:view",
      "gobierno_paquetes:generate",
      "gobierno_presupuesto:view",
      "gobierno_expedientes:view",
      "gobierno_actos:view",
      "documentos:view",
      "documentos:download",
    ],
    s.mundo.companyId,
  );
  await entrarEnGobierno(page, fiscal.username, s.mundo.codigo, "/gobierno/contratos");
  await cerrarNotificaciones(page);

  await page.goto(`/gobierno/contratos/${s.contrato.id}`);

  await page.getByRole("link", { name: "Expediente contractual" }).click();
  await expect(page).toHaveURL(`/gobierno/contratos/${s.contrato.id}/expediente`);
  await expect(
    page.getByRole("heading", { name: `Expediente contractual · ${s.contrato.codigo}` }),
  ).toBeVisible();
  await expect(page.getByRole("navigation", { name: "Secciones del expediente" })).toBeVisible();

  const seccionOrigen = page.locator("section", {
    has: page.getByRole("heading", { name: "Origen de contratación", exact: true }),
  });
  await expect(seccionOrigen.getByText(s.expediente.numero)).toBeVisible();
  await expect(seccionOrigen.getByRole("link", { name: "Abrir expediente de contratación" })).toBeVisible();

  const seccionAdjudicacion = page.locator("section", {
    has: page.getByRole("heading", { name: "Adjudicación", exact: true }),
  });
  await expect(seccionAdjudicacion).toBeVisible();
  await expect(seccionAdjudicacion.getByRole("link").first()).toBeVisible();

  const seccionPresupuesto = page.locator("section", {
    has: page.getByRole("heading", { name: "Presupuesto", exact: true }),
  });
  await expect(seccionPresupuesto.getByRole("region", { name: "Certificados" })).toContainText(s.cdp.codigo);

  const seccionInstrumento = page.locator("section", {
    has: page.getByRole("heading", { name: "Instrumento contractual", exact: true }),
  });
  await expect(seccionInstrumento.getByText("Condiciones originales")).toBeVisible();
  await expect(seccionInstrumento.getByText("50000.00 USD").first()).toBeVisible();
  await expect(seccionInstrumento.getByText("Condiciones vigentes")).toBeVisible();
  await expect(seccionInstrumento).toContainText(prorrogaFormalizada.codigo);

  const seccionGarantias = page.locator("section", {
    has: page.getByRole("heading", { name: "Garantías", exact: true }),
  });
  await expect(seccionGarantias).toBeVisible();
  await expect(seccionGarantias.getByText("Sin garantías vinculadas al contrato")).toBeVisible();

  const seccionSupervision = page.locator("section", {
    has: page.getByRole("heading", { name: "Supervisión", exact: true }),
  });
  await expect(seccionSupervision).toBeVisible();
  await expect(seccionSupervision.getByText("Supervisor en una fecha")).toBeVisible();
  await seccionSupervision.getByText("Supervisor en una fecha").fill(s.hoy);
  await seccionSupervision.getByRole("button", { name: "Consultar" }).click();
  await expect(seccionSupervision.getByText("Sin supervisor en esa fecha")).toBeVisible();

  const seccionEjecucion = page.locator("section", {
    has: page.getByRole("heading", { name: "Ejecución", exact: true }),
  });
  await expect(seccionEjecucion).toContainText("El módulo aún no está disponible");
  await expect(seccionEjecucion).not.toContainText("No hubo");

  const seccionActos = page.locator("section", {
    has: page.getByRole("heading", { name: "Actos y documentos", exact: true }),
  });
  const indiceDocumental = seccionActos.getByRole("region", { name: "Índice documental" });
  await expect(indiceDocumental).toContainText("Instrumento contractual");
  await expect(indiceDocumental).toContainText("Modificación contractual");

  const filaInstrumento = indiceDocumental.locator("tr", {
    hasText: "Instrumento contractual",
  });
  await expect(filaInstrumento).toContainText(
    "Sellado · la autoridad documental no lo entrega (huella registrada)",
  );
  await expect(
    filaInstrumento.getByRole("button", { name: "Descargar" }),
  ).toHaveCount(0);

  const filaCdp = indiceDocumental.locator("tr", { hasText: s.cdp.codigo });
  const downloadPromise = page.waitForEvent("download");
  await filaCdp.getByRole("button", { name: "Descargar" }).click();
  const download = await downloadPromise;
  expect(download.suggestedFilename()).toBeTruthy();

  const seccionIntegridad = page.locator("section", {
    has: page.getByRole("heading", { name: "Integridad", exact: true }),
  });
  await seccionIntegridad.getByRole("button", { name: "Comprobar huellas" }).click();
  await expect(seccionIntegridad.getByRole("region", { name: "Integridad documental" })).toBeVisible();
  await expect(seccionIntegridad.getByRole("region", { name: "Integridad documental" })).toContainText(
    "Verificada",
  );

  const seccionCronologia = page.locator("section", {
    has: page.getByRole("heading", { name: "Cronología", exact: true }),
  });
  const cronologiaRegion = seccionCronologia.getByRole("region", { name: "Cronología del expediente" });
  await expect(cronologiaRegion).toContainText("Contrato formalizado");
  await expect(cronologiaRegion).toContainText("Modificación formalizada");
  await seccionCronologia.getByLabel("Proceso").selectOption("CNT-02");
  await expect(cronologiaRegion).toContainText("Modificación formalizada");
  await expect(cronologiaRegion).not.toContainText("Contrato formalizado");

  const seccionAuditoria = page.locator("section", {
    has: page.getByRole("heading", { name: "Auditoría", exact: true }),
  });
  const auditoriaRegion = seccionAuditoria.getByRole("region", { name: "Auditoría del expediente" });
  await expect(auditoriaRegion).toBeVisible();
  await expect(auditoriaRegion.getByRole("link", { name: "Ver evento" }).first()).toBeVisible();

  const seccionExportaciones = page.locator("section", {
    has: page.getByRole("heading", { name: "Exportaciones", exact: true }),
  });
  await seccionExportaciones
    .getByLabel("Propósito del paquete")
    .fill("Paquete del expediente para control fiscal (E2E)");
  await seccionExportaciones.getByRole("button", { name: "Generar paquete" }).click();
  const paquetesRegion = seccionExportaciones.getByRole("region", { name: "Paquetes del expediente" });
  await expect(paquetesRegion).toBeVisible();
  await expect(paquetesRegion.locator("text=/EC-/").first()).toBeVisible();

  const rutaPaquete = test.info().outputPath("expediente.zip");
  const descargaPromise = page.waitForEvent("download");
  await paquetesRegion.getByRole("button", { name: "Descargar" }).click();
  const descarga = await descargaPromise;
  await descarga.saveAs(rutaPaquete);

  await page.getByLabel("Archivo .zip del paquete").setInputFiles(rutaPaquete);
  await page.getByRole("button", { name: "Verificar" }).click();
  await expect(seccionExportaciones.getByText("Válido")).toBeVisible();

  const aislarResp = await request.get(
    `${API}/gobierno/contratos/00000000-0000-0000-0000-000000000000/expediente`,
    { headers: s.mundo.headers },
  );
  expect(aislarResp.status()).toBe(404);

  await page.goto("/gobierno/contratos/00000000-0000-0000-0000-000000000000/expediente");
  await expect(page.getByText("Contrato no encontrado")).toBeVisible();

  await page.goto(`/gobierno/contratos/${s.contrato.id}/expediente`);
  for (const ancho of [1280, 390, 320]) {
    await page.setViewportSize({ width: ancho, height: 800 });
    const sinDesbordamiento = await page.evaluate(
      () => document.documentElement.scrollWidth <= document.documentElement.clientWidth,
    );
    expect(sinDesbordamiento).toBe(true);

    if (ancho === 390 || ancho === 320) {
      const axeResponsive = new AxeBuilder({ page })
        .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
        .analyze();
      const resultadoAxeResponsive = await axeResponsive;
      expect(
        resultadoAxeResponsive.violations.filter(
          (v) => v.impact === "serious" || v.impact === "critical",
        ),
      ).toEqual([]);
    }
  }

  await page.goto("/gobierno/expedientes-contractuales");
  await expect(page.getByText(s.contrato.codigo).first()).toBeVisible();
  for (const ancho of [1280, 390, 320]) {
    await page.setViewportSize({ width: ancho, height: 800 });
    const sinDesbordamiento = await page.evaluate(
      () => document.documentElement.scrollWidth <= document.documentElement.clientWidth,
    );
    expect(sinDesbordamiento).toBe(true);

    if (ancho === 390 || ancho === 320) {
      const axeResponsive = new AxeBuilder({ page })
        .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
        .analyze();
      const resultadoAxeResponsive = await axeResponsive;
      expect(
        resultadoAxeResponsive.violations.filter(
          (v) => v.impact === "serious" || v.impact === "critical",
        ),
      ).toEqual([]);
    }
  }
});
