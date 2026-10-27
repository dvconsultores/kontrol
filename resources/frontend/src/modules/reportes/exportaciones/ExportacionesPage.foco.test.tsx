/**
 * FOCO-01 · el botón Descargar conserva el foco tras la descarga con el NotificationProvider real (Spec 009, 02E).
 */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";

const apiFetch = vi.fn();
const descargarArchivo = vi.fn();

vi.mock("@/api/client", async (original) => ({
  ...(await original<typeof import("@/api/client")>()),
  apiFetch: (...args: unknown[]) => apiFetch(...args),
}));

vi.mock("@/api/descargas", async (original) => ({
  ...(await original<typeof import("@/api/descargas")>()),
  descargarArchivo: (...args: unknown[]) => descargarArchivo(...args),
}));

const { autoridad, permitidas } = vi.hoisted(() => {
  const permitidas = new Set<string>();
  const autoridad = {
    estado: "LISTA",
    tiene: () => true,
    puede: (m: string, r: string) => permitidas.has(`${m} ${r}`),
    motivo: () => null,
    motivoDeCapacidad: () => null,
  };
  return { autoridad, permitidas };
});

vi.mock("@/app/autoridad/AutoridadContext", () => ({
  useAutoridad: () => autoridad,
}));

const { ExportacionesPage } = await import("./ExportacionesPage");
import { NotificationProvider } from "@/app/contexts/NotificationContext";
import { NotificationViewport } from "@/components/NotificationViewport";

function renderPage() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <NotificationProvider>
        <MemoryRouter>
          <ExportacionesPage />
        </MemoryRouter>
        <NotificationViewport />
      </NotificationProvider>
    </QueryClientProvider>,
  );
}

describe("ExportacionesPage: foco del botón Descargar con NotificationProvider real", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    permitidas.clear();
    permitidas.add("GET /reporting/exports/_/download");

    apiFetch.mockImplementation((path: string) => {
      if (path === "/reporting/exports") {
        return Promise.resolve({
          items: [
            {
              id: "e1",
              report_key: "executive_ventas",
              format: "CSV",
              file_ref: "rep.csv",
              exported_by: "u",
              exported_at: "2026-01-01",
              status: "DONE",
            },
          ],
        });
      }

      if (path === "/reporting/jobs") {
        return Promise.resolve({ items: [] });
      }

      return Promise.reject(new Error(`ruta inesperada ${path}`));
    });

    descargarArchivo.mockResolvedValue("rep.csv");
  });

  it("FOCO-01 conserva el foco del botón Descargar tras la notificación real", async () => {
    renderPage();

    const boton = await screen.findByRole("button", { name: "Descargar rep.csv" });
    boton.focus();
    fireEvent.click(boton);

    await waitFor(() => expect(screen.getByText("Archivo descargado")).toBeTruthy());

    expect(boton.isConnected).toBe(true);
    expect(document.activeElement).toBe(boton);
  });
});
