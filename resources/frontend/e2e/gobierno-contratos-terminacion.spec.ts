import { AxeBuilder } from "@axe-core/playwright";
import { expect, test, sesionApi } from "./helpers/sesion";
import {
  API,
  TENANT,
  crearUsuario,
  adjuntarDocumentoApi,
  entrarEnGobierno,
  cerrarNotificaciones,
} from "./helpers/gobierno";
import { prepararContratoFormalizado, actoDecisionEmitidoApi } from "./helpers/contratos";

test.setTimeout(480_000);

function sumarDias(fecha: string, dias: number): string {
  const [anio, mes, dia] = fecha.split("-").map(Number);
  const d = new Date(Date.UTC(anio, mes - 1, dia + dias));
  return d.toISOString().slice(0, 10);
}

type DocumentoRecurso = { id: string };
type Notificacion = { id: string; version: number };
type AuditoriaItem = { accion: string };

test("T007 · CNT-07 recorrido del sponsor: figura, causal, motivación, acto, notificación, formalización, situación, bloqueo posterior, expediente, auditoría, negativos, responsive y Axe", async ({
  page,
  request,
}) => {
  const s = await prepararContratoFormalizado(request);
  const cid = s.contrato.id;

  const fichaResp = await request.get(`${API}/gobierno/contratos/${cid}`, {
    headers: s.mundo.headers,
  });
  expect(fichaResp.status()).toBe(200);
  const ficha = (await fichaResp.json()) as { contratista: { documento: string } };
  const documentoContratista = ficha.contratista.documento;

  const acto = await actoDecisionEmitidoApi(
    request,
    s.mundo.headers,
    s.mundo.companyId,
    s.tipoId,
    s.emisorId,
    s.hoy,
  );

  const notificacionResp = await request.post(`${API}/gobierno/notificaciones`, {
    headers: s.mundo.headers,
    data: {
      acto_id: acto.id,
      tipo_persona: "JURIDICA",
      nombre: "Contratista",
      identificacion: documentoContratista,
      domicilio: "Av. Principal, Caracas",
      recursos: "Recurso de reconsideración ante el mismo órgano en 15 días hábiles (LOPA art. 94)",
    },
  });
  expect(notificacionResp.status()).toBe(201);
  const notificacion = (await notificacionResp.json()) as Notificacion;

  await adjuntarDocumentoApi(
    request,
    s.mundo.headers,
    s.mundo.companyId,
    s.tipoId,
    "GovernmentNotification",
    notificacion.id,
  );
  await adjuntarDocumentoApi(
    request,
    s.mundo.headers,
    s.mundo.companyId,
    s.tipoId,
    "GovernmentNotification",
    notificacion.id,
  );

  const docsResp = await request.get(
    `${API}/documentos/por-recurso/GovernmentNotification/${notificacion.id}`,
    { headers: s.mundo.headers },
  );
  expect(docsResp.status()).toBe(200);
  const docs = (await docsResp.json()) as DocumentoRecurso[];
  expect(docs.length).toBeGreaterThanOrEqual(2);

  const intentoResp = await request.post(`${API}/gobierno/notificaciones/${notificacion.id}/intentos`, {
    headers: { ...s.mundo.headers, "If-Match": `"${notificacion.version}"` },
    data: {
      medio: "PERSONAL",
      resultado: "ENTREGADA",
      fecha: s.hoy,
      documento_oficio_id: docs[0].id,
      documento_id: docs[1].id,
      receptor_nombre: "María Gil",
      receptor_identificacion: "V-7654321",
    },
  });
  expect(intentoResp.status()).toBe(200);

  const hitoResp = await request.post(`${API}/gobierno/contratos/${cid}/ejecucion/hitos`, {
    headers: s.mundo.headers,
    data: {
      descripcion: "Hito inicial de ejecución para CNT-07",
      fecha_prevista: s.hoy,
      monto_previsto: "1000.00",
      obligatorio: true,
    },
  });
  expect(hitoResp.status()).toBe(201);

  const admin = await sesionApi("admintenant", { tenant: TENANT });
  const autoridad = await crearUsuario(
    request,
    admin.headers,
    [
      "organization:view",
      "gobierno_contratos:view",
      "gobierno_contratos:terminate",
      "gobierno_actos:view",
      "gobierno_notificaciones:view",
      "gobierno_auditoria:view",
      "gobierno_presupuesto:view",
      "gobierno_expedientes:view",
      "documentos:view",
      "documentos:download",
    ],
    s.mundo.companyId,
  );

  await entrarEnGobierno(page, autoridad.username, s.mundo.codigo, "/gobierno/contratos");
  await cerrarNotificaciones(page);

  await page.goto(`/gobierno/contratos/${cid}`);
  await page.getByRole("link", { name: "Terminación / resolución / rescisión" }).click();
  await page.waitForURL(`**/gobierno/contratos/${cid}/terminacion`);
  await expect(page.getByRole("heading", { name: "Terminación, resolución o rescisión" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Situación actual" })).toBeVisible();
  await expect(page.getByText("Vigente", { exact: true })).toBeVisible();

  await page.getByLabel("Figura jurídica").selectOption("RESCISION_NO_IMPUTABLE");
  await page.getByRole("button", { name: "Preparar" }).click();
  await expect(page.getByRole("heading", { name: "Actuación en preparación" })).toBeVisible();

  await page.getByLabel("Causal").selectOption("INTERES_DEL_CONTRATANTE");
  await page.getByLabel("Hechos").fill("Hechos detallados de la terminación por interés del contratante que superan los veinte caracteres.");
  await page.getByLabel("Fundamento jurídico").fill("Fundamento jurídico extenso que respalda la rescisión unilateral y supera los veinte caracteres requeridos.");
  await page.getByLabel("Acto decisorio").selectOption(acto.id);
  await page.getByRole("button", { name: "Guardar borrador" }).click();
  await expect(page.getByText(/^Pendiente ·/)).toHaveCount(0);

  await expect(page.getByRole("heading", { name: "Notificaciones del acto" })).toBeVisible();
  const regionNotificaciones = page.getByRole("region", { name: "Notificaciones del acto" });
  await expect(regionNotificaciones.getByText("Contratista", { exact: true }).first()).toBeVisible();
  await expect(regionNotificaciones.getByText("NOTIFICADA", { exact: true })).toBeVisible();

  await expect(page.getByRole("heading", { name: "Consecuencias de ejecución y financieras" })).toBeVisible();
  await expect(page.getByText("no crea pagos")).toBeVisible();

  await page.getByRole("button", { name: "Formalizar" }).click();
  const dialog = page.getByRole("dialog");
  await expect(dialog).toBeVisible();
  await expect(dialog).toContainText(
    "Esta actuación modifica la situación jurídica del contrato y no se puede editar después de formalizarse.",
  );
  await dialog.getByRole("button", { name: "Formalizar" }).click();

  await expect(page.getByRole("status")).toContainText(`Formalizada: ${s.contrato.codigo}/TER`);
  await expect(page.getByText("Extinguido", { exact: true })).toBeVisible();

  const hitoBloqueadoResp = await request.post(`${API}/gobierno/contratos/${cid}/ejecucion/hitos`, {
    headers: s.mundo.headers,
    data: {
      descripcion: "Hito posterior a la terminación",
      fecha_prevista: sumarDias(s.hoy, 1),
      monto_previsto: "500.00",
      obligatorio: true,
    },
  });
  expect(hitoBloqueadoResp.status()).toBe(409);
  const hitoBloqueado = (await hitoBloqueadoResp.json()) as { code: string };
  expect(hitoBloqueado.code).toBe("GOV_CONTRACT_TERMINATED");

  await page.goto(`/gobierno/contratos/${cid}`);
  await expect(page.getByText(/Extinguido \(/)).toBeVisible();

  await page.goto(`/gobierno/contratos/${cid}/expediente`);
  await expect(page.getByRole("heading", { name: "Terminación / resolución / rescisión" })).toBeVisible();
  await expect(page.getByText(`${s.contrato.codigo}/TER`).first()).toBeVisible();

  const auditoriaResp = await request.get(`${API}/gobierno/contratos/${cid}/expediente/auditoria`, {
    headers: autoridad.headers,
  });
  expect(auditoriaResp.status()).toBe(200);
  const auditoria = (await auditoriaResp.json()) as { items: AuditoriaItem[] };
  expect(auditoria.items.some((item) => item.accion === "GOV_CONTRACT_TERMINATION_FORMALIZED")).toBe(true);

  const csvResp = await request.get(`${API}/gobierno/contratos/terminaciones/reporte.csv`, {
    headers: autoridad.headers,
  });
  expect(csvResp.status()).toBe(200);
  const csv = await csvResp.text();
  expect(csv).toContain(`${s.contrato.codigo}/TER`);

  const duplicadoResp = await request.post(`${API}/gobierno/contratos/${cid}/terminacion`, {
    headers: autoridad.headers,
    data: { figura: "RESCISION_NO_IMPUTABLE" },
  });
  expect(duplicadoResp.status()).toBe(409);
  const duplicado = (await duplicadoResp.json()) as { code: string };
  expect(duplicado.code).toBe("GOV_CONTRACT_TERMINATION_ALREADY_EXISTS");

  const sinPermiso = await crearUsuario(
    request,
    admin.headers,
    ["organization:view", "gobierno_contratos:view"],
    s.mundo.companyId,
  );
  const sinPermisoResp = await request.post(`${API}/gobierno/contratos/${cid}/terminacion`, {
    headers: sinPermiso.headers,
    data: { figura: "RESCISION_NO_IMPUTABLE" },
  });
  expect(sinPermisoResp.status()).toBe(403);

  const noExisteResp = await request.get(
    `${API}/gobierno/contratos/00000000-0000-0000-0000-000000000000/terminacion`,
    { headers: autoridad.headers },
  );
  expect(noExisteResp.status()).toBe(404);

  await page.goto(`/gobierno/contratos/${cid}/terminacion`);
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
