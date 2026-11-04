import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { MemoryRouter, Route, Routes } from "react-router";

import { ApiError } from "@/api/client";
import type { HallazgoDetalle } from "@/modules/gobierno/api";

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

vi.mock("@/app/contexts/NotificationContext", () => ({
  useNotifications: () => ({ notify: vi.fn() }),
}));

vi.mock("react-router", async (original) => {
  const actual = await original<typeof import("react-router")>();
  return {
    ...actual,
    useNavigate: () => vi.fn(),
  };
});

vi.mock("@/modules/documentos/AdjuntosPanel", () => ({
  AdjuntosPanel: () => <div data-testid="adjuntos-panel" />,
}));

const { HallazgoPage } = await import("./HallazgoPage");

const DETALLE_BASE: HallazgoDetalle = {
  id: "h1",
  codigo: "HAL-001",
  titulo: "Hallazgo de prueba",
  estado: "ABIERTO",
  riesgo: "ALTO",
  condicion: "Condición de prueba",
  criterio: "Criterio de prueba",
  causa: "Causa de prueba",
  efecto: "Efecto de prueba",
  origen: "MUESTRA",
  origen_descripcion: null,
  muestra: { id: "m1", codigo: "M-001", titulo: "Muestra de prueba" },
  partidas: ["p1"],
  created_by: "usuario-creador",
  created_at: "2026-02-15T10:30:00Z",
  version: 7,
  recomendaciones: [
    {
      id: "r1",
      orden: 1,
      texto: "Recomendación de prueba",
      created_by: "usuario-creador",
      created_at: "2026-02-15T10:30:00Z",
    },
  ],
  acciones: [
    {
      id: "a1",
      recomendacion_id: "r1",
      orden: 1,
      descripcion: "Acción de prueba",
      cargo_id: "cargo1",
      cargo_codigo: "C-001",
      cargo_denominacion: "Responsable de prueba",
      unidad_id: "u1",
      unidad_nombre: "Unidad de prueba",
      ejercicio: 2026,
      fecha_objetivo: "2026-03-15",
      porcentaje: 0,
      estado: "PENDIENTE",
      vencida: false,
      documentos: [],
      avances: [],
    },
  ],
  historia: [
    {
      id: "hist1",
      tipo: "CREADO",
      created_at: "2026-02-15T10:30:00Z",
      created_by: "usuario-creador",
      estado_desde: null,
      estado_hasta: "ABIERTO",
      detalle: null,
    },
  ],
  presentado_por: null,
  presentado_en: null,
  verificado_por: null,
  verificado_en: null,
  nota_verificacion: null,
};

function renderHallazgo(hallazgoId = "h1") {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[`/gobierno/hallazgos/${hallazgoId}`]}>
        <Routes>
          <Route
            path="/gobierno/hallazgos/:hallazgoId"
            element={<HallazgoPage />}
          />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  apiFetchMock.mockReset();
  apiFetchMock.mockImplementation((url: string) => {
    if (url === "/gobierno/hallazgos/h1") {
      return Promise.resolve(DETALLE_BASE);
    }
    return Promise.reject(
      new ApiError(500, { code: "INTERNAL", message: "Error" }),
    );
  });
  capacidades = new Set(["gobierno_hallazgos:manage"]);
});

