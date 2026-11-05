import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "@/api/client";
import { CuentasPage } from "./CuentasPage";

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
  useCompany: () => ({
    activeCompanyId: "c1",
    activeCompany: { id: "c1", legal_name: "Contenedor 1" },
  }),
}));

vi.mock("@/app/contexts/NotificationContext", () => ({
  useNotifications: () => ({ notify: notifyMock }),
}));

const cuenta = {
  id: "c1",
  codigo: "CB-2026-0001",
  denominacion: "Fondos de funcionamiento",
  banco_id: "b1",
  banco_codigo: "0102",
  banco_nombre: "Banco Uno",
  tipo: "CORRIENTE" as const,
  moneda: "VES" as const,
  numero_enmascarado: "••••0001",
  vigente_desde: "2026-11-01",
  vigente_hasta: null,
  estado: "BORRADOR" as const,
  en_vigor: false,
  acto_sin_efecto: false,
  autorizados_en_vigor: 0,
  version: 1,
};

const bancos = {
  items: [
    { id: "b1", codigo: "0102", nombre: "Banco Uno", estado: "ACTIVO" as const, version: 1 },
    { id: "b2", codigo: "0104", nombre: "Banco Dos", estado: "ACTIVO" as const, version: 1 },
  ],
};

const opciones = {
  bancos: [
    { id: "b1", codigo: "0102", nombre: "Banco Uno" },
    { id: "b2", codigo: "0104", nombre: "Banco Dos" },
  ],
  cargos: [
    { id: "g1", codigo: "C-001", denominacion: "Gerente", unidad: "Unidad X" },
    { id: "g2", codigo: "C-002", denominacion: "Coordinador", unidad: "Unidad Y" },
  ],
  actos: [],
};

const listado = {
  items: [cuenta],
  resumen: { borradores: 1, vigentes: 2, inactivas: 3, cerradas: 4 },
};

