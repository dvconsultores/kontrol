/** Aislamiento de caché por empresa en AsyncCombobox (M4_CACHE_SCOPE_CERTIFICATION). */
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

const { AsyncCombobox } = await import("@/components/AsyncCombobox");
const { SelectorDeArticulo } = await import("@/modules/maestros/catalogo/SelectorDeArticulo");

type Diferido<T> = { promise: Promise<T>; resolve: (value: T) => void };

function diferido<T>(): Diferido<T> {
  let resolver: (value: T) => void = () => undefined;
  const promise = new Promise<T>((resolve) => {
    resolver = resolve;
  });
  return { promise, resolve: resolver };
}

type Item = { id: string; code: string; name: string; item_type?: "PRODUCT" | "SERVICE" };
type Empresa = "emp-a" | "emp-b";
type Pagina = { items: Item[]; total: number; page: number; page_size: number };
type LlamadaBusqueda = { empresa: Empresa; q: string };

const itemA: Item = { id: "a-1", code: "A-001", name: "Alfa", item_type: "PRODUCT" };
const itemB: Item = { id: "b-1", code: "B-001", name: "Beta", item_type: "PRODUCT" };

function pagina(items: Item[], total = items.length): Pagina {
  return { items, total, page: 1, page_size: 20 };
}

function ruta(url: string): { pathname: string; search: string } {
  const separador = url.indexOf("?");
  if (separador === -1) return { pathname: url, search: "" };
  return { pathname: url.slice(0, separador), search: url.slice(separador) };
}

let empresaServidor: Empresa = "emp-a";
const llamadasBusqueda: LlamadaBusqueda[] = [];

function configurarApi() {
  apiFetch.mockImplementation(async (url: string) => {
    const { pathname, search } = ruta(url);

    if (pathname === "/maestros/catalogos/items/search") {
      const q = new URLSearchParams(search).get("q") ?? "";
      llamadasBusqueda.push({ empresa: empresaServidor, q });

      if (empresaServidor === "emp-a") {
        return Promise.resolve(pagina([itemA]));
      }
      return Promise.resolve(pagina([itemB]));
    }

    if (pathname.startsWith("/maestros/catalogos/items/")) {
      if (empresaServidor === "emp-a") {
        return Promise.resolve({ code: "A-009", name: "Alfa nueve" });
      }
      return Promise.resolve({ code: "B-009", name: "Beta nueve" });
    }

    throw new Error(`URL inesperada: ${url}`);
  });
}

beforeEach(() => {
  apiFetch.mockReset();
  empresaServidor = "emp-a";
  empresaActiva = "emp-a";
  llamadasBusqueda.length = 0;
  configurarApi();
});

function crearCliente() {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });
}

function renderConCliente(cliente: QueryClient, ui: React.ReactElement) {
  return render(<QueryClientProvider client={cliente}>{ui}</QueryClientProvider>);
}

type ArnesProps = {
  scopeKey: string;
  value?: string | null;
  onValueChange?: (value: string | null) => void;
  resolveUrl?: string;
  mostrarValor?: boolean;
};

function Arnes({
  scopeKey,
  value: initialValue = null,
  onValueChange,
  resolveUrl = "/maestros/catalogos/items",
  mostrarValor = false,
}: ArnesProps) {
  const [value, setValue] = useState<string | null>(initialValue);

  return (
    <>
      <AsyncCombobox
        value={value}
        onChange={(next) => {
          setValue(next);
          onValueChange?.(next);
        }}
        searchUrl="/maestros/catalogos/items/search"
        resolveUrl={resolveUrl}
        scopeKey={scopeKey}
        label="Buscar artículo"
        placeholder="Buscar por código o nombre…"
        id="combobox-aislamiento"
      />
      {mostrarValor ? <output data-testid="valor">{value ?? ""}</output> : null}
    </>
  );
}

