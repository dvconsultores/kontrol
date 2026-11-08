import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const apiFetch = vi.fn();
vi.mock("@/api/client", async (original) => ({
  ...(await original<typeof import("@/api/client")>()),
  apiFetch: (...args: unknown[]) => apiFetch(...args),
}));

let empresaActiva = "emp-a";
vi.mock("@/app/contexts/CompanyContext", () => ({
  useCompany: () => ({ activeCompany: { id: empresaActiva, name: "Empresa" } }),
}));

const { SelectorDeTercero } = await import(
  "@/modules/maestros/terceros/SelectorDeTercero"
);

type Diferido<T> = { promise: Promise<T>; resolve: (value: T) => void };

function diferido<T>(): Diferido<T> {
  let resolver: (value: T) => void = () => undefined;
  const promise = new Promise<T>((resolve) => {
    resolver = resolve;
  });
  return { promise, resolve: resolver };
}

type Role = "CLIENTE" | "PROVEEDOR";
type Tercero = {
  id: string;
  code: string;
  name: string;
  tax_id: string;
  status: "ACTIVE" | "INACTIVE";
  roles: Role[];
};
type Empresa = "emp-a" | "emp-b";
type Pagina = { items: Tercero[]; total: number; page: number; page_size: number };
type LlamadaBusqueda = { empresa: Empresa; q: string; role?: string; status?: string };

const tercerosA: Tercero[] = Array.from({ length: 130 }, (_, index) => {
  const n = index + 1;
  const code = `T-${String(n).padStart(3, "0")}`;
  const roles: Role[] =
    n === 125 ? ["CLIENTE", "PROVEEDOR"] : n % 2 === 1 ? ["CLIENTE"] : ["PROVEEDOR"];
  return {
    id: `id-${n}`,
    code,
    name: `Tercero ${n}`,
    tax_id: `J-0000${String(n).padStart(3, "0")}`,
    status: n === 127 ? "INACTIVE" : "ACTIVE",
    roles,
  };
});

const tercerosB: Tercero[] = [
  {
    id: "id-b-9",
    code: "B-009",
    name: "Beta nueve",
    tax_id: "J-0000009",
    status: "ACTIVE",
    roles: ["PROVEEDOR"],
  },
  {
    id: "id-b-10",
    code: "B-010",
    name: "Beta diez",
    tax_id: "J-0000010",
    status: "ACTIVE",
    roles: ["CLIENTE"],
  },
];

let empresaServidor: Empresa = "emp-a";
const llamadasBusqueda: LlamadaBusqueda[] = [];

function tercerosDeEmpresa(empresa: Empresa): Tercero[] {
  return empresa === "emp-a" ? tercerosA : tercerosB;
}

function filtrarTerceros(
  terceros: Tercero[],
  q: string,
  role?: string,
  status?: string,
): Tercero[] {
  const normalizado = q.trim().toLowerCase();
  return terceros.filter((tercero) => {
    if (normalizado) {
      const coincide =
        tercero.code.toLowerCase().includes(normalizado) ||
        tercero.name.toLowerCase().includes(normalizado) ||
        tercero.tax_id.toLowerCase().includes(normalizado);
      if (!coincide) return false;
    }
    if (role && !tercero.roles.includes(role as Role)) return false;
    if (status && tercero.status !== status) return false;
    return true;
  });
}

function pagina(terceros: Tercero[], page: number, pageSize = 20): Pagina {
  const inicio = (page - 1) * pageSize;
  return {
    items: terceros.slice(inicio, inicio + pageSize),
    total: terceros.length,
    page,
    page_size: pageSize,
  };
}

function ruta(url: string): { pathname: string; search: string } {
  const separador = url.indexOf("?");
  if (separador === -1) return { pathname: url, search: "" };
  return { pathname: url.slice(0, separador), search: url.slice(separador) };
}

