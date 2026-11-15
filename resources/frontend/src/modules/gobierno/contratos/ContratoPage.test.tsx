import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError } from "@/api/client";
import { ContratoPage } from "./ContratoPage";
import type { Contrato } from "./api";

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

function borrador(over?: Partial<Contrato>): Contrato {
  return {
    id: "k1",
    version: 1,
    estado: "BORRADOR",
    estado_etiqueta: "Borrador",
    tipo: null,
    tipo_etiqueta: null,
    codigo: null,
    identificacion: "Borrador · EXP-1 · DEC-01",
    expediente: { id: "e1", numero: "EXP-1" },
    decision: { id: "d1", referencia: "DEC-01", fecha: "2026-01-15", acto: "Adjudicación", vigente: true },
    oferta: { id: "o1", referencia: "OF-01" },
    contratista: { nombre: "Constructora Andina", documento: "RUC-123", representante: "Juan Pérez" },
    objeto: "Construcción de puente",
    descripcion_complementaria: null,
    monto: "50000.00",
    moneda: "USD",
    fecha_inicio: null,
    fecha_fin: null,
    referencia_instrumento: null,
    documento: null,
    cobertura: {
      asignaciones: [],
      total_asignado: "0.00",
      faltante: "50000.00",
      completa: false,
    },
    garantias: [],
    firmante: null,
    fecha_formalizacion: null,
    formalizado_en: null,
    huella: null,
    opciones: {
      certificados_elegibles: [
        {
          id: "cert-1",
          codigo: "CDP-2026-0001",
          monto: "50000.00",
          saldo_libre: "50000.00",
          moneda: "USD",
          anio: 2026,
          partida: "5.1.1",
          fuente: "F01",
          concepto: "Disponibilidad",
        },
      ],
      garantias_elegibles: [
        {
          instrumento_id: "gar-1",
          referencia: "GAR-01",
          tipo_etiqueta: "Fiel cumplimiento",
          emisor: "Seguros Uno",
          monto: "5000.00",
          moneda: "USD",
          vigente_hasta: "2026-12-31",
          estado: "VIGENTE",
        },
      ],
      documentos_elegibles: [{ id: "doc-1", titulo: "Contrato firmado", version: 1 }],
      firmantes: [
        {
          cargo_id: "cargo-1",
          cargo: "Director General",
          limite: { cargo: null, tipo_limite: "SIN_LIMITE", monto: null, moneda: null, etiqueta: "Sin límite" },
          control: { estado: "OK", estado_etiqueta: "Permitido", permite: true, mensaje: "Dentro del límite." },
        },
        {
          cargo_id: "cargo-2",
          cargo: "Gerente Administrativo",
          limite: { cargo: null, tipo_limite: "MONTO", monto: "40000.00", moneda: "USD", etiqueta: "Hasta 40000.00 USD" },
          control: {
            estado: "EXCEDE_LIMITE",
            estado_etiqueta: "Excede el límite",
            permite: false,
            mensaje: "El monto supera el límite del firmante.",
          },
        },
      ],
    },
    pendientes: ["Falta cubrir 50000.00 USD con certificaciones de disponibilidad"],
    puede_formalizar: false,
    ...over,
  };
}

function formalizado(over?: Partial<Contrato>): Contrato {
  const base = borrador({
    estado: "FORMALIZADO",
    estado_etiqueta: "Formalizado",
    codigo: "CT-2026-0001",
    tipo: "CONTRATO",
    tipo_etiqueta: "Contrato",
    documento: { id: "doc-1", titulo: "Contrato firmado", version: 1, sha256: "abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890" },
    firmante: { cargo: "Director General", funcionario: "María López" },
    fecha_formalizacion: "2026-02-01",
    formalizado_en: "2026-02-01T10:00:00Z",
    huella: "1234567890abcdef1234567890abcdef",
    cobertura: {
      asignaciones: [
        {
          certificado_id: "cert-1",
          codigo: "CDP-2026-0001",
          monto: "50000.00",
          moneda: "USD",
          anio: 2026,
          partida: "5.1.1",
          fuente: "F01",
          estado: "VIGENTE",
        },
      ],
      total_asignado: "50000.00",
      faltante: "0.00",
      completa: true,
    },
    garantias: [
      {
        instrumento_id: "gar-1",
        referencia: "GAR-01",
        tipo_etiqueta: "Fiel cumplimiento",
        emisor: "Seguros Uno",
        monto: "5000.00",
        moneda: "USD",
        vigente_hasta: "2026-12-31",
        estado: "VIGENTE",
      },
    ],
    pendientes: [],
    puede_formalizar: true,
  });
  return { ...base, ...over };
}

