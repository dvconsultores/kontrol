import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { createMemoryRouter, RouterProvider } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";

const apiFetch = vi.fn();

vi.mock("@/api/client", async (original) => ({
  ...(await original<typeof import("@/api/client")>()),
  apiFetch: (...args: unknown[]) => apiFetch(...args),
}));

vi.mock("@/app/contexts/NotificationContext", () => ({
  useNotifications: () => ({ notify: vi.fn() }),
}));

vi.mock("@/app/autoridad/AutoridadContext", () => ({
  useAutoridad: () => ({
    estado: "LISTA",
    tiene: () => true,
    puede: () => true,
    motivo: () => null,
    motivoDeCapacidad: () => null,
  }),
}));

const { ProductoNuevoPage } = await import("@/modules/maestros/productos/ProductoNuevoPage");

const RUBRO = {
  id: "3f2b8c1e-0000-4000-8000-00000000abcd",
  code: "R-01",
  name: "Alimentos",
  level: 1,
};

function taxonomiaResponse(query: string) {
  const q = query.toLowerCase();
  const matches = [RUBRO].filter(
    (item) =>
      item.code.toLowerCase().includes(q) || item.name.toLowerCase().includes(q),
  );

  return {
    items: matches,
    total: matches.length,
    page: 1,
    page_size: 20,
  };
}

function mockSearchSuccess() {
  apiFetch.mockImplementation(async (path: string) => {
    if (path.startsWith("/maestros/catalogos/taxonomia/search")) {
      const url = new URL(path, "http://k");
      return taxonomiaResponse(url.searchParams.get("q") ?? "");
    }

    return {};
  });
}

function createQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
      mutations: {
        retry: false,
      },
    },
  });
}

function renderPage() {
  const router = createMemoryRouter(
    [
      {
        path: "/maestros/productos/nuevo",
        element: <ProductoNuevoPage />,
      },
      {
        path: "/maestros/productos",
        element: <p>Listado de productos</p>,
      },
    ],
    {
      initialEntries: ["/maestros/productos/nuevo"],
    },
  );

  const queryClient = createQueryClient();

  render(
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  );

  return { queryClient };
}

async function fillRequiredFields(user: ReturnType<typeof userEvent.setup>) {
  await user.type(screen.getByLabelText(/^Código/), "P-100");
  await user.type(screen.getByLabelText(/^Nombre/), "Arroz");
}

async function chooseRubro(user: ReturnType<typeof userEvent.setup>) {
  const rubro = screen.getByRole("combobox", { name: /^Rubro/ });
  await user.type(rubro, "Ali");
  const option = await screen.findByRole("option", { name: /Alimentos.*R-01|R-01.*Alimentos/ });
  await user.click(option);
}

function postCalls() {
  return apiFetch.mock.calls.filter(
    ([path, options]) =>
      path === "/maestros/catalogos/items" &&
      options &&
      typeof options === "object" &&
      "method" in options &&
      options.method === "POST",
  );
}

