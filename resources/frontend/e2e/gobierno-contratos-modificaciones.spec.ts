import { AxeBuilder } from "@axe-core/playwright";
import type { APIRequestContext } from "@playwright/test";
import { expect, test } from "./helpers/sesion";
import {
  API,
  TENANT,
  crearUsuario,
  cargoVigenteApi,
  adjuntarDocumentoApi,
  entrarEnGobierno,
  cerrarNotificaciones,
} from "./helpers/gobierno";
import { sesionApi } from "./helpers/sesion";
import { prepararContratoFormalizado } from "./helpers/contratos";

test.setTimeout(480_000);

type DocumentoRespuesta = {
  id: string;
};

type ModificacionesRespuesta = {
  original: {
    monto: string;
    fecha_fin: string;
    huella: string;
  };
  vigente: {
    monto: string;
    fecha_fin: string;
    modificacion_codigo: string;
  };
  historial: Array<{
    codigo: string;
    plazo: string | number | null;
    monto: {
      anterior: string;
      delta: string;
      nuevo: string;
    };
    documento: { sha256: string };
    huella: string;
    tipo_etiqueta?: string;
  }>;
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

async function crearCargoComprometer(
  request: APIRequestContext,
  headers: Record<string, string>,
  companyId: string,
  tipoId: string,
  ejercicio: number,
  unidadId: string,
): Promise<{ id: string; version: number }> {
  const codigo = `CC-${Date.now()}`;
  const resp = await request.post(`${API}/gobierno/estructuras/${ejercicio}/cargos`, {
    headers,
    data: {
      codigo,
      denominacion: "Comprometedor de Presupuesto",
      unidad_id: unidadId,
      vigente_desde: `${ejercicio}-01-01`,
    },
  });
  expect(resp.status(), await resp.text()).toBe(201);
  const cargo = (await resp.json()) as { id: string; version: number };

  const competenciaResp = await request.post(
    `${API}/gobierno/estructuras/${ejercicio}/cargos/${cargo.id}/competencias`,
    {
      headers: { ...headers, "If-Match": '"1"' },
      data: {
        accion: "COMPROMETER",
        materia: "PRESUPUESTO",
        tipo_limite: "SIN_LIMITE",
        monto: null,
        moneda: null,
      },
    },
  );
  expect(competenciaResp.status(), await competenciaResp.text()).toBe(201);

  await adjuntarDocumentoApi(request, headers, companyId, tipoId, "GovernmentPosition", cargo.id);

  const activarResp = await request.post(
    `${API}/gobierno/estructuras/${ejercicio}/cargos/${cargo.id}/activar`,
    {
      headers: { ...headers, "If-Match": '"2"' },
    },
  );
  expect(activarResp.status(), await activarResp.text()).toBe(200);

  return cargo;
}

test("CNT-02 · modificaciones versionadas del contrato: prórroga, ampliación con cobertura, autoridad, reducción frente a compromisos, historia, accesibilidad y responsive", async ({ page, request }) => {
  const s = await prepararContratoFormalizado(request);
  const contratoAntes = await (await request.get(`${API}/gobierno/contratos/${s.contrato.id}`, {
    headers: s.mundo.headers,
  })).json() as { huella: string; monto: string; fecha_fin: string };
  const antes = {
    huella: contratoAntes.huella,
    monto: contratoAntes.monto,
    fecha_fin: contratoAntes.fecha_fin,
  };
  expect(antes.monto).toBe("50000.00");
  expect(antes.fecha_fin).toBe(s.fechaFin);

  await entrarEnGobierno(page, s.mundo.username, s.mundo.codigo, "/gobierno/contratos");
  await cerrarNotificaciones(page);
  await page.goto(`/gobierno/contratos/${s.contrato.id}`);
  await expect(page.getByRole("heading", { name: "Instrumento formalizado" })).toBeVisible();
  await page.getByRole("link", { name: "Modificaciones (0)" }).click();
  await expect(page.getByRole("heading", { name: "Condiciones originales" })).toBeVisible();
  await expect(page.getByText("50000.00 USD").first()).toBeVisible();

  const ahoraMasDias = (dias: number): string => {
    const f = new Date(`${s.hoy}T12:00:00`);
    f.setDate(f.getDate() + dias);
    return new Intl.DateTimeFormat("en-CA", { timeZone: "America/Caracas" }).format(f);
  };

  const crearNuevaModificacion = async (tipo: string): Promise<void> => {
    await page.goto(`/gobierno/contratos/${s.contrato.id}/modificaciones`);
    await page.locator("#modificacion-tipo").selectOption(tipo);
    await page.getByRole("button", { name: "Nueva modificación" }).click();
    await page.waitForURL(new RegExp(`/gobierno/contratos/${s.contrato.id}/modificaciones/[^/]+$`));
  };

  const guardarDatosBase = async (opts: {
    motivo: string;
    referencia: string;
    documento: string;
    fechaInstrumento: string;
    vigenteDesde: string;
    nuevaFechaFin?: string;
    delta?: string;
  }): Promise<void> => {
    await page.locator("#modificacion-fecha-instrumento").fill(opts.fechaInstrumento);
    await page.locator("#modificacion-vigente-desde").fill(opts.vigenteDesde);
    await page.locator("#modificacion-motivo").fill(opts.motivo);
    await page.locator("#modificacion-referencia").fill(opts.referencia);
    await page.locator("#modificacion-documento").selectOption(opts.documento);
    if (opts.nuevaFechaFin) {
      await page.locator("#modificacion-nueva-fecha-fin").fill(opts.nuevaFechaFin);
    }
    if (opts.delta) {
      await page.locator("#modificacion-delta").fill(opts.delta);
    }
    await page.getByRole("button", { name: "Guardar datos" }).click();
    await page.waitForResponse(
      (resp) => resp.request().method() === "PATCH" && resp.url().includes("/modificaciones/"),
    );
  };

  const formalizarModificacion = async (firmanteId: string): Promise<void> => {
    await page.locator("#modificacion-firmante").selectOption(firmanteId);
    await page.getByRole("button", { name: "Formalizar" }).click();
    await page.getByRole("dialog").getByRole("button", { name: "Formalizar" }).click();
  };

  const guardarCobertura = async (codigo: string, monto: string): Promise<void> => {
    await page.locator(`#asignar-${codigo}`).fill(monto);
    await page.getByRole("button", { name: "Guardar cobertura" }).click();
    await page.waitForResponse(
      (resp) => resp.request().method() === "PUT" && resp.url().includes("/cobertura"),
    );
  };


  // ----------------------------------------------------------------------
  // 3. PRÓRROGA
  // ----------------------------------------------------------------------
  await crearNuevaModificacion("PRORROGA");

  const docPr = await adjuntarDocumentoExpediente(
    request,
    s.mundo.headers,
    s.mundo.companyId,
    s.tipoId,
    s.expediente.id,
  );
  await page.reload();

  await guardarDatosBase({
    fechaInstrumento: s.hoy,
    vigenteDesde: s.hoy,
    motivo: "Solicitud justificada del contratista por lluvias",
    referencia: "PR-INSTR-01",
    documento: docPr,
    nuevaFechaFin: ahoraMasDias(210),
  });
  await expect(page.getByRole("status")).toContainText("Cambios guardados.");
  await formalizarModificacion(s.firmanteSinLimiteId);
  await expect(page.getByRole("status")).toContainText(`Formalizada: ${s.contrato.codigo}/PR-001`);
  await expect(page.getByRole("heading", { name: "Instrumento formalizado" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Ver documento" })).toBeVisible();

  // ----------------------------------------------------------------------
  // 4. API: original intacto y vigente actualizado
  // ----------------------------------------------------------------------
  const mods1 = (await (
    await request.get(`${API}/gobierno/contratos/${s.contrato.id}/modificaciones`, {
      headers: s.mundo.headers,
    })
  ).json()) as ModificacionesRespuesta;
  expect(mods1.historial.length).toBe(1);
  expect(mods1.vigente.fecha_fin).toBe(ahoraMasDias(210));
  expect(mods1.original.fecha_fin).toBe(s.fechaFin);
  expect(mods1.original.huella).toBe(s.contrato.huella);

  const c1 = (await (
    await request.get(`${API}/gobierno/contratos/${s.contrato.id}`, { headers: s.mundo.headers })
  ).json()) as { huella: string; monto: string; fecha_fin: string };
  expect(c1.huella).toBe(antes.huella);
  expect(c1.fecha_fin).toBe(antes.fecha_fin);
  expect(c1.monto).toBe(antes.monto);

  // ----------------------------------------------------------------------
  // 5. ADENDA - intento sin cobertura
  // ----------------------------------------------------------------------
  await crearNuevaModificacion("ADENDA");
  const docAd = await adjuntarDocumentoExpediente(
    request,
    s.mundo.headers,
    s.mundo.companyId,
    s.tipoId,
    s.expediente.id,
  );
  await page.reload();
  await guardarDatosBase({
    fechaInstrumento: s.hoy,
    vigenteDesde: s.hoy,
    motivo: "Ampliación de cantidades por nuevas partidas",
    referencia: "AD-INSTR-02",
    documento: docAd,
    delta: "10000.00",
  });
  await expect(page.getByRole("status")).toContainText("Cambios guardados.");

  await formalizarModificacion(s.firmanteSinLimiteId);
  await expect(page.getByRole("alert")).toContainText("Falta cubrir 10000.00 USD");

  // ----------------------------------------------------------------------
  // 6. CDP adicional + cobertura
  // ----------------------------------------------------------------------
  const cdpAdicionalResp = await request.post(
    `${API}/gobierno/presupuesto/ejercicios/${s.ejercicioId}/certificaciones`,
    {
      headers: s.mundo.headers,
      data: {
        credito_id: s.creditoId,
        monto: "10000.00",
        concepto: "Ampliación contractual",
        expediente_id: s.expediente.id,
        firmante_cargo_id: s.cargoPresupuestoId,
      },
    },
  );
  expect(cdpAdicionalResp.status(), await cdpAdicionalResp.text()).toBe(201);
  const cdpAdicional = (await cdpAdicionalResp.json()) as { id: string; codigo: string };

  await page.reload();
  await guardarCobertura(cdpAdicional.codigo, "10000.00");
  await expect(page.getByText("Cobertura completa").first()).toBeVisible();

  // ----------------------------------------------------------------------
  // 7. AUTORIDAD: firmante excede límite
  // ----------------------------------------------------------------------
  const firmante55 = await cargoVigenteApi(
    request,
    s.mundo.headers,
    s.mundo.companyId,
    s.tipoId,
    new Date().getFullYear(),
    s.despId,
    `CF55-${Date.now()}`,
    { tipo_limite: "MONTO", monto: "55000.00", moneda: "USD" },
    "FIRMAR",
  );
  await page.reload();
  await page.locator("#modificacion-firmante").selectOption(firmante55.id);
  await expect(
    page.getByRole("region", { name: "Control del límite del firmante" }).getByText("Excede el límite", { exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Formalizar" }).click();
  await page.getByRole("dialog").getByRole("button", { name: "Formalizar" }).click();
  await expect(page.getByRole("alert")).toContainText("excede el límite de firma");

  await page.locator("#modificacion-firmante").selectOption(s.firmanteSinLimiteId);
  await page.getByRole("button", { name: "Formalizar" }).click();
  await page.getByRole("dialog").getByRole("button", { name: "Formalizar" }).click();
  await expect(page.getByRole("status")).toContainText(`Formalizada: ${s.contrato.codigo}/AD-002`);

  // ----------------------------------------------------------------------
  // 8. REDUCCIÓN con compromisos vigentes superando nuevo monto
  // ----------------------------------------------------------------------
  const comprometedor = await crearCargoComprometer(
    request,
    s.mundo.headers,
    s.mundo.companyId,
    s.tipoId,
    new Date().getFullYear(),
    s.despId,
  );

  const documentoCompromiso = s.documentosPresupuesto[0].id;
  const admin = await sesionApi("admintenant", { tenant: TENANT });
  const usuarioComp = await crearUsuario(request, admin.headers, [
    "organization:view",
    "gobierno_presupuesto:view",
    "gobierno_presupuesto:commit",
    "documentos:view",
  ], s.mundo.companyId);

  const compromisoResp = await request.post(
    `${API}/gobierno/presupuesto/ejercicios/${s.ejercicioId}/compromisos`,
    {
      headers: usuarioComp.headers,
      data: {
        concepto: "Compromiso para validar reducción frente a compromisos",
        lineas: [
          { certificado_id: s.cdp.id, monto: "50000.00" },
          { certificado_id: cdpAdicional.id, monto: "6000.00" },
        ],
        autoridad_cargo_id: comprometedor.id,
        soporte_documento_id: documentoCompromiso,
      },
    },
  );
  expect(compromisoResp.status(), await compromisoResp.text()).toBe(201);

  await crearNuevaModificacion("MODIFICACION");
  const docMo = await adjuntarDocumentoExpediente(
    request,
    s.mundo.headers,
    s.mundo.companyId,
    s.tipoId,
    s.expediente.id,
  );
  await page.reload();
  await guardarDatosBase({
    fechaInstrumento: s.hoy,
    vigenteDesde: s.hoy,
    motivo: "Reducción del alcance por ajuste presupuestario",
    referencia: "MO-INSTR-03",
    documento: docMo,
    delta: "-5000.00",
  });
  await expect(page.getByRole("status")).toContainText("Cambios guardados.");
  await expect(page.getByText("Compromisos presupuestarios").first()).toBeVisible();

  await formalizarModificacion(s.firmanteSinLimiteId);
  await expect(page.getByRole("alert")).toContainText("superan el monto del contrato");

  // ----------------------------------------------------------------------
  // 9. HISTORIA
  // ----------------------------------------------------------------------
  await page.goto(`/gobierno/contratos/${s.contrato.id}/modificaciones`);
  await expect(page.getByText("Contrato original").first()).toBeVisible();
  await expect(page.getByRole("heading", { name: `Prórroga ${s.contrato.codigo}/PR-001` })).toBeVisible();
  await expect(page.getByRole("heading", { name: `Adenda ${s.contrato.codigo}/AD-002` })).toBeVisible();
  await expect(page.getByRole("link", { name: "Continuar el borrador (Modificación)" })).toBeVisible();

  const mods2 = (await (
    await request.get(`${API}/gobierno/contratos/${s.contrato.id}/modificaciones`, {
      headers: s.mundo.headers,
    })
  ).json()) as ModificacionesRespuesta;
  expect(mods2.historial.length).toBe(2);
  const adenda = mods2.historial.find((h) => h.codigo.endsWith("AD-002"));
  expect(adenda).toBeTruthy();
  expect(adenda!.monto).toEqual({
    anterior: "50000.00",
    delta: "10000.00",
    nuevo: "60000.00",
  });
  for (const h of mods2.historial) {
    expect(h.huella).toMatch(/^[0-9a-f]{64}$/);
    expect(h.documento.sha256).toMatch(/^[0-9a-f]{64}$/);
  }
  expect(mods2.vigente.monto).toBe("60000.00");

  const c2 = (await (
    await request.get(`${API}/gobierno/contratos/${s.contrato.id}`, { headers: s.mundo.headers })
  ).json()) as { monto: string; modificaciones: { cantidad: number } };
  expect(c2.monto).toBe("50000.00");
  expect(c2.modificaciones.cantidad).toBe(2);

  // ----------------------------------------------------------------------
  // 10. RESPONSIVE Y AXE
  // ----------------------------------------------------------------------
  await page.getByRole("link", { name: "Continuar el borrador (Modificación)" }).click();
  await page.waitForURL(new RegExp(`/gobierno/contratos/${s.contrato.id}/modificaciones/[^/]+$`));

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

  await page.goto(`/gobierno/contratos/${s.contrato.id}/modificaciones`);
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