function renderPage(ruta = "/gobierno/tesoreria/cuentas") {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[ruta]}>
        <Routes>
          <Route path="/gobierno/tesoreria/cuentas" element={<CuentasPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("CuentasPage", () => {
  beforeEach(() => {
    apiFetchMock.mockReset();
    notifyMock.mockReset();
    capacidades = new Set<string>();

    apiFetchMock.mockImplementation((url: string) => {
      if (url === "/gobierno/tesoreria/bancos") return Promise.resolve(bancos);
      if (url === "/gobierno/tesoreria/opciones") return Promise.resolve(opciones);
      if (url.startsWith("/gobierno/tesoreria/cuentas")) {
        return Promise.resolve(listado);
      }
      return Promise.reject(new Error(`URL no mockeada: ${url}`));
    });
  });

  it("CP-01 · sin gobierno_cuentas:view muestra «Sin acceso» y no llama a la API", async () => {
    renderPage();

    expect(await screen.findByText("Sin acceso")).toBeInTheDocument();
    expect(apiFetchMock).not.toHaveBeenCalled();
  });

  it("CP-02 · con view: tabla con código, banco, tipo «Corriente», número enmascarado y estado; sin el enlace «Nueva cuenta»", async () => {
    capacidades.add("gobierno_cuentas:view");

    renderPage();

    expect(await screen.findByText("CB-2026-0001")).toBeInTheDocument();
    expect(screen.getByText("Fondos de funcionamiento")).toBeInTheDocument();
    expect(screen.getByRole("cell", { name: "Banco Uno" })).toBeInTheDocument();
    expect(screen.getByText("Corriente")).toBeInTheDocument();
    expect(screen.getByText("••••0001")).toBeInTheDocument();
    expect(screen.getByRole("cell", { name: "Borrador" })).toBeInTheDocument();
    expect(screen.queryByText("Nueva cuenta")).not.toBeInTheDocument();
    expect(screen.getByText("Bancos")).toBeInTheDocument();
  });

  it("CP-03 · con manage aparece «Nueva cuenta»", async () => {
    capacidades.add("gobierno_cuentas:view");
    capacidades.add("gobierno_cuentas:manage");

    renderPage();

    expect(await screen.findByText("Nueva cuenta")).toBeInTheDocument();
  });

  it("CP-04 · filtrar por moneda USD llama a /gobierno/tesoreria/cuentas?moneda=USD", async () => {
    capacidades.add("gobierno_cuentas:view");

    renderPage();

    const selectorMoneda = await screen.findByLabelText("Moneda");
    await userEvent.selectOptions(selectorMoneda, "USD");

    await waitFor(() => {
      expect(apiFetchMock).toHaveBeenCalledWith(
        "/gobierno/tesoreria/cuentas?moneda=USD",
      );
    });
  });

  it("CP-05 · pulsar el indicador «Vigentes» filtra estado=VIGENTE y queda aria-pressed=true", async () => {
    capacidades.add("gobierno_cuentas:view");

    renderPage();

    const indicadorVigentes = await screen.findByRole("button", {
      name: /Vigentes/,
    });
    await userEvent.click(indicadorVigentes);

    expect(await screen.findByRole("button", { name: /Vigentes/, pressed: true })).toBeInTheDocument();

    await waitFor(() => {
      expect(apiFetchMock).toHaveBeenCalledWith(
        "/gobierno/tesoreria/cuentas?estado=VIGENTE",
      );
    });
  });

  it("CP-06 · cuenta con acto_sin_efecto: true muestra «Acto sin efecto»", async () => {
    capacidades.add("gobierno_cuentas:view");

    apiFetchMock.mockImplementation((url: string) => {
      if (url === "/gobierno/tesoreria/bancos") return Promise.resolve(bancos);
      if (url === "/gobierno/tesoreria/opciones") return Promise.resolve(opciones);
      if (url.startsWith("/gobierno/tesoreria/cuentas")) {
        return Promise.resolve({
          ...listado,
          items: [{ ...cuenta, acto_sin_efecto: true, estado: "VIGENTE" as const, en_vigor: true }],
        });
      }
      return Promise.reject(new Error(`URL no mockeada: ${url}`));
    });

    renderPage();

    expect(await screen.findByText(/Acto sin efecto/)).toBeInTheDocument();
  });

  it("CP-07 · si falla /opciones, la tabla sigue visible", async () => {
    capacidades.add("gobierno_cuentas:view");

    apiFetchMock.mockImplementation((url: string) => {
      if (url === "/gobierno/tesoreria/bancos") return Promise.resolve(bancos);
      if (url === "/gobierno/tesoreria/opciones") {
        return Promise.reject(new ApiError(500, { code: "INTERNAL_ERROR", message: "Error interno", details: {} }));
      }
      if (url.startsWith("/gobierno/tesoreria/cuentas")) {
        return Promise.resolve(listado);
      }
      return Promise.reject(new Error(`URL no mockeada: ${url}`));
    });

    renderPage();

    expect(await screen.findByText("CB-2026-0001")).toBeInTheDocument();
    expect(screen.getByText("Fondos de funcionamiento")).toBeInTheDocument();
  });

  it("CP-08 · lista vacía sin filtros, con manage: «No hay cuentas bancarias» y enlace «Nueva cuenta»", async () => {
    capacidades.add("gobierno_cuentas:view");
    capacidades.add("gobierno_cuentas:manage");

    apiFetchMock.mockImplementation((url: string) => {
      if (url === "/gobierno/tesoreria/bancos") return Promise.resolve(bancos);
      if (url === "/gobierno/tesoreria/opciones") return Promise.resolve(opciones);
      if (url.startsWith("/gobierno/tesoreria/cuentas")) {
        return Promise.resolve({ items: [], resumen: { borradores: 0, vigentes: 0, inactivas: 0, cerradas: 0 } });
      }
      return Promise.reject(new Error(`URL no mockeada: ${url}`));
    });

    renderPage();

    expect(await screen.findByText("No hay cuentas bancarias")).toBeInTheDocument();
    expect(screen.getAllByRole("link", { name: "Nueva cuenta" })).toHaveLength(2);
  });

  it("CP-09 · lista vacía con filtro: «No hay cuentas con estos filtros.»", async () => {
    capacidades.add("gobierno_cuentas:view");

    apiFetchMock.mockImplementation((url: string) => {
      if (url === "/gobierno/tesoreria/bancos") return Promise.resolve(bancos);
      if (url === "/gobierno/tesoreria/opciones") return Promise.resolve(opciones);
      if (url.startsWith("/gobierno/tesoreria/cuentas")) {
        return Promise.resolve({ items: [], resumen: { borradores: 0, vigentes: 0, inactivas: 0, cerradas: 0 } });
      }
      return Promise.reject(new Error(`URL no mockeada: ${url}`));
    });

    renderPage();

    const selectorMoneda = await screen.findByLabelText("Moneda");
    await userEvent.selectOptions(selectorMoneda, "USD");

    expect(await screen.findByText("No hay cuentas con estos filtros.")).toBeInTheDocument();
  });
});
