import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "@/api/client";
import { PoliticaAsignacionFormPage } from "./PoliticaAsignacionFormPage";

const apiFetchMock = vi.fn();
const notifyMock = vi.fn();

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
  useCompany: () => ({ activeCompanyId: "c1", activeCompany: { id: "c1", legal_name: "Contenedor 1" } }),
}));

vi.mock("@/app/contexts/NotificationContext", () => ({
  useNotifications: () => ({ notify: notifyMock }),
}));

const catalogo = {
  figuras: [
    { codigo: "SUPLENCIA", etiqueta: "Suplencia" },
    { codigo: "TITULAR", etiqueta: "Titular" },
  ],
  estados: [
    { codigo: "BORRADOR", etiqueta: "Borrador" },
    { codigo: "VIGENTE", etiqueta: "Vigente" },
  ],
  medios: [
    { codigo: "GACETA", etiqueta: "Gaceta" },
    { codigo: "ACTA", etiqueta: "Acta" },
  ],
  emisor_tipos: [
    { codigo: "CUALQUIERA", etiqueta: "Cualquiera" },
    { codigo: "CARGO", etiqueta: "Cargo" },
    { codigo: "COMPETENCIA", etiqueta: "Competencia" },
  ],
  ambitos: [
    { codigo: "TODAS", etiqueta: "Todas" },
    { codigo: "MAXIMA_AUTORIDAD", etiqueta: "Máxima autoridad" },
  ],
  etapas: [
    { codigo: "ACTIVACION", etiqueta: "Activación" },
    { codigo: "REVOCACION", etiqueta: "Revocación" },
  ],
  acciones: [
    { codigo: "FIRMAR", etiqueta: "Firmar" },
    { codigo: "AUTORIZAR", etiqueta: "Autorizar" },
  ],
  materias: [
    { codigo: "PRESUPUESTO", etiqueta: "Presupuesto" },
    { codigo: "PERSONAL", etiqueta: "Personal" },
  ],
};

const opciones = {
  cargos: [
    { id: "cargo-1", etiqueta: "Dirección General" },
    { id: "cargo-2", etiqueta: "Secretaría" },
  ],
  tipos_documentales: [
    { id: "doc-1", etiqueta: "Gaceta" },
    { id: "doc-2", etiqueta: "Acta" },
  ],
  nivel_territorial: null,
  pisos: [
    {
      codigo: "LOPPM",
      fuente: "LOAP art. 40",
      version: "1",
      figuras: ["SUPLENCIA"],
      niveles: null,
    },
  ],
};

const detalleMock = {
  id: "p1",
  codigo: "POL-1",
  numero_version: 1,
  nombre: "Política 1",
  figura: "SUPLENCIA",
  figura_etiqueta: "Suplencia",
  estado: "BORRADOR",
  estado_etiqueta: "Borrador",
  vigente_desde: "2025-01-01",
  vigente_hasta: null,
  version: 4,
  asignaciones: 0,
  descripcion: "",
  fundamento: "",
  act_id: null,
  exige_fin: false,
  max_dias: null,
  acto_medio: null,
  emisor_tipo: "CUALQUIERA",
  emisor_position_id: null,
  emisor_competencia_accion: null,
  emisor_competencia_materia: null,
  autorizacion_requerida: false,
  autorizacion_etiqueta: null,
  autorizacion_ambito: null,
  autorizacion_mas_de_dias: null,
  prohibe_avocacion: false,
  competencias: [],
  documentos: [],
  regla: {
    origen: "POLITICA",
    origen_etiqueta: "Política",
    politica: { id: "p1", codigo: "POL-1", numero_version: 1, nombre: "Política 1" },
    regla_version: "1",
    figura: "SUPLENCIA",
    nivel_territorial: null,
    pisos: [],
    fundamentos: [],
    exige_fin: false,
    limites: [],
    acto_medio: null,
    emisor: { regla: "DELEGANTE", tipo: "CUALQUIERA", position_id: null, accion: null, materia: null },
    autorizaciones: [],
    competencias_permitidas: null,
    admite_avocacion: true,
    documentos: [],
  },
  historia: [],
  versiones: [{ id: "p1", numero_version: 1, estado: "BORRADOR" }],
  activada_en: null,
  cerrada_en: null,
  motivo_cierre: null,
  version_anterior_id: null,
  existe_borrador: false,
};

function createQueryClient() {
  return new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
}

