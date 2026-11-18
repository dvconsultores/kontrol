import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError } from "@/api/client";
import { PoliticasOrdenPagoPage } from "./PoliticasOrdenPagoPage";
import type { ConfiguracionNumeracionOP, PoliticaOrdenPago } from "./api";

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

function politicaReal(sobre: Partial<PoliticaOrdenPago> = {}): PoliticaOrdenPago {
  return {
    id: "b47d44d0-9453-46d1-8c4f-240d88cf6bd1",
    codigo: "OPB0C26DCB4EF7",
    nombre: "Política de orden de pago de prueba",
    descripcion: null,
    tipo_gasto: null,
    requiere_expediente_completo: false,
    competencia_accion: "ORDENAR_PAGO",
    competencia_materia: "TESORERIA",
    vigente_desde: "2026-11-17",
    vigente_hasta: null,
    fundamento: "Fundamento suficiente para activar la política de orden de pago.",
    act_id: null,
    acto: null,
    tipo_regla: "INSTITUTIONAL_POLICY",
    estado: "VIGENTE",
    version: 2,
    activada_en: "2026-11-17T18:45:36.632890+00:00",
    cerrada_en: null,
    motivo_cierre: null,
    documentos: [],
    historia: [
      {
        evento: "ACTIVADA",
        version: 2,
        fecha: "2026-11-17T18:45:36.623580+00:00",
        actor: "ord_t03",
      },
      {
        evento: "CREADA",
        version: 1,
        fecha: "2026-11-17T18:45:36.527753+00:00",
        actor: "ord_t03",
      },
    ],
    ...sobre,
  };
}

function configuracionReal(sobre: Partial<ConfiguracionNumeracionOP> = {}): ConfiguracionNumeracionOP {
  return {
    patron: "{ANIO}-{NUMERO:5}",
    ejemplo: "2026-00001",
    version: 0,
    configurado: false,
    ...sobre,
  };
}

const RUTA_CONFIG = "/gobierno/tesoreria/ordenes-pago/configuracion";
const RUTA_POLITICAS = "/gobierno/tesoreria/politicas-orden-pago";

function renderPagina() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[RUTA_POLITICAS]}>
        <Routes>
          <Route path={RUTA_POLITICAS} element={<PoliticasOrdenPagoPage />} />
          <Route path={`${RUTA_POLITICAS}/:id`} element={<div>politica-destino</div>} />
          <Route path={`${RUTA_POLITICAS}/nueva`} element={<div>nueva-politica-destino</div>} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

function respuestaExitosa(politicas: PoliticaOrdenPago[], config = configuracionReal()) {
  apiFetchMock.mockImplementation(
    (ruta: string, opciones?: { method?: string; body?: unknown; ifMatch?: string }) => {
      const metodo = opciones?.method ?? "GET";
      if (metodo === "GET" && ruta === RUTA_CONFIG) {
        return Promise.resolve(config);
      }
      if (metodo === "GET" && ruta === RUTA_POLITICAS) {
        return Promise.resolve(politicas);
      }
      return Promise.reject(new Error("Ruta no esperada: " + metodo + " " + ruta));
    },
  );
}

beforeEach(() => {
  apiFetchMock.mockReset();
  capacidades = new Set(["gobierno_ordenes_pago:view"]);
});

