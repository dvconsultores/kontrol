import { expect, test, entrar, sesionApi } from "./helpers/sesion";
import { readFile } from "node:fs/promises";
import { ctx as ctxVentas, get as getV, marca, post as postV, postCrudo, type Ctx } from "./helpers/ventas";
import { laReservaDe, reservasDePedido } from "./helpers/reservas";
import { verificadorDeEscenario } from "./helpers/usuario";
import { mundoN6 } from "./helpers/n6-mundo";
import { type APIRequestContext } from "@playwright/test";

const TENANT = process.env.KONTROL_E2E_TENANT ?? "DEMO";
const USER = process.env.KONTROL_E2E_USER ?? "admin";
const API = process.env.KONTROL_E2E_API ?? "http://127.0.0.1:8000/api/v1";

async function fiscalListo(request: APIRequestContext, c: Ctx, m: string) {
  const admin = await sesionApi("admintenant", { tenant: TENANT });
  const tenantCtx: Ctx = { ...c, token: admin.token, headers: { ...c.headers, Authorization: `Bearer ${admin.token}` } };
  const fuente = await postV(request, tenantCtx, "/fiscal/legal-sources", {
    authority: "SENIAT", source_type: "LEY", number: `LI-${m}`, effective_from: "2020-01-01",
  });
  await postV(request, tenantCtx, `/fiscal/legal-sources/${fuente.id}/activate`, {});
  const serie = await postV(request, c, "/fiscal/number-series", {
    document_type: "INVOICE", prefix: "I",
  });
  const desde = 100000 + Math.floor(Math.random() * 800000);
  const lote = await postV(request, c, "/fiscal/control-batches", {
    range_from: String(desde), range_to: String(desde + 49),
  });
  return { series: serie.id as string, batch: lote.id as string };
}

