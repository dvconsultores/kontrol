import { expect, test, entrar, sesionApi } from "./helpers/sesion";

const TENANT = process.env.KONTROL_E2E_TENANT ?? "DEMO";
const USER = process.env.KONTROL_E2E_USER ?? "admin";
const API = process.env.KONTROL_E2E_API ?? "http://127.0.0.1:8000/api/v1";

test.setTimeout(300000);
test("expediente de importación de punta a punta", async ({ page }) => {
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

  const ubicacion = await post<{ id: string; code: string }>("/organization/locations", {
    warehouse_id: almacen,
    code: `OK-${sufijo}`,
    name: "Rack válido",
    sequence: 1,
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
  await page.locator("#ubicacion").getByLabel(/Ubicación de destino/).selectOption(ubicacion.id);
  await page.locator("#ubicacion").getByRole("button", { name: /^Ubicar/ }).click();
  await expect(page.getByText("Recibida y ubicada").first()).toBeVisible();
  await expect(page.locator("#ubicacion").getByText(ubicacion.code)).toBeVisible();
  await expect(page.getByText("Mercancía recibida y ubicada. Queda pendiente el costo de importación.").first()).toBeVisible();

  // 7. Historial
  await expect(page.getByText("Recepción creada desde la importación").first()).toBeVisible();

  const costos = page.locator("#costos");
  await expect(page.getByRole("link", { name: "Costos", exact: true })).toBeVisible();
  await page.getByRole("link", { name: "Costos", exact: true }).click();

  await expect(costos.getByText("Distribución aún no disponible")).toBeVisible();
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

  await expect(page.getByText(/tasa/i).first()).toBeVisible();
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

  await page.getByRole("link", { name: "Ver historial" }).click();
  await expect(page.getByText("Gasto de importación registrado").first()).toBeVisible();
  await expect(page.getByText("Gasto de importación anulado").first()).toBeVisible();

  await page.goto("/compras/importaciones");
  const fila = page
    .getByRole("row")
    .filter({ hasText: `IMP-${sufijo}` })
    .filter({ hasText: `Proveedor Import ${sufijo}` });
  await expect(fila.first()).toBeVisible();
});