function renderizar() {
  const cliente = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={cliente}>
      <MemoryRouter initialEntries={["/gobierno/contratos/k1"]}>
        <Routes>
          <Route path="/gobierno/contratos/:contratoId" element={<ContratoPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("ContratoPage", () => {
  beforeEach(() => {
    apiFetchMock.mockReset();
    capacidades = new Set([
      "gobierno_contratos:view",
      "gobierno_contratos:manage",
      "gobierno_contratos:formalize",
    ]);
  });

  it("el borrador muestra el origen en solo lectura y los pendientes", async () => {
    apiFetchMock.mockResolvedValue(borrador());
    renderizar();

    expect(await screen.findByText("Constructora Andina")).toBeInTheDocument();
    expect(screen.getAllByText("50000.00 USD").length).toBeGreaterThan(0);
    expect(screen.getByText("Falta cubrir 50000.00 USD con certificaciones de disponibilidad")).toBeInTheDocument();
  });

  it("«Guardar cobertura» llama a PUT .../cobertura con ifMatch 1 y las asignaciones", async () => {
    apiFetchMock.mockResolvedValue(borrador());
    const usuario = userEvent.setup();
    renderizar();

    await screen.findByLabelText("Monto asignado a CDP-2026-0001");
    const entrada = screen.getByLabelText("Monto asignado a CDP-2026-0001");
    await usuario.clear(entrada);
    await usuario.type(entrada, "50000.00");
    await usuario.click(screen.getByRole("button", { name: "Guardar cobertura" }));

    await waitFor(() => {
      expect(apiFetchMock).toHaveBeenCalledWith(
        "/gobierno/contratos/k1/cobertura",
        expect.objectContaining({
          method: "PUT",
          ifMatch: "1",
          body: { asignaciones: [{ certificado_id: "cert-1", monto: "50000.00" }] },
        }),
      );
    });
  });

  it("elegir el firmante de 40000.00 muestra «Excede el límite» y el botón Formalizar sigue habilitado", async () => {
    apiFetchMock.mockResolvedValue(borrador());
    const usuario = userEvent.setup();
    renderizar();

    await screen.findByLabelText("Cargo firmante");
    await usuario.selectOptions(screen.getByLabelText("Cargo firmante"), "cargo-2");

    expect(screen.getByText("Excede el límite")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Formalizar" })).toBeEnabled();
  });

  it("formalizar con ApiError 409 muestra su message en un alert", async () => {
    apiFetchMock.mockImplementation((_ruta: string, opciones?: { method?: string }) => {
      if (opciones?.method === "POST") {
        return Promise.reject(new ApiError(409, { code: "GOV_CONTRACT_SIGNER_AMOUNT_EXCEEDED", message: "El monto supera el límite del firmante." }));
      }
      return Promise.resolve(borrador());
    });
    const usuario = userEvent.setup();
    renderizar();

    await screen.findByLabelText("Cargo firmante");
    await usuario.selectOptions(screen.getByLabelText("Cargo firmante"), "cargo-1");
    await usuario.click(screen.getByRole("button", { name: "Formalizar" }));
    const dialogo = await screen.findByRole("dialog");
    await usuario.click(within(dialogo).getByRole("button", { name: "Formalizar" }));

    expect(await screen.findByText("El monto supera el límite del firmante.")).toBeInTheDocument();
  });

  it("una ficha FORMALIZADA muestra el código CT-2026-0001 y no muestra el botón Formalizar", async () => {
    apiFetchMock.mockResolvedValue(formalizado());
    renderizar();

    expect(await screen.findByText("CT-2026-0001")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Formalizar" })).not.toBeInTheDocument();
  });
});
