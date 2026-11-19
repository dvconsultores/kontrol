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
    {
      codigo: "A1",
      titulo: "Anexo 1",
      obligatorio: true,
      generable: true,
      incluir_generado: false,
      documento_ids: [],
      constancia: null,
      resuelto: false,
      documentos_congelados: [],
      origen: "LEGAL",
      supuesto: "N34_ART11",
      fuente: "Fuente A1",
      evidencia: "DOCUMENTO",
      declaracion: null,
      document_type_id: null,
    },
    {
      codigo: "A2",
      titulo: "Anexo 2",
      obligatorio: false,
      generable: false,
      incluir_generado: false,
      documento_ids: [],
      constancia: null,
      resuelto: true,
      documentos_congelados: [],
      origen: "POLITICA",
      supuesto: null,
      fuente: "Política",
      evidencia: "DATO",
      declaracion: "Declaración existente",
      document_type_id: "doc-type-1",
    },
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
  regla: {
    origen: "LEGAL",
    origen_etiqueta: "Norma Nacional N34",
    politica: null,
    regla_version: "v1",
    norma: {
      codigo: "N34",
      version: "1",
      titulo: "Norma N34",
      instrumento: "Instrumento",
      gaceta: "Gaceta 123",
      vigente_desde: "2024-01-01",
    },
    fecha: "2024-12-31",
    ambito: "ENTE",
    unit_id: null,
    unidad: null,
    nivel_territorial: "MUNICIPAL",
    forma_organizativa: "ALCALDIA",
    supuestos: [
      {
        codigo: "N34_ART11",
        articulo: "11",
        titulo: "Entrega",
        sujeto: "Saliente",
        vinculo: "DECLARADO",
        alcance: "ENTE",
        motivo: "Obligatorio",
        nota: null,
      },
    ],
    anexos: [
      {
        codigo: "A1",
        titulo: "Anexo 1",
        obligatorio: true,
        generable: true,
        evidencia: "DOCUMENTO",
        fuente: "Fuente A1",
        origen: "LEGAL",
        supuesto: "N34_ART11",
        document_type_id: null,
        document_type_nombre: null,
      },
      {
        codigo: "A2",
        titulo: "Anexo 2",
        obligatorio: false,
        generable: false,
        evidencia: "DATO",
        fuente: "Política",
        origen: "POLITICA",
        supuesto: null,
        document_type_id: "doc-type-1",
        document_type_nombre: "Tipo documental",
      },
    ],
    testigos: {
      levantada_por_receptor: { modalidad: "LEVANTADA_POR_RECEPTOR", testigos: 2, auditor_interno: true, fuente: "N34" },
      entrega: { minimo: 0, fuente: null },
    },
    plazos: [
      {
        hito: "ELABORACION",
        valor: 3,
        unidad: "DIAS_HABILES",
        base: "TOMA_DE_POSESION",
        fuente: "N34",
        origen: "LEGAL",
      },
    ],
    numeracion: { patron: "ACTA-{correlativo}", origen: "DEFECTO" },
    fundamentos: [],
    avisos: [],
  },
  regla_congelada: false,
  responsabilidad: null,
  plazos: [
    {
      hito: "ELABORACION",
      valor: 3,
      unidad: "DIAS_HABILES",
      base: "TOMA_DE_POSESION",
      fuente: "N34",
      origen: "LEGAL",
      base_fecha: "2024-12-31",
      vence: null,
      hecho: null,
      estado: "SIN_CALENDARIO_HABIL",
    },
    {
      hito: "REMISION_UAI",
      valor: 10,
      unidad: "DIAS_CONTINUOS",
      base: "SUSCRIPCION",
      fuente: "N34",
      origen: "LEGAL",
      base_fecha: "2024-12-31",
      vence: "2025-01-10",
      hecho: null,
      estado: "VENCIDO",
    },
  ],
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

  it("VERIFICADA muestra la verificación", () => {
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

    return expect(screen.findByText("Verificación de la UAI")).resolves.toBeTruthy();
  });

  it("AE-REG-01 muestra Regla aplicada y regla_version", () => {
    apiFetchMock.mockImplementation((path: string) => {
      if (path.includes("/historial")) return Promise.resolve({ items: [] });
      if (path.includes("/actas/a1")) return Promise.resolve({ ...fichaBase, regla_congelada: false });
      return Promise.reject(new Error(`Ruta inesperada: ${path}`));
    });

    renderPage();

    return expect(screen.findByText("Regla aplicada")).resolves.toBeTruthy();
  });

  it("AE-REG-02 plazos muestran estados", () => {
    apiFetchMock.mockImplementation((path: string) => {
      if (path.includes("/historial")) return Promise.resolve({ items: [] });
      if (path.includes("/actas/a1")) return Promise.resolve(fichaBase);
      return Promise.reject(new Error(`Ruta inesperada: ${path}`));
    });

    renderPage();

    return expect(screen.findByText("Sin calendario hábil oficial")).resolves.toBeTruthy();
  });

  it("AE-REG-03 responsabilidad con SUCESOR", () => {
    const fichaConResponsabilidad = {
      ...fichaBase,
      responsabilidad: {
        fecha_efectiva: "2025-01-01",
        ambito: "ENTE",
        unit_id: null,
        saliente: {
          assignment_id: "asg1",
          official_id: "of1",
          figura: "Directora",
          cargo_id: "c1",
          cargo: "Directora",
          desde: null,
          situacion_al_corte: "EN_EJERCICIO",
        },
        receptor: {
          official_id: "of2",
          funcionario: "Luis Paz",
          assignment_id: null,
          desde: null,
          situacion_al_corte: null,
          relacion: "SUCESOR",
        },
      },
    };

    apiFetchMock.mockImplementation((path: string) => {
      if (path.includes("/historial")) return Promise.resolve({ items: [] });
      if (path.includes("/actas/a1")) return Promise.resolve(fichaConResponsabilidad);
      return Promise.reject(new Error(`Ruta inesperada: ${path}`));
    });

    renderPage();

    return expect(screen.findByText(/Sucesor en el cargo/)).resolves.toBeTruthy();
  });

  it("AE-REG-04 anexo DECLARACION en borrador con manage", () => {
    const fichaConDeclaracion = {
      ...fichaBase,
      anexos: [
        {
          codigo: "A1",
          titulo: "Anexo 1",
          obligatorio: true,
          generable: true,
          incluir_generado: false,
          documento_ids: [],
          constancia: null,
          resuelto: false,
          documentos_congelados: [],
          origen: "LEGAL",
          supuesto: "N34_ART11",
          fuente: "Fuente A1",
          evidencia: "DECLARACION",
          declaracion: null,
          document_type_id: null,
        },
      ],
    };

    apiFetchMock.mockImplementation((path: string) => {
      if (path.includes("/historial")) return Promise.resolve({ items: [] });
      if (path.includes("/actas/a1")) return Promise.resolve(fichaConDeclaracion);
      return Promise.reject(new Error(`Ruta inesperada: ${path}`));
    });

    renderPage();

    return expect(screen.findByText("Declaración (Declaración)")).resolves.toBeTruthy();
  });
});
