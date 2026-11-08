/** Selectores de terceros: todos los terceros elegibles deben ser alcanzables buscando (TERCEROS-SELECTORES-PRIMERA-PAGINA). */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
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

const { CotizacionesPage } = await import("@/modules/ventas/cotizaciones/CotizacionesPage");
const { OrdenesVentasPage } = await import("@/modules/ventas/ordenes/OrdenesVentasPage");
const { FacturasVentasPage } = await import("@/modules/ventas/facturas/FacturasVentasPage");
const { CuentasPorCobrarPage } = await import("@/modules/ventas/cuentas-por-cobrar/CuentasPorCobrarPage");
const { CotizacionesComprasPage } = await import("@/modules/compras/cotizaciones/CotizacionesComprasPage");
const { OrdenesComprasPage } = await import("@/modules/compras/ordenes/OrdenesComprasPage");
const { FacturasProveedorPage } = await import("@/modules/compras/facturas/FacturasProveedorPage");
const { NotasComprasPage } = await import("@/modules/compras/notas/NotasComprasPage");
const { CuentasPorPagarPage } = await import("@/modules/compras/cuentas-por-pagar/CuentasPorPagarPage");
const { RetencionesPage } = await import("@/modules/fiscal/retenciones/RetencionesPage");
const { VehiculosPage } = await import("@/modules/regulatorio/vehiculos/VehiculosPage");

type Tercero = {
  id: string;
  code: string;
  name: string;
  tax_id: string;
  roles: string[];
  status: string;
};

const TERCEROS: Tercero[] = Array.from({ length: 30 }, (_, index) => {
  const n = index + 1;
  const padded = String(n).padStart(3, "0");
  const roles: string[] = [];
  if (n <= 27) roles.push("CLIENTE", "PROVEEDOR");
  if (n === 28) roles.push("CLIENTE");
  if (n === 29) roles.push("PROVEEDOR");
  if (n === 30) roles.push("CONDUCTOR");
  const status = n === 27 ? "INACTIVE" : "ACTIVE";
  return {
    id: `id-${padded}`,
    code: `T-${padded}`,
    name: `Tercero ${n}`,
    tax_id: `J-000${padded}`,
    roles,
    status,
  };
});

function matchesQ(tercero: Tercero, q: string): boolean {
  const needle = q.toLowerCase();
  return (
    tercero.code.toLowerCase().includes(needle) ||
    tercero.name.toLowerCase().includes(needle) ||
    tercero.tax_id.toLowerCase().includes(needle)
  );
}

beforeEach(() => {
  apiFetch.mockReset();

  apiFetch.mockImplementation(async (path: string, options?: { method?: string; body?: unknown }) => {
    const url = new URL(path, "http://k");

    if (options?.method === "POST") {
      return { id: "nuevo", amount: 0, status: "CALCULADA" };
    }

    if (url.pathname === "/maestros/terceros") {
      const q = (url.searchParams.get("q") ?? "").toLowerCase();
      const role = url.searchParams.get("role");
      const status = url.searchParams.get("status");
      const page = Number(url.searchParams.get("page") ?? "1");
      const pageSize = Number(url.searchParams.get("page_size") ?? "20");

      const filtrados = TERCEROS.filter((tercero) => {
        if (q && !matchesQ(tercero, q)) return false;
        if (role && !tercero.roles.includes(role.toUpperCase())) return false;
        if (status && tercero.status !== status.toUpperCase()) return false;
        return true;
      });

      const start = (page - 1) * pageSize;
      const items = filtrados.slice(start, start + pageSize);
      return { items, total: filtrados.length, page, page_size: pageSize };
    }

    if (url.pathname.startsWith("/maestros/terceros/")) {
      const id = url.pathname.split("/").pop();
      return TERCEROS.find((tercero) => tercero.id === id) ?? null;
    }

    if (url.pathname.endsWith("/presentaciones")) {
      return [];
    }

    return { items: [], total: 0, page: 1, page_size: 20, limit: 50, offset: 0 };
  });
});

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

function llamadasPost(ruta: string): Array<{ pathname: string; body: unknown }> {
  return apiFetch.mock.calls
    .filter(([, options]) => (options as { method?: string } | undefined)?.method === "POST")
    .map(([path, options]) => ({
      pathname: new URL(path as string, "http://k").pathname,
      body: (options as { body?: unknown } | undefined)?.body,
    }))
    .filter((llamada) => llamada.pathname === ruta);
}

