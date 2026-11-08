import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router";
import { beforeEach, describe, expect, test, vi } from "vitest";

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

const notifyMock = vi.fn();
vi.mock("@/app/contexts/NotificationContext", () => ({
  useNotifications: () => ({ notify: notifyMock }),
}));

const catalogo = {
  tipos: [
    { codigo: "PERMANENTE", etiqueta: "Permanente" },
    { codigo: "ESPECIAL", etiqueta: "Especial" },
  ],
  funciones: [
    { codigo: "MIEMBRO", etiqueta: "Miembro" },
    { codigo: "SECRETARIO", etiqueta: "Secretario" },
  ],
  areas: [
    { codigo: "TECNICA", etiqueta: "Técnica" },
    { codigo: "JURIDICA", etiqueta: "Jurídica" },
  ],
  condiciones: [
    { codigo: "PRINCIPAL", etiqueta: "Principal" },
    { codigo: "SUPLENTE", etiqueta: "Suplente" },
  ],
  causas_fin: [{ codigo: "RENUNCIA", etiqueta: "Renuncia" }],
  causales: [
    { codigo: "INTERES", etiqueta: "Interés", fuente: "Ley" },
    { codigo: "PARENTESCO", etiqueta: "Parentesco", fuente: "Reglamento" },
  ],
  situaciones: [
    { codigo: "ACTIVA", etiqueta: "Activa" },
    { codigo: "EN_PROCESO", etiqueta: "En proceso" },
  ],
  regla_version: "Regla de prueba v1",
  fuente_regla: "Fuente de prueba",
};

const opciones = {
  funcionarios: [
    {
      id: "f1",
      nombre: "Persona Uno",
      cargos: ["Analista"],
      unidades: ["Unidad Uno"],
    },
    {
      id: "f2",
      nombre: "Persona Dos",
      cargos: [],
      unidades: [],
    },
  ],
  actos: [
    {
      id: "a1",
      etiqueta: "Resolución 1",
      medio: "Gaceta",
      fecha_eficacia: "2024-01-02",
      emisor: "Emisor 1",
    },
  ],
};

const detalle = {
  id: "co1",
  codigo: "CO-001",
  nombre: "Comisión de Prueba",
  tipo: "PERMANENTE",
  status: "VIGENTE",
  situacion: "ACTIVA",
  desde: "2024-01-01",
  hasta: null,
  acto: {
    id: "a1",
    etiqueta: "Resolución 1",
    medio: "Gaceta",
    fecha_eficacia: "2024-01-02",
    emisor: "Emisor 1",
  },
  miembros_principales: 1,
  miembros_total: 2,
  version: 2,
  objeto: "Objeto de prueba",
  regla_version: "Regla aplicada",
  snc_notificada_en: null,
  snc_referencia: null,
  snc_pendiente: true,
  motivo_cierre: null,
  fin_efectivo: null,
  fecha: "2024-01-10",
  es_historica: false,
  composicion: [
    {
      id: "m1",
      funcionario: {
        id: "f1",
        nombre: "Persona Uno",
        cargos: ["Analista"],
        unidades: ["Unidad Uno"],
      },
      funcion: "MIEMBRO" as const,
      area: "TECNICA",
      condicion: "PRINCIPAL" as const,
      suplente_de: null,
      suplente_de_id: null,
      desde: "2024-01-01",
      fin_efectivo: null,
      causa_fin: null,
      motivo_fin: null,
      acto: "Resolución 1",
      certificacion_snc: null,
    },
    {
      id: "m2",
      funcionario: {
        id: "f2",
        nombre: "Persona Dos",
        cargos: [],
        unidades: [],
      },
      funcion: "SECRETARIO" as const,
      area: null,
      condicion: "PRINCIPAL" as const,
      suplente_de: null,
      suplente_de_id: null,
      desde: "2024-01-01",
      fin_efectivo: null,
      causa_fin: null,
      motivo_fin: null,
      acto: "Resolución 1",
      certificacion_snc: null,
    },
  ],
  miembros: [
    {
      id: "m1",
      funcionario: {
        id: "f1",
        nombre: "Persona Uno",
        cargos: ["Analista"],
        unidades: ["Unidad Uno"],
      },
      funcion: "MIEMBRO" as const,
      area: "TECNICA",
      condicion: "PRINCIPAL" as const,
      suplente_de: null,
      suplente_de_id: null,
      desde: "2024-01-01",
      fin_efectivo: null,
      causa_fin: null,
      motivo_fin: null,
      acto: "Resolución 1",
      certificacion_snc: null,
    },
    {
      id: "m2",
      funcionario: {
        id: "f2",
        nombre: "Persona Dos",
        cargos: [],
        unidades: [],
      },
      funcion: "SECRETARIO" as const,
      area: null,
      condicion: "PRINCIPAL" as const,
      suplente_de: null,
      suplente_de_id: null,
      desde: "2024-01-01",
      fin_efectivo: null,
      causa_fin: null,
      motivo_fin: null,
      acto: "Resolución 1",
      certificacion_snc: null,
    },
  ],
  faltantes: [],
  inhibiciones: [],
  historia: [
    {
      tipo: "ACTIVACION",
      fecha: "2024-01-10",
      usuario: null,
      descripcion: "Activada con la regla",
    },
  ],
};

