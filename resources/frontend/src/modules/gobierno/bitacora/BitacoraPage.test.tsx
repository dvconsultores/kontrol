import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router";

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

import { BitacoraPage } from "./BitacoraPage";

const filtros = {
  resultados: [
    { codigo: "EXITO", etiqueta: "Éxito" },
    { codigo: "RECHAZO", etiqueta: "Rechazo" },
  ],
  acciones: [
    { codigo: "A1", entidad: "ENT", etiqueta: "Crear", proceso: "P1" },
    { codigo: "A2", entidad: "ENT", etiqueta: "Editar", proceso: "P2" },
  ],
  funcionarios: [{ id: "f1", nombre: "Funcionario Uno" }],
  unidades: [{ id: "u1", nombre: "Unidad Uno" }],
};

const lista = {
  items: [
    {
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
    },
    {
      id: "e2",
      fecha: "2024-03-01T13:00:00Z",
      resultado: "RECHAZO",
      accion: "A2",
      accion_etiqueta: "Editar",
      proceso: "P2",
      proceso_nombre: "Proceso Dos",
      usuario: null,
      funcionario: null,
      cargos: [],
      unidades: [],
      estado_contexto: "SIN_VINCULO",
      request_id: null,
      motivo: "Falta autorización",
    },
  ],
  total: 2,
  pagina: 1,
  por_pagina: 10,
};

function crearQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });
}

function renderizar() {
  const queryClient = crearQueryClient();
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <BitacoraPage />
      </MemoryRouter>
    </QueryClientProvider>
  );
}

describe("BitacoraPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    apiFetchMock.mockImplementation((url: string) => {
      if (url.includes("/filtros")) {
        return Promise.resolve(filtros);
      }
      return Promise.resolve(lista);
    });
  });

  it("muestra la fila con usuario técnico, funcionario, cargo, unidad y enlace al evento", async () => {
    capacidades = new Set(["gobierno_auditoria:view"]);
    renderizar();

    await screen.findByRole("cell", { name: "Funcionario Uno" });
    expect(screen.getByText("usuario@test.com")).toBeInTheDocument();
    expect(screen.getAllByText("Funcionario Uno").length).toBeGreaterThan(0);
    expect(screen.getByText("Cargo Uno")).toBeInTheDocument();
    expect(screen.getByRole("cell", { name: "Unidad Uno" })).toBeInTheDocument();
    const enlace = screen
      .getAllByRole("link")
      .find((a) => a.getAttribute("href") === "/gobierno/bitacora/e1");
    expect(enlace).toBeDefined();
  });

  it("al elegir Funcionario y pulsar Filtrar, la última URL pedida incluye funcionario_id=<id>", async () => {
    capacidades = new Set(["gobierno_auditoria:view"]);
    const usuario = userEvent.setup();
    renderizar();

    await screen.findByRole("option", { name: "Funcionario Uno" });
    const select = screen.getByLabelText("Funcionario");
    await usuario.selectOptions(select, "f1");
    await usuario.click(screen.getByRole("button", { name: /Filtrar/i }));

    await waitFor(() => {
      const urls = apiFetchMock.mock.calls.map((call) => String(call[0]));
      const ultima = urls[urls.length - 1];
      expect(ultima).toContain("funcionario_id=f1");
    });
  });

  it("un evento con funcionario null muestra Sin vínculo vigente", async () => {
    capacidades = new Set(["gobierno_auditoria:view"]);
    renderizar();

    await screen.findByText("Sin vínculo vigente");
    expect(screen.getByText("Sin vínculo vigente")).toBeInTheDocument();
  });

  it("sin la capacidad muestra Sin acceso y no llama a la API", async () => {
    capacidades = new Set();
    renderizar();

    expect(screen.getByText("Sin acceso")).toBeInTheDocument();
    expect(apiFetchMock).not.toHaveBeenCalled();
  });
});
