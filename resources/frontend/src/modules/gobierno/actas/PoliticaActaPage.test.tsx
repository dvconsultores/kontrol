import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";

const apiFetchMock = vi.fn();
vi.mock("@/api/client", async (original) => ({
  ...(await original<typeof import("@/api/client")>()),
  apiFetch: (...args: unknown[]) => apiFetchMock(...args),
  ApiError: class ApiError extends Error {
    status: number;
    code: string;
    constructor(message: string, status: number, code: string) {
      super(message);
      this.status = status;
      this.code = code;
    }
  },
}));

vi.mock("@/app/contexts/CompanyContext", () => ({
  useCompany: () => ({
    activeCompanyId: "c1",
    activeCompany: { id: "c1", legal_name: "Contenedor 1" },
  }),
}));

vi.mock("@/app/contexts/NotificationContext", () => ({
  useNotifications: () => ({
    notify: vi.fn(),
  }),
}));

const capacidades = new Set<string>();

vi.mock("@/app/autoridad/AutoridadContext", () => ({
  useAutoridad: () => ({
    estado: "LISTA",
    tiene: (c: string) => capacidades.has(c),
    puede: () => true,
    motivo: () => null,
    motivoDeCapacidad: () => null,
  }),
}));

import { PoliticaActaPage } from "./PoliticaActaPage";

const detalle: import("./politicasActa").PoliticaActaDetalle = {
  id: "p1",
  codigo: "PACT-2024-01",
  numero_version: 3,
  nombre: "Actas de entes territoriales",
  estado: "VIGENTE",
  estado_etiqueta: "Vigente",
  vigente_desde: "2024-01-01",
  vigente_hasta: null,
  total_vinculos: 1,
  total_requisitos: 1,
  version: 3,
  descripcion: "Política para actas de entrega de entes territoriales",
  fundamento: "Norma de ejemplo",
  act_id: null,
  numeracion_patron: "ACTA-{anio}-{secuencia}",
  testigos_en_entrega: 2,
  cargo_maxima_autoridad_codigo: "ALC",
  version_anterior_id: null,
  activada_en: "2024-01-01",
  cerrada_en: null,
  motivo_cierre: null,
  vinculos: [
    {
      supuesto: "N34_ART17",
      articulo: "17",
      titulo: "Entrega de bienes",
      alcance: "ENTE",
      unit_id: null,
      unidad: null,
    },
  ],
  requisitos: [
    {
      codigo: "R-1",
      titulo: "Informe de gestión",
      evidencia: "DOCUMENTO",
      obligatorio: true,
      ambito: "ENTE",
      supuesto: "N34_ART17",
      document_type_id: "DT-1",
      document_type_nombre: "Informe",
      fuente: "Norma de ejemplo",
    },
  ],
  plazos: [
    {
      hito: "ELABORACION",
      valor: 3,
      unidad: "DIAS_HABILES",
      fuente: "Norma de ejemplo",
      legal_valor: 10,
      legal_fuente: "Ley",
    },
  ],
  regla_ente: {
    origen: "POLITICA",
    origen_etiqueta: "Política PACT-2024-01",
    politica: {
      id: "p1",
      codigo: "PACT-2024-01",
      numero_version: 3,
      nombre: "Actas de entes territoriales",
    },
    regla_version: "v3",
    norma: {
      codigo: "N34",
      version: "N34-2009",
      titulo: "Decreto 123",
      instrumento: "Resolución CGR Nº 01-00-000162",
      gaceta: "Gaceta Oficial 456",
      vigente_desde: "2009-07-28",
    },
    fecha: "2024-01-01",
    ambito: "ENTE",
    unit_id: null,
    unidad: null,
    nivel_territorial: "MUNICIPAL",
    forma_organizativa: null,
    supuestos: [
      {
        codigo: "N34_ART17",
        articulo: "17",
        titulo: "Entrega de bienes",
        sujeto: "Ente territorial",
        vinculo: "DECLARADO",
        alcance: "ENTE",
        motivo: "Declarado",
        nota: null,
      },
    ],
    anexos: [
      {
        codigo: "A-1",
        titulo: "Inventario",
        obligatorio: true,
        generable: false,
        evidencia: "DOCUMENTO",
        fuente: "Norma de ejemplo",
        origen: "POLITICA",
        supuesto: "N34_ART17",
        document_type_id: "DT-1",
        document_type_nombre: "Inventario",
      },
    ],
    testigos: {
      levantada_por_receptor: {
        modalidad: "LEVANTADA_POR_RECEPTOR",
        testigos: 2,
        auditor_interno: true,
        fuente: "Norma de ejemplo",
      },
      entrega: {
        minimo: 1,
        fuente: "Norma de ejemplo",
      },
    },
    plazos: [
      {
        hito: "ELABORACION",
        valor: 3,
        unidad: "DIAS_HABILES",
        base: "TOMA_DE_POSESION",
        fuente: "Norma de ejemplo",
        origen: "LEGAL",
      },
    ],
    numeracion: {
      patron: "ACTA-{anio}-{secuencia}",
      origen: "POLITICA",
    },
    fundamentos: [],
    avisos: [],
  },
  historia: [
    {
      evento: "CREADA",
      version: 1,
      fecha: "2024-01-01",
      actor: "Usuario",
    },
    {
      evento: "SUSTITUIDA",
      version: 2,
      fecha: "2024-02-01",
      actor: "Usuario",
    },
  ],
  versiones: [
    { id: "p1", numero_version: 3, estado: "VIGENTE" },
    { id: "p1-v2", numero_version: 2, estado: "CERRADA" },
  ],
  actas_que_la_usan: 5,
  acciones: {
    editar: false,
    activar: true,
    cerrar: true,
    nueva_version: true,
  },
};

