import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
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

const { FuncionariosPage } = await import("./FuncionariosPage");

const listado = {
  items: [
    {
      id: "f1",
      codigo: "F-001",
      nombre: "Persona Uno",
      documento: "V-******90",
      estado: "ACTIVO" as const,
      version: 1,
      creado_en: "2025-01-01T00:00:00Z",
    },
  ],
  total: 1,
  pagina: 1,
  por_pagina: 10,
};

function renderPage() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={["/gobierno/ocupacion/funcionarios"]}>
        <Routes>
          <Route path="/gobierno/ocupacion/funcionarios" element={<FuncionariosPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("FuncionariosPage", () => {
  beforeEach(() => {
    apiFetchMock.mockReset();
    notifyMock.mockReset();
    capacidades = new Set<string>();
  });

  it("FP-01 · sin gobierno_ocupacion:view muestra el estado sin acceso", async () => {
    renderPage();

    expect(await screen.findByText("Sin acceso")).toBeInTheDocument();
    expect(
      screen.getByText("No tiene permiso para ver los funcionarios."),
    ).toBeInTheDocument();
    expect(apiFetchMock).not.toHaveBeenCalled();
  });

  it("FP-02 · con view muestra la lista con documento enmascarado", async () => {
    capacidades.add("gobierno_ocupacion:view");
    apiFetchMock.mockImplementation((ruta: string) => {
      if (ruta.startsWith("/gobierno/ocupacion/funcionarios")) {
        return Promise.resolve(listado);
      }
      return Promise.reject(new Error("Ruta inesperada"));
    });

    renderPage();

    expect(await screen.findByText("Persona Uno")).toBeInTheDocument();
    expect(screen.getByText("V-******90")).toBeInTheDocument();
    expect(screen.getByText("F-001")).toBeInTheDocument();
    expect(screen.getByRole("cell", { name: "Activo" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Abrir el funcionario F-001" })).toBeInTheDocument();
  });

  it("FP-03 · con view sin manage no muestra el formulario de alta", async () => {
    capacidades.add("gobierno_ocupacion:view");
    apiFetchMock.mockImplementation((ruta: string) => {
      if (ruta.startsWith("/gobierno/ocupacion/funcionarios")) {
        return Promise.resolve(listado);
      }
      return Promise.reject(new Error("Ruta inesperada"));
    });

    renderPage();

    expect(await screen.findByText("Persona Uno")).toBeInTheDocument();
    expect(
      screen.queryByRole("heading", { name: "Registrar funcionario" }),
    ).not.toBeInTheDocument();
  });

  it("FP-04 · alta válida hace POST y notifica y limpia campos", async () => {
    capacidades.add("gobierno_ocupacion:view");
    capacidades.add("gobierno_ocupacion:manage");
    apiFetchMock.mockImplementation((ruta: string, opciones?: { method?: string }) => {
      if (ruta.startsWith("/gobierno/ocupacion/funcionarios") && (!opciones?.method || opciones.method === "GET")) {
        return Promise.resolve(listado);
      }
      if (ruta === "/gobierno/ocupacion/funcionarios" && opciones?.method === "POST") {
        return Promise.resolve({});
      }
      return Promise.reject(new Error("Ruta inesperada"));
    });

    renderPage();

    const usuario = userEvent.setup();

    const nombreInput = await screen.findByLabelText(/^Nombre completo/);
    const tipoSelect = screen.getByLabelText(/^Tipo de documento/);
    const numeroInput = screen.getByLabelText(/^Número de documento/);

    await usuario.type(nombreInput, "Persona Nueva");
    await usuario.selectOptions(tipoSelect, "V");
    await usuario.type(numeroInput, "12345678");

    await usuario.click(screen.getByRole("button", { name: "Registrar funcionario" }));

    await waitFor(() => {
      expect(apiFetchMock).toHaveBeenCalledWith(
        "/gobierno/ocupacion/funcionarios",
        expect.objectContaining({
          method: "POST",
          body: {
            nombre: "Persona Nueva",
            tipo_documento: "V",
            numero_documento: "12345678",
          },
        }),
      );
    });

    await waitFor(() => {
      expect(notifyMock).toHaveBeenCalledWith({
        type: "success",
        title: "Funcionario registrado",
      });
    });

    await waitFor(() => {
      expect(screen.getByLabelText(/^Nombre completo/)).toHaveValue("");
      expect(screen.getByLabelText(/^Número de documento/)).toHaveValue("");
    });
  });

  it("FP-05 · 409 GOV_OFFICIAL_DUPLICATE muestra mensaje en role=alert", async () => {
    capacidades.add("gobierno_ocupacion:view");
    capacidades.add("gobierno_ocupacion:manage");
    const error409 = new ApiError(409, {
      code: "GOV_OFFICIAL_DUPLICATE",
      message: "Ya existe un funcionario con el mismo documento.",
    });
    apiFetchMock.mockImplementation((ruta: string, opciones?: { method?: string }) => {
      if (ruta.startsWith("/gobierno/ocupacion/funcionarios") && (!opciones?.method || opciones.method === "GET")) {
        return Promise.resolve(listado);
      }
      if (ruta === "/gobierno/ocupacion/funcionarios" && opciones?.method === "POST") {
        return Promise.reject(error409);
      }
      return Promise.reject(new Error("Ruta inesperada"));
    });

    renderPage();

    const usuario = userEvent.setup();

    const nombreInput = await screen.findByLabelText(/^Nombre completo/);
    const numeroInput = screen.getByLabelText(/^Número de documento/);

    await usuario.type(nombreInput, "Persona Uno");
    await usuario.type(numeroInput, "12345678");
    await usuario.click(screen.getByRole("button", { name: "Registrar funcionario" }));

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("Ya existe un funcionario con el mismo documento.");
  });

  it("FP-06 · 422 VALIDATION_ERROR muestra el error del campo", async () => {
    capacidades.add("gobierno_ocupacion:view");
    capacidades.add("gobierno_ocupacion:manage");
    const error422 = new ApiError(422, {
      code: "VALIDATION_ERROR",
      message: "Error de validación",
      field_errors: {
        nombre: ["El nombre es obligatorio."],
      },
    });
    apiFetchMock.mockImplementation((ruta: string, opciones?: { method?: string }) => {
      if (ruta.startsWith("/gobierno/ocupacion/funcionarios") && (!opciones?.method || opciones.method === "GET")) {
        return Promise.resolve(listado);
      }
      if (ruta === "/gobierno/ocupacion/funcionarios" && opciones?.method === "POST") {
        return Promise.reject(error422);
      }
      return Promise.reject(new Error("Ruta inesperada"));
    });

    renderPage();

    const usuario = userEvent.setup();

    const nombreInput = await screen.findByLabelText(/^Nombre completo/);
    const numeroInput = screen.getByLabelText(/^Número de documento/);

    await usuario.type(nombreInput, "X");
    await usuario.type(numeroInput, "12345678");
    await usuario.click(screen.getByRole("button", { name: "Registrar funcionario" }));

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("El nombre es obligatorio.");
  });

  it("FP-07 · búsqueda repite la consulta con texto=", async () => {
    capacidades.add("gobierno_ocupacion:view");
    apiFetchMock.mockImplementation((ruta: string) => {
      if (ruta.startsWith("/gobierno/ocupacion/funcionarios")) {
        return Promise.resolve(listado);
      }
      return Promise.reject(new Error("Ruta inesperada"));
    });

    renderPage();

    const usuario = userEvent.setup();
    const buscarInput = await screen.findByLabelText("Buscar");

    await usuario.type(buscarInput, "Persona");

    await waitFor(() => {
      expect(apiFetchMock).toHaveBeenCalledWith(
        expect.stringContaining("texto=Persona"),
      );
    });
  });
});
