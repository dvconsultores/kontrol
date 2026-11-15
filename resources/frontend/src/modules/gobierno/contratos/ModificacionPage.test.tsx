import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError } from "@/api/client";
import { ModificacionPage } from "./ModificacionPage";
import type { FichaModificacion, FirmanteOpcion, TasaConversion } from "./api";

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

function tasa(over: Partial<TasaConversion> = {}): TasaConversion {
  return {
    tasa_id: "t1",
    moneda: "USD",
    valor: "40",
    fecha_efectiva: "2026-11-14",
    version: 1,
    fuente: "BCV",
    fuente_referencia: "Referencia",
    ...over,
  };
}

function firmante(over: Partial<FirmanteOpcion> = {}): FirmanteOpcion {
  return {
    cargo_id: "cargo-1",
    cargo: "Director General",
    limite: {
      cargo: "Director General",
      tipo_limite: null,
      monto: null,
      moneda: null,
      etiqueta: "Sin límite",
    },
    control: {
      estado: "SIN_LIMITE",
      estado_etiqueta: "Sin límite",
      permite: true,
      mensaje: "Director General firma contrataciones sin límite de monto.",
    },
    ...over,
  };
}

function ficha(over: Partial<FichaModificacion> = {}): FichaModificacion {
  return {
    id: "m1",
    version: 1,
    estado: "BORRADOR",
    estado_etiqueta: "Borrador",
    tipo: "ADENDA",
    tipo_etiqueta: "Adenda",
    codigo: null,
    identificacion: "m1",
    contrato: { id: "k1", codigo: "CT-2026-0001" },
    moneda: "USD",
    fecha_instrumento: null,
    vigente_desde: null,
    motivo: null,
    nueva_fecha_fin: null,
    delta_monto: null,
    condiciones: null,
    referencia_instrumento: null,
    documento: null,
    base: { monto: "50000.00", fecha_fin: "2027-05-14", numero: 0 },
    propuesta: { monto_nuevo: null, fecha_fin_nueva: null },
    cobertura: {
      existente_valida: "0.00",
      requerida_adicional: "10000.00",
      asignaciones: [],
      total_asignado: "0.00",
      completa: false,
    },
    compromisos: { total: null, moneda: null, permite: true, aplica: false },
    firmante: null,
    formalizado_en: null,
    huella: null,
    opciones: {
      certificados_elegibles: [],
      documentos_elegibles: [],
      firmantes: [],
    },
    pendientes: [],
    puede_formalizar: false,
    ...over,
  };
}

