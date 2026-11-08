import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter, Routes, Route } from "react-router";

const apiFetchMock = vi.fn();
vi.mock("@/api/client", async (original) => ({
  ...(await original<typeof import("@/api/client")>()),
  apiFetch: (...args: unknown[]) => apiFetchMock(...args),
  ApiError: (await original<typeof import("@/api/client")>()).ApiError,
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

import { BitacoraEventoPage } from "./BitacoraEventoPage";
import { ApiError } from "@/api/client";

const eventoConContexto = {
  id: "e1",
  fecha: "2024-03-01T12:00:00Z",
  resultado: "EXITO",
  accion: "A1",
  accion_etiqueta: "Crear",
  proceso: "P1",
  proceso_nombre: "Proceso Uno",
  usuario: "usuario@test.com",
  funcionario: "Funcionario Uno",
  cargos: ["Cargo Uno"],
  unidades: ["Unidad Uno"],
  estado_contexto: "CON_IDENTIDAD",
  request_id: "req-1",
  motivo: null,
  entidad: "Entidad Uno",
  entidad_id: "ent-1",
  sesion_id: "s1",
  ip: "192.168.1.1",
  detalle: { campo: "valor" },
  objeto: null,
  contexto: {
    version: 1,
    estado: "ACTIVO",
    fecha: "2024-03-01",
    ente: { id: "ente1", nombre: "Ente Uno" },
    vinculo: { id: "v1", codigo: "VINC-001" },
    funcionario: { id: "f1", nombre: "Funcionario Uno" },
    ocupaciones: [
      {
        cargo_id: "c1",
        cargo: "Cargo Uno",
        cargo_codigo: "C1",
        unidad_id: "u1",
        unidad: "Unidad Uno",
        figura: "FIG1",
        figura_etiqueta: "Figura Uno",
        ejerce: true,
        autoridad: [{ accion: "aprobar", materia: "presupuesto" }],
      },
    ],
    roles: [{ id: "r1", codigo: "R1", nombre: "Rol Uno" }],
    categorias: ["Cat1"],
    tiene_autoridad: true,
    motivo_sin_autoridad: null,
  },
};

const eventoSinVinculo = {
  ...eventoConContexto,
  id: "e2",
  usuario: null,
  funcionario: null,
  unidades: [],
  cargos: [],
  estado_contexto: "SIN_VINCULO",
  request_id: null,
  sesion_id: null,
  ip: null,
  contexto: {
    version: 1,
    estado: "ACTIVO",
    fecha: "2024-03-01",
    ente: { id: "ente1", nombre: "Ente Uno" },
    vinculo: null,
    funcionario: null,
    ocupaciones: [],
    roles: [],
    categorias: [],
    tiene_autoridad: false,
    motivo_sin_autoridad: "No aplica",
  },
};

function crearQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });
}

function renderizar(eventoId: string) {
  const queryClient = crearQueryClient();
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[`/gobierno/bitacora/${eventoId}`]}>
        <Routes>
          <Route path="/gobierno/bitacora/:eventoId" element={<BitacoraEventoPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>
  );
}

describe("BitacoraEventoPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("con contexto: muestra actor efectivo, cargo, unidad, IP, sesión y correlación", async () => {
    capacidades = new Set(["gobierno_auditoria:view"]);
    apiFetchMock.mockResolvedValue(eventoConContexto);
    renderizar("e1");

    await screen.findByRole("heading", { level: 1, name: "Crear" });
    expect(screen.getByText("Funcionario Uno")).toBeInTheDocument();
    expect(screen.getByText("Cargo Uno")).toBeInTheDocument();
    expect(screen.getByText("Unidad Uno")).toBeInTheDocument();
    expect(screen.getByText("192.168.1.1")).toBeInTheDocument();
    expect(screen.getByText("s1")).toBeInTheDocument();
    expect(screen.getByText("req-1")).toBeInTheDocument();
  });

  it("contexto SIN_VINCULO con funcionario null: muestra Sin vínculo vigente y no muestra Actor efectivo", async () => {
    capacidades = new Set(["gobierno_auditoria:view"]);
    apiFetchMock.mockResolvedValue(eventoSinVinculo);
    renderizar("e2");

    await screen.findByText("Sin vínculo vigente");
    expect(screen.getByText("Sin vínculo vigente")).toBeInTheDocument();
    expect(screen.queryByText("Actor efectivo")).not.toBeInTheDocument();
  });

  it("404: apiFetch rechaza con ApiError y aparece el enlace Volver a la Bitácora institucional", async () => {
    capacidades = new Set(["gobierno_auditoria:view"]);
    apiFetchMock.mockRejectedValue(
      new ApiError(404, { code: "GOV_BITACORA_EVENT_NOT_FOUND", message: "x" })
    );
    renderizar("no-existe");

    await screen.findByRole("heading", { level: 1, name: "Evento no encontrado" });
    const enlace = screen.getByRole("link", { name: "Volver a la Bitácora institucional" });
    expect(enlace).toHaveAttribute("href", "/gobierno/bitacora");
  });

  it("el enlace al objeto respeta la capacidad del objeto", async () => {
    const conObjeto = { ...eventoConContexto, objeto: { tipo: "GovernmentOfficial", id: "o1", ruta: "/gobierno/ocupacion/funcionarios/o1", capacidad: "gobierno_ocupacion:view" } };
    apiFetchMock.mockResolvedValue(conObjeto);
    capacidades = new Set(["gobierno_auditoria:view", "gobierno_ocupacion:view"]);
    const { unmount } = renderizar("e1");
    const enlace = await screen.findByRole("link", { name: "Abrir el objeto" });
    expect(enlace).toHaveAttribute("href", "/gobierno/ocupacion/funcionarios/o1");
    unmount();
    capacidades = new Set(["gobierno_auditoria:view"]);
    renderizar("e1");
    await screen.findByRole("heading", { level: 1, name: "Crear" });
    expect(screen.queryByRole("link", { name: "Abrir el objeto" })).not.toBeInTheDocument();
  });
});
