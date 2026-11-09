import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { createMemoryRouter, RouterProvider } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "@/api/client";

let mockPuede = true;
const apiFetch = vi.fn();
const notify = vi.fn();
const descargarArchivo = vi.fn();
const mensajeDeDescarga = vi.fn();

vi.mock("@/api/client", async (original) => ({
  ...(await original<typeof import("@/api/client")>()),
  apiFetch: (...args: unknown[]) => apiFetch(...args),
}));

vi.mock("@/app/contexts/NotificationContext", () => ({
  useNotifications: () => ({ notify, dismiss: vi.fn(), notifications: [] }),
}));

vi.mock("@/app/autoridad/AutoridadContext", () => ({
  useAutoridad: () => ({
    estado: "LISTA",
    tiene: () => true,
    puede: () => mockPuede,
    motivo: () => null,
    motivoDeCapacidad: () => null,
  }),
}));

vi.mock("@/api/descargas", () => ({
  descargarArchivo: (...args: unknown[]) => descargarArchivo(...args),
  mensajeDeDescarga: (...args: unknown[]) => mensajeDeDescarga(...args),
}));

import {
  ReporteDiferenciasRecepcion,
  ReportesDeRecepcion,
} from "./ReporteDiferencias";

function crearEstado(overrides: Record<string, unknown> = {}) {
  return {
    receipt_id: "r-1",
    receipt_code: "REC-001",
    state: "NO_DIFFERENCES",
    has_differences: false,
    current_snapshot_hash: "snap-1",
    lines: [],
    incidents: [],
    evidence: [],
    reports: [],
    ...overrides,
  };
}

const reporteReciente = {
  id: "rep-1",
  reference: "RD-001",
  revision: 1,
  issued_at: "2025-01-15T10:00:00Z",
  issued_by_name: "Ana Pérez",
  snapshot_hash: "snap-1",
  supersedes_id: null,
  file_name: "rd-001.pdf",
  file_size: 1024,
  is_latest: true,
};

const reporteAnterior = {
  id: "rep-0",
  reference: "RD-000",
  revision: 0,
  issued_at: "2025-01-10T10:00:00Z",
  issued_by_name: "Luis Rojas",
  snapshot_hash: "snap-0",
  supersedes_id: null,
  file_name: "rd-000.pdf",
  file_size: 1024,
  is_latest: false,
};

function renderizar(ui: React.ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>,
  );
}

function renderizarRouter(ruta: string, componente: React.ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  const router = createMemoryRouter(
    [{ path: "/", element: componente }],
    { initialEntries: [ruta] },
  );
  return {
    ...render(
      <QueryClientProvider client={queryClient}>
        <RouterProvider router={router} />
      </QueryClientProvider>,
    ),
    queryClient,
  };
}

