import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "@/api/client";

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

const { PoliticasPage } = await import("./PoliticasPage");

const politica = {
  id: "p1",
  codigo: "CIE-2026-0001",
  nombre: "Cierre de estructura con hallazgos",
  accion_cierre: "ORG02_CERRAR_ESTRUCTURA",
  fundamento: "No cerrar con hallazgos materiales abiertos.",
  estado: "VIGENTE",
  vigente_desde: "2026-01-01",
  vigente_hasta: null,
  efectiva_hoy: true,
  version: 2,
};

const listado = {
  items: [politica],
  total: 1,
  resumen: { borradores: 2, vigentes: 1, retiradas: 3 },
};

function renderPage(ruta = "/gobierno/cierres") {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[ruta]}>
        <Routes>
          <Route path="/gobierno/cierres" element={<PoliticasPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("PoliticasPage", () => {
  beforeEach(() => {
    apiFetchMock.mockReset();
    capacidades = new Set<string>();
    apiFetchMock.mockResolvedValue(listado);
  });

  it("CIE-PP-01 · sin gobierno_cierre:view muestra «Sin acceso» y no llama a apiFetch", async () => {
    renderPage();

    expect(await screen.findByText("Sin acceso")).toBeInTheDocument();
    expect(apiFetchMock).not.toHaveBeenCalled();
  });

  it("CIE-PP-02 · con view muestra indicadores, tabla y enlace de la política", async () => {
    capacidades.add("gobierno_cierre:view");

    renderPage();

    expect(
      await screen.findByRole("heading", { name: "Controles de cierre" }),
    ).toBeInTheDocument();
    expect(await screen.findByText("Borradores")).toBeInTheDocument();
    expect(screen.getByText("Vigentes")).toBeInTheDocument();
    expect(screen.getByText("Retiradas")).toBeInTheDocument();
    expect(
      screen.getByRole("link", {
        name: "Abrir la política CIE-2026-0001",
      }),
    ).toHaveAttribute("href", "/gobierno/cierres/p1");
    expect(
      screen.getByRole("cell", { name: "Cerrar estructura del ejercicio" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("cell", { name: "Vigente" }),
    ).toBeInTheDocument();
    expect(screen.getByText("Sí")).toBeInTheDocument();
  });

  it("CIE-PP-03 · sin manage no aparece «Nueva política»; con manage aparece con href", async () => {
    capacidades.add("gobierno_cierre:view");

    const { unmount } = renderPage();
    await screen.findByText("Vigentes");
    expect(
      screen.queryByRole("link", { name: "Nueva política" }),
    ).not.toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: "Cierres bloqueados" }),
    ).toHaveAttribute("href", "/gobierno/cierres/bloqueos");
    unmount();

    capacidades.add("gobierno_cierre:manage");
    renderPage();
    await screen.findByText("Vigentes");
    expect(
      screen.getByRole("link", { name: "Nueva política" }),
    ).toHaveAttribute("href", "/gobierno/cierres/nueva");
  });

  it("CIE-PP-04 · 403 MODULE_NOT_ENTITLED muestra «Módulo no habilitado»", async () => {
    capacidades.add("gobierno_cierre:view");
    apiFetchMock.mockRejectedValue(
      new ApiError(403, {
        code: "MODULE_NOT_ENTITLED",
        message: "Módulo no habilitado",
      }),
    );

    renderPage();

    expect(
      await screen.findByText("Módulo no habilitado"),
    ).toBeInTheDocument();
  });

  it("CIE-PP-05 · 403 genérico muestra «Sin acceso»", async () => {
    capacidades.add("gobierno_cierre:view");
    apiFetchMock.mockRejectedValue(
      new ApiError(403, { code: "FORBIDDEN", message: "Sin permiso" }),
    );

    renderPage();

    expect(await screen.findByText("Sin acceso")).toBeInTheDocument();
  });

  it("CIE-PP-06 · error genérico muestra ErrorState con reintento", async () => {
    capacidades.add("gobierno_cierre:view");
    apiFetchMock.mockRejectedValue(
      new ApiError(500, { code: "SERVER_ERROR", message: "Error" }),
    );

    renderPage();

    expect(
      await screen.findByText("No fue posible cargar las políticas."),
    ).toBeInTheDocument();
  });

  it("CIE-PP-07 · vacío con manage invita a «Nueva política»", async () => {
    capacidades.add("gobierno_cierre:view");
    capacidades.add("gobierno_cierre:manage");
    apiFetchMock.mockResolvedValue({
      items: [],
      total: 0,
      resumen: { borradores: 0, vigentes: 0, retiradas: 0 },
    });

    renderPage();

    expect(await screen.findByText("Aún no hay políticas")).toBeInTheDocument();
    expect(
      screen.getByText("Registre la primera política con «Nueva política»."),
    ).toBeInTheDocument();
  });

  it("CIE-PP-08 · vacío con filtros indica que no hay políticas con esos filtros", async () => {
    capacidades.add("gobierno_cierre:view");
    apiFetchMock.mockResolvedValue({
      items: [],
      total: 0,
      resumen: { borradores: 0, vigentes: 0, retiradas: 0 },
    });

    renderPage();

    expect(await screen.findByText("Aún no hay políticas")).toBeInTheDocument();
    await userEvent.selectOptions(screen.getByLabelText("Estado"), "VIGENTE");
    expect(await screen.findByText("Sin resultados")).toBeInTheDocument();
    expect(
      screen.getByText("No hay políticas con estos filtros."),
    ).toBeInTheDocument();
  });

  it("CIE-PP-09 · pulsar la tarjeta «Borradores» vuelve a consultar con estado=BORRADOR", async () => {
    capacidades.add("gobierno_cierre:view");
    const user = userEvent.setup();
    apiFetchMock.mockClear();

    renderPage();
    const boton = await screen.findByRole("button", { name: /Borradores/ });
    await user.click(boton);

    await waitFor(() => {
      const llamadas = apiFetchMock.mock.calls;
      const ultima = llamadas[llamadas.length - 1];
      expect(ultima[0]).toContain("/gobierno/cierres/politicas");
      expect(ultima[0]).toContain("estado=BORRADOR");
    });
  });

  it("CIE-PP-10 · filtrar por acción envía accion_cierre en la consulta", async () => {
    capacidades.add("gobierno_cierre:view");
    const user = userEvent.setup();
    apiFetchMock.mockClear();

    renderPage();
    await screen.findByText("Vigentes");

    const selectorAccion = screen.getByLabelText("Acción");
    await user.selectOptions(
      selectorAccion,
      "ORG02_CERRAR_ESTRUCTURA",
    );

    await waitFor(() => {
      const llamadas = apiFetchMock.mock.calls;
      const ultima = llamadas[llamadas.length - 1];
      expect(ultima[0]).toContain(
        "accion_cierre=ORG02_CERRAR_ESTRUCTURA",
      );
    });
  });
});