describe("AsyncCombobox: aislamiento de caché por empresa", () => {
  it("CACHE-01 mantiene la consulta separada al cambiar de empresa con la lista abierta", async () => {
    const user = userEvent.setup();
    const cliente = crearCliente();
    const { rerender } = renderConCliente(cliente, <Arnes scopeKey="emp-a" />);

    const input = screen.getByRole("combobox");
    await user.click(input);
    await user.type(input, "producto");

    expect(await screen.findByRole("option", { name: /A-001/ })).toBeInTheDocument();

    const bPendiente = diferido<Pagina>();
    apiFetch.mockImplementation(async (url: string) => {
      const { pathname, search } = ruta(url);
      if (pathname === "/maestros/catalogos/items/search") {
        const q = new URLSearchParams(search).get("q") ?? "";
        llamadasBusqueda.push({ empresa: empresaServidor, q });
        if (empresaServidor === "emp-a") return Promise.resolve(pagina([itemA]));
        return bPendiente.promise;
      }
      if (pathname.startsWith("/maestros/catalogos/items/")) {
        return Promise.resolve({ code: "B-009", name: "Beta nueve" });
      }
      throw new Error(`URL inesperada: ${url}`);
    });
    empresaServidor = "emp-b";

    rerender(
      <QueryClientProvider client={cliente}>
        <Arnes scopeKey="emp-b" />
      </QueryClientProvider>,
    );

    expect(screen.queryByRole("option", { name: /A-001/ })).toBeNull();
    expect(screen.getByText("Buscando…")).toBeInTheDocument();

    await waitFor(() => {
      expect(llamadasBusqueda.some((llamada) => llamada.empresa === "emp-b")).toBe(true);
    });

    await act(async () => {
      bPendiente.resolve(pagina([itemB]));
    });

    expect(await screen.findByRole("option", { name: /B-001/ })).toBeInTheDocument();
    expect(screen.queryByRole("option", { name: /A-001/ })).toBeNull();
  });

  it("CACHE-02 no reutiliza resultados de otra empresa al reabrir la lista", async () => {
    const user = userEvent.setup();
    const cliente = crearCliente();
    const { rerender } = renderConCliente(cliente, <Arnes scopeKey="emp-a" />);

    const input = screen.getByRole("combobox");
    await user.click(input);
    await user.type(input, "producto");

    expect(await screen.findByRole("option", { name: /A-001/ })).toBeInTheDocument();

    await user.click(document.body);

    const bPendiente = diferido<Pagina>();
    apiFetch.mockImplementation(async (url: string) => {
      const { pathname, search } = ruta(url);
      if (pathname === "/maestros/catalogos/items/search") {
        const q = new URLSearchParams(search).get("q") ?? "";
        llamadasBusqueda.push({ empresa: empresaServidor, q });
        if (empresaServidor === "emp-a") return Promise.resolve(pagina([itemA]));
        return bPendiente.promise;
      }
      if (pathname.startsWith("/maestros/catalogos/items/")) {
        return Promise.resolve({ code: "B-009", name: "Beta nueve" });
      }
      throw new Error(`URL inesperada: ${url}`);
    });
    empresaServidor = "emp-b";

    rerender(
      <QueryClientProvider client={cliente}>
        <Arnes scopeKey="emp-b" />
      </QueryClientProvider>,
    );

    await user.click(input);

    expect(screen.queryByRole("option", { name: /A-001/ })).toBeNull();

    await waitFor(() => {
      expect(llamadasBusqueda.some((llamada) => llamada.empresa === "emp-b")).toBe(true);
    });

    await act(async () => {
      bPendiente.resolve(pagina([itemB]));
    });

    expect(await screen.findByRole("option", { name: /B-001/ })).toBeInTheDocument();
  });

  it("CACHE-03 ignora una respuesta tardía de la empresa anterior", async () => {
    const user = userEvent.setup();
    const cliente = crearCliente();
    const aPendiente = diferido<Pagina>();
    apiFetch.mockImplementation(async (url: string) => {
      const { pathname, search } = ruta(url);
      if (pathname === "/maestros/catalogos/items/search") {
        const q = new URLSearchParams(search).get("q") ?? "";
        llamadasBusqueda.push({ empresa: empresaServidor, q });
        if (empresaServidor === "emp-a") return aPendiente.promise;
        return Promise.resolve(pagina([itemB]));
      }
      if (pathname.startsWith("/maestros/catalogos/items/")) {
        return Promise.resolve({ code: "B-009", name: "Beta nueve" });
      }
      throw new Error(`URL inesperada: ${url}`);
    });

    const { rerender } = renderConCliente(cliente, <Arnes scopeKey="emp-a" />);

    const input = screen.getByRole("combobox");
    await user.click(input);
    await user.type(input, "producto");

    await waitFor(() => {
      expect(
        llamadasBusqueda.some(
          (llamada) => llamada.empresa === "emp-a" && llamada.q === "producto",
        ),
      ).toBe(true);
    });

    empresaServidor = "emp-b";

    rerender(
      <QueryClientProvider client={cliente}>
        <Arnes scopeKey="emp-b" />
      </QueryClientProvider>,
    );

    expect(await screen.findByRole("option", { name: /B-001/ })).toBeInTheDocument();

    await act(async () => {
      aPendiente.resolve(pagina([itemA]));
    });

    expect(screen.queryByRole("option", { name: /A-001/ })).toBeNull();
    expect(screen.getByRole("option", { name: /B-001/ })).toBeInTheDocument();
  });

  it("CACHE-04 limpia la selección al cambiar de empresa", async () => {
    const user = userEvent.setup();
    const cliente = crearCliente();
    const alCambiar = vi.fn();
    const { rerender } = renderConCliente(
      cliente,
      <Arnes scopeKey="emp-a" onValueChange={alCambiar} mostrarValor />,
    );

    const input = screen.getByRole("combobox");
    await user.click(input);
    await user.type(input, "A-001");

    const opcionA = await screen.findByRole("option", { name: /A-001/ });
    await user.click(opcionA);

    expect(input).toHaveValue("A-001 · Alfa");
    expect(screen.getByTestId("valor")).toHaveTextContent("a-1");

    const llamadasConA = alCambiar.mock.calls.filter(([value]) => value === "a-1").length;

    await act(async () => {
      rerender(
        <QueryClientProvider client={cliente}>
          <Arnes scopeKey="emp-b" onValueChange={alCambiar} mostrarValor />
        </QueryClientProvider>,
      );
    });

    await waitFor(() => {
      expect(screen.getByTestId("valor")).toHaveTextContent("");
      expect(input).toHaveValue("");
    });

    const ultimaLlamada = alCambiar.mock.calls.at(-1);
    expect(ultimaLlamada?.[0]).toBeNull();
    expect(alCambiar.mock.calls.filter(([value]) => value === "a-1")).toHaveLength(llamadasConA);
  });

  it("CACHE-05 aísla la resolución inicial por empresa compartiendo QueryClient", async () => {
    const cliente = crearCliente();

    const montajeUno = renderConCliente(
      cliente,
      <Arnes scopeKey="emp-a" value="x-1" />,
    );

    const inputUno = screen.getByRole("combobox");
    expect(await screen.findByDisplayValue("A-009 · Alfa nueve")).toBeInTheDocument();
    expect(inputUno).toHaveValue("A-009 · Alfa nueve");

    montajeUno.unmount();

    const bPendiente = diferido<{ code: string; name: string }>();
    apiFetch.mockImplementation(async (url: string) => {
      const { pathname } = ruta(url);
      if (pathname === "/maestros/catalogos/items/search") {
        return Promise.resolve(pagina([]));
      }
      if (pathname.startsWith("/maestros/catalogos/items/")) {
        if (empresaServidor === "emp-a") {
          return Promise.resolve({ code: "A-009", name: "Alfa nueve" });
        }
        return bPendiente.promise;
      }
      throw new Error(`URL inesperada: ${url}`);
    });
    empresaServidor = "emp-b";

    renderConCliente(cliente, <Arnes scopeKey="emp-b" value="x-1" />);

    const inputDos = screen.getByRole("combobox");
    expect(inputDos).toHaveValue("");

    await act(async () => {
      bPendiente.resolve({ code: "B-009", name: "Beta nueve" });
    });

    expect(await screen.findByDisplayValue("B-009 · Beta nueve")).toBeInTheDocument();
    expect(inputDos).toHaveValue("B-009 · Beta nueve");
  });

  it("CACHE-06 SelectorDeArticulo usa la empresa activa como scopeKey", async () => {
    const user = userEvent.setup();
    const cliente = crearCliente();

    function ArnesSelector() {
      const [value, setValue] = useState("");
      return (
        <>
          <label htmlFor="sel">Producto</label>
          <SelectorDeArticulo id="sel" value={value} onChange={setValue} />
        </>
      );
    }

    const { rerender } = renderConCliente(cliente, <ArnesSelector />);

    const input = screen.getByRole("combobox");
    await user.click(input);
    await user.type(input, "producto");

    expect(await screen.findByRole("option", { name: /A-001/ })).toBeInTheDocument();

    const bPendiente = diferido<Pagina>();
    apiFetch.mockImplementation(async (url: string) => {
      const { pathname, search } = ruta(url);
      if (pathname === "/maestros/catalogos/items/search") {
        const q = new URLSearchParams(search).get("q") ?? "";
        llamadasBusqueda.push({ empresa: empresaServidor, q });
        if (empresaServidor === "emp-a") return Promise.resolve(pagina([itemA]));
        return bPendiente.promise;
      }
      if (pathname.startsWith("/maestros/catalogos/items/")) {
        return Promise.resolve({ code: "B-009", name: "Beta nueve" });
      }
      throw new Error(`URL inesperada: ${url}`);
    });
    empresaServidor = "emp-b";
    empresaActiva = "emp-b";

    rerender(
      <QueryClientProvider client={cliente}>
        <ArnesSelector />
      </QueryClientProvider>,
    );

    expect(screen.queryByRole("option", { name: /A-001/ })).toBeNull();

    await waitFor(() => {
      expect(llamadasBusqueda.some((llamada) => llamada.empresa === "emp-b")).toBe(true);
    });

    await act(async () => {
      bPendiente.resolve(pagina([itemB]));
    });

    expect(await screen.findByRole("option", { name: /B-001/ })).toBeInTheDocument();
    expect(screen.queryByRole("option", { name: /A-001/ })).toBeNull();
  });
});
