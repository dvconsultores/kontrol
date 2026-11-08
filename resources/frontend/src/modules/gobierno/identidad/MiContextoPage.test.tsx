import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Routes, Route } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { ContextoInstitucional } from "@/modules/gobierno/api";

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

let empresaActiva: string | null = "c1";

vi.mock("@/app/contexts/CompanyContext", () => ({
  useCompany: () => ({
    activeCompanyId: empresaActiva,
    activeCompany: empresaActiva
      ? { id: empresaActiva, legal_name: "Contenedor 1" }
      : null,
  }),
}));

vi.mock("@/app/contexts/NotificationContext", () => ({
  useNotifications: () => ({ notify: notifyMock }),
}));

const { MiContextoPage } = await import("./MiContextoPage");

function renderPage(initialEntries: string[] = ["/gobierno/identidad/mi-contexto"]) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={initialEntries}>
        <Routes>
          <Route
            path="/gobierno/identidad/mi-contexto"
            element={<MiContextoPage />}
          />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

const contextoConVinculo: ContextoInstitucional = {
  fecha: "2026-01-15",
  es_historica: false,
  ente: { id: "ente-1", nombre: "Ente de Prueba" },
  cuenta: { id: "cuenta-1", usuario: "analista.prueba", estado: "ACTIVE" },
  vinculo: {
    id: "vinculo-1",
    codigo: "V-001",
    situacion: "VIGENTE",
  },
  funcionario: {
    id: "func-1",
    codigo: "F-001",
    nombre: "Funcionario de Prueba",
    documento: "V-******78",
  },
  ocupaciones: [
    {
      asignacion_id: "asig-1",
      codigo: "OC-001",
      figura: "TITULAR",
      figura_etiqueta: "Titular",
      cargo_id: "cargo-1",
      cargo: "Director General",
      cargo_codigo: "DG",
      unidad_id: "unidad-1",
      unidad: "Dirección General",
      ejercicio: 2026,
      ejerce: true,
      situacion: "VIGENTE",
      desde: "2026-01-01",
      hasta: null,
      autoridad: [
        {
          accion: "APROBAR",
          materia: "PRESUPUESTO",
          tipo_limite: null,
          monto: null,
          moneda: null,
        },
      ],
      avocaciones: 0,
    },
  ],
  unidades: [{ id: "unidad-1", nombre: "Dirección General" }],
  roles: [],
  categorias: [],
  conflictos: [],
  tiene_autoridad: true,
  motivo_sin_autoridad: null,
};

const contextoSinVinculo: ContextoInstitucional = {
  fecha: "2026-01-15",
  es_historica: false,
  ente: { id: "ente-1", nombre: "Ente de Prueba" },
  cuenta: { id: "cuenta-1", usuario: "analista.prueba", estado: "ACTIVE" },
  vinculo: null,
  funcionario: null,
  ocupaciones: [],
  unidades: [],
  roles: [],
  categorias: [],
  conflictos: [],
  tiene_autoridad: false,
  motivo_sin_autoridad: "SIN_VINCULO",
};

describe("MiContextoPage", () => {
  beforeEach(() => {
    apiFetchMock.mockReset();
    notifyMock.mockReset();
    empresaActiva = "c1";
    capacidades = new Set<string>();
  });

  it("sin empresa activa muestra 'Sin empresa seleccionada'", async () => {
    empresaActiva = null;
    renderPage();

    expect(
      await screen.findByText("Sin empresa seleccionada"),
    ).toBeInTheDocument();
    expect(apiFetchMock).not.toHaveBeenCalled();
  });

  it("no exige capacidades: con el Set vacío igual consulta /gobierno/identidad/mi-contexto y muestra la cuenta 'analista.prueba'", async () => {
    capacidades = new Set<string>();
    apiFetchMock.mockResolvedValue(contextoConVinculo);

    renderPage();

    await screen.findByText("analista.prueba");

    const llamada = apiFetchMock.mock.calls[0];
    expect(llamada[0]).toBe("/gobierno/identidad/mi-contexto");
    expect(llamada[1]).toBeUndefined();
  });

  it("sin vínculo: muestra 'Sin vínculo institucional vigente' y el texto 'La cuenta no tiene un vínculo institucional vigente' (negativa)", async () => {
    apiFetchMock.mockResolvedValue(contextoSinVinculo);

    renderPage();

    expect(
      await screen.findByText("Sin vínculo institucional vigente"),
    ).toBeInTheDocument();
    expect(
      screen.getByText("La cuenta no tiene un vínculo institucional vigente"),
    ).toBeInTheDocument();
  });

  it("con vínculo y una ocupación: muestra funcionario, cargo, unidad y autoridad 'APROBAR · PRESUPUESTO'", async () => {
    apiFetchMock.mockResolvedValue(contextoConVinculo);

    renderPage();

    await screen.findByText("analista.prueba");

    expect(
      screen.getByText("Funcionario de Prueba · V-******78"),
    ).toBeInTheDocument();
    expect(screen.getByText("Director General")).toBeInTheDocument();
    expect(screen.getByText("Dirección General")).toBeInTheDocument();
    expect(screen.getByText("APROBAR · PRESUPUESTO")).toBeInTheDocument();
  });

  it("cambiar la fecha consulta /gobierno/identidad/mi-contexto?fecha=AAAA-MM-DD y ninguna URL pedida contiene company_id ni ente (negativa)", async () => {
    apiFetchMock.mockResolvedValue(contextoConVinculo);

    renderPage();

    await screen.findByText("analista.prueba");

    const inputFecha = screen.getByLabelText("Consultar a la fecha");
    await userEvent.type(inputFecha, "2026-02-01");

    await waitFor(() => {
      const llamadas = apiFetchMock.mock.calls;
      expect(llamadas.length).toBeGreaterThan(0);
      const ultimaLlamada = llamadas[llamadas.length - 1];
      expect(ultimaLlamada[0]).toBe(
        "/gobierno/identidad/mi-contexto?fecha=2026-02-01",
      );
      expect(ultimaLlamada[0]).not.toContain("company_id");
      expect(ultimaLlamada[0]).not.toContain("ente");
    });
  });

  it("es_historica true muestra el aviso de consulta histórica", async () => {
    const contextoHistorico: ContextoInstitucional = {
      ...contextoConVinculo,
      es_historica: true,
    };
    apiFetchMock.mockResolvedValue(contextoHistorico);

    renderPage();

    expect(
      await screen.findByText(
        "La fecha consultada es pasada. Los datos corresponden al contexto institucional vigente a esa fecha.",
      ),
    ).toBeInTheDocument();
  });
});
