import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";


const apiFetchMock = vi.fn();
vi.mock("@/api/client", async (original) => ({
  ...(await original<typeof import("@/api/client")>()),
  apiFetch: (...args: unknown[]) => apiFetchMock(...args),
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

import { PoliticaAsignacionPage } from "./PoliticaAsignacionPage";

function renderPage(
  initialEntries: string[] = ["/gobierno/ocupacion/politicas/p1"],
) {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={initialEntries}>
        <Routes>
          <Route
            path="/gobierno/ocupacion/politicas/:politicaId"
            element={<PoliticaAsignacionPage />}
          />
          <Route
            path="/gobierno/ocupacion/politicas/p2"
            element={<div>Ficha de la política p2</div>}
          />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

const catalogo = {
  figuras: [
    { codigo: "SUPLENCIA", etiqueta: "Suplencia" },
    { codigo: "ENCARGADURIA", etiqueta: "Encargaduría" },
  ],
  estados: [
    { codigo: "BORRADOR", etiqueta: "Borrador" },
    { codigo: "VIGENTE", etiqueta: "Vigente" },
    { codigo: "CERRADA", etiqueta: "Cerrada" },
  ],
  medios: [{ codigo: "GACETA", etiqueta: "Gaceta" }],
  emisor_tipos: [],
  ambitos: [],
  etapas: [],
  acciones: [],
  materias: [],
};

const detalleBase = {
  id: "p1",
  codigo: "PA-2024-01",
  numero_version: 2,
  nombre: "Política de Suplencias",
  figura: "SUPLENCIA",
  figura_etiqueta: "Suplencia",
  estado: "BORRADOR",
  estado_etiqueta: "Borrador",
  vigente_desde: "2024-01-01",
  vigente_hasta: null,
  version: 3,
  asignaciones: 2,
  descripcion: "Descripción",
  fundamento: "Fundamento",
  act_id: null,
  exige_fin: true,
  max_dias: 90,
  acto_medio: null,
  emisor_tipo: "CUALQUIERA",
  emisor_position_id: null,
  emisor_competencia_accion: null,
  emisor_competencia_materia: null,
  autorizacion_requerida: false,
  autorizacion_etiqueta: null,
  autorizacion_ambito: null,
  autorizacion_mas_de_dias: null,
  prohibe_avocacion: true,
  competencias: [],
  documentos: [],
  regla: {
    origen: "POLITICA",
    origen_etiqueta: "Política vigente",
    politica: {
      id: "p1",
      codigo: "PA-2024-01",
      numero_version: 2,
      nombre: "Política de Suplencias",
    },
    regla_version: "2",
    figura: "SUPLENCIA",
    nivel_territorial: null,
    pisos: [
      {
        codigo: "LOPPM",
        fuente: "LOPPM (G.O. 6.015 Ext., 28-12-2010), arts. 87 y 95.18",
        version: "1",
      },
    ],
    fundamentos: [],
    exige_fin: true,
    limites: [],
    acto_medio: null,
    emisor: {
      regla: "DELEGANTE",
      tipo: "CUALQUIERA",
      position_id: null,
      accion: null,
      materia: null,
    },
    autorizaciones: [
      {
        etiqueta: "Autorización del Concejo Municipal",
        ambito: "MAXIMA_AUTORIDAD",
        mas_de_dias: 15,
        fuente: "LOPPM art. 87",
      },
    ],
    competencias_permitidas: null,
    admite_avocacion: false,
    documentos: [],
  },
  historia: [
    { evento: "CREADA", version: 1, fecha: "2024-01-01", actor: null },
    { evento: "NUEVA_VERSION", version: 2, fecha: "2024-02-01", actor: "admin" },
  ],
  versiones: [
    { id: "p1", numero_version: 2, estado: "BORRADOR" },
    { id: "p0", numero_version: 1, estado: "CERRADA" },
  ],
  activada_en: null,
  cerrada_en: null,
  motivo_cierre: null,
  version_anterior_id: null,
  existe_borrador: false,
};

beforeEach(() => {
  vi.clearAllMocks();
  capacidades.clear();
  capacidades.add("gobierno_ocupacion:view");
  capacidades.add("gobierno_ocupacion:configure");
  capacidades.add("gobierno_ocupacion:activate");
  capacidades.add("gobierno_ocupacion:revoke");
});

describe("PoliticaAsignacionPage", () => {
  it("(1) pinta «Regla aplicada» con la fuente de un piso y la autorización", async () => {
    apiFetchMock.mockImplementation((url: string) => {
      if (url.includes("/catalogo")) return Promise.resolve(catalogo);
      return Promise.resolve(detalleBase);
    });

    renderPage();

    await waitFor(() =>
      expect(screen.getByText(/Regla aplicada/i)).toBeInTheDocument(),
    );

    expect(
      screen.getByText("LOPPM (G.O. 6.015 Ext., 28-12-2010), arts. 87 y 95.18"),
    ).toBeInTheDocument();
    expect(
      screen.getByText(
        "Autorización del Concejo Municipal: con más de 15 días en la suplencia de la máxima autoridad (LOPPM art. 87)",
      ),
    ).toBeInTheDocument();
  });

  it("(2) en BORRADOR muestra «Activar» y al pulsarlo hace POST a `/gobierno/ocupacion/politicas/p1/activar` con If-Match \"3\"", async () => {
    apiFetchMock.mockImplementation((url: string) => {
      if (url.includes("/catalogo")) return Promise.resolve(catalogo);
      if (url.includes("/activar")) return Promise.resolve({ ...detalleBase, estado: "VIGENTE" });
      return Promise.resolve(detalleBase);
    });

    renderPage();

    await waitFor(() =>
      expect(screen.getByRole("button", { name: "Activar" })).toBeInTheDocument(),
    );

    await userEvent.click(screen.getByRole("button", { name: "Activar" }));

    await waitFor(() => {
      const activarCall = apiFetchMock.mock.calls.find((c) =>
        String(c[0]).includes("/activar"),
      );
      expect(activarCall).toBeTruthy();
      expect(activarCall?.[0]).toBe(
        "/gobierno/ocupacion/politicas/p1/activar",
      );
      expect(activarCall?.[1]).toMatchObject({
        method: "POST",
        ifMatch: "3",
      });
    });
  });

  it("(3) en VIGENTE «Cerrar» exige motivo y envía {motivo}", async () => {
    const vigente = {
      ...detalleBase,
      estado: "VIGENTE",
      estado_etiqueta: "Vigente",
    };
    apiFetchMock.mockImplementation((url: string) => {
      if (url.includes("/catalogo")) return Promise.resolve(catalogo);
      if (url.includes("/cerrar")) return Promise.resolve(vigente);
      return Promise.resolve(vigente);
    });

    renderPage();

    await waitFor(() =>
      expect(screen.getByRole("button", { name: "Cerrar" })).toBeInTheDocument(),
    );

    await userEvent.click(screen.getByRole("button", { name: "Cerrar" }));

    const textarea = await screen.findByLabelText("Motivo del cierre");
    await userEvent.type(textarea, "Motivo válido del cierre");

    const confirmar = screen.getByRole("button", { name: "Confirmar cierre" });
    await userEvent.click(confirmar);

    await waitFor(() => {
      const cerrarCall = apiFetchMock.mock.calls.find((c) =>
        String(c[0]).includes("/cerrar"),
      );
      expect(cerrarCall).toBeTruthy();
      expect(cerrarCall?.[0]).toBe(
        "/gobierno/ocupacion/politicas/p1/cerrar",
      );
      expect(cerrarCall?.[1]).toMatchObject({
        method: "POST",
        body: { motivo: "Motivo válido del cierre" },
      });
    });
  });

  it("(4) sin pisos muestra «Ningún piso legal para esta figura en el régimen del ente»", async () => {
    const sinPisos = {
      ...detalleBase,
      regla: {
        ...detalleBase.regla,
        pisos: [],
      },
    };
    apiFetchMock.mockImplementation((url: string) => {
      if (url.includes("/catalogo")) return Promise.resolve(catalogo);
      return Promise.resolve(sinPisos);
    });

    renderPage();

    await waitFor(() =>
      expect(
        screen.getByText(
          /Ningún piso legal para esta figura en el régimen del ente/i,
        ),
      ).toBeInTheDocument(),
    );
  });

  it("(5) la historia traduce «NUEVA_VERSION» a «Nueva versión»", async () => {
    apiFetchMock.mockImplementation((url: string) => {
      if (url.includes("/catalogo")) return Promise.resolve(catalogo);
      return Promise.resolve(detalleBase);
    });

    renderPage();

    await waitFor(() =>
      expect(screen.getByText(/Historia/i)).toBeInTheDocument(),
    );

    expect(screen.getByText("Nueva versión")).toBeInTheDocument();
  });
});
