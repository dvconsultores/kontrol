import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError } from "@/api/client";
import { PagosPage } from "./PagosPage";
import type { PagoResumen } from "./api";

const apiFetchMock = vi.fn();

vi.mock("@/api/client", async (original) => ({
  ...(await original<typeof import("@/api/client")>()),
  apiFetch: (...args: unknown[]) => apiFetchMock(...args),
  ApiError: (await original<typeof import("@/api/client")>()).ApiError,
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
  useCompany: () => ({ activeCompanyId: "c1", activeCompany: { id: "c1", legal_name: "Ente 1" } }),
}));

vi.mock("@/app/contexts/NotificationContext", () => ({
  useNotifications: () => ({ notify: vi.fn() }),
}));

const ESTADOS_PAGO: Record<string, string> = {
  BORRADOR: "Borrador",
  PENDIENTE_AUTORIZACION: "Pendiente de autorización",
  AUTORIZADO: "Autorizado",
  REGISTRADO: "Pago registrado",
  RECHAZADO: "Rechazado",
  ANULADO: "Anulado",
};

const ESTADOS_OPCIONES: Record<string, string> = {
  BORRADOR: "Borrador",
  PENDIENTE_AUTORIZACION: "Pendiente de autorización",
  AUTORIZADO: "Autorizado",
  REGISTRADO: "Pago registrado",
  RECHAZADO: "Rechazado",
  ANULADO: "Anulado",
};

function fabricarPagos(): PagoResumen[] {
  return [
    {
      id: "pago-1",
      codigo: "PAGO-0001",
      estado: "BORRADOR",
      orden_codigo: "OP-0001",
      order_id: "orden-1",
      beneficiario: "Proveedor Uno",
      cuenta_codigo: "C-01",
      medio_codigo: "M-01",
      moneda: "USD",
      monto: "100.00",
      fecha_pago: "2025-06-01",
      fecha_valor: null,
      referencia_externa: null,
      enviado_en: null,
      registrado_en: null,
      version: 1,
    },
    {
      id: "pago-2",
      codigo: "PAGO-0002",
      estado: "AUTORIZADO",
      orden_codigo: "OP-0002",
      order_id: "orden-2",
      beneficiario: "Proveedor Dos",
      cuenta_codigo: "C-02",
      medio_codigo: "M-02",
      moneda: "USD",
      monto: "200.00",
      fecha_pago: "2025-06-02",
      fecha_valor: null,
      referencia_externa: null,
      enviado_en: null,
      registrado_en: null,
      version: 1,
    },
  ];
}

function renderPagos(pagos: PagoResumen[] = fabricarPagos()) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });

  apiFetchMock.mockImplementation(async (ruta: string, opcionesFetch?: { method?: string }) => {
    const metodo = opcionesFetch?.method ?? "GET";

    if (ruta.endsWith("/pagos") && metodo === "GET") {
      return pagos;
    }

    throw new Error(`Ruta no mockeada: ${ruta} ${metodo}`);
  });

  render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={["/gobierno/tesoreria/pagos"]}>
        <Routes>
          <Route path="/gobierno/tesoreria/pagos" element={<PagosPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );

  return queryClient;
}

describe("PagosPage", () => {
  beforeEach(() => {
    capacidades = new Set<string>();
    apiFetchMock.mockReset();
  });

  it("h1 Pagos y filas con codigo, estado y enlace al detalle", async () => {
    capacidades = new Set(["gobierno_pagos:view"]);
    renderPagos();

    await screen.findByRole("heading", { name: "Pagos" });

    expect(screen.getByText("PAGO-0001")).toBeInTheDocument();
    expect(screen.getByText("Borrador")).toBeInTheDocument();

    const enlaces = screen.getAllByRole("link", { name: /PAGO-0001/i });
    expect(enlaces.length).toBeGreaterThan(0);
    expect(enlaces[0]).toHaveAttribute("href", "/gobierno/tesoreria/pagos/pago-1");
  });

  it("con manage muestra el enlace Nuevo pago y sin manage no", async () => {
    capacidades = new Set(["gobierno_pagos:view", "gobierno_pagos:manage"]);
    renderPagos();

    await screen.findByRole("heading", { name: "Pagos" });

    expect(screen.getByRole("link", { name: /Nuevo pago/i })).toBeInTheDocument();

    capacidades = new Set(["gobierno_pagos:view"]);
    apiFetchMock.mockReset();
    renderPagos();

    await screen.findByRole("heading", { name: "Pagos" });

    expect(screen.queryByRole("link", { name: /Nuevo pago/i })).not.toBeInTheDocument();
  });

  it("cambiar el filtro de estado vuelve a llamar a apiFetch con ?estado=...", async () => {
    capacidades = new Set(["gobierno_pagos:view"]);
    renderPagos();

    await screen.findByRole("heading", { name: "Pagos" });

    const selectEstado = screen.getByLabelText(/^Estado/);
    await userEvent.click(selectEstado);

    const opcion = await screen.findByRole("option", { name: "Autorizado" });
    await userEvent.click(opcion);

    await waitFor(() => {
      const llamadas = apiFetchMock.mock.calls.filter(
        ([ruta, opciones]: [string, { method?: string }]) =>
          ruta.endsWith("/pagos") && (opciones?.method ?? "GET") === "GET",
      );
      expect(llamadas.length).toBeGreaterThanOrEqual(2);
      const ultimaLlamada = llamadas[llamadas.length - 1];
      expect(ultimaLlamada[0]).toContain("estado=AUTORIZADO");
    });
  });

  it("lista vacia muestra el estado vacio", async () => {
    capacidades = new Set(["gobierno_pagos:view"]);
    renderPagos([]);

    await screen.findByRole("heading", { name: "Pagos" });

    expect(await screen.findByText(/Aún no hay pagos/i)).toBeInTheDocument();
  });
});
