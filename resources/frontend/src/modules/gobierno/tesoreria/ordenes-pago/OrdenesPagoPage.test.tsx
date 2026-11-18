import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError } from "@/api/client";
import { descargarArchivo } from "@/api/descargas";
import { OrdenesPagoPage } from "./OrdenesPagoPage";
import type { OrdenPago } from "./api";

const apiFetchMock = vi.fn();

vi.mock("@/api/client", async (original) => ({
  ...(await original<typeof import("@/api/client")>()),
  apiFetch: (...args: unknown[]) => apiFetchMock(...args),
  ApiError: (await original<typeof import("@/api/client")>()).ApiError,
}));

vi.mock("@/api/descargas", () => ({
  descargarArchivo: vi.fn(async () => "ok"),
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

interface Ejercicio {
  id: string;
  anio: string;
  moneda_funcional: string;
  estado: "BORRADOR" | "APROBADO" | "RECONDUCIDO" | "CERRADO";
  version: number;
}

const ejercicio: Ejercicio = {
  id: "590e6612-437c-4033-a94e-18a12be00b4e",
  anio: "2026",
  moneda_funcional: "VES",
  estado: "APROBADO",
  version: 1,
};

function ordenReal(sobre: Partial<OrdenPago> = {}): OrdenPago {
  return {
    id: "85aa99f2-2ae4-4936-a510-a8a239cb09f2",
    codigo: "2026-00001",
    numero: 1,
    estado: "EMITIDA",
    year_id: "590e6612-437c-4033-a94e-18a12be00b4e",
    anio: 2026,
    fecha_orden: "2026-11-17",
    concepto: "Orden de pago de prueba TRE-03",
    moneda: "VES",
    monto: "50.00",
    beneficiario: "Proveedor Uno C.A.",
    policy: {
      id: "b47d44d0-9453-46d1-8c4f-240d88cf6bd1",
      codigo: "OPB0C26DCB4EF7",
      nombre: "Política de orden de pago de prueba",
      version: 2,
    },
    lineas: [
      {
        cause_id: "36d1033f-2e01-4696-9536-bf93e97949ad",
        codigo: "2026-00002",
        compromiso_codigo: "CP-2026-0002",
        beneficiario: "Proveedor Uno C.A.",
        fecha_efectiva: "2026-11-17",
        monto_causado: "50.00",
        monto_ordenado: "10.00",
        pendiente_de_ordenar: "40.00",
        monto_asignado: "10.00",
      },
      {
        cause_id: "70b81d47-294f-4d34-9ac0-c75cbd29002c",
        codigo: "2026-00001",
        compromiso_codigo: "CP-2026-0001",
        beneficiario: "Proveedor Uno C.A.",
        fecha_efectiva: "2026-11-17",
        monto_causado: "100.00",
        monto_ordenado: "40.00",
        pendiente_de_ordenar: "60.00",
        monto_asignado: "40.00",
      },
    ],
    documentos: [],
    autoridad: {
      cargo_id: "a337dd42-7979-4741-877b-6b1b7da77854",
      cargo: "Cargo ordenar N-0018-167e0a",
      unidad: "Unidad raíz ORG-04",
      funcionario_id: null,
      funcionario: null,
      usuario_id: "d1952956-1ac0-4dd2-ad4f-96db4423254f",
    },
    emitida_en: "2026-11-17T18:45:37.121595Z",
    emitida_por: "ord_t03",
    anulada_en: null,
    motivo_anulacion: null,
    huella: "8e3776179494dced2e7dd627e69470d7e495caf498870d2d1d29a94fce047c25",
    version: 2,
    monto_pagado: "0.00",
    pendiente_de_pagar: "50.00",
    siguiente_paso: "Pago (TRE-04)",
    historia: [
      { evento: "EMITIDA", fecha: "2026-11-17T18:45:37.099232+00:00", actor: "ord_t03" },
      { evento: "BORRADOR_CREADO", fecha: "2026-11-17T18:45:36.812402+00:00", actor: "ord_t03" },
    ],
    ...sobre,
  };
}

function renderPagina() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={["/gobierno/tesoreria/ordenes-pago"]}>
        <Routes>
          <Route path="/gobierno/tesoreria/ordenes-pago" element={<OrdenesPagoPage />} />
          <Route path="/gobierno/tesoreria/ordenes-pago/:id" element={<div>detalle-destino</div>} />
          <Route path="/gobierno/tesoreria/ordenes-pago/nueva" element={<div>nueva-destino</div>} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  apiFetchMock.mockReset();
  vi.mocked(descargarArchivo).mockClear();
  capacidades = new Set(["gobierno_ordenes_pago:view"]);
});

describe("OrdenesPagoPage", () => {
  it("muestra el estado de carga mientras resuelven las promesas", () => {
    apiFetchMock.mockImplementation(
      (ruta: string, opciones?: { method?: string; body?: unknown; ifMatch?: string }) => {
        const metodo = opciones?.method ?? "GET";
        if (metodo === "GET" && ruta === "/gobierno/presupuesto/ejercicios") {
          return new Promise(() => {});
        }
        return Promise.reject(new Error("Ruta no esperada: " + metodo + " " + ruta));
      },
    );

    renderPagina();

    expect(screen.getByRole("status")).toBeInTheDocument();
  });

  it("muestra el vacío cuando no hay órdenes en el ejercicio", async () => {
    apiFetchMock.mockImplementation(
      (ruta: string, opciones?: { method?: string; body?: unknown; ifMatch?: string }) => {
        const metodo = opciones?.method ?? "GET";
        if (metodo === "GET" && ruta === "/gobierno/presupuesto/ejercicios") {
          return Promise.resolve({ items: [ejercicio], total: 1 });
        }
        if (
          metodo === "GET" &&
          ruta === "/gobierno/tesoreria/ejercicios/590e6612-437c-4033-a94e-18a12be00b4e/ordenes-pago"
        ) {
          return Promise.resolve([]);
        }
        return Promise.reject(new Error("Ruta no esperada: " + metodo + " " + ruta));
      },
    );

    renderPagina();

    expect(
      await screen.findByText("Aún no hay órdenes de pago en este ejercicio"),
    ).toBeInTheDocument();
  });

  it("muestra el ErrorState cuando la lista rechaza", async () => {
    apiFetchMock.mockImplementation(
      (ruta: string, opciones?: { method?: string; body?: unknown; ifMatch?: string }) => {
        const metodo = opciones?.method ?? "GET";
        if (metodo === "GET" && ruta === "/gobierno/presupuesto/ejercicios") {
          return Promise.resolve({ items: [ejercicio], total: 1 });
        }
        if (
          metodo === "GET" &&
          ruta === "/gobierno/tesoreria/ejercicios/590e6612-437c-4033-a94e-18a12be00b4e/ordenes-pago"
        ) {
          return Promise.reject(
            new ApiError(500, {
              code: "INTERNAL",
              message: "Fallo interno",
              field_errors: {},
              request_id: "r1",
            }),
          );
        }
        return Promise.reject(new Error("Ruta no esperada: " + metodo + " " + ruta));
      },
    );

    renderPagina();

    expect(
      await screen.findByText("No se pudieron cargar las órdenes de pago"),
    ).toBeInTheDocument();
    expect(screen.getByText("Fallo interno")).toBeInTheDocument();
  });

  it("lista una orden emitida y un borrador con sus datos", async () => {
    const borrador = ordenReal({
      id: "borrador-1",
      codigo: null,
      numero: null,
      estado: "BORRADOR",
      fecha_orden: "2026-11-18",
      monto: "1200.50",
      beneficiario: "Otro Proveedor S.A.",
      lineas: [
        {
          cause_id: "causa-1",
          codigo: "C-5",
          compromiso_codigo: "CP-5",
          beneficiario: "Otro Proveedor S.A.",
          fecha_efectiva: "2026-11-18",
          monto_causado: "1200.50",
          monto_ordenado: "0.00",
          pendiente_de_ordenar: "1200.50",
          monto_asignado: "0.00",
        },
      ],
    });

    apiFetchMock.mockImplementation(
      (ruta: string, opciones?: { method?: string; body?: unknown; ifMatch?: string }) => {
        const metodo = opciones?.method ?? "GET";
        if (metodo === "GET" && ruta === "/gobierno/presupuesto/ejercicios") {
          return Promise.resolve({ items: [ejercicio], total: 1 });
        }
        if (
          metodo === "GET" &&
          ruta === "/gobierno/tesoreria/ejercicios/590e6612-437c-4033-a94e-18a12be00b4e/ordenes-pago"
        ) {
          return Promise.resolve([ordenReal(), borrador]);
        }
        return Promise.reject(new Error("Ruta no esperada: " + metodo + " " + ruta));
      },
    );

    renderPagina();

    const filaEmitida = await screen.findByRole("cell", { name: "2026-00001" });
    const filaEmitidaCompleta = filaEmitida.closest("tr");
    expect(filaEmitidaCompleta).not.toBeNull();
    if (filaEmitidaCompleta) {
      expect(within(filaEmitidaCompleta as HTMLElement).getByText("Proveedor Uno C.A.")).toBeInTheDocument();
      expect(within(filaEmitidaCompleta as HTMLElement).getByText("50.00")).toBeInTheDocument();
      expect(within(filaEmitidaCompleta as HTMLElement).getByText("Emitida")).toBeInTheDocument();
      expect(within(filaEmitidaCompleta as HTMLElement).getByText("2026-00002, 2026-00001")).toBeInTheDocument();
    }

    const filaBorradorCompleta = screen.getByRole("row", { name: /Otro Proveedor S\.A\./ });
    expect(within(filaBorradorCompleta).getByText("Otro Proveedor S.A.")).toBeInTheDocument();
    expect(within(filaBorradorCompleta).getByText("C-5")).toBeInTheDocument();

    const celdaEmitida = screen.getByRole("cell", { name: "Emitida" });
    expect(celdaEmitida).toBeInTheDocument();
  });

  it("navega al detalle desde el enlace del código", async () => {
    apiFetchMock.mockImplementation(
      (ruta: string, opciones?: { method?: string; body?: unknown; ifMatch?: string }) => {
        const metodo = opciones?.method ?? "GET";
        if (metodo === "GET" && ruta === "/gobierno/presupuesto/ejercicios") {
          return Promise.resolve({ items: [ejercicio], total: 1 });
        }
        if (
          metodo === "GET" &&
          ruta === "/gobierno/tesoreria/ejercicios/590e6612-437c-4033-a94e-18a12be00b4e/ordenes-pago"
        ) {
          return Promise.resolve([ordenReal()]);
        }
        return Promise.reject(new Error("Ruta no esperada: " + metodo + " " + ruta));
      },
    );

    renderPagina();

    await userEvent.click(
      await screen.findByRole("link", { name: "2026-00001" }),
    );

    expect(await screen.findByText("detalle-destino")).toBeInTheDocument();
  });

  it("vuelve a consultar al cambiar el filtro de estado", async () => {
    apiFetchMock.mockImplementation(
      (ruta: string, opciones?: { method?: string; body?: unknown; ifMatch?: string }) => {
        const metodo = opciones?.method ?? "GET";
        if (metodo === "GET" && ruta === "/gobierno/presupuesto/ejercicios") {
          return Promise.resolve({ items: [ejercicio], total: 1 });
        }
        if (
          metodo === "GET" &&
          (ruta === "/gobierno/tesoreria/ejercicios/590e6612-437c-4033-a94e-18a12be00b4e/ordenes-pago" ||
            ruta === "/gobierno/tesoreria/ejercicios/590e6612-437c-4033-a94e-18a12be00b4e/ordenes-pago?estado=EMITIDA")
        ) {
          return Promise.resolve([ordenReal()]);
        }
        return Promise.reject(new Error("Ruta no esperada: " + metodo + " " + ruta));
      },
    );

    renderPagina();

    await screen.findByRole("cell", { name: "2026-00001" });

    await userEvent.selectOptions(
      screen.getByRole("combobox", { name: "Estado" }),
      "EMITIDA",
    );

    await waitFor(() => {
      expect(apiFetchMock.mock.calls.some(([ruta]) => ruta === "/gobierno/tesoreria/ejercicios/590e6612-437c-4033-a94e-18a12be00b4e/ordenes-pago?estado=EMITIDA")).toBe(true);
    });
  });

  it("descarga el CSV con la ruta del reporte", async () => {
    apiFetchMock.mockImplementation(
      (ruta: string, opciones?: { method?: string; body?: unknown; ifMatch?: string }) => {
        const metodo = opciones?.method ?? "GET";
        if (metodo === "GET" && ruta === "/gobierno/presupuesto/ejercicios") {
          return Promise.resolve({ items: [ejercicio], total: 1 });
        }
        if (
          metodo === "GET" &&
          ruta === "/gobierno/tesoreria/ejercicios/590e6612-437c-4033-a94e-18a12be00b4e/ordenes-pago"
        ) {
          return Promise.resolve([ordenReal()]);
        }
        return Promise.reject(new Error("Ruta no esperada: " + metodo + " " + ruta));
      },
    );

    renderPagina();

    await userEvent.click(
      await screen.findByRole("button", { name: "Descargar CSV" }),
    );

    await waitFor(() => {
      expect(descargarArchivo).toHaveBeenCalledWith(
        "/gobierno/tesoreria/ejercicios/590e6612-437c-4033-a94e-18a12be00b4e/ordenes-pago/reporte.csv",
        "ordenes-de-pago-2026.csv",
      );
    });
  });

  it("el CSV conserva los filtros", async () => {
    apiFetchMock.mockImplementation(
      (ruta: string, opciones?: { method?: string; body?: unknown; ifMatch?: string }) => {
        const metodo = opciones?.method ?? "GET";
        if (metodo === "GET" && ruta === "/gobierno/presupuesto/ejercicios") {
          return Promise.resolve({ items: [ejercicio], total: 1 });
        }
        if (
          metodo === "GET" &&
          ruta.startsWith("/gobierno/tesoreria/ejercicios/590e6612-437c-4033-a94e-18a12be00b4e/ordenes-pago") &&
          !ruta.includes("reporte")
        ) {
          return Promise.resolve([ordenReal()]);
        }
        return Promise.reject(new Error("Ruta no esperada: " + metodo + " " + ruta));
      },
    );

    renderPagina();

    await userEvent.selectOptions(
      screen.getByRole("combobox", { name: "Estado" }),
      "EMITIDA",
    );

    await userEvent.type(screen.getByRole("textbox", { name: "Moneda" }), "VES");

    await userEvent.click(
      await screen.findByRole("button", { name: "Descargar CSV" }),
    );

    await waitFor(() => {
      expect(descargarArchivo).toHaveBeenCalledWith(
        "/gobierno/tesoreria/ejercicios/590e6612-437c-4033-a94e-18a12be00b4e/ordenes-pago/reporte.csv?estado=EMITIDA&moneda=VES",
        "ordenes-de-pago-2026.csv",
      );
    });
  });

  it("muestra el mensaje de permiso sin pedir la lista", async () => {
    capacidades = new Set();

    renderPagina();

    expect(
      screen.getByText("No tiene permiso para consultar órdenes de pago"),
    ).toBeInTheDocument();
    expect(apiFetchMock).not.toHaveBeenCalled();
  });

  it("muestra Nueva orden de pago solo con la capacidad manage", async () => {
    apiFetchMock.mockImplementation(
      (ruta: string, opciones?: { method?: string; body?: unknown; ifMatch?: string }) => {
        const metodo = opciones?.method ?? "GET";
        if (metodo === "GET" && ruta === "/gobierno/presupuesto/ejercicios") {
          return Promise.resolve({ items: [ejercicio], total: 1 });
        }
        if (
          metodo === "GET" &&
          ruta === "/gobierno/tesoreria/ejercicios/590e6612-437c-4033-a94e-18a12be00b4e/ordenes-pago"
        ) {
          return Promise.resolve([]);
        }
        return Promise.reject(new Error("Ruta no esperada: " + metodo + " " + ruta));
      },
    );

    const { unmount } = renderPagina();

    await screen.findByText("Aún no hay órdenes de pago en este ejercicio");
    expect(screen.queryByRole("link", { name: "Nueva orden de pago" })).not.toBeInTheDocument();

    unmount();

    capacidades = new Set(["gobierno_ordenes_pago:view", "gobierno_ordenes_pago:manage"]);
    apiFetchMock.mockClear();

    renderPagina();

    expect(
      await screen.findByRole("link", { name: "Nueva orden de pago" }),
    ).toBeInTheDocument();
  });

  it("muestra el mensaje real cuando no hay ejercicios disponibles", async () => {
    apiFetchMock.mockImplementation(
      (ruta: string, opciones?: { method?: string; body?: unknown; ifMatch?: string }) => {
        const metodo = opciones?.method ?? "GET";
        if (metodo === "GET" && ruta === "/gobierno/presupuesto/ejercicios") {
          return Promise.resolve({ items: [], total: 0 });
        }
        return Promise.reject(new Error("Ruta no esperada: " + metodo + " " + ruta));
      },
    );

    renderPagina();

    expect(
      await screen.findByText("No hay ejercicios presupuestarios aprobados"),
    ).toBeInTheDocument();
  });
});
