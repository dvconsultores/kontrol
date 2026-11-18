import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "@/api/client";

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

import { PoliticaComisionPage } from "./PoliticaComisionPage";

function renderPage(initialEntries: string[] = ["/gobierno/contrataciones/politicas-comision/p1"]) {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={initialEntries}>
        <Routes>
          <Route
            path="/gobierno/contrataciones/politicas-comision/:politicaId"
            element={<PoliticaComisionPage />}
          />
          <Route
            path="/gobierno/contrataciones/politicas-comision/p2"
            element={<div>Ficha de la política p2</div>}
          />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

const itemBase = {
  id: "p1",
  codigo: "PC-2024-01",
  numero_version: 2,
  nombre: "Política de Licitaciones",
  tipo_comision: "ADJUDICACION",
  base_normativa: "LCP_ART14",
  estado: "BORRADOR",
  vigente_desde: "2024-01-01",
  vigente_hasta: null,
  aplica_apertura: true,
  aplica_recomendacion: false,
  version: 1,
  comisiones: 3,
};

const catalogo = {
  estados: [
    { codigo: "BORRADOR", etiqueta: "Borrador" },
    { codigo: "VIGENTE", etiqueta: "Vigente" },
    { codigo: "CERRADA", etiqueta: "Cerrada" },
  ],
  tipos_comision: [{ codigo: "ADJUDICACION", etiqueta: "Adjudicación" }],
  bases_normativas: [{ codigo: "LCP_ART14", etiqueta: "LCP art. 14" }],
  tipos_mayoria: [
    { codigo: "CALIFICADA", etiqueta: "Mayoría calificada" },
    { codigo: "SIMPLE", etiqueta: "Mayoría simple" },
    { codigo: "NUMERO_FIJO", etiqueta: "Número fijo de miembros" },
  ],
  bases_decision: [{ codigo: "MIEMBROS_PRESENTES", etiqueta: "Miembros presentes" }],
  funciones: [{ codigo: "COORDINADOR", etiqueta: "Coordinador" }],
  condiciones: [{ codigo: "SIN_CONDICION", etiqueta: "Sin condición" }],
  tipos_requisito: [{ codigo: "CARGO", etiqueta: "Cargo" }],
  areas: [{ codigo: "LEGAL", etiqueta: "Legal" }],
  etapas: [{ codigo: "ADMISION", etiqueta: "Admisión" }],
  medios: [],
  acciones_competencia: [],
  materias_competencia: [],
  piso_lcp: {},
};

const detalleBase = {
  ...itemBase,
  descripcion: "Descripción",
  fundamento: "Fundamento",
  min_principales: 3,
  max_principales: 5,
  exige_impar: true,
  suplente_por_principal: false,
  exige_secretario: false,
  exige_suplente_secretario: false,
  exige_presidente: false,
  quorum: { tipo: "CALIFICADA", cantidad: null, numerador: 2, denominador: 3 },
  decision: {
    tipo: "SIMPLE",
    cantidad: null,
    numerador: null,
    denominador: null,
    base: "MIEMBROS_PRESENTES",
  },
  presidente_vota: true,
  presidente_dirimente: false,
  acto_requerido: "Acto",
  acto_medio: null,
  requisitos: [
    {
      orden: 1,
      etiqueta: "Abogado",
      funcion: "COORDINADOR",
      condicion: "SIN_CONDICION",
      tipo: "CARGO",
      area: "LEGAL",
      area_etiqueta: "Legal",
      position_id: null,
      position_nombre: null,
      unit_id: null,
      unit_nombre: null,
      competencia_accion: null,
      competencia_materia: null,
      official_id: null,
      official_nombre: null,
      minimo: 1,
      maximo: 2,
    },
  ],
  documentos: [],
  regla: {},
  historia: [
    { evento: "CREADA", version: 1, fecha: "2024-01-01", actor: null },
    { evento: "SUSTITUIDA", version: 2, fecha: "2024-02-01", actor: "admin" },
  ],
  versiones: [
    { id: "p1", numero_version: 2, estado: "BORRADOR" },
    { id: "p0", numero_version: 1, estado: "CERRADA" },
  ],
  activada_en: null,
  cerrada_en: null,
  motivo_cierre: null,
  puede_editar: true,
  puede_activar: true,
  puede_cerrar: true,
  puede_versionar: true,
};

beforeEach(() => {
  vi.clearAllMocks();
  capacidades.clear();
  capacidades.add("gobierno_comisiones:view");
  capacidades.add("gobierno_comisiones:configure");
  capacidades.add("gobierno_comisiones:activate");
  capacidades.add("gobierno_comisiones:close");
});

describe("PoliticaComisionPage", () => {
  it("(a) muestra secciones, requisito con su referencia y quórum «Mayoría calificada (2/3)»", async () => {
    apiFetchMock.mockImplementation((url: string) => {
      if (url.includes("/catalogo")) return Promise.resolve(catalogo);
      return Promise.resolve(detalleBase);
    });

    renderPage();

    await waitFor(() =>
      expect(screen.getByText(/Identidad y vigencia/i)).toBeInTheDocument(),
    );

    expect(screen.getByText(/Legal/)).toBeInTheDocument();
    expect(screen.getByText(/Mayoría calificada \(2\/3\)/)).toBeInTheDocument();
  });

  it("(b) activar con 422 y details.motivos → alerta con cada motivo", async () => {
    apiFetchMock.mockImplementation((url: string) => {
      if (url.includes("/catalogo")) return Promise.resolve(catalogo);
      if (url.includes("/activar")) {
        return Promise.reject(
          new ApiError(422, {
            code: "GOV_COMMISSION_POLICY_INVALID",
            message: "La política no se puede activar",
            details: { motivos: ["Falta fundamento", "Vigencia inválida"] },
          }),
        );
      }
      return Promise.resolve(detalleBase);
    });

    renderPage();

    await waitFor(() =>
      expect(screen.getByRole("button", { name: "Activar" })).toBeInTheDocument(),
    );

    await userEvent.click(screen.getByRole("button", { name: "Activar" }));

    await waitFor(() =>
      expect(screen.getByText(/No se puede activar la política/i)).toBeInTheDocument(),
    );

    expect(screen.getByText("Falta fundamento")).toBeInTheDocument();
    expect(screen.getByText("Vigencia inválida")).toBeInTheDocument();
  });

  it("(c) activar ok → llama a apiFetch con POST y ifMatch = versión", async () => {
    apiFetchMock.mockImplementation(
      (url: string) => {
        if (url.includes("/catalogo")) return Promise.resolve(catalogo);
        if (url.includes("/activar")) return Promise.resolve(detalleBase);
        return Promise.resolve(detalleBase);
      },
    );

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
      expect(activarCall?.[1]).toMatchObject({
        method: "POST",
        ifMatch: "1",
      });
    });
  });

  it("(d) cerrar exige motivo (no llama sin motivo) y con motivo hace POST", async () => {
    apiFetchMock.mockImplementation(
      (url: string) => {
        if (url.includes("/catalogo")) return Promise.resolve(catalogo);
        if (url.includes("/cerrar")) {
          return Promise.resolve({ ...detalleBase, estado: "CERRADA" });
        }
        return Promise.resolve(detalleBase);
      },
    );

    renderPage();

    await waitFor(() =>
      expect(screen.getByRole("button", { name: "Cerrar" })).toBeInTheDocument(),
    );

    await userEvent.click(screen.getByRole("button", { name: "Cerrar" }));

    const confirmar = screen.getByRole("button", { name: "Confirmar cierre" });
    expect(confirmar).toBeDisabled();

    await userEvent.type(screen.getByLabelText("Motivo del cierre"), "Fin de período");
    await waitFor(() => expect(confirmar).not.toBeDisabled());

    await userEvent.click(confirmar);

    await waitFor(() => {
      const cerrarCall = apiFetchMock.mock.calls.find((c) =>
        String(c[0]).includes("/cerrar"),
      );
      expect(cerrarCall).toBeTruthy();
      expect(cerrarCall?.[1]).toMatchObject({
        method: "POST",
        body: { motivo: "Fin de período" },
      });
    });
  });

  it("(e) nueva versión navega a la ficha nueva", async () => {
    apiFetchMock.mockImplementation((url: string) => {
      if (url.includes("/catalogo")) return Promise.resolve(catalogo);
      if (url.includes("/nueva-version")) {
        return Promise.resolve({ ...detalleBase, id: "p2", numero_version: 3 });
      }
      return Promise.resolve(detalleBase);
    });

    renderPage();

    await waitFor(() =>
      expect(screen.getByRole("button", { name: "Nueva versión" })).toBeInTheDocument(),
    );

    await userEvent.click(screen.getByRole("button", { name: "Nueva versión" }));

    await waitFor(() =>
      expect(screen.getByText("Ficha de la política p2")).toBeInTheDocument(),
    );
  });

  it("(f) sin permiso activate no aparece «Activar»", async () => {
    capacidades.delete("gobierno_comisiones:activate");

    apiFetchMock.mockImplementation((url: string) => {
      if (url.includes("/catalogo")) return Promise.resolve(catalogo);
      return Promise.resolve(detalleBase);
    });

    renderPage();

    await waitFor(() =>
      expect(screen.getByText(/Identidad y vigencia/i)).toBeInTheDocument(),
    );

    expect(screen.queryByRole("button", { name: "Activar" })).not.toBeInTheDocument();
  });

  it("(g) historia traducida («Sustituida por una versión nueva»)", async () => {
    apiFetchMock.mockImplementation((url: string) => {
      if (url.includes("/catalogo")) return Promise.resolve(catalogo);
      return Promise.resolve(detalleBase);
    });

    renderPage();

    await waitFor(() =>
      expect(screen.getByText(/Sustituida por una versión nueva/i)).toBeInTheDocument(),
    );
  });
});