function configurarApi() {
  apiFetch.mockImplementation(async (url: string) => {
    const { pathname, search } = ruta(url);

    if (pathname === "/maestros/terceros") {
      const params = new URLSearchParams(search);
      const q = params.get("q") ?? "";
      const role = params.get("role") ?? undefined;
      const status = params.get("status") ?? undefined;
      const page = Number(params.get("page") ?? "1");
      const pageSize = Number(params.get("page_size") ?? "20");
      llamadasBusqueda.push({ empresa: empresaServidor, q, role, status });
      const filtrados = filtrarTerceros(tercerosDeEmpresa(empresaServidor), q, role, status);
      return Promise.resolve(pagina(filtrados, page, pageSize));
    }

    if (pathname.startsWith("/maestros/terceros/")) {
      const id = pathname.slice("/maestros/terceros/".length);
      const tercero = tercerosDeEmpresa(empresaServidor).find((item) => item.id === id);
      if (!tercero) {
        throw new Error(`Tercero no encontrado: ${id}`);
      }
      return Promise.resolve({ code: tercero.code, name: tercero.name });
    }

    throw new Error(`URL inesperada: ${url}`);
  });
}

function crearCliente(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });
}

function renderConCliente(cliente: QueryClient, ui: React.ReactElement) {
  return render(<QueryClientProvider client={cliente}>{ui}</QueryClientProvider>);
}

function ArnesSelector({
  value,
  onChange,
  role,
  soloActivos,
  id,
}: {
  value: string;
  onChange: (id: string) => void;
  role?: "CLIENTE" | "PROVEEDOR";
  soloActivos?: boolean;
  id?: string;
}) {
  return (
    <>
      <label htmlFor={id ?? "selector-tercero"}>Tercero</label>
      <SelectorDeTercero
        id={id ?? "selector-tercero"}
        value={value}
        onChange={onChange}
        role={role}
        soloActivos={soloActivos}
      />
    </>
  );
}

function ArnesControlado({
  role,
  soloActivos,
  onChange,
}: {
  role?: "CLIENTE" | "PROVEEDOR";
  soloActivos?: boolean;
  onChange?: (id: string) => void;
}) {
  const [value, setValue] = useState("");
  const manejarCambio = (id: string) => {
    setValue(id);
    onChange?.(id);
  };
  return (
    <ArnesSelector
      value={value}
      onChange={manejarCambio}
      role={role}
      soloActivos={soloActivos}
    />
  );
}

beforeEach(() => {
  empresaActiva = "emp-a";
  empresaServidor = "emp-a";
  llamadasBusqueda.length = 0;
  apiFetch.mockReset();
  configurarApi();
});

