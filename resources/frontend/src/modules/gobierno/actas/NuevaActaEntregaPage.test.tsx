import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
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

vi.mock("@/modules/documentos/AdjuntosPanel", () => ({
  AdjuntosPanel: () => <div>AdjuntosPanelMock</div>,
}));

import { NuevaActaEntregaPage } from "./NuevaActaEntregaPage";

const reglaCompleta = {
  origen: "POLITICA",
  origen_etiqueta: "Política del ente",
  politica: {
    id: "p1",
    codigo: "POL-1",
    numero_version: 3,
    nombre: "Política de ejemplo",
  },
  regla_version: "v2",
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
      codigo: "N34_ART17",
      articulo: "17",
      titulo: "Artículo 17",
      sujeto: "Saliente",
      vinculo: "DECLARADO",
      alcance: "ENTE",
      motivo: "Obligatorio",
      nota: null,
    },
  ],
  anexos: [
    {
      codigo: "A17_1",
      titulo: "Anexo 17.1",
      obligatorio: true,
      generable: false,
      evidencia: "DOCUMENTO",
      fuente: "N34",
      origen: "LEGAL",
      supuesto: "N34_ART17",
      document_type_id: null,
      document_type_nombre: null,
    },
    {
      codigo: "A17_2",
      titulo: "Anexo 17.2",
      obligatorio: false,
      generable: false,
      evidencia: "DOCUMENTO",
      fuente: "Política",
      origen: "POLITICA",
      supuesto: null,
      document_type_id: null,
      document_type_nombre: null,
    },
    {
      codigo: "A17_3",
      titulo: "Anexo 17.3",
      obligatorio: false,
      generable: false,
      evidencia: "DOCUMENTO",
      fuente: null,
      origen: "LEGAL",
      supuesto: null,
      document_type_id: null,
      document_type_nombre: null,
    },
    {
      codigo: "A17_4",
      titulo: "Anexo 17.4",
      obligatorio: false,
      generable: false,
      evidencia: "DOCUMENTO",
      fuente: null,
      origen: "LEGAL",
      supuesto: null,
      document_type_id: null,
      document_type_nombre: null,
    },
    {
      codigo: "A17_5",
      titulo: "Anexo 17.5",
      obligatorio: false,
      generable: false,
      evidencia: "DOCUMENTO",
      fuente: null,
      origen: "LEGAL",
      supuesto: null,
      document_type_id: null,
      document_type_nombre: "Tipo de documento",
    },
  ],
  testigos: {
    levantada_por_receptor: {
      modalidad: "LEVANTADA_POR_RECEPTOR",
      testigos: 2,
      auditor_interno: true,
      fuente: "N34",
    },
    entrega: {
      minimo: 1,
      fuente: "Política",
    },
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
  numeracion: {
    patron: "ACTA-{correlativo}",
    origen: "POLITICA",
  },
  fundamentos: ["Fundamento 1"],
  avisos: ["Aviso de prueba"],
  responsabilidad: undefined,
};

function renderPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={["/gobierno/actas-entrega/nueva"]}>
        <Routes>
          <Route path="/gobierno/actas-entrega/nueva" element={<NuevaActaEntregaPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

const opciones = {
  ocupaciones: [
    {
      asignacion_id: "asg-1",
      codigo: "C1",
      funcionario: "Ana Ruiz",
      cargo: "Directora",
      unidad: "Finanzas",
      figura: "DIRECTOR",
      estado: "ACTIVA",
      desde: "2024-01-01",
      hasta: null,
      fin_efectivo: null,
      maxima_autoridad: false,
    },
  ],
  funcionarios: [
    {
      official_id: "of-1",
      codigo: "F1",
      nombre: "Luis Paz",
    },
  ],
  anexos: [
    {
      codigo: "A1",
      titulo: "Anexo 1",
      obligatorio: true,
      generable: true,
    },
  ],
  nivel_territorial: "MUNICIPAL",
};

describe("NuevaActaEntregaPage", () => {
  beforeEach(() => {
    apiFetchMock.mockReset();
    capacidades = new Set(["gobierno_actas:manage"]);
    const hoy = new Date().toISOString().slice(0, 10);
    vi.setSystemTime(new Date(`${hoy}T00:00:00`));
  });

  it("NAE-01 sin ocupación elegida muestra el texto guía y no llama a /regla", async () => {
    apiFetchMock.mockImplementation((path: string) => {
      if (path.includes("/opciones")) return Promise.resolve(opciones);
      if (path.includes("/regla")) return Promise.reject(new Error("No debe llamarse a regla sin ocupación"));
      return Promise.reject(new Error(`Ruta inesperada: ${path}`));
    });

    renderPage();

    await waitFor(() => expect(screen.getByText("Elija la ocupación saliente y la fecha de corte para ver la regla aplicada.")).toBeTruthy());

    const reglaCall = apiFetchMock.mock.calls.find((args) => typeof args[0] === "string" && (args[0] as string).includes("/regla"));
    expect(reglaCall).toBeUndefined();
  });

  it("NAE-02 ente MUNICIPAL con regla sin N34_ART17 y con el aviso", async () => {
    const reglaSinArt17 = {
      ...reglaCompleta,
      supuestos: [
        {
          codigo: "N34_ART11",
          articulo: "11",
          titulo: "Artículo 11",
          sujeto: "Saliente",
          vinculo: "DECLARADO",
          alcance: "ENTE",
          motivo: "Obligatorio",
          nota: null,
        },
      ],
      anexos: [
        {
          codigo: "A11_1",
          titulo: "Anexo 11.1",
          obligatorio: true,
          generable: false,
          evidencia: "DOCUMENTO",
          fuente: "N34",
          origen: "LEGAL",
          supuesto: "N34_ART11",
          document_type_id: null,
          document_type_nombre: null,
        },
      ],
    };

    apiFetchMock.mockImplementation((path: string) => {
      if (path.includes("/opciones")) return Promise.resolve(opciones);
      if (path.includes("/regla")) return Promise.resolve(reglaSinArt17);
      return Promise.reject(new Error(`Ruta inesperada: ${path}`));
    });

    renderPage();

    const selectOcupacion = await screen.findByLabelText(/^Ocupación saliente/);
    await screen.findByRole("option", { name: /Ana Ruiz/ });
    fireEvent.change(selectOcupacion, { target: { value: "asg-1" } });
    expect((await screen.findAllByText(/A11_1/)).length).toBeGreaterThan(0);
    expect(screen.queryByText(/A17_/)).toBeNull();
    expect(screen.getByText("Aviso de prueba")).toBeTruthy();
    expect(screen.getByRole("status")).toBeTruthy();
  });

  it("NAE-03 regla con supuesto N34_ART17 y anexos A17_1..A17_5", async () => {
    apiFetchMock.mockImplementation((path: string) => {
      if (path.includes("/opciones")) return Promise.resolve(opciones);
      if (path.includes("/regla")) return Promise.resolve(reglaCompleta);
      return Promise.reject(new Error(`Ruta inesperada: ${path}`));
    });

    renderPage();

    const selectOcupacion = await screen.findByLabelText(/^Ocupación saliente/);
    await screen.findByRole("option", { name: /Ana Ruiz/ });
    fireEvent.change(selectOcupacion, { target: { value: "asg-1" } });
    expect((await screen.findAllByText(/A17_1/)).length).toBeGreaterThan(0);
    expect(screen.getByText(/N34 art. 17/)).toBeTruthy();
  });

  it("NAE-04 regla con entrega.minimo = 1 y modalidad ENTREGA: aparece Testigo 1 - Nombre y POST lleva testigos de longitud 1", async () => {
    apiFetchMock.mockImplementation((path: string) => {
      if (path.includes("/opciones")) return Promise.resolve(opciones);
      if (path.includes("/regla")) return Promise.resolve(reglaCompleta);
      if (path.includes("/actas")) return Promise.resolve({
        id: "a1",
        codigo: "ACTA-1",
        estado: "BORRADOR",
        ambito: "ENTE",
        unidad: null,
        saliente: {
          funcionario: "Ana Ruiz",
          funcionario_codigo: "F1",
          cargo: "Directora",
          cargo_codigo: "C1",
          unidad: "Finanzas",
          unidad_codigo: "U1",
          figura: "DIRECTOR",
          asignacion_codigo: "C1",
        },
        receptor: { funcionario: "Luis Paz", funcionario_codigo: "F1" },
        fecha_corte: "2024-12-31",
        fecha_suscripcion: null,
      });
      return Promise.reject(new Error(`Ruta inesperada: ${path}`));
    });

    renderPage();

    const selectOcupacion = await screen.findByLabelText(/^Ocupación saliente/);
    await screen.findByRole("option", { name: /Ana Ruiz/ });
    fireEvent.change(selectOcupacion, { target: { value: "asg-1" } });
    await waitFor(() => expect(screen.getByLabelText(/^Testigo 1 - Nombre/)).toBeTruthy());

    const receptorSelect = screen.getByLabelText(/^Receptor/);
    fireEvent.change(receptorSelect, { target: { value: "of-1" } });

    const motivoInput = screen.getByLabelText(/^Motivo/);
    fireEvent.change(motivoInput, { target: { value: "Motivo de prueba" } });

    const fundamentoInput = screen.getByLabelText(/^Fundamento/);
    fireEvent.change(fundamentoInput, { target: { value: "Fundamento de prueba" } });

    const lugarInput = screen.getByLabelText(/^Lugar/);
    fireEvent.change(lugarInput, { target: { value: "Lugar de prueba" } });

    const testigoNombre = screen.getByLabelText(/^Testigo 1 - Nombre/);
    fireEvent.change(testigoNombre, { target: { value: "Testigo Uno" } });

    const testigoDocumento = screen.getByLabelText(/^Testigo 1 - Documento/);
    fireEvent.change(testigoDocumento, { target: { value: "12345678" } });

    const botonCrear = screen.getByText("Crear acta de entrega");
    fireEvent.click(botonCrear);

    await waitFor(() => {
      const postCall = apiFetchMock.mock.calls.find((args) => args[1] && typeof args[1] === "object" && (args[1] as { method?: string; body?: { testigos?: unknown } }).method === "POST" && typeof args[0] === "string" && (args[0] as string).includes("/actas"));
      expect(postCall).toBeTruthy();
      const body = (postCall?.[1] as { method?: string; body?: { testigos?: unknown } }).body;
      expect(body?.testigos).toEqual([{ nombre: "Testigo Uno", documento: "12345678" }]);
    });
  });
});
