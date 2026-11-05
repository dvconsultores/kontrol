
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "@/api/client";
import type { AutorizadoCuenta, CuentaDetalle } from "@/modules/gobierno/api";
import { AutorizadosCuenta } from "./AutorizadosCuenta";

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

const acto = {
  id: "a1",
  tipo: "RESOLUCION",
  numero: "R-1",
  fecha: "2026-11-01",
  estado: "EMITIDO",
  asunto: "Apertura",
};

const opciones = {
  bancos: [{ id: "b1", codigo: "0102", nombre: "Banco Uno" }],
  cargos: [{ id: "g1", codigo: "DIR", denominacion: "Director", unidad: "Dirección" }],
  actos: [acto],
};

const autorizado = {
  id: "z1",
  cargo_id: "g1",
  cargo_codigo: "DIR",
  cargo_denominacion: "Director",
  cargo_unidad: "Dirección",
  cargo_vigente: true,
  acto_alta: acto,
  vigente_desde: "2026-11-01",
  vigente_hasta: null,
  acto_fin: null,
  motivo_fin: null,
  en_vigor: true,
  registrada_por: "ua",
  registrada_en: "2026-11-01T12:00:00Z",
  terminada_por: null,
  terminada_en: null,
};

const detalleBase: CuentaDetalle = {
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
  version: 3,
  acto: null,
  registrada_por: "ua",
  registrada_en: "2026-11-01T12:00:00Z",
  activada_por: null,
  activada_en: null,
  cerrada_por: null,
  cerrada_en: null,
  fecha_cierre: null,
  motivo_cierre: null,
  autorizados: [] as AutorizadoCuenta[],
  historia: [
    {
      tipo: "CREADA",
      detalle: null,
      registrado_por: "ua",
      registrado_en: "2026-11-01T12:00:00Z",
    },
  ],
};

function renderAutorizados(cuenta: CuentaDetalle) {
  const alCambiar = vi.fn();
  const alFallar = vi.fn();
  const result = render(
    <MemoryRouter>
      <AutorizadosCuenta
        cuenta={cuenta}
        opciones={opciones}
        alCambiar={alCambiar}
        alFallar={alFallar}
      />
    </MemoryRouter>,
  );
  return { ...result, alCambiar, alFallar };
}

