import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";

const apiFetchMock = vi.fn();

vi.mock("@/api/client", async (original) => ({
  ...(await original<typeof import("@/api/client")>()),
  apiFetch: (...args: unknown[]) => apiFetchMock(...args),
}));

vi.mock("@/modules/documentos/AdjuntosPanel", () => ({
  AdjuntosPanel: () => null,
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
  useNotifications: () => ({ notify: vi.fn() }),
}));

const { TasasOficialesPage } = await import("./TasasOficialesPage");

const t1 = {
  id: "t1",
  moneda: "USD",
  fecha_efectiva: "2026-11-05",
  valor: "905.12345678",
  version: 1,
  capturada_por: "capturista",
  aprobada_por: "aprobador",
  evidencia_sha256: "a".repeat(64),
  estado: "APROBADA",
  fuente: "BCV",
  fuente_referencia: "BCV · tipo de cambio de referencia",
  publicada_en: null,
  motivo_correccion: null,
  motivo_anulacion: null,
  sustituye_id: null,
  anulada_por: null,
  anulada_en: null,
  corregida_por: null,
  corregida_en: null,
  creada_en: "2026-11-05T12:00:00Z",
  actualizada_en: "2026-11-05T12:00:00Z",
};

const t2 = {
  ...t1,
  id: "t2",
  moneda: "EUR",
  fecha_efectiva: "2026-11-06",
  valor: "1000",
  aprobada_por: null,
  evidencia_sha256: null,
  estado: "BORRADOR",
};

const detalleT1 = { ...t1, historia: [t1] };
const detalleT2 = { ...t2, historia: [t2] };

function mockRutas() {
  apiFetchMock.mockImplementation(
    (ruta: string, opciones?: { method?: string }) => {
      if (ruta.startsWith("/gobierno/tesoreria/tasas/t1")) {
        return Promise.resolve(detalleT1);
      }
      if (ruta.startsWith("/gobierno/tesoreria/tasas/t2")) {
        return Promise.resolve(detalleT2);
      }
      if (ruta.startsWith("/gobierno/tesoreria/tasas")) {
        if (opciones?.method === "POST") {
          return Promise.resolve(t1);
        }
        return Promise.resolve({
          items: [t1, t2],
          monedas: ["USD", "EUR"],
          estados: ["BORRADOR", "APROBADA"],
        });
      }
      return Promise.reject(new Error(`No mock: ${ruta}`));
    },
  );
}

function renderizar() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <TasasOficialesPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("TasasOficialesPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    capacidades = new Set([
      "gobierno_tasas:view",
      "gobierno_tasas:manage",
      "gobierno_tasas:approve",
    ]);
    mockRutas();
  });

  it("muestra la tabla de tasas oficiales", async () => {
    renderizar();

    const region = await screen.findByRole("region", {
      name: "Tabla de tasas oficiales",
    });
    expect(within(region).getByText("1 USD = 905,12345678 VES")).toBeInTheDocument();
    expect(within(region).getByText("05/11/2026")).toBeInTheDocument();
  });

  it("registra una tasa", async () => {
    const user = userEvent.setup();
    renderizar();

    await screen.findByRole("region", { name: "Tabla de tasas oficiales" });

    await user.selectOptions(
      screen.getByRole("combobox", { name: "Moneda (obligatorio)" }),
      "USD",
    );
    fireEvent.change(
      screen.getByLabelText("Fecha efectiva", { exact: false }),
      { target: { value: "2026-11-10" } },
    );
    await user.type(
      screen.getByRole("textbox", { name: "Valor en VES por unidad (obligatorio)" }),
      "910,5",
    );
    await user.type(
      screen.getByRole("textbox", { name: "Referencia oficial del BCV (obligatorio)" }),
      "BCV · tipo de cambio de referencia",
    );
    await user.click(
      screen.getByRole("button", { name: "Registrar tasa" }),
    );

    expect(apiFetchMock).toHaveBeenCalledWith("/gobierno/tesoreria/tasas", {
      method: "POST",
      body: {
        moneda: "USD",
        fecha_efectiva: "2026-11-10",
        valor: "910.5",
        fuente_referencia: "BCV · tipo de cambio de referencia",
        publicada_en: null,
      },
    });
  });

  it("aprueba una tasa borrador", async () => {
    const user = userEvent.setup();
    renderizar();

    await screen.findByRole("region", { name: "Tabla de tasas oficiales" });
    await user.click(
      screen.getByRole("button", { name: "Ver EUR 06/11/2026 v1" }),
    );

    expect(await screen.findByText("Historia de versiones")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Aprobar tasa" }));

    expect(apiFetchMock).toHaveBeenCalledWith(
      "/gobierno/tesoreria/tasas/t2/aprobar",
      { method: "POST", body: {} },
    );
  });

  it("no muestra registrar sin permiso manage", async () => {
    capacidades.delete("gobierno_tasas:manage");
    renderizar();

    await screen.findByRole("region", { name: "Tabla de tasas oficiales" });
    expect(
      screen.queryByRole("button", { name: "Registrar tasa" }),
    ).not.toBeInTheDocument();
  });

  it("no muestra la página sin permiso view", async () => {
    capacidades.delete("gobierno_tasas:view");
    renderizar();

    expect(await screen.findByText("Sin acceso")).toBeInTheDocument();
  });

  it("registra una corrección", async () => {
    const user = userEvent.setup();
    renderizar();

    await screen.findByRole("region", { name: "Tabla de tasas oficiales" });
    await user.click(
      screen.getByRole("button", { name: "Ver USD 05/11/2026 v1" }),
    );

    await user.type(
      await screen.findByRole("textbox", { name: "Nuevo valor en VES por unidad (obligatorio)" }),
      "906",
    );
    await user.type(
      screen.getByRole("textbox", {
        name: "Referencia oficial del BCV de la corrección (obligatorio)",
      }),
      "BCV · corrección publicada",
    );
    await user.type(
      screen.getByRole("textbox", { name: "Motivo de la corrección (obligatorio)" }),
      "Corrección del valor publicado",
    );
    await user.click(
      screen.getByRole("button", { name: "Registrar corrección" }),
    );

    expect(apiFetchMock).toHaveBeenCalledWith(
      "/gobierno/tesoreria/tasas/t1/correccion",
      {
        method: "POST",
        body: {
          valor: "906",
          fuente_referencia: "BCV · corrección publicada",
          publicada_en: null,
          motivo: "Corrección del valor publicado",
        },
      },
    );
  });

  it("anula una tasa", async () => {
    const user = userEvent.setup();
    renderizar();

    await screen.findByRole("region", { name: "Tabla de tasas oficiales" });
    await user.click(
      screen.getByRole("button", { name: "Ver EUR 06/11/2026 v1" }),
    );

    await user.type(
      await screen.findByRole("textbox", { name: "Motivo de anulación" }),
      "Error de captura de la fecha",
    );
    await user.click(screen.getByRole("button", { name: "Anular tasa" }));

    expect(apiFetchMock).toHaveBeenCalledWith(
      "/gobierno/tesoreria/tasas/t2/anular",
      {
        method: "POST",
        body: { motivo: "Error de captura de la fecha" },
      },
    );
  });
});