test.setTimeout(600000);
test("expediente de importación de punta a punta", async ({ page, request }) => {
  const sufijo = Date.now().toString().slice(-8);
  const { token } = await sesionApi(USER, { tenant: TENANT });

  const authHeaders = (companyId: string) => ({
    Authorization: `Bearer ${token}`,
    "X-Kontrol-Company": companyId,
    "Content-Type": "application/json",
  });

  const getEmpresa = await fetch(`${API}/organization/companies`, {
    headers: {
      Authorization: `Bearer ${token}`,
      "X-Kontrol-Company": TENANT,
    },
  });
  expect(getEmpresa.ok).toBeTruthy();
  const empresas = (await getEmpresa.json()) as { items: Array<{ id: string }> };
  const companyId = empresas.items[0].id;

  const post = async <T>(
    ruta: string,
    datos: Record<string, unknown>,
  ): Promise<T> => {
    const res = await fetch(`${API}${ruta}`, {
      method: "POST",
      headers: authHeaders(companyId),
      body: JSON.stringify(datos),
    });
    expect([200, 201]).toContain(res.status);
    return (await res.json()) as T;
  };

  const monedasRes = await fetch(`${API}/treasury/currencies`, { headers: authHeaders(companyId) });
  const monedasJson = (await monedasRes.json()) as { items?: Array<{ code: string }> } | Array<{ code: string }>;
  const monedas = Array.isArray(monedasJson) ? monedasJson : (monedasJson.items ?? []);
  if (!monedas.some((m) => m.code === "USD")) await post("/treasury/currencies", { code: "USD", name: "Dólar" });
  const monedaGasto = `X${sufijo.slice(-5)}`;
  await post("/treasury/currencies", { code: monedaGasto, name: "Moneda E2E" });

  const proveedor = await post<{ id: string }>("/maestros/terceros", {
    code: `PRV-${sufijo}`,
    name: `Proveedor Import ${sufijo}`,
    roles: ["PROVEEDOR"],
    tax_id: `J-${sufijo}-0`,
  });

  const articulo = await post<{ id: string }>("/maestros/catalogos/items", {
    code: `ART-${sufijo}`,
    name: `Artículo ${sufijo}`,
    item_type: "PRODUCT",
  });

  const orden = await post<{ id: string }>("/purchasing/orders", {
    code: `OC-${sufijo}`,
    supplier_id: proveedor.id,
    currency: "USD",
  });

  await post(`/purchasing/orders/${orden.id}/lines`, {
    product_id: articulo.id,
    quantity_ordered: 10,
    unit_price: 5,
  });

  await post(`/purchasing/orders/${orden.id}/transition`, {
    target: "SUBMITTED",
  });
  await post(`/purchasing/orders/${orden.id}/transition`, {
    target: "APPROVED",
  });

  const tipoDocumental = await post<{ id: string }>("/documentos/tipos", {
    company_id: companyId,
    code: `IMP${sufijo}`,
    name: `Tipo Import ${sufijo}`,
    allowed_mime_types: ["application/pdf"],
    scan_required: true,
  });
  expect(tipoDocumental.id).toBeTruthy();

  await entrar(page, USER, { tenant: TENANT });
  await page.goto("/");
  if (page.viewportSize() && page.viewportSize()!.width < 1024) {
    await page.addLocatorHandler(
      page.getByRole("button", { name: "Cerrar notificación" }).first(),
      async (boton) => {
        await boton.click();
      },
    );
    await page.getByRole("button", { name: /abrir menú|menú/i }).click();
  }
  await page.getByRole("link", { name: "Importaciones" }).click();
  await expect(
    page.getByRole("heading", { name: "Importaciones", exact: true }),
  ).toBeVisible();
  await page.getByRole("link", { name: "Nueva importación" }).click();

  await page.getByLabel(/^Código \*/).fill(`IMP-${sufijo}`);

  const combo = page.getByLabel(/^Proveedor/);
  await combo.fill(`PRV-${sufijo}`);
  await page.getByRole("option", { name: new RegExp(`PRV-${sufijo}`) }).click();

  await page.getByLabel(/^Moneda/).fill("USD");
  await page.getByRole("button", { name: "Guardar", exact: true }).click();

  await expect(page).toHaveURL(/\/compras\/importaciones\/[0-9a-f-]{36}$/);
  await expect(page.getByText("En negociación").first()).toBeVisible();

  await page.getByLabel("Orden aprobada").click();
  await page.getByLabel("Orden aprobada").fill(`OC-${sufijo}`);
  await page
    .getByRole("option", { name: new RegExp(`OC-${sufijo}`) })
    .click();
  await page.getByRole("button", { name: "Vincular orden" }).click();
  await expect(page.getByRole("alert").first()).toContainText(
    "Completa la negociación",
  );

  await page.getByLabel(/^INCOTERM/).selectOption("FOB");
  await page.getByLabel(/^Condiciones de pago/).fill("Anticipo 30 %");
  await page
    .getByLabel(/^Condiciones de entrega/)
    .fill("Puerto de La Guaira");

  const guardarNegociacion = page.getByRole("button", {
    name: "Guardar negociación",
  });
  await guardarNegociacion.click();
  await expect(guardarNegociacion).toBeDisabled();

  await page.getByLabel("Orden aprobada").click();
  await page.getByLabel("Orden aprobada").fill(`OC-${sufijo}`);
  await page
    .getByRole("option", { name: new RegExp(`OC-${sufijo}`) })
    .click();
  await page.getByRole("button", { name: "Vincular orden" }).click();
  await expect(page.getByText("Orden vinculada").first()).toBeVisible();

  await page.getByRole("button", { name: "Confirmar documentación" }).click();
  await expect(page.getByRole("alert").first()).toContainText("Falta validar");

  const nombres = [
    "Documento de embarque",
    "Factura proforma",
    "Packing list",
  ];

  for (const nombre of nombres) {
    await page.getByLabel(`Referencia de ${nombre}`).fill(`REF-${sufijo}`);
    await page.getByRole("button", { name: `Recibir ${nombre}` }).click();
    const panel = page.locator("section").filter({
      has: page.getByRole("heading", { name: `Archivo de ${nombre}`, exact: true }),
    }).last();
    await panel.getByLabel("Tipo documental del archivo").selectOption({ label: `Tipo Import ${sufijo}` });
    await panel.locator('input[type="file"]').setInputFiles({
      name: "soporte.pdf",
      mimeType: "application/pdf",
      buffer: Buffer.from("%PDF-1.4\ntrailer\n%%EOF\n"),
    });
    await panel.getByRole("button", { name: "Adjuntar", exact: true }).click();
    await expect(panel.getByRole("button", { name: /Descargar soporte/ })).toBeVisible({ timeout: 60000 });
    await page.getByRole("button", { name: `Validar ${nombre}` }).click();
    await expect(page.getByRole("button", { name: `Validar ${nombre}` })).toHaveCount(0);
  }

  await page.getByRole("button", { name: "Confirmar documentación" }).click();
  await expect(page.getByText("Documentación completa").first()).toBeVisible();

  await expect(
    page.getByText("Documentación de importación confirmada"),
  ).toBeVisible();

  // Guardar URL del expediente antes de salir
  const expedienteUrl = page.url();

  // Crear agente por la ayuda post con roles PROVEEDOR
  const sufijoAgente = String(Date.now());
  await post<{ id: string }>("/maestros/terceros", {
    code: `AGT${sufijoAgente}`,
    name: `Agente ${sufijoAgente}`,
    roles: ["PROVEEDOR"],
  });

  // Aprobar proveedor
  await page.goto(`/maestros/terceros/${proveedor.id}`);
  await page.getByRole("button", { name: "Agregar en Cuentas bancarias" }).click();
  await page.getByLabel(/^Banco/).fill("Banco E2E");
  await page.getByLabel(/^Número de cuenta/).fill("01020000000000000001");
  await page.getByRole("button", { name: "Guardar", exact: true }).click();
  await expect(page.getByText("Banco E2E 01020000000000000001")).toBeVisible();
  await page
    .getByLabel("Evidencia de Banco E2E 01020000000000000001")
    .fill("constancia E2E");
  await page.getByRole("button", { name: "Verificar Banco E2E" }).click();
  await expect(
    page.getByText("Banco E2E 01020000000000000001 · Verificada"),
  ).toBeVisible();
  await page.getByRole("button", { name: "Aprobar proveedor" }).click();
  await expect(page.getByText("Estado de aprobación: Aprobado")).toBeVisible();

  // Volver a importación
  await page.goto(expedienteUrl);
  await page.getByLabel("Tipo", { exact: true }).selectOption("ADVANCE");
  await page.locator("#finanzas").getByLabel(/^Monto/).fill("100");
  await page.getByRole("button", { name: /^Registrar$/ }).click();
  await expect(page.getByText(/Anticipo 100\.00 USD/).first()).toBeVisible();

  // Designar agente y guardar seguimiento
  await page.getByLabel(/^Agente/).fill(`Agente ${sufijoAgente}`);
  await page.getByRole("option", { name: `Agente ${sufijoAgente}` }).click();
  await page.getByRole("button", { name: "Guardar seguimiento" }).click();
  await expect(page.getByText(`Agente ${sufijoAgente}`).first()).toBeVisible();

  // Hito Salida con fecha 2026-11-01
  await page.getByLabel(/^Hito/).selectOption("DEPARTED");
  await page.locator("#seguimiento").getByLabel(/^Fecha/).fill("2026-11-01");
  await page.getByRole("button", { name: "Registrar hito", exact: true }).click();
  await expect(
    page.getByRole("listitem").filter({ hasText: "2026-11-01" }).filter({ hasText: "Salida" })
  ).toBeVisible();

  // Abrir corrección: se ve «Orden vinculada»
  await page.getByLabel(/^Tipo de corrección/).selectOption("FALTANTE");
  await page.getByLabel(/^Descripción/).fill("Falta salida real");
  await page.getByLabel(/^Acción requerida/).fill("Registrar salida real");
  await page.getByRole("button", { name: "Crear corrección" }).click();
  await expect(page.getByText("Orden vinculada").first()).toBeVisible();

  // Resolverla: se ve «Resuelta»
  await page.getByLabel(/^Resolución/).fill("Resuelta");
  await page.getByRole("button", { name: "Resolver" }).click();
  await expect(page.getByText("Resuelta").first()).toBeVisible();

  // Confirmar documentación de nuevo
  await page.getByRole("button", { name: "Confirmar documentación" }).click();
  await expect(page.getByText("Documentación completa").first()).toBeVisible();

  // Confirmar despacho
  await page.getByRole("button", { name: "Confirmar despacho" }).click();
  await expect(page.getByText("Despachada").first()).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Cancelar importación" }),
  ).not.toBeVisible();
  await expect(page.getByText("Registra la recepción de la mercancía.").first()).toBeVisible();
  await expect(page.getByText("Despacho confirmado").first()).toBeVisible();

  const branchesRes = await fetch(`${API}/organization/branches`, {
    headers: authHeaders(companyId),
  });
  const branchesData = await branchesRes.json();
  const branches = Array.isArray(branchesData) ? branchesData : branchesData.items;
  let branchId = branches?.[0]?.id;
  if (!branchId) {
    branchId = await post<{ id: string }>("/organization/branches", {
      company_id: companyId,
      code: `BR-${sufijo}`,
      name: "Sucursal E2E",
    }).then((r) => r.id);
  }

  const almacen = await post<{ id: string }>("/organization/warehouses", {
    company_id: companyId,
    branch_id: branchId,
    code: `W-${sufijo}`,
    name: "Almacén E2E",
  }).then((r) => r.id);

  await page.reload();
  await expect(page.getByText("Registra la recepción de la mercancía.").first()).toBeVisible();

  const niveles = await fetch(`${API}/organization/warehouses/${almacen}/structure-levels`, {
    method: "PATCH",
    headers: authHeaders(companyId),
    body: JSON.stringify({ structure_levels: { zone: true } }),
  });
  expect(niveles.ok).toBeTruthy();

  const tipoZona = await post<{ id: string }>("/organization/zone-types", {
    company_id: companyId,
    code: `TZ-${sufijo}`,
    name: `Fríos ${sufijo}`,
  });
  const zona1 = await post<{ id: string; code: string }>(`/organization/warehouses/${almacen}/zones`, {
    code: `Z1-${sufijo}`,
    name: `Zona Fríos ${sufijo}`,
    zone_type_id: tipoZona.id,
    sequence: 1,
  });
  const zona2 = await post<{ id: string; code: string }>(`/organization/warehouses/${almacen}/zones`, {
    code: `Z2-${sufijo}`,
    name: `Zona General ${sufijo}`,
    sequence: 2,
  });

  const ubicacion = await post<{ id: string; code: string }>("/organization/locations", {
    warehouse_id: almacen,
    code: `OK-${sufijo}`,
    name: "Rack válido",
    sequence: 1,
    zone_id: zona1.id,
  });
  const ubicacionZ2 = await post<{ id: string; code: string }>("/organization/locations", {
    warehouse_id: almacen,
    code: `Z2L-${sufijo}`,
    name: "Rack general",
    sequence: 2,
    zone_id: zona2.id,
  });

  // 1. Crear recepción
  await page.locator("#recepcion").getByLabel(/^Código/).fill(`REC-${sufijo}`);
  await page.locator("#recepcion").getByLabel(/^Almacén/).selectOption(almacen);
  await page.locator("#recepcion").getByRole("button", { name: "Crear recepción" }).click();
  await expect(page.getByText("Esperando arribo")).toBeVisible();

  // 2. Confirmar arribo
  await page.locator("#arribo").getByLabel(/Bultos recibidos/).fill("10");
  await page.locator("#arribo").getByRole("button", { name: `Confirmar arribo de REC-${sufijo}` }).click();
  await expect(page.getByText("En recepción")).toBeVisible();

  // 3. Abrir recepción y completar calidad
  await page.getByRole("link", { name: `Abrir recepción REC-${sufijo}` }).click();
  await page.getByRole("link", { name: "Volver al expediente" }).waitFor();
  await page.getByLabel(/Línea de la orden/).selectOption({ index: 1 });
  await page.getByLabel(/^Recibido/).fill("10");
  await page.getByRole("button", { name: "Registrar", exact: true }).click();
  const filaRecepcion = page.locator("tr", { hasText: `REC-${sufijo}` });
  const confirmar = filaRecepcion.getByRole("button", { name: "confirmar", exact: true });
  await confirmar.waitFor();
  await confirmar.click();
  await page.waitForLoadState("networkidle");
  const enviarCalidad = filaRecepcion.getByRole("button", { name: "enviar a calidad", exact: true });
  await enviarCalidad.waitFor();
  await enviarCalidad.click();
  await page.waitForLoadState("networkidle");
  const conforme = filaRecepcion.getByRole("button", { name: "conforme", exact: true });
  await conforme.waitFor();
  await conforme.click();
  await page.waitForLoadState("networkidle");
  const aceptar = filaRecepcion.getByRole("button", { name: "aceptar", exact: true });
  await aceptar.waitFor();
  await aceptar.click();
  await page.waitForLoadState("networkidle");
  await page.getByRole("link", { name: "Volver al expediente" }).click();

  // 4. Gestionar incidencias
  await page.getByRole("link", { name: `Gestionar incidencias de REC-${sufijo}` }).click();
  await expect(page.getByRole("heading", { name: "Incidencias de recepción" })).toBeVisible();
  await page.getByLabel(/^Código/).fill(`INC-${sufijo}`);
  await page.getByLabel(/^Tipo/).selectOption("DANO");
  await page.getByLabel(/Línea recibida/).selectOption({ index: 1 });
  await page.getByLabel(/Cantidad afectada/).fill("3");
  await page.getByRole("button", { name: "Registrar", exact: true }).click();
  const filaIncidencia = page.locator("tr", { hasText: `INC-${sufijo}` });
  await filaIncidencia.getByRole("button", { name: "escalar", exact: true }).click();
  await expect(filaIncidencia.getByText("Escalada a Compras")).toBeVisible();
  await filaIncidencia.getByRole("button", { name: "tratar", exact: true }).click();
  const dialog = page.getByRole("dialog");
  await dialog.getByLabel(/Tratamiento/).selectOption("RECLAMO_PROVEEDOR");
  await dialog.getByLabel(/Motivo/).fill("Daño en transporte");
  await dialog.getByRole("button", { name: "Registrar tratamiento" }).click();
  await expect(filaIncidencia.getByText("Resuelta")).toBeVisible();
  await page.getByRole("link", { name: "Volver al expediente" }).click();
  await expect(page.locator("#diferencias").getByText(`INC-${sufijo}`).first()).toBeVisible();
  await expect(page.getByText("Por confirmar inventario")).toBeVisible();

  // 4.5. Reporte formal de diferencias (R1 y R2)
  const idExpediente = new URL(expedienteUrl).pathname.split("/").pop()!;
  const seccionReporte = page.getByRole("region", { name: `Reporte formal de diferencias · REC-${sufijo}` });

  const expedienteResp = await page.request.get(`${API}/importaciones/${idExpediente}`, {
    headers: authHeaders(companyId),
  });
  expect(expedienteResp.ok()).toBeTruthy();
  const expedienteJson = await expedienteResp.json();
  const receiptId = expedienteJson.logistics.receipts.find(
    (r: { code: string }) => r.code === `REC-${sufijo}`,
  ).id;

  await expect(seccionReporte).toContainText("Diferencias detectadas sin reporte");

  await seccionReporte.getByRole("button", { name: "Emitir reporte formal" }).click();
  await expect(seccionReporte).toContainText(/DIF-\d{6}-R1/);
  await expect(seccionReporte).toContainText("Revisión 1");
  await expect(seccionReporte).toContainText(`Emitido por ${USER}`);
  await expect(seccionReporte).toContainText("Reporte emitido");

  const textoR1 = await seccionReporte.textContent();
  const referenciaR1 = textoR1!.match(/DIF-\d{6}-R1/)![0];

  const descarga = page.waitForEvent("download");
  await seccionReporte.getByRole("button", { name: "Descargar PDF" }).click();
  const archivo = await descarga;
  expect(archivo.suggestedFilename()).toMatch(/\.pdf$/);
  expect(archivo.suggestedFilename()).toContain(referenciaR1);
  const contenido = await readFile((await archivo.path())!);
  expect(contenido.subarray(0, 5).toString()).toBe("%PDF-");

  const respuestaInline = page.waitForResponse(
    (r) => r.url().includes("/pdf?inline=true") && r.status() === 200,
  );
  const pestana = page.context().waitForEvent("page");
  await seccionReporte.getByRole("button", { name: "Imprimir" }).click();
  await respuestaInline;
  const nueva = await pestana;
  expect(nueva.url()).toMatch(/^blob:/);
  await nueva.close();

  const docResp = await post<{ id: string }>(`/purchasing/receipts/${receiptId}/incidencias`, {
    code: `DOC-${sufijo}`,
    incident_type: "DIFERENCIA_DOCUMENTAL",
    description: "Packing list no coincide con la factura",
  });
  await post(`/purchasing/receipts/${receiptId}/incidencias/${docResp.id}/resolve`, {
    resolution: "RECLAMO_PROVEEDOR",
    reason: "Reclamo documental",
  });

  await page.reload();
  await expect(seccionReporte).toContainText("Nueva revisión disponible");

  await seccionReporte.getByRole("button", { name: "Emitir nueva revisión" }).click();
  await expect(seccionReporte).toContainText(/DIF-\d{6}-R2/);

  const textoR2 = await seccionReporte.textContent();
  const referenciaR2 = textoR2!.match(/DIF-\d{6}-R2/)![0];
  expect(referenciaR2.slice(0, 10)).toBe(referenciaR1.slice(0, 10));

  const historial = seccionReporte.getByRole("list", { name: "Historial de revisiones" });
  await expect(historial).toContainText(referenciaR2);
  await expect(historial).toContainText(referenciaR1);
  await expect(historial.getByRole("button", { name: `Descargar ${referenciaR2}` })).toBeVisible();
  await expect(historial.getByRole("button", { name: `Descargar ${referenciaR1}` })).toBeVisible();

  await page.goto(`/compras/recepciones?recepcion=${receiptId}&importacion=${idExpediente}`);
  const seccionRecepcion = page.getByRole("region", { name: "Reporte formal de diferencias", exact: true });
  await expect(seccionRecepcion).toContainText(`Abrir expediente IMP-${sufijo}`);
  await expect(seccionRecepcion).toContainText(referenciaR1);
  await expect(seccionRecepcion).toContainText(referenciaR2);

  const listaReportes = seccionRecepcion.getByRole("list", { name: "Reportes de diferencias" });
  await expect(listaReportes).toContainText(referenciaR1);
  await expect(listaReportes).toContainText(referenciaR2);

  await seccionRecepcion.getByRole("link", { name: `Abrir expediente IMP-${sufijo}` }).click();
  await expect(page).toHaveURL(new RegExp(`/compras/importaciones/${idExpediente}`));
  await expect(page.locator("#diferencias")).toContainText(`INC-${sufijo}`);

  await expect(seccionReporte).not.toContainText(/[0-9a-f]{8}-[0-9a-f]{4}-/);

  // N1: antes de confirmar, la mercancía no confirmada no es vendible
  const saldosNoConfirmadosResponse = await fetch(
    `${API}/inventory/balances?product_id=${articulo.id}&warehouse_id=${almacen}&page_size=100`,
    { headers: authHeaders(companyId) },
  );
  expect(saldosNoConfirmadosResponse.ok).toBeTruthy();
  const saldosNoConfirmados = ((await saldosNoConfirmadosResponse.json()) as {
    items: Array<{ qty_available: number | string; state: string; qty_on_hand: number | string }>;
  }).items;
  const qtyAvailableNoConfirmado = saldosNoConfirmados
    .filter((item) => item.state === "DISPONIBLE")
    .reduce((acc, item) => acc + Number(item.qty_available ?? 0), 0);
  expect(qtyAvailableNoConfirmado).toBe(0);
  const qtyOnHandRecibido = saldosNoConfirmados
    .filter((item) => item.state === "RECIBIDO")
    .reduce((acc, item) => acc + Number(item.qty_on_hand ?? 0), 0);
  expect(qtyOnHandRecibido).toBe(10);

  // 5. Confirmar inventario
  await page.getByRole("link", { name: `Confirmar inventario de REC-${sufijo}` }).click();
  await expect(page.getByRole("heading", { name: "Confirmación de inventario" })).toBeVisible();
  await page.getByLabel(/Contado \(base\)/).fill("10");
  await page.getByRole("button", { name: "Registrar conteo" }).click();
  await expect(page.getByText("Faltan líneas por contar.")).toBeHidden();
  await page.getByLabel(/Cantidad a confirmar/).fill("10");
  await page.getByRole("button", { name: "Confirmar inventario" }).click();
  await expect(page.getByRole("heading", { name: "Decisiones tomadas" })).toBeVisible();
  await page.getByRole("link", { name: "Volver al expediente" }).click();
  await expect(page.getByText("Por ubicar")).toBeVisible();

  // 6. Ubicar mercancía
  await page.goto("/maestros/almacenamiento");
  const condiciones = page.getByRole("region", { name: "Condiciones especiales" });
  const perfil = page.getByRole("region", { name: "Perfil de almacenamiento del producto" });
  const reglas = page.getByRole("region", { name: "Reglas de almacenamiento" });
  const politica = page.getByRole("region", { name: "Política del almacén" });

  await condiciones.getByLabel(/^Código/).fill(`FRA-${sufijo}`);
  await condiciones.getByLabel(/^Nombre/).fill(`Frágil ${sufijo}`);
  await condiciones.getByRole("button", { name: "Crear condición" }).click();
  await expect(condiciones.getByText(`FRA-${sufijo}`)).toBeVisible();

  await perfil.getByLabel(/^Producto/).fill(`ART-${sufijo}`);
  await page.getByRole("listbox").getByRole("option", { name: new RegExp(`ART-${sufijo}`) }).click();
  await perfil.getByLabel(`FRA-${sufijo} - Frágil ${sufijo}`).check();
  await perfil.getByRole("button", { name: "Guardar perfil" }).click();
  await expect(perfil.getByLabel(`FRA-${sufijo} - Frágil ${sufijo}`)).toBeChecked();

  await reglas.getByLabel(/^Código/).fill(`REG-${sufijo}`);
  await reglas.getByLabel(/^Nombre/).fill(`Regla fríos ${sufijo}`);
  await reglas.getByLabel(/^Prioridad/).fill("1");
  await reglas.getByLabel(/^Almacén/).selectOption(almacen);
  await reglas.getByLabel(/^Tipo de destino/).selectOption("ZONE");
  await reglas.getByLabel(/^Zona$/).selectOption(zona1.id);
  await reglas.getByLabel(/^Condición especial/).selectOption({ label: `FRA-${sufijo} - Frágil ${sufijo}` });
  await reglas.getByLabel(/^Etiquetado/).selectOption("REQUIRED");
  await reglas.getByRole("button", { name: "Crear regla" }).click();
  await expect(reglas.getByText(`REG-${sufijo}`)).toBeVisible();

  await politica.getByLabel(/^Almacén de la política/).selectOption(almacen);
  await politica.getByLabel(/^Clasificación/).selectOption("ENFORCED");
  await politica.getByLabel(/^Sin regla aplicable/).selectOption("BLOCK");
  await politica.getByRole("button", { name: "Guardar política" }).click();

  await page.goto(expedienteUrl);
  const clasificacion = page.getByRole("region", { name: "Clasificación de almacenamiento" });
  const filaAlmacen = clasificacion.getByRole("group", { name: `Artículo ${sufijo} · REC-${sufijo}` });
  await expect(filaAlmacen).toContainText("Sin clasificar");
  await filaAlmacen.getByRole("button", { name: "Clasificar" }).click();
  await expect(filaAlmacen).toContainText("Zona determinada:");
  await expect(filaAlmacen).toContainText(`Zona Fríos ${sufijo}`);
  await expect(filaAlmacen).toContainText(`REG-${sufijo}`);
  await expect(filaAlmacen).toContainText("Etiqueta requerida");
  await expect(filaAlmacen.getByRole("button", { name: `Ubicar Artículo ${sufijo}` })).toBeDisabled();
  await expect(filaAlmacen.getByLabel(/^Ubicación de destino/).locator("option:not([value=''])")).toHaveCount(1);
  await expect(filaAlmacen.getByLabel(/^Ubicación de destino/)).toContainText(ubicacion.code);
  await expect(filaAlmacen.getByLabel(/^Ubicación de destino/)).not.toContainText(ubicacionZ2.code);

  await filaAlmacen.getByRole("button", { name: "Generar etiqueta" }).click();
  const botonDescargaEtq = filaAlmacen.getByRole("button", { name: /^Descargar ETQ-\d{6}$/ });
  await expect(botonDescargaEtq).toBeVisible();
  const descargaEtq = page.waitForEvent("download");
  await botonDescargaEtq.click();
  const archivoEtq = await descargaEtq;
  expect(archivoEtq.suggestedFilename()).toMatch(/^ETQ-\d{6}\.pdf$/);
  expect((await readFile((await archivoEtq.path())!)).subarray(0, 5).toString()).toBe("%PDF-");

  await filaAlmacen.getByLabel(/^Ubicación de destino/).selectOption(ubicacion.id);
  const botonUbicar = filaAlmacen.getByRole("button", { name: `Ubicar Artículo ${sufijo}` });
  await expect(botonUbicar).toBeEnabled();
  await botonUbicar.click();
  await expect(page.getByText("Recibida y ubicada").first()).toBeVisible();
  await expect(page.locator("#ubicacion").getByText(ubicacion.code).first()).toBeVisible();
  await expect(page.getByText("Mercancía recibida y ubicada. Queda pendiente el costo de importación.").first()).toBeVisible();

  // 6.5. Validación física y reubicación por error (A → B)
  const ubicacionB = await post<{ id: string; code: string }>("/organization/locations", {
    warehouse_id: almacen,
    code: `OKB-${sufijo}`,
    name: "Rack B",
    sequence: 2,
  });
  await page.reload();

  const saldosAntesResponse = await fetch(
    `${API}/inventory/balances?product_id=${articulo.id}&warehouse_id=${almacen}&page_size=100`,
    { headers: authHeaders(companyId) },
  );
  expect(saldosAntesResponse.ok).toBeTruthy();
  const saldosAntes = (await saldosAntesResponse.json()) as {
    items: Array<{ location_id: string | null; state: string; qty_on_hand: number | string }>;
  };
  const saldoA_antes = Number(
    saldosAntes.items.find((item) => item.location_id === ubicacion.id)?.qty_on_hand ?? 0,
  );
  const totalAntes = saldosAntes.items.reduce((acc, item) => acc + Number(item.qty_on_hand ?? 0), 0);
  const estadosAntes = saldosAntes.items.map((item) => item.state);

  const valoracionAntesResponse = await fetch(
    `${API}/inventory/valuation?product_id=${articulo.id}&warehouse_id=${almacen}`,
    { headers: authHeaders(companyId) },
  );
  expect(valoracionAntesResponse.ok).toBeTruthy();
  const valoracionAntes = ((await valoracionAntesResponse.json()) as { valuation: number }).valuation;

  const regionUbicacion = page.getByRole("region", { name: "Ubicación física" });
  const filaA = regionUbicacion.getByRole("group", { name: `Artículo ${sufijo} en ${ubicacion.code}` });
  await expect(filaA.getByText(`Ubicación registrada: ${ubicacion.code}`)).toBeVisible();
  await expect(filaA.getByRole("status")).toHaveText("Sin validar");

  // MATCH
  await filaA.getByLabel(/Ubicación encontrada/).selectOption(ubicacion.id);
  await filaA.getByRole("button", { name: "Validar ubicación física" }).click();
  await expect(filaA.getByRole("status")).toHaveText("Coincide · Ubicación física validada");
  const cerrarMatch = page.getByRole("button", { name: "Cerrar notificación" });
  if (await cerrarMatch.count()) await cerrarMatch.first().click();

  // MISMATCH
  await filaA.getByLabel(/Ubicación encontrada/).selectOption(ubicacionB.id);
  await filaA.getByRole("button", { name: "Validar ubicación física" }).click();
  await expect(filaA.getByRole("status")).toContainText("No coincide");
  await expect(filaA.getByText(`Registrada: ${ubicacion.code}`, { exact: true })).toBeVisible();
  await expect(filaA.getByText(`Encontrada: ${ubicacionB.code}`, { exact: true })).toBeVisible();
  const cerrarMismatch = page.getByRole("button", { name: "Cerrar notificación" });
  if (await cerrarMismatch.count()) await cerrarMismatch.first().click();

  const saldosMismatchResponse = await fetch(
    `${API}/inventory/balances?product_id=${articulo.id}&warehouse_id=${almacen}&page_size=100`,
    { headers: authHeaders(companyId) },
  );
  expect(saldosMismatchResponse.ok).toBeTruthy();
  const saldosMismatch = (await saldosMismatchResponse.json()) as {
    items: Array<{ location_id: string | null; state: string; qty_on_hand: number | string }>;
  };
  expect(
    Number(saldosMismatch.items.find((item) => item.location_id === ubicacion.id)?.qty_on_hand ?? 0),
  ).toBe(saldoA_antes);

  // Reubicar por error
  await filaA.getByRole("button", { name: "Reubicar por error" }).click();
  const dialogo = page.getByRole("dialog");
  await expect(dialogo.getByText(ubicacion.code)).toBeVisible();
  await expect(dialogo.getByText(ubicacionB.code)).toBeVisible();
  await dialogo.getByLabel(/^Motivo/).fill("Error de colocación E2E");
  await dialogo.getByRole("button", { name: "Confirmar reubicación" }).click();
  const cerrarReubicacion = page.getByRole("button", { name: "Cerrar notificación" });
  if (await cerrarReubicacion.count()) await cerrarReubicacion.first().click();

  const filaB = regionUbicacion.getByRole("group", { name: `Artículo ${sufijo} en ${ubicacionB.code}` });
  await expect(filaB.getByText(`Ubicación registrada: ${ubicacionB.code}`)).toBeVisible();
  await expect(
    regionUbicacion.getByRole("group", { name: `Artículo ${sufijo} en ${ubicacion.code}` }),
  ).toHaveCount(0);

  const saldosDespuesResponse = await fetch(
    `${API}/inventory/balances?product_id=${articulo.id}&warehouse_id=${almacen}&page_size=100`,
    { headers: authHeaders(companyId) },
  );
  expect(saldosDespuesResponse.ok).toBeTruthy();
  const saldosDespues = (await saldosDespuesResponse.json()) as {
    items: Array<{ location_id: string | null; state: string; qty_on_hand: number | string }>;
  };
  expect(
    Number(saldosDespues.items.find((item) => item.location_id === ubicacion.id)?.qty_on_hand ?? 0),
  ).toBe(saldoA_antes - saldoA_antes);
  expect(
    Number(saldosDespues.items.find((item) => item.location_id === ubicacionB.id)?.qty_on_hand ?? 0),
  ).toBe(saldoA_antes);
  expect(saldosDespues.items.reduce((acc, item) => acc + Number(item.qty_on_hand ?? 0), 0)).toBe(totalAntes);
  expect([...new Set(saldosDespues.items.map((item) => item.state))].sort()).toEqual([...new Set(estadosAntes)].sort());

  const valoracionDespuesResponse = await fetch(
    `${API}/inventory/valuation?product_id=${articulo.id}&warehouse_id=${almacen}`,
    { headers: authHeaders(companyId) },
  );
  expect(valoracionDespuesResponse.ok).toBeTruthy();
  const valoracionDespues = ((await valoracionDespuesResponse.json()) as { valuation: number }).valuation;
  expect(valoracionDespues).toBeCloseTo(valoracionAntes, 2);

  const historialFisico = regionUbicacion.getByRole("list", { name: "Historial de ubicación física" });
  await expect(historialFisico).toContainText("Coincide");
  await expect(historialFisico).toContainText("No coincide");
  await expect(historialFisico).toContainText(`${ubicacion.code} → ${ubicacionB.code}`);
  await expect(historialFisico).toContainText("Motivo: Error de colocación E2E");
  await expect(historialFisico).not.toHaveText(/[0-9a-f]{8}-[0-9a-f]{4}-/);

  await expect(page.locator("#ubicacion").getByText(ubicacionB.code).first()).toBeVisible();

  // 7. Historial
  await expect(page.getByText("Recepción creada desde la importación").first()).toBeVisible();

  const costos = page.locator("#costos");
  await expect(page.getByRole("link", { name: "Costos", exact: true })).toBeVisible();
  await page.getByRole("link", { name: "Costos", exact: true }).click();

  await expect(costos.getByText("Todavía no hay gastos registrados.")).toBeVisible();
  await expect(page.getByRole("button", { name: /aplicar/i })).toHaveCount(0);
  await expect(costos.getByText(`Artículo ${sufijo}`)).toBeVisible();
  await expect(costos.getByText(`REC-${sufijo}`)).toBeVisible();
  await expect(costos.getByText("5,00 USD")).toBeVisible();
  await expect(costos.getByText("Mercancía según capas de costo")).toBeVisible();

  const importId = new URL(expedienteUrl).pathname.split("/").pop()!;

  const campoConcepto = costos.getByLabel(/^Concepto/);
  await campoConcepto.fill("Flete internacional");
  await page.getByLabel(/^Proveedor/).fill(`Proveedor Import ${sufijo}`);
  await page.getByRole("option", { name: `Proveedor Import ${sufijo}` }).click();
  await costos.getByLabel(/^Referencia/).fill(`FL-${sufijo}`);
  await costos.getByLabel(/^Moneda/).selectOption(monedaGasto);
  await costos.getByLabel(/^Fecha/).fill(new Date().toISOString().slice(0, 10));
  await costos.getByLabel(/^Monto/).fill("1250,50");
  await costos.getByRole("button", { name: "Registrar gasto" }).click();

  await expect(page.locator("main").getByText(/tasa/i).first()).toBeVisible();
  await expect(page.getByRole("link", { name: "Registrar tasa en Tesorería" })).toBeVisible();

  const costosRespuesta = await fetch(`${API}/importaciones/${importId}/costs`, { headers: authHeaders(companyId) }).then((r) => r.json() as Promise<{ functional_currency: string }>);
  const functionalCurrency = costosRespuesta.functional_currency;

  const fnEnMaestro = await fetch(`${API}/treasury/currencies`, { headers: authHeaders(companyId) }).then((r) => r.json() as Promise<{ items?: Array<{ code: string }> } | Array<{ code: string }>>);
  const lista = Array.isArray(fnEnMaestro) ? fnEnMaestro : (fnEnMaestro.items ?? []);
  if (!lista.some((m) => m.code === functionalCurrency)) await post("/treasury/currencies", { code: functionalCurrency, name: functionalCurrency });
  const fuente = await post<{ id: string }>("/treasury/rate-sources", { code: `FT-${sufijo}`, name: "Fuente E2E" });
  await post("/treasury/exchange-rates/observations", {
    base_currency: monedaGasto,
    quote_currency: functionalCurrency,
    source_id: fuente.id,
    rate: "36.125",
    effective_at: new Date(Date.now() - 2 * 24 * 60 * 60 * 1000).toISOString(),
  });

  await costos.getByRole("button", { name: "Registrar gasto" }).click();
  await expect(costos.getByText("Gasto registrado.")).toBeVisible();
  await expect(costos.getByText("Flete internacional")).toBeVisible();
  await expect(costos.getByText(`1.250,50 ${monedaGasto}`).first()).toBeVisible();
  await expect(costos.getByText(`1 ${monedaGasto} = 36,125 ${functionalCurrency}`)).toBeVisible();
  await expect(costos.getByText(`45.174,31 ${functionalCurrency}`).first()).toBeVisible();
  await expect(costos.getByText("Gastos registrados").locator("..").getByText("1", { exact: true })).toBeVisible();

  await campoConcepto.fill("Gasto erróneo");
  await page.getByLabel(/^Proveedor/).fill(`Proveedor Import ${sufijo}`);
  await page.getByRole("option", { name: `Proveedor Import ${sufijo}` }).click();
  await costos.getByLabel(/^Referencia/).fill(`ERR-${sufijo}`);
  await costos.getByLabel(/^Moneda/).selectOption(functionalCurrency);
  await costos.getByLabel(/^Fecha/).fill(new Date().toISOString().slice(0, 10));
  await costos.getByLabel(/^Monto/).fill("100,10");
  await costos.getByRole("button", { name: "Registrar gasto" }).click();
  await expect(costos.getByText("Misma moneda, sin conversión")).toBeVisible();

  await page.reload();
  await costos.getByRole("button", { name: `Anular gasto ERR-${sufijo}` }).click();
  await page.getByLabel("Motivo de anulación").fill("Error de captura");
  await page.getByRole("dialog").getByRole("button", { name: "Anular gasto" }).click();
  await expect(costos.getByText("Anulado · Motivo: Error de captura")).toBeVisible();
  await expect(costos.getByText(`45.174,31 ${functionalCurrency}`).first()).toBeVisible();

  await expect(costos).not.toContainText(/[0-9a-f]{8}-[0-9a-f]{4}-/);

  await post("/treasury/exchange-rates/observations", {
    base_currency: "USD",
    quote_currency: functionalCurrency,
    source_id: fuente.id,
    rate: "36.125",
    effective_at: new Date(Date.now() - 2 * 24 * 60 * 60 * 1000).toISOString(),
  });

  const cerrarNotificacion = async () => {
    const boton = page.getByRole("button", { name: "Cerrar notificación" });
    if (await boton.count()) {
      await boton.first().click();
    }
  };

  await page.getByRole("button", { name: "Registrar gasto" }).click();
  await campoConcepto.fill("Flete capitalizable");
  await page.getByLabel(/^Proveedor/).fill(`Proveedor Import ${sufijo}`);
  await page.getByRole("option", { name: `Proveedor Import ${sufijo}` }).click();
  await costos.getByLabel(/^Referencia/).fill(`FC-${sufijo}`);
  await costos.getByLabel(/^Moneda/).selectOption("USD");
  await costos.getByLabel(/^Fecha/).fill(new Date().toISOString().slice(0, 10));
  await costos.getByLabel(/^Monto/).fill("10,00");
  await costos.getByRole("button", { name: "Registrar gasto" }).click();
  await expect(costos.getByText("Flete capitalizable")).toBeVisible();

  let tarjeta = costos.locator("li").filter({ hasText: "Flete capitalizable" });
  await expect(tarjeta).toBeVisible();

  await tarjeta.getByText("Por valor").click();
  await tarjeta.getByRole("button", { name: "Generar vista previa" }).click();
  await expect(tarjeta.getByText("El gasto no está clasificado como capitalizable.")).toBeVisible();
  await expect(tarjeta.getByRole("button", { name: "Aplicar costo" })).toHaveCount(0);

  await tarjeta.getByLabel(/^Clasificación del costo/).selectOption("CAPITALIZABLE");
  await tarjeta.getByRole("button", { name: "Guardar clasificación" }).click();
  await expect(tarjeta.getByLabel(/^Clasificación del costo/)).toHaveValue("CAPITALIZABLE");

  await tarjeta.getByText("Por valor").click();
  const previa = page.waitForResponse(
    (r) => r.url().includes("/allocation-preview") && r.status() === 200,
  );
  await tarjeta.getByRole("button", { name: "Generar vista previa" }).click();
  const tokenVistaPrevia = ((await (await previa).json()) as { preview_token: string }).preview_token;

  await expect(tarjeta.getByText("Vista previa: aún no se ha aplicado nada")).toBeVisible();
  await expect(tarjeta.getByText("El reparto cuadra exactamente")).toBeVisible();
  await expect(costos.getByText("50,00 USD").first()).toBeVisible();

  await cerrarNotificacion();
  await tarjeta.getByRole("button", { name: "Aplicar costo" }).click();
  const dialogoAplicar = page.getByRole("dialog");
  await expect(dialogoAplicar.getByText("Flete capitalizable")).toBeVisible();
  await expect(dialogoAplicar.getByText("10,00 USD").first()).toBeVisible();
  await dialogoAplicar.getByRole("button", { name: "Confirmar aplicación" }).click();

  await expect(tarjeta.getByText("Aplicado", { exact: true })).toBeVisible();
  await expect(costos.getByText("6,000000 USD").first()).toBeVisible();
  await expect(costos.getByText("60,00 USD").first()).toBeVisible();

  const gastos = (await (
    await fetch(`${API}/importaciones/${importId}/costs`, { headers: authHeaders(companyId) })
  ).json()) as { expenses: Array<{ id: string; concept: string }> };
  const gastoCapitalizable = gastos.expenses.find((item) => item.concept === "Flete capitalizable");
  const reintento = await fetch(
    `${API}/importaciones/${importId}/expenses/${gastoCapitalizable?.id}/apply`,
    {
      method: "POST",
      headers: authHeaders(companyId),
      body: JSON.stringify({ criterion: "VALUE", preview_token: tokenVistaPrevia }),
    },
  );
  expect(reintento.status).toBe(409);
  expect(((await reintento.json()) as { code: string }).code).toBe("IMPORT_COST_ALREADY_APPLIED");

  await page.reload();
  tarjeta = costos.locator("li").filter({ hasText: "Flete capitalizable" });
  await expect(tarjeta).toBeVisible();
  await expect(costos.getByText("60,00 USD").first()).toBeVisible();
  const valoracion = (await (
    await fetch(`${API}/inventory/valuation`, { headers: authHeaders(companyId) })
  ).json()) as { by_currency: Array<{ currency: string }> };
  expect(valoracion.by_currency.some((item) => item.currency === "USD")).toBeTruthy();

  await cerrarNotificacion();
  await tarjeta.getByRole("button", { name: "Revertir aplicación" }).click();
  const dialogoRevertir = page.getByRole("dialog");
  await dialogoRevertir.getByLabel("Motivo de reversión").fill("Prueba E2E");
  await dialogoRevertir.getByRole("button", { name: "Confirmar reversión" }).click();
  await expect(tarjeta.getByText("Revertido", { exact: true })).toBeVisible();
  await expect(costos.getByText("50,00 USD").first()).toBeVisible();
  await expect(tarjeta.getByText("Historial de aplicación")).toBeVisible();

  await page.getByRole("link", { name: "Historial" }).click();
  await expect(page.getByText("Gasto de importación aplicado a capas de costo").first()).toBeVisible();
  await expect(page.getByText("Aplicación de gasto de importación revertida").first()).toBeVisible();
  await expect(page.getByText("Gasto de importación registrado").first()).toBeVisible();
  await expect(page.getByText("Gasto de importación anulado").first()).toBeVisible();

  const previewReaplicar = (await (
    await fetch(`${API}/importaciones/${importId}/expenses/${gastoCapitalizable?.id}/allocation-preview`, {
      method: "POST",
      headers: authHeaders(companyId),
      body: JSON.stringify({ criterion: "VALUE" }),
    })
  ).json()) as { preview_token: string };
  const reaplicar = await fetch(
    `${API}/importaciones/${importId}/expenses/${gastoCapitalizable?.id}/apply`,
    {
      method: "POST",
      headers: authHeaders(companyId),
      body: JSON.stringify({ criterion: "VALUE", preview_token: previewReaplicar.preview_token }),
    },
  );
  expect(reaplicar.ok).toBeTruthy();
  const costosReaplicados = (await (
    await fetch(`${API}/importaciones/${importId}/costs`, { headers: authHeaders(companyId) })
  ).json()) as {
    layers: Array<{
      product_name: string;
      effective_unit_cost: string;
      value: string;
      quantity_remaining: string;
    }>;
  };
  const capaReaplicada = costosReaplicados.layers.find(
    (item) => item.product_name === `Artículo ${sufijo}`,
  );
  expect(capaReaplicada).toBeTruthy();
  expect(capaReaplicada!.effective_unit_cost).toBe("6.000000");
  expect(capaReaplicada!.value).toBe("60.00");

  // 7. Saldos y valoración tras el put-away
  const c = await ctxVentas(request);
  expect(c.company).toBe(companyId);
  const m = marca();

  const saldosPostPutawayResponse = await getV(
    request,
    c,
    `/inventory/balances?product_id=${articulo.id}&warehouse_id=${almacen}&page_size=100`,
  );
  const saldosPostPutaway = saldosPostPutawayResponse.items as Array<{
    warehouse_id: string;
    location_id: string | null;
    product_id: string;
    state: string;
    qty_on_hand: number | string;
    qty_reserved: number | string;
    qty_available: number | string;
  }>;
  const saldoUbicacionB = saldosPostPutaway.find(
    (item) => item.location_id === ubicacionB.id,
  );
  expect(saldoUbicacionB).toBeTruthy();
  expect(saldoUbicacionB!.state).toBe("DISPONIBLE");
  const qtyAvailableAntes = saldosPostPutaway
    .filter((item) => item.state === "DISPONIBLE")
    .reduce((acc, item) => acc + Number(item.qty_available ?? 0), 0);
  expect(qtyAvailableAntes).toBe(10);

  const valoracionPostPutaway = (await getV(
    request,
    c,
    `/inventory/valuation?product_id=${articulo.id}&warehouse_id=${almacen}`,
  )) as { valuation: number | string };
  const valoracionAntesNum = Number(valoracionPostPutaway.valuation ?? 0);

  const costosAntesDespacho = (await (
    await fetch(`${API}/importaciones/${importId}/costs`, { headers: authHeaders(companyId) })
  ).json()) as {
    layers: Array<{
      product_name: string;
      effective_unit_cost: string;
      value: string;
      quantity_remaining: string;
    }>;
  };
  const capaAntesDespacho = costosAntesDespacho.layers.find(
    (item) => item.product_name === `Artículo ${sufijo}`,
  );
  expect(capaAntesDespacho).toBeTruthy();
  const efectivoAntes = Number(capaAntesDespacho!.effective_unit_cost);
  const restanteAntes = Number(capaAntesDespacho!.quantity_remaining);
  expect(restanteAntes).toBe(10);

  // 8. Configuración fiscal, cliente y área de consolidación
  const fiscal = await fiscalListo(request, c, m);

  const cliente = await postV(request, c, "/maestros/terceros", {
    code: `CL-${m}`, name: `Cliente Import ${m}`, roles: ["CLIENTE"],
  });

  const areaConsolidacion = await postV(request, c, "/organization/locations", {
    warehouse_id: almacen, code: `CONS-${m}`, name: "Área de Consolidación", sequence: 99,
  });

  // 9. Pedido de 4 unidades
  const pedido = await postV(request, c, "/sales/orders", {
    code: `OVI-${m}`, customer_id: cliente.id, currency: "VED", warehouse_id: almacen,
  });
  const lineaVenta = await postV(request, c, `/sales/orders/${pedido.id}/lines`, {
    product_id: articulo.id, quantity: 4, unit_price: 25,
  });

  const emitido = await postV(request, c, `/sales/orders/${pedido.id}/submit`, {});
  if (emitido.status !== "RELEASED") {
    await postV(request, c, `/sales/orders/${pedido.id}/release`, {});
  }

  const reserva = await laReservaDe(request, c.headers, articulo.id);
  expect(reserva.source_order_id).toBe(pedido.id);
  expect(reserva.status).toBe("ACTIVE");
  expect(Number(reserva.quantity)).toBe(4);

  // 10. Picking con la ubicación B
  const plan = await postV(request, c, "/sales/pick-lists", {
    code: `PLI-${m}`, order_id: pedido.id, warehouse_id: almacen,
  });
  await postV(request, c, `/sales/picking/${plan.id}/asignaciones`, {
    order_line_id: lineaVenta.id, location_id: ubicacionB.id, quantity: 4,
  });

  await postV(request, c, `/sales/picking/${plan.id}/confirmar`, {});
  const prep = await getV(request, c, `/sales/picking/${plan.id}/preparacion`);
  expect((prep.picking as Array<{ location_id: string; product_id: string }>).every((p) => p.location_id === ubicacionB.id && p.product_id === articulo.id)).toBe(true);
  await postV(request, c, `/sales/picking/${plan.id}/recoger`, {
    line_id: (prep.picking as Array<{ id: string }>)[0].id, quantity: 4,
  });
  await postV(request, c, `/sales/picking/${plan.id}/consolidar`, { location_id: areaConsolidacion.id });

  const v = await verificadorDeEscenario(request, c, { usuario: `imp-${m.toLowerCase()}`, empresas: [c.company] });
  await postV(request, v, `/sales/confirmacion/${pedido.id}`, {
    lines: [{ order_line_id: lineaVenta.id, checked_base_quantity: 4 }],
  });

  // 11. Facturación
  await postV(request, v, `/sales/facturacion/${pedido.id}/solicitar`, {});
  const factura = await postV(request, c, `/sales/facturacion/${pedido.id}/generar`, {});
  const emitida = await postV(request, c, `/sales/facturacion/${factura.id}/emitir`, {
    series_id: fiscal.series, batch_id: fiscal.batch,
  });
  expect(emitida.status).toBe("EMITTED");

  // 12. UI de despacho
  await page.setViewportSize({ width: 1280, height: 844 });
  await page.goto("/ventas/despacho");
  await expect(page.getByRole("heading", { name: "Despacho" })).toBeVisible();
  await expect(page.getByText("Pedidos por despachar")).toBeVisible();
  await expect(page.getByText(pedido.code).first()).toBeVisible();

  // 13. Shipments create/validate/confirm
  const sh = await postV(request, c, "/sales/shipments", {
    code: `DESP-${m}`, order_id: pedido.id,
    destination: "Caracas", transport: "Transportista X",
  });
  expect(sh.lines.length).toBe(1);
  expect(Number(sh.lines[0].base_quantity)).toBe(4);
  expect(sh.origin_warehouse_id).toBe(almacen);

  const validado = await postV(request, c, `/sales/shipments/${sh.id}/validate`, {});
  expect(validado.status).toBe("READY");
  expect(validado.regulatory_status).toBe("CLEARED");
  expect(validado.invoice_id).toBeTruthy();

  const salido = await postV(request, c, `/sales/shipments/${sh.id}/confirm`, {});
  expect(salido.status).toBe("SHIPPED");
  expect(salido.dispatched_at).toBeTruthy();
  expect((await getV(request, c, `/sales/orders/${pedido.id}`)).status).toBe("SHIPPED");

  // 14. Verificación posterior al despacho
  const saldosTrasDespacho = (await getV(
    request,
    c,
    `/inventory/balances?product_id=${articulo.id}&warehouse_id=${almacen}&page_size=100`,
  )).items as Array<{
    location_id: string | null;
    state: string;
    qty_on_hand: number | string;
    qty_available: number | string;
  }>;
  const qtyOnHandPorEstado = (estado: string) =>
    saldosTrasDespacho
      .filter((item) => item.state === estado)
      .reduce((acc, item) => acc + Number(item.qty_on_hand ?? 0), 0);
  expect(qtyOnHandPorEstado("DISPONIBLE")).toBe(qtyAvailableAntes - 4);
  expect(qtyOnHandPorEstado("PREPARADO")).toBe(0);
  expect(qtyOnHandPorEstado("DESPACHADO")).toBe(4);

  const reservasDespues = await reservasDePedido(request, c.headers, pedido.id);
  expect(reservasDespues.filter((r) => r.status === "ACTIVE").length).toBe(0);

  const movimientos = (await getV(
    request,
    c,
    `/inventory/movements?product_id=${articulo.id}&warehouse_id=${almacen}&page_size=100`,
  )).items as Array<{
    id: string;
    warehouse_id: string;
    location_id: string | null;
    product_id: string;
    movement_type_id: string;
    quantity: number | string;
    unit_cost: number | string;
    currency: string;
    document_ref: string | null;
    occurred_at: string;
    status: string;
  }>;
  const movimientoSalida = movimientos.find(
    (mov) =>
      mov.document_ref === `SHIPMENT:${sh.id}` &&
      Math.abs(Number(mov.quantity)) === 4,
  );
  expect(movimientoSalida).toBeTruthy();
  expect(
    movimientos.some(
      (mov) =>
        mov.document_ref === `PICKLIST:${plan.id}` &&
        mov.location_id === ubicacionB.id,
    ),
  ).toBeTruthy();

  const valoracionTrasDespacho = (await getV(
    request,
    c,
    `/inventory/valuation?product_id=${articulo.id}&warehouse_id=${almacen}`,
  )) as { valuation: number | string };
  const valoracionDespuesNum = Number(valoracionTrasDespacho.valuation ?? 0);
  expect(valoracionDespuesNum).toBeCloseTo(valoracionAntesNum - 4 * efectivoAntes, 2);
  expect(valoracionAntesNum - valoracionDespuesNum).toBeCloseTo(24, 2);

  const costosDespuesDespacho = (await (
    await fetch(`${API}/importaciones/${importId}/costs`, { headers: authHeaders(companyId) })
  ).json()) as {
    expenses: Array<{
      concept: string;
      applications: Array<{ id: string; version: number; status: string }>;
    }>;
    layers: Array<{
      product_name: string;
      value: string;
      quantity_remaining: string;
    }>;
  };
  const capaDespuesDespacho = costosDespuesDespacho.layers.find(
    (item) => item.product_name === `Artículo ${sufijo}`,
  );
  expect(capaDespuesDespacho).toBeTruthy();
  expect(Number(capaDespuesDespacho!.quantity_remaining)).toBe(restanteAntes - 4);
  expect(capaDespuesDespacho!.value).toBe("36.00");

  const gastoAplicado = costosDespuesDespacho.expenses.find(
    (item) => item.concept === "Flete capitalizable",
  );
  const aplicacionAplicada = gastoAplicado?.applications.find(
    (item) => item.status === "APPLIED",
  );
  expect(aplicacionAplicada).toBeTruthy();
  const reversionBloqueada = await fetch(
    `${API}/importaciones/${importId}/cost-applications/${aplicacionAplicada!.id}/reverse`,
    {
      method: "POST",
      headers: authHeaders(companyId),
      body: JSON.stringify({ version: aplicacionAplicada!.version, reason: "Reversión tras despacho E2E" }),
    },
  );
  expect(reversionBloqueada.status).toBe(409);
  expect(((await reversionBloqueada.json()) as { code: string }).code).toBe("IMPORT_COST_REVERSAL_BLOCKED");

  await page.goto(expedienteUrl);
  await page.getByRole("link", { name: "Costos", exact: true }).click();
  await expect(page.locator("#costos").getByText("36,00 USD").first()).toBeVisible();

  // 15. N2: segundo pedido de 7 unidades no consigue reserva completa
  const pedido2 = await postV(request, c, "/sales/orders", {
    code: `OVI2-${m}`, customer_id: cliente.id, currency: "VED", warehouse_id: almacen,
  });
  await postV(request, c, `/sales/orders/${pedido2.id}/lines`, {
    product_id: articulo.id, quantity: 7, unit_price: 25,
  });
  const submitPedido2 = await postCrudo(request, c, `/sales/orders/${pedido2.id}/submit`, {});
  expect(submitPedido2.status()).toBe(409);
  expect((await submitPedido2.json()).code).toBe("INSUFFICIENT_AVAILABLE");

  // 16. N3: aislamiento entre empresas
  const hb = { ...c.headers, "X-Kontrol-Company": mundoN6().empresa_b };
  const balancesB = await request.get(
    `${API}/inventory/balances?product_id=${articulo.id}`,
    { headers: hb },
  );
  if (balancesB.ok()) {
    const bodyB = (await balancesB.json()) as { items: Array<unknown> };
    expect(bodyB.items ?? []).toHaveLength(0);
  } else {
    expect([403, 404]).toContain(balancesB.status());
  }

  const pedidoB = await request.post(`${API}/sales/orders`, {
    headers: hb,
    data: { code: `OVB-${m}`, customer_id: cliente.id, currency: "VED", warehouse_id: almacen },
  });
  expect(pedidoB.status()).toBeGreaterThanOrEqual(400);

  // 17. Responsive UI
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/ventas/despacho");
  await expect(page.getByRole("heading", { name: "Despacho" })).toBeVisible();
  await expect
    .poll(() => page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth))
    .toBe(true);

  await page.goto("/compras/importaciones");
  const fila = page
    .getByRole("row")
    .filter({ hasText: `IMP-${sufijo}` })
    .filter({ hasText: `Proveedor Import ${sufijo}` });
  await expect(fila.first()).toBeVisible();
});
