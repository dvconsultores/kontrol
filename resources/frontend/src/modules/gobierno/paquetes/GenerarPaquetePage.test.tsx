import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "@/api/client";

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

const { GenerarPaquetePage } = await import("./GenerarPaquetePage");

const VISTA = {
  muestra: {
    id: "m1",
    codigo: "MU-2026-0001",
    titulo: "Muestra de prueba",
    metodo: "ESPECIFICA",
    semilla: null,
    poblacion: 10,
    tamano: 2,
    creada_en: "2026-02-01T10:00:00Z",
    creada_por: "ua",
  },
  eventos: 2,
  documentos_incluidos: 1,
  documentos_excluidos: 1,
  hallazgos: 1,
  bytes_estimados: 2048,
  documentos: [
    {
      id: "d1aaaaaaaaaaaaaaaaaaaa",
      estado: "INCLUIDO",
      motivo: null,
      version: 1,
      bytes: 2048,
      sha256: "a".repeat(64),
      referencias: [{ tipo: "evento", id: "e1" }],
    },
    {
      id: "d2bbbbbbbbbbbbbbbbbbbb",
      estado: "EXCLUIDO",
      motivo: "SIN_PERMISO",
      version: null,
      bytes: null,
      sha256: null,
      referencias: [{ tipo: "accion_correctiva", id: "a1" }],
    },
  ],
  limites: { eventos: 500, documentos: 200, bytes: 262144000 },
  excede_limite: false,
  motivo_limite: null,
  paquetes_previos: 0,
};

function renderizar(ruta: string) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[ruta]}>
        <Routes>
          <Route
            path="/gobierno/auditoria/muestras/:muestraId/paquete"
            element={<GenerarPaquetePage />}
          />
          <Route
            path="/gobierno/paquetes/:paqueteId"
            element={<p>DETALLE DEL PAQUETE</p>}
          />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  apiFetchMock.mockReset();
  notifyMock.mockReset();
  capacidades = new Set(["gobierno_paquetes:view", "gobierno_paquetes:generate"]);

  apiFetchMock.mockImplementation((url: string) => {
    if (url.endsWith("/paquete/vista-previa")) {
      return Promise.resolve(VISTA);
    }

    if (url.endsWith("/paquetes")) {
      return Promise.resolve({ id: "p1", codigo: "PA-2026-0001" });
    }

    return Promise.reject(new ApiError(500, { code: "INTERNAL", message: "x" }));
  });
});

describe("GenerarPaquetePage", () => {
  it("GPQ-01 sin gobierno_paquetes:generate → findByText('Sin acceso') y apiFetchMock NO llamado", async () => {
    capacidades = new Set(["gobierno_paquetes:view"]);

    renderizar("/gobierno/auditoria/muestras/m1/paquete");

    expect(await screen.findByText("Sin acceso")).toBeInTheDocument();
    expect(apiFetchMock).not.toHaveBeenCalled();
  });

  it("GPQ-02 vista previa: heading, textos en la región de documentos y nota de integridad", async () => {
    renderizar("/gobierno/auditoria/muestras/m1/paquete");

    expect(
      await screen.findByRole("heading", { name: "Muestra MU-2026-0001" }),
    ).toBeInTheDocument();

    const region = screen.getByRole("region", {
      name: /Tabla de documentos del paquete/,
    });

    expect(within(region).getByText("Incluido")).toBeInTheDocument();
    expect(within(region).getByText("Excluido")).toBeInTheDocument();
    expect(
      within(region).getByText("Sin permiso para el documento"),
    ).toBeInTheDocument();

    expect(
      screen.getByText(
        "La huella SHA-256 prueba la integridad del paquete; no es una firma electrónica.",
      ),
    ).toBeInTheDocument();
  });

  it("GPQ-03 propósito corto: muestra error y no llama a la API de generación", async () => {
    const usuario = userEvent.setup();
    renderizar("/gobierno/auditoria/muestras/m1/paquete");

    const entrada = await screen.findByLabelText(/^Propósito/);
    await usuario.type(entrada, "corto");
    await usuario.click(screen.getByRole("button", { name: "Generar paquete" }));

    expect(
      await screen.findByText(
        "El propósito debe tener entre 10 y 1000 caracteres",
      ),
    ).toBeInTheDocument();

    expect(apiFetchMock).not.toHaveBeenCalledWith(
      "/gobierno/auditoria/muestras/m1/paquetes",
      expect.anything(),
    );
  });

  it("GPQ-04 genera: llama a la API con body e idempotencyKey, navega y notifica", async () => {
    const usuario = userEvent.setup();
    renderizar("/gobierno/auditoria/muestras/m1/paquete");

    const entrada = await screen.findByLabelText(/^Propósito/);
    await usuario.type(entrada, "Revisión de control fiscal externo");
    await usuario.click(screen.getByRole("button", { name: "Generar paquete" }));

    await waitFor(() => {
      expect(apiFetchMock).toHaveBeenCalledWith(
        "/gobierno/auditoria/muestras/m1/paquetes",
        expect.objectContaining({
          method: "POST",
          body: { proposito: "Revisión de control fiscal externo" },
          idempotencyKey: expect.any(String),
        }),
      );
    });

    expect(await screen.findByText("DETALLE DEL PAQUETE")).toBeInTheDocument();

    await waitFor(() => {
      expect(notifyMock).toHaveBeenCalledWith(
        expect.objectContaining({ type: "success" }),
      );
    });
  });

  it("GPQ-05 límite: muestra alerta y deshabilita el botón Generar paquete", async () => {
    apiFetchMock.mockImplementation((url: string) => {
      if (url.endsWith("/paquete/vista-previa")) {
        return Promise.resolve({
          ...VISTA,
          excede_limite: true,
          motivo_limite: "Los documentos incluidos superan 250 MiB",
        });
      }

      return Promise.reject(new ApiError(500, { code: "INTERNAL", message: "x" }));
    });

    renderizar("/gobierno/auditoria/muestras/m1/paquete");

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Los documentos incluidos superan 250 MiB",
    );

    expect(screen.getByRole("button", { name: "Generar paquete" })).toBeDisabled();
  });

  it("GPQ-06 404: muestra 'Muestra no encontrada'", async () => {
    apiFetchMock.mockImplementation((url: string) => {
      if (url.endsWith("/paquete/vista-previa")) {
        return Promise.reject(
          new ApiError(404, {
            code: "GOV_AUDIT_SAMPLE_NOT_FOUND",
            message: "No existe",
          }),
        );
      }

      return Promise.reject(new ApiError(500, { code: "INTERNAL", message: "x" }));
    });

    renderizar("/gobierno/auditoria/muestras/m1/paquete");

    expect(await screen.findByText("Muestra no encontrada")).toBeInTheDocument();
  });
});
