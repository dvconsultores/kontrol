/** Selectores de almacén: ningún almacén accesible queda fuera (ALMACENES-DESPLEGABLES-TRUNCADOS). */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, renderHook, screen, waitFor } from "@testing-library/react";
import type { ComponentType, ReactNode } from "react";
import { MemoryRouter } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";

const { EMPRESA_ACTIVA } = vi.hoisted(() => ({ EMPRESA_ACTIVA: "emp-a" }));

const apiFetch = vi.fn();
vi.mock("@/api/client", async (original) => ({
  ...(await original<typeof import("@/api/client")>()),
  apiFetch: (...args: unknown[]) => apiFetch(...args),
}));
vi.mock("@/app/contexts/CompanyContext", () => ({
  useCompany: () => ({ activeCompany: { id: EMPRESA_ACTIVA, name: "Empresa A" } }),
}));
vi.mock("@/app/contexts/NotificationContext", () => ({
  useNotifications: () => ({ notify: vi.fn() }),
}));
vi.mock("@/app/autoridad/AutoridadContext", () => ({
  useAutoridad: () => ({ estado: "LISTA", tiene: () => true, puede: () => true, motivo: () => null, motivoDeCapacidad: () => null }),
}));

const { AjustesPage } = await import("@/modules/inventario/ajustes/AjustesPage");
const { TransferenciasPage } = await import("@/modules/inventario/transferencias/TransferenciasPage");
const { ConteosPage } = await import("@/modules/inventario/conteos/ConteosPage");
const { ReservasPage } = await import("@/modules/inventario/reservas/ReservasPage");
const { SerialesPage } = await import("@/modules/inventario/seriales/SerialesPage");
const { MovimientosPage } = await import("@/modules/inventario/movimientos/MovimientosPage");
const { OrdenesVentasPage } = await import("@/modules/ventas/ordenes/OrdenesVentasPage");
const { UbicacionesPage } = await import("@/modules/organizacion/ubicaciones/UbicacionesPage");
const { PutAwayPage } = await import("@/modules/inventario/putaway/PutAwayPage");
const { PreparacionPage } = await import("@/modules/ventas/preparacion/PreparacionPage");
const { useAlmacenesDeEmpresa } = await import("@/modules/organizacion/almacenes/useAlmacenesDeEmpresa");
const FUENTES = import.meta.glob("/src/modules/**/*.tsx", { query: "?raw", import: "default", eager: true }) as Record<string, string>;

const PANTALLAS = [
  ["Ajustes", AjustesPage], ["Transferencias", TransferenciasPage], ["Conteos", ConteosPage],
  ["Reservas", ReservasPage], ["Seriales", SerialesPage], ["Movimientos", MovimientosPage],
  ["Órdenes de venta", OrdenesVentasPage], ["Ubicaciones", UbicacionesPage],
  ["Put-away", PutAwayPage], ["Preparación", PreparacionPage],
] as const;

function almacen(n: number) {
  return { id: `w-${n}`, code: `A-${String(n).padStart(3, "0")}`, name: `Almacén ${n}` };
}

function servidor(total: number, fallaEnOffset?: number) {
  const todos = Array.from({ length: total }, (_, i) => almacen(i + 1));
  apiFetch.mockImplementation((path: string) => {
    const url = new URL(path, "http://k");
    if (url.pathname === "/organization/warehouses") {
      const limit = Number(url.searchParams.get("limit") ?? 50);
      const offset = Number(url.searchParams.get("offset") ?? 0);
      const companyId = url.searchParams.get("company_id");
      if (limit > 100) return Promise.reject(new Error("LIMIT_FUERA_DE_CONTRATO"));
      if (offset === fallaEnOffset) return Promise.reject(new Error("PAGINA_CAIDA"));
      if (companyId && companyId !== EMPRESA_ACTIVA) {
        return Promise.resolve({ total: 0, limit, offset, items: [] });
      }
      const items = todos.slice(offset, offset + limit);
      return Promise.resolve({ total, limit, offset, items });
    }
    return Promise.resolve({ items: [], total: 0, page: 1, page_size: 20, limit: 50, offset: 0 });
  });
}

function Envoltura({ children }: { children: ReactNode }) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
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

function llamadasDeAlmacenes(): URL[] {
  return apiFetch.mock.calls
    .map(([path]) => new URL(String(path), "http://k"))
    .filter((url) => url.pathname === "/organization/warehouses");
}

beforeEach(() => {
  apiFetch.mockReset();
});