describe("HallazgoPage", () => {
  it("HLP-01a · ABIERTO con manage y acciones: muestra «Registrar plan» habilitado", async () => {
    capacidades = new Set(["gobierno_hallazgos:manage"]);

    renderHallazgo();

    const botonRegistrarPlan = await screen.findByRole("button", {
      name: /Registrar plan/,
    });
    expect(botonRegistrarPlan).toBeEnabled();
  });

  it("HLP-01b · ABIERTO con manage y sin acciones: «Registrar plan» queda deshabilitado", async () => {
    capacidades = new Set(["gobierno_hallazgos:manage"]);

    const detalleSinAcciones: HallazgoDetalle = {
      ...DETALLE_BASE,
      acciones: [],
    };

    apiFetchMock.mockImplementation((url: string) => {
      if (url === "/gobierno/hallazgos/h1") {
        return Promise.resolve(detalleSinAcciones);
      }
      return Promise.reject(
        new ApiError(500, { code: "INTERNAL", message: "Error" }),
      );
    });

    renderHallazgo();

    const botonDeshabilitado = await screen.findByRole("button", {
      name: /Registrar plan/,
    });
    expect(botonDeshabilitado).toBeDisabled();
  });

  it("HLP-02 · EVIDENCIA_PRESENTADA con verify: «Verificar y cerrar» abre el formulario y envía POST verificar con {nota} e If-Match de la versión", async () => {
    capacidades = new Set(["gobierno_hallazgos:verify"]);

    const detalleEvidencia: HallazgoDetalle = {
      ...DETALLE_BASE,
      estado: "EVIDENCIA_PRESENTADA",
      presentado_por: "usuario-presentador",
      presentado_en: "2026-02-20T10:00:00Z",
    };

    apiFetchMock.mockImplementation((url: string) => {
      if (url === "/gobierno/hallazgos/h1") {
        return Promise.resolve(detalleEvidencia);
      }
      return Promise.reject(
        new ApiError(500, { code: "INTERNAL", message: "Error" }),
      );
    });

    renderHallazgo();

    const botonVerificar = await screen.findByRole("button", {
      name: /Verificar y cerrar/,
    });
    await userEvent.click(botonVerificar);

    const textarea = await screen.findByLabelText(/^Nota de verificación/);
    await userEvent.type(textarea, "Nota de verificación válida");

    const botonConfirmar = screen.getByRole("button", {
      name: /Confirmar verificación/,
    });
    await userEvent.click(botonConfirmar);

    await waitFor(() => {
      expect(apiFetchMock).toHaveBeenCalledWith(
        "/gobierno/hallazgos/h1/verificar",
        {
          method: "POST",
          body: { nota: "Nota de verificación válida" },
          ifMatch: "7",
        },
      );
    });
  });

  it("HLP-03 · 409 GOV_FINDING_SELF_VERIFICATION muestra el mensaje con role=\"alert\"", async () => {
    capacidades = new Set(["gobierno_hallazgos:verify"]);

    const detalleEvidencia: HallazgoDetalle = {
      ...DETALLE_BASE,
      estado: "EVIDENCIA_PRESENTADA",
      presentado_por: "usuario-presentador",
      presentado_en: "2026-02-20T10:00:00Z",
    };

    apiFetchMock.mockImplementation((url: string) => {
      if (url === "/gobierno/hallazgos/h1") {
        return Promise.resolve(detalleEvidencia);
      }
      if (url === "/gobierno/hallazgos/h1/verificar") {
        return Promise.reject(
          new ApiError(409, {
            code: "GOV_FINDING_SELF_VERIFICATION",
            message: "Conflicto de auto-verificación",
          }),
        );
      }
      return Promise.reject(
        new ApiError(500, { code: "INTERNAL", message: "Error" }),
      );
    });

    renderHallazgo();

    const botonVerificar = await screen.findByRole("button", {
      name: /Verificar y cerrar/,
    });
    await userEvent.click(botonVerificar);

    const textarea = await screen.findByLabelText(/^Nota de verificación/);
    await userEvent.type(textarea, "Nota de verificación válida");

    const botonConfirmar = screen.getByRole("button", {
      name: /Confirmar verificación/,
    });
    await userEvent.click(botonConfirmar);

    const alerta = await screen.findByRole("alert");
    expect(alerta).toHaveTextContent(
      "Quien registró la evidencia o presentó el hallazgo no puede verificarlo. Debe hacerlo otro usuario de Control Interno.",
    );
  });

  it("HLP-04 · sin gobierno_auditoria:view el origen MUESTRA se muestra como texto, sin enlace", async () => {
    capacidades = new Set(["gobierno_hallazgos:manage"]);

    renderHallazgo();

    const textoOrigen = await screen.findByText(/Muestra M-001/);
    expect(textoOrigen).toBeInTheDocument();
    expect(textoOrigen.closest("a")).toBeNull();

    expect(
      screen.getByText(/Ver evidencia de la partida 1/),
    ).toBeInTheDocument();
    expect(screen.getByText(/Ver evidencia de la partida 1/).closest("a")).toBeNull();
  });

  it("HLP-05 · 404 muestra «Hallazgo no encontrado»", async () => {
    apiFetchMock.mockImplementation((url: string) => {
      if (url === "/gobierno/hallazgos/h1") {
        return Promise.reject(
          new ApiError(404, {
            code: "GOV_FINDING_NOT_FOUND",
            message: "No encontrado",
          }),
        );
      }
      return Promise.reject(
        new ApiError(500, { code: "INTERNAL", message: "Error" }),
      );
    });

    renderHallazgo();

    expect(
      await screen.findByRole("heading", { name: /Hallazgo no encontrado/ }),
    ).toBeInTheDocument();
  });

  it("HLP-06 · EVIDENCIA_PRESENTADA sin gobierno_hallazgos:verify no muestra «Verificar y cerrar» ni «Devolver»", async () => {
    capacidades = new Set(["gobierno_hallazgos:manage"]);

    const detalleEvidencia: HallazgoDetalle = {
      ...DETALLE_BASE,
      estado: "EVIDENCIA_PRESENTADA",
      presentado_por: "usuario-presentador",
      presentado_en: "2026-02-20T10:00:00Z",
    };

    apiFetchMock.mockImplementation((url: string) => {
      if (url === "/gobierno/hallazgos/h1") {
        return Promise.resolve(detalleEvidencia);
      }
      return Promise.reject(
        new ApiError(500, { code: "INTERNAL", message: "Error" }),
      );
    });

    renderHallazgo();

    await screen.findByRole("heading", {
      level: 1,
      name: `Hallazgo ${DETALLE_BASE.codigo}`,
    });

    expect(
      screen.queryByRole("button", { name: /Verificar y cerrar/ }),
    ).toBeNull();
    expect(screen.queryByRole("button", { name: /^Devolver/ })).toBeNull();
  });
});
