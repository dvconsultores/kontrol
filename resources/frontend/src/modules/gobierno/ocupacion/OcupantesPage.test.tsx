import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor, within, fireEvent } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "@/api/client";
import type { OcupacionListado } from "@/modules/gobierno/api";
import { hoyDeNegocio } from "@/lib/fecha-de-negocio";

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

const { OcupantesPage } = await import("./OcupantesPage");

function renderPage() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <OcupantesPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

const listadoConFilas: OcupacionListado = {
  ejercicio: 2024,
  fecha: hoyDeNegocio(),
  items: [
    {
      cargo: {
        id: "cargo-1",
        codigo: "C-001",
        nombre: "Director General",
        unidad_id: "u1",
        unidad: "Dirección General",
        ejercicio: 2024,
      },
      titular: {
        id: "a1",
        codigo: "ASG-001",
        figura: "TITULAR",
        figura_etiqueta: "Titular",
        funcionario: {
          id: "f1",
          codigo: "F-001",
          nombre: "Persona Uno",
          documento: "V-******90",
        },
        cargo: {
          id: "cargo-1",
          codigo: "C-001",
          nombre: "Director General",
          unidad_id: "u1",
          unidad: "Dirección General",
          ejercicio: 2024,
        },
        cargo_origen: null,
        acto: {
          id: "acto-1",
          tipo: "DECRETO",
          numero: "123",
          fecha: "2024-01-01",
          status: "ACTIVO",
          fecha_eficacia: "2024-01-01",
          medio: null,
          emisor_cargo_id: "cargo-emi",
          emisor_cargo: "Ministro",
          funcionario: "Persona Uno",
          asunto: "Nombramiento",
        },
        desde: "2024-01-01",
        hasta: null,
        fin_efectivo: null,
        status: "ACTIVO",
        situacion: "VIGENTE",
        version: 1,
      },
      ejerce: null,
      vacante: false,
      delegaciones: 0,
    },
    {
      cargo: {
        id: "cargo-2",
        codigo: "C-002",
        nombre: "Subdirector",
        unidad_id: "u1",
        unidad: "Dirección General",
        ejercicio: 2024,
      },
      titular: null,
      ejerce: null,
      vacante: true,
      delegaciones: 0,
    },
  ],
  total: 2,
  pagina: 1,
  por_pagina: 10,
};

const listadoVacio: OcupacionListado = {
  ejercicio: 2024,
  fecha: hoyDeNegocio(),
  items: [],
  total: 0,
  pagina: 1,
  por_pagina: 10,
};