describe("ProductoNuevoPage — contrato del Rubro con AsyncCombobox", () => {
  beforeEach(() => {
    apiFetch.mockReset();
  });

  it("PN-01 renderiza los campos Código, Nombre y Rubro", async () => {
    mockSearchSuccess();
    renderPage();

    expect(screen.getByLabelText(/^Código/)).toBeInTheDocument();
    expect(screen.getByLabelText(/^Nombre/)).toBeInTheDocument();
    expect(screen.getByRole("combobox", { name: /^Rubro/ })).toBeInTheDocument();
  });

  it("PN-02 buscar en Rubro muestra la opción y llama al endpoint de búsqueda con los parámetros correctos", async () => {
    mockSearchSuccess();
    renderPage();

    const user = userEvent.setup();
    const rubro = screen.getByRole("combobox", { name: /^Rubro/ });

    await user.type(rubro, "Ali");

    const option = await screen.findByRole("option", { name: /Alimentos.*R-01|R-01.*Alimentos/ });
    expect(option).toBeInTheDocument();

    const searchCall = await waitFor(() => {
      const called = apiFetch.mock.calls.find(([path]) => {
        if (!String(path).startsWith("/maestros/catalogos/taxonomia/search")) {
          return false;
        }
        const url = new URL(String(path), "http://k");
        return url.searchParams.get("q") === "Ali";
      });

      expect(called).toBeDefined();
      return called;
    });

    const url = new URL(String(searchCall?.[0]), "http://k");
    expect(url.searchParams.get("q")).toBe("Ali");
    expect(url.searchParams.get("page")).toBe("1");
    expect(url.searchParams.get("page_size")).toBe("20");

    const allSearchPaths = apiFetch.mock.calls
      .map(([path]) => String(path))
      .filter((path) => path.startsWith("/maestros/catalogos/taxonomia/search"));

    for (const path of allSearchPaths) {
      const searchUrl = new URL(path, "http://k");
      expect(searchUrl.searchParams.get("page_size")).toBe("20");
    }
  });

  it("PN-03 elegir Rubro muestra la etiqueta legible y no expone el id", async () => {
    mockSearchSuccess();
    renderPage();

    const user = userEvent.setup();
    await chooseRubro(user);

    const rubro = screen.getByRole("combobox", { name: /^Rubro/ });
    expect(rubro).toHaveValue("R-01 · Alimentos");
    expect(rubro).not.toHaveValue(RUBRO.id);
  });

  it("PN-04 guarda el producto con el Rubro elegido y navega al listado", async () => {
    apiFetch.mockImplementation(async (path: string) => {
      if (path.startsWith("/maestros/catalogos/taxonomia/search")) {
        const url = new URL(path, "http://k");
        return taxonomiaResponse(url.searchParams.get("q") ?? "");
      }

      if (path === "/maestros/catalogos/items") {
        return { id: "nuevo-1" };
      }

      return {};
    });

    renderPage();

    const user = userEvent.setup();
    await fillRequiredFields(user);
    await chooseRubro(user);

    await user.click(screen.getByRole("button", { name: "Siguiente" }));
    await user.click(screen.getByRole("button", { name: "Siguiente" }));
    await user.click(screen.getByRole("button", { name: "Siguiente" }));
    await user.click(screen.getByRole("button", { name: "Guardar producto" }));

    const posts = await waitFor(() => {
      const calls = postCalls();
      expect(calls.length).toBeGreaterThan(0);
      return calls;
    });

    for (const postCall of posts) {
      const options = postCall[1] as { body: Record<string, unknown> };
      expect(options.body).toMatchObject({
        code: "P-100",
        name: "Arroz",
        item_type: "PRODUCT",
        category_id: RUBRO.id,
      });
    }
  });

  it("PN-05 muestra el alert de error de búsqueda y permite continuar con el asistente", async () => {
    apiFetch.mockImplementation(async (path: string) => {
      if (path.startsWith("/maestros/catalogos/taxonomia/search")) {
        throw new Error("fallo");
      }

      return {};
    });

    renderPage();

    const user = userEvent.setup();
    const rubro = screen.getByRole("combobox", { name: /^Rubro/ });

    await user.type(rubro, "Ali");

    expect(await screen.findByText("No fue posible completar la búsqueda")).toBeInTheDocument();

    await fillRequiredFields(user);
    expect(screen.queryByLabelText(/^Código/)).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Siguiente" }));

    await waitFor(() => {
      expect(screen.queryByLabelText(/^Código/)).not.toBeInTheDocument();
    });

    expect(screen.getByText("2. Datos fiscales")).toHaveClass("bg-brand-600");
  });

  it("PN-06 sin resultados muestra mensaje vacío y el POST lleva category_id null", async () => {
    apiFetch.mockImplementation(async (path: string) => {
      if (path.startsWith("/maestros/catalogos/taxonomia/search")) {
        return {
          items: [],
          total: 0,
          page: 1,
          page_size: 20,
        };
      }

      if (path === "/maestros/catalogos/items") {
        return { id: "nuevo-1" };
      }

      return {};
    });

    renderPage();

    const user = userEvent.setup();
    await fillRequiredFields(user);

    const rubro = screen.getByRole("combobox", { name: /^Rubro/ });
    await user.type(rubro, "NoExiste");

    expect(await screen.findByText("Sin resultados")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Siguiente" }));
    await user.click(screen.getByRole("button", { name: "Siguiente" }));
    await user.click(screen.getByRole("button", { name: "Siguiente" }));
    await user.click(screen.getByRole("button", { name: "Guardar producto" }));

    const posts = await waitFor(() => {
      const calls = postCalls();
      expect(calls.length).toBeGreaterThan(0);
      return calls;
    });

    for (const postCall of posts) {
      const options = postCall[1] as { body: Record<string, unknown> };
      expect(options.body).toMatchObject({
        code: "P-100",
        name: "Arroz",
        item_type: "PRODUCT",
        category_id: null,
      });
    }
  });

  it("PN-07 no envía item_type en búsqueda, no resuelve el id y limpiar el campo anula category_id", async () => {
    const paths: string[] = [];

    apiFetch.mockImplementation(async (path: string) => {
      paths.push(path);

      if (path.startsWith("/maestros/catalogos/taxonomia/search")) {
        const url = new URL(path, "http://k");
        return taxonomiaResponse(url.searchParams.get("q") ?? "");
      }

      if (path === "/maestros/catalogos/items") {
        return { id: "nuevo-1" };
      }

      return {};
    });

    renderPage();

    const user = userEvent.setup();
    await fillRequiredFields(user);
    await chooseRubro(user);

    const rubro = screen.getByRole("combobox", { name: /^Rubro/ });
    await user.clear(rubro);
    await user.type(rubro, "X");

    await waitFor(() => {
      const searchPaths = paths.filter((path) =>
        path.startsWith("/maestros/catalogos/taxonomia/search"),
      );
      expect(
        searchPaths.some((path) => {
          const url = new URL(path, "http://k");
          return url.searchParams.get("q") === "X";
        }),
      ).toBe(true);
    });

    const searchPaths = paths.filter((path) =>
      path.startsWith("/maestros/catalogos/taxonomia/search"),
    );

    for (const path of searchPaths) {
      const url = new URL(path, "http://k");
      expect(url.searchParams.has("item_type")).toBe(false);
    }

    expect(
      paths.some(
        (path) =>
          path.startsWith("/maestros/catalogos/taxonomia/") &&
          !path.startsWith("/maestros/catalogos/taxonomia/search"),
      ),
    ).toBe(false);
    expect(paths.some((path) => path.startsWith("/maestros/catalogos/items/"))).toBe(false);

    await user.click(screen.getByRole("button", { name: "Siguiente" }));
    await user.click(screen.getByRole("button", { name: "Siguiente" }));
    await user.click(screen.getByRole("button", { name: "Siguiente" }));
    await user.click(screen.getByRole("button", { name: "Guardar producto" }));

    const posts = await waitFor(() => {
      const calls = postCalls();
      expect(calls.length).toBeGreaterThan(0);
      return calls;
    });

    for (const postCall of posts) {
      const options = postCall[1] as { body: Record<string, unknown> };
      expect(options.body).toMatchObject({
        code: "P-100",
        name: "Arroz",
        item_type: "PRODUCT",
        category_id: null,
      });
    }
  });
});
