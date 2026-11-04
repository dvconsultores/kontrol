import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "@/api/client";

const apiFetchMock = vi.fn();
const notifyMock = vi.fn();
const descargarArchivoMock = vi.fn();

vi.mock("@/api/client", async (original) => ({
  ...(await original<typeof import("@/api/client")>()),
  apiFetch: (...args: unknown[]) => apiFetchMock(...args),
}));

vi.mock("@/api/descargas", () => ({
  descargarArchivo: (...args: unknown[]) => descargarArchivoMock(...args),
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

const DETALLE = {
  id: "p1",
  codigo: "PA-2026-0001",
  muestra_id: "m1",
  muestra_codigo: "MU-2026-0001",
  numero_generacion: 1,
  titulo: "Paquete de auditoría · Muestra",
  generado_por: "ua",
  generado_en: "2026-02-01T10:00:00Z",
  bytes: 4096,
  huella_paquete: "e".repeat(64),
  eventos: 1,
  documentos_incluidos: 1,
  documentos_excluidos: 1,
  hallazgos: 1,
  muestra_titulo: "Muestra de prueba",
  proposito: "Revisión de control fiscal externo",
  version_manifiesto: 1,
  huella_manifiesto: "f".repeat(64),
  archivos: 7,
  nombre_archivo: "paquete-PA-2026-0001.zip",
  contenido: {
    eventos: [
      {
        orden: 1,
        id: "e1",
        fecha: "2026-02-01T09:00:00Z",
        proceso: "CTL-06",
        accion: "GOV_FINDING_CREATED",
        entidad: "GovernmentFinding",
        entidad_id: "h1",
        usuario: "ua",
        objeto: { tipo: "GovernmentFinding", id: "h1" },
        documentos: [],
      },
    ],
    documentos: [
      {
        id: "d1aaaaaaaaaaaaaaaaaaaa",
        estado: "INCLUIDO",
        motivo: null,
        version: 1,
        bytes: 2048,
        sha256: "a".repeat(64),
        referencias: [],
      },
      {
        id: "d2bbbbbbbbbbbbbbbbbbbb",
        estado: "EXCLUIDO",
        motivo: "NO_DISPONIBLE",
        version: null,
        bytes: null,
        sha256: null,
        referencias: [],
      },
    ],
    hallazgos: [
      {
        id: "h1",
        codigo: "HA-2026-0001",
        titulo: "Hallazgo de prueba",
        riesgo: "MEDIO",
        estado: "ABIERTO",
        partidas: ["e1"],
        acciones: ["a1"],
        documentos: [],
      },
    ],
  },
  verificaciones: [
    {
      id: "v1",
      resultado: "VALIDO",
      motivos: [],
      huella_archivo: "e".repeat(64),
      bytes_archivo: 4096,
      identico: true,
      verificado_por: "ub",
      verificado_en: "2026-02-02T10:00:00Z",
    },
  ],
};

function renderizar(ruta: string) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[ruta]}>
        <Routes>
          <Route path="/gobierno/paquetes/:paqueteId" element={<PaquetePage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

import { PaquetePage } from "./PaquetePage";

beforeEach(() => {
  apiFetchMock.mockReset();
  notifyMock.mockReset();
  descargarArchivoMock.mockReset();
  descargarArchivoMock.mockResolvedValue("x");
  capacidades = new Set(["gobierno_paquetes:view"]);
  apiFetchMock.mockImplementation((url: string) => {
    if (url === "/gobierno/paquetes/p1") {
      return Promise.resolve(DETALLE);
    }
    return Promise.reject(new ApiError(404, { code: "NOT_FOUND", message: "x" }));
  });
});

describe("PaquetePage", () => {
  it("PQT-01 muestra el detalle del paquete", async () => {
    renderizar("/gobierno/paquetes/p1");

    expect(await screen.findByRole("heading", { level: 1, name: "Paquete PA-2026-0001" })).toBeInTheDocument();

    expect(screen.getByText("e".repeat(64))).toBeInTheDocument();
    expect(screen.getByText("f".repeat(64))).toBeInTheDocument();
    expect(screen.getByText("Revisión de control fiscal externo")).toBeInTheDocument();

    const regionDocumentos = screen.getByRole("region", { name: /Documentos del paquete/ });
    expect(within(regionDocumentos).getByText("Incluido")).toBeInTheDocument();
    expect(within(regionDocumentos).getByText("Excluido")).toBeInTheDocument();
    expect(within(regionDocumentos).getByText("No disponible (sin analizar, alterado o ausente)")).toBeInTheDocument();
    const filas = within(regionDocumentos).getAllByRole("row");
    const filaD1 = filas.find((fila) => within(fila).queryByText(/^d1aaaaaaaaaa/));
    const filaD2 = filas.find((fila) => within(fila).queryByText(/^d2bbbbbbbbbb/));
    expect(filaD1).toBeDefined();
    expect(filaD2).toBeDefined();
    expect(within(filaD1 as HTMLElement).getByText("Incluido")).toBeInTheDocument();
    expect(within(filaD1 as HTMLElement).queryByText("Excluido")).toBeNull();
    expect(within(filaD2 as HTMLElement).getByText("Excluido")).toBeInTheDocument();
    expect(within(filaD2 as HTMLElement).getByText("No disponible (sin analizar, alterado o ausente)")).toBeInTheDocument();

    expect(screen.getByRole("link", { name: "HA-2026-0001" })).toHaveAttribute("href", "/gobierno/hallazgos/h1");
    expect(screen.getByText(/copia idéntica/)).toBeInTheDocument();
  });

  it("PQT-02 descarga el paquete y el manifiesto", async () => {
    const user = userEvent.setup();
    renderizar("/gobierno/paquetes/p1");
    await screen.findByRole("heading", { level: 1, name: "Paquete PA-2026-0001" });

    await user.click(screen.getByRole("button", { name: /Descargar paquete/ }));
    await waitFor(() => {
      expect(descargarArchivoMock).toHaveBeenCalledWith("/gobierno/paquetes/p1/descargar", "paquete-PA-2026-0001.zip");
    });

    await user.click(screen.getByRole("button", { name: /Descargar manifiesto/ }));
    await waitFor(() => {
      expect(descargarArchivoMock).toHaveBeenCalledWith("/gobierno/paquetes/p1/manifiesto", "manifiesto-PA-2026-0001.json");
    });
  });

  it("PQT-03 muestra error si la descarga está prohibida", async () => {
    descargarArchivoMock.mockRejectedValue(
      new ApiError(403, { code: "GOV_PACKAGE_DOCUMENTS_FORBIDDEN", message: "x" }),
    );
    const user = userEvent.setup();
    renderizar("/gobierno/paquetes/p1");
    await screen.findByRole("heading", { level: 1, name: "Paquete PA-2026-0001" });

    await user.click(screen.getByRole("button", { name: /Descargar paquete/ }));

    await waitFor(() => {
      expect(notifyMock).toHaveBeenCalledWith(
        expect.objectContaining({ type: "error", title: "No puede descargar el paquete" }),
      );
    });
  });

  it("PQT-04 muestra mensaje cuando el paquete no existe", async () => {
    apiFetchMock.mockRejectedValue(new ApiError(404, { code: "GOV_PACKAGE_NOT_FOUND", message: "x" }));
    renderizar("/gobierno/paquetes/p1");

    expect(await screen.findByText("Paquete no encontrado")).toBeInTheDocument();
    expect(screen.queryByRole("heading", { level: 1, name: /PA-2026/ })).toBeNull();
  });

  it("PQT-05 muestra sin acceso cuando falta la capacidad", async () => {
    capacidades = new Set();
    renderizar("/gobierno/paquetes/p1");

    expect(await screen.findByText("Sin acceso")).toBeInTheDocument();
    expect(apiFetchMock).not.toHaveBeenCalled();
  });
});