function llamadasGetTerceros(): URL[] {
  return apiFetch.mock.calls
    .filter(([, options]) => !(options as { method?: string } | undefined)?.method)
    .map(([path]) => new URL(path as string, "http://k"))
    .filter((url) => url.pathname === "/maestros/terceros");
}

const FILAS: Array<{
  nombre: string;
  Pagina: ComponentType;
  etiqueta: RegExp;
  indice: number;
  rol: string | null;
  activo: boolean;
  boton: RegExp;
  rutaPost: string;
  clave: string;
}> = [
  { nombre: "Cotización de venta", Pagina: CotizacionesPage, etiqueta: /^Cliente/, indice: 0, rol: "CLIENTE", activo: true, boton: /^Crear$/, rutaPost: "/sales/quotes", clave: "customer_id" },
  { nombre: "Orden de venta", Pagina: OrdenesVentasPage, etiqueta: /^Cliente/, indice: 0, rol: "CLIENTE", activo: true, boton: /^Crear$/, rutaPost: "/sales/orders", clave: "customer_id" },
  { nombre: "Factura de venta", Pagina: FacturasVentasPage, etiqueta: /^Cliente/, indice: 0, rol: "CLIENTE", activo: true, boton: /^Crear$/, rutaPost: "/sales/invoices", clave: "customer_id" },
  { nombre: "Cobro", Pagina: CuentasPorCobrarPage, etiqueta: /^Cliente/, indice: 0, rol: "CLIENTE", activo: false, boton: /Registrar cobro/, rutaPost: "/sales/collections", clave: "party_id" },
  { nombre: "Anticipo de cliente", Pagina: CuentasPorCobrarPage, etiqueta: /^Cliente/, indice: 1, rol: "CLIENTE", activo: true, boton: /Registrar anticipo/, rutaPost: "/sales/customer-advances", clave: "party_id" },
  { nombre: "Cotización de compra", Pagina: CotizacionesComprasPage, etiqueta: /^Proveedor/, indice: 0, rol: "PROVEEDOR", activo: true, boton: /^Crear$/, rutaPost: "/purchasing/quotes", clave: "supplier_id" },
  { nombre: "Orden de compra", Pagina: OrdenesComprasPage, etiqueta: /^Proveedor/, indice: 0, rol: "PROVEEDOR", activo: true, boton: /^Crear$/, rutaPost: "/purchasing/orders", clave: "supplier_id" },
  { nombre: "Factura de proveedor", Pagina: FacturasProveedorPage, etiqueta: /^Proveedor/, indice: 0, rol: "PROVEEDOR", activo: true, boton: /^Crear$/, rutaPost: "/purchasing/supplier-invoices", clave: "supplier_id" },
  { nombre: "Nota de crédito de compra", Pagina: NotasComprasPage, etiqueta: /^Proveedor/, indice: 0, rol: "PROVEEDOR", activo: false, boton: /Emitir/, rutaPost: "/purchasing/credit-notes", clave: "supplier_id" },
  { nombre: "Pago", Pagina: CuentasPorPagarPage, etiqueta: /^Proveedor/, indice: 0, rol: "PROVEEDOR", activo: false, boton: /Registrar pago/, rutaPost: "/purchasing/payments", clave: "party_id" },
  { nombre: "Anticipo a proveedor", Pagina: CuentasPorPagarPage, etiqueta: /^Proveedor/, indice: 1, rol: "PROVEEDOR", activo: true, boton: /Registrar anticipo/, rutaPost: "/purchasing/advances", clave: "party_id" },
  { nombre: "Cronograma de pago", Pagina: CuentasPorPagarPage, etiqueta: /^Proveedor/, indice: 2, rol: "PROVEEDOR", activo: false, boton: /Registrar cronograma/, rutaPost: "/purchasing/payment-schedules", clave: "party_id" },
  { nombre: "Retención", Pagina: RetencionesPage, etiqueta: /^Tercero/, indice: 0, rol: "PROVEEDOR", activo: false, boton: /Calcular/, rutaPost: "/fiscal/withholdings/calculate", clave: "party_id" },
  { nombre: "Conductor", Pagina: VehiculosPage, etiqueta: /^Conductor/, indice: 0, rol: null, activo: true, boton: /^Registrar$/, rutaPost: "/regulatory/drivers", clave: "party_id" },
];