describe("SelectorDeTercero", () => {
  it("TS-01 busca por nombre", async () => {
    const user = userEvent.setup();
    renderConCliente(crearCliente(), <ArnesControlado />);

    await user.type(screen.getByRole("combobox"), "Tercero 25");

    expect(await screen.findByRole("option", { name: /T-025/ })).toBeInTheDocument();
    expect(
      llamadasBusqueda.some((llamada) => llamada.q === "Tercero 25"),
    ).toBe(true);
  });

  it("TS-02 busca por código", async () => {
    const user = userEvent.setup();
    renderConCliente(crearCliente(), <ArnesControlado />);

    await user.type(screen.getByRole("combobox"), "T-026");

    expect(await screen.findByRole("option", { name: /T-026/ })).toBeInTheDocument();
    expect(llamadasBusqueda.some((llamada) => llamada.q === "T-026")).toBe(true);
  });

  it("TS-03 busca por RIF", async () => {
    const user = userEvent.setup();
    renderConCliente(crearCliente(), <ArnesControlado />);

    await user.type(screen.getByRole("combobox"), "J-0000027");

    expect(await screen.findByRole("option", { name: /T-027/ })).toBeInTheDocument();
    expect(
      llamadasBusqueda.some((llamada) => llamada.q === "J-0000027"),
    ).toBe(true);
  });

  it("TS-04 pagina más de 20 resultados con role CLIENTE", async () => {
    const user = userEvent.setup();
    renderConCliente(crearCliente(), <ArnesControlado role="CLIENTE" />);

    const input = screen.getByRole("combobox");
    await user.click(input);

    const cargarMas = await screen.findByRole("button", { name: /Cargar más resultados/ });
    await user.click(cargarMas);

    expect(await screen.findByRole("option", { name: /T-065/ })).toBeInTheDocument();
  });

  it("TS-05 pagina más de 100 resultados sin role", async () => {
    const user = userEvent.setup();
    renderConCliente(crearCliente(), <ArnesControlado />);

    const input = screen.getByRole("combobox");
    await user.click(input);

    for (let i = 1; i <= 6; i++) {
      await screen.findByText(`Mostrando ${20 * i} de 130`);
      await user.click(screen.getByRole("button", { name: /Cargar más resultados/ }));
    }

    expect(await screen.findByRole("option", { name: /T-130/ })).toBeInTheDocument();
  });

  it("TS-06 muestra etiqueta al elegir tercero", async () => {
    const user = userEvent.setup();
    renderConCliente(crearCliente(), <ArnesControlado />);

    await user.type(screen.getByRole("combobox"), "Tercero 25");
    await user.click(await screen.findByRole("option", { name: /T-025/ }));

    expect(screen.getByRole("combobox")).toHaveValue("T-025 · Tercero 25");
  });

  it("TS-07 la etiqueta no contiene el id", async () => {
    const user = userEvent.setup();
    renderConCliente(crearCliente(), <ArnesControlado />);

    await user.type(screen.getByRole("combobox"), "Tercero 25");
    await user.click(await screen.findByRole("option", { name: /T-025/ }));

    expect(screen.getByRole("combobox")).not.toHaveValue("id-25 · Tercero 25");
  });

  it("TS-08 onChange recibe el id", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    renderConCliente(crearCliente(), <ArnesSelector value="" onChange={onChange} />);

    await user.type(screen.getByRole("combobox"), "Tercero 25");
    await user.click(await screen.findByRole("option", { name: /T-025/ }));

    expect(onChange).toHaveBeenCalledWith("id-25");
  });

  it("TS-09 muestra valor inicial sin abrir la lista", async () => {
    renderConCliente(crearCliente(), <ArnesSelector value="id-77" onChange={() => undefined} />);

    expect(await screen.findByDisplayValue("T-077 · Tercero 77")).toBeInTheDocument();
  });

  it("TS-10 muestra cargando durante búsqueda diferida", async () => {
    const user = userEvent.setup();
    const pendiente = diferido<Pagina>();
    apiFetch.mockImplementation(async (url: string) => {
      const { pathname, search } = ruta(url);
      if (pathname === "/maestros/terceros") {
        const q = new URLSearchParams(search).get("q") ?? "";
        llamadasBusqueda.push({ empresa: empresaServidor, q });
        return pendiente.promise;
      }
      if (pathname.startsWith("/maestros/terceros/")) {
        return Promise.resolve({ code: "T-001", name: "Tercero 1" });
      }
      throw new Error(`URL inesperada: ${url}`);
    });

    renderConCliente(crearCliente(), <ArnesControlado />);

    await user.type(screen.getByRole("combobox"), "Tercero");

    expect(await screen.findByText("Buscando…")).toBeInTheDocument();

    await act(async () => {
      pendiente.resolve(pagina(filtrarTerceros(tercerosA, "Tercero"), 1));
    });
  });

  it("TS-11 muestra sin resultados", async () => {
    const user = userEvent.setup();
    renderConCliente(crearCliente(), <ArnesControlado />);

    await user.type(screen.getByRole("combobox"), "no-existe");

    expect(await screen.findByText("Sin resultados")).toBeInTheDocument();
  });

  it("TS-12 muestra error de primera página", async () => {
    const user = userEvent.setup();
    apiFetch.mockImplementation(async (url: string) => {
      const { pathname } = ruta(url);
      if (pathname === "/maestros/terceros") {
        throw new Error("Error de búsqueda");
      }
      if (pathname.startsWith("/maestros/terceros/")) {
        return Promise.resolve({ code: "T-001", name: "Tercero 1" });
      }
      throw new Error(`URL inesperada: ${url}`);
    });

    renderConCliente(crearCliente(), <ArnesControlado />);

    await user.type(screen.getByRole("combobox"), "Tercero");

    expect(
      await screen.findByText("No fue posible completar la búsqueda"),
    ).toBeInTheDocument();
  });

  it("TS-13 muestra error de página posterior manteniendo opciones", async () => {
    const user = userEvent.setup();
    renderConCliente(crearCliente(), <ArnesControlado />);

    const input = screen.getByRole("combobox");
    await user.click(input);

    const cargarMas = await screen.findByRole("button", { name: /Cargar más resultados/ });
    apiFetch.mockImplementation(async (url: string) => {
      const { pathname, search } = ruta(url);
      if (pathname === "/maestros/terceros") {
        const params = new URLSearchParams(search);
        const page = Number(params.get("page") ?? "1");
        if (page === 1) {
          return Promise.resolve(pagina(tercerosA, 1));
        }
        throw new Error("Error de página posterior");
      }
      if (pathname.startsWith("/maestros/terceros/")) {
        return Promise.resolve({ code: "T-001", name: "Tercero 1" });
      }
      throw new Error(`URL inesperada: ${url}`);
    });

    await user.click(cargarMas);

    expect(
      await screen.findByText("No fue posible cargar más resultados"),
    ).toBeInTheDocument();
    expect(screen.getByRole("option", { name: /T-001/ })).toBeInTheDocument();
  });

  it("TS-14 cambiar q reemplaza la lista", async () => {
    const user = userEvent.setup();
    renderConCliente(crearCliente(), <ArnesControlado />);

    const input = screen.getByRole("combobox");
    await user.type(input, "T-025");

    await waitFor(() => {
      const opciones = screen.getAllByRole("option");
      expect(opciones).toHaveLength(1);
      expect(opciones[0]).toHaveTextContent("T-025");
    });

    await user.clear(input);
    await user.type(input, "T-026");

    await waitFor(() => {
      const opciones = screen.getAllByRole("option");
      expect(opciones).toHaveLength(1);
      expect(opciones[0]).toHaveTextContent("T-026");
    });
  });

  it("TS-15 aísla búsqueda al cambiar de empresa con respuesta pendiente", async () => {
    const user = userEvent.setup();
    const cliente = crearCliente();
    const { rerender } = renderConCliente(cliente, <ArnesControlado />);

    const input = screen.getByRole("combobox");
    await user.click(input);

    expect(await screen.findByRole("option", { name: /T-001/ })).toBeInTheDocument();

    const bPendiente = diferido<Pagina>();
    apiFetch.mockImplementation(async (url: string) => {
      const { pathname, search } = ruta(url);
      if (pathname === "/maestros/terceros") {
        const q = new URLSearchParams(search).get("q") ?? "";
        llamadasBusqueda.push({ empresa: empresaServidor, q });
        if (empresaServidor === "emp-a") {
          return Promise.resolve(pagina(filtrarTerceros(tercerosA, q), 1));
        }
        return bPendiente.promise;
      }
      if (pathname.startsWith("/maestros/terceros/")) {
        return Promise.resolve({ code: "B-009", name: "Beta nueve" });
      }
      throw new Error(`URL inesperada: ${url}`);
    });

    empresaServidor = "emp-b";
    empresaActiva = "emp-b";

    rerender(
      <QueryClientProvider client={cliente}>
        <ArnesControlado />
      </QueryClientProvider>,
    );

    expect(screen.queryByRole("option", { name: /T-001/ })).toBeNull();
    expect(screen.getByText("Buscando…")).toBeInTheDocument();

    await waitFor(() => {
      expect(llamadasBusqueda.some((llamada) => llamada.empresa === "emp-b")).toBe(true);
    });

    await act(async () => {
      bPendiente.resolve(pagina(tercerosB, 1));
    });

    expect(await screen.findByRole("option", { name: /B-009/ })).toBeInTheDocument();
    expect(screen.queryByRole("option", { name: /T-001/ })).toBeNull();
  });

  it("TS-16 una respuesta tardía de la empresa A no contamina la empresa B", async () => {
    const user = userEvent.setup();
    const cliente = crearCliente();
    const { rerender } = renderConCliente(cliente, <ArnesControlado />);

    const input = screen.getByRole("combobox");

    const aPendiente = diferido<Pagina>();
    apiFetch.mockImplementation(async (url: string) => {
      const { pathname, search } = ruta(url);
      if (pathname === "/maestros/terceros") {
        const q = new URLSearchParams(search).get("q") ?? "";
        llamadasBusqueda.push({ empresa: empresaServidor, q });
        if (empresaServidor === "emp-a") return aPendiente.promise;
        return Promise.resolve(pagina(tercerosB, 1));
      }
      if (pathname.startsWith("/maestros/terceros/")) {
        return Promise.resolve({ code: "B-009", name: "Beta nueve" });
      }
      throw new Error(`URL inesperada: ${url}`);
    });

    await user.type(input, "producto");

    await waitFor(() => {
      expect(
        llamadasBusqueda.some(
          (llamada) => llamada.empresa === "emp-a" && llamada.q === "producto",
        ),
      ).toBe(true);
    });

    empresaServidor = "emp-b";
    empresaActiva = "emp-b";

    rerender(
      <QueryClientProvider client={cliente}>
        <ArnesControlado />
      </QueryClientProvider>,
    );

    expect(await screen.findByRole("option", { name: /B-009/ })).toBeInTheDocument();

    await act(async () => {
      aPendiente.resolve(pagina([tercerosA[0]], 1));
    });

    expect(screen.queryByRole("option", { name: /T-001/ })).toBeNull();
    expect(screen.getByRole("option", { name: /B-009/ })).toBeInTheDocument();
  });

  it("TS-17 la selección de la empresa A no se aplica a la empresa B", async () => {
    const user = userEvent.setup();
    const cliente = crearCliente();
    const onChange = vi.fn();
    const { rerender } = renderConCliente(
      cliente,
      <ArnesControlado onChange={onChange} />,
    );

    await user.type(screen.getByRole("combobox"), "Tercero 25");
    await user.click(await screen.findByRole("option", { name: /T-025/ }));

    expect(onChange).toHaveBeenLastCalledWith("id-25");
    expect(screen.getByRole("combobox")).toHaveValue("T-025 · Tercero 25");

    empresaActiva = "emp-b";
    empresaServidor = "emp-b";

    rerender(
      <QueryClientProvider client={cliente}>
        <ArnesControlado onChange={onChange} />
      </QueryClientProvider>,
    );

    await waitFor(() => {
      expect(onChange).toHaveBeenLastCalledWith("");
    });
    expect(screen.getByRole("combobox")).toHaveValue("");
  });

  it("TS-17b aísla la resolución inicial compartiendo QueryClient", async () => {
    const cliente = crearCliente();

    const montajeUno = renderConCliente(
      cliente,
      <ArnesSelector value="id-9" onChange={() => undefined} />,
    );

    expect(await screen.findByDisplayValue("T-009 · Tercero 9")).toBeInTheDocument();

    montajeUno.unmount();

    const bPendiente = diferido<{ code: string; name: string }>();
    apiFetch.mockImplementation(async (url: string) => {
      const { pathname } = ruta(url);
      if (pathname === "/maestros/terceros") {
        return Promise.resolve(pagina([], 1));
      }
      if (pathname.startsWith("/maestros/terceros/")) {
        if (empresaServidor === "emp-a") {
          return Promise.resolve({ code: "T-009", name: "Tercero 9" });
        }
        return bPendiente.promise;
      }
      throw new Error(`URL inesperada: ${url}`);
    });

    empresaServidor = "emp-b";
    empresaActiva = "emp-b";

    renderConCliente(cliente, <ArnesSelector value="id-9" onChange={() => undefined} />);

    expect(screen.getByRole("combobox")).toHaveValue("");

    await act(async () => {
      bPendiente.resolve({ code: "B-009", name: "Beta nueve" });
    });

    expect(await screen.findByDisplayValue("B-009 · Beta nueve")).toBeInTheDocument();
  });

  it("TS-18 role CLIENTE filtra las búsquedas", async () => {
    const user = userEvent.setup();
    renderConCliente(crearCliente(), <ArnesControlado role="CLIENTE" />);

    const input = screen.getByRole("combobox");
    await user.type(input, "T-025");

    expect(await screen.findByRole("option", { name: /T-025/ })).toBeInTheDocument();
    await waitFor(() => {
      expect(
        llamadasBusqueda.some(
          (llamada) => llamada.q === "T-025" && llamada.role === "CLIENTE",
        ),
      ).toBe(true);
    });
    expect(
      llamadasBusqueda
        .filter((llamada) => llamada.q === "T-025")
        .every((llamada) => llamada.role === "CLIENTE"),
    ).toBe(true);

    await user.clear(input);
    await user.type(input, "T-026");
    expect(await screen.findByText("Sin resultados")).toBeInTheDocument();
    await waitFor(() => {
      expect(
        llamadasBusqueda.some(
          (llamada) => llamada.q === "T-026" && llamada.role === "CLIENTE",
        ),
      ).toBe(true);
    });
  });

  it("TS-19 role PROVEEDOR filtra las búsquedas", async () => {
    const user = userEvent.setup();
    renderConCliente(crearCliente(), <ArnesControlado role="PROVEEDOR" />);

    const input = screen.getByRole("combobox");
    await user.type(input, "T-026");

    expect(await screen.findByRole("option", { name: /T-026/ })).toBeInTheDocument();
    await waitFor(() => {
      expect(
        llamadasBusqueda.some(
          (llamada) => llamada.q === "T-026" && llamada.role === "PROVEEDOR",
        ),
      ).toBe(true);
    });
    expect(
      llamadasBusqueda
        .filter((llamada) => llamada.q === "T-026")
        .every((llamada) => llamada.role === "PROVEEDOR"),
    ).toBe(true);

    await user.clear(input);
    await user.type(input, "T-025");
    expect(await screen.findByText("Sin resultados")).toBeInTheDocument();
    await waitFor(() => {
      expect(
        llamadasBusqueda.some(
          (llamada) => llamada.q === "T-025" && llamada.role === "PROVEEDOR",
        ),
      ).toBe(true);
    });
  });

  it("TS-20 el tercero multirol se ofrece en ambos roles", async () => {
    const user = userEvent.setup();
    const { unmount } = renderConCliente(
      crearCliente(),
      <ArnesControlado role="CLIENTE" />,
    );

    await user.type(screen.getByRole("combobox"), "T-125");
    expect(await screen.findByRole("option", { name: /T-125/ })).toBeInTheDocument();

    unmount();

    renderConCliente(crearCliente(), <ArnesControlado role="PROVEEDOR" />);
    const input = screen.getByRole("combobox");
    await user.type(input, "T-125");

    expect(await screen.findByRole("option", { name: /T-125/ })).toBeInTheDocument();
  });

  it("TS-21 soloActivos filtra inactivos", async () => {
    const user = userEvent.setup();
    const { unmount } = renderConCliente(
      crearCliente(),
      <ArnesControlado soloActivos />,
    );

    await user.type(screen.getByRole("combobox"), "T-127");
    expect(await screen.findByText("Sin resultados")).toBeInTheDocument();
    expect(
      llamadasBusqueda.some(
        (llamada) => llamada.q === "T-127" && llamada.status === "ACTIVE",
      ),
    ).toBe(true);

    unmount();

    renderConCliente(crearCliente(), <ArnesControlado />);
    const input = screen.getByRole("combobox");
    await user.type(input, "T-127");

    expect(await screen.findByRole("option", { name: /T-127/ })).toBeInTheDocument();
    expect(
      llamadasBusqueda.some(
        (llamada) => llamada.q === "T-127" && llamada.status === undefined,
      ),
    ).toBe(true);
  });

  it("TS-22 display histórico permite mostrar un inactivo existente", async () => {
    renderConCliente(
      crearCliente(),
      <ArnesSelector value="id-127" onChange={() => undefined} role="CLIENTE" soloActivos />,
    );

    expect(await screen.findByDisplayValue("T-127 · Tercero 127")).toBeInTheDocument();
  });

  it("TS-23 el filtro forma parte de la caché", async () => {
    const user = userEvent.setup();
    const cliente = crearCliente();
    const { rerender } = renderConCliente(cliente, <ArnesControlado role="CLIENTE" />);

    await user.type(screen.getByRole("combobox"), "T-025");
    expect(await screen.findByRole("option", { name: /T-025/ })).toBeInTheDocument();

    const pendienteProveedor = diferido<Pagina>();
    apiFetch.mockImplementation(async (url: string) => {
      const { pathname, search } = ruta(url);
      if (pathname === "/maestros/terceros") {
        const q = new URLSearchParams(search).get("q") ?? "";
        const role = new URLSearchParams(search).get("role") ?? undefined;
        llamadasBusqueda.push({ empresa: empresaServidor, q, role });
        if (role === "PROVEEDOR") return pendienteProveedor.promise;
        return Promise.resolve(pagina(filtrarTerceros(tercerosA, q, role), 1));
      }
      if (pathname.startsWith("/maestros/terceros/")) {
        return Promise.resolve({ code: "T-001", name: "Tercero 1" });
      }
      throw new Error(`URL inesperada: ${url}`);
    });

    rerender(
      <QueryClientProvider client={cliente}>
        <ArnesControlado role="PROVEEDOR" />
      </QueryClientProvider>,
    );

    expect(screen.queryByRole("option", { name: /T-025/ })).toBeNull();
    expect(screen.getByText("Buscando…")).toBeInTheDocument();

    await act(async () => {
      pendienteProveedor.resolve(pagina([], 1));
    });

    expect(screen.queryByRole("option", { name: /T-025/ })).toBeNull();
  });
});
