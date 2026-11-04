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

const { ReglasSodPage } = await import("./ReglasSodPage");

const regla = {
  id: "r1",
  codigo: "SOD-2026-0001",
  nombre: "Registro y recomendación",
  descripcion: "Quien registra un hallazgo no recomienda sobre él.",
  proceso: "CTL-06",
  accion_a: "CTL06_REGISTRAR",
  accion_a_etiqueta: "Registrar el hallazgo",
  accion_b: "CTL06_RECOMENDAR",
  accion_b_etiqueta: "Añadir una recomendación",
  bidireccional: false,
  alcance: "MISMO_OBJETO",
  modo: "BLOQUEAR",
  vigente_desde: "2026-11-04",
  vigente_hasta: null,
  estado: "VIGENTE",
  en_vigor: true,
  version: 1,
  creada_por: "ua",
  creada_en: "2026-11-04T12:00:00Z",
  activada_por: null,
  activada_en: null,
  cerrada_por: null,
  cerrada_en: null,
  motivo_cierre: null,
  conflictos: 0,
  historia: [{ tipo: "CREADA", detalle: null, registrado_por: "ua", registrado_en: "2026-11-04T12:00:00Z" }],
};

const listado = {
  items: [regla],
  resumen: { borradores: 2, vigentes: 1, cerradas: 3, conflictos_30_dias: 4 },
};

function renderPage(ruta = "/gobierno/sod") {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[ruta]}>
        <Routes>
          <Route path="/gobierno/sod" element={<ReglasSodPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("RSP", () => {
  beforeEach(() => {
    apiFetchMock.mockReset();
    notifyMock.mockReset();
    capacidades = new Set<string>();
    apiFetchMock.mockResolvedValue(listado);
  });

  it("RSP-01 · con gobierno_sod:view muestra los indicadores, el enlace, la incompatibilidad y el estado", async () => {
    capacidades.add("gobierno_sod:view");

    renderPage();

    expect(await screen.findByText("Vigentes")).toBeInTheDocument();
    expect(screen.getByText("Borradores")).toBeInTheDocument();
    expect(screen.getByText("Cerradas")).toBeInTheDocument();
    expect(screen.getByText("Conflictos en 30 días")).toBeInTheDocument();

    expect(screen.getByRole("link", { name: "Abrir la regla SOD-2026-0001" })).toHaveAttribute("href", "/gobierno/sod/r1");
    expect(screen.getByText("Registrar el hallazgo → Añadir una recomendación")).toBeInTheDocument();
    expect(screen.getByText("Vigente · en vigor")).toBeInTheDocument();
  });

  it("RSP-02 · sin gobierno_sod:manage no aparece el enlace «Nueva regla»; con manage aparece con href", async () => {
    capacidades.add("gobierno_sod:view");

    const { unmount } = renderPage();
    await screen.findByText("Vigentes");
    expect(screen.queryByRole("link", { name: "Nueva regla" })).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Ver conflictos" })).toBeInTheDocument();
    unmount();

    capacidades.add("gobierno_sod:manage");
    renderPage();
    await screen.findByText("Vigentes");
    expect(screen.getByRole("link", { name: "Nueva regla" })).toHaveAttribute("href", "/gobierno/sod/nueva");
    expect(screen.getByRole("link", { name: "Ver conflictos" })).toBeInTheDocument();
  });

  it("RSP-03 · pulsar la tarjeta «Borradores» vuelve a consultar con estado=BORRADOR", async () => {
    capacidades.add("gobierno_sod:view");
    const user = userEvent.setup();
    apiFetchMock.mockClear();

    renderPage();
    const botonBorradores = await screen.findByRole("button", { name: /Borradores/ });
    await user.click(botonBorradores);

    await waitFor(() => {
      const llamadas = apiFetchMock.mock.calls;
      const ultima = llamadas[llamadas.length - 1];
      expect(ultima[0]).toContain("/gobierno/sod/reglas?estado=BORRADOR");
    });
  });

  it("RSP-04 · sin gobierno_sod:view muestra «Sin acceso» y no llama a apiFetch", async () => {
    capacidades.clear();

    renderPage();

    expect(await screen.findByText("Sin acceso")).toBeInTheDocument();
    expect(apiFetchMock).not.toHaveBeenCalled();
  });

  it("RSP-05 · 403 MODULE_NOT_ENTITLED muestra «Módulo no habilitado»", async () => {
    capacidades.add("gobierno_sod:view");
    apiFetchMock.mockRejectedValue(
      new ApiError(403, {
        code: "MODULE_NOT_ENTITLED",
        message: "Módulo no habilitado",
      }),
    );

    renderPage();

    expect(await screen.findByText("Módulo no habilitado")).toBeInTheDocument();
  });
});