describe("selectores de almacén", () => {
  it.each(PANTALLAS)("%s alcanza el almacén 51", async (_nombre, Pagina) => {
    servidor(51);
    montar(Pagina as ComponentType);
    expect(await screen.findAllByRole("option", { name: /A-051/ })).not.toHaveLength(0);
  });

  it.each(PANTALLAS)("%s alcanza el último de 120", async (_nombre, Pagina) => {
    servidor(120);
    montar(Pagina as ComponentType);
    expect(await screen.findAllByRole("option", { name: /A-120/ })).not.toHaveLength(0);
  });

  it.each(PANTALLAS)("%s no pide fuera de contrato", async (_nombre, Pagina) => {
    servidor(120);
    montar(Pagina as ComponentType);
    await screen.findAllByRole("option", { name: /A-001/ });
    for (const [path] of apiFetch.mock.calls) {
      const url = new URL(String(path), "http://k");
      if (url.pathname !== "/organization/warehouses") continue;
      const raw = url.searchParams.get("limit");
      const limite = raw === null ? null : Number(raw);
      expect(limite === null || limite <= 100).toBe(true);
    }
  });

  it.each(PANTALLAS)("%s sin almacenes lo dice", async (_nombre, Pagina) => {
    servidor(0);
    montar(Pagina as ComponentType);
    expect(await screen.findByText("Esta empresa no tiene almacenes.")).toBeTruthy();
  });

  it.each(PANTALLAS)("%s con la segunda página caída no pinta una lista parcial", async (_nombre, Pagina) => {
    servidor(120, 100);
    montar(Pagina as ComponentType);
    expect(await screen.findByRole("alert")).toHaveProperty("textContent", "No fue posible cargar todos los almacenes.");
    expect(screen.queryAllByRole("option", { name: /A-001/ })).toHaveLength(0);
  });

  it.each(PANTALLAS)("%s pide siempre en la empresa activa y sin filtrar por estado", async (_nombre, Pagina) => {
    servidor(120);
    montar(Pagina as ComponentType);
    await screen.findAllByRole("option", { name: /A-120/ });
    const llamadas = llamadasDeAlmacenes();
    expect(llamadas.length).toBeGreaterThan(1);
    for (const url of llamadas) {
      expect(url.searchParams.get("company_id")).toBe(EMPRESA_ACTIVA);
      expect(url.searchParams.get("limit")).toBe("100");
      expect(url.searchParams.has("status")).toBe(false);
    }
  });

  it("muestra el estado de carga", async () => {
    apiFetch.mockImplementation(() => new Promise(() => undefined));
    montar(AjustesPage as ComponentType);
    expect(await screen.findByText("Cargando almacenes…")).toBeTruthy();
  });

  it("recorre más de dos páginas hasta la última", async () => {
    servidor(250);
    montar(AjustesPage as ComponentType);
    expect(await screen.findAllByRole("option", { name: /A-250/ })).toHaveLength(1);
    expect(llamadasDeAlmacenes().map((url) => url.searchParams.get("offset"))).toEqual(["0", "100", "200"]);
  });

  it("conserva el orden del servidor y no duplica filas", async () => {
    servidor(120);
    montar(AjustesPage as ComponentType);
    await screen.findAllByRole("option", { name: /A-120/ });
    const codigos = screen.getAllByRole("option", { name: /A-\d{3}/ }).map((opcion) => opcion.textContent?.slice(0, 5));
    expect(codigos).toHaveLength(120);
    expect(new Set(codigos).size).toBe(120);
    expect(codigos).toEqual([...codigos].sort());
  });

  it("una empresa no recibe almacenes de otra", async () => {
    servidor(3);
    const { result } = renderHook(() => useAlmacenesDeEmpresa("emp-b"), { wrapper: Envoltura });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.items).toEqual([]);
    expect(llamadasDeAlmacenes()[0]?.searchParams.get("company_id")).toBe("emp-b");
  });

  it("sin empresa activa no pregunta al servidor", () => {
    servidor(3);
    renderHook(() => useAlmacenesDeEmpresa(null), { wrapper: Envoltura });
    expect(llamadasDeAlmacenes()).toHaveLength(0);
  });

  it("ninguna pantalla pide el listado por su cuenta", () => {
    const directas = Object.entries(FUENTES)
      .filter(([ruta]) => !ruta.endsWith(".test.tsx"))
      .filter(([, fuente]) => fuente.includes("/organization/warehouses?"))
      .map(([ruta]) => ruta.replace("/src/modules/", ""));
    expect(directas).toEqual(["organizacion/almacenes/AlmacenesPage.tsx"]);
  });

  it.each([
    "inventario/ajustes/AjustesPage.tsx", "inventario/transferencias/TransferenciasPage.tsx",
    "inventario/conteos/ConteosPage.tsx", "inventario/reservas/ReservasPage.tsx",
    "inventario/seriales/SerialesPage.tsx", "inventario/movimientos/MovimientosPage.tsx",
    "ventas/ordenes/OrdenesVentasPage.tsx", "organizacion/ubicaciones/UbicacionesPage.tsx",
    "inventario/putaway/PutAwayPage.tsx", "ventas/preparacion/PreparacionPage.tsx",
    "maestros/almacenamiento/AlmacenamientoPage.tsx",
  ])("%s usa la autoridad única", (ruta) => {
    const fuente = FUENTES[`/src/modules/${ruta}`];
    expect(fuente).toContain("useAlmacenesDeEmpresa(");
    expect(fuente).toContain("<AvisoDeAlmacenes");
  });
});