describe("ReporteDiferenciasRecepcion", () => {
  beforeEach(() => {
    mockPuede = true;
    apiFetch.mockReset();
    notify.mockReset();
    descargarArchivo.mockReset();
    mensajeDeDescarga.mockReset();
    descargarArchivo.mockResolvedValue("rd-001.pdf");
    mensajeDeDescarga.mockReturnValue("No fue posible descargar el archivo.");
  });

  it.each([
    ["NO_DIFFERENCES", "Sin diferencias"],
    ["DIFFERENCES_WITHOUT_REPORT", "Diferencias detectadas sin reporte"],
    ["REPORT_ISSUED", "Reporte emitido"],
    ["NEW_REVISION_AVAILABLE", "Nueva revisión disponible"],
  ])("muestra la etiqueta exacta para %s", async (estado, etiqueta) => {
    apiFetch.mockResolvedValue(crearEstado({ state: estado }));

    renderizar(
      <ReporteDiferenciasRecepcion
        importacionId="i-1"
        recepcionId="r-1"
        recepcionCodigo="REC-001"
      />,
    );

    expect(await screen.findByText(etiqueta)).toBeInTheDocument();
  });

  it("muestra el botón de emitir solo en DIFFERENCES_WITHOUT_REPORT", async () => {
    apiFetch.mockResolvedValue(
      crearEstado({
        state: "DIFFERENCES_WITHOUT_REPORT",
        has_differences: true,
      }),
    );

    renderizar(
      <ReporteDiferenciasRecepcion
        importacionId="i-1"
        recepcionId="r-1"
        recepcionCodigo="REC-001"
      />,
    );

    expect(
      await screen.findByRole("button", { name: "Emitir reporte formal" }),
    ).toBeInTheDocument();
  });

  it("muestra el botón de emitir nueva revisión en NEW_REVISION_AVAILABLE", async () => {
    apiFetch.mockResolvedValue(
      crearEstado({
        state: "NEW_REVISION_AVAILABLE",
        has_differences: true,
      }),
    );

    renderizar(
      <ReporteDiferenciasRecepcion
        importacionId="i-1"
        recepcionId="r-1"
        recepcionCodigo="REC-001"
      />,
    );

    expect(
      await screen.findByRole("button", { name: "Emitir nueva revisión" }),
    ).toBeInTheDocument();
  });

  it("no muestra botón de emitir en REPORT_ISSUED", async () => {
    apiFetch.mockResolvedValue(
      crearEstado({ state: "REPORT_ISSUED", has_differences: true, reports: [reporteReciente] }),
    );

    renderizar(
      <ReporteDiferenciasRecepcion
        importacionId="i-1"
        recepcionId="r-1"
        recepcionCodigo="REC-001"
      />,
    );

    await screen.findByText("Reporte emitido");
    expect(
      screen.queryByRole("button", { name: "Emitir reporte formal" }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Emitir nueva revisión" }),
    ).not.toBeInTheDocument();
  });

  it("envía POST con expected_snapshot_hash al emitir", async () => {
    apiFetch.mockResolvedValueOnce(
      crearEstado({
        state: "DIFFERENCES_WITHOUT_REPORT",
        has_differences: true,
        current_snapshot_hash: "snap-abc",
      }),
    );
    apiFetch.mockResolvedValueOnce({
      ...reporteReciente,
      id: "rep-2",
      reference: "RD-002",
      revision: 2,
    });

    renderizar(
      <ReporteDiferenciasRecepcion
        importacionId="i-1"
        recepcionId="r-1"
        recepcionCodigo="REC-001"
      />,
    );

    const user = userEvent.setup();
    const boton = await screen.findByRole("button", {
      name: "Emitir reporte formal",
    });
    await user.click(boton);

    await waitFor(() => {
      const llamada = apiFetch.mock.calls.find(
        ([path, options]) =>
          path === "/importaciones/i-1/receipts/r-1/difference-report" &&
          options?.method === "POST",
      );
      expect(llamada).toBeTruthy();
      expect(llamada?.[1]?.body).toEqual({ expected_snapshot_hash: "snap-abc" });
    });
  });

  it("notifica warning con el texto exacto en DIFFERENCE_REPORT_STALE", async () => {
    apiFetch.mockResolvedValueOnce(
      crearEstado({
        state: "DIFFERENCES_WITHOUT_REPORT",
        has_differences: true,
        current_snapshot_hash: "snap-abc",
      }),
    );
    apiFetch.mockRejectedValueOnce(
      new ApiError(409, {
        code: "DIFFERENCE_REPORT_STALE",
        message: "x",
      }),
    );

    renderizar(
      <ReporteDiferenciasRecepcion
        importacionId="i-1"
        recepcionId="r-1"
        recepcionCodigo="REC-001"
      />,
    );

    const user = userEvent.setup();
    const boton = await screen.findByRole("button", {
      name: "Emitir reporte formal",
    });
    await user.click(boton);

    await waitFor(() => {
      expect(notify).toHaveBeenCalledWith({
        type: "warning",
        title: "La recepción cambió. Revise el estado actualizado antes de emitir.",
      });
    });
  });

  it("no muestra botón de emitir sin permiso pero sí Descargar PDF", async () => {
    mockPuede = false;
    apiFetch.mockResolvedValue(
      crearEstado({
        state: "NEW_REVISION_AVAILABLE",
        has_differences: true,
        reports: [reporteReciente],
      }),
    );

    renderizar(
      <ReporteDiferenciasRecepcion
        importacionId="i-1"
        recepcionId="r-1"
        recepcionCodigo="REC-001"
      />,
    );

    expect(await screen.findByRole("button", { name: "Descargar PDF" })).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Emitir nueva revisión" }),
    ).not.toBeInTheDocument();
  });

  it("Descargar PDF llama a descargarArchivo con la ruta exacta", async () => {
    apiFetch.mockResolvedValue(
      crearEstado({
        state: "REPORT_ISSUED",
        has_differences: true,
        reports: [reporteReciente],
      }),
    );

    renderizar(
      <ReporteDiferenciasRecepcion
        importacionId="i-1"
        recepcionId="r-1"
        recepcionCodigo="REC-001"
      />,
    );

    const user = userEvent.setup();
    const boton = await screen.findByRole("button", { name: "Descargar PDF" });
    await user.click(boton);

    await waitFor(() => {
      expect(descargarArchivo).toHaveBeenCalledWith(
        "/importaciones/i-1/difference-reports/rep-1/pdf",
        "rd-001.pdf",
      );
    });
  });

  it("muestra el historial con dos reportes", async () => {
    apiFetch.mockResolvedValue(
      crearEstado({
        state: "REPORT_ISSUED",
        has_differences: true,
        reports: [reporteReciente, reporteAnterior],
      }),
    );

    renderizar(
      <ReporteDiferenciasRecepcion
        importacionId="i-1"
        recepcionId="r-1"
        recepcionCodigo="REC-001"
      />,
    );

    const historial = await screen.findByRole("list", {
      name: "Historial de revisiones",
    });
    expect(historial).toBeInTheDocument();
    expect(within(historial).getByText("RD-001", { exact: false })).toBeInTheDocument();
    expect(within(historial).getByText("RD-000", { exact: false })).toBeInTheDocument();
  });
});

describe("ReportesDeRecepcion", () => {
  beforeEach(() => {
    apiFetch.mockReset();
  });

  it("muestra el enlace al expediente cuando import_file_id existe", async () => {
    apiFetch.mockResolvedValue({
      receipt_id: "r-1",
      receipt_code: "REC-001",
      import_file_id: "i-1",
      import_file_code: "IMP-001",
      reports: [reporteReciente],
    });

    renderizarRouter(
      "/",
      <ReportesDeRecepcion recepcionId="r-1" />,
    );

    const enlace = await screen.findByRole("link", {
      name: "Abrir expediente IMP-001",
    });
    expect(enlace).toHaveAttribute(
      "href",
      "/compras/importaciones/i-1#diferencias",
    );
  });

  it("no renderiza nada cuando import_file_id es null", async () => {
    apiFetch.mockResolvedValue({
      receipt_id: "r-1",
      receipt_code: "REC-001",
      import_file_id: null,
      import_file_code: null,
      reports: [],
    });

    const { container, queryClient } = renderizarRouter(
      "/",
      <ReportesDeRecepcion recepcionId="r-1" />,
    );

    await waitFor(() =>
      expect(
        queryClient.getQueryState(["recepciones", "r-1", "reportes-diferencias"])?.status,
      ).toBe("success"),
    );

    expect(container).toBeEmptyDOMElement();
  });
});
