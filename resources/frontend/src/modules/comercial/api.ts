/** Cliente de los maestros comerciales — Spec 012.
 *
 * La empresa **no viaja en el cuerpo**. La pone la cabecera que el cliente
 * añade a partir de la empresa activa de esta pestaña, y el backend la valida.
 * Enviarla aquí sería devolverle al cliente una decisión que no le toca.
 */
import { apiFetch } from "@/api/client";

export interface PaymentTerm {
  id: string;
  code: string;
  name: string;
  kind: string;
  days: number | null;
  due_offset_from: string;
  status: string;
}

export interface Basico {
  id: string;
  code: string;
  name: string;
  status: string;
}

export interface PriceList extends Basico {
  currency_id: string;
  segment: string | null;
  channel_id: string | null;
  source: string | null;
}

export interface PriceListVersion {
  id: string;
  price_list_id: string;
  version_number: number;
  valid_from: string;
  valid_to: string | null;
  status: string;
}

export interface PriceListItem {
  id: string;
  version_id: string;
  item_id: string | null;
  category_id: string | null;
  presentation_id: string | null;
  uom_id: string | null;
  min_quantity: string | null;
  unit_price: string;
}

interface Lista<T> {
  items: T[];
}

export const comercial = {
  condicionesPago: () => apiFetch<Lista<PaymentTerm>>("/comercial/condiciones-pago"),
  crearCondicionPago: (body: Record<string, unknown>) =>
    apiFetch<PaymentTerm>("/comercial/condiciones-pago", { method: "POST", body }),

  zonas: () => apiFetch<Lista<Basico>>("/comercial/zonas"),
  crearZona: (body: Record<string, unknown>) =>
    apiFetch<Basico>("/comercial/zonas", { method: "POST", body }),

  canales: () => apiFetch<Lista<Basico>>("/comercial/canales"),
  crearCanal: (body: Record<string, unknown>) =>
    apiFetch<Basico>("/comercial/canales", { method: "POST", body }),

  listas: () => apiFetch<Lista<PriceList>>("/comercial/listas-precio"),
  crearLista: (body: Record<string, unknown>) =>
    apiFetch<PriceList>("/comercial/listas-precio", { method: "POST", body }),
  lista: (id: string) =>
    apiFetch<PriceList & { versions: PriceListVersion[] }>(
      `/comercial/listas-precio/${encodeURIComponent(id)}`,
    ),

  crearVersion: (listaId: string, body: Record<string, unknown>) =>
    apiFetch<PriceListVersion>(
      `/comercial/listas-precio/${encodeURIComponent(listaId)}/versiones`,
      { method: "POST", body },
    ),
  transicionarVersion: (listaId: string, versionId: string, target: string) =>
    apiFetch<PriceListVersion>(
      `/comercial/listas-precio/${encodeURIComponent(listaId)}/versiones/${encodeURIComponent(versionId)}/transicion`,
      { method: "POST", body: { target } },
    ),

  items: (listaId: string, versionId: string) =>
    apiFetch<Lista<PriceListItem>>(
      `/comercial/listas-precio/${encodeURIComponent(listaId)}/versiones/${encodeURIComponent(versionId)}/items`,
    ),
  /** El identificador del padre se toma del formulario, fijado al abrirlo. */
  crearItem: (listaId: string, versionId: string, body: Record<string, unknown>) =>
    apiFetch<PriceListItem>(
      `/comercial/listas-precio/${encodeURIComponent(listaId)}/versiones/${encodeURIComponent(versionId)}/items`,
      { method: "POST", body },
    ),

  politicasDescuento: () => apiFetch<Lista<Basico>>("/comercial/politicas-descuento"),
  crearPoliticaDescuento: (body: Record<string, unknown>) =>
    apiFetch<Basico>("/comercial/politicas-descuento", { method: "POST", body }),

  politicasCredito: () => apiFetch<Lista<Basico>>("/comercial/politicas-credito"),
  crearPoliticaCredito: (body: Record<string, unknown>) =>
    apiFetch<Basico>("/comercial/politicas-credito", { method: "POST", body }),

  precedencia: () => apiFetch<{ orden: string[]; configurada: boolean }>("/comercial/precedencia"),
};
