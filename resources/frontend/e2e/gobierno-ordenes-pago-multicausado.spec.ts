import { expect, test } from "./helpers/sesion";
import { API, cerrarNotificaciones, entrarEnGobierno } from "./helpers/gobierno";
import {
  prepararMundoOrdenes,
  politicaOrdenPagoVigenteApi,
  opcionDe,
  reglaSodTre03Api,
  borradorApi,
  emitirApi,
  sinViolacionesSerias,
  type MundoOrdenes,
  type CausadoListo,
} from "./helpers/ordenes-pago";

test("Órdenes de pago multicausado, sobreorden, responsive, accesibilidad y SoD (TRE-03)", async ({ page, request }) => {
  test.setTimeout(480_000);

  let m: MundoOrdenes;
  let codigoMulticausado = "";
  let detalleMulticausadoId = "";
  let politicaId = "";
  let emitidaParaDialogoId = "";
  const causados: CausadoListo[] = [];

  await test.step("Preparar mundo con cuatro causados", async () => {
    m = await prepararMundoOrdenes(request, ["100.00", "200.00", "300.00", "100.00"]);
    causados.push(...m.causados);
    politicaId = (await politicaOrdenPagoVigenteApi(request, m, "POL-OP-MC", false)).id;
    await entrarEnGobierno(page, m.mundo.username, m.mundo.codigo, "/gobierno/tesoreria/ordenes-pago");
    await page.getByRole("link", { name: "Nueva orden de pago" }).click();
  });

  await test.step("Preparar orden multicausado por la UI", async () => {
    const [a, b, c] = causados;
    const filaA = page.getByRole("row").filter({ hasText: a.codigo });
    const filaB = page.getByRole("row").filter({ hasText: b.codigo });
    const filaC = page.getByRole("row").filter({ hasText: c.codigo });

    await page.getByRole("checkbox", { name: `Seleccionar causado ${a.codigo}` }).check();
    await page.getByRole("checkbox", { name: `Seleccionar causado ${b.codigo}` }).check();
    await page.getByRole("checkbox", { name: `Seleccionar causado ${c.codigo}` }).check();

    await page.getByLabel(`Monto a ordenar de ${a.codigo}`).fill("40.00");
    await page.getByLabel(`Monto a ordenar de ${b.codigo}`).fill("80.00");
    await page.getByLabel(`Monto a ordenar de ${c.codigo}`).fill("120.00");

    await expect(filaA).toContainText("60.00");
    await expect(filaB).toContainText("120.00");
    await expect(filaC).toContainText("180.00");
    await expect(page.getByText("TOTAL DE LA ORDEN:", { exact: false })).toContainText("240.00");
    await expect(page.getByText("Las obligaciones seleccionadas tienen beneficiarios distintos")).not.toBeVisible();
    await expect(page.getByText("Las obligaciones seleccionadas tienen monedas distintas")).not.toBeVisible();

    const opcionPolitica = await page.getByLabel("Política", { exact: true }).locator("option", { hasText: "POL-OP-MC" }).getAttribute("value");
    await page.getByLabel("Política", { exact: true }).selectOption(opcionPolitica ?? "");
    await page.getByLabel(/^Concepto/).fill("Orden multicausado E2E");
    await page.getByLabel(/^Cargo que ordena el pago/).selectOption(m.cargoOrdenarId);

    await page.getByRole("button", { name: "Guardar borrador" }).click();
    await expect(page.getByRole("heading", { level: 1, name: "Borrador de orden de pago" })).toBeVisible();

    for (const causado of [a, b, c]) {
      const pendiente = await opcionDe(request, m, causado.id);
      expect(pendiente.monto_ordenado).toBe("0.00");
    }

    await cerrarNotificaciones(page);
    await page.getByRole("button", { name: "Emitir orden de pago" }).click();
    const dialog = page.getByRole("dialog");
    const emitirResp = page.waitForResponse(
      (resp) => resp.request().method() === "POST" && new URL(resp.url()).pathname.endsWith("/emitir") && resp.status() === 200,
    );
    await dialog.getByRole("button", { name: "Emitir", exact: true }).click();
    await emitirResp;

    codigoMulticausado = (await page.getByRole("heading", { level: 1 }).textContent()) ?? "";
    detalleMulticausadoId = page.url().split("/ordenes-pago/")[1];
    expect(codigoMulticausado).toMatch(new RegExp(`^${m.anio}-\\d+$`));

    const filaDetalleA = page.getByRole("row").filter({ hasText: a.codigo });
    const filaDetalleB = page.getByRole("row").filter({ hasText: b.codigo });
    const filaDetalleC = page.getByRole("row").filter({ hasText: c.codigo });
    await expect(filaDetalleA).toContainText("40.00");
    await expect(filaDetalleB).toContainText("80.00");
    await expect(filaDetalleC).toContainText("120.00");

    const pa = await opcionDe(request, m, a.id);
    expect(pa.monto_ordenado).toBe("40.00");
    expect(pa.pendiente_de_ordenar).toBe("60.00");
    const pb = await opcionDe(request, m, b.id);
    expect(pb.monto_ordenado).toBe("80.00");
    expect(pb.pendiente_de_ordenar).toBe("120.00");
    const pc = await opcionDe(request, m, c.id);
    expect(pc.monto_ordenado).toBe("120.00");
    expect(pc.pendiente_de_ordenar).toBe("180.00");
  });

  await test.step("Anular la orden multicausado por la UI", async () => {
    await cerrarNotificaciones(page);
    await page.goto(`/gobierno/tesoreria/ordenes-pago/${detalleMulticausadoId}`);
    await page.getByRole("button", { name: "Anular" }).click();
    const dialog = page.getByRole("dialog");
    await dialog.getByLabel(/^Motivo de la anulación/).fill("Motivo de anulación multicausada E2E válido");
    await dialog.getByLabel(/^Cargo que anula/).selectOption(m.cargoOrdenarId);
    const anularResp = page.waitForResponse(
      (resp) => resp.request().method() === "POST" && new URL(resp.url()).pathname.endsWith("/anular") && resp.status() === 200,
    );
    await dialog.getByRole("button", { name: "Anular", exact: true }).click();
    await anularResp;

    const [a, b, c] = causados;
    const pa = await opcionDe(request, m, a.id);
    expect(pa.monto_ordenado).toBe("0.00");
    expect(pa.pendiente_de_ordenar).toBe("100.00");
    const pb = await opcionDe(request, m, b.id);
    expect(pb.monto_ordenado).toBe("0.00");
    expect(pb.pendiente_de_ordenar).toBe("200.00");
    const pc = await opcionDe(request, m, c.id);
    expect(pc.monto_ordenado).toBe("0.00");
    expect(pc.pendiente_de_ordenar).toBe("300.00");
  });

  await test.step("Emitir dos órdenes sobre el mismo causado por API", async () => {
    const d = causados[3];
    const b1 = await borradorApi(request, m, politicaId, [{ cause_id: d.id, monto: "40.00" }], []);
    const emitida1 = await emitirApi(request, m, b1);
    emitidaParaDialogoId = emitida1.id;
    const pd1 = await opcionDe(request, m, d.id);
    expect(pd1.monto_ordenado).toBe("40.00");
    expect(pd1.pendiente_de_ordenar).toBe("60.00");

    const b2 = await borradorApi(request, m, politicaId, [{ cause_id: d.id, monto: "50.00" }], []);
    await emitirApi(request, m, b2);
    const pd2 = await opcionDe(request, m, d.id);
    expect(pd2.monto_ordenado).toBe("90.00");
    expect(pd2.pendiente_de_ordenar).toBe("10.00");

    await cerrarNotificaciones(page);
    await page.goto(`/gobierno/tesoreria/ordenes-pago?ejercicio=${m.ejercicioId}`);
    await expect(page.getByRole("link", { name: emitida1.codigo })).toBeVisible();
  });

  await test.step("Sobreorden rechazada por backend y explicada en la UI", async () => {
    const d = causados[3];
    const b3 = await borradorApi(request, m, politicaId, [{ cause_id: d.id, monto: "10.00" }], []);
    const b4 = await borradorApi(request, m, politicaId, [{ cause_id: d.id, monto: "10.00" }], []);
    const emitida3 = await emitirApi(request, m, b3);
    const opcionesResp = await request.get(`${API}/gobierno/tesoreria/ejercicios/${m.ejercicioId}/ordenes-pago/opciones`, {
      headers: m.mundo.headers,
    });
    expect(opcionesResp.status()).toBe(200);
    const opciones = (await opcionesResp.json()) as { obligaciones: Array<{ id: string }> };
    expect(opciones.obligaciones.some((o) => o.id === d.id)).toBe(false);
    expect(emitida3.codigo).toBeTruthy();

    const sobreordenResp = await request.post(`${API}/gobierno/tesoreria/ordenes-pago/${b4.id}/emitir`, {
      headers: { ...m.mundo.headers, "If-Match": String(b4.version) },
    });
    expect(sobreordenResp.status()).toBe(409);
    const cuerpoSobreorden = await sobreordenResp.json();
    expect(cuerpoSobreorden.code).toBe("GOV_PAYMENT_ORDER_OVER_ORDER");

    await cerrarNotificaciones(page);
    await page.goto(`/gobierno/tesoreria/ordenes-pago/${b4.id}`);
    const controles = page.getByRole("region", { name: "Controles" });
    await expect(controles).toContainText(/Saldo insuficiente/);
    await expect(page.getByRole("button", { name: "Emitir orden de pago" })).toBeDisabled();
  });

  await test.step("Responsive y accesibilidad en vistas principales", async () => {
    const rutas = [
      `/gobierno/tesoreria/ordenes-pago?ejercicio=${m.ejercicioId}`,
      `/gobierno/tesoreria/ordenes-pago/nueva?ejercicio=${m.ejercicioId}`,
      `/gobierno/tesoreria/ordenes-pago/${detalleMulticausadoId}`,
      `/gobierno/tesoreria/politicas-orden-pago`,
    ];

    for (const width of [1280, 390, 320]) {
      await page.setViewportSize({ width, height: 800 });

      for (const ruta of rutas) {
        await page.goto(ruta);
        await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
        await sinViolacionesSerias(page, ruta);
      }

      await page.goto(`/gobierno/tesoreria/ordenes-pago/nueva?ejercicio=${m.ejercicioId}`);
      await page.getByRole("checkbox", { name: `Seleccionar causado ${causados[0].codigo}` }).check();
      await sinViolacionesSerias(page, `nueva con A marcado a ${width}`);

      await page.goto(`/gobierno/tesoreria/politicas-orden-pago/${politicaId}`);
      await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
      await sinViolacionesSerias(page, `política a ${width}`);

      if (width === 320) {
        await page.goto(`/gobierno/tesoreria/ordenes-pago/${emitidaParaDialogoId}`);
        await page.getByRole("button", { name: "Anular" }).click();
        const dialogo = page.getByRole("dialog");
        await expect(dialogo).toBeVisible();
        const caja = await dialogo.boundingBox();
        expect(caja).not.toBeNull();
        expect(caja?.x ?? -1).toBeGreaterThanOrEqual(0);
        expect((caja?.x ?? 0) + (caja?.width ?? 999)).toBeLessThanOrEqual(320);
        await expect(dialogo.getByRole("button", { name: "Anular", exact: true })).toBeVisible();
        await dialogo.getByRole("button", { name: "Cancelar" }).click();
      }
    }
  });

  await test.step("SoD real CTL-01 con regla TRE03_CAUSAR × TRE03_ORDENAR", async () => {
    await reglaSodTre03Api(request, m);

    const b5 = await borradorApi(request, m, politicaId, [{ cause_id: causados[1].id, monto: "10.00" }], []);
    await cerrarNotificaciones(page);
    await page.goto(`/gobierno/tesoreria/ordenes-pago/${b5.id}`);

    const emitirBot = page.getByRole("button", { name: "Emitir orden de pago" });
    await expect(emitirBot).toBeEnabled();
    await emitirBot.click();
    const dialog = page.getByRole("dialog");
    const emitirResp = page.waitForResponse(
      (resp) => resp.request().method() === "POST" && new URL(resp.url()).pathname.endsWith("/emitir") && resp.status() === 409,
    );
    await dialog.getByRole("button", { name: "Emitir", exact: true }).click();
    await emitirResp;

    const controles = page.getByRole("region", { name: "Controles" });
    await expect(controles).toContainText(/Bloqueado/);
    await expect(page.getByRole("heading", { level: 1, name: "Borrador de orden de pago" })).toBeVisible();

    const sodResp = await request.post(`${API}/gobierno/tesoreria/ordenes-pago/${b5.id}/emitir`, {
      headers: { ...m.mundo.headers, "If-Match": String(b5.version) },
    });
    expect(sodResp.status()).toBe(409);
    const cuerpoSod = await sodResp.json();
    expect(cuerpoSod.code).toBe("GOV_SOD_CONFLICT");
  });
});
