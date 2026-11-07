/** Recepciones como proceso: orden completa, hechos declarados y almacén activo (FR-019-019 a FR-019-024). */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";

const { empresa, notify } = vi.hoisted(() => ({ empresa: { id: "emp-a" }, notify: vi.fn() }));

const apiFetch = vi.fn();
vi.mock("@/api/client", async (original) => ({
  ...(await original<typeof import("@/api/client")>()),
  apiFetch: (...args: unknown[]) => apiFetch(...args),
}));
vi.mock("@/app/contexts/CompanyContext", () => ({
  useCompany: () => ({ activeCompany: { id: empresa.id, name: "Empresa" } }),
}));
vi.mock("@/app/contexts/NotificationContext", () => ({ useNotifications: () => ({ notify }) }));
vi.mock("@/app/autoridad/AutoridadContext", () => ({
  useAutoridad: () => ({
    estado: "LISTA",
    tiene: () => true,
    puede: () => true,
    motivo: () => null,
    motivoDeCapacidad: () => null,
  }),
}));

const { RecepcionesPage } = await import("./RecepcionesPage");

interface Opciones {
  method?: string;
  body?: unknown;
}

interface Orden {
  id: string;
  code: string;
  status: string;
  lines: unknown[];
}

interface Almacen {
  id: string;
  code: string;
  name: string;
  status: string;
}

type Recepcion = Record<string, unknown>;

interface Ajustes {
  ordenes?: Orden[];
  totalOrdenes?: number;
  fallaOrdenes?: boolean;
  fallaPagina?: number;
  ordenesPendientes?: boolean;
  almacenes?: Almacen[];
  recepcion?: Recepcion;
}

type FetchArgs = [string, Opciones?];

function servidor(ajustes: Ajustes = {}) {
  return (path: string, opciones: Opciones = {}): Promise<unknown> => {
    const url = new URL(path, "http://k");
    const p = url.pathname;
    const page = Number(url.searchParams.get("page") ?? "1");
    if (p === "/purchasing/orders") {
      if (ajustes.fallaOrdenes) {
        return Promise.reject(new Error("fallo"));
      }
      if (ajustes.fallaPagina === page) {
        return Promise.reject(new Error("fallo pagina"));
      }
      if (ajustes.ordenesPendientes) {
        return new Promise(() => undefined);
      }
      const base: Orden[] = ajustes.ordenes ?? [
        { id: "o1", code: "OC-1", status: "APPROVED", lines: [] },
      ];
      const lista = empresa.id !== "emp-a"
        ? [{ id: "o-b", code: "OC-B", status: "APPROVED", lines: [] }]
        : base;
      const q = url.searchParams.get("q");
      const filtrada = q === null ? lista : lista.filter((o) => o.code.includes(q));
      const total = ajustes.totalOrdenes ?? filtrada.length;
      const pageSize = Number(url.searchParams.get("page_size") ?? "50");
      const items = filtrada.slice((page - 1) * pageSize, page * pageSize);
      return Promise.resolve({ items, total, page, page_size: pageSize });
    }
    if (p === "/purchasing/orders/o1") {
      return Promise.resolve({
        id: "o1",
        code: "OC-1",
        status: "APPROVED",
        lines: [
          {
            id: "l1",
            product_id: "p1",
            quantity_ordered: 10,
            quantity_received: 0,
            unit_price: 5,
            needs_inventory: true,
          },
        ],
      });
    }
    if (p === "/organization/warehouses") {
      const offset = Number(url.searchParams.get("offset") ?? "0");
      const items: Almacen[] = offset > 0
        ? []
        : ajustes.almacenes ?? [
            { id: "w1", code: "A-1", name: "Central", status: "ACTIVE" },
            { id: "w2", code: "A-2", name: "Cerrado", status: "INACTIVE" },
          ];
      return Promise.resolve({ total: items.length, limit: 100, offset, items });
    }
    if (p === "/purchasing/receipts" && (opciones.method ?? "GET") === "GET") {
      return Promise.resolve({
        items: [
          {
            id: "r1",
            code: "REC-1",
            order_id: "00000000-aaaa",
            order_code: "OC-1",
            warehouse_id: "w1",
            status: "DRAFT",
            quality_status: "PENDING",
            ...ajustes.recepcion,
          },
        ],
      });
    }
    if (p === "/purchasing/receipts/r1") {
      return Promise.resolve({
        id: "r1",
        code: "REC-1",
        order_id: "o1",
        order_code: "OC-1",
        warehouse_id: "w1",
        status: "DRAFT",
        quality_status: "PENDING",
        ...ajustes.recepcion,
        lines: [],
      });
    }
    if (p === "/maestros/catalogos/items/p1") {
      return Promise.resolve({ id: "p1", code: "P-001", name: "Arroz" });
    }
    if (opciones.method === "POST") {
      if (p === "/purchasing/receipts") {
        return Promise.resolve({ id: "r9" });
      }
      return Promise.resolve({ id: "r1", status: "DRAFT" });
    }
    return Promise.resolve({ items: [], total: 0, page: 1, page_size: 20 });
  };
}

