import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "@/api/client";

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

const { FuncionarioPage } = await import("./FuncionarioPage");

const funcionarioDetalle = {
  id: "f1",
  codigo: "F-001",
  nombre: "Persona Uno",
  documento: "V-******90",
  estado: "ACTIVO" as const,
  version: 3,
  creado_en: "2025-01-15T10:00:00Z",
  historia: [
    {
      id: "h1",
      tipo: "FUNCIONARIO_REGISTRADO",
      detalle: null,
      actor: "admin@example.com",
      creado_en: "2025-01-15T10:00:00Z",
    },
  ],
  asignaciones: [
    {
      id: "a1",
      codigo: "ASIG-001",
      figura: "TITULAR" as const,
      figura_etiqueta: "Titular",
      funcionario: {
        id: "f1",
        codigo: "F-001",
        nombre: "Persona Uno",
        documento: "V-******90",
      },
      cargo: {
        id: "c1",
        codigo: "C-001",
        nombre: "Director de Obras",
        unidad_id: "u1",
        unidad: "Obras Públicas",
        ejercicio: 2025,
      },
      cargo_origen: null,
      acto: {
        id: "act1",
        tipo: "DECRETO",
        numero: "123",
        fecha: "2025-01-01",
        status: "VIGENTE",
        fecha_eficacia: "2025-01-01",
        medio: null,
        emisor_cargo_id: "ce1",
        emisor_cargo: "Alcalde",
        funcionario: "Persona Uno",
        asunto: "Nombramiento",
      },
      desde: "2025-01-01",
      hasta: null,
      fin_efectivo: null,
      status: "ACTIVO" as const,
      situacion: "VIGENTE" as const,
      version: 1,
    },
  ],
};

function renderPage() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={["/gobierno/ocupacion/funcionarios/f1"]}>
        <Routes>
          <Route
            path="/gobierno/ocupacion/funcionarios/:funcionarioId"
            element={<FuncionarioPage />}
          />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("FuncionarioPage", () => {
  beforeEach(() => {
    apiFetchMock.mockReset();
    notifyMock.mockReset();
    capacidades = new Set<string>();
  });

  it("FP-01 · sin gobierno_ocupacion:view muestra Sin acceso", async () => {
    renderPage();

    expect(await screen.findByText("Sin acceso")).toBeInTheDocument();
    expect(
      screen.getByText("No tiene permiso para ver este funcionario."),
    ).toBeInTheDocument();
    expect(apiFetchMock).not.toHaveBeenCalled();
  });

  it("FP-02 · 404 muestra Funcionario no encontrado", async () => {
    capacidades.add("gobierno_ocupacion:view");

    apiFetchMock.mockRejectedValue(
      new ApiError(404, { code: "NOT_FOUND", message: "Not found" }),
    );

    renderPage();

    expect(
      await screen.findByText("Funcionario no encontrado"),
    ).toBeInTheDocument();
    expect(apiFetchMock).toHaveBeenCalledWith(
      "/gobierno/ocupacion/funcionarios/f1",
    );
  });

  it("FP-03 · muestra datos, asignaciones e historia", async () => {
    capacidades.add("gobierno_ocupacion:view");

    apiFetchMock.mockResolvedValue(funcionarioDetalle);

    renderPage();

    expect(
      await screen.findByRole("heading", { level: 1, name: "Persona Uno" }),
    ).toBeInTheDocument();
    expect(screen.getByText("F-001")).toBeInTheDocument();
    expect(screen.getByText("V-******90")).toBeInTheDocument();

    expect(screen.getByText("Asignaciones")).toBeInTheDocument();
    const asignacionLink = screen.getByRole("link", {
      name: "Abrir la asignación ASIG-001",
    });
    expect(asignacionLink).toBeInTheDocument();
    expect(screen.getByText("Director de Obras")).toBeInTheDocument();

    expect(screen.getByText("Historia")).toBeInTheDocument();
    expect(
      screen.getByText("FUNCIONARIO_REGISTRADO"),
    ).toBeInTheDocument();
    expect(screen.getByText("admin@example.com")).toBeInTheDocument();
  });

  it("FP-04 · Modificar solo con manage y hace PATCH con ifMatch y { nombre, estado }", async () => {
    capacidades.add("gobierno_ocupacion:view");
    capacidades.add("gobierno_ocupacion:manage");

    apiFetchMock.mockResolvedValue(funcionarioDetalle);

    const usuario = userEvent.setup();
    renderPage();

    expect(await screen.findByText("Modificar")).toBeInTheDocument();

    const nombreInput = screen.getByLabelText("Nombre");
    await usuario.clear(nombreInput);
    await usuario.type(nombreInput, "Persona Modificada");

    const estadoSelect = screen.getByLabelText("Estado");
    await usuario.selectOptions(estadoSelect, "INACTIVO");

    await usuario.click(
      screen.getByRole("button", { name: "Guardar cambios" }),
    );

    await waitFor(() => {
      expect(apiFetchMock).toHaveBeenCalledWith(
        "/gobierno/ocupacion/funcionarios/f1",
        expect.objectContaining({
          method: "PATCH",
          ifMatch: String(funcionarioDetalle.version),
          body: {
            nombre: "Persona Modificada",
            estado: "INACTIVO",
          },
        }),
      );
    });
  });

  it("FP-05 · 409 GOV_OFFICIAL_STALE muestra el aviso de recargar", async () => {
    capacidades.add("gobierno_ocupacion:view");
    capacidades.add("gobierno_ocupacion:manage");

    apiFetchMock.mockResolvedValue(funcionarioDetalle);

    const usuario = userEvent.setup();
    renderPage();

    expect(await screen.findByText("Modificar")).toBeInTheDocument();

    apiFetchMock.mockRejectedValue(
      new ApiError(409, {
        code: "GOV_OFFICIAL_STALE",
        message: "Otra persona cambió este funcionario. Recargue la página.",
      }),
    );

    await usuario.click(
      screen.getByRole("button", { name: "Guardar cambios" }),
    );

    expect(
      await screen.findByText(
        "Otra persona cambió este funcionario. Recargue la página.",
      ),
    ).toBeInTheDocument();
  });
});
