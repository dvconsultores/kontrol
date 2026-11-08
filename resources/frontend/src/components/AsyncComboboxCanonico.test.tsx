/** AsyncCombobox: búsqueda en servidor sin truncado y selección legible (FR-002-043). */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { apiFetch } from "@/api/client";
import { AsyncCombobox } from "./AsyncCombobox";

vi.mock("@/api/client", () => ({
  apiFetch: vi.fn(),
}));

const llamar = vi.mocked(apiFetch);

type OpcionesServidor = {
  total?: number;
  fallaPagina?: number;
  fallaTodo?: boolean;
};

type ItemServidor = {
  id: string;
  code: string;
  name: string;
  item_type: "PRODUCT" | "SERVICE";
};

function servidor(opciones: OpcionesServidor = {}): void {
  const total = opciones.total ?? 25;
  const universo: ItemServidor[] = Array.from({ length: total }, (_, indice) => {
    const n = indice + 1;
    return {
      id: `id-${n}`,
      code: `P-${String(n).padStart(3, "0")}`,
      name: `Artículo ${n}`,
      item_type: "PRODUCT",
    };
  });

  llamar.mockImplementation((ruta: string) => {
    const url = new URL(ruta, "http://k");
    if (url.pathname === "/maestros/catalogos/items/search") {
      if (opciones.fallaTodo === true) {
        return Promise.reject(new Error("fallo simulado"));
      }
      const page = Number(url.searchParams.get("page"));
      if (opciones.fallaPagina !== undefined && page === opciones.fallaPagina) {
        return Promise.reject(new Error("fallo simulado"));
      }
      const q = url.searchParams.get("q") ?? "";
      const filtrados = universo.filter(
        (item) => item.code.includes(q) || item.name.includes(q),
      );
      const inicio = (page - 1) * 20;
      return Promise.resolve({
        items: filtrados.slice(inicio, inicio + 20),
        total: filtrados.length,
        page,
        page_size: 20,
      });
    }
    if (url.pathname.startsWith("/maestros/catalogos/items/")) {
      const partes = url.pathname.split("/");
      const id = partes[partes.length - 1];
      return Promise.resolve({ id, code: "P-077", name: "Artículo 77" });
    }
    return Promise.resolve({ items: [], total: 0, page: 1, page_size: 20 });
  });
}

type PropsCombobox = Parameters<typeof AsyncCombobox>[0];

function montar(
  props: Partial<PropsCombobox> = {},
  alCambiar: ReturnType<typeof vi.fn> = vi.fn(),
): {
  alCambiar: ReturnType<typeof vi.fn>;
  rerender: (nuevas: Partial<PropsCombobox>) => void;
} {
  const consultas = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  const { value: valorInicial, ...resto } = props;

  function Prueba(actuales: Partial<PropsCombobox>) {
    const [valor, setValor] = useState<string | null>(
      actuales.value ?? valorInicial ?? null,
    );
    return (
      <QueryClientProvider client={consultas}>
        <label htmlFor="campo">Producto</label>
        <AsyncCombobox
          searchUrl="/maestros/catalogos/items/search"
          {...resto}
          {...actuales}
          id="campo"
          value={valor}
          onChange={(v, item) => {
            setValor(v);
            alCambiar(v, item);
          }}
        />
      </QueryClientProvider>
    );
  }

  const resultado = render(<Prueba {...props} />);
  return {
    alCambiar,
    rerender: (nuevas: Partial<PropsCombobox>) => {
      resultado.rerender(<Prueba {...nuevas} />);
    },
  };
}

const rutas = (): string[] => llamar.mock.calls.map((c) => String(c[0]));

function opcionPorCodigo(codigo: string): HTMLElement {
  const opciones = screen
    .getAllByRole("option")
    .filter(
      (opcion) =>
        (opcion.textContent ?? "").includes(codigo) ||
        (opcion.getAttribute("aria-label") ?? "").includes(codigo),
    );
  if (opciones.length === 0) {
    throw new Error(`No hay opción con código ${codigo}`);
  }
  return opciones[0];
}

