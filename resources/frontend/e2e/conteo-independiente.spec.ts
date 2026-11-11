import { type APIRequestContext } from "@playwright/test";
import { entrar, entrarComoUsuario, expect, test } from "./helpers/sesion";
import { ctx, get, marca, post, postCrudo, type Ctx } from "./helpers/ventas";
import { verificadorDeEscenario } from "./helpers/usuario";

const USER = process.env.KONTROL_E2E_USER ?? "admin";
const TENANT = process.env.KONTROL_E2E_TENANT ?? "DEMO";

interface ReceiptSetup {
  receipt: string;
  line: string;
  product: string;
}

async function recepcionAceptada(
  request: APIRequestContext,
  c: Ctx,
  m: string,
): Promise<ReceiptSetup> {
  // Warehouse
  const warehouses = (await get(
    request,
    c,
    `/organization/warehouses?company_id=${c.company}`,
  )) as { items: Array<{ id: string }> };
  let warehouseId = warehouses.items[0]?.id;
  if (!warehouseId) {
    const branch = (await post(request, c, "/organization/branches", {
      company_id: c.company,
      code: `S-${m}`,
      name: "Sucursal E2E",
    })) as { id: string };
    const warehouse = (await post(request, c, "/organization/warehouses", {
      company_id: c.company,
      branch_id: branch.id,
      code: `W-${m}`,
      name: "Almacén E2E",
    })) as { id: string };
    warehouseId = warehouse.id;
  }

  const supplier = (await post(request, c, "/maestros/terceros", {
    code: `PIC-${m}`,
    name: `Proveedor ${m}`,
    roles: ["PROVEEDOR"],
  })) as { id: string };

  const product = (await post(request, c, "/maestros/catalogos/items", {
    code: `AIC-${m}`,
    name: `Artículo ${m}`,
    item_type: "PRODUCT",
  })) as { id: string };

  const order = (await post(request, c, "/purchasing/orders", {
    code: `OIC-${m}`,
    supplier_id: supplier.id,
    currency: "VED",
  })) as { id: string };

  const orderLine = (await post(request, c, `/purchasing/orders/${order.id}/lines`, {
    product_id: product.id,
    quantity_ordered: 100,
    unit_price: 1,
  })) as { id: string };

  await post(request, c, `/purchasing/orders/${order.id}/transition`, {
    target: "SUBMITTED",
  });
  await post(request, c, `/purchasing/orders/${order.id}/transition`, {
    target: "APPROVED",
  });

  const receipt = (await post(request, c, "/purchasing/receipts", {
    code: `RIC-${m}`,
    order_id: order.id,
    warehouse_id: warehouseId,
  })) as { id: string };

  const receiptLine = (await post(request, c, `/purchasing/receipts/${receipt.id}/lines`, {
    order_line_id: orderLine.id,
    product_id: product.id,
    quantity_received: 20,
    quantity_accepted: 20,
    quantity_rejected: 0,
  })) as { id: string };

  await post(request, c, `/purchasing/receipts/${receipt.id}/confirm`, {});
  await post(request, c, `/purchasing/receipts/${receipt.id}/quality`, {});
  await post(request, c, `/purchasing/receipts/${receipt.id}/quality`, {
    quality_status: "APPROVED",
  });
  await post(request, c, `/purchasing/receipts/${receipt.id}/accept`, {});

  return { receipt: receipt.id, line: receiptLine.id, product: product.id };
}

interface PolicyResponse {
  receipt_count_same_user_allowed: boolean;
  independent_count_required: boolean;
}

interface BalanceItem {
  state: string;
  qty_on_hand: string;
}

interface AuditEvent {
  action: string;
  entity_id: string;
  username: string;
}

