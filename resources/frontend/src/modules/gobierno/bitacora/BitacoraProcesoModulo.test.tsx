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

import { BitacoraPage } from "./BitacoraPage";
import { BitacoraEventoPage } from "./BitacoraEventoPage";

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

function crearQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });
}

function renderizarLista() {
  const queryClient = crearQueryClient();
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <BitacoraPage />
      </MemoryRouter>
    </QueryClientProvider>
  );
}

function renderizarDetalle(eventoId: string) {
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

const listaConModulo = {
  items: [
    {
      id: "e1",
      fecha: "2024-03-01T12:00:00Z",
      resultado: "EXITO",
      accion: "A1",
      accion_etiqueta: "Crear",
      proceso: "P1",
      proceso_nombre: "Compromiso presupuestario",
      modulo: "M1",
      modulo_nombre: "Presupuesto",
      usuario: "usuario@test.com",
      funcionario: "Funcionario Uno",
      cargos: ["Cargo Uno"],
      unidades: ["Unidad Uno"],
      estado_contexto: "CON_IDENTIDAD",
      request_id: "req-1",
      motivo: null,
    },
  ],
  total: 1,
  pagina: 1,
  por_pagina: 10,
};

const listaSinModulo = {
  items: [
    {
      id: "e1",
      fecha: "2024-03-01T12:00:00Z",
      resultado: "EXITO",
      accion: "A1",
      accion_etiqueta: "Crear",
      proceso: "P1",
      proceso_nombre: "Autenticación",
      modulo: null,
      modulo_nombre: null,
      usuario: "usuario@test.com",
      funcionario: "Funcionario Uno",
      cargos: ["Cargo Uno"],
      unidades: ["Unidad Uno"],
      estado_contexto: "CON_IDENTIDAD",
      request_id: "req-1",
      motivo: null,
    },
  ],
  total: 1,
  pagina: 1,
  por_pagina: 10,
};

const eventoConModulo = {
  id: "e1",
  fecha: "2024-03-01T12:00:00Z",
  resultado: "EXITO",
  accion: "A1",
  accion_etiqueta: "Crear",
  proceso: "P1",
  proceso_nombre: "Proceso Uno",
  modulo: "M1",
  modulo_nombre: "Tesorería",
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
  },
};

const eventoSinModulo = {
  ...eventoConModulo,
  modulo: null,
  modulo_nombre: null,
};

describe("Bitacora proceso y módulo", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    capacidades = new Set(["gobierno_auditoria:view"]);
  });

  it("MOD-01 lista: muestra módulo y proceso en la línea gris", async () => {
    apiFetchMock.mockImplementation((url: string) => {
      if (url.includes("/filtros")) {
        return Promise.resolve(filtros);
      }
      return Promise.resolve(listaConModulo);
    });

    renderizarLista();
    await screen.findByText("Presupuesto · Compromiso presupuestario");
  });

  it("MOD-02 lista: sin módulo muestra solo el proceso", async () => {
    apiFetchMock.mockImplementation((url: string) => {
      if (url.includes("/filtros")) {
        return Promise.resolve(filtros);
      }
      return Promise.resolve(listaSinModulo);
    });

    renderizarLista();
    await screen.findByText("Autenticación");
    expect(screen.queryByText(/ · /)).not.toBeInTheDocument();
  });

  it("MOD-03 detalle: muestra el término Módulo y su valor", async () => {
    apiFetchMock.mockResolvedValue(eventoConModulo);
    renderizarDetalle("e1");

    await screen.findByRole("heading", { level: 1, name: "Crear" });
    expect(screen.getByText("Módulo")).toBeInTheDocument();
    expect(screen.getByText("Tesorería")).toBeInTheDocument();
    expect(screen.getByText("Proceso")).toBeInTheDocument();
  });

  it("MOD-04 detalle: sin módulo no aparece el término Módulo", async () => {
    apiFetchMock.mockResolvedValue(eventoSinModulo);
    renderizarDetalle("e1");

    await screen.findByRole("heading", { level: 1, name: "Crear" });
    expect(screen.queryByText("Módulo")).not.toBeInTheDocument();
  });
});
