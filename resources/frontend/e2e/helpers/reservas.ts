/**
 * Encontrar la reserva de un escenario, sin suponer que es la única.
 *
 * `GET /inventory/reservations` devuelve **todas** las reservas de la empresa:
 * así lo especifica el contrato de la 023 —«reservas activas/históricas»— y así
 * se comporta. La base del E2E es compartida a propósito, de modo que ese
 * conjunto crece mientras la suite corre: entre dos mediciones de un mismo
 * ciclo pasó de 330 a 369.
 *
 * Dos suites afirmaban sobre el tamaño de ese conjunto —«había las mismas antes
 * que después»— cuando lo que querían decir era «ubicar no tocó mi reserva».
 * La diferencia no se nota hasta que otra prueba reserva en el hueco entre las
 * dos lecturas, y entonces falla algo que no tiene que ver con lo que se está
 * probando.
 *
 * Aquí está la forma correcta, que además ya existía en `sales-orders.spec.ts`:
 * pedir lo que el servidor sabe filtrar y quedarse con lo propio por un campo
 * que el servidor publica.
 *
 * Sobre `source_order_id`: es un **campo de la respuesta**, no un filtro. El
 * servidor no lo declara como parámetro y, como no lo declara, lo ignora en
 * silencio: pedirlo devuelve la lista entera. Por eso aquí se filtra en el
 * cliente y no se finge una consulta que no existe.
 *
 * Este módulo no contiene pruebas; Playwright solo recoge `*.spec.ts`.
 */
import { expect, type APIRequestContext } from "@playwright/test";

const API = process.env.KONTROL_E2E_API ?? "http://127.0.0.1:8000/api/v1";

export interface Reserva {
  id: string;
  product_id: string;
  warehouse_id: string;
  quantity: string | number;
  status: string;
  source_document: string | null;
  source_type: string | null;
  source_order_id: string | null;
  source_line_id: string | null;
  release_reason: string | null;
}

async function listar(
  request: APIRequestContext,
  headers: Record<string, string>,
  consulta = "",
): Promise<Reserva[]> {
  const r = await request.get(`${API}/inventory/reservations${consulta}`, { headers });
  expect(r.ok(), `reservas${consulta}: ${r.status()}`).toBeTruthy();
  return (await r.json()).items as Reserva[];
}

/**
 * Las reservas de un producto, filtradas **por el servidor**.
 *
 * `product_id` sí es un parámetro declarado. Como cada escenario crea su propio
 * producto, esto deja exactamente sus reservas y ninguna ajena.
 */
export function reservasDeProducto(
  request: APIRequestContext,
  headers: Record<string, string>,
  producto: string,
): Promise<Reserva[]> {
  return listar(request, headers, `?product_id=${producto}`);
}

/** Las reservas de un pedido, filtradas en el cliente por el campo publicado. */
export async function reservasDePedido(
  request: APIRequestContext,
  headers: Record<string, string>,
  pedido: string,
): Promise<Reserva[]> {
  return (await listar(request, headers)).filter((r) => r.source_order_id === pedido);
}

/**
 * La única reserva del escenario para ese producto, o falla diciendo qué vio.
 *
 * Falla en vez de devolver la primera: elegir por posición dentro de un
 * conjunto que no se controla es la misma clase de error que contar el total.
 */
export async function laReservaDe(
  request: APIRequestContext,
  headers: Record<string, string>,
  producto: string,
): Promise<Reserva> {
  const suyas = await reservasDeProducto(request, headers, producto);
  expect(
    suyas.length,
    `se esperaba una sola reserva del producto ${producto} y hay ${suyas.length}: ` +
      JSON.stringify(suyas.map((r) => ({ id: r.id, doc: r.source_document, estado: r.status }))),
  ).toBe(1);
  return suyas[0];
}
