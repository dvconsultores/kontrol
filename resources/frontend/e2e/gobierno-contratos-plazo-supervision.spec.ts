import { AxeBuilder } from "@axe-core/playwright";
import type { APIRequestContext } from "@playwright/test";
import { expect, test, sesionApi } from "./helpers/sesion";
import {
  API,
  TENANT,
  ANIO,
  crearUsuario,
  cargoVigenteApi,
  adjuntarDocumentoApi,
  entrarEnGobierno,
  cerrarNotificaciones,
} from "./helpers/gobierno";
import {
  prepararContratoFormalizado,
  actoEmitidoApi,
  crearFuncionario,
} from "./helpers/contratos";

test.setTimeout(480_000);

function sumarDias(fecha: string, dias: number): string {
  const [anio, mes, dia] = fecha.split("-").map(Number);
  const d = new Date(Date.UTC(anio, mes - 1, dia + dias));
  return d.toISOString().slice(0, 10);
}

function dmy(iso: string): string {
  const [a, m, d] = iso.split("-");
  return `${d}/${m}/${a}`;
}

type DocumentoRespuesta = { id: string };

async function ultimoDocumentoExpediente(
  request: APIRequestContext,
  headers: Record<string, string>,
  expedienteId: string,
): Promise<DocumentoRespuesta> {
  const resp = await request.get(
    `${API}/documentos/por-recurso/GovernmentProcurementFile/${expedienteId}`,
    { headers },
  );
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
  await adjuntarDocumentoApi(
    request,
    headers,
    companyId,
    tipoId,
    "GovernmentProcurementFile",
    expedienteId,
  );
  const doc = await ultimoDocumentoExpediente(request, headers, expedienteId);
  return doc.id;
}

type SupervisionRespuesta = {
  contrato: {
    fecha_fin_original: string;
    fecha_fin_vigente: string;
    fuente_plazo: string;
    modificacion_plazo: unknown;
  };
};