describe("AutorizadosCuenta", () => {
  beforeEach(() => {
    apiFetchMock.mockReset();
    notifyMock.mockReset();
    capacidades = new Set(["gobierno_cuentas:manage"]);
  });

  it("AC-01: sin manage muestra la tabla sin acciones", async () => {
    capacidades = new Set();
    const cuenta = { ...detalleBase, autorizados: [autorizado] };

    renderAutorizados(cuenta);

    expect(await screen.findByText(/DIR · Director/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Autorizar un cargo" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Terminar la autorización de DIR/ })).not.toBeInTheDocument();
  });

  it("AC-02: con manage abre el formulario y valida vacío sin POST", async () => {
    const user = userEvent.setup();
    const cuenta = { ...detalleBase, autorizados: [autorizado] };

    renderAutorizados(cuenta);

    await user.click(await screen.findByRole("button", { name: "Autorizar un cargo" }));
    await user.click(screen.getByRole("button", { name: "Registrar autorización" }));

    expect(await screen.findByText("Elija un cargo")).toBeInTheDocument();
    expect(screen.getByText("Elija un acto")).toBeInTheDocument();
    expect(apiFetchMock).not.toHaveBeenCalled();
  });

  it("AC-03: alta válida llama a la API y a alCambiar", async () => {
    const user = userEvent.setup();
    const cuenta = { ...detalleBase };
    const respuesta = { ...detalleBase, autorizados: [autorizado], version: 4 };

    apiFetchMock.mockResolvedValueOnce(respuesta);

    const { alCambiar } = renderAutorizados(cuenta);

    await user.click(await screen.findByRole("button", { name: "Autorizar un cargo" }));
    await user.selectOptions(screen.getByRole("combobox", { name: /^Cargo/ }), "g1");
    await user.selectOptions(screen.getByLabelText(/Acto que lo autoriza/), "a1");
    const fecha = screen.getByLabelText(/^Autorizado desde/);
    await user.clear(fecha);
    await user.type(fecha, "2026-11-10");
    await user.click(screen.getByRole("button", { name: "Registrar autorización" }));

    await waitFor(() => {
      expect(apiFetchMock).toHaveBeenCalledWith(
        "/gobierno/tesoreria/cuentas/c1/autorizados",
        {
          method: "POST",
          body: { cargo_id: "g1", acto_id: "a1", vigente_desde: "2026-11-10" },
          ifMatch: "3",
        },
      );
    });
    expect(alCambiar).toHaveBeenCalledWith(respuesta);
    expect(notifyMock).toHaveBeenCalledWith({ type: "success", title: "Autorización registrada" });
  });

  it("AC-04: el campo Cargo es un select, no un input de texto", async () => {
    const user = userEvent.setup();
    const cuenta = { ...detalleBase };

    renderAutorizados(cuenta);

    await user.click(await screen.findByRole("button", { name: "Autorizar un cargo" }));

    expect(screen.queryByLabelText(/nombre/i)).not.toBeInTheDocument();
    expect(screen.getByRole("combobox", { name: /^Cargo/ })).toBeInTheDocument();
  });

  it("AC-05: acto_sin_efecto oculta el botón de autorizar", async () => {
    const cuenta = { ...detalleBase, acto_sin_efecto: true };

    renderAutorizados(cuenta);

    await waitFor(() => {
      expect(screen.queryByRole("button", { name: "Autorizar un cargo" })).not.toBeInTheDocument();
    });
  });

  it("AC-06: terminar con motivo corto muestra error sin POST", async () => {
    const user = userEvent.setup();
    const cuenta = { ...detalleBase, autorizados: [autorizado] };

    renderAutorizados(cuenta);

    await user.click(await screen.findByRole("button", { name: /Terminar la autorización de DIR/ }));
    await user.selectOptions(screen.getByLabelText(/^Acto de fin/), "a1");
    await user.type(screen.getByLabelText(/^Motivo/), "corto");
    await user.click(screen.getByRole("button", { name: "Confirmar fin" }));

    expect(await screen.findByText("El motivo debe tener al menos 10 caracteres")).toBeInTheDocument();
    expect(apiFetchMock).not.toHaveBeenCalled();
  });

  it("AC-07: fin válido llama a la API correcta", async () => {
    const user = userEvent.setup();
    const cuenta = { ...detalleBase, autorizados: [autorizado] };
    const respuesta = {
      ...detalleBase,
      autorizados: [{ ...autorizado, en_vigor: false, vigente_hasta: "2026-11-10", motivo_fin: "Cambio de cargo" }],
      version: 4,
    };

    apiFetchMock.mockResolvedValueOnce(respuesta);

    const { alCambiar } = renderAutorizados(cuenta);

    await user.click(await screen.findByRole("button", { name: /Terminar la autorización de DIR/ }));
    await user.selectOptions(screen.getByLabelText(/^Acto de fin/), "a1");
    await user.clear(screen.getByLabelText(/^Vigente hasta/));
    await user.type(screen.getByLabelText(/^Vigente hasta/), "2026-11-10");
    await user.type(screen.getByLabelText(/^Motivo/), "Cambio de cargo por reestructuración");
    await user.click(screen.getByRole("button", { name: "Confirmar fin" }));

    await waitFor(() => {
      expect(apiFetchMock).toHaveBeenCalledWith(
        "/gobierno/tesoreria/cuentas/c1/autorizados/z1/fin",
        {
          method: "POST",
          body: { acto_id: "a1", vigente_hasta: "2026-11-10", motivo: "Cambio de cargo por reestructuración" },
          ifMatch: "3",
        },
      );
    });
    expect(alCambiar).toHaveBeenCalledWith(respuesta);
    expect(notifyMock).toHaveBeenCalledWith({ type: "success", title: "Autorización terminada" });
  });

  it("AC-08: error de la API llama a alFallar", async () => {
    const user = userEvent.setup();
    const cuenta = { ...detalleBase };
    const error = new ApiError(409, {
      code: "CONFLICTO_VERSION",
      message: "La cuenta fue modificada",
      details: null,
    });

    apiFetchMock.mockRejectedValueOnce(error);

    const { alFallar } = renderAutorizados(cuenta);

    await user.click(await screen.findByRole("button", { name: "Autorizar un cargo" }));
    await user.selectOptions(screen.getByRole("combobox", { name: /^Cargo/ }), "g1");
    await user.selectOptions(screen.getByLabelText(/Acto que lo autoriza/), "a1");
    await user.click(screen.getByRole("button", { name: "Registrar autorización" }));

    await waitFor(() => {
      expect(alFallar).toHaveBeenCalledWith(error);
    });
  });

  it("AC-09: cargo no vigente muestra alerta", async () => {
    const cuenta = {
      ...detalleBase,
      autorizados: [{ ...autorizado, cargo_vigente: false }],
    };

    renderAutorizados(cuenta);

    expect(await screen.findByText(/El cargo DIR ya no está vigente\./)).toBeInTheDocument();
  });

  it("AC-10: autorización terminada muestra motivo_fin sin botón", async () => {
    const autorizadoTerminado = {
      ...autorizado,
      en_vigor: false,
      vigente_hasta: "2026-11-10",
      motivo_fin: "Cambio de cargo",
      acto_fin: acto,
    };
    const cuenta = { ...detalleBase, autorizados: [autorizadoTerminado] };

    renderAutorizados(cuenta);

    expect(await screen.findByText("Cambio de cargo")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Terminar la autorización de DIR/ })).not.toBeInTheDocument();
  });

  it("AC-11: cuenta CERRADA oculta todas las acciones", async () => {
    const cuenta = { ...detalleBase, estado: "CERRADA" as const, autorizados: [autorizado] };

    renderAutorizados(cuenta);

    expect(await screen.findByText(/DIR · Director/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Autorizar un cargo" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Terminar la autorización de DIR/ })).not.toBeInTheDocument();
  });

  it("AC-12: sin autorizados muestra mensaje vacío", async () => {
    const cuenta = { ...detalleBase, autorizados: [] };

    renderAutorizados(cuenta);

    expect(await screen.findByText("Aún no hay cargos autorizados.")).toBeInTheDocument();
  });
});
