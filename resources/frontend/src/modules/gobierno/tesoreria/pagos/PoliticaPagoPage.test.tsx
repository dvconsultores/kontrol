import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError } from "@/api/client";
import { PoliticaPagoPage } from "./PoliticaPagoPage";
import type { PoliticaPago, MedioPago } from "./api";

const apiFetchMock = vi.fn();

vi.mock("@/api/client", async (original) => ({
  ...(await original<typeof import("@/api/client")>()),
  apiFetch: (...args: unknown[]) => apiFetchMock(...args),
  ApiError: (await original<typeof import("@/api/client")>()).ApiError,
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
  useCompany: () => ({ activeCompanyId: "c1", activeCompany: { id: "c1", legal_name: "Ente 1" } }),
}));

vi.mock("@/app/contexts/NotificationContext", () => ({
  useNotifications: () => ({ notify: vi.fn() }),
}));

function fabricarPolitica(sobrescribir: Partial<PoliticaPago> = {}): PoliticaPago {
  return {
    id: "politica-1",
    codigo: "POL-01",
    numero_version: 1,
    nombre: "Política general",
    moneda: "USD",
    estado: "VIGENTE",
    vigente_desde: "2025-01-01",
    vigente_hasta: null,
    version: 1,
    descripcion: "Política general de pagos",
    permite_pago_parcial: true,
    preparador_competencia_accion: "PAGAR",
    preparador_competencia_materia: "TESORERIA",
    exige_cargo_autorizado_cuenta: false,
    control_duplicado: "ADVERTIR",
    fundamento: "Fundamento legal",
    act_id: null,
    tipo_regla: "BANDA",
    version_anterior_id: null,
    medios: [
      {
        id: "medio-1",
        codigo: "M-01",
        nombre: "Transferencia",
        estado: "ACTIVO",
      },
    ],
    bandas: [
      {
        orden: 1,
        monto_desde: "0.00",
        monto_hasta: "1000.00",
        requisitos: [
          { accion: "PAGAR", materia: "TESORERIA", cantidad: 2 },
        ],
      },
    ],
    documentos: [
      {
        document_type_id: "tipo-doc-1",
        etiqueta: "Comprobante",
        etapa: "AUTORIZAR",
        obligatorio: true,
      },
    ],
    historia: [
      {
        evento: "CREACION",
        numero_version: 1,
        actor_id: null,
        created_at: "2025-01-01T00:00:00Z",
      },
    ],
    ...sobrescribir,
  };
}

function fabricarMedios(): MedioPago[] {
  return [
    {
      id: "medio-1",
      codigo: "M-01",
      nombre: "Transferencia",
      descripcion: null,
      estado: "ACTIVO",
      vigente_desde: "2025-01-01",
      vigente_hasta: null,
      exige_referencia: true,
      referencia_unica: false,
      patron_referencia: "^[A-Z0-9]{8}$",
      fundamento: null,
      version: 1,
    },
    {
      id: "medio-2",
      codigo: "M-02",
      nombre: "Cheque",
      descripcion: null,
      estado: "ACTIVO",
      vigente_desde: "2025-01-01",
      vigente_hasta: null,
      exige_referencia: false,
      referencia_unica: false,
      patron_referencia: null,
      fundamento: null,
      version: 1,
    },
  ];
}

function renderEdicion(politica: PoliticaPago | null) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });

  apiFetchMock.mockImplementation(async (ruta: string, opcionesFetch?: { method?: string }) => {
    const metodo = opcionesFetch?.method ?? "GET";

    if (ruta.includes("/medios-pago") && metodo === "GET") {
      return fabricarMedios();
    }

    if (ruta.includes(`/politicas-pago/${politica?.id}`) && metodo === "GET" && politica) {
      return politica;
    }

    if (ruta.endsWith("/politicas-pago") && metodo === "POST") {
      return { id: "nueva-politica", ...(opcionesFetch?.body as Record<string, unknown>) };
    }

    if (ruta.endsWith("/politicas-pago/nueva") && metodo === "GET") {
      return null;
    }

    throw new Error(`Ruta no mockeada: ${ruta} ${metodo}`);
  });

  render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter
        initialEntries={[
          politica
            ? `/gobierno/tesoreria/politicas-pago/${politica.id}`
            : "/gobierno/tesoreria/politicas-pago/nueva",
        ]}
      >
        <Routes>
          <Route
            path="/gobierno/tesoreria/politicas-pago/nueva"
            element={<PoliticaPagoPage />}
          />
          <Route
            path="/gobierno/tesoreria/politicas-pago/:politicaId"
            element={<PoliticaPagoPage />}
          />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );

  return queryClient;
}

