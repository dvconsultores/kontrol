import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter, Routes, Route } from "react-router";

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

vi.mock("@/app/contexts/NotificationContext", () => ({ useNotifications: () => ({ notify: vi.fn(), notifications: [], dismiss: vi.fn() }) }));
vi.mock("@/app/contexts/CompanyContext", () => ({
  useCompany: () => ({
    activeCompanyId: "c1",
    activeCompany: { id: "c1", legal_name: "Contenedor 1" },
  }),
}));

import { ExpedienteCuentaPage } from "./ExpedienteCuentaPage";

function renderPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={["/gobierno/rendicion/e1"]}>
        <Routes>
          <Route path="/gobierno/rendicion/:expedienteId" element={<ExpedienteCuentaPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

const fichaBase = {
  id: "e1",
  codigo: "EXP-001",
  numero_version: 1,
  version: "v1",
  estado: "EN_FORMACION",
  anterior_id: null,
  sustituido_por_id: null,
  sustitucion_motivo: null,
  denominacion: "Cuenta 2024",
  ejercicio: 2024,
  periodo_desde: "2024-01-01",
  periodo_hasta: "2024-12-31",
  fecha_corte: "2024-12-31",
  observaciones: null,
  ente: "Municipio X",
  responsable: {
    funcionario: "Ana Ruiz",
    funcionario_codigo: "F1",
    cargo: "Directora",
    cargo_codigo: "C1",
    unidad: "Finanzas",
    unidad_codigo: "U1",
    figura: "Responsable",
    asignacion_codigo: "A1",
  },
  piezas: [],
  formado_en: null,
  formado_por: null,
  snapshot_sha256: null,
  informe: null,
  participacion: null,
  plazo_participacion: "2025-02-15",
  calificacion: null,
  fenecimiento: null,
  hallazgos: [],
};

const opciones = {
  responsables: [],
  procesos: [],
  estados: [],
};

const reporte = {
  provisional: true,
  generado_en: null,
  expediente: {},
  ente: "Municipio X",
  responsable: fichaBase.responsable,
  piezas: [],
  resumen: [{ concepto: "Total", fuente: "Eventos", filtro: "Período", periodo: "2024", conjunto: "Todos", regla: "Suma", resultado: 10 }],
  hallazgos: [],
  snapshot_sha256: null,
};

describe("ExpedienteCuentaPage", () => {
  beforeEach(() => {
    apiFetchMock.mockReset();
    capacidades = new Set(["gobierno_rendicion:view", "gobierno_rendicion:form", "gobierno_rendicion:qualify"]);
  });

  it("ficha EN_FORMACION con form muestra Formar la cuenta y hechos disponibles", async () => {
    apiFetchMock.mockImplementation((path: string) => {
      if (path.includes("/opciones")) return Promise.resolve(opciones);
      if (path.includes("/candidatas")) return Promise.resolve({ items: [], total: 0, pagina: 1, por_pagina: 10 });
      if (path.includes("/reporte")) return Promise.resolve(reporte);
      if (path.includes("/historial")) return Promise.resolve({ items: [] });
      if (path.includes("/expedientes/e1")) return Promise.resolve(fichaBase);
      return Promise.reject(new Error(`Ruta inesperada: ${path}`));
    });

    renderPage();

    await waitFor(() => expect(screen.getByText("Formar la cuenta")).toBeTruthy());
    expect(screen.getByText("Hechos disponibles del período")).toBeTruthy();
  });

  it("ficha PARTICIPADA con qualify muestra calificacion y la nota no la calcula", async () => {
    apiFetchMock.mockImplementation((path: string) => {
      if (path.includes("/opciones")) return Promise.resolve(opciones);
      if (path.includes("/reporte")) return Promise.resolve(reporte);
      if (path.includes("/historial")) return Promise.resolve({ items: [] });
      if (path.includes("/expedientes/e1")) return Promise.resolve({ ...fichaBase, estado: "PARTICIPADA" });
      return Promise.reject(new Error(`Ruta inesperada: ${path}`));
    });

    renderPage();

    await waitFor(() => expect(screen.getByText("Registrar calificación del órgano de control")).toBeTruthy());
    expect(screen.getByText("KONTROL registra la calificación emitida por el órgano de control; no la calcula.")).toBeTruthy();
  });

  it("sin qualify no muestra formulario de calificacion", async () => {
    capacidades.delete("gobierno_rendicion:qualify");
    apiFetchMock.mockImplementation((path: string) => {
      if (path.includes("/opciones")) return Promise.resolve(opciones);
      if (path.includes("/reporte")) return Promise.resolve(reporte);
      if (path.includes("/historial")) return Promise.resolve({ items: [] });
      if (path.includes("/expedientes/e1")) return Promise.resolve({ ...fichaBase, estado: "PARTICIPADA" });
      return Promise.reject(new Error(`Ruta inesperada: ${path}`));
    });

    renderPage();

    await waitFor(() => expect(screen.getByText("Rendición")).toBeTruthy());
    expect(screen.queryByText("Registrar calificación del órgano de control")).toBeNull();
  });

  it("reporte provisional muestra aviso", async () => {
    apiFetchMock.mockImplementation((path: string) => {
      if (path.includes("/opciones")) return Promise.resolve(opciones);
      if (path.includes("/candidatas")) return Promise.resolve({ items: [], total: 0, pagina: 1, por_pagina: 10 });
      if (path.includes("/reporte")) return Promise.resolve(reporte);
      if (path.includes("/historial")) return Promise.resolve({ items: [] });
      if (path.includes("/expedientes/e1")) return Promise.resolve(fichaBase);
      return Promise.reject(new Error(`Ruta inesperada: ${path}`));
    });

    renderPage();

    await waitFor(() => expect(screen.getByText("Reporte provisional: cambia mientras la cuenta esté en formación")).toBeTruthy());
  });
});
