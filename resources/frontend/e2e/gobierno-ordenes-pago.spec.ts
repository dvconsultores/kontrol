import { expect, test } from "./helpers/sesion";
import { API, cerrarNotificaciones, entrarEnGobierno, prepararMundo } from "./helpers/gobierno";
import {
  prepararMundoOrdenes,
  opcionDe,
  type MundoOrdenes,
} from "./helpers/ordenes-pago";

test("Recorrido principal de órdenes de pago de Gobierno (TRE-03)", async ({ page, request }) => {
  test.setTimeout(420_000);

  let m: MundoOrdenes;
  let ordenEmitidaId = "";
  let codigoEmitido = "";

  await test.step("Preparar mundo y ver políticas vacías", async () => {
    m = await prepararMundoOrdenes(request, ["100.00"]);
    await entrarEnGobierno(page, m.mundo.username, m.mundo.codigo, "/gobierno/tesoreria/politicas-orden-pago");
    await expect(page.getByText("Aún no hay políticas de orden de pago", { exact: true })).toBeVisible();
    await expect(page.getByText("El producto no trae ninguna precargada.", { exact: true })).toBeVisible();
  });

  await test.step("Crear política por la UI", async () => {
    await cerrarNotificaciones(page);
    const crearResp = page.waitForResponse(
      (resp) => resp.request().method() === "POST" && new URL(resp.url()).pathname.endsWith("/politicas-orden-pago") && resp.status() === 201,
    );
    await page.getByRole("link", { name: "Nueva política" }).click();
    await page.getByLabel(/^Código/).fill("POL-OP-E2E");
    await page.getByLabel(/^Nombre/).fill("Política E2E de órdenes de pago");
    await page.getByLabel(/^Vigente desde/).fill(`${m.anio}-01-01`);
    await page.getByLabel(/^Tipo de regla/).selectOption({ label: "Política institucional" });
    await page.getByLabel(/^Fundamento/).fill("Fundamento normativo de la política de orden de pago E2E");
    await page.getByRole("button", { name: "Añadir documento" }).click();
    await page.getByLabel(/^Documento 1/).selectOption(m.tipoId);
    await page.getByRole("checkbox", { name: "Obligatorio" }).check();
    await page.getByRole("button", { name: "Guardar", exact: true }).click();
    await crearResp;
    await expect(page.getByRole("heading", { level: 1, name: /Política E2E de órdenes de pago/ })).toBeVisible();
    await expect(page.getByText("Borrador", { exact: true }).first()).toBeVisible();
  });

  await test.step("Activar política", async () => {
    await cerrarNotificaciones(page);
    await page.getByRole("button", { name: "Activar" }).click();
    const dialog = page.getByRole("dialog");
    await expect(dialog.getByRole("heading", { name: "Activar la política" })).toBeVisible();
    await dialog.getByLabel(/^Fundamento de la activación/).fill("Fundamento de activación de la política E2E con más de veinte caracteres");
    const activarResp = page.waitForResponse(
      (resp) => resp.request().method() === "POST" && new URL(resp.url()).pathname.endsWith("/activar") && resp.status() === 200,
    );
    await dialog.getByRole("button", { name: "Activar", exact: true }).click();
    await activarResp;
    await expect(page.getByText("Vigente", { exact: true }).first()).toBeVisible();
    const eventosPolitica = page.getByRole("region", { name: "Historia" }).getByRole("listitem");
    expect(await eventosPolitica.count()).toBeGreaterThanOrEqual(2);
  });

  await test.step("Configurar numeración", async () => {
    await cerrarNotificaciones(page);
    await page.getByRole("link", { name: "Políticas de órdenes de pago" }).click();
    await expect(page.getByText("Numeración de órdenes de pago")).toBeVisible();
    await page.getByLabel(/^Patrón/).fill("OP-{ANIO}-{NUMERO:4}");
    const patronResp = page.waitForResponse(
      (resp) => resp.request().method() === "PUT" && new URL(resp.url()).pathname.endsWith("/ordenes-pago/configuracion") && resp.status() === 200,
    );
    await page.getByRole("button", { name: "Guardar patrón" }).click();
    await patronResp;
    await expect(page.getByText(`Ejemplo: OP-${m.anio}-0001`, { exact: true })).toBeVisible();
  });

  await test.step("Ir a órdenes de pago y crear nueva", async () => {
    await cerrarNotificaciones(page);
    await page.getByRole("link", { name: "Órdenes de pago", exact: true }).click();
    await expect(page.getByText("Aún no hay órdenes de pago en este ejercicio")).toBeVisible();
    await page.getByRole("link", { name: "Nueva orden de pago" }).click();
  });

  await test.step("Validar monto, saldo y total en la nueva orden", async () => {
    const codigo = m.causados[0].codigo;
    const filaCausado = page.getByRole("row").filter({ hasText: codigo });
    await page.getByRole("checkbox", { name: `Seleccionar causado ${codigo}` }).check();
    await expect(page.getByLabel(`Monto a ordenar de ${codigo}`)).toHaveValue("100.00");

    await page.getByLabel(`Monto a ordenar de ${codigo}`).fill("101.00");
    await expect(page.getByText("Supera el pendiente de la línea")).toBeVisible();
    await expect(page.getByRole("button", { name: "Guardar borrador" })).toBeDisabled();

    await page.getByLabel(`Monto a ordenar de ${codigo}`).fill("60.00");
    await expect(filaCausado.getByText("40.00", { exact: true })).toBeVisible();
    await expect(page.getByText("TOTAL DE LA ORDEN:", { exact: false })).toBeVisible();
  });

  await test.step("Guardar borrador sin documento y validar controles", async () => {
    const opcionPolitica = await page.getByLabel("Política", { exact: true }).locator("option", { hasText: "POL-OP-E2E" }).getAttribute("value");
    await page.getByLabel("Política", { exact: true }).selectOption(opcionPolitica ?? "");
    await page.getByLabel(/^Concepto/).fill("Orden de pago E2E sin documento");
    await page.getByLabel(/^Cargo que ordena el pago/).selectOption(m.cargoOrdenarId);
    const guardarResp = page.waitForResponse(
      (resp) => resp.request().method() === "POST" && new URL(resp.url()).pathname.endsWith("/ordenes-pago") && resp.status() === 201,
    );
    await page.getByRole("button", { name: "Guardar borrador" }).click();
    await guardarResp;
    await expect(page.getByRole("heading", { level: 1, name: "Borrador de orden de pago" })).toBeVisible();

    const controles = page.getByRole("region", { name: "Controles" });
    await expect(controles).toContainText(/· Falta ·/);
    await expect(page.getByRole("button", { name: "Emitir orden de pago" })).toBeDisabled();
  });

  await test.step("Verificar que el borrador no consume saldo", async () => {
    const pendiente = await opcionDe(request, m, m.causados[0].id);
    expect(pendiente.monto_ordenado).toBe("0.00");
    expect(pendiente.pendiente_de_ordenar).toBe("100.00");
  });

  await test.step("Editar, adjuntar documento y guardar", async () => {
    await cerrarNotificaciones(page);
    await page.getByRole("link", { name: "Editar" }).click();
    const marcarDocResp = page.waitForResponse(
      (resp) => resp.request().method() === "PUT" && /\/ordenes-pago\/[^/]+$/.test(new URL(resp.url()).pathname) && resp.status() === 200,
    );
    await page.getByLabel(/^Documento .+/).first().check();
    await page.getByRole("button", { name: "Guardar borrador" }).click();
    await marcarDocResp;

    const controles = page.getByRole("region", { name: "Controles" });
    await expect(controles).not.toContainText(/· Falta ·/);
    await expect(page.getByRole("button", { name: "Emitir orden de pago" })).toBeEnabled();
  });

  await test.step("Emitir la orden y validar detalle", async () => {
    await cerrarNotificaciones(page);
    await page.getByRole("button", { name: "Emitir orden de pago" }).click();
    const dialog = page.getByRole("dialog");
    await expect(dialog.getByRole("heading", { name: "Emitir orden de pago" })).toBeVisible();
    const emitirResp = page.waitForResponse(
      (resp) => resp.request().method() === "POST" && new URL(resp.url()).pathname.endsWith("/emitir") && resp.status() === 200,
    );
    await dialog.getByRole("button", { name: "Emitir", exact: true }).click();
    await emitirResp;

    codigoEmitido = `OP-${m.anio}-0001`;
    ordenEmitidaId = page.url().split("/ordenes-pago/")[1];

    await expect(page.getByRole("heading", { level: 1, name: codigoEmitido })).toBeVisible();
    await expect(page.getByText("Siguiente paso: Pago (TRE-04)", { exact: false })).toBeVisible();

    const filaCausado = page.getByRole("row").filter({ hasText: m.causados[0].codigo });
    await expect(filaCausado).toContainText("60.00");

    const filasHistoria = page.getByRole("region", { name: "Historia" }).getByRole("row");
    expect(await filasHistoria.count()).toBeGreaterThanOrEqual(3);
  });

  await test.step("Verificar que la emitida consume saldo", async () => {
    const pendiente = await opcionDe(request, m, m.causados[0].id);
    expect(pendiente.monto_ordenado).toBe("60.00");
    expect(pendiente.pendiente_de_ordenar).toBe("40.00");

    await page.goto(`/gobierno/presupuesto/causados/${m.causados[0].id}`);
    await expect(page.getByText(/Pendiente de orden de pago: 40\.00/)).toBeVisible();
  });

  await test.step("Anular la orden por la UI", async () => {
    await cerrarNotificaciones(page);
    await page.goto(`/gobierno/tesoreria/ordenes-pago/${ordenEmitidaId}`);
    await page.getByRole("button", { name: "Anular" }).click();
    const dialog = page.getByRole("dialog");
    await expect(dialog.getByRole("heading", { name: "Anular la orden de pago" })).toBeVisible();
    await expect(dialog.getByText("El monto vuelve a quedar pendiente de ordenar en los causados.")).toBeVisible();
    await dialog.getByLabel(/^Motivo de la anulación/).fill("Motivo de anulación de la orden E2E válido");
    await dialog.getByLabel(/^Cargo que anula/).selectOption(m.cargoOrdenarId);
    const anularResp = page.waitForResponse(
      (resp) => resp.request().method() === "POST" && new URL(resp.url()).pathname.endsWith("/anular") && resp.status() === 200,
    );
    await dialog.getByRole("button", { name: "Anular", exact: true }).click();
    await anularResp;

    await expect(page.getByText("Anulada", { exact: true }).first()).toBeVisible();
    await expect(page.getByText("Motivo de anulación de la orden E2E válido")).toBeVisible();

    const pendiente = await opcionDe(request, m, m.causados[0].id);
    expect(pendiente.monto_ordenado).toBe("0.00");
    expect(pendiente.pendiente_de_ordenar).toBe("100.00");
  });

  await test.step("Validar lista y CSV", async () => {
    await cerrarNotificaciones(page);
    await page.getByRole("link", { name: "Órdenes de pago", exact: true }).first().click();
    const enlaceOrden = page.getByRole("link", { name: codigoEmitido });
    await expect(enlaceOrden).toBeVisible();
    const filaOrden = page.getByRole("row").filter({ hasText: codigoEmitido });
    await expect(filaOrden).toContainText("Anulada");

    const csvResp = await request.get(`${API}/gobierno/tesoreria/ejercicios/${m.ejercicioId}/ordenes-pago/reporte.csv`, {
      headers: m.mundo.headers,
    });
    expect(csvResp.status()).toBe(200);
    expect(await csvResp.text()).toContain(codigoEmitido);
  });

  await test.step("Validar aislamiento entre entes", async () => {
    const otro = await prepararMundo(request, ["organization:view", "gobierno_ordenes_pago:view"]);
    const detalleResp = await request.get(`${API}/gobierno/tesoreria/ordenes-pago/${ordenEmitidaId}`, {
      headers: otro.headers,
    });
    expect(detalleResp.status()).toBe(404);
  });
});