function montar() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  function arbol() {
    return (
      <QueryClientProvider client={client}>
        <MemoryRouter>
          <RecepcionesPage />
        </MemoryRouter>
      </QueryClientProvider>
    );
  }
  const { rerender } = render(arbol());
  const repintar = () => rerender(arbol());
  return { repintar };
}

async function abrir(): Promise<void> {
  const celda = await screen.findByText("REC-1");
  const fila = celda.closest("tr");
  if (fila === null) {
    throw new Error("sin fila");
  }
  fireEvent.click(within(fila).getByRole("button", { name: "detalle" }));
  await screen.findByRole("heading", { name: "Inspección de REC-1" });
}

function posts(sufijo: string): FetchArgs[] {
  return apiFetch.mock.calls.filter((llamada: unknown) => {
    const [path, opciones] = llamada as FetchArgs;
    return opciones?.method === "POST" && path.endsWith(sufijo);
  }) as FetchArgs[];
}

function rutaDe(llamada: FetchArgs): string {
  return llamada[0];
}

function esperaOpcion(nombre: string | RegExp): Promise<HTMLElement> {
  return screen.findByRole("option", { name: nombre }) as Promise<HTMLElement>;
}

describe("Recepciones · proceso", () => {
  beforeEach(() => {
    apiFetch.mockReset();
    notify.mockReset();
    empresa.id = "emp-a";
  });

  it("O-01 O-02 una orden fuera de la primera página se alcanza cargando más", async () => {
    const ordenes: Orden[] = Array.from({ length: 60 }, (_, i) => ({
      id: `o${i + 1}`,
      code: `OC-${i + 1}`,
      status: "APPROVED",
      lines: [],
    }));
    apiFetch.mockImplementation(servidor({ ordenes }));
    montar();
    await screen.findByText("Mostrando 50 de 60 órdenes.");
    expect(screen.queryByRole("option", { name: "OC-55" })).toBeNull();
    fireEvent.click(screen.getByRole("button", { name: "Cargar más órdenes" }));
    await esperaOpcion("OC-55");
    await waitFor(() => expect(screen.queryByText("Mostrando 50 de 60 órdenes.")).toBeNull());
  });

  it("O-02b una orden se alcanza por búsqueda", async () => {
    const ordenes: Orden[] = Array.from({ length: 60 }, (_, i) => ({
      id: `o${i + 1}`,
      code: `OC-${i + 1}`,
      status: "APPROVED",
      lines: [],
    }));
    apiFetch.mockImplementation(servidor({ ordenes }));
    montar();
    const buscar = screen.getByLabelText(/^Buscar orden/);
    fireEvent.change(buscar, { target: { value: "OC-55" } });
    await esperaOpcion("OC-55");
    const rutas = (apiFetch.mock.calls as FetchArgs[]).map(rutaDe);
    expect(rutas.some((r) => r.includes("q=OC-55"))).toBe(true);
  });

  it("O-03 O-05 cambiar de empresa descarta la orden", async () => {
    apiFetch.mockImplementation(servidor());
    const { repintar } = montar();
    await esperaOpcion("OC-1");
    const select = screen.getByRole("combobox", { name: /^Orden de compra/ });
    fireEvent.change(select, { target: { value: "o1" } });
    empresa.id = "emp-b";
    repintar();
    await esperaOpcion("OC-B");
    await waitFor(() => expect((select as HTMLSelectElement).value).toBe(""));
    expect(screen.queryByRole("option", { name: "OC-1" })).toBeNull();
  });

  it("O-04 pide solo órdenes recibibles", async () => {
    apiFetch.mockImplementation(servidor());
    montar();
    await esperaOpcion("OC-1");
    const primera = (apiFetch.mock.calls as FetchArgs[])
      .map(rutaDe)
      .find((r) => r.includes("/purchasing/orders"));
    expect(primera).toBeDefined();
    expect(primera as string).toContain("receivable=true");
    expect(primera as string).toContain("page=1");
    expect(primera as string).toContain("page_size=50");
  });

  it("O-06 un fallo al cargar más no pasa por lista completa", async () => {
    const ordenes: Orden[] = Array.from({ length: 60 }, (_, i) => ({
      id: `o${i + 1}`,
      code: `OC-${i + 1}`,
      status: "APPROVED",
      lines: [],
    }));
    apiFetch.mockImplementation(servidor({ ordenes, fallaPagina: 2 }));
    montar();
    await screen.findByText("Mostrando 50 de 60 órdenes.");
    fireEvent.click(screen.getByRole("button", { name: "Cargar más órdenes" }));
    const alerta = await screen.findByText("No fue posible cargar más órdenes.");
    expect(alerta.getAttribute("role")).toBe("alert");
    expect(screen.getByRole("option", { name: "OC-1" })).toBeTruthy();
  });

  it("O-02c ninguna página queda fuera por un tope", async () => {
    apiFetch.mockImplementation(
      servidor({
        ordenes: Array.from({ length: 120 }, (_, i) => ({
          id: `o${i + 1}`,
          code: `OC-${i + 1}`,
          status: "APPROVED",
          lines: [],
        })),
      }),
    );
    montar();
    await screen.findByText("Mostrando 50 de 120 órdenes.");
    fireEvent.click(screen.getByRole("button", { name: "Cargar más órdenes" }));
    await screen.findByText("Mostrando 100 de 120 órdenes.");
    fireEvent.click(screen.getByRole("button", { name: "Cargar más órdenes" }));
    await esperaOpcion("OC-120");
  });

  it("O-05b una orden de la empresa anterior no se envía", async () => {
    apiFetch.mockImplementation(servidor());
    const { repintar } = montar();
    await esperaOpcion("OC-1");
    fireEvent.change(screen.getByRole("combobox", { name: /^Orden de compra/ }), {
      target: { value: "o1" },
    });
    empresa.id = "emp-b";
    repintar();
    await esperaOpcion("OC-B");
    await esperaOpcion(/A-1/);
    fireEvent.change(screen.getByRole("combobox", { name: /^Almacén/ }), {
      target: { value: "w1" },
    });
    fireEvent.change(screen.getByLabelText(/^Código/), { target: { value: "R" } });
    fireEvent.click(screen.getByRole("button", { name: "Crear" }));
    await waitFor(() =>
      expect(notify).toHaveBeenCalledWith({
        type: "error",
        title: "No fue posible crear la recepción",
        description: "Seleccione una orden de compra.",
      }),
    );
    expect(posts("/purchasing/receipts")).toHaveLength(0);
  });

  it("crear recarga las órdenes recibibles", async () => {
    apiFetch.mockImplementation(servidor());
    montar();
    await esperaOpcion("OC-1");
    fireEvent.change(screen.getByRole("combobox", { name: /^Orden de compra/ }), {
      target: { value: "o1" },
    });
    await esperaOpcion(/A-1/);
    fireEvent.change(screen.getByRole("combobox", { name: /^Almacén/ }), {
      target: { value: "w1" },
    });
    fireEvent.change(screen.getByLabelText(/^Código/), { target: { value: "R" } });
    fireEvent.click(screen.getByRole("button", { name: "Crear" }));
    await waitFor(() => {
      const llamadas = apiFetch.mock.calls
        .map((llamada) => rutaDe(llamada as FetchArgs))
        .filter((ruta) => ruta.startsWith("/purchasing/orders?"));
      expect(llamadas.length).toBeGreaterThanOrEqual(2);
    });
  });

  it("registrar limpia las observaciones declaradas", async () => {
    apiFetch.mockImplementation(servidor());
    montar();
    await abrir();
    await esperaOpcion(/Arroz/);
    fireEvent.change(screen.getByRole("combobox", { name: /^Línea de la orden/ }), {
      target: { value: "l1" },
    });
    fireEvent.change(screen.getByRole("combobox", { name: /^Identificación/ }), {
      target: { value: "true" },
    });
    fireEvent.change(screen.getByRole("combobox", { name: /^Referencia/ }), {
      target: { value: "false" },
    });
    fireEvent.change(screen.getByLabelText(/^Recibido/), { target: { value: "1" } });
    fireEvent.click(screen.getByRole("button", { name: "Registrar" }));
    await waitFor(() => expect(posts("/lines")).toHaveLength(1));
    await waitFor(() =>
      expect(
        (screen.getByRole("combobox", { name: /^Identificación/ }) as HTMLSelectElement).value,
      ).toBe(""),
    );
    expect((screen.getByRole("combobox", { name: /^Referencia/ }) as HTMLSelectElement).value).toBe(
      "",
    );
  });

  it("abrir de nuevo una recepción no conserva la inspección a medias", async () => {
    apiFetch.mockImplementation(servidor());
    montar();
    await abrir();
    fireEvent.change(screen.getByRole("combobox", { name: /^Packing list comparado/ }), {
      target: { value: "true" },
    });
    fireEvent.change(screen.getByRole("combobox", { name: /^Factura comparada/ }), {
      target: { value: "false" },
    });
    const celda = screen.getByText("REC-1");
    fireEvent.click(within(celda.closest("tr") as HTMLElement).getByRole("button", { name: "detalle" }));
    await waitFor(() =>
      expect(
        (screen.getByRole("combobox", { name: /^Packing list comparado/ }) as HTMLSelectElement)
          .value,
      ).toBe(""),
    );
    expect(
      (screen.getByRole("combobox", { name: /^Factura comparada/ }) as HTMLSelectElement).value,
    ).toBe("");
  });

  it("O-07 estado de carga", async () => {
    apiFetch.mockImplementation(servidor({ ordenesPendientes: true }));
    montar();
    const estado = await screen.findByText("Cargando órdenes…");
    expect(estado.getAttribute("role")).toBe("status");
  });

  it("O-08 sin órdenes", async () => {
    apiFetch.mockImplementation(servidor({ ordenes: [] }));
    montar();
    const estado = await screen.findByText("No hay órdenes por recibir.");
    expect(estado.getAttribute("role")).toBe("status");
  });

  it("O-08b error", async () => {
    apiFetch.mockImplementation(servidor({ fallaOrdenes: true }));
    montar();
    const alerta = await screen.findByText("No fue posible cargar las órdenes.");
    expect(alerta.getAttribute("role")).toBe("alert");
  });

  it("O-09 O-10 la etiqueta es el código y la tabla no enseña identificadores", async () => {
    apiFetch.mockImplementation(servidor());
    montar();
    const celda = await screen.findByText("REC-1");
    const fila = celda.closest("tr");
    if (fila === null) {
      throw new Error("sin fila");
    }
    expect(fila.textContent).toContain("OC-1");
    expect(fila.textContent).not.toContain("00000000");
  });

  it("crear sin orden no envía", async () => {
    apiFetch.mockImplementation(servidor());
    montar();
    await esperaOpcion("OC-1");
    fireEvent.change(screen.getByLabelText(/^Código/), { target: { value: "R" } });
    await esperaOpcion(/A-1/);
    fireEvent.change(screen.getByRole("combobox", { name: /^Almacén/ }), { target: { value: "w1" } });
    fireEvent.click(screen.getByRole("button", { name: "Crear" }));
    await waitFor(() =>
      expect(notify).toHaveBeenCalledWith({
        type: "error",
        title: "No fue posible crear la recepción",
        description: "Seleccione una orden de compra.",
      }),
    );
    expect(posts("/purchasing/receipts")).toHaveLength(0);
  });

  it("crear envía la orden elegida", async () => {
    apiFetch.mockImplementation(servidor());
    montar();
    await esperaOpcion("OC-1");
    fireEvent.change(screen.getByRole("combobox", { name: /^Orden de compra/ }), {
      target: { value: "o1" },
    });
    await esperaOpcion(/A-1/);
    fireEvent.change(screen.getByRole("combobox", { name: /^Almacén/ }), { target: { value: "w1" } });
    fireEvent.change(screen.getByLabelText(/^Código/), { target: { value: "R" } });
    fireEvent.click(screen.getByRole("button", { name: "Crear" }));
    await waitFor(() => expect(posts("/purchasing/receipts")).toHaveLength(1));
    const [llamada] = posts("/purchasing/receipts");
    expect((llamada[1]?.body as { order_id: string }).order_id).toBe("o1");
  });

  it("W-02 W-05 solo se ofrecen almacenes activos", async () => {
    apiFetch.mockImplementation(servidor());
    montar();
    await esperaOpcion(/A-1/);
    expect(screen.queryByRole("option", { name: /A-2/ })).toBeNull();
  });

  it("W sin activos avisa", async () => {
    apiFetch.mockImplementation(
      servidor({ almacenes: [{ id: "w2", code: "A-2", name: "Cerrado", status: "INACTIVE" }] }),
    );
    montar();
    const estado = await screen.findByText("Esta empresa no tiene almacenes activos.");
    expect(estado.getAttribute("role")).toBe("status");
  });

  it.each([
    ["true", true],
    ["false", false],
    ["", null],
  ])("I y R envían lo declarado: %s", async (valor, esperado) => {
    apiFetch.mockImplementation(servidor());
    montar();
    await abrir();
    await esperaOpcion(/Arroz/);
    fireEvent.change(screen.getByRole("combobox", { name: /^Línea de la orden/ }), {
      target: { value: "l1" },
    });
    fireEvent.change(screen.getByRole("combobox", { name: /^Identificación/ }), {
      target: { value: valor },
    });
    fireEvent.change(screen.getByRole("combobox", { name: /^Referencia/ }), {
      target: { value: valor },
    });
    fireEvent.change(screen.getByLabelText(/^Recibido/), { target: { value: "1" } });
    fireEvent.click(screen.getByRole("button", { name: "Registrar" }));
    await waitFor(() => expect(posts("/lines")).toHaveLength(1));
    const [llamada] = posts("/lines");
    const body = llamada[1]?.body as { identification_ok: boolean | null; reference_ok: boolean | null };
    expect(body.identification_ok).toBe(esperado);
    expect(body.reference_ok).toBe(esperado);
  });

  it("OBS-02 nada viene declarado por defecto", async () => {
    apiFetch.mockImplementation(servidor());
    montar();
    await abrir();
    expect((screen.getByRole("combobox", { name: /^Identificación/ }) as HTMLSelectElement).value).toBe("");
    expect((screen.getByRole("combobox", { name: /^Referencia/ }) as HTMLSelectElement).value).toBe("");
    expect((screen.getByRole("combobox", { name: /^Estado físico/ }) as HTMLSelectElement).value).toBe("");
  });

  it("estado físico sin declarar va nulo", async () => {
    apiFetch.mockImplementation(servidor());
    montar();
    await abrir();
    await esperaOpcion(/Arroz/);
    fireEvent.change(screen.getByRole("combobox", { name: /^Línea de la orden/ }), {
      target: { value: "l1" },
    });
    fireEvent.change(screen.getByLabelText(/^Recibido/), { target: { value: "1" } });
    fireEvent.click(screen.getByRole("button", { name: "Registrar" }));
    await waitFor(() => expect(posts("/lines")).toHaveLength(1));
    const [llamada] = posts("/lines");
    const body = llamada[1]?.body as { physical_condition: string | null };
    expect(body.physical_condition).toBeNull();
  });

  it("estado físico declarado se envía", async () => {
    apiFetch.mockImplementation(servidor());
    montar();
    await abrir();
    await esperaOpcion(/Arroz/);
    fireEvent.change(screen.getByRole("combobox", { name: /^Línea de la orden/ }), {
      target: { value: "l1" },
    });
    fireEvent.change(screen.getByRole("combobox", { name: /^Estado físico/ }), {
      target: { value: "DAÑADO" },
    });
    fireEvent.change(screen.getByLabelText(/^Recibido/), { target: { value: "1" } });
    fireEvent.click(screen.getByRole("button", { name: "Registrar" }));
    await waitFor(() => expect(posts("/lines")).toHaveLength(1));
    const [llamada] = posts("/lines");
    const body = llamada[1]?.body as { physical_condition: string | null };
    expect(body.physical_condition).toBe("DAÑADO");
  });

  it("INS cada comparación envía lo suyo", async () => {
    apiFetch.mockImplementation(servidor());
    montar();
    await abrir();
    fireEvent.change(screen.getByRole("combobox", { name: /^Packing list comparado/ }), {
      target: { value: "true" },
    });
    fireEvent.change(screen.getByRole("combobox", { name: /^Factura comparada/ }), {
      target: { value: "false" },
    });
    fireEvent.change(screen.getByRole("combobox", { name: /^Documentación comparada/ }), {
      target: { value: "true" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Registrar inspección" }));
    await waitFor(() => expect(posts("/inspection")).toHaveLength(1));
    const [llamada] = posts("/inspection");
    const body = llamada[1]?.body as {
      packing_list_match: boolean | null;
      supplier_invoice_match: boolean | null;
      order_match: boolean | null;
      documentation_match: boolean | null;
    };
    expect(body.packing_list_match).toBe(true);
    expect(body.supplier_invoice_match).toBe(false);
    expect(body.order_match).toBeNull();
    expect(body.documentation_match).toBe(true);
  });

  it("INS no hay botones de todo o nada", async () => {
    apiFetch.mockImplementation(servidor());
    montar();
    await abrir();
    expect(screen.queryByRole("button", { name: "Registrar inspección conforme" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Registrar diferencias" })).toBeNull();
  });

  it("Q no conforme rechaza", async () => {
    apiFetch.mockImplementation(servidor({ recepcion: { status: "CONFIRMED" } }));
    montar();
    const celda = await screen.findByText("REC-1");
    const fila = celda.closest("tr");
    if (fila === null) {
      throw new Error("sin fila");
    }
    fireEvent.click(within(fila).getByRole("button", { name: "no conforme" }));
    await waitFor(() => expect(posts("/quality")).toHaveLength(1));
    const [llamada] = posts("/quality");
    const body = llamada[1]?.body as { quality_status: string };
    expect(body.quality_status).toBe("REJECTED");
  });
});
