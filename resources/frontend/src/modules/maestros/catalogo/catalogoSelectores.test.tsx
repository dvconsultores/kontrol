/** Selectores de catálogo: todo artículo elegible se alcanza buscando (CATALOGO-SELECTORES-PRIMERA-PAGINA). */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ComponentType } from "react";
import { MemoryRouter } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";

const apiFetch = vi.fn();
vi.mock("@/api/client", async (original) => ({
  ...(await original<typeof import("@/api/client")>()),
  apiFetch: (...args: unknown[]) => apiFetch(...args),
}));
vi.mock("@/app/contexts/CompanyContext", () => ({
  useCompany: () => ({ activeCompany: { id: "emp-a", name: "Empresa A" } }),
}));
vi.mock("@/app/contexts/NotificationContext", () => ({
  useNotifications: () => ({ notify: vi.fn() }),
}));
vi.mock("@/app/autoridad/AutoridadContext", () => ({
  useAutoridad: () => ({ estado: "LISTA", tiene: () => true, puede: () => true, motivo: () => null, motivoDeCapacidad: () => null }),
}));

const { TransferenciasPage } = await import("@/modules/inventario/transferencias/TransferenciasPage");
const { SerialesPage } = await import("@/modules/inventario/seriales/SerialesPage");
const { AjustesPage } = await import("@/modules/inventario/ajustes/AjustesPage");
const { ConteosPage } = await import("@/modules/inventario/conteos/ConteosPage");
const { LotesPage } = await import("@/modules/inventario/lotes/LotesPage");
const { ReservasPage } = await import("@/modules/inventario/reservas/ReservasPage");
const { MovimientosPage } = await import("@/modules/inventario/movimientos/MovimientosPage");
const { FacturasVentasPage } = await import("@/modules/ventas/facturas/FacturasVentasPage");
const { CotizacionesPage } = await import("@/modules/ventas/cotizaciones/CotizacionesPage");
const { OrdenesVentasPage } = await import("@/modules/ventas/ordenes/OrdenesVentasPage");
const { CotizacionesComprasPage } = await import("@/modules/compras/cotizaciones/CotizacionesComprasPage");
const { FacturasProveedorPage } = await import("@/modules/compras/facturas/FacturasProveedorPage");
const { DevolucionesComprasPage } = await import("@/modules/compras/devoluciones/DevolucionesComprasPage");
const { OrdenesComprasPage } = await import("@/modules/compras/ordenes/OrdenesComprasPage");
const FUENTES = import.meta.glob("/src/modules/**/*.tsx", { query: "?raw", import: "default", eager: true }) as Record<string, string>;

const INVENTARIO = [["Transferencias", TransferenciasPage], ["Seriales", SerialesPage], ["Ajustes", AjustesPage], ["Conteos", ConteosPage], ["Lotes", LotesPage], ["Reservas", ReservasPage], ["Movimientos", MovimientosPage]] as const;
const COMERCIALES = [["Facturas de venta", FacturasVentasPage], ["Cotizaciones de venta", CotizacionesPage], ["Órdenes de venta", OrdenesVentasPage], ["Cotizaciones de compra", CotizacionesComprasPage], ["Facturas de proveedor", FacturasProveedorPage], ["Devoluciones de compra", DevolucionesComprasPage], ["Órdenes de compra", OrdenesComprasPage]] as const;
const TODAS = [...INVENTARIO, ...COMERCIALES];

interface Articulo {
  id: string;
  code: string;
  name: string;
  item_type: "PRODUCT" | "SERVICE";
}

const UNIVERSO: Articulo[] = Array.from({ length: 30 }, (_, indice) => {
  const n = indice + 1;
  return {
    id: `id-${n}`,
    code: `P-${String(n).padStart(3, "0")}`,
    name: n <= 25 ? `Artículo ${n}` : `Servicio ${n}`,
    item_type: n <= 25 ? "PRODUCT" : "SERVICE",
  };
});

function paginar(items: Articulo[], page: number, pageSize: number) {
  const inicio = (page - 1) * pageSize;
  return { items: items.slice(inicio, inicio + pageSize), total: items.length, page, page_size: pageSize };
}

