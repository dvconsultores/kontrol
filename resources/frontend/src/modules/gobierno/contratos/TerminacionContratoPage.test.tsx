import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { TerminacionContratoPage } from "./TerminacionContratoPage";
import type { VistaTerminacion } from "./api";
import { formatearInstante } from "@/lib/fecha-de-negocio";

const apiFetchMock = vi.fn();
const descargarArchivoMock = vi.fn();

vi.mock("@/api/client", async (original) => ({
  ...(await original<typeof import("@/api/client")>()),
  apiFetch: (...args: unknown[]) => apiFetchMock(...args),
  ApiError: (await original<typeof import("@/api/client")>()).ApiError,
}));

vi.mock("@/api/descargas", () => ({
  descargarArchivo: (...args: unknown[]) => descargarArchivoMock(...args),
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

function vista(sobrescribir: Partial<VistaTerminacion> = {}): VistaTerminacion {
  return {
    contrato: {
      id: "k1",
      codigo: "K-001",
      contratista: { nombre: "Constructora Sur", documento: "99999999" },
      objeto: "Obra vial",
      tipo_contratacion: "OBRAS",
      fecha_formalizacion: "2025-01-15",
      enlace: "/gobierno/contratos/k1",
    },
    situacion: {
      estado: "VIGENTE",
      estado_etiqueta: "Vigente",
      figura: null,
      figura_etiqueta: null,
      fecha_eficacia: null,
      fecha_limite_ejecucion: "2026-03-31",
      cumplimiento_cnt03: false,
      alerta_acto_base: null,
    },
    catalogo: {
      figuras: [
        {
          codigo: "RESCISION_NO_IMPUTABLE",
          etiqueta: "Rescisión no imputable",
          fuente: "LCP art. 149.1",
          causales: [{ codigo: "FUERZA_MAYOR", etiqueta: "Fuerza mayor", fuente: "LCP art. 99" }],
        },
        {
          codigo: "RESOLUCION_MUTUO_ACUERDO",
          etiqueta: "Resolución por mutuo acuerdo",
          fuente: "LCP art. 151",
          causales: [{ codigo: "MUTUO_ACUERDO", etiqueta: "Mutuo acuerdo", fuente: "LCP art. 151" }],
        },
        {
          codigo: "RESCISION_IMPUTABLE",
          etiqueta: "Rescisión imputable",
          fuente: "LCP art. 148",
          causales: [
            { codigo: "INCUMPLIMIENTO", etiqueta: "Incumplimiento", fuente: "LCP art. 148.1" },
            { codigo: "CLAUSULA_CONTRATO", etiqueta: "Cláusula del contrato", fuente: "Cláusula 15" },
          ],
        },
      ],
    },
    borrador: null,
    formalizada: null,
    requisitos: [],
    opciones: {
      actos: [
        {
          id: "acto-1",
          etiqueta: "Resolución 1/26",
          estado: "EMITIDO",
          fecha: "2026-02-10",
          fecha_eficacia: "2026-02-20",
          emisor_cargo: "Ministra",
        },
      ],
      documentos: [{ id: "doc-1", titulo: "Acuerdo firmado", version: 2 }],
    },
    notificaciones: [],
    consecuencias: {
      fecha_corte: "2026-01-31",
      moneda: "PYG",
      monto_vigente: "500000000",
      valuado_conformado: "300000000",
      valuado_presentado: "320000000",
      saldo_no_ejecutado: "200000000",
      saldo_por_valuar_cnt03: "50000000",
      facturado_conforme: "280000000",
      recepciones: { total: 3, definitiva: false },
      estado_ejecucion: "EN_EJECUCION",
      estado_ejecucion_etiqueta: "En ejecución",
      hitos: { total: 10, cumplidos: 6 },
      compromisos: [{ codigo: "BUD-08-1", estado: "Vigente", total: "500000000", moneda: "PYG", enlace: "/bud/1" }],
      indemnizacion: { regla: "Regla 1", estado: "Cumplida", mensaje: "Sin indemnización" },
      efectos: "Se liberan las garantías al cierre.",
    },
    garantias: [],
    obligaciones: [],
    permisos: { terminar: true },
    ...sobrescribir,
  };
}

function renderPagina(data: VistaTerminacion) {
  apiFetchMock.mockResolvedValue(data);
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={["/gobierno/contratos/k1/terminacion"]}>
        <Routes>
          <Route path="/gobierno/contratos/:contratoId/terminacion" element={<TerminacionContratoPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
  return queryClient;
}

beforeEach(() => {
  apiFetchMock.mockReset();
  descargarArchivoMock.mockReset();
  capacidades = new Set(["gobierno_contratos:view", "gobierno_contratos:terminate"]);
});

describe("TerminacionContratoPage", () => {
  it("sin borrador permite preparar con la figura elegida", async () => {
    const usuario = userEvent.setup();
    apiFetchMock.mockResolvedValue(vista());
    renderPagina(vista());

    await waitFor(() => expect(screen.getByText("Preparar la actuación")).toBeTruthy());

    await usuario.selectOptions(screen.getByLabelText("Figura jurídica"), "RESCISION_IMPUTABLE");
    await usuario.click(screen.getByRole("button", { name: "Preparar" }));

    await waitFor(() => {
      expect(apiFetchMock).toHaveBeenCalledWith("/gobierno/contratos/k1/terminacion", {
        method: "POST",
        body: { figura: "RESCISION_IMPUTABLE" },
      });
    });
  });

  it("el borrador muestra requisitos pendientes y deshabilita Formalizar", async () => {
    apiFetchMock.mockResolvedValue(
      vista({
        borrador: {
          id: "b1",
          codigo: null,
          estado: "BORRADOR",
          version: 3,
          figura: "RESCISION_IMPUTABLE",
          figura_etiqueta: "Rescisión imputable",
          causal: "INCUMPLIMIENTO",
          causal_etiqueta: "Incumplimiento",
          causal_referencia: null,
          hechos: "Hechos",
          fundamento: "Fundamento",
          acto: null,
          apertura: null,
          documento: null,
          conclusion: null,
          fecha_acto: null,
          fecha_eficacia: null,
          formalizado_en: null,
          formalizado_por: null,
          huella: null,
        },
        requisitos: [
          { codigo: "ACTO", cumplido: false, mensaje: "Se requiere acto decisorio eficaz" },
        ],
      }),
    );
    renderPagina(
      vista({
        borrador: {
          id: "b1",
          codigo: null,
          estado: "BORRADOR",
          version: 3,
          figura: "RESCISION_IMPUTABLE",
          figura_etiqueta: "Rescisión imputable",
          causal: "INCUMPLIMIENTO",
          causal_etiqueta: "Incumplimiento",
          causal_referencia: null,
          hechos: "Hechos",
          fundamento: "Fundamento",
          acto: null,
          apertura: null,
          documento: null,
          conclusion: null,
          fecha_acto: null,
          fecha_eficacia: null,
          formalizado_en: null,
          formalizado_por: null,
          huella: null,
        },
        requisitos: [
          { codigo: "ACTO", cumplido: false, mensaje: "Se requiere acto decisorio eficaz" },
        ],
      }),
    );

    await waitFor(() => expect(screen.getByText("Pendiente · Se requiere acto decisorio eficaz")).toBeTruthy());
    expect((screen.getByRole("button", { name: "Formalizar" }) as HTMLButtonElement).disabled).toBe(true);
  });

  it("con todos los requisitos, Formalizar abre la confirmación con la advertencia y envía ifMatch", async () => {
    const usuario = userEvent.setup();
    const data = vista({
      borrador: {
        id: "b1",
        codigo: null,
        estado: "BORRADOR",
        version: 3,
        figura: "RESCISION_IMPUTABLE",
        figura_etiqueta: "Rescisión imputable",
        causal: "INCUMPLIMIENTO",
        causal_etiqueta: "Incumplimiento",
        causal_referencia: null,
        hechos: "Hechos",
        fundamento: "Fundamento",
        acto: {
          id: "acto-1",
          etiqueta: "Resolución 1/26",
          tipo: "RESOLUCION",
          numero: "1/26",
          fecha: "2026-02-10",
          estado: "EFICAZ",
          fecha_eficacia: "2026-02-20",
          emisor_cargo: "Ministra",
          funcionario: "Fulana",
          enlace: "/actos/1",
        },
        apertura: null,
        documento: null,
        conclusion: null,
        fecha_acto: "2026-02-10",
        fecha_eficacia: "2026-02-20",
        formalizado_en: null,
        formalizado_por: null,
        huella: null,
      },
      requisitos: [{ codigo: "ACTO", cumplido: true, mensaje: "Acto decisorio eficaz" }],
    });
    apiFetchMock.mockResolvedValue(data);
    renderPagina(data);

    await waitFor(() => expect(screen.getByRole("button", { name: "Formalizar" })).toBeTruthy());
    await usuario.click(screen.getByRole("button", { name: "Formalizar" }));

    expect(
      screen.getByText(
        "Esta actuación modifica la situación jurídica del contrato y no se puede editar después de formalizarse.",
      ),
    ).toBeTruthy();

    apiFetchMock.mockResolvedValue({
      ...data,
      formalizada: { ...data.borrador, estado: "FORMALIZADA", codigo: "T-001" },
      borrador: null,
    });

    await usuario.click(within(screen.getByRole("dialog")).getByRole("button", { name: "Formalizar" }));

    await waitFor(() => {
      expect(apiFetchMock).toHaveBeenCalledWith("/gobierno/contratos/k1/terminacion/formalizar", {
        method: "POST",
        ifMatch: "3",
      });
    });
  });

  it("la formalizada muestra la actuación, la fecha de registro con hora y la alerta de acto revocado", async () => {
    const data = vista({
      situacion: {
        estado: "VIGENTE",
        estado_etiqueta: "Vigente",
        figura: "RESCISION_IMPUTABLE",
        figura_etiqueta: "Rescisión imputable",
        fecha_eficacia: "2026-02-20",
        fecha_limite_ejecucion: "2026-03-31",
        cumplimiento_cnt03: false,
        alerta_acto_base: {
          estado: "REVOCADO",
          mensaje: "El acto base fue revocado.",
          enlace: "/actos/base",
        },
      },
      formalizada: {
        id: "t1",
        codigo: "T-001",
        estado: "FORMALIZADA",
        version: 4,
        figura: "RESCISION_IMPUTABLE",
        figura_etiqueta: "Rescisión imputable",
        causal: "INCUMPLIMIENTO",
        causal_etiqueta: "Incumplimiento",
        causal_referencia: null,
        hechos: "Hechos",
        fundamento: "Fundamento",
        acto: {
          id: "acto-1",
          etiqueta: "Resolución 1/26",
          tipo: "RESOLUCION",
          numero: "1/26",
          fecha: "2026-02-10",
          estado: "EFICAZ",
          fecha_eficacia: "2026-02-20",
          emisor_cargo: "Ministra",
          funcionario: "Fulana",
          enlace: "/actos/1",
        },
        apertura: null,
        documento: null,
        conclusion: null,
        fecha_acto: "2026-02-10",
        fecha_eficacia: "2026-02-20",
        formalizado_en: "2026-03-01T14:30:00Z",
        formalizado_por: "Fulana",
        huella: "abcdef1234567890abcdef",
      },
    });
    renderPagina(data);

    await waitFor(() => expect(screen.getByText("Actuación formalizada")).toBeTruthy());
    expect(screen.getByRole("alert")).toBeTruthy();
    expect(screen.getByText("El acto base fue revocado.")).toBeTruthy();
    expect(screen.getByText(formatearInstante("2026-03-01T14:30:00Z"))).toBeTruthy();
    expect(screen.getByTitle("abcdef1234567890abcdef").textContent).toContain("abcdef123456");
  });

  it("Descargar CSV llama a descargarArchivo con los filtros", async () => {
    const usuario = userEvent.setup();
    renderPagina(vista());

    await waitFor(() => expect(screen.getByLabelText("Figura")).toBeTruthy());

    await usuario.selectOptions(screen.getByLabelText("Figura"), "RESCISION_NO_IMPUTABLE");
    await usuario.type(screen.getByLabelText("Desde"), "2026-01-01");
    await usuario.type(screen.getByLabelText("Hasta"), "2026-03-31");
    await usuario.click(screen.getByRole("button", { name: "Descargar CSV" }));

    await waitFor(() => {
      expect(descargarArchivoMock).toHaveBeenCalledWith(
        "/gobierno/contratos/terminaciones/reporte.csv?figura=RESCISION_NO_IMPUTABLE&desde=2026-01-01&hasta=2026-03-31",
        "terminaciones-contractuales.csv",
      );
    });
  });
});
