/** Recepciones: la línea se elige de la orden y el producto se deriva de ella (FR-019-015). */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";

const { notify } = vi.hoisted(() => ({ notify: vi.fn() }));

const apiFetch = vi.fn();
vi.mock("@/api/client", async (original) => ({
  ...(await original<typeof import("@/api/client")>()),
  apiFetch: (...args: unknown[]) => apiFetch(...args),
}));
vi.mock("@/app/contexts/CompanyContext", () => ({
  useCompany: () => ({ activeCompany: { id: "emp-a", name: "Empresa" } }),
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

interface LineaOrden {
  id: string;
  product_id: string;
  quantity_ordered: number;
  quantity_received: number;
  unit_price: number;
  needs_inventory: boolean;
}

interface LineaRecepcion {
  id: string;
  order_line_id: string;
  product_id: string;
  quantity_received: string;
  presentation_id: string | null;
}

interface Ajustes {
  lineas?: LineaOrden[];
  lineasDeRecepcion?: LineaRecepcion[];
  orden?: "error" | "pendiente";
  productoFallido?: string;
}

function rechazo(): Promise<unknown> {
  return Promise.reject(new Error("offline"));
}

const RECIBOS = [
  {
    id: "r1",
    code: "REC-1",
    order_id: "o1",
    warehouse_id: "w1",
    status: "DRAFT",
    quality_status: "PENDING",
  },
  {
    id: "r2",
    code: "REC-2",
    order_id: "o2",
    warehouse_id: "w1",
    status: "DRAFT",
    quality_status: "PENDING",
  },
  {
    id: "r3",
    code: "REC-3",
    order_id: "o1",
    warehouse_id: "w1",
    status: "DRAFT",
    quality_status: "PENDING",
  },
];

const LINEAS_O1: LineaOrden[] = [
  {
    id: "l1",
    product_id: "p1",
    quantity_ordered: 100,
    quantity_received: 20,
    unit_price: 5,
    needs_inventory: true,
  },
  {
    id: "l2",
    product_id: "p2",
    quantity_ordered: 50,
    quantity_received: 50,
    unit_price: 5,
    needs_inventory: true,
  },
];

function producto(id: string): { id: string; code: string; name: string } {
  if (id === "p1") return { id, code: "P-001", name: "Arroz" };
  if (id === "p2") return { id, code: "P-002", name: "Harina" };
  if (id === "p9") return { id, code: "P-009", name: "Azúcar" };
  const n = id.replace(/^p/, "");
  return { id, code: `P-${n}`, name: `Producto ${n}` };
}

function presentaciones(id: string): Array<{ id: string; code: string; name: string }> {
  if (id === "p1") return [{ id: "pr1", code: "C1", name: "Caja arroz" }];
  if (id === "p2") return [{ id: "pr2", code: "C2", name: "Caja harina" }];
  return [];
}

function servidor(ajustes: Ajustes = {}) {
  const lineas = ajustes.lineas ?? LINEAS_O1;
  return (path: string, opciones?: Opciones): Promise<unknown> => {
    const url = new URL(path, "http://k");
    const ruta = url.pathname;
    const method = opciones?.method ?? "GET";

    if (ruta === "/purchasing/receipts" && method !== "POST") {
      return Promise.resolve({ items: RECIBOS });
    }
    if (ruta === "/purchasing/receipts/r1") {
      return Promise.resolve({ ...RECIBOS[0], lines: ajustes.lineasDeRecepcion ?? [] });
    }
    if (ruta === "/purchasing/receipts/r2") {
      return Promise.resolve({ ...RECIBOS[1], lines: [] });
    }
    if (ruta === "/purchasing/receipts/r3") {
      return Promise.resolve({ ...RECIBOS[2], lines: [] });
    }
    if (ruta === "/purchasing/orders/o1") {
      if (ajustes.orden === "error") return rechazo();
      if (ajustes.orden === "pendiente") return new Promise<unknown>(() => undefined);
      return Promise.resolve({ id: "o1", code: "OC-1", status: "APPROVED", lines: lineas });
    }
    if (ruta === "/purchasing/orders/o2") {
      return Promise.resolve({
        id: "o2",
        code: "OC-2",
        status: "APPROVED",
        lines: [
          {
            id: "l9",
            product_id: "p9",
            quantity_ordered: 10,
            quantity_received: 0,
            unit_price: 5,
            needs_inventory: true,
          },
        ],
      });
    }
    if (ruta.startsWith("/maestros/catalogos/items/")) {
      const id = ruta.slice("/maestros/catalogos/items/".length);
      if (ajustes.productoFallido === id) return rechazo();
      return Promise.resolve(producto(id));
    }
    if (ruta.startsWith("/maestros/productos/") && ruta.endsWith("/presentaciones")) {
      const id = ruta.slice("/maestros/productos/".length, -"/presentaciones".length);
      return Promise.resolve(presentaciones(id));
    }
    if (ruta === "/purchasing/receipts/r1/lines" && method === "POST") {
      return Promise.resolve({ id: "nueva" });
    }
    if (ruta === "/purchasing/receipts/r3/lines" && method === "POST") {
      return Promise.resolve({ id: "nueva" });
    }
    return Promise.resolve({ items: [], total: 0, page: 1, page_size: 20 });
  };
}

function montar() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <RecepcionesPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

async function abrir(codigo: string): Promise<void> {
  const celda = await screen.findByText(codigo);
  const fila = celda.closest("tr");
  if (!fila) throw new Error("fila no encontrada");
  fireEvent.click(within(fila as HTMLElement).getByRole("button", { name: "detalle" }));
  await screen.findByRole("heading", { name: `Inspección de ${codigo}` });
}

function selectorDeLinea(): Promise<HTMLElement> {
  return screen.findByRole("combobox", { name: /^Línea de la orden/ });
}

async function elegirLinea(id: string, textoDeOpcion: string | RegExp): Promise<void> {
  await screen.findByRole("option", { name: textoDeOpcion });
  fireEvent.change(await selectorDeLinea(), { target: { value: id } });
}

function postsDeLinea(): Array<{ path: string; opciones?: Opciones }> {
  return apiFetch.mock.calls
    .map((call) => {
      const [path, opciones] = call as [string, Opciones | undefined];
      return { path, opciones };
    })
    .filter(
      (llamada) =>
        llamada.opciones?.method === "POST" && llamada.path.endsWith("/lines"),
    );
}

beforeEach(() => {
  apiFetch.mockReset();
  notify.mockReset();
});

describe("Recepciones · línea de la orden", () => {
  it("FT-01 hay un selector de línea", async () => {
    apiFetch.mockImplementation(servidor());
    montar();
    await abrir("REC-1");
    const selector = await selectorDeLinea();
    expect(selector.tagName).toBe("SELECT");
    expect((selector as HTMLSelectElement).required).toBe(true);
  });

  it("FT-02 no se pide un identificador", async () => {
    apiFetch.mockImplementation(servidor());
    montar();
    await abrir("REC-1");
    await selectorDeLinea();
    expect(screen.queryByPlaceholderText("Identificador de la línea")).toBeNull();
  });

  it("FT-03 solo ofrece líneas de la orden de la recepción", async () => {
    apiFetch.mockImplementation(servidor());
    montar();
    await abrir("REC-2");
    await screen.findByRole("option", { name: /Azúcar/ });
    expect(screen.queryByRole("option", { name: /Arroz/ })).toBeNull();
  });

  it("FT-04 la etiqueta es humana", async () => {
    apiFetch.mockImplementation(servidor());
    montar();
    await abrir("REC-1");
    const opcion = await screen.findByRole("option", {
      name: "P-001 · Arroz — pedido 100, recibido 20, pendiente 80",
    });
    expect(opcion).toBeTruthy();
    const selector = await selectorDeLinea();
    const opciones = within(selector).getAllByRole("option");
    for (const item of opciones) {
      const texto = item.textContent ?? "";
      expect(texto).not.toContain("l1");
      expect(texto).not.toContain("p1");
    }
  });

  it("FT-05 FT-06 envía la línea elegida y su producto", async () => {
    apiFetch.mockImplementation(servidor());
    montar();
    await abrir("REC-1");
    await elegirLinea("l1", /Arroz/);
    fireEvent.change(screen.getByLabelText(/^Recibido/), { target: { value: "5" } });
    fireEvent.click(screen.getByRole("button", { name: "Registrar" }));
    await waitFor(() => expect(postsDeLinea()).toHaveLength(1));
    const [post] = postsDeLinea();
    const body = post.opciones?.body as Record<string, unknown>;
    expect(body.order_line_id).toBe("l1");
    expect(body.product_id).toBe("p1");
    expect(body.quantity_received).toBe(5);
    expect(body.presentation_id).toBeNull();
  });

  it("FT-07 FT-08 el producto se muestra y no se elige", async () => {
    apiFetch.mockImplementation(servidor());
    montar();
    await abrir("REC-1");
    await elegirLinea("l2", /Harina/);
    const campo = screen.getByLabelText(/^Producto/) as HTMLInputElement;
    await waitFor(() => expect(campo.value).toBe("P-002 · Harina"));
    expect(campo.readOnly).toBe(true);
    expect(screen.queryByRole("combobox", { name: /^Producto/ })).toBeNull();
  });

  it("FT-09 las presentaciones son las del producto de la línea", async () => {
    apiFetch.mockImplementation(servidor());
    montar();
    await abrir("REC-1");
    await elegirLinea("l1", /Arroz/);
    await screen.findByRole("option", { name: /Caja arroz/ });
    expect(screen.queryByRole("option", { name: /Caja harina/ })).toBeNull();
    const llamada = apiFetch.mock.calls.some(
      (call) => (call as [string])[0] === "/maestros/productos/p1/presentaciones",
    );
    expect(llamada).toBe(true);
  });

  it("FT-10 cambiar de línea limpia la presentación", async () => {
    apiFetch.mockImplementation(servidor());
    montar();
    await abrir("REC-1");
    await elegirLinea("l1", /Arroz/);
    await screen.findByRole("option", { name: /Caja arroz/ });
    const presentacion = screen.getByRole("combobox", { name: /^Presentación/ });
    fireEvent.change(presentacion, { target: { value: "pr1" } });
    await elegirLinea("l2", /Harina/);
    await screen.findByRole("option", { name: /Caja harina/ });
    expect((presentacion as HTMLSelectElement).value).toBe("");
    fireEvent.change(screen.getByLabelText(/^Recibido/), { target: { value: "1" } });
    fireEvent.click(screen.getByRole("button", { name: "Registrar" }));
    await waitFor(() => expect(postsDeLinea()).toHaveLength(1));
    const [post] = postsDeLinea();
    const body = post.opciones?.body as Record<string, unknown>;
    expect(body.product_id).toBe("p2");
    expect(body.presentation_id).toBeNull();
  });

  it("FT-11 otra recepción limpia lo elegido", async () => {
    apiFetch.mockImplementation(servidor());
    montar();
    await abrir("REC-1");
    await elegirLinea("l1", /Arroz/);
    fireEvent.change(screen.getByLabelText(/^Recibido/), { target: { value: "5" } });
    await abrir("REC-3");
    await screen.findByRole("option", { name: /Arroz/ });
    const selector = await selectorDeLinea();
    expect((selector as HTMLSelectElement).value).toBe("");
    expect((screen.getByLabelText(/^Recibido/) as HTMLInputElement).value).toBe("");
    fireEvent.click(screen.getByRole("button", { name: "Registrar" }));
    await waitFor(() => expect(notify).toHaveBeenCalled());
    expect(postsDeLinea()).toHaveLength(0);
  });

  it("FT-12 estado de carga", async () => {
    apiFetch.mockImplementation(servidor({ orden: "pendiente" }));
    montar();
    await abrir("REC-1");
    const aviso = await screen.findByText("Cargando líneas de la orden…");
    expect(aviso.getAttribute("role")).toBe("status");
  });

  it("FT-13 orden sin líneas", async () => {
    apiFetch.mockImplementation(servidor({ lineas: [] }));
    montar();
    await abrir("REC-1");
    const aviso = await screen.findByText("La orden no tiene líneas.");
    expect(aviso.getAttribute("role")).toBe("status");
  });

  it("FT-14 error de carga", async () => {
    apiFetch.mockImplementation(servidor({ orden: "error" }));
    montar();
    await abrir("REC-1");
    const aviso = await screen.findByText("No fue posible cargar las líneas de la orden.");
    expect(aviso.getAttribute("role")).toBe("alert");
  });

  it("FT-15 ofrece todas las líneas de una orden grande", async () => {
    const lineas: LineaOrden[] = Array.from({ length: 150 }, (_, i) => ({
      id: `l${i + 1}`,
      product_id: `p${i + 1}`,
      quantity_ordered: 10,
      quantity_received: 0,
      unit_price: 5,
      needs_inventory: true,
    }));
    apiFetch.mockImplementation(servidor({ lineas }));
    montar();
    await abrir("REC-1");
    await waitFor(async () => {
      const selector = await selectorDeLinea();
      expect(within(selector).getAllByRole("option")).toHaveLength(151);
    });
  });

  it("FT-16 una línea ya recibida se puede registrar", async () => {
    apiFetch.mockImplementation(servidor());
    montar();
    await abrir("REC-1");
    await elegirLinea("l2", "P-002 · Harina — pedido 50, recibido 50, pendiente 0");
    const opcion = screen.getByRole("option", {
      name: "P-002 · Harina — pedido 50, recibido 50, pendiente 0",
    });
    expect((opcion as HTMLOptionElement).disabled).toBe(false);
    fireEvent.change(screen.getByLabelText(/^Recibido/), { target: { value: "3" } });
    fireEvent.click(screen.getByRole("button", { name: "Registrar" }));
    await waitFor(() => expect(postsDeLinea()).toHaveLength(1));
  });

  it("un sobrante no deja pendiente negativo", async () => {
    apiFetch.mockImplementation(
      servidor({
        lineas: [
          {
            id: "l1",
            product_id: "p1",
            quantity_ordered: 50,
            quantity_received: 60,
            unit_price: 5,
            needs_inventory: true,
          },
        ],
      }),
    );
    montar();
    await abrir("REC-1");
    await screen.findByRole("option", {
      name: "P-001 · Arroz — pedido 50, recibido 60, pendiente 0",
    });
  });

  it("volver a una línea no recupera la presentación anterior", async () => {
    apiFetch.mockImplementation(servidor());
    montar();
    await abrir("REC-1");
    await elegirLinea("l1", /Arroz/);
    await screen.findByRole("option", { name: /Caja arroz/ });
    const presentacion = screen.getByRole("combobox", { name: /^Presentación/ });
    fireEvent.change(presentacion, { target: { value: "pr1" } });
    await elegirLinea("l2", /Harina/);
    await screen.findByRole("option", { name: /Caja harina/ });
    await elegirLinea("l1", /Arroz/);
    await screen.findByRole("option", { name: /Caja arroz/ });
    expect((presentacion as HTMLSelectElement).value).toBe("");
  });

  it("sin línea no se envía", async () => {
    apiFetch.mockImplementation(servidor());
    montar();
    await abrir("REC-1");
    await selectorDeLinea();
    await screen.findByRole("option", { name: /Arroz/ });
    fireEvent.change(screen.getByLabelText(/^Recibido/), { target: { value: "5" } });
    fireEvent.click(screen.getByRole("button", { name: "Registrar" }));
    await waitFor(() =>
      expect(notify).toHaveBeenCalledWith({
        type: "error",
        title: "No fue posible registrar la línea",
        description: "Seleccione la línea de la orden.",
      }),
    );
    expect(postsDeLinea()).toHaveLength(0);
  });

  it("tras registrar se vacía la línea y se recarga la orden", async () => {
    apiFetch.mockImplementation(servidor());
    montar();
    await abrir("REC-1");
    await elegirLinea("l1", /Arroz/);
    fireEvent.change(screen.getByLabelText(/^Recibido/), { target: { value: "5" } });
    fireEvent.click(screen.getByRole("button", { name: "Registrar" }));
    await waitFor(() => expect(postsDeLinea()).toHaveLength(1));
    await waitFor(async () => {
      const selector = await selectorDeLinea();
      expect((selector as HTMLSelectElement).value).toBe("");
    });
    await waitFor(() => {
      const llamadas = apiFetch.mock.calls.filter(
        (call) => (call as [string])[0] === "/purchasing/orders/o1",
      );
      expect(llamadas.length).toBeGreaterThanOrEqual(2);
    });
  });

  it("un producto sin resolver no muestra su identificador", async () => {
    apiFetch.mockImplementation(servidor({ productoFallido: "p1" }));
    montar();
    await abrir("REC-1");
    const aviso = await screen.findByText(
      "No fue posible identificar algunos productos de la orden.",
    );
    expect(aviso.getAttribute("role")).toBe("alert");
    await screen.findByRole("option", { name: /^Producto sin identificar — pedido 100/ });
  });

  it("la tabla de líneas recibidas muestra el producto", async () => {
    apiFetch.mockImplementation(
      servidor({
        lineasDeRecepcion: [
          {
            id: "g1",
            order_line_id: "l1",
            product_id: "p1",
            quantity_received: "2",
            presentation_id: null,
          },
        ],
      }),
    );
    montar();
    await abrir("REC-1");
    const region = await screen.findByRole("region", {
      name: "Líneas de la recepción REC-1",
    });
    await within(region).findByText("P-001 · Arroz");
  });
});
