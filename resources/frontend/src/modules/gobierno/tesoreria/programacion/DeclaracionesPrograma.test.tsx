import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "@/api/client";
import type {
  DeclaracionPrograma,
  OpcionesPrograma,
  ProgramaDetalle,
} from "@/modules/gobierno/api";
import { DeclaracionesPrograma } from "./DeclaracionesPrograma";

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

const declaracion: DeclaracionPrograma = {
  id: "d1",
  cuenta_id: "cu1",
  cuenta_codigo: "CB-0001",
  cuenta_denominacion: "Fondos de funcionamiento",
  banco_nombre: "Banco Uno",
  monto: "150000.00",
  fecha_corte: "2026-11-01",
  fundamento: "Disponibilidad inicial",
  declarado_por: "ua",
  declarado_en: "2026-11-01T12:00:00Z",
};

const detalleBase: ProgramaDetalle = {
  id: "p1",
  codigo: "PG-2026-0001",
  ejercicio: 2026,
  moneda: "USD",
  mes_inicial: 1,
  estado: "BORRADOR",
  version: 3,
  version_vigente: null,
  disponibilidad_inicial: "150000.00",
  version_vista: 3,
  borrador_numero: null,
  cerrado_por: null,
  cerrado_en: null,
  motivo_cierre: null,
  registrado_por: "ua",
  registrado_en: "2026-11-01T12:00:00Z",
  declaraciones: [] as DeclaracionPrograma[],
  lineas: [],
  meses: [],
  hay_deficit: false,
  versiones: [],
  historia: [],
};

const opciones: OpcionesPrograma = {
  cuentas: [
    {
      id: "cu1",
      codigo: "CB-0001",
      denominacion: "Fondos de funcionamiento",
      banco_nombre: "Banco Uno",
    },
  ],
  rubros: [],
};

function renderDeclaraciones(
  programa: ProgramaDetalle,
  editable = true,
) {
  const onCambio = vi.fn();
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });
  const result = render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <DeclaracionesPrograma
          programa={programa}
          editable={editable}
          onCambio={onCambio}
        />
      </MemoryRouter>
    </QueryClientProvider>,
  );
  return { ...result, onCambio };
}

