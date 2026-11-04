import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";

const apiFetchMock = vi.fn();
const notifyMock = vi.fn();

vi.mock("@/api/client", async (original) => ({
  ...(await original<typeof import("@/api/client")>()),
  apiFetch: (...args: unknown[]) => apiFetchMock(...args),
}));

let capacidades = new Set<string>();

vi.mock("@/app/autoridad/AutoridadContext", () => ({
  useAutoridad: () => ({
    estado: "LISTA",
    tiene: (c: string) => capacidades.has(c),
    puede: () => true,
    motivo: () => null,
    motivoDeCapacidad: () => null,
  }),
}));

vi.mock("@/app/contexts/CompanyContext", () => ({
  useCompany: () => ({ activeCompanyId: "c1", activeCompany: { id: "c1", legal_name: "Contenedor 1" } }),
}));

vi.mock("@/app/contexts/NotificationContext", () => ({
  useNotifications: () => ({ notify: notifyMock }),
}));

const { ConflictosSodPage } = await import("./ConflictosSodPage");

const CATALOGO = {
  procesos: [
    {
      proceso: "DOC-02",
      nombre: "Actos administrativos",
      objeto: "GovernmentAct",
      acciones: [
        { codigo: "DOC02_REGISTRAR", etiqueta: "Registrar el acto", crea_objeto: true },
        { codigo: "DOC02_EDITAR", etiqueta: "Editar el borrador del acto", crea_objeto: false },
      ],
    },
    {
      proceso: "CTL-06",
      nombre: "Hallazgos y acciones correctivas",
      objeto: "GovernmentFinding",
      acciones: [
        { codigo: "CTL06_REGISTRAR", etiqueta: "Registrar el hallazgo", crea_objeto: true },
        { codigo: "CTL06_RECOMENDAR", etiqueta: "Añadir una recomendación", crea_objeto: false },
        { codigo: "CTL06_VERIFICAR", etiqueta: "Verificar y cerrar", crea_objeto: false },
      ],
    },
  ],
};

const LISTADO = {
  items: [
    {
      id: "e1",
      fecha: "2026-11-04T12:30:00Z",
      usuario: "ua",
      regla_id: "r1",
      regla_codigo: "SOD-2026-0001",
      regla_nombre: "Registro y recomendación",
      proceso: "CTL-06",
      accion: "CTL06_RECOMENDAR",
      accion_etiqueta: "Añadir una recomendación",
      accion_previa: "CTL06_REGISTRAR",
      accion_previa_etiqueta: "Registrar el hallazgo",
      objeto_tipo: "GovernmentFinding",
      objeto_id: "h1",
    },
  ],
  total: 1,
  pagina: 1,
  por_pagina: 20,
};

function renderPagina(ruta = "/gobierno/sod/conflictos") {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[ruta]}>
        <Routes>
          <Route path="/gobierno/sod/conflictos" element={<ConflictosSodPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("ConflictosSodPage", () => {
  beforeEach(() => {
    apiFetchMock.mockReset();
    notifyMock.mockReset();
    capacidades = new Set(["gobierno_sod:view"]);

    apiFetchMock.mockImplementation((url: string) => {
      if (url === "/gobierno/sod/acciones") {
        return Promise.resolve(CATALOGO);
      }
      if (url.startsWith("/gobierno/sod/conflictos")) {
        return Promise.resolve(LISTADO);
      }
      return Promise.reject(new Error(`URL no esperada: ${url}`));
    });
  });

  it("CSP-01 · con :view muestra la fila", async () => {
    renderPagina();

    expect(await screen.findByText("ua")).toBeInTheDocument();

    const enlaceRegla = screen.getByRole("link", { name: "SOD-2026-0001" });
    expect(enlaceRegla).toHaveAttribute("href", "/gobierno/sod/r1");

    expect(screen.getByText("Añadir una recomendación")).toBeInTheDocument();
    expect(screen.getByText("Registrar el hallazgo")).toBeInTheDocument();

    const enlaceHallazgo = screen.getByRole("link", { name: "Abrir hallazgo" });
    expect(enlaceHallazgo).toHaveAttribute("href", "/gobierno/hallazgos/h1");
  });

  it("CSP-02 · con la entrada regla_id la consulta lleva regla_id y se puede quitar", async () => {
    const user = userEvent.setup();
    renderPagina("/gobierno/sod/conflictos?regla_id=r1");

    expect(await screen.findByText("Filtrando por una regla.")).toBeInTheDocument();

    await waitFor(() => {
      const urls = apiFetchMock.mock.calls.map((llamada) => String(llamada[0]));
      expect(urls.some((url) => url.includes("regla_id=r1"))).toBe(true);
    });

    await user.click(screen.getByRole("button", { name: "Quitar filtro de regla" }));

    await waitFor(() => {
      const urls = apiFetchMock.mock.calls
        .map((llamada) => String(llamada[0]))
        .filter((url) => url.startsWith("/gobierno/sod/conflictos"));
      expect(urls.length).toBeGreaterThan(0);
      expect(urls[urls.length - 1]).not.toContain("regla_id=r1");
    });
  });

  it("CSP-03 · escribir usuario NO consulta hasta aplicar filtros", async () => {
    const user = userEvent.setup();
    renderPagina();

    await screen.findByText("ua");

    apiFetchMock.mockClear();

    const inputUsuario = screen.getByLabelText(/^Usuario/);
    await user.type(inputUsuario, "ub");

    expect(apiFetchMock).not.toHaveBeenCalled();

    await user.click(screen.getByRole("button", { name: "Aplicar filtros" }));

    await waitFor(() => {
      const urls = apiFetchMock.mock.calls
        .map((llamada) => String(llamada[0]))
        .filter((url) => url.startsWith("/gobierno/sod/conflictos"));
      expect(urls[urls.length - 1]).toContain("usuario=ub");
    });
  });

  it("CSP-04 · items vacíos muestra No hay intentos bloqueados", async () => {
    apiFetchMock.mockImplementation((url: string) => {
      if (url === "/gobierno/sod/acciones") {
        return Promise.resolve(CATALOGO);
      }
      if (url.startsWith("/gobierno/sod/conflictos")) {
        return Promise.resolve({ items: [], total: 0, pagina: 1, por_pagina: 20 });
      }
      return Promise.reject(new Error(`URL no esperada: ${url}`));
    });

    renderPagina();

    expect(await screen.findByText("No hay intentos bloqueados")).toBeInTheDocument();
  });

  it("CSP-05 · sin :view muestra Sin acceso", async () => {
    capacidades = new Set();

    renderPagina();

    expect(await screen.findByText("Sin acceso")).toBeInTheDocument();
    expect(apiFetchMock).not.toHaveBeenCalled();
  });
});