describe("OcupantesPage", () => {
  beforeEach(() => {
    apiFetchMock.mockReset();
    notifyMock.mockReset();
    capacidades = new Set<string>();
    apiFetchMock.mockResolvedValue(listadoConFilas);
  });

  it("sin gobierno_ocupacion:view muestra 'Sin acceso' y no llama a apiFetch", () => {
    renderPage();

    expect(screen.getByText("Sin acceso")).toBeInTheDocument();
    expect(apiFetchMock).not.toHaveBeenCalled();
  });

  it("lista una fila con titular y otra vacante: comprueba cargo, titular, 'Vacante', y que el enlace del cargo lleva ?fecha=", async () => {
    capacidades.add("gobierno_ocupacion:view");

    renderPage();

    expect(await screen.findByText("Director General")).toBeInTheDocument();
    expect(screen.getByText("Persona Uno")).toBeInTheDocument();
    expect(screen.getByText("V-******90")).toBeInTheDocument();

    const filaVacante = screen.getByText("Subdirector").closest("tr");
    expect(filaVacante).not.toBeNull();
    if (filaVacante) {
      expect(within(filaVacante).getByText("Vacante")).toBeInTheDocument();
    }

    const enlace = screen.getByRole("link", { name: "Director General" });
    expect(enlace).toHaveAttribute(
      "href",
      `/gobierno/ocupacion/cargos/cargo-1?fecha=${hoyDeNegocio()}`,
    );
  });

  it("'Nueva asignación' solo con manage", async () => {
    capacidades.add("gobierno_ocupacion:view");

    const view = renderPage();

    await screen.findByText("Director General");
    expect(
      screen.queryByRole("link", { name: "Nueva asignación" }),
    ).not.toBeInTheDocument();

    capacidades.add("gobierno_ocupacion:manage");
    view.rerender(
      <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
        <MemoryRouter>
          <OcupantesPage />
        </MemoryRouter>
      </QueryClientProvider>,
    );

    expect(
      await screen.findByRole("link", { name: "Nueva asignación" }),
    ).toBeInTheDocument();
  });

  it("cambiar la fecha repite la consulta con esa fecha y vuelve a la página 1", async () => {
    capacidades.add("gobierno_ocupacion:view");

    renderPage();

    await screen.findByText("Director General");
    expect(apiFetchMock).toHaveBeenCalledTimes(1);

    const inputFecha = screen.getByLabelText(/Fecha/);
    fireEvent.change(inputFecha, { target: { value: "2024-07-01" } });

    await waitFor(() => {
      const llamadas = apiFetchMock.mock.calls;
      expect(llamadas.some((call) => String(call[0]).includes("fecha=2024-07-01"))).toBe(
        true,
      );
      expect(String(llamadas.at(-1)?.[0])).not.toContain("pagina=");
    });
  });

  it("paginación: Siguiente pide pagina=2; Anterior deshabilitado en página 1", async () => {
    capacidades.add("gobierno_ocupacion:view");

    const listadoPagina1: OcupacionListado = {
      ...listadoConFilas,
      total: 25,
      por_pagina: 10,
      pagina: 1,
    };

    apiFetchMock.mockResolvedValueOnce(listadoPagina1);

    renderPage();

    await screen.findByText("Director General");

    const botonAnterior = screen.getByRole("button", { name: "Anterior" });
    expect(botonAnterior).toBeDisabled();

    const botonSiguiente = screen.getByRole("button", { name: "Siguiente" });
    expect(botonSiguiente).not.toBeDisabled();

    const listadoPagina2: OcupacionListado = {
      ...listadoPagina1,
      pagina: 2,
    };

    apiFetchMock.mockResolvedValueOnce(listadoPagina2);

    await userEvent.click(botonSiguiente);

    await waitFor(() => {
      const llamadas = apiFetchMock.mock.calls;
      expect(llamadas.some((call) => String(call[0]).includes("pagina=2"))).toBe(
        true,
      );
    });
  });

  it("error 500 muestra ErrorState y Reintentar llama de nuevo", async () => {
    capacidades.add("gobierno_ocupacion:view");

    apiFetchMock.mockRejectedValueOnce(new ApiError(500, { code: "INTERNAL_ERROR", message: "Error interno" }));

    renderPage();

    expect(
      await screen.findByText("No fue posible cargar la ocupación de cargos."),
    ).toBeInTheDocument();

    apiFetchMock.mockResolvedValueOnce(listadoConFilas);

    const botonReintentar = screen.getByRole("button", { name: "Reintentar" });
    await userEvent.click(botonReintentar);

    await waitFor(() => {
      expect(apiFetchMock).toHaveBeenCalledTimes(2);
    });

    expect(await screen.findByText("Director General")).toBeInTheDocument();
  });

  it("403 MODULE_NOT_ENTITLED muestra 'Módulo no habilitado'", async () => {
    capacidades.add("gobierno_ocupacion:view");

    apiFetchMock.mockRejectedValueOnce(
      new ApiError(403, { code: "MODULE_NOT_ENTITLED", message: "No autorizado" }),
    );

    renderPage();

    expect(await screen.findByText("Módulo no habilitado")).toBeInTheDocument();
  });

  it("vacío", async () => {
    capacidades.add("gobierno_ocupacion:view");

    apiFetchMock.mockResolvedValueOnce(listadoVacio);

    renderPage();

    expect(
      await screen.findByText("No hay cargos en ese ejercicio"),
    ).toBeInTheDocument();
  });
});
