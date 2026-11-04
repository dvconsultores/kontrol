import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "@/api/client";
import type {
  AuditoriaMuestraDetalle,
  HallazgoDetalle,
} from "@/modules/gobierno/api";

const apiFetchMock = vi.fn();

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
  useNotifications: () => ({ notify: vi.fn() }),
}));

const navigateMock = vi.fn();

vi.mock("react-router", async (original) => ({
  ...(await original<typeof import("react-router")>()),
  useNavigate: () => navigateMock,
}));

vi.mock("@/modules/documentos/AdjuntosPanel", () => ({
  AdjuntosPanel: () => <div data-testid="adjuntos-panel-mock" />,
}));

const { RegistrarHallazgoPage } = await import("./RegistrarHallazgoPage");

const MUESTRA: AuditoriaMuestraDetalle = {
  id: "m1",
  codigo: "M-001",
  titulo: "Muestra de ejemplo",
  criterio: "Criterio de ejemplo",
  justificacion: "Justificación de ejemplo",
  metodo: "TODAS",
  semilla: 12345,
  tamano: 10,
  poblacion: 100,
  filtros: {
    proceso: "ORG-03",
  },
  registrada_por: "ua",
  registrada_en: "2026-01-01T00:00:00Z",
  eventos: [
    {
      id: "ev1",
      fecha: "2026-02-15T10:30:00Z",
      proceso: "ORG-03",
      proceso_nombre: "Concejo Municipal",
      accion: "update",
      accion_etiqueta: "Actualización",
      entidad: "partida",
      entidad_id: "p1",
      usuario: "ua",
      motivo: null,
      request_id: null,
    },
    {
      id: "ev2",
      fecha: "2026-02-16T11:30:00Z",
      proceso: "ORG-03",
      proceso_nombre: "Concejo Municipal",
      accion: "delete",
      accion_etiqueta: "Eliminación",
      entidad: "partida",
      entidad_id: "p2",
      usuario: "ua",
      motivo: null,
      request_id: null,
    },
  ],
};

const HALLAZGO_CREADO: HallazgoDetalle = {
  id: "h1",
  codigo: "HAL-001",
  titulo: "Hallazgo de ejemplo",
  condicion: "Condición de ejemplo",
  criterio: "Criterio de ejemplo",
  causa: "Causa de ejemplo",
  efecto: "Efecto de ejemplo",
  riesgo: "ALTO",
  origen: "INDEPENDIENTE",
  origen_descripcion: "Origen descrito de ejemplo",
  muestra: null,
  partidas: [],
  estado: "ABIERTO",
  version: 1,
  presentado_por: null,
  presentado_en: null,
  verificado_por: null,
  verificado_en: null,
  nota_verificacion: null,
  created_by: "ua",
  created_at: "2026-02-20T10:00:00Z",
  recomendaciones: [],
  acciones: [],
  historia: [],
};

function renderRegistrarHallazgo(initialEntry = "/gobierno/hallazgos/nuevo") {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[initialEntry]}>
        <RegistrarHallazgoPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  apiFetchMock.mockReset();
  navigateMock.mockReset();
  capacidades = new Set(["gobierno_hallazgos:manage"]);
});

