import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "@/api/client";
import type {
  AsignacionResumen,
  CargoOcupacion,
} from "@/modules/gobierno/api";
import { hoyDeNegocio } from "@/lib/fecha-de-negocio";

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

const { CargoOcupacionPage } = await import("./CargoOcupacionPage");

const crearQueryClient = () =>
  new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });

const renderPage = () => {
  return render(
    <QueryClientProvider client={crearQueryClient()}>
      <MemoryRouter initialEntries={["/gobierno/ocupacion/cargos/cargo-1"]}>
        <Routes>
          <Route path="/gobierno/ocupacion/cargos/:cargoId" element={<CargoOcupacionPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
};

const cargoOcupado: CargoOcupacion = {
  cargo: {
    id: "cargo-1",
    codigo: "CGO-001",
    nombre: "Director de Administración",
    unidad_id: "u1",
    unidad: "Administración",
    ejercicio: 2024,
  },
  fecha: hoyDeNegocio(),
  titular: {
    id: "asig-1",
    codigo: "ASG-001",
    figura: "TITULAR",
    figura_etiqueta: "Titular",
    funcionario: { id: "f1", codigo: "FUN-001", nombre: "Persona Uno", documento: "V-******90" },
    cargo: {
      id: "cargo-1",
      codigo: "CGO-001",
      nombre: "Director de Administración",
      unidad_id: "u1",
      unidad: "Administración",
      ejercicio: 2024,
    },
    cargo_origen: null,
    acto: {
      id: "acto-1",
      tipo: "DECRETO",
      numero: "123",
      fecha: "2024-01-15",
      status: "PUBLICADO",
      fecha_eficacia: "2024-01-15",
      medio: null,
      emisor_cargo_id: "cargo-2",
      emisor_cargo: "Alcalde",
      funcionario: "Persona Uno",
      asunto: "Nombramiento",
    },
    desde: "2024-01-15",
    hasta: null,
    fin_efectivo: null,
    status: "ACTIVO",
    situacion: "VIGENTE",
    version: 1,
  },
  ejerce: null,
  vacante: false,
  delegaciones: [],
  competencias: [
    {
      accion: "ORDENAR_PAGO",
      materia: "PRESUPUESTO",
      tipo_limite: "SIN_LIMITE",
      monto: null,
      moneda: null,
    },
    {
      accion: "APROBAR",
      materia: "CONTRATACIONES",
      tipo_limite: "MONTO_MAXIMO",
      monto: "5000",
      moneda: "USD",
    },
  ],
  historial: [],
};

const cargoVacante: CargoOcupacion = {
  ...cargoOcupado,
  titular: null,
  ejerce: null,
  vacante: true,
  delegaciones: [],
  historial: [],
};

describe("CargoOcupacionPage", () => {
  beforeEach(() => {
    apiFetchMock.mockReset();
    notifyMock.mockReset();
    capacidades = new Set<string>();
  });

  it("COP-01 · sin acceso no consulta la API y muestra el mensaje de permiso", async () => {
    renderPage();

    expect(await screen.findByText("Sin acceso")).toBeInTheDocument();
    expect(
      screen.getByText("No tiene permiso para ver la ocupación de cargos."),
    ).toBeInTheDocument();
    expect(apiFetchMock).not.toHaveBeenCalled();
  });

  it("COP-02 · cargo cubierto muestra titular, acto con enlace, autoridad Sin límite y monto con moneda", async () => {
    capacidades.add("gobierno_ocupacion:view");
    apiFetchMock.mockResolvedValue(cargoOcupado);

    renderPage();

    expect(
      await screen.findByRole("heading", { level: 1, name: "Director de Administración" }),
    ).toBeInTheDocument();
    expect(screen.getByText("Persona Uno")).toBeInTheDocument();
    expect(screen.getAllByText("Emitido por: Alcalde").length).toBeGreaterThan(0);

    const enlaceActo = screen.getByRole("link", { name: "DECRETO · 123" });
    expect(enlaceActo).toHaveAttribute("href", "/gobierno/actos/acto-1");

    expect(screen.getByText("Sin límite")).toBeInTheDocument();
    expect(screen.getByText("5000 USD")).toBeInTheDocument();
  });

  it("COP-03 · cargo vacante muestra el mensaje correspondiente", async () => {
    capacidades.add("gobierno_ocupacion:view");
    apiFetchMock.mockResolvedValue(cargoVacante);

    renderPage();

    expect(
      await screen.findByText("El cargo está vacante a esa fecha."),
    ).toBeInTheDocument();
  });

  it("COP-04 · delegaciones vacías muestran su texto", async () => {
    capacidades.add("gobierno_ocupacion:view");
    apiFetchMock.mockResolvedValue({ ...cargoOcupado, delegaciones: [] });

    renderPage();

    expect(
      await screen.findByText("No hay delegaciones vigentes."),
    ).toBeInTheDocument();
  });

  it("COP-05 · historia lista una fila revocada con etiqueta Revocada", async () => {
    capacidades.add("gobierno_ocupacion:view");
    apiFetchMock.mockResolvedValue({
      ...cargoOcupado,
      historial: [
        {
          ...(cargoOcupado.titular as AsignacionResumen),
          id: "asig-rev",
          codigo: "ASG-REV",
          funcionario: { id: "f2", codigo: "FUN-002", nombre: "Persona Dos", documento: "V-******91" },
          figura_etiqueta: "Suplencia",
          desde: "2023-05-10",
          hasta: "2024-01-14",
          fin_efectivo: "2024-01-14",
          situacion: "REVOCADA",
        },
      ],
    });

    renderPage();

    expect(await screen.findByText("Persona Dos")).toBeInTheDocument();
    expect(screen.getByText("Revocada")).toBeInTheDocument();
  });

  it("COP-06 · cambiar la fecha repite la consulta con ?fecha=", async () => {
    capacidades.add("gobierno_ocupacion:view");
    apiFetchMock.mockResolvedValue(cargoOcupado);

    renderPage();

    expect(
      await screen.findByRole("heading", { level: 1, name: "Director de Administración" }),
    ).toBeInTheDocument();
    expect(apiFetchMock).toHaveBeenCalledWith(
      `/gobierno/ocupacion/cargos/cargo-1?fecha=${hoyDeNegocio()}`,
    );

    const inputFecha = screen.getByLabelText("Fecha");
    fireEvent.change(inputFecha, { target: { value: "2024-07-20" } });

    await waitFor(() => {
      expect(apiFetchMock).toHaveBeenCalledWith(
        "/gobierno/ocupacion/cargos/cargo-1?fecha=2024-07-20",
      );
    });
  });

  it("COP-07 · 404 muestra no encontrado", async () => {
    capacidades.add("gobierno_ocupacion:view");
    apiFetchMock.mockRejectedValue(
      new ApiError(404, { code: "NOT_FOUND", message: "No encontrado" }),
    );

    renderPage();

    expect(await screen.findByText("Cargo no encontrado")).toBeInTheDocument();
    expect(screen.getByText("El cargo solicitado no existe.")).toBeInTheDocument();
  });

  it("COP-08 · Nueva asignación solo con manage y con ?cargo=", async () => {
    const user = userEvent.setup();

    capacidades.add("gobierno_ocupacion:view");
    apiFetchMock.mockResolvedValue(cargoOcupado);

    const view = renderPage();

    expect(
      await screen.findByRole("heading", { level: 1, name: "Director de Administración" }),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("link", { name: "Nueva asignación" }),
    ).not.toBeInTheDocument();

    capacidades.add("gobierno_ocupacion:manage");
    view.rerender(
      <QueryClientProvider client={crearQueryClient()}>
        <MemoryRouter initialEntries={["/gobierno/ocupacion/cargos/cargo-1"]}>
          <Routes>
            <Route path="/gobierno/ocupacion/cargos/:cargoId" element={<CargoOcupacionPage />} />
          </Routes>
        </MemoryRouter>
      </QueryClientProvider>,
    );

    const enlaceNueva = await screen.findByRole("link", { name: "Nueva asignación" });
    expect(enlaceNueva).toHaveAttribute(
      "href",
      "/gobierno/ocupacion/asignaciones/nueva?cargo=cargo-1",
    );

    await user.click(enlaceNueva);
  });
});