describe("DeclaracionesPrograma", () => {
  beforeEach(() => {
    apiFetchMock.mockReset();
    notifyMock.mockReset();
    capacidades = new Set(["gobierno_caja:manage"]);
    apiFetchMock.mockImplementation((...args: unknown[]) => {
      const url = String(args[0]);
      if (url.endsWith("/opciones")) {
        return Promise.resolve(opciones);
      }
      return Promise.reject(new Error("Unexpected API call"));
    });
  });

  it("lista las declaraciones sin número de cuenta", async () => {
    const programa = { ...detalleBase, declaraciones: [declaracion] };

    renderDeclaraciones(programa, false);

    expect(await screen.findByText(/CB-0001 · Fondos de funcionamiento/)).toBeInTheDocument();
    expect(screen.getByText("Banco Uno")).toBeInTheDocument();
    expect(screen.getByText(/150\.000,00/)).toBeInTheDocument();
    expect(screen.getByText("Disponibilidad inicial")).toBeInTheDocument();
    expect(screen.queryByText(/\d{20}|••••/)).not.toBeInTheDocument();
  });

  it("solo lectura sin botones de declarar o quitar", async () => {
    const programa = { ...detalleBase, declaraciones: [declaracion] };

    renderDeclaraciones(programa, false);

    expect(await screen.findByText(/CB-0001 · Fondos de funcionamiento/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Declarar" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Quitar declaración de CB-0001/ })).not.toBeInTheDocument();
  });

  it("declarar válido envía POST con ifMatch y llama a onCambio", async () => {
    const user = userEvent.setup();
    const programa = { ...detalleBase };
    const respuesta: DeclaracionPrograma = declaracion;
    apiFetchMock.mockImplementation((...args: unknown[]) => {
      const url = String(args[0]);
      const options = args[1] as { method?: string } | undefined;
      if (url.endsWith("/opciones")) {
        return Promise.resolve(opciones);
      }
      if (options?.method === "POST") {
        return Promise.resolve(respuesta);
      }
      return Promise.reject(new Error("Unexpected API call"));
    });

    const { onCambio } = renderDeclaraciones(programa);

    await user.click(await screen.findByRole("button", { name: "Declarar" }));
    await user.selectOptions(screen.getByLabelText(/^Cuenta/), "cu1");
    await user.type(screen.getByLabelText(/^Monto/), "150000");
    await user.clear(screen.getByLabelText(/^Fecha de corte/));
    await user.type(screen.getByLabelText(/^Fecha de corte/), "2026-11-01");
    await user.type(screen.getByLabelText(/^Fundamento/), "Disponibilidad inicial");
    await user.click(screen.getByRole("button", { name: "Registrar declaración" }));

    await waitFor(() => {
      expect(apiFetchMock).toHaveBeenCalledWith(
        "/gobierno/tesoreria/programas/p1/declaraciones",
        {
          method: "POST",
          body: {
            cuenta_id: "cu1",
            monto: "150000",
            fecha_corte: "2026-11-01",
            fundamento: "Disponibilidad inicial",
          },
          ifMatch: "3",
        },
      );
    });
    expect(onCambio).toHaveBeenCalled();
    expect(notifyMock).toHaveBeenCalledWith({ type: "success", title: "Declaración registrada" });
  });

  it("duplicada muestra error de cuenta sin llamar onCambio", async () => {
    const user = userEvent.setup();
    const programa = { ...detalleBase };
    apiFetchMock.mockImplementation((...args: unknown[]) => {
      const url = String(args[0]);
      const options = args[1] as { method?: string } | undefined;
      if (url.endsWith("/opciones")) {
        return Promise.resolve(opciones);
      }
      if (options?.method === "POST") {
        return Promise.reject(
          new ApiError(409, {
            code: "GOV_CASH_DECLARATION_DUPLICATE",
            message: "Ya existe una declaración",
            field_errors: {},
            details: null,
          }),
        );
      }
      return Promise.reject(new Error("Unexpected API call"));
    });

    const { onCambio } = renderDeclaraciones(programa);

    await user.click(await screen.findByRole("button", { name: "Declarar" }));
    await user.selectOptions(screen.getByLabelText(/^Cuenta/), "cu1");
    await user.type(screen.getByLabelText(/^Monto/), "150000");
    await user.type(screen.getByLabelText(/^Fundamento/), "Disponibilidad inicial");
    await user.click(screen.getByRole("button", { name: "Registrar declaración" }));

    expect(await screen.findByText("Ya existe una declaración para esta cuenta")).toBeInTheDocument();
    expect(onCambio).not.toHaveBeenCalled();
    expect(notifyMock).not.toHaveBeenCalled();
  });

  it("quitar envía DELETE con ifMatch y llama a onCambio", async () => {
    const user = userEvent.setup();
    const programa = { ...detalleBase, declaraciones: [declaracion] };
    apiFetchMock.mockImplementation((...args: unknown[]) => {
      const url = String(args[0]);
      const options = args[1] as { method?: string } | undefined;
      if (url.endsWith("/opciones")) {
        return Promise.resolve(opciones);
      }
      if (options?.method === "DELETE") {
        return Promise.resolve(null);
      }
      return Promise.reject(new Error("Unexpected API call"));
    });

    const { onCambio } = renderDeclaraciones(programa);

    await user.click(await screen.findByRole("button", { name: /Quitar declaración de CB-0001/ }));

    await waitFor(() => {
      expect(apiFetchMock).toHaveBeenCalledWith(
        "/gobierno/tesoreria/programas/p1/declaraciones/d1",
        {
          method: "DELETE",
          ifMatch: "3",
        },
      );
    });
    expect(onCambio).toHaveBeenCalled();
    expect(notifyMock).toHaveBeenCalledWith({ type: "success", title: "Declaración eliminada" });
  });

  it("sin cuentas muestra aviso con enlace a cuentas", async () => {
    const user = userEvent.setup();
    const programa = { ...detalleBase };
    apiFetchMock.mockImplementation((...args: unknown[]) => {
      const url = String(args[0]);
      if (url.endsWith("/opciones")) {
        return Promise.resolve({ cuentas: [], rubros: [] });
      }
      return Promise.reject(new Error("Unexpected API call"));
    });

    renderDeclaraciones(programa);

    await user.click(await screen.findByRole("button", { name: "Declarar" }));

    expect(await screen.findByText(/No hay cuentas disponibles/)).toBeInTheDocument();
    const enlace = screen.getByRole("link", { name: "Administre cuentas" });
    expect(enlace).toHaveAttribute("href", "/gobierno/tesoreria/cuentas");
  });

  it("versión vieja notifica alerta y llama onCambio", async () => {
    const user = userEvent.setup();
    const programa = { ...detalleBase };
    apiFetchMock.mockImplementation((...args: unknown[]) => {
      const url = String(args[0]);
      const options = args[1] as { method?: string } | undefined;
      if (url.endsWith("/opciones")) {
        return Promise.resolve(opciones);
      }
      if (options?.method === "POST") {
        return Promise.reject(
          new ApiError(409, {
            code: "GOV_CASH_PROGRAM_STALE",
            message: "Versión antigua",
            field_errors: {},
            details: null,
          }),
        );
      }
      return Promise.reject(new Error("Unexpected API call"));
    });

    const { onCambio } = renderDeclaraciones(programa);

    await user.click(await screen.findByRole("button", { name: "Declarar" }));
    await user.selectOptions(screen.getByLabelText(/^Cuenta/), "cu1");
    await user.type(screen.getByLabelText(/^Monto/), "150000");
    await user.type(screen.getByLabelText(/^Fundamento/), "Disponibilidad inicial");
    await user.click(screen.getByRole("button", { name: "Registrar declaración" }));

    const alertas = await screen.findAllByText(
      "El programa fue modificado. Recargue la página.",
    );
    expect(alertas.length).toBeGreaterThanOrEqual(1);
    expect(onCambio).toHaveBeenCalled();
  });
});
