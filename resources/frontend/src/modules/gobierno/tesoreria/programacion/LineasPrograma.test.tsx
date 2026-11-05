import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "@/api/client";
import type {
  LineaPrograma,
  OpcionesPrograma,
  ProgramaDetalle,
} from "@/modules/gobierno/api";
import { LineasPrograma } from "./LineasPrograma";

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

const rubro = {
  id: "r1",
  codigo: "4.01",
  nombre: "Personal",
  tipo: "DESEMBOLSO" as const,
  estado: "ACTIVO" as const,
};

const linea: LineaPrograma = {
  id: "l1",
  rubro_id: "r1",
  rubro_codigo: "4.01",
  rubro_nombre: "Personal",
  tipo: "DESEMBOLSO" as const,
  mes: 1,
  monto: "1500.50",
};

const programaBase: ProgramaDetalle = {
  id: "p1",
  codigo: "PG-2026-0001",
  ejercicio: 2026,
  moneda: "VES" as const,
  mes_inicial: 1,
  estado: "BORRADOR" as const,
  version: 3,
  version_vigente: null,
  disponibilidad_inicial: "0",
  version_vista: 3,
  borrador_numero: null,
  cerrado_por: null,
  cerrado_en: null,
  motivo_cierre: null,
  registrado_por: "ua",
  registrado_en: "2026-11-01T12:00:00Z",
  declaraciones: [],
  lineas: [linea],
  meses: [],
  hay_deficit: false,
  versiones: [],
  historia: [],
};

const opciones: OpcionesPrograma = {
  cuentas: [],
  rubros: [rubro],
};

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { retry: false },
  },
});

function renderLineas(programa: ProgramaDetalle, editable = true) {
  const onCambio = vi.fn();
  const result = render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <LineasPrograma
          programa={programa}
          editable={editable}
          onCambio={onCambio}
        />
      </MemoryRouter>
    </QueryClientProvider>,
  );
  return { ...result, onCambio };
}

