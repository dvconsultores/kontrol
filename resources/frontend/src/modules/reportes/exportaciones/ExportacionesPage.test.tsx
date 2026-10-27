/**
 * ExportacionesPage: la descarga solo se pinta para quien puede GET /reporting/exports/_/download
 * y la bitácora exige audit:view (SPEC-003, READ-FR-08/14; AD-6, AD-8).
 */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";

const apiFetch = vi.fn();
const descargarArchivo = vi.fn();
const notify = vi.fn();

vi.mock("@/api/client", async (original) => ({
  ...(await original<typeof import("@/api/client")>()),
  apiFetch: (...args: unknown[]) => apiFetch(...args),
}));

vi.mock("@/api/descargas", async (original) => ({
  ...(await original<typeof import("@/api/descargas")>()),
  descargarArchivo: (...args: unknown[]) => descargarArchivo(...args),
}));

let permitidas = new Set<string>();

vi.mock("@/app/autoridad/AutoridadContext", () => ({
  useAutoridad: () => ({
    estado: "LISTA",
    tiene: () => true,
    puede: (m: string, r: string) => permitidas.has(`${m} ${r}`),
    motivo: () => null,
    motivoDeCapacidad: () => null,
  }),
}));

vi.mock("@/app/contexts/NotificationContext", () => ({
  useNotifications: () => ({ notify }),
}));

const { ExportacionesPage } = await import("./ExportacionesPage");
import { requisitoDe } from "@/app/autoridad/pantallas";
import { ApiError } from "@/api/client";

const EXPORT_SUMMARY = {
  id: "e1",
  report_key: "executive_ventas",
  format: "CSV",
  file_ref: "rep.csv",
  exported_by: "u",
  exported_at: "2026-01-01",
  status: "DONE",
};

function respuestas(): void {
  apiFetch.mockImplementation((ruta: string) => {
    if (ruta === "/reporting/exports") {
      return Promise.resolve({ items: [EXPORT_SUMMARY] });
    }
    if (ruta === "/reporting/jobs") {
      return Promise.resolve({ items: [] });
    }
    return Promise.reject(new Error(`ruta inesperada ${ruta}`));
  });
}

function montar(): void {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <ExportacionesPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  apiFetch.mockReset();
  descargarArchivo.mockReset();
  notify.mockReset();
  permitidas = new Set<string>();
});

describe("ExportacionesPage: descarga según permiso", () => {
  it("EXP-01 pinta el botón de descarga cuando puede GET /reporting/exports/_/download", async () => {
    permitidas = new Set(["GET /reporting/exports/_/download"]);
    respuestas();
    montar();
    expect(await screen.findByRole("button", { name: "Descargar rep.csv" })).toBeTruthy();
  });

  it("EXP-02 no pinta el botón de descarga sin el permiso", async () => {
    permitidas = new Set();
    respuestas();
    montar();
    await screen.findByText("rep.csv");
    expect(screen.queryByRole("button", { name: "Descargar rep.csv" })).toBeNull();
  });

  it("EXP-04 descarga y notifica éxito", async () => {
    permitidas = new Set(["GET /reporting/exports/_/download"]);
    descargarArchivo.mockResolvedValue("rep.csv");
    respuestas();
    montar();
    fireEvent.click(await screen.findByRole("button", { name: "Descargar rep.csv" }));
    await waitFor(() =>
      expect(notify).toHaveBeenCalledWith({
        type: "success",
        title: "Archivo descargado",
        description: "rep.csv",
      }),
    );
    expect(descargarArchivo).toHaveBeenCalledWith("/reporting/exports/e1/download", "exportacion-e1");
  });

  it("EXP-05 notifica error al descargar", async () => {
    permitidas = new Set(["GET /reporting/exports/_/download"]);
    descargarArchivo.mockRejectedValue(new ApiError(403, { code: "PERMISSION_DENIED" }));
    respuestas();
    montar();
    fireEvent.click(await screen.findByRole("button", { name: "Descargar rep.csv" }));
    await waitFor(() =>
      expect(notify).toHaveBeenCalledWith({
        type: "error",
        title: "No fue posible descargar",
        description: "No tiene permiso para descargar este archivo.",
      }),
    );
    expect(notify).not.toHaveBeenCalledWith(expect.objectContaining({ type: "success" }));
  });

  it("EXP-06 bloquea el doble clic hasta terminar la descarga", async () => {
    permitidas = new Set(["GET /reporting/exports/_/download"]);
    let resolver: (value: string) => void = () => undefined;
    descargarArchivo.mockImplementation(
      () =>
        new Promise<string>((resolve) => {
          resolver = resolve;
        }),
    );
    respuestas();
    montar();
    const boton = await screen.findByRole("button", { name: "Descargar rep.csv" });
    fireEvent.click(boton);
    await waitFor(() => expect(boton).toBeDisabled());
    fireEvent.click(boton);
    expect(descargarArchivo).toHaveBeenCalledTimes(1);
    resolver("rep.csv");
    await waitFor(() => expect(boton).not.toBeDisabled());
    expect(boton.isConnected).toBe(true);
  });

  it("EXP-07 el botón conserva el foco tras la descarga", async () => {
    permitidas = new Set(["GET /reporting/exports/_/download"]);
    descargarArchivo.mockResolvedValue("rep.csv");
    respuestas();
    montar();
    const boton = await screen.findByRole("button", { name: "Descargar rep.csv" });
    boton.focus();
    fireEvent.click(boton);
    await waitFor(() =>
      expect(notify).toHaveBeenCalledWith(
        expect.objectContaining({ type: "success" }),
      ),
    );
    expect(document.activeElement).toBe(boton);
    expect(boton.isConnected).toBe(true);
  });
});

describe("ExportacionesPage: registro de pantallas", () => {
  it("EXP-03 la bitácora exige audit:view", () => {
    expect(requisitoDe("reportes/auditoria")).toEqual({ capacidad: "audit:view", alcance: "empresa" });
  });
});
