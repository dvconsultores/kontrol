/** Selectores de catálogo: cobertura de mutantes supervivientes del selector canónico de artículos. */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ComponentType } from "react";
import { useState } from "react";
import { MemoryRouter } from "react-router";
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
vi.mock("@/app/contexts/NotificationContext", () => ({
  useNotifications: () => ({ notify: vi.fn() }),
}));
vi.mock("@/app/autoridad/AutoridadContext", () => ({
  useAutoridad: () => ({ estado: "LISTA", tiene: () => true, puede: () => true, motivo: () => null, motivoDeCapacidad: () => null }),
}));

const { AsyncCombobox } = await import("@/components/AsyncCombobox");
const { SelectorDeArticulo } = await import("@/modules/maestros/catalogo/SelectorDeArticulo");
const { OrdenesVentasPage } = await import("@/modules/ventas/ordenes/OrdenesVentasPage");

type Item = { id: string; code: string; name: string };
const articulos: Item[] = Array.from({ length: 5 }, (_, n) => ({
  id: `id-${n + 1}`,
  code: `P-00${n + 1}`,
  name: `Artículo ${n + 1}`,
}));

function respuestaBusqueda(items: Item[]) {
  return { items, total: items.length, page: 1, page_size: 20, limit: 50, offset: 0 };
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

beforeEach(() => {
  apiFetch.mockReset();
  empresaActiva = "emp-a";
});

describe("Selector de artículos: mutantes supervivientes", () => {
  it("S-04: la clave de búsqueda incluye el scopeKey activo", async () => {
    const usuario = userEvent.setup();
    let empresaServidor = "emp-a";
    apiFetch.mockImplementation(async (url: string) => {
      if (String(url).includes("/maestros/catalogos/items/search")) {
        return empresaServidor === "emp-a"
          ? respuestaBusqueda([{ id: "a-1", code: "A-001", name: "Alfa" }])
          : respuestaBusqueda([{ id: "b-1", code: "B-001", name: "Beta" }]);
      }
      return { items: [], total: 0, page: 1, page_size: 20, limit: 50, offset: 0 };
    });

    function Pagina({ scopeKey }: { scopeKey: string }) {
      const [valor, setValor] = useState<string | null>(null);
      return (
        <AsyncCombobox
          value={valor}
          onChange={setValor}
          searchUrl="/maestros/catalogos/items/search"
          scopeKey={scopeKey}
        />
      );
    }

    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    const resultado = render(
      <QueryClientProvider client={queryClient}>
        <Pagina scopeKey="emp-a" />
      </QueryClientProvider>,
    );
    const campo = screen.getByRole("combobox");
    await usuario.click(campo);
    await screen.findByRole("option", { name: /A-001/ });
    await usuario.click(document.body);

    empresaServidor = "emp-b";
    resultado.rerender(
      <QueryClientProvider client={queryClient}>
        <Pagina scopeKey="emp-b" />
      </QueryClientProvider>,
    );

    await usuario.click(screen.getByRole("combobox"));
    expect(screen.queryByRole("option", { name: /A-001/ })).toBeNull();
    await screen.findByRole("option", { name: /B-001/ });
  });

  it("S-07: la etiqueta mostrada sigue estando atada al id actual", async () => {
    const usuario = userEvent.setup();
    apiFetch.mockImplementation(async (url: string) => {
      const u = String(url);
      if (u.includes("/maestros/catalogos/items/search")) {
        return respuestaBusqueda(articulos);
      }
      if (u.includes("/maestros/catalogos/items/id-9")) {
        return new Promise(() => {});
      }
      return { items: [], total: 0, page: 1, page_size: 20, limit: 50, offset: 0 };
    });

    function Pagina() {
      const [valor, setValor] = useState<string | null>(null);
      return (
        <>
          <AsyncCombobox
            value={valor}
            onChange={setValor}
            searchUrl="/maestros/catalogos/items/search"
            resolveUrl="/maestros/catalogos/items"
          />
          <button type="button" onClick={() => setValor("id-9")}>
            Fijar id-9
          </button>
        </>
      );
    }

    montar(Pagina);
    const campo = screen.getByRole("combobox");
    await usuario.click(campo);
    await usuario.type(campo, "P-003");
    await usuario.click(await screen.findByRole("option", { name: /P-003/ }));
    expect(campo).toHaveValue("P-003 · Artículo 3");

    await usuario.click(screen.getByRole("button", { name: "Fijar id-9" }));
    await waitFor(() => expect(campo).toHaveValue(""));
  });

  it("S-13: escribir tras elegir limpia el valor", async () => {
    const usuario = userEvent.setup();
    apiFetch.mockImplementation(async (url: string) => {
      if (String(url).includes("/maestros/catalogos/items/search")) {
        return respuestaBusqueda(articulos);
      }
      return { items: [], total: 0, page: 1, page_size: 20, limit: 50, offset: 0 };
    });
    const alCambiar = vi.fn();

    function Pagina() {
      const [valor, setValor] = useState<string | null>(null);
      return (
        <AsyncCombobox
          value={valor}
          onChange={(v) => {
            setValor(v);
            alCambiar(v);
          }}
          searchUrl="/maestros/catalogos/items/search"
        />
      );
    }

    montar(Pagina);
    const campo = screen.getByRole("combobox");
    await usuario.click(campo);
    await usuario.type(campo, "P-003");
    await usuario.click(await screen.findByRole("option", { name: /P-003/ }));
    expect(alCambiar).toHaveBeenLastCalledWith("id-3");

    await usuario.type(campo, "x");
    expect(alCambiar).toHaveBeenLastCalledWith(null);
  });

  it("S-14: el SelectorDeArticulo usa la empresa activa como scopeKey", async () => {
    const usuario = userEvent.setup();
    apiFetch.mockImplementation(async (url: string) => {
      if (String(url).includes("/maestros/catalogos/items/search")) {
        return respuestaBusqueda(articulos);
      }
      return { items: [], total: 0, page: 1, page_size: 20, limit: 50, offset: 0 };
    });
    const espia = vi.fn();

    function Pagina() {
      const [v, setV] = useState("");
      return (
        <>
          <label htmlFor="sel">Producto</label>
          <SelectorDeArticulo
            id="sel"
            value={v}
            onChange={(x) => {
              setV(x);
              espia(x);
            }}
          />
          <output data-testid="valor">{v}</output>
        </>
      );
    }

    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    const resultado = render(
      <QueryClientProvider client={queryClient}>
        <Pagina />
      </QueryClientProvider>,
    );
    const campo = await screen.findByRole("combobox", { name: /Producto/ });
    await usuario.click(campo);
    await usuario.type(campo, "P-003");
    await usuario.click(await screen.findByRole("option", { name: /P-003/ }));
    await waitFor(() => expect(screen.getByTestId("valor").textContent).toBe("id-3"));

    empresaActiva = "emp-b";
    resultado.rerender(
      <QueryClientProvider client={queryClient}>
        <Pagina />
      </QueryClientProvider>,
    );
    await waitFor(() => expect(screen.getByTestId("valor").textContent).toBe(""));
  });

  it("S-17: en OrdenesVentasPage, cambiar de producto reinicia la presentación", async () => {
    const usuario = userEvent.setup();
    apiFetch.mockImplementation(async (url: string) => {
      const u = String(url);
      if (u.includes("/maestros/catalogos/items/search")) {
        return respuestaBusqueda(articulos);
      }
      if (u.match(/\/maestros\/productos\/[^/]+\/presentaciones/)) {
        return [{ id: "pr-1", code: "CJ", name: "Caja" }];
      }
      return { items: [], total: 0, page: 1, page_size: 20, limit: 50, offset: 0 };
    });

    montar(OrdenesVentasPage);

    const campo = await screen.findByRole("combobox", { name: /^Producto/ });
    await usuario.click(campo);
    await usuario.type(campo, "P-001");
    await usuario.click(await screen.findByRole("option", { name: /P-001/ }));

    const presentacion = screen.getByRole("combobox", { name: /^Presentación/ });
    await screen.findByRole("option", { name: "CJ · Caja" });
    await usuario.selectOptions(presentacion, "pr-1");
    expect(presentacion).toHaveValue("pr-1");

    await usuario.clear(campo);
    await usuario.type(campo, "P-002");
    await usuario.click(await screen.findByRole("option", { name: /P-002/ }));
    await screen.findByRole("option", { name: "CJ · Caja" });
    expect(presentacion).toHaveValue("");
  });
});