describe("PoliticaPagoPage", () => {
  beforeEach(() => {
    capacidades = new Set<string>();
    apiFetchMock.mockReset();
  });

  it("alta: h1 Nueva política de pago", async () => {
    capacidades = new Set(["gobierno_pagos:manage"]);
    renderEdicion(null);

    await screen.findByRole("heading", { name: "Nueva política de pago" });
  });

  it("Añadir banda crea una fila cuyo desde es el hasta de la anterior", async () => {
    capacidades = new Set(["gobierno_pagos:manage"]);
    renderEdicion(null);

    await screen.findByRole("heading", { name: "Nueva política de pago" });

    const primerDesde = screen.getAllByLabelText(/^Desde/)[0] as HTMLInputElement;
    const primerHasta = screen.getAllByLabelText(/Hasta \(vacío = sin tope\)/)[0] as HTMLInputElement;

    await userEvent.clear(primerDesde);
    await userEvent.type(primerDesde, "0.00");
    await userEvent.clear(primerHasta);
    await userEvent.type(primerHasta, "500.00");

    const botonAnadirBanda = screen.getByRole("button", { name: /Añadir banda/i });
    await userEvent.click(botonAnadirBanda);

    await waitFor(() => {
      const segundoDesde = screen.getAllByLabelText(/^Desde/)[1] as HTMLInputElement;
      expect(segundoDesde).toBeTruthy();
      expect(segundoDesde.value).toBe("500.00");
    });
  });

  it("Añadir requisito anade accion/materia/cantidad editables", async () => {
    capacidades = new Set(["gobierno_pagos:manage"]);
    renderEdicion(null);

    await screen.findByRole("heading", { name: "Nueva política de pago" });

    const botonAnadirRequisito = screen.getByRole("button", { name: /Añadir requisito/i });
    await userEvent.click(botonAnadirRequisito);

    await waitFor(() => {
      expect(screen.getAllByLabelText(/Acción del preparador/).length).toBeGreaterThan(0);
    });
    expect(screen.getAllByLabelText(/Materia del preparador/).length).toBeGreaterThan(0);
    expect(screen.getAllByLabelText(/Cantidad/).length).toBeGreaterThan(0);
  });

  it("guardar hace POST a /gobierno/tesoreria/politicas-pago con medios, bandas y documentos en el body", async () => {
    capacidades = new Set(["gobierno_pagos:manage"]);
    renderEdicion(null);

    await screen.findByRole("heading", { name: "Nueva política de pago" });

    const nombreInput = screen.getByLabelText(/^Nombre/);
    await userEvent.type(nombreInput, "Política Test");

    const desdeInput = screen.getAllByLabelText(/^Desde/)[0] as HTMLInputElement;
    const hastaInput = screen.getAllByLabelText(/Hasta \(vacío = sin tope\)/)[0] as HTMLInputElement;
    await userEvent.clear(desdeInput);
    await userEvent.type(desdeInput, "0.00");
    await userEvent.clear(hastaInput);
    await userEvent.type(hastaInput, "1000.00");

    const botonGuardar = screen.getByRole("button", { name: /^Guardar/ });
    await userEvent.click(botonGuardar);

    await waitFor(() => {
      const llamada = apiFetchMock.mock.calls.find(
        ([ruta, opciones]: [string, { method?: string }]) =>
          ruta.endsWith("/politicas-pago") && opciones?.method === "POST",
      );
      expect(llamada).toBeTruthy();
      const [, opciones] = llamada as [string, { method?: string; body?: Record<string, unknown> }];
      const body = opciones.body as Record<string, unknown>;
      expect(body).toBeInstanceOf(Object);
      expect(body).toHaveProperty("medios");
      expect(body).toHaveProperty("bandas");
      expect(body).toHaveProperty("documentos");
      expect(body.bandas).toEqual([
        {
          monto_desde: "0.00",
          monto_hasta: "1000.00",
          requisitos: [],
        },
      ]);
    });
  });

  it("ficha VIGENTE con policy muestra Cerrar y Nueva versión y no el formulario editable", async () => {
    capacidades = new Set(["gobierno_pagos:view", "gobierno_pagos:manage"]);
    const politica = fabricarPolitica({ estado: "VIGENTE" });
    renderEdicion(politica);

    await screen.findByRole("heading", { name: /Política general/ });

    expect(screen.getByRole("button", { name: /^Cerrar/ })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Nueva versión/i })).toBeInTheDocument();
    expect(screen.queryByLabelText(/^Nombre/)).not.toBeInTheDocument();
  });

  it("sin policy no muestra acciones", async () => {
    capacidades = new Set(["gobierno_pagos:view"]);
    renderEdicion(null);

    await screen.findByRole("heading", { name: "Nueva política de pago" });

    expect(screen.queryByRole("button", { name: /^Cerrar/ })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Nueva versión/i })).not.toBeInTheDocument();
  });
});
