/**
 * Organización — el listado de empresas, con su contrato de respuesta declarado.
 *
 * `GET /organization/companies` responde el sobre de listados del contrato
 * (`{items, total, page, page_size}`; `page` desde 1, `page_size` hasta 100),
 * y no un array. Aquí se declara una vez, para que ningún consumidor vuelva a
 * afirmar la forma por su cuenta en `apiFetch<T>`.
 */
import { apiFetch } from "@/api/client";
import type { CompanySummary, PagedResult, WarehouseSummary } from "@/api/types";

export type CompanyPage = PagedResult<CompanySummary>;

/** El tamaño máximo de página que el contrato admite (`page_size ≤ 100`). */
export const TAMANO_MAXIMO_DE_PAGINA = 100;

export interface ConsultaDeEmpresas {
  q?: string;
  page?: number;
  page_size?: number;
}

export function listCompanies(consulta: ConsultaDeEmpresas = {}): Promise<CompanyPage> {
  // La página y su tamaño viajan siempre, con los valores por defecto del
  // contrato: así la ruta es una plantilla plana y la guarda de completitud
  // (G3/G4) puede leer qué endpoint pide este módulo.
  const params = new URLSearchParams();
  if (consulta.q) params.set("q", consulta.q);
  params.set("page", String(consulta.page ?? 1));
  params.set("page_size", String(consulta.page_size ?? 20));
  return apiFetch<CompanyPage>(`/organization/companies?${params.toString()}`);
}

/**
 * Todas las empresas en las que el usuario opera.
 *
 * El selector de contexto no puede quedarse con una página: si al usuario le
 * falta una empresa en la lista, no puede elegirla. Se recorren las páginas
 * que el contrato declara, con el tamaño máximo que admite, hasta reunir
 * `total`. No se inventa un `page_size` fuera de contrato ni un `all=true`.
 */
export async function listAllCompanies(): Promise<CompanySummary[]> {
  const todas: CompanySummary[] = [];
  let page = 1;
  for (;;) {
    const pagina = await listCompanies({ page, page_size: TAMANO_MAXIMO_DE_PAGINA });
    todas.push(...pagina.items);
    if (todas.length >= pagina.total || pagina.items.length === 0) return todas;
    page += 1;
  }
}

/** Página del listado de almacenes: su contrato es `{total, limit, offset, items}` (`limit` de 1 a 100, 50 por defecto). */
export interface WarehousePage {
  items: WarehouseSummary[];
  total: number;
  limit: number;
  offset: number;
}

/**
 * Todos los almacenes de la empresa en la que se opera.
 *
 * Un selector de almacén no puede quedarse con una página: el que falte no se
 * puede elegir. Se recorren las páginas con el tamaño máximo que el contrato
 * admite (`limit` ≤ 100) hasta reunir `total`. No se pide un `limit` fuera de
 * contrato: el servidor lo rechaza con 422.
 */
export async function listAllWarehouses(): Promise<WarehouseSummary[]> {
  const todos: WarehouseSummary[] = [];
  for (let offset = 0; ; offset += TAMANO_MAXIMO_DE_PAGINA) {
    const pagina = await apiFetch<WarehousePage>(
      `/organization/warehouses?limit=${TAMANO_MAXIMO_DE_PAGINA}&offset=${offset}`,
    );
    todos.push(...pagina.items);
    if (todos.length >= pagina.total || pagina.items.length === 0) return todos;
  }
}