function renderPage(initialEntries = ["/gobierno/ocupacion/politicas/nueva"]) {
  const queryClient = createQueryClient();
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={initialEntries}>
        <Routes>
          <Route path="/gobierno/ocupacion/politicas/nueva" element={<PoliticaAsignacionFormPage />} />
          <Route path="/gobierno/ocupacion/politicas/:politicaId/editar" element={<PoliticaAsignacionFormPage />} />
          <Route path="/gobierno/ocupacion/politicas/:politicaId" element={<div>Ficha de la política</div>} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>
  );
}

describe("PoliticaAsignacionFormPage", () => {
  beforeEach(() => {
    apiFetchMock.mockReset();
    notifyMock.mockReset();
    capacidades = new Set<string>();
    capacidades.add("gobierno_ocupacion:configure");
    apiFetchMock.mockImplementation(async (url: string) => {
      if (url === "/gobierno/ocupacion/politicas/catalogo") {
        return catalogo;
      }
      if (url === "/gobierno/ocupacion/politicas/opciones") {
        return opciones;
      }
      if (url === "/gobierno/ocupacion/politicas/p1") {
        return detalleMock;
      }
      throw new Error(`URL no esperada: ${url}`);
    });
  });

  it("sin configure muestra «Sin acceso» y no llama a apiFetch", () => {
    capacidades.clear();
    renderPage();
    expect(screen.getByText("Sin acceso")).toBeInTheDocument();
    expect(screen.getByText("No tiene permiso para configurar políticas de asignación.")).toBeInTheDocument();
    expect(apiFetchMock).not.toHaveBeenCalled();
  });

  it("crear SUPLENCIA con autorización «Autorización del Consejo Directivo», ámbito TODAS y 10 días → POST y navega a la ficha", async () => {
    apiFetchMock.mockImplementation(async (url: string, options?: { method?: string; body?: unknown }) => {
      if (url === "/gobierno/ocupacion/politicas/catalogo") return catalogo;
      if (url === "/gobierno/ocupacion/politicas/opciones") return opciones;
      if (url === "/gobierno/ocupacion/politicas" && options?.method === "POST") {
        return { ...detalleMock, id: "p-nueva" };
      }
      throw new Error(`URL no esperada: ${url}`);
    });

    renderPage();
    await waitFor(() => expect(screen.getByLabelText(/^Código/)).toBeInTheDocument());

    await userEvent.type(screen.getByLabelText(/^Código/), "POL-2");
    await userEvent.type(screen.getByLabelText(/^Nombre(\s|$)/), "Política 2");
    await userEvent.selectOptions(screen.getByLabelText(/^Figura/), "SUPLENCIA");
    await userEvent.type(screen.getByLabelText(/^Vigente desde/), "2025-06-01");
    await userEvent.click(screen.getByLabelText(/^Exige autorización especial/));
    await userEvent.type(screen.getByLabelText(/^Nombre de la autorización/), "Autorización del Consejo Directivo");
    await userEvent.selectOptions(screen.getByLabelText(/^Ámbito de la autorización/), "TODAS");
    await userEvent.type(screen.getByLabelText(/^Exigir con más de/), "10");
    await userEvent.click(screen.getByRole("button", { name: "Guardar borrador" }));

    await waitFor(() => expect(apiFetchMock).toHaveBeenCalledWith(
      "/gobierno/ocupacion/politicas",
      expect.objectContaining({
        method: "POST",
        body: expect.objectContaining({
          codigo: "POL-2",
          nombre: "Política 2",
          figura: "SUPLENCIA",
          autorizacion_requerida: true,
          autorizacion_etiqueta: "Autorización del Consejo Directivo",
          autorizacion_ambito: "TODAS",
          autorizacion_mas_de_dias: 10,
          emisor_tipo: "CUALQUIERA",
          emisor_position_id: null,
          emisor_competencia_accion: null,
          emisor_competencia_materia: null,
        }),
      }),
    ));

    await waitFor(() => expect(screen.getByText("Ficha de la política")).toBeInTheDocument());
  });

  it("autorización marcada sin nombre → error y sin POST", async () => {
    renderPage();
    await waitFor(() => expect(screen.getByLabelText(/^Código/)).toBeInTheDocument());

    await userEvent.type(screen.getByLabelText(/^Código/), "POL-3");
    await userEvent.type(screen.getByLabelText(/^Nombre(\s|$)/), "Política 3");
    await userEvent.selectOptions(screen.getByLabelText(/^Figura/), "SUPLENCIA");
    await userEvent.type(screen.getByLabelText(/^Vigente desde/), "2025-06-01");
    await userEvent.click(screen.getByLabelText(/^Exige autorización especial/));
    await userEvent.click(screen.getByRole("button", { name: "Guardar borrador" }));

    expect(await screen.findByText("La autorización debe tener entre 5 y 120 caracteres.")).toBeInTheDocument();
    const postLlamadas = apiFetchMock.mock.calls.filter(([, options]) => options?.method === "POST");
    expect(postLlamadas).toHaveLength(0);
  });

  it("con figura SUPLENCIA muestra fuente LOPPM; con TITULAR muestra «Ningún piso legal…»", async () => {
    renderPage();
    await waitFor(() => expect(screen.getByLabelText(/^Figura/)).toBeInTheDocument());

    await userEvent.selectOptions(screen.getByLabelText(/^Figura/), "SUPLENCIA");
    expect(await screen.findByText("LOAP art. 40")).toBeInTheDocument();
    expect(screen.getByText("Se aplican siempre; la política solo puede endurecerlos.")).toBeInTheDocument();

    await userEvent.selectOptions(screen.getByLabelText(/^Figura/), "TITULAR");
    expect(await screen.findByText("Ningún piso legal para esta figura en el régimen del ente.")).toBeInTheDocument();
  });

  it("editar carga el detalle y hace PUT con If-Match 4", async () => {
    renderPage(["/gobierno/ocupacion/politicas/p1/editar"]);
    await waitFor(() => expect(screen.getByLabelText(/^Código/)).toBeInTheDocument());
    expect(apiFetchMock).toHaveBeenCalledWith("/gobierno/ocupacion/politicas/p1");

    apiFetchMock.mockImplementation(async (url: string, options?: { method?: string; body?: unknown; ifMatch?: string }) => {
      if (url === "/gobierno/ocupacion/politicas/catalogo") return catalogo;
      if (url === "/gobierno/ocupacion/politicas/opciones") return opciones;
      if (url === "/gobierno/ocupacion/politicas/p1" && options?.method === "PUT") {
        return detalleMock;
      }
      if (url === "/gobierno/ocupacion/politicas/p1" && !options?.method) {
        return detalleMock;
      }
      throw new Error(`URL no esperada: ${url}`);
    });

    await userEvent.click(screen.getByRole("button", { name: "Guardar borrador" }));

    await waitFor(() => expect(apiFetchMock).toHaveBeenCalledWith(
      "/gobierno/ocupacion/politicas/p1",
      expect.objectContaining({
        method: "PUT",
        ifMatch: "4",
      }),
    ));
  });

  it("un 422 con fieldErrors acto_medio muestra ese texto", async () => {
    apiFetchMock.mockImplementation(async (url: string, options?: { method?: string }) => {
      if (url === "/gobierno/ocupacion/politicas/catalogo") return catalogo;
      if (url === "/gobierno/ocupacion/politicas/opciones") return opciones;
      if (url === "/gobierno/ocupacion/politicas" && options?.method === "POST") {
        throw new ApiError(422, {
          code: "VALIDATION_ERROR",
          message: "Error de validación",
          field_errors: { acto_medio: ["La LOAP art. 40 exige publicar la delegación en gaceta"] },
        });
      }
      throw new Error(`URL no esperada: ${url}`);
    });

    renderPage();
    await waitFor(() => expect(screen.getByLabelText(/^Código/)).toBeInTheDocument());

    await userEvent.type(screen.getByLabelText(/^Código/), "POL-4");
    await userEvent.type(screen.getByLabelText(/^Nombre(\s|$)/), "Política 4");
    await userEvent.selectOptions(screen.getByLabelText(/^Figura/), "SUPLENCIA");
    await userEvent.type(screen.getByLabelText(/^Vigente desde/), "2025-06-01");
    await userEvent.click(screen.getByRole("button", { name: "Guardar borrador" }));

    expect(await screen.findByText("La LOAP art. 40 exige publicar la delegación en gaceta")).toBeInTheDocument();
  });

  it("emisor «Cargo» muestra el select «Cargo emisor»", async () => {
    renderPage();
    await waitFor(() => expect(screen.getByLabelText(/^Emisor del acto/)).toBeInTheDocument());

    await userEvent.selectOptions(screen.getByLabelText(/^Emisor del acto/), "CARGO");
    expect(await screen.findByLabelText(/^Cargo emisor/)).toBeInTheDocument();
  });
});