describe("AsyncCombobox canónico", () => {
  beforeEach(() => {
    llamar.mockReset();
  });

  it("CC-01 busca por código", async () => {
    servidor();
    const user = userEvent.setup();
    montar();
    await user.type(
      screen.getByRole("combobox", { name: "Producto" }),
      "P-025",
    );
    await screen.findByRole("option", { name: /Artículo 25/ });
  });

  it("CC-02 busca por nombre", async () => {
    servidor();
    const user = userEvent.setup();
    montar();
    await user.type(
      screen.getByRole("combobox", { name: "Producto" }),
      "Artículo 7",
    );
    await screen.findByRole("option", { name: /Artículo 7/ });
  });

  it("CC-03 CC-04 más de 20 coincidencias no se truncan", async () => {
    servidor();
    const user = userEvent.setup();
    montar();
    await user.click(screen.getByRole("combobox", { name: "Producto" }));
    await screen.findByText("Mostrando 20 de 25");
    expect(
      screen.queryByRole("option", { name: /Artículo 25/ }),
    ).toBeNull();
    await user.click(
      screen.getByRole("button", { name: "Cargar más resultados" }),
    );
    await screen.findByRole("option", { name: /Artículo 25/ });
  });

  it("CC-05 más de 100 siguen alcanzables", async () => {
    servidor({ total: 130 });
    const user = userEvent.setup();
    montar();
    await user.click(screen.getByRole("combobox", { name: "Producto" }));
    for (let i = 0; i < 6; i += 1) {
      await screen.findByText(`Mostrando ${20 * (i + 1)} de 130`);
      await user.click(
        screen.getByRole("button", { name: "Cargar más resultados" }),
      );
    }
    await screen.findByRole("option", { name: /Artículo 130/ });
  });

  it("CC-06 CC-07 CC-08 elegir muestra código y nombre y devuelve el id", async () => {
    servidor();
    const user = userEvent.setup();
    const { alCambiar } = montar();
    await user.type(
      screen.getByRole("combobox", { name: "Producto" }),
      "P-003",
    );
    await user.click(opcionPorCodigo("P-003"));
    expect(alCambiar).toHaveBeenCalled();
    const [primerArgumento, segundoArgumento] = alCambiar.mock.calls[0];
    expect(primerArgumento).toBe("id-3");
    expect(typeof segundoArgumento).toBe("object");
    const combobox = screen.getByRole("combobox", { name: "Producto" });
    expect((combobox as HTMLInputElement).value).toBe("P-003 · Artículo 3");
    expect((combobox as HTMLInputElement).value).not.toContain("id-");
  });

  it("CC-09 un id inicial se muestra con su etiqueta", async () => {
    servidor();
    const user = userEvent.setup();
    void user;
    montar({
      value: "id-77",
      resolveUrl: "/maestros/catalogos/items",
    });
    const combobox = screen.getByRole("combobox", { name: "Producto" });
    expect((combobox as HTMLInputElement).value).not.toContain("id-");
    await waitFor(() => {
      expect((combobox as HTMLInputElement).value).toBe(
        "P-077 · Artículo 77",
      );
    });
  });

  it("CC-10 estado de carga", async () => {
    llamar.mockImplementation(
      () => new Promise(() => undefined),
    );
    const user = userEvent.setup();
    montar();
    await user.click(screen.getByRole("combobox", { name: "Producto" }));
    const estado = await screen.findByText("Buscando…");
    expect(estado.getAttribute("role")).toBe("status");
  });

  it("CC-11 sin resultados", async () => {
    servidor();
    const user = userEvent.setup();
    montar();
    await user.type(
      screen.getByRole("combobox", { name: "Producto" }),
      "ZZZ",
    );
    await screen.findByText("Sin resultados");
  });

  it("CC-12 error", async () => {
    servidor({ fallaTodo: true });
    const user = userEvent.setup();
    montar();
    await user.click(screen.getByRole("combobox", { name: "Producto" }));
    const alerta = await screen.findByText(
      "No fue posible completar la búsqueda",
    );
    expect(alerta.getAttribute("role")).toBe("alert");
  });

  it("CC-12b el fallo de una página posterior no pasa por completo", async () => {
    servidor({ fallaPagina: 2 });
    const user = userEvent.setup();
    montar();
    await user.click(screen.getByRole("combobox", { name: "Producto" }));
    await screen.findByText("Mostrando 20 de 25");
    await user.click(
      screen.getByRole("button", { name: "Cargar más resultados" }),
    );
    const alerta = await screen.findByText(
      "No fue posible cargar más resultados",
    );
    expect(alerta.getAttribute("role")).toBe("alert");
    expect(opcionPorCodigo("P-001")).toBeTruthy();
  });

  it("CC-13 cambiar la búsqueda no mezcla resultados", async () => {
    servidor();
    const user = userEvent.setup();
    montar();
    await user.click(screen.getByRole("combobox", { name: "Producto" }));
    await screen.findByText("Mostrando 20 de 25");
    await user.click(
      screen.getByRole("button", { name: "Cargar más resultados" }),
    );
    await screen.findByRole("option", { name: /Artículo 25/ });
    const combobox = screen.getByRole("combobox", { name: "Producto" });
    await user.clear(combobox);
    await user.type(combobox, "P-002");
    await screen.findByRole("option", { name: /Artículo 2/ });
    expect(
      screen.queryByRole("option", { name: /Artículo 25/ }),
    ).toBeNull();
    const llamadas = rutas();
    const ultima = llamadas[llamadas.length - 1];
    expect(ultima).toContain("q=P-002");
    expect(ultima).toContain("page=1");
  });

  it("CC-14 cambiar de empresa invalida la selección", async () => {
    servidor();
    const user = userEvent.setup();
    const { alCambiar, rerender } = montar({ scopeKey: "emp-a" });
    await user.type(
      screen.getByRole("combobox", { name: "Producto" }),
      "P-003",
    );
    await user.click(opcionPorCodigo("P-003"));
    expect(alCambiar).toHaveBeenCalledWith("id-3", expect.anything());
    rerender({ scopeKey: "emp-b" });
    await waitFor(() => {
      const llamadas = alCambiar.mock.calls;
      const ultima = llamadas[llamadas.length - 1];
      expect(ultima[0]).toBeNull();
    });
  });

  it("CC-15 filtra PRODUCT", async () => {
    servidor();
    const user = userEvent.setup();
    montar({ itemType: "PRODUCT" });
    await user.click(screen.getByRole("combobox", { name: "Producto" }));
    await waitFor(() => {
      expect(rutas().length).toBeGreaterThan(0);
    });
    expect(rutas().some((ruta) => ruta.includes("item_type=PRODUCT"))).toBe(
      true,
    );
  });

  it("CC-16 filtra SERVICE", async () => {
    servidor();
    const user = userEvent.setup();
    montar({ itemType: "SERVICE" });
    await user.click(screen.getByRole("combobox", { name: "Producto" }));
    await waitFor(() => {
      expect(rutas().length).toBeGreaterThan(0);
    });
    expect(rutas().some((ruta) => ruta.includes("item_type=SERVICE"))).toBe(
      true,
    );
  });

  it("CC-17 sin tipo no filtra", async () => {
    servidor();
    const user = userEvent.setup();
    montar();
    await user.click(screen.getByRole("combobox", { name: "Producto" }));
    await waitFor(() => {
      expect(rutas().length).toBeGreaterThan(0);
    });
    expect(rutas().some((ruta) => ruta.includes("item_type"))).toBe(false);
  });

  it("CC-18 se elige con teclado", async () => {
    servidor();
    const user = userEvent.setup();
    const { alCambiar } = montar();
    await user.type(
      screen.getByRole("combobox", { name: "Producto" }),
      "P-004",
    );
    await waitFor(() => {
      expect(screen.getAllByRole("option")).toHaveLength(1);
    });
    const opcion = opcionPorCodigo("P-004");
    let intentos = 0;
    while (!opcion.contains(document.activeElement) && intentos < 5) {
      await user.tab();
      intentos += 1;
    }
    expect(opcion.contains(document.activeElement)).toBe(true);
    await user.keyboard("{Enter}");
    await waitFor(() => {
      const llamadas = alCambiar.mock.calls;
      const ultima = llamadas[llamadas.length - 1];
      expect(ultima[0]).toBe("id-4");
    });
  });

  it("CC-19 el nombre accesible viene de la etiqueta", async () => {
    servidor();
    const user = userEvent.setup();
    montar();
    const combobox = screen.getByRole("combobox", { name: "Producto" });
    await user.click(combobox);
    await screen.findByRole("listbox");
    const controles = combobox.getAttribute("aria-controls");
    expect(controles).toBeTruthy();
    const listbox = document.getElementById(controles ?? "");
    expect(listbox).not.toBeNull();
    expect(listbox?.getAttribute("role")).toBe("listbox");
  });

  it("CC-20 Escape cierra la lista", async () => {
    servidor();
    const user = userEvent.setup();
    montar();
    await user.click(screen.getByRole("combobox", { name: "Producto" }));
    await screen.findByRole("listbox");
    await user.keyboard("{Escape}");
    await waitFor(() => {
      expect(screen.queryByRole("listbox")).toBeNull();
    });
  });
});
