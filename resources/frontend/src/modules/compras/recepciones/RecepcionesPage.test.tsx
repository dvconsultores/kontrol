/** Recepciones: el almacén se elige, no se escribe (RECEPCION-ALMACEN-TEXTO-LIBRE, FR-004-030). */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
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

interface Almacen {
  id: string;
  code: string;
  name: string;
}

function servidor(total: number, fallaEnOffset?: number) {
  return (path: string, opciones?: Opciones) => {
    const url = new URL(path, "http://k");

    if (url.pathname === "/organization/warehouses") {
      const limit = Number(url.searchParams.get("limit") ?? 50);
      const offset = Number(url.searchParams.get("offset") ?? 0);
      const compania = url.searchParams.get("company_id");

      if (offset === fallaEnOffset) {
        return Promise.reject(new Error("PAGINA_CAIDA"));
      }
      if (limit > 100) {
        return Promise.reject(new Error("LIMITE"));
      }
      if (compania !== null && compania !== empresa.id) {
        return Promise.resolve({ total: 0, limit, offset, items: [] });
      }

      const todos: Almacen[] = Array.from({ length: total }, (_, i) => {
        const n = i + 1;
        return { id: `${empresa.id}-w${n}`, code: `A-${String(n).padStart(3, "0")}`, name: `Almacén ${n}` };
      });
      const items = todos.slice(offset, offset + limit);
      return Promise.resolve({ total, limit, offset, items });
    }

    if (url.pathname === "/purchasing/orders") {
      return Promise.resolve({
        items: [{ id: "o1", code: "OC-1", status: "APPROVED" }],
        total: 1,
        page: 1,
        page_size: 20,
      });
    }

    if (url.pathname === "/purchasing/receipts" && opciones?.method === "POST") {
      return Promise.resolve({ id: "r1" });
    }

    if (url.pathname === "/purchasing/receipts/r1") {
      return Promise.reject(new Error("SIN_DETALLE"));
    }

    return Promise.resolve({ items: [], total: 0, page: 1, page_size: 20 });
  };
}

function montar() {
  const cliente = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  function arbol() {
    return (
      <QueryClientProvider client={cliente}>
        <MemoryRouter>
          <RecepcionesPage />
        </MemoryRouter>
      </QueryClientProvider>
    );
  }
  const { rerender } = render(arbol());
  function repintar() {
    rerender(arbol());
  }
  return { repintar };
}

function selector() {
  return screen.findByRole("combobox", { name: /^Almacén/ });
}

async function rellenar(valor?: string) {
  await screen.findByRole("option", { name: "OC-1" });
  fireEvent.change(screen.getByLabelText(/^Código/), { target: { value: "REC-1" } });
  fireEvent.change(screen.getByLabelText(/^Orden de compra/), { target: { value: "o1" } });
  if (valor !== undefined) {
    await screen.findByRole("option", { name: /A-002/ });
    fireEvent.change(await selector(), { target: { value: valor } });
    expect(((await selector()) as HTMLSelectElement).value).toBe(valor);
  }
}

function posts() {
  return apiFetch.mock.calls.filter((llamada) => (llamada[1] as Opciones | undefined)?.method === "POST");
}

beforeEach(() => {
  apiFetch.mockReset();
  notify.mockReset();
  empresa.id = "emp-a";
});