const { ComisionPage } = await import("./ComisionPage");

function renderPage() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });

  render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={["/gobierno/contrataciones/comisiones/co1"]}>
        <Routes>
          <Route
            path="/gobierno/contrataciones/comisiones/:comisionId"
            element={<ComisionPage />}
          />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("ComisionPage", () => {
  beforeEach(() => {
    apiFetchMock.mockImplementation((url: string) => {
      if (url.includes("/catalogo")) return Promise.resolve(catalogo);
      if (url.includes("/opciones")) return Promise.resolve(opciones);
      return Promise.resolve(detalle);
    });
  });

  test("VIGENTE con composición: muestra funcionario, cargo, área y enlace al acto", async () => {
    capacidades = new Set([
      "gobierno_comisiones:view",
      "gobierno_comisiones:manage",
      "gobierno_comisiones:activate",
      "gobierno_comisiones:close",
      "gobierno_actos:view",
    ]);
    renderPage();

    expect(await screen.findByText("Persona Uno")).toBeInTheDocument();
    expect(screen.getByText(/Analista/)).toBeInTheDocument();
    expect(screen.getByText("Técnica")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Abrir el acto" })).toHaveAttribute(
      "href",
      "/gobierno/actos/a1",
    );
  });

  test("BORRADOR con faltantes: muestra alerta y activar solo con capacidad", async () => {
    apiFetchMock.mockImplementation((url: string) => {
      if (url.includes("/catalogo")) return Promise.resolve(catalogo);
      if (url.includes("/opciones")) return Promise.resolve(opciones);
      return Promise.resolve({
        ...detalle,
        status: "BORRADOR",
        situacion: "EN_PROCESO",
        faltantes: ["Falta un secretario"],
      });
    });

    capacidades = new Set(["gobierno_comisiones:view", "gobierno_comisiones:manage"]);
    renderPage();

    expect(await screen.findByText("Para activar falta")).toBeInTheDocument();
    expect(screen.getByText("Falta un secretario")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Activar" })).not.toBeInTheDocument();

    capacidades = new Set([
      "gobierno_comisiones:view",
      "gobierno_comisiones:manage",
      "gobierno_comisiones:activate",
    ]);
    renderPage();

    expect(await screen.findByRole("button", { name: "Activar" })).toBeInTheDocument();
  });

  test("al pulsar Activar llama a /activar con If-Match", async () => {
    apiFetchMock.mockImplementation((url: string) => {
      if (url.includes("/catalogo")) return Promise.resolve(catalogo);
      if (url.includes("/opciones")) return Promise.resolve(opciones);
      return Promise.resolve({
        ...detalle,
        status: "BORRADOR",
        situacion: "EN_PROCESO",
        faltantes: [],
      });
    });

    capacidades = new Set([
      "gobierno_comisiones:view",
      "gobierno_comisiones:manage",
      "gobierno_comisiones:activate",
    ]);
    const user = userEvent.setup();
    renderPage();

    await user.click(await screen.findByRole("button", { name: "Activar" }));

    await waitFor(() => {
      expect(apiFetchMock).toHaveBeenCalledWith(
        "/gobierno/contrataciones/comisiones/co1/activar",
        expect.objectContaining({
          method: "POST",
          ifMatch: "2",
        }),
      );
    });
  });

  test("es_historica muestra aviso de composición a fecha", async () => {
    apiFetchMock.mockImplementation((url: string) => {
      if (url.includes("/catalogo")) return Promise.resolve(catalogo);
      if (url.includes("/opciones")) return Promise.resolve(opciones);
      return Promise.resolve({ ...detalle, es_historica: true, fecha: "2023-06-15" });
    });

    capacidades = new Set(["gobierno_comisiones:view"]);
    renderPage();

    expect(
      await screen.findByText(/No concede nada hoy/),
    ).toBeInTheDocument();
  });

  test("sin view muestra Sin acceso", async () => {
    capacidades = new Set();
    renderPage();

    expect(await screen.findByText("Sin acceso")).toBeInTheDocument();
  });
});
