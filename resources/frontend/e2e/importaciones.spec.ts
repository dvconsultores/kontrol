import { expect, test, entrar, sesionApi } from "./helpers/sesion";

const TENANT = process.env.KONTROL_E2E_TENANT ?? "DEMO";
const USER = process.env.KONTROL_E2E_USER ?? "admin";
const API = process.env.KONTROL_E2E_API ?? "http://127.0.0.1:8000/api/v1";

test.setTimeout(180000);
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
    currency: "VED",
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
  await page.getByLabel(/^Monto/).fill("100");
  await page.getByRole("button", { name: /^Registrar$/ }).click();
  await expect(page.getByText(/Anticipo 100\.00 VED/).first()).toBeVisible();

  // Designar agente y guardar seguimiento
  await page.getByLabel(/^Agente/).fill(`Agente ${sufijoAgente}`);
  await page.getByRole("option", { name: `Agente ${sufijoAgente}` }).click();
  await page.getByRole("button", { name: "Guardar seguimiento" }).click();
  await expect(page.getByText(`Agente ${sufijoAgente}`).first()).toBeVisible();

  // Hito Salida con fecha 2026-11-01
  await page.getByLabel(/^Hito/).selectOption("DEPARTED");
  await page.getByLabel(/^Fecha/).fill("2026-11-01");
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
  await expect(page.getByText("Importación despachada.")).toBeVisible();
  await expect(page.getByText("Despacho confirmado").first()).toBeVisible();

  await page.goto("/compras/importaciones");
  const fila = page
    .getByRole("row")
    .filter({ hasText: `IMP-${sufijo}` })
    .filter({ hasText: `Proveedor Import ${sufijo}` });
  await expect(fila.first()).toBeVisible();
});