function renderizar() {
  const cliente = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={cliente}>
      <MemoryRouter initialEntries={["/gobierno/contratos/k1/modificaciones/m1"]}>
        <Routes>
          <Route
            path="/gobierno/contratos/:contratoId/modificaciones/:modificacionId"
            element={<ModificacionPage />}
          />
          <Route
            path="/gobierno/contratos/:contratoId/modificaciones"
            element={<p>Lista de modificaciones</p>}
          />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("ModificacionPage", () => {
  beforeEach(() => {
    apiFetchMock.mockReset();
    capacidades = new Set([
      "gobierno_contratos:view",
      "gobierno_contratos:manage",
      "gobierno_contratos:formalize",
    ]);
  });

  it("guarda los datos de una modificación borrador", async () => {
    apiFetchMock.mockImplementation((ruta: string, opciones?: { method?: string }) => {
      if (ruta === "/gobierno/contratos/k1/modificaciones/m1" && opciones?.method === "PATCH") {
        return Promise.resolve(ficha({ delta_monto: "10000.00" }));
      }
      return Promise.resolve(ficha());
    });
    renderizar();

    await screen.findByText("Datos de la modificación");
    await userEvent.type(screen.getByLabelText("Cambio de monto"), "10000.00");
    await userEvent.click(screen.getByRole("button", { name: "Guardar datos" }));

    await waitFor(() => {
      expect(apiFetchMock).toHaveBeenCalledWith("/gobierno/contratos/k1/modificaciones/m1", {
        method: "PATCH",
        ifMatch: "1",
        body: { delta_monto: "10000.00" },
      });
    });
  });

  it("guarda la cobertura adicional", async () => {
    apiFetchMock.mockImplementation((ruta: string, opciones?: { method?: string }) => {
      if (ruta === "/gobierno/contratos/k1/modificaciones/m1/cobertura" && opciones?.method === "PUT") {
        return Promise.resolve(ficha());
      }
      return Promise.resolve(
        ficha({
          opciones: {
            certificados_elegibles: [
              {
                id: "cert-3",
                codigo: "CDP-2026-0003",
                monto: "15000.00",
                saldo_libre: "15000.00",
                moneda: "USD",
                anio: 2026,
                partida: "4.02.00.00.00",
                fuente: "Fuente",
                concepto: "Concepto",
              },
            ],
            documentos_elegibles: [],
            firmantes: [],
          },
        }),
      );
    });
    renderizar();

    await screen.findByText("Cobertura adicional");
    await userEvent.type(screen.getByLabelText("Monto asignado a CDP-2026-0003"), "10000.00");
    await userEvent.click(screen.getByRole("button", { name: "Guardar cobertura" }));

    await waitFor(() => {
      expect(apiFetchMock).toHaveBeenCalledWith("/gobierno/contratos/k1/modificaciones/m1/cobertura", {
        method: "PUT",
        ifMatch: "1",
        body: { asignaciones: [{ certificado_id: "cert-3", monto: "10000.00" }] },
      });
    });
  });

  it("formaliza la modificación con el firmante elegido", async () => {
    const respuestaFormalizada = ficha({
      estado: "FORMALIZADA",
      estado_etiqueta: "Formalizada",
      codigo: "CT-2026-0001/AD-001",
    });

    apiFetchMock.mockImplementation((ruta: string, opciones?: { method?: string }) => {
      if (ruta === "/gobierno/contratos/k1/modificaciones/m1/formalizar" && opciones?.method === "POST") {
        return Promise.resolve(respuestaFormalizada);
      }
      return Promise.resolve(
        ficha({
          opciones: {
            certificados_elegibles: [],
            documentos_elegibles: [],
            firmantes: [firmante()],
          },
        }),
      );
    });
    renderizar();

    await screen.findByText("Formalización");
    await userEvent.selectOptions(screen.getByLabelText("Cargo firmante"), "cargo-1");
    expect(
      await screen.findByText("Director General firma contrataciones sin límite de monto."),
    ).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Formalizar" }));

    const dialogo = await screen.findByRole("dialog");
    await userEvent.click(within(dialogo).getByRole("button", { name: "Formalizar" }));

    await waitFor(() => {
      expect(apiFetchMock).toHaveBeenCalledWith("/gobierno/contratos/k1/modificaciones/m1/formalizar", {
        method: "POST",
        ifMatch: "1",
        body: { firmante_cargo_id: "cargo-1" },
      });
    });
    expect(await screen.findByText("Formalizada: CT-2026-0001/AD-001")).toBeInTheDocument();
  });

  it("muestra el error de formalización cuando excede el límite", async () => {
    apiFetchMock.mockImplementation((ruta: string, opciones?: { method?: string }) => {
      if (ruta === "/gobierno/contratos/k1/modificaciones/m1/formalizar" && opciones?.method === "POST") {
        return Promise.reject(
          new ApiError(409, {
            code: "GOV_CONTRACT_SIGNER_AMOUNT_EXCEEDED",
            message: "El monto efectivo nuevo del contrato excede el límite de firma",
          }),
        );
      }
      return Promise.resolve(
        ficha({
          opciones: {
            certificados_elegibles: [],
            documentos_elegibles: [],
            firmantes: [
              firmante({
                control: {
                  estado: "MONTO_EXCEDIDO",
                  estado_etiqueta: "Monto excedido",
                  permite: false,
                  mensaje: "El monto efectivo nuevo del contrato excede el límite de firma",
                },
              }),
            ],
          },
        }),
      );
    });
    renderizar();

    await screen.findByText("Formalización");
    await userEvent.selectOptions(screen.getByLabelText("Cargo firmante"), "cargo-1");
    await userEvent.click(screen.getByRole("button", { name: "Formalizar" }));

    const dialogo = await screen.findByRole("dialog");
    await userEvent.click(within(dialogo).getByRole("button", { name: "Formalizar" }));

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent(
        "El monto efectivo nuevo del contrato excede el límite de firma",
      );
    });
  });

  it("muestra el instrumento formalizado con conversión y sin edición", async () => {
    const conversion = {
      moneda_operacion: "USD",
      moneda_limite: "VES",
      fecha: "2026-11-14",
      tasas: [tasa()],
      total_ves: "2000000",
      limite_ves: "4400000",
      resultado: "OK",
    };

    apiFetchMock.mockResolvedValue(
      ficha({
        estado: "FORMALIZADA",
        estado_etiqueta: "Formalizada",
        codigo: "CT-2026-0001/AD-001",
        version: 2,
        firmante: {
          cargo: "Director General",
          funcionario: null,
          limite: "Sin límite",
          conversion,
        },
        documento: {
          id: "doc-1",
          titulo: "Documento firmado",
          version: 1,
          sha256: "abc123",
        },
      }),
    );
    renderizar();

    expect(await screen.findByText("Instrumento formalizado")).toBeInTheDocument();
    expect(screen.getByText(/Comparado en VES con tasa oficial BCV/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Ver documento" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Guardar datos" })).toBeNull();
  });

  it("descarta el borrador y navega a la lista", async () => {
    apiFetchMock.mockImplementation((ruta: string, opciones?: { method?: string }) => {
      if (ruta === "/gobierno/contratos/k1/modificaciones/m1" && opciones?.method === "DELETE") {
        return Promise.resolve(undefined);
      }
      return Promise.resolve(ficha());
    });
    renderizar();

    await screen.findByRole("button", { name: "Descartar borrador" });
    await userEvent.click(screen.getByRole("button", { name: "Descartar borrador" }));

    const dialogo = await screen.findByRole("dialog");
    await userEvent.click(within(dialogo).getByRole("button", { name: "Descartar" }));

    await waitFor(() => {
      expect(apiFetchMock).toHaveBeenCalledWith("/gobierno/contratos/k1/modificaciones/m1", {
        method: "DELETE",
        ifMatch: "1",
      });
    });
    expect(await screen.findByText("Lista de modificaciones")).toBeInTheDocument();
  });
});