function servidor() {
  apiFetch.mockImplementation((path: string) => {
    const url = new URL(path, "http://k");
    const pathname = url.pathname;
    if (pathname === "/maestros/catalogos/items") {
      return Promise.resolve({ items: UNIVERSO.slice(0, 20), total: UNIVERSO.length, page: 1, page_size: 20 });
    }
    if (pathname === "/maestros/catalogos/items/search") {
      const q = (url.searchParams.get("q") ?? "").toLowerCase();
      const itemType = url.searchParams.get("item_type");
      const page = Number(url.searchParams.get("page") ?? "1");
      const pageSize = Number(url.searchParams.get("page_size") ?? "20");
      let filtrados = UNIVERSO;
      if (itemType) {
        filtrados = filtrados.filter((a) => a.item_type === itemType);
      }
      if (q) {
        filtrados = filtrados.filter((a) => a.code.toLowerCase().includes(q) || a.name.toLowerCase().includes(q));
      }
      return Promise.resolve(paginar(filtrados, page, pageSize));
    }
    if (pathname.startsWith("/maestros/catalogos/items/")) {
      const id = pathname.slice("/maestros/catalogos/items/".length);
      const articulo = UNIVERSO.find((a) => a.id === id);
      return Promise.resolve(articulo ?? null);
    }
    if (pathname.startsWith("/maestros/productos/") && pathname.endsWith("/presentaciones")) {
      return Promise.resolve([]);
    }
    return Promise.resolve({ items: [], total: 0, page: 1, page_size: 20, limit: 50, offset: 0 });
  });
}

function montar(Pagina: ComponentType) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <Pagina />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

function rutas(): string[] {
  return apiFetch.mock.calls.map((c) => String(c[0]));
}

beforeEach(() => {
  apiFetch.mockReset();
  servidor();
});

describe("Selectores de catálogo", () => {
  it.each(TODAS)("%s alcanza el artículo 25, fuera de la primera página", async (_n, Pagina) => {
    const user = userEvent.setup();
    montar(Pagina);
    const campo = await screen.findByRole("combobox", { name: /^Producto/ });
    await user.type(campo, "P-025");
    const opcion = await screen.findByRole("option", { name: /P-025/ });
    await user.click(opcion);
    await waitFor(() => expect((campo as HTMLInputElement).value).toBe("P-025 · Artículo 25"));
  });

  it.each(INVENTARIO)("%s solo busca productos", async (_n, Pagina) => {
    const user = userEvent.setup();
    montar(Pagina);
    const campo = await screen.findByRole("combobox", { name: /^Producto/ });
    await user.click(campo);
    await waitFor(() => {
      const busquedas = rutas().filter((r) => r.startsWith("/maestros/catalogos/items/search"));
      expect(busquedas.some((r) => r.includes("item_type=PRODUCT"))).toBe(true);
    });
    const busquedas = rutas().filter((r) => r.startsWith("/maestros/catalogos/items/search"));
    expect(busquedas.some((r) => r.includes("item_type=SERVICE"))).toBe(false);
  });

  it.each(COMERCIALES)("%s admite servicios", async (_n, Pagina) => {
    const user = userEvent.setup();
    montar(Pagina);
    const campo = await screen.findByRole("combobox", { name: /^Producto/ });
    await user.type(campo, "P-027");
    await screen.findByRole("option", { name: /P-027/ });
    const busquedas = rutas().filter((r) => r.startsWith("/maestros/catalogos/items/search"));
    expect(busquedas.some((r) => r.includes("item_type="))).toBe(false);
  });

  it.each(TODAS)("%s no usa la primera página como universo", async (_n, Pagina) => {
    montar(Pagina);
    await screen.findByRole("combobox", { name: /^Producto/ });
    expect(rutas().some((r) => r.startsWith("/maestros/catalogos/items?"))).toBe(false);
  });

  it("ningún módulo vuelve a pedir el catálogo truncado", () => {
    const infractores = Object.entries(FUENTES)
      .filter(([nombre]) => !nombre.endsWith(".test.tsx"))
      .filter(([, contenido]) => contenido.includes("catalogos/items?status=ACTIVE"))
      .map(([nombre]) => nombre);
    expect(infractores).toEqual([]);
  });
});
