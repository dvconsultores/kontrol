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
  useCompany: () => ({
    activeCompanyId: "c1",
    activeCompany: { id: "c1", legal_name: "Contenedor 1" },
  }),
}));

vi.mock("@/app/contexts/NotificationContext", () => ({
  useNotifications: () => ({ notify: notifyMock }),
}));

const { BloqueosPage } = await import("./BloqueosPage");

const LISTADO = {
  items: [
    {
      id: "b1",
      instante: "2026-11-04T12:30:00Z",
      politica_id: "p1",
      politica_codigo: "CERRAR-2026-0001",
      accion_cierre: "ORG02_CERRAR_ESTRUCTURA",
      objeto_tipo: "GovernmentStructure",
      objeto_id: "s1",
      objeto_codigo: "EST-2026",
      total: 3,
      usuario: "ua",
    },
  ],
  total: 1,
  pagina: 1,
  tamano: 20,
};

function renderPagina() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={["/gobierno/cierres/bloqueos"]}>
        <Routes>
          <Route
            path="/gobierno/cierres/bloqueos"
            element={<BloqueosPage />}
          />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("BloqueosPage", () => {
  beforeEach(() => {
    apiFetchMock.mockReset();
    notifyMock.mockReset();
    capacidades = new Set(["gobierno_cierre:view"]);

    apiFetchMock.mockImplementation((url: string) => {
      if (url.startsWith("/gobierno/cierres/bloqueos")) {
        return Promise.resolve(LISTADO);
      }
      return Promise.reject(new Error(`URL no esperada: ${url}`));
    });
  });

  it("BLQ-01 · sin :view muestra Sin acceso y no consulta", async () => {
    capacidades = new Set();

    renderPagina();

    expect(await screen.findByText("Sin acceso")).toBeInTheDocument();
    expect(apiFetchMock).not.toHaveBeenCalled();
  });

  it("BLQ-02 · muestra estado de carga", () => {
    apiFetchMock.mockImplementation(() => new Promise(() => undefined));

    renderPagina();

    expect(screen.getByText("Cargando cierres bloqueados…")).toBeInTheDocument();
  });

  it("BLQ-03 · en error muestra ErrorState", async () => {
    apiFetchMock.mockImplementation(() =>
      Promise.reject(new Error("fallo de red")),
    );

    renderPagina();

    expect(
      await screen.findByText("No fue posible cargar los cierres bloqueados."),
    ).toBeInTheDocument();
  });

  it("BLQ-04 · vacio sin filtros muestra No hay cierres bloqueados", async () => {
    apiFetchMock.mockImplementation(() =>
      Promise.resolve({ items: [], total: 0, pagina: 1, tamano: 20 }),
    );

    renderPagina();

    expect(
      await screen.findByText("No hay cierres bloqueados"),
    ).toBeInTheDocument();
  });

  it("BLQ-05 · con :view muestra la fila con enlaces y celdas", async () => {
    renderPagina();

    expect(await screen.findByText("ua")).toBeInTheDocument();

    const enlacePolitica = screen.getByRole("link", {
      name: "CERRAR-2026-0001",
    });
    expect(enlacePolitica).toHaveAttribute(
      "href",
      "/gobierno/cierres/p1",
    );

    const enlaceObjeto = screen.getByRole("link", { name: "EST-2026" });
    expect(enlaceObjeto).toHaveAttribute(
      "href",
      "/gobierno/estructura/2026",
    );

    expect(
      screen.getByRole("cell", { name: "Cerrar estructura del ejercicio" }),
    ).toBeInTheDocument();
    expect(screen.queryByText("2026")).not.toBeInTheDocument();
    expect(screen.getByText("3")).toBeInTheDocument();

    const urls = apiFetchMock.mock.calls.map((llamada) => String(llamada[0]));
    expect(
      urls.some(
        (url) =>
          url.startsWith("/gobierno/cierres/bloqueos") &&
          url.includes("pagina=1") &&
          url.includes("tamano=20"),
      ),
    ).toBe(true);
  });

  it("BLQ-06 · aplicar filtros consulta con accion, desde y hasta", async () => {
    const user = userEvent.setup();
    renderPagina();

    await screen.findByText("ua");

    apiFetchMock.mockClear();

    await user.selectOptions(
      screen.getByLabelText("Acción"),
      "ORG02_CERRAR_ESTRUCTURA",
    );
    await user.type(screen.getByLabelText("Desde"), "2026-01-01");
    await user.type(screen.getByLabelText("Hasta"), "2026-12-31");

    expect(apiFetchMock).not.toHaveBeenCalled();

    await user.click(screen.getByRole("button", { name: "Aplicar filtros" }));

    await waitFor(() => {
      const urls = apiFetchMock.mock.calls
        .map((llamada) => String(llamada[0]))
        .filter((url) => url.startsWith("/gobierno/cierres/bloqueos"));
      expect(urls.length).toBeGreaterThan(0);
      const ultima = urls[urls.length - 1];
      expect(ultima).toContain("accion_cierre=ORG02_CERRAR_ESTRUCTURA");
      expect(ultima).toContain("desde=2026-01-01");
      expect(ultima).toContain("hasta=2026-12-31");
    });
  });

  it("BLQ-07 · vacio con filtros muestra Sin resultados", async () => {
    apiFetchMock.mockImplementation(() =>
      Promise.resolve({ items: [], total: 0, pagina: 1, tamano: 20 }),
    );
    const user = userEvent.setup();
    renderPagina();

    await screen.findByText("No hay cierres bloqueados");

    await user.selectOptions(
      screen.getByLabelText("Acción"),
      "ORG02_CERRAR_ESTRUCTURA",
    );
    await user.click(screen.getByRole("button", { name: "Aplicar filtros" }));

    expect(await screen.findByText("Sin resultados")).toBeInTheDocument();
  });

  it("BLQ-08 · politica con politica_id enlaza a /gobierno/cierres/<politica_id>", async () => {
    apiFetchMock.mockImplementation(() =>
      Promise.resolve({
        items: [
          {
            id: "b2",
            instante: "2026-11-04T12:30:00Z",
            politica_id: "p456",
            politica_codigo: "CERRAR-2026-0002",
            accion_cierre: "ORG02_CERRAR_ESTRUCTURA",
            objeto_tipo: "GovernmentStructure",
            objeto_id: "s2",
            objeto_codigo: "EST-2027",
            total: 1,
            usuario: "ub",
          },
        ],
        total: 1,
        pagina: 1,
        tamano: 20,
      }),
    );

    renderPagina();

    const enlacePolitica = await screen.findByRole("link", {
      name: "CERRAR-2026-0002",
    });
    expect(enlacePolitica).toHaveAttribute(
      "href",
      "/gobierno/cierres/p456",
    );
  });

  it("BLQ-09 · politica_id null muestra el codigo sin enlace", async () => {
    apiFetchMock.mockImplementation(() =>
      Promise.resolve({
        items: [
          {
            id: "b3",
            instante: "2026-11-04T12:30:00Z",
            politica_id: null,
            politica_codigo: "CERRAR-2026-0003",
            accion_cierre: "ORG02_CERRAR_ESTRUCTURA",
            objeto_tipo: "GovernmentStructure",
            objeto_id: "s3",
            objeto_codigo: "EST-2028",
            total: 2,
            usuario: "uc",
          },
        ],
        total: 1,
        pagina: 1,
        tamano: 20,
      }),
    );

    renderPagina();

    const textoPolitica = await screen.findByText("CERRAR-2026-0003");
    expect(textoPolitica).toBeInTheDocument();
    expect(
      screen.queryByRole("link", { name: "CERRAR-2026-0003" }),
    ).not.toBeInTheDocument();
  });

  it("BLQ-10 · objeto no resoluble se muestra como texto", async () => {
    apiFetchMock.mockImplementation(() =>
      Promise.resolve({
        items: [
          {
            id: "b4",
            instante: "2026-11-04T12:30:00Z",
            politica_id: "p4",
            politica_codigo: "CERRAR-2026-0004",
            accion_cierre: "ORG02_CERRAR_ESTRUCTURA",
            objeto_tipo: "OtroTipo",
            objeto_id: "s4",
            objeto_codigo: "OBJ-2026",
            total: 4,
            usuario: "ud",
          },
        ],
        total: 1,
        pagina: 1,
        tamano: 20,
      }),
    );

    renderPagina();

    const textoObjeto = await screen.findByText("OBJ-2026");
    expect(textoObjeto).toBeInTheDocument();
    expect(
      screen.queryByRole("link", { name: "OBJ-2026" }),
    ).not.toBeInTheDocument();
  });
});
