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

const { CompromisosEjercicio } = await import("./CompromisosEjercicio");
const { descargarArchivo } = await import("@/api/descargas");

import type {
  CompromisosVista,
  EjercicioDetalle,
  OpcionesCompromisoVista,
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

const opcionesBase: OpcionesCompromisoVista = {
  anio: 2027,
  estado: "APROBADO",
  moneda: "VED",
  comprometible: true,
  certificados: [
    {
      certificado_id: "cert1",
      codigo: "CDP-2027-0001",
      credito_id: "cred1",
      categoria: "01.02 · Atención primaria",
      unidad: "DESP · Despacho",
      partida: "401.01 · Servicios personales",
      fuente: "F01 · Tesoro municipal",
      expediente_id: "exp1",
      expediente_referencia: "EXP-PRES-001",
      monto: "300.00",
      consumido: "100.00",
      remanente: "200.00",
      situacion: "PARCIALMENTE_CONSUMIDA",
      etiqueta: "CDP-2027-0001 · saldo certificado disponible 200,00 VED",
    },
    {
      certificado_id: "cert2",
      codigo: "CDP-2027-0002",
      credito_id: "cred2",
      categoria: "02.01 · Educación",
      unidad: "DESP · Despacho",
      partida: "402.01 · Servicios no personales",
      fuente: "F01 · Tesoro municipal",
      expediente_id: "exp1",
      expediente_referencia: "EXP-PRES-001",
      monto: "500.00",
      consumido: "0.00",
      remanente: "500.00",
      situacion: "DISPONIBLE",
      etiqueta: "CDP-2027-0002 · saldo certificado disponible 500,00 VED",
    },
  ],
  autoridades: [
    {
      cargo_id: "car9",
      etiqueta: "C-09 · Director de Administración",
      unidad: "DESP · Despacho",
      limite_tipo: "SIN_LIMITE",
      limite_monto: null,
      limite_moneda: null,
      limite: "Sin límite",
    },
  ],
  soportes: [{ id: "doc1", etiqueta: "OC-2027-01 · Orden de compra" }],
};

const compromisosBase: CompromisosVista = {
  items: [
    {
      id: "k1",
      codigo: "CP-2027-0001",
      estado: "VIGENTE",
      fecha: "2027-01-15",
      emitido_en: "2027-01-15T10:00:00Z",
      total: "100.00",
      moneda: "VED",
      concepto: "Compra de reactivos",
      expediente_id: "exp1",
      expediente_referencia: "EXP-PRES-001",
      autoridad_cargo: "C-09 · Director de Administración",
      autoridad_unidad: "DESP · Despacho",
      autoridad_funcionario: "Funcionario Nueve",
      limite: "Sin límite",
      soporte_documento_id: "doc1",
      soporte: "OC-2027-01 · Orden de compra",
      soporte_sha256: "sha1",
      emitido_por: "usuario",
      huella: "abc",
      documento_nombre: "compromiso-CP-2027-0001.pdf",
      documento_sha256: "sha2",
      anulado_en: null,
      anulado_por: null,
      motivo_anulacion: null,
      lineas: [
        {
          linea: 1,
          certificado_id: "cert1",
          certificado_codigo: "CDP-2027-0001",
          credito_id: "cred1",
          categoria: "01.02 · Atención primaria",
          unidad: "DESP · Despacho",
          partida: "401.01 · Servicios personales",
          fuente: "F01 · Tesoro municipal",
          monto: "100.00",
        },
      ],
    },
  ],
};

function renderizar({
  detalle = detalleBase,
  escribirBloque = vi.fn(),
  opciones = opcionesBase,
  compromisos = compromisosBase,
  puedeComprometer = true,
}: {
  detalle?: EjercicioDetalle;
  escribirBloque?: ReturnType<typeof vi.fn>;
  opciones?: OpcionesCompromisoVista;
  compromisos?: CompromisosVista;
  puedeComprometer?: boolean;
}) {
  apiFetchMock.mockImplementation((ruta: string) => {
    if (
      ruta === `/gobierno/presupuesto/ejercicios/${detalle.id}/compromisos/opciones`
    ) {
      return Promise.resolve(opciones);
    }
    if (ruta === `/gobierno/presupuesto/ejercicios/${detalle.id}/compromisos`) {
      return Promise.resolve(compromisos);
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
              <CompromisosEjercicio
                detalle={detalle}
                puedeComprometer={puedeComprometer}
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

describe("CompromisosEjercicio", () => {
  it("muestra compromisos y opciones", async () => {
    renderizar({});

    await waitFor(() => {
      expect(
        screen.getByRole("region", { name: "Tabla de compromisos" }),
      ).toBeInTheDocument();
    });

    const tablaCompromisos = screen.getByRole("region", {
      name: "Tabla de compromisos",
    });
    expect(
      within(tablaCompromisos).getByText("CP-2027-0001"),
    ).toBeInTheDocument();

    expect(
      screen.getByText("CDP-2027-0001 · saldo certificado disponible 200,00 VED"),
    ).toBeInTheDocument();
  });

  it("registra compromiso multilínea", async () => {
    const user = userEvent.setup();
    const escribirBloque = vi.fn().mockResolvedValue({
      id: "nuevo",
      codigo: "CP-2027-0002",
      total: "250.50",
      moneda: "VED",
    });

    renderizar({ escribirBloque });

    await waitFor(() => {
      expect(
        screen.getByRole("region", { name: "Tabla de compromisos" }),
      ).toBeInTheDocument();
    });

    await user.selectOptions(
      screen.getByRole("combobox", {
        name: "Certificación de la imputación 1 (obligatorio)",
      }),
      "cert1",
    );
    await user.type(
      screen.getByRole("textbox", {
        name: "Monto de la imputación 1 (obligatorio)",
      }),
      "150,50",
    );

    await user.click(screen.getByText("Añadir imputación"));

    await user.selectOptions(
      screen.getByRole("combobox", {
        name: "Certificación de la imputación 2 (obligatorio)",
      }),
      "cert2",
    );
    await user.type(
      screen.getByRole("textbox", {
        name: "Monto de la imputación 2 (obligatorio)",
      }),
      "100",
    );

    await user.type(
      screen.getByRole("textbox", {
        name: "Concepto (obligatorio)",
      }),
      "Orden de compra de reactivos",
    );

    await user.selectOptions(
      screen.getByRole("combobox", {
        name: "Autoridad que compromete (cargo) (obligatorio)",
      }),
      "car9",
    );

    await user.selectOptions(
      screen.getByRole("combobox", {
        name: "Soporte documental (obligatorio)",
      }),
      "doc1",
    );

    expect(screen.getByText("Total del compromiso: 250,50 VED")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Registrar compromiso" }));

    await waitFor(() => {
      expect(escribirBloque).toHaveBeenCalledWith("/compromisos", "POST", {
        concepto: "Orden de compra de reactivos",
        autoridad_cargo_id: "car9",
        soporte_documento_id: "doc1",
        lineas: [
          { certificado_id: "cert1", monto: "150.50" },
          { certificado_id: "cert2", monto: "100" },
        ],
      });
    });
  });

  it("anula un compromiso", async () => {
    const user = userEvent.setup();
    const escribirBloque = vi.fn().mockResolvedValue({
      id: "k1",
      codigo: "CP-2027-0001",
      estado: "ANULADO",
    });

    renderizar({ escribirBloque });

    await waitFor(() => {
      expect(
        screen.getByRole("region", { name: "Tabla de compromisos" }),
      ).toBeInTheDocument();
    });

    const motivoInput = screen.getByRole("textbox", {
      name: "Motivo de anulación de CP-2027-0001",
    });
    await user.type(motivoInput, "Error en la orden de compra");
    await user.click(screen.getByText("Anular CP-2027-0001"));

    await waitFor(() => {
      expect(escribirBloque).toHaveBeenCalledWith(
        "/compromisos/k1/anular",
        "POST",
        { motivo: "Error en la orden de compra" },
      );
    });
  });

  it("descarga documento del compromiso", async () => {
    const user = userEvent.setup();

    renderizar({});

    await waitFor(() => {
      expect(
        screen.getByRole("region", { name: "Tabla de compromisos" }),
      ).toBeInTheDocument();
    });

    await user.click(screen.getByText("Descargar CP-2027-0001"));

    await waitFor(() => {
      expect(descargarArchivo).toHaveBeenCalledWith(
        "/gobierno/presupuesto/ejercicios/e1/compromisos/k1/documento",
        "compromiso-CP-2027-0001.pdf",
      );
    });
  });

  it("muestra aviso si no es comprometible", async () => {
    renderizar({
      opciones: { ...opcionesBase, comprometible: false },
    });

    await waitFor(() => {
      expect(
        screen.getByText(
          "El ejercicio no admite compromisos: debe estar aprobado o reconducido y dentro de su año.",
        ),
      ).toBeInTheDocument();
    });

    expect(screen.queryByRole("button", { name: "Registrar compromiso" })).not.toBeInTheDocument();
  });

  it("no muestra registrar ni anular si no puedeComprometer", async () => {
    renderizar({ puedeComprometer: false });

    await waitFor(() => {
      expect(
        screen.getByRole("region", { name: "Tabla de compromisos" }),
      ).toBeInTheDocument();
    });

    expect(screen.queryByRole("button", { name: "Registrar compromiso" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Anular CP-2027-0001" })).not.toBeInTheDocument();
  });
});