test("T004 · CNT-04-EFFECTIVE-TERM-01: la prórroga CNT-02 amplía el plazo que gobierna la designación de supervisor", async ({
  page,
  request,
}) => {
  const s = await prepararContratoFormalizado(request);
  const admin = await sesionApi("admintenant", { tenant: TENANT });
  const activadorOcupacion = await crearUsuario(
    request,
    admin.headers,
    ["organization:view", "gobierno_ocupacion:view", "gobierno_ocupacion:activate"],
    s.mundo.companyId,
  );

  const cargoSupervisora = await cargoVigenteApi(
    request,
    s.mundo.headers,
    s.mundo.companyId,
    s.tipoId,
    ANIO,
    s.despId,
    `CSP-${Date.now()}`,
  );
  const funcionaria = await crearFuncionario(
    request,
    s.mundo.headers,
    "Paula Supervisora",
  );
  const actoOcupacion = await actoEmitidoApi(
    request,
    s.mundo.headers,
    s.mundo.companyId,
    s.tipoId,
    s.emisorId,
    s.hoy,
  );

  async function asignarTitular(funcionarioId: string, cargoId: string): Promise<string> {
    const resp = await request.post(`${API}/gobierno/ocupacion/asignaciones`, {
      headers: s.mundo.headers,
      data: {
        funcionario_id: funcionarioId,
        cargo_id: cargoId,
        figura: "TITULAR",
        acto_id: actoOcupacion.id,
        desde: s.hoy,
        fundamento: "Designación de prueba CNT-04",
        cargo_origen_id: null,
        hasta: null,
        rendicion: null,
        maxima_autoridad: false,
        autorizacion_concejo: null,
        declara_delegable: false,
        competencias: [],
      },
    });
    expect(resp.status(), await resp.text()).toBe(201);
    const json: { id: string; version: number } = await resp.json();
    const actResp = await request.post(
      `${API}/gobierno/ocupacion/asignaciones/${json.id}/activar`,
      {
        headers: { ...activadorOcupacion.headers, "If-Match": `"${json.version}"` },
        data: {},
      },
    );
    expect(actResp.status(), await actResp.text()).toBe(200);
    return json.id;
  }

  await asignarTitular(funcionaria.id, cargoSupervisora.id);

  const cargoSinLimite = await cargoVigenteApi(
    request,
    s.mundo.headers,
    s.mundo.companyId,
    s.tipoId,
    ANIO,
    s.despId,
    `CSL-${Date.now()}`,
    { tipo_limite: "SIN_LIMITE" },
  );

  const actoDesignacion = await actoEmitidoApi(
    request,
    s.mundo.headers,
    s.mundo.companyId,
    s.tipoId,
    cargoSinLimite.id,
    s.hoy,
  );

  await entrarEnGobierno(page, s.mundo.username, s.mundo.codigo, "/gobierno/contratos");
  await cerrarNotificaciones(page);
  await page.goto(`/gobierno/contratos/${s.contrato.id}`);

  const seccionSup = page.locator("section").filter({
    has: page.getByRole("heading", {
      name: "Supervisor / responsable del contrato",
      exact: true,
    }),
  });

  const dtFinVigente = seccionSup.locator("dt", { hasText: /^Fin del plazo vigente$/ });
  const ddFinVigente = dtFinVigente.locator("xpath=following-sibling::dd[1]");
  const dtSegun = seccionSup.locator("dt", { hasText: /^Según$/ });
  const ddSegun = dtSegun.locator("xpath=following-sibling::dd[1]");

  await expect(ddFinVigente).toHaveText(dmy(s.fechaFin));
  await expect(ddSegun).toHaveText("Contrato original");

  const crearNuevaModificacion = async (tipo: string): Promise<void> => {
    await page.goto(`/gobierno/contratos/${s.contrato.id}/modificaciones`);
    await page.locator("#modificacion-tipo").selectOption(tipo);
    await page.getByRole("button", { name: "Nueva modificación" }).click();
    await page.waitForURL(
      new RegExp(`/gobierno/contratos/${s.contrato.id}/modificaciones/[^/]+$`),
    );
  };

  const guardarDatosBase = async (opts: {
    motivo: string;
    referencia: string;
    documento: string;
    fechaInstrumento: string;
    vigenteDesde: string;
    nuevaFechaFin?: string;
  }): Promise<void> => {
    await page.locator("#modificacion-fecha-instrumento").fill(opts.fechaInstrumento);
    await page.locator("#modificacion-vigente-desde").fill(opts.vigenteDesde);
    await page.locator("#modificacion-motivo").fill(opts.motivo);
    await page.locator("#modificacion-referencia").fill(opts.referencia);
    await page.locator("#modificacion-documento").selectOption(opts.documento);
    if (opts.nuevaFechaFin) {
      await page.locator("#modificacion-nueva-fecha-fin").fill(opts.nuevaFechaFin);
    }
    await page.getByRole("button", { name: "Guardar datos" }).click();
    await page.waitForResponse(
      (resp) =>
        resp.request().method() === "PATCH" &&
        resp.url().includes("/modificaciones/"),
    );
  };

  const formalizarModificacion = async (firmanteId: string): Promise<void> => {
    await page.locator("#modificacion-firmante").selectOption(firmanteId);
    await page.getByRole("button", { name: "Formalizar" }).click();
    await page.getByRole("dialog").getByRole("button", { name: "Formalizar" }).click();
  };

  const hoyMas210 = sumarDias(s.hoy, 210);

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
    nuevaFechaFin: hoyMas210,
  });
  await expect(page.getByRole("status")).toContainText("Cambios guardados.");
  await formalizarModificacion(s.firmanteSinLimiteId);
  await expect(page.getByRole("status")).toContainText(
    `Formalizada: ${s.contrato.codigo}/PR-001`,
  );
  await expect(
    page.getByRole("heading", { name: "Instrumento formalizado" }),
  ).toBeVisible();

  await page.goto(`/gobierno/contratos/${s.contrato.id}`);

  await expect(ddFinVigente).toHaveText(dmy(hoyMas210));
  await expect(ddSegun).toHaveText(`Modificación ${s.contrato.codigo}/PR-001`);

  const dtFinOriginal = seccionSup.locator("dt", { hasText: /^Fin original$/ });
  const ddFinOriginal = dtFinOriginal.locator("xpath=following-sibling::dd[1]");
  await expect(ddFinOriginal).toHaveText(dmy(s.fechaFin));

  const supervisionResp = await request.get(
    `${API}/gobierno/contratos/${s.contrato.id}/supervision`,
    { headers: s.mundo.headers },
  );
  expect(supervisionResp.status(), await supervisionResp.text()).toBe(200);
  const supervisionJson = (await supervisionResp.json()) as SupervisionRespuesta;
  expect(supervisionJson.contrato.fecha_fin_vigente).toBe(hoyMas210);
  expect(supervisionJson.contrato.fecha_fin_original).toBe(s.fechaFin);

  const hoyMas190 = sumarDias(s.hoy, 190);
  const hoyMas215 = sumarDias(s.hoy, 215);

  await seccionSup.getByRole("button", { name: "Nueva designación", exact: true }).click();

  await Promise.all([
    page.waitForResponse(
      (r) =>
        r.request().method() === "GET" &&
        new URL(r.url()).pathname.endsWith("/supervision/opciones") &&
        new URL(r.url()).searchParams.get("fecha") === hoyMas215,
    ),
    page.locator("#supervision-desde").fill(hoyMas215),
  ]);

  await seccionSup
    .getByRole("combobox", { name: "Funcionario (obligatorio)", exact: true })
    .selectOption(funcionaria.id);
  await seccionSup
    .getByRole("combobox", { name: "Acto de designación (obligatorio)", exact: true })
    .selectOption(actoDesignacion.id);
  await seccionSup
    .getByRole("button", { name: "Formalizar designación", exact: true })
    .click();

  const dialogoSup = page.getByRole("dialog");

  const post422 = page.waitForResponse(
    (r) =>
      r.request().method() === "POST" &&
      new URL(r.url()).pathname.endsWith("/supervision/designaciones") &&
      r.status() === 422,
  );
  await dialogoSup.getByRole("button", { name: "Formalizar", exact: true }).click();
  await post422;

  await expect(seccionSup.getByRole("alert")).toBeVisible();
  await expect(seccionSup.getByText("Designación SUP-01 registrada.")).toHaveCount(0);

  await Promise.all([
    page.waitForResponse(
      (r) =>
        r.request().method() === "GET" &&
        new URL(r.url()).pathname.endsWith("/supervision/opciones") &&
        new URL(r.url()).searchParams.get("fecha") === hoyMas190,
    ),
    page.locator("#supervision-desde").fill(hoyMas190),
  ]);

  await seccionSup
    .getByRole("combobox", { name: "Funcionario (obligatorio)", exact: true })
    .selectOption(funcionaria.id);
  await seccionSup
    .getByRole("combobox", { name: "Acto de designación (obligatorio)", exact: true })
    .selectOption(actoDesignacion.id);
  await seccionSup
    .getByRole("button", { name: "Formalizar designación", exact: true })
    .click();

  const dialogoSupPositivo = page.getByRole("dialog");

  await Promise.all([
    page.waitForResponse(
      (r) =>
        r.request().method() === "POST" &&
        new URL(r.url()).pathname.endsWith("/supervision/designaciones") &&
        r.status() === 201,
    ),
    dialogoSupPositivo
      .getByRole("button", { name: "Formalizar", exact: true })
      .click(),
  ]);

  await expect(seccionSup.getByRole("status")).toContainText(
    "Designación SUP-01 registrada.",
  );

  const historial = page.getByRole("region", { name: "Historial de supervisores" });
  await expect(historial).toContainText("SUP-01");
  await expect(historial).toContainText("Programada · Vigente");

  for (const ancho of [1280, 390, 320]) {
    await page.setViewportSize({ width: ancho, height: 800 });
    const sinDesbordamiento = await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    );
    expect(sinDesbordamiento).toBe(true);
    await expect(
      page.getByRole("heading", { name: "Plazo del contrato", exact: true }),
    ).toBeVisible();

    const resultadoAxe = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
      .analyze();
    expect(
      resultadoAxe.violations.filter(
        (v) => v.impact === "serious" || v.impact === "critical",
      ),
    ).toEqual([]);
  }
});
