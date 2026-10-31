import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes, useParams } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "@/api/client";

const apiFetch = vi.fn();

vi.mock("@/api/client", async (original) => ({
  ...(await original<typeof import("@/api/client")>()),
  apiFetch: (...args: unknown[]) => apiFetch(...args),
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

const notify = vi.fn();

vi.mock("@/app/contexts/NotificationContext", () => ({
  useNotifications: () => ({ notify }),
}));

vi.mock("@/app/contexts/CompanyContext", () => ({
  useCompany: () => ({
    activeCompanyId: "c1",
    activeCompany: { id: "c1", legal_name: "Contenedor 1" },
  }),
}));

vi.mock("@/modules/documentos/AdjuntosPanel", () => ({
  AdjuntosPanel: (p: { resourceType: string; resourceId: string }) => (
    <div data-testid="adjuntos">{`${p.resourceType}:${p.resourceId}`}</div>
  ),
}));

const { EjerciciosPage } = await import("./EjerciciosPage");

const LISTA = {
  items: [
    { ejercicio: 2025, estado: "CERRADA", unidades_activas: 3, publicada_en: "2025-01-10", cerrada_en: "2026-01-05" },
    { ejercicio: 2026, estado: "VIGENTE", unidades_activas: 4, publicada_en: "2026-01-08", cerrada_en: null },
    { ejercicio: 2027, estado: "BORRADOR", unidades_activas: 0, publicada_en: null, cerrada_en: null },
  ],
  total: 3,
};

function montar(): void {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={["/gobierno/estructura"]}>
        <Routes>
          <Route path="/gobierno/estructura" element={<EjerciciosPage />} />
          <Route path="/gobierno/estructura/:ejercicio" element={<DetalleEjercicio />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

function DetalleEjercicio(): React.JSX.Element {
  const { ejercicio } = useParams();
  return <p>detalle {ejercicio}</p>;
}

function responderLista(): void {
  apiFetch.mockImplementation((ruta: string) => {
    if (ruta === "/gobierno/estructuras") {
      return Promise.resolve(LISTA);
    }
    return Promise.reject(new Error(`ruta inesperada ${ruta}`));
  });
}

beforeEach(() => {
  apiFetch.mockReset();
  notify.mockReset();
  capacidades = new Set<string>();
});

describe("EjerciciosPage", () => {
  it("GEJ-01 · módulo no habilitado muestra el estado vacío", async () => {
    apiFetch.mockImplementation((ruta: string) => {
      if (ruta === "/gobierno/estructuras") {
        return Promise.reject(new ApiError(403, { code: "MODULE_NOT_ENTITLED", message: "x" }));
      }
      return Promise.reject(new Error(`ruta inesperada ${ruta}`));
    });
    montar();
    expect(await screen.findByText("El módulo de Gobierno no está habilitado")).toBeInTheDocument();
  });

  it("GEJ-02 · sin ente muestra el enlace a Configuración del ente", async () => {
    apiFetch.mockImplementation((ruta: string) => {
      if (ruta === "/gobierno/estructuras") {
        return Promise.reject(new ApiError(404, { code: "GOV_ENTITY_NOT_FOUND", message: "x" }));
      }
      return Promise.reject(new Error(`ruta inesperada ${ruta}`));
    });
    montar();
    expect(await screen.findByText("Primero configure el ente")).toBeInTheDocument();
    const enlace = screen.getByRole("link", { name: "Ir a Configuración del ente" });
    expect(enlace).toHaveAttribute("href", "/gobierno/ente");
  });

  it("GEJ-03 · lista muestra enlaces y formulario con opciones de copia", async () => {
    capacidades = new Set(["gobierno_estructura:edit"]);
    responderLista();
    montar();
    expect(await screen.findByRole("link", { name: "Estructura 2025" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Estructura 2026" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Estructura 2027" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Abrir la estructura de un ejercicio" })).toBeInTheDocument();
    const select = screen.getByLabelText("Copiar del ejercicio");
    expect(within(select).getByRole("option", { name: "No copiar: empezar vacía" })).toBeInTheDocument();
    expect(within(select).getByRole("option", { name: /2025/ })).toBeInTheDocument();
    expect(within(select).getByRole("option", { name: /2026/ })).toBeInTheDocument();
    expect(within(select).queryByRole("option", { name: /2027/ })).toBeNull();
  });

  it("GEJ-04 · sin edit no hay formulario", async () => {
    responderLista();
    montar();
    expect(await screen.findByRole("link", { name: "Estructura 2026" })).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Abrir la estructura de un ejercicio" })).toBeNull();
  });

  it("GEJ-05 · abrir estructura crea y navega al detalle", async () => {
    capacidades = new Set(["gobierno_estructura:edit"]);
    apiFetch.mockImplementation((ruta: string, opciones?: { method?: string }) => {
      if (ruta === "/gobierno/estructuras" && (!opciones?.method || opciones.method === "GET")) {
        return Promise.resolve(LISTA);
      }
      if (ruta === "/gobierno/estructuras" && opciones?.method === "POST") {
        return Promise.resolve({ id: "s1", ejercicio: 2028, estado: "BORRADOR", version: 1, unidades: [] });
      }
      return Promise.reject(new Error(`ruta inesperada ${ruta}`));
    });
    montar();
    const campo = await screen.findByLabelText(/^Ejercicio/);
    await userEvent.clear(campo);
    await userEvent.type(campo, "2028");
    await userEvent.selectOptions(screen.getByLabelText("Copiar del ejercicio"), "2026");
    await userEvent.click(screen.getByRole("button", { name: "Abrir estructura" }));
    await waitFor(() => {
      expect(apiFetch).toHaveBeenCalledWith(
        "/gobierno/estructuras",
        expect.objectContaining({ method: "POST", body: { ejercicio: 2028, copiar_de: 2026 } }),
      );
    });
    await waitFor(() => {
      expect(notify).toHaveBeenCalledWith({ type: "success", title: "Estructura abierta en borrador" });
    });
    expect(await screen.findByText("detalle 2028")).toBeInTheDocument();
  });

  it("GEJ-06 · ya existe muestra error en el campo Ejercicio", async () => {
    capacidades = new Set(["gobierno_estructura:edit"]);
    apiFetch.mockImplementation((ruta: string, opciones?: { method?: string }) => {
      if (ruta === "/gobierno/estructuras" && (!opciones?.method || opciones.method === "GET")) {
        return Promise.resolve(LISTA);
      }
      if (ruta === "/gobierno/estructuras" && opciones?.method === "POST") {
        return Promise.reject(new ApiError(409, { code: "GOV_STRUCTURE_ALREADY_EXISTS", message: "x" }));
      }
      return Promise.reject(new Error(`ruta inesperada ${ruta}`));
    });
    montar();
    const campo = await screen.findByLabelText(/^Ejercicio/);
    await userEvent.clear(campo);
    await userEvent.type(campo, "2026");
    await userEvent.click(screen.getByRole("button", { name: "Abrir estructura" }));
    expect(await screen.findByText("Ya existe la estructura de ese ejercicio")).toBeInTheDocument();
    expect(screen.getByLabelText(/^Ejercicio/)).toHaveAttribute("aria-invalid", "true");
  });
});