describe("LineasPrograma", () => {
  beforeEach(() => {
    apiFetchMock.mockReset();
    notifyMock.mockReset();
    queryClient.clear();
    capacidades = new Set(["gobierno_caja:manage"]);
  });

  it("LP-01: lista las líneas de la versión mostrada", async () => {
    apiFetchMock.mockResolvedValueOnce(opciones);
    renderLineas(programaBase);

    expect(await screen.findByText(/Enero/)).toBeInTheDocument();
    expect(screen.getByText(/4\.01 · Personal/)).toBeInTheDocument();
    expect(screen.getByText(/Desembolso/)).toBeInTheDocument();
  });

  it("LP-02: solo lectura no muestra acciones", async () => {
    apiFetchMock.mockResolvedValueOnce(opciones);
    renderLineas(programaBase, false);

    expect(await screen.findByText(/Enero/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Añadir línea" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Cambiar monto/ })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Quitar línea/ })).not.toBeInTheDocument();
  });

  it("LP-03: añadir línea válida llama a POST con cuerpo e If-Match", async () => {
    const user = userEvent.setup();
    apiFetchMock.mockResolvedValueOnce(opciones);
    apiFetchMock.mockResolvedValueOnce(programaBase);

    const { onCambio } = renderLineas(programaBase);

    await user.click(await screen.findByRole("button", { name: "Añadir línea" }));
    await user.selectOptions(screen.getByRole("combobox", { name: /^Rubro/ }), "r1");
    await user.selectOptions(screen.getByRole("combobox", { name: /^Mes/ }), "2");
    await user.type(screen.getByLabelText(/^Monto/), "2500.75");
    await user.click(screen.getByRole("button", { name: "Añadir línea" }));

    await waitFor(() => {
      expect(apiFetchMock).toHaveBeenCalledWith(
        "/gobierno/tesoreria/programas/p1/lineas",
        {
          method: "POST",
          body: { rubro_id: "r1", mes: 2, monto: "2500.75" },
          ifMatch: "3",
        },
      );
    });
    expect(onCambio).toHaveBeenCalled();
    expect(notifyMock).toHaveBeenCalledWith({ type: "success", title: "Línea añadida" });
  });

  it("LP-04: añadir con mes pasado muestra error del servidor", async () => {
    const user = userEvent.setup();
    const error = new ApiError(409, {
      code: "GOV_CASH_PROGRAM_PAST_MONTH",
      message: "No se puede programar un mes pasado",
      details: null,
    });

    apiFetchMock.mockResolvedValueOnce(opciones);
    apiFetchMock.mockRejectedValueOnce(error);

    renderLineas({ ...programaBase, mes_inicial: 5 });

    await user.click(await screen.findByRole("button", { name: "Añadir línea" }));
    await user.selectOptions(screen.getByRole("combobox", { name: /^Rubro/ }), "r1");
    await user.selectOptions(screen.getByRole("combobox", { name: /^Mes/ }), "5");
    await user.type(screen.getByLabelText(/^Monto/), "100");
    await user.click(screen.getByRole("button", { name: "Añadir línea" }));

    await waitFor(() => {
      expect(apiFetchMock).toHaveBeenCalledTimes(2);
      expect(apiFetchMock).toHaveBeenNthCalledWith(
        2,
        "/gobierno/tesoreria/programas/p1/lineas",
        {
          method: "POST",
          body: { rubro_id: "r1", mes: 5, monto: "100" },
          ifMatch: "3",
        },
      );
    });
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "No se puede programar un mes pasado",
    );
  });

  it("LP-05: cambiar y quitar con If-Match", async () => {
    const user = userEvent.setup();
    apiFetchMock.mockResolvedValueOnce(opciones);
    apiFetchMock.mockResolvedValueOnce(programaBase);
    apiFetchMock.mockResolvedValueOnce(programaBase);

    const { onCambio } = renderLineas(programaBase);

    await user.click(await screen.findByRole("button", { name: /Cambiar monto/ }));
    await user.clear(screen.getByLabelText(/^Monto/));
    await user.type(screen.getByLabelText(/^Monto/), "2000");
    await user.click(screen.getByRole("button", { name: "Guardar" }));

    await waitFor(() => {
      expect(apiFetchMock).toHaveBeenCalledWith(
        "/gobierno/tesoreria/programas/p1/lineas/l1",
        {
          method: "PATCH",
          body: { monto: "2000" },
          ifMatch: "3",
        },
      );
    });
    expect(onCambio).toHaveBeenCalled();

    apiFetchMock.mockClear();
    apiFetchMock.mockResolvedValueOnce(opciones);
    apiFetchMock.mockResolvedValueOnce(programaBase);
    await user.click(screen.getByRole("button", { name: /Quitar línea/ }));

    await waitFor(() => {
      expect(apiFetchMock).toHaveBeenCalledWith(
        "/gobierno/tesoreria/programas/p1/lineas/l1",
        {
          method: "DELETE",
          ifMatch: "3",
        },
      );
    });
  });

  it("LP-06: meses desde el mes inicial", async () => {
    const user = userEvent.setup();
    apiFetchMock.mockResolvedValueOnce(opciones);

    renderLineas({ ...programaBase, mes_inicial: 4 });

    await user.click(await screen.findByRole("button", { name: "Añadir línea" }));
    const select = screen.getByRole("combobox", { name: /^Mes/ });
    expect(select).toHaveTextContent("Abril");
    expect(select).not.toHaveTextContent("Marzo");
  });

  it("LP-07: error GOV_CASH_LINE_DUPLICATE muestra mensaje", async () => {
    const user = userEvent.setup();
    const error = new ApiError(409, {
      code: "GOV_CASH_LINE_DUPLICATE",
      message: "Ya existe una línea para ese rubro y mes",
      details: null,
    });

    apiFetchMock.mockResolvedValueOnce(opciones);
    apiFetchMock.mockRejectedValueOnce(error);

    renderLineas(programaBase);

    await user.click(await screen.findByRole("button", { name: "Añadir línea" }));
    await user.selectOptions(screen.getByRole("combobox", { name: /^Rubro/ }), "r1");
    await user.selectOptions(screen.getByRole("combobox", { name: /^Mes/ }), "2");
    await user.type(screen.getByLabelText(/^Monto/), "100");
    await user.click(screen.getByRole("button", { name: "Añadir línea" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Ya existe una línea para ese rubro y mes",
    );
  });

  it("LP-08: error GOV_CASH_PROGRAM_STALE alerta y llama a onCambio", async () => {
    const user = userEvent.setup();
    const error = new ApiError(409, {
      code: "GOV_CASH_PROGRAM_STALE",
      message: "El programa fue modificado",
      details: null,
    });

    apiFetchMock.mockResolvedValueOnce(opciones);
    apiFetchMock.mockRejectedValueOnce(error);

    const { onCambio } = renderLineas(programaBase);

    await user.click(await screen.findByRole("button", { name: "Añadir línea" }));
    await user.selectOptions(screen.getByRole("combobox", { name: /^Rubro/ }), "r1");
    await user.selectOptions(screen.getByRole("combobox", { name: /^Mes/ }), "2");
    await user.type(screen.getByLabelText(/^Monto/), "100");
    await user.click(screen.getByRole("button", { name: "Añadir línea" }));

    await waitFor(() => {
      expect(onCambio).toHaveBeenCalled();
    });
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "El programa fue modificado por otra persona",
    );
  });

  it("LP-09: sin rubros activos muestra aviso", async () => {
    apiFetchMock.mockResolvedValueOnce({ cuentas: [], rubros: [] });

    renderLineas({
      ...programaBase,
      lineas: [] as LineaPrograma[],
    });

    expect(await screen.findByText(/No hay rubros activos/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Gestione los rubros/ })).toBeInTheDocument();
  });
});