describe("PoliticasOrdenPagoPage", () => {
  it("muestra el vacío sin políticas precargadas", async () => {
    respuestaExitosa([]);

    renderPagina();

    expect(
      await screen.findByText("Aún no hay políticas de orden de pago"),
    ).toBeInTheDocument();
    expect(
      screen.getByText("El producto no trae ninguna precargada."),
    ).toBeInTheDocument();
  });

  it("lista las políticas y navega al detalle desde el código", async () => {
    const borrador = politicaReal({
      id: "borrador-politica",
      codigo: "OP-DRAFT",
      nombre: "Política borrador",
      tipo_gasto: "Obras",
      tipo_regla: "OPERATIONAL_CONFIGURATION",
      estado: "BORRADOR",
      vigente_desde: "2026-12-01",
      vigente_hasta: "2026-12-31",
    });
    respuestaExitosa([borrador, politicaReal()]);

    renderPagina();

    await screen.findByText("Política de orden de pago de prueba");

    const filaBorrador = screen.getByRole("link", { name: "Abrir la política OP-DRAFT" });
    const filaBorradorCompleta = filaBorrador.closest("tr");
    expect(filaBorradorCompleta).not.toBeNull();
    if (filaBorradorCompleta) {
      expect(within(filaBorradorCompleta as HTMLElement).getByText("Política borrador")).toBeInTheDocument();
      expect(within(filaBorradorCompleta as HTMLElement).getByText("Obras")).toBeInTheDocument();
      expect(within(filaBorradorCompleta as HTMLElement).getByText("Configuración operativa")).toBeInTheDocument();
      expect(within(filaBorradorCompleta as HTMLElement).getByText("Borrador")).toBeInTheDocument();
      expect(within(filaBorradorCompleta as HTMLElement).getByText(/01\/12\/2026/)).toBeInTheDocument();
    }

    const filaVigente = screen.getByRole("link", { name: "Abrir la política OPB0C26DCB4EF7" });
    const filaVigenteCompleta = filaVigente.closest("tr");
    expect(filaVigenteCompleta).not.toBeNull();
    if (filaVigenteCompleta) {
      expect(within(filaVigenteCompleta as HTMLElement).getByText("Vigente")).toBeInTheDocument();
      expect(within(filaVigenteCompleta as HTMLElement).getByText("Política institucional")).toBeInTheDocument();
    }

    await userEvent.click(filaVigente);
    expect(await screen.findByText("politica-destino")).toBeInTheDocument();
  });

  it("muestra Nueva política solo con la capacidad policy", async () => {
    respuestaExitosa([]);

    const { unmount } = renderPagina();

    await screen.findByText("Aún no hay políticas de orden de pago");
    expect(screen.queryByRole("link", { name: "Nueva política" })).not.toBeInTheDocument();

    unmount();

    capacidades = new Set(["gobierno_ordenes_pago:view", "gobierno_ordenes_pago:policy"]);
    apiFetchMock.mockClear();
    respuestaExitosa([]);

    renderPagina();

    expect(
      await screen.findByRole("link", { name: "Nueva política" }),
    ).toBeInTheDocument();
  });

  it("precarga el patrón y muestra el ejemplo con la ayuda", async () => {
    capacidades = new Set(["gobierno_ordenes_pago:view", "gobierno_ordenes_pago:policy"]);
    respuestaExitosa([politicaReal()]);

    renderPagina();

    const campoPatron = await screen.findByRole("textbox", { name: /^Patrón/ });
    expect(campoPatron).toHaveValue("{ANIO}-{NUMERO:5}");
    expect(screen.getByText("Ejemplo: 2026-00001")).toBeInTheDocument();
    expect(screen.getByText("Variables admitidas: {ANIO}, {NUMERO:n}")).toBeInTheDocument();
  });

  it("guarda la numeración con el patrón editado", async () => {
    respuestaExitosa([politicaReal()]);
    capacidades = new Set(["gobierno_ordenes_pago:view", "gobierno_ordenes_pago:policy"]);

    const configPrevia = configuracionReal();
    let configuracionGuardada: ConfiguracionNumeracionOP | null = null;

    apiFetchMock.mockImplementation(
      (ruta: string, opciones?: { method?: string; body?: unknown; ifMatch?: string }) => {
        const metodo = opciones?.method ?? "GET";
        if (metodo === "GET" && ruta === RUTA_CONFIG) {
          return Promise.resolve(configuracionGuardada ?? configPrevia);
        }
        if (metodo === "PUT" && ruta === RUTA_CONFIG) {
          configuracionGuardada = {
            patron: (opciones?.body as { patron: string }).patron,
            ejemplo: "OP-2026-0001",
            version: 1,
            configurado: true,
          };
          return Promise.resolve(configuracionGuardada);
        }
        if (metodo === "GET" && ruta === RUTA_POLITICAS) {
          return Promise.resolve([politicaReal()]);
        }
        return Promise.reject(new Error("Ruta no esperada: " + metodo + " " + ruta));
      },
    );

    renderPagina();

    const campoPatron = await screen.findByRole("textbox", { name: /^Patrón/ });
    await userEvent.clear(campoPatron);
    fireEvent.change(campoPatron, { target: { value: "OP-{ANIO}-{NUMERO:4}" } });

    await userEvent.click(
      screen.getByRole("button", { name: "Guardar patrón" }),
    );

    await waitFor(() => {
      expect(apiFetchMock).toHaveBeenCalledWith(
        RUTA_CONFIG,
        expect.objectContaining({
          method: "PUT",
          body: { patron: "OP-{ANIO}-{NUMERO:4}" },
          ifMatch: "0",
        }),
      );
    });

    expect(await screen.findByText("Ejemplo: OP-2026-0001")).toBeInTheDocument();
  });

  it("muestra el error de campo al rechazar el PUT con 422", async () => {
    respuestaExitosa([politicaReal()]);
    capacidades = new Set(["gobierno_ordenes_pago:view", "gobierno_ordenes_pago:policy"]);

    apiFetchMock.mockImplementation(
      (ruta: string, opciones?: { method?: string; body?: unknown; ifMatch?: string }) => {
        const metodo = opciones?.method ?? "GET";
        if (metodo === "GET" && ruta === RUTA_CONFIG) {
          return Promise.resolve(configuracionReal());
        }
        if (metodo === "PUT" && ruta === RUTA_CONFIG) {
          return Promise.reject(
            new ApiError(422, {
              code: "GOV_PAYMENT_ORDER_POLICY_INVALID",
              message: "Patrón inválido",
              field_errors: { patron: ["Falta {NUMERO:n}"] },
              request_id: "r1",
            }),
          );
        }
        if (metodo === "GET" && ruta === RUTA_POLITICAS) {
          return Promise.resolve([politicaReal()]);
        }
        return Promise.reject(new Error("Ruta no esperada: " + metodo + " " + ruta));
      },
    );

    renderPagina();

    const campoPatron = await screen.findByRole("textbox", { name: /^Patrón/ });
    await userEvent.clear(campoPatron);
    fireEvent.change(campoPatron, { target: { value: "INCORRECTO" } });

    await userEvent.click(
      screen.getByRole("button", { name: "Guardar patrón" }),
    );

    expect(await screen.findByText("Falta {NUMERO:n}")).toBeInTheDocument();
  });

  it("no permite editar el patrón sin la capacidad policy", async () => {
    respuestaExitosa([politicaReal()]);

    renderPagina();

    await screen.findByText("Política de orden de pago de prueba");

    expect(screen.queryByRole("textbox", { name: /^Patrón/ })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Guardar patrón" })).not.toBeInTheDocument();
  });

  it("muestra el mensaje de permiso y no consulta la API sin la capacidad view", async () => {
    capacidades = new Set();

    renderPagina();

    expect(
      screen.getByRole("heading", {
        level: 1,
        name: "Políticas de orden de pago",
      }),
    ).toBeInTheDocument();
    expect(screen.getByText("Sin acceso")).toBeInTheDocument();
    expect(
      screen.getByText("No tiene permiso para ver las políticas de orden de pago."),
    ).toBeInTheDocument();
    expect(apiFetchMock).not.toHaveBeenCalled();
  });
});