describe("RegistrarHallazgoPage", () => {
  it("RGH-01 · sin gobierno_hallazgos:manage muestra «Sin acceso»", async () => {
    capacidades = new Set();

    renderRegistrarHallazgo();

    expect(
      screen.getByRole("heading", { name: "Sin acceso" }),
    ).toBeInTheDocument();
    expect(
      screen.getByText("No tiene permiso para registrar hallazgos."),
    ).toBeInTheDocument();
  });

  it("RGH-02 · INDEPENDIENTE: completar los campos y enviar hace POST /gobierno/hallazgos con origen INDEPENDIENTE y origen_descripcion, y navega a /gobierno/hallazgos/{id}", async () => {
    apiFetchMock.mockImplementation((url: string, init?: RequestInit) => {
      if (url === "/gobierno/hallazgos" && init?.method === "POST") {
        return Promise.resolve(HALLAZGO_CREADO);
      }
      return Promise.reject(
        new ApiError(500, { code: "INTERNAL", message: "Error" }),
      );
    });

    renderRegistrarHallazgo();

    const user = userEvent.setup();

    await user.click(screen.getByLabelText("Independiente"));

    await user.type(
      screen.getByLabelText(/^Origen descrito/),
      "Origen descrito de ejemplo",
    );
    await user.type(screen.getByLabelText(/^Título/), "Hallazgo de ejemplo");
    await user.type(
      screen.getByLabelText(/^Condición/),
      "Condición de ejemplo",
    );
    await user.type(screen.getByLabelText(/^Criterio/), "Criterio de ejemplo");
    await user.type(screen.getByLabelText(/^Causa/), "Causa de ejemplo");
    await user.type(screen.getByLabelText(/^Efecto/), "Efecto de ejemplo");
    await user.selectOptions(screen.getByLabelText(/^Riesgo/), "ALTO");

    await user.click(
      screen.getByRole("button", { name: "Registrar hallazgo" }),
    );

    await waitFor(() => {
      expect(apiFetchMock).toHaveBeenCalledWith(
        "/gobierno/hallazgos",
        expect.objectContaining({
          method: "POST",
          body: expect.objectContaining({
            origen: "INDEPENDIENTE",
            titulo: "Hallazgo de ejemplo",
            condicion: "Condición de ejemplo",
            criterio: "Criterio de ejemplo",
            causa: "Causa de ejemplo",
            efecto: "Efecto de ejemplo",
            riesgo: "ALTO",
            origen_descripcion: "Origen descrito de ejemplo",
          }),
        }),
      );
    });

    await waitFor(() => {
      expect(navigateMock).toHaveBeenCalledWith("/gobierno/hallazgos/h1");
    });
  });

  it("RGH-03 · con ?muestra=m1 carga la muestra y muestra las partidas como casillas; enviar incluye muestra_id y las partidas marcadas", async () => {
    apiFetchMock.mockImplementation((url: string, init?: RequestInit) => {
      if (url === "/gobierno/auditoria/muestras/m1") {
        return Promise.resolve(MUESTRA);
      }
      if (url === "/gobierno/hallazgos" && init?.method === "POST") {
        return Promise.resolve({
          ...HALLAZGO_CREADO,
          origen: "MUESTRA" as const,
          muestra: {
            id: "m1",
            codigo: "M-001",
            titulo: "Muestra de ejemplo",
          },
          partidas: ["ev1"],
          origen_descripcion: null,
        });
      }
      return Promise.reject(
        new ApiError(500, { code: "INTERNAL", message: "Error" }),
      );
    });

    renderRegistrarHallazgo("/gobierno/hallazgos/nuevo?muestra=m1");

    const user = userEvent.setup();

    expect(
      await screen.findByText("Muestra M-001 · Muestra de ejemplo"),
    ).toBeInTheDocument();

    const casillas = screen.getAllByRole("checkbox");
    expect(casillas).toHaveLength(2);
    expect(screen.getByText(/Partida 1: Actualización/)).toBeInTheDocument();
    expect(screen.getByText(/Partida 2: Eliminación/)).toBeInTheDocument();

    await user.click(casillas[0]);

    await user.type(screen.getByLabelText(/^Título/), "Hallazgo de ejemplo");
    await user.type(
      screen.getByLabelText(/^Condición/),
      "Condición de ejemplo",
    );
    await user.type(screen.getByLabelText(/^Criterio/), "Criterio de ejemplo");
    await user.type(screen.getByLabelText(/^Causa/), "Causa de ejemplo");
    await user.type(screen.getByLabelText(/^Efecto/), "Efecto de ejemplo");
    await user.selectOptions(screen.getByLabelText(/^Riesgo/), "ALTO");

    await user.click(
      screen.getByRole("button", { name: "Registrar hallazgo" }),
    );

    await waitFor(() => {
      expect(apiFetchMock).toHaveBeenCalledWith(
        "/gobierno/hallazgos",
        expect.objectContaining({
          method: "POST",
          body: expect.objectContaining({
            origen: "MUESTRA",
            muestra_id: "m1",
            partidas: ["ev1"],
            titulo: "Hallazgo de ejemplo",
            condicion: "Condición de ejemplo",
            criterio: "Criterio de ejemplo",
            causa: "Causa de ejemplo",
            efecto: "Efecto de ejemplo",
            riesgo: "ALTO",
          }),
        }),
      );
    });

    await waitFor(() => {
      expect(navigateMock).toHaveBeenCalledWith("/gobierno/hallazgos/h1");
    });
  });

  it("RGH-04 · 422 con field_errors {\"condicion\": [\"...\"]} muestra el error bajo «Condición»", async () => {
    apiFetchMock.mockImplementation((url: string, init?: RequestInit) => {
      if (url === "/gobierno/hallazgos" && init?.method === "POST") {
        return Promise.reject(
          new ApiError(422, {
            code: "VALIDATION_ERROR",
            message: "Error de validación",
            field_errors: {
              condicion: ["La condición no es válida."],
            },
          }),
        );
      }
      return Promise.reject(
        new ApiError(500, { code: "INTERNAL", message: "Error" }),
      );
    });

    renderRegistrarHallazgo();

    const user = userEvent.setup();

    await user.click(screen.getByLabelText("Independiente"));

    await user.type(
      screen.getByLabelText(/^Origen descrito/),
      "Origen descrito de ejemplo",
    );
    await user.type(screen.getByLabelText(/^Título/), "Hallazgo de ejemplo");
    await user.type(
      screen.getByLabelText(/^Condición/),
      "Condición de ejemplo",
    );
    await user.type(screen.getByLabelText(/^Criterio/), "Criterio de ejemplo");
    await user.type(screen.getByLabelText(/^Causa/), "Causa de ejemplo");
    await user.type(screen.getByLabelText(/^Efecto/), "Efecto de ejemplo");
    await user.selectOptions(screen.getByLabelText(/^Riesgo/), "ALTO");

    await user.click(
      screen.getByRole("button", { name: "Registrar hallazgo" }),
    );

    expect(
      await screen.findByText("La condición no es válida."),
    ).toBeInTheDocument();
  });
});
