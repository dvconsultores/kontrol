import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor, within } from "@testing-library/react";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router";

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

import { SeparacionPage } from "./SeparacionPage";
import { ETIQUETA_ACCION, ETIQUETA_MATERIA } from "@/modules/gobierno/api";

function crearDatosBase() {
  return {
    ente: "Ente de prueba",
    integridad: {
      integra: true,
      admin: {
        codigo: "ADMIN",
        nombre: "Administrador",
        capacidades: 10,
        fuera_de_lugar: [] as string[],
      },
      funcional: {
        codigo: "FUNCIONAL_COMPLETO",
        nombre: "Funcional completo",
        capacidades: 5,
        fuera_de_lugar: [] as string[],
      },
    },
    exigencia_identidad: {
      activa: false,
      version: 1,
      efecto: "La exigencia de identidad institucional está inactiva.",
    },
    administradores: [] as unknown[],
    denegaciones: [] as unknown[],
  };
}

function renderPagina() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <SeparacionPage />
      </MemoryRouter>
    </QueryClientProvider>
  );
}

describe("SeparacionPage", () => {
  beforeEach(() => {
    capacidades = new Set(["gobierno_auditoria:view"]);
    apiFetchMock.mockReset();
  });

  it("V1 pinta las tres secciones con sus h2, 'Separación íntegra', 'Exigencia de identidad institucional: Inactiva'", async () => {
    apiFetchMock.mockResolvedValue(crearDatosBase());

    renderPagina();

    await waitFor(() => {
      expect(
        screen.getByRole("heading", { name: "Integridad de la separación" })
      ).toBeInTheDocument();
    });

    expect(
      screen.getByRole("heading", { name: "Administradores técnicos" })
    ).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "Intentos denegados" })
    ).toBeInTheDocument();

    const seccionIntegridad = screen.getByRole("region", {
      name: "Integridad de la separación",
    });
    expect(within(seccionIntegridad).getByText("Separación íntegra")).toBeInTheDocument();
    expect(
      within(seccionIntegridad).getByText(
        "Exigencia de identidad institucional: Inactiva"
      )
    ).toBeInTheDocument();
  });

  it("V2 un administrador SOLO_TECNICO muestra 'Solo técnico', 'Concedido por ua', 'Sin vínculo institucional vigente' y en 'Roles de negocio' 'Ninguno'", async () => {
    const datos = crearDatosBase();
    datos.administradores = [
      {
        usuario: "tecnico1",
        estado: "ACTIVE",
        separacion: "SOLO_TECNICO",
        separacion_etiqueta: "Solo técnico",
        separacion_detalle: "No tiene roles de negocio.",
        roles: [
          {
            codigo: "ADMIN",
            nombre: "Administrador",
            protegido: true,
            tipo: "TECNICO",
            alcance: "TODAS",
            capacidades: 10,
            categorias: [],
            origen: {
              fuente: "ASIGNACION",
              actor: "ua",
              fecha: "2025-01-15T10:00:00Z",
            },
          },
        ],
        identidad: {
          vinculo_codigo: null,
          funcionario: null,
          ocupaciones: [],
          tiene_autoridad: false,
          motivo: "SIN_VINCULO",
          motivo_etiqueta: "Sin vínculo institucional vigente",
        },
      },
    ];
    apiFetchMock.mockResolvedValue(datos);

    renderPagina();

    await waitFor(() => {
      expect(screen.getByText("tecnico1")).toBeInTheDocument();
    });

    const seccionAdmin = screen.getByRole("region", {
      name: "Administradores técnicos",
    });

    expect(within(seccionAdmin).getByText("Solo técnico")).toBeInTheDocument();
    expect(within(seccionAdmin).getByText(/Concedido por ua/)).toBeInTheDocument();
    expect(
      within(seccionAdmin).getByText("Sin vínculo institucional vigente")
    ).toBeInTheDocument();

    const rolesNegocio = within(seccionAdmin).getByText("Roles de negocio");
    const articulo = rolesNegocio.closest("article");
    expect(articulo).not.toBeNull();
    expect(within(articulo as HTMLElement).getByText("Ninguno")).toBeInTheDocument();
  });

  it("V3 un administrador TECNICO_Y_FUNCIONAL_CON_AUTORIDAD muestra el funcionario y 'Aprobar · Presupuesto'", async () => {
    const datos = crearDatosBase();
    datos.administradores = [
      {
        usuario: "tecnico2",
        estado: "ACTIVE",
        separacion: "TECNICO_Y_FUNCIONAL_CON_AUTORIDAD",
        separacion_etiqueta: "Técnico y funcional con autoridad",
        separacion_detalle: "Tiene autoridad institucional.",
        roles: [
          {
            codigo: "ADMIN",
            nombre: "Administrador",
            protegido: true,
            tipo: "TECNICO",
            alcance: "TODAS",
            capacidades: 10,
            categorias: [],
            origen: {
              fuente: "INSTALACION",
              actor: null,
              fecha: null,
            },
          },
          {
            codigo: "FUNCIONAL",
            nombre: "Funcional",
            protegido: false,
            tipo: "FUNCIONAL",
            alcance: "ENTE",
            capacidades: 3,
            categorias: ["ORG-06"],
            origen: {
              fuente: "ASIGNACION",
              actor: "ua",
              fecha: "2025-01-15T10:00:00Z",
            },
          },
        ],
        identidad: {
          vinculo_codigo: "V-001",
          funcionario: "Juan Pérez",
          ocupaciones: [
            {
              cargo: "Director",
              cargo_codigo: "DIR-01",
              figura_etiqueta: "Titular",
              unidad: "Unidad de Presupuesto",
              competencias: [
                {
                  accion: "APROBAR",
                  materia: "PRESUPUESTO",
                },
              ],
            },
          ],
          tiene_autoridad: true,
          motivo: null,
          motivo_etiqueta: null,
        },
      },
    ];
    apiFetchMock.mockResolvedValue(datos);

    renderPagina();

    await waitFor(() => {
      expect(screen.getByText("tecnico2")).toBeInTheDocument();
    });

    const seccionAdmin = screen.getByRole("region", {
      name: "Administradores técnicos",
    });

    expect(within(seccionAdmin).getByText(/Juan Pérez/)).toBeInTheDocument();
    expect(
      within(seccionAdmin).getByText(
        `${ETIQUETA_ACCION.APROBAR} · ${ETIQUETA_MATERIA.PRESUPUESTO}`
      )
    ).toBeInTheDocument();
  });

  it("V4 una denegacion con en_bitacora true tiene enlace con href '/gobierno/bitacora/e1'; otra con false no tiene enlace", async () => {
    const datos = crearDatosBase();
    datos.denegaciones = [
      {
        id: "e1",
        fecha: "2025-01-15T10:00:00Z",
        usuario: "tecnico1",
        accion: "crear",
        codigo: "DENEGADO",
        codigo_etiqueta: "Denegado por falta de autoridad",
        rol: "ADMIN",
        capacidades_excedidas: ["crear_presupuesto"],
        en_bitacora: true,
      },
      {
        id: "e2",
        fecha: "2025-01-16T10:00:00Z",
        usuario: "tecnico2",
        accion: "aprobar",
        codigo: "DENEGADO",
        codigo_etiqueta: "Denegado por falta de autoridad",
        rol: null,
        capacidades_excedidas: ["aprobar_presupuesto"],
        en_bitacora: false,
      },
    ];
    apiFetchMock.mockResolvedValue(datos);

    renderPagina();

    await waitFor(() => {
      expect(screen.getAllByText("Denegado por falta de autoridad").length).toBeGreaterThan(0);
    });

    const seccionDenegaciones = screen.getByRole("region", {
      name: "Intentos denegados",
    });

    const enlaces = within(seccionDenegaciones).getAllByRole("link", {
      name: /Ver en la bitácora el intento de tecnico1/,
    });
    expect(enlaces.length).toBeGreaterThan(0);
    for (const enlace of enlaces) {
      expect(enlace).toHaveAttribute("href", "/gobierno/bitacora/e1");
    }

    expect(
      within(seccionDenegaciones).queryAllByRole("link", {
        name: /Ver en la bitácora el intento de tecnico2/,
      })
    ).toHaveLength(0);
  });

  it("V5 'Separación alterada' y la capacidad fuera de lugar cuando integra es false", async () => {
    const datos = crearDatosBase();
    datos.integridad = {
      integra: false,
      admin: {
        codigo: "ADMIN",
        nombre: "Administrador",
        capacidades: 10,
        fuera_de_lugar: ["aprobar_presupuesto"],
      },
      funcional: {
        codigo: "FUNCIONAL_COMPLETO",
        nombre: "Funcional completo",
        capacidades: 5,
        fuera_de_lugar: [] as string[],
      },
    };
    apiFetchMock.mockResolvedValue(datos);

    renderPagina();

    await waitFor(() => {
      expect(screen.getByText("Separación alterada")).toBeInTheDocument();
    });

    const seccionIntegridad = screen.getByRole("region", {
      name: "Integridad de la separación",
    });

    expect(
      within(seccionIntegridad).getByText(/aprobar_presupuesto/)
    ).toBeInTheDocument();
  });

  it("V6 sin datos: los dos estados vacios", async () => {
    apiFetchMock.mockResolvedValue(crearDatosBase());

    renderPagina();

    await waitFor(() => {
      expect(
        screen.getByText("No hay administradores técnicos con acceso a este ente.")
      ).toBeInTheDocument();
    });

    expect(screen.getByText("No hay intentos denegados.")).toBeInTheDocument();
  });
});