describe.each(FILAS)("selector de terceros en $nombre", (fila) => {
  it("alcanza el tercero fuera de la primera página (SP-A)", async () => {
    let objetivo: Tercero;
    if (fila.rol === "CLIENTE") objetivo = TERCEROS[27];
    else if (fila.rol === "PROVEEDOR") objetivo = TERCEROS[28];
    else objetivo = TERCEROS[29];

    const user = userEvent.setup();
    montar(fila.Pagina);

    const campos = await screen.findAllByRole("combobox", { name: fila.etiqueta });
    const campo = campos[fila.indice] as HTMLInputElement;
    await user.clear(campo);
    await user.type(campo, objetivo.code);
    await user.click(await screen.findByRole("option", { name: new RegExp(objetivo.code) }));

    await waitFor(() => {
      expect(campo.value).toBe(`${objetivo.code} · ${objetivo.name}`);
    });
    expect(campo.value).not.toContain(objetivo.id);

    const formulario = campo.closest("form");
    expect(formulario).not.toBeNull();
    const dentro = within(formulario as HTMLElement);
    await user.click(dentro.getByRole("button", { name: fila.boton }));

    await waitFor(() => {
      const posts = llamadasPost(fila.rutaPost);
      expect(posts.length).toBeGreaterThan(0);
      expect((posts[0]?.body as Record<string, unknown>)[fila.clave]).toBe(objetivo.id);
    });
  });

  it("pide el rol y el estado del proceso (SP-B)", async () => {
    const user = userEvent.setup();
    montar(fila.Pagina);

    const campos = await screen.findAllByRole("combobox", { name: fila.etiqueta });
    await user.click(campos[fila.indice] as HTMLElement);

    await waitFor(() => {
      expect(llamadasGetTerceros().length).toBeGreaterThan(0);
    });

    const llamadas = llamadasGetTerceros();
    for (const url of llamadas) {
      expect(url.searchParams.has("page_size")).toBe(true);
      expect(url.searchParams.has("page")).toBe(true);

      if (fila.rol !== null) {
        expect(url.searchParams.get("role")).toBe(fila.rol);
      } else {
        expect(url.searchParams.has("role")).toBe(false);
      }

      if (fila.activo) {
        expect(url.searchParams.get("status")).toBe("ACTIVE");
      } else {
        expect(url.searchParams.has("status")).toBe(false);
      }
    }
  });

  it("no ofrece terceros no elegibles (SP-C)", async () => {
    const texto = fila.rol === "CLIENTE" ? "T-029" : fila.rol === "PROVEEDOR" ? "T-028" : "T-029";

    const user = userEvent.setup();
    montar(fila.Pagina);

    const campos = await screen.findAllByRole("combobox", { name: fila.etiqueta });
    const campo = campos[fila.indice] as HTMLInputElement;
    await user.clear(campo);
    await user.type(campo, texto);

    if (fila.rol === null) {
      await screen.findByRole("option", { name: /T-029/ });
    } else {
      await screen.findByText("Sin resultados");
    }
  });

  it("respeta el estado del tercero (SP-D)", async () => {
    const user = userEvent.setup();
    montar(fila.Pagina);

    const campos = await screen.findAllByRole("combobox", { name: fila.etiqueta });
    const campo = campos[fila.indice] as HTMLInputElement;
    await user.clear(campo);
    await user.type(campo, "T-027");

    if (fila.activo) {
      await screen.findByText("Sin resultados");
    } else {
      await screen.findByRole("option", { name: /T-027/ });
    }
  });
});

describe("fuente de los selectores de terceros", () => {
  it("ningún fichero usa GET /maestros/terceros sin parámetros (SP-E)", async () => {
    const fuentes = import.meta.glob("/src/modules/**/*.tsx", {
      query: "?raw",
      import: "default",
      eager: true,
    }) as Record<string, string>;

    const expresion = /apiFetch(<[^(]*>)?\(\s*["`]\/maestros\/terceros["`]\s*\)/;

    for (const [ruta, contenido] of Object.entries(fuentes)) {
      if (ruta.includes(".test.tsx")) continue;
      expect(expresion.test(contenido)).toBe(false);
    }
  });
});