test.describe("Spec T021-IC — conteo independiente", () => {
  test("quien recibe no cuenta; otra persona cuenta y confirma", async ({ page, request }) => {
    const c = await ctx(request);
    const m = marca();
    const r = await recepcionAceptada(request, c, m);

    const policy = (await get(
      request,
      c,
      "/purchasing/settings/receipt-count",
    )) as PolicyResponse;
    expect(policy.independent_count_required).toBe(true);

    await entrar(page, USER, {
      tenant: TENANT,
      ruta: `/inventario/confirmacion?recepcion=${r.receipt}`,
    });
    await expect(
      page.getByRole("heading", { name: "Confirmación de inventario" }),
    ).toBeVisible();
    await expect(page.getByRole("note")).toContainText("Conteo independiente activo");

    await page.getByLabel(/Contado \(base\)/).fill("20");
    await page.getByRole("button", { name: "Registrar conteo" }).click();
    await expect(
      page
        .getByText(
          "El conteo debe hacerlo una persona distinta de quien registró o aceptó la recepción.",
        )
        .first(),
    ).toBeVisible();
    await expect(page.getByText("Faltan líneas por contar.")).toBeVisible();

    const rawConfirm = await postCrudo(
      request,
      c,
      `/purchasing/receipts/${r.receipt}/confirmacion-inventario`,
      {
        decisions: [
          {
            receipt_line_id: r.line,
            target_state: "DISPONIBLE",
            base_quantity: "20",
          },
        ],
      },
    );
    expect(rawConfirm.status()).toBe(409);
    const confirmJson = (await rawConfirm.json()) as { code: string };
    expect(confirmJson.code).toBe("COUNT_REQUIRED_BEFORE_CONFIRMATION");

    const balancesBefore = (await get(
      request,
      c,
      `/inventory/balances?product_id=${r.product}`,
    )) as { items: BalanceItem[] };
    expect(balancesBefore.items.map((b) => [b.state, Number(b.qty_on_hand)])).toEqual([
      ["RECIBIDO", 20],
    ]);

    const usuario = `ic-${m.toLowerCase()}`;
    const v: Ctx = await verificadorDeEscenario(request, c, {
      usuario,
      empresas: [c.company],
    });

    await entrarComoUsuario(page, usuario, {
      tenant: TENANT,
      ruta: `/inventario/confirmacion?recepcion=${r.receipt}`,
    });
    await expect(
      page.getByRole("heading", { name: "Confirmación de inventario" }),
    ).toBeVisible();

    await page.getByLabel(/Contado \(base\)/).fill("20");
    await page.getByRole("button", { name: "Registrar conteo" }).click();
    await expect(page.getByText("Faltan líneas por contar.")).toBeHidden({
      timeout: 15_000,
    });

    await page.getByLabel(/Cantidad a confirmar/).fill("20");
    await page.getByRole("button", { name: "Confirmar inventario" }).click();
    await expect(
      page.getByRole("heading", { name: "Decisiones tomadas" }),
    ).toBeVisible({ timeout: 15_000 });

    const balancesAfter = (await get(
      request,
      v,
      `/inventory/balances?product_id=${r.product}`,
    )) as { items: BalanceItem[] };
    const disponibleItem = balancesAfter.items.find((b) => b.state === "DISPONIBLE");
    expect(disponibleItem).toBeDefined();
    expect(Number(disponibleItem?.qty_on_hand)).toBe(20);

    const countedAudit = (await get(
      request,
      c,
      `/audit/events?entity_id=${r.line}&action=RECEIPT_LINE_COUNTED&page_size=20`,
    )) as { items: AuditEvent[] };
    expect(countedAudit.items[0]?.username).toBe(usuario);

    const confirmedAudit = (await get(
      request,
      c,
      `/audit/events?entity_id=${r.receipt}&action=RECEIPT_INVENTORY_CONFIRMED&page_size=20`,
    )) as { items: AuditEvent[] };
    expect(confirmedAudit.items[0]?.username).toBe(usuario);

    for (const width of [390, 320]) {
      await page.setViewportSize({ width, height: 800 });
      await page.reload();
      await expect(
        page.getByRole("heading", { name: "Confirmación de inventario" }),
      ).toBeVisible();
      await expect
        .poll(() =>
          page.evaluate(
            () => document.documentElement.scrollWidth <= document.documentElement.clientWidth,
          ),
        )
        .toBe(true);
    }
  });
});
