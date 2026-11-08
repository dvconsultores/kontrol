import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "@/api/client";
import type { VinculoDetalle } from "@/modules/gobierno/api";

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

const { VinculoPage } = await import("./VinculoPage");

function renderPage() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={["/gobierno/identidad/vinculos/v1"]}>
        <Routes>
          <Route path="/gobierno/identidad/vinculos/:vinculoId" element={<VinculoPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

const cuenta = { id: "u1", usuario: "analista.prueba", estado: "ACTIVE" };
const funcionario = { id: "f1", codigo: "F-001", nombre: "Funcionario de Prueba", documento: "V-******90" };
const ente = { id: "e1", nombre: "Ente de Prueba" };
const unidad = { id: "un1", nombre: "Dirección General" };
const vinculo = { id: "v1", codigo: "VIN-001", situacion: "VIGENTE" as const };

const detalleBorrador: VinculoDetalle = {
  id: "v1",
  codigo: "VIN-001",
  status: "BORRADOR",
  situacion: "BORRADOR",
  desde: "2024-01-01",
  hasta: null,
  fin_efectivo: null,
  motivo: "Registro inicial",
  soporte: "Soporte 1",
  registrado_por: "Funcionario de Prueba",
  activado_por: null,
  activado_en: null,
  terminado_por: null,
  terminado_en: null,
  motivo_fin: null,
  version: 1,
  cuenta,
  funcionario,
  contexto: {
    es_historica: false,
    fecha: "2024-01-15",
    tiene_autoridad: true,
    motivo_sin_autoridad: null,
    ente,
    cuenta,
    vinculo,
    funcionario,
    unidades: [unidad],
    ocupaciones: [
      {
        asignacion_id: "a1",
        codigo: "OC-001",
        figura: "TITULAR",
        figura_etiqueta: "Titular",
        cargo_id: "c1",
        cargo: "Director General",
        cargo_codigo: "C-001",
        unidad_id: "un1",
        unidad: "Dirección General",
        ejercicio: 2024,
        ejerce: true,
        situacion: "VIGENTE",
        desde: "2024-01-01",
        hasta: null,
        autoridad: [{ accion: "APROBAR", materia: "PRESUPUESTO", tipo_limite: null, monto: null, moneda: null }],
        avocaciones: 0,
      },
    ],
    roles: [],
    categorias: [],
    conflictos: [],
  },
  historia: [],
};

const detalleActivo: VinculoDetalle = {
  ...detalleBorrador,
  status: "ACTIVO",
  situacion: "VIGENTE",
};

const detalleConConflictos: VinculoDetalle = {
  ...detalleBorrador,
  contexto: {
    ...detalleBorrador.contexto!,
    es_historica: false,
    tiene_autoridad: true,
    motivo_sin_autoridad: null,
    ente,
    cuenta,
    vinculo,
    funcionario,
    unidades: [unidad],
    ocupaciones: [],
    roles: [],
    categorias: [],
    conflictos: [
      {
        regla_codigo: "CONF-001",
        regla_nombre: "Conflicto de prueba",
        categoria_a: "CAT_A",
        categoria_b: "CAT_B",
      },
    ],
  },
};

const detalleHistorico: VinculoDetalle = {
  ...detalleBorrador,
  contexto: {
    ...detalleBorrador.contexto!,
    es_historica: true,
    fecha: "2024-01-15",
    tiene_autoridad: true,
    motivo_sin_autoridad: null,
    ente,
    cuenta,
    vinculo,
    funcionario,
    unidades: [unidad],
    ocupaciones: [],
    roles: [],
    categorias: [],
    conflictos: [],
  },
};

describe("VinculoPage", () => {
  beforeEach(() => {
    apiFetchMock.mockReset();
    notifyMock.mockReset();
    capacidades = new Set<string>([
      "gobierno_identidad:view",
      "gobierno_identidad:manage",
      "gobierno_identidad:activate",
      "gobierno_identidad:revoke",
    ]);
  });

  it("404 del detalle (ApiError status 404) muestra 'Vínculo no encontrado'", async () => {
    apiFetchMock.mockRejectedValueOnce(
      new ApiError(404, {
        code: "GOV_IDENTITY_LINK_NOT_FOUND",
        message: "El vínculo no existe",
      }),
    );
    renderPage();
    expect((await screen.findAllByText("Vínculo no encontrado")).length).toBeGreaterThanOrEqual(1);
  });

  it("BORRADOR con manage y activate: se ven Editar, Activar, Descartar", async () => {
    apiFetchMock.mockResolvedValueOnce(detalleBorrador);
    renderPage();
    expect(await screen.findByRole("link", { name: "Editar" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Activar" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Descartar" })).toBeInTheDocument();
  });

  it("BORRADOR sin activate no se ve Activar", async () => {
    capacidades.delete("gobierno_identidad:activate");
    apiFetchMock.mockResolvedValueOnce(detalleBorrador);
    renderPage();
    expect(await screen.findByRole("link", { name: "Editar" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Descartar" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Activar" })).not.toBeInTheDocument();
  });

  it("Activar hace POST con ifMatch igual a String(version) y muestra éxito", async () => {
    apiFetchMock.mockImplementation(async (url: string, options?: { method?: string }) => {
      if (!options?.method || options.method === "GET") {
        return detalleBorrador;
      }
      if (options.method === "POST" && url.endsWith("/activar")) {
        return { ...detalleBorrador, status: "ACTIVO" };
      }
      throw new Error(`Unexpected method ${options.method}`);
    });
    renderPage();
    const activarButton = await screen.findByRole("button", { name: "Activar" });
    await userEvent.click(activarButton);
    await waitFor(() => {
      expect(apiFetchMock).toHaveBeenCalledWith(
        "/gobierno/identidad/vinculos/v1/activar",
        {
          method: "POST",
          body: {},
          ifMatch: "1",
        },
      );
    });
    await waitFor(() => {
      expect(notifyMock).toHaveBeenCalledWith({
        type: "success",
        title: "Vínculo activado",
      });
    });
  });

  it("si activar responde ApiError 403 con code GOV_IDENTITY_SELF_ACTIVATION, el message aparece en role=alert", async () => {
    apiFetchMock.mockImplementation(async (url: string, options?: { method?: string }) => {
      if (!options?.method || options.method === "GET") {
        return detalleBorrador;
      }
      if (options.method === "POST" && url.endsWith("/activar")) {
        throw new ApiError(403, {
          code: "GOV_IDENTITY_SELF_ACTIVATION",
          message: "El actor efectivo registró el vínculo",
        });
      }
      throw new Error(`Unexpected method ${options.method}`);
    });
    renderPage();
    const activarButton = await screen.findByRole("button", { name: "Activar" });
    await userEvent.click(activarButton);
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "El actor efectivo registró el vínculo",
    );
    expect(notifyMock).not.toHaveBeenCalled();
  });

  it("ACTIVO con revoke: Cerrar abre panel en línea con Fecha y Motivo; enviar hace POST a .../cerrar con body {fecha, motivo}", async () => {
    apiFetchMock.mockImplementation(async (url: string, options?: { method?: string }) => {
      if (!options?.method || options.method === "GET") {
        return detalleActivo;
      }
      if (options.method === "POST" && url.endsWith("/cerrar")) {
        return detalleActivo;
      }
      throw new Error(`Unexpected method ${options.method}`);
    });
    renderPage();
    const cerrarButton = await screen.findByRole("button", { name: "Cerrar" });
    await userEvent.click(cerrarButton);
    expect(screen.getByRole("heading", { name: "Cerrar vínculo" })).toBeInTheDocument();
    const panelSection = screen.getByRole("region", { name: "Cerrar vínculo" });
    const fechaInput = within(panelSection).getByLabelText("Fecha");
    const motivoTextInput = within(panelSection).getByLabelText("Motivo");
    await userEvent.type(fechaInput, "2024-06-30");
    await userEvent.type(motivoTextInput, "Motivo de cierre válido");
    const submitCerrarButton = within(panelSection).getByRole("button", { name: "Cerrar" });
    await userEvent.click(submitCerrarButton);
    await waitFor(() => {
      expect(apiFetchMock).toHaveBeenCalledWith(
        "/gobierno/identidad/vinculos/v1/cerrar",
        {
          method: "POST",
          body: { fecha: "2024-06-30", motivo: "Motivo de cierre válido" },
          ifMatch: "1",
        },
      );
    });
    await waitFor(() => {
      expect(notifyMock).toHaveBeenCalledWith({
        type: "success",
        title: "Vínculo cerrado",
      });
    });
  });

  it("contexto con tiene_autoridad false y motivo SIN_OCUPACION muestra el texto de ese motivo", async () => {
    const detalleSinAutoridad: VinculoDetalle = {
      ...detalleBorrador,
      contexto: {
        ...detalleBorrador.contexto!,
        tiene_autoridad: false,
        motivo_sin_autoridad: "SIN_OCUPACION",
      },
    };
    apiFetchMock.mockResolvedValueOnce(detalleSinAutoridad);
    renderPage();
    expect(
      await screen.findByText("El funcionario no ejerce ningún cargo en esa fecha"),
    ).toBeInTheDocument();
  });

  it("contexto con conflictos muestra el aviso de conflictos", async () => {
    apiFetchMock.mockResolvedValueOnce(detalleConConflictos);
    renderPage();
    const conflictosTexts = await screen.findAllByText("Conflictos de separación de funciones");
    expect(conflictosTexts.length).toBeGreaterThanOrEqual(1);
    expect(screen.getByRole("alert")).toHaveTextContent(/CONF-001/);
  });

  it("contexto es_historica true muestra el aviso de consulta histórica", async () => {
    apiFetchMock.mockResolvedValueOnce(detalleHistorico);
    renderPage();
    expect(
      await screen.findByText(/Consulta histórica a/),
    ).toBeInTheDocument();
  });

  it("la tabla de ocupaciones muestra cargo, unidad, figura y autoridad 'APROBAR · PRESUPUESTO'", async () => {
    apiFetchMock.mockResolvedValueOnce(detalleBorrador);
    renderPage();
    expect(await screen.findByText("Director General")).toBeInTheDocument();
    expect(screen.getByText("Dirección General")).toBeInTheDocument();
    expect(screen.getByText("Titular")).toBeInTheDocument();
    expect(screen.getByText("APROBAR · PRESUPUESTO")).toBeInTheDocument();
  });

  it("cambiar la fecha consulta /gobierno/identidad/vinculos/v1?fecha=AAAA-MM-DD", async () => {
    apiFetchMock.mockImplementation(async (url: string, options?: { method?: string }) => {
      if (url.includes("?fecha=") || (!options?.method && url.endsWith("/v1"))) {
        return detalleBorrador;
      }
      throw new Error(`Unexpected URL ${url} with method ${options?.method}`);
    });
    renderPage();
    const fechaConsultaInput = await screen.findByLabelText("Consultar a la fecha");
    await userEvent.type(fechaConsultaInput, "2024-02-15");
    await waitFor(() => {
      expect(apiFetchMock).toHaveBeenCalledWith(
        "/gobierno/identidad/vinculos/v1?fecha=2024-02-15",
      );
    });
  });
});
