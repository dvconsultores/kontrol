import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";

const apiFetchMock = vi.fn();

vi.mock("@/api/client", async (original) => ({
  ...(await original<typeof import("@/api/client")>()),
  apiFetch: (...args: unknown[]) => apiFetchMock(...args),
}));

vi.mock("@/api/descargas", () => ({
  descargarArchivo: vi.fn(),
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

const { DisponibilidadEjercicio } = await import("./DisponibilidadEjercicio");
const { descargarArchivo } = await import("@/api/descargas");

import type {
  Certificacion,
  CertificacionesVista,
  DisponibilidadVista,
  EjercicioDetalle,
} from "./api";

const detalleBase: EjercicioDetalle = {
  id: "e1",
  anio: 2027,
  moneda_funcional: "VED",
  estado: "APROBADO" as const,
  version: 3,
  congelado: true,
  reconduccion_definitiva: false,
  precompromiso_activo: false,
  precompromiso_desde: null,
  niveles: [
    { orden: 1, nombre: "Programa" },
    { orden: 2, nombre: "Proyecto" },
  ],
  cerrado_en: null,
  motivo_cierre: null,
  clasificador: null,
  categorias: [],
  fundamentos: [],
  faltantes: [],
  historia: [],
  fijado_en: null,
};

const vistaBase: DisponibilidadVista = {
  anio: 2027,
  estado: "APROBADO",
  moneda: "VED",
  certificable: true,
  items: [
    {
      credito_id: "cred1",
      categoria: { id: "cat1", etiqueta: "01.02 · Atención primaria" },
      unidad: { id: "u1", etiqueta: "DESP · Despacho" },
      partida: { id: "p1", etiqueta: "401.01 · Servicios personales" },
      fuente: { id: "f1", etiqueta: "F01 · Tesoro municipal" },
      credito: "1000.00",
      certificado: "300.00",
      disponible: "700.00",
    },
  ],
  totales: {
    credito: "1000.00",
    certificado: "300.00",
    disponible: "700.00",
  },
  filtros: {
    categorias: [{ id: "cat1", etiqueta: "01.02 · Atención primaria" }],
    unidades: [{ id: "u1", etiqueta: "DESP · Despacho" }],
    partidas: [{ id: "p1", etiqueta: "401.01 · Servicios personales" }],
    fuentes: [{ id: "f1", etiqueta: "F01 · Tesoro municipal" }],
  },
  firmantes: [
    {
      cargo_id: "car1",
      etiqueta: "C-01 · Director de Presupuesto",
      unidad: "DESP · Despacho",
    },
  ],
  expedientes: [
    { id: "exp1", etiqueta: "EXP-2026-01 · Compra de insumos" },
  ],
};

const certificacionesBase: CertificacionesVista = {
  items: [
    {
      id: "cert1",
      codigo: "CDP-2026-0001",
      estado: "VIGENTE",
      fecha: "2026-01-15",
      emitida_en: "2026-01-15",
      monto: "300.00",
      saldo_antes: "1000.00",
      saldo_despues: "700.00",
      moneda: "VED",
      concepto: "Insumos",
      expediente_id: null,
      expediente_referencia: "EXP-PRES-001",
      credito_id: "cred1",
      categoria: "01.02 · Atención primaria",
      unidad: "DESP · Despacho",
      partida: "401.01 · Servicios personales",
      fuente: "F01 · Tesoro municipal",
      firmante_cargo: "C-01 · Director de Presupuesto",
      firmante_unidad: "DESP · Despacho",
      firmante_funcionario: "Funcionario Uno",
      emitida_por: "usuario",
      huella: "abc",
      documento_nombre: "certificacion-CDP-2026-0001.pdf",
      documento_sha256: "sha",
      anulada_en: null,
      anulada_por: null,
      motivo_anulacion: null,
    },
  ],
};

function renderizar({
  detalle = detalleBase,
  escribirBloque = vi.fn(),
  vista = vistaBase,
  certificaciones = certificacionesBase,
  puedeCertificar = true,
}: {
  detalle?: EjercicioDetalle;
  escribirBloque?: ReturnType<typeof vi.fn>;
  vista?: DisponibilidadVista;
  certificaciones?: CertificacionesVista;
  puedeCertificar?: boolean;
}) {
  apiFetchMock.mockImplementation((ruta: string) => {
    if (
      ruta ===
        `/gobierno/presupuesto/ejercicios/${detalle.id}/disponibilidad` ||
      ruta.startsWith(
        `/gobierno/presupuesto/ejercicios/${detalle.id}/disponibilidad?`,
      )
    ) {
      return Promise.resolve(vista);
    }
    if (
      ruta === `/gobierno/presupuesto/ejercicios/${detalle.id}/certificaciones`
    ) {
      return Promise.resolve(certificaciones);
    }
    return Promise.reject(new Error(`No mock: ${ruta}`));
  });

  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <Routes>
          <Route
            path="/"
            element={
              <DisponibilidadEjercicio
                detalle={detalle}
                puedeCertificar={puedeCertificar}
                escribirBloque={escribirBloque}
                erroresServidor={{}}
              />
            }
          />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  apiFetchMock.mockReset();
  capacidades = new Set<string>();
  vi.mocked(descargarArchivo).mockReset();
});

describe("DisponibilidadEjercicio", () => {
  it("muestra disponibilidad y certificaciones", async () => {
    renderizar({});

    await waitFor(() => {
      expect(
        screen.getByRole("region", { name: "Tabla de disponibilidad" }),
      ).toBeInTheDocument();
    });

    const tablaDisponibilidad = screen.getByRole("region", {
      name: "Tabla de disponibilidad",
    });
    expect(within(tablaDisponibilidad).getAllByText("700,00 VED").length).toBeGreaterThan(0);

    const tablaCertificaciones = screen.getByRole("region", {
      name: "Tabla de certificaciones",
    });
    expect(
      within(tablaCertificaciones).getByText("CDP-2026-0001"),
    ).toBeInTheDocument();
  });

  it("emite una certificación", async () => {
    const escribirBloque = vi.fn().mockResolvedValue({
      id: "nueva",
      codigo: "CDP-2026-0002",
      estado: "VIGENTE",
      fecha: "2026-01-16",
      emitida_en: "2026-01-16",
      monto: "200.50",
      saldo_antes: "700.00",
      saldo_despues: "499.50",
      moneda: "VED",
      concepto: "Compra de reactivos de laboratorio",
      expediente_id: null,
      expediente_referencia: "EXP-PRES-001",
      credito_id: "cred1",
      categoria: "01.02 · Atención primaria",
      unidad: "DESP · Despacho",
      partida: "401.01 · Servicios personales",
      fuente: "F01 · Tesoro municipal",
      firmante_cargo: "C-01 · Director de Presupuesto",
      firmante_unidad: "DESP · Despacho",
      firmante_funcionario: null,
      emitida_por: "usuario",
      huella: "abc",
      documento_nombre: "doc.pdf",
      documento_sha256: "sha",
      anulada_en: null,
      anulada_por: null,
      motivo_anulacion: null,
    } satisfies Certificacion);

    renderizar({ escribirBloque });

    await waitFor(() => {
      expect(screen.getByRole("button", { name: "Emitir certificación" })).toBeInTheDocument();
    });

    const user = userEvent.setup();

    await user.selectOptions(
      screen.getByRole("combobox", {
        name: "Crédito presupuestario (obligatorio)",
      }),
      "cred1",
    );
    await user.type(
      screen.getByRole("textbox", { name: "Monto (obligatorio)" }),
      "200,50",
    );
    await user.type(
      screen.getByRole("textbox", { name: "Concepto (obligatorio)" }),
      "Compra de reactivos de laboratorio",
    );
    await user.type(
      screen.getByRole("textbox", {
        name: "Referencia del expediente (obligatorio)",
      }),
      "EXP-PRES-001",
    );
    await user.selectOptions(
      screen.getByRole("combobox", {
        name: "Firmante (cargo) (obligatorio)",
      }),
      "car1",
    );
    await user.click(
      screen.getByRole("button", { name: "Emitir certificación" }),
    );

    await waitFor(() => {
      expect(escribirBloque).toHaveBeenCalledWith("/certificaciones", "POST", {
        credito_id: "cred1",
        monto: "200.50",
        concepto: "Compra de reactivos de laboratorio",
        expediente_id: null,
        expediente_referencia: "EXP-PRES-001",
        firmante_cargo_id: "car1",
      });
    });
  });

  it("anula una certificación", async () => {
    const escribirBloque = vi.fn().mockResolvedValue({
      ...certificacionesBase.items[0],
      estado: "ANULADA",
      motivo_anulacion: "Error de imputación",
    } satisfies Certificacion);

    renderizar({ escribirBloque });

    await waitFor(() => {
      expect(
        screen.getByRole("button", { name: "Anular CDP-2026-0001" }),
      ).toBeInTheDocument();
    });

    const user = userEvent.setup();
    await user.type(
      screen.getByRole("textbox", {
        name: "Motivo de anulación de CDP-2026-0001",
      }),
      "Error de imputación",
    );
    await user.click(
      screen.getByRole("button", { name: "Anular CDP-2026-0001" }),
    );

    await waitFor(() => {
      expect(escribirBloque).toHaveBeenCalledWith(
        "/certificaciones/cert1/anular",
        "POST",
        { motivo: "Error de imputación" },
      );
    });
  });

  it("descarga el documento de la certificación", async () => {
    renderizar({});

    await waitFor(() => {
      expect(
        screen.getByRole("button", { name: "Descargar CDP-2026-0001" }),
      ).toBeInTheDocument();
    });

    const user = userEvent.setup();
    await user.click(
      screen.getByRole("button", { name: "Descargar CDP-2026-0001" }),
    );

    await waitFor(() => {
      expect(descargarArchivo).toHaveBeenCalledWith(
        "/gobierno/presupuesto/ejercicios/e1/certificaciones/cert1/documento",
        "certificacion-CDP-2026-0001.pdf",
      );
    });
  });

  it("muestra aviso y oculta emisión cuando no es certificable", async () => {
    renderizar({
      vista: { ...vistaBase, certificable: false },
    });

    await waitFor(() => {
      expect(
        screen.getByText(
          "El ejercicio no admite certificaciones: debe estar aprobado o reconducido y dentro de su año.",
        ),
      ).toBeInTheDocument();
    });

    expect(
      screen.queryByRole("button", { name: "Emitir certificación" }),
    ).not.toBeInTheDocument();
  });

  it("oculta emisión y anulación sin capacidad", async () => {
    renderizar({ puedeCertificar: false });

    await waitFor(() => {
      expect(
        screen.getByRole("region", { name: "Tabla de certificaciones" }),
      ).toBeInTheDocument();
    });

    expect(
      screen.queryByRole("button", { name: "Emitir certificación" }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Anular CDP-2026-0001" }),
    ).not.toBeInTheDocument();
  });
});