function renderPage() {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={["/politicas/p1"]}>
        <Routes>
          <Route path="/politicas/:politicaId" element={<PoliticaActaPage />} />
          <Route
            path="/gobierno/actas-entrega/politicas/:politicaId/editar"
            element={<div>Editar política</div>}
          />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  capacidades.clear();
  capacidades.add("gobierno_actas:view");
  capacidades.add("gobierno_actas:configure");
  capacidades.add("gobierno_actas:activate");
});

describe("PoliticaActaPage", () => {
  it("FPA-01 pinta Datos, Supuestos declarados, Requisitos, Plazos y Regla aplicada", async () => {
    apiFetchMock.mockResolvedValue(detalle);

    renderPage();

    await waitFor(() =>
      expect(screen.getByRole("heading", { name: "Política PACT-2024-01 v3" })).toBeInTheDocument(),
    );

    // Datos
    expect(screen.getByText("Actas de entes territoriales")).toBeInTheDocument();
    expect(screen.getByText("ACTA-{anio}-{secuencia}")).toBeInTheDocument();
    expect(screen.getByText("2")).toBeInTheDocument();
    expect(screen.getByText("ALC")).toBeInTheDocument();

    // Supuestos declarados
    const supuestos = screen.getByRole("table", { name: "Supuestos declarados" });
    expect(within(supuestos).getByText(/N34 art\. 17/)).toBeInTheDocument();
    expect(within(supuestos).getByText("Entidad")).toBeInTheDocument();

    // Requisitos
    const requisitos = screen.getByRole("table", { name: "Requisitos del ente" });
    expect(within(requisitos).getByText("R-1")).toBeInTheDocument();
    expect(within(requisitos).getByText("Informe de gestión")).toBeInTheDocument();
    expect(within(requisitos).getByText("Documento")).toBeInTheDocument();
    expect(within(requisitos).getByText("Sí")).toBeInTheDocument();
    expect(within(requisitos).getByText("Acta de la entidad")).toBeInTheDocument();
    expect(within(requisitos).getByText("N34_ART17")).toBeInTheDocument();
    expect(within(requisitos).getByText("Informe")).toBeInTheDocument();
    expect(within(requisitos).getByText("Norma de ejemplo")).toBeInTheDocument();

    // Plazos
    const plazos = screen.getByRole("table", { name: "Plazos internos" });
    expect(within(plazos).getByText("Elaboración del acta")).toBeInTheDocument();
    expect(within(plazos).getByText("3 días hábiles")).toBeInTheDocument();
    expect(within(plazos).getByText("10 días hábiles")).toBeInTheDocument();

    // Regla aplicada
    expect(screen.getByText("Regla aplicada")).toBeInTheDocument();
    expect(screen.getByText(/Decreto 123/)).toBeInTheDocument();
    expect(screen.getAllByText(/N34 art\. 17/).length).toBeGreaterThan(1);
  });

  it("FPA-02 con activate y acciones.activar, «Activar» hace POST a /activar con ifMatch 3", async () => {
    apiFetchMock.mockResolvedValue(detalle);

    renderPage();

    await waitFor(() => {
      expect(screen.getByRole("button", { name: "Activar" })).toBeInTheDocument();
    });

    await userEvent.click(screen.getByRole("button", { name: "Activar" }));

    await waitFor(() => {
      const calls = apiFetchMock.mock.calls.map((c) => String(c[0]));
      expect(calls.some((u) => u.includes("/gobierno/actas-entrega/politicas/p1/activar"))).toBe(true);
    });

    const activationCall = apiFetchMock.mock.calls.find((c) =>
      String(c[0]).includes("/activar"),
    );
    expect(activationCall?.[1]).toMatchObject({ ifMatch: "3" });
  });

  it("FPA-03 historia con SUSTITUIDA muestra «Cerrada (sustituida)»", async () => {
    apiFetchMock.mockResolvedValue(detalle);

    renderPage();

    await waitFor(() =>
      expect(screen.findByText(/Cerrada \(sustituida\)/)).resolves.toBeInTheDocument(),
    );
  });

  it("FPA-04 sin activate no hay «Activar»", async () => {
    capacidades.delete("gobierno_actas:activate");
    apiFetchMock.mockResolvedValue(detalle);

    renderPage();

    await waitFor(() =>
      expect(screen.queryByRole("button", { name: "Activar" })).not.toBeInTheDocument(),
    );
  });
});