describe("Recepciones · elección de almacén", () => {
  it("DT-01 muestra un selector de almacén y no un campo de texto", async () => {
    apiFetch.mockImplementation(servidor(3));
    montar();

    await selector();

    expect(screen.queryByPlaceholderText(/Identificador del almac/)).toBeNull();
  });

  it("DT-02 cada opción muestra código y nombre", async () => {
    apiFetch.mockImplementation(servidor(3));
    montar();

    expect(await screen.findByRole("option", { name: "A-001 · Almacén 1" })).toBeTruthy();
  });

  it("DT-03 envía el id del almacén elegido", async () => {
    apiFetch.mockImplementation(servidor(3));
    montar();

    await rellenar("emp-a-w2");
    fireEvent.click(screen.getByRole("button", { name: /Crear/ }));

    await waitFor(() => expect(posts()).toHaveLength(1));
    const body = (posts()[0][1] as Opciones).body as { warehouse_id: string; order_id: string };
    expect(body.warehouse_id).toBe("emp-a-w2");
    expect(body.order_id).toBe("o1");
  });

  it("DT-04 el campo es obligatorio", async () => {
    apiFetch.mockImplementation(servidor(3));
    montar();

    const campo = await selector();
    expect((campo as HTMLSelectElement).required).toBe(true);
  });

  it("sin almacén no se envía", async () => {
    apiFetch.mockImplementation(servidor(3));
    montar();

    await rellenar();
    fireEvent.click(screen.getByRole("button", { name: /Crear/ }));

    await waitFor(() => expect(notify).toHaveBeenCalled());
    expect(posts()).toHaveLength(0);
    expect(notify).toHaveBeenCalledWith(expect.objectContaining({ type: "error" }));
  });

  it("DT-05 alcanza el almacén 51", async () => {
    apiFetch.mockImplementation(servidor(51));
    montar();

    expect(await screen.findByRole("option", { name: "A-051 · Almacén 51" })).toBeTruthy();
  });

  it("DT-06 recorre más de 100 almacenes", async () => {
    apiFetch.mockImplementation(servidor(250));
    montar();

    await selector();
    expect(await screen.findByRole("option", { name: /A-250/ })).toBeTruthy();
    const opciones = await screen.findAllByRole("option", { name: /^A-\d{3}/ });
    expect(opciones).toHaveLength(250);
  });

  it("DT-07 pide en la empresa activa", async () => {
    apiFetch.mockImplementation(servidor(3));
    montar();

    await selector();
    await waitFor(() => expect(apiFetch).toHaveBeenCalled());

    const llamadas = apiFetch.mock.calls.filter(
      (llamada) => new URL(llamada[0] as string, "http://k").pathname === "/organization/warehouses",
    );
    expect(llamadas.length).toBeGreaterThan(0);
    for (const llamada of llamadas) {
      const url = new URL(llamada[0] as string, "http://k");
      expect(url.searchParams.get("company_id")).toBe("emp-a");
    }
  });

  it("DT-08 muestra la carga", async () => {
    apiFetch.mockImplementation(() => new Promise(() => undefined));
    montar();

    expect(await screen.findByText("Cargando almacenes…")).toBeTruthy();
  });

  it("DT-09 muestra el vacío", async () => {
    apiFetch.mockImplementation(servidor(0));
    montar();

    expect(await screen.findByText("Esta empresa no tiene almacenes.")).toBeTruthy();
  });

  it("DT-10 una página caída no pinta lista parcial", async () => {
    apiFetch.mockImplementation(servidor(120, 100));
    montar();

    const aviso = await screen.findByRole("alert");
    expect(aviso.textContent).toContain("No fue posible cargar todos los almacenes.");
    expect(screen.queryByRole("option", { name: /A-001/ })).toBeNull();
  });

  it("DT-11 una página caída no pinta lista parcial (sin selección parcial)", async () => {
    apiFetch.mockImplementation(servidor(120, 100));
    montar();

    await screen.findByRole("alert");
    expect(screen.queryByRole("option", { name: /^A-\d{3}/ })).toBeNull();
  });

  it("DT-12 el cambio de empresa descarta la selección", async () => {
    apiFetch.mockImplementation(servidor(3));
    const { repintar } = montar();

    await rellenar("emp-a-w2");

    empresa.id = "emp-b";
    repintar();

    const nueva = await screen.findByRole("option", { name: /A-001/ });
    expect((nueva as HTMLOptionElement).value).toBe("emp-b-w1");

    fireEvent.change(screen.getByLabelText(/^Código/), { target: { value: "REC-1" } });
    fireEvent.change(screen.getByLabelText(/^Orden de compra/), { target: { value: "o1" } });
    fireEvent.click(screen.getByRole("button", { name: /Crear/ }));

    await waitFor(() => expect(notify).toHaveBeenCalledWith(expect.objectContaining({ type: "error" })));
    expect(posts()).toHaveLength(0);
  });

  it("DT-14 los demás campos no cambian", async () => {
    apiFetch.mockImplementation(servidor(3));
    montar();

    await rellenar("emp-a-w2");
    fireEvent.change(screen.getByLabelText(/^Packing list/), { target: { value: "PL-1" } });
    fireEvent.click(screen.getByRole("button", { name: /Crear/ }));

    await waitFor(() => expect(posts()).toHaveLength(1));
    const body = (posts()[0][1] as Opciones).body as { packing_list_ref: string };
    expect(body.packing_list_ref).toBe("PL-1");
  });
});
