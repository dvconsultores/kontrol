import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter, Routes, Route } from "react-router";

const apiFetchMock = vi.fn();
vi.mock("@/api/client", async (original) => ({
  ...(await original<typeof import("@/api/client")>()),
  apiFetch: (...args: unknown[]) => apiFetchMock(...args),
}));

const descargarArchivoMock = vi.fn();
vi.mock("@/api/descargas", () => ({
  descargarArchivo: (...args: unknown[]) => descargarArchivoMock(...args),
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

vi.mock("@/modules/documentos/AdjuntosPanel", () => ({
  AdjuntosPanel: () => <div>AdjuntosPanelMock</div>,
}));

import { ActaEntregaPage } from "./ActaEntregaPage";

function renderPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={["/gobierno/actas-entrega/a1"]}>
        <Routes>
          <Route path="/gobierno/actas-entrega/:actaId" element={<ActaEntregaPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

const fichaBase = {
  id: "a1",
  codigo: "ACTA-001",
  estado: "BORRADOR",
  ambito: "UNIDAD",
  unidad: "Finanzas",
  saliente: {
    funcionario: "Ana Ruiz",
    funcionario_codigo: "F1",
    cargo: "Directora",
    cargo_codigo: "C1",
    unidad: "Finanzas",
    unidad_codigo: "U1",
    figura: "Responsable",
    asignacion_codigo: "A1",
  },
  receptor: { funcionario: "Luis Paz", funcionario_codigo: "F2" },
  fecha_corte: "2024-12-31",
  fecha_suscripcion: null,
  version: "v1",
  modalidad: "ENTREGA",
  testigos: [],
  auditor: null,
  motivo: "Cambio de gestión",
  fundamento: "Art. 1",
  lugar: "Oficina",
  anexos: [
    { codigo: "A1", titulo: "Anexo 1", obligatorio: true, generable: true, incluir_generado: false, documento_ids: [], constancia: null, resuelto: false, documentos_congelados: [] },
    { codigo: "A2", titulo: "Anexo 2", obligatorio: false, generable: false, incluir_generado: false, documento_ids: [], constancia: null, resuelto: true, documentos_congelados: [] },
  ],
  anexos_pendientes: ["A1"],
  documentos_del_acta: [{ id: "d1", title: "Doc 1" }],
  errores_deficiencias: null,
  suscrita_por: null,
  suscrita_en: null,
  snapshot_sha256: null,
  informe: null,
  remision_uai_fecha: null,
  observaciones: [],
  verificacion: null,
};

describe("ActaEntregaPage", () => {
  beforeEach(() => {
    apiFetchMock.mockReset();
    descargarArchivoMock.mockReset();
    capacidades = new Set(["gobierno_actas:view", "gobierno_actas:manage", "gobierno_actas:verify"]);
  });

  it("BORRADOR con manage muestra Suscribir acta deshabilitado si hay pendientes y el aviso", async () => {
    apiFetchMock.mockImplementation((path: string) => {
      if (path.includes("/historial")) return Promise.resolve({ items: [] });
      if (path.includes("/integridad")) return Promise.resolve({ estado: "VALIDO" });
      if (path.includes("/actas/a1")) return Promise.resolve(fichaBase);
      return Promise.reject(new Error(`Ruta inesperada: ${path}`));
    });

    renderPage();

    await waitFor(() => expect(screen.getByText("Suscribir acta")).toBeTruthy());
    expect(screen.getByText("Anexos obligatorios pendientes: A1")).toBeTruthy();
    const boton = screen.getByText("Suscribir acta").closest("button");
    expect(boton?.hasAttribute("disabled")).toBe(true);
  });

  it("BORRADOR sin manage no muestra acciones", async () => {
    capacidades.delete("gobierno_actas:manage");
    apiFetchMock.mockImplementation((path: string) => {
      if (path.includes("/historial")) return Promise.resolve({ items: [] });
      if (path.includes("/actas/a1")) return Promise.resolve(fichaBase);
      return Promise.reject(new Error(`Ruta inesperada: ${path}`));
    });

    renderPage();

    await waitFor(() => expect(screen.getByText("Sin permisos para suscribir.")).toBeTruthy());
    expect(screen.queryByText("Guardar documentos")).toBeNull();
  });

  it("SUSCRITA muestra Descargar acta (PDF) y con verify muestra Registrar verificación", async () => {
    apiFetchMock.mockImplementation((path: string) => {
      if (path.includes("/historial")) return Promise.resolve({ items: [] });
      if (path.includes("/integridad")) return Promise.resolve({ estado: "VALIDO" });
      if (path.includes("/actas/a1")) return Promise.resolve({ ...fichaBase, estado: "SUSCRITA", snapshot_sha256: "abc123", anexos_pendientes: [] });
      return Promise.reject(new Error(`Ruta inesperada: ${path}`));
    });

    renderPage();

    await waitFor(() => expect(screen.getByText("Descargar acta (PDF)")).toBeTruthy());
    expect(screen.getByText("Registrar verificación")).toBeTruthy();
  });

  it("VERIFICADA muestra la verificación", async () => {
    apiFetchMock.mockImplementation((path: string) => {
      if (path.includes("/historial")) return Promise.resolve({ items: [] });
      if (path.includes("/actas/a1")) return Promise.resolve({
        ...fichaBase,
        estado: "VERIFICADA",
        verificacion: { numero: "1", fecha: "2025-01-15", resultado: "CONFORME", fundamento: "Ok", verificada_por: "UAI", verificada_en: "2025-01-15" },
      });
      return Promise.reject(new Error(`Ruta inesperada: ${path}`));
    });

    renderPage();

    await waitFor(() => expect(screen.getByText("Verificación de la UAI")).toBeTruthy());
    expect(screen.getByText("Conforme")).toBeTruthy();
  });
});
