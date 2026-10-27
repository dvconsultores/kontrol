/**
 * El camino real hasta una nota de crédito emitida.
 *
 * No es un atajo: una nota de crédito **solo nace de una factura** (Spec 036),
 * y la factura solo se emite sobre un pedido confirmado y despachado. Cualquier
 * prueba que necesite un crédito a favor del cliente tiene que recorrer esa
 * cadena entera, porque inventar la nota por la puerta de atrás probaría un
 * flujo que en producción no existe.
 *
 * Este módulo no contiene pruebas; Playwright solo recoge `*.spec.ts`.
 */
import { expect, type APIRequestContext } from "@playwright/test";

import { sesionApi } from "./sesion";
import { verificadorDeEscenario } from "./usuario";

const TENANT = process.env.KONTROL_E2E_TENANT ?? "DEMO";
const USER = process.env.KONTROL_E2E_USER ?? "admin";
const API = process.env.KONTROL_E2E_API ?? "http://127.0.0.1:8000/api/v1";

export type Ctx = { token: string; company: string; headers: Record<string, string> };

export async function ctx(request: APIRequestContext): Promise<Ctx> {
  const token = (await sesionApi(USER, { tenant: TENANT })).token;
  const r = await request.get(`${API}/organization/companies`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  const body = await r.json();
  const company = body.items[0].id as string;
  return {
    token,
    company,
    headers: { Authorization: `Bearer ${token}`, "X-Kontrol-Company": company },
  };
}

export async function post(request: APIRequestContext, c: Ctx, ruta: string, data: unknown) {
  const r = await request.post(`${API}${ruta}`, { headers: c.headers, data });
  expect([200, 201], `${ruta}: ${r.status()} ${await r.text()}`).toContain(r.status());
  return r.json();
}

export async function postCrudo(request: APIRequestContext, c: Ctx, ruta: string, data: unknown) {
  return request.post(`${API}${ruta}`, { headers: c.headers, data });
}

export async function get(request: APIRequestContext, c: Ctx, ruta: string) {
  const r = await request.get(`${API}${ruta}`, { headers: c.headers });
  expect(r.ok(), `${ruta}: ${r.status()}`).toBeTruthy();
  return r.json();
}

export const marca = (): string =>
  `${Date.now().toString(36)}${Math.random().toString(36).slice(2, 6)}`.toUpperCase();

/**
 * El día de negocio, que es el de Caracas (Spec 001 · POLICY-CLOCK-LOCAL).
 *
 * `toISOString()` daba el día en UTC: entre las 20:00 y las 24:00 de Caracas ya
 * estaba en mañana, y el backend —que resuelve por día de negocio— no encontraba
 * lo que el propio E2E acababa de sembrar.
 */
export const hoy = (): string =>
  new Intl.DateTimeFormat("en-CA", {
    timeZone: "America/Caracas",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).format(new Date());

/** Un verificador distinto del preparador: `R-D0-12-5` lo exige por defecto. */
async function verificador(request: APIRequestContext, c: Ctx, m: string): Promise<Ctx> {
  return verificadorDeEscenario(request, c, {
    usuario: `tz-${m.toLowerCase()}`,
    empresas: [c.company],
  });
}

async function fiscalListo(request: APIRequestContext, c: Ctx, m: string) {
  // Los catálogos fiscales valen en todas las empresas: los prepara el administrador de QA de todo el tenant (ADR-017, C4).
  const admin = await sesionApi("admintenant", { tenant: TENANT });
  const tenantCtx: Ctx = { ...c, token: admin.token, headers: { ...c.headers, Authorization: `Bearer ${admin.token}` } };
  const fuente = await post(request, tenantCtx, "/fiscal/legal-sources", {
    authority: "SENIAT", source_type: "LEY", number: `LT-${m}`, effective_from: "2020-01-01",
  });
  await post(request, tenantCtx, `/fiscal/legal-sources/${fuente.id}/activate`, {});
  const series: Record<string, string> = {};
  for (const [tipo, prefijo] of [["INVOICE", "F"], ["CREDIT_NOTE", "NC"]]) {
    const s = await post(request, c, "/fiscal/number-series", {
      document_type: tipo, prefix: prefijo,
    });
    series[tipo] = s.id as string;
  }
  const desde = 100000 + Math.floor(Math.random() * 800000);
  const lote = await post(request, c, "/fiscal/control-batches", {
    range_from: String(desde), range_to: String(desde + 99),
  });
  return { series, batch: lote.id as string };
}

export type CreditoListo = {
  cliente: string;
  nota: { id: string; amount: string; currency: string; customer_id: string };
};

/**
 * Un cliente con una nota de crédito emitida a su favor.
 *
 * La cantidad que se devuelve se factura y se despacha primero; la nota se
 * emite sobre esa factura. Al emitirse, la 036 la imputa sola al documento por
 * cobrar, así que para dejar **crédito libre** se factura de más y se acredita
 * solo una parte… pero eso lo consume la factura. Para tener saldo a favor de
 * verdad se emite la nota por el total y se cobra la factura antes: ahí el
 * crédito queda sin documento contra el que imputarse.
 */
export async function creditoAFavor(
  request: APIRequestContext,
  c: Ctx,
  m: string,
  { cantidad = 4, precio = 25 } = {},
): Promise<CreditoListo> {
  const f = await fiscalListo(request, c, m);

  const almacen = (await post(request, c, "/organization/warehouses", {
    company_id: c.company, code: `WT-${m}`, name: `Almacén tesorería ${m}`,
    warehouse_type: "PHYSICAL", status: "ACTIVE",
  })).id as string;
  const producto = await post(request, c, "/maestros/catalogos/items", {
    code: `PT-${m}`, name: `Artículo ${m}`, item_type: "PRODUCT", status: "ACTIVE",
  });
  const l1 = await post(request, c, "/organization/locations", {
    warehouse_id: almacen, code: `T1-${m}`, name: "Origen", sequence: 1,
  });
  const area = await post(request, c, "/organization/locations", {
    warehouse_id: almacen, code: `TC-${m}`, name: "Área de Confirmación", sequence: 99,
  });

  // Buscar y, si falta, crear. En una base recién instalada varias pruebas
  // llegan a la vez, todas ven que el tipo no existe y solo la primera consigue
  // crearlo: las demás reciben un 409 legítimo del índice único. Ese 409 no es
  // un fallo del escenario sino la señal de que otra prueba ya lo creó, así que
  // se vuelve a leer. Cualquier otro error sí rompe la prueba.
  const buscarEntrada = async () => {
    const tipos = await get(request, c, "/inventory/movement-types");
    return (tipos.items ?? tipos).find(
      (x: { code: string }) => x.code === "ENTRADA_RECEPCION",
    ) as { id: string } | undefined;
  };
  let entrada = await buscarEntrada();
  if (!entrada) {
    const creado = await request.post(`${API}/inventory/movement-types`, {
      headers: c.headers,
      data: { code: "ENTRADA_RECEPCION", name: "Entrada por recepción", direction: "IN" },
    });
    if (creado.ok()) {
      entrada = (await creado.json()) as { id: string };
    } else {
      expect((await creado.json()).code, `movement-types: ${creado.status()}`)
        .toBe("MOVEMENT_TYPE_DUPLICATE");
      entrada = await buscarEntrada();
    }
  }
  if (!entrada) throw new Error("No existe el tipo de movimiento ENTRADA_RECEPCION");
  await post(request, c, "/inventory/movements", {
    warehouse_id: almacen, product_id: producto.id, movement_type_id: entrada.id,
    quantity: cantidad + 20,
  });
  await post(request, c, "/inventory/putaway", {
    warehouse_id: almacen, product_id: producto.id, target_location_id: l1.id,
    quantity: cantidad + 20,
  });

  const cliente = await post(request, c, "/maestros/terceros", {
    code: `CT-${m}`, name: `Cliente tesorería ${m}`, roles: ["CLIENTE"],
  });
  const pedido = await post(request, c, "/sales/orders", {
    code: `OVT-${m}`, customer_id: cliente.id, currency: "VED", warehouse_id: almacen,
  });
  const linea = await post(request, c, `/sales/orders/${pedido.id}/lines`, {
    product_id: producto.id, quantity: cantidad, unit_price: precio,
  });
  const emitido = await post(request, c, `/sales/orders/${pedido.id}/submit`, {});
  if (emitido.status !== "RELEASED") {
    await post(request, c, `/sales/orders/${pedido.id}/release`, {});
  }

  const plan = await post(request, c, "/sales/pick-lists", {
    code: `PLT-${m}`, order_id: pedido.id, warehouse_id: almacen,
  });
  await post(request, c, `/sales/picking/${plan.id}/asignaciones`, {
    order_line_id: linea.id, location_id: l1.id, quantity: cantidad,
  });
  await post(request, c, `/sales/picking/${plan.id}/confirmar`, {});
  const prep = await get(request, c, `/sales/picking/${plan.id}/preparacion`);
  await post(request, c, `/sales/picking/${plan.id}/recoger`, {
    line_id: (prep.picking as Array<{ id: string }>)[0].id, quantity: cantidad,
  });
  await post(request, c, `/sales/picking/${plan.id}/consolidar`, { location_id: area.id });

  const v = await verificador(request, c, m);
  await post(request, v, `/sales/confirmacion/${pedido.id}`, {
    lines: [{ order_line_id: linea.id, checked_base_quantity: cantidad }],
  });

  await post(request, v, `/sales/facturacion/${pedido.id}/solicitar`, {});
  const factura = await post(request, c, `/sales/facturacion/${pedido.id}/generar`, {});
  const emitida = await post(request, c, `/sales/facturacion/${factura.id}/emitir`, {
    series_id: f.series.INVOICE, batch_id: f.batch,
  });
  expect(emitida.status).toBe("EMITTED");

  const sh = await post(request, c, "/sales/shipments", {
    code: `DT-${m}`, order_id: pedido.id, destination: "Caracas", transport: "Transportista",
  });
  await post(request, c, `/sales/shipments/${sh.id}/validate`, {});
  await post(request, c, `/sales/shipments/${sh.id}/confirm`, {});

  // Se cobra la factura entera: así el documento queda cerrado y la nota que
  // viene después no tiene contra qué imputarse. Eso es tener saldo a favor.
  const docs = await get(request, c, "/sales/open-items");
  const doc = (docs.items as Array<{ id: string; source_document: string; balance: string }>)
    .find((x) => x.source_document === `SALES_INVOICE:${factura.id}`);
  expect(doc, "la factura emitida no abrió su cuenta por cobrar").toBeTruthy();
  const cobro = await post(request, c, "/sales/collections", {
    party_id: cliente.id, amount: Number(doc!.balance), currency: "VED",
  });
  await post(request, c, "/sales/applications", {
    source_type: "PAYMENT", source_id: cobro.id, target_open_item_id: doc!.id,
    amount: Number(doc!.balance), currency: "VED",
  });

  const elegible = await get(request, c, `/sales/devoluciones/elegibles/${factura.id}`);
  const nota = await post(request, c, `/sales/notas/credito/${factura.id}/generar`, {
    cause: "Devolución de mercancía",
    lines: [{ invoice_line_id: elegible.lines[0].invoice_line_id, quantity: cantidad }],
  });
  const emitidaNota = await post(request, c, `/sales/notas/credito/${nota.id}/emitir`, {
    series_id: f.series.CREDIT_NOTE, batch_id: f.batch,
  });

  return { cliente: cliente.id as string, nota: emitidaNota };
}
